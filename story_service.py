# app/services/story_service.py
# ──────────────────────────────────────────────────────────────
# Business-logic layer for story management.
#
# Responsibilities:
#   • Orchestrate prompt building → AI generation → DB writes
#   • Build the canonical story document structure
#   • Translate raw DB dicts into API response shapes
# ──────────────────────────────────────────────────────────────

from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import story_repository as repo
from app.models.story_models import (
    ChapterOut,
    GenerateStoryRequest,
    NextChapterRequest,
    StoryOut,
)
from app.services.ai_service import generate_story
from app.utils.prompt_builder import build_chapter_one_prompt, build_next_chapter_prompt
from app.utils.text_utils import parse_chapter_output, word_count

logger = logging.getLogger(__name__)


# ── Internal helpers ──────────────────────────────────────────

def _build_chapter_doc(
    chapter_number: int, title: str, content: str
) -> Dict[str, Any]:
    """Create the dict that gets stored in MongoDB chapters array."""
    return {
        "chapter_number": chapter_number,
        "title":          title,
        "content":        content,
        "word_count":     word_count(content),
    }


def _story_doc_to_out(doc: Dict[str, Any]) -> StoryOut:
    """
    Convert a raw MongoDB document (already serialised — _id → id)
    into a StoryOut Pydantic model.
    """
    chapters_out = [
        ChapterOut(
            chapter_number=ch["chapter_number"],
            title=ch["title"],
            content=ch["content"],
            word_count=ch["word_count"],
        )
        for ch in doc.get("chapters", [])
    ]

    total_words = sum(ch.word_count for ch in chapters_out)

    return StoryOut(
        id=doc["id"],
        title=doc["title"],
        characters=doc["characters"],
        config=doc["config"],
        chapters=chapters_out,
        total_words=total_words,
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


# ── Public service functions ──────────────────────────────────

async def create_new_story(
    db: AsyncIOMotorDatabase, request: GenerateStoryRequest
) -> StoryOut:
    """
    Full pipeline for POST /generate-story:
      1. Build a Chapter 1 prompt
      2. Call Claude to generate the text
      3. Parse the response into (title, body)
      4. Persist the story document to MongoDB
      5. Return the serialised StoryOut
    """

    # ── Step 1: Build prompt ───────────────────────────────────
    prompt = build_chapter_one_prompt(
        title=request.title,
        characters=request.characters,
        config=request.config,
        additional_instructions=request.additional_instructions,
    )

    # ── Step 2: Generate with Claude ──────────────────────────
    logger.info("Generating Chapter 1 for '%s'", request.title)
    raw_output = await generate_story(prompt)

    # ── Step 3: Parse response ─────────────────────────────────
    chapter_title, chapter_body = parse_chapter_output(raw_output)

    chapter_doc = _build_chapter_doc(
        chapter_number=1,
        title=chapter_title,
        content=chapter_body,
    )

    # ── Step 4: Build & persist MongoDB document ───────────────
    story_doc: Dict[str, Any] = {
        "title":      request.title,
        "characters": [c.model_dump() for c in request.characters],
        "config":     request.config.model_dump(),
        "chapters":   [chapter_doc],
    }

    story_id = await repo.create_story(db, story_doc)
    logger.info("Story saved — id=%s", story_id)

    # ── Step 5: Fetch back & return ────────────────────────────
    saved_doc = await repo.get_story_by_id(db, story_id)
    return _story_doc_to_out(saved_doc)


async def generate_next_chapter(
    db: AsyncIOMotorDatabase, request: NextChapterRequest
) -> StoryOut:
    """
    Full pipeline for POST /next-chapter:
      1. Fetch existing story (validates existence)
      2. Determine next chapter number
      3. Build continuation prompt with full story context
      4. Call Claude
      5. Parse → append chapter to MongoDB
      6. Return updated StoryOut
    """

    # ── Step 1: Fetch story ────────────────────────────────────
    story_doc = await repo.get_story_by_id(db, request.story_id)
    if not story_doc:
        raise HTTPException(
            status_code=404,
            detail=f"Story with id '{request.story_id}' not found.",
        )

    # ── Step 2: Chapter number ─────────────────────────────────
    existing_chapters: list = story_doc.get("chapters", [])
    next_chapter_num = len(existing_chapters) + 1

    # ── Step 3: Build continuation prompt ─────────────────────
    prompt = build_next_chapter_prompt(
        story=story_doc,
        chapter_number=next_chapter_num,
        plot_hint=request.plot_hint,
    )

    # ── Step 4: Generate with Claude ──────────────────────────
    logger.info(
        "Generating Chapter %d for story id=%s",
        next_chapter_num,
        request.story_id,
    )
    raw_output = await generate_story(prompt)

    # ── Step 5: Parse & persist ────────────────────────────────
    chapter_title, chapter_body = parse_chapter_output(raw_output)
    chapter_doc = _build_chapter_doc(
        chapter_number=next_chapter_num,
        title=chapter_title,
        content=chapter_body,
    )

    success = await repo.append_chapter(db, request.story_id, chapter_doc)
    if not success:
        raise HTTPException(
            status_code=500,
            detail="Failed to append chapter to the database.",
        )

    # ── Step 6: Return refreshed story ────────────────────────
    updated_doc = await repo.get_story_by_id(db, request.story_id)
    return _story_doc_to_out(updated_doc)


async def fetch_story(
    db: AsyncIOMotorDatabase, story_id: str
) -> StoryOut:
    """
    Pipeline for GET /story/{id}:
      Fetch and return a story by its MongoDB ObjectId string.
    """
    story_doc = await repo.get_story_by_id(db, story_id)
    if not story_doc:
        raise HTTPException(
            status_code=404,
            detail=f"Story with id '{story_id}' not found.",
        )
    return _story_doc_to_out(story_doc)
