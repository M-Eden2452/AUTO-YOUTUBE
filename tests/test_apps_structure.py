from __future__ import annotations

import importlib
import unittest
from pathlib import Path


class AppsStructureTests(unittest.TestCase):
    def test_apps_entrypoints_exist_without_moving_legacy_modules(self) -> None:
        for module_name in ("apps.news_to_short.main", "apps.youtube_pipeline.main", "apps.anime_factory.main"):
            module = importlib.import_module(module_name)
            self.assertTrue(hasattr(module, "main"))

        self.assertTrue(Path("pipeline.py").is_file())
        self.assertTrue(Path("anime_factory/pipeline.py").is_file())


if __name__ == "__main__":
    unittest.main()
