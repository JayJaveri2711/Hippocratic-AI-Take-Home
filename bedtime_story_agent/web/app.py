from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import Optional

from flask import Flask, render_template, request

from bedtime_story_agent.agent.story_agent import run_story_agent
from bedtime_story_agent.domain.constants import DEFAULT_MODEL, SUPPORTED_MODELS
from bedtime_story_agent.domain.models import StoryResult

logger = logging.getLogger(__name__)

AgentRunner = Callable[..., StoryResult]


def _selected_model(raw_model: Optional[str]) -> tuple[str, Optional[str]]:
    if raw_model in SUPPORTED_MODELS:
        return raw_model, None
    if raw_model:
        return DEFAULT_MODEL, f"Unsupported model '{raw_model}' was replaced with {DEFAULT_MODEL}."
    return DEFAULT_MODEL, None


def _json_dump(value: object) -> str:
    return json.dumps(value, indent=2, default=str)


def create_app(agent_runner: AgentRunner = run_story_agent) -> Flask:
    app = Flask(__name__)
    app.config["STORY_AGENT_RUNNER"] = agent_runner

    @app.get("/")
    def index():
        return render_template(
            "index.html",
            request_text="",
            selected_model=DEFAULT_MODEL,
            supported_models=SUPPORTED_MODELS,
            debug=False,
            result=None,
            status_label=None,
            warnings=[],
            final_judgment_json=None,
            debug_info_json=None,
        )

    @app.post("/")
    def generate_story():
        request_text = request.form.get("request", "").strip()
        selected_model, model_warning = _selected_model(request.form.get("model"))
        debug = request.form.get("debug") == "on"
        warnings = [model_warning] if model_warning else []

        logger.info("Web story request received model=%s debug=%s", selected_model, debug)
        result = app.config["STORY_AGENT_RUNNER"](
            request_text,
            debug=debug,
            model=selected_model,
        )
        warnings.extend(result.warnings)

        return render_template(
            "index.html",
            request_text=request_text,
            selected_model=selected_model,
            supported_models=SUPPORTED_MODELS,
            debug=debug,
            result=result,
            status_label=result.status.value,
            warnings=warnings,
            final_judgment_json=_json_dump(result.final_judgment)
            if result.final_judgment is not None
            else None,
            debug_info_json=_json_dump(result.debug_info) if debug else None,
        )

    return app


app = create_app()
