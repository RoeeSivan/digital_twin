"""Look and feel of the Gradio chat: Hebrew UI texts, theme, CSS and a small JS hook.

Kept apart from app.py so the app file holds only the wiring. Colours match the
architecture diagram: blue = Actor, purple = Critic, green / amber / red = the three exits.
"""

from __future__ import annotations

import gradio as gr

TITLE = "התאום הדיגיטלי של רועי סיון"
DESCRIPTION = (
    "שאלו על הלימודים, הניסיון, הכישורים והפרויקטים של רועי. "
    "התשובות מבוססות רק על פרופיל ה-LinkedIn שלו ועל סיכום אישי שכתב. "
    "כל תשובה נבדקת על ידי מעריך לפני שהיא מוצגת, ותהליך הבדיקה מופיע ביומן שבצד."
)
EXAMPLES = [
    "איפה אתה לומד ומה הפרויקט המרכזי שלך?",
    "באיזה טכנולוגיות אתה עובד?",
    "ספר לי על הניסיון שלך ב-QA",
    "מה הציון הממוצע שלך בתואר?",
]

FONT = ["Heebo", "-apple-system", "BlinkMacSystemFont", "Segoe UI", "Arial", "sans-serif"]

THEME = gr.themes.Base(
    primary_hue=gr.themes.colors.blue,
    neutral_hue=gr.themes.colors.slate,
    radius_size=gr.themes.sizes.radius_md,
    font=FONT,
    font_mono=["Menlo", "SF Mono", "Consolas", "monospace"],
)

CSS = """
:root {
  --twin-actor: #1d4ed8;
  --twin-critic: #7e22ce;
  --twin-ok: #15803d;
  --twin-ok-bg: #e7f6ec;
  --twin-warn: #b45309;
  --twin-warn-bg: #fef3c7;
  --twin-err: #b91c1c;
  --twin-err-bg: #fee2e2;
  --twin-bg: #f4f6fa;
  --twin-surface: #ffffff;
  --twin-surface-2: #f1f5f9;
  --twin-border: #dbe1ea;
  --twin-text: #0f172a;
  --twin-muted: #5b6678;
}
/* Gradio adds .dark to <body> in dark mode. Only the neutral palette and tints change. */
body.dark {
  --twin-ok-bg: #12301d;
  --twin-warn-bg: #3a2a0c;
  --twin-err-bg: #3b1616;
  --twin-ok: #4ade80;
  --twin-warn: #fbbf24;
  --twin-err: #f87171;
  --twin-actor: #60a5fa;
  --twin-critic: #c084fc;
  --twin-bg: #0f1218;
  --twin-surface: #171b23;
  --twin-surface-2: #1f2530;
  --twin-border: #2c3442;
  --twin-text: #e8ecf2;
  --twin-muted: #98a2b3;
}

footer { display: none !important; }
html, body, gradio-app { background: var(--twin-bg) !important; }
.gradio-container {
  background: var(--twin-bg) !important;
  color: var(--twin-text) !important;
  max-width: 1320px !important;
  margin: 0 auto !important;
  padding: 24px 24px 32px !important;
}

/* ---------- Header ---------- */
.twin-header {
  direction: rtl;
  text-align: right;
  background: var(--twin-surface);
  border: 1px solid var(--twin-border);
  border-inline-start: 5px solid var(--twin-actor);
  border-radius: 12px;
  padding: 18px 22px;
}
.twin-header h1 { margin: 0 0 6px; font-size: 26px; font-weight: 700; color: var(--twin-text); letter-spacing: -0.01em; }
.twin-header p { margin: 0; font-size: 15px; line-height: 1.6; color: var(--twin-muted); max-width: 900px; }
.twin-facts { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }
.twin-fact {
  font-size: 12.5px; padding: 4px 10px; border-radius: 999px;
  background: var(--twin-surface-2); border: 1px solid var(--twin-border); color: var(--twin-text);
}
.twin-fact b { font-weight: 700; }
.twin-fact.actor b { color: var(--twin-actor); }
.twin-fact.critic b { color: var(--twin-critic); }

/* ---------- Layout: chat on the right (RTL), audit log on the left ---------- */
.twin-row { direction: rtl; gap: 18px !important; align-items: flex-start !important; }
.twin-row > * { direction: rtl; }

/* ---------- Chat ---------- */
.twin-chatbot {
  background: var(--twin-surface) !important;
  border: 1px solid var(--twin-border) !important;
  border-radius: 12px !important;
  box-shadow: none !important;
}
/* Gradio nests two .message elements: the outer one is the bubble, the inner one must stay plain. */
.twin-chatbot .message-row .flex-wrap > .message {
  border-radius: 14px !important;
  padding: 10px 16px !important;
  box-shadow: none !important;
  font-size: 15px !important;
  line-height: 1.65 !important;
}
.twin-chatbot .message-row .message .message,
.twin-chatbot .message-row .message .md {
  background: transparent !important;
  border: 0 !important;
  padding: 0 !important;
  box-shadow: none !important;
  font-size: inherit !important;
  line-height: inherit !important;
}
.twin-chatbot .message-row.user-row .flex-wrap > .message {
  background: #1d4ed8 !important;
  border: 1px solid #1d4ed8 !important;
}
.twin-chatbot .message-row.user-row .message * { color: #ffffff !important; }
.twin-chatbot .message-row.bot-row .flex-wrap > .message {
  background: var(--twin-surface-2) !important;
  border: 1px solid var(--twin-border) !important;
}
.twin-chatbot .message-row.bot-row .message * { color: var(--twin-text) !important; }
.twin-chatbot .message-row p { margin: 0 0 8px !important; }
.twin-chatbot .message-row p:last-child { margin-bottom: 0 !important; }
.twin-chatbot .examples { direction: rtl; }
.twin-chatbot button.example {
  direction: rtl; font-size: 14px !important;
  background: var(--twin-surface-2) !important;
  border: 1px solid var(--twin-border) !important;
  color: var(--twin-text) !important;
  border-radius: 10px !important;
}
.twin-chatbot button.example:hover { border-color: var(--twin-actor) !important; color: var(--twin-actor) !important; }
.twin-chat textarea {
  font-size: 15px !important;
  background: var(--twin-surface) !important;
  color: var(--twin-text) !important;
}
/* Keep the chosen test mode visible after a message is sent (Gradio drops the fill while the form is busy). */
.twin-chat input[type="radio"]:checked {
  background-color: var(--twin-actor) !important;
  border-color: var(--twin-actor) !important;
}
.twin-chat label.selected { border-color: var(--twin-actor) !important; }
.twin-chat .gr-accordion { direction: rtl; border: 1px solid var(--twin-border) !important; background: var(--twin-surface) !important; }

/* ---------- Audit log panel ---------- */
.twin-audit-title {
  direction: rtl; font-size: 16px; font-weight: 700; color: var(--twin-text);
  margin: 0 0 2px; padding: 0 2px;
}
.twin-audit-title small { display: block; font-size: 12.5px; font-weight: 400; color: var(--twin-muted); margin-top: 2px; }
.audit { direction: rtl; text-align: right; color: var(--twin-text); font-size: 14px; line-height: 1.6; }
.audit-empty {
  background: var(--twin-surface); border: 1px dashed var(--twin-border); border-radius: 12px;
  padding: 22px; color: var(--twin-muted);
}
.audit-head { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 10px; }
.chip {
  display: inline-block; font-size: 12px; font-weight: 600; padding: 3px 10px; border-radius: 999px;
  border: 1px solid var(--twin-border); background: var(--twin-surface-2); color: var(--twin-text);
  white-space: nowrap;
}
.chip-approved, .chip-status-approved { background: var(--twin-ok-bg); color: var(--twin-ok); border-color: var(--twin-ok); }
.chip-rejected, .chip-status-exhausted { background: var(--twin-warn-bg); color: var(--twin-warn); border-color: var(--twin-warn); }
.chip-error, .chip-status-error { background: var(--twin-err-bg); color: var(--twin-err); border-color: var(--twin-err); }
.chip-test { background: transparent; color: var(--twin-critic); border-color: var(--twin-critic); border-style: dashed; }
.audit-question, .attempt, .audit-shown {
  background: var(--twin-surface); border: 1px solid var(--twin-border); border-radius: 10px;
  padding: 10px 14px; margin-bottom: 10px;
}
.attempt { border-inline-start: 4px solid var(--twin-border); }
.attempt-approved { border-inline-start-color: var(--twin-ok); }
.attempt-rejected { border-inline-start-color: var(--twin-warn); }
.attempt-error { border-inline-start-color: var(--twin-err); }
.attempt-head { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; margin-bottom: 4px; }
.attempt-num { font-weight: 700; font-size: 14.5px; margin-inline-end: 4px; }
.field-label {
  display: block; font-size: 11.5px; font-weight: 700; color: var(--twin-muted);
  margin: 8px 0 2px; letter-spacing: 0.02em;
}
.audit-question .field-label { margin-top: 0; }
.draft { white-space: normal; }
.feedback {
  direction: ltr; text-align: left; font-size: 13px; line-height: 1.55;
  background: var(--twin-surface-2); border-radius: 8px; padding: 8px 10px; color: var(--twin-text);
}
.audit-shown { font-size: 13px; color: var(--twin-muted); background: transparent; border-style: dashed; }

@media (max-width: 900px) {
  .gradio-container { padding: 14px !important; }
  .twin-header h1 { font-size: 21px; }
}
"""

# Runs once when the page loads: Hebrew page direction for screen readers, and focus on the message box.
JS = """
() => {
  document.documentElement.lang = 'he';
  document.title = 'התאום הדיגיטלי של רועי סיון';
  setTimeout(() => {
    const box = document.querySelector('.twin-chat textarea');
    if (box) box.focus();
  }, 300);
}
"""


def header_html(actor_model: str, actor_effort: str, critic_model: str, critic_effort: str, max_attempts: int) -> str:
    """Page header: title, description and the settings used for this run."""
    return (
        '<div class="twin-header">'
        f"<h1>{TITLE}</h1><p>{DESCRIPTION}</p>"
        '<div class="twin-facts">'
        f'<span class="twin-fact actor"><b>היוצר (Actor)</b> · <span dir="ltr">{actor_model} · effort {actor_effort}</span></span>'
        f'<span class="twin-fact critic"><b>המעריך (Critic)</b> · <span dir="ltr">{critic_model} · effort {critic_effort}</span></span>'
        f'<span class="twin-fact"><b>עד {max_attempts} ניסיונות</b> לכל שאלה</span>'
        "</div></div>"
    )
