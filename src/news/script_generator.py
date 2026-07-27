"""Adapter between the news_to_short pipeline and the shared script engine.

This module used to *be* the generator: six hard-coded phrases and the duration
table ``[3.5, 7.0, 10.0, 13.0, 10.0, 8.0]``. That code still exists, unchanged, as
``src.content.script_engine.providers.legacy_template`` - it is now one provider
among several rather than the only way a script can be written.

``build_script(job, research)`` keeps its exact signature and still returns the
``script.json`` dict the rest of the pipeline reads, so ``visual_plan``,
``voice_adapter``, ``subtitles``, ``final_renderer``, ``quality_check`` and
``exporter`` did not have to change.
"""

from __future__ import annotations

from typing import Any

from src.content.script_engine import (
    DEFAULT_PROVIDER_ID,
    SOURCE_NARRATION_TEXT,
    SOURCE_RESEARCH,
    SOURCE_TOPIC,
    SOURCE_USER_SCRIPT,
    ScriptConstraints,
    ScriptGeneration,
    ScriptRequest,
    generate_script,
    get_provider,
    resolve_provider_id,
)

from .models import INPUT_MODE_TEXT, INPUT_MODE_TOPIC, NewsJob

# Source kinds a job may declare in NewsJob.script_source. Empty means "work it
# out from input_mode", which is what every pre-existing job.json does.
JOB_SOURCE_KINDS = (SOURCE_RESEARCH, SOURCE_TOPIC, SOURCE_USER_SCRIPT, SOURCE_NARRATION_TEXT)


def resolve_source_kind(job: NewsJob, research: dict[str, Any] | None = None) -> str:
    """What the job's material actually is.

    ``job.script_source`` is set by the caller that knows - the content-creation
    service, which is the only place that can tell a pasted *article* from a
    pasted *script* (``content_input_mode``). Without it we fall back to the
    input mode, exactly as before.
    """
    declared = (getattr(job, "script_source", "") or "").strip()
    if declared in JOB_SOURCE_KINDS:
        return declared
    if job.input_mode == INPUT_MODE_TOPIC and not (research or {}).get("claims"):
        return SOURCE_TOPIC
    if job.input_mode == INPUT_MODE_TEXT:
        return SOURCE_RESEARCH
    return SOURCE_RESEARCH


def build_script_request(job: NewsJob, research: dict[str, Any]) -> ScriptRequest:
    source_kind = resolve_source_kind(job, research)
    if source_kind in {SOURCE_USER_SCRIPT, SOURCE_NARRATION_TEXT}:
        # The user's own words are the material - never the research re-telling of them.
        raw_text = job.input_text
    else:
        raw_text = _article_text(research)
    return ScriptRequest(
        source_kind=source_kind,
        language=job.language,
        title=job.title or "",
        topic=research.get("topic") or job.topic or "",
        raw_text=raw_text,
        summary=str(research.get("summary") or ""),
        claims=list(research.get("claims") or []),
        source_urls=list(job.source_urls),
        constraints=ScriptConstraints(target_duration_sec=float(job.target_duration_sec or 55)),
        format_id="vertical_short",
        template_id="fullscreen_voiceover_v1",
        channel_id=job.channel_id,
        include_cta=bool(getattr(job, "script_include_cta", False)),
        cta_text=str(getattr(job, "script_cta_text", "") or ""),
        provider_id=str(getattr(job, "script_provider", "") or ""),
        # The author's explicit "what to show", carried from the job to the provider
        # that can honour it. Empty for every job written before Q2.2A.
        visual_briefs={
            str(key): dict(value)
            for key, value in (getattr(job, "visual_briefs", None) or {}).items()
            if isinstance(value, dict)
        },
    )


def generate_for_job(job: NewsJob, research: dict[str, Any]) -> ScriptGeneration:
    """Full engine outcome (script + validation), for callers that want both.

    A provider that needs the network or a paid API can fail for reasons the user
    cannot do anything about mid-run, so the pipeline asks for a local fallback in
    that one case. A local provider's failure is a real input problem (empty text,
    unsupported source) and is left to surface.
    """
    request = build_script_request(job, research)
    capabilities = get_provider(resolve_provider_id(request)).capabilities
    remote = capabilities.requires_network or capabilities.requires_paid_api
    return generate_script(request, fallback_provider_id=DEFAULT_PROVIDER_ID if remote else "")


def build_script(job: NewsJob, research: dict[str, Any]) -> dict[str, Any]:
    """The script.json payload for this job. Signature unchanged since Stage AB."""
    outcome = generate_for_job(job, research)
    script = outcome.to_legacy_script(target_duration_sec=job.target_duration_sec)
    # The verdict travels with the script instead of being recomputed by every
    # reader; quality_check keeps its own independent checks.
    script["script_validation"] = outcome.validation.to_dict()
    return script


def _article_text(research: dict[str, Any]) -> str:
    """Claims carry the article's sentences already (research keeps the first eight,
    which is more than a 55-second short can hold), so raw text is only needed when
    research produced none."""
    if research.get("claims"):
        return ""
    return str(research.get("summary") or "")


__all__ = ["build_script", "build_script_request", "generate_for_job", "resolve_source_kind"]
