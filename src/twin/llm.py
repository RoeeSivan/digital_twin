"""Anthropic client wrapper shared by the Actor and the Critic.

Holds the client, the shared call options (server-side refusal fallback) and
`TechnicalError`, raised when a model call fails, is refused, or returns output
that cannot be used. A TechnicalError is never treated as an approval.
"""

from __future__ import annotations

from functools import cache
from typing import Any

import anthropic
from anthropic.types import Message

from twin.config import MAX_TOKENS

# Same pattern as lab 3: if a safety classifier declines a request, the API retries it
# on Anthropic's recommended fallback model inside the same call.
FALLBACK_OPTIONS: dict[str, Any] = {
    "extra_headers": {"anthropic-beta": "server-side-fallback-2026-07-01"},
    "extra_body": {"fallbacks": "default"},
}


class TechnicalError(RuntimeError):
    """A model call did not produce usable output. Ends the question in the `error` state."""

    def __init__(self, message: str, raw: str | None = None) -> None:
        super().__init__(message)
        self.raw = raw


@cache
def get_client() -> anthropic.Anthropic:
    """Created lazily so that tests with fake actors/critics never need an API key."""
    return anthropic.Anthropic()


def create_message(
    *,
    model: str,
    system: str,
    messages: list[dict[str, Any]],
    effort: str,
    output_format: dict[str, Any] | None = None,
) -> Message:
    """One Messages API call. Any API or network failure becomes a TechnicalError."""
    output_config: dict[str, Any] = {"effort": effort}
    if output_format is not None:
        output_config["format"] = output_format
    try:
        return get_client().messages.create(
            model=model,
            max_tokens=MAX_TOKENS,
            system=system,
            messages=messages,
            output_config=output_config,
            **FALLBACK_OPTIONS,
        )
    except anthropic.APIStatusError as e:
        raise TechnicalError(f"API error {e.status_code} ({type(e).__name__}): {e.message}") from e
    except anthropic.APIConnectionError as e:
        raise TechnicalError(f"Network error ({type(e).__name__}): {e}") from e
    except (anthropic.AnthropicError, TypeError) as e:
        # e.g. a missing API key: the SDK raises TypeError before any request is sent.
        raise TechnicalError(f"Model call failed ({type(e).__name__}): {e}") from e


def text_of(response: Message) -> str:
    """Join the text blocks of a finished response. Raises TechnicalError if it is not usable."""
    if response.stop_reason == "refusal":
        category = response.stop_details.category if response.stop_details else None
        raise TechnicalError(f"The model declined to answer (refusal, category={category}).")
    text = "".join(block.text for block in response.content if block.type == "text").strip()
    if response.stop_reason != "end_turn":
        raise TechnicalError(f"Unexpected stop_reason: {response.stop_reason}", raw=text)
    if not text:
        raise TechnicalError("The model returned an empty answer.")
    return text
