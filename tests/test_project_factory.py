from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.project_foundation.models import ChannelProfile, ProjectFoundationError
from src.project_foundation.projects import PROJECT_FILENAME, PROJECT_SUBDIRS, ProjectFactory


def _channel(**overrides) -> ChannelProfile:
    defaults = dict(
        channel_id="test_channel",
        default_language="ru",
        supported_languages=["ru", "en"],
        default_application="content_creator",
        default_format="vertical_short",
        default_template="story_card_text_only_v1",
        export_targets=["youtube_shorts"],
    )
    defaults.update(overrides)
    return ChannelProfile(**defaults)


class ProjectFactoryCreateTests(unittest.TestCase):
    def test_create_writes_expected_structure(self) -> None:
        with TemporaryDirectory() as tmp:
            projects_root = Path(tmp) / "projects"
            factory = ProjectFactory(base_dir=projects_root)
            channel = _channel()

            result = factory.create(channel, title="My Test Project", project_id="fixed_id")

            self.assertFalse(result.dry_run)
            self.assertEqual(result.manifest.project_id, "fixed_id")
            self.assertEqual(result.manifest.channel_id, "test_channel")
            self.assertEqual(result.manifest.application_id, "content_creator")
            self.assertEqual(result.manifest.format_id, "vertical_short")
            self.assertEqual(result.manifest.template_id, "story_card_text_only_v1")
            self.assertEqual(result.manifest.language, "ru")
            self.assertEqual(result.manifest.export_targets, ["youtube_shorts"])

            project_dir = projects_root / "fixed_id"
            self.assertTrue((project_dir / PROJECT_FILENAME).is_file())
            for sub in PROJECT_SUBDIRS:
                self.assertTrue((project_dir / sub).is_dir())
            self.assertTrue((project_dir / "localizations" / "ru").is_dir())

    def test_dry_run_creates_nothing(self) -> None:
        with TemporaryDirectory() as tmp:
            projects_root = Path(tmp) / "projects"
            factory = ProjectFactory(base_dir=projects_root)
            channel = _channel()

            result = factory.create(channel, title="Dry Run Project", project_id="dry_id", dry_run=True)

            self.assertTrue(result.dry_run)
            self.assertEqual(result.manifest.project_id, "dry_id")
            self.assertFalse(projects_root.exists())

    def test_cannot_overwrite_existing_project(self) -> None:
        with TemporaryDirectory() as tmp:
            factory = ProjectFactory(base_dir=Path(tmp) / "projects")
            channel = _channel()
            factory.create(channel, title="First", project_id="same_id")

            with self.assertRaises(ProjectFoundationError):
                factory.create(channel, title="Second", project_id="same_id")

    def test_inherits_channel_defaults(self) -> None:
        with TemporaryDirectory() as tmp:
            factory = ProjectFactory(base_dir=Path(tmp) / "projects")
            channel = _channel()

            result = factory.create(channel, title="Inherit Defaults", project_id="inherited")

            self.assertEqual(result.manifest.application_id, channel.default_application)
            self.assertEqual(result.manifest.format_id, channel.default_format)
            self.assertEqual(result.manifest.template_id, channel.default_template)
            self.assertEqual(result.manifest.language, channel.default_language)
            self.assertEqual(result.manifest.export_targets, channel.export_targets)

    def test_explicit_overrides_win_over_channel_defaults(self) -> None:
        with TemporaryDirectory() as tmp:
            factory = ProjectFactory(base_dir=Path(tmp) / "projects")
            channel = _channel()

            result = factory.create(
                channel,
                title="Overridden",
                project_id="overridden",
                application_id="video_repurposer",
                format_id="longform",
                template_id="custom_template",
                language="en",
                export_targets=["tiktok"],
            )

            self.assertEqual(result.manifest.application_id, "video_repurposer")
            self.assertEqual(result.manifest.format_id, "longform")
            self.assertEqual(result.manifest.template_id, "custom_template")
            self.assertEqual(result.manifest.language, "en")
            self.assertEqual(result.manifest.export_targets, ["tiktok"])

    def test_language_must_be_supported_by_channel(self) -> None:
        with TemporaryDirectory() as tmp:
            factory = ProjectFactory(base_dir=Path(tmp) / "projects")
            channel = _channel(supported_languages=["ru"])

            with self.assertRaises(ProjectFoundationError):
                factory.create(channel, title="Bad Language", project_id="bad_lang", language="fr")

    def test_missing_application_id_raises(self) -> None:
        with TemporaryDirectory() as tmp:
            factory = ProjectFactory(base_dir=Path(tmp) / "projects")
            channel = _channel(default_application="")

            with self.assertRaises(ProjectFoundationError):
                factory.create(channel, title="No App", project_id="no_app")

    def test_project_id_is_generated_when_not_provided(self) -> None:
        with TemporaryDirectory() as tmp:
            factory = ProjectFactory(base_dir=Path(tmp) / "projects")
            channel = _channel()

            result = factory.create(channel, title="Auto Generated Id")

            # Stage B3: date first (so a folder listing sorts chronologically),
            # then the title. The old format was title + a random hex suffix.
            self.assertRegex(result.manifest.project_id, r"^\d{4}-\d{2}-\d{2}_auto-generated-id$")

    def test_two_projects_with_the_same_title_do_not_collide(self) -> None:
        with TemporaryDirectory() as tmp:
            factory = ProjectFactory(base_dir=Path(tmp) / "projects")
            channel = _channel()

            first = factory.create(channel, title="Одинаковое название")
            second = factory.create(channel, title="Одинаковое название")

            self.assertNotEqual(first.manifest.project_id, second.manifest.project_id)
            self.assertTrue(second.manifest.project_id.endswith("-2"))

    def test_russian_title_is_transliterated_instead_of_being_dropped(self) -> None:
        with TemporaryDirectory() as tmp:
            factory = ProjectFactory(base_dir=Path(tmp) / "projects")

            result = factory.create(_channel(), title="Почему вороны запоминают лица")

            # The old _slugify stripped every non-ASCII character, which is how the
            # one story-card project on disk ended up called "project-61958823".
            self.assertIn("pochemu-vorony", result.manifest.project_id)
            self.assertNotIn("project-", result.manifest.project_id)

    def test_list_and_get(self) -> None:
        with TemporaryDirectory() as tmp:
            factory = ProjectFactory(base_dir=Path(tmp) / "projects")
            channel = _channel()
            factory.create(channel, title="One", project_id="p_one")
            factory.create(channel, title="Two", project_id="p_two")

            listed = factory.list()
            fetched = factory.get("p_one")

            self.assertEqual({item.project_id for item in listed}, {"p_one", "p_two"})
            self.assertEqual(fetched.title, "One")

    def test_does_not_write_to_real_projects_directory(self) -> None:
        real_projects_dir = Path("projects")
        before = set(real_projects_dir.iterdir()) if real_projects_dir.is_dir() else set()

        with TemporaryDirectory() as tmp:
            factory = ProjectFactory(base_dir=Path(tmp) / "projects")
            channel = _channel()
            factory.create(channel, title="Isolated", project_id="isolated_test_project")

        after = set(real_projects_dir.iterdir()) if real_projects_dir.is_dir() else set()
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
