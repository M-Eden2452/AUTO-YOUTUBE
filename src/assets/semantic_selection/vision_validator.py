from __future__ import annotations

from typing import Any


def validate_candidate_vision(candidate: dict[str, Any]) -> dict[str, Any]:
    """Phase 1 only consumes precomputed tags; no paid vision API calls are made here."""
    return {
        "vision_validation_enabled": False,
        "vision_tags": candidate.get("vision_tags", []),
        "objects": candidate.get("vision_objects", []),
        "reject_reason": "",
    }
