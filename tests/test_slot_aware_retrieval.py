"""Stage Q2.3: Slot-Aware Targeted Retrieval.

Composite assembly (stage Q2.2B) could only ever combine candidates the *general*
per-scene search happened to return. A scene whose general query is long (subject +
action + place combined) commonly gets fuzzy-matched results for only part of that
phrase, and there was nowhere to ask again for just the part that was missing.

This stage adds exactly one bounded, automatic step in ``draft_complete`` mode: once
composite assembly has a downloaded result that is not publish-ready, whichever
semantic slots (subject/action/location/context) it still could not answer get one
targeted query each - built only from the author's own English brief fields, never a
new translation - and the results are merged into the same pool before the ladder is
walked once more. Rights, technical, ``must_avoid`` and conflicting-context gates are
unchanged: a targeted result is just another candidate to the ladder, with no special
authority of its own.

Nothing here talks to a real network. ``SlotAwareFakeProvider`` stands in for a stock
provider and varies what it returns by the query text it receives, the same way
``FakeStockProvider`` already does for the rest of this test suite.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PIL import Image

from src.assets.query_adapter import (
    STATUS_OK,
    STATUS_TRANSLATION_REQUIRED,
    build_slot_queries,
)
from src.assets.completion import (
    ASSEMBLY_KEY,
    MODE_DRAFT_COMPLETE,
    SceneVisualAssembly,
    UsabilityVerdict,
    VisualSlot,
    unfilled_semantic_slots,
)
from src.providers.fake_provider import FakeStockProvider


# --- Pure unit tests: build_slot_queries -------------------------------------


class BuildSlotQueriesTests(unittest.TestCase):
    def _brief_scene(self, **overrides: object) -> dict:
        brief = {
            "subject": "scientist",
            "action": "collecting sample",
            "place": "Antarctic ice cave",
            "exact_entities": [],
            "must_include": ["snow"],
        }
        brief.update(overrides)
        return {"scene_id": "scene_001", "visual_brief": brief}

    def test_each_slot_draws_from_its_own_restricted_fields_only(self) -> None:
        scene = self._brief_scene()
        subject_query = build_slot_queries(scene, "subject", providers=["pexels"]).queries[0]
        action_query = build_slot_queries(scene, "action", providers=["pexels"]).queries[0]
        location_query = build_slot_queries(scene, "location", providers=["pexels"]).queries[0]
        context_query = build_slot_queries(scene, "context", providers=["pexels"]).queries[0]

        self.assertEqual(subject_query.query, "scientist")
        self.assertEqual(action_query.query, "scientist collecting sample")
        self.assertEqual(location_query.query, "Antarctic ice cave")
        self.assertEqual(context_query.query, "scientist snow")
        for item in (subject_query, action_query, location_query, context_query):
            self.assertEqual(item.status, STATUS_OK)
            self.assertTrue(item.kind.startswith("slot_"))

    def test_no_english_brief_terms_for_the_slot_is_translation_required_not_invented(self) -> None:
        scene = self._brief_scene(place="")

        plan = build_slot_queries(scene, "location", providers=["pexels"])

        self.assertEqual(plan.queries[0].status, STATUS_TRANSLATION_REQUIRED)
        self.assertEqual(plan.queries[0].query, "")
        self.assertIn("pexels", plan.untranslatable_providers)

    def test_provider_that_cannot_search_english_is_also_translation_required(self) -> None:
        scene = self._brief_scene()

        plan = build_slot_queries(
            scene,
            "subject",
            providers=["russian_only"],
            capabilities={"russian_only": {"query_languages": ["ru"]}},
        )

        self.assertEqual(plan.queries[0].status, STATUS_TRANSLATION_REQUIRED)

    def test_cyrillic_brief_fields_are_dropped_rather_than_smuggled_into_an_english_query(self) -> None:
        scene = self._brief_scene(subject="учёный", place="")

        plan = build_slot_queries(scene, "subject", providers=["pexels"])

        # Only "exact_entities" survives for the subject slot once "учёный" is
        # dropped for not being English; there are none here, so nothing is left.
        self.assertEqual(plan.queries[0].status, STATUS_TRANSLATION_REQUIRED)


# --- Pure unit tests: unfilled_semantic_slots ---------------------------------


def _slot(*, limitations: list[str], matched_slots: list[str] | None = None, slot_id: str = "slot_001") -> VisualSlot:
    usability = UsabilityVerdict(usable_in_draft=True, publish_ready=False, limitations=limitations)
    asset: dict = {"asset_id": slot_id}
    if matched_slots is not None:
        from src.assets.semantic_selection.decision import DECISION_KEY

        asset[DECISION_KEY] = {"slots": {"matched_slots": matched_slots}}
    return VisualSlot(slot_id=slot_id, selected_asset=asset, usability=usability)


class UnfilledSemanticSlotsTests(unittest.TestCase):
    def test_aggregates_missing_and_missing_required_across_slots_in_a_fixed_order(self) -> None:
        assembly = SceneVisualAssembly(
            scene_id="scene_001",
            scene_duration_sec=8.0,
            slots=[
                _slot(limitations=["missing_required:location", "crop_not_verified"]),
                _slot(limitations=["missing:action"]),
            ],
        )

        self.assertEqual(unfilled_semantic_slots(assembly), ["action", "location"])

    def test_publish_ready_assembly_has_nothing_left_to_ask_for(self) -> None:
        usability = UsabilityVerdict(usable_in_draft=True, publish_ready=True, limitations=[])
        assembly = SceneVisualAssembly(
            scene_id="scene_001",
            scene_duration_sec=8.0,
            slots=[VisualSlot(slot_id="slot_001", selected_asset={"asset_id": "a"}, usability=usability)],
        )

        self.assertEqual(unfilled_semantic_slots(assembly), [])

    def test_a_slot_kind_no_limitation_ever_names_is_not_reported(self) -> None:
        assembly = SceneVisualAssembly(
            scene_id="scene_001",
            scene_duration_sec=8.0,
            slots=[_slot(limitations=["missing:context"])],
        )

        self.assertEqual(unfilled_semantic_slots(assembly), ["context"])
        self.assertNotIn("subject", unfilled_semantic_slots(assembly))

    def test_a_slot_covered_by_its_sibling_is_not_reported_as_unfilled(self) -> None:
        """A location-only asset's own limitations always list "subject" as missing -
        that is true of *that one asset*, not of the scene. A sibling slot that
        actually matches subject must suppress it, or every two-slot composite would
        trigger a redundant targeted search for a slot it already has."""
        assembly = SceneVisualAssembly(
            scene_id="scene_001",
            scene_duration_sec=8.0,
            slots=[
                _slot(
                    slot_id="slot_001",
                    limitations=["missing_required:subject", "missing_required:action"],
                    matched_slots=["location"],
                ),
                _slot(
                    slot_id="slot_002",
                    limitations=["missing_required:action", "missing_required:location"],
                    matched_slots=["subject"],
                ),
            ],
        )

        self.assertEqual(unfilled_semantic_slots(assembly), ["action"])


# --- Integration: the full draft_complete pipeline ----------------------------


class SlotAwareFakeProvider(FakeStockProvider):
    """Returns different, query-dependent material - never real network access.

    Every general-search query variant (primary, alternative, context-fallback) that
    ``build_scene_queries`` builds for this fixture's brief contains "cave" - the place
    is part of all three. A fuzzy stock search asked any of them, real or fake,
    plausibly turns up the same *location*-relevant result every time and nothing
    *subject*-relevant, which is exactly what this fixture reproduces: any "cave"
    query returns the location-only candidate. Only a query that is exactly the bare
    subject term - the shape ``build_slot_queries`` builds for the "subject" slot, and
    that the general search never sends on its own - turns up the subject-relevant
    candidate. Anything else (the "action" slot's targeted query included) finds
    nothing new, standing in for a targeted search that genuinely does not help.
    """

    # Kept as the registered fixture provider name ("fake") from config/license_policy
    # .json - a name the license policy does not recognise is blocked as an unknown
    # provider before rights are even considered, which is the correct behaviour and
    # not something this test should work around.
    name = "fake"

    def __init__(self, *, fixture: Path) -> None:
        super().__init__(image_fixture=fixture)
        self.queries_received: list[str] = []

    def search(self, request):  # type: ignore[override]
        self.queries_received.append(request.query)
        query = request.query.lower().strip()
        if "cave" in query:
            return self._tagged(request, suffix="location", title="Antarctic ice cave interior",
                                 description="A frozen ice cave in Antarctica", tags=["antarctic", "ice", "cave"])
        if query == "scientist":
            return self._tagged(request, suffix="subject", title="Scientist portrait in laboratory",
                                 description="A researcher scientist standing indoors", tags=["scientist"])
        # The action slot's own targeted query, or anything else: nothing new to offer.
        return []

    def _tagged(self, request, *, suffix: str, title: str, description: str, tags: list[str]):
        candidates = super().search(request)
        for candidate in candidates:
            candidate.asset_id = f"{candidate.asset_id}_{suffix}"
            candidate.provider_asset_id = f"{candidate.provider_asset_id}_{suffix}"
            candidate.title = title
            candidate.description = description
            candidate.tags = list(tags)
        return candidates


def _exact_location_scene(**overrides: object) -> dict:
    scene = {
        "scene_id": "scene_001",
        "visual_type": "image",
        "target_duration_sec": 8.0,
        "visual_parts": ["a", "b"],
        "visual_brief": {
            "subject": "scientist",
            "action": "collecting sample",
            "place": "Antarctic ice cave",
            "source_class": "exact_location",
        },
        "semantic": {
            "subject": ["scientist"],
            "action": ["collecting sample"],
            "location": ["antarctic ice cave"],
            "context": [],
            "must_include": ["antarctic"],
            "must_not_include": [],
            "source_class": "exact_location",
        },
    }
    scene.update(overrides)
    return scene


class TargetedSlotRetrievalIntegrationTests(unittest.TestCase):
    def test_targeted_search_fills_a_slot_the_general_pool_alone_could_not(self) -> None:
        from src.news.asset_manager import build_assets_manifest

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture = root / "fixture.jpg"
            Image.new("RGB", (1080, 1920), (30, 60, 90)).save(fixture)
            provider = SlotAwareFakeProvider(fixture=fixture)
            visual_plan = {"scenes": [_exact_location_scene()], "intent_language": "ru", "language": "ru"}

            manifest = build_assets_manifest(
                visual_plan=visual_plan,
                user_assets=[],
                media_index={"version": 1, "items": []},
                providers=[provider],
                dry_run=False,
                completion_mode=MODE_DRAFT_COMPLETE,
                project_root=root / "project",
                project_id="project_001",
            )

            entry = manifest["scenes"][0]
            assembly = entry[ASSEMBLY_KEY]

            self.assertEqual(assembly["slot_count"], 2)
            titles = {slot["selected_asset"]["title"] for slot in assembly["slots"]}
            self.assertEqual(titles, {"Scientist portrait in laboratory", "Antarctic ice cave interior"})
            self.assertFalse(assembly["publish_ready"])
            self.assertTrue(assembly["usable_in_draft"])

            # The ladder's own audit trail says a targeted pass ran and which slots it
            # was for - the general pool by itself only ever returns duplicates of the
            # location-only candidate (every general query variant contains "cave"),
            # which cannot form a composite with itself.
            self.assertIn("Q2.3:targeted_slot_search:subject,action", assembly["ladder_trace"])

            # The bare "scientist" query only exists because ``build_slot_queries``
            # built it for the "subject" slot - the general search never sends the
            # subject term on its own, and rule 7 means it is sent exactly once even
            # though both a general query and the general search's own context-only
            # query already used "cave".
            self.assertEqual(provider.queries_received.count("scientist"), 1)
            self.assertEqual(provider.queries_received.count("Antarctic ice cave"), 1)

            # Rule 9: the slot a targeted search could not fill (action) is still
            # visible as unresolved rather than silently dropped.
            still_missing = {
                name
                for slot in assembly["slots"]
                for name in slot["usability"]["limitations"]
                if name.startswith("missing")
            }
            self.assertTrue(any("action" in item for item in still_missing))

    def test_targeted_search_runs_at_most_once_per_scene_even_with_several_missing_slots(self) -> None:
        from src.news.asset_manager import build_assets_manifest

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture = root / "fixture.jpg"
            Image.new("RGB", (1080, 1920), (30, 60, 90)).save(fixture)
            provider = SlotAwareFakeProvider(fixture=fixture)
            visual_plan = {"scenes": [_exact_location_scene()], "intent_language": "ru", "language": "ru"}

            manifest = build_assets_manifest(
                visual_plan=visual_plan,
                user_assets=[],
                media_index={"version": 1, "items": []},
                providers=[provider],
                dry_run=False,
                completion_mode=MODE_DRAFT_COMPLETE,
                project_root=root / "project",
                project_id="project_001",
            )

            # Every query actually sent is distinct - a targeted pass never repeats a
            # query the general search (or a previous slot in the same pass) already
            # sent (rules 6 and 7).
            self.assertEqual(len(provider.queries_received), len(set(provider.queries_received)))

            # Exactly one targeted-search pass is recorded, even though two slot kinds
            # (subject, action) were unfilled going into it - rule 10, not a retry loop.
            trace = manifest["scenes"][0][ASSEMBLY_KEY]["ladder_trace"]
            targeted_entries = [item for item in trace if item.startswith("Q2.3:targeted_slot_search:")]
            self.assertEqual(len(targeted_entries), 1)

    def test_a_rights_blocked_targeted_result_never_enters_the_accepted_assembly(self) -> None:
        from src.news.asset_manager import build_assets_manifest

        class BlockedRightsProvider(SlotAwareFakeProvider):
            def _tagged(self, request, *, suffix, title, description, tags):
                candidates = super()._tagged(request, suffix=suffix, title=title, description=description, tags=tags)
                if suffix == "subject":
                    # The candidate only stage Q2.3's targeted search ever finds here -
                    # blocking its rights must make it invisible to the accepted
                    # assembly exactly as it would for any other candidate.
                    # ``_search_provider`` re-applies the license policy after this
                    # method returns (``_candidate_to_rankable``), which recomputes
                    # ``license`` from ``license_name`` - setting the license fields
                    # directly would just be overwritten a second time, so the licence
                    # *name* itself is made unrecognisable instead.
                    for candidate in candidates:
                        candidate.license.license_name = "unknown"
                return candidates

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture = root / "fixture.jpg"
            Image.new("RGB", (1080, 1920), (30, 60, 90)).save(fixture)
            provider = BlockedRightsProvider(fixture=fixture)
            visual_plan = {"scenes": [_exact_location_scene()], "intent_language": "ru", "language": "ru"}

            manifest = build_assets_manifest(
                visual_plan=visual_plan,
                user_assets=[],
                media_index={"version": 1, "items": []},
                providers=[provider],
                dry_run=False,
                completion_mode=MODE_DRAFT_COMPLETE,
                project_root=root / "project",
                project_id="project_001",
            )

            assembly = manifest["scenes"][0][ASSEMBLY_KEY]
            titles = {slot["selected_asset"]["title"] for slot in assembly["slots"]}
            # The targeted search still ran and still found the subject candidate, but
            # its blocked rights must keep it out of the accepted assembly - the scene
            # falls back to the single location-only slot the general search found.
            self.assertIn("Q2.3:targeted_slot_search:subject,action", assembly["ladder_trace"])
            self.assertNotIn("Scientist portrait in laboratory", titles)
            self.assertEqual(assembly["slot_count"], 1)
            self.assertEqual(titles, {"Antarctic ice cave interior"})


class HalfOutageSlotProvider(FakeStockProvider):
    """Answers the image endpoint and is down for video - a real half-outage."""

    name = "fake"

    def __init__(self, *, fixture: Path, failing_media_type: str) -> None:
        super().__init__(image_fixture=fixture)
        self.failing_media_type = failing_media_type
        self.requested_media_types: list[str] = []

    def search(self, request):  # type: ignore[override]
        from src.assets.provider_contract import ProviderNetworkError

        self.requested_media_types.append(request.media_type)
        if request.media_type == self.failing_media_type:
            raise ProviderNetworkError(
                f"fake {request.media_type} endpoint is unavailable.",
                provider=self.name,
                query=request.query,
                retryable=True,
            )
        return super().search(request)


class TargetedSearchPartialMediaTests(unittest.TestCase):
    """VA-NEW-06 / M2-A at the second ``search_provider`` call site.

    ``targeted_slot_search`` asks the same provider through the same retrieval
    owner, so a mixed-kind targeted query loses its answered half in exactly the
    same way the general search did. It is wired to the real ``search_provider``
    and ``rank_provider_results`` here, the way production injects them.
    """

    def test_a_targeted_query_keeps_the_media_type_that_answered(self) -> None:
        from src.assets.semantic_selection import analyze_scene
        from src.news.asset_provider_adapters import (
            rank_provider_results,
            search_provider,
        )
        from src.news.asset_scene_completion import targeted_slot_search

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture = root / "fixture.jpg"
            Image.new("RGB", (1080, 1920), (30, 60, 90)).save(fixture)
            provider = HalfOutageSlotProvider(fixture=fixture, failing_media_type="video")
            scene = _exact_location_scene(allowed_media_kinds=["image", "video"])

            found, attempts = targeted_slot_search(
                scene=scene,
                semantic_scene=analyze_scene(scene),
                slot_names=["subject"],
                ordered_providers=[provider],
                provider_capabilities={provider.name: provider.capabilities().to_dict()},
                project_id="va_new_06_targeted",
                sent_queries=set(),
                rank_provider_results=rank_provider_results,
                search_provider=search_provider,
            )

            self.assertEqual(provider.requested_media_types, ["image", "video"])
            self.assertEqual([str(item["media_type"]) for item in found], ["image"])

            self.assertEqual(attempts[0]["status"], "completed")
            self.assertEqual(attempts[0]["result_count"], 1)
            self.assertEqual(
                [
                    (item["media_type"], item["status"])
                    for item in attempts[0]["media_attempts"]
                ],
                [("image", "completed"), ("video", "failed")],
            )


class StrictModeUnaffectedTests(unittest.TestCase):
    def test_strict_mode_never_triggers_a_targeted_search(self) -> None:
        from src.news.asset_manager import build_assets_manifest

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture = root / "fixture.jpg"
            Image.new("RGB", (1080, 1920), (30, 60, 90)).save(fixture)
            provider = SlotAwareFakeProvider(fixture=fixture)
            visual_plan = {"scenes": [_exact_location_scene()], "intent_language": "ru", "language": "ru"}

            build_assets_manifest(
                visual_plan=visual_plan,
                user_assets=[],
                media_index={"version": 1, "items": []},
                providers=[provider],
                dry_run=False,
                project_root=root / "project",
                project_id="project_001",
            )

            # The general per-scene search still runs its own (up to three) query
            # variants - that is unrelated to Q2.3 - but the bare, single-slot query
            # shapes ``build_slot_queries`` builds (targeted search only) must never
            # appear: strict mode never calls ``_complete_scene_assembly`` at all.
            self.assertNotIn("scientist", provider.queries_received)
            self.assertNotIn("scientist collecting sample", provider.queries_received)


if __name__ == "__main__":
    unittest.main()
