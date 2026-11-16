"""Smoke test for the environment. Run with: uv run scripts/smoke_test.py

Checks that `.env` provides an API key, that the configured models are reachable,
and that one tiny call succeeds. Prints nothing secret.
"""

from __future__ import annotations

import sys

import anthropic

from twin.config import ACTOR_MODEL, ANTHROPIC_API_KEY, CRITIC_MODEL


def main() -> int:
    if not ANTHROPIC_API_KEY:
        print("ANTHROPIC_API_KEY is missing. Copy .env.example to .env and fill it in.")
        return 1

    client = anthropic.Anthropic()
    for model in sorted({ACTOR_MODEL, CRITIC_MODEL}):
        info = client.models.retrieve(model)
        print(f"model ok: {info.id} ({info.display_name})")

    response = client.messages.create(
        model=ACTOR_MODEL,
        max_tokens=1000,
        output_config={"effort": "low"},
        messages=[{"role": "user", "content": "Reply with the single word: ok"}],
    )
    text = "".join(block.text for block in response.content if block.type == "text")
    print(f"call ok: {text.strip()!r} (stop_reason={response.stop_reason})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
