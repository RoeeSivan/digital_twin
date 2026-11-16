"""Control-flow tests for the generate -> evaluate -> fix loop, with fake actor/critic (no API calls)."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from twin import critic as critic_module
from twin.audit_log import append_record, read_records, session_log_path
from twin.critic import Critic, FakeRejectCritic
from twin.llm import TechnicalError
from twin.loop import ERROR_MESSAGE, EXHAUSTED_MESSAGE, answer_question
from twin.schemas import Evaluation

BACKGROUND = "SOURCES"


class FakeActor:
    """Returns draft-1, draft-2, ... and records what it was given on each call."""

    model = "fake-actor"
    effort = "low"

    def __init__(self, fail_on_call: int | None = None) -> None:
        self.calls: list[dict] = []
        self.fail_on_call = fail_on_call

    def generate(self, question, history, background, rejected=None, feedback=None) -> str:
        self.calls.append({"question": question, "history": history, "rejected": rejected, "feedback": feedback})
        if len(self.calls) == self.fail_on_call:
            raise TechnicalError("API error 529 (OverloadedError): overloaded")
        return f"draft-{len(self.calls)}"


class ScriptedCritic:
    """Returns (or raises) the scripted results in order."""

    kind = "llm"
    model = "scripted-critic"
    effort = "medium"

    def __init__(self, *results) -> None:
        self.results = list(results)
        self.seen: list[str] = []

    def evaluate(self, question, candidate, background, history):
        self.seen.append(candidate)
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


APPROVE = Evaluation(is_acceptable=True, feedback="Grounded and clear.")


def reject(text: str) -> Evaluation:
    return Evaluation(is_acceptable=False, feedback=text)


def run(actor, critic, **kwargs):
    return answer_question("q", [], actor=actor, critic=critic, scenario_id="test", background=BACKGROUND, **kwargs)


# --- the three exits --------------------------------------------------------------

def test_approved_on_first_attempt():
    actor = FakeActor()
    record = run(actor, ScriptedCritic(APPROVE))
    assert record.status == "approved"
    assert record.final_text == "draft-1"
    assert len(record.attempts) == 1
    assert actor.calls[0]["rejected"] is None and actor.calls[0]["feedback"] is None


def test_reject_then_approve_passes_draft_and_feedback_to_the_actor():
    actor = FakeActor()
    critic = ScriptedCritic(reject("Remove the Google claim (A)."), APPROVE)
    record = run(actor, critic)

    assert record.status == "approved"
    assert record.final_text == "draft-2"
    assert critic.seen == ["draft-1", "draft-2"]  # every new draft is evaluated again
    assert actor.calls[1]["rejected"] == "draft-1"
    assert actor.calls[1]["feedback"] == "Remove the Google claim (A)."
    assert [a.evaluation.is_acceptable for a in record.attempts] == [False, True]


def test_three_rejections_exhaust_and_show_no_draft():
    actor = FakeActor()
    record = run(actor, FakeRejectCritic())

    assert record.status == "exhausted"
    assert len(record.attempts) == 3 and len(actor.calls) == 3  # stops after the third attempt
    assert record.final_text == EXHAUSTED_MESSAGE
    assert record.final_text not in {a.candidate for a in record.attempts}
    assert record.critic_kind == "fake_reject"
    # each retry gets the previous rejected draft
    assert [c["rejected"] for c in actor.calls] == [None, "draft-1", "draft-2"]


def test_critic_error_ends_in_error_not_approval():
    critic = ScriptedCritic(reject("fix X"), TechnicalError("Network error (APIConnectionError)"))
    record = run(FakeActor(), critic)

    assert record.status == "error"
    assert record.final_text == ERROR_MESSAGE
    failed = record.attempts[-1]
    assert failed.attempt == 2 and failed.candidate == "draft-2"
    assert failed.evaluation_completed is False and failed.evaluation is None
    assert "Evaluation not completed" in failed.error


def test_invalid_json_from_the_real_critic_ends_in_error(monkeypatch):
    bad = SimpleNamespace(stop_reason="end_turn", stop_details=None, content=[SimpleNamespace(type="text", text="looks fine to me")])
    monkeypatch.setattr(critic_module, "create_message", lambda **kw: bad)
    record = run(FakeActor(), Critic())

    assert record.status == "error"
    assert record.attempts[0].evaluation is None
    assert record.attempts[0].raw_output == "looks fine to me"  # unusable output kept in the log


def test_critic_returning_an_unvalidated_object_is_an_error():
    record = run(FakeActor(), ScriptedCritic({"is_acceptable": True, "feedback": "ok"}))
    assert record.status == "error"
    assert record.final_text == ERROR_MESSAGE


def test_actor_error_ends_in_error_without_calling_the_critic():
    critic = ScriptedCritic(reject("fix X"))
    record = run(FakeActor(fail_on_call=2), critic)

    assert record.status == "error"
    assert critic.seen == ["draft-1"]
    assert record.attempts[-1].candidate is None
    assert "Answer generation failed" in record.attempts[-1].error


# --- scenario hooks --------------------------------------------------------------

def test_injected_first_draft_is_evaluated_and_then_fixed_by_the_actor():
    actor = FakeActor()
    critic = ScriptedCritic(reject("I never worked at Google (A)."), APPROVE)
    record = run(actor, critic, first_draft_override="עבדתי בגוגל")

    assert [a.source for a in record.attempts] == ["injected", "actor"]
    assert critic.seen[0] == "עבדתי בגוגל"
    assert len(actor.calls) == 1 and actor.calls[0]["rejected"] == "עבדתי בגוגל"
    assert record.final_text == "draft-1"


def test_counter_restarts_and_history_is_passed_on_the_next_question():
    history = [{"role": "user", "content": "q0"}, {"role": "assistant", "content": "a0"}]
    first = answer_question("q1", [], actor=FakeActor(), critic=FakeRejectCritic(), scenario_id="t", background=BACKGROUND)
    actor = FakeActor()
    second = answer_question("q2", history, actor=actor, critic=FakeRejectCritic(), scenario_id="t", background=BACKGROUND)

    assert len(first.attempts) == 3 and len(second.attempts) == 3
    assert [a.attempt for a in second.attempts] == [1, 2, 3]
    assert actor.calls[0]["history"] == history


# --- audit log ------------------------------------------------------------------

def test_audit_log_round_trip_keeps_hebrew_readable(tmp_path):
    path = session_log_path(logs_dir=tmp_path)
    ok = run(FakeActor(), ScriptedCritic(reject("fix X"), APPROVE))
    failed = run(FakeActor(), ScriptedCritic(TechnicalError("bad JSON", raw="{oops")))
    append_record(path, ok)
    append_record(path, failed)

    records = read_records(path)
    assert [r.status for r in records] == ["approved", "error"]
    assert records[0].attempts[0].evaluation.feedback == "fix X"

    data = json.loads(path.read_text(encoding="utf-8"))
    assert data[1]["attempts"][0]["evaluation"] is None
    assert data[1]["attempts"][0]["evaluation_completed"] is False
    assert ERROR_MESSAGE in path.read_text(encoding="utf-8")  # Hebrew stored as text, not \u escapes


@pytest.mark.parametrize("status", ["approved", "exhausted", "error"])
def test_each_exit_is_distinguishable_in_the_log(status):
    critics = {
        "approved": ScriptedCritic(APPROVE),
        "exhausted": FakeRejectCritic(),
        "error": ScriptedCritic(TechnicalError("boom")),
    }
    assert run(FakeActor(), critics[status]).status == status
