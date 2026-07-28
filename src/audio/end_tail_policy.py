from __future__ import annotations

from typing import Any

END_POLICY_MATCH_NARRATION = "match_narration"
END_POLICY_NARRATION_PLUS_TAIL = "narration_plus_tail"
END_POLICY_PRESERVE_VISUAL_TIMELINE = "preserve_visual_timeline"
END_POLICY_FIXED_DURATION = "fixed_duration"
END_POLICIES = frozenset(
    {
        END_POLICY_MATCH_NARRATION,
        END_POLICY_NARRATION_PLUS_TAIL,
        END_POLICY_PRESERVE_VISUAL_TIMELINE,
        END_POLICY_FIXED_DURATION,
    }
)

DEFAULT_TAIL_SEC = 0.5
MIN_TAIL_SEC = 0.5
MAX_TAIL_SEC = 0.7

# Keyed by template_id (src/production_catalog templates). Mirrors AUDIO_POLICY_DEFAULTS
# in src/audio/voice_policy.py: a separate, small table so this module never needs to
# import src.production_catalog.
END_POLICY_DEFAULTS: dict[str, str] = {
    "fullscreen_voiceover_v1": END_POLICY_NARRATION_PLUS_TAIL,
}

DEFAULT_END_POLICY = END_POLICY_PRESERVE_VISUAL_TIMELINE


class EndTailPolicyError(ValueError):
    """Raised for an invalid end-tail policy id or tail value."""


def resolve_end_policy(template_id: str | None) -> str:
    """Resolve the end-tail policy id for a template_id.

    Falls back to preserve_visual_timeline (today's behavior: video length
    follows the visual plan) for any template without a registered default,
    so this never changes behavior for templates that don't use voiceover.
    """
    return END_POLICY_DEFAULTS.get(template_id or "", DEFAULT_END_POLICY)


def clamp_tail_sec(tail_sec: float) -> float:
    return max(MIN_TAIL_SEC, min(MAX_TAIL_SEC, float(tail_sec)))


def compute_target_duration(
    policy_id: str,
    *,
    narration_duration_sec: float | None,
    visual_duration_sec: float,
    tail_sec: float = DEFAULT_TAIL_SEC,
    fixed_duration_sec: float | None = None,
) -> float:
    """Compute the final output duration for a render given an end-tail policy.

    narration_duration_sec may be None/0 when there is no narration (voice
    disabled); in that case the visual timeline always wins regardless of
    policy, since there is nothing to align the tail against.
    """
    if policy_id not in END_POLICIES:
        raise EndTailPolicyError(f"policy_id must be one of {sorted(END_POLICIES)}, got {policy_id!r}.")
    visual_duration_sec = max(0.0, float(visual_duration_sec))
    narration = float(narration_duration_sec) if narration_duration_sec else 0.0

    if policy_id == END_POLICY_FIXED_DURATION:
        if fixed_duration_sec is None:
            raise EndTailPolicyError("fixed_duration_sec is required for the fixed_duration policy.")
        return max(0.0, float(fixed_duration_sec))

    if narration <= 0.0:
        return visual_duration_sec

    if policy_id == END_POLICY_MATCH_NARRATION:
        return narration
    if policy_id == END_POLICY_NARRATION_PLUS_TAIL:
        return narration + clamp_tail_sec(tail_sec)
    # preserve_visual_timeline
    return visual_duration_sec


def narration_duration_from_voice_manifest(voice_manifest: dict[str, Any] | None) -> float:
    """Read the real assembled-narration duration from a voice_manifest dict.

    Supports both the schema_version=2 shape (``narration.duration_sec``,
    written by src.audio.audio_assembler) and the legacy/manual-audio shape
    (top-level ``duration_sec``, written by src.audio.voice_workflow.import_manual_audio).
    """
    manifest = voice_manifest or {}
    narration = manifest.get("narration")
    if isinstance(narration, dict) and narration.get("duration_sec"):
        return float(narration["duration_sec"])
    if manifest.get("duration_sec"):
        return float(manifest["duration_sec"])
    return 0.0
