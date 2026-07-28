from __future__ import annotations

from typing import Any


RIGHTS_STATUS_LABELS = {
    "verified": "подтверждено",
    "review_required": "требует проверки",
    "blocked": "заблокировано",
    "unknown": "нет данных",
}


def print_rights_lines(evidence: dict[str, Any], *, prefix: str = "") -> None:
    """Print the short rights summary shared by CLI and terminal wizard."""
    if not evidence or not evidence.get("evidence_manifest_path"):
        return
    status = str(evidence.get("rights_status") or "unknown")
    print(f"{prefix}rights_status={RIGHTS_STATUS_LABELS.get(status, status)}")
    print(f"{prefix}evidence_path={evidence['evidence_manifest_path']}")
    print(f"{prefix}source_type={evidence.get('source_type') or '-'}")
    print(
        f"{prefix}review_required="
        f"{'да' if evidence.get('review_required') else 'нет'}"
    )


__all__ = ["RIGHTS_STATUS_LABELS", "print_rights_lines"]
