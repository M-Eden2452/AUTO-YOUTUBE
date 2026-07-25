import tempfile
import unittest
from pathlib import Path

from anime_factory.modules.refine_boundaries import refine_candidate_boundaries
from anime_factory.modules.score_candidates import find_candidates
from anime_factory.modules.selection import load_selected_candidates


class AnimeFactoryV3Tests(unittest.TestCase):
    def test_refine_boundaries_does_not_cut_middle_of_segment(self):
        candidate = {"id": 1, "start": 11.0, "end": 24.0, "duration": 13.0}
        transcript = [
            {"id": 0, "start": 9.0, "end": 13.0, "text": "начало реплики"},
            {"id": 1, "start": 13.0, "end": 25.0, "text": "продолжение реплики"},
        ]

        refined = refine_candidate_boundaries(candidate, transcript, [], [], trim_silence=False, use_scene_cuts=False)

        self.assertEqual(refined["start"], 9.0)
        self.assertEqual(refined["end"], 25.0)
        self.assertEqual(refined["original_start"], 11.0)
        self.assertEqual(refined["original_end"], 24.0)
        self.assertIn("start перенесен к началу реплики", refined["boundary_reason"])

    def test_selection_reads_selected_candidate_ids(self):
        candidates = [{"id": 1}, {"id": 2}, {"id": 3}]
        with tempfile.TemporaryDirectory() as temp_dir:
            selected_path = Path(temp_dir) / "selected.json"
            selected_path.write_text('{"selected_candidate_ids": [3, 1]}', encoding="utf-8")

            selected = load_selected_candidates(selected_path, candidates)

        self.assertEqual([candidate["id"] for candidate in selected], [3, 1])

    def test_candidate_scoring_has_hook_and_context_penalty(self):
        transcript = [
            {"id": 0, "start": 0.0, "end": 5.0, "text": "Почему стой! Это невозможно"},
            {"id": 1, "start": 5.0, "end": 22.0, "text": "мы должны бежать прямо сейчас и спасти всех"},
            {"id": 2, "start": 30.0, "end": 35.0, "text": "он сказал что надо идти"},
            {"id": 3, "start": 35.0, "end": 52.0, "text": "обычный разговор без сильного начала"},
        ]
        audio_features = [{"start": float(i), "end": float(i + 1), "loudness": 0.8 if i > 17 else 0.3} for i in range(60)]
        config = {
            "emotional_words": ["почему", "стой", "невозможно", "бежать"],
            "candidate_scoring": {"min_text_chars": 10, "overlap_threshold": 0.2},
        }

        candidates = find_candidates(transcript, audio_features, config, max_clips=4, min_duration=20, max_duration=25)

        self.assertTrue(candidates)
        self.assertIn("hook", candidates[0]["score_breakdown"])
        self.assertGreater(candidates[0]["score_breakdown"]["hook"], 0)
        context_candidate = next(candidate for candidate in candidates if candidate["start"] == 30.0)
        self.assertLess(context_candidate["score_breakdown"]["context"], 0)
        self.assertIn("начало может требовать контекст", context_candidate["warnings"])


if __name__ == "__main__":
    unittest.main()
