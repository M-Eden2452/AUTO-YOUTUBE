from __future__ import annotations

import dataclasses
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import ASSET_SCHEMA_VERSION, AssetCandidate, AssetLicense


DEFAULT_LICENSE_POLICY_PATH = Path("config/license_policy.json")
APPROVED_STATUSES = {"approved", "confirmed", "owner_approved"}
MANUAL_PROVIDERS = {"user", "manual", "manual_asset", "envato_manual"}


@dataclass
class LicensePolicyDecision:
    policy_version: str
    policy_reviewed_date: str
    provider: str
    media_type: str
    license_name: str
    policy_context: str = "internal_content_production"
    license_url: str = ""
    provider_terms_url: str = ""
    commercial_use_allowed: bool = False
    modification_allowed: bool = False
    attribution_required: bool = True
    required_attribution: str = ""
    modification_notice_required: bool = False
    share_alike: bool = False
    allowed_for_render: bool = False
    review_required: bool = True
    owner_review_required: bool = True
    owner_approval_status: str = "not_reviewed"
    status: str = "blocked"
    reason: str = "default_deny"
    notes: str = ""
    source_url: str = ""
    provider_asset_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)

    def to_license(self, existing: AssetLicense | None = None) -> AssetLicense:
        base = existing or AssetLicense()
        return AssetLicense(
            license_name=self.license_name or base.license_name,
            license_url=self.license_url or base.license_url,
            provider_terms_url=self.provider_terms_url or base.provider_terms_url,
            rights_status="licensed" if self.allowed_for_render else "review_required",
            commercial_use_allowed=self.commercial_use_allowed,
            modification_allowed=self.modification_allowed,
            attribution_required=self.attribution_required,
            attribution_text=self.required_attribution or base.attribution_text,
            allowed_for_render=self.allowed_for_render,
            review_required=self.review_required,
            notes=self.notes or base.notes,
            checked_at=base.checked_at,
        )


def load_license_policy(path: str | Path | None = None) -> dict[str, Any]:
    target = Path(path) if path else DEFAULT_LICENSE_POLICY_PATH
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    data.setdefault("policy_version", "missing-policy")
    data.setdefault("policy_reviewed_date", "")
    data.setdefault("default_decision", {})
    data.setdefault("providers", {})
    return data


def evaluate_asset_policy(
    asset: AssetCandidate | dict[str, Any],
    *,
    policy: dict[str, Any] | None = None,
    policy_path: str | Path | None = None,
    context: str | None = None,
) -> LicensePolicyDecision:
    candidate = asset if isinstance(asset, AssetCandidate) else AssetCandidate.from_dict(asset)
    raw = asset.to_manifest_dict() if isinstance(asset, AssetCandidate) else dict(asset)
    loaded_policy = policy or load_license_policy(policy_path)
    default = dict(loaded_policy.get("default_decision") or {})
    policy_context = _policy_context(candidate, raw, loaded_policy, context)
    provider = str(candidate.provider or raw.get("provider") or "").strip()
    media_type = str(candidate.media_type or raw.get("media_type") or raw.get("type") or "").strip()
    license_name = _license_name(candidate, raw)
    source_url = _source_url(candidate, raw)
    provider_asset_id = str(candidate.provider_asset_id or raw.get("provider_asset_id") or "").strip()
    base_provider_config = (loaded_policy.get("providers") or {}).get(provider)
    provider_config = _contextual_provider_config(base_provider_config, policy_context) if isinstance(base_provider_config, dict) else None
    rule = _match_rule(provider_config, media_type, license_name) if isinstance(provider_config, dict) else None
    reason_parts: list[str] = []

    if not provider:
        reason_parts.append("missing_provider")
    elif not isinstance(provider_config, dict):
        reason_parts.append("unknown_provider")
    elif not provider_config.get("enabled", True):
        reason_parts.append("provider_disabled")

    if not license_name or license_name == "unknown":
        reason_parts.append("unknown_license")
    elif isinstance(provider_config, dict) and not rule:
        # The licence is stated and readable, it simply has no rule yet. Calling that
        # "unknown_license" made an accurate CC BY-SA 3.0 record - author, licence URL
        # and source page all present - indistinguishable from a file that says nothing
        # about its rights, and the operator was told to review "incomplete metadata"
        # that was not incomplete. Both still block; only one of them is a mystery.
        reason_parts.append("license_not_in_policy")

    if not source_url:
        reason_parts.append("missing_source")

    if not provider_asset_id:
        reason_parts.append("missing_provider_asset_id")

    schema_version = int(raw.get("schema_version") or candidate.schema_version or 0)
    if schema_version < ASSET_SCHEMA_VERSION:
        reason_parts.append("legacy_schema_version_0")

    manual_declaration = _manual_declaration(candidate, raw)
    if provider in MANUAL_PROVIDERS:
        if not _manual_declaration_is_confirmed(manual_declaration):
            reason_parts.append("manual_rights_not_confirmed")
        else:
            provider_asset_id = provider_asset_id or str(raw.get("asset_id") or candidate.asset_id)

    if rule and int(rule.get("requires_schema_version") or 0) > schema_version:
        reason_parts.append("schema_version_too_old")

    if rule and bool(rule.get("requires_rights_confirmation")) and not _manual_declaration_is_confirmed(manual_declaration):
        reason_parts.append("manual_rights_not_confirmed")

    reason_parts.extend(
        _provider_specific_policy_reasons(
            candidate=candidate,
            raw=raw,
            provider=provider,
            license_name=license_name,
            source_url=source_url,
            provider_asset_id=provider_asset_id,
            provider_config=provider_config or {},
            rule=rule,
            policy_context=policy_context,
        )
    )

    owner_review_required = bool((provider_config or {}).get("owner_review_required", default.get("owner_review_required", True)))
    owner_approval_status = str((provider_config or {}).get("owner_approval_status") or default.get("owner_approval_status") or "not_reviewed")
    if _manual_declaration_is_confirmed(manual_declaration):
        owner_approval_status = str(manual_declaration.get("owner_approval_status") or manual_declaration.get("confirmation_status") or "approved")
        owner_review_required = False

    if owner_review_required and owner_approval_status not in APPROVED_STATUSES and owner_approval_status != "schema_v1_required":
        reason_parts.append("owner_review_required")

    if provider == "local_library" and owner_approval_status == "schema_v1_required" and schema_version >= ASSET_SCHEMA_VERSION:
        owner_review_required = False

    blocked = bool(reason_parts)
    allowed = bool(rule.get("allowed_for_render", False)) if rule else bool(default.get("allowed_for_render", False))
    review_required = bool(rule.get("review_required", True)) if rule else bool(default.get("review_required", True))
    if blocked:
        allowed = False
        review_required = True

    status = "allowed" if allowed and not review_required else "blocked" if blocked else "review_required"
    reason = "|".join(dict.fromkeys(reason_parts)) if reason_parts else "policy_rule_allowed"
    notes = str((rule or {}).get("notes") or default.get("notes") or "")
    license_url = str(candidate.license.license_url or raw.get("license_url") or (rule or {}).get("license_url") or "")
    provider_terms_url = str((provider_config or {}).get("provider_terms_url") or candidate.license.provider_terms_url or "")
    attribution_text = str(candidate.license.attribution_text or raw.get("attribution_text") or "")
    modification_notice_required = _modification_notice_required(provider, license_name, bool((rule or {}).get("modification_notice_required", False)))
    share_alike = _is_share_alike_license(license_name) or bool((rule or {}).get("share_alike", False))

    return LicensePolicyDecision(
        policy_version=str(loaded_policy.get("policy_version") or ""),
        policy_reviewed_date=str(loaded_policy.get("policy_reviewed_date") or ""),
        provider=provider,
        media_type=media_type,
        license_name=license_name or "unknown",
        policy_context=policy_context,
        license_url=license_url,
        provider_terms_url=provider_terms_url,
        commercial_use_allowed=False if blocked else bool((rule or {}).get("commercial_use_allowed", default.get("commercial_use_allowed", False))),
        modification_allowed=False if blocked else bool((rule or {}).get("modification_allowed", default.get("modification_allowed", False))),
        attribution_required=True if blocked else bool((rule or {}).get("attribution_required", default.get("attribution_required", True))),
        required_attribution=attribution_text,
        modification_notice_required=modification_notice_required,
        share_alike=share_alike,
        allowed_for_render=allowed,
        review_required=review_required,
        owner_review_required=owner_review_required,
        owner_approval_status=owner_approval_status,
        status=status,
        reason=reason,
        notes=notes,
        source_url=source_url,
        provider_asset_id=provider_asset_id,
    )


def apply_policy_to_candidate(
    candidate: AssetCandidate,
    *,
    policy: dict[str, Any] | None = None,
    policy_path: str | Path | None = None,
    context: str | None = None,
) -> LicensePolicyDecision:
    decision = evaluate_asset_policy(candidate, policy=policy, policy_path=policy_path, context=context)
    candidate.policy_decision = decision.to_dict()
    candidate.license = decision.to_license(candidate.license)
    return decision


def policy_status_for_provider(provider: str, *, policy: dict[str, Any] | None = None) -> dict[str, Any]:
    loaded_policy = policy or load_license_policy()
    providers = loaded_policy.get("providers") or {}
    if provider not in providers:
        return {
            "policy_version": loaded_policy.get("policy_version", ""),
            "policy_status": "missing_provider_policy",
            "owner_approval_status": "not_reviewed",
            "owner_review_required": True,
        }
    base_provider_config = providers.get(provider, {})
    if not isinstance(base_provider_config, dict):
        return {
            "policy_version": loaded_policy.get("policy_version", ""),
            "policy_status": "missing_provider_policy",
            "owner_approval_status": "not_reviewed",
            "owner_review_required": True,
        }
    provider_config = _contextual_provider_config(base_provider_config, str(loaded_policy.get("default_context") or "internal_content_production")) or base_provider_config
    return {
        "policy_version": loaded_policy.get("policy_version", ""),
        "policy_status": "configured" if provider_config.get("enabled", True) else "disabled",
        "owner_approval_status": provider_config.get("owner_approval_status", "not_reviewed"),
        "owner_review_required": bool(provider_config.get("owner_review_required", True)),
    }


def _match_rule(provider_config: dict[str, Any] | None, media_type: str, license_name: str) -> dict[str, Any] | None:
    if not provider_config:
        return None
    normalized_license = license_name.lower().strip()
    normalized_media = media_type.lower().strip()
    for rule in provider_config.get("rules", []):
        if not isinstance(rule, dict):
            continue
        rule_media = str(rule.get("media_type") or "*").lower().strip()
        rule_license = str(rule.get("license_name") or "").lower().strip()
        if rule_license == normalized_license and rule_media in {"*", normalized_media}:
            return rule
    return None


def _license_name(candidate: AssetCandidate, raw: dict[str, Any]) -> str:
    if isinstance(raw.get("license"), dict):
        return str(raw["license"].get("license_name") or raw["license"].get("name") or "").strip()
    return str(candidate.license.license_name or raw.get("license_name") or raw.get("license") or "unknown").strip()


def _source_url(candidate: AssetCandidate, raw: dict[str, Any]) -> str:
    provenance = raw.get("provenance") if isinstance(raw.get("provenance"), dict) else {}
    return str(
        candidate.source_page_url
        or raw.get("source_page_url")
        or raw.get("source_page")
        or raw.get("source_url")
        or provenance.get("source_page_url")
        or ""
    ).strip()


def _manual_declaration(candidate: AssetCandidate, raw: dict[str, Any]) -> dict[str, Any]:
    if isinstance(raw.get("rights_declaration"), dict):
        return dict(raw["rights_declaration"])
    if isinstance(candidate.rights_declaration, dict):
        return dict(candidate.rights_declaration)
    metadata = candidate.raw_metadata if isinstance(candidate.raw_metadata, dict) else {}
    if isinstance(metadata.get("rights_declaration"), dict):
        return dict(metadata["rights_declaration"])
    return {}


def _manual_declaration_is_confirmed(declaration: dict[str, Any]) -> bool:
    if not declaration:
        return False
    if bool(declaration.get("confirmed") or declaration.get("owner_confirmed") or declaration.get("rights_confirmed")):
        return True
    status = str(declaration.get("confirmation_status") or declaration.get("owner_approval_status") or "").strip().lower()
    return status in APPROVED_STATUSES


def _policy_context(candidate: AssetCandidate, raw: dict[str, Any], policy: dict[str, Any], context: str | None) -> str:
    metadata = candidate.raw_metadata if isinstance(candidate.raw_metadata, dict) else {}
    value = (
        context
        or raw.get("policy_context")
        or metadata.get("policy_context")
        or policy.get("default_context")
        or "internal_content_production"
    )
    return str(value or "internal_content_production")


def _contextual_provider_config(provider_config: dict[str, Any] | None, context: str) -> dict[str, Any] | None:
    if not isinstance(provider_config, dict):
        return None
    merged = {key: value for key, value in provider_config.items() if key != "contexts"}
    contexts = provider_config.get("contexts") if isinstance(provider_config.get("contexts"), dict) else {}
    context_config = contexts.get(context) if isinstance(contexts, dict) else None
    if isinstance(context_config, dict):
        merged.update(context_config)
    return merged


def _provider_specific_policy_reasons(
    *,
    candidate: AssetCandidate,
    raw: dict[str, Any],
    provider: str,
    license_name: str,
    source_url: str,
    provider_asset_id: str,
    provider_config: dict[str, Any],
    rule: dict[str, Any] | None,
    policy_context: str,
) -> list[str]:
    if provider in {"pexels", "pixabay"}:
        return _stock_provider_reasons(candidate, raw, provider_config, policy_context)
    if provider == "wikimedia":
        return _wikimedia_reasons(
            candidate, raw, license_name, source_url, provider_asset_id,
            share_alike_accepted=_share_alike_accepted(_manual_declaration(candidate, raw)),
        )
    if provider == "nasa_images":
        return _nasa_reasons(candidate, raw, source_url, provider_asset_id, policy_context)
    if provider == "internet_archive":
        return _internet_archive_reasons(candidate, raw, license_name, source_url, provider_asset_id, rule, provider_config)
    if provider == "envato_manual":
        return _envato_reasons(candidate, raw)
    return []


def _stock_provider_reasons(candidate: AssetCandidate, raw: dict[str, Any], provider_config: dict[str, Any], policy_context: str) -> list[str]:
    reasons: list[str] = []
    metadata = candidate.raw_metadata if isinstance(candidate.raw_metadata, dict) else {}
    license_url = candidate.license.license_url or raw.get("license_url")
    provider_terms_url = candidate.license.provider_terms_url or provider_config.get("provider_terms_url")
    if policy_context == "internal_content_production":
        if not candidate.download_url and not raw.get("download_url"):
            reasons.append("missing_download_url")
        if not license_url:
            reasons.append("missing_license_url")
        if not provider_terms_url:
            reasons.append("missing_provider_terms_url")
        if bool(metadata.get("forbidden_use_detected") or raw.get("forbidden_use_detected")):
            reasons.append("prohibited_use_detected")
        if metadata.get("use_inside_edited_video", True) is False or raw.get("use_inside_edited_video") is False:
            reasons.append("standalone_stock_redistribution")
    return reasons


def _share_alike_accepted(declaration: dict[str, Any]) -> bool:
    """Has a person accepted ShareAlike for this one file, in writing?

    ShareAlike is not an attribution formality: it can oblige the finished video to be
    released under the same licence. So it is never cleared by a rule in the policy
    table, by a provider being trusted, or by the licence simply being recognised - only
    by an explicit, per-asset declaration that says both "confirmed" and "we accept the
    ShareAlike terms for this asset". Anything less leaves the asset flagged.
    """
    if not _manual_declaration_is_confirmed(declaration):
        return False
    return bool(
        declaration.get("share_alike_accepted")
        or declaration.get("sharealike_accepted")
        or declaration.get("accepts_share_alike")
    )


def _wikimedia_reasons(
    candidate: AssetCandidate,
    raw: dict[str, Any],
    license_name: str,
    source_url: str,
    provider_asset_id: str,
    *,
    share_alike_accepted: bool = False,
) -> list[str]:
    reasons: list[str] = []
    metadata = candidate.raw_metadata if isinstance(candidate.raw_metadata, dict) else {}
    key = _license_key(license_name)
    license_url = candidate.license.license_url or raw.get("license_url")
    author = candidate.author_name or raw.get("author_name") or raw.get("author")
    attribution = candidate.license.attribution_text or raw.get("attribution_text")
    allowed_keys = {
        "public domain",
        "pd",
        "cc0",
        "cc by 2.0",
        "cc by 2.5",
        "cc by 3.0",
        "cc by 4.0",
    }
    if not key or key in {"unknown", "unknown license"}:
        reasons.append("unknown_license")
    elif "cc by sa" in key or "cc by-sa" in key or "sharealike" in key:
        # Cleared only by a written per-asset acceptance; see _share_alike_accepted.
        if not share_alike_accepted:
            reasons.append("share_alike_review_required")
    elif "gfdl" in key or "gnu free documentation" in key:
        reasons.append("gfdl_review_required")
    elif "free art license" in key or key == "fal":
        reasons.append("free_art_license_review_required")
    elif "|" in license_name or "," in license_name and "cc by" in key:
        reasons.append("multiple_licenses_review_required")
    elif "cc by" in key and key not in allowed_keys:
        reasons.append("unknown_creative_commons_version")
    elif key not in allowed_keys:
        reasons.append("unknown_license")
    if not license_url:
        reasons.append("missing_license_url")
    if key.startswith("cc by") and not author:
        reasons.append("missing_author")
    if key.startswith("cc by") and not attribution:
        reasons.append("missing_attribution_text")
    warnings_text = " ".join(str(value).lower() for value in metadata.get("restriction_warnings", []) if value)
    if any(term in warnings_text for term in ("personality", "trademark", "coat of arms", "non-copyright", "privacy", "moral rights")):
        reasons.append("non_copyright_restriction_warning")
    if metadata.get("conflicting_metadata"):
        reasons.append("conflicting_metadata")
    if key in {"public domain", "pd"} and metadata.get("public_domain_rationale_unclear"):
        reasons.append("unclear_public_domain_rationale")
    return reasons


def _nasa_reasons(candidate: AssetCandidate, raw: dict[str, Any], source_url: str, provider_asset_id: str, policy_context: str) -> list[str]:
    reasons: list[str] = []
    metadata = candidate.raw_metadata if isinstance(candidate.raw_metadata, dict) else {}
    text = " ".join(
        str(value).lower()
        for value in (
            candidate.title,
            candidate.description,
            " ".join(candidate.tags),
            json.dumps(metadata, ensure_ascii=False),
        )
    )
    use_context = str(metadata.get("use_context") or raw.get("use_context") or "editorial/informational").lower()
    if not source_url:
        reasons.append("missing_source_page")
    if not provider_asset_id:
        reasons.append("missing_nasa_id")
    if not any(term in use_context for term in ("editorial", "informational", "educational", "documentary")):
        reasons.append("non_editorial_context")
    if any(term in text for term in ("third party", "third-party", "copyright ", "courtesy of")):
        reasons.append("third_party_notice")
    if any(term in text for term in ("clearance", "permission required", "restricted")):
        reasons.append("clearance_warning")
    if any(term in text for term in ("identifiable person", "astronaut", "employee", "portrait")):
        reasons.append("identifiable_person_review")
    if "logo" in text or "emblem" in text:
        reasons.append("logo_or_emblem_review")
    if policy_context == "public_multi_user_product":
        reasons.append("public_product_review_required")
    return reasons


def _internet_archive_reasons(
    candidate: AssetCandidate,
    raw: dict[str, Any],
    license_name: str,
    source_url: str,
    provider_asset_id: str,
    rule: dict[str, Any] | None,
    provider_config: dict[str, Any],
) -> list[str]:
    reasons: list[str] = []
    metadata = candidate.raw_metadata if isinstance(candidate.raw_metadata, dict) else {}
    text = " ".join(
        str(value).lower()
        for value in (
            license_name,
            candidate.license.license_url,
            metadata.get("rights", ""),
            metadata.get("access_restricted", ""),
            metadata.get("collection", ""),
        )
    )
    if not (candidate.license.license_url or raw.get("license_url")) and not license_name:
        reasons.append("missing_license")
    if "all rights reserved" in text:
        reasons.append("all_rights_reserved")
    if "by-nc" in text or "noncommercial" in text or "non-commercial" in text:
        reasons.append("non_commercial_license")
    if "by-nd" in text or "no derivatives" in text:
        reasons.append("no_derivatives_license")
    if "borrow" in text or "access-restricted" in text or "access restricted" in text:
        reasons.append("access_restricted")
    if "copyright warning" in text:
        reasons.append("copyright_warning")
    if "by-sa" in text:
        reasons.append("share_alike_review_required")
    if metadata.get("conflicting_rights"):
        reasons.append("conflicting_rights")
    if _license_key(license_name) in {"public domain", "pd"} and metadata.get("public_domain_rationale_unclear"):
        reasons.append("unclear_public_domain")
    if _license_key(license_name).startswith("cc by") and not candidate.author_name:
        reasons.append("missing_author")
    trusted = {str(item).lower() for item in provider_config.get("trusted_collections", [])}
    collections = {str(item).lower() for item in _as_iterable(metadata.get("collection"))}
    if not rule and trusted and not (trusted & collections):
        reasons.append("unknown_collection")
    return reasons


def _envato_reasons(candidate: AssetCandidate, raw: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    metadata = candidate.raw_metadata if isinstance(candidate.raw_metadata, dict) else {}
    proof = metadata.get("license_proof_reference") or raw.get("license_proof_reference")
    registered = metadata.get("confirm_project_registration") or raw.get("confirm_project_registration")
    if not proof:
        reasons.append("missing_license_proof")
    if not registered:
        reasons.append("project_registration_not_confirmed")
    return reasons


def _license_key(value: str) -> str:
    return " ".join(str(value or "").lower().replace("-", " ").split())


def _is_share_alike_license(value: str) -> bool:
    key = _license_key(value)
    return "cc by sa" in key or "sharealike" in key or "share alike" in key


def _modification_notice_required(provider: str, license_name: str, default: bool) -> bool:
    key = _license_key(license_name)
    if provider == "wikimedia" and key.startswith("cc by"):
        return True
    return bool(default)


def _as_iterable(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple | set):
        return list(value)
    return [value]
