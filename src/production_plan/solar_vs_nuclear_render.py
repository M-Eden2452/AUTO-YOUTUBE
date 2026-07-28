from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

import imageio_ffmpeg
import requests
from dotenv import load_dotenv

from src.audio.tts.elevenlabs_provider import ElevenLabsProvider
from src.audio.tts.models import TTSRequest
from src.providers import pexels_provider, pixabay_provider
from .youtube_shorts import check_render_readiness, render_html_preview


WIDTH = 1080
HEIGHT = 1920
FPS = 30
REQUEST_TIMEOUT = 30
VOICE_ID_DOM = "hDfThiytYnsDMuVgm6Qy"
MODEL_ID = "eleven_multilingual_v2"

KNOWN_BAD_VISUAL_ASSETS = {
    "pixabay_212433": "known_bad_visual_asset: snake clip returned for a solar panel scene",
}

OFF_TOPIC_SOURCE_TERMS = {
    "solar": ["snake", "reptile", "wildlife", "forest", "jungle"],
    "nuclear": ["chernobyl", "accident", "explosion", "abandoned", "radiation"],
}

MOTION_SCENE_STOCK_QUERIES = {
    "scene_004": [
        "solar farm day to night timelapse",
        "solar panels sunset timelapse",
        "solar farm clouds passing aerial",
    ],
    "scene_007": [
        "utility scale solar farm power lines aerial",
        "electricity grid solar farm aerial",
        "solar power plant transmission infrastructure",
    ],
    "scene_011": [
        "nuclear power plant aerial",
        "large solar farm aerial",
        "electricity power grid aerial",
    ],
}


def build_solar_vs_nuclear_video(project_root: str | Path = "project_solar_vs_nuclear") -> dict[str, Any]:
    root = Path(project_root)
    from src.config_resolver.paths import resolve_application_paths

    load_dotenv(resolve_application_paths().repository_root / ".env", override=True)
    scenes_data = _read_json(root / "scenes.json")
    scenes = scenes_data["scenes"]
    voice = ensure_final_voice(root)
    selected = select_and_download_stock(root, scenes)
    stock_index = write_stock_source_index(root, selected)
    scenes_data["scenes"] = selected
    _write_json(root / "scenes.json", scenes_data)
    config = _sync_render_policy(root)
    (root / "preview.html").write_text(render_html_preview(config, selected), encoding="utf-8")
    readiness = check_render_readiness(root)
    if readiness["status"] != "ready":
        return {"status": "blocked", "readiness": readiness}
    render = render_final_video(root, selected, voice["duration_sec"])
    return {"status": "completed", "voice": voice, "render": render, "readiness": readiness, "stock_index": stock_index}


def _sync_render_policy(root: Path) -> dict[str, Any]:
    config = _read_json(root / "project_config.json")
    config.setdefault("asset_selection", {})
    config["asset_selection"].update(
        {
            "mode": "semantic",
            "legacy_fallback_enabled": False,
            "visual_review_required": True,
        }
    )
    config["render_policy"] = {
        "allowed_text_layers": ["ass_subtitles"],
        "subtitle_layers": 1,
        "allow_overlay_text": False,
        "allow_generated_motion_placeholders": False,
        "allow_debug_labels": False,
        "allow_branding": False,
    }
    config.setdefault("render_gate", {})
    config["render_gate"].update(
        {
            "requires_voice_final": True,
            "requires_all_scenes_selected": True,
            "requires_no_generated_visual_assets": True,
            "block_final_render_when_missing": True,
        }
    )
    _write_json(root / "project_config.json", config)
    return config


def ensure_final_voice(root: Path) -> dict[str, Any]:
    voice_dir = root / "02_voice"
    voice_dir.mkdir(parents=True, exist_ok=True)
    wav_path = voice_dir / "voice_final.wav"
    mp3_path = voice_dir / "voice_final.mp3"
    text = (root / "01_script" / "voiceover_ru.txt").read_text(encoding="utf-8").strip()
    if not wav_path.exists() or wav_path.stat().st_size < 1024:
        request = TTSRequest(
            job_id="solar_vs_nuclear",
            localization_id="ru",
            provider="elevenlabs",
            language="ru",
            text=text,
            voice_id=(os.getenv("ELEVENLABS_VOICE_ID") or VOICE_ID_DOM).strip(),
            voice_name="Dom",
            model_id=MODEL_ID,
            output_format="mp3_44100_128",
            sample_rate=44100,
            settings={
                "stability": 0.60,
                "similarity_boost": 0.75,
                "style": 0.05,
                "use_speaker_boost": True,
                "speed": 1.02,
            },
            output_path=str(mp3_path),
        )
        ElevenLabsProvider().synthesize(request)
        _run_ffmpeg(["-y", "-v", "error", "-i", str(mp3_path), "-ar", "48000", "-ac", "1", str(wav_path)])
    duration = _probe_duration(wav_path)
    manifest = {
        "status": "completed",
        "provider": "elevenlabs",
        "voice_name": "Dom",
        "voice_id": (os.getenv("ELEVENLABS_VOICE_ID") or VOICE_ID_DOM).strip(),
        "model_id": MODEL_ID,
        "audio_path": str(wav_path),
        "mp3_path": str(mp3_path),
        "duration_sec": duration,
        "characters": len(text),
    }
    _write_json(voice_dir / "voice_manifest.json", manifest)
    return manifest


def select_and_download_stock(root: Path, scenes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    used_ids: set[str] = set()
    report: list[dict[str, Any]] = []
    for scene in scenes:
        existing = scene.get("selected_asset") or {}
        if _can_keep_reviewed_asset(existing):
            used_ids.add(str(existing.get("asset_key") or existing.get("asset_id") or existing.get("path")))
            scene["status"] = "selected"
            scene["rejection_reason"] = ""
            report.append({"scene_id": scene["scene_id"], "selected": existing, "candidate_count": 0, "kept_existing": True})
            continue

        candidates: list[dict[str, Any]] = []
        for query in _scene_stock_queries(scene):
            candidates.extend(_search_candidates(query, scene))
        candidates = [candidate for candidate in candidates if candidate["asset_key"] not in used_ids]
        ranked = sorted(candidates, key=lambda item: (not item.get("rejected", False), item["score"]), reverse=True)

        selected = None
        for candidate in ranked:
            if candidate.get("rejected"):
                continue
            target = _stock_target(root, scene, candidate)
            if _download_file(candidate["download_url"], target):
                selected = {**candidate, "path": str(target), "downloaded_path": str(target), "type": "video"}
                used_ids.add(candidate["asset_key"])
                break

        if selected:
            scene["selected_asset"] = selected
            scene["status"] = "selected"
            scene["rejection_reason"] = ""
        else:
            scene["selected_asset"] = None
            scene["status"] = "needs_assets"
            scene["rejection_reason"] = "no_downloadable_stock_asset"
        scene["candidate_report"] = ranked[:8]
        report.append({"scene_id": scene["scene_id"], "selected": selected, "candidate_count": len(ranked)})
    _write_json(root / "03_stock" / "stock_selection_report.json", {"scenes": report})
    return scenes


def write_stock_source_index(root: Path, scenes: list[dict[str, Any]]) -> dict[str, str]:
    stock_dir = root / "03_stock"
    stock_dir.mkdir(parents=True, exist_ok=True)
    entries = []
    for scene in scenes:
        asset = scene.get("selected_asset") or {}
        if not asset:
            continue
        entries.append(
            {
                "scene_id": scene.get("scene_id", ""),
                "provider": asset.get("provider", ""),
                "asset_id": asset.get("asset_id") or asset.get("asset_key", ""),
                "author": asset.get("author", ""),
                "license": asset.get("license", ""),
                "rights_status": asset.get("rights_status", ""),
                "allowed_for_render": bool(asset.get("allowed_for_render", False)),
                "search_query": asset.get("search_query", ""),
                "source_page": asset.get("source_page") or asset.get("source_url", ""),
                "direct_download_url": asset.get("direct_download_url") or asset.get("download_url", ""),
                "width": int(asset.get("width") or 0),
                "height": int(asset.get("height") or 0),
                "duration_sec": float(asset.get("duration") or 0),
                "orientation": asset.get("orientation", ""),
                "local_path": asset.get("path") or asset.get("downloaded_path", ""),
                "visual_review_status": asset.get("visual_review_status", ""),
                "visual_review_note": asset.get("visual_review_note", ""),
            }
        )
    json_path = stock_dir / "selected_sources.json"
    markdown_path = stock_dir / "selected_sources.md"
    _write_json(json_path, {"project_id": "solar_vs_nuclear", "sources": entries})
    markdown_path.write_text(_stock_source_markdown(entries), encoding="utf-8")
    return {"json_path": str(json_path), "markdown_path": str(markdown_path)}


def _stock_source_markdown(entries: list[dict[str, Any]]) -> str:
    lines = [
        "# Selected Stock Sources",
        "",
        "This file lists the visual assets selected for the render.",
        "",
        "| Scene | Provider | Asset ID | Author | Query | Resolution | Duration | Source | Local file |",
        "| --- | --- | --- | --- | --- | --- | ---: | --- | --- |",
    ]
    for entry in entries:
        resolution = f"{entry['width']}x{entry['height']}" if entry["width"] and entry["height"] else ""
        lines.append(
            "| {scene} | {provider} | {asset_id} | {author} | {query} | {resolution} | {duration:.1f}s | {source} | `{path}` |".format(
                scene=_md_cell(entry["scene_id"]),
                provider=_md_cell(entry["provider"]),
                asset_id=_md_cell(entry["asset_id"]),
                author=_md_cell(entry["author"]),
                query=_md_cell(entry["search_query"]),
                resolution=_md_cell(resolution),
                duration=float(entry["duration_sec"] or 0),
                source=_md_link(entry["source_page"]),
                path=_md_cell(entry["local_path"]),
            )
        )
    lines.append("")
    return "\n".join(lines)


def _md_cell(value: Any) -> str:
    return str(value or "").replace("|", "\\|").replace("\n", " ")


def _md_link(url: Any) -> str:
    text = str(url or "").strip()
    if not text:
        return ""
    return f"[source]({text})"


def _can_keep_reviewed_asset(asset: dict[str, Any]) -> bool:
    if not asset:
        return False
    asset_id = str(asset.get("asset_id") or asset.get("asset_key") or "")
    if asset_id in KNOWN_BAD_VISUAL_ASSETS:
        return False
    if asset.get("provider") in {"motion_design", "generated_motion", "placeholder"}:
        return False
    if asset.get("type") in {"motion", "generated_motion", "placeholder"}:
        return False
    if asset.get("visual_review_status") not in {"agent_reviewed", "manual_approved", "approved"}:
        return False
    path = Path(str(asset.get("path") or ""))
    return path.exists() and path.stat().st_size > 100_000


def render_final_video(root: Path, scenes: list[dict[str, Any]], voice_duration: float) -> dict[str, Any]:
    render_dir = root / "05_project" / "render"
    segment_dir = render_dir / "segments"
    export_dir = root / "05_project" / "exports"
    segment_dir.mkdir(parents=True, exist_ok=True)
    export_dir.mkdir(parents=True, exist_ok=True)
    durations = _scene_durations(scenes, voice_duration)
    segments = []
    for scene, duration in zip(scenes, durations):
        source = Path(scene["selected_asset"]["path"])
        target = segment_dir / f"{scene['scene_id']}.mp4"
        _render_stock_segment(source, target, duration)
        segments.append(target)

    concat = render_dir / "segments.txt"
    concat.write_text("\n".join(f"file '{str(path.resolve()).replace(chr(92), '/')}'" for path in segments) + "\n", encoding="utf-8")
    silent = render_dir / "silent.mp4"
    no_subtitles = export_dir / "solar_vs_nuclear_no_subtitles.mp4"
    final = export_dir / "solar_vs_nuclear_final.mp4"
    subtitles = root / "05_project" / "subtitles.ass"
    _write_ass_subtitles(subtitles, scenes, durations)
    _run_ffmpeg(["-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(concat), "-c:v", "copy", str(silent)])
    _run_ffmpeg(
        [
            "-y",
            "-v",
            "error",
            "-i",
            str(silent),
            "-i",
            str(root / "02_voice" / "voice_final.wav"),
            "-shortest",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            str(no_subtitles),
        ]
    )
    _burn_ass_subtitles(no_subtitles, subtitles, final)
    manifest = {
        "status": "completed",
        "output_path": str(final),
        "no_subtitles_path": str(no_subtitles),
        "subtitle_path": str(subtitles),
        "subtitle_layers": 1,
        "overlay_text_layers": 0,
        "branding_layers": 0,
        "duration_sec": _probe_duration(final),
        "resolution": {"width": WIDTH, "height": HEIGHT},
        "fps": FPS,
        "scene_count": len(scenes),
    }
    _write_json(root / "05_project" / "render_manifest.json", manifest)
    return manifest


def _search_candidates(query: str, scene: dict[str, Any]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    pexels_key = (os.getenv("PEXELS_API_KEY") or "").strip()
    pixabay_key = (os.getenv("PIXABAY_API_KEY") or "").strip()
    if pexels_key:
        try:
            for item in pexels_provider.search_videos(pexels_key, query, per_page=8):
                best = _best_pexels_file(item.get("video_files", []))
                if best:
                    results.append(
                        _candidate(
                            provider="pexels",
                            source_id=str(item.get("id", "")),
                            source_page=item.get("url", ""),
                            download_url=best.get("link", ""),
                            author=item.get("user", {}).get("name", ""),
                            license_name="pexels",
                            width=int(best.get("width") or 0),
                            height=int(best.get("height") or 0),
                            duration=float(item.get("duration") or 0),
                            query=query,
                            scene=scene,
                        )
                    )
        except Exception:
            pass
    if pixabay_key:
        try:
            for item in pixabay_provider.search_videos(pixabay_key, query, per_page=8):
                best = _best_pixabay_file(item.get("videos", {}))
                if best:
                    results.append(
                        _candidate(
                            provider="pixabay",
                            source_id=str(item.get("id", "")),
                            source_page=item.get("pageURL", ""),
                            download_url=best.get("url", ""),
                            author=item.get("user", ""),
                            license_name="pixabay",
                            width=int(best.get("width") or 0),
                            height=int(best.get("height") or 0),
                            duration=float(item.get("duration") or 0),
                            query=query,
                            scene=scene,
                        )
                    )
        except Exception:
            pass
    return [item for item in results if item["width"] >= 1280 and item["height"] >= 720 and item["score"] >= 20]


def _scene_stock_queries(scene: dict[str, Any]) -> list[str]:
    queries = [str(item).strip() for item in scene.get("search_queries", []) if str(item).strip()]
    if queries:
        return queries
    return MOTION_SCENE_STOCK_QUERIES.get(str(scene.get("scene_id", "")), [])


def _candidate(
    *,
    provider: str,
    source_id: str,
    source_page: str,
    download_url: str,
    author: str,
    license_name: str,
    width: int,
    height: int,
    duration: float,
    query: str,
    scene: dict[str, Any],
) -> dict[str, Any]:
    text = f"{query} {source_page}".lower()
    source_text = str(source_page).lower()
    positive = [item.lower() for item in scene.get("positive_keywords", [])]
    negative = [item.lower() for item in scene.get("negative_keywords", [])]
    positive_score = sum(18 for item in positive if item in text)
    negative_penalty = sum(35 for item in negative if item and item in text)
    quality_score = min(30, (width * height) / (1920 * 1080) * 10)
    vertical_score = 12 if height > width else 4
    duration_score = 10 if duration >= 3 else -20
    score = positive_score + quality_score + vertical_score + duration_score - negative_penalty
    asset_key = f"{provider}_{source_id}"
    reject_reasons: list[str] = []
    if asset_key in KNOWN_BAD_VISUAL_ASSETS:
        reject_reasons.append(KNOWN_BAD_VISUAL_ASSETS[asset_key])
    off_topic_matches = [term for term in _off_topic_terms_for_scene(scene) if term.lower() in source_text]
    if off_topic_matches:
        reject_reasons.append("off_topic_source_terms:" + ",".join(off_topic_matches))
    if negative_penalty:
        reject_reasons.append("negative_keyword_match")
    return {
        "asset_key": asset_key,
        "asset_id": asset_key,
        "provider": provider,
        "source_id": source_id,
        "source_page": source_page,
        "source_url": source_page,
        "direct_download_url": download_url,
        "download_url": download_url,
        "author": author,
        "license": license_name,
        "rights_status": "licensed",
        "allowed_for_render": True,
        "width": width,
        "height": height,
        "duration": duration,
        "orientation": "vertical" if height > width else "horizontal",
        "search_query": query,
        "score": round(score, 3),
        "positive_matches": [item for item in positive if item in text],
        "negative_matches": [item for item in negative if item and item in text],
        "visual_review_status": "provider_metadata_only",
        "rejected": bool(reject_reasons),
        "reject_reason": ";".join(reject_reasons),
    }


def _off_topic_terms_for_scene(scene: dict[str, Any]) -> list[str]:
    text = " ".join(scene.get("positive_keywords", []) + scene.get("search_queries", [])).lower()
    terms: list[str] = []
    for domain, values in OFF_TOPIC_SOURCE_TERMS.items():
        if domain in text:
            terms.extend(values)
    return terms


def _render_stock_segment(source: Path, target: Path, duration: float) -> None:
    vf = f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,crop={WIDTH}:{HEIGHT},setsar=1,fps={FPS},format=yuv420p"
    _run_ffmpeg(
        [
            "-y",
            "-v",
            "error",
            "-stream_loop",
            "-1",
            "-i",
            str(source),
            "-t",
            f"{duration:.3f}",
            "-an",
            "-vf",
            vf,
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "21",
            str(target),
        ]
    )


def _scene_durations(scenes: list[dict[str, Any]], total: float) -> list[float]:
    base = []
    for scene in scenes:
        start, end = [float(part.replace("0:", "")) for part in scene["timecode"].split("-")]
        base.append(max(1.0, end - start))
    scale = total / sum(base)
    values = [round(item * scale, 3) for item in base]
    values[-1] = round(total - sum(values[:-1]), 3)
    return values


def _best_pexels_file(files: list[dict[str, Any]]) -> dict[str, Any] | None:
    valid = [item for item in files if item.get("link") and str(item.get("file_type", "")).startswith("video")]
    valid.sort(key=lambda item: int(item.get("width") or 0) * int(item.get("height") or 0), reverse=True)
    return valid[0] if valid else None


def _best_pixabay_file(videos: dict[str, Any]) -> dict[str, Any] | None:
    valid = [item for item in videos.values() if isinstance(item, dict) and item.get("url")]
    valid.sort(key=lambda item: int(item.get("width") or 0) * int(item.get("height") or 0), reverse=True)
    return valid[0] if valid else None


def _stock_target(root: Path, scene: dict[str, Any], candidate: dict[str, Any]) -> Path:
    return root / "03_stock" / _stock_category(scene) / f"{scene['scene_id']}_{candidate['asset_key']}.mp4"


def _stock_category(scene: dict[str, Any]) -> str:
    text = " ".join(scene.get("positive_keywords", []) + scene.get("search_queries", [])).lower()
    if "nuclear" in text:
        return "nuclear"
    if "battery" in text:
        return "battery_storage"
    if "weather" in text or "night" in text:
        return "weather"
    if "60" in text or "area" in text:
        return "city_scale"
    return "solar"


def _download_file(url: str, target: Path) -> bool:
    if target.exists() and target.stat().st_size > 100_000:
        return True
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with requests.get(url, stream=True, timeout=REQUEST_TIMEOUT) as response:
            response.raise_for_status()
            with target.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=1024 * 512):
                    if chunk:
                        handle.write(chunk)
        return target.exists() and target.stat().st_size > 100_000
    except Exception:
        if target.exists():
            target.unlink()
        return False


def _write_ass_subtitles(path: Path, scenes: list[dict[str, Any]], durations: list[float]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    events: list[str] = []
    current = 0.0
    for scene, duration in zip(scenes, durations):
        text = str(scene.get("voiceover") or "").strip()
        if text:
            events.extend(_subtitle_events_for_scene(text, current, duration))
        current += duration
    header = "\n".join(
        [
            "[Script Info]",
            "ScriptType: v4.00+",
            f"PlayResX: {WIDTH}",
            f"PlayResY: {HEIGHT}",
            "",
            "[V4+ Styles]",
            "Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
            "Style: Default,Arial,58,&H00FFFFFF,&HCC000000,&H88000000,0,0,0,0,100,100,0,0,1,4,1,2,90,90,250,1",
            "",
            "[Events]",
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
        ]
    )
    path.write_text(header + "\n" + "\n".join(events) + "\n", encoding="utf-8")


def _subtitle_events_for_scene(text: str, start: float, duration: float) -> list[str]:
    chunks = _subtitle_chunks(text)
    if not chunks:
        return []
    chunk_duration = max(0.8, duration / len(chunks))
    events = []
    for index, chunk in enumerate(chunks):
        chunk_start = start + index * chunk_duration
        chunk_end = start + min(duration, (index + 1) * chunk_duration)
        if chunk_end <= chunk_start:
            continue
        events.append(f"Dialogue: 0,{_ass_time(chunk_start)},{_ass_time(chunk_end)},Default,,0,0,0,,{_ass_escape(chunk)}")
    return events


def _subtitle_chunks(text: str) -> list[str]:
    words = re.findall(r"\S+", text.replace("\n", " "))
    chunks = []
    current: list[str] = []
    for word in words:
        current.append(word)
        if len(current) >= 5 or word.endswith((".", "?", "!", ",")):
            chunks.append(" ".join(current))
            current = []
    if current:
        chunks.append(" ".join(current))
    return chunks


def _ass_time(value: float) -> str:
    value = max(0.0, value)
    hours = int(value // 3600)
    minutes = int((value % 3600) // 60)
    seconds = int(value % 60)
    centiseconds = int(round((value - int(value)) * 100))
    if centiseconds >= 100:
        seconds += 1
        centiseconds = 0
    return f"{hours}:{minutes:02d}:{seconds:02d}.{centiseconds:02d}"


def _ass_escape(text: str) -> str:
    return text.replace("{", "").replace("}", "").replace("\n", "\\N")


def _burn_ass_subtitles(source: Path, subtitles: Path, target: Path) -> None:
    subtitle_filter = f"subtitles='{_escape_subtitle_path(subtitles)}'"
    _run_ffmpeg(
        [
            "-y",
            "-v",
            "error",
            "-i",
            str(source),
            "-vf",
            subtitle_filter,
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "21",
            "-c:a",
            "copy",
            str(target),
        ]
    )


def _escape_subtitle_path(path: Path) -> str:
    return str(path.resolve()).replace("\\", "/").replace(":", "\\:")


def _probe_duration(path: Path) -> float:
    result = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-i", str(path)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", result.stderr or "")
    if not match:
        return 0.0
    hours, minutes, seconds = match.groups()
    return round(int(hours) * 3600 + int(minutes) * 60 + float(seconds), 3)


def _run_ffmpeg(args: list[str]) -> None:
    result = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise RuntimeError((result.stderr or "").strip() or "FFmpeg failed.")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
