"""One vocabulary decides which rights statuses exist; nobody keeps a second copy.

PLAN-STAB-9. Until this slice the four allowed ``rights_status`` strings were
declared twice - ``RIGHTS_ALLOWED_STATUSES`` in ``src.assets.models`` and
``ALLOWED_RENDER_RIGHTS`` in ``src.news.models`` - as two independent mutable
sets that happened to agree. Nothing failed if they stopped agreeing, and the
news copy is the one that decides ``allowed_for_render`` for local-library
records and provider results.

``src.assets.models`` is now the canonical owner. ``src.news.models`` keeps every
historical name importable, but as re-exports of that owner rather than a second
declaration, so the old import paths still work and cannot drift.

These tests pin two separate things:

- the *vocabulary*: one canonical set, one sanctioned extension, and everything
  outside it fail-closed - unknown, missing and legacy statuses all block;
- the *invariant that there is only one copy*: identity of the alias, identity
  of each re-exported name, and a source-level check that no set literal in
  ``src.news.models`` has quietly grown back into a second dictionary.

What these tests deliberately do not claim: that a canonical status is by itself
permission. It never is. ``review_required``, ``allowed_for_render`` and the
licence policy each keep their own veto, and that is asserted here too.

Offline: synthetic records only, no provider, no network, no real asset.
"""

from __future__ import annotations

import ast
import unittest
from pathlib import Path

from src.assets.completion.modes import (
    _ALLOWED_RIGHTS_STATUSES,
    _rights_are_allowed,
)
from src.assets.license_policy import (
    RECORD_REVIEW_REQUIRED_REASON,
    evaluate_asset_policy,
)
from src.assets.models import (
    RIGHTS_ALLOWED_STATUSES,
    RIGHTS_BLOCKED,
    RIGHTS_CREATIVE_COMMONS,
    RIGHTS_EDITORIAL_REVIEW_REQUIRED,
    RIGHTS_LEGACY_CLEARED,
    RIGHTS_LICENSED,
    RIGHTS_PUBLIC_DOMAIN,
    RIGHTS_REFERENCE_ONLY,
    RIGHTS_USER_OWNED,
    AssetCandidate,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
NEWS_MODELS_SOURCE = REPOSITORY_ROOT / "src" / "news" / "models.py"

SOURCE = "https://example.invalid/library/asset"
UNKNOWN_STATUS = "totally_made_up_status"

# The four spellings this repository accepts, written out rather than imported,
# so that widening the canonical set has to be a deliberate edit here as well.
EXPECTED_ALLOWED = {"user_owned", "licensed", "creative_commons", "public_domain"}

# Every historical name src.news.models used to declare itself.
HISTORICAL_NAMES = (
    "RIGHTS_USER_OWNED",
    "RIGHTS_LICENSED",
    "RIGHTS_CREATIVE_COMMONS",
    "RIGHTS_PUBLIC_DOMAIN",
    "RIGHTS_EDITORIAL_REVIEW_REQUIRED",
    "RIGHTS_REFERENCE_ONLY",
    "RIGHTS_BLOCKED",
)


def _permissive_policy() -> dict:
    """A policy that allows the licence outright, so only rights fields can block."""

    return {
        "policy_version": "test-policy",
        "policy_reviewed_date": "2026-08-06",
        "default_decision": {},
        "providers": {
            "local_library": {
                "enabled": True,
                "owner_review_required": False,
                "owner_approval_status": "approved",
                "rules": [
                    {
                        "media_type": "*",
                        "license_name": "user_owned",
                        "allowed_for_render": True,
                        "review_required": False,
                    }
                ],
            }
        },
    }


def _record(status: str, **overrides) -> dict:
    """A structurally complete record whose only open question is its status."""

    record = {
        "schema_version": 1,
        "asset_id": "local_asset",
        "provider": "local_library",
        "provider_asset_id": "local_asset",
        "type": "video",
        "media_type": "video",
        "local_path": "assets/library/videos/asset.mp4",
        "source_url": SOURCE,
        "source_page_url": SOURCE,
        # Only the licence name lives here: the rights fields stay at the root so
        # the record carries exactly one statement about them.
        "license": {"license_name": "user_owned"},
        "rights_status": status,
        "allowed_for_render": True,
        "review_required": False,
        "provenance": {"provider": "local_library", "source_page_url": SOURCE},
        "width": 1080,
        "height": 1920,
    }
    record.update(overrides)
    return record


def _news_rights(status: str):
    from src.news.models import AssetRights

    return AssetRights(asset_id="asset_001", rights_status=status)


class CanonicalVocabularyTests(unittest.TestCase):
    """What the canonical set contains, and what it refuses to contain."""

    def test_the_canonical_set_is_exactly_the_four_expected_statuses(self) -> None:
        self.assertEqual(set(RIGHTS_ALLOWED_STATUSES), EXPECTED_ALLOWED)

    def test_the_canonical_set_is_immutable(self) -> None:
        """It is handed to every consumer; one importer must not be able to move it."""
        self.assertIsInstance(RIGHTS_ALLOWED_STATUSES, frozenset)

    def test_non_render_statuses_are_not_in_the_canonical_set(self) -> None:
        """Disjointness, stated once, where both halves of the vocabulary live."""
        for status in (
            RIGHTS_REFERENCE_ONLY,
            RIGHTS_BLOCKED,
            RIGHTS_EDITORIAL_REVIEW_REQUIRED,
            RIGHTS_LEGACY_CLEARED,
        ):
            with self.subTest(status=status):
                self.assertNotIn(status, RIGHTS_ALLOWED_STATUSES)

    def test_every_canonical_status_is_allowed_when_nothing_else_blocks(self) -> None:
        """Scenario 1: the vocabulary admits all four, not a subset."""
        for status in sorted(RIGHTS_ALLOWED_STATUSES):
            with self.subTest(status=status):
                self.assertTrue(_rights_are_allowed(_record(status)))
                self.assertTrue(_news_rights(status).allowed_for_render)

    def test_an_unknown_status_is_blocked_everywhere(self) -> None:
        """Scenario 2: a status nobody declared is not silently normalised to allowed."""
        self.assertNotIn(UNKNOWN_STATUS, RIGHTS_ALLOWED_STATUSES)
        self.assertFalse(_rights_are_allowed(_record(UNKNOWN_STATUS)))
        self.assertFalse(_news_rights(UNKNOWN_STATUS).allowed_for_render)

    def test_a_missing_or_empty_status_is_blocked(self) -> None:
        """Scenario 3: absence is not permission, in any of its spellings."""
        for status in ("", "   "):
            with self.subTest(status=repr(status)):
                self.assertFalse(_news_rights(status).allowed_for_render)

        # No status at all: a positive allowed_for_render is not a substitute for
        # one, so the gate still refuses.
        missing = _record(RIGHTS_USER_OWNED)
        del missing["rights_status"]
        self.assertFalse(_rights_are_allowed(missing))

        self.assertFalse(_rights_are_allowed(_record(RIGHTS_USER_OWNED, rights_status=None)))


class StatusIsNotPermissionTests(unittest.TestCase):
    """A canonical status still has to get past every other gate."""

    def test_review_required_blocks_a_canonical_status(self) -> None:
        """Scenario 4: the render gate and the policy both refuse it."""
        for status in sorted(RIGHTS_ALLOWED_STATUSES):
            with self.subTest(status=status):
                flagged = _record(status, review_required=True)

                self.assertFalse(_rights_are_allowed(flagged))

                decision = evaluate_asset_policy(flagged, policy=_permissive_policy())
                self.assertTrue(decision.review_required)
                self.assertFalse(decision.allowed_for_render)
                self.assertEqual(decision.status, "blocked")
                self.assertIn(RECORD_REVIEW_REQUIRED_REASON, decision.reason)

    def test_allowed_for_render_false_blocks_a_canonical_status(self) -> None:
        """Scenario 5: an explicit refusal is not overridden by a good status."""
        for status in sorted(RIGHTS_ALLOWED_STATUSES):
            with self.subTest(status=status):
                refused = _record(status, allowed_for_render=False)
                self.assertFalse(_rights_are_allowed(refused))

    def test_a_confirmed_declaration_does_not_excuse_a_structurally_incomplete_asset(
        self,
    ) -> None:
        """Scenario 11: owner confirmation answers rights, not missing provenance."""
        incomplete = _record(RIGHTS_USER_OWNED)
        incomplete["provider"] = "user"
        del incomplete["provider_asset_id"]
        incomplete["source_url"] = ""
        incomplete["source_page_url"] = ""
        incomplete["provenance"] = {}
        incomplete["rights_declaration"] = {
            "confirmed": True,
            "owner_approval_status": "approved",
        }

        decision = evaluate_asset_policy(incomplete, policy=_permissive_policy())

        self.assertFalse(decision.allowed_for_render)
        self.assertEqual(decision.status, "blocked")
        self.assertIn("missing_source", decision.reason)

    def test_the_monotonic_review_invariant_still_holds(self) -> None:
        """Scenario 12: PLAN-STAB-5 - automation may add a review, never remove one."""
        flagged = _record(
            RIGHTS_USER_OWNED,
            review_required=True,
            license={
                "license_name": "user_owned",
                "rights_status": RIGHTS_USER_OWNED,
                "allowed_for_render": True,
                "review_required": True,
            },
        )

        first = evaluate_asset_policy(flagged, policy=_permissive_policy())
        self.assertTrue(first.review_required)
        self.assertIn(RECORD_REVIEW_REQUIRED_REASON, first.reason)

        # Re-evaluating is not a way to launder the flag.
        again = evaluate_asset_policy(flagged, policy=_permissive_policy())
        self.assertTrue(again.review_required)
        self.assertFalse(again.allowed_for_render)


class OwnerAndConsumersAgreeTests(unittest.TestCase):
    """Scenario 6: one verdict, whichever owner is asked."""

    def test_policy_and_render_gate_agree_on_the_same_record(self) -> None:
        """Both owners read one record and reach one verdict, per status.

        The record states its rights the way the models derive them - a status
        outside the vocabulary is not cleared for render and therefore carries a
        review requirement - so the two readers are being asked the same question.
        """
        for status in sorted(RIGHTS_ALLOWED_STATUSES) + [UNKNOWN_STATUS]:
            with self.subTest(status=status):
                expected = status in RIGHTS_ALLOWED_STATUSES
                record = _record(
                    status,
                    allowed_for_render=expected,
                    review_required=not expected,
                )

                decision = evaluate_asset_policy(record, policy=_permissive_policy())

                self.assertEqual(_rights_are_allowed(record), expected)
                self.assertEqual(_news_rights(status).allowed_for_render, expected)
                self.assertEqual(decision.allowed_for_render, expected)
                self.assertEqual(decision.review_required, not expected)

    def test_the_ranker_verdict_is_interim_and_the_licence_policy_decides(self) -> None:
        """Characterization: in the news path the vocabulary answer is not the last word.

        ``rank_provider_results`` computes ``allowed_for_render`` from the
        vocabulary and then hands the candidate to ``with_policy_decision``,
        which replaces the rights fields - including ``rights_status`` itself -
        with the licence policy's answer. This is the behaviour CLEANUP_REGISTRY
        records as C40 ("значение перезаписывается политикой"), and it is pinned
        here so the shared vocabulary is not mistaken for the render authority.
        """
        from src.news.asset_provider_adapters import rank_provider_results

        scene = {"primary_query": "city skyline", "visual_type": "video"}

        for status in (RIGHTS_USER_OWNED, UNKNOWN_STATUS):
            with self.subTest(status=status):
                raw = {
                    "schema_version": 1,
                    "asset_id": "provider_asset",
                    "provider": "local_library",
                    "provider_asset_id": "provider_asset",
                    "media_type": "video",
                    "source_page_url": SOURCE,
                    "license": "user_owned",
                    "rights_status": status,
                    "width": 1080,
                    "height": 1920,
                }
                ranked = rank_provider_results([raw], scene)[0]

                self.assertEqual(
                    ranked["allowed_for_render"],
                    ranked["policy_decision"]["allowed_for_render"],
                )
                self.assertEqual(
                    ranked["review_required"],
                    ranked["policy_decision"]["review_required"],
                )
                # The policy rewrites the status too, so the interim spelling
                # never reaches a manifest unreviewed.
                self.assertIn(ranked["rights_status"], {"licensed", "review_required"})

    def test_two_assets_in_one_batch_do_not_contaminate_each_other(self) -> None:
        """Scenario 9: one blocked asset is not a reason to block its neighbour."""
        allowed = _record(RIGHTS_USER_OWNED, asset_id="good")
        blocked = _record(UNKNOWN_STATUS, asset_id="bad")

        verdicts = [_rights_are_allowed(item) for item in (allowed, blocked, allowed)]

        self.assertEqual(verdicts, [True, False, True])


class SerializationTests(unittest.TestCase):
    """A stored status means the same thing after a round trip as before it."""

    def test_round_trip_preserves_every_status_verbatim(self) -> None:
        """Scenario 7: serialization is not a place where a status changes meaning.

        Both directions matter: an allowed status must not be downgraded on the
        way out, and an unknown one must not be normalised into something the
        vocabulary recognises on the way back in.
        """
        for status in sorted(RIGHTS_ALLOWED_STATUSES) + [
            UNKNOWN_STATUS,
            RIGHTS_REFERENCE_ONLY,
            RIGHTS_LEGACY_CLEARED,
            "legacy_unknown",
        ]:
            with self.subTest(status=status):
                original = AssetCandidate.from_dict(
                    _record(
                        status,
                        license={
                            "license_name": "user_owned",
                            "rights_status": status,
                            "allowed_for_render": status in RIGHTS_ALLOWED_STATUSES,
                            "review_required": status not in RIGHTS_ALLOWED_STATUSES,
                        },
                    )
                )
                self.assertEqual(original.license.rights_status, status)

                restored = AssetCandidate.from_dict(original.to_dict())

                self.assertEqual(restored.license.rights_status, status)
                self.assertEqual(restored.to_manifest_dict()["rights_status"], status)
                self.assertEqual(
                    restored.license.allowed_for_render,
                    status in RIGHTS_ALLOWED_STATUSES,
                )

    def test_a_legacy_manifest_without_rights_fields_stays_fail_closed(self) -> None:
        """Scenario 8: an old record is still readable, and still not permission."""
        legacy = {
            "provider": "pexels",
            "title": "old asset",
            "path": "assets/library/videos/old.mp4",
        }

        candidate = AssetCandidate.from_dict(legacy)

        self.assertEqual(candidate.schema_version, 0)
        self.assertEqual(candidate.license.rights_status, "legacy_unknown")
        self.assertNotIn(candidate.license.rights_status, RIGHTS_ALLOWED_STATUSES)
        self.assertFalse(candidate.license.allowed_for_render)
        self.assertTrue(candidate.license.review_required)
        self.assertFalse(_rights_are_allowed(candidate.to_manifest_dict()))


class NoSecondCopyTests(unittest.TestCase):
    """The divergence test PLAN-STAB-9 requires: copies must fail, names must not.

    The historical ``src.news.models`` import paths are kept on purpose, so the
    check is not "the name is gone" but "the name is the owner's object".
    """

    def test_the_news_alias_is_the_canonical_object_not_an_equal_copy(self) -> None:
        import src.news.models as news_models

        self.assertIs(news_models.ALLOWED_RENDER_RIGHTS, RIGHTS_ALLOWED_STATUSES)

    def test_every_historical_name_is_a_re_export(self) -> None:
        import src.assets.models as assets_models
        import src.news.models as news_models

        for name in HISTORICAL_NAMES:
            with self.subTest(name=name):
                self.assertIs(
                    getattr(news_models, name), getattr(assets_models, name)
                )

    def test_news_models_declares_no_vocabulary_set_of_its_own(self) -> None:
        """Source-level: a re-export may not grow back into a second dictionary.

        Identity checks above pass for a re-export today, but they would keep
        passing if someone added a *separate* set literal beside them. This reads
        the module and refuses any set/frozenset whose members are rights
        statuses, whether spelled as strings or as ``RIGHTS_*`` references.
        """
        tree = ast.parse(NEWS_MODELS_SOURCE.read_text(encoding="utf-8"))
        forbidden = set(RIGHTS_ALLOWED_STATUSES) | set(HISTORICAL_NAMES)

        offenders: list[int] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Set):
                elements = node.elts
            elif (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id in {"set", "frozenset"}
            ):
                elements = [
                    element
                    for argument in node.args
                    for element in getattr(argument, "elts", [])
                ]
            else:
                continue

            members = {
                element.value
                for element in elements
                if isinstance(element, ast.Constant) and isinstance(element.value, str)
            } | {
                element.id for element in elements if isinstance(element, ast.Name)
            }
            if members & forbidden:
                offenders.append(node.lineno)

        self.assertEqual(
            offenders,
            [],
            f"src/news/models.py declares a rights vocabulary set at lines {offenders}; "
            "the canonical owner is src.assets.models",
        )

    def test_the_completion_gate_extends_the_vocabulary_by_exactly_one_status(
        self,
    ) -> None:
        """The story-card ``cleared`` spelling is the only sanctioned extension."""
        self.assertEqual(
            _ALLOWED_RIGHTS_STATUSES,
            RIGHTS_ALLOWED_STATUSES | {RIGHTS_LEGACY_CLEARED},
        )

    def test_the_news_consumers_accept_exactly_the_canonical_set(self) -> None:
        """No consumer quietly recognises a status the canonical vocabulary does not."""
        candidates = sorted(
            EXPECTED_ALLOWED
            | {
                UNKNOWN_STATUS,
                RIGHTS_REFERENCE_ONLY,
                RIGHTS_BLOCKED,
                RIGHTS_EDITORIAL_REVIEW_REQUIRED,
                RIGHTS_LEGACY_CLEARED,
                "legacy_unknown",
                "unconfirmed",
                "review_required",
            }
        )

        accepted = {status for status in candidates if _news_rights(status).allowed_for_render}

        self.assertEqual(accepted, EXPECTED_ALLOWED)

    def test_the_historical_import_path_still_works(self) -> None:
        """Backwards compatibility is part of the contract, not an accident."""
        from src.news.models import (  # noqa: F401 - the import itself is the assertion
            ALLOWED_RENDER_RIGHTS,
            RIGHTS_BLOCKED as NEWS_BLOCKED,
            RIGHTS_CREATIVE_COMMONS as NEWS_CREATIVE_COMMONS,
            RIGHTS_EDITORIAL_REVIEW_REQUIRED as NEWS_EDITORIAL,
            RIGHTS_LICENSED as NEWS_LICENSED,
            RIGHTS_PUBLIC_DOMAIN as NEWS_PUBLIC_DOMAIN,
            RIGHTS_REFERENCE_ONLY as NEWS_REFERENCE_ONLY,
            RIGHTS_USER_OWNED as NEWS_USER_OWNED,
        )

        self.assertEqual(NEWS_USER_OWNED, RIGHTS_USER_OWNED)
        self.assertEqual(NEWS_LICENSED, RIGHTS_LICENSED)
        self.assertEqual(NEWS_CREATIVE_COMMONS, RIGHTS_CREATIVE_COMMONS)
        self.assertEqual(NEWS_PUBLIC_DOMAIN, RIGHTS_PUBLIC_DOMAIN)
        self.assertEqual(NEWS_EDITORIAL, RIGHTS_EDITORIAL_REVIEW_REQUIRED)
        self.assertEqual(NEWS_REFERENCE_ONLY, RIGHTS_REFERENCE_ONLY)
        self.assertEqual(NEWS_BLOCKED, RIGHTS_BLOCKED)
        self.assertEqual(ALLOWED_RENDER_RIGHTS, EXPECTED_ALLOWED)


if __name__ == "__main__":
    unittest.main()
