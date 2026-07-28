"""Единый движок субтитров (этап Q3): нарезка, тайминг, валидация, сериализация.

Ни один тест не открывает сеть (tests.network_guard стоит на весь пакет), не
вызывает TTS, не распознаёт речь, не выравнивает по словам, не скачивает модели и
не запускает FFmpeg: движок субтитров по построению работает только с уже готовыми
JSON и строками.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.subtitles import (
    FORMAT_ASS,
    FORMAT_SRT,
    RESUME_COMPATIBLE,
    RESUME_LANGUAGE_CHANGED,
    RESUME_LEGACY_ARTIFACT,
    RESUME_NARRATION_CHANGED,
    RESUME_NO_ARTIFACT,
    RESUME_PROTECTED,
    RESUME_SCRIPT_CHANGED,
    SCHEMA_VERSION,
    TIMING_SOURCE_LEGACY_PLANNED,
    TIMING_SOURCE_SCENE_TIMELINE,
    TIMING_SOURCE_WORD,
    SubtitlePolicy,
    SubtitleRequest,
    SubtitleStyle,
    build_subtitle_result,
    manifest_cues,
    plan_resume,
    read_manifest,
    read_srt,
    resolve_subtitle_style,
    subtitle_dir,
    to_ass,
    to_srt,
    validate_cues,
    wrap_lines,
    write_artifact,
)
from src.subtitles.models import (
    ERR_CUE_OVERLAP,
    ERR_END_NOT_AFTER_START,
    ERR_LANGUAGE_MISMATCH,
    ERR_NEGATIVE_TIME,
    ERR_NON_FINITE_TIME,
    ERR_TEXT_NOT_COVERED,
    SubtitleCue,
)
from src.subtitles.segmentation import split_scene_text, tokenize
from src.subtitles.serialization import ass_style_line

RU_LONG = (
    "Учёные впервые записали звук, который издаёт ледник при таянии, и он оказался "
    "неожиданно низким. Оказалось, что этот гул слышен на 12 километров вокруг, "
    "даже сквозь толщу воды."
)
EN_LONG = (
    "Researchers recorded the sound a glacier makes while melting, and it turned out "
    "to be far lower than expected. The hum carries for 12 kilometres."
)


def _scene(index: int, narration: str, *, duration: float = 6.0, pause: float = 0.35) -> dict:
    return {
        "scene_id": f"scene_{index:03d}",
        "start_sec": 0.0,
        "target_duration_sec": duration,
        "narration": narration,
        "on_screen_text": " ".join(narration.split()[:5]),
        "pause_after_sec": pause,
    }


def _script(narrations: list[str], *, language: str = "ru") -> dict:
    return {
        "language": language,
        "narration_text": " ".join(narrations),
        "scenes": [_scene(index, text) for index, text in enumerate(narrations, start=1)],
    }


def _voice_manifest(script: dict, durations: list[float], *, pause: float = 0.35, extra: dict | None = None) -> dict:
    scenes = []
    for index, (scene, duration) in enumerate(zip(script["scenes"], durations, strict=True)):
        entry = {
            "scene_id": scene["scene_id"],
            "scene_index": index,
            "duration_seconds": duration,
            "generation_status": "completed",
        }
        if extra and scene["scene_id"] in extra:
            entry.update(extra[scene["scene_id"]])
        scenes.append(entry)
    gaps = max(0, len(durations) - 1)
    return {
        "schema_version": 2,
        "status": "completed",
        "voice_stage_status": "completed",
        "format_id": "vertical_short",
        "audio_path": "narration.wav",
        "scenes": scenes,
        "narration": {
            "output_path": "narration.wav",
            "duration_sec": sum(durations) + pause * gaps,
            "pause_total_sec": pause * gaps,
        },
    }


def _build(script: dict, voice: dict | None = None, *, language: str = "ru", **kwargs):
    style = kwargs.pop("style", SubtitleStyle())
    policy = kwargs.pop("policy", SubtitlePolicy.from_style(style))
    return build_subtitle_result(
        SubtitleRequest(
            script=script,
            localization_id=kwargs.pop("localization_id", language),
            language=language,
            voice_manifest=voice,
            policy=policy,
            style=style,
            **kwargs,
        )
    )


class SegmentationTests(unittest.TestCase):
    def test_short_scene_becomes_one_cue(self) -> None:
        segments = split_scene_text(
            "Лёд уходит быстрее.",
            scene_id="scene_001",
            scene_index=0,
            source_field="narration",
            policy=SubtitlePolicy(),
        )
        self.assertEqual(len(segments), 1)
        self.assertEqual(segments[0].text.replace("\n", " "), "Лёд уходит быстрее.")

    def test_long_scene_becomes_several_cues(self) -> None:
        segments = split_scene_text(
            RU_LONG, scene_id="scene_001", scene_index=0, source_field="narration", policy=SubtitlePolicy()
        )
        self.assertGreater(len(segments), 3)

    def test_no_word_is_lost_or_duplicated(self) -> None:
        for label, text in (("ru", RU_LONG), ("en", EN_LONG)):
            with self.subTest(language=label):
                segments = split_scene_text(
                    text, scene_id="scene_001", scene_index=0, source_field="narration", policy=SubtitlePolicy()
                )
                produced = " ".join(segment.text.replace("\n", " ") for segment in segments).split()
                self.assertEqual(produced, [token for token, _, _ in tokenize(text)])

    def test_punctuation_and_cyrillic_survive_unchanged(self) -> None:
        text = 'Он сказал: «это не гипотеза» — и добавил, что данные есть.'
        segments = split_scene_text(
            text, scene_id="scene_001", scene_index=0, source_field="narration", policy=SubtitlePolicy()
        )
        joined = " ".join(segment.text.replace("\n", " ") for segment in segments)
        self.assertEqual(joined.split(), text.split())
        self.assertIn("«это", joined)

    def test_abbreviation_is_not_a_sentence_end(self) -> None:
        from src.subtitles.segmentation import ends_sentence

        self.assertFalse(ends_sentence("т.д."))
        self.assertFalse(ends_sentence("млн."))
        self.assertTrue(ends_sentence("вокруг."))
        self.assertTrue(ends_sentence("правда?»"))

    def test_number_is_not_separated_from_its_unit(self) -> None:
        policy = SubtitlePolicy(max_characters_per_line=14, max_lines=1, max_words_per_cue=4)
        segments = split_scene_text(
            "Гул слышен на 12 километров вокруг всего залива",
            scene_id="scene_001",
            scene_index=0,
            source_field="narration",
            policy=policy,
        )
        for segment in segments:
            self.assertFalse(segment.text.rstrip().endswith("12"), segment.text)

    def test_wrap_never_exceeds_the_allowed_line_count(self) -> None:
        wrapped = wrap_lines("Оказалось, что он слышен на 12 километров.", max_characters_per_line=18, max_lines=2)
        self.assertEqual(len(wrapped.split("\n")), 2)
        self.assertEqual(wrapped.replace("\n", " ").split(), "Оказалось, что он слышен на 12 километров.".split())

    def test_narration_wins_over_on_screen_text(self) -> None:
        """Дефект W2: до Q3 в кадр попадали только первые пять слов сцены."""
        result = _build(_script([RU_LONG]), _voice_manifest(_script([RU_LONG]), [9.0]))
        joined = " ".join(cue.plain_text for cue in result.cues)
        self.assertEqual(joined.split(), RU_LONG.split())


class TimingTests(unittest.TestCase):
    def test_scene_timeline_from_voice_manifest_is_the_default_source(self) -> None:
        script = _script(["Первая мысль здесь.", "Вторая мысль здесь."])
        voice = _voice_manifest(script, [4.0, 6.0])
        result = _build(script, voice)
        self.assertEqual(result.timing_source, TIMING_SOURCE_SCENE_TIMELINE)
        self.assertEqual(result.scene_timeline_source, "voice_manifest")
        self.assertAlmostEqual(result.narration_duration_sec, 10.35, places=3)

    def test_last_cue_ends_exactly_at_the_narration_end(self) -> None:
        script = _script([RU_LONG, EN_LONG, "Короткий финал."])
        voice = _voice_manifest(script, [11.0, 9.5, 3.0])
        result = _build(script, voice)
        self.assertAlmostEqual(result.cues[-1].end_sec, voice["narration"]["duration_sec"], delta=0.02)

    def test_script_actual_durations_are_used_without_a_manifest(self) -> None:
        script = _script(["Первая мысль здесь.", "Вторая мысль здесь."])
        script["scenes"][0].update({"actual_duration_sec": 5.0, "speech_duration_sec": 4.65, "start_sec": 0.0})
        script["scenes"][1].update({"actual_duration_sec": 3.0, "speech_duration_sec": 3.0, "start_sec": 5.0})
        result = _build(script)
        self.assertEqual(result.timing_source, TIMING_SOURCE_SCENE_TIMELINE)
        self.assertAlmostEqual(result.cues[-1].end_sec, 8.0, delta=0.02)

    def test_planned_only_script_is_marked_as_legacy_timing(self) -> None:
        result = _build(_script(["Первая мысль здесь.", "Вторая мысль здесь."]))
        self.assertEqual(result.timing_source, TIMING_SOURCE_LEGACY_PLANNED)
        self.assertIn("legacy_timing_source", result.validation.codes())

    def test_word_timestamps_are_used_only_when_they_really_exist(self) -> None:
        """Без потаймингов слов движок не притворяется, что они есть."""
        script = _script(["Лёд уходит быстрее."])
        plain = _build(script, _voice_manifest(script, [4.0]))
        self.assertEqual(plain.timing_source, TIMING_SOURCE_SCENE_TIMELINE)

        words = [
            {"start": 0.0, "end": 1.1},
            {"start": 1.2, "end": 2.4},
            {"start": 2.5, "end": 3.9},
        ]
        with_words = _build(
            script,
            _voice_manifest(script, [4.0], extra={"scene_001": {"word_timestamps": words}}),
        )
        self.assertEqual(with_words.timing_source, TIMING_SOURCE_WORD)
        self.assertAlmostEqual(with_words.cues[0].end_sec, 3.9, places=3)

    def test_broken_word_timestamps_fall_back_instead_of_being_trusted(self) -> None:
        script = _script(["Лёд уходит быстрее."])
        broken = [{"start": 0.0, "end": 1.1}, {"start": 1.2, "end": 0.9}, {"start": 2.5, "end": 3.9}]
        result = _build(script, _voice_manifest(script, [4.0], extra={"scene_001": {"word_timestamps": broken}}))
        self.assertEqual(result.timing_source, TIMING_SOURCE_SCENE_TIMELINE)

    def test_word_timestamps_with_the_wrong_word_count_are_ignored(self) -> None:
        script = _script(["Лёд уходит быстрее."])
        short = [{"start": 0.0, "end": 1.1}]
        result = _build(script, _voice_manifest(script, [4.0], extra={"scene_001": {"word_timestamps": short}}))
        self.assertEqual(result.timing_source, TIMING_SOURCE_SCENE_TIMELINE)

    def test_manual_audio_gives_scene_level_timing_not_word_level(self) -> None:
        """Ручной WAV - это готовая озвучка, но не выравнивание по словам."""
        script = _script([RU_LONG])
        manifest = _voice_manifest(script, [12.0])
        manifest["source_type"] = "user_provided"
        manifest["provider"] = "audio_file"
        result = _build(script, manifest)
        self.assertEqual(result.timing_source, TIMING_SOURCE_SCENE_TIMELINE)
        self.assertTrue(all(cue.timing_source == TIMING_SOURCE_SCENE_TIMELINE for cue in result.cues))

    def test_unapproved_voice_manifest_does_not_produce_fake_timings(self) -> None:
        script = _script(["Первая мысль здесь."])
        stub = {"status": "provider_selection_required", "audio_path": "", "scenes": []}
        result = _build(script, stub)
        self.assertEqual(result.timing_source, TIMING_SOURCE_LEGACY_PLANNED)

    def test_any_scene_count_works_without_a_fixed_table(self) -> None:
        for count in (1, 3, 4, 6, 9, 14):
            with self.subTest(scenes=count):
                script = _script([f"Мысль номер {index} про лёд и воду." for index in range(1, count + 1)])
                voice = _voice_manifest(script, [3.0 + index * 0.4 for index in range(count)])
                result = _build(script, voice)
                self.assertEqual(result.scene_count, count)
                self.assertEqual(
                    [scene["scene_id"] for scene in script["scenes"]],
                    list(dict.fromkeys(cue.scene_id for cue in result.cues)),
                )
                self.assertTrue(result.validation.ok, result.validation.codes())


class InvariantTests(unittest.TestCase):
    def _result(self):
        script = _script([RU_LONG, EN_LONG, "Финальная мысль о будущем льда."])
        return script, _voice_manifest(script, [12.0, 10.0, 4.5]), None

    def test_cues_never_overlap_and_keep_their_order(self) -> None:
        script, voice, _ = self._result()
        result = _build(script, voice)
        for previous, current in zip(result.cues, result.cues[1:]):
            self.assertGreaterEqual(current.start_sec, previous.end_sec - 0.011)
            self.assertLess(previous.start_sec, previous.end_sec)
        self.assertEqual([cue.index for cue in result.cues], list(range(1, len(result.cues) + 1)))

    def test_no_cue_leaves_its_own_scene_or_the_narration(self) -> None:
        script, voice, _ = self._result()
        result = _build(script, voice)
        from src.subtitles import resolve_scene_spans

        spans = resolve_scene_spans(script, voice_manifest=voice, format_id="vertical_short").by_scene_id()
        for cue in result.cues:
            span = spans[cue.scene_id]
            self.assertGreaterEqual(cue.start_sec, span.start_sec - 0.011)
            self.assertLessEqual(cue.end_sec, span.end_sec + 0.011)
            self.assertLessEqual(cue.end_sec, result.narration_duration_sec + 0.011)

    def test_scene_text_is_fully_covered(self) -> None:
        script, voice, _ = self._result()
        result = _build(script, voice)
        grouped = result.cues_by_scene()
        for scene in script["scenes"]:
            produced = " ".join(cue.plain_text for cue in grouped[scene["scene_id"]]).split()
            self.assertEqual(produced, scene["narration"].split())
        self.assertNotIn(ERR_TEXT_NOT_COVERED, result.validation.codes())

    def test_neighbouring_cues_do_not_repeat_the_same_text(self) -> None:
        script, voice, _ = self._result()
        result = _build(script, voice)
        for previous, current in zip(result.cues, result.cues[1:]):
            self.assertNotEqual(previous.plain_text.casefold(), current.plain_text.casefold())


class ValidationTests(unittest.TestCase):
    def _cue(self, index: int, start: float, end: float, *, text: str = "текст", language: str = "ru") -> SubtitleCue:
        return SubtitleCue(
            cue_id=f"scene_001#{index:02d}",
            scene_id="scene_001",
            index=index,
            scene_cue_index=index,
            text=text,
            start_sec=start,
            end_sec=end,
            language=language,
            timing_source=TIMING_SOURCE_SCENE_TIMELINE,
        )

    def test_broken_arithmetic_is_an_error(self) -> None:
        cases = {
            ERR_END_NOT_AFTER_START: self._cue(1, 2.0, 2.0),
            ERR_NEGATIVE_TIME: self._cue(1, -1.0, 2.0),
            ERR_NON_FINITE_TIME: self._cue(1, float("nan"), 2.0),
        }
        for code, cue in cases.items():
            with self.subTest(code=code):
                result = validate_cues([cue], policy=SubtitlePolicy())
                self.assertIn(code, result.codes())
                self.assertFalse(result.ok)

    def test_overlap_is_an_error_unless_explicitly_allowed(self) -> None:
        cues = [self._cue(1, 0.0, 3.0, text="один"), self._cue(2, 2.0, 4.0, text="два")]
        self.assertIn(ERR_CUE_OVERLAP, validate_cues(cues, policy=SubtitlePolicy()).codes())
        self.assertNotIn(ERR_CUE_OVERLAP, validate_cues(cues, policy=SubtitlePolicy(allow_overlap=True)).codes())

    def test_wrong_language_is_an_error(self) -> None:
        result = validate_cues([self._cue(1, 0.0, 2.0, language="en")], policy=SubtitlePolicy(), language="ru")
        self.assertIn(ERR_LANGUAGE_MISMATCH, result.codes())

    def test_missing_text_coverage_is_an_error(self) -> None:
        result = validate_cues(
            [self._cue(1, 0.0, 2.0, text="только начало")],
            policy=SubtitlePolicy(),
            scene_texts={"scene_001": "только начало и ещё продолжение"},
        )
        self.assertIn(ERR_TEXT_NOT_COVERED, result.codes())

    def test_reading_speed_is_a_warning_not_an_error(self) -> None:
        result = validate_cues(
            [self._cue(1, 0.0, 0.9, text="очень много символов в очень коротком кадре")],
            policy=SubtitlePolicy(),
        )
        self.assertIn("reading_speed_too_high", result.codes())
        self.assertTrue(result.ok)


class SerializationTests(unittest.TestCase):
    def test_srt_round_trip(self) -> None:
        script = _script([RU_LONG])
        result = _build(script, _voice_manifest(script, [11.0]))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "subtitles.srt"
            path.write_text(to_srt(result.cues), encoding="utf-8")
            restored = read_srt(path, language="ru")
        self.assertEqual(len(restored), len(result.cues))
        for original, parsed in zip(result.cues, restored):
            self.assertEqual(parsed.text, original.text)
            self.assertAlmostEqual(parsed.start_sec, original.start_sec, places=3)
            self.assertAlmostEqual(parsed.end_sec, original.end_sec, places=3)

    def test_default_style_keeps_legacy_header_and_channel_style_uses_safe_margins(self) -> None:
        self.assertEqual(
            ass_style_line(SubtitleStyle()),
            "Style: Default,Arial,72,&H00FFFFFF,&H00000000,1,4,0,2,80,80,260,1",
        )
        self.assertEqual(
            ass_style_line(resolve_subtitle_style(channel_id="nature_science_news_ru")),
            "Style: Default,Arial,64,&H00FFFFFF,&H00000000,1,4,0,2,120,120,360,1",
        )

    def test_ass_escapes_line_breaks_and_never_writes_negative_time(self) -> None:
        script = _script([RU_LONG])
        result = _build(script, _voice_manifest(script, [11.0]))
        text = to_ass(result.cues, style=result.style)
        self.assertNotIn("\n\\N", text)
        self.assertNotIn("Dialogue: 0,-", text)
        self.assertEqual(text.count("Dialogue:"), len(result.cues))

    def test_ass_shrinks_an_unusually_long_unbreakable_line(self) -> None:
        cue = SubtitleCue(
            cue_id="cue_001",
            scene_id="scene_001",
            index=1,
            scene_cue_index=1,
            start_sec=0.0,
            end_sec=2.0,
            text="сверхдлинноесловобезпереносакотороенельзяобрезать",
        )
        text = to_ass([cue], style=SubtitleStyle(font_size=64, max_characters_per_line=24))
        self.assertIn(r"{\fs", text)
        self.assertIn("сверхдлинноеслово", text)

    def test_unsupported_format_is_refused(self) -> None:
        from src.subtitles import serialize
        from src.subtitles.models import SubtitleError

        with self.assertRaises(SubtitleError):
            serialize([], "vtt")

    def test_channel_style_is_read_from_its_own_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            channel_dir = Path(tmp) / "demo_channel"
            channel_dir.mkdir(parents=True)
            (channel_dir / "subtitle_style.json").write_text(
                json.dumps({"font": "Verdana", "font_size": 64, "max_lines": 1, "margin_v": 300, "outline": False}),
                encoding="utf-8",
            )
            style = resolve_subtitle_style(channel_id="demo_channel", channels_dir=tmp)
        self.assertEqual(style.font_family, "Verdana")
        self.assertEqual(style.font_size, 64)
        self.assertEqual(style.max_lines, 1)
        self.assertEqual(style.margin_bottom, 300)
        self.assertEqual(style.source, "channel_subtitle_style")
        self.assertIn(",0,0,2,80,80,300,1", ass_style_line(style))


class ArtifactAndResumeTests(unittest.TestCase):
    def _write(self, root: Path, script: dict, voice: dict, *, localization: str = "ru"):
        result = _build(script, voice, language=localization, localization_id=localization)
        return result, write_artifact(result, project_root=root, localization_id=localization)

    def test_manifest_keeps_every_key_existing_readers_use(self) -> None:
        script = _script([RU_LONG, "Финальная мысль."])
        voice = _voice_manifest(script, [11.0, 3.0])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, artifact = self._write(root, script, voice)
        manifest = artifact.manifest
        for key in ("status", "language", "srt_path", "ass_path", "segments"):
            self.assertIn(key, manifest)
        self.assertTrue(manifest["segments"])
        self.assertEqual(set(manifest["segments"][0]), {"start", "end", "text"})
        self.assertEqual(manifest["schema_version"], SCHEMA_VERSION)
        self.assertEqual(manifest["timing_source"], TIMING_SOURCE_SCENE_TIMELINE)

    def test_renderer_and_exporter_find_the_files_they_expect(self) -> None:
        script = _script([RU_LONG])
        voice = _voice_manifest(script, [11.0])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, artifact = self._write(root, script, voice)
            from src.news.final_renderer import _load_subtitles_manifest

            loaded = _load_subtitles_manifest(root, "ru")
            self.assertTrue(Path(loaded["ass_path"]).is_file())
            self.assertEqual(Path(loaded["ass_path"]).name, "subtitles.ass")
            # exporter копирует ровно эти два имени
            for name in ("subtitles.srt", "subtitles.ass"):
                self.assertTrue((subtitle_dir(root, "ru") / name).is_file())
            self.assertEqual(artifact.paths[FORMAT_ASS].parent, subtitle_dir(root, "ru"))
            self.assertIn(FORMAT_SRT, artifact.paths)

    def test_each_localization_has_its_own_paths_and_language(self) -> None:
        ru_script = _script(["Русская мысль про лёд."], language="ru")
        en_script = _script(["An English thought about ice."], language="en")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, ru = self._write(root, ru_script, _voice_manifest(ru_script, [4.0]), localization="ru")
            _, en = self._write(root, en_script, _voice_manifest(en_script, [4.0]), localization="en")
            self.assertNotEqual(ru.paths[FORMAT_SRT], en.paths[FORMAT_SRT])
            self.assertEqual(ru.manifest["subtitle_language"], "ru")
            self.assertEqual(en.manifest["subtitle_language"], "en")
            self.assertIn("Русская", Path(ru.paths[FORMAT_SRT]).read_text(encoding="utf-8"))
            self.assertNotIn("Русская", Path(en.paths[FORMAT_SRT]).read_text(encoding="utf-8"))
            from src.subtitles import duplicate_paths

            self.assertEqual(duplicate_paths([ru.manifest, en.manifest]), [])

    def test_compatible_artifact_is_reused(self) -> None:
        script = _script([RU_LONG])
        voice = _voice_manifest(script, [11.0])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result, artifact = self._write(root, script, voice)
            decision = plan_resume(read_manifest(artifact.manifest_path), result, project_root=root, localization_id="ru")
        self.assertTrue(decision.reuse)
        self.assertEqual(decision.reason, RESUME_COMPATIBLE)

    def test_changed_script_and_changed_narration_invalidate_the_artifact(self) -> None:
        script = _script([RU_LONG])
        voice = _voice_manifest(script, [11.0])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, artifact = self._write(root, script, voice)
            stored = read_manifest(artifact.manifest_path)

            edited = _script([RU_LONG + " И ещё одно наблюдение."])
            new_script_result = _build(edited, _voice_manifest(edited, [11.0]))
            self.assertEqual(
                plan_resume(stored, new_script_result, project_root=root, localization_id="ru").reason,
                RESUME_SCRIPT_CHANGED,
            )

            relouded = _build(script, _voice_manifest(script, [13.5]))
            self.assertEqual(
                plan_resume(stored, relouded, project_root=root, localization_id="ru").reason,
                RESUME_NARRATION_CHANGED,
            )

    def test_artifact_of_another_localization_is_never_reused(self) -> None:
        ru_script = _script(["Русская мысль про лёд."], language="ru")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, ru = self._write(root, ru_script, _voice_manifest(ru_script, [4.0]), localization="ru")
            en_script = _script(["An English thought about ice."], language="en")
            en_result = _build(en_script, _voice_manifest(en_script, [4.0]), language="en", localization_id="en")
            decision = plan_resume(ru.manifest, en_result, project_root=root, localization_id="en")
        self.assertFalse(decision.reuse)
        self.assertEqual(decision.reason, RESUME_LANGUAGE_CHANGED)

    def test_missing_files_invalidate_a_manifest_that_claims_them(self) -> None:
        script = _script([RU_LONG])
        voice = _voice_manifest(script, [11.0])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result, artifact = self._write(root, script, voice)
            artifact.paths[FORMAT_ASS].unlink()
            decision = plan_resume(read_manifest(artifact.manifest_path), result, project_root=root, localization_id="ru")
        self.assertFalse(decision.reuse)
        self.assertEqual(decision.reason, "artifact_files_missing")

    def test_protected_user_artifact_is_never_overwritten(self) -> None:
        script = _script([RU_LONG])
        voice = _voice_manifest(script, [11.0])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result, artifact = self._write(root, script, voice)
            stored = read_manifest(artifact.manifest_path)
            stored["protected"] = True
            stored["script_fingerprint"] = "definitely-different"
            decision = plan_resume(stored, result, project_root=root, localization_id="ru")
        self.assertTrue(decision.reuse)
        self.assertEqual(decision.reason, RESUME_PROTECTED)

    def test_pre_q3_manifest_is_readable_and_gets_regenerated(self) -> None:
        """Старый артефакт не ломает чтение, но и не притворяется совместимым."""
        legacy = {
            "status": "completed",
            "language": "ru",
            "srt_path": "subtitles.srt",
            "ass_path": "subtitles.ass",
            "segments": [
                {"start": 0.0, "end": 2.0, "text": "Учёные впервые записали звук,"},
                {"start": 2.0, "end": 4.0, "text": "Оказалось что гул слышен"},
            ],
        }
        cues = manifest_cues(legacy)
        self.assertEqual(len(cues), 2)
        self.assertEqual(cues[0].scene_id, "")
        self.assertTrue(validate_cues(cues, policy=SubtitlePolicy()).ok)

        script = _script([RU_LONG])
        result = _build(script, _voice_manifest(script, [11.0]))
        decision = plan_resume(legacy, result, localization_id="ru")
        self.assertFalse(decision.reuse)
        self.assertEqual(decision.reason, RESUME_LEGACY_ARTIFACT)

    def test_absent_artifact_is_reported_as_such(self) -> None:
        script = _script([RU_LONG])
        result = _build(script, _voice_manifest(script, [11.0]))
        self.assertEqual(plan_resume({}, result, localization_id="ru").reason, RESUME_NO_ARTIFACT)


if __name__ == "__main__":
    unittest.main()
