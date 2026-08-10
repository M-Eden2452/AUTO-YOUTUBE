"""The one media-selection policy: what may win a scene, and what only prefers to.

The defect this module was written for (PLAN-9C-2): production wrapped
``select_best_candidate`` in an unconditional video-first override - the first
non-rejected video *at any rank* replaced the ranker's choice. Measured on real
runs, that handed scenes to weaker material solely for being a video: LIVE-4
scene_003 lost a rank-1 hummingbird frame (80.72) to an archive video (65.75)
that nobody had previewed; scene_004 lost snow images (80.0) to a zoo video
(70.0); the PLAN-9D-C corpus shows 7 of 12 selections were first-video
overrides. No product contract ever asked for "any video at any cost" - the
scene's preferred visual kind is a hint, and this module keeps it one.

What this module is, and deliberately is not
--------------------------------------------
It is *not* a fourth selector. Ranking stays with ``select_best_candidate``;
every score, gate and decision record is produced there and reused here as-is.
This module only answers the question the ranker never owned: given the ranked
answers, which media kinds may win at all, and when may a video be preferred
over the ranker's best. Its vocabulary is the one that already exists -
``SUPPORT_RANK`` classes, the stored ``SelectionDecision``, the
mode-independent usability gate of ``src.assets.completion.modes``, and the
scene's ``allowed_media_kinds``.

The lexicographic order the policy enforces: user/author authority (upstream of
this call - a manual selection never reaches it), allowed media kinds, rights,
semantic admissibility and ranking (the ranker's verdicts, untouched), then -
and only then - a soft media preference among competitive candidates, and an
honest abstention when nothing admissible remains.

A video is *competitive* with the ranker's best candidate only when all of the
following hold, none of which is a new number:

- it passed the same hard gates (it is not rejected, and the mode-independent
  blocking gate raises nothing against it);
- it sits in the same support class as the best candidate (``SUPPORT_RANK``);
- its rights/review state is not worse than the best candidate's;
- it sits inside the declared review window - the same ``shortlist_size`` a
  human reviewer is shown. What nobody evaluated cannot silently win.

``VIDEO_ONLY`` / ``IMAGE_ONLY`` are not preferences but hard whitelists,
expressed through the scene's existing ``allowed_media_kinds`` field: when no
admissible candidate of an allowed kind exists, the scene abstains into the
ordinary review path instead of silently substituting the other kind.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .candidate_ranker import SUPPORT_RANK, select_best_candidate
from .decision import read_decision
from .models import SemanticScene

# The policy's window default equals the visual-preview shortlist default: the
# preference may only reach what a reviewer would actually be shown.
DEFAULT_REVIEW_WINDOW_SIZE = 5

# Recorded in the existing ``selected_by`` field (the same field user assets,
# the local library and the neutral backdrop already use), so the manifest says
# which branch decided without any schema change.
MEDIA_POLICY_VIDEO_PREFERENCE = "media_policy_video_preference"
MEDIA_POLICY_VIDEO_PREFERENCE_FALLBACK = "media_policy_video_preference_fallback"

# Candidate-kind vocabulary. This is the canonical home of the classifier that
# ``src.news.asset_manifest_summaries.slot_media_type`` re-exports; the sets are
# shared so the selection policy and the coverage summaries can never disagree
# about what counts as a video.
VIDEO_MEDIA_TYPES = frozenset({"video", "clip", "movie"})
IMAGE_MEDIA_TYPES = frozenset({"image", "photo", "photograph", "animated_image", "diagram"})
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v"}


def candidate_media_kind(asset: dict[str, Any]) -> str:
    """"video", "image", or "unknown" - from declared type first, file suffix second."""
    media_type = str(asset.get("media_type") or asset.get("type") or "").strip().casefold()
    if media_type in VIDEO_MEDIA_TYPES:
        return "video"
    if media_type in IMAGE_MEDIA_TYPES:
        return "image"
    path = str(
        asset.get("path") or asset.get("local_path") or asset.get("downloaded_path") or ""
    )
    suffix = Path(path).suffix.casefold()
    if suffix in VIDEO_EXTENSIONS:
        return "video"
    if suffix in IMAGE_EXTENSIONS:
        return "image"
    return "unknown"


def media_kind_restriction(allowed_media_kinds: list[str] | None) -> str:
    """The single routable kind the scene restricts itself to, or "" for none.

    Mirrors the search layer's raw membership semantics (``"image" in allowed``):
    only the two kinds the pipeline can actually route act as a whitelist, and
    only when exactly one of them is allowed. An empty or absent list restricts
    nothing - older persisted plans without the field keep their behaviour - and
    kinds outside {video, image} restrict nothing either, exactly as they gate
    nothing in retrieval today.
    """
    allowed = {
        str(kind).strip().casefold()
        for kind in (allowed_media_kinds or [])
        if str(kind).strip()
    }
    routable = allowed & {"video", "image"}
    if len(routable) == 1:
        return next(iter(routable))
    return ""


def select_with_media_policy(
    scene: SemanticScene,
    candidates: list[dict[str, Any]],
    *,
    prefer_video: bool = False,
    allowed_media_kinds: list[str] | None = None,
    review_window_size: int = DEFAULT_REVIEW_WINDOW_SIZE,
    **ranking_kwargs: Any,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """Rank with the existing owner, then apply the media policy on top.

    Called for the metadata pass and again for the post-Vision reselection -
    one owner for both, which is the PLAN-9C-2 contract. Returns the same
    ``(selected, ranked)`` shape as ``select_best_candidate``; ``ranked`` is the
    ranker's list, unchanged and in the ranker's order.
    """
    selected, ranked = select_best_candidate(scene, candidates, **ranking_kwargs)

    restriction = media_kind_restriction(allowed_media_kinds)
    if restriction:
        selected = next(
            (
                candidate
                for candidate in ranked
                if not candidate.get("rejected")
                and candidate_media_kind(candidate) == restriction
            ),
            None,
        )

    if not prefer_video or selected is None or restriction == "image":
        return selected, ranked
    if candidate_media_kind(selected) == "video":
        return selected, ranked

    window = ranked[: max(0, int(review_window_size))]
    promoted = _competitive_video(window, best=selected)
    if promoted is not None:
        promoted["selected_by"] = MEDIA_POLICY_VIDEO_PREFERENCE
        return promoted, ranked
    # The preference was asked for and no video earned it; say so in the same
    # field, but never overwrite an origin mark such as ``local_library``.
    selected.setdefault("selected_by", MEDIA_POLICY_VIDEO_PREFERENCE_FALLBACK)
    return selected, ranked


def _competitive_video(
    window: list[dict[str, Any]],
    *,
    best: dict[str, Any],
) -> dict[str, Any] | None:
    """The first video inside the review window that is competitive with ``best``.

    "Competitive" is defined by boundaries the repository already has, not by a
    score gap: the same ``SUPPORT_RANK`` class, a rights/review state that is
    not worse, and nothing raised by the mode-independent blocking gate. The
    window is scanned in the ranker's own order, so among several competitive
    videos the ranker's better one still wins.
    """
    best_decision = read_decision(best)
    best_support = SUPPORT_RANK.get(
        str(best.get("support_status") or best_decision.support_status or ""), 0
    )
    for candidate in window:
        if candidate is best or candidate.get("rejected"):
            continue
        if candidate_media_kind(candidate) != "video":
            continue
        decision = read_decision(candidate)
        support = SUPPORT_RANK.get(
            str(candidate.get("support_status") or decision.support_status or ""), 0
        )
        if support != best_support:
            continue
        if not decision.rights_allowed_for_render and best_decision.rights_allowed_for_render:
            continue
        if decision.rights_review_required and not best_decision.rights_review_required:
            continue
        if _mode_independent_blocks(candidate):
            continue
        return candidate
    return None


def _mode_independent_blocks(candidate: dict[str, Any]) -> list[str]:
    # Imported lazily on purpose: ``src.assets.completion.modes`` imports this
    # package's ``decision`` module at import time, so a top-level import here
    # would close an import cycle through the package ``__init__``. Same
    # precedent as the lazy download import inside ``modes`` itself.
    from src.assets.completion.modes import blocking_reasons

    return blocking_reasons(candidate, require_local_file=False)


__all__ = [
    "DEFAULT_REVIEW_WINDOW_SIZE",
    "IMAGE_EXTENSIONS",
    "IMAGE_MEDIA_TYPES",
    "MEDIA_POLICY_VIDEO_PREFERENCE",
    "MEDIA_POLICY_VIDEO_PREFERENCE_FALLBACK",
    "VIDEO_EXTENSIONS",
    "VIDEO_MEDIA_TYPES",
    "candidate_media_kind",
    "media_kind_restriction",
    "select_with_media_policy",
]
