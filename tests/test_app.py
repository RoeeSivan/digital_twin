"""The chat shows only final_text; drafts and feedback go to the side panel and the session log."""

import app
from twin.audit_log import read_records
from twin.audit_view import render_record_html
from twin.critic import FakeRejectCritic
from twin.loop import EXHAUSTED_MESSAGE, answer_question
from twin.scenarios import INJECTED_FLAWED_DRAFT
from twin.schemas import Evaluation


class FakeActor:
    model, effort = "fake-actor", "low"

    def __init__(self):
        self.n = 0

    def generate(self, question, history, background, rejected=None, feedback=None):
        self.n += 1
        return f"draft-{self.n}"


class RejectOnceCritic:
    kind, model = "llm", "fake-critic"

    def __init__(self):
        self.n = 0

    def evaluate(self, question, candidate, background, history):
        self.n += 1
        return Evaluation(is_acceptable=self.n > 1, feedback="fix it" if self.n == 1 else "ok")


def test_respond_shows_only_the_approved_answer_and_logs_every_attempt(monkeypatch, tmp_path):
    log = tmp_path / "session.json"
    monkeypatch.setattr(app, "actor", FakeActor())
    monkeypatch.setattr(app, "critic", RejectOnceCritic())
    monkeypatch.setattr(app, "SESSION_LOG", log)

    shown, panel_html, panel = app.respond("שאלה", [])

    assert shown == "draft-2"
    assert [a["candidate"] for a in panel["attempts"]] == ["draft-1", "draft-2"]  # rejected draft only in the panel
    assert "draft-1" in panel_html and "fix it" in panel_html  # the side panel shows the rejected draft and the feedback
    assert read_records(log)[0].status == "approved"


def test_respond_shows_the_stop_message_when_attempts_run_out(monkeypatch, tmp_path):
    monkeypatch.setattr(app, "actor", FakeActor())
    monkeypatch.setattr(app, "critic", FakeRejectCritic())
    monkeypatch.setattr(app, "SESSION_LOG", tmp_path / "session.json")

    shown, _, panel = app.respond("שאלה", [])

    assert shown == EXHAUSTED_MESSAGE
    assert panel["status"] == "exhausted" and len(panel["attempts"]) == 3


def test_injected_draft_mode_evaluates_the_flawed_draft_first(monkeypatch, tmp_path):
    actor, critic = FakeActor(), RejectOnceCritic()
    monkeypatch.setattr(app, "actor", actor)
    monkeypatch.setattr(app, "critic", critic)
    monkeypatch.setattr(app, "SESSION_LOG", tmp_path / "session.json")

    shown, panel_html, panel = app.respond("שאלה", [], app.MODE_INJECTED)

    assert panel["attempts"][0]["source"] == "injected"
    assert panel["attempts"][0]["candidate"] == INJECTED_FLAWED_DRAFT
    assert shown == "draft-1" and actor.n == 1  # the Actor wrote only the corrected version
    assert "טיוטת מבחן מוזרקת" in panel_html


def test_fake_critic_mode_is_labelled_as_a_control_flow_test(monkeypatch, tmp_path):
    monkeypatch.setattr(app, "actor", FakeActor())
    monkeypatch.setattr(app, "critic", RejectOnceCritic())
    monkeypatch.setattr(app, "SESSION_LOG", tmp_path / "session.json")

    shown, panel_html, panel = app.respond("שאלה", [], app.MODE_FAKE_CRITIC)

    assert shown == EXHAUSTED_MESSAGE
    assert panel["critic_kind"] == "fake_reject"
    assert "מעריך מדומה" in panel_html


def test_audit_panel_escapes_model_text():
    record = answer_question(
        "<script>alert(1)</script>", [], actor=FakeActor(), critic=RejectOnceCritic(), scenario_id="t", background="S"
    )
    assert "<script>" not in render_record_html(record)
