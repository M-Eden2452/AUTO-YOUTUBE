from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from src.assets.semantic_selection import analyze_scene
from src.content.visual_planning import semantic_scene_queries


PROJECT_FOLDER = "project_solar_vs_nuclear"
PROJECT_ID = "solar_vs_nuclear"

VOICEOVER_RU = """Сколько солнечных панелей потребуется, чтобы заменить один атомный реактор?

Одна современная панель выдаёт примерно 530 ватт. Поэтому для реактора мощностью один гигаватт сначала получается около двух миллионов панелей.

Но это неправильный ответ.

Реактор производит электричество почти круглосуточно. А солнечные панели ночью не работают и зависят от облаков, сезона и расположения станции.

Поэтому сравнивать нужно не максимальную мощность, а всю энергию, произведённую за год.

И тогда результат вырастает примерно до семи миллионов панелей.

Вместе с дорогами и оборудованием такая солнечная станция может занять около шестидесяти квадратных километров.

Значит, солнечная энергия способна заменить годовую выработку реактора. Но для этого нужны миллионы панелей, огромная территория и отдельное решение для ночи."""

DEFAULT_NEGATIVES = [
    "accident",
    "explosion",
    "Chernobyl",
    "abandoned",
    "radiation",
    "rooftop",
    "single house",
    "portable solar panel",
    "home solar",
]


def create_solar_vs_nuclear_plan(base_dir: str | Path = ".") -> dict[str, Any]:
    root = Path(base_dir) / PROJECT_FOLDER
    _create_folders(root)
    config = _project_config()
    scenes = [_enrich_scene(scene) for scene in _raw_scenes()]
    _write_text(root / "01_script" / "script_ru.txt", _script_outline())
    _write_text(root / "01_script" / "voiceover_ru.txt", VOICEOVER_RU + "\n")
    _write_text(root / "01_script" / "fact_sources.txt", _fact_sources())
    _write_json(root / "project_config.json", config)
    _write_json(root / "scenes.json", {"project_id": PROJECT_ID, "scenes": scenes})
    _write_json(root / "06_analytics" / "metrics_24h.json", {"project_id": PROJECT_ID, "status": "not_collected"})
    _write_json(root / "06_analytics" / "metrics_7d.json", {"project_id": PROJECT_ID, "status": "not_collected"})
    _write_text(root / "preview.html", render_html_preview(config, scenes))
    readiness = check_render_readiness(root)
    return {"root": root, "config": config, "scenes": scenes, "readiness": readiness}


def replace_selected_clip(
    project_root: str | Path,
    scene_id: str,
    clip_path: str | Path,
    *,
    provider: str = "manual",
    note: str = "",
) -> dict[str, Any]:
    root = Path(project_root)
    data = _read_json(root / "scenes.json")
    clip = Path(clip_path)
    updated_scene: dict[str, Any] | None = None
    for scene in data.get("scenes", []):
        if scene.get("scene_id") == scene_id:
            scene["selected_asset"] = {
                "path": str(clip),
                "provider": provider,
                "status": "manual_replacement",
                "replacement_note": note,
            }
            scene["status"] = "selected"
            scene["rejection_reason"] = ""
            updated_scene = scene
            break
    if not updated_scene:
        raise ValueError(f"Scene not found: {scene_id}")
    _write_json(root / "scenes.json", data)
    config = _read_json(root / "project_config.json")
    _write_text(root / "preview.html", render_html_preview(config, data.get("scenes", [])))
    check_render_readiness(root)
    return updated_scene


def check_render_readiness(project_root: str | Path) -> dict[str, Any]:
    root = Path(project_root)
    scenes_path = root / "scenes.json"
    scenes = _read_json(scenes_path).get("scenes", []) if scenes_path.exists() else []
    errors: list[str] = []
    missing_scenes = [
        {
            "scene_id": scene.get("scene_id"),
            "reason": "selected_asset_missing",
            "asset_type": scene.get("asset_type", []),
            "search_queries": scene.get("search_queries", []),
        }
        for scene in scenes
        if not scene.get("selected_asset")
    ]
    if not (root / "02_voice" / "voice_final.wav").exists():
        errors.append("missing_voice_final")
    if missing_scenes:
        errors.append("missing_scene_materials")
    generated_visual_scenes = [
        {
            "scene_id": scene.get("scene_id"),
            "reason": "generated_or_placeholder_visual_not_allowed",
            "provider": (scene.get("selected_asset") or {}).get("provider", ""),
            "type": (scene.get("selected_asset") or {}).get("type", ""),
        }
        for scene in scenes
        if (scene.get("selected_asset") or {}).get("provider") in {"motion_design", "generated_motion", "placeholder"}
        or (scene.get("selected_asset") or {}).get("type") in {"motion", "generated_motion", "placeholder"}
    ]
    if generated_visual_scenes:
        errors.append("generated_visual_assets_not_allowed")
    readiness = {
        "project_id": PROJECT_ID,
        "status": "ready" if not errors else "blocked",
        "errors": errors,
        "missing_scenes": missing_scenes,
        "generated_visual_scenes": generated_visual_scenes,
        "final_render_allowed": not errors,
        "required_voice_file": str(root / "02_voice" / "voice_final.wav"),
    }
    _write_json(root / "render_readiness.json", readiness)
    return readiness


def render_html_preview(config: dict[str, Any], scenes: list[dict[str, Any]]) -> str:
    rows = "\n".join(_scene_row(scene) for scene in scenes)
    return f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(config["title"])}</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; background: #f7f8fa; color: #15171a; }}
    h1 {{ margin: 0 0 8px; font-size: 28px; }}
    .meta {{ margin-bottom: 20px; color: #4a5563; }}
    table {{ width: 100%; border-collapse: collapse; background: white; }}
    th, td {{ border: 1px solid #d8dee8; padding: 10px; vertical-align: top; font-size: 14px; }}
    th {{ background: #eef2f7; text-align: left; }}
    code {{ background: #edf2f7; padding: 2px 4px; border-radius: 4px; }}
    .pending {{ color: #975a16; font-weight: bold; }}
    .selected {{ color: #276749; font-weight: bold; }}
  </style>
</head>
<body>
  <h1>{html.escape(config["title"])}</h1>
  <div class="meta">Format: {config["format"]["aspect_ratio"]}, {config["format"]["resolution"]["width"]}x{config["format"]["resolution"]["height"]}, target {config["target_duration_sec"]}s</div>
  <table>
    <thead>
      <tr><th>Scene</th><th>Time</th><th>Voiceover</th><th>Visual</th><th>Queries</th><th>Status</th><th>Selected</th></tr>
    </thead>
    <tbody>{rows}</tbody>
  </table>
</body>
</html>
"""


def _scene_row(scene: dict[str, Any]) -> str:
    selected = scene.get("selected_asset", {}).get("path", "") if scene.get("selected_asset") else ""
    queries = "<br>".join(f"<code>{html.escape(query)}</code>" for query in scene.get("search_queries", []))
    return (
        "<tr>"
        f"<td>{html.escape(scene['scene_id'])}</td>"
        f"<td>{html.escape(scene['timecode'])}</td>"
        f"<td>{html.escape(scene.get('voiceover', ''))}</td>"
        f"<td>{html.escape(scene.get('visual', ''))}</td>"
        f"<td>{queries}</td>"
        f"<td class='{html.escape(scene.get('status', 'pending'))}'>{html.escape(scene.get('status', 'pending'))}</td>"
        f"<td>{html.escape(selected)}</td>"
        "</tr>"
    )


def _project_config() -> dict[str, Any]:
    return {
        "project_id": PROJECT_ID,
        "title": "Сколько солнечных панелей заменят один атомный реактор?",
        "mode": "youtube_shorts_production_plan",
        "story_structure": ["стимул", "ожидание", "награда"],
        "narrative_structure": "levels_plus_scale_comparison",
        "target_duration_sec": 58,
        "format": {
            "aspect_ratio": "9:16",
            "resolution": {"width": 1080, "height": 1920},
            "platform": "youtube_shorts",
        },
        "voice": {
            "provider": "elevenlabs",
            "language": "ru",
            "required_final_file": "02_voice/voice_final.wav",
            "final_render_requires_voice_final": True,
        },
        "asset_selection": {
            "mode": "semantic",
            "legacy_fallback_enabled": False,
            "vision_validation_enabled": False,
            "visual_review_required": True,
            "minimum_clean_seconds": 3,
            "prefer": ["4K", "crop_safe", "no_text", "no_logo", "camera_motion"],
        },
        "render_policy": {
            "allowed_text_layers": ["ass_subtitles"],
            "subtitle_layers": 1,
            "allow_overlay_text": False,
            "allow_generated_motion_placeholders": False,
            "allow_debug_labels": False,
            "allow_branding": False,
        },
        "render_gate": {
            "requires_voice_final": True,
            "requires_all_scenes_selected": True,
            "requires_no_generated_visual_assets": True,
            "block_final_render_when_missing": True,
        },
    }


def _create_folders(root: Path) -> None:
    for rel in [
        "01_script",
        "02_voice",
        "03_stock/nuclear",
        "03_stock/solar",
        "03_stock/weather",
        "03_stock/city_scale",
        "03_stock/battery_storage",
        "04_motion/counter_panels",
        "04_motion/capacity_factor",
        "04_motion/annual_energy",
        "04_motion/land_area",
        "05_project/capcut",
        "05_project/exports",
        "06_analytics/retention_screenshots",
    ]:
        (root / rel).mkdir(parents=True, exist_ok=True)


def _enrich_scene(scene: dict[str, Any]) -> dict[str, Any]:
    semantic_scene = analyze_scene(
        {
            "scene_id": scene["scene_id"],
            "primary_query": " ".join(scene["search_queries"][:1]),
            "visual_description": scene["visual"],
            "visual_type": "video",
            "visual_priority": scene.get("visual_priority", "exact_subject"),
            "semantic": scene.get("semantic", {}),
        }
    )
    # The same ordered ``{kind, fallback_level, query}`` items the asset manifest
    # stores. It used to be a dict keyed by four fixed rung names; the ladder that
    # replaced them has no such rungs, and naming them here would be re-writing the
    # retired literals into a plan that no longer produces them.
    semantic_queries = semantic_scene_queries(semantic_scene)
    return {
        **scene,
        "positive_keywords": scene.get("positive_keywords", []) or _positive_keywords(scene),
        "negative_keywords": DEFAULT_NEGATIVES + scene.get("negative_keywords", []),
        "semantic_scene": semantic_scene.to_dict(),
        "semantic_queries": semantic_queries,
        "status": scene.get("status", "pending"),
        "selected_asset": scene.get("selected_asset"),
        "rejection_reason": scene.get("rejection_reason", ""),
        "manual_replacement_allowed": True,
    }


def _positive_keywords(scene: dict[str, Any]) -> list[str]:
    text = " ".join(scene.get("search_queries", [])).lower()
    values = []
    for keyword in ["solar farm", "solar panel", "nuclear power plant", "night", "aerial", "top view", "utility scale", "battery storage"]:
        if keyword in text:
            values.append(keyword)
    return values


def _raw_scenes() -> list[dict[str, Any]]:
    return [
        _scene("scene_001", "0:00-0:04", "Сколько солнечных панелей потребуется, чтобы заменить один атомный реактор?", ["stock", "composite", "motion"], "Одна солнечная панель слева, атомная электростанция справа, между ними знак вопроса.", "1 реактор = ? панелей", ["single solar panel close up", "solar panel isolated outdoor", "nuclear power plant aerial", "nuclear cooling towers drone"], ["solar panel", "nuclear power plant"], ["Chernobyl", "accident", "explosion"], "exact_subject"),
        _scene("scene_002", "0:04-0:08", "Одна современная панель выдаёт примерно 530 ватт.", ["stock", "motion"], "Крупный план современной промышленной солнечной панели.", "≈ 530 Вт", ["modern photovoltaic panel close up", "solar panel cells macro", "utility scale solar module"], ["solar panel", "utility scale"], ["home solar", "rooftop", "single house", "people close up"], "exact_subject"),
        _scene("scene_003", "0:08-0:13", "Поэтому для реактора мощностью один гигаватт сначала получается около двух миллионов панелей.", ["stock", "motion"], "Одна панель размножается до огромной солнечной фермы, счётчик растёт до 2 000 000.", "Первая оценка: ≈ 2 000 000", ["massive solar farm aerial", "solar panels endless drone", "large photovoltaic power station", "solar farm rows top view"], ["solar farm", "aerial"], ["rooftop", "single house"], "exact_subject"),
        _scene("scene_004", "0:13-0:16", "Но это неправильный ответ.", ["motion"], "Счётчик останавливается, появляется крест, день переходит в ночь.", "Но есть проблема", [], ["counter", "day night"], ["loud meme"], "abstract_explanation", "needs_motion"),
        _scene("scene_005", "0:16-0:21", "Реактор производит электричество почти круглосуточно.", ["stock", "motion"], "АЭС днём, вечером, ночью и утром.", "АЭС: около 91%", ["nuclear power plant timelapse", "nuclear power station night", "cooling towers sunrise", "power plant day to night"], ["nuclear power plant", "night"], ["accident", "abandoned", "anti nuclear"], "exact_subject"),
        _scene("scene_006", "0:21-0:27", "А солнечные панели ночью не работают и зависят от облаков, сезона и расположения станции.", ["stock"], "Солнечная ферма днём, облака, закат, ночь, зима.", "День / Погода / Сезон / Регион", ["solar farm cloudy weather", "solar panels sunset", "solar farm night", "solar panels winter snow", "cloud shadow solar farm aerial"], ["solar farm", "weather", "night"], ["rooftop", "home solar"], "exact_action"),
        _scene("scene_007", "0:27-0:32", "Поэтому сравнивать нужно не максимальную мощность, а всю энергию, произведённую за год.", ["motion"], "Карточка «Мощность сейчас» заменяется карточкой «Энергия за год», календарь январь–декабрь, простой график.", "Энергия за год", [], ["annual energy", "calendar", "graph"], [], "abstract_explanation", "needs_motion"),
        _scene("scene_008", "0:32-0:39", "И тогда результат вырастает примерно до семи миллионов панелей.", ["stock", "motion"], "Камера отдаляется от солнечной фермы, счётчик растёт до 7 000 000.", "≈ 7 000 000 панелей", ["massive solar farm aerial", "solar panels endless drone", "large photovoltaic power station", "solar farm rows top view"], ["solar farm", "aerial"], ["rooftop", "home solar"], "exact_subject"),
        _scene("scene_009", "0:39-0:44", "Вместе с дорогами и оборудованием такая солнечная станция может занять около шестидесяти квадратных километров.", ["stock", "map", "motion"], "Вид сверху, карта, квадрат площади, сравнение с футбольным полем или городским районом.", "≈ 60 км²", ["solar farm aerial top down", "vast solar power plant desert", "solar farm satellite view", "industrial solar facility drone"], ["solar farm", "top view", "industrial"], ["rooftop", "single house"], "environment"),
        _scene("scene_010", "0:44-0:48", "", ["stock", "annotation"], "Выделить панели, дороги, промежутки, инверторы, подстанции и линии электропередачи.", "Панели + дороги + оборудование", ["solar farm aerial top down", "industrial solar facility drone", "utility scale solar plant infrastructure"], ["solar farm", "infrastructure"], ["rooftop", "home solar"], "exact_subject"),
        _scene("scene_011", "0:48-0:53", "Значит, солнечная энергия способна заменить годовую выработку реактора.", ["motion"], "Слева один реактор, справа семь миллионов панелей, одинаковый индикатор годовой энергии.", "Сопоставимая энергия за год", [], ["annual energy", "nuclear reactor", "solar panels"], ["fully identical"], "abstract_explanation", "needs_motion"),
        _scene("scene_012", "0:53-0:58", "Но для этого нужны миллионы панелей, огромная территория и отдельное решение для ночи.", ["stock", "motion"], "Солнечная ферма на закате, затем батарейный комплекс. Оставить 0.3–0.5 секунды после фразы.", "7 млн панелей / ≈ 60 км² / Хранение энергии", ["battery storage containers", "utility battery storage facility", "solar farm sunset"], ["battery storage", "solar farm"], ["home solar", "portable solar panel"], "exact_subject"),
    ]


def _scene(
    scene_id: str,
    timecode: str,
    voiceover: str,
    asset_type: list[str],
    visual: str,
    on_screen_text: str,
    search_queries: list[str],
    positive_keywords: list[str],
    negative_keywords: list[str],
    visual_priority: str,
    status: str = "pending",
) -> dict[str, Any]:
    return {
        "scene_id": scene_id,
        "timecode": timecode,
        "voiceover": voiceover,
        "asset_type": asset_type,
        "visual": visual,
        "on_screen_text": on_screen_text,
        "search_queries": search_queries,
        "positive_keywords": positive_keywords,
        "negative_keywords": negative_keywords,
        "visual_priority": visual_priority,
        "status": status,
        "rejection_reason": "",
    }


def _script_outline() -> str:
    return (
        "Проект: solar_vs_nuclear\n"
        "Тема: Сколько солнечных панелей заменят один атомный реактор?\n"
        "Структура: 1 акт — стимул; 2 акт — ожидание; 3 акт — награда.\n"
        "Повествование: уровни + сравнение масштаба.\n\n"
        + VOICEOVER_RU
        + "\n"
    )


def _fact_sources() -> str:
    return (
        "Рабочие допущения для проверки перед публикацией:\n"
        "- современная солнечная панель: примерно 530 Вт;\n"
        "- реактор: 1 ГВт установленной мощности;\n"
        "- атомная генерация: около 91% capacity factor;\n"
        "- итоговая оценка: около 7 млн панелей;\n"
        "- территория солнечной станции с инфраструктурой: около 60 км².\n"
        "Перед публикацией заменить этот файл ссылками на конкретные источники расчётов.\n"
    )


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")
