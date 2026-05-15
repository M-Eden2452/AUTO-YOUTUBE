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
    "self_eval": "outputs/self_eval.json",
}


def export_obsidian_note(config: dict[str, Any]) -> Path:
    quote_plan = _read_plan(config["plans"].get("quote_plan", PLAN_KEYS["quote_plan"]))
    scene_plan = _read_plan(config["plans"].get("scene_plan", PLAN_KEYS["scene_plan"]))
    asset_plan = _read_plan(config["plans"].get("asset_plan", PLAN_KEYS["asset_plan"]))
    render_plan = _read_plan(config["plans"].get("render_plan", PLAN_KEYS["render_plan"]))
    self_eval = _read_plan(PLAN_KEYS["self_eval"])
    metadata = load_youtube_metadata()
    output_video = _find_output_video()

    markdown = build_obsidian_markdown(
        config=config,
        quote_plan=quote_plan,
        scene_plan=scene_plan,
        asset_plan=asset_plan,
        render_plan=render_plan,
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
    self_eval: dict[str, Any],
    metadata: dict[str, Any],
    output_video: Path | None,
) -> str:
    scene = _first(scene_plan.get("scenes", []), {})
    quote = _first(quote_plan.get("quotes", []), {})
    title = _first(metadata.get("title_variants", []), f"{config.get('person', 'Видео с цитатой')} Превью")
    duration = scene.get("duration") or render_plan.get("duration") or config.get("scene_duration", "")

    image = asset_plan.get("image", {})
    music = asset_plan.get("music", {})
    broll = asset_plan.get("broll", [])
    final_video = output_video or Path(render_plan.get("output_path", config.get("output_filename", "")))
    write_json_links = config.get("obsidian", {}).get("write_json_links", True)

    return "\n".join(
        [
            f"# {title}",
            "",
            "## Статус",
            "Превью",
            "",
            "## Основа",
            f"- Формат: {config.get('video_type', '')}",
            f"- Тема: {config.get('topic', '')}",
            f"- Персона / источник: {scene.get('person') or config.get('person', '')}",
            f"- Язык: {config.get('language', '')}",
            f"- Стиль: {config.get('visual_style', '')}",
            f"- Длительность: {duration} сек.",
            f"- Итоговое видео: {_path_text(final_video)}",
            "",
            "## Цитата / текст",
            quote.get("quote_ru") or quote.get("quote", scene.get("quote", "")),
            "",
            "## Идеи заголовков",
            _bullet_list(metadata.get("title_variants", [])),
            "",
            "## Метаданные YouTube",
            f"- Описание: {metadata.get('description', '')}",
            f"- Теги: {', '.join(metadata.get('tags', []))}",
            f"- Ключевые слова: {', '.join(metadata.get('keywords', []))}",
            f"- Идея обложки: {metadata.get('thumbnail_idea', '')}",
            "",
            "## Визуальный стиль",
            f"- Общий стиль: {config.get('visual_style', '')}",
            f"- Стиль изображения: {config.get('image_style', '')}",
            f"- Стиль интро: {config.get('intro_style', '')}",
            f"- Макет: {config.get('layout', '')}",
            f"- Шрифт: {config.get('font_path', '')}",
            f"- Музыка: {_path_text(music.get('path', ''))}",
            "",
            "## Ассеты",
            f"- Изображения: {_path_text(image.get('path', ''))}",
            f"- B-roll: {_asset_list(broll)}",
            f"- Музыка: {_path_text(music.get('path', ''))}",
            f"- Финальное видео: {_path_text(final_video)}",
            "",
            "## Production-планы",
            _plan_links(write_json_links),
            "",
            "## Следующие действия",
            "- улучшить цитаты",
            "- подобрать картинки",
            "- добавить интро",
            "- добавить voice-over",
            "- сделать production render",
            "",
            "## Заметки",
            "",
            "",
            "## Self-eval",
            _bullet_list(self_eval.get("checks", [])),
            "",
            "## Предупреждения",
            _bullet_list(self_eval.get("warnings", [])),
            "",
        ]
    )


def _resolve_note_path(config: dict[str, Any], metadata: dict[str, Any], scene_plan: dict[str, Any]) -> Path:
    obsidian = config.get("obsidian", {})
    vault_path = Path(obsidian.get("vault_path", ""))
    folder = obsidian.get("folder", "YouTube/Цитаты")
    fallback_to_outputs = obsidian.get("fallback_to_outputs", True)
    title = _first(metadata.get("title_variants", []), scene_plan.get("topic", "quote video"))
    filename = f"{datetime.now().strftime('%Y-%m-%d')} - {_slugify(title)}.md"

    if vault_path.exists() and vault_path.is_dir():
        return vault_path / folder / filename
    if fallback_to_outputs:
        return project_path("outputs/obsidian_note_preview.md")
    return PROJECT_ROOT / filename


def _find_output_video() -> Path | None:
    for candidate in ("outputs/final_preview.mp4", "outputs/final_video.mp4"):
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
    if not value:
        return ""
    return str(value)


def _bullet_list(items: list[Any]) -> str:
    if not items:
        return "- "
    return "\n".join(f"- {item}" for item in items)


def _asset_list(items: list[Any]) -> str:
    if not items:
        return "Пока нет"
    return ", ".join(str(item) for item in items)


def _plan_links(enabled: bool) -> str:
    lines = []
    for label, path in PLAN_KEYS.items():
        text = str(project_path(path)) if enabled else path
        lines.append(f"- {Path(path).name}: {text}")
    return "\n".join(lines)


def _first(items: list[Any], fallback: Any) -> Any:
    return items[0] if items else fallback


def _slugify(value: str) -> str:
    value = re.sub(r"[^\w\s.-]", "", value, flags=re.UNICODE).strip()
    value = re.sub(r"\s+", " ", value)
    return value[:90] or "quote-video"
