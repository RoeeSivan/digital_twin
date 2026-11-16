"""Pydantic models.

- Evaluation: the Critic's structured verdict (required by the brief: is_acceptable, feedback).
- AttemptRecord / QuestionRecord: audit-log entries for every attempt and every question.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Evaluation(BaseModel):
    """The Critic's verdict. The loop decides only on `is_acceptable`, after validation."""

    # extra="forbid": an unknown field fails validation (and the JSON schema gets
    # additionalProperties: false, which structured output requires).
    # strict=True: is_acceptable must be a real JSON boolean; the string "true" is rejected.
    model_config = ConfigDict(extra="forbid", strict=True)

    is_acceptable: bool = Field(description="True only if the candidate answer meets all four criteria.")
    feedback: str = Field(
        description=(
            "Short justification. On rejection: quote each problematic part of the answer, "
            "name the criterion it breaks, and say exactly what to change."
        )
    )

    @field_validator("feedback")
    @classmethod
    def feedback_not_blank(cls, value: str) -> str:
        # Checked here, not in the JSON schema: structured output does not support minLength.
        if not value.strip():
            raise ValueError("feedback must not be empty")
        return value


def evaluation_json_schema() -> dict[str, Any]:
    """The JSON schema sent to the API as the Critic's output format."""
    return Evaluation.model_json_schema()


# --- audit log ------------------------------------------------------------------

Status = Literal["approved", "exhausted", "error"]


class AttemptRecord(BaseModel):
    """One generation attempt and what happened to it."""

    attempt: int = Field(ge=1, description="1 to MAX_ATTEMPTS. The counter restarts for every question.")
    source: Literal["actor", "injected"] = Field(
        description="'injected' = a fixed first draft supplied by a test scenario instead of the Actor."
    )
    candidate: str | None = Field(description="The draft that was evaluated. None only if the Actor call failed.")
    evaluation_completed: bool = Field(
        description="False when the Critic produced no valid verdict. Then `evaluation` is None, not a guessed decision."
    )
    evaluation: Evaluation | None = None
    error: str | None = None
    raw_output: str | None = Field(default=None, description="Unusable model output kept for debugging.")


class QuestionRecord(BaseModel):
    """Everything that happened while handling one user question."""

    scenario_id: str
    question: str
    status: Status
    final_text: str = Field(description="What the user saw: the approved answer, the stop message or the error message.")
    attempts: list[AttemptRecord]
    actor_model: str
    actor_effort: str | None
    critic_model: str
    critic_effort: str | None
    critic_kind: Literal["llm", "fake_reject"]
    timestamp: str
