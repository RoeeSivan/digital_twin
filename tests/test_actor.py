"""Part A: background block and the messages the Actor sends (no API calls)."""

import pytest

from twin.actor import build_messages, build_system, clean_history
from twin.context import load_background


def test_background_contains_both_sources():
    background = load_background()
    assert '<source id="linkedin"' in background
    assert '<source id="summary"' in background
    assert "Reichman University" in background
    assert "0527" not in background  # phone number was stripped


def test_system_prompt_is_prompt_file_plus_background():
    system = build_system("BACKGROUND")
    assert system.startswith("# Role")
    assert system.endswith("BACKGROUND")


def test_clean_history_accepts_both_gradio_content_shapes():
    history = [
        {"role": "user", "content": "question", "metadata": None, "options": []},
        {"role": "assistant", "content": [{"type": "text", "text": "answer"}], "metadata": {"title": "x"}},
        {"role": "assistant", "content": [{"type": "file", "file": {}}]},  # no text -> dropped
    ]
    assert clean_history(history) == [
        {"role": "user", "content": "question"},
        {"role": "assistant", "content": "answer"},
    ]


def test_first_attempt_sends_history_then_question():
    history = [{"role": "user", "content": "q1"}, {"role": "assistant", "content": "a1"}]
    messages = build_messages("q2", history)
    assert messages[:2] == history
    assert messages[-1] == {"role": "user", "content": [{"type": "text", "text": "q2"}]}


def test_retry_carries_rejected_draft_and_feedback():
    messages = build_messages("q", [], rejected="DRAFT", feedback="FEEDBACK")
    question_block, revision_block = messages[-1]["content"]
    assert question_block["text"] == "q"
    assert "<rejected_draft>\nDRAFT\n</rejected_draft>" in revision_block["text"]
    assert "<critic_feedback>\nFEEDBACK\n</critic_feedback>" in revision_block["text"]


def test_retry_needs_both_draft_and_feedback():
    with pytest.raises(ValueError):
        build_messages("q", [], rejected="DRAFT")
