import unittest

from anime_factory.modules.score_candidates import find_candidates


class AnimeFactoryCandidateTests(unittest.TestCase):
    def test_find_candidates_prefers_dense_emotional_audio_window(self):
        transcript = [
            {"id": 0, "start": 0.0, "end": 8.0, "text": "тихий разговор"},
            {"id": 1, "start": 8.0, "end": 18.0, "text": "почему нет стой!"},
            {"id": 2, "start": 18.0, "end": 30.0, "text": "я люблю тебя, но он предал нас"},
            {"id": 3, "start": 60.0, "end": 65.0, "text": "коротко"},
        ]
        audio_features = [
            {"start": float(i), "end": float(i + 1), "loudness": 0.9 if 8 <= i < 30 else 0.1}
            for i in range(70)
        ]
        config = {
            "emotional_words": ["почему", "нет", "стой", "люблю", "предал"],
            "candidate_scoring": {"min_text_chars": 10, "overlap_threshold": 0.6},
        }

        candidates = find_candidates(
            transcript,
            audio_features,
            config,
            max_clips=2,
            min_duration=20,
            max_duration=45,
        )

        self.assertTrue(candidates)
        self.assertEqual(candidates[0]["start"], 0.0)
        self.assertTrue(20 <= candidates[0]["duration"] <= 45)
        self.assertIn("эмоциональные слова", candidates[0]["reason"])
        self.assertIn("аудио пик", candidates[0]["reason"])
        self.assertTrue(candidates[0]["subtitle_segments"])

    def test_find_candidates_filters_short_and_overlapping_windows(self):
        transcript = [
            {"id": 0, "start": 0.0, "end": 10.0, "text": "нет стой беги! " * 2},
            {"id": 1, "start": 10.0, "end": 22.0, "text": "monster kill death! " * 2},
            {"id": 2, "start": 22.0, "end": 34.0, "text": "why stop impossible! " * 2},
            {"id": 3, "start": 35.0, "end": 38.0, "text": "мало"},
        ]
        audio_features = [
            {"start": float(i), "end": float(i + 1), "loudness": 0.7}
            for i in range(50)
        ]
        config = {
            "emotional_words": ["нет", "стой", "беги", "monster", "kill", "death", "why", "stop", "impossible"],
            "candidate_scoring": {"min_text_chars": 10, "overlap_threshold": 0.4},
        }

        candidates = find_candidates(
            transcript,
            audio_features,
            config,
            max_clips=5,
            min_duration=20,
            max_duration=45,
        )

        self.assertLessEqual(len(candidates), 2)
        self.assertTrue(all(candidate["duration"] >= 20 for candidate in candidates))
        self.assertTrue(
            all(
                len(" ".join(seg["text"] for seg in candidate["subtitle_segments"])) >= 10
                for candidate in candidates
            )
        )


if __name__ == "__main__":
    unittest.main()
