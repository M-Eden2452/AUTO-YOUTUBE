from __future__ import annotations

import argparse
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from anime_factory.modules.analyze_audio import analyze_audio
from anime_factory.modules.detect_scenes import detect_scene_cuts
from anime_factory.modules.extract_audio import copy_source_video, extract_audio
from anime_factory.modules.ffmpeg_utils import ensure_ffmpeg
from anime_factory.modules.paths import (
    clean_force_outputs,
    clean_output_only,
    ensure_episode_dirs,
    get_episode_paths,
    load_config,
    read_json,
    write_json,
)
from anime_factory.modules.preview import create_previews
from anime_factory.modules.refine_boundaries import refine_candidates
from anime_factory.modules.render_clips import render_clips
from anime_factory.modules.report import write_report
from anime_factory.modules.score_candidates import find_candidates
from anime_factory.modules.selection import load_selected_candidates, write_selected_example
from anime_factory.modules.transcribe import transcribe_audio


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MVP пайплайн для создания YouTube Shorts из локального anime mp4.")
    parser.add_argument("--input", help="Путь к исходному видео.")
    parser.add_argument("--episode", required=True, help="Имя эпизода, например episode_001.")
    parser.add_argument("--max-clips", type=int, default=10, help="Количество финальных роликов, по умолчанию 10.")
    parser.add_argument("--candidate-count", type=int, default=30, help="Сколько кандидатов искать и сохранять, по умолчанию 30.")
    parser.add_argument("--min-duration", type=float, default=20, help="Минимальная длина клипа, по умолчанию 20.")
    parser.add_argument("--max-duration", type=float, default=45, help="Максимальная длина клипа, по умолчанию 45.")
    parser.add_argument("--skip-transcribe", action="store_true", help="Пропустить транскрибацию, если артефакты уже есть.")
    parser.add_argument("--skip-render", action="store_true", help="Пропустить рендер финальных роликов.")
    parser.add_argument("--force", action="store_true", help="Очистить output/previews/artifacts/crops/report.html перед новым рендером.")
    parser.add_argument("--clean-output", action="store_true", help="Очистить только output старого episode и завершить работу.")
    parser.add_argument("--preview-only", action="store_true", help="Создать candidates, previews и report без финального render.")
    parser.add_argument("--preview-quality", default="fast", choices=["fast", "better"], help="Качество preview, по умолчанию fast.")
    parser.add_argument("--compare-crops", action="store_true", help="Создать side-by-side preview для сравнения crop modes.")
    parser.add_argument("--render-selected", help="Путь к selected.json с выбранными candidate ids.")
    parser.add_argument("--refine-boundaries", action="store_true", help="Уточнить границы кандидатов по репликам, тишине и scene cuts.")
    parser.add_argument("--trim-edges-silence", action="store_true", help="Обрезать тишину по краям при refinement.")
    parser.add_argument("--scene-detect", action="store_true", help="Найти резкие смены сцен и сохранить scene_cuts.json.")
    parser.add_argument("--whisper-model", default="small", help="Модель faster-whisper, по умолчанию small.")
    parser.add_argument(
        "--crop-mode",
        choices=["center", "smart_static", "dynamic", "blur", "auto"],
        default="auto",
        help="Режим кадрирования: center, smart_static, dynamic, blur или auto. По умолчанию auto.",
    )
    parser.add_argument("--disable-face-crop", action="store_true", help="Отключить face-aware crop и использовать fallback.")
    parser.add_argument("--crop-debug", action="store_true", help="Сохранять временные файлы dynamic crop для отладки.")
    return parser.parse_args()


def run_pipeline(args: argparse.Namespace) -> int:
    paths = get_episode_paths(args.episode)
    if args.clean_output:
        clean_output_only(paths)
        print(f"Output очищен для episode: {args.episode}")
        return 0
    _validate_args(args)

    input_video = Path(args.input)
    ensure_ffmpeg()
    config = load_config()
    ensure_episode_dirs(paths)
    if args.force:
        print("Режим --force: очищаю старые output/previews/crop artifacts для этого episode")
        clean_force_outputs(paths)
        ensure_episode_dirs(paths)

    print(f"Готовлю эпизод: {args.episode}")
    copy_source_video(input_video, paths.source_video, force=False)
    extract_audio(paths.source_video, paths.audio_wav, force=False)
    transcript = _load_or_transcribe(args, paths)
    audio_features = analyze_audio(paths.audio_wav, paths.audio_features_json, force=False)
    scene_cuts = _load_or_detect_scenes(args, paths)
    candidates = _load_or_score_candidates(args, paths, transcript, audio_features, scene_cuts, config)
    write_selected_example(paths.selected_example_json, candidates, args.max_clips)

    output_paths: list[Path] = []
    if args.preview_only:
        create_previews(
            paths.source_video,
            candidates,
            paths.previews_dir,
            config,
            force=args.force,
            crop_mode=args.crop_mode,
            preview_quality=args.preview_quality,
            compare_crops=args.compare_crops,
        )
        write_json(paths.candidates_json, candidates)
        write_report(candidates, output_paths, paths.report_html)
        print("Preview workflow завершен. Финальные ролики не рендерились.")
        return 0

    render_candidates = _select_render_candidates(args, candidates)
    if args.skip_render:
        print("Рендер пропущен по флагу --skip-render.")
    else:
        output_paths = render_clips(
            paths.source_video,
            render_candidates,
            paths.output_dir,
            paths.artifacts_dir,
            config,
            force=False,
            crop_mode=args.crop_mode,
            disable_face_crop=args.disable_face_crop,
            crop_debug=args.crop_debug,
        )

    write_report(candidates, output_paths, paths.report_html)
    print("Пайплайн завершен.")
    return 0


def _validate_args(args: argparse.Namespace) -> None:
    if not args.input:
        raise ValueError("Нужно указать --input, если не используется --clean-output.")
    if not Path(args.input).exists():
        raise FileNotFoundError(f"Не найден input video: {args.input}")
    if args.min_duration <= 0 or args.max_duration <= 0 or args.min_duration > args.max_duration:
        raise ValueError("Некорректные значения --min-duration и --max-duration.")
    if args.max_clips <= 0:
        raise ValueError("--max-clips должен быть больше 0.")
    if args.candidate_count <= 0:
        raise ValueError("--candidate-count должен быть больше 0.")


def _load_or_transcribe(args: argparse.Namespace, paths) -> list[dict]:
    if args.skip_transcribe:
        if not paths.transcript_json.exists() or not paths.subtitles_raw_srt.exists():
            raise FileNotFoundError("Нельзя пропустить транскрибацию: transcript.json или subtitles_raw.srt еще не существуют.")
        print("Транскрибация пропущена по флагу --skip-transcribe.")
        return read_json(paths.transcript_json)
    return transcribe_audio(
        paths.audio_wav,
        paths.transcript_json,
        paths.subtitles_raw_srt,
        model_name=args.whisper_model,
        force=False,
    )


def _load_or_detect_scenes(args: argparse.Namespace, paths) -> list[dict]:
    if args.scene_detect or args.refine_boundaries:
        return detect_scene_cuts(paths.source_video, paths.scene_cuts_json, force=args.force)
    if paths.scene_cuts_json.exists():
        return read_json(paths.scene_cuts_json)
    return []


def _load_or_score_candidates(args: argparse.Namespace, paths, transcript, audio_features, scene_cuts, config) -> list[dict]:
    if args.render_selected and paths.candidates_json.exists() and not args.force:
        print(f"Использую существующие candidates для render-selected: {paths.candidates_json}")
        return read_json(paths.candidates_json)
    should_rebuild = args.force or args.refine_boundaries or not paths.candidates_json.exists()
    if not should_rebuild:
        candidates = read_json(paths.candidates_json)
        if len(candidates) >= args.candidate_count:
            print(f"Кандидаты уже существуют, пропускаю пересчет: {paths.candidates_json}")
            return candidates
        print("Кандидатов меньше, чем requested candidate-count, пересчитываю.")

    print("Ищу лучшие кандидаты для Shorts...")
    candidates = find_candidates(
        transcript,
        audio_features,
        config,
        max_clips=args.candidate_count,
        min_duration=args.min_duration,
        max_duration=args.max_duration,
    )
    if args.refine_boundaries or args.trim_edges_silence:
        candidates = refine_candidates(
            candidates,
            transcript,
            audio_features,
            scene_cuts,
            trim_silence=args.trim_edges_silence,
            use_scene_cuts=args.scene_detect,
        )
    write_json(paths.candidates_json, candidates)
    print(f"Кандидаты сохранены: {paths.candidates_json}")
    return candidates


def _select_render_candidates(args: argparse.Namespace, candidates: list[dict]) -> list[dict]:
    if args.render_selected:
        selected = load_selected_candidates(Path(args.render_selected), candidates)
        print(f"Выбрано кандидатов для финального рендера: {len(selected)}")
        return selected
    return candidates[: args.max_clips]


def main() -> int:
    try:
        return run_pipeline(parse_args())
    except Exception as exc:
        print(f"Ошибка: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
