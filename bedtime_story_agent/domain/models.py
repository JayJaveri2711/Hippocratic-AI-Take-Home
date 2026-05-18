from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from bedtime_story_agent.domain.enums import StoryStatus


@dataclass(frozen=True)
class StoryPreset:
    arc: str
    strategy: str


@dataclass
class StoryResult:
    status: StoryStatus
    story: Optional[str]
    final_judgment: Optional[dict[str, Any]]
    attempts_used: int
    used_fallback: bool = False
    warnings: list[str] = field(default_factory=list)
    error: Optional[str] = None
    debug_info: dict[str, Any] = field(default_factory=dict)
