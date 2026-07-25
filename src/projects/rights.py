"""One read-only rights view over the manifests a project already writes.

What this answers
----------------
For one finished (or half-finished) project: which materials are actually used,
where each came from, under what licence, and - honestly - which ones we cannot
prove the right to use at all.

Where the data really lives (verified against the repository, 2026-07-25)
-------------------------------------------------------------------------
- ``assets/assets_manifest.json`` -> ``scenes[].selected_asset`` is the primary and,
  for 20 of the 21 projects on disk, the *only* real source. It already carries
  provider, provider_asset_id, source_page_url, download_url, author, license,
  rights_status, allowed_for_render, review_required, checksum_sha256 and local_path.
- ``assets/missing_assets.json`` lists scenes that ended up with no material at all.
  A rights report that hides those would be misleading, so they are first-class here.
- ``assets/music/music_manifest.json`` (written by src.audio.music_manifest) carries a
  deliberately unverified rights record for a user-supplied track.
- ``assets/sources.json`` is a derived attribution export: read only as a fallback for
  material the assets manifest did not already describe.
- ``evidence/evidence_manifest.json`` / EvidenceBundle is where the Story Card
  workflow records the visual it actually rendered (Stage C3). News projects still
  do not write it - their provenance lives in the assets manifest above - so this
  reader remains one of several rather than the primary one. Records written before
  Stage C3 (schema v1) are read exactly as they were.

Deliberate non-goals
--------------------
Strictly read-only: no file in the project is created, modified or deleted. This is
not a new evidence store and not a second rights model - it normalizes what already
exists so the CLI and a future UI can ask one question instead of four.

A generated report is **not** a legal clearance: "unknown" and "review_required" mean
a human still has to look, and a present local file proves nothing about rights.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.project_foundation.models import (
    MEDIA_ROLE_MUSIC,
    MEDIA_ROLE_OTHER,
    MEDIA_ROLE_VISUAL,
    MEDIA_ROLE_VOICE,
    VERIFICATION_BLOCKED,
    VERIFICATION_REVIEW_REQUIRED,
    VERIFICATION_UNKNOWN,
    VERIFICATION_VERIFIED,
)

from .repository import PROJECT_KIND_NEWS_JOB, PROJECT_KIND_PROJECT_MANIFEST, _read_json

# Re-exported (see __all__) so existing importers of src.projects.rights keep working;
# the values themselves now live next to EvidenceRecord, which stores them.

# Ordered worst-first: used to fold many item statuses into one project status.
_STATUS_SEVERITY = {
    VERIFICATION_BLOCKED: 3,
    VERIFICATION_REVIEW_REQUIRED: 2,
    VERIFICATION_UNKNOWN: 1,
    VERIFICATION_VERIFIED: 0,
}

SOURCE_ASSETS_MANIFEST = "assets/assets_manifest.json"
SOURCE_MISSING_ASSETS = "assets/missing_assets.json"
SOURCE_MUSIC_MANIFEST = "assets/music/music_manifest.json"
SOURCE_SOURCES_JSON = "assets/sources.json"
SOURCE_EVIDENCE_MANIFEST = "evidence/evidence_manifest.json"


@dataclass
class RightsItem:
    """One material actually used by the project."""

    item_id: str
    media_role: str = MEDIA_ROLE_OTHER
    scene_id: str = ""
    asset_id: str = ""
    media_type: str = ""
    provider: str = ""
    provider_asset_id: str = ""
    source_page_url: str = ""
    download_url: str = ""
    author: str = ""
    license_name: str = ""
    license_url: str = ""
    commercial_use_status: str = "unknown"
    attribution_required: bool = False
    attribution_text: str = ""
    checksum_sha256: str = ""
    local_path: str = ""
    local_file_present: bool = False
    verification_status: str = VERIFICATION_UNKNOWN
    allowed_for_render: bool = False
    review_required: bool = False
    proof_files: list[str] = field(default_factory=list)
    source_manifest: str = ""
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "media_role": self.media_role,
            "scene_id": self.scene_id,
            "asset_id": self.asset_id,
            "media_type": self.media_type,
            "provider": self.provider,
            "provider_asset_id": self.provider_asset_id,
            "source_page_url": self.source_page_url,
            "download_url": self.download_url,
            "author": self.author,
            "license_name": self.license_name,
            "license_url": self.license_url,
            "commercial_use_status": self.commercial_use_status,
            "attribution_required": self.attribution_required,
            "attribution_text": self.attribution_text,
            "checksum_sha256": self.checksum_sha256,
            "local_path": self.local_path,
            "local_file_present": self.local_file_present,
            "verification_status": self.verification_status,
            "allowed_for_render": self.allowed_for_render,
            "review_required": self.review_required,
            "proof_files": list(self.proof_files),
            "source_manifest": self.source_manifest,
            "warnings": list(self.warnings),
        }


@dataclass
class MissingSceneRecord:
    """A scene the pipeline could not find any usable material for."""

    scene_id: str
    reason: str = ""
    query: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"scene_id": self.scene_id, "reason": self.reason, "query": self.query}


@dataclass
class RightsSummary:
    total: int = 0
    verified: int = 0
    review_required: int = 0
    blocked: int = 0
    unknown: int = 0
    visual_items: int = 0
    music_items: int = 0
    other_items: int = 0
    scenes_without_asset: int = 0
    items_missing_source: int = 0
    items_missing_license: int = 0
    items_missing_checksum: int = 0
    items_missing_local_file: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "verified": self.verified,
            "review_required": self.review_required,
            "blocked": self.blocked,
            "unknown": self.unknown,
            "visual_items": self.visual_items,
            "music_items": self.music_items,
            "other_items": self.other_items,
            "scenes_without_asset": self.scenes_without_asset,
            "items_missing_source": self.items_missing_source,
            "items_missing_license": self.items_missing_license,
            "items_missing_checksum": self.items_missing_checksum,
            "items_missing_local_file": self.items_missing_local_file,
        }


@dataclass
class ProjectRightsReport:
    project_id: str
    project_kind: str
    project_root: str
    overall_status: str = VERIFICATION_UNKNOWN
    items: list[RightsItem] = field(default_factory=list)
    missing_scenes: list[MissingSceneRecord] = field(default_factory=list)
    summary: RightsSummary = field(default_factory=RightsSummary)
    sources_read: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    # Everything the pre-Stage-C2 command used to print for project.json projects,
    # preserved verbatim so nothing that was previously available is lost.
    evidence_bundle_report: dict[str, Any] = field(default_factory=dict)

    @property
    def has_blocking_problems(self) -> bool:
        """Drives the CLI exit code: blocked material or a scene with nothing to show."""
        return self.summary.blocked > 0 or bool(self.missing_scenes)

    def items_needing_attention(self) -> list[RightsItem]:
        return [item for item in self.items if item.verification_status != VERIFICATION_VERIFIED]

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "project_kind": self.project_kind,
            "project_root": self.project_root,
            "overall_status": self.overall_status,
            "has_blocking_problems": self.has_blocking_problems,
            "summary": self.summary.to_dict(),
            "items": [item.to_dict() for item in self.items],
            "missing_scenes": [scene.to_dict() for scene in self.missing_scenes],
            "sources_read": list(self.sources_read),
            "warnings": list(self.warnings),
            "evidence_bundle_report": dict(self.evidence_bundle_report),
        }


# ---------------------------------------------------------------------------
# Status rules
# ---------------------------------------------------------------------------


def classify_rights(
    *,
    allowed_for_render: Any,
    review_required: Any,
    license_name: str,
    source_url: str,
    checksum: str,
) -> str:
    """Map one material's recorded facts onto the canonical verification statuses.

    Deliberately pessimistic: a material only reaches "verified" when it is cleared
    for render *and* we can point at a licence, a source and a checksum. Anything
    partial is review_required; nothing at all is unknown. A present local file and
    a present source URL are never on their own treated as permission.
    """
    if allowed_for_render is False:
        return VERIFICATION_BLOCKED
    if review_required is True:
        return VERIFICATION_REVIEW_REQUIRED
    known = [bool(license_name), bool(source_url), bool(checksum)]
    if all(known):
        return VERIFICATION_VERIFIED if allowed_for_render is True else VERIFICATION_REVIEW_REQUIRED
    if not any(known):
        return VERIFICATION_UNKNOWN
    return VERIFICATION_REVIEW_REQUIRED


def _worst_status(statuses: list[str]) -> str:
    if not statuses:
        return VERIFICATION_UNKNOWN
    return max(statuses, key=lambda status: _STATUS_SEVERITY.get(status, 1))


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------


def _normalize_url(url: str) -> str:
    return str(url or "").strip().rstrip("/").lower()


def dedup_keys(item: RightsItem) -> list[str]:
    """Identity candidates, strongest first.

    A shared filename is intentionally not a key: two different materials can easily
    be called scene_001.mp4.
    """
    keys: list[str] = []
    if item.checksum_sha256:
        keys.append(f"checksum:{item.checksum_sha256.lower()}")
    if item.provider and item.provider_asset_id:
        keys.append(f"provider:{item.provider.lower()}:{item.provider_asset_id}")
    if item.source_page_url:
        keys.append(f"url:{_normalize_url(item.source_page_url)}")
    if item.asset_id:
        keys.append(f"asset:{item.asset_id}")
    if item.local_path:
        keys.append(f"path:{Path(item.local_path).as_posix().lower()}")
    return keys


def contradicts(first: RightsItem, second: RightsItem) -> bool:
    """True when two items are provably *different* materials.

    A weak key can accidentally collide - two clips can share a source page, and a
    provider can host several assets under one landing URL. When a stronger identity
    (checksum, or provider + provider_asset_id) is present on both sides and
    disagrees, that wins: the weaker match must not merge them.
    """
    if (
        first.checksum_sha256
        and second.checksum_sha256
        and first.checksum_sha256.lower() != second.checksum_sha256.lower()
    ):
        return True
    if first.provider and second.provider and first.provider_asset_id and second.provider_asset_id:
        if (first.provider.lower(), first.provider_asset_id) != (second.provider.lower(), second.provider_asset_id):
            return True
    return False


class _Deduplicator:
    """First writer wins: the primary manifest describes a material fully, later
    sources only fill gaps for materials nobody described yet."""

    def __init__(self) -> None:
        self._seen: dict[str, RightsItem] = {}
        self.items: list[RightsItem] = []

    def add(self, item: RightsItem) -> bool:
        keys = dedup_keys(item)
        for key in keys:
            existing = self._seen.get(key)
            if existing is None or contradicts(existing, item):
                continue
            if item.scene_id and item.scene_id not in existing.scene_id:
                existing.scene_id = ", ".join(filter(None, [existing.scene_id, item.scene_id]))
            return False
        for key in keys:
            # Never let a weaker duplicate steal a key that already identifies a
            # different material - the first, better-described item keeps it.
            self._seen.setdefault(key, item)
        self.items.append(item)
        return True


# ---------------------------------------------------------------------------
# Readers - one per manifest that really exists
# ---------------------------------------------------------------------------


def _as_bool(value: Any) -> Any:
    """Preserve the difference between False and 'not recorded'."""
    return value if isinstance(value, bool) else None


def _visual_item_from_selected_asset(selected: dict[str, Any], scene_id: str) -> RightsItem:
    license_block = selected.get("license") if isinstance(selected.get("license"), dict) else {}
    provenance = selected.get("provenance") if isinstance(selected.get("provenance"), dict) else {}

    license_name = str(selected.get("license_name") or license_block.get("license_name") or "")
    source_page = str(
        selected.get("source_page_url") or selected.get("source_page") or provenance.get("source_page_url") or ""
    )
    checksum = str(selected.get("checksum_sha256") or provenance.get("checksum_sha256") or "")
    local_path = str(selected.get("local_path") or selected.get("path") or selected.get("downloaded_path") or "")

    allowed = _as_bool(selected.get("allowed_for_render"))
    if allowed is None:
        allowed = _as_bool(license_block.get("allowed_for_render"))
    review = _as_bool(selected.get("review_required"))
    if review is None:
        review = _as_bool(license_block.get("review_required"))

    commercial = license_block.get("commercial_use_allowed")
    commercial_status = (
        "allowed" if commercial is True else "not_allowed" if commercial is False else "unknown"
    )

    warnings: list[str] = []
    local_present = bool(local_path) and Path(local_path).is_file()
    if local_path and not local_present:
        warnings.append("Локальный файл не найден на диске.")
    if not source_page:
        warnings.append("Не записана ссылка на страницу-источник.")
    if not license_name:
        warnings.append("Не записано название лицензии.")
    if not checksum:
        warnings.append("Не записана контрольная сумма файла.")

    item = RightsItem(
        item_id=str(selected.get("asset_id") or f"{scene_id}_asset"),
        media_role=MEDIA_ROLE_VISUAL,
        scene_id=scene_id,
        asset_id=str(selected.get("asset_id") or ""),
        media_type=str(selected.get("media_type") or selected.get("type") or ""),
        provider=str(selected.get("provider") or provenance.get("provider") or ""),
        provider_asset_id=str(selected.get("provider_asset_id") or provenance.get("provider_asset_id") or ""),
        source_page_url=source_page,
        download_url=str(selected.get("download_url") or provenance.get("download_url") or ""),
        author=str(selected.get("author") or selected.get("author_name") or ""),
        license_name=license_name,
        license_url=str(selected.get("license_url") or license_block.get("license_url") or ""),
        commercial_use_status=commercial_status,
        attribution_required=bool(license_block.get("attribution_required", False)),
        attribution_text=str(license_block.get("attribution_text") or ""),
        checksum_sha256=checksum,
        local_path=local_path,
        local_file_present=local_present,
        allowed_for_render=allowed is True,
        review_required=review is True,
        source_manifest=SOURCE_ASSETS_MANIFEST,
        warnings=warnings,
    )
    item.verification_status = classify_rights(
        allowed_for_render=allowed,
        review_required=review,
        license_name=license_name,
        source_url=source_page,
        checksum=checksum,
    )
    return item


def _music_item(manifest: dict[str, Any]) -> RightsItem:
    license_block = manifest.get("license") if isinstance(manifest.get("license"), dict) else {}
    local_path = str(manifest.get("path") or "")
    local_present = bool(local_path) and Path(local_path).is_file()
    commercial_status = str(license_block.get("commercial_use_status") or "unknown")
    license_name = str(license_block.get("name") or "")
    source_url = str(license_block.get("url") or "")

    warnings = ["Права на музыкальный файл не проверялись автоматически."]
    if local_path and not local_present:
        warnings.append("Музыкальный файл не найден на диске.")

    item = RightsItem(
        item_id=f"music:{manifest.get('original_filename') or local_path or 'track'}",
        media_role=MEDIA_ROLE_MUSIC,
        media_type="audio",
        provider=str(manifest.get("source") or ""),
        license_name=license_name,
        license_url=source_url,
        commercial_use_status=commercial_status,
        attribution_required=bool(license_block.get("attribution_required", False)),
        attribution_text=str(license_block.get("attribution_text") or ""),
        checksum_sha256=str(manifest.get("checksum_sha256") or ""),
        local_path=local_path,
        local_file_present=local_present,
        source_manifest=SOURCE_MUSIC_MANIFEST,
        warnings=warnings,
    )
    # A user-supplied track is never "verified": we have a checksum and a file, but no
    # licence and no source, which classify_rights maps to review_required by design.
    item.verification_status = classify_rights(
        allowed_for_render=None,
        review_required=None,
        license_name=license_name,
        source_url=source_url,
        checksum=item.checksum_sha256,
    )
    if item.verification_status == VERIFICATION_VERIFIED and commercial_status != "allowed":
        item.verification_status = VERIFICATION_REVIEW_REQUIRED
    return item


def _item_from_sources_entry(entry: dict[str, Any]) -> RightsItem:
    source_page = str(entry.get("source_page") or entry.get("source_page_url") or "")
    license_name = str(entry.get("license_name") or "")
    item = RightsItem(
        item_id=str(entry.get("asset_id") or source_page or entry.get("provider") or "source_entry"),
        media_role=MEDIA_ROLE_VISUAL,
        asset_id=str(entry.get("asset_id") or ""),
        provider=str(entry.get("provider") or ""),
        provider_asset_id=str(entry.get("provider_asset_id") or ""),
        source_page_url=source_page,
        author=str(entry.get("author") or ""),
        license_name=license_name,
        license_url=str(entry.get("license_url") or ""),
        attribution_text=str(entry.get("attribution_text") or ""),
        checksum_sha256=str(entry.get("checksum_sha256") or ""),
        source_manifest=SOURCE_SOURCES_JSON,
        warnings=["Описан только в производном файле attribution, не в основном манифесте ассетов."],
    )
    item.verification_status = classify_rights(
        allowed_for_render=None,
        review_required=None,
        license_name=license_name,
        source_url=source_page,
        checksum=item.checksum_sha256,
    )
    return item


def _item_from_evidence_record(record: dict[str, Any]) -> RightsItem:
    """Read one EvidenceRecord, v1 or v2.

    A v1 record has no media_role and no explicit allowed_for_render/review_required,
    so those keep the values this reader has always derived: role "other", and both
    flags read off the verification status. A v2 record (written by the Story Card
    workflow) states them, and then they are used as recorded.
    """
    status = str(record.get("verification_status") or VERIFICATION_UNKNOWN)
    status = status if status in _STATUS_SEVERITY else VERIFICATION_UNKNOWN

    local_path = str(record.get("local_path") or "")
    warnings: list[str] = []
    if local_path and not Path(local_path).is_file():
        warnings.append("Локальный файл не найден на диске.")
    if str(record.get("source_type") or "") == "user_supplied":
        warnings.append(
            "Файл предоставлен пользователем: права не проверялись автоматически. "
            "Перед публикацией подтвердите право на коммерческое использование."
        )

    item = RightsItem(
        item_id=str(record.get("evidence_id") or record.get("asset_id") or "evidence"),
        media_role=str(record.get("media_role") or MEDIA_ROLE_OTHER),
        asset_id=str(record.get("asset_id") or ""),
        media_type=str(record.get("media_type") or ""),
        provider=str(record.get("provider") or ""),
        provider_asset_id=str(record.get("provider_asset_id") or ""),
        source_page_url=str(record.get("source_url") or ""),
        download_url=str(record.get("download_url") or ""),
        author=str(record.get("author") or ""),
        license_name=str(record.get("license_name") or ""),
        license_url=str(record.get("license_url") or ""),
        commercial_use_status=str(record.get("commercial_use_status") or "unknown"),
        attribution_required=bool(record.get("attribution_required", False)),
        attribution_text=str(record.get("attribution_text") or ""),
        checksum_sha256=str(record.get("checksum_sha256") or ""),
        local_path=local_path,
        proof_files=[str(path) for path in (record.get("proof_files") or [])],
        source_manifest=SOURCE_EVIDENCE_MANIFEST,
        warnings=warnings,
    )
    item.local_file_present = bool(item.local_path) and Path(item.local_path).is_file()
    # EvidenceRecord already carries a human-set verification_status - trust it.
    item.verification_status = status
    item.allowed_for_render = bool(record.get("allowed_for_render", status == VERIFICATION_VERIFIED))
    item.review_required = bool(record.get("review_required", status == VERIFICATION_REVIEW_REQUIRED))
    return item


# ---------------------------------------------------------------------------
# Report builder
# ---------------------------------------------------------------------------


def build_rights_report(
    *, project_id: str, project_root: str | Path, project_kind: str = PROJECT_KIND_NEWS_JOB
) -> ProjectRightsReport:
    """Read every rights-bearing manifest a project has and normalize them.

    Never raises for missing or corrupt files: each problem becomes a warning and,
    where it matters, an "unknown" status. Writes nothing.
    """
    root = Path(project_root)
    report = ProjectRightsReport(
        project_id=str(project_id), project_kind=str(project_kind), project_root=str(root)
    )
    dedup = _Deduplicator()

    # 1. Primary source: the visual material actually selected per scene.
    assets_path = root / "assets" / "assets_manifest.json"
    if assets_path.is_file():
        report.sources_read.append(SOURCE_ASSETS_MANIFEST)
        assets_manifest = _read_json(assets_path)
        if assets_manifest is None:
            report.warnings.append(f"{SOURCE_ASSETS_MANIFEST}: файл повреждён и не прочитан как JSON.")
        else:
            for scene in assets_manifest.get("scenes") or []:
                if not isinstance(scene, dict):
                    continue
                selected = scene.get("selected_asset")
                if not isinstance(selected, dict) or not selected:
                    continue
                dedup.add(_visual_item_from_selected_asset(selected, str(scene.get("scene_id") or "")))

    # 2. Scenes with no material at all - never hidden.
    missing_path = root / "assets" / "missing_assets.json"
    if missing_path.is_file():
        report.sources_read.append(SOURCE_MISSING_ASSETS)
        missing_manifest = _read_json(missing_path)
        if missing_manifest is None:
            report.warnings.append(f"{SOURCE_MISSING_ASSETS}: файл повреждён и не прочитан как JSON.")
        else:
            for entry in missing_manifest.get("missing_scenes") or []:
                if isinstance(entry, dict):
                    report.missing_scenes.append(
                        MissingSceneRecord(
                            scene_id=str(entry.get("scene_id") or ""),
                            reason=str(entry.get("reason") or ""),
                            query=str(entry.get("primary_query") or ""),
                        )
                    )
                elif entry:
                    report.missing_scenes.append(MissingSceneRecord(scene_id=str(entry)))

    # 3. Music bed, if one was configured.
    music_path = root / "assets" / "music" / "music_manifest.json"
    if music_path.is_file():
        report.sources_read.append(SOURCE_MUSIC_MANIFEST)
        music_manifest = _read_json(music_path)
        if music_manifest is None:
            report.warnings.append(f"{SOURCE_MUSIC_MANIFEST}: файл повреждён и не прочитан как JSON.")
        elif music_manifest.get("path"):
            dedup.add(_music_item(music_manifest))

    # 4. Derived attribution export - only fills gaps.
    sources_path = root / "assets" / "sources.json"
    if sources_path.is_file():
        report.sources_read.append(SOURCE_SOURCES_JSON)
        sources_manifest = _read_json(sources_path)
        if sources_manifest is None:
            report.warnings.append(f"{SOURCE_SOURCES_JSON}: файл повреждён и не прочитан как JSON.")
        else:
            for entry in sources_manifest.get("assets") or []:
                if isinstance(entry, dict) and entry:
                    dedup.add(_item_from_sources_entry(entry))

    # 5. EvidenceBundle - supported for compatibility; no production code fills it yet.
    evidence_path = root / "evidence" / "evidence_manifest.json"
    if evidence_path.is_file():
        report.sources_read.append(SOURCE_EVIDENCE_MANIFEST)
        evidence_manifest = _read_json(evidence_path)
        if evidence_manifest is None:
            report.warnings.append(f"{SOURCE_EVIDENCE_MANIFEST}: файл повреждён и не прочитан как JSON.")
        else:
            for record in evidence_manifest.get("records") or []:
                if isinstance(record, dict) and record:
                    dedup.add(_item_from_evidence_record(record))

    report.items = dedup.items
    report.summary = _summarize(report)
    report.overall_status = _overall_status(report)

    if not report.items and not report.missing_scenes:
        report.warnings.append(
            "Не найдено ни одной записи о материалах. Права по этому проекту подтвердить нельзя."
        )
    if project_kind == PROJECT_KIND_PROJECT_MANIFEST and not evidence_path.is_file():
        report.warnings.append(
            "У проекта нет evidence_manifest.json. Так выглядят story-card проекты, "
            "созданные до того, как workflow начал записывать provenance: подтвердить "
            "права по ним нельзя."
        )
    return report


def _summarize(report: ProjectRightsReport) -> RightsSummary:
    summary = RightsSummary(total=len(report.items), scenes_without_asset=len(report.missing_scenes))
    for item in report.items:
        if item.verification_status == VERIFICATION_VERIFIED:
            summary.verified += 1
        elif item.verification_status == VERIFICATION_REVIEW_REQUIRED:
            summary.review_required += 1
        elif item.verification_status == VERIFICATION_BLOCKED:
            summary.blocked += 1
        else:
            summary.unknown += 1

        if item.media_role == MEDIA_ROLE_VISUAL:
            summary.visual_items += 1
        elif item.media_role == MEDIA_ROLE_MUSIC:
            summary.music_items += 1
        else:
            summary.other_items += 1

        if not item.source_page_url:
            summary.items_missing_source += 1
        if not item.license_name:
            summary.items_missing_license += 1
        if not item.checksum_sha256:
            summary.items_missing_checksum += 1
        if item.local_path and not item.local_file_present:
            summary.items_missing_local_file += 1
    return summary


def _overall_status(report: ProjectRightsReport) -> str:
    # A required scene with no material is as blocking as a forbidden asset: the video
    # cannot be produced honestly either way.
    if report.missing_scenes:
        return VERIFICATION_BLOCKED
    if not report.items:
        return VERIFICATION_UNKNOWN
    return _worst_status([item.verification_status for item in report.items])


__all__ = [
    "MEDIA_ROLE_MUSIC",
    "MEDIA_ROLE_OTHER",
    "MEDIA_ROLE_VISUAL",
    "MEDIA_ROLE_VOICE",
    "MissingSceneRecord",
    "ProjectRightsReport",
    "RightsItem",
    "RightsSummary",
    "build_rights_report",
    "classify_rights",
    "contradicts",
    "dedup_keys",
]
