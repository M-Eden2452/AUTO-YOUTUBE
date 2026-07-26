from __future__ import annotations

import dataclasses
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from src.project_foundation.naming import build_project_id, suggest_title

MODE_NEWS_TO_SHORT = "news_to_short"
INPUT_MODE_URL = "url"
INPUT_MODE_TOPIC = "topic"
INPUT_MODE_TEXT = "text"

RIGHTS_USER_OWNED = "user_owned"
RIGHTS_LICENSED = "licensed"
RIGHTS_CREATIVE_COMMONS = "creative_commons"
RIGHTS_PUBLIC_DOMAIN = "public_domain"
RIGHTS_EDITORIAL_REVIEW_REQUIRED = "editorial_review_required"
RIGHTS_REFERENCE_ONLY = "reference_only"
RIGHTS_BLOCKED = "blocked"

ALLOWED_RENDER_RIGHTS = {
    RIGHTS_USER_OWNED,
    RIGHTS_LICENSED,
    RIGHTS_CREATIVE_COMMONS,
    RIGHTS_PUBLIC_DOMAIN,
}

NEWS_TO_SHORT_STAGES = [
    "input",
    "article_ingestion",
    "research",
    "script",
    "visual_plan",
    "asset_search",
    "voice",
    "subtitles",
    "preview_render",
    "quality_check",
    "final_render",
    "export",
]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def slugify(value: str, fallback: str = "news") -> str:
    lowered = value.lower()
    normalized = re.sub(r"[^a-z0-9а-яё]+", "_", lowered, flags=re.IGNORECASE).strip("_")
    normalized = re.sub(r"_+", "_", normalized)
    return normalized[:64] or fallback


def asdict_clean(value: Any) -> Any:
    if dataclasses.is_dataclass(value):
        return {key: asdict_clean(item) for key, item in dataclasses.asdict(value).items()}
    if isinstance(value, dict):
        return {key: asdict_clean(item) for key, item in value.items()}
    if isinstance(value, list):
        return [asdict_clean(item) for item in value]
    return value


@dataclass
class StageState:
    stage: str
    status: str = "pending"
    started_at: str | None = None
    finished_at: str | None = None
    result_path: str | None = None
    error: str | None = None
    attempts: int = 0
    settings: dict[str, Any] = field(default_factory=dict)


@dataclass
class LocalizationState:
    language: str
    script_locale: str
    enabled: bool = False
    voice_status: str = "unconfigured"
    script_path: str | None = None
    narration_path: str | None = None
    visual_plan_path: str | None = None
    timeline_path: str | None = None


@dataclass
class AssetRights:
    asset_id: str
    source_url: str = ""
    source_page: str = ""
    provider: str = ""
    author: str = ""
    license: str = "unknown"
    credit_required: bool = False
    rights_status: str = RIGHTS_REFERENCE_ONLY

    @property
    def allowed_for_render(self) -> bool:
        return self.rights_status in ALLOWED_RENDER_RIGHTS


@dataclass
class NewsJob:
    job_id: str
    mode: str
    channel_id: str
    input_mode: str
    # Human name of the video, chosen by the user. Separate from `topic`, which is
    # pipeline input (and, for a pasted script, was simply its first 80 characters).
    # Optional: a job.json written before this field existed loads unchanged.
    title: str = ""
    topic: str = ""
    source_urls: list[str] = field(default_factory=list)
    input_text: str = ""
    user_assets: list[str] = field(default_factory=list)
    language: str = "ru"
    target_duration_sec: int = 55
    # Script engine selection (src.content.script_engine). All optional: a job.json
    # written before the engine existed loads unchanged and resolves to the defaults.
    # script_source says what input_text really is - only the caller that collected
    # it can tell a pasted article from a pasted script.
    script_provider: str = ""
    script_source: str = ""
    script_include_cta: bool = False
    script_cta_text: str = ""
    aspect_ratio: str = "9:16"
    resolution: dict[str, int] = field(default_factory=lambda: {"width": 1080, "height": 1920})
    platforms: list[str] = field(default_factory=lambda: ["youtube_shorts", "instagram_reels", "facebook_reels"])
    status: str = "created"
    current_stage: str = "input"
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    stages: dict[str, StageState] = field(default_factory=dict)
    localizations: dict[str, LocalizationState] = field(default_factory=dict)
    localization: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        *,
        channel_id: str,
        input_mode: str,
        title: str = "",
        topic: str = "",
        source_urls: list[str] | None = None,
        input_text: str = "",
        user_assets: list[str] | None = None,
        language: str = "ru",
        target_duration_sec: int = 55,
        script_provider: str = "",
        script_source: str = "",
        script_include_cta: bool = False,
        script_cta_text: str = "",
        now: str | None = None,
        is_taken: Any = None,
    ) -> "NewsJob":
        created_at = now or utc_now_iso()
        # The folder is named after the title the user gave the video. It falls back
        # to the topic and only then to the input text - which is how folders like
        # "wizard_установил_questionary_единственная_подходящая_библиотека_..." used
        # to happen: that was the first 80 characters of a pasted script.
        seed = title or topic or suggest_title(input_text) or (source_urls or ["news"])[0]
        job_id = build_project_id(seed, created_at=created_at, is_taken=is_taken, fallback="news")
        localizations = {
            "ru": LocalizationState(language="ru", script_locale="ru-RU", enabled=language == "ru"),
            "en": LocalizationState(language="en", script_locale="en-US", enabled=language == "en"),
            "es": LocalizationState(language="es", script_locale="es-ES", enabled=language == "es"),
        }
        if language not in localizations:
            localizations[language] = LocalizationState(language=language, script_locale=language, enabled=True)
        stages = {stage: StageState(stage=stage) for stage in NEWS_TO_SHORT_STAGES}
        return cls(
            job_id=job_id,
            mode=MODE_NEWS_TO_SHORT,
            channel_id=channel_id,
            input_mode=input_mode,
            title=title or suggest_title(topic, input_text),
            topic=topic,
            source_urls=source_urls or [],
            input_text=input_text,
            user_assets=user_assets or [],
            language=language,
            target_duration_sec=target_duration_sec,
            script_provider=script_provider,
            script_source=script_source,
            script_include_cta=script_include_cta,
            script_cta_text=script_cta_text,
            created_at=created_at,
            updated_at=created_at,
            stages=stages,
            localizations=localizations,
            localization={
                "master_language": language,
                "reuse_research": True,
                "reuse_assets": True,
                "reuse_master_visual_plan": True,
                "localize_hook": True,
                "localize_script": True,
                "localize_subtitles": True,
                "localize_on_screen_text": True,
                "localize_call_to_action": True,
                "retime_scenes_from_audio": True,
                "allow_scene_overrides": True,
            },
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "NewsJob":
        data = dict(data)
        data["stages"] = {key: StageState(**value) for key, value in data.get("stages", {}).items()}
        data["localizations"] = {
            key: LocalizationState(**value) for key, value in data.get("localizations", {}).items()
        }
        return cls(**data)

    def to_dict(self) -> dict[str, Any]:
        return asdict_clean(self)

