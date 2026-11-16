"""Actor: generates a candidate answer in Hebrew.

Each call receives the system prompt (prompts/actor_system.md + background),
the cleaned conversation history and the user question. On a retry it also
receives the rejected draft and the Critic's feedback, in the same user turn.
"""

from __future__ import annotations

from functools import cache
from typing import Any

from twin.config import ACTOR_EFFORT, ACTOR_MODEL, PROMPTS_DIR
from twin.llm import create_message, text_of

ACTOR_PROMPT_PATH = PROMPTS_DIR / "actor_system.md"


@cache
def load_actor_prompt() -> str:
    return ACTOR_PROMPT_PATH.read_text(encoding="utf-8").strip()


def build_system(background: str) -> str:
    """System prompt = role and rules, then the background sources (as in lab 3)."""
    return f"{load_actor_prompt()}\n\n# Background sources\n\n{background}"


def _text_of_content(content: Any) -> str:
    """Gradio 6 history content is either a string or a list of parts like {"type": "text", "text": ...}."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            part.get("text", "") for part in content if isinstance(part, dict) and part.get("type") == "text"
        )
    return ""


def clean_history(history: list[dict[str, Any]] | None) -> list[dict[str, str]]:
    """Keep only role + plain text of user/assistant turns.

    Gradio history items carry extra keys (metadata, options) that the Anthropic API rejects.
    """
    cleaned = []
    for item in history or []:
        role = item.get("role")
        text = _text_of_content(item.get("content")).strip()
        if role in ("user", "assistant") and text:
            cleaned.append({"role": role, "content": text})
    return cleaned


def revision_request(rejected: str, feedback: str) -> str:
    """The extra block a retry adds after the question: the rejected draft and the Critic's feedback."""
    return (
        "<revision_request>\n"
        "Your previous draft for this question was rejected in review.\n\n"
        f"<rejected_draft>\n{rejected}\n</rejected_draft>\n\n"
        f"<critic_feedback>\n{feedback}\n</critic_feedback>\n\n"
        "Write a new, complete answer to the question above. "
        "Fix what the feedback points to and keep what was correct.\n"
        "</revision_request>"
    )


def build_messages(
    question: str,
    history: list[dict[str, Any]] | None,
    rejected: str | None = None,
    feedback: str | None = None,
) -> list[dict[str, Any]]:
    """Cleaned history + the question; on a retry the question turn also carries the revision block."""
    if (rejected is None) != (feedback is None):
        raise ValueError("rejected and feedback must be given together")
    content: list[dict[str, str]] = [{"type": "text", "text": question}]
    if rejected is not None and feedback is not None:
        content.append({"type": "text", "text": revision_request(rejected, feedback)})
    return clean_history(history) + [{"role": "user", "content": content}]


class Actor:
    """Generates answers with Claude. `generate` is the interface the loop (Part C) depends on."""

    def __init__(self, model: str = ACTOR_MODEL, effort: str = ACTOR_EFFORT) -> None:
        self.model = model
        self.effort = effort

    def generate(
        self,
        question: str,
        history: list[dict[str, Any]] | None,
        background: str,
        rejected: str | None = None,
        feedback: str | None = None,
    ) -> str:
        response = create_message(
            model=self.model,
            system=build_system(background),
            messages=build_messages(question, history, rejected, feedback),
            effort=self.effort,
        )
        return text_of(response)
