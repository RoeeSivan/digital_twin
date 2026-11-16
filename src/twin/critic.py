"""Critic: evaluates a candidate answer against the sources and the four criteria.

System Evaluator = prompts/critic_system.md (criteria + decision rule).
User Evaluator   = the material to evaluate: sources, recent history, question, candidate answer.

The model is asked for structured output (JSON schema derived from `Evaluation`), and the
text is then validated explicitly with `Evaluation.model_validate_json`. Any call failure,
refusal, truncated output or validation error raises TechnicalError, never an approval.
Also provides FakeRejectCritic for the control-flow test (scenario 5).
"""

from __future__ import annotations

from functools import cache
from typing import Any, Literal

from pydantic import ValidationError

from twin.actor import clean_history
from twin.config import CRITIC_EFFORT, CRITIC_HISTORY_MESSAGES, CRITIC_MODEL, PROMPTS_DIR
from twin.llm import TechnicalError, create_message, text_of
from twin.schemas import Evaluation, evaluation_json_schema

CRITIC_PROMPT_PATH = PROMPTS_DIR / "critic_system.md"


@cache
def load_critic_prompt() -> str:
    return CRITIC_PROMPT_PATH.read_text(encoding="utf-8").strip()


def render_history(history: list[dict[str, Any]] | None, limit: int = CRITIC_HISTORY_MESSAGES) -> str:
    """The last `limit` history messages as a plain transcript."""
    recent = clean_history(history)[-limit:] if limit > 0 else []
    if not recent:
        return "(No earlier turns: this is the first question in the conversation.)"
    speaker = {"user": "Visitor", "assistant": "Answer writer"}
    return "\n\n".join(f"{speaker[m['role']]}: {m['content']}" for m in recent)


def build_user_message(question: str, candidate: str, background: str, history: list[dict[str, Any]] | None) -> str:
    """User Evaluator: everything the Critic needs to check the candidate answer."""
    return (
        f"<background_sources>\n{background}\n</background_sources>\n\n"
        f"<conversation_history>\n{render_history(history)}\n</conversation_history>\n\n"
        f"<question>\n{question}\n</question>\n\n"
        f"<candidate_answer>\n{candidate}\n</candidate_answer>\n\n"
        "Evaluate the candidate answer against criteria A to D and return your decision."
    )


def parse_evaluation(text: str) -> Evaluation:
    """Explicit validation against the schema. Invalid JSON, a missing field or a wrong type -> TechnicalError."""
    try:
        return Evaluation.model_validate_json(text)
    except ValidationError as e:
        raise TechnicalError(f"Critic output failed validation: {e.errors(include_url=False)}", raw=text) from e


class Critic:
    """Evaluates answers with Claude. `evaluate` is the interface the loop (Part C) depends on."""

    kind: Literal["llm", "fake_reject"] = "llm"

    def __init__(self, model: str = CRITIC_MODEL, effort: str = CRITIC_EFFORT) -> None:
        self.model = model
        self.effort = effort

    def evaluate(
        self,
        question: str,
        candidate: str,
        background: str,
        history: list[dict[str, Any]] | None,
    ) -> Evaluation:
        response = create_message(
            model=self.model,
            system=load_critic_prompt(),
            messages=[{"role": "user", "content": build_user_message(question, candidate, background, history)}],
            effort=self.effort,
            output_format={"type": "json_schema", "schema": evaluation_json_schema()},
        )
        return parse_evaluation(text_of(response))


class FakeRejectCritic:
    """Mock critic for scenario 5: rejects every attempt. Makes no API call.

    Used only to test the control flow (exhaustion after MAX_ATTEMPTS); every log it
    touches is marked critic_kind="fake_reject".
    """

    kind: Literal["llm", "fake_reject"] = "fake_reject"
    model = "fake-reject-critic"
    FEEDBACK = (
        "[MOCK CRITIC - control-flow test] This critic rejects every answer on purpose, "
        "to test that the loop stops after the maximum number of attempts."
    )

    def evaluate(
        self,
        question: str,
        candidate: str,
        background: str,
        history: list[dict[str, Any]] | None,
    ) -> Evaluation:
        return Evaluation(is_acceptable=False, feedback=self.FEEDBACK)
