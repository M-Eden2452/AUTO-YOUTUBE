"""C125: a process no camera can film is a class of scene, not a banned candidate.

Owner decision of 2026-08-20, recorded in
[ADR 0026](../docs/adr/0026-scientific-visualization-source-class.md): scientific,
medical and technical animation is admissible for a scene whose subject cannot be
honestly filmed - neurons, brain activity, cells, molecules, processes inside the
body. Entertainment animation stays refused for every class.

Measured on the saved run before this slice: ``scene_008`` ("neural connections")
found ``abstract neural network connections animation`` with a semantic score of
**64.7** against a threshold of 60, and the only thing that rejected it was
``non_real_video_footage:animation``. The scene was left empty and the preview render
was blocked for having empty scenes.

No network, no paid calls: scene records in, class and verdict out.
"""

from __future__ import annotations

import unittest
from typing import Any

from src.assets.scene_strategy import (
    CLASS_GENERIC_BROLL,
    CLASS_SCIENTIFIC_VISUALIZATION,
    SOURCE_CLASSES,
    build_strategy,
    classify_scene,
)
from src.assets.semantic_selection import SemanticScene, rank_candidates

ALL_PROVIDERS = [
    "local_library", "pexels", "pixabay", "wikimedia", "nasa_images", "internet_archive",
]


def _scene(**kwargs: Any) -> dict[str, Any]:
    scene = {"scene_id": "scene_001", "narration": "", "visual_brief": {}}
    scene.update(kwargs)
    return scene


def _candidate(title: str, **kwargs: Any) -> dict[str, Any]:
    candidate = {
        "asset_id": "a1",
        "provider": "pixabay",
        "media_type": "video",
        "title": title,
        "description": "",
        "tags": [],
        "keywords": [],
        "duration_sec": 30.0,
        "width": 2160,
        "height": 3840,
        "allowed_for_render": True,
        "license": "pixabay",
    }
    candidate.update(kwargs)
    return candidate


class TheClassIsDeclaredBySubjectNotByNarration(unittest.TestCase):
    """What puts a scene into the class, and what deliberately does not."""

    def test_the_class_exists_in_the_catalogue(self) -> None:
        self.assertIn(CLASS_SCIENTIFIC_VISUALIZATION, SOURCE_CLASSES)

    def test_a_subject_no_camera_can_film_is_classified_as_visualization(self) -> None:
        for subject in (
            "neurons", "нейронные связи", "a single cell", "molecule", "human brain",
        ):
            with self.subTest(subject=subject):
                scene = _scene(visual_brief={"subject": subject})
                self.assertEqual(
                    classify_scene(scene)[0], CLASS_SCIENTIFIC_VISUALIZATION
                )

    def test_a_passing_mention_in_the_narration_does_not_reclassify_the_scene(
        self,
    ) -> None:
        """The alarm clock scene says "гормон" out loud and is still an alarm clock.

        Read from the declared subject only. ``_evidence_text`` includes narration,
        and classifying on it would move a filmable scene into a class that relaxes
        the footage rule for a word the shot is not about.
        """

        scene = _scene(
            narration="В глубоком сне организм выбрасывает гормон роста.",
            visual_brief={"subject": "alarm clock at night", "place": "bedside table"},
        )
        self.assertEqual(classify_scene(scene)[0], CLASS_GENERIC_BROLL)

    def test_the_author_can_still_declare_the_class_outright(self) -> None:
        scene = _scene(visual_brief={"source_class": CLASS_SCIENTIFIC_VISUALIZATION})
        source_class, _, origin = classify_scene(scene)
        self.assertEqual(source_class, CLASS_SCIENTIFIC_VISUALIZATION)
        self.assertEqual(origin, "visual_brief")

    def test_the_class_has_a_provider_order_like_every_other_class(self) -> None:
        strategy = build_strategy(
            _scene(visual_brief={"subject": "neurons"}), available_providers=ALL_PROVIDERS
        )
        self.assertEqual(strategy.source_class, CLASS_SCIENTIFIC_VISUALIZATION)
        self.assertTrue(strategy.provider_order)


class WhatTheClassChangesAboutFootage(unittest.TestCase):
    """One rule moves, and only for this class."""

    SCENE = SemanticScene(
        scene_id="scene_008",
        subject=["neural connections"],
        action=["signals travelling"],
        environment=["abstract dark space"],
        source_class=CLASS_SCIENTIFIC_VISUALIZATION,
    )
    FILMABLE = SemanticScene(
        scene_id="scene_001",
        subject=["sleeping woman"],
        action=["sleeping"],
        source_class=CLASS_GENERIC_BROLL,
    )

    def _reasons(self, scene: SemanticScene, title: str) -> list[str]:
        ranked = rank_candidates(scene, [_candidate(title)])
        return list(ranked[0].get("blocking_reject_reasons") or [])

    def test_scientific_animation_is_no_longer_refused_for_this_class(self) -> None:
        reasons = self._reasons(
            self.SCENE, "abstract neural network connections animation"
        )
        self.assertFalse([r for r in reasons if r.startswith("non_real_video_footage")])

    def test_entertainment_animation_stays_refused_for_this_class(self) -> None:
        for title in (
            "Toopy and Binoo cartoon episode",
            "Disney neural network short",
            "neuron gameplay walkthrough",
        ):
            with self.subTest(title=title):
                reasons = self._reasons(self.SCENE, title)
                self.assertTrue(
                    [r for r in reasons if r.startswith("non_real_video_footage")],
                    reasons,
                )

    def test_a_filmable_scene_still_refuses_animation(self) -> None:
        reasons = self._reasons(self.FILMABLE, "sleeping woman animation")
        self.assertTrue(
            [r for r in reasons if r.startswith("non_real_video_footage")], reasons
        )


if __name__ == "__main__":
    unittest.main()
