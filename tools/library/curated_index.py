"""Курируемая локальная медиатека: проверка манифеста и запись его в runtime-индекс.

Зачем это существует. Сами файлы медиатеки не versioned, а
``assets/library/metadata/media_index.json`` ещё и в ``.gitignore``: провенанс
и права курируемых клипов иначе жили бы только на одной машине. Versioned
источник правды — ``assets/library/metadata/curated_library.json``: для каждого
клипа он держит то, что реально в кадре, откуда файл, права, и технические
параметры вместе с checksum. Этот инструмент сверяет манифест с фактическими
файлами и переносит его записи в существующий индекс.

Команды:
- ``verify`` — файл на месте, checksum/размер/длительность совпадают, решение
  ``license_policy`` для каждой записи. Без ``--deep`` checksum не считается.
- ``apply`` — пишет курируемые записи в ``media_index.json`` через канонический
  ``src.media_library``; некурируемые записи индекса сохраняются и помечаются
  ``curation_status='legacy_unreviewed'``.

Не владеет: правами (их решает ``src/assets/license_policy.py``), поиском и
скачиванием (провайдеры), схемой записи индекса (``src.media_library``).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from src.assets.frame_primitives import sha256_file
from src.assets.frame_sampling import ffprobe_media_info
from src.assets.license_policy import evaluate_asset_policy
from src.config_resolver.paths import repository_path
from src.media_library import load_media_index, register_asset, save_media_index

LIBRARY_ROOT = repository_path("assets", "library")
MANIFEST_PATH = LIBRARY_ROOT / "metadata" / "curated_library.json"
INDEX_PATH = LIBRARY_ROOT / "metadata" / "media_index.json"
DURATION_TOLERANCE_SEC = 0.5
REQUIRED_FIELDS = (
    "id",
    "type",
    "provider",
    "provider_asset_id",
    "file",
    "checksum_sha256",
    "content_ru",
    "license_name",
    "rights_status",
    "source_page_url",
    "provenance_evidence",
)


def load_manifest(path: str | Path | None = None) -> dict[str, Any]:
    target = Path(path) if path else MANIFEST_PATH
    data = json.loads(target.read_text(encoding="utf-8"))
    data.setdefault("schema_version", 1)
    data.setdefault("items", [])
    return data


def resolve_file(item: dict[str, Any], *, library_root: Path | None = None) -> Path:
    return (library_root or LIBRARY_ROOT) / str(item.get("file", ""))


def check_structure(item: dict[str, Any]) -> list[str]:
    """Поля, без которых запись не является курируемой; файлы здесь не читаются."""
    problems = [f"missing:{field}" for field in REQUIRED_FIELDS if not item.get(field)]
    if not item.get("keywords_en"):
        problems.append("missing:keywords_en")
    if not item.get("allowed_for_render"):
        problems.append("not_allowed_for_render")
    if item.get("review_required"):
        problems.append("review_required")
    return problems


def policy_decision(item: dict[str, Any], *, provider: str = "local_library") -> Any:
    """Решение прав для записи, какой её увидит provider, отдающий локальный файл."""
    return evaluate_asset_policy(as_candidate_dict(item, provider=provider))


def as_candidate_dict(item: dict[str, Any], *, provider: str = "local_library") -> dict[str, Any]:
    return {
        "asset_id": item.get("id", ""),
        "schema_version": 1,
        "provider": provider,
        "provider_asset_id": item.get("provider_asset_id", ""),
        "media_type": item.get("type", "video"),
        "source_page_url": item.get("source_page_url", ""),
        "download_url": item.get("download_url", ""),
        "license": license_block(item),
        "provenance": provenance_block(item),
        "allowed_for_render": bool(item.get("allowed_for_render")),
        "review_required": bool(item.get("review_required")),
    }


def license_block(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "license_name": item.get("license_name", ""),
        "license_url": item.get("license_url", ""),
        "provider_terms_url": item.get("provider_terms_url", ""),
        "rights_status": item.get("rights_status", ""),
        "allowed_for_render": bool(item.get("allowed_for_render")),
        "review_required": bool(item.get("review_required")),
        "attribution_text": item.get("author", ""),
    }


def provenance_block(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "provider": item.get("provider", ""),
        "provider_asset_id": item.get("provider_asset_id", ""),
        "source_page_url": item.get("source_page_url", ""),
        "download_url": item.get("download_url", ""),
        "original_filename": Path(str(item.get("file", ""))).name,
        "checksum_sha256": item.get("checksum_sha256", ""),
        "search_query": item.get("search_query", ""),
        "metadata_snapshot": {
            "provenance_evidence": item.get("provenance_evidence", ""),
            "rendition_note": item.get("rendition_note", ""),
        },
    }


def index_record(item: dict[str, Any], *, library_root: Path | None = None) -> dict[str, Any]:
    path = resolve_file(item, library_root=library_root)
    keywords = [
        *item.get("keywords_en", []),
        *item.get("keywords_ru", []),
        *item.get("themes", []),
    ]
    return {
        "schema_version": 1,
        "id": item["id"],
        "type": item.get("type", "video"),
        "provider": item.get("provider", ""),
        "provider_asset_id": item.get("provider_asset_id", ""),
        "source_url": item.get("source_page_url", ""),
        "source_page_url": item.get("source_page_url", ""),
        "download_url": item.get("download_url", ""),
        "local_path": str(path),
        "original_filename": path.name,
        "description": item.get("content_ru", ""),
        "title": item.get("content_ru", ""),
        "original_query": item.get("search_query", ""),
        "keywords": keywords,
        "tags": list(item.get("themes", [])),
        "channel_tags": [],
        "scene_tags": [],
        "width": int(item.get("width") or 0),
        "height": int(item.get("height") or 0),
        "duration": float(item.get("duration_sec") or 0.0),
        "fps": float(item.get("fps") or 0.0),
        "author": item.get("author", ""),
        "rights_status": item.get("rights_status", ""),
        "allowed_for_render": bool(item.get("allowed_for_render")),
        "review_required": bool(item.get("review_required")),
        "license": license_block(item),
        "license_name": item.get("license_name", ""),
        "license_url": item.get("license_url", ""),
        "provenance": provenance_block(item),
        "checksum_sha256": item.get("checksum_sha256", ""),
        "technical_validation": {
            "status": "passed",
            "width": int(item.get("width") or 0),
            "height": int(item.get("height") or 0),
            "duration_sec": float(item.get("duration_sec") or 0.0),
            "codec": item.get("codec", ""),
            "checked_by": "tools.library.curated_index",
        },
    }


def verify(manifest: dict[str, Any], *, deep: bool = False, library_root: Path | None = None) -> list[dict[str, Any]]:
    results = []
    seen_ids: set[str] = set()
    seen_files: set[str] = set()
    for item in manifest.get("items", []):
        problems = check_structure(item)
        item_id = str(item.get("id", ""))
        if item_id in seen_ids:
            problems.append("duplicate_id")
        seen_ids.add(item_id)
        file_key = str(item.get("file", "")).lower()
        if file_key in seen_files:
            problems.append("duplicate_file")
        seen_files.add(file_key)

        path = resolve_file(item, library_root=library_root)
        if not path.exists():
            problems.append("file_missing")
        else:
            info = ffprobe_media_info(path)
            if int(info.get("width") or 0) != int(item.get("width") or 0):
                problems.append("width_mismatch")
            if int(info.get("height") or 0) != int(item.get("height") or 0):
                problems.append("height_mismatch")
            if abs(float(info.get("duration_sec") or 0.0) - float(item.get("duration_sec") or 0.0)) > DURATION_TOLERANCE_SEC:
                problems.append("duration_mismatch")
            if deep and sha256_file(path) != str(item.get("checksum_sha256", "")):
                problems.append("checksum_mismatch")
        decision = policy_decision(item)
        results.append(
            {
                "id": item_id,
                "file": item.get("file", ""),
                "problems": problems,
                "policy_status": decision.status,
                "policy_reason": decision.reason,
            }
        )
    return results


def apply(manifest: dict[str, Any], *, index_path: str | Path | None = None, library_root: Path | None = None) -> dict[str, Any]:
    target = Path(index_path) if index_path else INDEX_PATH
    index = load_media_index(target)
    curated_paths = {
        str(resolve_file(item, library_root=library_root)).lower() for item in manifest.get("items", [])
    }
    kept = []
    for existing in index.get("items", []):
        if str(existing.get("local_path", "")).lower() in curated_paths:
            continue
        if existing.get("curation_status") != "curated":
            existing["curation_status"] = "legacy_unreviewed"
        kept.append(existing)
    index["items"] = kept
    for item in manifest.get("items", []):
        # ``curation_status`` is set on the stored record rather than passed through
        # ``index_record``: the canonical writer keeps a fixed field set, and adding a
        # bookkeeping flag to it is not this tool's call.
        register_asset(index, index_record(item, library_root=library_root))["curation_status"] = "curated"
    save_media_index(index, target)
    return index


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["verify", "apply"], nargs="?", default="verify")
    parser.add_argument("--manifest", default=None)
    parser.add_argument("--index", default=None)
    parser.add_argument("--deep", action="store_true", help="verify: also recompute every checksum")
    arguments = parser.parse_args(argv)

    manifest = load_manifest(arguments.manifest)
    results = verify(manifest, deep=arguments.deep)
    broken = [row for row in results if row["problems"]]
    blocked = [row for row in results if row["policy_status"] != "allowed"]
    print(f"curated items: {len(results)}")
    print(f"structural/technical problems: {len(broken)}")
    for row in broken[:20]:
        print(f"  {row['id']}: {','.join(row['problems'])}")
    print(f"policy allowed: {len(results) - len(blocked)}  blocked/review: {len(blocked)}")
    reasons: dict[str, int] = {}
    for row in blocked:
        reasons[row["policy_reason"]] = reasons.get(row["policy_reason"], 0) + 1
    for reason, count in sorted(reasons.items(), key=lambda pair: -pair[1]):
        print(f"  {reason}: {count}")

    if arguments.command == "apply":
        if broken:
            print("refusing to apply: fix the problems above first")
            return 1
        index = apply(manifest, index_path=arguments.index)
        print(f"index items after apply: {len(index.get('items', []))}")
    return 1 if broken else 0


if __name__ == "__main__":
    raise SystemExit(main())
