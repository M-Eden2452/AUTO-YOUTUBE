from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

from .image_tools import create_person_placeholder
from .utils import project_path
from .video_asset_engine import build_documentary_asset_plan


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
REQUEST_TIMEOUT = 20


def build_asset_plan(config: dict[str, Any], scene_plan: dict[str, Any], refresh: bool = False) -> dict[str, Any]:
    if config.get("video_task"):
        return build_documentary_asset_plan(config, scene_plan, refresh=refresh)

    load_dotenv()
    image_assets = _collect_scene_assets(config, scene_plan, refresh=refresh)
    person_image_path, person_image_status = find_person_image(config["person"], config)
    music_path = project_path(config["music_path"])
    music_status = "найдено" if music_path.exists() else "нет_музыки_рендер_без_звука"

    return {
        "person": config["person"],
        "image": {
            "path": str(person_image_path),
            "status": person_image_status,
            "query": f"портрет {config['person']}",
        },
        "scene_assets": image_assets,
        "music": {
            "path": str(music_path),
            "status": music_status,
            "volume": float(config.get("music_volume", 0.18)),
        },
        "broll": image_assets,
        "intro_image": {
            "enabled": False,
            "status": "зарезервировано_для_будущей_openai_генерации_изображений",
        },
        "warnings": _asset_warnings(image_assets),
    }


def find_person_image(person: str, config: dict[str, Any]) -> tuple[Path, str]:
    image_dir = project_path("assets/images")
    image_dir.mkdir(parents=True, exist_ok=True)
    tokens = [part.lower() for part in person.replace("-", " ").split() if part]
    placeholder = image_dir / "jordan_peterson_placeholder.jpg"

    for candidate in image_dir.iterdir():
        if not candidate.is_file() or candidate.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        if candidate.resolve() == placeholder.resolve():
            continue
        name = candidate.stem.lower()
        if all(token in name for token in tokens) or any(token in name for token in tokens):
            return candidate, "найдено_локально"

    create_person_placeholder(person, placeholder, config)
    return placeholder, "создана_placeholder_картинка"


def _collect_scene_assets(config: dict[str, Any], scene_plan: dict[str, Any], refresh: bool) -> list[dict[str, Any]]:
    if config.get("dev_mode", False):
        return []

    assets_dir = project_path("assets/images/generated")
    assets_dir.mkdir(parents=True, exist_ok=True)
    assets: list[dict[str, Any]] = []
    pexels_key = os.getenv("PEXELS_API_KEY")
    pixabay_key = os.getenv("PIXABAY_API_KEY")
    scenes = scene_plan.get("scenes", [])

    for scene in scenes:
        query = scene.get("image_query") or "dark cinematic library"
        scene_number = int(scene.get("scene_number", len(assets) + 1))
        existing = _existing_scene_asset(assets_dir, scene_number)
        if existing and not refresh:
            assets.append(_asset_entry(scene_number, query, existing, "локальный_кэш", "найдено"))
            continue

        downloaded = None
        if pexels_key and config.get("pexels_search", {}).get("enabled", True):
            downloaded = _download_from_pexels(pexels_key, query, assets_dir, scene_number)
        if not downloaded and pixabay_key and config.get("pixabay_search", {}).get("enabled", True):
            downloaded = _download_from_pixabay(pixabay_key, query, assets_dir, scene_number)

        if downloaded:
            assets.append(downloaded)
        else:
            fallback = _create_scene_placeholder(scene, assets_dir / f"scene_{scene_number:02d}_placeholder.jpg", config)
            assets.append(_asset_entry(scene_number, query, fallback, "placeholder", "создан_fallback"))

    return assets


def _download_from_pexels(api_key: str, query: str, assets_dir: Path, scene_number: int) -> dict[str, Any] | None:
    headers = {"Authorization": api_key}
    params = {"query": query, "orientation": "landscape", "per_page": 5}
    try:
        response = requests.get("https://api.pexels.com/v1/search", headers=headers, params=params, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        photos = response.json().get("photos", [])
        for photo in photos:
            url = photo.get("src", {}).get("large2x") or photo.get("src", {}).get("large")
            if not url:
                continue
            target = assets_dir / f"scene_{scene_number:02d}_pexels_{photo.get('id', 'image')}.jpg"
            if _download_file(url, target):
                return _asset_entry(scene_number, query, target, "pexels", "скачано", photo.get("url", ""))
    except requests.RequestException:
        return None
    return None


def _download_from_pixabay(api_key: str, query: str, assets_dir: Path, scene_number: int) -> dict[str, Any] | None:
    params = {
        "key": api_key,
        "q": query,
        "image_type": "photo",
        "orientation": "horizontal",
        "safesearch": "true",
        "per_page": 8,
    }
    try:
        response = requests.get("https://pixabay.com/api/", params=params, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        hits = response.json().get("hits", [])
        for hit in hits:
            url = hit.get("largeImageURL") or hit.get("webformatURL")
            if not url:
                continue
            target = assets_dir / f"scene_{scene_number:02d}_pixabay_{hit.get('id', 'image')}.jpg"
            if _download_file(url, target):
                return _asset_entry(scene_number, query, target, "pixabay", "скачано", hit.get("pageURL", ""))
    except requests.RequestException:
        return None
    return None


def _download_file(url: str, target: Path) -> bool:
    try:
        with requests.get(url, stream=True, timeout=REQUEST_TIMEOUT) as response:
            response.raise_for_status()
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=1024 * 128):
                    if chunk:
                        handle.write(chunk)
        return target.exists() and target.stat().st_size > 0
    except requests.RequestException:
        return False


def _existing_scene_asset(assets_dir: Path, scene_number: int) -> Path | None:
    for candidate in sorted(assets_dir.glob(f"scene_{scene_number:02d}_*.jpg")):
        if candidate.exists() and candidate.stat().st_size > 0:
            return candidate
    return None


def _create_scene_placeholder(scene: dict[str, Any], output_path: Path, config: dict[str, Any]) -> Path:
    text = scene.get("image_query") or scene.get("background_mood") or "dark cinematic"
    create_person_placeholder(text, output_path, config)
    return output_path


def _asset_entry(
    scene_number: int,
    query: str,
    path: Path,
    provider: str,
    status: str,
    source_url: str = "",
) -> dict[str, Any]:
    return {
        "scene_number": scene_number,
        "query": query,
        "provider": provider,
        "status": status,
        "path": str(path),
        "source_url": source_url,
    }


def _asset_warnings(assets: list[dict[str, Any]]) -> list[str]:
    missing = [asset for asset in assets if asset.get("provider") == "placeholder"]
    if not missing:
        return []
    return [f"Для {len(missing)} сцен использованы placeholder-ассеты."]
