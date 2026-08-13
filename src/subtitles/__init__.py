"""Единый движок субтитров, осведомлённый о локализации (этап Q3).

Второго движка субтитров это не создаёт и создать не может: ``src/news/subtitles.py``
остаётся точкой входа пайплайна и стал тонким адаптером над этим пакетом, а границы
сцен по-прежнему считает только ``src.audio.scene_timeline`` (этап B1).

Разделение ответственности:

- ``models``        - контракты (cue, segment, policy, style, request, result);
- ``segmentation``  - где рвётся текст (слова не теряются и не переставляются);
- ``timing``        - откуда берётся время (иерархия источников);
- ``validation``    - что считается ошибкой, а что предупреждением;
- ``style``         - ``config/channels/<id>/subtitle_style.json`` (остаток этапа E2);
- ``serialization`` - SRT и ASS, и только они (VTT никто не читает);
- ``manifest``      - артефакт на диске и решение resume;
- ``engine``        - сборка всего перечисленного.

Ни один модуль пакета не ходит в сеть, не вызывает TTS, не распознаёт речь, не
выравнивает по словам, не рендерит и не тратит деньги.
"""

from .engine import (
    build_subtitle_result,
    explain_scene_mapping,
    narration_fingerprint,
    script_fingerprint,
)
from .manifest import (
    RESUME_COMPATIBLE,
    RESUME_LANGUAGE_CHANGED,
    RESUME_LEGACY_ARTIFACT,
    RESUME_NARRATION_CHANGED,
    RESUME_NO_ARTIFACT,
    RESUME_PROTECTED,
    RESUME_SCRIPT_CHANGED,
    SCHEMA_VERSION,
    SubtitleArtifact,
    SubtitleResumeDecision,
    artifact_paths,
    build_manifest,
    duplicate_paths,
    manifest_cues,
    manifest_path,
    plan_resume,
    read_manifest,
    subtitle_dir,
    write_artifact,
)
from .models import (
    FORMAT_ASS,
    FORMAT_SRT,
    SUPPORTED_FORMATS,
    TEXT_FIELD_NARRATION,
    TEXT_FIELD_ON_SCREEN,
    TIMING_SOURCE_LEGACY_PLANNED,
    TIMING_SOURCE_SCENE_TIMELINE,
    TIMING_SOURCE_SEGMENT,
    TIMING_SOURCE_UNAVAILABLE,
    TIMING_SOURCE_WORD,
    SubtitleCue,
    SubtitleError,
    SubtitleIssue,
    SubtitlePolicy,
    SubtitleRequest,
    SubtitleResult,
    SubtitleSegment,
    SubtitleStyle,
    SubtitleValidationResult,
)
from .segmentation import split_scene_text, wrap_lines
from .serialization import read_srt, serialize, subtitle_filename, to_ass, to_srt, write_subtitle_file
from .style import resolve_subtitle_style
from .timing import SceneSpan, SceneTimingPlan, resolve_scene_spans
from .validation import validate_cues

__all__ = [
    "FORMAT_ASS",
    "FORMAT_SRT",
    "RESUME_COMPATIBLE",
    "RESUME_LANGUAGE_CHANGED",
    "RESUME_LEGACY_ARTIFACT",
    "RESUME_NARRATION_CHANGED",
    "RESUME_NO_ARTIFACT",
    "RESUME_PROTECTED",
    "RESUME_SCRIPT_CHANGED",
    "SCHEMA_VERSION",
    "SUPPORTED_FORMATS",
    "TEXT_FIELD_NARRATION",
    "TEXT_FIELD_ON_SCREEN",
    "TIMING_SOURCE_LEGACY_PLANNED",
    "TIMING_SOURCE_SCENE_TIMELINE",
    "TIMING_SOURCE_SEGMENT",
    "TIMING_SOURCE_UNAVAILABLE",
    "TIMING_SOURCE_WORD",
    "SceneSpan",
    "SceneTimingPlan",
    "SubtitleArtifact",
    "SubtitleCue",
    "SubtitleError",
    "SubtitleIssue",
    "SubtitlePolicy",
    "SubtitleRequest",
    "SubtitleResult",
    "SubtitleResumeDecision",
    "SubtitleSegment",
    "SubtitleStyle",
    "SubtitleValidationResult",
    "artifact_paths",
    "build_manifest",
    "build_subtitle_result",
    "duplicate_paths",
    "explain_scene_mapping",
    "manifest_cues",
    "manifest_path",
    "narration_fingerprint",
    "plan_resume",
    "read_manifest",
    "read_srt",
    "resolve_scene_spans",
    "resolve_subtitle_style",
    "script_fingerprint",
    "serialize",
    "split_scene_text",
    "subtitle_dir",
    "subtitle_filename",
    "to_ass",
    "to_srt",
    "validate_cues",
    "wrap_lines",
    "write_artifact",
    "write_subtitle_file",
]
