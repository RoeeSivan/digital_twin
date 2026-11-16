"""Part B: Evaluation schema, explicit validation and the Critic's inputs (no API calls)."""

from types import SimpleNamespace

import pytest

from twin import critic as critic_module
from twin.critic import Critic, FakeRejectCritic, build_user_message, parse_evaluation, render_history
from twin.llm import TechnicalError
from twin.schemas import Evaluation, evaluation_json_schema


# --- schema -----------------------------------------------------------------

def test_schema_has_exactly_the_two_required_fields():
    schema = evaluation_json_schema()
    assert set(schema["properties"]) == {"is_acceptable", "feedback"}
    assert set(schema["required"]) == {"is_acceptable", "feedback"}
    assert schema["properties"]["is_acceptable"]["type"] == "boolean"
    assert schema["properties"]["feedback"]["type"] == "string"
    assert schema["additionalProperties"] is False  # required by structured output


# --- explicit validation ----------------------------------------------------

def test_valid_json_parses():
    ev = parse_evaluation('{"is_acceptable": false, "feedback": "The claim X is not in the sources."}')
    assert ev == Evaluation(is_acceptable=False, feedback="The claim X is not in the sources.")


@pytest.mark.parametrize(
    "raw",
    [
        "this is not json",
        '{"is_acceptable": true}',  # missing feedback
        '{"feedback": "ok"}',  # missing decision
        '{"is_acceptable": "true", "feedback": "ok"}',  # string, not a boolean
        '{"is_acceptable": 1, "feedback": "ok"}',  # number, not a boolean
        '{"is_acceptable": true, "feedback": "   "}',  # blank feedback
        '{"is_acceptable": true, "feedback": "ok", "score": 9}',  # unknown field
        '{"is_acceptable": true, "feedback": "ok"',  # truncated
    ],
)
def test_invalid_output_is_a_technical_error_not_an_approval(raw):
    with pytest.raises(TechnicalError) as excinfo:
        parse_evaluation(raw)
    assert excinfo.value.raw == raw  # raw text kept for the audit log


# --- Critic.evaluate with a stubbed API call ---------------------------------

def _fake_response(text: str, stop_reason: str = "end_turn"):
    return SimpleNamespace(
        stop_reason=stop_reason,
        stop_details=None,
        content=[SimpleNamespace(type="thinking", thinking=""), SimpleNamespace(type="text", text=text)],
    )


def test_evaluate_sends_schema_and_validates(monkeypatch):
    sent = {}

    def fake_create_message(**kwargs):
        sent.update(kwargs)
        return _fake_response('{"is_acceptable": true, "feedback": "Grounded and clear."}')

    monkeypatch.setattr(critic_module, "create_message", fake_create_message)
    ev = Critic().evaluate("q", "answer", "BACKGROUND", [])
    assert ev.is_acceptable is True
    assert sent["output_format"] == {"type": "json_schema", "schema": evaluation_json_schema()}
    assert sent["system"].startswith("# Role")
    assert "BACKGROUND" in sent["messages"][0]["content"]


@pytest.mark.parametrize(
    "text, stop_reason",
    [
        ('{"is_acceptable": true', "max_tokens"),  # cut off
        ("", "refusal"),  # model declined
        ("not json at all", "end_turn"),  # unparseable
    ],
)
def test_evaluate_never_turns_a_failure_into_approval(monkeypatch, text, stop_reason):
    monkeypatch.setattr(critic_module, "create_message", lambda **kw: _fake_response(text, stop_reason))
    with pytest.raises(TechnicalError):
        Critic().evaluate("q", "answer", "BACKGROUND", [])


# --- what the Critic receives -------------------------------------------------

def test_user_message_carries_all_material():
    history = [{"role": "user", "content": "q1"}, {"role": "assistant", "content": [{"type": "text", "text": "a1"}]}]
    msg = build_user_message("q2", "CANDIDATE", "SOURCES", history)
    for part in ("<background_sources>\nSOURCES", "Visitor: q1", "Answer writer: a1", "<question>\nq2", "<candidate_answer>\nCANDIDATE"):
        assert part in msg


def test_history_window_keeps_only_recent_turns():
    history = [{"role": "user" if i % 2 == 0 else "assistant", "content": f"m{i}"} for i in range(10)]
    rendered = render_history(history, limit=4)
    assert "m5" not in rendered and "m6" in rendered and "m9" in rendered


def test_first_question_has_no_history():
    assert "first question" in render_history([])


# --- mock critic ----------------------------------------------------------------

def test_fake_critic_always_rejects_and_is_labelled():
    fake = FakeRejectCritic()
    assert fake.kind == "fake_reject"
    for _ in range(3):
        ev = fake.evaluate("q", "any answer", "SOURCES", [])
        assert ev.is_acceptable is False
        assert "MOCK CRITIC" in ev.feedback
