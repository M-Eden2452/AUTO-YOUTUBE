"""Offline retrieval quality gate over the frozen current corpus (PLAN-9D-C).

Why this module exists
----------------------
PLAN-9D-B proved only that a bounded run of the current production retrieval
path happened and that its result is frozen. It deliberately asserted nothing
about whether the pools it captured are any good. PLAN-9D-C is that question,
and it has to be answered *before* a human annotates anything, because a Vision
comparison run on top of a retrieval failure would report the failure as a
decision-quality result.

So this module measures the frozen corpus and nothing else. It opens no socket,
reads no provider, changes no production behaviour and tunes nothing. Every
number it produces is recomputed from ``current_corpus_v1.json`` on every call.

What it may and may not judge
-----------------------------
The corpus carries three levels and the PLAN-9D-B closure fixed what each one
admits:

``raw provider retrieval``
    1064 candidate observations across 14 scenes, provider metadata only. May be
    judged by metadata and by query provenance. May **not** be judged visually -
    1008 of them were never rendered to a preview.

``ranked / rights-filtered pool``
    the same 1064 after the production ranker and the rights owner.

``visually previewed shortlist``
    56 candidates - the production ``shortlist_size=5`` per scene, which is the
    only part a human can actually look at.

This module stays on the mechanical side of that line. It counts, it compares
declared strings against captured strings, and it reports. It does not look at
pixels and it does not encode anyone's opinion about a picture: the visual read
of the 56 previewed candidates is recorded in the PLAN-9D-C section of
``docs/current/PROJECT_EXECUTION_PLAN.md`` as evidence, never here as an oracle,
and the owner's blind annotation remains PLAN-9D-D's own step.

How the subject is matched
--------------------------
Only what the scene itself declares is used - ``semantic_scene.subject``,
``must_include`` and the provider-language part of ``secondary_subjects``. No
synonym list is invented here, because a hand-written lexicon would quietly
become the thing being measured. Two different strictnesses are reported side by
side rather than blended into one score:

``phrase``
    the declared term occurs verbatim. Strict, and what the gate decides on.

``token``
    any word of a declared term with at least four characters occurs. Loose, and
    reported for context only - for a subject such as ``solar power plant`` the
    words ``power`` and ``plant`` match plenty of things that are neither.

The gate's own thresholds are minimal on purpose. It asks whether current
retrieval can reach the subject at all, not whether it reaches it beautifully -
"beautifully" is a human judgement and belongs to PLAN-9D-D onwards.
"""

from __future__ import annotations

import json
import re
import sys
from typing import Any, Iterable

from tests.plan9d_ground_truth import (
    LEGACY_BROAD_QUERY_LITERALS,
    assert_current_benchmark_input,
    load_current_corpus,
)

GATE_VERSION = "plan9d-c-retrieval-gate-1"
PLAN_STEP = "PLAN-9D-C"

#: Scenes the PLAN-9D-C contract names explicitly as the mandatory evaluation set.
MANDATORY_CASE_IDS = (
    "gecko_on_smooth_glass",
    "hummingbird_hovering",
    "penguin_tobogganing_on_snow",
    "orca_in_open_ocean",
)

#: Written in a non-Latin script, so it can never have been a provider query.
_NON_PROVIDER_SCRIPT = re.compile(r"[^\x00-\x7f]")

_MIN_TOKEN_LENGTH = 4


class RetrievalGateError(RuntimeError):
    """Raised when the frozen corpus cannot support a retrieval verdict at all."""


def _text(value: Any) -> str:
    return str(value or "")


def _lower(values: Iterable[Any]) -> list[str]:
    return [_text(item).strip().lower() for item in values if _text(item).strip()]


def declared_subject_terms(scene: dict[str, Any]) -> list[str]:
    """The provider-language terms the scene itself declares for its subject.

    ``secondary_subjects`` is included but filtered: the current planner also
    stores narration words there, and those are not provider language. Filtering
    by script rather than by a stop list keeps the rule mechanical.
    """

    semantic = scene.get("semantic_scene") or {}
    declared = list(semantic.get("subject") or [])
    declared += list(semantic.get("must_include") or [])
    declared += [
        term
        for term in (semantic.get("secondary_subjects") or [])
        if not _NON_PROVIDER_SCRIPT.search(_text(term))
    ]
    ordered: list[str] = []
    for term in _lower(declared):
        if term not in ordered:
            ordered.append(term)
    return ordered


def subject_tokens(terms: Iterable[str]) -> list[str]:
    tokens: list[str] = []
    for term in terms:
        for word in re.split(r"\W+", term):
            if len(word) >= _MIN_TOKEN_LENGTH and word not in tokens:
                tokens.append(word)
    return tokens


def candidate_metadata_text(candidate: dict[str, Any]) -> str:
    """Everything the provider itself said about the asset.

    ``search_query`` is deliberately left out. It is the string *we* sent, so
    including it would make every candidate match its own query and turn the
    measurement into a tautology.
    """

    record = candidate.get("candidate") or {}
    parts = [
        record.get("title"),
        record.get("description"),
        " ".join(_text(item) for item in (record.get("tags") or [])),
        " ".join(_text(item) for item in (record.get("keywords") or [])),
    ]
    return " ".join(_text(part) for part in parts).lower()


def _carries_phrase(text: str, terms: Iterable[str]) -> bool:
    return any(term in text for term in terms)


def _carries_token(text: str, tokens: Iterable[str]) -> bool:
    return any(token in text for token in tokens)


def evaluate_query_integrity(scene: dict[str, Any]) -> dict[str, Any]:
    """Did the scene's own subject reach a provider, in provider language?

    The three defects PLAN-9B repaired are re-checked here against what was
    actually sent, not against what was planned: a non-provider-language query
    reaching a Latin index, a retired broad literal standing in for a subject,
    and a rung that carries no subject at all.
    """

    terms = declared_subject_terms(scene)
    attempts = scene.get("provider_attempts") or []
    retired = {literal.lower() for literal in LEGACY_BROAD_QUERY_LITERALS}

    executed = [_text(attempt.get("query")) for attempt in attempts]
    subjectful = [query for query in executed if _carries_phrase(query.lower(), terms)]
    subject_free = [query for query in executed if query not in subjectful]
    results_from_subjectful = sum(
        int(attempt.get("result_count") or 0)
        for attempt in attempts
        if _text(attempt.get("query")) in subjectful
    )
    results_from_subject_free = sum(
        int(attempt.get("result_count") or 0)
        for attempt in attempts
        if _text(attempt.get("query")) not in subjectful
    )

    return {
        "scene_id": _text(scene.get("scene_id")),
        "case_id": _text(scene.get("case_id")),
        "declared_subject_terms": terms,
        "provider_attempts": len(attempts),
        "subjectful_attempts": len(subjectful),
        "subject_free_attempts": len(subject_free),
        "subject_free_queries": sorted({query for query in subject_free}),
        "results_from_subjectful_queries": results_from_subjectful,
        "results_from_subject_free_queries": results_from_subject_free,
        "non_provider_script_queries": sorted(
            {query for query in executed if _NON_PROVIDER_SCRIPT.search(query)}
        ),
        "retired_broad_literals": sorted(
            {query for query in executed if query.lower() in retired}
        ),
        # The flat compatibility mirror is not what providers were asked, but it
        # is persisted, so a reader is told when it disagrees with the plan.
        "non_provider_script_in_legacy_mirror": sorted(
            {
                query
                for query in [_text(scene.get("primary_query"))]
                + [_text(item) for item in (scene.get("alternative_queries") or [])]
                if _NON_PROVIDER_SCRIPT.search(query)
            }
        ),
    }


def evaluate_raw_retrieval(scene: dict[str, Any]) -> dict[str, Any]:
    """What the whole captured pool contains, by provider metadata alone."""

    terms = declared_subject_terms(scene)
    tokens = subject_tokens(terms)
    candidates = scene.get("candidates") or []

    phrase_hits = 0
    token_hits = 0
    licensed = 0
    review_required = 0
    repeated = 0
    by_provider: dict[str, int] = {}
    for candidate in candidates:
        text = candidate_metadata_text(candidate)
        phrase_hits += int(_carries_phrase(text, terms))
        token_hits += int(_carries_token(text, tokens))
        rights = candidate.get("rights") or {}
        licensed += int(_text(rights.get("rights_status")) == "licensed")
        review_required += int(bool(rights.get("review_required")))
        repeated += int(int(candidate.get("returned_times") or 1) > 1)
        provider = _text(candidate.get("provider"))
        by_provider[provider] = by_provider.get(provider, 0) + 1

    avoid_terms = _lower(
        list((scene.get("semantic_scene") or {}).get("must_not_include") or [])
    )
    conflicting_terms = _lower(
        list((scene.get("semantic_scene") or {}).get("conflicting_context") or [])
    )
    return {
        "scene_id": _text(scene.get("scene_id")),
        "pool_size": len(candidates),
        "subject_phrase_hits": phrase_hits,
        "subject_token_hits": token_hits,
        "licensed": licensed,
        "review_required": review_required,
        "repeated_observations": repeated,
        "by_provider": dict(sorted(by_provider.items())),
        "must_avoid_terms": avoid_terms,
        "must_avoid_metadata_hits": sum(
            int(_carries_phrase(candidate_metadata_text(candidate), avoid_terms))
            for candidate in candidates
        )
        if avoid_terms
        else 0,
        "conflicting_context_terms": conflicting_terms,
        "conflicting_context_metadata_hits": sum(
            int(_carries_phrase(candidate_metadata_text(candidate), conflicting_terms))
            for candidate in candidates
        )
        if conflicting_terms
        else 0,
    }


def evaluate_shortlist(scene: dict[str, Any], *, shortlist_size: int = 5) -> dict[str, Any]:
    """What the decision owner - and later the annotator - can actually see.

    ``input_order`` is the position in the stored pool, which the capture builds
    by keeping the first occurrence of each asset in manifest order. The builder
    previews ``state.candidates[:shortlist_size]`` instead, and that list still
    contains repeated observations, so a repeat inside the window consumes a
    preview slot without adding a candidate anyone can look at. The difference
    between the two is reported rather than smoothed over.
    """

    terms = declared_subject_terms(scene)
    candidates = sorted(
        scene.get("candidates") or [], key=lambda item: int(item.get("input_order") or 0)
    )
    window = candidates[:shortlist_size]
    previewed = [item for item in candidates if item.get("frames")]

    return {
        "scene_id": _text(scene.get("scene_id")),
        "shortlist_size": shortlist_size,
        "window_size": len(window),
        "previewed": len(previewed),
        "preview_slots_lost_to_repeats": max(0, len(window) - len(previewed)),
        "previewed_ranks": [int(item.get("input_order") or 0) for item in previewed],
        "previewed_subject_phrase_hits": sum(
            int(_carries_phrase(candidate_metadata_text(item), terms))
            for item in previewed
        ),
        "previewed_not_allowed_for_render": [
            _text(item.get("blind_id"))
            for item in previewed
            if not (item.get("rights") or {}).get("allowed_for_render")
        ],
        "frames": sum(len(item.get("frames") or []) for item in previewed),
    }


def evaluate_selection(scene: dict[str, Any], *, shortlist_size: int = 5) -> dict[str, Any]:
    """Where the selected candidate sits relative to what was previewed.

    ``select_best_with_video`` replaces the ranker's choice with the first
    non-rejected video anywhere in the ranked list, so the selected asset is not
    bound to the preview window at all. Whether that is right is not decided
    here; that it happens is recorded, because PLAN-9D-D annotates the previewed
    set and PLAN-9D-E compares the decision against that annotation.
    """

    terms = declared_subject_terms(scene)
    selected_id = _text(scene.get("selected_asset_id"))
    candidates = sorted(
        scene.get("candidates") or [], key=lambda item: int(item.get("input_order") or 0)
    )
    selected = next(
        (item for item in candidates if _text(item.get("asset_id")) == selected_id), None
    )
    first_video = next(
        (
            item
            for item in candidates
            if _text((item.get("candidate") or {}).get("media_type")) == "video"
        ),
        None,
    )
    avoid_terms = _lower(
        list((scene.get("semantic_scene") or {}).get("must_not_include") or [])
    )

    record: dict[str, Any] = {
        "scene_id": _text(scene.get("scene_id")),
        "selected_asset_id": selected_id,
        "selected_blind_id": _text(scene.get("selected_blind_id")),
        "has_selection": bool(selected_id),
        "support_status": _text(scene.get("selection_support_status")),
    }
    if selected is None:
        record.update(
            {
                "selected_rank": None,
                "selected_media_type": "",
                "selected_in_preview_window": False,
                "selected_previewed": False,
                "selected_subject_phrase_hit": False,
                "selected_must_avoid_hit": False,
                "selected_is_first_video": False,
            }
        )
        return record

    text = candidate_metadata_text(selected)
    rank = int(selected.get("input_order") or 0)
    record.update(
        {
            "selected_rank": rank,
            "selected_media_type": _text((selected.get("candidate") or {}).get("media_type")),
            "selected_in_preview_window": rank < shortlist_size,
            "selected_previewed": bool(selected.get("frames")),
            "selected_subject_phrase_hit": _carries_phrase(text, terms),
            "selected_must_avoid_hit": bool(avoid_terms)
            and _carries_phrase(text, avoid_terms),
            "selected_is_first_video": first_video is not None
            and _text(first_video.get("asset_id")) == selected_id,
            "selected_allowed_for_render": bool(
                (selected.get("rights") or {}).get("allowed_for_render")
            ),
        }
    )
    return record


def scene_verdict(
    query: dict[str, Any], raw: dict[str, Any], shortlist: dict[str, Any], selection: dict[str, Any]
) -> dict[str, Any]:
    """The five conditions PLAN-9D-C actually gates on, per scene.

    Deliberately minimal. The step exists to answer whether current retrieval can
    reach the declared subject at all; how well it reaches it is what the human
    pass after this step is for.
    """

    failures: list[str] = []
    if query["subjectful_attempts"] < 1:
        failures.append("no_executed_query_carried_the_subject")
    if query["non_provider_script_queries"]:
        failures.append("non_provider_language_query_reached_a_provider")
    if query["retired_broad_literals"]:
        failures.append("retired_broad_literal_reached_a_provider")
    if raw["subject_phrase_hits"] < 1:
        failures.append("no_pool_candidate_carries_the_subject_in_provider_metadata")
    if shortlist["previewed"] < 1:
        failures.append("nothing_was_previewed_for_this_scene")
    if shortlist["previewed_not_allowed_for_render"]:
        failures.append("a_rights_blocked_candidate_reached_the_shortlist")
    if selection["has_selection"] and selection["selected_must_avoid_hit"]:
        failures.append("selected_candidate_matches_a_declared_must_avoid_phrase")

    return {
        "scene_id": query["scene_id"],
        "case_id": query["case_id"],
        "passed": not failures,
        "failures": failures,
    }


def run_retrieval_gate(corpus: dict[str, Any] | None = None) -> dict[str, Any]:
    """The whole gate, recomputed from the frozen corpus on every call."""

    corpus = corpus if corpus is not None else load_current_corpus()
    assert_current_benchmark_input(corpus)
    scenes = corpus.get("scenes") or []
    if not scenes:
        raise RetrievalGateError("the frozen corpus carries no scene to evaluate")

    per_scene = []
    for scene in scenes:
        query = evaluate_query_integrity(scene)
        raw = evaluate_raw_retrieval(scene)
        shortlist = evaluate_shortlist(scene)
        selection = evaluate_selection(scene)
        per_scene.append(
            {
                "query_integrity": query,
                "raw_retrieval": raw,
                "preview_shortlist": shortlist,
                "selection": selection,
                "verdict": scene_verdict(query, raw, shortlist, selection),
            }
        )

    observed_cases = {entry["verdict"]["case_id"] for entry in per_scene}
    missing_mandatory = [
        case_id for case_id in MANDATORY_CASE_IDS if case_id not in observed_cases
    ]

    totals = {
        "scenes": len(per_scene),
        "observations": sum(entry["raw_retrieval"]["pool_size"] for entry in per_scene),
        "previewed": sum(entry["preview_shortlist"]["previewed"] for entry in per_scene),
        "frames": sum(entry["preview_shortlist"]["frames"] for entry in per_scene),
        "licensed": sum(entry["raw_retrieval"]["licensed"] for entry in per_scene),
        "review_required": sum(
            entry["raw_retrieval"]["review_required"] for entry in per_scene
        ),
        "subject_phrase_hits": sum(
            entry["raw_retrieval"]["subject_phrase_hits"] for entry in per_scene
        ),
        "subject_token_hits": sum(
            entry["raw_retrieval"]["subject_token_hits"] for entry in per_scene
        ),
        "preview_slots_lost_to_repeats": sum(
            entry["preview_shortlist"]["preview_slots_lost_to_repeats"]
            for entry in per_scene
        ),
        "scenes_with_selection": sum(
            int(entry["selection"]["has_selection"]) for entry in per_scene
        ),
        "selections_outside_preview_window": sum(
            int(entry["selection"]["has_selection"])
            and int(not entry["selection"]["selected_in_preview_window"])
            for entry in per_scene
        ),
        "selections_never_previewed": sum(
            int(entry["selection"]["has_selection"])
            and int(not entry["selection"]["selected_previewed"])
            for entry in per_scene
        ),
        "selections_that_are_the_first_video": sum(
            int(entry["selection"]["selected_is_first_video"]) for entry in per_scene
        ),
        "scenes_with_non_provider_script_in_legacy_mirror": sum(
            int(bool(entry["query_integrity"]["non_provider_script_in_legacy_mirror"]))
            for entry in per_scene
        ),
        "subject_free_provider_attempts": sum(
            entry["query_integrity"]["subject_free_attempts"] for entry in per_scene
        ),
        "results_from_subject_free_queries": sum(
            entry["query_integrity"]["results_from_subject_free_queries"]
            for entry in per_scene
        ),
    }

    failed = [entry["verdict"] for entry in per_scene if not entry["verdict"]["passed"]]
    return {
        "gate_version": GATE_VERSION,
        "plan_step": PLAN_STEP,
        "corpus_version": _text(corpus.get("corpus_version")),
        "corpus_sha256": _text(corpus.get("corpus_sha256")),
        "capture_head_sha": _text(corpus.get("capture_head_sha")),
        "mandatory_case_ids": list(MANDATORY_CASE_IDS),
        "missing_mandatory_cases": missing_mandatory,
        "totals": totals,
        "scenes": per_scene,
        "failed_scenes": failed,
        "passed": not failed and not missing_mandatory,
    }


def main(argv: list[str] | None = None) -> int:
    report = run_retrieval_gate()
    json.dump(report, sys.stdout, ensure_ascii=False, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0 if report["passed"] else 1


if __name__ == "__main__":  # pragma: no cover - manual inspection entry point
    raise SystemExit(main())
