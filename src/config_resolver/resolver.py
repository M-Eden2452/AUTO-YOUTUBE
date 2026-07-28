"""ConfigResolver: for one run, what every setting is and why.

Precedence, weakest first::

    global_default → format_policy → channel_profile → channel_config
        → template_policy → project_override → localization_override
        → runtime_override        (+ environment, secrets only)

Two things about this order differ from the sketch in
``docs/handoff/PRODUCT_VISION_AND_ROADMAP.md`` ("Бриф 5"), and both are deliberate:

* **template_policy sits above the channel layers, not below them.** That is what the
  code does today: ``src.audio.voice_policy.resolve_voice_policy`` merges
  ``channel_defaults`` first and ``template_defaults`` second, so the template wins.
  Putting the channel above it would silently change voice behaviour for
  ``nature_science_news_ru`` (its ``never_auto_fallback_to_paid: true`` currently loses
  to the template's ``fallback_policy: manual_audio``), and D1 must not change
  behaviour. The conflict is surfaced instead: whenever the template really did
  override a channel value, that value carries a
  ``template_policy_overrode_channel`` warning.
* **There is a runtime layer above localization.** An explicit CLI flag beats every
  file today (``request.target_duration_sec or ... or 55``,
  ``load_voice_profile_for_channel(profile_override=...)``), and it keeps that place.

This module reads; it does not write and it is not wired into any pipeline stage. At
this commit its only consumer is ``content_creation.cli channels show --explain``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from . import keys as k
from .layers import CHANNEL_CONFIG_FILENAME, CHANNEL_PROFILE_FILENAME, build_layers
from .models import (
    OUTCOME_BLANK,
    OUTCOME_INVALID,
    OUTCOME_OVERRIDDEN,
    OUTCOME_SELECTED,
    SOURCE_CHANNEL_CONFIG,
    SOURCE_CHANNEL_PROFILE,
    SOURCE_GLOBAL_DEFAULT,
    SOURCE_PRIORITY,
    SOURCE_TEMPLATE_POLICY,
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

_TRUE_STRINGS = frozenset({"1", "true", "yes", "on", "да"})
_FALSE_STRINGS = frozenset({"0", "false", "no", "off", "нет", ""})

CHANNEL_LAYER_SOURCES = (SOURCE_CHANNEL_PROFILE, SOURCE_CHANNEL_CONFIG)


class _Unset:
    """Distinguishes "this layer said nothing" from "this layer said None"."""


UNSET = _Unset()


def _coerce(value: Any, value_type: str) -> Any:
    """Normalize a raw layer value to the declared type, or raise ValueError.

    Blank strings are *not* handled here - the caller treats them as "not set", the
    same way every existing ``a or b or default`` chain in this codebase does.
    """
    if value_type == k.TYPE_SECRET_PRESENCE or value_type == k.TYPE_BOOL:
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return bool(value)
        text = str(value).strip().lower()
        if text in _TRUE_STRINGS:
            return True
        if text in _FALSE_STRINGS:
            return False
        raise ValueError(f"{value!r} не похоже на логическое значение")
    if value_type == k.TYPE_INT:
        if isinstance(value, bool):
            raise ValueError(f"{value!r} - логическое значение, ожидалось целое")
        return int(value)
    if value_type == k.TYPE_FLOAT:
        if isinstance(value, bool):
            raise ValueError(f"{value!r} - логическое значение, ожидалось число")
        return float(value)
    if value_type == k.TYPE_DICT:
        if not isinstance(value, dict):
            raise ValueError(f"{value!r} - ожидался словарь настроек")
        return dict(value)
    return str(value)


def _is_blank(value: Any, value_type: str) -> bool:
    """An empty string or an empty settings block means "не задано", the same way every
    existing ``a or b or default`` chain in this codebase reads it. This is what keeps a
    disabled language's placeholder ``voice_id: ""`` from wiping the channel's voice."""
    if value is None:
        return True
    if value_type == k.TYPE_STR:
        return not str(value).strip()
    if value_type == k.TYPE_DICT:
        return not value
    return False


class ConfigResolver:
    """Answers "какое значение здесь действует и откуда оно" for one request.

    Deliberately not a singleton and deliberately not a bag of every setting in the
    project: it is constructed per request, knows only the keys in ``keys.SETTINGS``,
    and holds no state between calls.
    """

    def __init__(self, request: ConfigResolutionRequest | None = None) -> None:
        self.request = request or ConfigResolutionRequest()

    def resolve(self) -> ResolvedConfig:
        request = self.request
        self._require_known_channel(request)
        layers = build_layers(request)
        values = {
            setting.key: self._resolve_one(setting, layers)
            for setting in k.SETTINGS
        }
        warnings = self._config_warnings(layers, values)
        return ResolvedConfig(request=request, values=values, layers=layers, warnings=warnings)

    # -- one key ------------------------------------------------------------

    def _resolve_one(self, setting: k.SettingDefinition, layers: tuple[ConfigLayer, ...]) -> ResolvedValue:
        steps: list[ResolutionStep] = []
        winner: ConfigLayer | None = None
        winner_step: int = -1
        winning_value: Any = UNSET
        normalized = False
        warnings: list[str] = []

        for layer in layers:
            if setting.key not in layer.values:
                continue
            raw = layer.values[setting.key]
            if _is_blank(raw, setting.value_type):
                steps.append(
                    ResolutionStep(
                        source=layer.source,
                        origin=layer.origin,
                        raw_value=raw,
                        outcome=OUTCOME_BLANK,
                        detail="Пустое значение считается «не задано».",
                    )
                )
                continue
            try:
                coerced = _coerce(raw, setting.value_type)
            except (TypeError, ValueError) as exc:
                warnings.append(WARNING_INVALID_LAYER_VALUE)
                steps.append(
                    ResolutionStep(
                        source=layer.source,
                        origin=layer.origin,
                        raw_value=raw,
                        outcome=OUTCOME_INVALID,
                        detail=str(exc),
                    )
                )
                continue
            if winner is not None:
                previous = steps[winner_step]
                steps[winner_step] = ResolutionStep(
                    source=previous.source,
                    origin=previous.origin,
                    raw_value=previous.raw_value,
                    outcome=OUTCOME_OVERRIDDEN,
                    detail=f"Перекрыт слоем {layer.source} (приоритет {layer.priority}).",
                )
                if previous.source in CHANNEL_LAYER_SOURCES and layer.source == SOURCE_TEMPLATE_POLICY:
                    warnings.append(WARNING_TEMPLATE_OVER_CHANNEL)
            winner = layer
            winning_value = coerced
            normalized = coerced != raw
            winner_step = len(steps)
            steps.append(
                ResolutionStep(
                    source=layer.source,
                    origin=layer.origin,
                    raw_value=raw,
                    outcome=OUTCOME_SELECTED,
                    detail=f"Наивысший приоритет среди заданных ({layer.priority}).",
                )
            )

        if winner is None:
            value = setting.default
            source = SOURCE_GLOBAL_DEFAULT
            origin = "src/config_resolver/keys.py"
            used_default = True
        else:
            value = winning_value
            source = winner.source
            origin = winner.origin
            used_default = winner.source == SOURCE_GLOBAL_DEFAULT

        if normalized:
            warnings.append(WARNING_NORMALIZED)
        if not setting.consumers:
            warnings.append(WARNING_NO_CONSUMER)

        return ResolvedValue(
            key=setting.key,
            value=value,
            value_type=setting.value_type,
            source=source,
            origin=origin,
            priority=SOURCE_PRIORITY[source],
            used_default=used_default,
            is_secret=setting.is_secret,
            normalized=normalized,
            warnings=tuple(dict.fromkeys(warnings)),
            trace=tuple(steps),
        )

    # -- request-level checks ------------------------------------------------

    @staticmethod
    def _require_known_channel(request: ConfigResolutionRequest) -> None:
        """A channel_id that names nothing on disk is an error, not an empty layer."""
        if not request.channel_id:
            return
        channel_dir = Path(request.channels_dir) / request.channel_id
        if (channel_dir / CHANNEL_PROFILE_FILENAME).is_file() or (
            channel_dir / CHANNEL_CONFIG_FILENAME
        ).is_file():
            return
        raise ConfigResolutionError(
            f"Неизвестный канал {request.channel_id!r}: в "
            f"{channel_dir.as_posix()!r} нет ни {CHANNEL_PROFILE_FILENAME}, ни {CHANNEL_CONFIG_FILENAME}.",
            reason="unknown_channel",
        )

    @staticmethod
    def _config_warnings(
        layers: tuple[ConfigLayer, ...], values: dict[str, ResolvedValue]
    ) -> tuple[str, ...]:
        warnings: list[str] = []
        for layer in layers:
            if layer.note:
                warnings.append(f"{layer.source}: {layer.note}")
        unread = sorted(
            key for key, value in values.items() if WARNING_NO_CONSUMER in value.warnings
        )
        if unread:
            warnings.append(
                "Настройки без потребителей в коде (значение разрешается, но ни на что "
                f"не влияет): {', '.join(unread)}."
            )
        return tuple(warnings)


def resolve_config(
    *,
    channel_id: str = "",
    template_id: str = "",
    format_id: str = "",
    language: str = "",
    project_id: str = "",
    overrides: dict[str, Any] | None = None,
    channels_dir: str | Path | None = None,
    projects_dir: str | Path | None = None,
    projects_fallback_dirs: tuple[str | Path, ...] | list[str | Path] = (),
    include_secrets: bool = True,
) -> ResolvedConfig:
    """Convenience entry point - the same thing as ``ConfigResolver(request).resolve()``."""
    request = ConfigResolutionRequest(
        channel_id=channel_id,
        template_id=template_id,
        format_id=format_id,
        language=language,
        project_id=project_id,
        overrides=dict(overrides or {}),
        channels_dir=str(channels_dir or ""),
        projects_dir=str(projects_dir or ""),
        projects_fallback_dirs=tuple(str(path) for path in projects_fallback_dirs),
        include_secrets=include_secrets,
    )
    return ConfigResolver(request).resolve()


__all__ = ["CHANNEL_LAYER_SOURCES", "ConfigResolver", "resolve_config"]
