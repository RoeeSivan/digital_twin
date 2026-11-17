# HW1 - Digital-twin chat with an Actor-Critic loop

Agentic AI Systems, Reichman University. Assignment 1.
Student: Roee Sivan

A Hebrew Gradio chat that answers questions about Roee from two background sources
(LinkedIn export + personal summary). Every answer is drafted by an **Actor** and checked by a
**Critic** that returns a validated Pydantic `Evaluation`. Rejected drafts are revised with the
feedback, at most three attempts per question.

## Requirements

- Python 3.12 (pinned in `.python-version`)
- [uv](https://docs.astral.sh/uv/)
- An Anthropic API key

## Install

```bash
uv sync
cp .env.example .env   # then put your key in ANTHROPIC_API_KEY
```

## Environment variables

| Name | Meaning | Default |
|---|---|---|
| `ANTHROPIC_API_KEY` | Anthropic API key (never committed) | - |
| `ACTOR_MODEL` | model used by the Actor | `claude-opus-5-5` |
| `CRITIC_MODEL` | model used by the Critic | `claude-opus-5-5` |

## Run

```bash
uv run scripts/smoke_test.py      # key + models reachable
uv run app.py                     # Gradio chat on http://127.0.0.1:7860
uv run pytest -q                  # tests
uv run scripts/run_scenarios.py   # the five scenarios -> logs/scenario_N.json + results/scenarios.md
uv run scripts/run_scenarios.py --report   # rebuild results/scenarios.md from the saved logs (no API calls)
```

## Models and settings

| Setting | Actor | Critic |
|---|---|---|
| Model | `claude-opus-5-5` (`ACTOR_MODEL`) | `claude-opus-5-5` (`CRITIC_MODEL`) |
| Effort | `low` (`ACTOR_EFFORT`) | `medium` (`CRITIC_EFFORT`) |
| Output | plain text | JSON validated into the Pydantic `Evaluation` |

`MAX_ATTEMPTS = 3` generations per question (the first draft included) and `max_tokens = 16000` per call.
All of these are set in [`src/twin/config.py`](src/twin/config.py).

## Project layout

```
data/        background sources (linkedin.txt, summary.txt, raw/ PDF export)
prompts/     actor_system.md, critic_system.md
src/twin/    application code
app.py       Gradio entry point
styles.py    UI texts, theme, CSS and JS of the chat
scripts/     smoke_test.py, run_scenarios.py
tests/       pytest
logs/        audit logs (JSON); the chat's own per-run session_<timestamp>.json files are git-ignored
results/     scenarios.md, screenshots/
report/      REPORT.md/.docx/.pdf (short report + results), architecture diagram
```

## Results

- [`results/scenarios.md`](results/scenarios.md): the five scenarios, with input, attempts, displayed output and
  expected vs actual. LLM-critic results (1-4) and the mock-critic control-flow test (5) are in separate sections.
- [`results/manual_check.md`](results/manual_check.md): manual claim-by-claim check of approved answers against the sources.
- `logs/scenario_1.json` ... `logs/scenario_5.json`: the audit log of each scenario.
- `results/screenshots/`: the chat and the audit panel for each scenario. They come from a separate run of the same
  inputs through the UI; that run's log is `logs/session_screenshots.json`.
- [`report/architecture.svg`](report/architecture.svg) (+ `.png`): architecture diagram.

To reproduce scenarios 4 and 5 in the UI, open "מצבי בדיקה" under the message box and pick the mode:
scenario 4 injects a flawed first draft, scenario 5 swaps the Critic for a mock that always rejects.
