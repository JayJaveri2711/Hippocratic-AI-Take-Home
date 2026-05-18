from __future__ import annotations

import logging
from typing import Any, Callable, Optional

from bedtime_story_agent.agent.categories import categorize_request
from bedtime_story_agent.agent.judge import (
    JudgeError,
    has_safety_failure,
    is_quality_threshold_met,
    judge_story,
)
from bedtime_story_agent.agent.prompts import (
    build_fallback_prompt,
    build_revision_prompt,
    build_story_prompt,
)
from bedtime_story_agent.agent.scope import scope_check_request
from bedtime_story_agent.clients.openai_client import call_model
from bedtime_story_agent.domain.constants import (
    DEFAULT_MODEL,
    MAX_REVISION_ATTEMPTS,
    STRUCTURED_OUTPUT_MODELS,
    SUPPORTED_MODELS,
)
from bedtime_story_agent.domain.enums import StoryStatus
from bedtime_story_agent.domain.models import StoryResult

logger = logging.getLogger(__name__)

ModelClient = Callable[..., str]


def _normalize_model(model: str) -> tuple[str, Optional[str]]:
    if model in SUPPORTED_MODELS:
        return model, None
    return (
        DEFAULT_MODEL,
        f"Unsupported model '{model}' was replaced with {DEFAULT_MODEL}.",
    )


def _attempt_summary(
    attempt_number: int,
    attempt_type: str,
    judgment: dict[str, Any],
) -> dict[str, Any]:
    return {
        "attempt": attempt_number,
        "type": attempt_type,
        "safety_passed": not has_safety_failure(judgment),
        "quality_passed": is_quality_threshold_met(judgment),
        "overall_score": judgment.get("overall_score"),
        "issues": judgment.get("issues", []),
        "revision_instructions": judgment.get("revision_instructions", ""),
    }


def _failure_result(
    status: StoryStatus,
    attempts_used: int,
    error: str,
    debug_info: dict[str, Any],
    warning: str,
    extra_warnings: Optional[list[str]] = None,
) -> StoryResult:
    return StoryResult(
        status=status,
        story=None,
        final_judgment=None,
        attempts_used=attempts_used,
        warnings=(extra_warnings or []) + [warning],
        error=error,
        debug_info=debug_info,
    )


def run_story_agent(
    user_request: str,
    debug: bool = False,
    model: str = DEFAULT_MODEL,
    model_client: Optional[ModelClient] = None,
) -> StoryResult:
    del debug  # Debug rendering is handled by the caller; metadata is always collected.
    selected_model, model_warning = _normalize_model(model)
    startup_warnings = [model_warning] if model_warning else []
    if model_client is None:
        model_client = call_model

    debug_info: dict[str, Any] = {
        "original_request": user_request,
        "requested_model": model,
        "selected_model": selected_model,
        "structured_outputs_enabled": selected_model in STRUCTURED_OUTPUT_MODELS,
        "attempt_history": [],
        "fallback_attempted": False,
    }
    logger.info("Starting story agent with model=%s", selected_model)

    scope = scope_check_request(user_request)
    debug_info["scope_check"] = scope
    logger.info("Scope check allowed=%s sanitized=%s", scope["allowed"], scope["was_sanitized"])
    if not scope["allowed"]:
        return _failure_result(
            StoryStatus.REFUSED_SCOPE,
            0,
            "request_out_of_scope",
            debug_info,
            "I can only create bedtime stories appropriate for ages 5 to 10. Please try a gentler story idea.",
            startup_warnings,
        )

    request_for_generation = scope["sanitized_request"]
    categorization = categorize_request(request_for_generation)
    debug_info["categorization"] = categorization
    logger.info("Request category=%s", categorization["category"])

    attempts_used = 0
    best_safe_story: Optional[str] = None
    best_safe_judgment: Optional[dict[str, Any]] = None
    prompt = build_story_prompt(request_for_generation, categorization)

    for attempt_index in range(MAX_REVISION_ATTEMPTS + 1):
        attempt_type = "initial" if attempt_index == 0 else "revision"
        logger.info("Generating %s story attempt %s", attempt_type, attempt_index + 1)
        try:
            story = model_client(
                prompt,
                model=selected_model,
                max_tokens=3000,
                temperature=0.7,
            )
        except Exception as exc:
            logger.exception("Story generation failed")
            return _failure_result(
                StoryStatus.FAILED_GENERATION,
                attempts_used,
                "generation_failed",
                debug_info,
                f"Story generation failed: {exc}",
                startup_warnings,
            )

        attempts_used += 1
        try:
            judgment = judge_story(request_for_generation, story, model_client, selected_model)
        except JudgeError as exc:
            logger.info("Judge failed: %s", exc)
            debug_info["judge_raw_outputs"] = exc.raw_outputs
            return _failure_result(
                StoryStatus.FAILED_JUDGE,
                attempts_used,
                "judge_json_parse_failed",
                debug_info,
                "Story was not returned because safety could not be verified.",
                startup_warnings,
            )

        debug_info["attempt_history"].append(
            _attempt_summary(attempts_used, attempt_type, judgment)
        )
        logger.info(
            "Attempt %s judged safety_passed=%s quality_passed=%s overall=%s",
            attempts_used,
            not has_safety_failure(judgment),
            is_quality_threshold_met(judgment),
            judgment.get("overall_score"),
        )

        if not has_safety_failure(judgment):
            if (
                best_safe_judgment is None
                or float(judgment["overall_score"])
                > float(best_safe_judgment["overall_score"])
            ):
                best_safe_story = story
                best_safe_judgment = judgment

            if is_quality_threshold_met(judgment):
                logger.info("Story agent completed with status=%s", StoryStatus.PASSED.value)
                return StoryResult(
                    status=StoryStatus.PASSED,
                    story=story,
                    final_judgment=judgment,
                    attempts_used=attempts_used,
                    warnings=startup_warnings,
                    debug_info=debug_info,
                )

        if attempt_index < MAX_REVISION_ATTEMPTS:
            prompt = build_revision_prompt(request_for_generation, story, judgment)
            continue

        if (
            best_safe_story is not None
            and best_safe_judgment is not None
            and not has_safety_failure(judgment)
        ):
            logger.info(
                "Story agent completed with status=%s",
                StoryStatus.COMPLETED_WITH_WARNINGS.value,
            )
            return StoryResult(
                status=StoryStatus.COMPLETED_WITH_WARNINGS,
                story=best_safe_story,
                final_judgment=best_safe_judgment,
                attempts_used=attempts_used,
                warnings=startup_warnings
                + [
                    "Story passed safety checks but did not meet the full quality threshold."
                ],
                debug_info=debug_info,
            )

    debug_info["fallback_attempted"] = True
    logger.info("Generating fallback story")
    try:
        fallback_story = model_client(
            build_fallback_prompt(request_for_generation),
            model=selected_model,
            max_tokens=2500,
            temperature=0.5,
        )
    except Exception as exc:
        logger.exception("Fallback story generation failed")
        return _failure_result(
            StoryStatus.FAILED_GENERATION,
            attempts_used,
            "fallback_generation_failed",
            debug_info,
            f"Fallback story generation failed: {exc}",
            startup_warnings,
        )

    attempts_used += 1
    try:
        fallback_judgment = judge_story(
            request_for_generation, fallback_story, model_client, selected_model
        )
    except JudgeError as exc:
        logger.info("Fallback judge failed: %s", exc)
        debug_info["judge_raw_outputs"] = exc.raw_outputs
        return _failure_result(
            StoryStatus.FAILED_JUDGE,
            attempts_used,
            "judge_json_parse_failed",
            debug_info,
            "Fallback story was not returned because safety could not be verified.",
            startup_warnings,
        )

    debug_info["attempt_history"].append(
        _attempt_summary(attempts_used, "fallback", fallback_judgment)
    )

    if not has_safety_failure(fallback_judgment):
        logger.info("Story agent completed with fallback status=%s", StoryStatus.PASSED.value)
        return StoryResult(
            status=StoryStatus.PASSED,
            story=fallback_story,
            final_judgment=fallback_judgment,
            attempts_used=attempts_used,
            used_fallback=True,
            warnings=startup_warnings
            + ["Used a safer fallback story after the original draft failed safety checks."],
            debug_info=debug_info,
        )

    logger.info("Story agent completed with status=%s", StoryStatus.REFUSED_SAFETY.value)
    return StoryResult(
        status=StoryStatus.REFUSED_SAFETY,
        story=None,
        final_judgment=fallback_judgment,
        attempts_used=attempts_used,
        used_fallback=True,
        warnings=startup_warnings
        + ["I could not verify a bedtime-safe story after revision and fallback."],
        error="fallback_failed_safety",
        debug_info=debug_info,
    )

