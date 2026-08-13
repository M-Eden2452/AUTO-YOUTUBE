from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.config_resolver.paths import repository_path
from tools.library.curated_index import check_structure, load_manifest, policy_decision

PROVIDER_DOMAINS = {"pexels": "pexels.com", "pixabay": "pixabay.com"}


class CuratedLibraryManifestTests(unittest.TestCase):
    """Инварианты versioned манифеста медиатеки. Сами медиафайлы здесь не читаются:
    они не versioned и в CI отсутствуют, поэтому проверяется запись, а не файл."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = load_manifest()
        cls.items = cls.manifest["items"]

    def test_every_record_is_structurally_complete(self) -> None:
        broken = {item.get("id"): check_structure(item) for item in self.items}
        self.assertEqual({key: value for key, value in broken.items() if value}, {})
        self.assertTrue(self.items)

    def test_ids_and_files_are_unique(self) -> None:
        ids = [item["id"] for item in self.items]
        files = [item["file"].lower() for item in self.items]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(files), len(set(files)))

    def test_source_page_belongs_to_the_declared_provider(self) -> None:
        for item in self.items:
            with self.subTest(item["id"]):
                domain = PROVIDER_DOMAINS[item["provider"]]
                self.assertIn(domain, item["source_page_url"])
                self.assertIn(item["provider_asset_id"], item["source_page_url"])
                self.assertEqual(item["license_name"], item["provider"])

    def test_provenance_evidence_points_at_a_file_that_exists(self) -> None:
        for item in self.items:
            with self.subTest(item["id"]):
                evidence = repository_path(*item["provenance_evidence"].split("/"))
                self.assertTrue(evidence.exists(), f"missing evidence: {item['provenance_evidence']}")

    def test_content_description_is_not_the_search_query(self) -> None:
        """Дефект, ради которого писался манифест: метаданные описывали запрос, а не кадр."""
        for item in self.items:
            with self.subTest(item["id"]):
                self.assertTrue(item["content_ru"].strip())
                self.assertNotEqual(item["content_ru"].strip().lower(), item.get("search_query", "").strip().lower())

    def test_upgraded_renditions_do_not_borrow_another_renditions_url(self) -> None:
        for item in self.items:
            with self.subTest(item["id"]):
                if item.get("rendition_note"):
                    self.assertEqual(item["download_url"], "")
                elif item["download_url"]:
                    self.assertIn(item["provider_asset_id"], item["download_url"])

    def test_records_are_allowed_for_internal_production(self) -> None:
        """Owner decision 2026-08-14: локальная медиатека отдаёт сток на тех же правилах,
        что и сам провайдер. Любая причина отказа здесь означает, что запись потеряла
        провенанс или права, — это регрессия, а не ужесточение политики."""
        for item in self.items:
            with self.subTest(item["id"]):
                decision = policy_decision(item, context="internal_content_production")
                self.assertEqual(decision.status, "allowed", decision.reason)
                self.assertEqual(decision.reason, "policy_rule_allowed")

    def test_stock_records_stay_held_for_a_public_multi_user_product(self) -> None:
        """Зеркало правил провайдеров распространяется и на запрет: публичный
        мультипользовательский контекст остаётся закрытым до коммерческого аудита."""
        for item in self.items:
            with self.subTest(item["id"]):
                decision = policy_decision(item, context="public_multi_user_product")
                self.assertNotEqual(decision.status, "allowed")
                self.assertFalse(decision.allowed_for_render)


class CuratedRecordRoundTripTests(unittest.TestCase):
    def test_curated_record_survives_the_index_and_stays_a_current_safe_record(self) -> None:
        from src.providers.local_library_provider import _is_current_safe_record
        from tools.library.curated_index import apply

        item = load_manifest()["items"][0]
        with TemporaryDirectory() as tmp:
            index_path = Path(tmp) / "media_index.json"
            apply({"items": [item]}, index_path=index_path, library_root=Path(tmp))
            stored = json.loads(index_path.read_text(encoding="utf-8"))["items"][0]

        self.assertTrue(_is_current_safe_record(stored))
        self.assertEqual(stored["description"], item["content_ru"])
        self.assertEqual(stored["checksum_sha256"], item["checksum_sha256"])
        self.assertEqual(stored["license"]["license_name"], item["license_name"])
        self.assertEqual(stored["provenance"]["source_page_url"], item["source_page_url"])
        self.assertEqual(stored["curation_status"], "curated")
        self.assertIn(item["keywords_en"][0], stored["keywords"])


if __name__ == "__main__":
    unittest.main()
