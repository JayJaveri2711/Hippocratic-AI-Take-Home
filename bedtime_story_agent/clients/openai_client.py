from __future__ import annotations

import logging
import os
from typing import Any, Optional

from bedtime_story_agent.domain.constants import DEFAULT_MODEL

logger = logging.getLogger(__name__)


def _extract_response_text(response: Any) -> str:
    output_text = getattr(response, "output_text", None)
    if output_text:
        return output_text

    text_parts: list[str] = []
    for output in getattr(response, "output", []) or []:
        for content in getattr(output, "content", []) or []:
            text = getattr(content, "text", None)
            if text:
                text_parts.append(text)
    return "\n".join(text_parts)


def call_model(
    messages: list[dict[str, str]],
    model: str = DEFAULT_MODEL,
    max_tokens: int = 3000,
    temperature: float = 0.7,
    text_format: Optional[dict[str, Any]] = None,
) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Set it before running the story agent."
        )

    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    payload: dict[str, Any] = {
        "model": model,
        "input": messages,
        "max_output_tokens": max_tokens,
        "temperature": temperature,
    }
    if text_format is not None:
        payload["text"] = {"format": text_format}

    logger.info("Calling OpenAI Responses API with model=%s", model)
    response = client.responses.create(**payload)
    return _extract_response_text(response)
