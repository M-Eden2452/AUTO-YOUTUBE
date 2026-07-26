"""Config resolution: one place that answers «какое значение настройки здесь действует».

    resolved = resolve_config(channel_id="nature_science_news_ru",
                              template_id="fullscreen_voiceover_v1",
                              format_id="vertical_short",
                              language="ru")

    resolved.get("voice.voice_profile")        # "ru_dom"
    resolved.source_of("voice.voice_profile")  # "channel_config"
    resolved.resolved("voice.fallback_policy").trace   # почему победил именно этот слой

Not a third configuration system and not a global settings object. It owns no files,
writes nothing, and holds only the keys listed in ``keys.SETTINGS`` - each of which is
a setting that some file on disk really carries or some module really reads. Every
layer is a *reader* over an existing component: the production catalog,
``ChannelRegistry``, ``channel_config.json`` exactly as ``src.news.pipeline`` reads it,
``src.audio.voice_policy.AUDIO_POLICY_DEFAULTS``, and the two project manifests that
``src.projects.ProjectRepository`` already distinguishes.

Secrets are a separate kind of key: the resolver checks whether a credential
environment variable is set and stores that **boolean**, never the value. There is no
code path by which an API key can reach a ResolvedValue, a trace, a report or a
project manifest.

At this commit nothing in the pipeline uses the resolver - see ``resolver`` for why the
precedence order it implements is the one the code already has, and ``adapters`` for
the compatibility shims that let consumers migrate one at a time.
"""

from __future__ import annotations

from .adapters import secret_presence, to_render_settings, to_voice_policy
from .keys import (
    SECRET_KEYS,
    SETTINGS,
    SETTINGS_BY_KEY,
    TYPE_BOOL,
    TYPE_FLOAT,
    TYPE_INT,
    TYPE_SECRET_PRESENCE,
    TYPE_STR,
    VOICE_KEYS,
    SettingDefinition,
    get_setting,
    list_keys,
)
from .layers import build_layers
from .models import (
    OUTCOME_BLANK,
    OUTCOME_INVALID,
    OUTCOME_OVERRIDDEN,
    OUTCOME_SELECTED,
    REDACTED,
    SOURCE_CHANNEL_CONFIG,
    SOURCE_CHANNEL_PROFILE,
    SOURCE_DISPLAY_NAMES,
    SOURCE_ENVIRONMENT,
    SOURCE_FORMAT_POLICY,
    SOURCE_GLOBAL_DEFAULT,
    SOURCE_LOCALIZATION_OVERRIDE,
    SOURCE_PRIORITY,
    SOURCE_PROJECT_OVERRIDE,
    SOURCE_RUNTIME_OVERRIDE,
    SOURCE_TEMPLATE_POLICY,
    SOURCES,
    WARNING_INVALID_LAYER_VALUE,
    WARNING_NORMALIZED,
    WARNING_NO_CONSUMER,
    WARNING_TEMPLATE_OVER_CHANNEL,
    ConfigLayer,
    ConfigResolutionError,
    ConfigResolutionRequest,
    ResolutionStep,
    ResolvedConfig,
    ResolvedValue,
)
from .resolver import ConfigResolver, resolve_config

__all__ = [
    "OUTCOME_BLANK",
    "OUTCOME_INVALID",
    "OUTCOME_OVERRIDDEN",
    "OUTCOME_SELECTED",
    "REDACTED",
    "SECRET_KEYS",
    "SETTINGS",
    "SETTINGS_BY_KEY",
    "SOURCES",
    "SOURCE_CHANNEL_CONFIG",
    "SOURCE_CHANNEL_PROFILE",
    "SOURCE_DISPLAY_NAMES",
    "SOURCE_ENVIRONMENT",
    "SOURCE_FORMAT_POLICY",
    "SOURCE_GLOBAL_DEFAULT",
    "SOURCE_LOCALIZATION_OVERRIDE",
    "SOURCE_PRIORITY",
    "SOURCE_PROJECT_OVERRIDE",
    "SOURCE_RUNTIME_OVERRIDE",
    "SOURCE_TEMPLATE_POLICY",
    "TYPE_BOOL",
    "TYPE_FLOAT",
    "TYPE_INT",
    "TYPE_SECRET_PRESENCE",
    "TYPE_STR",
    "VOICE_KEYS",
    "WARNING_INVALID_LAYER_VALUE",
    "WARNING_NORMALIZED",
    "WARNING_NO_CONSUMER",
    "WARNING_TEMPLATE_OVER_CHANNEL",
    "ConfigLayer",
    "ConfigResolutionError",
    "ConfigResolutionRequest",
    "ConfigResolver",
    "ResolutionStep",
    "ResolvedConfig",
    "ResolvedValue",
    "SettingDefinition",
    "build_layers",
    "get_setting",
    "list_keys",
    "resolve_config",
    "secret_presence",
    "to_render_settings",
    "to_voice_policy",
]
