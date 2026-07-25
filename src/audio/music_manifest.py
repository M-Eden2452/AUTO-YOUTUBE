"""Writes the music manifest the final renderer has always been able to read.

``src/news/final_renderer.py`` already implements a full music path - loop the
track to the video length, sidechain-compress it against the narration so speech
ducks the bed, and mix - gated on ``assets/music/music_manifest.json`` existing.
Nothing in the repository ever wrote that file, so the feature was unreachable and
the wizard had to hide the music option with a "temporarily hidden" message.

This module is that missing writer and nothing more: it validates a local audio
file, records where it came from and under what rights, and writes the manifest.
It performs no mixing, no ffmpeg call, no download and no rights lookup - music
mixing stays in the renderer, exactly where it already worked.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
MANIFEST_RELATIVE_PATH = ("assets", "music", "music_manifest.json")

# Matches src.content_creation.input_validation.SUPPORTED_MUSIC_EXTENSIONS; kept as a
# separate constant so this module does not import the application layer.
SUPPORTED_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"}

DEFAULT_VOLUME = 0.10
MIN_VOLUME = 0.0
MAX_VOLUME = 1.0

SOURCE_USER_PROVIDED = "user_provided"

# Rights for a locally supplied track cannot be verified by this code: the user
# points at a file on their own disk. The manifest records that honestly rather
# than claiming a licence it has not checked, so a later rights report can flag it.
DEFAULT_LICENSE = {
    "name": "unverified_user_supplied",
    "url": "",
    "commercial_use_status": "unknown",
    "attribution_required": False,
    "attribution_text": "",
    "verification_status": "unknown",
    "notes": "Локальный файл, предоставленный пользователем. Права не проверялись автоматически.",
}


class MusicManifestError(ValueError):
    """Raised when a music track cannot be accepted for rendering."""


@dataclass
class MusicManifest:
    path: str
    volume: float = DEFAULT_VOLUME
    ducking: bool = True
    source: str = SOURCE_USER_PROVIDED
    original_filename: str = ""
    size_bytes: int = 0
    checksum_sha256: str = ""
    license: dict[str, Any] = field(default_factory=lambda: dict(DEFAULT_LICENSE))
    schema_version: int = SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "path": self.path,
            "volume": self.volume,
            "ducking": self.ducking,
            "source": self.source,
            "original_filename": self.original_filename,
            "size_bytes": self.size_bytes,
            "checksum_sha256": self.checksum_sha256,
            "license": dict(self.license),
        }


def manifest_path(project_root: str | Path) -> Path:
    return Path(project_root).joinpath(*MANIFEST_RELATIVE_PATH)


def clamp_volume(volume: float | None) -> float:
    if volume is None:
        return DEFAULT_VOLUME
    try:
        value = float(volume)
    except (TypeError, ValueError):
        return DEFAULT_VOLUME
    return max(MIN_VOLUME, min(MAX_VOLUME, value))


def build_music_manifest(
    music_path: str | Path,
    *,
    volume: float | None = DEFAULT_VOLUME,
    ducking: bool = True,
    source: str = SOURCE_USER_PROVIDED,
    license_info: dict[str, Any] | None = None,
) -> MusicManifest:
    """Validate a local track and describe it, without writing anything."""
    path = Path(music_path)
    if not str(music_path).strip():
        raise MusicManifestError("Путь к музыкальному файлу не указан.")
    if not path.is_file():
        raise MusicManifestError(f"Музыкальный файл не найден: {path}")
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise MusicManifestError(
            f"Формат {path.suffix!r} не поддерживается. Допустимые: {', '.join(sorted(SUPPORTED_EXTENSIONS))}."
        )
    size_bytes = path.stat().st_size
    if size_bytes <= 0:
        raise MusicManifestError(f"Музыкальный файл пуст: {path}")

    from src.assets.frame_sampling import sha256_file

    return MusicManifest(
        path=str(path.resolve()),
        volume=clamp_volume(volume),
        ducking=bool(ducking),
        source=source,
        original_filename=path.name,
        size_bytes=size_bytes,
        checksum_sha256=sha256_file(path),
        license={**DEFAULT_LICENSE, **(license_info or {})},
    )


def write_music_manifest(project_root: str | Path, manifest: MusicManifest) -> Path:
    target = manifest_path(project_root)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(manifest.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target


def prepare_project_music(
    project_root: str | Path,
    music_path: str | Path,
    *,
    volume: float | None = DEFAULT_VOLUME,
    ducking: bool = True,
) -> Path:
    """Validate the track and write the manifest the renderer reads. Returns its path."""
    return write_music_manifest(project_root, build_music_manifest(music_path, volume=volume, ducking=ducking))


def read_music_manifest(project_root: str | Path) -> dict[str, Any]:
    """Tolerant reader: an absent, unreadable or pathless manifest means "no music"."""
    path = manifest_path(project_root)
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict) or not data.get("path"):
        return {}
    return data


__all__ = [
    "DEFAULT_LICENSE",
    "DEFAULT_VOLUME",
    "MusicManifest",
    "MusicManifestError",
    "build_music_manifest",
    "clamp_volume",
    "manifest_path",
    "prepare_project_music",
    "read_music_manifest",
    "write_music_manifest",
]
