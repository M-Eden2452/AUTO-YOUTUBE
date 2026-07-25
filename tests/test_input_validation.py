from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.content_creation import input_validation


class ArticleUrlValidationTests(unittest.TestCase):
    def test_valid_article_url_passes(self) -> None:
        result = input_validation.validate_article_url("https://example.com/news/some-article")
        self.assertTrue(result.valid)

    def test_empty_url_rejected(self) -> None:
        result = input_validation.validate_article_url("")
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "empty")

    def test_bad_scheme_rejected(self) -> None:
        result = input_validation.validate_article_url("ftp://example.com/a")
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "bad_scheme")

    def test_google_search_url_rejected_before_network(self) -> None:
        result = input_validation.validate_article_url("https://www.google.com/search?q=crows+remember+faces")
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "search_engine_url")

    def test_bing_search_url_rejected(self) -> None:
        result = input_validation.validate_article_url("https://www.bing.com/search?q=test")
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "search_engine_url")

    def test_yandex_search_url_rejected(self) -> None:
        result = input_validation.validate_article_url("https://yandex.ru/search/?text=test")
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "search_engine_url")

    def test_duckduckgo_search_url_rejected(self) -> None:
        result = input_validation.validate_article_url("https://duckduckgo.com/?q=test")
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "search_engine_url")

    def test_google_non_search_path_is_not_rejected(self) -> None:
        # Only /search paths on google.* are treated as search-result URLs.
        result = input_validation.validate_article_url("https://news.google.com/articles/some-real-article")
        self.assertTrue(result.valid)

    def test_too_long_url_rejected(self) -> None:
        result = input_validation.validate_article_url("https://example.com/" + "a" * 3000)
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "too_long")


class ScriptFileValidationTests(unittest.TestCase):
    def test_missing_file_rejected(self) -> None:
        result = input_validation.validate_script_file("/no/such/file.txt")
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "not_found")

    def test_unsupported_extension_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "script.docx"
            path.write_text("hello", encoding="utf-8")
            result = input_validation.validate_script_file(str(path))
            self.assertFalse(result.valid)
            self.assertEqual(result.reason, "unsupported_extension")

    def test_valid_txt_file_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "script.txt"
            path.write_text("Текст сценария.", encoding="utf-8")
            result = input_validation.validate_script_file(str(path))
            self.assertTrue(result.valid)


class MusicPathValidationTests(unittest.TestCase):
    def test_empty_path_rejected(self) -> None:
        result = input_validation.validate_music_path("")
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "empty")

    def test_missing_file_rejected(self) -> None:
        result = input_validation.validate_music_path("/no/such/music.mp3")
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "not_found")

    def test_unsupported_extension_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "music.txt"
            path.write_text("not audio", encoding="utf-8")
            result = input_validation.validate_music_path(str(path))
            self.assertFalse(result.valid)
            self.assertEqual(result.reason, "unsupported_extension")

    def test_valid_mp3_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "music.mp3"
            path.write_bytes(b"\x00")
            result = input_validation.validate_music_path(str(path))
            self.assertTrue(result.valid)


class PastedScriptValidationTests(unittest.TestCase):
    def test_empty_rejected(self) -> None:
        result = input_validation.validate_pasted_script("   ")
        self.assertFalse(result.valid)

    def test_non_empty_accepted(self) -> None:
        result = input_validation.validate_pasted_script("Готовый текст сценария.")
        self.assertTrue(result.valid)


if __name__ == "__main__":
    unittest.main()
