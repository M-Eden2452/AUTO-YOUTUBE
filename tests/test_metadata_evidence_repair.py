from __future__ import annotations

import unittest

from src.assets.scene_strategy import CLASS_SPECIFIC_OBJECT
from src.assets.semantic_selection.candidate_ranker import rank_candidates
from src.assets.semantic_selection.evidence import (
    LOCAL_MATCH_MAX_GAP,
    METADATA_FIELDS,
    build_evidence,
)
from src.assets.semantic_selection.models import SemanticScene


def _candidate(
    asset_id: str,
    *,
    provider: str = "fake",
    title: str = "",
    description: str = "",
    tags: list[str] | None = None,
) -> dict[str, object]:
    return {
        "asset_id": asset_id,
        "provider": provider,
        "media_type": "image",
        "title": title,
        "description": description,
        "tags": list(tags or []),
        "tags_source": "provider",
        "width": 1080,
        "height": 1920,
        "allowed_for_render": True,
        "review_required": False,
        "rights_status": "licensed",
    }


def _rank(
    candidate: dict[str, object],
    *,
    subject: str,
    action: str = "",
    environment: str = "",
) -> dict[str, object]:
    scene = SemanticScene(
        scene_id="scene_metadata_evidence",
        subject=[subject] if subject else [],
        action=[action] if action else [],
        environment=[environment] if environment else [],
        source_class=CLASS_SPECIFIC_OBJECT,
    )
    return rank_candidates(scene, [candidate], source_class=scene.source_class)[0]


def _slot(result: dict[str, object], kind: str) -> dict[str, object]:
    decision = result["selection_decision"]
    assert isinstance(decision, dict)
    slots = decision["slots"]
    assert isinstance(slots, dict)
    details = slots["details"]
    assert isinstance(details, list)
    return next(item for item in details if item["kind"] == kind)


class MetadataEvidenceRepairTest(unittest.TestCase):
    def test_dispersed_multiword_tokens_are_not_full_strength_evidence(self) -> None:
        candidate = _candidate(
            "dispersed",
            title="Volcanic archive survey",
            description=(
                "A rare mineral was recorded during the first survey. "
                + "unrelated catalogue material " * 20
                + "Coastal weather observations followed many years later. "
                + "more unrelated catalogue material " * 20
                + "The final appendix indexes animal migration records."
            ),
        )

        result = _rank(candidate, subject="rare coastal animal")

        self.assertLess(result["subject_match"], 99.0)
        self.assertNotEqual(_slot(result, "subject")["status"], "matched")

    def test_direct_phrase_in_title_remains_full_strength(self) -> None:
        result = _rank(
            _candidate("direct", title="Rare coastal animal in its nesting grounds"),
            subject="rare coastal animal",
        )

        self.assertEqual(result["subject_match"], 100.0)
        self.assertEqual(_slot(result, "subject")["status"], "matched")

    def test_description_locality_window_accepts_documented_boundary(self) -> None:
        filler = " ".join(f"bridge{index}" for index in range(LOCAL_MATCH_MAX_GAP))
        result = _rank(
            _candidate(
                "local_boundary",
                title="Field observation",
                description=f"Rare {filler} coastal animal in view.",
            ),
            subject="rare coastal animal",
        )

        self.assertEqual(result["subject_match"], 100.0)

    def test_description_locality_window_rejects_one_token_beyond_boundary(self) -> None:
        filler = " ".join(
            f"bridge{index}" for index in range(LOCAL_MATCH_MAX_GAP + 1)
        )
        result = _rank(
            _candidate(
                "outside_boundary",
                title="Field observation",
                description=f"Rare {filler} coastal animal in view.",
            ),
            subject="rare coastal animal",
        )

        self.assertLess(result["subject_match"], 99.0)

    def test_explicit_single_word_entity_in_title_remains_full_strength(self) -> None:
        result = _rank(
            _candidate("single", title="Hummingbird feeding beside red flowers"),
            subject="hummingbird",
        )

        self.assertEqual(result["subject_match"], 100.0)
        self.assertEqual(_slot(result, "subject")["status"], "matched")

    def test_live4_lava_catalogue_prose_does_not_match_unusual_animals(self) -> None:
        # Deterministic extraction of the causal pattern in LIVE-4
        # internet_archive_galapagos_ast_2005306. The persisted description mentions
        # habitat, animals and unusual in different statements about a lava image.
        candidate = _candidate(
            "internet_archive_galapagos_ast_2005306",
            provider="internet_archive",
            title="Lava at Sierra Negra Summit: Image of the Day",
            description=(
                "The Sierra Negra volcano erupted and a thermal satellite recorded "
                "the lava flow. Once the lava cools it may eventually provide a "
                "habitat for Galapagos wildlife. "
                + "volcano observation and catalogue notes " * 30
                + "Today the animals on these islands count among the world's most "
                "unusual and colorful species."
            ),
            tags=["ASTER", "Terra"],
        )

        result = _rank(candidate, subject="unusual animals", environment="natural habitat")

        self.assertLess(result["subject_match"], 99.0)
        self.assertNotEqual(_slot(result, "subject")["status"], "matched")

    def test_live4_life_on_earth_catalogue_prose_does_not_match_hummingbird(self) -> None:
        # Deterministic extraction of the causal pattern in LIVE-4
        # internet_archive_life_on_earth: one animal mention inside a catalogue of a
        # complete television series is not evidence that the selected asset depicts it.
        candidate = _candidate(
            "internet_archive_life_on_earth",
            provider="internet_archive",
            title="Life On Earth BBC Nature series with complete episodes",
            description=(
                "This catalogue describes a complete natural-history television series. "
                + "Episode synopsis and production notes cover many unrelated species. " * 35
                + "One chapter mentions the elongated mouth of the hummingbird. "
                + "Further episode synopsis and production notes follow. " * 35
            ),
            tags=["Biology", "BBC Earth", "Complete Series", "Educational"],
        )

        result = _rank(candidate, subject="hummingbird", action="hovering midair")

        self.assertLess(result["subject_match"], 99.0)
        self.assertNotEqual(_slot(result, "subject")["status"], "matched")

    def test_live4_style_hummingbird_phrase_remains_strong(self) -> None:
        result = _rank(
            _candidate(
                "pexels_hummingbird",
                provider="pexels",
                title="Detailed photo of a hummingbird hovering midair",
            ),
            subject="hummingbird",
            action="hovering midair",
        )

        self.assertEqual(result["subject_match"], 100.0)
        self.assertEqual(result["action_match"], 100.0)
        self.assertEqual(_slot(result, "subject")["status"], "matched")
        self.assertEqual(_slot(result, "action")["status"], "matched")

    def test_live4_style_orca_title_remains_strong(self) -> None:
        result = _rank(
            _candidate(
                "pexels_orcas",
                provider="pexels",
                title="A pod of orcas swimming in the open ocean",
            ),
            subject="orcas",
        )

        self.assertEqual(result["subject_match"], 100.0)
        self.assertEqual(_slot(result, "subject")["status"], "matched")

    def test_coherent_metadata_outranks_provider_neutral_dispersed_prose(self) -> None:
        scene = SemanticScene(
            scene_id="scene_provider_neutral",
            subject=["glasswing butterfly"],
            source_class=CLASS_SPECIFIC_OBJECT,
        )
        dispersed = _candidate(
            "dispersed_generic",
            title="General natural history catalogue",
            description=(
                "Glasswing appears in an index entry. "
                + "unrelated archive prose " * 40
                + "A separate chapter describes butterfly migration."
            ),
        )
        coherent = _candidate(
            "coherent_generic",
            title="Glasswing butterfly resting on a green leaf",
        )

        ranked = rank_candidates(
            scene,
            [dispersed, coherent],
            source_class=scene.source_class,
        )

        self.assertEqual(ranked[0]["asset_id"], "coherent_generic")
        self.assertEqual(ranked[0]["subject_match"], 100.0)
        by_id = {item["asset_id"]: item for item in ranked}
        self.assertLess(by_id["dispersed_generic"]["subject_match"], 99.0)

    def test_metadata_fields_match_the_canonical_asset_contract(self) -> None:
        self.assertEqual(METADATA_FIELDS, ("title", "description"))
        evidence = build_evidence(
            {
                "categories": ["hummingbird"],
                "depicts": ["hummingbird"],
                "location": "open air",
            }
        )
        self.assertFalse(evidence.has_metadata)

    def test_provider_brand_does_not_change_semantic_or_final_score(self) -> None:
        scene = SemanticScene(
            scene_id="scene_provider_neutral_scores",
            subject=["hummingbird"],
            source_class=CLASS_SPECIFIC_OBJECT,
        )
        ranked = rank_candidates(
            scene,
            [
                _candidate("ia", provider="internet_archive", title="Hummingbird in flight"),
                _candidate("pexels", provider="pexels", title="Hummingbird in flight"),
            ],
            source_class=scene.source_class,
        )
        by_id = {item["asset_id"]: item for item in ranked}

        self.assertEqual(by_id["ia"]["subject_match"], by_id["pexels"]["subject_match"])
        self.assertEqual(by_id["ia"]["semantic_score"], by_id["pexels"]["semantic_score"])
        self.assertEqual(by_id["ia"]["final_score"], by_id["pexels"]["final_score"])
        self.assertNotEqual(by_id["ia"]["provider_confidence"], by_id["pexels"]["provider_confidence"])


if __name__ == "__main__":
    unittest.main()
