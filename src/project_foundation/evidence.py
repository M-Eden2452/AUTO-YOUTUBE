from __future__ import annotations

from pathlib import Path
from typing import Any

from .models import (
    SCHEMA_VERSION,
    EvidenceRecord,
    EvidenceSummary,
    ProjectFoundationError,
    VERIFICATION_BLOCKED,
    VERIFICATION_REVIEW_REQUIRED,
    VERIFICATION_UNKNOWN,
    VERIFICATION_VERIFIED,
    utc_now_iso,
)
from .storage import atomic_write_json, read_json_if_exists

EVIDENCE_MANIFEST_FILENAME = "evidence_manifest.json"
RIGHTS_REPORT_FILENAME = "rights_report.json"


class EvidenceBundle:
    """Ordered collection of EvidenceRecord entries for a single project.

    Never downloads or copies proof files - it only stores references and metadata.
    """

    def __init__(self, project_id: str) -> None:
        self.project_id = str(project_id or "")
        if not self.project_id:
            raise ProjectFoundationError("EvidenceBundle requires a non-empty project_id.")
        self._records: dict[str, EvidenceRecord] = {}

    def add(self, record: EvidenceRecord, *, overwrite: bool = False) -> EvidenceRecord:
        if not isinstance(record, EvidenceRecord):
            raise ProjectFoundationError("EvidenceBundle.add requires an EvidenceRecord instance.")
        if record.evidence_id in self._records and not overwrite:
            raise ProjectFoundationError(
                f"Evidence record {record.evidence_id!r} already exists in project {self.project_id!r}. "
                "Pass overwrite=True to replace it explicitly."
            )
        self._records[record.evidence_id] = record
        return record

    def get(self, evidence_id: str) -> EvidenceRecord:
        record = self._records.get(evidence_id)
        if record is None:
            raise ProjectFoundationError(f"Evidence record {evidence_id!r} was not found in project {self.project_id!r}.")
        return record

    def get_by_asset_id(self, asset_id: str) -> list[EvidenceRecord]:
        return [record for record in self._records.values() if record.asset_id == asset_id]

    def list(self) -> list[EvidenceRecord]:
        return list(self._records.values())

    def __len__(self) -> int:
        return len(self._records)

    def validate(self) -> list[str]:
        errors: list[str] = []
        seen_evidence_ids: set[str] = set()
        for record in self._records.values():
            if record.evidence_id in seen_evidence_ids:
                errors.append(f"Duplicate evidence_id: {record.evidence_id!r}.")
            seen_evidence_ids.add(record.evidence_id)

            if record.verification_status == VERIFICATION_VERIFIED:
                if not record.source_url:
                    errors.append(f"{record.evidence_id}: verified evidence must have a source_url.")
                if not record.license_name:
                    errors.append(f"{record.evidence_id}: verified evidence must have a license_name.")
                if not record.checksum_sha256:
                    errors.append(f"{record.evidence_id}: verified evidence must have a checksum_sha256.")

            if record.checksum_sha256 and len(record.checksum_sha256) != 64:
                errors.append(f"{record.evidence_id}: checksum_sha256 must be 64 hex characters if present.")

            if record.attribution_required and not record.attribution_text:
                errors.append(f"{record.evidence_id}: attribution_required is true but attribution_text is empty.")

        return errors

    def summary(self) -> EvidenceSummary:
        summary = EvidenceSummary(total=len(self._records))
        for record in self._records.values():
            if record.verification_status == VERIFICATION_VERIFIED:
                summary.verified += 1
            elif record.verification_status == VERIFICATION_REVIEW_REQUIRED:
                summary.review_required += 1
            elif record.verification_status == VERIFICATION_BLOCKED:
                summary.blocked += 1
            else:
                summary.unknown += 1
        return summary

    def to_manifest_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "schema_version": SCHEMA_VERSION,
            "updated_at": utc_now_iso(),
            "records": [record.to_dict() for record in self._records.values()],
        }

    @staticmethod
    def _evidence_dir(project_root: str | Path) -> Path:
        return Path(project_root) / "evidence"

    @classmethod
    def manifest_path(cls, project_root: str | Path) -> Path:
        return cls._evidence_dir(project_root) / EVIDENCE_MANIFEST_FILENAME

    @classmethod
    def rights_report_path(cls, project_root: str | Path) -> Path:
        return cls._evidence_dir(project_root) / RIGHTS_REPORT_FILENAME

    @classmethod
    def load(cls, project_root: str | Path, project_id: str) -> EvidenceBundle:
        bundle = cls(project_id=project_id)
        data = read_json_if_exists(cls.manifest_path(project_root))
        if data is None:
            return bundle
        for raw_record in data.get("records", []):
            bundle.add(EvidenceRecord.from_dict(raw_record))
        return bundle

    def save(self, project_root: str | Path) -> Path:
        target = self.manifest_path(project_root)
        atomic_write_json(target, self.to_manifest_dict())
        return target

    def rights_report(self) -> dict[str, Any]:
        summary = self.summary()
        by_provider: dict[str, int] = {}
        by_license: dict[str, int] = {}
        needs_attention: list[dict[str, Any]] = []
        for record in self._records.values():
            provider_key = record.provider or "unknown_provider"
            license_key = record.license_name or "unknown_license"
            by_provider[provider_key] = by_provider.get(provider_key, 0) + 1
            by_license[license_key] = by_license.get(license_key, 0) + 1
            if record.verification_status in (VERIFICATION_BLOCKED, VERIFICATION_REVIEW_REQUIRED, VERIFICATION_UNKNOWN):
                needs_attention.append(
                    {
                        "evidence_id": record.evidence_id,
                        "asset_id": record.asset_id,
                        "verification_status": record.verification_status,
                        "license_name": record.license_name,
                        "provider": record.provider,
                    }
                )
        return {
            "project_id": self.project_id,
            "schema_version": SCHEMA_VERSION,
            "generated_at": utc_now_iso(),
            "summary": summary.to_dict(),
            "by_provider": by_provider,
            "by_license": by_license,
            "needs_attention": needs_attention,
        }

    def save_rights_report(self, project_root: str | Path) -> Path:
        target = self.rights_report_path(project_root)
        atomic_write_json(target, self.rights_report())
        return target
