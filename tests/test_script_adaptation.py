"""Offline contract tests for Q2.2B script adaptation and fact locks.

No network, provider, TTS, render, or user project is touched.  Adapters in this
module are in-memory fakes and every assertion operates on plain dictionaries.
"""

from __future__ import annotations

import unittest

from src.content.script_engine.adaptation import (
    ADAPT_LIGHT,
    ADAPT_NONE,
    MAX_ADAPTATION_PASSES,
    NeutralPhrasingAdapter,
    SceneAdaptationProposal,
    SceneAdaptationRequest,
    adapt_scenes,
    apply_adaptation_to_script,
)
from src.content.script_engine.fact_locks import (
    LOCK_CAUSAL,
    LOCK_DATE,
    LOCK_ENTITY,
    LOCK_GEOGRAPHY,
    LOCK_MEASUREMENT,
    LOCK_NUMBER,
    LOCK_SUPERLATIVE,
    LOCK_UNCERTAINTY,
    FactLockSet,
    extract_fact_locks,
    extract_scene_locks,
    normalize_text,
    verify_scene_adaptation,
)


def _lock_surfaces(locks: FactLockSet, kind: str) -> set[str]:
    return {normalize_text(lock.surface) for lock in locks.locks if lock.kind == kind}


def _request(narration: str, *, scene_id: str = "scene_001") -> tuple[SceneAdaptationRequest, FactLockSet]:
    script = {"scenes": [{"scene_id": scene_id, "narration": narration}]}
    locks = extract_fact_locks(script)
    return (
        SceneAdaptationRequest(
            scene_id=scene_id,
            narration=narration,
            reason="visual_coverage_incomplete",
            scene_duration_sec=8.0,
            locks=locks.for_scene(scene_id),
        ),
        locks,
    )


class FactLockExtractionTests(unittest.TestCase):
    def test_numbers_dates_and_measurements_are_locked_without_conflating_them(self) -> None:
        narration = "27.07.2026 исследователи подтвердили 54% проб и частицы размером 13,5 нм."
        locks = FactLockSet(extract_scene_locks(narration, scene_id="scene_001"))

        self.assertIn("27.07.2026", _lock_surfaces(locks, LOCK_DATE))
        self.assertIn("54%", _lock_surfaces(locks, LOCK_NUMBER))
        self.assertIn("13,5", _lock_surfaces(locks, LOCK_NUMBER))
        self.assertIn("54%", _lock_surfaces(locks, LOCK_MEASUREMENT))
        self.assertIn("13,5 нм", _lock_surfaces(locks, LOCK_MEASUREMENT))

    def test_textual_month_and_year_are_dates(self) -> None:
        locks = FactLockSet(
            extract_scene_locks("В январе 2023 года начался отбор проб.", scene_id="scene_001")
        )

        dates = _lock_surfaces(locks, LOCK_DATE)
        self.assertIn("2023", dates)
        self.assertIn("январ", dates)

    def test_declared_entities_and_geography_are_locked_even_at_sentence_start(self) -> None:
        script = {
            "scenes": [
                {
                    "scene_id": "scene_001",
                    "narration": "Антарктида включает McMurdo Dry Valleys.",
                    "visual_brief": {
                        "place": "Антарктида",
                        "exact_entities": ["McMurdo Dry Valleys"],
                    },
                }
            ]
        }

        locks = extract_fact_locks(script)
        self.assertIn("антарктида", _lock_surfaces(locks, LOCK_GEOGRAPHY))
        self.assertIn("mcmurdo dry valleys", _lock_surfaces(locks, LOCK_ENTITY))

    def test_research_entities_are_locked_only_when_the_scene_actually_names_them(self) -> None:
        script = {
            "scenes": [
                {"scene_id": "scene_001", "narration": "Прибор PTR-TOF измерил частицы."},
                {"scene_id": "scene_002", "narration": "Вторая сцена говорит только о почве."},
            ]
        }
        research = {"claims": [{"entities": ["PTR-TOF", "Ionicon"]}]}

        locks = extract_fact_locks(script, research=research)
        first = {normalize_text(lock.surface) for lock in locks.for_scene("scene_001")}
        second = {normalize_text(lock.surface) for lock in locks.for_scene("scene_002")}
        self.assertIn("ptr-tof", first)
        self.assertNotIn("ptr-tof", second)
        self.assertNotIn("ionicon", first)

    def test_uncertainty_causality_and_superlative_claims_are_locked(self) -> None:
        narration = (
            "Вероятно, это произошло из-за ветра и стало самым крупным переносом частиц."
        )
        locks = FactLockSet(extract_scene_locks(narration, scene_id="scene_001"))

        self.assertTrue(_lock_surfaces(locks, LOCK_UNCERTAINTY))
        self.assertTrue(_lock_surfaces(locks, LOCK_CAUSAL))
        self.assertIn("самым крупным", _lock_surfaces(locks, LOCK_SUPERLATIVE))

    def test_fact_lock_set_round_trip_preserves_all_kinds(self) -> None:
        original = extract_fact_locks(
            {
                "scenes": [
                    {
                        "scene_id": "scene_001",
                        "narration": "В 2023 году Антарктида, вероятно, получила 5 мг частиц.",
                        "visual_brief": {"place": "Антарктида"},
                    }
                ]
            }
        )

        restored = FactLockSet.from_dict(original.to_dict())
        self.assertEqual(restored.to_dict(), original.to_dict())


class FactLockVerificationTests(unittest.TestCase):
    def test_changed_number_and_date_are_rejected(self) -> None:
        original = "В январе 2023 года частицы нашли в 54% проб."
        locks = extract_scene_locks(original, scene_id="scene_001")
        violations = verify_scene_adaptation(
            "В январе 2024 года частицы нашли в 55% проб.",
            locks,
            original=original,
        )

        self.assertTrue(any(item.startswith("date:2023") for item in violations))
        self.assertTrue(any(item.startswith("number:54%") for item in violations))

    def test_measurement_values_cannot_be_swapped_between_units(self) -> None:
        original = "В образце было 5 мг вещества на дистанции 10 км."
        locks = extract_scene_locks(original, scene_id="scene_001")
        violations = verify_scene_adaptation(
            "В образце было 10 мг вещества на дистанции 5 км.",
            locks,
            original=original,
        )

        self.assertTrue(any(item.startswith("measurement:5 мг") for item in violations))
        self.assertTrue(any(item.startswith("measurement:10 км") for item in violations))

    def test_named_entity_and_geography_must_survive(self) -> None:
        original = "Антарктида включает McMurdo Dry Valleys."
        locks = extract_scene_locks(
            original,
            scene_id="scene_001",
            extra_entities=["McMurdo Dry Valleys"],
            extra_geography=["Антарктида"],
        )
        violations = verify_scene_adaptation(
            "Арктика включает другие сухие долины.",
            locks,
            original=original,
        )

        self.assertTrue(any(item.startswith("geography:Антарктида") for item in violations))
        self.assertTrue(any(item.startswith("named_entity:McMurdo Dry Valleys") for item in violations))

    def test_uncertainty_level_may_be_rephrased_but_not_strengthened(self) -> None:
        original = "Вероятно, частицы пришли по воздуху."
        locks = extract_scene_locks(original, scene_id="scene_001")

        same_level = verify_scene_adaptation(
            "Скорее всего, частицы пришли по воздуху.",
            locks,
            original=original,
        )
        strengthened = verify_scene_adaptation(
            "Возможно, частицы пришли по воздуху.",
            locks,
            original=original,
        )

        self.assertEqual(same_level, [])
        self.assertTrue(any(item.startswith("uncertainty_level:") for item in strengthened))

    def test_causality_cannot_be_removed_or_added(self) -> None:
        causal = "Частицы переместились из-за сильного ветра."
        causal_locks = extract_scene_locks(causal, scene_id="scene_001")
        removed = verify_scene_adaptation(
            "Частицы переместились при сильном ветре.",
            causal_locks,
            original=causal,
        )
        neutral = "Частицы обнаружили рядом с сильным ветром."
        neutral_locks = extract_scene_locks(neutral, scene_id="scene_001")
        added = verify_scene_adaptation(
            "Частицы обнаружили из-за сильного ветра.",
            neutral_locks,
            original=neutral,
        )

        self.assertTrue(any(item.startswith("causal:") for item in removed))
        self.assertTrue(any(item == "causal:added" for item in added))

    def test_superlative_phrase_cannot_change_or_be_added(self) -> None:
        original = "Это был самый крупный перенос частиц."
        locks = extract_scene_locks(original, scene_id="scene_001")
        changed = verify_scene_adaptation(
            "Это был самый быстрый перенос частиц.",
            locks,
            original=original,
        )
        neutral = "Это был заметный перенос частиц."
        added = verify_scene_adaptation(
            "Это был самый крупный перенос частиц.",
            extract_scene_locks(neutral, scene_id="scene_001"),
            original=neutral,
        )

        self.assertTrue(any(item.startswith("superlative:самый крупный") for item in changed))
        self.assertTrue(any(item == "superlative:added" for item in added))


class _RecordingAdapter:
    adapter_id = "recording"
    paid = False

    def __init__(self, proposal: SceneAdaptationProposal | None = None, error: Exception | None = None):
        self.proposal = proposal
        self.error = error
        self.calls = 0

    def adapt(self, request: SceneAdaptationRequest) -> SceneAdaptationProposal:
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.proposal or SceneAdaptationProposal(scene_id=request.scene_id)


class _PaidAdapter(_RecordingAdapter):
    adapter_id = "paid"
    paid = True


class AdaptationContractTests(unittest.TestCase):
    def test_none_mode_never_calls_the_adapter(self) -> None:
        request, locks = _request("В 2023 году нашли 54% проб.")
        adapter = _RecordingAdapter()

        report = adapt_scenes(
            requests=[request],
            fact_locks=locks,
            adapter=adapter,
            mode=ADAPT_NONE,
        )

        self.assertEqual(adapter.calls, 0)
        self.assertEqual(report.changed_scene_ids, [])
        self.assertIn("script_adaptation_disabled", report.warnings)

    def test_light_mode_accepts_a_safe_visual_only_adaptation(self) -> None:
        narration = "В 2023 году исследователи работали в Антарктиде, и они собрали образцы почвы."
        request, locks = _request(narration)
        adapter = _RecordingAdapter(
            SceneAdaptationProposal(
                scene_id=request.scene_id,
                narration=narration,
                visual_parts=[
                    "В 2023 году исследователи работали в Антарктиде",
                    "они собрали образцы почвы",
                ],
                revised_brief={"media_types": ["video", "image"]},
                rules_applied=["split_into_visual_parts"],
                reasons=["two honest visual parts"],
            )
        )

        report = adapt_scenes(
            requests=[request],
            fact_locks=locks,
            adapter=adapter,
            mode=ADAPT_LIGHT,
        )
        updated = apply_adaptation_to_script(
            {"scenes": [{"scene_id": request.scene_id, "narration": narration}]},
            report,
        )

        self.assertEqual(adapter.calls, 1)
        self.assertEqual(report.changed_scene_ids, [request.scene_id])
        self.assertEqual(updated["scenes"][0]["narration"], narration)
        self.assertEqual(len(updated["scenes"][0]["visual_parts"]), 2)
        self.assertTrue(updated["scenes"][0]["visual_brief_adapted"])

    def test_maximum_one_pass_is_enforced_before_calling_the_adapter(self) -> None:
        request, locks = _request("В 2023 году нашли частицы.")
        adapter = _RecordingAdapter()

        report = adapt_scenes(
            requests=[request],
            fact_locks=locks,
            adapter=adapter,
            mode=ADAPT_LIGHT,
            pass_index=MAX_ADAPTATION_PASSES,
        )

        self.assertEqual(adapter.calls, 0)
        self.assertIn("adaptation_pass_limit_reached", report.warnings)

    def test_paid_adapter_requires_explicit_opt_in(self) -> None:
        request, locks = _request("В 2023 году нашли частицы.")
        adapter = _PaidAdapter(
            SceneAdaptationProposal(
                scene_id=request.scene_id,
                narration=request.narration,
                visual_parts=["В 2023 году", "нашли частицы"],
            )
        )

        blocked = adapt_scenes(
            requests=[request],
            fact_locks=locks,
            adapter=adapter,
            mode=ADAPT_LIGHT,
            allow_paid=False,
        )
        allowed = adapt_scenes(
            requests=[request],
            fact_locks=locks,
            adapter=adapter,
            mode=ADAPT_LIGHT,
            allow_paid=True,
        )

        self.assertEqual(adapter.calls, 1)
        self.assertIn("adapter_paid_requires_explicit_paid_approval", blocked.warnings)
        self.assertEqual(allowed.changed_scene_ids, [request.scene_id])

    def test_adapter_failure_keeps_the_original_scene(self) -> None:
        narration = "В 2023 году нашли 54% проб."
        request, locks = _request(narration)
        adapter = _RecordingAdapter(error=RuntimeError("offline adapter failed"))
        script = {"scenes": [{"scene_id": request.scene_id, "narration": narration}]}

        report = adapt_scenes(
            requests=[request],
            fact_locks=locks,
            adapter=adapter,
            mode=ADAPT_LIGHT,
        )
        updated = apply_adaptation_to_script(script, report)

        outcome = report.for_scene(request.scene_id)
        self.assertFalse(outcome.accepted)
        self.assertTrue(outcome.rejection_reason.startswith("adapter_failed:"))
        self.assertEqual(updated, {**script, "scenes": [dict(script["scenes"][0])], "narration_text": narration, "script_adaptation": {
            "adapter_id": "recording",
            "mode": ADAPT_LIGHT,
            "pass_index": 0,
            "changed_scene_ids": [],
        }})

    def test_fact_lock_violation_keeps_original_and_records_validation_failure(self) -> None:
        narration = "В январе 2023 года нашли 54% проб."
        request, locks = _request(narration)
        adapter = _RecordingAdapter(
            SceneAdaptationProposal(
                scene_id=request.scene_id,
                narration="В январе 2024 года нашли 55% проб.",
                rules_applied=["rephrase_narration"],
                reasons=["unsafe change for test"],
            )
        )
        script = {"scenes": [{"scene_id": request.scene_id, "narration": narration}]}

        report = adapt_scenes(
            requests=[request],
            fact_locks=locks,
            adapter=adapter,
            mode=ADAPT_LIGHT,
        )
        updated = apply_adaptation_to_script(script, report)
        outcome = report.for_scene(request.scene_id)

        self.assertFalse(outcome.accepted)
        self.assertEqual(outcome.rejection_reason, "fact_lock_violation")
        self.assertTrue(outcome.fact_violations)
        self.assertEqual(outcome.adapted_narration, narration)
        self.assertEqual(updated["scenes"][0]["narration"], narration)
        self.assertEqual(report.changed_scene_ids, [])

    def test_default_offline_adapter_never_rewrites_narration(self) -> None:
        narration = "Учёные работали в Антарктиде, и они собрали образцы почвы."
        request, locks = _request(narration)

        report = adapt_scenes(
            requests=[request],
            fact_locks=locks,
            adapter=NeutralPhrasingAdapter(),
            mode=ADAPT_LIGHT,
        )

        outcome = report.for_scene(request.scene_id)
        self.assertTrue(outcome.accepted)
        self.assertEqual(outcome.adapted_narration, narration)
        self.assertFalse(outcome.narration_changed)


if __name__ == "__main__":
    unittest.main()
