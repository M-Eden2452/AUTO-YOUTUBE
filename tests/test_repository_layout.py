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


class ChannelsLocationTests(unittest.TestCase):
    """Профиль канала — versioned-конфигурация, а не runtime-данные."""

    def test_path_contract_resolves_channels_under_config(self) -> None:
        root = resolve_application_paths().channels_root
        self.assertEqual(root, (REPOSITORY_ROOT / "config" / "channels").resolve())

    def test_repository_root_has_no_separate_channels_directory(self) -> None:
        self.assertFalse(
            (REPOSITORY_ROOT / "channels").exists(),
            "Корневой channels/ переехал: единственный корень — config/channels.",
        )

    def test_active_channels_are_discoverable_at_the_new_root(self) -> None:
        """Активные каналы versioned (`Preserved runtime corpus`) и обязаны пережить переезд."""
        root = resolve_application_paths().channels_root
        for channel_id in ("nature_science_news_ru", "nature_pulse"):
            with self.subTest(channel=channel_id):
                directory = root / channel_id
                self.assertTrue(directory.is_dir(), f"Канал {channel_id} потерян при переезде.")
                self.assertTrue(
                    (directory / "channel_config.json").is_file()
                    or (directory / "channel.json").is_file(),
                    f"У канала {channel_id} нет ни одного профиля.",
                )


class ChannelStyleResolutionTests(unittest.TestCase):
    """Стиль канала обязан находиться по контракту путей, а не по текущему каталогу.

    До переезда `src/news/subtitles.py` объявлял `channels_dir="channels"` — строку
    относительно cwd, которую канонический пайплайн (`src/news/pipeline.py:669`) не
    переопределяет. Совпадение с реальным каталогом держалось на том, что процесс
    запускали из корня репозитория.
    """

    def test_channel_subtitle_style_is_found_from_any_working_directory(self) -> None:
        import os
        import tempfile

        from src.subtitles.style import resolve_subtitle_style

        previous = Path.cwd()
        with tempfile.TemporaryDirectory() as elsewhere:
            os.chdir(elsewhere)
            try:
                style = resolve_subtitle_style(channel_id="nature_science_news_ru")
            finally:
                os.chdir(previous)
        self.assertEqual(style.font_size, 64, "Стиль канала не найден вне корня репозитория.")

    def test_news_adapter_delegates_the_channels_root_to_the_path_contract(self) -> None:
        """Дефолт адаптера обязан быть `None`: канонический пайплайн его не передаёт."""
        import inspect

        from src.news import subtitles

        checked = 0
        for name in ("_build_result", "build_subtitles_for_localization"):
            parameter = inspect.signature(getattr(subtitles, name)).parameters["channels_dir"]
            with self.subTest(function=name):
                self.assertIsNone(
                    parameter.default,
                    f"{name} снова прибил корень каналов строкой относительно cwd.",
                )
            checked += 1
        self.assertEqual(checked, 2, "Проверяемые функции адаптера исчезли — обнови тест.")


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
