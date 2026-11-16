"""The five required scenarios (brief, Part D), shared by scripts/run_scenarios.py and the chat's test modes.

Scenarios 1-4 use the real LLM Critic. Scenario 4 replaces the Actor's first draft with a
fixed flawed draft. Scenario 5 uses FakeRejectCritic and is a control-flow test only.
"""

from __future__ import annotations

from dataclasses import dataclass

# Scenario 4: a first draft with invented personal facts (Roee never worked at Google and never led a team).
# The first sentence is true, so the Critic has to find the invented part, not reject everything.
INJECTED_FLAWED_DRAFT = (
    "עבדתי כ-QA Engineer ב-Agora (LinkedIn). לפני כן עבדתי שנתיים ב-Google כמהנדס תוכנה בכיר, "
    "ושם הובלתי צוות של חמישה מפתחים."
)
# Phrases that exist only in the invented part; none of them may survive into the final answer.
INVENTED_PHRASES = ("מהנדס תוכנה בכיר", "צוות של חמישה", "שנתיים ב-Google")


@dataclass(frozen=True)
class Scenario:
    number: int
    title: str  # Hebrew, used in results/scenarios.md
    questions: tuple[str, ...]  # asked in order, in one conversation
    expected: str  # Hebrew, the expected behaviour
    injected_draft: str | None = None
    fake_critic: bool = False

    @property
    def scenario_id(self) -> str:
        return f"scenario_{self.number}"


SCENARIOS: tuple[Scenario, ...] = (
    Scenario(
        number=1,
        title="שאלה על מידע קיים",
        questions=("איפה אתה לומד ומה הפרויקט המרכזי שלך?",),
        expected="תשובה מאושרת שמבוססת על המקורות (אוניברסיטת רייכמן, UniRate) ומפנה למקור התומך.",
    ),
    Scenario(
        number=2,
        title="שאלת המשך",
        questions=("מה הפרויקט המרכזי שלך?", "ובאיזה טכנולוגיות הוא בנוי?"),
        expected=(
            "בפנייה השנייה המילה \"הוא\" מפוענחת כ-UniRate מתוך התשובה הקודמת, "
            "והתשובה מפרטת את הטכנולוגיות שלו (Next.js, TypeScript, Prisma, PostgreSQL)."
        ),
    ),
    Scenario(
        number=3,
        title="פרט שאינו במקורות",
        questions=("מה הציון הממוצע שלך בתואר?",),
        expected="תשובה מאושרת שמציינת שאין במקורות מידע על ממוצע הציונים, בלי להמציא ציון.",
    ),
    Scenario(
        number=4,
        title="דחייה ושיפור",
        questions=("ספר לי על הניסיון התעסוקתי שלך",),
        expected=(
            "הטיוטה הראשונה (מוזרקת, עם עובדה מומצאת על Google) נדחית עם משוב שמצביע על הטענה המומצאת. "
            "היוצר מקבל את הטיוטה ואת המשוב, כותב גרסה מתוקנת בלי ההמצאה, והיא נבדקת שוב ומאושרת."
        ),
        injected_draft=INJECTED_FLAWED_DRAFT,
    ),
    Scenario(
        number=5,
        title="מיצוי הניסיונות (בדיקת זרימת בקרה, מעריך מדומה)",
        questions=("ספר לי על הניסיון שלך ב-QA",),
        expected=(
            "שלושה ניסיונות, כולם נדחים על ידי המעריך המדומה. עצירה אחרי הניסיון השלישי, "
            "הודעת סיום למשתמש, ואף טיוטה שנדחתה לא מוצגת כתשובה."
        ),
        fake_critic=True,
    ),
)
