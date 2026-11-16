"""Part D: run the five required scenarios and write the results.

    uv run scripts/run_scenarios.py            # run all five
    uv run scripts/run_scenarios.py --only 4   # re-run one scenario
    uv run scripts/run_scenarios.py --report   # rebuild results/scenarios.md from the saved logs, no API calls

Output:
    logs/scenario_<n>.json   the audit log of each scenario (one QuestionRecord per question)
    results/scenarios.md     input, attempts, displayed output and expected-vs-actual, in Hebrew

Scenarios 1-4 use the real LLM Critic. Scenario 4 injects a flawed first draft.
Scenario 5 uses FakeRejectCritic: a control-flow test, reported in its own section.
"""

from __future__ import annotations

import argparse
from typing import Any

from twin.actor import Actor
from twin.audit_log import read_records, write_records
from twin.config import LOGS_DIR, MAX_ATTEMPTS, RESULTS_DIR
from twin.critic import Critic, FakeRejectCritic
from twin.loop import EXHAUSTED_MESSAGE, answer_question
from twin.scenarios import INVENTED_PHRASES, SCENARIOS, Scenario
from twin.schemas import AttemptRecord, QuestionRecord

REPORT_PATH = RESULTS_DIR / "scenarios.md"
SCREENSHOTS_DIR = RESULTS_DIR / "screenshots"

Check = tuple[str, bool]  # (what was checked, in Hebrew; did it hold)


def log_path(scenario: Scenario):
    return LOGS_DIR / f"{scenario.scenario_id}.json"


# --- running ----------------------------------------------------------------------

def run_scenario(scenario: Scenario, actor: Actor, critic: Critic) -> list[QuestionRecord]:
    """Ask the scenario's questions in one conversation. History grows the way the chat UI grows it."""
    history: list[dict[str, Any]] = []
    records = []
    for index, question in enumerate(scenario.questions):
        is_last = index == len(scenario.questions) - 1
        record = answer_question(
            question,
            history,
            actor=actor,
            critic=FakeRejectCritic() if scenario.fake_critic else critic,
            scenario_id=scenario.scenario_id,
            first_draft_override=scenario.injected_draft if is_last else None,
        )
        records.append(record)
        # The displayed history holds the user message and the final text shown to the user.
        history += [{"role": "user", "content": question}, {"role": "assistant", "content": record.final_text}]
    return records


# --- expected vs actual -------------------------------------------------------------

def _verdicts(record: QuestionRecord) -> list[bool | None]:
    return [a.evaluation.is_acceptable if a.evaluation else None for a in record.attempts]


def check_scenario(scenario: Scenario, records: list[QuestionRecord]) -> list[Check]:
    """Automatic checks of the control flow and of simple text markers.

    They do not prove the content is true: that is the manual check in results/manual_check.md.
    """
    last = records[-1]
    final = last.final_text
    if scenario.number == 1:
        return [
            ("הסתיים באישור", last.status == "approved"),
            (
                "התשובה מזכירה את רייכמן ואת UniRate",
                ("רייכמן" in final or "Reichman" in final) and "unirate" in final.lower(),
            ),
            ("התשובה מפנה למקור: (LinkedIn) או (סיכום אישי)", "LinkedIn" in final or "סיכום אישי" in final),
        ]
    if scenario.number == 2:
        technologies = [t for t in ("Next.js", "TypeScript", "Prisma", "PostgreSQL") if t in final]
        return [
            ("שתי הפניות הסתיימו באישור", all(r.status == "approved" for r in records)),
            ("הפנייה השנייה קיבלה את ההיסטוריה, והתשובה מפרטת את הטכנולוגיות של UniRate", len(technologies) >= 3),
        ]
    if scenario.number == 3:
        markers = ("אין", "לא מופיע", "לא מצוין", "לא כולל", "לא מציינ")
        return [
            ("הסתיים באישור", last.status == "approved"),
            ("התשובה מציינת שהמידע חסר", any(m in final for m in markers)),
            ("אין בתשובה ציון מספרי", not any(ch.isdigit() for ch in final)),
        ]
    if scenario.number == 4:
        first = last.attempts[0]
        return [
            ("הניסיון הראשון הוא הטיוטה המוזרקת", first.source == "injected" and first.candidate == scenario.injected_draft),
            ("המעריך דחה את הטיוטה המוזרקת", first.evaluation is not None and not first.evaluation.is_acceptable),
            ("המשוב מצביע על הטענה המומצאת (Google)", first.evaluation is not None and "Google" in first.evaluation.feedback),
            ("נוצרה גרסה מתוקנת והיא נבדקה שוב", len(last.attempts) >= 2 and last.attempts[1].source == "actor"),
            ("הסתיים באישור", last.status == "approved"),
            ("הטענות המומצאות לא מופיעות בתשובה הסופית", not any(p in final for p in INVENTED_PHRASES)),
        ]
    if scenario.number == 5:
        drafts = {a.candidate for a in last.attempts}
        return [
            ("מעריך מדומה (critic_kind = fake_reject)", last.critic_kind == "fake_reject"),
            (f"בדיוק {MAX_ATTEMPTS} ניסיונות", len(last.attempts) == MAX_ATTEMPTS),
            ("כל הניסיונות נדחו", _verdicts(last) == [False] * MAX_ATTEMPTS),
            ("מצב הסיום הוא exhausted", last.status == "exhausted"),
            ("הוצגה הודעת הסיום ולא אחת מהטיוטות", final == EXHAUSTED_MESSAGE and final not in drafts),
        ]
    raise ValueError(f"no checks defined for scenario {scenario.number}")


# --- report ---------------------------------------------------------------------

STATUS_HE = {"approved": "אישור", "exhausted": "מיצוי ניסיונות", "error": "שגיאה טכנית"}


def _cell(text: str) -> str:
    """Make free text safe for one Markdown table cell."""
    return text.replace("|", "\\|").replace("\n", "<br>")


def _quote(text: str) -> str:
    return "\n".join(f"> {line}" if line else ">" for line in text.splitlines())


def _verdict_he(attempt: AttemptRecord) -> str:
    if attempt.evaluation is None:
        return "ההערכה לא הושלמה"
    return "אושר (`true`)" if attempt.evaluation.is_acceptable else "נדחה (`false`)"


def _attempts_table(record: QuestionRecord) -> str:
    rows = ["| ניסיון | מקור הטיוטה | החלטת המעריך | משוב המעריך |", "|---|---|---|---|"]
    for a in record.attempts:
        source = "טיוטת מבחן מוזרקת" if a.source == "injected" else "היוצר"
        feedback = a.evaluation.feedback if a.evaluation else (a.error or "")
        rows.append(f"| {a.attempt} | {source} | {_verdict_he(a)} | {_cell(feedback)} |")
    return "\n".join(rows)


def _question_section(record: QuestionRecord, label: str) -> str:
    parts = [f"**{label}:** {record.question}", "", _attempts_table(record), ""]
    for a in record.attempts:
        if a.candidate is not None:
            parts += [f"טיוטה {a.attempt}:", "", _quote(a.candidate), ""]
    parts += [f"**הפלט שהוצג למשתמש** (מצב סיום: {STATUS_HE[record.status]}, `{record.status}`):", "", _quote(record.final_text), ""]
    return "\n".join(parts)


def _scenario_section(scenario: Scenario, records: list[QuestionRecord]) -> str:
    checks = check_scenario(scenario, records)
    matched = all(ok for _, ok in checks)
    parts = [f"### תרחיש {scenario.number}: {scenario.title}", "", f"**ציפייה:** {scenario.expected}", ""]
    if scenario.injected_draft:
        parts += ["**טיוטת המבחן שהוזנה כתשובה ראשונה** (עובדה אישית מומצאת):", "", _quote(scenario.injected_draft), ""]
    for index, record in enumerate(records, start=1):
        label = "קלט" if len(records) == 1 else f"פנייה {index}"
        parts.append(_question_section(record, label))
    parts += ["**בדיקות אוטומטיות:**", ""]
    parts += [f"- {'✅' if ok else '❌'} {text}" for text, ok in checks]
    parts += ["", f"**האם ההתנהגות בפועל תאמה את הציפייה:** {'כן' if matched else 'לא'}", ""]
    parts.append(f"יומן מלא: [`logs/{scenario.scenario_id}.json`](../logs/{scenario.scenario_id}.json)")
    shots = sorted(SCREENSHOTS_DIR.glob(f"{scenario.scenario_id}*.png"))
    if shots:
        parts += ["", "צילומי מסך (הרצה נפרדת של אותו קלט בממשק, ראו הערה בראש המסמך):", ""]
        parts += [f"![{shot.stem}](screenshots/{shot.name})" for shot in shots]
    return "\n".join(parts) + "\n"


def _summary_row(scenario: Scenario, records: list[QuestionRecord]) -> str:
    last = records[-1]
    matched = all(ok for _, ok in check_scenario(scenario, records))
    attempts = " + ".join(str(len(r.attempts)) for r in records)
    return (
        f"| {scenario.number} | {scenario.title} | {_cell(' / '.join(r.question for r in records))} "
        f"| {attempts} | {STATUS_HE[last.status]} | {'כן' if matched else 'לא'} |"
    )


def build_report(results: dict[int, list[QuestionRecord]]) -> str:
    """results: scenario number -> its records. Scenarios without a saved log are listed as not run."""
    done = [s for s in SCENARIOS if s.number in results]
    sample = results[done[0].number][0] if done else None
    header = "| # | תרחיש | קלט | ניסיונות | מצב סיום | תאם את הציפייה |\n|---|---|---|---|---|---|"
    llm = [s for s in done if not s.fake_critic]
    fake = [s for s in done if s.fake_critic]
    critic_sample = results[llm[0].number][0] if llm else sample  # a record made with the real Critic

    parts = ["# תוצאות חמשת התרחישים (חלק ד)", ""]
    parts += [
        "המסמך נוצר אוטומטית על ידי `scripts/run_scenarios.py` מתוך היומנים שב-`logs/`. "
        "לכל תרחיש מופיעים הקלט, יומן הניסיונות, הפלט שהוצג למשתמש, והשוואה בין הציפייה להתנהגות בפועל.",
        "",
    ]
    if sample:
        parts += [
            f"- **היוצר (Actor):** `{sample.actor_model}`, effort `{sample.actor_effort}`",
            f"- **המעריך (Critic):** `{critic_sample.critic_model}`, effort `{critic_sample.critic_effort}`",
            f"- **מגבלת ניסיונות:** {MAX_ATTEMPTS} לכל שאלה, כולל התשובה הראשונה",
            f"- **מועד ההרצה:** {sample.timestamp}",
            "",
        ]
    parts += [
        "הבדיקות האוטומטיות בודקות את זרימת הבקרה וסימנים פשוטים בטקסט. הן לא מוכיחות שהתוכן נכון. "
        "בדיקה ידנית של הטענות מול המקורות מופיעה ב-[`manual_check.md`](manual_check.md).",
        "",
        "צילומי המסך צולמו בהרצה נפרדת של אותם קלטים דרך ממשק הצ'אט, ולכן ניסוח התשובות בהם יכול להיות "
        "שונה מעט מהניסוח שביומני התרחישים. היומן של הרצת הצילומים שמור ב-"
        "[`logs/session_screenshots.json`](../logs/session_screenshots.json).",
        "",
        "## סיכום",
        "",
        "### תוצאות שהתקבלו ממודל שפה (תרחישים 1 עד 4, מעריך אמיתי)",
        "",
        header,
        *[_summary_row(s, results[s.number]) for s in llm],
        "",
        "### תוצאות של בדיקה מדומה (תרחיש 5, בדיקת זרימת בקרה)",
        "",
        "בתרחיש זה המעריך הוא `FakeRejectCritic`: רכיב מדומה שמחזיר דחייה בכל ניסיון ולא קורא למודל שפה. "
        "הטיוטות עצמן נכתבו על ידי היוצר האמיתי. התרחיש בודק רק שהלולאה נעצרת אחרי הניסיון השלישי. "
        "הוא לא אומר דבר על איכות ההערכה.",
        "",
        header,
        *[_summary_row(s, results[s.number]) for s in fake],
        "",
    ]
    missing = [s for s in SCENARIOS if s.number not in results]
    if missing:
        parts += ["**לא הורצו עדיין:** " + ", ".join(f"תרחיש {s.number}" for s in missing), ""]

    parts += ["## פירוט: תרחישים עם מעריך אמיתי (מודל שפה)", ""]
    parts += [_scenario_section(s, results[s.number]) for s in llm]
    parts += ["## פירוט: בדיקת זרימת בקרה עם מעריך מדומה", ""]
    parts += [_scenario_section(s, results[s.number]) for s in fake]
    return "\n".join(parts).rstrip() + "\n"


def load_results() -> dict[int, list[QuestionRecord]]:
    return {s.number: read_records(log_path(s)) for s in SCENARIOS if log_path(s).exists()}


# --- entry point ----------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--only", type=int, choices=[s.number for s in SCENARIOS], help="run one scenario")
    parser.add_argument("--report", action="store_true", help="only rebuild results/scenarios.md from saved logs")
    args = parser.parse_args()

    if not args.report:
        actor, critic = Actor(), Critic()
        for scenario in SCENARIOS:
            if args.only not in (None, scenario.number):
                continue
            print(f"Scenario {scenario.number}: {scenario.title} ...", flush=True)
            records = run_scenario(scenario, actor, critic)
            write_records(log_path(scenario), records)
            for record in records:
                print(f"  {record.status:9} attempts={len(record.attempts)}  {record.question}")
            for text, ok in check_scenario(scenario, records):
                print(f"  [{'ok' if ok else 'FAIL'}] {text}")

    results = load_results()
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(build_report(results), encoding="utf-8")
    print(f"\nWrote {REPORT_PATH.relative_to(RESULTS_DIR.parent)} ({len(results)}/{len(SCENARIOS)} scenarios)")


if __name__ == "__main__":
    main()
