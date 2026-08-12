"""Canonical boundary сборки ``assets_manifest`` workflow ``news_to_short``.

Оркестратор стадии ``asset_search``: проходит сцены визуального плана и
собирает для каждой один манифестный ответ. Модуль появился при разделении 6A и
остаётся app-specific orchestration поверх shared contracts ``src.assets``;
``src.news.asset_manager`` сохранён как compatibility facade.

Responsibilities:
- по каждой сцене: приоритет пользовательских ассетов, локальная библиотека,
  провайдерский поиск, ранжирование, отбор, скачивание с повторами и сборка
  ``SceneVisualAssembly``;
- запись фактических попыток: provider attempts, routing decision, query plan,
  download attempts и причины отказа кандидатов;
- запрос semantic/Vision evidence по bounded shortlist **до** окончательного
  отбора, когда это включено конфигурацией, и передача её существующему
  владельцу решения через ``vision_tags``;
- video-first покрытие сцены и учёт повторного использования через
  существующий ``ReuseLedger``;
- контролируемые fallback-ступени, когда материал не найден, и список
  ``missing_scenes``;
- итоговый манифест со schema-версией, сводками и visual review bundle.

Does not own:
- контракт провайдера, модели ассета, скачивание и техническую валидацию —
  ``src.assets``;
- состав автоматического набора провайдеров — ``src.providers.registry``;
- права: ``apply_policy_to_candidate`` / ``with_policy_decision``
  ``src.assets.license_policy`` остаются единственным авторитетом;
- лестницу завершённости и словарь причин — ``src.assets.completion``;
- semantic evidence и решение об отборе — ``src.assets.semantic_selection``,
  ``src.assets.semantic_visual_service``;
- формирование строки запроса к провайдеру — ``src.assets.query_adapter``;
- визуальный план как таковой и порядок стадий — ``src.news.pipeline``.

Inputs: визуальный план, пользовательские ассеты, media index, список
провайдеров, режим завершённости и настройки отбора.

Outputs: dict манифеста, который ``pipeline`` записывает в
``assets/assets_manifest.json``, плюс скачанные файлы внутри проекта.

Important invariants:
- сцена без пригодного материала остаётся честно пустой и попадает в
  ``missing_scenes``; правдоподобная подмена субъекта не создаётся;
- пользовательский ассет имеет приоритет над найденным;
- ``dry_run`` не выполняет ни одного сетевого запроса и ни одного скачивания;
- ни один кандидат не попадает в манифест без provider, source, лицензии и
  контрольной суммы;
- сборщик не решает вопрос прав сам и не переопределяет решение политики;
- fixture-backend (``mock``) не участвует в отборе кандидатов: его ответ выведен
  из самого запроса, поэтому он остаётся доказательством wiring и отчётом, а не
  основанием выбора;
- второй asset pipeline, второй selector и второй manifest owner не создаются.

See also: ``src/news/asset_manager.py``, ``src/news/asset_scene_completion.py``,
``src/news/asset_manifest_summaries.py``, ``src/assets/README.md``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from PIL import Image

from src.assets.completion import (
    MODE_DRAFT_COMPLETE,
    ReuseLedger,
    SceneVisualAssembly,
    assembly_from_selected_asset,
    attach_assembly,
    blocking_reasons,
    normalize_mode,
)
from src.assets.download import validate_local_asset
from src.assets.frame_primitives import sha256_file
from src.assets.generated_infographic import build_generated_asset, spec_from_scene
from src.assets.license_policy import apply_policy_to_candidate
from src.assets.models import (
    ASSET_SCHEMA_VERSION,
    RIGHTS_ALLOWED_STATUSES,
    RIGHTS_REFERENCE_ONLY,
    RIGHTS_USER_OWNED,
    AssetCandidate,
    AssetLicense,
    AssetProvenance,
)
from src.assets.provider_contract import ProviderError
from src.assets.provider_routing import route_providers
from src.assets.query_adapter import (
    STATUS_TRANSLATION_REQUIRED,
    build_scene_queries,
)
from src.assets.review_bundle import (
    attach_selected_asset,
    create_scene_review_bundle,
    write_review_bundle,
)
from src.assets.scene_strategy import CLASS_DATA_INFOGRAPHIC
from src.assets.semantic_selection import (
    analyze_scene,
    check_continuity,
    rank_candidates,
    select_with_media_policy,
)
from src.assets.semantic_selection.decision import (
    DECISION_KEY,
    NEEDS_MANUAL_CONFIRMATION,
    NEEDS_RIGHTS_CLEARANCE,
    SUPPORT_FULL,
    SUPPORT_MANUAL,
    VERDICT_COMPLETE,
    VERDICT_UNVERIFIED,
    SelectionDecision,
    framing_decision,
    read_decision,
    scene_resolution_status,
)
from src.assets.semantic_visual_service import (
    analyse_semantic_visual_for_project,
    analyse_semantic_visual_for_shortlist,
    load_semantic_visual_config,
)
from src.assets.semantic_selection.evidence import (
    bind_vision_tags,
    carry_vision_evidence,
    current_vision_tags,
)
from src.assets.visual_preview import (
    VisualPreviewRequest,
    load_visual_preview_config,
    prepare_candidate_preview_analyses,
)
from src.content.visual_planning import semantic_scene_queries
from src.media_library import search_local_assets
from src.providers.envato_manual_provider import EnvatoManualProvider
from src.utils import project_path

from .asset_manifest_summaries import (
    DEFAULT_MIN_VIDEO_CLIPS,
    DEFAULT_MIN_VIDEO_DURATION_RATIO,
    IMAGE_EXTENSIONS,
    VIDEO_EXTENSIONS,
    apply_video_first_readiness,
    completion_summary,
    summarize_media_coverage,
    video_first_policy,
    visual_support_summary,
)
from .asset_provider_adapters import (
    AssetProvider,
    ensure_selected_asset_downloaded,
    provider_capabilities,
    public_candidate,
    quality_score,
    rank_provider_results,
    rights_block_attempts,
    search_provider,
    stable_asset_id,
    vertical_score,
    with_policy_decision,
)
from .asset_scene_completion import complete_scene_assembly


# Semantic backends that answer from a fixture instead of from the pixels. Their verdict
# is built out of the request, so they confirm every requirement they are handed - which
# is exactly what makes them useful for proving wiring and useless as evidence. Named
# rather than inferred from ``paid_backend``: a local model would cost nothing and still
# be looking at the actual frames.
FIXTURE_SEMANTIC_BACKENDS = frozenset({"mock"})



def _vision_source_sha256(analysis: dict[str, Any]) -> str:
    """Identify the exact preview/source bytes observed by semantic analysis."""
    preview = analysis.get("preview") if isinstance(analysis.get("preview"), dict) else {}
    local_source = Path(str(preview.get("preview_local_source") or ""))
    if str(local_source) not in {"", "."} and local_source.is_file():
        return sha256_file(local_source)
    return str(preview.get("sha256") or "")


@dataclass
class SceneBuildState:
    scene: dict[str, Any]
    semantic_scene: Any
    candidates: list[dict[str, Any]]
    scene_provider_attempts: list[dict[str, Any]]
    provider_capabilities: dict[str, dict[str, Any]]
    routing_decision: dict[str, Any]
    query_plan: Any
    source_class: str
    required_duration: float
    user_ranked: list[dict[str, Any]]
    manual_request: dict[str, Any] | None = None
    generated_asset: dict[str, Any] | None = None
    selected: dict[str, Any] | None = None
    assembly: SceneVisualAssembly | None = None
    download_attempts: list[dict[str, Any]] = field(default_factory=list)
    visual_review_entry: dict[str, Any] = field(default_factory=dict)
    scene_review_bundle: Any = None


class AssetManifestBuilder:
    def __init__(
        self,
        *,
        visual_plan: dict[str, Any],
        user_assets: list[str],
        media_index: dict[str, Any],
        providers: list[AssetProvider] | None,
        dry_run: bool,
        channel: str,
        allow_generated_fallback: bool,
        asset_selection: dict[str, Any] | None,
        project_root: str | Path | None,
        project_id: str,
        max_download_attempts: int,
        completion_mode: str,
        reuse_ledger: ReuseLedger | None,
        allow_infographic_fallback: bool,
        allow_emergency_backdrop: bool,
        prefer_video: bool,
        minimum_video_clips: int,
        minimum_video_duration_ratio: float,
    ) -> None:
        self.visual_plan = visual_plan
        self.media_index = media_index
        self.providers = providers or []
        self.dry_run = dry_run
        self.channel = channel
        self.allow_generated_fallback = allow_generated_fallback
        self.project_root = Path(project_root) if project_root else None
        self.project_id = project_id
        self.max_download_attempts = max_download_attempts
        self.completion_mode = normalize_mode(completion_mode)
        self.reuse = reuse_ledger if reuse_ledger is not None else ReuseLedger()
        self.allow_infographic_fallback = allow_infographic_fallback
        self.allow_emergency_backdrop = allow_emergency_backdrop
        self.prefer_video = prefer_video
        self.minimum_video_clips = minimum_video_clips
        self.minimum_video_duration_ratio = minimum_video_duration_ratio
        self.visual_preview_config = load_visual_preview_config()
        self.semantic_visual_config = load_semantic_visual_config()
        self.selection_config = self._selection_config(asset_selection)
        self.user_candidates = [
            inspect_user_asset(path, index)
            for index, path in enumerate(user_assets, start=1)
        ]
        self.providers_by_name = {
            provider.name: provider for provider in self.providers
        }
        self.provider_errors: list[dict[str, Any]] = []
        self.provider_attempts: list[dict[str, Any]] = []
        self.routing_decisions: list[dict[str, Any]] = []
        self.scene_entries: list[dict[str, Any]] = []
        self.missing_scenes: list[dict[str, Any]] = []
        self.used_asset_ids: set[str] = set()
        self.project_pool: list[dict[str, Any]] = []
        self.review_bundles: list[Any] = []
        self.review_output: dict[str, str] = {}

    def build(self) -> dict[str, Any]:
        for scene in self.visual_plan.get("scenes", []):
            state = self._prepare_scene(scene)
            self._search_scene_providers(state)
            self._add_generated_infographic(state)
            self._select_scene_asset(state)
            self._prepare_visual_review(state)
            self._download_and_complete(state)
            self._apply_fallbacks(state)
            self._record_scene(state)
        # Advisory only. ``_record_scene`` above is the sole owner of scene
        # resolution, and an entry here is read downstream as "this scene has no
        # material": it reaches ``missing_assets.json`` and makes the rights
        # report blocking. A cross-scene keyword heuristic may not return a scene
        # it already resolved, so continuity travels in the manifest report.
        continuity = check_continuity(self.scene_entries)
        self._write_reviews()
        return self._final_manifest(continuity)

    def _selection_config(
        self,
        override: dict[str, Any] | None,
    ) -> dict[str, Any]:
        config = {
            "mode": "semantic",
            "legacy_fallback_enabled": False,
            "vision_validation_enabled": False,
            "visual_preview": {
                "enabled": bool(self.visual_preview_config.get("enabled", True)),
                "mode": str(
                    self.visual_preview_config.get("mode")
                    or "analyse_and_report"
                ),
                "shortlist_size": int(
                    self.visual_preview_config.get("shortlist_size") or 5
                ),
                "technical_rerank_enabled": bool(
                    self.visual_preview_config.get(
                        "technical_rerank_enabled",
                        False,
                    )
                ),
                "target_aspect_ratio": "9:16",
                "offline": False,
                "no_html": False,
            },
            "semantic_visual": {
                "enabled": bool(
                    self.semantic_visual_config.get("enabled", False)
                ),
                "mode": str(
                    self.semantic_visual_config.get("mode")
                    or "analyse_and_report"
                ),
                "backend": str(
                    self.semantic_visual_config.get("backend") or "mock"
                ),
                "maximum_candidates": int(
                    self.semantic_visual_config.get("maximum_candidates") or 5
                ),
                "maximum_frames_per_candidate": int(
                    self.semantic_visual_config.get(
                        "maximum_frames_per_candidate"
                    )
                    or 5
                ),
                "semantic_rerank_enabled": bool(
                    self.semantic_visual_config.get(
                        "semantic_rerank_enabled",
                        False,
                    )
                ),
                "allow_paid_vision": bool(
                    self.semantic_visual_config.get("allow_paid_vision", False)
                ),
                "offline": False,
                "no_html": False,
            },
        }
        return merge_selection_config(config, override or {})

    def _prepare_scene(self, scene: dict[str, Any]) -> SceneBuildState:
        semantic_scene = analyze_scene(scene)
        capabilities = provider_capabilities(self.providers_by_name)
        routing = route_providers(
            scene,
            provider_names=list(self.providers_by_name.keys()),
            provider_enabled={name: True for name in self.providers_by_name},
            capabilities=capabilities,
        )
        self.routing_decisions.append(routing)
        query_plan = build_scene_queries(
            scene,
            providers=list(routing["ordered_providers"]),
            intent_language=str(
                self.visual_plan.get("intent_language")
                or self.visual_plan.get("language")
                or "ru"
            ),
            capabilities=capabilities,
        )
        preferred = set(scene.get("preferred_asset_ids") or [])
        user_ranked = rank_user_assets(
            self.user_candidates,
            scene,
            preferred,
            self.used_asset_ids,
        )
        candidates = [
            *user_ranked,
            *rank_local_assets(
                self.media_index,
                scene,
                self.channel,
                self.used_asset_ids,
            ),
        ]
        return SceneBuildState(
            scene=scene,
            semantic_scene=semantic_scene,
            candidates=candidates,
            scene_provider_attempts=[],
            provider_capabilities=capabilities,
            routing_decision=routing,
            query_plan=query_plan,
            source_class=str(routing.get("source_class") or ""),
            required_duration=float(scene.get("target_duration_sec") or 0),
            user_ranked=user_ranked,
        )

    def _search_scene_providers(self, state: SceneBuildState) -> None:
        if self.dry_run:
            return
        ordered_names = (
            state.routing_decision["ordered_providers"]
            or list(self.providers_by_name)
        )
        providers = [
            self.providers_by_name[name]
            for name in ordered_names
            if name in self.providers_by_name
        ]
        for provider in providers:
            planned = state.query_plan.for_provider(provider.name)
            if not planned:
                blocked = [
                    item
                    for item in state.query_plan.queries
                    if item.provider == provider.name
                    and item.status == STATUS_TRANSLATION_REQUIRED
                ]
                for item in blocked:
                    attempt = {
                        "scene_id": state.scene.get("scene_id", ""),
                        "provider": provider.name,
                        "query": "",
                        "status": "skipped",
                        "reason": STATUS_TRANSLATION_REQUIRED,
                        "message": item.notes,
                    }
                    self._record_provider_attempt(state, attempt)
                continue
            allowed_queries = [
                {
                    "kind": item.kind,
                    "fallback_level": item.fallback_level,
                    "query": item.query,
                    "language": item.language,
                    "query_source": item.source,
                }
                for item in planned
                if not query_not_allowed_for_scene(
                    state.semantic_scene,
                    {
                        "kind": item.kind,
                        "fallback_level": item.fallback_level,
                        "query": item.query,
                        "language": item.language,
                        "query_source": item.source,
                    },
                )
            ]
            for query in allowed_queries:
                self._run_provider_query(state, provider, query)

    def _run_provider_query(
        self,
        state: SceneBuildState,
        provider: AssetProvider,
        query: dict[str, Any],
    ) -> None:
        attempt = {
            "scene_id": state.scene.get("scene_id", ""),
            "provider": provider.name,
            "query": str(query["query"]),
            "query_language": str(query.get("language") or ""),
            "query_source": str(query.get("query_source") or ""),
            "status": "started",
        }
        try:
            results = search_provider(
                provider,
                str(query["query"]),
                state.scene,
                state.semantic_scene.to_dict(),
                project_id=self.project_id,
                limit=5,
            )
            state.candidates.extend(
                rank_provider_results(
                    results,
                    state.scene,
                    str(query["query"]),
                    int(query["fallback_level"]),
                )
            )
            attempt.update({"status": "completed", "result_count": len(results)})
        except ProviderError as exc:
            error = exc.to_dict()
            error.update(
                {
                    "scene_id": state.scene.get("scene_id", ""),
                    "query": str(query["query"]),
                }
            )
            self.provider_errors.append(error)
            attempt.update({"status": "failed", "error": error})
        except Exception as exc:
            error = {
                "code": "provider_unexpected_error",
                "provider": provider.name,
                "scene_id": state.scene.get("scene_id", ""),
                "query": str(query["query"]),
                "message": str(exc),
            }
            self.provider_errors.append(error)
            attempt.update({"status": "failed", "error": error})
        self._record_provider_attempt(state, attempt)

    def _record_provider_attempt(
        self,
        state: SceneBuildState,
        attempt: dict[str, Any],
    ) -> None:
        state.scene_provider_attempts.append(attempt)
        self.provider_attempts.append(attempt)

    def _add_generated_infographic(self, state: SceneBuildState) -> None:
        if not (
            self.allow_infographic_fallback
            and state.source_class == CLASS_DATA_INFOGRAPHIC
            and self.project_root
            and not self.dry_run
        ):
            return
        spec = spec_from_scene(state.scene)
        if spec is None:
            return
        state.generated_asset = build_generated_asset(
            spec,
            project_root=self.project_root,
            project_id=self.project_id or self.project_root.name,
            scene_id=str(state.scene.get("scene_id") or ""),
        )
        ensure_decision(
            state.generated_asset,
            scene_id=str(state.scene.get("scene_id") or ""),
            source_class=state.source_class,
        )
        state.candidates.insert(0, state.generated_asset)

    def _select_scene_asset(self, state: SceneBuildState) -> None:
        if state.user_ranked:
            evaluated_user = rank_candidates(
                state.semantic_scene,
                state.user_ranked,
                used_asset_ids=self.used_asset_ids,
                required_duration_sec=state.required_duration,
                require_provider_metadata=False,
                source_class=state.source_class,
            )
            safe_user = next(
                (
                    item
                    for item in evaluated_user
                    if not blocking_reasons(item, require_local_file=False)
                ),
                None,
            )
            state.selected = dict(safe_user) if safe_user is not None else None
            if state.selected is not None:
                state.selected["rejected"] = False
                state.selected["selected_by"] = "user_asset_priority_manual"
            user_ids = {
                str(item.get("asset_id") or "") for item in state.user_ranked
            }
            state.candidates = [
                *evaluated_user,
                *[
                    item
                    for item in state.candidates
                    if str(item.get("asset_id") or "") not in user_ids
                ],
            ]
            if state.selected is None and state.generated_asset is not None:
                state.selected = state.generated_asset
            elif (
                state.selected is None
                and self.selection_config["mode"] == "semantic"
            ):
                state.selected, state.candidates = select_best_with_video(
                    state.semantic_scene,
                    state.candidates,
                    prefer_video=self.prefer_video,
                    allowed_media_kinds=state.scene.get("allowed_media_kinds"),
                    review_window_size=self._review_window_size(),
                    used_asset_ids=self.used_asset_ids,
                    required_duration_sec=state.required_duration,
                    require_provider_metadata=bool(
                        state.routing_decision.get("requires_provider_metadata")
                    ),
                    source_class=state.source_class,
                )
        elif state.generated_asset is not None:
            state.selected = state.generated_asset
        elif self.selection_config["mode"] == "semantic":
            state.selected, state.candidates = select_best_with_video(
                state.semantic_scene,
                state.candidates,
                prefer_video=self.prefer_video,
                allowed_media_kinds=state.scene.get("allowed_media_kinds"),
                review_window_size=self._review_window_size(),
                used_asset_ids=self.used_asset_ids,
                required_duration_sec=state.required_duration,
                require_provider_metadata=bool(
                    state.routing_decision.get("requires_provider_metadata")
                ),
                source_class=state.source_class,
            )
        else:
            state.candidates.sort(
                key=lambda item: item.get("total_score", 0),
                reverse=True,
            )
            state.selected = state.candidates[0] if state.candidates else None
        state.selected = ensure_decision(
            state.selected,
            scene_id=str(state.scene.get("scene_id") or ""),
            source_class=state.source_class,
        )

    def _prepare_visual_review(self, state: SceneBuildState) -> None:
        settings = (
            self.selection_config.get("visual_preview", {})
            if isinstance(self.selection_config.get("visual_preview"), dict)
            else {}
        )
        if not (
            self.project_root
            and state.candidates
            and bool(settings.get("enabled", True))
        ):
            return
        top_k = self._review_window_size()
        request = self._preview_request(state, settings, top_k)
        analyses = prepare_candidate_preview_analyses(
            state.candidates,
            providers_by_name=self.providers_by_name,
            request=request,
            config=self.visual_preview_config,
        )
        self._apply_semantic_visual_evidence(state, analyses, top_k, request)
        # The id of the asset this scene actually selected, and nothing else. It used
        # to fall back to the top-ranked candidate, which turned an honest abstention
        # into a selection on the review board. VA-NEW-03 left no post-selection owner,
        # so "before" and "after" name the same decision.
        before_id = str((state.selected or {}).get("asset_id") or "")
        technical_analysis_requested = bool(
            settings.get("technical_rerank_enabled", False)
        )
        # The compatibility flag still requests and records technical analysis,
        # but that evidence cannot replace the canonical semantic/media/manual
        # decision made above. Any future technical tie-break must enter through
        # that canonical decision path rather than becoming a post-selection owner.
        after_id = before_id
        bundle = create_scene_review_bundle(
            project_id=self.project_id,
            scene=state.scene,
            semantic_scene=state.semantic_scene.to_dict(),
            metadata_queries=semantic_scene_queries(state.semantic_scene),
            provider_routing=state.routing_decision,
            candidates=state.candidates[:top_k],
            analyses=analyses,
            selected_candidate_id=after_id,
            target_aspect_ratio=request.target_aspect_ratio,
            manual_request=state.manual_request,
            technical_rerank_enabled=technical_analysis_requested,
        )
        self.review_bundles.append(bundle)
        state.scene_review_bundle = bundle
        state.visual_review_entry = {
            "status": "prepared",
            "analysis_mode": (
                "technical_analysis"
                if technical_analysis_requested
                else "analyse_and_report"
            ),
            "analysed_candidates": len(analyses),
            "selected_candidate_before_rerank": before_id,
            "selected_candidate_after_rerank": after_id,
            "manifest_path": str(
                self.project_root
                / "assets"
                / "review"
                / "visual_review_manifest.json"
            ),
            "html_path": (
                ""
                if bool(settings.get("no_html", False))
                else str(
                    self.project_root
                    / "assets"
                    / "review"
                    / "visual_review_board.html"
                )
            ),
        }

    def _apply_semantic_visual_evidence(
        self,
        state: SceneBuildState,
        analyses: list[dict[str, Any]],
        top_k: int,
        request: VisualPreviewRequest,
    ) -> None:
        """Ask the semantic evidence provider about the shortlist while it still matters.

        Vision used to run after every scene had been selected and downloaded, so its
        verdict could describe the result and never change it. Here the same provider is
        asked about the same bounded shortlist, with the previews and frames already
        prepared above, and what it saw is handed to the existing decision owner in the
        field it already reads - ``vision_tags``.

        Nothing is chosen here. ``select_best_with_video`` is asked again, this time with
        the evidence present; a scene answered by the user's own asset or by a figure the
        project drew itself is not ranked material and is left alone.

        A fixture backend is not asked at all. It derives its answer from the requirements
        it was given, so it confirms whatever the scene stated - an iceberg the provider
        never mentioned becomes an observed iceberg, and the requirement is met by the act
        of stating it. That is a report about the wiring, never grounds for a choice, and
        it is the shipped default; the review pass after selection still records it.
        """
        settings = (
            self.selection_config.get("semantic_visual", {})
            if isinstance(self.selection_config.get("semantic_visual"), dict)
            else {}
        )
        backend_name = str(settings.get("backend") or "mock")
        if not (
            self.project_root
            and bool(settings.get("enabled", False))
            and bool(settings.get("semantic_rerank_enabled", False))
            and backend_name not in FIXTURE_SEMANTIC_BACKENDS
        ):
            return
        # The candidates exactly as the review board writes them, so this request and the
        # one built later from the written review manifest are the same request - one
        # analysis, one cache entry, one cost.
        board = create_scene_review_bundle(
            project_id=self.project_id,
            scene=state.scene,
            semantic_scene=state.semantic_scene.to_dict(),
            metadata_queries=semantic_scene_queries(state.semantic_scene),
            provider_routing=state.routing_decision,
            candidates=state.candidates[:top_k],
            analyses=analyses,
            selected_candidate_id=str((state.selected or {}).get("asset_id") or ""),
            target_aspect_ratio=request.target_aspect_ratio,
            manual_request=state.manual_request,
        )
        if not board.shortlist:
            return
        analyse_semantic_visual_for_shortlist(
            project_root=self.project_root,
            project_id=self.project_id,
            scene_id=board.scene_id,
            semantic_scene=board.semantic_scene,
            scene_text=board.scene_text,
            target_aspect_ratio=board.target_aspect_ratio,
            shortlist=board.shortlist,
            backend_name=backend_name,
            offline=bool(settings.get("offline", False)),
            maximum_candidates=int(
                settings.get("maximum_candidates")
                or self.semantic_visual_config.get("maximum_candidates")
                or 5
            ),
            maximum_frames=int(
                settings.get("maximum_frames_per_candidate")
                or self.semantic_visual_config.get(
                    "maximum_frames_per_candidate"
                )
                or 5
            ),
            config=self.semantic_visual_config,
        )
        observed = False
        entries_by_asset = {
            str(entry.get("asset_id") or ""): entry for entry in board.shortlist
        }
        analyses_by_asset = {
            str(analysis.get("asset_id") or ""): analysis for analysis in analyses
        }
        for candidate in state.candidates:
            asset_id = str(candidate.get("asset_id") or "")
            entry = entries_by_asset.get(asset_id, {})
            tags = [str(tag) for tag in entry.get("vision_tags") or []]
            if not tags:
                continue
            semantic = (
                entry.get("semantic_analysis")
                if isinstance(entry.get("semantic_analysis"), dict)
                else {}
            )
            bind_vision_tags(
                candidate,
                tags,
                source_sha256=_vision_source_sha256(
                    analyses_by_asset.get(asset_id, {})
                ),
                cache_key=str(semantic.get("cache_key") or ""),
            )
            canonical = candidate.get("canonical_asset")
            if isinstance(canonical, dict):
                candidate["canonical_asset"] = AssetCandidate.from_dict(
                    carry_vision_evidence(candidate, dict(canonical))
                ).to_dict()
            observed = bool(current_vision_tags(candidate)) or observed
        if not (observed and self._semantic_reselection_allowed(state)):
            return
        # The same canonical policy as the metadata pass, with the same window:
        # Vision evidence may re-rank, it may not widen what media kind can win.
        state.selected, state.candidates = select_best_with_video(
            state.semantic_scene,
            state.candidates,
            prefer_video=self.prefer_video,
            allowed_media_kinds=state.scene.get("allowed_media_kinds"),
            review_window_size=top_k,
            used_asset_ids=self.used_asset_ids,
            required_duration_sec=state.required_duration,
            require_provider_metadata=bool(
                state.routing_decision.get("requires_provider_metadata")
            ),
            source_class=state.source_class,
        )
        state.selected = ensure_decision(
            state.selected,
            scene_id=str(state.scene.get("scene_id") or ""),
            source_class=state.source_class,
        )

    def _review_window_size(self) -> int:
        """The one shortlist number: preview, review board and media policy agree.

        The media policy's video preference may only reach candidates a reviewer
        would actually be shown, so the selection window and the preview window
        must be the same value from the same settings.
        """
        settings = self.selection_config.get("visual_preview")
        values = settings if isinstance(settings, dict) else {}
        return int(
            values.get("shortlist_size")
            or self.visual_preview_config.get("shortlist_size")
            or 5
        )

    def _semantic_reselection_allowed(self, state: SceneBuildState) -> bool:
        """Whether the ranker made this choice, and may therefore be asked again."""
        if str(self.selection_config.get("mode") or "") != "semantic":
            return False
        if state.generated_asset is not None:
            return False
        return (
            str((state.selected or {}).get("selected_by") or "")
            != "user_asset_priority_manual"
        )

    def _preview_request(
        self,
        state: SceneBuildState,
        settings: dict[str, Any],
        top_k: int,
    ) -> VisualPreviewRequest:
        return VisualPreviewRequest(
            project_id=self.project_id,
            scene_id=str(state.scene.get("scene_id") or ""),
            top_k=top_k,
            target_aspect_ratio=str(
                settings.get("target_aspect_ratio") or "9:16"
            ),
            project_root=str(self.project_root),
            refresh=bool(settings.get("refresh", False)),
            offline=bool(settings.get("offline", False)),
            technical_rerank=bool(
                settings.get("technical_rerank_enabled", False)
            ),
            no_html=bool(settings.get("no_html", False)),
            sample_count=int(
                self.visual_preview_config.get("frame_sample_count") or 5
            ),
            sample_positions=[
                float(item)
                for item in self.visual_preview_config.get(
                    "frame_sample_positions",
                    [0.1, 0.3, 0.5, 0.7, 0.9],
                )
            ],
            target_aspect_ratios=[
                str(item)
                for item in self.visual_preview_config.get(
                    "target_aspect_ratios",
                    ["9:16", "16:9", "1:1"],
                )
            ],
        )

    def _download_and_complete(self, state: SceneBuildState) -> None:
        original_selected_asset_id = str((state.selected or {}).get("asset_id") or "")
        if (
            state.generated_asset is not None
            and state.selected is state.generated_asset
        ):
            state.download_attempts = []
        elif state.selected:
            state.selected, state.download_attempts = (
                ensure_selected_asset_downloaded(
                    selected=state.selected,
                    ranked_candidates=state.candidates,
                    providers_by_name=self.providers_by_name,
                    project_root=self.project_root,
                    project_id=self.project_id,
                    scene_id=str(state.scene.get("scene_id") or ""),
                    media_index=self.media_index,
                    max_attempts=self.max_download_attempts,
                )
            )
        elif state.candidates:
            state.download_attempts = rights_block_attempts(
                state.candidates,
                str(state.scene.get("scene_id") or ""),
            )
        if self.completion_mode == MODE_DRAFT_COMPLETE:
            (
                state.selected,
                state.assembly,
                ladder_attempts,
            ) = complete_scene_assembly(
                scene=state.scene,
                semantic_scene=state.semantic_scene,
                candidates=state.candidates,
                strict_selection=state.selected,
                scene_index=len(self.scene_entries),
                duration=state.required_duration,
                reuse=self.reuse,
                providers_by_name=self.providers_by_name,
                project_root=self.project_root,
                project_id=self.project_id,
                media_index=self.media_index,
                dry_run=self.dry_run,
                project_pool=list(self.project_pool),
                source_class=state.source_class,
                download_selected=ensure_selected_asset_downloaded,
                ensure_decision=ensure_decision,
                rank_provider_results=rank_provider_results,
                search_provider=search_provider,
                routing_decision=state.routing_decision,
                provider_capabilities=state.provider_capabilities,
                scene_provider_attempts=state.scene_provider_attempts,
                allow_emergency_backdrop=self.allow_emergency_backdrop,
                original_selected_asset_id=original_selected_asset_id,
            )
            state.download_attempts.extend(ladder_attempts)
        if state.scene_review_bundle is not None:
            attach_selected_asset(state.scene_review_bundle, state.selected)
        if state.download_attempts:
            self.provider_attempts.extend(state.download_attempts)

    def _apply_fallbacks(self, state: SceneBuildState) -> None:
        if (
            not state.selected
            and self.allow_generated_fallback
            and not self.dry_run
            and (
                self.allow_generated_fallback
                or bool(
                    self.selection_config.get("legacy_fallback_enabled", False)
                )
            )
        ):
            state.selected = generated_fallback_asset(state.scene)
        if (
            not state.selected
            and not self.dry_run
            and self.project_root
            and bool(
                self.selection_config.get(
                    "envato_manual_fallback_enabled",
                    False,
                )
            )
        ):
            state.manual_request = EnvatoManualProvider(
                projects_root=self.project_root.parent
            ).prepare_request(
                project_id=self.project_id or self.project_root.name,
                scene_id=str(state.scene.get("scene_id") or ""),
                scene=state.scene,
                # The provider builds its own request from the scene text when this is
                # empty, which is what an idea with no provider-language evidence must
                # produce here - a manual search URL is opened by a person, so a query
                # in a language the index cannot answer is worse than none.
                queries=[
                    str(item["query"])
                    for item in semantic_scene_queries(state.semantic_scene)[:3]
                    if item.get("query")
                ],
                limit=int(
                    self.selection_config.get("envato_manual_query_limit") or 6
                ),
                open_browser=False,
            )
        if state.assembly is None:
            state.assembly = assembly_from_selected_asset(
                {
                    "scene_id": str(state.scene.get("scene_id") or ""),
                    "selected_asset": state.selected or {},
                },
                scene_duration_sec=state.required_duration,
                completion_mode=self.completion_mode,
            )

    def _record_scene(self, state: SceneBuildState) -> None:
        assert state.assembly is not None
        for slot in state.assembly.slots:
            if slot.asset_id:
                self.used_asset_ids.add(slot.asset_id)
            if slot.selected_asset and not any(
                str(item.get("asset_id") or "") == slot.asset_id
                for item in self.project_pool
            ):
                self.project_pool.append(dict(slot.selected_asset))
        if state.selected:
            self.used_asset_ids.add(state.selected["asset_id"])
        unresolved = (
            not state.assembly.usable_in_draft
            if self.completion_mode == MODE_DRAFT_COMPLETE
            else not state.selected
        )
        if unresolved:
            self.missing_scenes.append(self._missing_scene_entry(state))
        entry = self._scene_entry(state)
        attach_assembly(entry, state.assembly)
        self.scene_entries.append(entry)

    def _missing_scene_entry(self, state: SceneBuildState) -> dict[str, Any]:
        reason = (
            "manual_action_required"
            if state.manual_request
            else "selected_asset_not_publish_ready"
            if state.selected
            else "unresolved_generator_failed"
            if state.source_class == CLASS_DATA_INFOGRAPHIC
            else missing_reason(
                self.dry_run,
                state.candidates,
                state.download_attempts,
            )
        )
        return {
            "scene_id": state.scene.get("scene_id"),
            "primary_query": state.scene.get("primary_query", ""),
            "semantic_queries": semantic_scene_queries(state.semantic_scene),
            "semantic_scene": state.semantic_scene.to_dict(),
            "provider_attempts": state.scene_provider_attempts,
            "download_attempts": state.download_attempts,
            "manual_request": state.manual_request or {},
            "source_class": state.source_class,
            "asset_strategy": state.routing_decision.get("strategy", {}),
            "query_plan": state.query_plan.to_dict(),
            "untranslatable_providers": list(
                state.query_plan.untranslatable_providers
            ),
            "rejected_reasons": sorted(
                {
                    str(item.get("reject_reason") or "")
                    for item in state.candidates
                    if item.get("rejected")
                }
                - {""}
            ),
            "resolution_status": scene_resolution_status(
                selected=state.selected,
                candidates=state.candidates,
                source_class=state.source_class,
                manual_request=bool(state.manual_request),
            ),
            "reason": reason,
        }

    def _scene_entry(self, state: SceneBuildState) -> dict[str, Any]:
        return {
            "scene_id": state.scene.get("scene_id"),
            "primary_query": state.scene.get("primary_query", ""),
            "queries": semantic_scene_queries(state.semantic_scene),
            "visual_type": state.scene.get("visual_type", ""),
            "semantic_scene": state.semantic_scene.to_dict(),
            "provider_routing": state.routing_decision,
            "asset_strategy": state.routing_decision.get("strategy", {}),
            "source_class": state.source_class,
            "query_plan": state.query_plan.to_dict(),
            "required_duration_sec": state.required_duration,
            "selected_asset": state.selected,
            "resolution_status": scene_resolution_status(
                selected=state.selected,
                candidates=state.candidates,
                source_class=state.source_class,
                manual_request=bool(state.manual_request),
            ),
            "support_status": (
                read_decision(state.selected).support_status
                if state.selected
                else ""
            ),
            "support_requirements": (
                read_decision(state.selected).support_requirements
                if state.selected
                else []
            ),
            "manual_request": state.manual_request or {},
            "visual_review": state.visual_review_entry,
            "provider_attempts": state.scene_provider_attempts,
            "download_attempts": state.download_attempts,
            "ranked_candidates": [
                public_candidate(candidate)
                for candidate in state.candidates[:10]
            ],
            "candidates": [
                public_candidate(candidate) for candidate in state.candidates[:5]
            ],
            "rejected_candidates": [
                public_candidate(candidate)
                for candidate in state.candidates
                if candidate.get("rejected")
            ][:5],
            "visual_brief": (
                state.scene.get("visual_brief")
                if isinstance(state.scene.get("visual_brief"), dict)
                else {}
            ),
        }

    def _write_reviews(self) -> None:
        if not (self.project_root and self.review_bundles):
            return
        preview = (
            self.selection_config.get("visual_preview", {})
            if isinstance(self.selection_config.get("visual_preview"), dict)
            else {}
        )
        self.review_output = write_review_bundle(
            self.project_root,
            self.review_bundles,
            write_html=not bool(preview.get("no_html", False)),
        )
        semantic = (
            self.selection_config.get("semantic_visual", {})
            if isinstance(self.selection_config.get("semantic_visual"), dict)
            else {}
        )
        if bool(semantic.get("enabled", False)):
            analyse_semantic_visual_for_project(
                project_root=self.project_root,
                project_id=self.project_id,
                all_scenes=True,
                backend_name=str(semantic.get("backend") or "mock"),
                offline=bool(semantic.get("offline", False)),
                maximum_candidates=int(
                    semantic.get("maximum_candidates")
                    or self.semantic_visual_config.get("maximum_candidates")
                    or 5
                ),
                maximum_frames=int(
                    semantic.get("maximum_frames_per_candidate")
                    or self.semantic_visual_config.get(
                        "maximum_frames_per_candidate"
                    )
                    or 5
                ),
                no_html=bool(semantic.get("no_html", False)),
                config=self.semantic_visual_config,
            )

    def _final_manifest(self, continuity: dict[str, Any]) -> dict[str, Any]:
        policy = video_first_policy(
            enabled=self.prefer_video,
            minimum_video_clips=self.minimum_video_clips,
            minimum_video_duration_ratio=self.minimum_video_duration_ratio,
        )
        coverage = summarize_media_coverage(self.scene_entries, policy=policy)
        completion = completion_summary(
            self.scene_entries,
            mode=self.completion_mode,
            reuse=self.reuse,
        )
        apply_video_first_readiness(completion, coverage)
        manifest_warnings = warnings(
            self.dry_run,
            self.provider_errors,
            self.missing_scenes,
        )
        if coverage["review_required"]:
            manifest_warnings.append(
                "Video-first coverage is below the publish-ready threshold; "
                "the image fallback is draft/review only."
            )
        return {
            "schema_version": ASSET_SCHEMA_VERSION,
            "dry_run": self.dry_run,
            "visual_mode": "video_first" if self.prefer_video else "mixed",
            "video_first_policy": policy,
            "media_coverage": coverage,
            "infographic_fallback": bool(self.allow_infographic_fallback),
            "asset_selection": self.selection_config,
            "provider_order": [
                "user_assets",
                "local_library",
                *[provider.name for provider in self.providers],
            ],
            "routing_decisions": self.routing_decisions,
            "assets": self.user_candidates,
            "scenes": self.scene_entries,
            "missing_scenes": self.missing_scenes,
            "visual_support": visual_support_summary(
                self.scene_entries,
                self.missing_scenes,
            ),
            "completion": completion,
            "continuity": continuity,
            "provider_attempts": self.provider_attempts,
            "provider_errors": self.provider_errors,
            "visual_review": self._visual_review_summary(),
            "semantic_visual": self._semantic_visual_summary(),
            "warnings": manifest_warnings,
        }

    def _visual_review_summary(self) -> dict[str, Any]:
        settings = self.selection_config.get("visual_preview")
        values = settings if isinstance(settings, dict) else {}
        return {
            "enabled": bool(values.get("enabled", False)),
            "mode": str(values.get("mode", "analyse_and_report")),
            "manifest_path": self.review_output.get("json_path", ""),
            "html_path": self.review_output.get("html_path", ""),
        }

    def _semantic_visual_summary(self) -> dict[str, Any]:
        settings = self.selection_config.get("semantic_visual")
        values = settings if isinstance(settings, dict) else {}
        return {
            "enabled": bool(values.get("enabled", False)),
            "mode": str(values.get("mode", "analyse_and_report")),
            # Was written as a constant ``False`` while the flag it names had no effect
            # at all. Now that the flag decides whether semantic evidence reaches the
            # selection, the manifest reports what actually happened.
            "semantic_rerank_enabled": bool(
                values.get("semantic_rerank_enabled", False)
            ),
        }


def build_assets_manifest(
    *,
    visual_plan: dict[str, Any],
    user_assets: list[str],
    media_index: dict[str, Any],
    providers: list[AssetProvider] | None = None,
    dry_run: bool = False,
    channel: str = "nature_science_news_ru",
    allow_generated_fallback: bool = False,
    asset_selection: dict[str, Any] | None = None,
    project_root: str | Path | None = None,
    project_id: str = "",
    max_download_attempts: int = 3,
    completion_mode: str = "",
    reuse_ledger: ReuseLedger | None = None,
    allow_infographic_fallback: bool = True,
    allow_emergency_backdrop: bool = True,
    prefer_video: bool = False,
    minimum_video_clips: int = DEFAULT_MIN_VIDEO_CLIPS,
    minimum_video_duration_ratio: float = DEFAULT_MIN_VIDEO_DURATION_RATIO,
) -> dict[str, Any]:
    return AssetManifestBuilder(
        visual_plan=visual_plan,
        user_assets=user_assets,
        media_index=media_index,
        providers=providers,
        dry_run=dry_run,
        channel=channel,
        allow_generated_fallback=allow_generated_fallback,
        asset_selection=asset_selection,
        project_root=project_root,
        project_id=project_id,
        max_download_attempts=max_download_attempts,
        completion_mode=completion_mode,
        reuse_ledger=reuse_ledger,
        allow_infographic_fallback=allow_infographic_fallback,
        allow_emergency_backdrop=allow_emergency_backdrop,
        prefer_video=prefer_video,
        minimum_video_clips=minimum_video_clips,
        minimum_video_duration_ratio=minimum_video_duration_ratio,
    ).build()


def select_best_with_video(
    semantic_scene: Any,
    candidates: list[dict[str, Any]],
    *,
    prefer_video: bool,
    allowed_media_kinds: list[str] | None = None,
    review_window_size: int | None = None,
    **selection_kwargs: Any,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """Compatibility wrapper over the canonical media-selection policy.

    This used to be the unconditional video-first override: the first
    non-rejected video at any rank replaced the ranker's choice (LIVE-4
    scene_003/004, 7 of 12 PLAN-9D-C scenes). The decision now belongs to
    ``src.assets.semantic_selection.media_policy``; the name and signature stay
    for existing callers and the PLAN-9D harnesses until their retirement gate.
    """
    window_kwargs: dict[str, Any] = (
        {} if review_window_size is None else {"review_window_size": review_window_size}
    )
    return select_with_media_policy(
        semantic_scene,
        candidates,
        prefer_video=prefer_video,
        allowed_media_kinds=allowed_media_kinds,
        **window_kwargs,
        **selection_kwargs,
    )


def ensure_decision(
    asset: dict[str, Any] | None,
    *,
    scene_id: str,
    source_class: str,
) -> dict[str, Any] | None:
    if not isinstance(asset, dict) or asset.get(DECISION_KEY):
        return asset
    framing = framing_decision(asset)
    provider = str(asset.get("provider") or "")
    allowed = bool(asset.get("allowed_for_render", False))
    review_required = bool(asset.get("review_required", False))
    if provider == "generated" and source_class == CLASS_DATA_INFOGRAPHIC:
        support, requirements, verdict = SUPPORT_FULL, [], VERDICT_COMPLETE
        reasons = ["generated_from_scene_specification"]
    else:
        support, requirements = SUPPORT_MANUAL, [NEEDS_MANUAL_CONFIRMATION]
        verdict = VERDICT_UNVERIFIED
        reasons = [f"selected_by:{asset.get('selected_by') or 'unranked'}"]
        if review_required or not allowed:
            requirements.append(NEEDS_RIGHTS_CLEARANCE)
    decision = SelectionDecision(
        scene_id=scene_id,
        asset_id=str(asset.get("asset_id") or ""),
        provider=provider,
        source_class=source_class,
        technical_status=str(framing["status"]),
        framing=framing,
        rights_status=str(asset.get("rights_status") or ""),
        rights_allowed_for_render=allowed,
        rights_review_required=review_required,
        slot_verdict=verdict,
        support_status=support,
        support_requirements=requirements,
        selection_reasons=reasons,
    )
    asset[DECISION_KEY] = decision.to_dict()
    asset["support_status"] = support
    asset["slot_verdict"] = verdict
    return asset


def merge_selection_config(
    base: dict[str, Any],
    override: dict[str, Any],
) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            nested = dict(merged[key])
            nested.update(value)
            merged[key] = nested
        else:
            merged[key] = value
    return merged


def inspect_user_asset(path: Any, index: int) -> dict[str, Any]:
    raw = path if isinstance(path, dict) else {"path": str(path)}
    source = Path(str(raw.get("path") or raw.get("local_path") or ""))
    media_kind = media_type(source)
    asset_id = str(raw.get("asset_id") or f"user_asset_{index:03d}")
    rights_declaration = dict(raw.get("rights_declaration") or {})
    if not rights_declaration:
        rights_declaration = {
            "confirmation_status": "missing",
            "rights_status": "unconfirmed",
            "notes": "Manual asset rights were not confirmed by the owner.",
        }
    provider_asset_id = str(raw.get("provider_asset_id") or asset_id)
    source_url = str(
        raw.get("source_page_url")
        or raw.get("source_url")
        or f"manual://{provider_asset_id}"
    )
    width = int(raw.get("width") or 0)
    height = int(raw.get("height") or 0)
    technical_validation: dict[str, Any] = {}
    checksum = ""
    if source.exists():
        try:
            technical_validation = validate_local_asset(source, media_kind)
            width = int(technical_validation.get("width") or width)
            height = int(technical_validation.get("height") or height)
            checksum = sha256_file(source)
        except Exception:
            if media_kind == "image":
                try:
                    with Image.open(source) as image:
                        width, height = image.size
                except Exception:
                    width = height = 0
    candidate = AssetCandidate(
        asset_id=asset_id,
        provider="user",
        provider_asset_id=provider_asset_id,
        media_type=media_kind,
        title=str(raw.get("title") or source.stem),
        description=str(raw.get("description") or ""),
        tags=[source.stem],
        source_page_url=source_url,
        preview_url=str(raw.get("preview_url") or ""),
        download_url=str(raw.get("download_url") or source_url),
        author_name=str(raw.get("author") or raw.get("author_name") or "user"),
        width=width,
        height=height,
        duration_sec=float(raw.get("duration") or raw.get("duration_sec") or 0),
        local_path=str(source),
        original_filename=source.name,
        checksum_sha256=checksum,
        license=AssetLicense(
            license_name=str(
                rights_declaration.get("license_name")
                or raw.get("license")
                or "user_owned"
            ),
            rights_status=str(
                rights_declaration.get("rights_status") or RIGHTS_USER_OWNED
            ),
            allowed_for_render=False,
            review_required=True,
            notes=str(rights_declaration.get("notes") or ""),
        ),
        provenance=AssetProvenance(
            provider="user",
            provider_asset_id=provider_asset_id,
            source_page_url=source_url,
            download_url=str(raw.get("download_url") or source_url),
            original_filename=source.name,
            checksum_sha256=checksum,
            metadata_snapshot={"rights_declaration": rights_declaration},
        ),
        technical_validation=technical_validation,
        rights_declaration=rights_declaration,
    )
    apply_policy_to_candidate(candidate)
    data = candidate.to_manifest_dict()
    data.update(
        {
            "author": candidate.author_name,
            "vertical_score": vertical_score(width, height),
            "quality_score": 0.7 if source.exists() else 0.2,
            "rights_score": (
                1.0
                if candidate.license.allowed_for_render
                and not candidate.license.review_required
                else 0.0
            ),
        }
    )
    return data


def rank_user_assets(
    assets: list[dict[str, Any]],
    scene: dict[str, Any],
    preferred: set[str],
    used_asset_ids: set[str],
) -> list[dict[str, Any]]:
    ranked = []
    for asset in assets:
        score = 100.0
        if asset["asset_id"] in preferred:
            score += 20
        if asset["asset_id"] in used_asset_ids:
            score -= 30
        ranked.append(
            {
                **asset,
                "total_score": score,
                "selected_by": "user_asset_priority",
            }
        )
    return ranked


def _current_local_checksum(asset: dict[str, Any]) -> str:
    local_path = str(asset.get("local_path") or "")
    if not local_path:
        return ""
    try:
        return sha256_file(project_path(local_path))
    except OSError:
        # Keep tolerant local records readable without granting stale evidence authority.
        return ""


def rank_local_assets(
    media_index: dict[str, Any],
    scene: dict[str, Any],
    channel: str,
    used_asset_ids: set[str],
) -> list[dict[str, Any]]:
    requested_type = (
        "image"
        if scene.get("visual_type") in {"image", "animated_image"}
        else "video"
    )
    matches = search_local_assets(
        media_index,
        {
            "visual_keywords": scene.get("primary_query", "").split(),
            "scene_type": scene.get("visual_type", ""),
            "duration": scene.get("target_duration_sec", 0),
        },
        media_type=requested_type,
        channel=channel,
        min_score=1,
        limit=10,
    )
    ranked = []
    for match in matches:
        asset = match["asset"]
        rights_status = asset.get("rights_status") or RIGHTS_REFERENCE_ONLY
        allowed = rights_status in RIGHTS_ALLOWED_STATUSES
        asset_id = asset.get("id") or stable_asset_id(asset)
        if asset_id in used_asset_ids:
            continue
        current_checksum = _current_local_checksum(asset)
        duplicate_penalty = 25 if asset_id in used_asset_ids else 0
        width = int(asset.get("width") or 0)
        height = int(asset.get("height") or 0)
        item = {
            "schema_version": int(asset.get("schema_version") or 0),
            "asset_id": asset_id,
            "provider_asset_id": asset.get("provider_asset_id") or asset_id,
            "path": asset.get("local_path", ""),
            "local_path": asset.get("local_path", ""),
            "provider": "local_library",
            "type": asset.get("type", requested_type),
            "media_type": asset.get("type", requested_type),
            "title": asset.get("title", ""),
            "description": asset.get(
                "description",
                asset.get("caption", ""),
            ),
            "keywords": asset.get("keywords", []),
            "tags": asset.get("tags", []),
            "vision_tags": asset.get("vision_tags", []),
            "source_url": asset.get("source_url", ""),
            "source_page": asset.get(
                "source_page",
                asset.get("source_url", ""),
            ),
            "source_page_url": asset.get("source_page_url")
            or asset.get("source_page")
            or asset.get("source_url", ""),
            "author": asset.get("author", ""),
            "license": asset.get("license", asset.get("license_note", "")),
            "provenance": asset.get("provenance", {}),
            "checksum_sha256": current_checksum,
            "technical_validation": asset.get("technical_validation", {}),
            "rights_status": rights_status,
            "allowed_for_render": allowed,
            # The record's own review flag travels with it. Dropping it here used to
            # hand the policy a candidate that no longer said anything about review.
            "review_required": bool(asset.get("review_required", False)),
            "width": width,
            "height": height,
            "duration": float(asset.get("duration") or 0),
            "duration_sec": float(
                asset.get("duration_sec") or asset.get("duration") or 0
            ),
            "relevance_score": float(match.get("score", 0)),
            "quality_score": quality_score(width, height),
            "vertical_score": vertical_score(width, height),
            "rights_score": 1.0 if allowed else 0.0,
            "duplicate_penalty": duplicate_penalty,
            "watermark_penalty": 0,
            "total_score": (
                float(match.get("score", 0))
                + quality_score(width, height)
                + vertical_score(width, height)
                - duplicate_penalty
            ),
            "selected_by": "local_library",
        }
        carry_vision_evidence(asset, item)
        ranked.append(with_policy_decision(item))
    return ranked


def query_not_allowed_for_scene(
    semantic_scene: Any,
    query: dict[str, str | int],
) -> bool:
    level = int(query.get("fallback_level") or 1)
    if semantic_scene.visual_priority in {"transition", "environment"}:
        return False
    return level >= 4


def missing_reason(
    dry_run: bool,
    candidates: list[dict[str, Any]],
    download_attempts: list[dict[str, Any]] | None = None,
) -> str:
    if dry_run:
        return "dry_run_does_not_download_assets"
    for attempt in download_attempts or []:
        if (
            attempt.get("download_status") == "blocked"
            and attempt.get("reason")
        ):
            return str(attempt["reason"])
    if download_attempts:
        return "download_or_validation_failed"
    if not candidates:
        return "no_allowed_asset_found"
    return "no_semantic_asset_above_threshold"


def media_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in IMAGE_EXTENSIONS:
        return "image"
    if suffix in VIDEO_EXTENSIONS:
        return "video"
    return "unknown"


def warnings(
    dry_run: bool,
    provider_errors: list[dict[str, str]],
    missing_scenes: list[dict[str, Any]],
) -> list[str]:
    values: list[str] = []
    if dry_run:
        values.append("Dry run skipped downloads and paid providers.")
    if provider_errors:
        values.append(f"{len(provider_errors)} provider error(s) were recorded.")
    if missing_scenes:
        values.append(f"{len(missing_scenes)} scene(s) still need allowed assets.")
    return values


def generated_fallback_asset(scene: dict[str, Any]) -> dict[str, Any]:
    return {
        "asset_id": f"generated_{scene.get('scene_id', 'scene')}",
        "path": "",
        "provider": "generated_layout",
        "type": scene.get("fallback_type") or "text_card",
        "source_url": "",
        "source_page": "",
        "author": "AI-YouTube",
        "license": "project_generated",
        "rights_status": "licensed",
        "allowed_for_render": True,
        "width": 1080,
        "height": 1920,
        "duration": float(scene.get("target_duration_sec") or 0),
        "relevance_score": 2.0,
        "quality_score": 5.0,
        "vertical_score": 10.0,
        "rights_score": 1.0,
        "duplicate_penalty": 0,
        "watermark_penalty": 0,
        "total_score": 8.0,
        "selected_by": "generated_fallback",
    }
