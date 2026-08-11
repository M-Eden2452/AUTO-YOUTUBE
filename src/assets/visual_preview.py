from __future__ import annotations

import dataclasses
import hashlib
import json
import mimetypes
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

import imageio_ffmpeg
from PIL import Image

from src.runtime_network import NETWORK_ACTION_PREVIEW_DOWNLOAD

from .frame_sampling import ffprobe_media_info, sample_frames, sha256_file
from .http_client import ProviderHttpClient
from .models import AssetCandidate, utc_now_iso
from .perceptual_similarity import signature_from_frames, signature_from_image
from .provider_contract import AssetPreview
from .visual_metrics import analyze_visual_technical_quality


from src.config_resolver.paths import repository_path


DEFAULT_CONFIG_PATH = repository_path("config", "visual_preview.json")
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
VIDEO_SUFFIXES = {".mp4", ".mov", ".m4v", ".webm", ".ogv"}


@dataclass
class VisualPreviewRequest:
    project_id: str
    scene_id: str = ""
    top_k: int = 5
    target_aspect_ratio: str = "9:16"
    project_root: str = ""
    cache_root: str = ""
    refresh: bool = False
    offline: bool = False
    technical_rerank: bool = False
    no_html: bool = False
    sample_count: int = 5
    sample_positions: list[float] = field(default_factory=lambda: [0.1, 0.3, 0.5, 0.7, 0.9])
    target_aspect_ratios: list[str] = field(default_factory=lambda: ["9:16", "16:9", "1:1"])

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VisualPreviewRequest":
        return cls(
            project_id=str(data.get("project_id") or ""),
            scene_id=str(data.get("scene_id") or ""),
            top_k=int(data.get("top_k") or data.get("shortlist_size") or 5),
            target_aspect_ratio=str(data.get("target_aspect_ratio") or "9:16"),
            project_root=str(data.get("project_root") or ""),
            cache_root=str(data.get("cache_root") or ""),
            refresh=bool(data.get("refresh", False)),
            offline=bool(data.get("offline", False)),
            technical_rerank=bool(data.get("technical_rerank", False)),
            no_html=bool(data.get("no_html", False)),
            sample_count=int(data.get("sample_count") or data.get("frame_sample_count") or 5),
            sample_positions=[float(item) for item in data.get("sample_positions") or data.get("frame_sample_positions") or [0.1, 0.3, 0.5, 0.7, 0.9]],
            target_aspect_ratios=[str(item) for item in data.get("target_aspect_ratios") or ["9:16", "16:9", "1:1"]],
        )

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclass
class CandidatePreview:
    candidate_id: str
    provider: str = ""
    provider_asset_id: str = ""
    preview_source_url: str = ""
    preview_local_source: str = ""
    preview_media_type: str = ""
    width: int = 0
    height: int = 0
    duration_sec: float = 0.0
    expected_content_type: str = ""
    expected_size_bytes: int = 0
    rendition: str = "provider_preview"
    fallback_reason: str = ""
    original_used: bool = False
    timestamp: str = field(default_factory=utc_now_iso)
    cache_key: str = ""

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclass
class PreviewCacheRecord:
    cache_key: str
    local_path: str = ""
    preview_media_type: str = ""
    preview_source_url: str = ""
    width: int = 0
    height: int = 0
    duration_sec: float = 0.0
    expected_content_type: str = ""
    expected_size_bytes: int = 0
    sha256: str = ""
    bytes: int = 0
    fallback_reason: str = ""
    original_used: bool = False
    cache_status: str = "miss"
    created_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PreviewCacheRecord":
        values = {field.name: data.get(field.name) for field in dataclasses.fields(cls) if field.name in data}
        return cls(**values)


def load_visual_preview_config(path: str | Path = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    target = Path(path)
    if not target.exists():
        return _default_config()
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return _default_config()
    config = _default_config()
    if isinstance(data, dict):
        _deep_update(config, data)
    return config


class PreviewCache:
    def __init__(self, root: str | Path, *, max_preview_size_bytes: int) -> None:
        self.root = Path(root)
        self.max_preview_size_bytes = int(max_preview_size_bytes)

    def read(self, cache_key: str, *, media_type: str) -> PreviewCacheRecord | None:
        record_path = self._record_path(cache_key)
        if not record_path.exists():
            return None
        try:
            record = PreviewCacheRecord.from_dict(json.loads(record_path.read_text(encoding="utf-8")))
        except Exception:
            return None
        local = Path(record.local_path)
        if not local.exists() or local.stat().st_size <= 0:
            return None
        if record.sha256 and sha256_file(local) != record.sha256:
            return None
        if not _validate_preview_file(local, media_type):
            return None
        record.cache_status = "hit"
        return record

    def store_bytes(
        self,
        cache_key: str,
        data: bytes,
        *,
        media_type: str,
        extension: str,
        source_url: str,
        expected_content_type: str = "",
    ) -> PreviewCacheRecord:
        if len(data) > self.max_preview_size_bytes:
            raise ValueError(f"preview_exceeds_max_size:{len(data)}")
        folder = self.root / _safe(cache_key)
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / f"preview{_safe_extension(extension, media_type)}"
        part = target.with_suffix(target.suffix + ".part")
        if part.exists():
            part.unlink()
        part.write_bytes(data)
        part.replace(target)
        if not _validate_preview_file(target, media_type):
            target.unlink(missing_ok=True)
            raise ValueError("stored_preview_validation_failed")
        record = _record_for_file(
            cache_key,
            target,
            media_type=media_type,
            source_url=source_url,
            expected_content_type=expected_content_type,
            cache_status="stored",
        )
        self._write_record(record)
        return record

    def store_file(
        self,
        cache_key: str,
        path: str | Path,
        *,
        media_type: str,
        source_url: str = "",
        fallback_reason: str = "",
        original_used: bool = False,
    ) -> PreviewCacheRecord:
        local = Path(path)
        if not _validate_preview_file(local, media_type):
            raise ValueError("preview_validation_failed")
        record = _record_for_file(cache_key, local, media_type=media_type, source_url=source_url, cache_status="stored")
        record.fallback_reason = fallback_reason
        record.original_used = original_used
        self._write_record(record)
        return record

    def _record_path(self, cache_key: str) -> Path:
        return self.root / _safe(cache_key) / "preview_record.json"

    def _write_record(self, record: PreviewCacheRecord) -> None:
        path = self._record_path(record.cache_key)
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(path.suffix + ".part")
        temp.write_text(json.dumps(record.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temp.replace(path)


def compute_preview_cache_key(
    candidate: AssetCandidate,
    request: VisualPreviewRequest,
    *,
    preview_source_url: str,
    rendition: str = "provider_preview",
    video_preview_max_duration_sec: float = 8.0,
) -> str:
    local_source = _preview_local_source_path(preview_source_url)
    payload = {
        "version": 1,
        "provider": candidate.provider,
        "provider_asset_id": candidate.provider_asset_id,
        "asset_id": candidate.asset_id,
        "preview_source_url": preview_source_url,
        "media_type": candidate.media_type,
        "rendition": rendition,
        "target_aspect_ratio": request.target_aspect_ratio,
        "sample_count": request.sample_count,
        "top_k": request.top_k,
    }
    if local_source is not None:
        # A pathname identifies a location, not the bytes technical review or
        # Vision will observe. Hash the current local snapshot before any cache
        # lookup so in-place/manual replacements cannot inherit old evidence.
        payload["version"] = 2
        payload["source_sha256"] = sha256_file(local_source)
        payload["local_preview_transform"] = {
            "max_dimension": 720,
            "video_max_duration_sec": float(video_preview_max_duration_sec),
        }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def create_local_preview(
    source: str | Path,
    cache_root: str | Path,
    *,
    media_type: str,
    cache_key: str,
    max_dimension: int = 720,
    max_duration_sec: float = 8.0,
) -> PreviewCacheRecord:
    source_path = Path(source)
    folder = Path(cache_root) / _safe(cache_key)
    folder.mkdir(parents=True, exist_ok=True)
    actual_media_type = _media_type_from_path(source_path, fallback=media_type)
    if actual_media_type == "image":
        target = folder / "preview.jpg"
        _create_image_preview(source_path, target, max_dimension=max_dimension)
    else:
        target = folder / "preview.mp4"
        _create_video_preview(source_path, target, max_dimension=max_dimension, max_duration_sec=max_duration_sec)
    record = _record_for_file(cache_key, target, media_type=actual_media_type, source_url=str(source_path), cache_status="stored")
    record.fallback_reason = "local_preview_generated"
    _write_standalone_record(folder, record)
    return record


def resolve_candidate_preview(
    candidate: AssetCandidate,
    *,
    provider: Any | None,
    request: VisualPreviewRequest,
    video_preview_max_duration_sec: float = 8.0,
) -> CandidatePreview:
    preview = CandidatePreview(
        candidate_id=candidate.asset_id,
        provider=candidate.provider,
        provider_asset_id=candidate.provider_asset_id,
        preview_media_type=candidate.media_type,
        width=candidate.width,
        height=candidate.height,
        duration_sec=candidate.duration_sec,
    )
    local_candidate_path = candidate.local_path
    if candidate.provider == "envato_manual" and not local_candidate_path:
        preview.fallback_reason = "envato_remote_preview_disabled"
        preview.cache_key = compute_preview_cache_key(candidate, request, preview_source_url="", rendition="envato_disabled")
        return preview
    provider_preview = _provider_preview(provider, candidate)
    if provider_preview.local_path:
        preview.preview_local_source = provider_preview.local_path
        preview.preview_media_type = _media_type_from_path(Path(provider_preview.local_path), fallback=provider_preview.media_type or candidate.media_type)
        preview.rendition = provider_preview.rendition or "provider_local_preview"
        preview.fallback_reason = provider_preview.fallback_reason or "provider_local_preview"
    elif provider_preview.url:
        preview.preview_source_url = provider_preview.url
        preview.preview_media_type = provider_preview.media_type or _media_type_from_url(provider_preview.url, fallback=candidate.media_type)
        preview.expected_content_type = provider_preview.expected_content_type
        preview.expected_size_bytes = provider_preview.expected_size_bytes
        preview.rendition = provider_preview.rendition or "provider_preview"
        preview.original_used = provider_preview.original_used
        preview.fallback_reason = provider_preview.fallback_reason or "provider_preview_url"
    if not preview.preview_local_source and not preview.preview_source_url:
        _fill_provider_specific_preview(preview, candidate)
    if not preview.preview_local_source and not preview.preview_source_url and local_candidate_path:
        preview.preview_local_source = local_candidate_path
        preview.preview_media_type = _media_type_from_path(Path(local_candidate_path), fallback=candidate.media_type)
        preview.fallback_reason = "existing_local_file"
        preview.rendition = "local_file"
    if not preview.preview_local_source and not preview.preview_source_url and candidate.download_url and _allow_original_fallback(candidate, request):
        preview.preview_source_url = candidate.download_url
        preview.preview_media_type = candidate.media_type
        preview.original_used = True
        preview.fallback_reason = "safe_original_fallback"
        preview.rendition = "original_fallback"
    source = preview.preview_local_source or preview.preview_source_url
    preview.cache_key = compute_preview_cache_key(
        candidate,
        request,
        preview_source_url=source,
        rendition=preview.rendition,
        video_preview_max_duration_sec=video_preview_max_duration_sec,
    )
    return preview


def prepare_candidate_preview_analyses(
    candidates: list[dict[str, Any]],
    *,
    providers_by_name: dict[str, Any],
    request: VisualPreviewRequest,
    config: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    config = config or load_visual_preview_config()
    max_bytes = int(float(config.get("maximum_preview_size_mb", 5)) * 1024 * 1024)
    cache_root = _request_cache_root(request, config)
    cache = PreviewCache(cache_root, max_preview_size_bytes=max_bytes)
    analyses: list[dict[str, Any]] = []
    for raw in list(candidates)[: max(1, request.top_k)]:
        candidate = AssetCandidate.from_dict(raw)
        provider = providers_by_name.get(candidate.provider)
        preview = CandidatePreview(
            candidate_id=candidate.asset_id,
            provider=candidate.provider,
            provider_asset_id=candidate.provider_asset_id,
            preview_media_type=candidate.media_type,
        )
        try:
            preview = resolve_candidate_preview(
                candidate,
                provider=provider,
                request=request,
                video_preview_max_duration_sec=float(config.get("video_preview_max_duration_sec", 8.0)),
            )
            record = _materialize_preview(preview, cache, request, config)
            frames = sample_frames(
                record.local_path,
                media_type=record.preview_media_type,
                output_dir=Path(cache_root) / _safe(record.cache_key) / "frames",
                sample_count=request.sample_count,
                positions=request.sample_positions,
                duration_sec=record.duration_sec,
            )
            technical = analyze_visual_technical_quality(
                record.local_path,
                media_type=record.preview_media_type,
                sampled_frames=frames,
                target_aspect_ratios=request.target_aspect_ratios,
                duration_sec=record.duration_sec,
            )
            signature = signature_from_image(candidate.asset_id, record.local_path) if record.preview_media_type == "image" else signature_from_frames(candidate.asset_id, frames)
            analysis_status = "passed" if technical.analysis_status == "passed" and signature.status == "passed" else "failed"
            analyses.append(
                {
                    "asset_id": candidate.asset_id,
                    "provider": candidate.provider,
                    "provider_asset_id": candidate.provider_asset_id,
                    "analysis_status": analysis_status,
                    "analysis_error": technical.analysis_error or signature.error,
                    "preview": {**preview.to_dict(), **record.to_dict()},
                    "sampled_frames": [frame.to_dict() for frame in frames],
                    "technical_metrics": technical.to_dict(),
                    "perceptual_signature": signature.to_dict(),
                    "duplicate_scores": [],
                    "crop_scores": technical.crop_suitability,
                    "technical_quality_score": technical.technical_quality_score,
                }
            )
        except Exception as exc:
            reason = preview.fallback_reason or str(exc)
            if request.offline and preview.preview_source_url and not preview.preview_local_source:
                reason = "offline_no_cache"
            analyses.append(
                {
                    "asset_id": candidate.asset_id,
                    "provider": candidate.provider,
                    "provider_asset_id": candidate.provider_asset_id,
                    "analysis_status": "failed",
                    "analysis_error": str(exc),
                    "preview": {**preview.to_dict(), "fallback_reason": reason},
                    "sampled_frames": [],
                    "technical_metrics": {"analysis_status": "failed", "technical_quality_score": 0.0},
                    "perceptual_signature": {"asset_id": candidate.asset_id, "status": "failed", "frame_hashes": []},
                    "duplicate_scores": [],
                    "crop_scores": {},
                    "technical_quality_score": 0.0,
                }
            )
    _attach_similarity(analyses, config)
    return analyses


def prepare_visual_preview_for_project(
    *,
    project_root: str | Path,
    project_id: str,
    scene_id: str = "",
    all_scenes: bool = False,
    top_k: int = 5,
    refresh: bool = False,
    technical_rerank: bool = False,
    target_aspect_ratio: str = "9:16",
    no_html: bool = False,
    offline: bool = False,
) -> dict[str, Any]:
    from .review_bundle import create_scene_review_bundle, write_review_bundle

    root = Path(project_root)
    visual_plan = _read_json(_visual_plan_path(root))
    assets_manifest = _read_json(root / "assets" / "assets_manifest.json")
    request_base = VisualPreviewRequest(
        project_id=project_id,
        top_k=top_k,
        target_aspect_ratio=target_aspect_ratio,
        project_root=str(root),
        refresh=refresh,
        technical_rerank=technical_rerank,
        no_html=no_html,
        offline=offline,
    )
    scenes_by_id = {str(scene.get("scene_id") or ""): scene for scene in visual_plan.get("scenes", [])}
    bundles = []
    for scene_entry in assets_manifest.get("scenes", []):
        current_scene_id = str(scene_entry.get("scene_id") or "")
        if scene_id and current_scene_id != scene_id:
            continue
        if not all_scenes and not scene_id:
            continue
        scene = {**scenes_by_id.get(current_scene_id, {}), **scene_entry}
        candidates = _scene_candidates(scene_entry)
        request = dataclasses.replace(request_base, scene_id=current_scene_id)
        analyses = prepare_candidate_preview_analyses(candidates, providers_by_name={}, request=request)
        selected = scene_entry.get("selected_asset") or (candidates[0] if candidates else {})
        bundle = create_scene_review_bundle(
            project_id=project_id,
            scene=scene,
            semantic_scene=scene_entry.get("semantic_scene", {}),
            metadata_queries=scene_entry.get("queries", []),
            provider_routing=scene_entry.get("provider_routing", {}),
            candidates=candidates,
            analyses=analyses,
            selected_candidate_id=str(selected.get("asset_id") or ""),
            target_aspect_ratio=target_aspect_ratio,
            manual_request=scene_entry.get("manual_request", {}),
        )
        bundles.append(bundle)
    result = write_review_bundle(root, bundles, write_html=not no_html)
    return {"status": "completed", "scene_count": len(bundles), **result}


def inspect_visual_preview_project(project_root: str | Path) -> dict[str, Any]:
    from .review_bundle import inspect_review_manifest

    root = Path(project_root)
    return inspect_review_manifest(root / "assets" / "review" / "visual_review_manifest.json")


def _materialize_preview(
    preview: CandidatePreview,
    cache: PreviewCache,
    request: VisualPreviewRequest,
    config: dict[str, Any],
) -> PreviewCacheRecord:
    media_type = preview.preview_media_type or "image"
    if not request.refresh:
        hit = cache.read(preview.cache_key, media_type=media_type)
        if hit:
            return hit
    max_duration = float(config.get("video_preview_max_duration_sec", 8.0))
    if preview.preview_local_source:
        return create_local_preview(
            preview.preview_local_source,
            cache.root,
            media_type=media_type,
            cache_key=preview.cache_key,
            max_duration_sec=max_duration,
        )
    if not preview.preview_source_url:
        raise ValueError(preview.fallback_reason or "preview_unavailable")
    if request.offline:
        raise ValueError("offline_no_cache")
    local_file = _file_url_to_path(preview.preview_source_url)
    if local_file:
        return create_local_preview(local_file, cache.root, media_type=media_type, cache_key=preview.cache_key, max_duration_sec=max_duration)
    extension = Path(urlparse(preview.preview_source_url).path).suffix or (".jpg" if media_type == "image" else ".mp4")
    allowed = {"image/jpeg", "image/png", "image/webp"} if media_type == "image" else {"video/mp4", "video/webm", "video/quicktime", "application/octet-stream"}
    client = ProviderHttpClient(timeout=float(config.get("download_timeout_sec", 20)))
    target = cache.root / _safe(preview.cache_key) / f"remote{_safe_extension(extension, media_type)}"
    result = client.download_stream(
        preview.preview_source_url,
        target,
        allowed_content_types=allowed,
        max_bytes=cache.max_preview_size_bytes,
        min_bytes=64,
        timeout=float(config.get("download_timeout_sec", 20)),
        network_action=NETWORK_ACTION_PREVIEW_DOWNLOAD,
    )
    record = _record_for_file(preview.cache_key, target, media_type=media_type, source_url=preview.preview_source_url, cache_status="stored")
    record.sha256 = result.get("checksum_sha256") or record.sha256
    record.expected_content_type = result.get("content_type") or ""
    cache._write_record(record)
    return record


def _provider_preview(provider: Any | None, candidate: AssetCandidate) -> AssetPreview:
    if provider is None or not hasattr(provider, "get_preview"):
        return AssetPreview(candidate_id=candidate.asset_id)
    try:
        return provider.get_preview(candidate)
    except Exception:
        return AssetPreview(candidate_id=candidate.asset_id, fallback_reason="provider_preview_failed")


def _fill_provider_specific_preview(preview: CandidatePreview, candidate: AssetCandidate) -> None:
    raw = candidate.raw_metadata
    if candidate.provider == "fake":
        fixture = str(raw.get("fixture_path") or "")
        if fixture and Path(fixture).exists():
            preview.preview_local_source = fixture
            preview.preview_media_type = _media_type_from_path(Path(fixture), fallback=candidate.media_type)
            preview.fallback_reason = "fake_fixture_preview"
            preview.rendition = "fake_fixture"
            return
    if candidate.provider == "pixabay":
        hit = raw.get("pixabay") if isinstance(raw.get("pixabay"), dict) else {}
        videos = hit.get("videos") if isinstance(hit.get("videos"), dict) else {}
        small = _smallest_video_variant(videos)
        if small:
            preview.preview_source_url = small
            preview.preview_media_type = "video"
            preview.rendition = "pixabay_small_video_variant"
            preview.fallback_reason = "pixabay_video_variant"
            return
    if candidate.provider == "pexels":
        video = raw.get("pexels") if isinstance(raw.get("pexels"), dict) else {}
        small = _smallest_pexels_video(video.get("video_files", []) if isinstance(video.get("video_files"), list) else [])
        if small:
            preview.preview_source_url = small
            preview.preview_media_type = "video"
            preview.rendition = "pexels_small_video_file"
            preview.fallback_reason = "pexels_video_variant"
            return
    if candidate.provider == "internet_archive" and candidate.provider_asset_id:
        preview.preview_source_url = f"https://archive.org/services/img/{candidate.provider_asset_id}"
        preview.preview_media_type = "image"
        preview.rendition = "internet_archive_thumbnail"
        preview.fallback_reason = "internet_archive_services_thumbnail"
        return
    if candidate.preview_url:
        preview.preview_source_url = candidate.preview_url
        preview.preview_media_type = _media_type_from_url(candidate.preview_url, fallback=candidate.media_type)
        preview.fallback_reason = "candidate_preview_url"
        preview.rendition = "candidate_preview"


def _attach_similarity(analyses: list[dict[str, Any]], config: dict[str, Any]) -> None:
    from .perceptual_similarity import PerceptualSignature, compare_signatures

    signatures: list[PerceptualSignature] = []
    for item in analyses:
        raw = item.get("perceptual_signature") or {}
        signatures.append(
            PerceptualSignature(
                asset_id=str(raw.get("asset_id") or item.get("asset_id") or ""),
                media_type=str(raw.get("media_type") or "image"),
                frame_hashes=list(raw.get("frame_hashes") or []),
                frame_sha256=list(raw.get("frame_sha256") or []),
                source_sha256=str(raw.get("source_sha256") or ""),
                status=str(raw.get("status") or item.get("analysis_status") or "failed"),
            )
        )
    thresholds = config.get("similarity_thresholds", {}) if isinstance(config.get("similarity_thresholds"), dict) else {}
    near = int(thresholds.get("near_hash_distance", 6))
    similar = int(thresholds.get("similar_hash_distance", 20))
    for index, item in enumerate(analyses):
        scores = []
        for other_index, other in enumerate(analyses):
            if index == other_index:
                continue
            result = compare_signatures(signatures[index], signatures[other_index], near_threshold=near, similar_threshold=similar)
            if result.classification != "not_similar":
                scores.append(result.to_dict())
        item["duplicate_scores"] = scores


def _record_for_file(
    cache_key: str,
    path: Path,
    *,
    media_type: str,
    source_url: str,
    expected_content_type: str = "",
    cache_status: str,
) -> PreviewCacheRecord:
    width = height = 0
    duration = 0.0
    actual_media_type = _media_type_from_path(path, fallback=media_type)
    if actual_media_type == "image":
        with Image.open(path) as image:
            width, height = image.size
    else:
        info = ffprobe_media_info(path)
        width = int(info.get("width") or 0)
        height = int(info.get("height") or 0)
        duration = float(info.get("duration_sec") or 0.0)
    return PreviewCacheRecord(
        cache_key=cache_key,
        local_path=str(path),
        preview_media_type=actual_media_type,
        preview_source_url=source_url,
        width=width,
        height=height,
        duration_sec=duration,
        expected_content_type=expected_content_type,
        expected_size_bytes=path.stat().st_size,
        sha256=sha256_file(path),
        bytes=path.stat().st_size,
        cache_status=cache_status,
    )


def _create_image_preview(source: Path, target: Path, *, max_dimension: int) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    part = target.with_suffix(target.suffix + ".part")
    with Image.open(source) as image:
        image = image.convert("RGB")
        image.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
        image.save(part, format="JPEG", quality=86)
    part.replace(target)


def _create_video_preview(source: Path, target: Path, *, max_dimension: int, max_duration_sec: float) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    part = target.with_name(target.stem + ".part" + target.suffix)
    if part.exists():
        part.unlink()
    command = [
        imageio_ffmpeg.get_ffmpeg_exe(),
        "-y",
        "-v",
        "error",
        "-i",
        str(source),
        "-t",
        f"{max(0.1, float(max_duration_sec)):.3f}",
        "-vf",
        f"scale={int(max_dimension)}:-2:force_original_aspect_ratio=decrease,fps=12,format=yuv420p",
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "28",
        str(part),
    ]
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise RuntimeError((result.stderr or "").strip() or "ffmpeg_video_preview_failed")
    part.replace(target)


def _validate_preview_file(path: Path, media_type: str) -> bool:
    try:
        actual = _media_type_from_path(path, fallback=media_type)
        if actual == "image":
            with Image.open(path) as image:
                image.verify()
            return True
        info = ffprobe_media_info(path)
        return info.get("status") == "passed" and bool(info.get("width")) and bool(info.get("height"))
    except Exception:
        return False


def _request_cache_root(request: VisualPreviewRequest, config: dict[str, Any]) -> Path:
    if request.cache_root:
        return Path(request.cache_root)
    if request.project_root:
        return Path(request.project_root) / "assets" / "previews"
    configured = Path(str(config.get("preview_cache_root") or "assets/cache/previews"))
    if configured.is_absolute():
        return configured
    from src.config_resolver.paths import resolve_application_paths

    return resolve_application_paths().workspace.root / configured


def _scene_candidates(scene_entry: dict[str, Any]) -> list[dict[str, Any]]:
    candidates = []
    seen = set()
    for key in ("ranked_candidates", "candidates"):
        for candidate in scene_entry.get(key, []) or []:
            asset_id = str(candidate.get("asset_id") or "")
            if asset_id and asset_id not in seen:
                seen.add(asset_id)
                candidates.append(candidate)
    selected = scene_entry.get("selected_asset") or {}
    if selected and str(selected.get("asset_id") or "") not in seen:
        candidates.insert(0, selected)
    return candidates


def _visual_plan_path(root: Path) -> Path:
    localizations = root / "localizations"
    if localizations.exists():
        for path in localizations.glob("*/visual/visual_plan.json"):
            return path
    return root / "localizations" / "ru" / "visual" / "visual_plan.json"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_standalone_record(folder: Path, record: PreviewCacheRecord) -> None:
    path = folder / "preview_record.json"
    temp = path.with_suffix(path.suffix + ".part")
    temp.write_text(json.dumps(record.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def _file_url_to_path(url: str) -> Path | None:
    parsed = urlparse(url)
    if parsed.scheme != "file":
        return None
    raw = unquote(parsed.path)
    if re.match(r"^/[A-Za-z]:/", raw):
        raw = raw[1:]
    path = Path(raw)
    return path if path.exists() else None


def _preview_local_source_path(source: str) -> Path | None:
    if not source:
        return None
    if re.match(r"^[A-Za-z]:[\\/]", source):
        return Path(source)
    parsed = urlparse(source)
    if parsed.scheme == "file":
        raw = unquote(parsed.path)
        if re.match(r"^/[A-Za-z]:/", raw):
            raw = raw[1:]
        return Path(raw)
    if parsed.scheme:
        return None
    return Path(source)


def _media_type_from_path(path: Path, *, fallback: str) -> str:
    suffix = path.suffix.lower()
    if suffix in IMAGE_SUFFIXES:
        return "image"
    if suffix in VIDEO_SUFFIXES:
        return "video"
    return fallback or "image"


def _media_type_from_url(url: str, *, fallback: str) -> str:
    suffix = Path(urlparse(url).path).suffix.lower()
    if suffix in IMAGE_SUFFIXES:
        return "image"
    if suffix in VIDEO_SUFFIXES:
        return "video"
    guessed = mimetypes.guess_type(url)[0] or ""
    if guessed.startswith("image/"):
        return "image"
    if guessed.startswith("video/"):
        return "video"
    return fallback or "image"


def _safe_extension(extension: str, media_type: str) -> str:
    extension = extension.lower()
    allowed = IMAGE_SUFFIXES | VIDEO_SUFFIXES
    if extension in allowed:
        return extension
    return ".jpg" if media_type == "image" else ".mp4"


def _safe(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", str(value or "")).strip("_")[:96] or "preview"


def _allow_original_fallback(candidate: AssetCandidate, request: VisualPreviewRequest) -> bool:
    if request.offline:
        return False
    config = load_visual_preview_config()
    return bool(config.get("allow_original_fallback", False)) and candidate.media_type == "image"


def _smallest_video_variant(videos: dict[str, Any]) -> str:
    variants = [value for value in videos.values() if isinstance(value, dict) and value.get("url")]
    variants.sort(key=lambda item: int(item.get("width") or 99999) * int(item.get("height") or 99999))
    return str(variants[0].get("url") or "") if variants else ""


def _smallest_pexels_video(files: list[dict[str, Any]]) -> str:
    variants = [item for item in files if str(item.get("file_type") or "").startswith("video") and item.get("link")]
    variants.sort(key=lambda item: int(item.get("width") or 99999) * int(item.get("height") or 99999))
    return str(variants[0].get("link") or "") if variants else ""


def _default_config() -> dict[str, Any]:
    return {
        "enabled": True,
        "mode": "analyse_and_report",
        "shortlist_size": 5,
        "maximum_preview_size_mb": 5,
        "video_preview_max_duration_sec": 8,
        "frame_sample_count": 5,
        "frame_sample_positions": [0.1, 0.3, 0.5, 0.7, 0.9],
        "target_aspect_ratios": ["9:16", "16:9", "1:1"],
        "technical_rerank_enabled": False,
        "preview_cache_root": "assets/cache/previews",
        "refresh_policy": "reuse_valid_cache",
        "download_timeout_sec": 20,
        "similarity_thresholds": {"near_hash_distance": 6, "similar_hash_distance": 20},
    }


def _deep_update(base: dict[str, Any], override: dict[str, Any]) -> None:
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_update(base[key], value)
        else:
            base[key] = value
