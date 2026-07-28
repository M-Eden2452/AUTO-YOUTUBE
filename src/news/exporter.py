from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from src.assets.attribution_export import export_asset_sources


def export_localization(
    *,
    project_root: str | Path,
    language: str,
    job: dict[str, Any],
    script: dict[str, Any],
    research: dict[str, Any],
    assets_manifest: dict[str, Any],
    quality_report: dict[str, Any],
) -> dict[str, Any]:
    root = Path(project_root)
    output = root / "localizations" / language / "output"
    output.mkdir(parents=True, exist_ok=True)
    description_path = output / "description.txt"
    sources_path = output / "sources.json"
    manifest_path = output / "project_manifest.json"
    description_path.write_text(script.get("description", "") + "\n", encoding="utf-8")
    sources = {
        "fact_sources": research.get("claims", []),
        "asset_sources": assets_manifest.get("scenes", []),
        "provider_errors": assets_manifest.get("provider_errors", []),
    }
    _write_json(sources_path, sources)
    attribution_exports = export_asset_sources(project_root=root, assets_manifest=assets_manifest)
    subtitles_root = root / "localizations" / language / "subtitles"
    for name in ("subtitles.srt", "subtitles.ass"):
        source = subtitles_root / name
        if source.exists():
            shutil.copyfile(source, output / name)
    outputs = _render_outputs(root)
    manifest = {
        "job_id": job.get("job_id"),
        "mode": job.get("mode"),
        "channel_id": job.get("channel_id"),
        "language": language,
        "status": quality_report.get("status"),
        "description_path": str(description_path),
        "sources_path": str(sources_path),
        "asset_sources_path": attribution_exports["sources_json"],
        "attribution_path": attribution_exports["attribution_md"],
        "youtube_sources_path": attribution_exports["youtube_sources_txt"],
        "quality_report": quality_report,
        "outputs": outputs,
    }
    _write_json(manifest_path, manifest)
    return {
        "status": "completed",
        "manifest_path": str(manifest_path),
        "sources_path": str(sources_path),
        "asset_sources_path": attribution_exports["sources_json"],
        "attribution_path": attribution_exports["attribution_md"],
        "youtube_sources_path": attribution_exports["youtube_sources_txt"],
    }


def _render_outputs(root: Path) -> dict[str, str]:
    defaults = {
        "master_1080x1920": "",
        "youtube_shorts": "",
        "instagram_reels": "",
        "facebook_reels": "",
        "no_subtitles": "",
    }
    render_manifest_path = root / "render" / "final_render_manifest.json"
    if not render_manifest_path.is_file():
        return defaults
    try:
        render_manifest = json.loads(render_manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return defaults
    rendered = render_manifest.get("outputs")
    if not isinstance(rendered, dict):
        return defaults
    outputs = {**defaults, **{str(key): str(value or "") for key, value in rendered.items()}}
    draft = outputs.get("draft_1080x1920", "")
    if draft:
        outputs["youtube_shorts"] = outputs.get("youtube_shorts") or draft
        outputs["instagram_reels"] = outputs.get("instagram_reels") or draft
        outputs["facebook_reels"] = outputs.get("facebook_reels") or draft
        outputs["no_subtitles"] = outputs.get("no_subtitles") or outputs.get("draft_no_subtitles", "")
    return outputs


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
