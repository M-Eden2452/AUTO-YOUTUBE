"""Контракт раскладки репозитория.

Тест владеет одним фактом: где канонический код ищет versioned-конфигурацию и
исходные медиа. Раскладка — часть контракта путей
(``src/config_resolver/paths.py``), а не деталь оформления: каталог переезжает
вместе с этим файлом, а не молча на диске.

Медиа и `media_index.json` в истории не лежат (`.gitignore`), поэтому проверки
содержимого пропускаются, когда файла нет: тест обязан быть зелёным на свежем
клоне.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from src.config_resolver.paths import resolve_application_paths

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
MEDIA_INDEX = REPOSITORY_ROOT / "assets" / "library" / "metadata" / "media_index.json"
VIDEO_STYLE = REPOSITORY_ROOT / "config" / "video_style.json"


class MusicLocationTests(unittest.TestCase):
    """Исходная музыка — медиа, а значит живёт в `assets/`, а не в корне."""

    def test_path_contract_resolves_music_under_assets(self) -> None:
        music = resolve_application_paths().workspace.music
        self.assertEqual(music, (REPOSITORY_ROOT / "assets" / "music").resolve())

    def test_repository_root_has_no_separate_music_directory(self) -> None:
        self.assertFalse(
            (REPOSITORY_ROOT / "music").exists(),
            "Корневой music/ ретайрен: единственный источник — assets/music.",
        )

    def test_legacy_video_style_points_at_the_moved_music_bed(self) -> None:
        """`config/video_style.json` ещё жив (умирает в PLAN-L3) и обязан не лгать."""
        style = json.loads(VIDEO_STYLE.read_text(encoding="utf-8"))
        declared = [style.get("music_path", "")]
        declared.append(style.get("music_search", {}).get("fallback_path", ""))
        for value in declared:
            with self.subTest(path=value):
                self.assertTrue(
                    value.startswith("assets/music/"),
                    f"Путь музыки {value!r} обязан вести в assets/music/.",
                )


class MediaIndexLocationTests(unittest.TestCase):
    """Индекс библиотеки не должен указывать наружу из `assets/`."""

    def test_every_indexed_asset_lives_under_assets(self) -> None:
        if not MEDIA_INDEX.is_file():
            self.skipTest("media_index.json не versioned — на свежем клоне его нет.")
        items = json.loads(MEDIA_INDEX.read_text(encoding="utf-8")).get("items", [])
        self.assertTrue(items, "Пустой индекс делает проверку бессмысленной.")
        assets_root = (REPOSITORY_ROOT / "assets").resolve()
        for item in items:
            local_path = str(item.get("local_path") or "")
            with self.subTest(asset=item.get("id", local_path)):
                resolved = Path(local_path.replace("\\", "/")).resolve()
                self.assertTrue(
                    resolved.is_relative_to(assets_root),
                    f"Запись индекса ведёт вне assets/: {local_path!r}.",
                )


if __name__ == "__main__":
    unittest.main()
