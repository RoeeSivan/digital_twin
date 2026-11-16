"""Gradio entry point. Run with: uv run app.py

Hebrew RTL chat. The chat shows user messages and final answers only;
drafts and feedback go to the audit log (logs/session_<ts>.json) and the side panel.
"""

from __future__ import annotations

from typing import Any

import gradio as gr

from styles import CSS, EXAMPLES, JS, THEME, header_html
from twin.actor import Actor
from twin.audit_log import append_record, session_log_path
from twin.audit_view import EMPTY_PANEL, render_record_html
from twin.config import MAX_ATTEMPTS
from twin.critic import Critic, FakeRejectCritic
from twin.loop import answer_question
from twin.scenarios import INJECTED_FLAWED_DRAFT

# Test modes, for reproducing scenarios 4 and 5 in the UI. The default is the normal chat.
MODE_NORMAL = "רגיל"
MODE_INJECTED = "תרחיש 4: טיוטה ראשונה פגומה (מוזרקת)"
MODE_FAKE_CRITIC = "תרחיש 5: מעריך מדומה שדוחה תמיד (בדיקת זרימת בקרה)"
MODES = [MODE_NORMAL, MODE_INJECTED, MODE_FAKE_CRITIC]

actor = Actor()
critic = Critic()
SESSION_LOG = session_log_path()  # one log file per app run, created on the first question


def respond(message: str, history: list[dict[str, Any]], mode: str = MODE_NORMAL) -> tuple[str, str, dict[str, Any]]:
    """Return (text shown in the chat, audit panel HTML, raw audit record).

    The chat gets only `final_text`: the approved answer, the stop message or the error
    message. Rejected drafts and feedback go to the side panel and the session log.
    Gradio appends the question and `final_text` to the displayed history itself.
    """
    if mode == MODE_INJECTED:
        record = answer_question(
            message, history, actor=actor, critic=critic,
            scenario_id="chat-injected-draft", first_draft_override=INJECTED_FLAWED_DRAFT,
        )
    elif mode == MODE_FAKE_CRITIC:
        record = answer_question(message, history, actor=actor, critic=FakeRejectCritic(), scenario_id="chat-fake-critic")
    else:
        record = answer_question(message, history, actor=actor, critic=critic, scenario_id="chat")
    append_record(SESSION_LOG, record)
    return record.final_text, render_record_html(record), record.model_dump(mode="json")


def build_app() -> gr.Blocks:
    audit_panel = gr.HTML(EMPTY_PANEL, render=False)
    audit_json = gr.JSON(label="JSON", open=False, render=False)
    with gr.Blocks(title="Roee Sivan - digital twin") as demo:
        gr.HTML(header_html(actor.model, actor.effort, critic.model, critic.effort, MAX_ATTEMPTS))
        with gr.Row(elem_classes="twin-row"):
            with gr.Column(scale=3, elem_classes="twin-chat"):
                gr.ChatInterface(
                    fn=respond,
                    chatbot=gr.Chatbot(label="שיחה", rtl=True, height=540, show_label=False, elem_classes="twin-chatbot"),
                    textbox=gr.Textbox(placeholder="כתבו שאלה...", rtl=True, submit_btn=True),
                    additional_inputs=[gr.Radio(MODES, value=MODE_NORMAL, label="מצב הרצה", rtl=True, render=False)],
                    additional_inputs_accordion=gr.Accordion("מצבי בדיקה (לתרחישים 4 ו-5)", open=False, render=False),
                    additional_outputs=[audit_panel, audit_json],
                    examples=[[question] for question in EXAMPLES],
                    examples_label="שאלות לדוגמה",
                )
            with gr.Column(scale=2):
                gr.HTML(
                    '<div class="twin-audit-title">יומן בדיקה: השאלה האחרונה'
                    "<small>מה שהצ'אט לא מציג: כל טיוטה, החלטת המעריך והמשוב</small></div>"
                )
                audit_panel.render()
                with gr.Accordion("הרשומה המלאה (JSON), כפי שנשמרת ביומן", open=False):
                    audit_json.render()
    return demo


def main() -> None:
    build_app().launch(inbrowser=True, css=CSS, js=JS, theme=THEME)


if __name__ == "__main__":
    main()
