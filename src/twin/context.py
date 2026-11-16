"""Background sources for the digital twin.

Loads `data/linkedin.txt` and `data/summary.txt` and renders them as one block in which
each source is wrapped in its own tag. The block is appended to the Actor's system
prompt and passed to the Critic, so both see exactly the same sources.
"""

from __future__ import annotations

from functools import cache
from pathlib import Path

from twin.config import DATA_DIR

# (file name, tag id, human-readable label)
SOURCES: tuple[tuple[str, str, str], ...] = (
    ("linkedin.txt", "linkedin", "LinkedIn profile"),
    ("summary.txt", "summary", "Personal summary"),
)


def render_background(data_dir: Path = DATA_DIR) -> str:
    """Read the source files and return them as one tagged text block."""
    parts = []
    for file_name, source_id, label in SOURCES:
        text = (data_dir / file_name).read_text(encoding="utf-8").strip()
        parts.append(f'<source id="{source_id}" label="{label}">\n{text}\n</source>')
    return "\n\n".join(parts)


@cache
def load_background() -> str:
    """The background block for the default data folder, read once per process."""
    return render_background()
