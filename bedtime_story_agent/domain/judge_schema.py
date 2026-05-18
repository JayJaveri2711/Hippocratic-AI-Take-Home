SAFETY_FIELDS = [
    "age_appropriate",
    "safe_for_bedtime",
    "no_unsafe_content",
]

QUALITY_BOOLEAN_FIELDS = [
    "follows_request",
    "has_story_arc",
    "appropriate_length",
]

NUMERIC_SCORE_FIELDS = [
    "language_score",
    "creativity_score",
    "bedtime_score",
]

REQUIRED_JUDGE_FIELDS = (
    SAFETY_FIELDS
    + QUALITY_BOOLEAN_FIELDS
    + NUMERIC_SCORE_FIELDS
    + ["overall_score", "issues", "revision_instructions"]
)

JUDGE_RESULT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": REQUIRED_JUDGE_FIELDS,
    "properties": {
        "age_appropriate": {"type": "boolean"},
        "safe_for_bedtime": {"type": "boolean"},
        "no_unsafe_content": {"type": "boolean"},
        "follows_request": {"type": "boolean"},
        "has_story_arc": {"type": "boolean"},
        "appropriate_length": {"type": "boolean"},
        "language_score": {"type": "number", "minimum": 1, "maximum": 5},
        "creativity_score": {"type": "number", "minimum": 1, "maximum": 5},
        "bedtime_score": {"type": "number", "minimum": 1, "maximum": 5},
        "overall_score": {"type": "number", "minimum": 1, "maximum": 5},
        "issues": {"type": "array", "items": {"type": "string"}},
        "revision_instructions": {"type": "string"},
    },
}

JUDGE_RESPONSE_FORMAT = {
    "type": "json_schema",
    "name": "bedtime_story_judgment",
    "schema": JUDGE_RESULT_SCHEMA,
    "strict": True,
}
