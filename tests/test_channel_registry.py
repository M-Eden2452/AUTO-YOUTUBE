from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.project_foundation.channels import CHANNEL_FILENAME, ChannelRegistry
from src.project_foundation.models import ChannelProfile, ProjectFoundationError


class ChannelRegistryTests(unittest.TestCase):
    def test_create_get_and_list(self) -> None:
        with TemporaryDirectory() as tmp:
            registry = ChannelRegistry(base_dir=Path(tmp) / "channels")
            profile = ChannelProfile(channel_id="alpha", display_name="Alpha Channel")

            created = registry.create(profile)
            fetched = registry.get("alpha")
            listed = registry.list()

            self.assertEqual(created.channel_id, "alpha")
            self.assertEqual(fetched.display_name, "Alpha Channel")
            self.assertEqual([item.channel_id for item in listed], ["alpha"])
            self.assertTrue(registry.exists("alpha"))
            self.assertTrue((Path(tmp) / "channels" / "alpha" / CHANNEL_FILENAME).is_file())

    def test_duplicate_channel_id_rejected(self) -> None:
        with TemporaryDirectory() as tmp:
            registry = ChannelRegistry(base_dir=Path(tmp) / "channels")
            registry.create(ChannelProfile(channel_id="dup"))

            with self.assertRaises(ProjectFoundationError):
                registry.create(ChannelProfile(channel_id="dup"))

    def test_get_missing_channel_raises(self) -> None:
        with TemporaryDirectory() as tmp:
            registry = ChannelRegistry(base_dir=Path(tmp) / "channels")

            with self.assertRaises(ProjectFoundationError):
                registry.get("does_not_exist")

    def test_update_requires_existing_channel(self) -> None:
        with TemporaryDirectory() as tmp:
            registry = ChannelRegistry(base_dir=Path(tmp) / "channels")

            with self.assertRaises(ProjectFoundationError):
                registry.update("missing", ChannelProfile(channel_id="missing"))

    def test_update_changes_updated_at_and_persists(self) -> None:
        with TemporaryDirectory() as tmp:
            registry = ChannelRegistry(base_dir=Path(tmp) / "channels")
            profile = registry.create(ChannelProfile(channel_id="beta", display_name="Beta"))
            original_updated_at = profile.updated_at

            profile.display_name = "Beta Updated"
            registry.update("beta", profile)
            fetched = registry.get("beta")

            self.assertEqual(fetched.display_name, "Beta Updated")
            self.assertGreaterEqual(fetched.updated_at, original_updated_at)

    def test_corrupted_json_raises_clear_error(self) -> None:
        with TemporaryDirectory() as tmp:
            channels_root = Path(tmp) / "channels"
            channel_dir = channels_root / "broken"
            channel_dir.mkdir(parents=True)
            (channel_dir / CHANNEL_FILENAME).write_text("{not valid json", encoding="utf-8")

            registry = ChannelRegistry(base_dir=channels_root)

            with self.assertRaises(ProjectFoundationError):
                registry.get("broken")

    def test_list_on_missing_directory_returns_empty(self) -> None:
        with TemporaryDirectory() as tmp:
            registry = ChannelRegistry(base_dir=Path(tmp) / "does_not_exist_yet")

            self.assertEqual(registry.list(), [])

    def test_atomic_write_leaves_no_temp_files(self) -> None:
        with TemporaryDirectory() as tmp:
            channels_root = Path(tmp) / "channels"
            registry = ChannelRegistry(base_dir=channels_root)
            registry.create(ChannelProfile(channel_id="gamma"))

            entries = list((channels_root / "gamma").iterdir())
            self.assertEqual([entry.name for entry in entries], [CHANNEL_FILENAME])

    def test_does_not_write_to_real_channels_directory(self) -> None:
        real_channels_dir = Path("channels")
        before = set(real_channels_dir.iterdir()) if real_channels_dir.is_dir() else set()

        with TemporaryDirectory() as tmp:
            registry = ChannelRegistry(base_dir=Path(tmp) / "channels")
            registry.create(ChannelProfile(channel_id="isolated_test_channel"))

        after = set(real_channels_dir.iterdir()) if real_channels_dir.is_dir() else set()
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
