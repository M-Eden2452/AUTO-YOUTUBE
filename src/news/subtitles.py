"""Адаптер News-to-Short над единым движком субтитров (``src.subtitles``).

До этапа Q3 весь движок был здесь: пять слов на кусок, деление длительности сцены
на число кусков и текст, взятый из ``on_screen_text``. Из-за последнего в кадре
висели только **первые пять слов каждой сцены** - тот же ``on_screen_text``, который
все провайдеры сценария заполняют через ``text_analysis.first_words`` (дефект W2
аудита V1). Логика переехала в ``src/subtitles/``; здесь осталась склейка с
пайплайном.

Публичная функция ``build_subtitles(script, output_dir)`` сохранила подпись и все
ключи возвращаемого манифеста (``status``, ``language``, ``srt_path``, ``ass_path``,
``segments``), потому что их читают ``final_renderer``, ``quality_check`` и
``exporter``.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from src.subtitles import (
    RESUME_PROTECTED,
    SubtitleArtifact,
    SubtitlePolicy,
    SubtitleRequest,
    SubtitleResult,
    build_subtitle_result,
    manifest_path,
    plan_resume,
    read_manifest,
    resolve_subtitle_style,
    write_artifact,
)

if TYPE_CHECKING:  # pragma: no cover - только для аннотации
    from src.localization.models import ResolvedLocalization

NEWS_FORMAT_ID = "vertical_short"


def _build_result(
    script: dict[str, Any],
    *,
    language: str,
    localization_id: str,
    subtitle_language: str = "",
    voice_manifest: dict[str, Any] | None = None,
    channel_id: str = "",
    resolution: dict[str, Any] | None = None,
    channels_dir: str = "channels",
) -> SubtitleResult:
    style = resolve_subtitle_style(
        channel_id=channel_id,
        resolution=resolution,
        channels_dir=channels_dir,
    )
    return build_subtitle_result(
        SubtitleRequest(
            script=script,
            localization_id=localization_id,
            language=language,
            subtitle_language=subtitle_language,
            voice_manifest=voice_manifest,
            policy=SubtitlePolicy.from_style(style),
            style=style,
            format_id=NEWS_FORMAT_ID,
        )
    )


def build_subtitles(script: dict[str, Any], output_dir: str | Path) -> dict[str, Any]:
    """Субтитры по одному сценарию, в заданный каталог. Подпись не менялась.

    Тайминг берётся из ``actual_duration_sec``, который в ``script.json`` записывает
    этап B1 (``src.audio.scene_timeline.apply_timeline_to_script``) после реальной
    озвучки. Если его там нет, движок честно помечает тайминг как ``legacy_planned``
    вместо того, чтобы делать вид, что субтитры совпадают с голосом.
    """
    language = str(script.get("language") or "")
    result = _build_result(script, language=language, localization_id=language)
    artifact = write_artifact(result, output_dir=output_dir, localization_id=language)
    return artifact.manifest


def build_subtitles_for_localization(
    *,
    project_root: str | Path,
    localization_id: str,
    script: dict[str, Any],
    voice_manifest: dict[str, Any] | None = None,
    channel_id: str = "",
    localization: "ResolvedLocalization | None" = None,
    visual_plan: dict[str, Any] | None = None,
    resume: bool = True,
    channels_dir: str = "channels",
) -> SubtitleArtifact:
    """Субтитры одной локализации проекта, с resume и стилем канала.

    Язык субтитров берётся из ``ResolvedLocalization`` (этап D2/E2), а не из
    ``script.json``: контракт локализации специально различает язык озвучки и язык
    субтитров. Каталог выводится из ``localization_id``, поэтому русский артефакт
    физически не может попасть в папку английской версии.

    ``resume=True``: полностью совместимый артефакт (тот же текст сценария, та же
    озвучка, та же локализация, файлы на месте) не перезаписывается. Защищённый
    пользовательский файл не перезаписывается никогда.
    """
    language = str(getattr(localization, "language", "") or localization_id)
    subtitle_language = str(getattr(localization, "subtitle_language", "") or "")
    result = _build_result(
        script,
        language=subtitle_language or language,
        localization_id=localization_id,
        subtitle_language=subtitle_language,
        voice_manifest=voice_manifest,
        channel_id=channel_id,
        resolution=(visual_plan or {}).get("resolution"),
        channels_dir=channels_dir,
    )
    existing = read_manifest(manifest_path(project_root, localization_id))
    decision = plan_resume(existing, result, project_root=project_root, localization_id=localization_id)
    # resume=False разрешает перезапись всего, кроме защищённого пользовательского
    # файла: его не перезаписывает ничто.
    if decision.reuse and (resume or decision.reason == RESUME_PROTECTED):
        return SubtitleArtifact(
            manifest=existing,
            manifest_path=manifest_path(project_root, localization_id),
            paths={name: Path(str(path)) for name, path in (existing.get("paths") or {}).items()},
            result=result,
            reused=True,
            resume_reason=decision.reason,
        )
    artifact = write_artifact(result, project_root=project_root, localization_id=localization_id)
    return SubtitleArtifact(
        manifest=artifact.manifest,
        manifest_path=artifact.manifest_path,
        paths=artifact.paths,
        result=result,
        reused=False,
        resume_reason=decision.reason,
    )


__all__ = ["NEWS_FORMAT_ID", "build_subtitles", "build_subtitles_for_localization"]
