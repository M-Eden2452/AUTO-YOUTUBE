from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def export_asset_sources(*, project_root: str | Path, assets_manifest: dict[str, Any]) -> dict[str, str]:
    from src.assets.completion import read_assembly

    root = Path(project_root)
    output_dir = root / "assets"
    output_dir.mkdir(parents=True, exist_ok=True)
    assets: list[dict[str, Any]] = []
    for scene in assets_manifest.get("scenes", []):
        if not isinstance(scene, dict):
            continue
        assembly = read_assembly(
            scene,
            scene_duration_sec=float(scene.get("required_duration_sec") or 0.0),
        )
        assets.extend(
            _source_record(
                slot.selected_asset,
                str(scene.get("scene_id") or ""),
                slot_id=slot.slot_id,
            )
            for slot in assembly.slots
            if slot.selected_asset
        )
    assets = [asset for asset in assets if asset.get("provider")]
    sources_json = output_dir / "sources.json"
    attribution_md = output_dir / "ATTRIBUTION.md"
    youtube_sources_txt = output_dir / "youtube_sources.txt"
    _write_json(sources_json, {"schema_version": 1, "assets": assets})
    attribution_md.write_text(_attribution_markdown(assets), encoding="utf-8")
    youtube_sources_txt.write_text(_youtube_sources_text(assets), encoding="utf-8")
    return {
        "sources_json": str(sources_json),
        "attribution_md": str(attribution_md),
        "youtube_sources_txt": str(youtube_sources_txt),
    }


def _source_record(asset: dict[str, Any], scene_id: str, *, slot_id: str = "") -> dict[str, Any]:
    license_data = asset.get("license") if isinstance(asset.get("license"), dict) else {}
    policy = asset.get("policy_decision") if isinstance(asset.get("policy_decision"), dict) else {}
    source_page = asset.get("source_page_url") or asset.get("source_page") or asset.get("source_url") or ""
    local_name = Path(str(asset.get("local_path") or asset.get("path") or asset.get("downloaded_path") or "")).name
    record = {
        "provider": asset.get("provider", ""),
        "source_page": source_page,
        "author": asset.get("author_name") or asset.get("author") or "",
        "license_name": license_data.get("license_name") or asset.get("license_name") or "",
        "license_url": license_data.get("license_url") or asset.get("license_url") or "",
        "attribution_text": license_data.get("attribution_text") or asset.get("attribution_text") or "",
        "modification_notice": "Modified for video edit." if policy.get("modification_notice_required") else "",
        "selected_filename": local_name or asset.get("original_filename", ""),
        "project_id": asset.get("project_id") or (asset.get("provenance") or {}).get("project_id", ""),
        "scene_id": asset.get("scene_id") or scene_id,
        "slot_id": slot_id,
    }
    if record["provider"] == "nasa_images" and not record["attribution_text"]:
        record["attribution_text"] = "Source: NASA"
    return record


def _attribution_markdown(assets: list[dict[str, Any]]) -> str:
    lines = ["# Attribution", ""]
    for asset in assets:
        provider = asset["provider"]
        title = f"{asset['scene_id']} - {provider}"
        lines.append(f"## {title}")
        credit = asset.get("attribution_text") or _credit_line(asset)
        if credit:
            lines.append(f"- Credit: {credit}")
        if asset.get("source_page"):
            lines.append(f"- Source: {asset['source_page']}")
        if asset.get("license_name"):
            license_line = asset["license_name"]
            if asset.get("license_url"):
                license_line += f" ({asset['license_url']})"
            lines.append(f"- License: {license_line}")
        if asset.get("modification_notice"):
            lines.append(f"- Modification notice: {asset['modification_notice']}")
        if provider == "nasa_images":
            lines.append("- NASA is identified as the source; this does not imply NASA endorsement.")
        if provider == "envato_manual":
            lines.append("- Envato license certificate is retained locally in project metadata and is not published here.")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _youtube_sources_text(assets: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for asset in assets:
        provider = asset["provider"]
        if provider == "envato_manual":
            if asset.get("source_page"):
                lines.append(f"Envato item used under project registration: {asset['source_page']}")
            continue
        credit = asset.get("attribution_text") or _credit_line(asset)
        parts = [part for part in [credit, asset.get("license_name"), asset.get("license_url"), asset.get("source_page")] if part]
        if provider == "nasa_images":
            parts.insert(0, "Source: NASA")
            parts.append("No NASA endorsement is implied.")
        if parts:
            lines.append(" | ".join(dict.fromkeys(parts)))
    return "\n".join(lines) + ("\n" if lines else "")


def _credit_line(asset: dict[str, Any]) -> str:
    author = asset.get("author") or ""
    provider = asset.get("provider") or ""
    if author and provider:
        return f"{author} via {provider}"
    return author or provider


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
