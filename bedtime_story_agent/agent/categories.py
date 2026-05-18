from __future__ import annotations

from typing import Any

from bedtime_story_agent.domain.enums import StoryCategory
from bedtime_story_agent.domain.models import StoryPreset


CATEGORY_KEYWORDS: dict[StoryCategory, tuple[str, ...]] = {
    StoryCategory.CALMING_BEDTIME: (
        "sleep",
        "sleepy",
        "bed",
        "bedtime",
        "moon",
        "stars",
        "dream",
        "night",
        "lullaby",
    ),
    StoryCategory.FRIENDSHIP: (
        "friend",
        "friends",
        "lonely",
        "kind",
        "share",
        "belong",
        "together",
    ),
    StoryCategory.LEARNING: (
        "learn",
        "lesson",
        "school",
        "curious",
        "discover",
        "patience",
        "practice",
        "manners",
    ),
    StoryCategory.ADVENTURE: (
        "adventure",
        "journey",
        "quest",
        "explore",
        "space",
        "robot",
        "ninja",
        "treasure",
    ),
}

CATEGORY_PRIORITY = (
    StoryCategory.CALMING_BEDTIME,
    StoryCategory.FRIENDSHIP,
    StoryCategory.LEARNING,
    StoryCategory.ADVENTURE,
)

STORY_PRESETS: dict[StoryCategory, StoryPreset] = {
    StoryCategory.CALMING_BEDTIME: StoryPreset(
        arc="wind-down arc",
        strategy=(
            "Use slower pacing, soft sensory details, very low conflict, "
            "gentle repetition, and a peaceful ending."
        ),
    ),
    StoryCategory.FRIENDSHIP: StoryPreset(
        arc="friendship conflict-resolution arc",
        strategy=(
            "Focus on a character who feels unsure, makes a kind choice, "
            "and ends with belonging or renewed friendship."
        ),
    ),
    StoryCategory.LEARNING: StoryPreset(
        arc="gentle discovery arc",
        strategy="Teach one simple concept through discovery and action, not a lecture.",
    ),
    StoryCategory.ADVENTURE: StoryPreset(
        arc="gentle quest arc",
        strategy=(
            "Create an exciting but non-scary journey with a safe challenge, "
            "a discovery, and a calm return home."
        ),
    ),
    StoryCategory.GENERAL: StoryPreset(
        arc="classic bedtime arc",
        strategy=(
            "Use a clear beginning, middle, and end with a gentle problem, "
            "a kind choice, and a comforting resolution."
        ),
    ),
}


def categorize_request(user_request: str) -> dict[str, Any]:
    text = user_request.lower()
    matched_categories = [
        category
        for category, keywords in CATEGORY_KEYWORDS.items()
        if any(keyword in text for keyword in keywords)
    ]
    primary = next(
        (category for category in CATEGORY_PRIORITY if category in matched_categories),
        StoryCategory.GENERAL,
    )
    preset = STORY_PRESETS[primary]

    return {
        "category": primary.value,
        "matched_categories": [
            category.value for category in matched_categories
        ]
        or [StoryCategory.GENERAL.value],
        "arc": preset.arc,
        "strategy": preset.strategy,
    }
