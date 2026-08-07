"""Canonical boundary получения semantic evidence по кандидатам сцены.

Слой между review-манифестом проекта и сменным semantic backend. Он готовит
запрос по кандидату, отвечает за кэш и записывает evidence обратно в
существующий ``assets/review/visual_review_manifest.json``. Evidence-провайдер,
а не второй selector: окончательный выбор кандидата остаётся у существующего
владельца решения в ``src.assets.semantic_selection``.

Responsibilities:
- ``load_semantic_visual_config`` — конфигурация с tolerant чтением
  ``config/semantic_visual.json`` поверх встроенных значений по умолчанию;
- ``create_semantic_visual_backend`` — выбор backend (``mock``, ``openai``,
  внешний) по имени;
- ``analyse_semantic_visual_for_project`` — проход по сценам и bounded
  shortlist, кэшированный вызов backend, запись результата и semantic rank,
  сводка выполнения;
- ``analyse_semantic_visual_for_shortlist`` — тот же проход по одной сцене,
  вызываемый **до** окончательного отбора; результат отдаётся существующему
  владельцу решения через ``vision_tags``;
- ``inspect_semantic_visual_project`` — read-only состояние без вызовов.

Does not own:
- сам backend и его протокол — ``semantic_visual_backend`` и реализации
  ``semantic_visual_mock`` / ``semantic_visual_openai`` /
  ``semantic_visual_external``;
- ключ и хранение кэша — ``semantic_visual_cache``;
- форму review-манифеста и его запись — ``review_bundle``;
- решение об отборе кандидата — ``src.assets.semantic_selection``;
- права и лицензии — ``src.assets.license_policy``;
- поиск, скачивание и сборку манифеста ассетов — ``src.assets``, ``src.news``;
- offline dataset, метрики и отчёты калибровки —
  ``src.assets.semantic_visual_evaluation*``.

Inputs: корень проекта, идентификатор проекта, сцена или ``all_scenes``, имя
backend либо готовый backend, флаги ``offline`` / ``refresh`` и лимиты
кандидатов и кадров.

Outputs: обновлённый review-манифест и сводка — обработанные сцены и
кандидаты, попадания и промахи кэша, число вызовов backend, hard rejects и
число случаев, требующих проверки человеком.

Important invariants:
- модуль даёт evidence, а не финальный выбор; неожиданная смена уже выбранного
  кандидата фиксируется как ``selection_warning``, а не выполняется молча;
- оба входа строят один и тот же запрос по одному и тому же shortlist, поэтому
  кандидат анализируется и оплачивается один раз, а не дважды;
- ``offline`` не выполняет ни одного вызова backend: промах кэша даёт явный
  ``offline_cache_miss``, а не тихий успех;
- анализ ограничен bounded shortlist и лимитом кадров, поэтому объём вызовов
  предсказуем до запуска;
- сбой backend и низкая уверенность приводят к ``review_required``, а не к
  молчаливому пропуску кандидата (fail-closed);
- повторный запуск с включённым кэшем не тратит вызовы заново;
- второй semantic stack, второй selector и второй manifest не создаются.

See also: ``src/assets/README.md``, ``src/assets/semantic_selection/__init__.py``,
``src/assets/semantic_visual_cache.py``, ``docs/current/PRODUCT_PLAN.md``.
"""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .semantic_visual_backend import SemanticVisualBackend
from .semantic_visual_cache import SemanticVisualCache, compute_semantic_cache_key
from .semantic_visual_external import ExternalSemanticVisualBackend
from .semantic_visual_mock import MockSemanticVisualBackend
from .semantic_visual_openai import OpenAISemanticVisualBackend
from .semantic_visual_models import (
    SceneVisualRequirements,
    SemanticFrameReference,
    SemanticVisualRequest,
    fallback_semantic_result,
    apply_semantic_aggregation_rules,
    semantic_result_vision_tags,
)


from src.config_resolver.paths import repository_path


DEFAULT_SEMANTIC_CONFIG_PATH = repository_path("config", "semantic_visual.json")
DEFAULT_PROMPT_TEMPLATE_VERSION = "semantic_visual_prompt.v1"


def load_semantic_visual_config(path: str | Path = DEFAULT_SEMANTIC_CONFIG_PATH) -> dict[str, Any]:
    target = Path(path)
    config = _default_config()
    if target.exists():
        try:
            data = json.loads(target.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                _deep_update(config, data)
        except json.JSONDecodeError:
            pass
    return config


def create_semantic_visual_backend(backend_name: str, config: dict[str, Any]) -> SemanticVisualBackend:
    if backend_name == "mock":
        return MockSemanticVisualBackend(model=str(config.get("model") or "mock-semantic-v1"))
    if backend_name == "openai":
        return OpenAISemanticVisualBackend(config)
    backend_config = dict(config)
    backend_config["backend"] = backend_name or backend_config.get("backend") or "external"
    return ExternalSemanticVisualBackend(backend_config)


@dataclass(frozen=True)
class _SemanticRun:
    """Everything one analysis run needs, resolved once.

    Both entry points below build this the same way, so the request - and therefore the
    cache key - does not depend on which of them asked for the analysis.
    """

    backend: SemanticVisualBackend
    backend_name: str
    backend_version: str
    model: str
    semantic_config: dict[str, Any]
    cache: SemanticVisualCache
    prompt_template_version: str
    max_candidates: int
    max_frames: int
    minimum_confidence: float
    hard_reject_confidence: float
    offline: bool
    project_root: Path
    project_id: str


def _prepare_run(
    *,
    project_root: Path,
    project_id: str,
    backend: SemanticVisualBackend | None,
    backend_name: str,
    refresh: bool,
    offline: bool,
    maximum_candidates: int | None,
    maximum_frames: int | None,
    config: dict[str, Any] | None,
) -> _SemanticRun:
    semantic_config = load_semantic_visual_config()
    if config:
        _deep_update(semantic_config, config)
    if backend_name:
        semantic_config["backend"] = backend_name
    if refresh:
        semantic_config["refresh_cache"] = True
    effective_backend_name = str(semantic_config.get("backend") or "mock")
    selected_backend = backend or create_semantic_visual_backend(effective_backend_name, semantic_config)
    capabilities = selected_backend.capabilities()
    effective_model = capabilities.model or str(semantic_config.get("model") or "")
    if effective_model:
        semantic_config["model"] = effective_model
    semantic_config["backend"] = capabilities.backend or effective_backend_name
    semantic_config["backend_version"] = capabilities.backend_version
    return _SemanticRun(
        backend=selected_backend,
        backend_name=capabilities.backend or effective_backend_name,
        backend_version=capabilities.backend_version,
        model=effective_model,
        semantic_config=semantic_config,
        cache=SemanticVisualCache(_semantic_cache_root(project_root, semantic_config)),
        prompt_template_version=str(semantic_config.get("prompt_template_version") or DEFAULT_PROMPT_TEMPLATE_VERSION),
        max_candidates=int(maximum_candidates or semantic_config.get("maximum_candidates") or 5),
        max_frames=int(maximum_frames or semantic_config.get("maximum_frames_per_candidate") or capabilities.maximum_frames or 5),
        minimum_confidence=float(semantic_config.get("minimum_confidence") or 0.65),
        hard_reject_confidence=float(semantic_config.get("hard_reject_confidence") or 0.90),
        offline=offline,
        project_root=project_root,
        project_id=project_id,
    )


def _analyse_scene_shortlist(
    run: _SemanticRun,
    *,
    scene_id: str,
    scene: dict[str, Any],
    requirements: SceneVisualRequirements,
    shortlist: list[dict[str, Any]],
    summary: dict[str, Any],
) -> list[Any]:
    """One scene's bounded shortlist, analysed once. The only place a call is made."""
    semantic_config = run.semantic_config
    results: list[Any] = []
    for candidate in shortlist[: max(0, run.max_candidates)]:
        summary["candidates_processed"] += 1
        request = _request_for_candidate(
            project_id=run.project_id,
            scene_id=scene_id,
            backend_name=run.backend_name,
            model=run.model,
            backend_version=run.backend_version,
            requirements=requirements,
            candidate=candidate,
            scene=scene,
            project_root=run.project_root,
            maximum_frames=run.max_frames,
            semantic_config=semantic_config,
        )
        cache_key = compute_semantic_cache_key(request, semantic_config=semantic_config, prompt_template_version=run.prompt_template_version)
        result = None
        if bool(semantic_config.get("cache_enabled", True)) and not bool(semantic_config.get("refresh_cache", False)):
            result = run.cache.read(cache_key)
            if result:
                summary["cache_hits"] += 1
        if not result:
            summary["cache_misses"] += 1
            if run.offline:
                result = fallback_semantic_result(
                    backend=run.backend_name,
                    model=run.model,
                    backend_version=run.backend_version,
                    request_version=request.request_version,
                    status="offline_cache_miss",
                    error_code="offline_cache_miss",
                    message="Offline semantic analysis requires an existing cache entry.",
                    cache_key=cache_key,
                )
            else:
                summary["backend_calls"] += 1
                result = _safe_backend_call(run.backend, request, cache_key, run.minimum_confidence, run.hard_reject_confidence)
                if bool(semantic_config.get("cache_enabled", True)):
                    try:
                        run.cache.write(result)
                    except ValueError:
                        pass
        result.cache_key = cache_key
        _attach_candidate_semantic_result(candidate, result)
        results.append(result)
        if result.status == "success":
            summary["successful_analyses"] += 1
        else:
            summary["failed_analyses"] += 1
        if result.hard_reject:
            summary["hard_rejects"] += 1
        if result.review_required_reasons or result.status != "success":
            summary["review_required"] += 1
    _attach_semantic_ranks(shortlist)
    return results


def analyse_semantic_visual_for_shortlist(
    *,
    project_root: str | Path,
    project_id: str,
    scene_id: str,
    semantic_scene: dict[str, Any],
    scene_text: str = "",
    target_aspect_ratio: str = "",
    shortlist: list[dict[str, Any]],
    backend_name: str = "",
    backend: SemanticVisualBackend | None = None,
    refresh: bool = False,
    offline: bool = False,
    maximum_candidates: int | None = None,
    maximum_frames: int | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Analyse one scene's bounded shortlist while the choice can still be affected.

    The same producer and the same request as ``analyse_semantic_visual_for_project``:
    the caller passes the candidates in the shape the review board writes them, so both
    entry points compute the same cache key and a candidate is paid for once.

    Every analysed candidate is given ``vision_tags`` - the field
    ``src.assets.semantic_selection.evidence`` already reads - and nothing else. What
    that evidence is worth stays with the ranker; this function selects nothing.
    """
    root = Path(project_root)
    run = _prepare_run(
        project_root=root,
        project_id=project_id,
        backend=backend,
        backend_name=backend_name,
        refresh=refresh,
        offline=offline,
        maximum_candidates=maximum_candidates,
        maximum_frames=maximum_frames,
        config=config,
    )
    summary = _empty_summary(root / "assets" / "review" / "visual_review_manifest.json")
    summary["backend"] = run.backend_name
    summary["estimated_cost"] = 0.0
    summary["paid_calls_performed"] = False
    summary["scenes_processed"] = 1
    scene = {
        "scene_id": scene_id,
        "scene_text": scene_text,
        "target_aspect_ratio": target_aspect_ratio,
    }
    requirements = SceneVisualRequirements.from_current_semantic_scene(semantic_scene or {}, scene=scene)
    results = _analyse_scene_shortlist(
        run,
        scene_id=scene_id,
        scene=scene,
        requirements=requirements,
        shortlist=shortlist,
        summary=summary,
    )
    for candidate, result in zip(shortlist, results):
        candidate["vision_tags"] = semantic_result_vision_tags(result, minimum_confidence=run.minimum_confidence)
    return summary


def analyse_semantic_visual_for_project(
    *,
    project_root: str | Path,
    project_id: str,
    scene_id: str = "",
    all_scenes: bool = False,
    backend_name: str = "",
    backend: SemanticVisualBackend | None = None,
    refresh: bool = False,
    offline: bool = False,
    maximum_candidates: int | None = None,
    maximum_frames: int | None = None,
    no_html: bool = False,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    root = Path(project_root)
    run = _prepare_run(
        project_root=root,
        project_id=project_id,
        backend=backend,
        backend_name=backend_name,
        refresh=refresh,
        offline=offline,
        maximum_candidates=maximum_candidates,
        maximum_frames=maximum_frames,
        config=config,
    )
    semantic_config = run.semantic_config

    manifest_path = root / "assets" / "review" / "visual_review_manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"visual review manifest not found: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_before_selection = _selection_fingerprint(manifest)

    summary = _empty_summary(manifest_path)
    summary["backend"] = run.backend_name
    summary["estimated_cost"] = 0.0
    summary["paid_calls_performed"] = False

    for scene in manifest.get("scenes", []) or []:
        current_scene_id = str(scene.get("scene_id") or "")
        if scene_id and current_scene_id != scene_id:
            continue
        if not all_scenes and not scene_id:
            continue
        summary["scenes_processed"] += 1
        requirements = SceneVisualRequirements.from_current_semantic_scene(
            scene.get("semantic_scene") or {},
            scene={
                "scene_id": current_scene_id,
                "scene_text": scene.get("scene_text", ""),
                "target_aspect_ratio": scene.get("target_aspect_ratio", ""),
            },
        )
        shortlist = scene.get("shortlist") if isinstance(scene.get("shortlist"), list) else []
        _analyse_scene_shortlist(
            run,
            scene_id=current_scene_id,
            scene=scene,
            requirements=requirements,
            shortlist=shortlist,
            summary=summary,
        )

    manifest["semantic_visual"] = {
        "status": "completed",
        "mode": str(semantic_config.get("mode") or "analyse_and_report"),
        "backend": summary["backend"],
        "semantic_rerank_enabled": bool(semantic_config.get("semantic_rerank_enabled", False)),
        "summary": {key: value for key, value in summary.items() if key not in {"manifest_path", "html_path"}},
    }
    if _selection_fingerprint(manifest) != manifest_before_selection:
        manifest["semantic_visual"]["selection_warning"] = "selected_candidate_changed_unexpectedly"
    from .review_bundle import write_review_manifest_data

    paths = write_review_manifest_data(root, manifest, write_html=not no_html)
    summary["manifest_path"] = paths.get("json_path", str(manifest_path))
    summary["html_path"] = paths.get("html_path", "") if not no_html else ""
    return summary


def inspect_semantic_visual_project(project_root: str | Path) -> dict[str, Any]:
    root = Path(project_root)
    manifest_path = root / "assets" / "review" / "visual_review_manifest.json"
    html_path = root / "assets" / "review" / "visual_review_board.html"
    if not manifest_path.exists():
        return {
            "scenes": 0,
            "analysed_candidates": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "successful": 0,
            "failed": 0,
            "hard_rejects": 0,
            "review_required": 0,
            "backend": "",
            "paid_calls": 0,
            "review_manifest_path": str(manifest_path),
            "html_board_path": str(html_path),
        }
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    scenes = manifest.get("scenes", []) or []
    candidates = [candidate for scene in scenes for candidate in scene.get("shortlist", []) if candidate.get("semantic_analysis")]
    semantic = manifest.get("semantic_visual") if isinstance(manifest.get("semantic_visual"), dict) else {}
    summary = semantic.get("summary") if isinstance(semantic.get("summary"), dict) else {}
    return {
        "scenes": len(scenes),
        "analysed_candidates": len(candidates),
        "cache_hits": int(summary.get("cache_hits") or 0),
        "cache_misses": int(summary.get("cache_misses") or 0),
        "successful": sum(1 for candidate in candidates if candidate.get("semantic_status") == "success"),
        "failed": sum(1 for candidate in candidates if candidate.get("semantic_status") != "success"),
        "hard_rejects": sum(1 for candidate in candidates if candidate.get("semantic_analysis", {}).get("hard_reject")),
        "review_required": sum(1 for candidate in candidates if candidate.get("semantic_review_required")),
        "backend": str(semantic.get("backend") or (candidates[0].get("semantic_analysis", {}).get("backend") if candidates else "")),
        "paid_calls": int(bool(summary.get("paid_calls_performed", False))),
        "review_manifest_path": str(manifest_path),
        "html_board_path": str(html_path),
    }


def _safe_backend_call(
    backend: SemanticVisualBackend,
    request: SemanticVisualRequest,
    cache_key: str,
    minimum_confidence: float,
    hard_reject_confidence: float,
):
    try:
        result = backend.analyse_candidate(request)
        result.cache_key = cache_key
        result = apply_semantic_aggregation_rules(
            result,
            request,
            minimum_confidence=minimum_confidence,
            hard_reject_confidence=hard_reject_confidence,
        )
        result.assert_valid()
        return result
    except Exception as exc:
        capabilities = backend.capabilities()
        return fallback_semantic_result(
            backend=capabilities.backend,
            model=capabilities.model,
            backend_version=capabilities.backend_version,
            request_version=request.request_version,
            status="invalid_response",
            error_code="invalid_response",
            message=str(exc),
            cache_key=cache_key,
        )


def _request_for_candidate(
    *,
    project_id: str,
    scene_id: str,
    backend_name: str,
    model: str,
    backend_version: str,
    requirements: SceneVisualRequirements,
    candidate: dict[str, Any],
    scene: dict[str, Any],
    project_root: Path,
    maximum_frames: int,
    semantic_config: dict[str, Any],
) -> SemanticVisualRequest:
    media_type = str(candidate.get("media_type") or candidate.get("type") or "video")
    raw_frames = _candidate_frames(candidate, scene)
    frame_refs = [
        SemanticFrameReference.from_review_frame(frame, project_root=project_root, media_type=media_type)
        for frame in raw_frames[: max(0, maximum_frames)]
    ]
    if media_type == "video" and len(frame_refs) == 1:
        frame_refs[0].is_poster_frame = True
    else:
        for frame in frame_refs:
            frame.is_poster_frame = bool(frame.is_poster_frame and len(frame_refs) == 1)
    candidate_metadata = _candidate_metadata(candidate)
    candidate_metadata["media_type"] = media_type
    return SemanticVisualRequest(
        project_id=project_id,
        scene_id=scene_id,
        backend=backend_name,
        requirements=requirements,
        candidate_id=str(candidate.get("asset_id") or ""),
        provider=str(candidate.get("provider") or ""),
        candidate_metadata=candidate_metadata,
        sampled_frame_references=frame_refs,
        technical_metrics_summary=_technical_summary(candidate),
        maximum_frames=maximum_frames,
        backend_options={
            "model": model,
            "backend_version": backend_version,
            "minimum_confidence": semantic_config.get("minimum_confidence"),
            "hard_reject_confidence": semantic_config.get("hard_reject_confidence"),
        },
        request_version=str(semantic_config.get("request_version") or "semantic_visual_request.v1"),
    )


def _candidate_frames(candidate: dict[str, Any], scene: dict[str, Any]) -> list[dict[str, Any]]:
    frames = candidate.get("sampled_frames") if isinstance(candidate.get("sampled_frames"), list) else []
    if frames:
        return frames
    scene_frames = scene.get("sampled_frames") if isinstance(scene.get("sampled_frames"), dict) else {}
    candidate_frames = scene_frames.get(str(candidate.get("asset_id") or ""))
    return list(candidate_frames or [])


def _candidate_metadata(candidate: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "asset_id",
        "provider",
        "provider_asset_id",
        "media_type",
        "type",
        "title",
        "description",
        "tags",
        "keywords",
        "source_page_url",
        "author_name",
        "width",
        "height",
        "duration_sec",
        "orientation",
        "metadata_rank",
        "metadata_score",
        "technical_score",
        "semantic_fixture",
        "mock_semantic_case",
    }
    return copy.deepcopy({key: candidate.get(key) for key in allowed if key in candidate})


def _technical_summary(candidate: dict[str, Any]) -> dict[str, Any]:
    if isinstance(candidate.get("technical_metrics"), dict):
        return dict(candidate["technical_metrics"])
    return {
        "technical_quality_score": candidate.get("technical_score", 0.0),
        "score_breakdown": candidate.get("score_breakdown", {}),
        "crop_scores": candidate.get("crop_scores", {}),
    }


def _attach_candidate_semantic_result(candidate: dict[str, Any], result: Any) -> None:
    review = result.to_review_dict()
    candidate["semantic_analysis"] = review
    candidate["semantic_score"] = float(review.get("semantic_score") or 0.0)
    candidate["semantic_status"] = str(review.get("status") or "")
    candidate["semantic_review_required"] = bool(review.get("review_required_reasons") or review.get("status") != "success")


def _attach_semantic_ranks(shortlist: list[dict[str, Any]]) -> None:
    analysed = [candidate for candidate in shortlist if candidate.get("semantic_analysis")]
    analysed.sort(
        key=lambda item: (
            bool(item.get("semantic_analysis", {}).get("hard_reject")),
            -float(item.get("semantic_score") or 0.0),
            int(item.get("metadata_rank") or 9999),
        )
    )
    for rank, candidate in enumerate(analysed, start=1):
        candidate["semantic_rank"] = rank


def _semantic_cache_root(project_root: Path, config: dict[str, Any]) -> Path:
    configured = str(config.get("cache_root") or "")
    if configured:
        path = Path(configured)
        if path.is_absolute():
            return path
        from src.config_resolver.paths import resolve_application_paths

        return resolve_application_paths().workspace.root / path
    if project_root:
        return project_root / "assets" / "semantic_cache"
    from src.config_resolver.paths import resolve_application_paths

    return resolve_application_paths().workspace.provider_cache / "semantic_visual"


def _selection_fingerprint(manifest: dict[str, Any]) -> list[tuple[str, str]]:
    return [
        (str(scene.get("scene_id") or ""), str((scene.get("selected_candidate") or {}).get("asset_id") or ""))
        for scene in manifest.get("scenes", []) or []
    ]


def _empty_summary(manifest_path: Path) -> dict[str, Any]:
    return {
        "status": "completed",
        "scenes_processed": 0,
        "candidates_processed": 0,
        "cache_hits": 0,
        "cache_misses": 0,
        "backend_calls": 0,
        "successful_analyses": 0,
        "failed_analyses": 0,
        "hard_rejects": 0,
        "review_required": 0,
        "estimated_cost": 0.0,
        "paid_calls_performed": False,
        "manifest_path": str(manifest_path),
        "html_path": str(manifest_path.with_name("visual_review_board.html")),
    }


def _default_config() -> dict[str, Any]:
    return {
        "enabled": False,
        "mode": "analyse_and_report",
        "backend": "mock",
        "model": "",
        "maximum_candidates": 5,
        "maximum_frames_per_candidate": 5,
        "minimum_confidence": 0.65,
        "hard_reject_confidence": 0.90,
        "semantic_rerank_enabled": False,
        "allow_paid_vision": False,
        "maximum_calls_per_project": 0,
        "maximum_budget_usd": 0,
        "cache_enabled": True,
        "refresh_cache": False,
        "request_version": "semantic_visual_request.v1",
        "result_version": "semantic_visual_result.v1",
        "prompt_template_version": DEFAULT_PROMPT_TEMPLATE_VERSION,
        "openai": {
            "enabled": False,
            "primary_model": "gpt-5.6-terra",
            "comparison_model": "gpt-5.6-luna",
            "initial_detail": "low",
            "escalation_detail": "high",
            "allow_auto_detail": False,
            "allow_original_detail": False,
            "reasoning_effort": "low",
            "timeout_sec": 60,
            "maximum_retries": 2,
            "maximum_candidates_per_scene": 3,
            "maximum_frames_per_candidate": 3,
            "maximum_calls_per_project": 0,
            "maximum_budget_usd": 0,
            "allow_paid_vision": False,
        },
    }


def _deep_update(base: dict[str, Any], override: dict[str, Any]) -> None:
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_update(base[key], value)
        else:
            base[key] = value
