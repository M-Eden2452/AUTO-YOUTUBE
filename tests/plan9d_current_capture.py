"""PLAN-9D-B: capture the candidate pools the *current* retrieval path returns.

Hand-run, evaluation-only, and deliberately not a test: it is the one place in
PLAN-9D that is allowed to touch the network, and only under an owner approval
issued for a single bounded run.

Why it exists
-------------
PLAN-9D-A curated the proof that the pre-9B/9C retrieval defects were real, and
retired that data as a quality benchmark: every runtime project on disk predates
the query work of PLAN-9B-1..9B-3 and PLAN-9C, so a pool harvested from those
projects says what the *retired* queries returned. A statement about the decision
owner needs pools that today's retrieval actually produces. This module produces
them once, freezes them behind a digest, and hands the frozen file to the offline
harness in ``tests.plan9d_ground_truth``.

What "the current production path" means here, exactly
------------------------------------------------------
Nothing is re-implemented. The capture drives the production owners in the
production order, through ``AssetManifestBuilder``:

    evaluation script (scene requirement, author visual brief)
      -> src.news.visual_plan.build_visual_plan       (canonical planning entry)
         -> src.content.visual_planning.build_plan    (planner + brief overlay)
            -> legacy_format.scene_to_legacy          (visual_brief, semantic, intents)
      -> AssetManifestBuilder._prepare_scene
         -> semantic_selection.analyze_scene          (semantic_scene)
         -> assets.provider_routing.route_providers   (source class, provider order)
         -> assets.query_adapter.build_scene_queries  (provider-ready queries)
      -> AssetManifestBuilder._search_scene_providers (real provider search)
         -> news.asset_provider_adapters.search_provider / rank_provider_results
            -> assets.license_policy.apply_policy_to_candidate   (rights)
      -> AssetManifestBuilder._select_scene_asset     (the single decision owner)
      -> AssetManifestBuilder._prepare_visual_review  (previews + sampled frames)

and stops there. ``_download_and_complete`` and everything after it is *not*
called: the frame evidence PLAN-9D needs comes from the bounded preview cache,
so the capture never needs the ``asset_download`` network class. That omission is
recorded in the corpus rather than left to be inferred.

What it must not do
-------------------
No retrieval tuning of any kind. Not one query is written by hand, not one
provider is added or removed, no pagination, no threshold, no ranking change, and
no second run "to get a better pool". A query the planner did not produce would
make the corpus a statement about this file instead of about the system. Vision,
paid model calls, TTS, render and Envato are out of scope entirely; the semantic
backend stays at its shipped default (``enabled: false``), so no Vision evidence
can reach the ranker during a capture.

Evaluation constants, stated rather than hidden
-----------------------------------------------
``user_assets`` is empty and the media index is empty
    The corpus measures *provider retrieval*. The local media library is a
    different source, and it is populated from the very historical projects
    PLAN-9D-A retired as benchmark input; letting it seed the pools would put
    historical material back in as if it were a current provider result.

``used_asset_ids`` is empty
    Every scene is captured on its own, exactly as the offline harness measures
    it. Cross-scene reuse state belongs to a production run, not to a benchmark.

Frames are provider previews, not the assets themselves
    The preview path is capped by ``config/visual_preview.json``
    (``maximum_preview_size_mb``), so what lands on disk is a small rendition and
    the frames sampled from it. Declared provider width/height are carried
    verbatim in the candidate record and are the dimensions the framing gate
    reads.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from src.assets.http_client import ProviderHttpClient
from src.assets.query_adapter import provider_query_languages
from src.news.asset_manifest_builder import AssetManifestBuilder, query_not_allowed_for_scene
from src.news.visual_plan import build_visual_plan
from src.providers import create_default_stock_providers
from src.runtime_network import (
    NETWORK_ACTION_PREVIEW_DOWNLOAD,
    NETWORK_ACTION_PROVIDER_SEARCH,
    approval_for_actions,
    network_approval_scope,
)

# The rules for reducing a stored candidate to what a provider (plus the licence
# policy) supplied, and for tagging a scene with the technical categories the
# benchmark vocabulary defines, are owned by the offline builder; importing them
# keeps one owner rather than a second, silently diverging copy.
from .plan9d_corpus_builder import categorize, _strip_ranker_output
from .plan9d_ground_truth import (
    CORPUS_SCHEMA_VERSION,
    CURRENT_CORPUS_PATH,
    FIXTURE_KIND_CURRENT_BENCHMARK,
    GENERATION_CURRENT,
    LEGACY_BROAD_QUERY_LITERALS,
    assign_blind_ids,
    corpus_digest,
    secret_like_findings,
    validate_corpus,
    validate_current_capture,
)


REPO_ROOT = Path(__file__).resolve().parents[1]

#: The capture's own runtime namespace. Deterministic and marked, so it can never
#: be mistaken for a user project or for one of the historical projects PLAN-9D-A
#: curated. ``projects/`` is ignored by Git in full, so nothing here is committed.
CAPTURE_PROJECT_ID = "plan9d_current_capture_v1"
CAPTURE_WORKSPACE = f"projects/{CAPTURE_PROJECT_ID}"

CORPUS_VERSION = "plan9d-b-2026-08-08"
EVALUATION_SET_VERSION = "plan9d-b-eval-2026-08-08"
PLAN_STEP = "PLAN-9D-B"

#: The classes the owner approved for this one capture. ``asset_download`` is
#: deliberately absent: the preview path supplies the frame evidence, so a full
#: asset download is never requested and would be refused fail-closed if it were.
CAPTURE_NETWORK_ACTIONS = (NETWORK_ACTION_PROVIDER_SEARCH, NETWORK_ACTION_PREVIEW_DOWNLOAD)

#: Production stages this capture runs, in order, and the ones it stops before.
#: Recorded in the corpus so a reader does not have to reconstruct it from here.
PRODUCTION_STAGES = (
    "src.news.visual_plan.build_visual_plan",
    "AssetManifestBuilder._prepare_scene",
    "AssetManifestBuilder._search_scene_providers",
    "AssetManifestBuilder._add_generated_infographic",
    "AssetManifestBuilder._select_scene_asset",
    "AssetManifestBuilder._prepare_visual_review",
)
STAGES_NOT_RUN = (
    "AssetManifestBuilder._download_and_complete",
    "AssetManifestBuilder._apply_fallbacks",
    "AssetManifestBuilder._record_scene",
    "AssetManifestBuilder._write_reviews",
)

CHANNEL = "nature_science_news_ru"

TRIPWIRE_NO_BRIEF = "scene_without_visual_brief"
TRIPWIRE_EMPTY_SEMANTIC_SUBJECT = "empty_semantic_subject"
TRIPWIRE_SUBJECT_LOST = "subject_absent_from_provider_query"
TRIPWIRE_RETIRED_LITERAL = "retired_broad_query_literal"
TRIPWIRE_LANGUAGE_CONTRACT = "query_violates_provider_language_contract"
TRIPWIRE_NO_PROVIDER_QUERY = "no_provider_ready_query"


class CaptureError(RuntimeError):
    """The capture cannot proceed honestly as it stands."""


# --------------------------------------------------------------------------- #
# The evaluation scene set
# --------------------------------------------------------------------------- #

#: Fourteen independent scenes, chosen for product/failure-mode coverage rather
#: than for statistical power. Each one is what the product actually consumes: a
#: narration line in the script's own language plus the author's explicit
#: ``visual_brief`` - the canonical, documented way a scene states what to show
#: (``src/content/visual_planning/brief.py``). No brief declares
#: ``provider_queries``: that field bypasses query building, and the whole point
#: of this capture is to measure the query planner, not to hand it an answer.
#: ``source_class`` is likewise never declared, so provider routing classifies
#: each scene the way it would in production.
COVERAGE_SIMPLE_SUBJECT = "simple_subject"
COVERAGE_SUBJECT_ACTION = "subject_action"
COVERAGE_ENVIRONMENT = "environment_constraint"
COVERAGE_CAPTIVE = "wild_vs_captive_risk"
COVERAGE_MUST_INCLUDE = "must_include_declared"
COVERAGE_MUST_AVOID = "must_avoid_declared"
COVERAGE_SIMILAR_SPECIES = "visually_similar_wrong_subject_risk"
COVERAGE_CONTEXT_CONFLICT = "declared_conflicting_context"
COVERAGE_CROP = "crop_framing_concern"
COVERAGE_HARD_STOCK = "acceptable_stock_may_be_hard"
COVERAGE_NON_WILDLIFE = "non_wildlife_subject"
COVERAGE_EXACT_ENTITY = "exact_entity_declared"


@dataclass(frozen=True)
class EvaluationScene:
    """One scene requirement, in the shape the script stage actually writes."""

    scene_id: str
    case_id: str
    coverage: tuple[str, ...]
    narration: str
    target_duration_sec: float
    visual_brief: dict[str, Any]

    def script_scene(self, index: int) -> dict[str, Any]:
        return {
            "scene_id": self.scene_id,
            "narration": self.narration,
            "target_duration_sec": self.target_duration_sec,
            "role": "hook" if index == 1 else "development",
            "visual_brief": dict(self.visual_brief),
        }


EVALUATION_SCENES: tuple[EvaluationScene, ...] = (
    EvaluationScene(
        scene_id="scene_001",
        case_id="gecko_on_smooth_glass",
        coverage=(COVERAGE_SIMPLE_SUBJECT, COVERAGE_SUBJECT_ACTION),
        narration=(
            "Геккон держится на идеально гладком стекле и не падает: его лапы покрыты "
            "миллионами микроскопических щетинок."
        ),
        target_duration_sec=4.0,
        visual_brief={
            "subject": "gecko",
            "action": "clinging to smooth glass",
            "shot_type": "detail",
        },
    ),
    EvaluationScene(
        scene_id="scene_002",
        case_id="hummingbird_hovering",
        coverage=(COVERAGE_SIMPLE_SUBJECT, COVERAGE_SUBJECT_ACTION),
        narration=(
            "Колибри — единственная птица, которая умеет зависать на месте и лететь назад: "
            "её крылья описывают восьмёрку до восьмидесяти раз в секунду."
        ),
        target_duration_sec=4.5,
        visual_brief={
            "subject": "hummingbird",
            "action": "hovering in flight",
            "shot_type": "action",
        },
    ),
    EvaluationScene(
        scene_id="scene_003",
        case_id="penguin_tobogganing_on_snow",
        coverage=(COVERAGE_SIMPLE_SUBJECT, COVERAGE_SUBJECT_ACTION, COVERAGE_ENVIRONMENT),
        narration=(
            "Пингвины ложатся на живот и скользят по снегу: так они тратят меньше сил, "
            "чем при ходьбе вразвалку."
        ),
        target_duration_sec=4.0,
        visual_brief={
            "subject": "penguin",
            "action": "sliding on snow",
            "place": "Antarctica",
            "shot_type": "action",
        },
    ),
    EvaluationScene(
        scene_id="scene_004",
        case_id="orca_in_open_ocean",
        coverage=(COVERAGE_SIMPLE_SUBJECT, COVERAGE_EXACT_ENTITY, COVERAGE_ENVIRONMENT),
        narration=(
            "Косатка — самый крупный представитель дельфиновых: в открытом океане её спинной "
            "плавник поднимается почти на два метра."
        ),
        target_duration_sec=5.0,
        visual_brief={
            "subject": "orca",
            "action": "swimming at the surface",
            "place": "open ocean",
            "exact_entities": ["killer whale", "Orcinus orca"],
            "shot_type": "establishing",
        },
    ),
    EvaluationScene(
        scene_id="scene_005",
        case_id="cheetah_not_leopard",
        coverage=(COVERAGE_SIMILAR_SPECIES, COVERAGE_MUST_AVOID, COVERAGE_SUBJECT_ACTION),
        narration=(
            "Гепарда постоянно путают с леопардом, хотя это разные звери: гепард разгоняется "
            "до ста километров в час за три секунды."
        ),
        target_duration_sec=4.5,
        visual_brief={
            "subject": "cheetah",
            "action": "running at full speed",
            "place": "savanna",
            "must_avoid": ["leopard", "jaguar", "serval"],
            "shot_type": "action",
        },
    ),
    EvaluationScene(
        scene_id="scene_006",
        case_id="tiger_wild_not_captive",
        coverage=(COVERAGE_CAPTIVE, COVERAGE_MUST_AVOID, COVERAGE_ENVIRONMENT),
        narration=(
            "В дикой природе тигр проходит за ночь десятки километров по своему участку — "
            "это поведение невозможно увидеть в вольере."
        ),
        target_duration_sec=5.0,
        visual_brief={
            "subject": "wild tiger",
            "action": "walking through forest",
            "place": "forest",
            "must_avoid": ["zoo", "enclosure", "cage", "captivity"],
            "shot_type": "establishing",
        },
    ),
    EvaluationScene(
        scene_id="scene_007",
        case_id="pangolin_rare_subject",
        coverage=(COVERAGE_HARD_STOCK, COVERAGE_SIMPLE_SUBJECT),
        narration=(
            "Панголин — единственное млекопитающее, покрытое чешуёй из кератина, и самое "
            "контрабандное животное планеты."
        ),
        target_duration_sec=4.5,
        visual_brief={
            "subject": "pangolin",
            "action": "walking",
            "exact_entities": ["scaly anteater"],
            "shot_type": "detail",
        },
    ),
    EvaluationScene(
        scene_id="scene_008",
        case_id="arctic_fox_winter_coat",
        coverage=(COVERAGE_MUST_INCLUDE, COVERAGE_ENVIRONMENT),
        narration=(
            "К зиме песец полностью меняет окрас: летняя бурая шерсть уступает место белой, "
            "и зверь исчезает на фоне снега."
        ),
        target_duration_sec=4.5,
        visual_brief={
            "subject": "arctic fox",
            "action": "standing in snow",
            "place": "tundra",
            "must_include": ["white winter coat"],
            "shot_type": "establishing",
        },
    ),
    EvaluationScene(
        scene_id="scene_009",
        case_id="solar_farm_aerial",
        coverage=(COVERAGE_NON_WILDLIFE, COVERAGE_MUST_INCLUDE, COVERAGE_CROP),
        narration=(
            "Солнечная электростанция в пустыне занимает площадь небольшого города, и её "
            "панели поворачиваются вслед за солнцем."
        ),
        target_duration_sec=5.0,
        visual_brief={
            "subject": "solar power plant",
            "action": "aerial view of panel rows",
            "place": "desert",
            "must_include": ["solar panels"],
            "shot_type": "establishing",
        },
    ),
    EvaluationScene(
        scene_id="scene_010",
        case_id="laboratory_pipetting_detail",
        coverage=(COVERAGE_NON_WILDLIFE, COVERAGE_SUBJECT_ACTION),
        narration=(
            "Пробу делят на десятки микролитровых порций: одна ошибка пипетирования — и весь "
            "эксперимент придётся повторять."
        ),
        target_duration_sec=4.0,
        visual_brief={
            "subject": "laboratory pipette",
            "action": "dispensing a sample into a microplate",
            "place": "laboratory",
            "shot_type": "detail",
        },
    ),
    EvaluationScene(
        scene_id="scene_011",
        case_id="iss_orbit_declared_conflict",
        coverage=(COVERAGE_NON_WILDLIFE, COVERAGE_CONTEXT_CONFLICT, COVERAGE_EXACT_ENTITY),
        narration=(
            "Международная космическая станция обходит Землю за девяносто минут — экипаж "
            "видит шестнадцать рассветов в сутки."
        ),
        target_duration_sec=5.0,
        visual_brief={
            "subject": "International Space Station",
            "action": "orbiting Earth",
            "place": "low Earth orbit",
            "exact_entities": ["International Space Station"],
            "conflicting_context": ["mars mission", "concept art", "artist impression"],
            "shot_type": "establishing",
        },
    ),
    EvaluationScene(
        scene_id="scene_012",
        case_id="suspension_bridge_vertical_crop",
        coverage=(COVERAGE_NON_WILDLIFE, COVERAGE_CROP, COVERAGE_ENVIRONMENT),
        narration=(
            "Пролёт висячего моста растянут больше чем на километр, и вся конструкция держится "
            "на двух основных тросах."
        ),
        target_duration_sec=4.5,
        visual_brief={
            "subject": "suspension bridge",
            "action": "spanning a wide bay",
            "place": "bay",
            "shot_type": "establishing",
        },
    ),
    EvaluationScene(
        scene_id="scene_013",
        case_id="saturn_v_archive_launch",
        coverage=(COVERAGE_NON_WILDLIFE, COVERAGE_EXACT_ENTITY, COVERAGE_SUBJECT_ACTION),
        narration=(
            "Ракета «Сатурн-5» сжигала пятнадцать тонн топлива в секунду — до сих пор это самый "
            "мощный носитель, доставивший людей к Луне."
        ),
        target_duration_sec=5.0,
        visual_brief={
            "subject": "Saturn V rocket",
            "action": "lifting off from the launch pad",
            "exact_entities": ["Apollo 11", "Saturn V"],
            "shot_type": "action",
        },
    ),
    EvaluationScene(
        scene_id="scene_014",
        case_id="brown_bear_catching_salmon",
        coverage=(COVERAGE_MUST_INCLUDE, COVERAGE_SUBJECT_ACTION, COVERAGE_ENVIRONMENT),
        narration=(
            "На нерестовом пороге бурый медведь ловит лосося прямо в прыжке: за день он "
            "съедает до тридцати рыбин."
        ),
        target_duration_sec=5.0,
        visual_brief={
            "subject": "brown bear",
            "action": "catching a salmon at a waterfall",
            "place": "river waterfall",
            "must_include": ["salmon"],
            "shot_type": "action",
        },
    ),
)


def build_script() -> dict[str, Any]:
    """The evaluation script, in the legacy ``script.json`` shape the pipeline reads."""

    return {
        "title": "PLAN-9D-B current retrieval capture",
        "language": "ru",
        "source_kind": "user_script",
        "scenes": [
            scene.script_scene(index)
            for index, scene in enumerate(EVALUATION_SCENES, start=1)
        ],
    }


def build_plan() -> dict[str, Any]:
    """The visual plan, through the canonical production entry point."""

    return build_visual_plan(build_script(), language="ru", user_assets=[])


# --------------------------------------------------------------------------- #
# Offline planning lineage and the pre-network tripwires
# --------------------------------------------------------------------------- #


def create_builder(*, providers: list[Any], project_root: Path | None, dry_run: bool) -> AssetManifestBuilder:
    """The production orchestrator, configured the way ``news_to_short`` configures it.

    Only the evaluation constants differ, and each is stated in the module
    docstring: no user assets, an empty media index, no generated fallbacks.
    """

    return AssetManifestBuilder(
        visual_plan=build_plan(),
        user_assets=[],
        media_index={"version": 1, "items": []},
        providers=providers,
        dry_run=dry_run,
        channel=CHANNEL,
        allow_generated_fallback=False,
        asset_selection=None,
        project_root=project_root,
        project_id=CAPTURE_PROJECT_ID,
        max_download_attempts=3,
        completion_mode="",
        reuse_ledger=None,
        allow_infographic_fallback=False,
        allow_emergency_backdrop=False,
        prefer_video=True,
        minimum_video_clips=0,
        minimum_video_duration_ratio=0.0,
    )


def plan_lineage(builder: AssetManifestBuilder) -> list[dict[str, Any]]:
    """Everything the planning half of the path produced, before any request.

    ``_prepare_scene`` is the production stage that owns this: it analyses the
    scene, routes the providers and builds the provider-ready queries. Calling it
    opens no socket, which is why the tripwires below can run before the capture
    is allowed to start.
    """

    lineage: list[dict[str, Any]] = []
    by_case = {scene.scene_id: scene for scene in EVALUATION_SCENES}
    for raw_scene in builder.visual_plan.get("scenes") or []:
        state = builder._prepare_scene(raw_scene)
        scene_id = str(raw_scene.get("scene_id") or "")
        spec = by_case.get(scene_id)
        plan_queries = [item.to_dict() for item in state.query_plan.queries]
        executable = _executable_queries(state)
        lineage.append(
            {
                "scene_id": scene_id,
                "case_id": spec.case_id if spec else "",
                "coverage": list(spec.coverage) if spec else [],
                "scene_text": str(raw_scene.get("narration") or ""),
                "declared_brief": dict(spec.visual_brief) if spec else {},
                "visual_brief": dict(raw_scene.get("visual_brief") or {}),
                "visual_intents": list(raw_scene.get("visual_intents") or []),
                "primary_query": str(raw_scene.get("primary_query") or ""),
                "alternative_queries": list(raw_scene.get("alternative_queries") or []),
                "semantic_scene": state.semantic_scene.to_dict(),
                "routing": _routing_record(state.routing_decision),
                "query_plan": {
                    "intent_language": state.query_plan.intent_language,
                    "queries": plan_queries,
                    "untranslatable_providers": list(state.query_plan.untranslatable_providers),
                },
                "executable_queries": executable,
                "planned_provider_search_calls": _planned_search_calls(raw_scene, state, executable),
                "scene": raw_scene,
                "state": state,
            }
        )
    return lineage


def _routing_record(decision: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_class": str(decision.get("source_class") or ""),
        "classification_reason": str(decision.get("classification_reason") or ""),
        "classified_from": str(decision.get("classified_from") or ""),
        "ordered_providers": list(decision.get("ordered_providers") or []),
        "skipped_providers": dict(decision.get("skipped_providers") or {}),
        "requires_provider_metadata": bool(decision.get("requires_provider_metadata")),
        "allows_generic_stock": bool(decision.get("allows_generic_stock")),
        "media_type": str(decision.get("media_type") or ""),
    }


def _executable_queries(state: Any) -> list[dict[str, Any]]:
    """The queries that would actually be sent, after the production level filter.

    ``query_not_allowed_for_scene`` is production's own cap on how deep the ladder
    may go for a scene of this priority. Applying it here - rather than counting
    the whole plan - is what makes the pre-network request bound honest.
    """

    executable: list[dict[str, Any]] = []
    for provider_name in state.routing_decision.get("ordered_providers") or []:
        for item in state.query_plan.for_provider(provider_name):
            record = {
                "kind": item.kind,
                "fallback_level": item.fallback_level,
                "query": item.query,
                "language": item.language,
                "query_source": item.source,
            }
            if query_not_allowed_for_scene(state.semantic_scene, record):
                continue
            executable.append({"provider": provider_name, **record})
    return executable


def _planned_search_calls(
    scene: dict[str, Any], state: Any, executable: list[dict[str, Any]]
) -> int:
    """Upper bound on ``provider.search`` calls for this scene.

    ``search_provider`` asks a second media type when the scene prefers video and
    also allows images and the provider supports them, so the bound is one or two
    calls per executable query and per provider.
    """

    preferred = str(scene.get("visual_type") or "video")
    allowed = {str(item) for item in (scene.get("allowed_media_kinds") or [])}
    total = 0
    for item in executable:
        capabilities = state.provider_capabilities.get(item["provider"], {})
        supported = {str(value) for value in (capabilities.get("media_types") or [])}
        total += 2 if (preferred == "video" and "image" in allowed and "image" in supported) else 1
    return total


def check_tripwires(lineage: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Refuse to spend a provider request on a scene the planner already broke.

    Each check is a property PLAN-9D-B needs in order for the capture to mean
    anything: a corpus retrieved by a query that lost the subject, or by the very
    literal PLAN-9B-3 retired, would repeat the mistake PLAN-9D-A exists to
    document. A violation stops the run; it is never worked around by writing the
    query by hand, which would measure this file instead of the system.
    """

    violations: list[dict[str, Any]] = []
    for entry in lineage:
        scene_id = entry["scene_id"]
        declared = entry["declared_brief"]

        if not entry["visual_brief"]:
            violations.append(
                {
                    "tripwire": TRIPWIRE_NO_BRIEF,
                    "scene_id": scene_id,
                    "detail": "the scene declares an author visual brief and the plan carries none",
                }
            )
        semantic = entry["semantic_scene"]
        if not [item for item in (semantic.get("subject") or []) if str(item).strip()]:
            violations.append(
                {
                    "tripwire": TRIPWIRE_EMPTY_SEMANTIC_SUBJECT,
                    "scene_id": scene_id,
                    "detail": "semantic_scene.subject is empty for a scene that states a subject",
                }
            )

        executable = entry["executable_queries"]
        if not executable:
            violations.append(
                {
                    "tripwire": TRIPWIRE_NO_PROVIDER_QUERY,
                    "scene_id": scene_id,
                    "detail": "no provider-ready query survived the production query ladder",
                }
            )

        subject_tokens = _subject_tokens(declared)
        by_provider: dict[str, list[str]] = {}
        for item in executable:
            by_provider.setdefault(item["provider"], []).append(item["query"])
        for provider_name, queries in by_provider.items():
            if subject_tokens and not any(
                _carries_subject(query, subject_tokens) for query in queries
            ):
                violations.append(
                    {
                        "tripwire": TRIPWIRE_SUBJECT_LOST,
                        "scene_id": scene_id,
                        "provider": provider_name,
                        "detail": f"no query for this provider names {sorted(subject_tokens)}",
                        "queries": list(queries),
                    }
                )
            languages = provider_query_languages(provider_name)
            for query in queries:
                if _query_language(query) not in languages:
                    violations.append(
                        {
                            "tripwire": TRIPWIRE_LANGUAGE_CONTRACT,
                            "scene_id": scene_id,
                            "provider": provider_name,
                            "detail": f"query language not searchable by this provider: {query!r}",
                        }
                    )
                if _normalized(query) in LEGACY_BROAD_QUERY_LITERALS:
                    violations.append(
                        {
                            "tripwire": TRIPWIRE_RETIRED_LITERAL,
                            "scene_id": scene_id,
                            "provider": provider_name,
                            "detail": f"retired broad literal reached a provider-facing query: {query!r}",
                        }
                    )
    return violations


_CYRILLIC_RE = re.compile(r"[Ѐ-ӿ]")
_LATIN_RE = re.compile(r"[A-Za-z]")
_WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)


def _normalized(value: str) -> str:
    return " ".join(str(value or "").casefold().split())


def _query_language(query: str) -> str:
    if _CYRILLIC_RE.search(query):
        return "ru"
    return "en" if _LATIN_RE.search(query) else ""


def _subject_tokens(brief: dict[str, Any]) -> set[str]:
    """The words a query for this scene must not lose.

    Read from what the scene *declared*, never from what the planner produced: a
    check fed by the planner's own output cannot catch the planner dropping the
    subject. Multi-word subjects are reduced to their head noun, because the
    ladder legitimately widens "wild tiger" to "tiger".
    """

    subject = str(brief.get("subject") or "").strip()
    if not subject:
        return set()
    words = [word.casefold() for word in _WORD_RE.findall(subject)]
    return {words[-1]} if words else set()


def _carries_subject(query: str, subject_tokens: set[str]) -> bool:
    tokens = {word.casefold() for word in _WORD_RE.findall(query)}
    return bool(tokens & subject_tokens)


# --------------------------------------------------------------------------- #
# Provider availability
# --------------------------------------------------------------------------- #

#: Providers that only exist when a key is configured. Read from the registry's
#: own behaviour, not restated as policy: the registry refuses to create them
#: without a key rather than creating one that silently returns nothing.
KEYED_PROVIDERS = ("pexels", "pixabay")

#: Every provider the canonical registry can put in the automatic set.
CANONICAL_FREE_PROVIDERS = ("wikimedia", "nasa_images", "internet_archive", "pexels", "pixabay")


def provider_matrix(providers: list[Any]) -> list[dict[str, Any]]:
    """Configured / enabled / eligible per provider. Never a key, never a token."""

    created = {provider.name: provider for provider in providers}
    rows: list[dict[str, Any]] = []
    for name in CANONICAL_FREE_PROVIDERS:
        provider = created.get(name)
        capabilities = provider.capabilities().to_dict() if provider is not None else {}
        rows.append(
            {
                "provider": name,
                "configured": provider is not None,
                "enabled": provider is not None,
                "routing_eligible": provider is not None,
                "requires_credential": name in KEYED_PROVIDERS,
                "paid_operation": bool(capabilities.get("paid", False)),
                "media_types": [str(item) for item in (capabilities.get("media_types") or [])],
                "query_languages": list(provider_query_languages(name, capabilities)),
            }
        )
    return rows


# --------------------------------------------------------------------------- #
# The capture
# --------------------------------------------------------------------------- #


@dataclass
class RequestCounter:
    """Observation only: counts HTTP calls without changing one of them.

    Wraps the two ``ProviderHttpClient`` entry points for the duration of a
    capture and delegates verbatim. It exists so the report can state request
    counts as measured facts rather than as an estimate from the query ladder.
    """

    get_json: int = 0
    download_stream: int = 0
    hosts: dict[str, int] = field(default_factory=dict)

    def note(self, url: str) -> None:
        host = str(url or "").split("//", 1)[-1].split("/", 1)[0]
        self.hosts[host] = self.hosts.get(host, 0) + 1


class _CountingClient:
    """Context manager installing the counter on the production HTTP client."""

    def __init__(self, counter: RequestCounter) -> None:
        self.counter = counter
        self._get_json = ProviderHttpClient.get_json
        self._download = ProviderHttpClient.download_stream

    def __enter__(self) -> RequestCounter:
        counter, original_get, original_download = self.counter, self._get_json, self._download

        def get_json(client, url, *args, **kwargs):
            counter.get_json += 1
            counter.note(url)
            return original_get(client, url, *args, **kwargs)

        def download_stream(client, url, *args, **kwargs):
            counter.download_stream += 1
            counter.note(url)
            return original_download(client, url, *args, **kwargs)

        ProviderHttpClient.get_json = get_json  # type: ignore[method-assign]
        ProviderHttpClient.download_stream = download_stream  # type: ignore[method-assign]
        return counter

    def __exit__(self, *exc: Any) -> None:
        ProviderHttpClient.get_json = self._get_json  # type: ignore[method-assign]
        ProviderHttpClient.download_stream = self._download  # type: ignore[method-assign]


def assert_socket_guard_released() -> None:
    """Refuse to "capture" through the guard that stops ordinary tests reaching out.

    This module lives in ``tests/``, and importing that package installs the
    socket guard (``tests/__init__.py``). A capture run under the guard does not
    fail loudly: every provider raises, every attempt is recorded as an error and
    the result is a corpus-shaped file describing an outage that never happened.
    So the guard is detected rather than removed - it stays the single owner of
    the rule - and releasing it for one approved live run is left to the operator,
    through the switch the guard itself already defines.
    """

    from . import network_guard

    if getattr(network_guard, "_installed", False):
        raise CaptureError(
            "the test socket guard is installed, so no provider could be reached and the "
            "capture would record a fake outage. This run is an owner-approved live capture: "
            "set "
            + "=1 ".join(network_guard.ALLOW_LIVE_ENV_VARS[:1])
            + "=1 for this invocation only."
        )


def capture_corpus(*, granted_by: str) -> dict[str, Any]:
    """Run the current retrieval path over the evaluation set, once, and freeze it."""

    assert_socket_guard_released()
    project_root = REPO_ROOT / CAPTURE_WORKSPACE
    project_root.mkdir(parents=True, exist_ok=True)
    providers = create_default_stock_providers(load_environment=_load_environment)
    builder = create_builder(providers=providers, project_root=project_root, dry_run=False)

    lineage = plan_lineage(builder)
    violations = check_tripwires(lineage)
    if violations:
        raise CaptureError(
            "pre-network tripwires failed; no provider request was sent:\n"
            + json.dumps(violations, ensure_ascii=False, indent=1)
        )

    approval = approval_for_actions(CAPTURE_NETWORK_ACTIONS, granted_by=granted_by)
    counter = RequestCounter()
    captured: list[dict[str, Any]] = []
    with network_approval_scope(approval), _CountingClient(counter):
        for entry in lineage:
            state = entry["state"]
            builder._search_scene_providers(state)
            builder._add_generated_infographic(state)
            builder._select_scene_asset(state)
            builder._prepare_visual_review(state)
            captured.append(_scene_record(entry, state))

    return _freeze(captured, lineage, providers, counter, granted_by)


def _load_environment() -> None:
    """The registry's environment hook, as production supplies it."""

    from dotenv import load_dotenv

    load_dotenv()


def _scene_record(entry: dict[str, Any], state: Any) -> dict[str, Any]:
    """One captured scene: the requirement, the plan, the pool and the evidence."""

    scene_key = f"{CAPTURE_PROJECT_ID}/{entry['scene_id']}"
    frames_by_asset, previews_by_asset = _preview_evidence(state)
    pool, repeats = _unique_pool(state.candidates)

    blind = assign_blind_ids(scene_key, [str(item.get("asset_id") or "") for item in pool])
    entries = [
        {
            "blind_id": blind[str(candidate.get("asset_id"))],
            "asset_id": str(candidate.get("asset_id")),
            "input_order": index,
            "provider": str(candidate.get("provider") or ""),
            "search_query": str(candidate.get("search_query") or ""),
            "fallback_level": int(candidate.get("fallback_level") or 0),
            "returned_by_queries": repeats[str(candidate.get("asset_id"))]["queries"],
            "returned_times": repeats[str(candidate.get("asset_id"))]["count"],
            # The three flags a reader needs at a glance. The policy decision that
            # produced them is not repeated here: it is already inside the stored
            # candidate record, where the rights owner wrote it, and duplicating it
            # cost more than a megabyte of the frozen file.
            "rights": {
                "rights_status": str(candidate.get("rights_status") or ""),
                "allowed_for_render": bool(candidate.get("allowed_for_render")),
                "review_required": bool(candidate.get("review_required")),
                "policy_decision_in_candidate": bool(candidate.get("policy_decision")),
            },
            "declared_dimensions": {
                "width": int(candidate.get("width") or 0),
                "height": int(candidate.get("height") or 0),
                "duration_sec": float(candidate.get("duration_sec") or 0.0),
            },
            "preview": previews_by_asset.get(str(candidate.get("asset_id")), {}),
            "frames": frames_by_asset.get(str(candidate.get("asset_id")), []),
            "candidate": _strip_ranker_output(candidate, drop_archival=True),
        }
        for index, candidate in enumerate(pool)
    ]
    entries.sort(key=lambda item: int(item["blind_id"][1:]))

    selected_id = str((state.selected or {}).get("asset_id") or "")
    scene = entry["scene"]
    return {
        "scene_key": scene_key,
        "project": CAPTURE_PROJECT_ID,
        "scene_id": entry["scene_id"],
        "case_id": entry["case_id"],
        "coverage": entry["coverage"],
        "scene_text": entry["scene_text"],
        "declared_brief": entry["declared_brief"],
        "visual_brief": entry["visual_brief"],
        "visual_intents": entry["visual_intents"],
        "primary_query": entry["primary_query"],
        "alternative_queries": entry["alternative_queries"],
        "semantic_scene": entry["semantic_scene"],
        "routing": entry["routing"],
        "query_plan": entry["query_plan"],
        "executable_queries": entry["executable_queries"],
        "provider_attempts": [_attempt_record(item) for item in state.scene_provider_attempts],
        "required_duration_sec": float(scene.get("target_duration_sec") or 0.0),
        "source_class": str(state.source_class or ""),
        "require_provider_metadata": bool(
            state.routing_decision.get("requires_provider_metadata")
        ),
        "prefer_video": True,
        "target_aspect_ratio": "9:16",
        "visual_type": str(scene.get("visual_type") or ""),
        "allowed_media_kinds": [str(item) for item in (scene.get("allowed_media_kinds") or [])],
        "selected_asset_id": selected_id,
        "selected_blind_id": blind.get(selected_id, "") if selected_id else "",
        "selected_by": str((state.selected or {}).get("selected_by") or ""),
        "selection_support_status": str((state.selected or {}).get("support_status") or ""),
        "categories": [],
        "candidates": entries,
    }


def _attempt_record(attempt: dict[str, Any]) -> dict[str, Any]:
    record = {
        "provider": str(attempt.get("provider") or ""),
        "query": str(attempt.get("query") or ""),
        "query_language": str(attempt.get("query_language") or ""),
        "query_source": str(attempt.get("query_source") or ""),
        "status": str(attempt.get("status") or ""),
        "result_count": int(attempt.get("result_count") or 0),
    }
    if attempt.get("reason"):
        record["reason"] = str(attempt["reason"])
    error = attempt.get("error")
    if isinstance(error, dict):
        record["error"] = {
            "code": str(error.get("code") or ""),
            "message": str(error.get("message") or ""),
        }
    return record


def _unique_pool(
    candidates: Iterable[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    """One entry per asset, and a count of how often retrieval returned it again.

    A provider really did return the same asset for two different queries of the
    same scene, and that repetition is captured rather than erased - but the
    corpus stores one record per asset, because a blind identifier has to name one
    thing. The first occurrence wins, so the pool keeps the manifest order the
    ranker's stable sort uses as its tie-break.
    """

    pool: list[dict[str, Any]] = []
    repeats: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        asset_id = str(candidate.get("asset_id") or "")
        if not asset_id:
            continue
        query = str(candidate.get("search_query") or "")
        if asset_id in repeats:
            repeats[asset_id]["count"] += 1
            if query and query not in repeats[asset_id]["queries"]:
                repeats[asset_id]["queries"].append(query)
            continue
        repeats[asset_id] = {"count": 1, "queries": [query] if query else []}
        pool.append(candidate)
    return pool, repeats


def _preview_evidence(state: Any) -> tuple[dict[str, list[dict[str, Any]]], dict[str, dict[str, Any]]]:
    """Frames and preview provenance for the shortlist production actually previewed.

    The frames come from the review bundle the builder just produced. The preview
    itself is described by the record the preview cache wrote next to the frames,
    which is read back rather than recomputed: it is the only place that knows
    which rendition was fetched and why.
    """

    frames: dict[str, list[dict[str, Any]]] = {}
    previews: dict[str, dict[str, Any]] = {}
    bundle = state.scene_review_bundle
    for item in getattr(bundle, "shortlist", None) or []:
        asset_id = str(item.get("asset_id") or "")
        if not asset_id:
            continue
        sampled: list[dict[str, Any]] = []
        cache_dir: Path | None = None
        for frame in item.get("sampled_frames") or []:
            raw_path = str(frame.get("local_frame_path") or "")
            path = _relative(raw_path)
            if not path or not frame.get("sha256"):
                continue
            if cache_dir is None and raw_path:
                cache_dir = _cache_dir_for_frame(raw_path)
            sampled.append(
                {
                    "local_frame_path": path,
                    "sha256": str(frame.get("sha256")),
                    "width": int(frame.get("width") or 0),
                    "height": int(frame.get("height") or 0),
                    "frame_index": int(frame.get("frame_index") or 0),
                    "perceptual_hash": str(frame.get("perceptual_hash") or ""),
                    "extraction_status": str(frame.get("extraction_status") or ""),
                }
            )
        frames[asset_id] = sampled
        previews[asset_id] = {
            "preview_status": str(item.get("preview_status") or "not_analysed"),
            **_preview_record(cache_dir),
        }
    return frames, previews


def _cache_dir_for_frame(frame_path: str) -> Path | None:
    """The preview cache folder a frame belongs to.

    A sampled video frame lives in ``<cache_key>/frames/``; the single "frame" of
    an image preview *is* the preview file, one level up. So the record is looked
    for from the frame outwards rather than at a fixed depth - which is what the
    first capture got wrong, leaving 54 of 56 previews without provenance.
    """

    if not frame_path:
        return None
    folder = Path(frame_path).resolve().parent
    for candidate in (folder, folder.parent):
        if (candidate / "preview_record.json").is_file():
            return candidate
    return None


def _preview_record(cache_dir: Path | None) -> dict[str, Any]:
    if cache_dir is None:
        return {}
    record_path = cache_dir / "preview_record.json"
    if not record_path.is_file():
        return {}
    try:
        record = json.loads(record_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return {
        "cache_key": str(record.get("cache_key") or ""),
        "preview_media_type": str(record.get("preview_media_type") or ""),
        "preview_source_url": str(record.get("preview_source_url") or ""),
        "local_path": _relative(str(record.get("local_path") or "")),
        "sha256": str(record.get("sha256") or ""),
        "bytes": int(record.get("bytes") or 0),
        "width": int(record.get("width") or 0),
        "height": int(record.get("height") or 0),
        "duration_sec": float(record.get("duration_sec") or 0.0),
        "fallback_reason": str(record.get("fallback_reason") or ""),
        "original_used": bool(record.get("original_used")),
        "cache_status": str(record.get("cache_status") or ""),
    }


def _relative(path: str) -> str:
    if not path:
        return ""
    candidate = Path(path)
    try:
        return candidate.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return candidate.as_posix()


def _freeze(
    scenes: list[dict[str, Any]],
    lineage: list[dict[str, Any]],
    providers: list[Any],
    counter: RequestCounter,
    granted_by: str,
) -> dict[str, Any]:
    """Assemble the frozen corpus, refusing anything that cannot be measured."""

    usable = [scene for scene in scenes if len(scene["candidates"]) >= 2]
    excluded = [
        {
            "scene_key": scene["scene_key"],
            "case_id": scene["case_id"],
            "reason": "insufficient_candidates_for_a_benchmark_scene",
            "candidate_count": len(scene["candidates"]),
            "executable_queries": scene["executable_queries"],
            "provider_attempts": scene["provider_attempts"],
        }
        for scene in scenes
        if len(scene["candidates"]) < 2
    ]

    corpus: dict[str, Any] = {
        "schema_version": CORPUS_SCHEMA_VERSION,
        "corpus_version": CORPUS_VERSION,
        "fixture_kind": FIXTURE_KIND_CURRENT_BENCHMARK,
        "generation_class": GENERATION_CURRENT,
        "plan_step": PLAN_STEP,
        "capture_head_sha": _head_sha(),
        "capture_timestamp_utc": _now(),
        "built_at_utc": _now(),
        "capture_workspace": CAPTURE_WORKSPACE,
        "evaluation_set_version": EVALUATION_SET_VERSION,
        "source": (
            "one bounded run of the current production retrieval path over a local "
            "evaluation script; no article fetch, no Vision, no paid call"
        ),
        "production_stages": list(PRODUCTION_STAGES),
        "stages_not_run": list(STAGES_NOT_RUN),
        "network": {
            "approved_actions": list(CAPTURE_NETWORK_ACTIONS),
            "granted_by": granted_by,
            "asset_download_used": False,
            "http_get_json_calls": counter.get_json,
            "http_download_stream_calls": counter.download_stream,
            "hosts": dict(sorted(counter.hosts.items())),
        },
        "providers": provider_matrix(providers),
        "evaluation_constants": {
            "used_asset_ids": "empty - every benchmark scene is judged on its own",
            "user_assets": "empty - the corpus measures provider retrieval",
            "media_index": (
                "empty - the local media library is a different source and is populated "
                "from the historical projects PLAN-9D-A retired as benchmark input"
            ),
            "vision_tags": "empty - the semantic backend stays at its shipped default (disabled)",
            "framing": "production dimensions come from the candidate record, never from the preview",
        },
        "scene_count": len(usable),
        "observation_count": sum(len(scene["candidates"]) for scene in usable),
        "scenes": usable,
        "excluded_scenes": excluded,
        "capture_statistics": capture_statistics(usable),
        "retrieval_failures": _failures(scenes),
        "planned_provider_search_calls": sum(
            int(entry["planned_provider_search_calls"]) for entry in lineage
        ),
        "corpus_sha256": "",
    }
    # Written before anything can refuse it. The provider requests are the one
    # part of this step that cannot be repeated cheaply or honestly, so they are
    # put on disk first; a later check that says no then costs a re-run of
    # ``finalize``, not of the capture. The raw file stays in the untracked
    # workspace and is never the corpus - it carries no digest.
    raw_path = REPO_ROOT / CAPTURE_WORKSPACE / "capture_raw.json"
    raw_path.write_text(json.dumps(corpus, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"raw capture written to {raw_path}")

    assert_no_configured_secret(corpus)
    findings = secret_like_findings(corpus)
    if findings:
        raise CaptureError(f"refusing to freeze a corpus with secret-like values: {findings}")
    corpus["corpus_sha256"] = corpus_digest(corpus)
    validate_corpus(corpus)
    validate_current_capture(corpus)
    return corpus


#: Environment names whose value must never appear in a captured artefact. The
#: pattern scan in ``plan9d_ground_truth`` guesses at shapes; this one knows the
#: actual strings, so it is exact. Only the *name* is ever reported.
SECRET_ENV_NAMES = (
    "PEXELS_API_KEY",
    "PIXABAY_API_KEY",
    "UNSPLASH_ACCESS_KEY",
    "OPENAI_API_KEY",
    "ELEVENLABS_API_KEY",
)


def assert_no_configured_secret(payload: Any) -> None:
    """Refuse to write anything that contains a credential this machine has."""

    blob = json.dumps(payload, ensure_ascii=False)
    leaked = [
        name
        for name in SECRET_ENV_NAMES
        if len((os.getenv(name) or "").strip()) >= 8 and (os.getenv(name) or "").strip() in blob
    ]
    if leaked:
        raise CaptureError(f"a configured credential reached the capture: {sorted(leaked)}")


def _fill_missing_preview_record(candidate: dict[str, Any]) -> None:
    """Read preview provenance out of the cache, once, while the cache is here.

    Only ever *fills*: a record already in the corpus is never rewritten, so this
    runs to a fixed point and the digest stops moving after the first finalize.
    On a clean clone the workspace is absent and nothing is added - which is why
    it has to happen before the corpus is committed, and why it is recorded as a
    property of the file rather than as something a reader can reproduce.
    """

    preview = candidate.get("preview")
    if not isinstance(preview, dict) or preview.get("cache_key"):
        return
    frames = candidate.get("frames") or []
    if not frames:
        return
    record = _preview_record(_cache_dir_for_frame(str(frames[0].get("local_frame_path") or "")))
    if record:
        candidate["preview"] = {**preview, **record}


def scene_categories(scene: dict[str, Any]) -> list[str]:
    """Technical categories for one captured scene, from the stored pool alone.

    Derived, never captured: the vocabulary and the rules belong to the offline
    builder's ``categorize``, and every input it needs is already frozen in the
    corpus. So this is a pure function of the file and can be recomputed by
    anyone, which is what makes ``finalize`` idempotent rather than a second pass
    at the providers.
    """

    categories, _selected, _support = categorize(
        {
            "scene_key": scene["scene_key"],
            "semantic_scene": scene["semantic_scene"],
            "raw_candidates": [dict(item["candidate"]) for item in scene["candidates"]],
            "prefer_video": bool(scene.get("prefer_video")),
            "required_duration_sec": float(scene.get("required_duration_sec") or 0.0),
            "require_provider_metadata": bool(scene.get("require_provider_metadata")),
            "source_class": str(scene.get("source_class") or ""),
        }
    )
    return sorted(categories)


def finalize(corpus: dict[str, Any]) -> dict[str, Any]:
    """Recompute everything the corpus derives from its own candidates, then re-freeze.

    Separate from the capture on purpose. The pools, the queries and the frames
    are network facts and are written once; the technical categories and the
    duplication statistics are arithmetic over those facts. Keeping the second
    kind recomputable means a reader can check them without asking a provider
    anything, and means a gap in the derivation is fixed by running this again
    rather than by capturing a second time.
    """

    finalized = json.loads(json.dumps(corpus))
    for scene in finalized["scenes"]:
        for candidate in scene["candidates"]:
            _fill_missing_preview_record(candidate)
            rights = candidate.get("rights") or {}
            # Normalised, not edited away: the decision itself stays verbatim in
            # ``candidate.policy_decision``; only the copy of it in the summary is
            # dropped. A capture written by the current ``_scene_record`` never has
            # one, so this is a no-op there and makes ``finalize`` idempotent.
            rights["policy_decision_in_candidate"] = bool(
                rights.pop("policy_decision", None) or candidate["candidate"].get("policy_decision")
            )
        scene["categories"] = scene_categories(scene)
    finalized["capture_statistics"] = capture_statistics(finalized["scenes"])
    finalized["scene_count"] = len(finalized["scenes"])
    finalized["observation_count"] = sum(len(scene["candidates"]) for scene in finalized["scenes"])
    assert_no_configured_secret(finalized)
    findings = secret_like_findings(finalized)
    if findings:
        raise CaptureError(f"refusing to freeze a corpus with secret-like values: {findings}")
    finalized["corpus_sha256"] = ""
    finalized["corpus_sha256"] = corpus_digest(finalized)
    validate_corpus(finalized)
    validate_current_capture(finalized)
    return finalized


def capture_statistics(scenes: list[dict[str, Any]]) -> dict[str, Any]:
    """Duplication and independence, measured rather than engineered away."""

    by_scene = {
        scene["scene_key"]: {str(item["asset_id"]) for item in scene["candidates"]}
        for scene in scenes
    }
    all_ids: list[str] = [
        str(item["asset_id"]) for scene in scenes for item in scene["candidates"]
    ]
    scene_count_by_asset: dict[str, int] = {}
    for scene_key, ids in by_scene.items():
        for asset_id in ids:
            scene_count_by_asset[asset_id] = scene_count_by_asset.get(asset_id, 0) + 1

    intersections = []
    keys = sorted(by_scene)
    for left_index, left in enumerate(keys):
        for right in keys[left_index + 1 :]:
            shared = sorted(by_scene[left] & by_scene[right])
            if shared:
                intersections.append(
                    {"scenes": [left, right], "shared_asset_count": len(shared), "shared_asset_ids": shared}
                )

    within_scene_repeats = [
        {
            "scene_key": scene["scene_key"],
            "asset_id": str(item["asset_id"]),
            "returned_times": int(item["returned_times"]),
            "queries": list(item["returned_by_queries"]),
        }
        for scene in scenes
        for item in scene["candidates"]
        if int(item["returned_times"]) > 1
    ]

    category_counts: dict[str, int] = {}
    for scene in scenes:
        for category in scene.get("categories") or []:
            category_counts[str(category)] = category_counts.get(str(category), 0) + 1

    return {
        "observation_count": len(all_ids),
        "unique_asset_count": len(set(all_ids)),
        "technical_categories": dict(sorted(category_counts.items())),
        "declared_vs_preview_dimension_divergence": _dimension_divergence(scenes),
        "assets_in_more_than_one_scene": sorted(
            [
                {"asset_id": asset_id, "scene_count": count}
                for asset_id, count in scene_count_by_asset.items()
                if count > 1
            ],
            key=lambda item: (-item["scene_count"], item["asset_id"]),
        ),
        "cross_scene_intersections": intersections,
        "within_scene_repeated_results": within_scene_repeats,
        "candidates_per_scene": {
            scene["scene_key"]: len(scene["candidates"]) for scene in scenes
        },
        "candidates_by_provider": _by_provider(scenes),
        "frames_captured": sum(
            1 for scene in scenes for item in scene["candidates"] for _ in item["frames"]
        ),
        "candidates_with_frames": sum(
            1 for scene in scenes for item in scene["candidates"] if item["frames"]
        ),
    }


def _dimension_divergence(scenes: list[dict[str, Any]]) -> dict[str, int]:
    """How often the provider's declared size differs from the cached preview's.

    The framing gate reads the *declared* size; the annotator looks at the
    preview. Counting the divergence keeps that distinction a measured property
    of the corpus instead of a footnote.
    """

    same = differs = unknown = 0
    for scene in scenes:
        for candidate in scene["candidates"]:
            declared = candidate.get("declared_dimensions") or {}
            preview = candidate.get("preview") or {}
            if not (declared.get("width") and declared.get("height")):
                unknown += 1
            elif not (preview.get("width") and preview.get("height")):
                unknown += 1
            elif (declared["width"], declared["height"]) == (preview["width"], preview["height"]):
                same += 1
            else:
                differs += 1
    return {"same": same, "differs": differs, "not_comparable": unknown}


def _by_provider(scenes: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for scene in scenes:
        for item in scene["candidates"]:
            name = str(item.get("provider") or "")
            counts[name] = counts.get(name, 0) + 1
    return dict(sorted(counts.items()))


def _failures(scenes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Provider attempts that did not complete. Facts only, no verdict."""

    failures: list[dict[str, Any]] = []
    for scene in scenes:
        for attempt in scene["provider_attempts"]:
            if attempt.get("status") == "completed":
                continue
            failures.append({"scene_key": scene["scene_key"], **attempt})
    return failures


def _head_sha() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="PLAN-9D-B current retrieval capture")
    sub = parser.add_subparsers(dest="command", required=True)
    preflight = sub.add_parser("preflight", help="offline planning, tripwires and provider matrix")
    preflight.add_argument(
        "--out",
        default="",
        help="write the report here as UTF-8 (the Windows console cannot print Cyrillic)",
    )
    capture = sub.add_parser("capture", help="run the bounded owner-approved capture")
    capture.add_argument("--granted-by", required=True, help="who approved this run")
    capture.add_argument("--out", default=str(CURRENT_CORPUS_PATH), help="frozen corpus path")
    final = sub.add_parser(
        "finalize", help="recompute the corpus's derived fields offline and re-freeze it"
    )
    final.add_argument(
        "--corpus",
        default=str(CURRENT_CORPUS_PATH),
        help="captured payload to finalize (the raw capture, or the frozen corpus itself)",
    )
    final.add_argument("--out", default="", help="destination; defaults to --corpus in place")
    args = parser.parse_args(argv)

    providers = create_default_stock_providers(load_environment=_load_environment)
    if args.command == "preflight":
        builder = create_builder(providers=providers, project_root=None, dry_run=True)
        lineage = plan_lineage(builder)
        violations = check_tripwires(lineage)
        report = {
            "evaluation_set_version": EVALUATION_SET_VERSION,
            "scene_count": len(lineage),
            "providers": provider_matrix(providers),
            "planned_provider_search_calls": sum(
                int(entry["planned_provider_search_calls"]) for entry in lineage
            ),
            "tripwire_violations": violations,
            "scenes": [
                {
                    key: entry[key]
                    for key in (
                        "scene_id",
                        "case_id",
                        "coverage",
                        "scene_text",
                        "visual_brief",
                        "visual_intents",
                        "primary_query",
                        "alternative_queries",
                        "semantic_scene",
                        "routing",
                        "query_plan",
                        "executable_queries",
                        "planned_provider_search_calls",
                    )
                }
                for entry in lineage
            ],
        }
        payload = json.dumps(report, ensure_ascii=False, indent=1)
        if args.out:
            out = Path(args.out)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(payload + "\n", encoding="utf-8")
            print(f"preflight report written to {out}")
        else:
            print(payload)
        print(f"scenes={len(lineage)} tripwire_violations={len(violations)}")
        return 1 if violations else 0

    if args.command == "finalize":
        path = Path(args.corpus)
        corpus = finalize(json.loads(path.read_text(encoding="utf-8")))
        out = Path(args.out) if args.out else path
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(corpus, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"finalized {out}")
        print(
            f"scenes={corpus['scene_count']} observations={corpus['observation_count']} "
            f"unique_assets={corpus['capture_statistics']['unique_asset_count']} "
            f"excluded={len(corpus['excluded_scenes'])}"
        )
        print(f"head={corpus['capture_head_sha']}")
        print(f"sha256={corpus['corpus_sha256']}")
        print("categories=" + json.dumps(corpus["capture_statistics"]["technical_categories"]))
        return 0

    corpus = finalize(capture_corpus(granted_by=args.granted_by))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(corpus, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"current retrieval corpus written to {out}")
    print(
        f"scenes={corpus['scene_count']} observations={corpus['observation_count']} "
        f"unique_assets={corpus['capture_statistics']['unique_asset_count']} "
        f"excluded={len(corpus['excluded_scenes'])}"
    )
    print(f"head={corpus['capture_head_sha']} sha256={corpus['corpus_sha256']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
