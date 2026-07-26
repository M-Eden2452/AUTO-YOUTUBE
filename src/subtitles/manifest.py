"""Артефакт субтитров на диске и решение о переиспользовании (resume).

Манифест не заменяется новым: ``status``, ``language``, ``srt_path``, ``ass_path`` и
``segments`` остаются на своих местах и с тем же смыслом, потому что их читают
``src/news/final_renderer.py``, ``src/news/quality_check.py`` и
``src/news/exporter.py``. Всё остальное добавлено рядом - старый читатель просто
не видит новых ключей, а новый читатель понимает и старый файл.

Путь артефакта всегда включает ``localization_id``:
``localizations/<id>/subtitles/``. Ни при какой ошибке движок не может записать
русский SRT в папку английской версии - каталог выводится из локализации, а не из
имени файла.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import (
    FORMAT_ASS,
    FORMAT_SRT,
    SUPPORTED_FORMATS,
    TIMING_SOURCE_LEGACY_PLANNED,
    SubtitleCue,
    SubtitleResult,
)
from .serialization import subtitle_filename, write_subtitle_file

SCHEMA_VERSION = 2
ENGINE_ID = "src.subtitles.engine"

MANIFEST_FILENAME = "subtitles_manifest.json"

# --- причины resume-решения ---------------------------------------------------
RESUME_NO_ARTIFACT = "no_existing_artifact"
RESUME_COMPATIBLE = "compatible"
RESUME_PROTECTED = "protected_artifact"
RESUME_SCRIPT_CHANGED = "script_changed"
RESUME_NARRATION_CHANGED = "narration_changed"
RESUME_LANGUAGE_CHANGED = "localization_changed"
RESUME_FILES_MISSING = "artifact_files_missing"
RESUME_LEGACY_ARTIFACT = "legacy_artifact_without_metadata"
RESUME_FORMAT_MISSING = "requested_format_missing"


def subtitle_dir(project_root: str | Path, localization_id: str) -> Path:
    return Path(project_root) / "localizations" / str(localization_id) / "subtitles"


def manifest_path(project_root: str | Path, localization_id: str) -> Path:
    return subtitle_dir(project_root, localization_id) / MANIFEST_FILENAME


def artifact_paths(project_root: str | Path, localization_id: str, formats: tuple[str, ...] | list[str]) -> dict[str, Path]:
    root = subtitle_dir(project_root, localization_id)
    return {name: root / subtitle_filename(name) for name in formats if name in SUPPORTED_FORMATS}


def read_manifest(path: str | Path) -> dict[str, Any]:
    """Прочитать манифест, не падая ни на старом, ни на повреждённом файле."""
    target = Path(path)
    if not target.is_file():
        return {}
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def manifest_cues(manifest: dict[str, Any]) -> list[SubtitleCue]:
    """Cues из манифеста.

    Манифест до Q3 хранил только ``segments`` (``{start, end, text}``) без сцен и
    без языка - он читается и превращается в cues с пустым ``scene_id``, чтобы
    старый артефакт можно было хотя бы провалидировать по времени.
    """
    stored = manifest.get("cues")
    if isinstance(stored, list) and stored:
        return [SubtitleCue.from_dict(item) for item in stored if isinstance(item, dict)]
    cues: list[SubtitleCue] = []
    language = str(manifest.get("subtitle_language") or manifest.get("language") or "")
    for index, item in enumerate(manifest.get("segments") or [], start=1):
        if not isinstance(item, dict):
            continue
        try:
            start = float(item.get("start"))
            end = float(item.get("end"))
        except (TypeError, ValueError):
            continue
        cues.append(
            SubtitleCue(
                cue_id=f"legacy#{index:02d}",
                scene_id="",
                index=index,
                scene_cue_index=index,
                text=str(item.get("text") or ""),
                start_sec=start,
                end_sec=end,
                language=language,
                timing_source=str(manifest.get("timing_source") or TIMING_SOURCE_LEGACY_PLANNED),
            )
        )
    return cues


def is_protected(manifest: dict[str, Any]) -> bool:
    """Пользовательский артефакт, который перезаписывать нельзя ни при каких
    условиях. Признаётся по явному флагу в самом манифесте: сам движок его никогда
    не ставит, поставить может только человек."""
    return bool(manifest.get("protected")) or str(manifest.get("source") or "") == "user_supplied"


@dataclass(frozen=True)
class SubtitleResumeDecision:
    reuse: bool
    reason: str
    message: str
    existing: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"reuse": self.reuse, "reason": self.reason, "message": self.message}


def plan_resume(
    existing: dict[str, Any],
    result: SubtitleResult,
    *,
    project_root: str | Path = "",
    localization_id: str = "",
) -> SubtitleResumeDecision:
    """Нужно ли перегенерировать субтитры.

    Переиспользуется только полностью совместимый артефакт: та же локализация, тот
    же язык, тот же текст сценария, та же озвучка, все объявленные файлы на месте.
    Любое расхождение - перегенерация, кроме одного случая: защищённый
    пользовательский файл не перезаписывается никогда.
    """
    target_localization = localization_id or result.localization_id
    if not existing:
        return SubtitleResumeDecision(False, RESUME_NO_ARTIFACT, "Субтитров ещё нет - будут созданы.")
    if is_protected(existing):
        return SubtitleResumeDecision(
            True, RESUME_PROTECTED,
            "Артефакт помечен как пользовательский: он используется как есть и не перезаписывается.",
            existing,
        )
    if int(existing.get("schema_version") or 0) < SCHEMA_VERSION:
        return SubtitleResumeDecision(
            False, RESUME_LEGACY_ARTIFACT,
            "Существующий артефакт создан до Q3 и не хранит ссылок на сценарий и озвучку - "
            "он будет пересоздан текущим движком.",
            existing,
        )
    stored_localization = str(existing.get("localization_id") or existing.get("language") or "")
    stored_language = str(existing.get("subtitle_language") or existing.get("language") or "")
    if stored_localization != target_localization or stored_language != result.language:
        return SubtitleResumeDecision(
            False, RESUME_LANGUAGE_CHANGED,
            f"Артефакт принадлежит локализации {stored_localization!r}/{stored_language!r}, "
            f"а нужна {target_localization!r}/{result.language!r}.",
            existing,
        )
    if str(existing.get("script_fingerprint") or "") != result.script_fingerprint:
        return SubtitleResumeDecision(False, RESUME_SCRIPT_CHANGED, "Текст сценария изменился - субтитры устарели.", existing)
    if str(existing.get("narration_fingerprint") or "") != result.narration_fingerprint:
        return SubtitleResumeDecision(
            False, RESUME_NARRATION_CHANGED,
            "Озвучка изменилась (другой файл, другая длительность или другой уровень тайминга).",
            existing,
        )
    # Проверяются пути, которые объявил сам артефакт: он мог быть создан
    # совместимым вызовом с явным каталогом, и выводить путь заново нельзя.
    declared = {str(name): Path(str(path)) for name, path in (existing.get("paths") or {}).items()}
    expected = declared or artifact_paths(project_root, target_localization, result.formats)
    missing = [name for name, path in expected.items() if not path.is_file()]
    if missing:
        return SubtitleResumeDecision(
            False, RESUME_FILES_MISSING,
            f"Манифест есть, но файлов нет: {', '.join(sorted(missing))}.",
            existing,
        )
    return SubtitleResumeDecision(
        True, RESUME_COMPATIBLE,
        "Сценарий и озвучка не менялись - существующие субтитры переиспользуются.",
        existing,
    )


def build_manifest(
    result: SubtitleResult,
    *,
    paths: dict[str, Path],
    localization_id: str = "",
    include_cues: bool = True,
) -> dict[str, Any]:
    """Полный манифест. Секретов, ключей и ответов провайдеров здесь нет и быть не
    может: движок субтитров ни одного провайдера не видит."""
    localization = localization_id or result.localization_id
    srt_path = paths.get(FORMAT_SRT)
    ass_path = paths.get(FORMAT_ASS)
    manifest: dict[str, Any] = {
        # --- ключи, которые читают существующие модули; смысл не менялся ---
        "status": result.status,
        "language": result.language,
        "srt_path": str(srt_path) if srt_path else "",
        "ass_path": str(ass_path) if ass_path else "",
        "segments": result.to_segments(),
        # --- добавлено этапом Q3 ---
        "schema_version": SCHEMA_VERSION,
        "engine": ENGINE_ID,
        "localization_id": localization,
        "subtitle_language": result.language,
        "timing_source": result.timing_source,
        "scene_timeline_source": result.scene_timeline_source,
        "narration_path": result.narration_path,
        "narration_duration_sec": round(result.narration_duration_sec, 3),
        "narration_fingerprint": result.narration_fingerprint,
        "script_fingerprint": result.script_fingerprint,
        "formats": [name for name in result.formats if name in paths],
        "paths": {name: str(path) for name, path in paths.items()},
        "cue_count": len(result.cues),
        "scene_count": result.scene_count,
        "total_duration_sec": round(result.total_duration_sec, 3),
        "validation": result.validation.to_dict(),
        "policy": result.policy.to_dict(),
        "style": result.style.to_dict(),
        "warnings": list(result.warnings),
        "protected": False,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    if include_cues:
        manifest["cues"] = [cue.to_dict() for cue in result.cues]
    return manifest


@dataclass(frozen=True)
class SubtitleArtifact:
    manifest: dict[str, Any]
    manifest_path: Path
    paths: dict[str, Path]
    result: SubtitleResult | None = None
    reused: bool = False
    resume_reason: str = ""

    @property
    def status(self) -> str:
        return str(self.manifest.get("status") or "unknown")

    def to_dict(self) -> dict[str, Any]:
        return dict(self.manifest)


def write_artifact(
    result: SubtitleResult,
    *,
    project_root: str | Path | None = None,
    localization_id: str = "",
    output_dir: str | Path | None = None,
    include_cues: bool = True,
) -> SubtitleArtifact:
    """Записать SRT/ASS и манифест в папку своей локализации.

    Форматы берутся из ``result.formats`` и дополнительно фильтруются стилем
    (``save_srt``/``save_ass`` канала), поэтому канал может отказаться от одного из
    файлов, не отключая субтитры целиком.

    ``output_dir`` - для одного совместимого вызова: ``src.news.subtitles.build_subtitles``
    всегда принимал готовый каталог и продолжает его принимать. Обычный путь -
    ``project_root`` + ``localization_id``, где каталог выводится из локализации и
    перепутать две языковые версии невозможно.
    """
    localization = localization_id or result.localization_id or result.language
    if output_dir is None and project_root is None:
        raise ValueError("write_artifact requires either project_root or output_dir")
    wanted = [
        name
        for name in result.formats
        if name in SUPPORTED_FORMATS
        and (name != FORMAT_SRT or result.style.save_srt)
        and (name != FORMAT_ASS or result.style.save_ass)
    ]
    directory = Path(output_dir) if output_dir is not None else subtitle_dir(project_root, localization)
    paths = {name: directory / subtitle_filename(name) for name in wanted}
    for name, path in paths.items():
        write_subtitle_file(path, result.cues, name, style=result.style)
    manifest = build_manifest(result, paths=paths, localization_id=localization, include_cues=include_cues)
    target = directory / MANIFEST_FILENAME
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return SubtitleArtifact(manifest=manifest, manifest_path=target, paths=paths, result=result)


def duplicate_paths(manifests: list[dict[str, Any]]) -> list[str]:
    """Пути, которые объявили сразу две локализации.

    Такого быть не может, пока каталог выводится из ``localization_id``, но проверка
    дешёвая, а последствие ошибки - английский SRT поверх русского.
    """
    seen: dict[str, str] = {}
    duplicates: list[str] = []
    for manifest in manifests:
        localization = str(manifest.get("localization_id") or manifest.get("language") or "")
        for path in (manifest.get("paths") or {}).values():
            key = str(Path(str(path)).resolve()).casefold()
            if key in seen and seen[key] != localization:
                duplicates.append(str(path))
            seen.setdefault(key, localization)
    return duplicates


__all__ = [
    "ENGINE_ID",
    "MANIFEST_FILENAME",
    "RESUME_COMPATIBLE",
    "RESUME_FILES_MISSING",
    "RESUME_FORMAT_MISSING",
    "RESUME_LANGUAGE_CHANGED",
    "RESUME_LEGACY_ARTIFACT",
    "RESUME_NARRATION_CHANGED",
    "RESUME_NO_ARTIFACT",
    "RESUME_PROTECTED",
    "RESUME_SCRIPT_CHANGED",
    "SCHEMA_VERSION",
    "SubtitleArtifact",
    "SubtitleResumeDecision",
    "artifact_paths",
    "build_manifest",
    "duplicate_paths",
    "is_protected",
    "manifest_cues",
    "manifest_path",
    "plan_resume",
    "read_manifest",
    "subtitle_dir",
    "write_artifact",
]
