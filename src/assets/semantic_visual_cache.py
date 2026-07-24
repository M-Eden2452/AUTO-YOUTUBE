from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .semantic_visual_models import SemanticVisualRequest, SemanticVisualResult


def compute_semantic_cache_key(
    request: SemanticVisualRequest,
    *,
    semantic_config: dict[str, Any],
    prompt_template_version: str,
) -> str:
    public_request = request.to_public_dict()
    frame_identity = [
        {
            "frame_index": frame.get("frame_index"),
            "sha256": frame.get("sha256"),
            "perceptual_hash": frame.get("perceptual_hash"),
            "is_poster_frame": frame.get("is_poster_frame", False),
        }
        for frame in public_request.get("sampled_frame_references", [])
    ]
    config_payload = _semantic_cache_config(semantic_config)
    payload = {
        "version": 1,
        "backend": public_request.get("backend", ""),
        "model": (public_request.get("backend_options") or {}).get("model", ""),
        "backend_version": (public_request.get("backend_options") or {}).get("backend_version", ""),
        "request_schema_version": public_request.get("request_version", ""),
        "requirements": public_request.get("requirements", {}),
        "candidate_id": public_request.get("candidate_id", ""),
        "provider": public_request.get("provider", ""),
        "sampled_frames": frame_identity,
        "semantic_configuration": config_payload,
        "prompt_template_version": prompt_template_version,
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class SemanticVisualCache:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def read(self, cache_key: str) -> SemanticVisualResult | None:
        path = self._result_path(cache_key)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            result = SemanticVisualResult.from_dict(data.get("result") if isinstance(data.get("result"), dict) else data)
            if result.cache_key and result.cache_key != cache_key:
                return None
            result.cache_key = cache_key
            result.assert_valid()
            return result
        except Exception:
            return None

    def write(self, result: SemanticVisualResult) -> Path:
        if not result.cache_key:
            raise ValueError("semantic cache write requires result.cache_key")
        result.assert_valid()
        path = self._result_path(result.cache_key)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": "semantic_cache_record.v1",
            "cache_key": result.cache_key,
            "result": result.to_dict(),
        }
        temp = path.with_suffix(path.suffix + ".part")
        temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temp.replace(path)
        return path

    def _result_path(self, cache_key: str) -> Path:
        return self.root / _safe_cache_key(cache_key) / "semantic_result.json"


def _safe_cache_key(cache_key: str) -> str:
    return re.sub(r"[^a-fA-F0-9]+", "_", str(cache_key or "")).strip("_")[:96] or "semantic"


def _semantic_cache_config(config: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "mode",
        "minimum_confidence",
        "hard_reject_confidence",
        "maximum_frames_per_candidate",
        "maximum_candidates",
        "semantic_rerank_enabled",
        "request_version",
        "result_version",
        "backend",
        "model",
    }
    return {key: config.get(key) for key in sorted(allowed) if key in config}
