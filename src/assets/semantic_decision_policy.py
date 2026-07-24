from __future__ import annotations

import json
from pathlib import Path
from typing import Any


CALIBRATED_DECISIONS = {"suitable", "suitable_with_limitations", "review", "unsuitable"}
DECISION_PRIORITY = {
    "suitable": 3,
    "suitable_with_limitations": 2,
    "review": 1,
    "unsuitable": 0,
}
HIGH_CONFIDENCE = 0.85
MINIMUM_CONFIDENCE = 0.65


def calibrate_semantic_result(raw_result: dict[str, Any]) -> dict[str, Any]:
    """Return a non-destructive calibrated decision over a raw semantic result dict."""

    raw = dict(raw_result or {})
    raw_decision = _raw_decision(raw)
    raw_score = _score(raw.get("semantic_score"))
    confidence = _score(raw.get("confidence"))
    reasons: list[str] = []
    limitations: list[str] = []

    _append_limitations(raw, limitations, reasons)
    _append_term_limitations(raw, limitations)

    blockers = _blocking_reasons(raw)
    if blockers:
        calibrated_decision = "unsuitable"
        calibrated_score = min(raw_score, _blocker_score(blockers))
        reasons.extend(blockers)
    elif _has_low_confidence(raw, confidence):
        calibrated_decision = "review"
        calibrated_score = min(raw_score or confidence, 0.60)
        reasons.append("semantic_uncertainty")
    elif _all_required_semantics_present(raw):
        semantic_limitations = [item for item in limitations if item != "license_review_separate"]
        if raw_decision == "review" or semantic_limitations or reasons:
            calibrated_decision = "suitable_with_limitations" if semantic_limitations or reasons else "suitable"
        else:
            calibrated_decision = "suitable"
        calibrated_score = _positive_material_score(raw_score, calibrated_decision)
        if raw_decision == "review" and calibrated_decision == "suitable_with_limitations":
            reasons.append("raw_review_reclassified_as_suitable_material")
    elif raw_decision == "unsuitable":
        calibrated_decision = "unsuitable"
        calibrated_score = min(raw_score, 0.40)
        reasons.append("raw_unsuitable_without_overriding_evidence")
    else:
        calibrated_decision = "review"
        calibrated_score = min(max(raw_score, 0.45), 0.68)
        reasons.append("semantic_uncertainty")

    reasons = _unique(reasons)
    limitations = _unique(limitations)
    return {
        "candidate_id": str(raw.get("candidate_id") or raw.get("asset_id") or ""),
        "scene_id": str(raw.get("scene_id") or ""),
        "raw_decision": raw_decision,
        "raw_score": round(raw_score, 6),
        "confidence": round(confidence, 6),
        "calibrated_decision": calibrated_decision,
        "calibrated_score": round(max(0.0, min(1.0, calibrated_score)), 6),
        "calibration_reasons": reasons,
        "evidence_limitations": limitations,
        "hard_reject": bool(raw.get("hard_reject", False)),
        "effective_expected_classification": _effective_decision(calibrated_decision),
    }


def evaluate_live_dataset_calibration(
    *,
    results_path: str | Path,
    dataset_path: str | Path,
) -> dict[str, Any]:
    results = _load_json(results_path)
    dataset = _load_json(dataset_path)
    candidate_results = [dict(item) for item in results.get("candidate_results", []) or []]
    expected_by_id = _expected_by_candidate(dataset)
    expected_winners = _expected_winners_by_scene(dataset)

    calibrated = [calibrate_semantic_result(item) for item in candidate_results]
    raw_accuracy = _classification_accuracy(
        [
            (_effective_decision(_raw_decision(item)), expected_by_id.get(str(item.get("candidate_id") or "")))
            for item in candidate_results
        ]
    )
    calibrated_accuracy = _classification_accuracy(
        [
            (item["effective_expected_classification"], expected_by_id.get(str(item.get("candidate_id") or "")))
            for item in calibrated
        ]
    )
    pairwise = rank_pairwise_by_scene(calibrated, expected_winners=expected_winners)
    correct = sum(1 for item in pairwise if item.get("correct"))
    total = len(pairwise)
    return {
        "schema_version": "semantic_decision_calibration.v1",
        "results_path": str(results_path),
        "dataset_path": str(dataset_path),
        "raw_accuracy": raw_accuracy,
        "calibrated_accuracy": calibrated_accuracy,
        "pairwise_ranking_accuracy": round(correct / total, 6) if total else 0.0,
        "pairwise_correct": correct,
        "pairwise_total": total,
        "calibrated_results": calibrated,
        "pairwise_rankings": pairwise,
        "api_calls_performed": 0,
    }


def rank_pairwise_by_scene(
    calibrated_results: list[dict[str, Any]],
    *,
    expected_winners: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    expected_winners = expected_winners or {}
    by_scene: dict[str, list[dict[str, Any]]] = {}
    for item in calibrated_results:
        by_scene.setdefault(str(item.get("scene_id") or ""), []).append(item)

    rankings: list[dict[str, Any]] = []
    for scene_id, items in sorted(by_scene.items()):
        ranked = sorted(
            items,
            key=lambda item: (
                DECISION_PRIORITY.get(str(item.get("calibrated_decision") or ""), -1),
                float(item.get("calibrated_score") or 0.0),
                float(item.get("confidence") or 0.0),
            ),
            reverse=True,
        )
        if len(ranked) < 2:
            continue
        winner = ranked[0]
        runner_up = ranked[1]
        margin = round(float(winner.get("calibrated_score") or 0.0) - float(runner_up.get("calibrated_score") or 0.0), 6)
        expected = expected_winners.get(scene_id, "")
        rankings.append(
            {
                "scene_id": scene_id,
                "winner_candidate_id": winner.get("candidate_id", ""),
                "runner_up_candidate_id": runner_up.get("candidate_id", ""),
                "expected_winner_candidate_id": expected,
                "score_margin": margin,
                "correct": bool(expected and winner.get("candidate_id") == expected),
                "shadow_recommendation": {
                    "recommended_candidate": winner.get("candidate_id", ""),
                    "runner_up": runner_up.get("candidate_id", ""),
                    "score_margin": margin,
                    "confidence": _ranking_confidence(margin, str(winner.get("calibrated_decision") or "")),
                    "reasons": list(winner.get("calibration_reasons") or []),
                    "evidence_limitations": list(winner.get("evidence_limitations") or []),
                },
            }
        )
    return rankings


def write_calibration_report(evaluation: dict[str, Any], path: str | Path) -> None:
    lines = [
        "# Semantic Calibration Report",
        "",
        f"- Raw classification accuracy: {evaluation.get('raw_accuracy', 0.0)}",
        f"- Calibrated classification accuracy: {evaluation.get('calibrated_accuracy', 0.0)}",
        f"- Pairwise ranking accuracy: {evaluation.get('pairwise_correct', 0)}/{evaluation.get('pairwise_total', 0)}",
        f"- API calls performed: {evaluation.get('api_calls_performed', 0)}",
        "",
        "## Pairwise Rankings",
        "",
    ]
    for item in evaluation.get("pairwise_rankings", []) or []:
        lines.append(
            "- {scene}: winner `{winner}`, runner-up `{runner}`, margin {margin}, correct={correct}".format(
                scene=item.get("scene_id", ""),
                winner=item.get("winner_candidate_id", ""),
                runner=item.get("runner_up_candidate_id", ""),
                margin=item.get("score_margin", 0.0),
                correct=str(bool(item.get("correct"))).lower(),
            )
        )
    lines.extend(["", "## Calibrated Decisions", ""])
    for item in evaluation.get("calibrated_results", []) or []:
        reasons = ", ".join(item.get("calibration_reasons") or []) or "none"
        limits = ", ".join(item.get("evidence_limitations") or []) or "none"
        lines.append(
            "- `{candidate}`: raw `{raw}` ({raw_score}), calibrated `{decision}` ({score}); reasons: {reasons}; limitations: {limits}".format(
                candidate=item.get("candidate_id", ""),
                raw=item.get("raw_decision", ""),
                raw_score=item.get("raw_score", 0.0),
                decision=item.get("calibrated_decision", ""),
                score=item.get("calibrated_score", 0.0),
                reasons=reasons,
                limits=limits,
            )
        )
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write_text(target, "\n".join(lines) + "\n")


def _blocking_reasons(raw: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    if bool(raw.get("hard_reject", False)):
        reasons.append("hard_reject")
    exact_match = raw.get("exact_entity_match")
    subject_match = raw.get("subject_match")
    if subject_match is False or exact_match is False:
        reasons.append("exact_entity_or_subject_mismatch")
    for item in raw.get("negative_element_results") or []:
        if isinstance(item, dict) and bool(item.get("present", False)) and _score(item.get("confidence")) >= HIGH_CONFIDENCE:
            reasons.append("confirmed_negative_element")
            break
    for item in raw.get("must_have_results") or []:
        if isinstance(item, dict) and not bool(item.get("present", False)) and _score(item.get("confidence")) >= HIGH_CONFIDENCE:
            reasons.append("required_element_missing")
            break
    return _unique(reasons)


def _append_limitations(raw: dict[str, Any], limitations: list[str], reasons: list[str]) -> None:
    texts = [str(item).lower() for item in [*(raw.get("review_required_reasons") or []), *(raw.get("mismatch_reasons") or [])]]
    for text in texts:
        if "license" in text or "rights" in text or "attribution" in text:
            limitations.append("license_review_separate")
        if "single" in text and ("frame" in text or "still" in text or "image" in text):
            limitations.append("limited_temporal_evidence")
        if "temporal" in text and ("limited" in text or "cannot" in text):
            limitations.append("limited_temporal_evidence")
        if ("camera" in text or "viewpoint" in text or "view " in text or "shot" in text) and not _negative_word(text):
            reasons.append("camera_view_mismatch_non_blocking")
        if "not independently confirmed" in text or "species-level" in text or "cannot be confirmed" in text:
            limitations.append("visual_specificity_limited")


def _all_required_semantics_present(raw: dict[str, Any]) -> bool:
    if raw.get("subject_match") is False:
        return False
    if raw.get("action_match") is False:
        return False
    if raw.get("environment_match") is False:
        return False
    if raw.get("exact_entity_match") is False:
        return False
    for item in raw.get("must_have_results") or []:
        if isinstance(item, dict) and not bool(item.get("present", False)) and _score(item.get("confidence")) >= HIGH_CONFIDENCE:
            return False
    for item in raw.get("negative_element_results") or []:
        if isinstance(item, dict) and bool(item.get("present", False)) and _score(item.get("confidence")) >= HIGH_CONFIDENCE:
            return False
    return True


def _append_term_limitations(raw: dict[str, Any], limitations: list[str]) -> None:
    for item in raw.get("must_have_results") or []:
        if not isinstance(item, dict):
            continue
        confidence = _score(item.get("confidence"))
        if not bool(item.get("present", False)) and MINIMUM_CONFIDENCE <= confidence < HIGH_CONFIDENCE:
            limitations.append("low_confidence_required_element_missing")
    for item in raw.get("negative_element_results") or []:
        if not isinstance(item, dict):
            continue
        confidence = _score(item.get("confidence"))
        if bool(item.get("present", False)) and MINIMUM_CONFIDENCE <= confidence < HIGH_CONFIDENCE:
            limitations.append("low_confidence_negative_element")


def _has_low_confidence(raw: dict[str, Any], confidence: float) -> bool:
    if confidence and confidence < MINIMUM_CONFIDENCE:
        return True
    return any("low_confidence" in str(item).lower() for item in raw.get("review_required_reasons") or [])


def _raw_decision(raw: dict[str, Any]) -> str:
    value = str(raw.get("returned_classification") or raw.get("classification") or raw.get("decision") or "").strip().lower()
    if value in CALIBRATED_DECISIONS:
        return value
    if bool(raw.get("hard_reject", False)):
        return "unsuitable"
    score = _score(raw.get("semantic_score"))
    if score >= 0.75 and not raw.get("review_required_reasons"):
        return "suitable"
    if score < 0.45:
        return "unsuitable"
    return "review"


def _positive_material_score(raw_score: float, decision: str) -> float:
    if decision == "suitable":
        return max(raw_score, 0.86)
    return max(raw_score, 0.78)


def _blocker_score(blockers: list[str]) -> float:
    if "confirmed_negative_element" in blockers:
        return 0.15
    if "exact_entity_or_subject_mismatch" in blockers:
        return 0.20
    if "required_element_missing" in blockers:
        return 0.25
    return 0.30


def _ranking_confidence(margin: float, decision: str) -> str:
    if decision == "unsuitable":
        return "low"
    if margin >= 0.20:
        return "high"
    if margin >= 0.05:
        return "medium"
    return "low"


def _effective_decision(decision: str) -> str:
    return "suitable" if decision == "suitable_with_limitations" else decision


def _classification_accuracy(pairs: list[tuple[str, str | None]]) -> float:
    usable = [(actual, expected) for actual, expected in pairs if expected]
    if not usable:
        return 0.0
    return round(sum(1 for actual, expected in usable if actual == expected) / len(usable), 6)


def _expected_by_candidate(dataset: dict[str, Any]) -> dict[str, str]:
    expected: dict[str, str] = {}
    for scene in dataset.get("scenes") or []:
        for candidate in scene.get("candidates") or []:
            ground_truth = candidate.get("ground_truth") if isinstance(candidate.get("ground_truth"), dict) else {}
            candidate_id = str(candidate.get("candidate_id") or "")
            classification = str(ground_truth.get("expected_classification") or "")
            if candidate_id and classification:
                expected[candidate_id] = classification
    return expected


def _expected_winners_by_scene(dataset: dict[str, Any]) -> dict[str, str]:
    winners: dict[str, str] = {}
    for scene in dataset.get("scenes") or []:
        scene_id = str(scene.get("scene_id") or "")
        suitable = []
        for candidate in scene.get("candidates") or []:
            ground_truth = candidate.get("ground_truth") if isinstance(candidate.get("ground_truth"), dict) else {}
            if str(ground_truth.get("expected_classification") or "") == "suitable":
                suitable.append(str(candidate.get("candidate_id") or ""))
        if scene_id and suitable:
            winners[scene_id] = suitable[0]
    return winners


def _score(value: Any) -> float:
    try:
        return max(0.0, min(1.0, float(value or 0.0)))
    except (TypeError, ValueError):
        return 0.0


def _negative_word(text: str) -> bool:
    return "not visible" in text or "absent" in text or "negative" in text or "prohibited" in text


def _load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _atomic_write_text(path: Path, text: str) -> None:
    temp = path.with_suffix(path.suffix + ".part")
    temp.write_text(text, encoding="utf-8")
    temp.replace(path)


def _unique(values: list[str]) -> list[str]:
    return [item for item in dict.fromkeys(str(value) for value in values if str(value))]
