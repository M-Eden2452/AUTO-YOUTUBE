from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import imageio_ffmpeg
from PIL import Image, ImageDraw

from src.project_foundation.channels import ChannelRegistry
from src.project_foundation.models import ChannelProfile
from src.project_foundation.projects import ProjectFactory
from src.templates.story_card import (
    RENDER_STATUS_DRY_RUN,
    RENDER_STATUS_PREPARED,
    RENDER_STATUS_RENDERED,
    RENDER_STATUS_SKIPPED_EXISTING_OUTPUT,
    STORY_CARD_CANONICAL_TEMPLATE_ID,
    StoryCardIntegrationError,
    canonicalize_story_card_template_id,
    prepare_story_card_render,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

_TINY_PRESET = {
    "schema_version": "story_card_short_preset.v1",
    "name": "story_card_short_integration_test",
    "resolution": [270, 480],
    "fps": 12,
    "duration_sec": 1.2,
    "fragment": {"start_sec": 0.0, "duration_sec": 1.0, "repeat_count": 1, "first_zoom": 1.05, "second_zoom": 1.12},
    "safe_margins": {"left": 18, "right": 18, "top": 18, "bottom": 18},
    "card": {"x": 22, "y": 28, "width": 226, "height": 420, "radius": 10, "background_color": "#111a24", "shadow_alpha": 120},
    "background": {"blur_radius": 8, "darken_alpha": 150, "zoom_start": 1.05, "zoom_end": 1.08},
    "central_video": {"x": 36, "y": 178, "width": 198, "height": 124, "corner_radius": 6},
    "text": {
        "font": "DejaVuSans.ttf",
        "top_font_size": 16,
        "comment_font_size": 13,
        "brand_font_size": 14,
        "username_font_size": 10,
        "line_spacing": 4,
        "top": "placeholder top text",
        "comment": "placeholder comment text",
        "top_highlights": {"negative": "", "number": "", "mechanism": "", "context": ""},
        "colors": {"primary": "#ffffff", "negative": "#ff5252", "number": "#ffe66d", "mechanism": "#72e084", "context": "#7ecbff", "muted": "#b7c2cf"},
    },
    "brand": {"name": "Test Brand", "username": "@test_brand", "icon_size": 32},
    "encoding": {"codec": "libx264", "crf": 28, "preset": "ultrafast", "pix_fmt": "yuv420p"},
}


def _write_tiny_preset(root: Path) -> Path:
    path = root / "tiny_preset.json"
    path.write_text(json.dumps(_TINY_PRESET), encoding="utf-8")
    return path


def _make_source_video(root: Path) -> Path:
    frames_dir = root / "frames"
    frames_dir.mkdir()
    for index in range(18):
        image = Image.new("RGB", (320, 180), (38, 62, 48))
        draw = ImageDraw.Draw(image)
        x = 120 + min(index, 10) * 4
        draw.ellipse((x, 56, x + 66, 126), fill=(220, 220, 205))
        image.save(frames_dir / f"frame_{index:03d}.png")
    output = root / "source.mp4"
    command = [
        imageio_ffmpeg.get_ffmpeg_exe(),
        "-y",
        "-v",
        "error",
        "-framerate",
        "12",
        "-i",
        str(frames_dir / "frame_%03d.png"),
        "-pix_fmt",
        "yuv420p",
        "-c:v",
        "libx264",
        str(output),
    ]
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise RuntimeError(result.stderr)
    return output


def _make_source_image(root: Path) -> Path:
    path = root / "source_asset.png"
    Image.new("RGB", (16, 16), (10, 20, 30)).save(path, format="PNG")
    return path


class CanonicalTemplateIdTests(unittest.TestCase):
    def test_canonical_template_id_passes_through(self) -> None:
        self.assertEqual(canonicalize_story_card_template_id("story_card_text_only_v1"), STORY_CARD_CANONICAL_TEMPLATE_ID)

    def test_legacy_alias_resolves_to_canonical(self) -> None:
        self.assertEqual(canonicalize_story_card_template_id("story_card_short_v1"), STORY_CARD_CANONICAL_TEMPLATE_ID)

    def test_unknown_template_id_raises(self) -> None:
        with self.assertRaises(StoryCardIntegrationError):
            canonicalize_story_card_template_id("some_other_template_v1")


class StoryCardProjectIntegrationTests(unittest.TestCase):
    def _make_channel_and_project(self, tmp: Path, *, template_id: str | None = None, output_policy: dict | None = None):
        channels_root = tmp / "channels"
        projects_root = tmp / "projects"
        channel_registry = ChannelRegistry(base_dir=channels_root)
        project_factory = ProjectFactory(base_dir=projects_root)

        channel = ChannelProfile(
            channel_id="story_card_test_channel",
            default_language="ru",
            supported_languages=["ru"],
            default_application="content_creator",
            default_format="vertical_short",
            default_template="story_card_text_only_v1",
            export_targets=["youtube_shorts"],
            output_policy=output_policy or {},
        )
        channel_registry.create(channel)

        result = project_factory.create(
            channel,
            title="Story Card Integration Project",
            template_id=template_id,
        )
        return channel, result.manifest, project_factory

    def test_dry_run_returns_planned_paths_without_writing_files(self) -> None:
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            channel, manifest, _ = self._make_channel_and_project(tmp_path)
            source_asset = _make_source_image(tmp_path)

            result = prepare_story_card_render(
                manifest,
                channel=channel,
                source_asset_path=source_asset,
                text={"top": "Верхний текст", "comment": "Комментарий"},
                render_preset_path=_write_tiny_preset(tmp_path),
                dry_run=True,
            )

            self.assertEqual(result.render_status, RENDER_STATUS_DRY_RUN)
            self.assertEqual(result.canonical_template_id, STORY_CARD_CANONICAL_TEMPLATE_ID)
            self.assertFalse(Path(result.render_request_path).exists())
            self.assertFalse(Path(result.output_path).exists())
            self.assertTrue(result.output_path.startswith(manifest.project_root))
            self.assertTrue(result.render_request_path.startswith(manifest.project_root))
            self.assertEqual(result.width, 270)
            self.assertEqual(result.height, 480)

    def test_legacy_alias_template_id_is_accepted_and_canonicalized(self) -> None:
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            channel, manifest, _ = self._make_channel_and_project(tmp_path, template_id="story_card_short_v1")
            source_asset = _make_source_image(tmp_path)

            result = prepare_story_card_render(
                manifest,
                channel=channel,
                source_asset_path=source_asset,
                text={"top": "Верхний текст"},
                render_preset_path=_write_tiny_preset(tmp_path),
                dry_run=True,
            )

            self.assertEqual(manifest.template_id, "story_card_short_v1")
            self.assertEqual(result.template_id, "story_card_short_v1")
            self.assertEqual(result.canonical_template_id, STORY_CARD_CANONICAL_TEMPLATE_ID)

    def test_render_request_creation_and_project_relative_paths(self) -> None:
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            channel, manifest, _ = self._make_channel_and_project(tmp_path)
            source_asset = _make_source_image(tmp_path)

            result = prepare_story_card_render(
                manifest,
                channel=channel,
                source_asset_path=source_asset,
                text={"top": "Верхний текст", "comment": "Комментарий"},
                render_preset_path=_write_tiny_preset(tmp_path),
                dry_run=False,
                render=False,
            )

            self.assertEqual(result.render_status, RENDER_STATUS_PREPARED)
            request_path = Path(result.render_request_path)
            self.assertTrue(request_path.is_file())
            self.assertFalse(Path(result.output_path).exists())
            payload = json.loads(request_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["canonical_template_id"], STORY_CARD_CANONICAL_TEMPLATE_ID)
            self.assertEqual(payload["preset"]["text"]["top"], "Верхний текст")
            self.assertTrue(result.output_path.startswith(manifest.project_root))

    def test_overwrite_protection_skips_existing_output(self) -> None:
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            channel, manifest, _ = self._make_channel_and_project(tmp_path)
            source_video = _make_source_video(tmp_path)
            preset_path = _write_tiny_preset(tmp_path)

            first = prepare_story_card_render(
                manifest,
                channel=channel,
                source_asset_path=source_video,
                text={"top": "Верхний текст", "comment": "Комментарий"},
                render_preset_path=preset_path,
                dry_run=False,
                render=True,
            )
            self.assertEqual(first.render_status, RENDER_STATUS_RENDERED)
            output_path = Path(first.output_path)
            self.assertTrue(output_path.is_file())
            original_bytes = output_path.read_bytes()

            second = prepare_story_card_render(
                manifest,
                channel=channel,
                source_asset_path=source_video,
                text={"top": "Другой текст", "comment": "Другой комментарий"},
                render_preset_path=preset_path,
                dry_run=False,
                render=True,
            )

            self.assertEqual(second.render_status, RENDER_STATUS_SKIPPED_EXISTING_OUTPUT)
            self.assertTrue(second.warnings)
            self.assertEqual(output_path.read_bytes(), original_bytes)

    def test_smoke_local_render_produces_vertical_mp4(self) -> None:
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            channel, manifest, _ = self._make_channel_and_project(tmp_path)
            source_video = _make_source_video(tmp_path)

            with patch("socket.socket", side_effect=AssertionError("no network calls expected")):
                result = prepare_story_card_render(
                    manifest,
                    channel=channel,
                    source_asset_path=source_video,
                    text={"top": "Верхний текст", "comment": "Комментарий"},
                    render_preset_path=_write_tiny_preset(tmp_path),
                    dry_run=False,
                    render=True,
                )

            self.assertEqual(result.render_status, RENDER_STATUS_RENDERED)
            self.assertTrue(Path(result.output_path).is_file())
            self.assertEqual(result.width, 270)
            self.assertEqual(result.height, 480)
            self.assertIn("render_manifest", result.metadata)
            self.assertFalse(result.metadata["render_manifest"]["audio"]["tts_performed"])

    def test_invalid_format_raises(self) -> None:
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            channel, manifest, _ = self._make_channel_and_project(tmp_path)
            manifest.format_id = "longform"
            source_asset = _make_source_image(tmp_path)

            with self.assertRaises(StoryCardIntegrationError):
                prepare_story_card_render(
                    manifest,
                    channel=channel,
                    source_asset_path=source_asset,
                    text={"top": "Верхний текст"},
                    render_preset_path=_write_tiny_preset(tmp_path),
                    dry_run=True,
                )

    def test_invalid_template_raises(self) -> None:
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            channel, manifest, _ = self._make_channel_and_project(tmp_path)
            manifest.template_id = "some_other_template_v1"
            source_asset = _make_source_image(tmp_path)

            with self.assertRaises(StoryCardIntegrationError):
                prepare_story_card_render(
                    manifest,
                    channel=channel,
                    source_asset_path=source_asset,
                    text={"top": "Верхний текст"},
                    render_preset_path=_write_tiny_preset(tmp_path),
                    dry_run=True,
                )

    def test_missing_localization_text_raises(self) -> None:
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            channel, manifest, _ = self._make_channel_and_project(tmp_path)
            source_asset = _make_source_image(tmp_path)

            with self.assertRaises(StoryCardIntegrationError):
                prepare_story_card_render(
                    manifest,
                    channel=channel,
                    source_asset_path=source_asset,
                    text={},
                    render_preset_path=_write_tiny_preset(tmp_path),
                    dry_run=True,
                )

    def test_missing_source_asset_raises(self) -> None:
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            channel, manifest, _ = self._make_channel_and_project(tmp_path)

            with self.assertRaises(StoryCardIntegrationError):
                prepare_story_card_render(
                    manifest,
                    channel=channel,
                    source_asset_path=tmp_path / "does_not_exist.mp4",
                    text={"top": "Верхний текст"},
                    render_preset_path=_write_tiny_preset(tmp_path),
                    dry_run=True,
                )

    def test_channel_output_policy_disallows_other_templates(self) -> None:
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            channel, manifest, _ = self._make_channel_and_project(
                tmp_path, output_policy={"allowed_templates": ["some_other_template_v1"]}
            )
            source_asset = _make_source_image(tmp_path)

            with self.assertRaises(StoryCardIntegrationError):
                prepare_story_card_render(
                    manifest,
                    channel=channel,
                    source_asset_path=source_asset,
                    text={"top": "Верхний текст"},
                    render_preset_path=_write_tiny_preset(tmp_path),
                    dry_run=True,
                )

    def test_channel_output_policy_allows_legacy_alias(self) -> None:
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            channel, manifest, _ = self._make_channel_and_project(
                tmp_path, output_policy={"allowed_templates": ["story_card_short_v1"]}
            )
            source_asset = _make_source_image(tmp_path)

            result = prepare_story_card_render(
                manifest,
                channel=channel,
                source_asset_path=source_asset,
                text={"top": "Верхний текст"},
                render_preset_path=_write_tiny_preset(tmp_path),
                dry_run=True,
            )

            self.assertEqual(result.render_status, RENDER_STATUS_DRY_RUN)

    def test_does_not_import_pipeline(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "-B",
                "-c",
                "import sys; import src.templates.story_card; assert 'pipeline' not in sys.modules",
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_does_not_write_to_real_channels_or_projects(self) -> None:
        real_channels = set(Path("channels").iterdir()) if Path("channels").is_dir() else set()
        real_projects = set(Path("projects").iterdir()) if Path("projects").is_dir() else set()

        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            channel, manifest, _ = self._make_channel_and_project(tmp_path)
            source_asset = _make_source_image(tmp_path)
            prepare_story_card_render(
                manifest,
                channel=channel,
                source_asset_path=source_asset,
                text={"top": "Верхний текст"},
                render_preset_path=_write_tiny_preset(tmp_path),
                dry_run=False,
                render=False,
            )

        self.assertEqual(set(Path("channels").iterdir()) if Path("channels").is_dir() else set(), real_channels)
        self.assertEqual(set(Path("projects").iterdir()) if Path("projects").is_dir() else set(), real_projects)


if __name__ == "__main__":
    unittest.main()
