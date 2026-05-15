from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any

from .utils import PROJECT_ROOT, project_path, read_json
from .youtube_metadata import load_youtube_metadata


PLAN_KEYS = {
    "quote_plan": "outputs/quote_plan.json",
    "scene_plan": "outputs/scene_plan.json",
    "asset_plan": "outputs/asset_plan.json",
    "render_plan": "outputs/render_plan.json",
    "music_plan": "outputs/music_plan.json",
    "self_eval": "outputs/self_eval.json",
}


def export_obsidian_note(config: dict[str, Any]) -> Path:
    quote_plan = _read_plan(config["plans"].get("quote_plan", PLAN_KEYS["quote_plan"]))
    scene_plan = _read_plan(config["plans"].get("scene_plan", PLAN_KEYS["scene_plan"]))
    asset_plan = _read_plan(config["plans"].get("asset_plan", PLAN_KEYS["asset_plan"]))
    render_plan = _read_plan(config["plans"].get("render_plan", PLAN_KEYS["render_plan"]))
    music_plan = _read_plan(config["plans"].get("music_plan", PLAN_KEYS["music_plan"]))
    self_eval = _read_plan(PLAN_KEYS["self_eval"])
    metadata = load_youtube_metadata()
    output_video = _find_output_video(config)

    markdown = build_obsidian_markdown(
        config=config,
        quote_plan=quote_plan,
        scene_plan=scene_plan,
        asset_plan=asset_plan,
        render_plan=render_plan,
        music_plan=music_plan,
        self_eval=self_eval,
        metadata=metadata,
        output_video=output_video,
    )
    target = _resolve_note_path(config, metadata, scene_plan)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(markdown, encoding="utf-8")
    return target


def build_obsidian_markdown(
    config: dict[str, Any],
    quote_plan: dict[str, Any],
    scene_plan: dict[str, Any],
    asset_plan: dict[str, Any],
    render_plan: dict[str, Any],
    music_plan: dict[str, Any],
    self_eval: dict[str, Any],
    metadata: dict[str, Any],
    output_video: Path | None,
) -> str:
    title = metadata.get("chosen_title") or _first(metadata.get("title_variants", []), config.get("topic", "Видео"))
    scenes = scene_plan.get("scenes", [])
    final_video = output_video or Path(render_plan.get("output_path", config.get("output_filename", "")))
    write_json_links = config.get("obsidian", {}).get("write_json_links", True)

    return "\n".join(
        [
            f"# {title}",
            "",
            "## Статус",
            "Production preview",
            "",
            "## Основа",
            f"- Тема: {config.get('topic', '')}",
            f"- Формат: {config.get('video_type', '')}",
            f"- Персона / источник: {config.get('person', '')}",
            f"- Язык: {config.get('language', '')}",
            f"- Стиль: {config.get('visual_style', '')}",
            f"- Сцен: {len(scenes)}",
            f"- Длительность: {render_plan.get('duration', '')} сек.",
            f"- Итоговое видео: {_path_text(final_video)}",
            "",
            "## Описание",
            metadata.get("description", ""),
            "",
            "## Теги",
            _bullet_list(metadata.get("tags", [])),
            "",
            "## Ключевые слова",
            _bullet_list(metadata.get("keywords", [])),
            "",
            "## Идеи заголовков",
            _title_list(metadata),
            "",
            "## Thumbnail",
            f"- Идея: {metadata.get('thumbnail_idea', '')}",
            f"- Prompt: {metadata.get('thumbnail_prompt', '')}",
            "",
            "## Список сцен",
            _scene_list(scenes),
            "",
            "## Цитаты / идеи",
            _quote_list(quote_plan.get("items", [])),
            "",
            "## Ассеты",
            _asset_list(asset_plan),
            "",
            "## Музыка",
            f"- Статус: {music_plan.get('status', '')}",
            f"- Файл: {music_plan.get('path', '')}",
            f"- Громкость: {music_plan.get('volume', '')}",
            f"- Рекомендации: {', '.join(music_plan.get('recommendations', []))}",
            "",
            "## Production-планы",
            _plan_links(write_json_links),
            "",
            "## Предупреждения self-eval",
            _bullet_list(self_eval.get("warnings", [])),
            "",
            "## Проверки self-eval",
            _bullet_list(self_eval.get("checks", [])),
            "",
            "## Следующие действия",
            "- добавить озвучку",
            "- проверить цитаты",
            "- проверить авторские права",
            "- сделать thumbnail",
            "- загрузить на YouTube",
            "",
            "## Notes",
            "",
            "",
        ]
    )


def _resolve_note_path(config: dict[str, Any], metadata: dict[str, Any], scene_plan: dict[str, Any]) -> Path:
    obsidian = config.get("obsidian", {})
    vault_path = Path(obsidian.get("vault_path", ""))
    folder = obsidian.get("folder", "YouTube/Цитаты")
    fallback_to_outputs = obsidian.get("fallback_to_outputs", True)
    title = metadata.get("chosen_title") or scene_plan.get("topic", "video")
    filename = f"{datetime.now().strftime('%Y-%m-%d')} - {_slugify(title)}.md"

    if vault_path.exists() and vault_path.is_dir():
        return vault_path / folder / filename
    if fallback_to_outputs:
        return project_path("outputs/obsidian_note_preview.md")
    return PROJECT_ROOT / filename


def _find_output_video(config: dict[str, Any]) -> Path | None:
    candidates = [config.get("output_filename", ""), "outputs/final_video.mp4", "outputs/final_preview.mp4"]
    for candidate in candidates:
        if not candidate:
            continue
        path = project_path(candidate)
        if path.exists():
            return path
    return None


def _read_plan(path: str | Path) -> dict[str, Any]:
    target = project_path(path)
    if not target.exists():
        return {}
    return read_json(target)


def _path_text(value: str | Path) -> str:
    return str(value) if value else ""


def _bullet_list(items: list[Any]) -> str:
    if not items:
        return "- "
    return "\n".join(f"- {item}" for item in items)


def _title_list(metadata: dict[str, Any]) -> str:
    chosen = metadata.get("chosen_title")
    lines = []
    for title in metadata.get("title_variants", []):
        prefix = "выбранный" if title == chosen else "вариант"
        lines.append(f"- {prefix}: {title}")
    return "\n".join(lines) if lines else "- "


def _scene_list(scenes: list[dict[str, Any]]) -> str:
    lines = []
    for scene in scenes:
        lines.append(
            f"- {scene.get('scene_number')}. {scene.get('scene_type')} / {scene.get('content_type')} / "
            f"{scene.get('duration')} сек. — {scene.get('screen_text') or scene.get('title', '')}"
        )
    return "\n".join(lines) if lines else "- "


def _quote_list(items: list[dict[str, Any]]) -> str:
    lines = []
    for index, item in enumerate(items, start=1):
        lines.append(f"- {index}. [{item.get('content_type')}] {item.get('text')} — {item.get('source_note')}")
    return "\n".join(lines) if lines else "- "


def _asset_list(asset_plan: dict[str, Any]) -> str:
    lines = []
    for asset in asset_plan.get("scene_assets", []):
        lines.append(
            f"- Сцена {asset.get('scene_number')}: {asset.get('provider')} / {asset.get('status')} / {asset.get('path')}"
        )
    if not lines:
        lines.append(f"- Изображение: {asset_plan.get('image', {}).get('path', '')}")
    return "\n".join(lines)


def _plan_links(enabled: bool) -> str:
    lines = []
    for _, path in PLAN_KEYS.items():
        text = str(project_path(path)) if enabled else path
        lines.append(f"- {Path(path).name}: {text}")
    return "\n".join(lines)


def _first(items: list[Any], fallback: Any) -> Any:
    return items[0] if items else fallback


def _slugify(value: str) -> str:
    value = re.sub(r"[^\w\s.-]", "", value, flags=re.UNICODE).strip()
    value = re.sub(r"\s+", " ", value)
    return value[:90] or "video"
