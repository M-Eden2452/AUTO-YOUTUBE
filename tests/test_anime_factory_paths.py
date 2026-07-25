import tempfile
import unittest
from pathlib import Path

from anime_factory.modules.paths import read_json


class AnimeFactoryPathTests(unittest.TestCase):
    def test_read_json_accepts_utf8_bom_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "artifact.json"
            path.write_text('\ufeff[{"id": 1, "text": "готово"}]', encoding="utf-8")

            data = read_json(path)

        self.assertEqual(data, [{"id": 1, "text": "готово"}])


if __name__ == "__main__":
    unittest.main()
