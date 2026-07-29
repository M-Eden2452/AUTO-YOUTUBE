from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.news.asset_manager import build_news_asset_manifest


def download_stock_videos_for_project(project_root: str | Path, *, max_scenes: int = 10) -> dict[str, Any]:
    load_dotenv()
    root = Path(project_root)
    visual_plan = _read_json(root / "localizations" / "ru" / "visual" / "visual_plan.json")
    limited_plan = {**visual_plan, "scenes": list(visual_plan.get("scenes", []))[:max_scenes]}
    manifest = build_news_asset_manifest(
        visual_plan=limited_plan,
        user_assets=[],
        dry_run=False,
        project_root=root,
        project_id=root.name,
    )
    _write_json(root / "assets" / "assets_manifest.json", manifest)
    _write_json(root / "assets" / "missing_assets.json", {"missing_scenes": manifest.get("missing_scenes", [])})
    return manifest


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
