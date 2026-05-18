from __future__ import annotations

import json
import logging
from typing import Any, Callable, Optional

from bedtime_story_agent.agent.prompts import build_judge_prompt
from bedtime_story_agent.domain.constants import (
    DEFAULT_MODEL,
    MIN_NUMERIC_SCORE,
    PASSING_OVERALL_SCORE,
    STRUCTURED_OUTPUT_MODELS,
)
from bedtime_story_agent.domain.judge_schema import (
    JUDGE_RESPONSE_FORMAT,
    NUMERIC_SCORE_FIELDS,
    QUALITY_BOOLEAN_FIELDS,
    REQUIRED_JUDGE_FIELDS,
    SAFETY_FIELDS,
)

logger = logging.getLogger(__name__)

ModelClient = Callable[..., str]


class JudgeError(Exception):
    def __init__(self, message: str, raw_outputs: Optional[list[str]] = None):
        super().__init__(message)
        self.raw_outputs = raw_outputs or []


def parse_judgment(raw: str) -> dict[str, Any]:
    judgment = json.loads(raw.strip())
    if not isinstance(judgment, dict):
        raise ValueError("Judge output must be a JSON object.")

    missing = [field for field in REQUIRED_JUDGE_FIELDS if field not in judgment]
    if missing:
        raise ValueError(f"Judge output missing required fields: {missing}")

    extra = [field for field in judgment if field not in REQUIRED_JUDGE_FIELDS]
    if extra:
        raise ValueError(f"Judge output contains extra fields: {extra}")

    for field_name in SAFETY_FIELDS + QUALITY_BOOLEAN_FIELDS:
        if not isinstance(judgment[field_name], bool):
            raise ValueError(f"{field_name} must be boolean.")

    for field_name in NUMERIC_SCORE_FIELDS + ["overall_score"]:
        value = judgment[field_name]
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError(f"{field_name} must be numeric.")
        if value < 1 or value > 5:
            raise ValueError(f"{field_name} must be between 1 and 5.")

    if not isinstance(judgment["issues"], list):
        raise ValueError("issues must be a list.")
    if not all(isinstance(issue, str) for issue in judgment["issues"]):
        raise ValueError("issues must be a list of strings.")
    if not isinstance(judgment["revision_instructions"], str):
        raise ValueError("revision_instructions must be a string.")

    return judgment


def judge_story(
    user_request: str,
    story: str,
    model_client: ModelClient,
    model: str = DEFAULT_MODEL,
) -> dict[str, Any]:
    raw_outputs: list[str] = []

    if model in STRUCTURED_OUTPUT_MODELS:
        try:
            raw = model_client(
                build_judge_prompt(user_request, story, strict_json=True),
                model=model,
                max_tokens=1200,
                temperature=0.0,
                text_format=JUDGE_RESPONSE_FORMAT,
            )
            raw_outputs.append(raw)
            return parse_judgment(raw)
        except Exception as exc:  # pragma: no cover - exact SDK errors vary
            logger.info("Structured judge output failed; retrying JSON parser path: %s", exc)

    for strict_json in (False, True):
        try:
            raw = model_client(
                build_judge_prompt(user_request, story, strict_json=strict_json),
                model=model,
                max_tokens=1200,
                temperature=0.0,
            )
        except Exception as exc:  # pragma: no cover - exact SDK errors vary
            raise JudgeError(f"Judge model call failed: {exc}", raw_outputs) from exc

        raw_outputs.append(raw)
        try:
            return parse_judgment(raw)
        except (json.JSONDecodeError, ValueError) as exc:
            logger.info("Judge JSON parse failed on strict_json=%s: %s", strict_json, exc)
            continue

    raise JudgeError("Judge response could not be parsed after retry.", raw_outputs)


def has_safety_failure(judgment: dict[str, Any]) -> bool:
    return not all(bool(judgment[field_name]) for field_name in SAFETY_FIELDS)


def is_quality_threshold_met(judgment: dict[str, Any]) -> bool:
    booleans_pass = all(bool(judgment[field_name]) for field_name in QUALITY_BOOLEAN_FIELDS)
    numeric_scores_pass = all(
        float(judgment[field_name]) >= MIN_NUMERIC_SCORE
        for field_name in NUMERIC_SCORE_FIELDS
    )
    overall_pass = float(judgment["overall_score"]) >= PASSING_OVERALL_SCORE
    return booleans_pass and numeric_scores_pass and overall_pass

