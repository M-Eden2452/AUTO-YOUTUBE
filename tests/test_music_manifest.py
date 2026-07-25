"""Music manifest writer + the renderer wiring that was previously unreachable.

The renderer's mixing/ducking path already existed but was gated on
assets/music/music_manifest.json, which nothing wrote. These tests cover the writer,
the tolerant reader, and the ffmpeg argument construction - without invoking ffmpeg.

No network, no downloads: tracks are tiny WAV files created in tempfile.
"""

from __future__ import annotations

import json
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

from src.audio.music_manifest import (
    DEFAULT_VOLUME,
    MusicManifestError,
    build_music_manifest,
    clamp_volume,
    manifest_path,
    prepare_project_music,
    read_music_manifest,
)


def _write_wav(path: Path, seconds: float = 0.2) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(8000)
        handle.writeframes(b"\x00\x00" * int(8000 * seconds))
    return path


class BuildManifestTests(unittest.TestCase):
    def test_records_checksum_size_and_absolute_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            track = _write_wav(Path(tmp) / "bed.wav")
            manifest = build_music_manifest(track, volume=0.2)

            self.assertTrue(Path(manifest.path).is_absolute())
            self.assertEqual(manifest.original_filename, "bed.wav")
            self.assertGreater(manifest.size_bytes, 0)
            self.assertEqual(len(manifest.checksum_sha256), 64)
            self.assertAlmostEqual(manifest.volume, 0.2)
            self.assertTrue(manifest.ducking)

    def test_rights_are_recorded_as_unverified_not_claimed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manifest = build_music_manifest(_write_wav(Path(tmp) / "bed.wav"))
            self.assertEqual(manifest.license["commercial_use_status"], "unknown")
            self.assertEqual(manifest.license["verification_status"], "unknown")
            self.assertEqual(manifest.source, "user_provided")

    def test_missing_file_is_rejected(self) -> None:
        with self.assertRaises(MusicManifestError):
            build_music_manifest("/no/such/track.mp3")

    def test_empty_path_is_rejected(self) -> None:
        with self.assertRaises(MusicManifestError):
            build_music_manifest("")

    def test_unsupported_extension_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "bed.txt"
            bad.write_text("not audio", encoding="utf-8")
            with self.assertRaises(MusicManifestError):
                build_music_manifest(bad)

    def test_empty_file_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            empty = Path(tmp) / "bed.mp3"
            empty.write_bytes(b"")
            with self.assertRaises(MusicManifestError):
                build_music_manifest(empty)


class VolumeTests(unittest.TestCase):
    def test_volume_is_clamped_into_range(self) -> None:
        self.assertEqual(clamp_volume(-1.0), 0.0)
        self.assertEqual(clamp_volume(5.0), 1.0)
        self.assertEqual(clamp_volume(0.25), 0.25)

    def test_unusable_values_fall_back_to_the_default(self) -> None:
        self.assertEqual(clamp_volume(None), DEFAULT_VOLUME)
        self.assertEqual(clamp_volume("громко"), DEFAULT_VOLUME)


class WriteAndReadTests(unittest.TestCase):
    def test_manifest_lands_where_the_renderer_looks_for_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            track = _write_wav(Path(tmp) / "bed.wav")
            written = prepare_project_music(project, track, volume=0.15)

            self.assertEqual(written, manifest_path(project))
            self.assertEqual(written.relative_to(project).as_posix(), "assets/music/music_manifest.json")
            data = json.loads(written.read_text(encoding="utf-8"))
            self.assertEqual(data["schema_version"], 1)
            self.assertAlmostEqual(data["volume"], 0.15)

    def test_reader_round_trips(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            prepare_project_music(project, _write_wav(Path(tmp) / "bed.wav"))
            self.assertTrue(read_music_manifest(project)["path"])

    def test_absent_manifest_means_no_music(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(read_music_manifest(Path(tmp)), {})

    def test_corrupt_manifest_means_no_music_rather_than_a_crash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            target = manifest_path(project)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("{ not json", encoding="utf-8")
            self.assertEqual(read_music_manifest(project), {})

    def test_manifest_without_a_path_means_no_music(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            target = manifest_path(project)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps({"volume": 0.1}), encoding="utf-8")
            self.assertEqual(read_music_manifest(project), {})


class RendererWiringTests(unittest.TestCase):
    """The mix filter must use the manifest's values - no ffmpeg is executed."""

    def _captured_filter(self, **manifest_overrides) -> str:
        from src.news import final_renderer

        captured: dict[str, list[str]] = {}

        def fake_run(args: list[str]) -> None:
            if "-filter_complex" in args:
                captured["args"] = list(args)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            voice = _write_wav(root / "voice.wav")
            music = _write_wav(root / "music.wav")
            video = root / "silent.mp4"
            video.write_bytes(b"x")
            with patch.object(final_renderer, "_run_ffmpeg", side_effect=fake_run):
                final_renderer._mux_voice_and_music(
                    video, voice, music, root / "out.mp4", 10.0, 12.0, **manifest_overrides
                )
        args = captured.get("args", [])
        return args[args.index("-filter_complex") + 1] if "-filter_complex" in args else ""

    def test_manifest_volume_reaches_the_filter(self) -> None:
        self.assertIn("volume=0.250", self._captured_filter(volume=0.25))

    def test_ducking_enabled_uses_sidechain_compression(self) -> None:
        self.assertIn("sidechaincompress", self._captured_filter(ducking=True))

    def test_ducking_disabled_is_a_plain_mix(self) -> None:
        filter_complex = self._captured_filter(ducking=False)
        self.assertNotIn("sidechaincompress", filter_complex)
        self.assertIn("amix=inputs=2", filter_complex)

    def test_music_bed_covers_the_full_target_duration_not_just_the_visuals(self) -> None:
        # narration_plus_tail can push the output past the visual timeline; the bed
        # must not stop early and leave a silent tail.
        self.assertIn("atrim=0:12.000", self._captured_filter())

    def test_narration_is_padded_so_the_mix_covers_the_tail(self) -> None:
        """Regression for the W1 defect found by the V1 live render.

        Preparing the bed for the full length (the assertion above) is necessary
        but not sufficient: `amix=duration=first` ends the mixed stream with its
        first input, so a narration shorter than the output left the end tail
        completely silent - 60.233 s of video against 59.475 s of audio on a real
        render. The narration must be padded to the same length the bed is.
        """
        for ducking in (True, False):
            with self.subTest(ducking=ducking):
                filter_complex = self._captured_filter(ducking=ducking)
                self.assertIn("apad=whole_dur=12.000", filter_complex)

    def test_padding_matches_the_bed_length_exactly(self) -> None:
        # Both must be derived from the same duration; a mismatch would either
        # re-introduce the silent tail or run the mix past the video.
        filter_complex = self._captured_filter()
        bed = filter_complex.split("atrim=0:")[1].split(",")[0]
        pad = filter_complex.split("apad=whole_dur=")[1].split(",")[0].split("[")[0]
        self.assertEqual(pad, bed)

    def test_padding_is_applied_to_the_sidechain_too(self) -> None:
        # The padded narration feeds asplit, so the sidechain sees silence over the
        # tail and the bed comes back up instead of staying ducked to the end.
        filter_complex = self._captured_filter(ducking=True)
        voice_stage = filter_complex.split(";")[0]
        self.assertIn("apad=whole_dur=", voice_stage)
        self.assertIn("asplit=2[voice_mix][voice_sidechain]", voice_stage)
        self.assertLess(voice_stage.index("apad="), voice_stage.index("asplit="))


class ServiceWiringTests(unittest.TestCase):
    def test_capability_no_longer_claims_music_is_unwired(self) -> None:
        from src.content_creation import capabilities

        local_file = next(o for o in capabilities.list_music_options() if o["mode_id"] == "local_file")
        self.assertNotEqual(local_file["status"], "architecture_supported")
        self.assertIn("fullscreen_voiceover_v1", local_file["supported_templates"])


if __name__ == "__main__":
    unittest.main()
