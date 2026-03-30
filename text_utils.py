# app/utils/text_utils.py
# ──────────────────────────────────────────────────────────────
# Text processing helpers used by the story service.
# Keeps parsing logic isolated and testable.
# ──────────────────────────────────────────────────────────────

from __future__ import annotations

import re
from typing import Tuple


def parse_chapter_output(raw_text: str) -> Tuple[str, str]:
    """
    Parse the raw LLM output into (chapter_title, chapter_body).

    Expected format produced by the prompt builder:
        CHAPTER N: Some Compelling Title

        ... body text ...

        ---END CHAPTER---

    Falls back gracefully if the model deviates slightly.

    Returns
    -------
    (title, body)  — both are stripped strings
    """

    # ── 1. Strip the sentinel marker ──────────────────────────
    body = raw_text.replace("---END CHAPTER---", "").strip()

    # ── 2. Extract the chapter title line ─────────────────────
    # Matches: "CHAPTER 3: The Reckoning" or "Chapter 3 — The Reckoning"
    title_pattern = re.compile(
        r"^CHAPTER\s+\d+\s*[:\-–—]\s*(.+)$",
        re.IGNORECASE | re.MULTILINE,
    )
    match = title_pattern.search(body)

    if match:
        chapter_title = match.group(1).strip()
        # Remove the title line from the body
        body = body[match.end():].strip()
    else:
        # Fallback: use first non-empty line as title
        lines = [ln.strip() for ln in body.splitlines() if ln.strip()]
        chapter_title = lines[0] if lines else "Untitled Chapter"
        body = "\n".join(lines[1:]).strip() if len(lines) > 1 else body

    return chapter_title, body


def word_count(text: str) -> int:
    """Return the number of words in a string."""
    return len(text.split())


def extract_chapter_number_from_prompt(raw_text: str) -> int:
    """
    Attempt to extract a chapter number from 'CHAPTER N:' in raw text.
    Returns 1 as a safe default.
    """
    match = re.search(r"CHAPTER\s+(\d+)", raw_text, re.IGNORECASE)
    return int(match.group(1)) if match else 1
