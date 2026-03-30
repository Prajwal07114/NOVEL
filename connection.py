# app/database/connection.py
# ──────────────────────────────────────────────────────────────
# Async MongoDB connection using Motor.
# The client is stored as a module-level singleton so it can be
# reused across the entire application lifetime.
# ──────────────────────────────────────────────────────────────

import logging
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.utils.config import settings

logger = logging.getLogger(__name__)

# Module-level singleton references
_client: Optional[AsyncIOMotorClient] = None
_db:     Optional[AsyncIOMotorDatabase] = None


async def connect_db() -> None:
    """Open the MongoDB connection pool (called at app startup)."""
    global _client, _db

    logger.info("Connecting to MongoDB…")
    _client = AsyncIOMotorClient(settings.MONGODB_URI)
    _db     = _client[settings.MONGODB_DB_NAME]

    # Lightweight ping to verify connectivity
    await _client.admin.command("ping")
    logger.info("MongoDB connected — database: %s", settings.MONGODB_DB_NAME)


async def close_db() -> None:
    """Close the MongoDB connection pool (called at app shutdown)."""
    global _client
    if _client:
        _client.close()
        logger.info("MongoDB connection closed.")


def get_db() -> AsyncIOMotorDatabase:
    """
    Return the active database handle.
    Raises RuntimeError if connect_db() was never called.
    """
    if _db is None:
        raise RuntimeError("Database not initialised. Call connect_db() first.")
    return _db
