from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class EpisodePaths:
    root: Path
    source_video: Path
    artifacts_dir: Path
    output_dir: Path
    previews_dir: Path
    audio_wav: Path
    transcript_json: Path
    subtitles_raw_srt: Path
    audio_features_json: Path
    candidates_json: Path
    scene_cuts_json: Path
    crops_dir: Path
    selected_example_json: Path
    report_html: Path


def get_episode_paths(episode: str) -> EpisodePaths:
    safe_episode = episode.strip().replace("\\", "_").replace("/", "_")
    if not safe_episode:
        raise ValueError("Имя эпизода не может быть пустым.")
    root = PROJECT_ROOT / "episodes" / safe_episode
    artifacts = root / "artifacts"
    output = root / "output"
    previews = root / "previews"
    return EpisodePaths(
        root=root,
        source_video=root / "source.mp4",
        artifacts_dir=artifacts,
        output_dir=output,
        previews_dir=previews,
        audio_wav=artifacts / "audio.wav",
        transcript_json=artifacts / "transcript.json",
        subtitles_raw_srt=artifacts / "subtitles_raw.srt",
        audio_features_json=artifacts / "audio_features.json",
        candidates_json=artifacts / "candidates.json",
        scene_cuts_json=artifacts / "scene_cuts.json",
        crops_dir=artifacts / "crops",
        selected_example_json=root / "selected.example.json",
        report_html=root / "report.html",
    )


def ensure_episode_dirs(paths: EpisodePaths) -> None:
    paths.root.mkdir(parents=True, exist_ok=True)
    paths.artifacts_dir.mkdir(parents=True, exist_ok=True)
    paths.crops_dir.mkdir(parents=True, exist_ok=True)
    paths.output_dir.mkdir(parents=True, exist_ok=True)
    paths.previews_dir.mkdir(parents=True, exist_ok=True)


def _clear_directory_contents(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for item in directory.iterdir():
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()


def clean_force_outputs(paths: EpisodePaths) -> None:
    _clear_directory_contents(paths.output_dir)
    _clear_directory_contents(paths.previews_dir)
    _clear_directory_contents(paths.crops_dir)
    if paths.report_html.exists():
        paths.report_html.unlink()


def clean_output_only(paths: EpisodePaths) -> None:
    _clear_directory_contents(paths.output_dir)


def load_config(config_path: Path | None = None) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("Не установлена зависимость pyyaml. Выполните: pip install -r anime_factory/requirements.txt") from exc

    path = config_path or PROJECT_ROOT / "config.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Не найден config.yaml: {path}")
    with path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8-sig") as file:
        return json.load(file)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
