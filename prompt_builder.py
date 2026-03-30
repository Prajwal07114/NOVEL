# app/utils/prompt_builder.py
# ──────────────────────────────────────────────────────────────
# Prompt engineering module.
#
# Two public functions:
#   build_chapter_one_prompt()   — for the very first chapter
#   build_next_chapter_prompt()  — for all subsequent chapters
#
# The prompts are deliberately rich:
#   • Style-specific instructions (especially Shakespearean)
#   • Emotional storytelling directives
#   • Dialogue requirements
#   • Continuity anchors
# ──────────────────────────────────────────────────────────────

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.models.story_models import Character, StoryConfig, WritingStyle


# ── Style-specific writing instructions ───────────────────────

_STYLE_INSTRUCTIONS: Dict[str, str] = {
    WritingStyle.shakespearean: (
        "Write in rich Elizabethan English. Use archaic pronouns (thee, thou, thy, thine, dost, hast). "
        "Employ iambic-inflected prose with rhetorical flourishes — anaphora, apostrophe, and extended metaphor. "
        "Characters should deliver impassioned soliloquies that reveal inner conflict. "
        "Include asides and dramatic irony. Use Latinate vocabulary alongside Anglo-Saxon plainness for contrast. "
        "Speech should be elevated, poetic, and steeped in the language of honour, fate, and celestial imagery."
    ),
    WritingStyle.modern: (
        "Write in clean, contemporary prose. Sentences vary between short punchy beats and longer flowing thoughts. "
        "Dialogue should sound natural and authentic to how real people speak today. "
        "Show internal consciousness through close third-person or first-person intimacy."
    ),
    WritingStyle.minimalist: (
        "Write with extreme economy. Every word must earn its place. "
        "Short declarative sentences. White space carries weight. Subtext over text. "
        "Resist the urge to explain — trust the reader."
    ),
    WritingStyle.gothic: (
        "Write in brooding, atmospheric prose laden with dread and melancholy. "
        "Describe settings as living entities — the darkness breathes, the walls remember. "
        "Use long, winding sentences that build claustrophobic tension. "
        "Lean into the grotesque, the sublime, and the uncanny."
    ),
    WritingStyle.lyrical: (
        "Write in lush, musically cadenced prose. Sentences should sing. "
        "Employ sensory imagery, synesthesia, and poetic metaphor liberally. "
        "The emotional interior of characters should be rendered in images, not statements."
    ),
    WritingStyle.noir: (
        "Write in a hard-boiled first-person voice — cynical, world-weary, darkly witty. "
        "Snappy similes, laconic dialogue, moral ambiguity. "
        "The city is always a character. Trust is a luxury nobody can afford."
    ),
    WritingStyle.epistolary: (
        "Render the story entirely through documents — letters, diary entries, telegrams, reports, or messages. "
        "Each document should have a clear sender, recipient, and date. "
        "Voice must shift authentically between different writers."
    ),
    WritingStyle.stream_of_consciousness: (
        "Write in an unfiltered, associative interior monologue. "
        "Thoughts interrupt themselves; memories bleed into the present; "
        "punctuation bends to the rhythm of the mind, not grammar."
    ),
}

_DEFAULT_STYLE_INSTRUCTION = (
    "Write in vivid, engaging prose that suits the genre and tone."
)


def _style_block(style: WritingStyle) -> str:
    return _STYLE_INSTRUCTIONS.get(style, _DEFAULT_STYLE_INSTRUCTION)


def _character_block(characters: List[Character]) -> str:
    """Render a readable character sheet for the prompt."""
    lines = []
    for char in characters:
        lines.append(f"  • {char.name} ({char.role.upper()})")
        lines.append(f"    Background  : {char.background}")
        lines.append(f"    Motivation  : {char.motivation}")
        if char.appearance:
            lines.append(f"    Appearance  : {char.appearance}")
    return "\n".join(lines)


# ── Public builders ───────────────────────────────────────────

def build_chapter_one_prompt(
    title: str,
    characters: List[Character],
    config: StoryConfig,
    additional_instructions: Optional[str] = None,
) -> str:
    """
    Build the system + user prompt for generating Chapter 1.

    Returns a single string that will be sent as the user message.
    The system message is handled separately in ai_service.py.
    """

    extra = (
        f"\n\nADDITIONAL AUTHOR NOTES:\n{additional_instructions}"
        if additional_instructions
        else ""
    )

    prompt = f"""You are a master novelist tasked with writing Chapter 1 of a novel.

═══════════════════════════════════════════════════════════════
NOVEL BLUEPRINT
═══════════════════════════════════════════════════════════════

TITLE          : {title}
GENRE          : {config.genre.value}
WRITING STYLE  : {config.style.value}
SETTING        : {config.setting}
TONE           : {config.tone or "dramatic"}
POINT OF VIEW  : {config.pov or "third-person limited"}

PLOT SUMMARY:
{config.plot_summary}

CHARACTERS:
{_character_block(characters)}
{extra}

═══════════════════════════════════════════════════════════════
STYLE DIRECTIVE
═══════════════════════════════════════════════════════════════

{_style_block(config.style)}

═══════════════════════════════════════════════════════════════
STORYTELLING REQUIREMENTS
═══════════════════════════════════════════════════════════════

1. EMOTIONAL DEPTH
   - Every scene must carry an emotional charge.
   - Characters' inner lives should be palpable — readers must feel what they feel.
   - At least one moment of genuine vulnerability or raw emotion.

2. DIALOGUE
   - Include at least three exchanges of meaningful dialogue.
   - Dialogue must reveal character, advance plot, or both simultaneously.
   - Each character must have a distinct voice — no two characters sound alike.

3. WORLD-BUILDING
   - Establish the setting with rich, specific sensory detail in the first 200 words.
   - Weave world-building into action and dialogue — never info-dump.

4. NARRATIVE HOOK
   - The opening sentence must be irresistible.
   - End Chapter 1 with a compelling hook that demands the reader continue.

5. CHARACTER CONSISTENCY
   - Every action, thought, and word must be true to the characters defined above.
   - Protagonist and antagonist must both be introduced, directly or by implication.

═══════════════════════════════════════════════════════════════
OUTPUT FORMAT
═══════════════════════════════════════════════════════════════

Return ONLY the chapter content in this exact format:

CHAPTER 1: [Give this chapter a compelling title]

[Full chapter text — minimum 800 words, aim for 1 200–1 500 words]

---END CHAPTER---

Do not include any commentary, author notes, or preamble outside the chapter block.
"""

    return prompt.strip()


def build_next_chapter_prompt(
    story: Dict[str, Any],
    chapter_number: int,
    plot_hint: Optional[str] = None,
) -> str:
    """
    Build the continuation prompt for chapters 2+.

    Uses the full story document so the AI can maintain character
    consistency and pick up exactly where the previous chapter ended.
    """

    chapters: List[Dict] = story.get("chapters", [])
    config_raw          = story.get("config", {})
    characters_raw      = story.get("characters", [])
    title               = story.get("title", "Untitled")

    # Reconstruct style from stored config string
    style_value   = config_raw.get("style", "modern")
    genre_value   = config_raw.get("genre", "literary fiction")
    tone_value    = config_raw.get("tone", "dramatic")
    pov_value     = config_raw.get("pov", "third-person limited")
    plot_summary  = config_raw.get("plot_summary", "")
    setting       = config_raw.get("setting", "")

    # Build a brief character reference
    char_lines = []
    for c in characters_raw:
        char_lines.append(
            f"  • {c['name']} ({c['role']}): {c['motivation']}"
        )
    char_ref = "\n".join(char_lines) if char_lines else "  (see earlier chapters)"

    # Summarise previous chapters — send the LAST chapter in full,
    # earlier ones as brief summaries (saves tokens, preserves context).
    chapter_context_parts = []
    for ch in chapters[:-1]:
        chapter_context_parts.append(
            f"[Chapter {ch['chapter_number']}: {ch['title']} — summary]\n"
            f"{ch['content'][:400].strip()}…\n"
        )
    if chapters:
        last = chapters[-1]
        chapter_context_parts.append(
            f"[Chapter {last['chapter_number']}: {last['title']} — FULL TEXT]\n"
            f"{last['content']}\n"
        )

    chapter_context = "\n".join(chapter_context_parts) or "No previous chapters."

    # Try to look up style instruction; fall back to generic
    try:
        style_enum = WritingStyle(style_value)
        style_directive = _style_block(style_enum)
    except ValueError:
        style_directive = _DEFAULT_STYLE_INSTRUCTION

    hint_block = (
        f"\nAUTHOR DIRECTION FOR THIS CHAPTER:\n{plot_hint}\n"
        if plot_hint
        else ""
    )

    prompt = f"""You are continuing to write the novel "{title}".

═══════════════════════════════════════════════════════════════
STORY CONTEXT
═══════════════════════════════════════════════════════════════

GENRE          : {genre_value}
WRITING STYLE  : {style_value}
TONE           : {tone_value}
POINT OF VIEW  : {pov_value}
SETTING        : {setting}

MASTER PLOT:
{plot_summary}

CHARACTERS (maintain consistency):
{char_ref}
{hint_block}
═══════════════════════════════════════════════════════════════
STORY SO FAR
═══════════════════════════════════════════════════════════════

{chapter_context}

═══════════════════════════════════════════════════════════════
STYLE DIRECTIVE
═══════════════════════════════════════════════════════════════

{style_directive}

═══════════════════════════════════════════════════════════════
CHAPTER {chapter_number} REQUIREMENTS
═══════════════════════════════════════════════════════════════

1. CONTINUITY
   - Begin exactly where Chapter {chapter_number - 1} ended — same time, same location.
   - Honour every plot point, character decision, and world-building detail established earlier.
   - Do NOT contradict or reset anything that has already happened.

2. EMOTIONAL PROGRESSION
   - The emotional stakes must be HIGHER than the previous chapter.
   - At least one scene of genuine conflict — internal, interpersonal, or physical.

3. DIALOGUE
   - Rich, character-specific dialogue. At least three exchanges.
   - Use dialogue to reveal new information or deepen existing tension.

4. PACING
   - Vary pace: a moment of stillness, a moment of action, a moment of revelation.

5. CHAPTER ENDING
   - End on a hook, revelation, or emotional pivot that propels the reader into Chapter {chapter_number + 1}.

═══════════════════════════════════════════════════════════════
OUTPUT FORMAT
═══════════════════════════════════════════════════════════════

Return ONLY the chapter content in this exact format:

CHAPTER {chapter_number}: [Give this chapter a compelling title]

[Full chapter text — minimum 800 words, aim for 1 200–1 500 words]

---END CHAPTER---

Do not include any commentary, author notes, or preamble outside the chapter block.
"""

    return prompt.strip()
