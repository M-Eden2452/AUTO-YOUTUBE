from __future__ import annotations

import json
import re
import shutil
import webbrowser
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

from src.assets.download import sha256_file, validate_local_asset
from src.assets.license_policy import apply_policy_to_candidate
from src.assets.models import AssetCandidate, AssetLicense, AssetProvenance, DownloadedAsset, ProviderCapabilities, utc_now_iso
from src.assets.provider_contract import AssetPreview, AssetSearchRequest, DownloadContext, ProviderHealth, ProviderNoResultsError


ENVATO_TERMS_URL = "https://help.elements.envato.com/hc/en-us/articles/360000629006-Envato-Elements-User-Terms"
ENVATO_LIMITS_URL = "https://help.elements.envato.com/hc/en-us/articles/360000621703-Do-any-limits-apply-to-downloads"
ENVATO_SEARCH_BASE = "https://elements.envato.com/search"


class EnvatoManualProvider:
    name = "envato_manual"

    def __init__(self, *, projects_root: str | Path = "projects", search_base: str = ENVATO_SEARCH_BASE) -> None:
        self.projects_root = Path(projects_root)
        self.search_base = search_base

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            provider=self.name,
            media_types=["image", "video"],
            supports_search=False,
            supports_preview=False,
            supports_download=False,
            supports_license_metadata=True,
            notes="Manual request/import only. No automated login, scraping or download.",
        )

    def search(self, request: AssetSearchRequest) -> list[AssetCandidate]:
        raise ProviderNoResultsError("Envato Manual Provider does not return automatic stock candidates.", provider=self.name, query=request.query)

    def get_preview(self, candidate: AssetCandidate) -> AssetPreview:
        if candidate.local_path:
            return AssetPreview(
                candidate_id=candidate.asset_id,
                local_path=candidate.local_path,
                media_type=candidate.media_type,
                duration_sec=candidate.duration_sec,
                rendition="envato_imported_local",
                fallback_reason="imported_local_file",
            )
        return AssetPreview(candidate_id=candidate.asset_id, fallback_reason="envato_remote_preview_disabled")

    def resolve_license(self, candidate: AssetCandidate) -> AssetLicense:
        apply_policy_to_candidate(candidate)
        return candidate.license

    def download(self, candidate: AssetCandidate, destination: Path, context: DownloadContext) -> DownloadedAsset:
        raise ProviderNoResultsError("Envato Manual Provider never downloads automatically.", provider=self.name, query=context.search_query)

    def health_check(self) -> ProviderHealth:
        return ProviderHealth(provider=self.name, configured=True, status="manual_only")

    def prepare_request(
        self,
        *,
        project_id: str,
        scene_id: str,
        scene: dict[str, Any] | None = None,
        queries: list[str] | None = None,
        limit: int = 6,
        open_browser: bool = False,
    ) -> dict[str, Any]:
        scene = scene or {}
        search_queries = _queries(queries, scene, limit)
        search_urls = [self.search_url(query) for query in search_queries]
        destination = self._project_root(project_id) / "assets" / "manual_imports" / scene_id
        manifest = {
            "schema_version": 1,
            "provider": self.name,
            "project_id": project_id,
            "scene_id": scene_id,
            "semantic_description": scene.get("visual_description") or scene.get("primary_query") or scene.get("narration") or "",
            "search_queries": search_queries,
            "search_urls": search_urls,
            "destination_import_folder": str(destination),
            "required_metadata_checklist": [
                "source_url",
                "item_id",
                "author",
                "license_proof",
                "confirm_project_registration",
            ],
            "automatic_download": False,
            "manual_actions": [
                "Open one of the public search URLs manually.",
                "Download/license the chosen Envato item in a regular browser session.",
                "Import the local file with source URL, item id, author, proof file and project registration confirmation.",
            ],
            "policy_references": [ENVATO_LIMITS_URL, ENVATO_TERMS_URL],
        }
        path = self._manifest_path(project_id, scene_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if open_browser and search_urls:
            webbrowser.open(search_urls[0])
        return manifest

    def search_url(self, query: str) -> str:
        return f"{self.search_base}?term={quote_plus(query)}"

    def import_asset(
        self,
        *,
        project_id: str,
        scene_id: str,
        file: str | Path,
        source_url: str,
        item_id: str,
        author: str,
        license_proof: str | Path | None,
        confirm_project_registration: bool,
    ) -> DownloadedAsset:
        source = Path(file)
        media_type = _media_type(source)
        validation = validate_local_asset(source, media_type)
        target = self._import_path(project_id, scene_id, item_id, source.suffix)
        target.parent.mkdir(parents=True, exist_ok=True)
        part = target.with_suffix(target.suffix + ".part")
        if part.exists():
            part.unlink()
        shutil.copyfile(source, part)
        part.replace(target)
        checksum = sha256_file(target)
        proof_reference = ""
        if license_proof:
            proof_source = Path(license_proof)
            if proof_source.exists():
                proof_target = self._license_proof_path(project_id, scene_id, item_id, proof_source.suffix)
                proof_target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(proof_source, proof_target)
                proof_reference = str(proof_target)
        confirmed = bool(source_url and item_id and author and proof_reference and confirm_project_registration)
        rights_declaration = {
            "confirmation_status": "approved" if confirmed else "missing",
            "owner_approval_status": "approved" if confirmed else "missing",
            "rights_confirmed": confirmed,
            "license_name": "envato_elements_project_registered",
            "rights_status": "licensed" if confirmed else "unconfirmed",
        }
        raw_metadata = {
            "source_url": source_url,
            "item_id": item_id,
            "author": author,
            "license_proof_reference": proof_reference,
            "confirm_project_registration": confirm_project_registration,
            "policy_references": [ENVATO_LIMITS_URL, ENVATO_TERMS_URL],
        }
        candidate = AssetCandidate(
            asset_id=f"envato_manual_{_safe(scene_id)}_{_safe(item_id or 'unregistered')}",
            provider=self.name,
            provider_asset_id=item_id,
            media_type=media_type,
            title=f"Envato item {item_id}".strip(),
            source_page_url=source_url,
            download_url=source_url,
            author_name=author,
            local_path=str(target),
            original_filename=source.name,
            checksum_sha256=checksum,
            project_id=project_id,
            scene_id=scene_id,
            license=AssetLicense(
                license_name="envato_elements_project_registered",
                license_url=ENVATO_TERMS_URL,
                provider_terms_url=ENVATO_TERMS_URL,
                rights_status="licensed" if confirmed else "unconfirmed",
                commercial_use_allowed=confirmed,
                modification_allowed=confirmed,
                attribution_required=False,
                allowed_for_render=confirmed,
                review_required=not confirmed,
                notes="Manual Envato import. License proof is retained by local reference only.",
            ),
            provenance=AssetProvenance(
                provider=self.name,
                provider_asset_id=item_id,
                source_page_url=source_url,
                download_url=source_url,
                original_filename=source.name,
                downloaded_at=utc_now_iso(),
                checksum_sha256=checksum,
                project_id=project_id,
                scene_id=scene_id,
                metadata_snapshot=raw_metadata,
            ),
            raw_metadata=raw_metadata,
            rights_declaration=rights_declaration,
            technical_validation=validation,
        )
        apply_policy_to_candidate(candidate)
        return DownloadedAsset.from_candidate(
            candidate,
            local_path=str(target),
            checksum_sha256=checksum,
            downloaded_at=candidate.provenance.downloaded_at or utc_now_iso(),
            technical_validation=validation,
        )

    def _project_root(self, project_id: str) -> Path:
        return self.projects_root / project_id

    def _manifest_path(self, project_id: str, scene_id: str) -> Path:
        return self._project_root(project_id) / "assets" / "envato_manual" / f"{scene_id}.json"

    def _import_path(self, project_id: str, scene_id: str, item_id: str, suffix: str) -> Path:
        return self._project_root(project_id) / "assets" / "manual_imports" / scene_id / f"envato_{_safe(item_id or 'item')}{suffix or '.mp4'}"

    def _license_proof_path(self, project_id: str, scene_id: str, item_id: str, suffix: str) -> Path:
        return self._project_root(project_id) / "metadata" / "licenses" / f"{scene_id}_{_safe(item_id or 'item')}{suffix or '.txt'}"


def _queries(queries: list[str] | None, scene: dict[str, Any], limit: int) -> list[str]:
    requested = [query.strip() for query in queries or [] if query.strip()]
    if requested:
        base = requested
    else:
        text = " ".join(
            str(scene.get(key) or "")
            for key in ("primary_query", "visual_description", "visual_intent", "narration")
        )
        words = [word for word in re.findall(r"[a-zA-Z0-9]+", text.lower()) if len(word) > 2]
        compact = " ".join(dict.fromkeys(words[:8])) or "documentary cinematic footage"
        base = [
            compact,
            f"{compact} cinematic stock footage",
            f"{compact} documentary b-roll",
            f"{compact} aerial shot",
            f"{compact} close up",
            f"{compact} background",
            f"{compact} 4k",
            f"{compact} editorial",
        ]
    normalized = list(dict.fromkeys(base))
    desired = max(3, min(8, int(limit or 6)))
    while len(normalized) < desired:
        normalized.append(f"{normalized[0]} stock footage {len(normalized) + 1}")
    return normalized[:desired]


def _media_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".webp"}:
        return "image"
    if suffix in {".mp4", ".mov", ".m4v", ".webm"}:
        return "video"
    return "image"


def _safe(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", str(value or "")).strip("_")[:80]
