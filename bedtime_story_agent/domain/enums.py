from enum import Enum


class StoryStatus(str, Enum):
    PASSED = "passed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    REFUSED_SCOPE = "refused_scope"
    REFUSED_SAFETY = "refused_safety"
    FAILED_JUDGE = "failed_judge"
    FAILED_GENERATION = "failed_generation"


class StoryCategory(str, Enum):
    CALMING_BEDTIME = "calming_bedtime"
    FRIENDSHIP = "friendship"
    LEARNING = "learning"
    ADVENTURE = "adventure"
    GENERAL = "general"
