"""Contracts for config resolution: sources, one resolved value with its trace, and
the resolved set for a single run.

Same shape as the other foundations in this repo (``src.audio.voice_policy``,
``src.content.script_engine.models``): plain frozen dataclasses, string constants
instead of enums, ``to_dict()`` on everything that a CLI or a report may print.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .keys import SETTINGS_BY_KEY, TYPE_SECRET_PRESENCE

# --- sources -----------------------------------------------------------------
# Lowest number = weakest layer. A later layer's explicit value replaces an earlier
# one; see resolver.ConfigResolver for the full rationale of this order.
SOURCE_GLOBAL_DEFAULT = "global_default"
SOURCE_FORMAT_POLICY = "format_policy"
SOURCE_CHANNEL_PROFILE = "channel_profile"
SOURCE_CHANNEL_CONFIG = "channel_config"
SOURCE_TEMPLATE_POLICY = "template_policy"
SOURCE_PROJECT_OVERRIDE = "project_override"
SOURCE_LOCALIZATION_OVERRIDE = "localization_override"
SOURCE_RUNTIME_OVERRIDE = "runtime_override"
SOURCE_ENVIRONMENT = "environment"

SOURCE_PRIORITY: dict[str, int] = {
    SOURCE_GLOBAL_DEFAULT: 10,
    SOURCE_FORMAT_POLICY: 20,
    SOURCE_CHANNEL_PROFILE: 30,
    SOURCE_CHANNEL_CONFIG: 40,
    SOURCE_TEMPLATE_POLICY: 50,
    SOURCE_PROJECT_OVERRIDE: 60,
    SOURCE_LOCALIZATION_OVERRIDE: 70,
    SOURCE_RUNTIME_OVERRIDE: 80,
    SOURCE_ENVIRONMENT: 90,
}

SOURCES = frozenset(SOURCE_PRIORITY)

SOURCE_DISPLAY_NAMES: dict[str, str] = {
    SOURCE_GLOBAL_DEFAULT: "встроенное значение по умолчанию",
    SOURCE_FORMAT_POLICY: "политика формата",
    SOURCE_CHANNEL_PROFILE: "профиль канала (channel.json)",
    SOURCE_CHANNEL_CONFIG: "конфигурация канала (channel_config.json)",
    SOURCE_TEMPLATE_POLICY: "политика шаблона",
    SOURCE_PROJECT_OVERRIDE: "настройка проекта",
    SOURCE_LOCALIZATION_OVERRIDE: "локализация",
    SOURCE_RUNTIME_OVERRIDE: "явное указание при запуске",
    SOURCE_ENVIRONMENT: "переменная окружения",
}

# --- outcomes of one layer for one key ---------------------------------------
OUTCOME_SELECTED = "selected"  # this layer supplied the winning value
OUTCOME_OVERRIDDEN = "overridden"  # it supplied a value, a stronger layer replaced it
OUTCOME_BLANK = "blank"  # present but empty - treated as "not set"
OUTCOME_INVALID = "invalid"  # present but not coercible to the declared type

OUTCOMES = frozenset({OUTCOME_SELECTED, OUTCOME_OVERRIDDEN, OUTCOME_BLANK, OUTCOME_INVALID})

# --- warning codes ------------------------------------------------------------
WARNING_NO_CONSUMER = "no_consumer_yet"
WARNING_NORMALIZED = "value_normalized"
WARNING_INVALID_LAYER_VALUE = "invalid_layer_value"
WARNING_TEMPLATE_OVER_CHANNEL = "template_policy_overrode_channel"

REDACTED = "***"


class ConfigResolutionError(ValueError):
    """Raised for an unknown channel/template/format, or an unknown setting key."""

    def __init__(self, message: str, *, reason: str = "generic") -> None:
        super().__init__(message)
        self.reason = reason


@dataclass(frozen=True)
class ConfigLayer:
    """One source of settings, already read and flattened to resolver keys."""

    source: str
    # Where the values physically came from: a file path, a registry, a catalog id.
    origin: str
    values: dict[str, Any] = field(default_factory=dict)
    # Why the layer contributed nothing, when it did not apply at all.
    note: str = ""

    @property
    def priority(self) -> int:
        return SOURCE_PRIORITY[self.source]

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "origin": self.origin,
            "priority": self.priority,
            "keys": sorted(self.values),
            "note": self.note,
        }


@dataclass(frozen=True)
class ResolutionStep:
    """One layer's contribution to one key - the answer to "почему победил этот источник"."""

    source: str
    origin: str
    raw_value: Any
    outcome: str
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "origin": self.origin,
            "raw_value": self.raw_value,
            "outcome": self.outcome,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class ResolvedValue:
    """The final value of one setting plus everything needed to explain it.

    For a secret key (``keys.TYPE_SECRET_PRESENCE``) ``value`` is a bool meaning
    "configured / not configured" and nothing else: the resolver never reads the
    secret itself, so there is no secret in this object to leak into a manifest,
    a log or a trace.
    """

    key: str
    value: Any
    value_type: str
    source: str
    origin: str
    priority: int
    used_default: bool
    is_secret: bool
    normalized: bool = False
    warnings: tuple[str, ...] = ()
    trace: tuple[ResolutionStep, ...] = ()

    @property
    def display_value(self) -> str:
        """Always safe to print, log or paste into a report."""
        if self.is_secret:
            return "настроен" if self.value else "не настроен"
        if self.value is None or self.value == "" or self.value == {}:
            return "—"
        if isinstance(self.value, bool):
            return "да" if self.value else "нет"
        return str(self.value)

    @property
    def redacted_value(self) -> Any:
        """The value as it may appear in machine-readable output."""
        return REDACTED if self.is_secret else self.value

    def to_dict(self, *, include_trace: bool = True) -> dict[str, Any]:
        data: dict[str, Any] = {
            "key": self.key,
            "value": self.redacted_value,
            "display_value": self.display_value,
            "value_type": self.value_type,
            "resolved_from": self.source,
            "origin": self.origin,
            "priority": self.priority,
            "used_default": self.used_default,
            "is_secret": self.is_secret,
            "normalized": self.normalized,
            "warnings": list(self.warnings),
        }
        if self.is_secret:
            data["configured"] = bool(self.value)
        if include_trace:
            data["trace"] = [step.to_dict() for step in self.trace]
        return data


@dataclass(frozen=True)
class ConfigResolutionRequest:
    """What is being configured. Every field is optional: a layer whose identifiers
    are missing simply does not contribute, and the resolver says so in the trace."""

    channel_id: str = ""
    template_id: str = ""
    format_id: str = ""
    language: str = ""
    project_id: str = ""
    # Explicit values supplied by the caller (CLI flags, wizard answers). Keys are
    # resolver keys; an unknown key raises rather than being silently ignored.
    overrides: dict[str, Any] = field(default_factory=dict)
    # Injectable roots so tests never touch the real channels/ and projects/.
    channels_dir: str = "channels"
    projects_dir: str = "projects"
    # Reading the environment is opt-out so a report can be produced on a machine
    # with no .env at all without pretending keys are missing.
    include_secrets: bool = True

    def __post_init__(self) -> None:
        unknown = sorted(set(self.overrides) - set(SETTINGS_BY_KEY))
        if unknown:
            raise ConfigResolutionError(
                f"Неизвестные ключи в overrides: {', '.join(unknown)}.", reason="unknown_key"
            )
        secrets = sorted(
            key for key in self.overrides if SETTINGS_BY_KEY[key].value_type == TYPE_SECRET_PRESENCE
        )
        if secrets:
            raise ConfigResolutionError(
                f"Секреты нельзя передавать через overrides: {', '.join(secrets)}.", reason="secret_override"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "channel_id": self.channel_id,
            "template_id": self.template_id,
            "format_id": self.format_id,
            "language": self.language,
            "project_id": self.project_id,
            "overrides": dict(self.overrides),
            "channels_dir": self.channels_dir,
            "projects_dir": self.projects_dir,
            "include_secrets": self.include_secrets,
        }


@dataclass(frozen=True)
class ResolvedConfig:
    """Every known setting resolved for one request."""

    request: ConfigResolutionRequest
    values: dict[str, ResolvedValue]
    layers: tuple[ConfigLayer, ...] = ()
    warnings: tuple[str, ...] = ()

    def __contains__(self, key: str) -> bool:
        return key in self.values

    def resolved(self, key: str) -> ResolvedValue:
        value = self.values.get(key)
        if value is None:
            raise ConfigResolutionError(f"Настройка {key!r} не разрешалась.", reason="unknown_key")
        return value

    def get(self, key: str, default: Any = None) -> Any:
        """The plain value, for a consumer that does not care where it came from.

        Refuses secret keys - ask ``resolved(key).value`` for presence instead, so
        that no caller can accidentally treat this like a credential lookup.
        """
        setting = SETTINGS_BY_KEY.get(key)
        if setting is not None and setting.is_secret:
            raise ConfigResolutionError(
                f"{key!r} - секрет; резолвер не хранит его значение. "
                "Используйте resolved(key).value для признака «настроен».",
                reason="secret_access",
            )
        value = self.values.get(key)
        return default if value is None else value.value

    def source_of(self, key: str) -> str:
        return self.resolved(key).source

    def explain_rows(self) -> list[dict[str, Any]]:
        """One row per setting: «параметр → значение → откуда взято»."""
        return [
            {
                "key": value.key,
                "value": value.display_value,
                "resolved_from": value.source,
                "resolved_from_display": SOURCE_DISPLAY_NAMES.get(value.source, value.source),
                "origin": value.origin,
                "warnings": list(value.warnings),
            }
            for value in self.values.values()
        ]

    def to_dict(self, *, include_trace: bool = False) -> dict[str, Any]:
        return {
            "request": self.request.to_dict(),
            "values": {key: value.to_dict(include_trace=include_trace) for key, value in self.values.items()},
            "layers": [layer.to_dict() for layer in self.layers],
            "warnings": list(self.warnings),
        }


__all__ = [
    "OUTCOMES",
    "OUTCOME_BLANK",
    "OUTCOME_INVALID",
    "OUTCOME_OVERRIDDEN",
    "OUTCOME_SELECTED",
    "REDACTED",
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
    "WARNING_INVALID_LAYER_VALUE",
    "WARNING_NORMALIZED",
    "WARNING_NO_CONSUMER",
    "WARNING_TEMPLATE_OVER_CHANNEL",
    "ConfigLayer",
    "ConfigResolutionError",
    "ConfigResolutionRequest",
    "ResolutionStep",
    "ResolvedConfig",
    "ResolvedValue",
]
