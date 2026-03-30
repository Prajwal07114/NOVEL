# app/services/ai_service.py
# ──────────────────────────────────────────────────────────────
# Anthropic Claude API integration.
#
# Single responsibility: take a prompt string → return the
# model's text response.  All prompt construction happens in
# prompt_builder.py; all database ops happen in story_service.py.
# ──────────────────────────────────────────────────────────────

import logging

import anthropic

from app.utils.config import settings

logger = logging.getLogger(__name__)

# ── Lazy singleton client ─────────────────────────────────────
# Instantiated once on first call to avoid unnecessary overhead
# at import time and to respect env-var loading order.
_client: anthropic.AsyncAnthropic | None = None


def _get_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _client


# ── System prompt ─────────────────────────────────────────────
# Establishes the model's persona for every generation request.
SYSTEM_PROMPT = (
    "You are a celebrated novelist with mastery over many genres and literary styles. "
    "You write stories that are emotionally resonant, narratively gripping, and stylistically precise. "
    "You follow formatting instructions exactly and never break character. "
    "You produce only the requested creative content — no meta-commentary, no apologies, no preamble."
)


# ── Core generation function ──────────────────────────────────

async def generate_story(prompt: str) -> str:
    """
    Send a prompt to Claude and return the generated text.

    Parameters
    ----------
    prompt : str
        Fully constructed user-turn prompt from prompt_builder.py

    Returns
    -------
    str
        The model's raw text response (chapter content)

    Raises
    ------
    anthropic.APIError subclasses on network / auth / rate-limit failures
    """
    client = _get_client()

    logger.info(
        "Calling Claude model=%s max_tokens=%d",
        settings.CLAUDE_MODEL,
        settings.CLAUDE_MAX_TOKENS,
    )

    message = await client.messages.create(
        model=settings.CLAUDE_MODEL,
        max_tokens=settings.CLAUDE_MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": prompt}
        ],
    )

    # Extract text from the first content block
    response_text = message.content[0].text

    logger.info(
        "Generation complete — stop_reason=%s input_tokens=%d output_tokens=%d",
        message.stop_reason,
        message.usage.input_tokens,
        message.usage.output_tokens,
    )

    return response_text
