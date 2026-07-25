import tempfile
import unittest
from pathlib import Path

from anime_factory.modules.transcribe import transcribe_audio


class AnimeFactoryTranscribeTests(unittest.TestCase):
    def test_transcribe_audio_reuses_existing_bom_transcript(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            transcript = root / "transcript.json"
            subtitles = root / "subtitles_raw.srt"
            audio = root / "audio.wav"
            transcript.write_text('\ufeff[{"id": 0, "start": 1.0, "end": 2.0, "text": "привет"}]', encoding="utf-8")
            subtitles.write_text("1\n00:00:01,000 --> 00:00:02,000\nпривет\n", encoding="utf-8")

            data = transcribe_audio(audio, transcript, subtitles, force=False)

        self.assertEqual(data[0]["text"], "привет")


if __name__ == "__main__":
    unittest.main()
