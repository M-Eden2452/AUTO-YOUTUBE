"""Reading each configuration layer from what already exists on disk.

Nothing here owns configuration: every function is a *reader* over an existing
component - the production catalog, ``ChannelRegistry``, ``channel_config.json`` as
``src.news.pipeline`` already reads it, ``src.audio.voice_policy.AUDIO_POLICY_DEFAULTS``,
and the two project manifests that ``src.projects.ProjectRepository`` already knows how
to tell apart. No file is written and no file format changes.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from . import keys as k
from .models import (
    SOURCE_CHANNEL_CONFIG,
    SOURCE_CHANNEL_PROFILE,
    SOURCE_ENVIRONMENT,
    SOURCE_FORMAT_POLICY,
    SOURCE_GLOBAL_DEFAULT,
    SOURCE_LOCALIZATION_OVERRIDE,
    SOURCE_PROJECT_OVERRIDE,
    SOURCE_RUNTIME_OVERRIDE,
    SOURCE_TEMPLATE_POLICY,
    ConfigLayer,
    ConfigResolutionError,
    ConfigResolutionRequest,
)

CHANNEL_PROFILE_FILENAME = "channel.json"
CHANNEL_CONFIG_FILENAME = "channel_config.json"


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _put(target: dict[str, Any], key: str, value: Any) -> None:
    """Record a layer value, skipping keys the layer simply does not mention."""
    if value is not None:
        target[key] = value


def global_default_layer() -> ConfigLayer:
    values = {
        setting.key: setting.default
        for setting in k.SETTINGS
        if not setting.is_secret and setting.default is not None
    }
    return ConfigLayer(
        source=SOURCE_GLOBAL_DEFAULT,
        origin="src/config_resolver/keys.py",
        values=values,
    )


def format_layer(format_id: str) -> ConfigLayer:
    """Frame geometry from the read-only production catalog."""
    if not format_id:
        return ConfigLayer(source=SOURCE_FORMAT_POLICY, origin="", note="format_id не задан.")

    from src.production_catalog.catalog import get_default_catalog
    from src.production_catalog.models import CatalogValidationError

    try:
        definition = get_default_catalog().formats.get(format_id)
    except CatalogValidationError as exc:
        raise ConfigResolutionError(
            f"Неизвестный format_id {format_id!r}: {exc}", reason="unknown_format"
        ) from exc
    return ConfigLayer(
        source=SOURCE_FORMAT_POLICY,
        origin=f"production_catalog:format:{definition.format_id}",
        values={
            k.KEY_WIDTH: definition.width,
            k.KEY_HEIGHT: definition.height,
            k.KEY_ASPECT_RATIO: definition.aspect_ratio,
        },
    )


def channel_profile_layer(channel_id: str, channels_dir: str | Path = "channels") -> ConfigLayer:
    """``channels/<id>/channel.json`` - the project_foundation ChannelProfile."""
    if not channel_id:
        return ConfigLayer(source=SOURCE_CHANNEL_PROFILE, origin="", note="channel_id не задан.")
    path = Path(channels_dir) / channel_id / CHANNEL_PROFILE_FILENAME
    if not path.is_file():
        return ConfigLayer(
            source=SOURCE_CHANNEL_PROFILE, origin=path.as_posix(), note="У канала нет channel.json."
        )

    from src.project_foundation.channels import ChannelRegistry
    from src.project_foundation.models import ProjectFoundationError

    try:
        profile = ChannelRegistry(channels_dir).get(channel_id)
    except (ProjectFoundationError, ValueError) as exc:
        # ChannelRegistry raises on malformed JSON and on a profile that fails its own
        # validation. Surfacing the resolver's own error type keeps the CLI's clean
        # message path working instead of leaking a JSONDecodeError traceback.
        raise ConfigResolutionError(
            f"Канал {channel_id!r}: не удалось прочитать {path.as_posix()} - {exc}",
            reason="invalid_channel_profile",
        ) from exc
    return ConfigLayer(
        source=SOURCE_CHANNEL_PROFILE,
        origin=path.as_posix(),
        values={k.KEY_LANGUAGE: profile.default_language},
    )


def channel_config_layer(channel_id: str, channels_dir: str | Path = "channels") -> ConfigLayer:
    """``channels/<id>/channel_config.json``, flattened exactly as it is written today.

    Only the ``voice``/``voice_workflow`` blocks are read by the pipeline at this
    commit (``src.news.pipeline._load_channel_voice_config`` /
    ``_load_channel_workflow_config``). Duration, resolution, fps, subtitles and music
    are read here too because the file really carries them - the resolver reports them
    with a ``no_consumer_yet`` warning rather than leaving them invisible.
    """
    if not channel_id:
        return ConfigLayer(source=SOURCE_CHANNEL_CONFIG, origin="", note="channel_id не задан.")
    path = Path(channels_dir) / channel_id / CHANNEL_CONFIG_FILENAME
    data = _read_json(path)
    if data is None:
        return ConfigLayer(
            source=SOURCE_CHANNEL_CONFIG,
            origin=path.as_posix(),
            note="У канала нет channel_config.json (или он нечитаем).",
        )

    values: dict[str, Any] = {}
    _put(values, k.KEY_LANGUAGE, data.get("language"))
    _put(values, k.KEY_TARGET_DURATION, data.get("target_duration_sec"))
    _put(values, k.KEY_MIN_DURATION, data.get("min_duration_sec"))
    _put(values, k.KEY_MAX_DURATION, data.get("max_duration_sec"))
    _put(values, k.KEY_FPS, data.get("fps"))
    resolution = data.get("resolution")
    if isinstance(resolution, dict):
        _put(values, k.KEY_WIDTH, resolution.get("width"))
        _put(values, k.KEY_HEIGHT, resolution.get("height"))
    values.update(_voice_block_values(data.get("voice")))
    values.update(_voice_workflow_values(data.get("voice_workflow")))
    subtitles = data.get("subtitles")
    if isinstance(subtitles, dict):
        _put(values, k.KEY_SUBTITLES_ENABLED, subtitles.get("enabled"))
    music = data.get("music")
    if isinstance(music, dict):
        _put(values, k.KEY_MUSIC_ENABLED, music.get("enabled"))
        _put(values, k.KEY_MUSIC_DUCKING, music.get("ducking"))
    return ConfigLayer(source=SOURCE_CHANNEL_CONFIG, origin=path.as_posix(), values=values)


def _voice_block_values(voice: Any) -> dict[str, Any]:
    """The ``voice`` block, mapped onto resolver keys the same way
    ``src.audio.voice_policy.voice_policy_from_channel_config`` maps it onto
    VoicePolicy fields - including its ``model_id`` / ``model`` alias."""
    if not isinstance(voice, dict):
        return {}
    values: dict[str, Any] = {}
    _put(values, k.KEY_VOICE_PROVIDER, voice.get("provider"))
    _put(values, k.KEY_VOICE_PROFILE, voice.get("voice_profile"))
    _put(values, k.KEY_VOICE_MODEL_ID, voice.get("model_id", voice.get("model")))
    settings = voice.get("settings")
    if isinstance(settings, dict):
        _put(values, k.KEY_VOICE_PROVIDER_SETTINGS, settings)
        _put(values, k.KEY_VOICE_SPEED, settings.get("speed"))
    return values


def _voice_workflow_values(workflow: Any) -> dict[str, Any]:
    if not isinstance(workflow, dict):
        return {}
    from src.audio.voice_policy import FALLBACK_POLICY_MANUAL_AUDIO, FALLBACK_POLICY_NONE

    values: dict[str, Any] = {}
    _put(values, k.KEY_VOICE_APPROVAL_REQUIRED, workflow.get("paid_tts_requires_approval"))
    _put(values, k.KEY_VOICE_AUDITION_REQUIRED, workflow.get("audition_requires_approval"))
    never_auto_fallback = workflow.get("never_auto_fallback_to_paid")
    if never_auto_fallback is not None:
        values[k.KEY_VOICE_FALLBACK_POLICY] = (
            FALLBACK_POLICY_NONE if never_auto_fallback else FALLBACK_POLICY_MANUAL_AUDIO
        )
    return values


def template_layer(template_id: str) -> ConfigLayer:
    """The template's own policy: what the renderer requires, not what the user prefers.

    Audio fields come from ``AUDIO_POLICY_DEFAULTS[template.audio_policy_id]``, the same
    dict ``src.news.voice_adapter.resolve_voice_policy_for_channel`` feeds into the
    template layer today. Subtitle/music capability comes from the catalog entry via
    ``src.content_creation.capabilities.describe_template_capabilities``.
    """
    if not template_id:
        return ConfigLayer(source=SOURCE_TEMPLATE_POLICY, origin="", note="template_id не задан.")

    from src.audio.voice_policy import AUDIO_POLICY_DEFAULTS
    from src.production_catalog.catalog import get_default_catalog
    from src.production_catalog.models import CatalogValidationError

    try:
        template = get_default_catalog().templates.get(template_id)
    except CatalogValidationError as exc:
        raise ConfigResolutionError(
            f"Неизвестный template_id {template_id!r}: {exc}", reason="unknown_template"
        ) from exc

    from src.content_creation.capabilities import describe_template_capabilities

    capabilities = describe_template_capabilities(template.template_id)
    audio_policy = AUDIO_POLICY_DEFAULTS.get(template.audio_policy_id or "", {})

    values: dict[str, Any] = {}
    for policy_field, key in (
        ("enabled", k.KEY_VOICE_ENABLED),
        ("required", k.KEY_VOICE_REQUIRED),
        ("provider", k.KEY_VOICE_PROVIDER),
        ("voice_profile", k.KEY_VOICE_PROFILE),
        ("model_id", k.KEY_VOICE_MODEL_ID),
        ("output_mode", k.KEY_VOICE_OUTPUT_MODE),
        ("timing_mode", k.KEY_VOICE_TIMING_MODE),
        ("approval_required", k.KEY_VOICE_APPROVAL_REQUIRED),
        ("audition_required", k.KEY_VOICE_AUDITION_REQUIRED),
        ("scene_level_generation", k.KEY_VOICE_SCENE_LEVEL),
        ("fallback_policy", k.KEY_VOICE_FALLBACK_POLICY),
        ("failure_policy", k.KEY_VOICE_FAILURE_POLICY),
        ("output_format", k.KEY_VOICE_OUTPUT_FORMAT),
        ("target_sample_rate", k.KEY_VOICE_SAMPLE_RATE),
        ("target_channels", k.KEY_VOICE_CHANNELS),
        ("speed", k.KEY_VOICE_SPEED),
        ("provider_settings", k.KEY_VOICE_PROVIDER_SETTINGS),
    ):
        _put(values, key, audio_policy.get(policy_field))
    # A template that cannot burn in subtitles or mix music decides that itself; a
    # channel asking for either cannot make the renderer able to do it.
    if not capabilities.get("subtitles_allowed", False):
        values[k.KEY_SUBTITLES_ENABLED] = False
        values[k.KEY_SUBTITLES_STYLE] = "disabled"
    if not capabilities.get("music_allowed", False):
        values[k.KEY_MUSIC_ENABLED] = False
    return ConfigLayer(
        source=SOURCE_TEMPLATE_POLICY,
        origin=f"production_catalog:template:{template.template_id}",
        values=values,
    )


def project_layer(
    project_id: str,
    projects_dir: str | Path | None = None,
    projects_fallback_dirs: tuple[str | Path, ...] | list[str | Path] = (),
) -> ConfigLayer:
    """Whichever of the two project manifests this project actually uses.

    ``src.projects.ProjectRepository`` already owns the "which kind is this" question;
    reading the raw manifest here avoids adding render fields to its normalized
    ``ProjectView``, which exists for a different purpose.
    """
    if not project_id:
        return ConfigLayer(source=SOURCE_PROJECT_OVERRIDE, origin="", note="project_id не задан.")

    from src.projects.repository import (
        PROJECT_KIND_NEWS_JOB,
        PROJECT_KIND_PROJECT_MANIFEST,
        ProjectRepository,
    )

    repository = ProjectRepository(projects_dir, fallback_roots=projects_fallback_dirs)
    kind = repository.detect_kind(project_id)
    root = repository.project_root(project_id)
    if kind == PROJECT_KIND_NEWS_JOB:
        path = root / "job.json"
    elif kind == PROJECT_KIND_PROJECT_MANIFEST:
        path = root / "project.json"
    else:
        raise ConfigResolutionError(
            f"Проект {project_id!r} не найден в "
            f"{', '.join(path.as_posix() for path in repository.projects_roots)!r} "
            "(нет ни job.json, ни project.json).",
            reason="unknown_project",
        )

    data = _read_json(path) or {}
    values: dict[str, Any] = {}
    _put(values, k.KEY_LANGUAGE, data.get("language"))
    _put(values, k.KEY_TARGET_DURATION, data.get("target_duration_sec"))
    _put(values, k.KEY_ASPECT_RATIO, data.get("aspect_ratio"))
    resolution = data.get("resolution")
    if isinstance(resolution, dict):
        _put(values, k.KEY_WIDTH, resolution.get("width"))
        _put(values, k.KEY_HEIGHT, resolution.get("height"))
    return ConfigLayer(source=SOURCE_PROJECT_OVERRIDE, origin=path.as_posix(), values=values)


def localization_layer(
    channel_id: str, language: str, channels_dir: str | Path = "channels"
) -> ConfigLayer:
    """``channel_config.json`` → ``languages.<language>``.

    This block exists in ``channels/nature_science_news_ru/channel_config.json`` and is
    read by nothing at this commit (confirmed by repo-wide search) - wiring it into the
    voice stage is stage D2. It is read here so that the layer is real and tested, and
    only for a language whose block is ``enabled``: a disabled language carries empty
    placeholder fields (``voice_id: ""``, ``model: ""``) that must not wipe the
    channel's own voice.
    """
    if not channel_id or not language:
        return ConfigLayer(
            source=SOURCE_LOCALIZATION_OVERRIDE, origin="", note="channel_id или language не задан."
        )
    path = Path(channels_dir) / channel_id / CHANNEL_CONFIG_FILENAME
    data = _read_json(path)
    languages = (data or {}).get("languages")
    block = languages.get(language) if isinstance(languages, dict) else None
    if not isinstance(block, dict):
        return ConfigLayer(
            source=SOURCE_LOCALIZATION_OVERRIDE,
            origin=path.as_posix(),
            note=f"Для языка {language!r} блока languages нет.",
        )
    if not block.get("enabled", False):
        return ConfigLayer(
            source=SOURCE_LOCALIZATION_OVERRIDE,
            origin=f"{path.as_posix()}#languages.{language}",
            note=f"Язык {language!r} выключен (enabled=false) - его настройки не применяются.",
        )
    return ConfigLayer(
        source=SOURCE_LOCALIZATION_OVERRIDE,
        origin=f"{path.as_posix()}#languages.{language}",
        values=_voice_block_values(block.get("voice")),
    )


def runtime_layer(overrides: dict[str, Any]) -> ConfigLayer:
    return ConfigLayer(
        source=SOURCE_RUNTIME_OVERRIDE,
        origin="runtime",
        values=dict(overrides or {}),
    )


def environment_layer(*, include_secrets: bool = True) -> ConfigLayer:
    """Presence of credentials, never their value.

    ``os.getenv`` is called only to take ``bool(...)`` of the result; the string is not
    stored, returned, traced or logged. ``.env`` itself is not opened here - if the
    process has not loaded it (``src.audio.tts.env.load_elevenlabs_env`` does that for
    the TTS path), a key simply reports as not configured.
    """
    if not include_secrets:
        return ConfigLayer(
            source=SOURCE_ENVIRONMENT, origin="", note="Чтение окружения отключено запросом."
        )
    values = {
        setting.key: bool((os.getenv(setting.env_var) or "").strip())
        for setting in k.SETTINGS
        if setting.is_secret and setting.env_var
    }
    return ConfigLayer(source=SOURCE_ENVIRONMENT, origin="environment", values=values)


def build_layers(request: ConfigResolutionRequest) -> tuple[ConfigLayer, ...]:
    """Every layer for one request, weakest first."""
    return (
        global_default_layer(),
        format_layer(request.format_id),
        channel_profile_layer(request.channel_id, request.channels_dir),
        channel_config_layer(request.channel_id, request.channels_dir),
        template_layer(request.template_id),
        project_layer(
            request.project_id,
            request.projects_dir,
            request.projects_fallback_dirs,
        ),
        localization_layer(request.channel_id, request.language, request.channels_dir),
        runtime_layer(request.overrides),
        environment_layer(include_secrets=request.include_secrets),
    )


__all__ = [
    "CHANNEL_CONFIG_FILENAME",
    "CHANNEL_PROFILE_FILENAME",
    "build_layers",
    "channel_config_layer",
    "channel_profile_layer",
    "environment_layer",
    "format_layer",
    "global_default_layer",
    "localization_layer",
    "project_layer",
    "runtime_layer",
    "template_layer",
]
