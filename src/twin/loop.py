"""Generate -> evaluate -> fix loop.

At most MAX_ATTEMPTS generations per question, the first answer included. Every draft is
evaluated. Three exits:

- approved:  the Critic returned is_acceptable=True -> that draft is the answer.
- exhausted: all attempts were rejected -> a stop message, never one of the rejected drafts.
- error:     a model call failed or the Critic's output was invalid -> an error message.

The decision uses only the validated `is_acceptable` boolean of an `Evaluation`.
The attempt counter is local to `answer_question`, so it restarts for every question.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Protocol

from twin.config import MAX_ATTEMPTS
from twin.context import load_background
from twin.llm import TechnicalError
from twin.schemas import AttemptRecord, Evaluation, QuestionRecord, Status

# User-facing text stays in Hebrew (brief A.4).
EXHAUSTED_MESSAGE = (
    f"לא התקבלה תשובה מאושרת במסגרת מגבלת הניסיונות ({MAX_ATTEMPTS} ניסיונות). "
    "אפשר לנסח את השאלה אחרת ולנסות שוב."
)
ERROR_MESSAGE = "אירעה שגיאה טכנית, ולכן הטיפול בשאלה הופסק. אפשר לנסות לשאול שוב."


class AnswerWriter(Protocol):
    """What the loop needs from the Actor (fakes in tests implement the same)."""

    model: str
    effort: str

    def generate(
        self,
        question: str,
        history: list[dict[str, Any]] | None,
        background: str,
        rejected: str | None = None,
        feedback: str | None = None,
    ) -> str: ...


class Reviewer(Protocol):
    """What the loop needs from the Critic (Critic and FakeRejectCritic both match)."""

    kind: Literal["llm", "fake_reject"]
    model: str

    def evaluate(
        self,
        question: str,
        candidate: str,
        background: str,
        history: list[dict[str, Any]] | None,
    ) -> Evaluation: ...


def answer_question(
    question: str,
    history: list[dict[str, Any]] | None,
    *,
    actor: AnswerWriter,
    critic: Reviewer,
    scenario_id: str,
    background: str | None = None,
    first_draft_override: str | None = None,
    max_attempts: int = MAX_ATTEMPTS,
) -> QuestionRecord:
    """Handle one user question and return its full audit record.

    `record.final_text` is what the user should see; `record.attempts` holds every draft,
    verdict and error. `first_draft_override` replaces the Actor's first draft (scenario 4:
    a draft with a planted error, to show the Critic catching it).
    """
    background = load_background() if background is None else background
    attempts: list[AttemptRecord] = []
    rejected: str | None = None
    feedback: str | None = None

    def finish(status: Status, final_text: str) -> QuestionRecord:
        return QuestionRecord(
            scenario_id=scenario_id,
            question=question,
            status=status,
            final_text=final_text,
            attempts=attempts,
            actor_model=actor.model,
            actor_effort=getattr(actor, "effort", None),
            critic_model=critic.model,
            critic_effort=getattr(critic, "effort", None),
            critic_kind=critic.kind,
            timestamp=datetime.now().astimezone().isoformat(timespec="seconds"),
        )

    for attempt in range(1, max_attempts + 1):
        # 1. Generate (or take the injected first draft).
        if attempt == 1 and first_draft_override is not None:
            source, candidate = "injected", first_draft_override
        else:
            source = "actor"
            try:
                candidate = actor.generate(question, history, background, rejected=rejected, feedback=feedback)
            except TechnicalError as e:
                attempts.append(
                    AttemptRecord(
                        attempt=attempt, source=source, candidate=None, evaluation_completed=False,
                        error=f"Answer generation failed: {e}", raw_output=e.raw,
                    )
                )
                return finish("error", ERROR_MESSAGE)

        # 2. Evaluate. A failed or invalid evaluation ends the question; it is never an approval.
        try:
            evaluation = critic.evaluate(question, candidate, background, history)
            if not isinstance(evaluation, Evaluation):
                raise TechnicalError(f"Critic returned {type(evaluation).__name__}, not a validated Evaluation.")
        except TechnicalError as e:
            attempts.append(
                AttemptRecord(
                    attempt=attempt, source=source, candidate=candidate, evaluation_completed=False,
                    error=f"Evaluation not completed: {e}", raw_output=e.raw,
                )
            )
            return finish("error", ERROR_MESSAGE)

        attempts.append(
            AttemptRecord(attempt=attempt, source=source, candidate=candidate, evaluation_completed=True, evaluation=evaluation)
        )

        # 3. Decide on the validated boolean only.
        if evaluation.is_acceptable:
            return finish("approved", candidate)

        # 4. Rejected: the next attempt gets this draft and the feedback.
        rejected, feedback = candidate, evaluation.feedback

    # 5. Every attempt was rejected.
    return finish("exhausted", EXHAUSTED_MESSAGE)
