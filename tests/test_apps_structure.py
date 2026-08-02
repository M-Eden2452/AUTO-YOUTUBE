"""Test classification: LEGACY ANCHOR

Protects:
- существование переходных compatibility entrypoints в том виде, в каком они
  есть сегодня: импортируемость ``apps.news_to_short.main``,
  ``apps.youtube_pipeline.main``, ``apps.anime_factory.main`` и наличие файлов
  ``pipeline.py`` и ``anime_factory/pipeline.py``.

Does not prove:
- что эти entrypoints обещаны пользователю: канонический CLI —
  ``python -m ai_youtube``, а перечисленные пути являются compatibility
  wrappers с exit condition в реестре;
- что они работают: проверяется наличие атрибута ``main``, а не поведение;
- что этот модуль препятствует ретайру. Класс — LEGACY ANCHOR
  (``docs/current/CLEANUP_REGISTRY.md``, «Accidental invariants»): он
  переписывается в fitness-тест «нет второго canonical public CLI» и
  ретайрится вместе с wrapper'ами по gate PLAN-9B-5b / PLAN-L4 — что наступит
  раньше.
"""

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
