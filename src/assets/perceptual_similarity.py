from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .frame_primitives import SampledFrame, image_perceptual_hash, sha256_file


@dataclass
class PerceptualSignature:
    asset_id: str
    media_type: str
    frame_hashes: list[str] = field(default_factory=list)
    frame_sha256: list[str] = field(default_factory=list)
    source_sha256: str = ""
    algorithm: str = "dhash_8x8"
    status: str = "passed"
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclass
class SimilarityResult:
    compared_asset_ids: list[str]
    hash_distance: int = 0
    frame_level_distances: list[int] = field(default_factory=list)
    aggregate_similarity: float = 0.0
    threshold: int = 6
    classification: str = "insufficient_data"
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


def hamming_distance(first: str, second: str) -> int:
    if not first or not second:
        return 64
    width = max(len(first), len(second))
    a = int(first.zfill(width), 16)
    b = int(second.zfill(width), 16)
    return (a ^ b).bit_count()


def signature_from_image(asset_id: str, path: str | Path) -> PerceptualSignature:
    target = Path(path)
    try:
        return PerceptualSignature(
            asset_id=asset_id,
            media_type="image",
            frame_hashes=[image_perceptual_hash(target)],
            frame_sha256=[sha256_file(target)],
            source_sha256=sha256_file(target),
        )
    except Exception as exc:
        return PerceptualSignature(asset_id=asset_id, media_type="image", status="failed", error=str(exc))


def signature_from_frames(asset_id: str, frames: list[SampledFrame], *, media_type: str = "video") -> PerceptualSignature:
    hashes: list[str] = []
    checksums: list[str] = []
    errors: list[str] = []
    for frame in frames:
        if frame.extraction_status != "extracted" or not frame.local_frame_path:
            if frame.extraction_error:
                errors.append(frame.extraction_error)
            continue
        frame_hash = frame.perceptual_hash
        if not frame_hash:
            try:
                frame_hash = image_perceptual_hash(frame.local_frame_path)
            except Exception as exc:
                errors.append(str(exc))
                continue
        hashes.append(frame_hash)
        checksums.append(frame.sha256 or sha256_file(frame.local_frame_path))
    status = "passed" if hashes else "failed"
    return PerceptualSignature(
        asset_id=asset_id,
        media_type=media_type,
        frame_hashes=hashes,
        frame_sha256=checksums,
        source_sha256=checksums[0] if len(set(checksums)) == 1 and checksums else "",
        status=status,
        error="; ".join(errors),
    )


def compare_signatures(
    first: PerceptualSignature,
    second: PerceptualSignature,
    *,
    near_threshold: int = 6,
    similar_threshold: int = 20,
) -> SimilarityResult:
    ids = [first.asset_id, second.asset_id]
    if not first.frame_hashes or not second.frame_hashes:
        return SimilarityResult(ids, threshold=near_threshold, classification="insufficient_data", reason="missing_perceptual_hash")
    shared_sha = set(item for item in first.frame_sha256 if item) & set(item for item in second.frame_sha256 if item)
    if shared_sha or (first.source_sha256 and first.source_sha256 == second.source_sha256):
        return SimilarityResult(
            ids,
            hash_distance=0,
            frame_level_distances=[0],
            aggregate_similarity=1.0,
            threshold=near_threshold,
            classification="exact_duplicate",
            reason="sha256_match",
        )
    distances = _frame_distances(first.frame_hashes, second.frame_hashes)
    if not distances:
        return SimilarityResult(ids, threshold=near_threshold, classification="insufficient_data", reason="no_comparable_frames")
    mean_distance = sum(distances) / len(distances)
    similarity = max(0.0, min(1.0, 1.0 - (mean_distance / 64.0)))
    min_distance = min(distances)
    if min_distance <= near_threshold:
        classification = "near_duplicate"
        reason = "perceptual_hash_distance_within_near_threshold"
    elif mean_distance <= similar_threshold:
        classification = "visually_similar"
        reason = "aggregate_hash_distance_within_similar_threshold"
    else:
        classification = "not_similar"
        reason = "hash_distance_above_threshold"
    return SimilarityResult(
        ids,
        hash_distance=int(round(mean_distance)),
        frame_level_distances=distances,
        aggregate_similarity=similarity,
        threshold=near_threshold,
        classification=classification,
        reason=reason,
    )


def _frame_distances(first: list[str], second: list[str]) -> list[int]:
    count = min(len(first), len(second))
    if count <= 0:
        return []
    return [hamming_distance(first[index], second[index]) for index in range(count)]
