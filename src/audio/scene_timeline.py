"""Real per-scene timing, derived from a generated voice manifest.

Why this exists
---------------
``src/news/subtitles.py`` and ``src/news/final_renderer.py`` both already prefer a
scene's ``actual_duration_sec`` over its planned ``target_duration_sec`` - but until
now *nothing in the repository ever wrote that field*. The result was a rendered
video whose visual timeline followed the script's estimate while the audio followed
the real narration: on the first confirmed live fullscreen-voiceover run the visual
timeline was 51.5 s against 59.47 s of narration, and individual scenes were off by
more than 100 % (scene_001: planned 3.5 s, spoken 7.24 s). Subtitles inherited the
same drift because their chunk timing is a straight division of the scene duration.

This module is the missing bridge. It reads what the voice stage already recorded -
per-scene ``duration_seconds`` in ``voice_manifest.json`` (schema v2) - reconstructs
the same inter-scene pauses that ``src.audio.audio_assembler.assemble_narration``
actually inserted, and returns a timeline the renderer and subtitle builder can use.

It deliberately does not:

- call any provider, read any audio file, or run ffmpeg (pure arithmetic over JSON);
- invent durations when there is no narration - callers get an empty timeline and
  keep their existing planned-duration behaviour unchanged;
- mutate the voice manifest.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .pause_policy import PausePolicy, pause_policy_for_format

# Tolerance when comparing a reconstructed timeline against the assembled narration
# duration reported by ffprobe. Encoder/container rounding makes an exact match
# unrealistic; anything larger than this means the two really disagree.
DURATION_TOLERANCE_SEC = 0.05


@dataclass
class SceneTiming:
    scene_id: str
    scene_index: int
    start_sec: float
    duration_sec: float
    speech_duration_sec: float
    pause_after_sec: float

    @property
    def end_sec(self) -> float:
        return self.start_sec + self.duration_sec

    def to_dict(self) -> dict[str, Any]:
        return {
            "scene_id": self.scene_id,
            "scene_index": self.scene_index,
            "start_sec": round(self.start_sec, 3),
            "duration_sec": round(self.duration_sec, 3),
            "speech_duration_sec": round(self.speech_duration_sec, 3),
            "pause_after_sec": round(self.pause_after_sec, 3),
            "end_sec": round(self.end_sec, 3),
        }


@dataclass
class SceneTimeline:
    """A scene-by-scene timeline covering the whole narration.

    ``scenes`` is empty whenever the timeline could not be derived (no narration, a
    stub manifest, missing per-scene durations). Callers must treat that as "keep
    the planned timings" rather than as an error.
    """

    scenes: list[SceneTiming] = field(default_factory=list)
    source: str = "unavailable"
    narration_duration_sec: float = 0.0
    pause_total_sec: float = 0.0
    warnings: list[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        return bool(self.scenes)

    @property
    def total_duration_sec(self) -> float:
        return self.scenes[-1].end_sec if self.scenes else 0.0

    def by_scene_id(self) -> dict[str, SceneTiming]:
        return {scene.scene_id: scene for scene in self.scenes}

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "narration_duration_sec": round(self.narration_duration_sec, 3),
            "pause_total_sec": round(self.pause_total_sec, 3),
            "total_duration_sec": round(self.total_duration_sec, 3),
            "scene_count": len(self.scenes),
            "scenes": [scene.to_dict() for scene in self.scenes],
            "warnings": list(self.warnings),
        }


def _scene_duration(entry: dict[str, Any]) -> float:
    """Per-scene audio length, tolerant of both spellings seen in the repo.

    ``scene_voice_generator`` writes ``duration_seconds``; some older/manual records
    use ``duration_sec``.
    """
    for key in ("duration_seconds", "duration_sec"):
        value = entry.get(key)
        if value:
            try:
                return max(0.0, float(value))
            except (TypeError, ValueError):
                continue
    return 0.0


def _resolve_pauses(
    manifest_scenes: list[dict[str, Any]],
    script_scenes_by_id: dict[str, dict[str, Any]],
    policy: PausePolicy,
    pause_total_sec: float,
) -> list[float]:
    """Reconstruct the pauses ``assemble_narration`` inserted between scenes.

    Mirrors ``src.audio.narration_workflow.generate_final`` exactly: one pause after
    every scene except the last, value ``policy.clamp(scene.pause_after_sec or
    policy.between_scenes_sec)``. When the reconstructed total disagrees with the
    ``pause_total_sec`` the assembler recorded, the recorded total wins and is spread
    evenly - the manifest is evidence of what was really rendered, the policy is only
    a prediction of it.
    """
    gaps = max(0, len(manifest_scenes) - 1)
    if gaps == 0:
        return []
    pauses: list[float] = []
    for entry in manifest_scenes[:-1]:
        script_scene = script_scenes_by_id.get(str(entry.get("scene_id", "")), {})
        declared = script_scene.get("pause_after_sec")
        pauses.append(policy.clamp(float(declared) if declared is not None else policy.between_scenes_sec))
    if pause_total_sec > 0 and abs(sum(pauses) - pause_total_sec) > DURATION_TOLERANCE_SEC:
        even = pause_total_sec / gaps
        pauses = [even] * gaps
    return pauses


def build_scene_timeline(
    voice_manifest: dict[str, Any] | None,
    *,
    script: dict[str, Any] | None = None,
    format_id: str = "",
) -> SceneTimeline:
    """Derive the real scene timeline from a completed voice manifest.

    Returns an empty (falsy) timeline - never raises - when narration does not exist
    or the manifest is a stub, so every caller can safely fall back to planned
    durations.
    """
    manifest = voice_manifest or {}
    scenes_meta = manifest.get("scenes")
    if not isinstance(scenes_meta, list) or not scenes_meta:
        return SceneTimeline(warnings=["voice_manifest has no scenes"])
    status = manifest.get("status")
    if status is not None and status != "completed":
        # partially_completed / provider_selection_required / skipped: some scene
        # audio may exist, but the assembled narration does not, so any timeline we
        # built would not match the rendered audio track.
        return SceneTimeline(warnings=[f"voice status is {status!r}, not completed"])

    ordered = sorted(
        scenes_meta,
        key=lambda entry: (
            int(entry.get("scene_index") if entry.get("scene_index") is not None else 0),
            str(entry.get("scene_id", "")),
        ),
    )
    durations = [_scene_duration(entry) for entry in ordered]
    if not all(duration > 0 for duration in durations):
        return SceneTimeline(warnings=["voice_manifest scenes are missing per-scene durations"])

    narration = manifest.get("narration") if isinstance(manifest.get("narration"), dict) else {}
    narration_duration = float(narration.get("duration_sec") or manifest.get("duration_sec") or 0.0)
    pause_total = float(narration.get("pause_total_sec") or 0.0)

    script_scenes_by_id = {
        str(scene.get("scene_id", "")): scene for scene in ((script or {}).get("scenes") or []) if isinstance(scene, dict)
    }
    policy = pause_policy_for_format(format_id or str(manifest.get("format_id") or ""))
    pauses = _resolve_pauses(ordered, script_scenes_by_id, policy, pause_total)

    warnings: list[str] = []
    timings: list[SceneTiming] = []
    cursor = 0.0
    for index, (entry, speech) in enumerate(zip(ordered, durations, strict=True)):
        pause_after = pauses[index] if index < len(pauses) else 0.0
        timings.append(
            SceneTiming(
                scene_id=str(entry.get("scene_id", f"scene_{index + 1:03d}")),
                scene_index=int(entry.get("scene_index") if entry.get("scene_index") is not None else index),
                start_sec=cursor,
                duration_sec=speech + pause_after,
                speech_duration_sec=speech,
                pause_after_sec=pause_after,
            )
        )
        cursor += speech + pause_after

    if narration_duration > 0 and abs(cursor - narration_duration) > DURATION_TOLERANCE_SEC:
        # The last scene absorbs the remainder so the timeline always ends exactly
        # where the audio does - otherwise the final scene would be cut short or the
        # video would run past the narration.
        remainder = narration_duration - cursor
        adjusted = max(0.1, timings[-1].duration_sec + remainder)
        warnings.append(
            f"timeline total {cursor:.3f}s did not match narration {narration_duration:.3f}s; "
            f"last scene adjusted by {remainder:+.3f}s"
        )
        timings[-1].duration_sec = adjusted
        cursor = timings[-1].end_sec

    return SceneTimeline(
        scenes=timings,
        source="voice_manifest",
        narration_duration_sec=narration_duration or cursor,
        pause_total_sec=sum(timing.pause_after_sec for timing in timings),
        warnings=warnings,
    )


def apply_timeline_to_script(script: dict[str, Any], timeline: SceneTimeline) -> dict[str, Any]:
    """Return a copy of ``script`` with real timings written onto its scenes.

    Additive and backward compatible: ``target_duration_sec`` is left untouched (it
    stays the record of what was planned), and ``actual_duration_sec``/``start_sec``
    are set to what was actually spoken. Scenes with no matching narration entry are
    left exactly as they were. An empty timeline returns the script unchanged.
    """
    if not timeline:
        return script
    by_id = timeline.by_scene_id()
    updated = dict(script)
    scenes: list[dict[str, Any]] = []
    for index, scene in enumerate(script.get("scenes") or []):
        if not isinstance(scene, dict):
            scenes.append(scene)
            continue
        scene_id = str(scene.get("scene_id", f"scene_{index + 1:03d}"))
        timing = by_id.get(scene_id)
        if timing is None:
            scenes.append(dict(scene))
            continue
        scenes.append(
            {
                **scene,
                "start_sec": round(timing.start_sec, 3),
                "actual_duration_sec": round(timing.duration_sec, 3),
                "speech_duration_sec": round(timing.speech_duration_sec, 3),
                "pause_after_sec": round(timing.pause_after_sec, 3),
            }
        )
    updated["scenes"] = scenes
    updated["actual_duration_sec"] = round(timeline.total_duration_sec, 3)
    updated["timing_source"] = timeline.source
    return updated


def scene_render_duration(scene: dict[str, Any], *, minimum_sec: float = 1.0, fallback_sec: float = 3.0) -> float:
    """The duration a renderer/subtitle builder should use for one scene.

    Single place that encodes "real narration wins over the plan", so
    ``final_renderer`` and ``subtitles`` cannot drift apart again.
    """
    for key in ("actual_duration_sec", "target_duration_sec"):
        value = scene.get(key)
        if value:
            try:
                return max(minimum_sec, float(value))
            except (TypeError, ValueError):
                continue
    return max(minimum_sec, fallback_sec)


__all__ = [
    "DURATION_TOLERANCE_SEC",
    "SceneTimeline",
    "SceneTiming",
    "apply_timeline_to_script",
    "build_scene_timeline",
    "scene_render_duration",
]
