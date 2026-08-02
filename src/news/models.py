"""Canonical boundary данных задания ``news_to_short``: контракт ``NewsJob``.

Модуль описывает форму того, что хранится в ``job.json``, и словарь стадий
активного workflow. Он ничего не читает и не пишет: persistence принадлежит
``src.news.project_store``, порядок исполнения — ``src.news.pipeline``.

Responsibilities:
- ``NewsJob`` и вложенные ``StageState``, ``LocalizationState``, ``AssetRights``;
- ``NEWS_JOB_SCHEMA_VERSION`` и tolerant чтение задания без версии (ADR 0004);
- ``NEWS_TO_SHORT_STAGES`` — единственный список стадий активного workflow;
- словарь прав ``RIGHTS_*`` и ``ALLOWED_RENDER_RIGHTS`` — какие статусы вообще
  допускают попадание материала в рендер;
- нормализация completion-настроек задания поверх существующего словаря
  ``src.assets.completion``.

Does not own:
- запись, atomic replace, lock и валидацию выходов стадии —
  ``src.news.project_store``;
- исполнение стадий, resume и force-stage — ``src.news.pipeline``;
- решение о правах конкретного кандидата — ``src.assets.license_policy``
  остаётся авторитетом; здесь только словарь допустимых статусов;
- словарь состояний завершённости — ``src.assets.completion.modes``;
- JSON-схему на диске — ``schemas/job.schema.json``.

Important invariants:
- новые payload ``to_dict()`` содержат ``schema_version``; ``job.json``,
  записанный до появления поля, читается как v1 без миграции;
- ``title`` отделён от ``topic``: первый — имя ролика для человека, второй —
  вход pipeline; задание без ``title`` загружается без изменений;
- ``strict`` остаётся режимом по умолчанию, а ``draft_complete`` включает
  лёгкую адаптацию сценария только пока вызывающая сторона не отключила её явно;
- порядок ``NEWS_TO_SHORT_STAGES`` — это объявленный порядок, а не гарантия
  достижимости каждой стадии: известное расхождение ``preview_render`` записано
  как C58 в ``docs/current/CLEANUP_REGISTRY.md`` и здесь не дублируется.

See also: ``src/news/__init__.py``, ``src/news/project_store.py``,
``docs/adr/0004-news-job-schema-version.md``, ``schemas/job.schema.json``.
"""

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

NEWS_JOB_SCHEMA_VERSION = 1

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


def build_completion_state(*, mode: str = "", script_adaptation: str = "") -> dict[str, Any]:
    """The job's completion settings, normalized. Defaults are the pre-Q2.2B behaviour.

    ``draft_complete`` turns on light script adaptation unless the caller switched it
    off explicitly; ``strict`` never adapts, because in strict mode an unanswerable
    scene is meant to stop the run and be looked at.
    """
    from src.assets.completion import MODE_DRAFT_COMPLETE, normalize_mode
    from src.content.script_engine.adaptation import ADAPT_LIGHT, ADAPT_NONE, normalize_adaptation_mode

    resolved_mode = normalize_mode(mode)
    if str(script_adaptation or "").strip():
        adaptation = normalize_adaptation_mode(script_adaptation)
    else:
        adaptation = ADAPT_LIGHT if resolved_mode == MODE_DRAFT_COMPLETE else ADAPT_NONE
    return {"mode": resolved_mode, "script_adaptation": adaptation, "adaptation_pass": 0}


def completion_settings(job: "NewsJob") -> dict[str, Any]:
    """A job's completion settings, filled in for a job.json written before they existed."""
    stored = job.completion if isinstance(job.completion, dict) else {}
    defaults = build_completion_state(
        mode=str(stored.get("mode") or ""), script_adaptation=str(stored.get("script_adaptation") or "")
    )
    defaults["adaptation_pass"] = int(stored.get("adaptation_pass") or 0)
    return defaults


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
    # Explicit "what to show" per scene, keyed by 1-based scene number or scene_id.
    # Optional and additive: a job.json written before this exists simply has none, and
    # ``from_dict`` fills the default. Never spoken - the voice stage reads narration.
    visual_briefs: dict[str, dict[str, Any]] = field(default_factory=dict)
    # How far the project is allowed to go on its own when a scene has no perfect
    # material (stage Q2.2B). Optional and additive: a job.json written before this
    # field existed loads with the strict default, which is the pre-Q2.2B behaviour.
    # Keys: mode (src.assets.completion.MODE_*), script_adaptation
    # (src.content.script_engine.adaptation.ADAPT_*), adaptation_pass (int).
    completion: dict[str, Any] = field(default_factory=dict)
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
    schema_version: int = NEWS_JOB_SCHEMA_VERSION

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
        visual_briefs: dict[str, dict[str, Any]] | None = None,
        completion_mode: str = "",
        script_adaptation: str = "",
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
            visual_briefs={str(key): dict(value) for key, value in (visual_briefs or {}).items()},
            completion=build_completion_state(mode=completion_mode, script_adaptation=script_adaptation),
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
        data.setdefault("schema_version", NEWS_JOB_SCHEMA_VERSION)
        data["stages"] = {key: StageState(**value) for key, value in data.get("stages", {}).items()}
        data["localizations"] = {
            key: LocalizationState(**value) for key, value in data.get("localizations", {}).items()
        }
        # A job.json from before a field existed simply lacks it; unknown keys from a
        # newer writer are dropped rather than crashing an older reader.
        known = {field.name for field in dataclasses.fields(cls)}
        return cls(**{key: value for key, value in data.items() if key in known})

    def to_dict(self) -> dict[str, Any]:
        return asdict_clean(self)

