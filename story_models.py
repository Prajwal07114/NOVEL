# app/models/story_models.py
# ──────────────────────────────────────────────────────────────
# Pydantic models for request validation and response shaping.
# These act as the contract between the client and the API.
# ──────────────────────────────────────────────────────────────

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


# ── Enumerations ──────────────────────────────────────────────

class Genre(str, Enum):
    fantasy     = "fantasy"
    romance     = "romance"
    thriller    = "thriller"
    mystery     = "mystery"
    sci_fi      = "sci-fi"
    horror      = "horror"
    historical  = "historical fiction"
    adventure   = "adventure"
    literary    = "literary fiction"


class WritingStyle(str, Enum):
    shakespearean   = "Shakespearean"
    modern          = "modern"
    minimalist      = "minimalist"
    gothic          = "gothic"
    lyrical         = "lyrical"
    noir            = "noir"
    epistolary      = "epistolary"
    stream_of_consciousness = "stream of consciousness"


# ── Sub-models ────────────────────────────────────────────────

class Character(BaseModel):
    """Represents a single story character."""
    name:        str = Field(..., min_length=1, max_length=100, description="Character's full name")
    role:        str = Field(..., description="e.g. 'protagonist' or 'antagonist'")
    background:  str = Field(..., description="Brief backstory and personality traits")
    motivation:  str = Field(..., description="What drives this character?")
    appearance:  Optional[str] = Field(None, description="Physical description")


class StoryConfig(BaseModel):
    """Top-level story settings shared across all chapters."""
    genre:       Genre       = Field(..., description="Story genre")
    style:       WritingStyle = Field(..., description="Writing / narration style")
    setting:     str         = Field(..., description="World or location the story takes place in")
    plot_summary: str        = Field(..., description="High-level plot outline (2-5 sentences)")
    tone:        Optional[str] = Field("dramatic", description="Emotional tone: e.g. dark, hopeful, comedic")
    pov:         Optional[str] = Field("third-person limited", description="Point of view")


# ── Request bodies ────────────────────────────────────────────

class GenerateStoryRequest(BaseModel):
    """
    Request body for POST /generate-story.
    Kick-starts a brand-new story and generates Chapter 1.
    """
    title:      str            = Field(..., min_length=1, max_length=200)
    characters: List[Character] = Field(..., min_length=1, description="At least one character required")
    config:     StoryConfig
    additional_instructions: Optional[str] = Field(
        None, description="Any extra author notes or constraints"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "title": "The Crimson Throne",
                "characters": [
                    {
                        "name": "Lord Aldric Vane",
                        "role": "protagonist",
                        "background": "A disgraced knight seeking redemption after betraying his king.",
                        "motivation": "To restore his family honour and protect the realm.",
                        "appearance": "Tall, scarred jaw, piercing grey eyes, silver-streaked hair."
                    },
                    {
                        "name": "Seraphine Mourne",
                        "role": "antagonist",
                        "background": "A sorceress who believes power is the only truth.",
                        "motivation": "To claim the Crimson Throne and reshape the world in her image.",
                        "appearance": "Slender, obsidian hair, violet eyes that glow when casting."
                    }
                ],
                "config": {
                    "genre": "fantasy",
                    "style": "Shakespearean",
                    "setting": "The medieval kingdom of Aevoria, perpetually at war.",
                    "plot_summary": "A disgraced knight must stop a dark sorceress from seizing the throne using an ancient blood-magic ritual.",
                    "tone": "dark and tragic",
                    "pov": "third-person limited"
                },
                "additional_instructions": "Open with a battle scene. Heavy use of soliloquy."
            }
        }
    }


class NextChapterRequest(BaseModel):
    """
    Request body for POST /next-chapter.
    Continues an existing story identified by story_id.
    """
    story_id:   str = Field(..., description="MongoDB ObjectId of the existing story")
    plot_hint:  Optional[str] = Field(
        None,
        description="Optional author hint for where this chapter should go"
    )


# ── Response bodies ───────────────────────────────────────────

class ChapterOut(BaseModel):
    """A single chapter as returned to the client."""
    chapter_number: int
    title:          str
    content:        str
    word_count:     int


class StoryOut(BaseModel):
    """Full story response returned after generation or retrieval."""
    id:          str
    title:       str
    characters:  List[Character]
    config:      StoryConfig
    chapters:    List[ChapterOut]
    total_words: int
    created_at:  str
    updated_at:  str
