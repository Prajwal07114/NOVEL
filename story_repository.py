# app/database/story_repository.py
# ──────────────────────────────────────────────────────────────
# All MongoDB read/write operations for the "stories" collection.
# Keeps database logic completely separate from business logic.
# ──────────────────────────────────────────────────────────────

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

COLLECTION = "stories"


def _utcnow() -> str:
    """Return current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


def _serialize(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Convert MongoDB ObjectId → plain string so FastAPI can JSON-encode it."""
    doc["id"] = str(doc.pop("_id"))
    return doc


# ── Create ────────────────────────────────────────────────────

async def create_story(db: AsyncIOMotorDatabase, story_doc: Dict[str, Any]) -> str:
    """
    Insert a new story document.

    Parameters
    ----------
    db        : active Motor database handle
    story_doc : dict containing characters, config, and the first chapter

    Returns
    -------
    str  — the newly created document's ObjectId as a string
    """
    story_doc["created_at"] = _utcnow()
    story_doc["updated_at"] = _utcnow()

    result = await db[COLLECTION].insert_one(story_doc)
    logger.info("Created story _id=%s", result.inserted_id)
    return str(result.inserted_id)


# ── Read ──────────────────────────────────────────────────────

async def get_story_by_id(
    db: AsyncIOMotorDatabase, story_id: str
) -> Optional[Dict[str, Any]]:
    """
    Fetch a story by its MongoDB ObjectId string.

    Returns None if the id is invalid or the document doesn't exist.
    """
    try:
        oid = ObjectId(story_id)
    except InvalidId:
        logger.warning("Invalid ObjectId: %s", story_id)
        return None

    doc = await db[COLLECTION].find_one({"_id": oid})
    if doc:
        return _serialize(doc)
    return None


# ── Update ────────────────────────────────────────────────────

async def append_chapter(
    db: AsyncIOMotorDatabase,
    story_id: str,
    chapter: Dict[str, Any],
) -> bool:
    """
    Push a new chapter dict into the story's `chapters` array
    and refresh the `updated_at` timestamp.

    Returns True on success, False if the document was not found.
    """
    try:
        oid = ObjectId(story_id)
    except InvalidId:
        return False

    result = await db[COLLECTION].update_one(
        {"_id": oid},
        {
            "$push": {"chapters": chapter},
            "$set":  {"updated_at": _utcnow()},
        },
    )
    return result.modified_count == 1
