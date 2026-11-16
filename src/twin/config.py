"""Configuration: environment variables, model names, paths and loop limits.

Secrets live in `.env` (see `.env.example`); nothing here prints the API key.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
PROMPTS_DIR = PROJECT_ROOT / "prompts"
LOGS_DIR = PROJECT_ROOT / "logs"
RESULTS_DIR = PROJECT_ROOT / "results"

load_dotenv(PROJECT_ROOT / ".env", override=True)

ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
ACTOR_MODEL: str = os.getenv("ACTOR_MODEL", "claude-opus-5-5")
CRITIC_MODEL: str = os.getenv("CRITIC_MODEL", "claude-opus-5-5")

# The brief allows at most three generation attempts per question, including the first.
MAX_ATTEMPTS = 3

# Opus 5.5 always thinks; effort is the only depth control (its default is "medium").
# The Actor writes short chat answers, so "low" is enough. The Critic setting is used in Part B.
ACTOR_EFFORT: str = os.getenv("ACTOR_EFFORT", "low")
CRITIC_EFFORT: str = os.getenv("CRITIC_EFFORT", "medium")

# Generous ceiling so thinking + answer never get cut off; the prompt keeps answers short.
MAX_TOKENS = 16000

# The Critic sees the last N history messages (user + assistant), enough to judge follow-up questions.
CRITIC_HISTORY_MESSAGES = 6
