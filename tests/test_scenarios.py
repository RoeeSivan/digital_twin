"""The scenario runner and its report, with fake actor/critic (no API calls)."""

from __future__ import annotations

from scripts import run_scenarios as rs
from twin.loop import EXHAUSTED_MESSAGE
from twin.scenarios import SCENARIOS
from twin.schemas import Evaluation

BY_NUMBER = {s.number: s for s in SCENARIOS}


class FakeActor:
    model, effort = "fake-actor", "low"

    def __init__(self, answer: str = "אני לומד ברייכמן ובניתי את UniRate (LinkedIn)") -> None:
        self.answer = answer
        self.calls: list[dict] = []

    def generate(self, question, history, background, rejected=None, feedback=None):
        self.calls.append({"question": question, "history": list(history), "rejected": rejected, "feedback": feedback})
        return self.answer


class RejectInventedCritic:
    """Rejects any draft that mentions Google, approves everything else."""

    kind, model, effort = "llm", "fake-critic", "medium"

    def evaluate(self, question, candidate, background, history):
        if "Google" in candidate:
            return Evaluation(is_acceptable=False, feedback="The Google role is not in the sources (A). Remove it.")
        return Evaluation(is_acceptable=True, feedback="Grounded.")


def run(number: int, actor: FakeActor | None = None):
    return rs.run_scenario(BY_NUMBER[number], actor or FakeActor(), RejectInventedCritic())


def test_five_scenarios_are_defined_and_only_the_fifth_uses_the_fake_critic():
    assert [s.number for s in SCENARIOS] == [1, 2, 3, 4, 5]
    assert [s.fake_critic for s in SCENARIOS] == [False, False, False, False, True]
    assert BY_NUMBER[4].injected_draft and "Google" in BY_NUMBER[4].injected_draft


def test_follow_up_scenario_passes_the_first_answer_as_history():
    actor = FakeActor()
    records = run(2, actor)

    assert len(records) == 2
    assert actor.calls[0]["history"] == []
    assert actor.calls[1]["history"] == [
        {"role": "user", "content": BY_NUMBER[2].questions[0]},
        {"role": "assistant", "content": records[0].final_text},
    ]


def test_scenario_4_injects_the_flawed_draft_and_the_actor_gets_it_with_the_feedback():
    actor = FakeActor()
    (record,) = run(4, actor)

    assert [a.source for a in record.attempts] == ["injected", "actor"]
    assert actor.calls[0]["rejected"] == BY_NUMBER[4].injected_draft
    assert "Google" in actor.calls[0]["feedback"]
    assert all(ok for _, ok in rs.check_scenario(BY_NUMBER[4], [record]))


def test_scenario_4_checks_fail_if_the_critic_approves_the_flawed_draft():
    class ApproveAll(RejectInventedCritic):
        def evaluate(self, question, candidate, background, history):
            return Evaluation(is_acceptable=True, feedback="Fine.")

    records = rs.run_scenario(BY_NUMBER[4], FakeActor(), ApproveAll())
    assert not all(ok for _, ok in rs.check_scenario(BY_NUMBER[4], records))


def test_scenario_5_exhausts_with_the_fake_critic():
    (record,) = run(5)
    assert record.critic_kind == "fake_reject" and record.final_text == EXHAUSTED_MESSAGE
    assert all(ok for _, ok in rs.check_scenario(BY_NUMBER[5], [record]))


def test_report_separates_llm_results_from_the_mock_test():
    report = rs.build_report({n: run(n) for n in (1, 4, 5)})

    llm_part, mock_part = report.split("## פירוט: בדיקת זרימת בקרה עם מעריך מדומה")
    assert "### תרחיש 4" in llm_part and "### תרחיש 5" not in llm_part.split("## פירוט")[1]
    assert "### תרחיש 5" in mock_part
    assert "תרחיש 2" in report.split("**לא הורצו עדיין:**")[1].splitlines()[0]  # missing scenarios are listed
