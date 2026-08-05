"""Test classification: PRODUCT CONTRACT

A finished video the user already has must survive a failed re-render. The
pre-fix renderer pointed FFmpeg (``-y``) and ``shutil.copyfile`` straight at
``master_1080x1920.mp4``, so an interrupted or invalid second render destroyed
the previous result before anyone could tell it had failed.

These tests pin the promotion contract of ``src.news.final_renderer``: the
attempt is written beside the final output, validated by the canonical
``ffprobe_media_info`` owner, and only then promoted with ``os.replace``. No
real FFmpeg, ffprobe, network, TTS, Vision or provider call is made.
"""

from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SENTINEL = b"the previously finished video the user already has"


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _passing_probe(*_args, **_kwargs) -> dict[str, object]:
    return {"status": "passed", "width": 1080, "height": 1920, "duration_sec": 2.0}


def _failing_probe(*_args, **_kwargs) -> dict[str, object]:
    return {"status": "failed", "error": "moov atom not found"}


class FinalOutputPromotionTests(unittest.TestCase):
    """Drive ``render_final_video`` with segments and FFmpeg faked out."""

    def _render(self, root: Path, **patches):
        from src.news.final_renderer import render_final_video

        segment = root / "segment.mp4"
        segment.write_bytes(b"segment")

        def fake_ffmpeg(args: list[str]) -> None:
            target = Path(args[-1])
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"newly rendered video")

        stack = {
            "src.news.final_renderer._run_ffmpeg": {"side_effect": fake_ffmpeg},
            "src.news.final_renderer.ffprobe_media_info": {"side_effect": _passing_probe},
        }
        stack.update(patches)

        with patch(
            "src.news.final_renderer._create_scene_segments",
            return_value=[
                {
                    "path": segment,
                    "duration": 2.0,
                    "scene_id": "scene_001",
                    "slot_id": "slot_001",
                    "quality_tier": "full",
                }
            ],
        ):
            with _patch_all(stack):
                return render_final_video(
                    project_root=root,
                    language="en",
                    script={
                        "estimated_duration_sec": 2.0,
                        "scenes": [{"scene_id": "scene_001", "target_duration_sec": 2.0}],
                    },
                    visual_plan={"resolution": {"width": 1080, "height": 1920}},
                    assets_manifest={"scenes": []},
                    voice_manifest={},
                )

    @staticmethod
    def _output_dir(root: Path) -> Path:
        return root / "localizations" / "en" / "output"

    def _existing_master(self, root: Path) -> Path:
        master = self._output_dir(root) / "master_1080x1920.mp4"
        master.parent.mkdir(parents=True, exist_ok=True)
        master.write_bytes(SENTINEL)
        return master

    @staticmethod
    def _leftovers(output_dir: Path) -> list[str]:
        return sorted(item.name for item in output_dir.glob(".*partial*"))

    def test_render_failure_leaves_the_existing_final_video_untouched(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            master = self._existing_master(root)
            before = _digest(master)

            def exploding_ffmpeg(args: list[str]) -> None:
                target = Path(args[-1])
                if "partial" in target.name:
                    target.write_bytes(b"half-written")
                    raise RuntimeError("FFmpeg failed.")
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(b"newly rendered video")

            self._write_subtitles(root)
            with self.assertRaises(RuntimeError) as caught:
                self._render(
                    root,
                    **{"src.news.final_renderer._run_ffmpeg": {"side_effect": exploding_ffmpeg}},
                )

            self.assertIn("FFmpeg failed.", str(caught.exception))
            self.assertEqual(_digest(master), before, "a failed render replaced the finished video")
            self.assertEqual(master.read_bytes(), SENTINEL)
            self.assertEqual(self._leftovers(self._output_dir(root)), [])

    def test_validation_failure_leaves_the_existing_final_video_untouched(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            master = self._existing_master(root)
            before = _digest(master)

            with self.assertRaises(RuntimeError) as caught:
                self._render(
                    root,
                    **{
                        "src.news.final_renderer.ffprobe_media_info": {"side_effect": _failing_probe},
                    },
                )

            self.assertIn("invalid video file", str(caught.exception))
            self.assertEqual(_digest(master), before, "a rejected render replaced the finished video")
            self.assertEqual(self._leftovers(self._output_dir(root)), [])

    def test_zero_duration_output_is_rejected_before_promotion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            master = self._existing_master(root)

            with self.assertRaises(RuntimeError):
                self._render(
                    root,
                    **{
                        "src.news.final_renderer.ffprobe_media_info": {
                            "return_value": {"status": "passed", "duration_sec": 0.0}
                        },
                    },
                )

            self.assertEqual(master.read_bytes(), SENTINEL)

    def test_success_replaces_the_final_video_and_keeps_the_return_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            master = self._existing_master(root)

            manifest = self._render(root)

            self.assertEqual(manifest["status"], "completed")
            self.assertEqual(Path(manifest["output_path"]), master)
            self.assertEqual(manifest["renderer"], "news_to_short_final_renderer_v2")
            self.assertEqual(master.read_bytes(), b"newly rendered video")
            self.assertNotEqual(master.read_bytes(), SENTINEL)
            self.assertEqual(self._leftovers(self._output_dir(root)), [])

    def test_failure_without_a_previous_render_leaves_no_final_video_behind(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            master = self._output_dir(root) / "master_1080x1920.mp4"

            with self.assertRaises(RuntimeError):
                self._render(
                    root,
                    **{
                        "src.news.final_renderer.ffprobe_media_info": {"side_effect": _failing_probe},
                    },
                )

            self.assertFalse(master.exists(), "a rejected render was published as the final video")
            self.assertEqual(self._leftovers(self._output_dir(root)), [])

    def test_replace_failure_preserves_the_previous_video_and_surfaces_the_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            master = self._existing_master(root)
            before = _digest(master)

            with self.assertRaises(PermissionError) as caught:
                self._render(
                    root,
                    **{
                        "src.news.final_renderer.os.replace": {
                            "side_effect": PermissionError("target is locked by another process")
                        },
                    },
                )

            self.assertIn("locked", str(caught.exception))
            self.assertEqual(_digest(master), before, "a failed replace damaged the finished video")
            self.assertEqual(self._leftovers(self._output_dir(root)), [])

    def test_cleanup_failure_does_not_mask_the_original_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._existing_master(root)

            with self.assertRaises(RuntimeError) as caught:
                self._render(
                    root,
                    **{
                        "src.news.final_renderer.ffprobe_media_info": {"side_effect": _failing_probe},
                        "pathlib.Path.unlink": {"side_effect": OSError("still in use")},
                    },
                )

            self.assertIn("invalid video file", str(caught.exception))

    def test_the_renderer_never_writes_to_the_existing_final_path(self) -> None:
        """The attempt, not the final output, is what FFmpeg and copyfile are handed."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            master = self._existing_master(root)
            self._write_subtitles(root)
            seen: list[Path] = []

            def recording_ffmpeg(args: list[str]) -> None:
                target = Path(args[-1])
                seen.append(target)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(b"newly rendered video")

            self._render(
                root,
                **{"src.news.final_renderer._run_ffmpeg": {"side_effect": recording_ffmpeg}},
            )

            self.assertNotIn(master, seen, "FFmpeg was pointed at the existing final video")
            attempts = [item for item in seen if item.name.startswith(".master_1080x1920.partial")]
            self.assertTrue(attempts, f"no same-name attempt file was used; targets were {seen}")
            attempt = attempts[-1]
            self.assertEqual(attempt.parent, master.parent, "attempt is not beside the final output")
            self.assertEqual(attempt.suffix, ".mp4", "attempt lost the container suffix")

    def _write_subtitles(self, root: Path) -> None:
        """Force the subtitle-burn branch, which is the one that runs FFmpeg last."""
        subtitles = root / "localizations" / "en" / "subtitles"
        subtitles.mkdir(parents=True, exist_ok=True)
        ass = subtitles / "subs.ass"
        ass.write_text("[Script Info]\n", encoding="utf-8")
        (subtitles / "subtitles_manifest.json").write_text(
            '{"ass_path": ' + f'"{str(ass).replace(chr(92), chr(92) * 2)}"' + "}",
            encoding="utf-8",
        )


class TemporaryOutputPathTests(unittest.TestCase):
    def test_attempt_sits_next_to_the_target_and_keeps_the_suffix(self) -> None:
        from src.news.final_renderer import _temporary_output_path

        final = Path("/projects/demo/localizations/en/output/master_1080x1920.mp4")
        attempt = _temporary_output_path(final)

        self.assertEqual(attempt.parent, final.parent)
        self.assertEqual(attempt.suffix, ".mp4")
        self.assertNotEqual(attempt, final)
        self.assertTrue(attempt.name.startswith("."))

    def test_draft_output_gets_its_own_attempt_name(self) -> None:
        from src.news.final_renderer import _temporary_output_path

        draft = Path("/projects/demo/localizations/en/output/draft_1080x1920.mp4")
        master = Path("/projects/demo/localizations/en/output/master_1080x1920.mp4")

        self.assertNotEqual(_temporary_output_path(draft), _temporary_output_path(master))


def _patch_all(stack: dict[str, dict]):
    """Nest ``patch`` calls described as {target: kwargs} into one context manager."""
    from contextlib import ExitStack

    class _Combined:
        def __enter__(self):
            self._stack = ExitStack()
            self._stack.__enter__()
            for target, kwargs in stack.items():
                self._stack.enter_context(patch(target, **kwargs))
            return self

        def __exit__(self, *exc):
            return self._stack.__exit__(*exc)

    return _Combined()


if __name__ == "__main__":
    unittest.main()
