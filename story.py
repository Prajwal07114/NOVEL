# app/routes/story.py
# ──────────────────────────────────────────────────────────────
# FastAPI router for all story-related endpoints.
#
# Endpoints:
#   POST /generate-story   — start a new story (Chapter 1)
#   POST /next-chapter     — generate the next chapter
#   GET  /story/{story_id} — retrieve a full story by id
#
# Route handlers are intentionally thin — they validate input,
# call the service layer, and return the response.
# ──────────────────────────────────────────────────────────────

import logging

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse

import anthropic

from app.database.connection import get_db
from app.models.story_models import (
    GenerateStoryRequest,
    NextChapterRequest,
    StoryOut,
)
from app.services import story_service

logger = logging.getLogger(__name__)

router = APIRouter()


# ── POST /generate-story ──────────────────────────────────────

@router.post(
    "/generate-story",
    response_model=StoryOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new story and generate Chapter 1",
    description=(
        "Provide characters, genre, style, and plot. "
        "Chapter 1 is generated immediately and stored in MongoDB."
    ),
)
async def generate_story_endpoint(request: GenerateStoryRequest):
    """
    Kick off a brand-new novel.

    - Validates the request via Pydantic
    - Builds a style-aware prompt (Shakespearean, noir, etc.)
    - Calls Claude to generate Chapter 1
    - Persists and returns the full story object
    """
    db = get_db()
    try:
        story = await story_service.create_new_story(db, request)
        return story
    except anthropic.AuthenticationError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Anthropic API key. Check ANTHROPIC_API_KEY in .env",
        )
    except anthropic.RateLimitError:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Claude API rate limit reached. Please retry shortly.",
        )
    except anthropic.APIError as exc:
        logger.error("Anthropic API error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI generation failed: {str(exc)}",
        )
    except Exception as exc:
        logger.exception("Unexpected error in /generate-story")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


# ── POST /next-chapter ────────────────────────────────────────

@router.post(
    "/next-chapter",
    response_model=StoryOut,
    status_code=status.HTTP_200_OK,
    summary="Generate the next chapter of an existing story",
    description=(
        "Pass the story_id returned from /generate-story. "
        "An optional plot_hint can guide the direction of the chapter."
    ),
)
async def next_chapter_endpoint(request: NextChapterRequest):
    """
    Continue an existing novel.

    - Fetches the story from MongoDB (404 if not found)
    - Injects full story context into the continuation prompt
    - Maintains character consistency and style across chapters
    - Appends the new chapter and returns the updated story
    """
    db = get_db()
    try:
        story = await story_service.generate_next_chapter(db, request)
        return story
    except HTTPException:
        raise  # Re-raise 404 / 500 from service layer as-is
    except anthropic.AuthenticationError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Anthropic API key. Check ANTHROPIC_API_KEY in .env",
        )
    except anthropic.RateLimitError:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Claude API rate limit reached. Please retry shortly.",
        )
    except anthropic.APIError as exc:
        logger.error("Anthropic API error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI generation failed: {str(exc)}",
        )
    except Exception as exc:
        logger.exception("Unexpected error in /next-chapter")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


# ── GET /story/{story_id} ─────────────────────────────────────

@router.get(
    "/story/{story_id}",
    response_model=StoryOut,
    status_code=status.HTTP_200_OK,
    summary="Retrieve a full story by ID",
    description="Returns all chapters, characters, and metadata for a story.",
)
async def get_story_endpoint(story_id: str):
    """
    Fetch a stored story by its MongoDB ObjectId.

    Returns 404 if the id is invalid or the story doesn't exist.
    """
    db = get_db()
    try:
        story = await story_service.fetch_story(db, story_id)
        return story
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Unexpected error in GET /story/%s", story_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )
