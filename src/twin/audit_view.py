"""Renders one QuestionRecord as HTML for the audit side panel of the chat.

The panel shows what the chat hides: every draft, the Critic's verdict and feedback,
and why the question ended. All model text is HTML-escaped before it is inserted.
"""

from __future__ import annotations

import html
import re

from twin.config import MAX_ATTEMPTS
from twin.schemas import AttemptRecord, QuestionRecord

STATUS_LABELS = {
    "approved": "הסתיים באישור",
    "exhausted": "מיצוי ניסיונות",
    "error": "שגיאה טכנית",
}
SHOWN_TO_USER = {
    "approved": "הוצגה בצ'אט התשובה שאושרה (ניסיון {n}).",
    "exhausted": "הוצגה הודעת עצירה. אף אחת מהטיוטות שנדחו לא הוצגה.",
    "error": "הוצגה הודעת שגיאה. הטיפול בשאלה הופסק.",
}
EMPTY_PANEL = '<div class="audit audit-empty">היומן יתמלא אחרי השאלה הראשונה: כל טיוטה, החלטת המעריך והמשוב.</div>'


def _text(value: str) -> str:
    """Escape model text; keep line breaks and **bold**."""
    escaped = html.escape(value)
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
    return escaped.replace("\n", "<br>")


def _attempt_html(attempt: AttemptRecord) -> str:
    if not attempt.evaluation_completed or attempt.evaluation is None:
        kind, verdict = "error", "ההערכה לא הושלמה"
    elif attempt.evaluation.is_acceptable:
        kind, verdict = "approved", "אושר · is_acceptable = true"
    else:
        kind, verdict = "rejected", "נדחה · is_acceptable = false"

    chips = f'<span class="chip chip-{kind}">{verdict}</span>'
    if attempt.source == "injected":
        chips += '<span class="chip chip-test">טיוטת מבחן מוזרקת</span>'

    parts = [f'<div class="attempt-head"><span class="attempt-num">ניסיון {attempt.attempt}</span>{chips}</div>']
    if attempt.candidate is not None:
        parts.append(f'<div class="field-label">טיוטת היוצר</div><div class="draft">{_text(attempt.candidate)}</div>')
    if attempt.evaluation is not None:
        parts.append(
            '<div class="field-label">משוב המעריך</div>'
            f'<div class="feedback" dir="ltr">{_text(attempt.evaluation.feedback)}</div>'
        )
    if attempt.error:
        parts.append(f'<div class="field-label">שגיאה</div><div class="feedback" dir="ltr">{_text(attempt.error)}</div>')
    return f'<div class="attempt attempt-{kind}">{"".join(parts)}</div>'


def render_record_html(record: QuestionRecord) -> str:
    chips = f'<span class="chip chip-status-{record.status}">{STATUS_LABELS[record.status]}</span>'
    chips += f'<span class="chip chip-plain">{len(record.attempts)} מתוך {MAX_ATTEMPTS} ניסיונות</span>'
    if record.critic_kind == "fake_reject":
        chips += '<span class="chip chip-test">מעריך מדומה · בדיקת זרימת בקרה</span>'
    shown = SHOWN_TO_USER[record.status].format(n=len(record.attempts))
    return (
        '<div class="audit">'
        f'<div class="audit-head">{chips}</div>'
        f'<div class="audit-question"><span class="field-label">השאלה</span>{_text(record.question)}</div>'
        f'{"".join(_attempt_html(a) for a in record.attempts)}'
        f'<div class="audit-shown">{shown}</div>'
        "</div>"
    )
