from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path


class AttributionExportTests(unittest.TestCase):
    def test_attribution_files_are_generated_without_local_paths_or_envato_certificate(self) -> None:
        from src.assets.attribution_export import export_asset_sources

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cert = root / "metadata" / "licenses" / "envato-cert.txt"
            cert.parent.mkdir(parents=True)
            cert.write_text("secret certificate body", encoding="utf-8")
            manifest = {
                "schema_version": 1,
                "scenes": [
                    {
                        "scene_id": "scene_wiki",
                        "selected_asset": {
                            "provider": "wikimedia",
                            "project_id": "project_001",
                            "scene_id": "scene_wiki",
                            "path": str(root / "assets" / "downloaded" / "wiki.jpg"),
                            "source_page_url": "https://commons.wikimedia.org/wiki/File:Wiki.jpg",
                            "author_name": "Commons Author",
                            "license": {
                                "license_name": "CC BY 4.0",
                                "license_url": "https://creativecommons.org/licenses/by/4.0/",
                                "attribution_text": "Commons Author, CC BY 4.0",
                            },
                            "policy_decision": {"modification_notice_required": True},
                        },
                    },
                    {
                        "scene_id": "scene_nasa",
                        "selected_asset": {
                            "provider": "nasa_images",
                            "project_id": "project_001",
                            "scene_id": "scene_nasa",
                            "path": str(root / "assets" / "downloaded" / "nasa.jpg"),
                            "source_page_url": "https://images.nasa.gov/details/NASA-1",
                            "author_name": "NASA",
                            "license": {
                                "license_name": "NASA Media Guidelines",
                                "license_url": "https://www.nasa.gov/nasa-brand-center/images-and-media/",
                                "attribution_text": "Source: NASA",
                            },
                        },
                    },
                    {
                        "scene_id": "scene_envato",
                        "selected_asset": {
                            "provider": "envato_manual",
                            "project_id": "project_001",
                            "scene_id": "scene_envato",
                            "path": str(root / "assets" / "manual_imports" / "envato.jpg"),
                            "source_page_url": "https://elements.envato.com/item-1",
                            "author_name": "Envato Author",
                            "license": {
                                "license_name": "envato_elements_project_registered",
                                "license_url": "https://help.elements.envato.com/hc/en-us/articles/360000629006-Envato-Elements-User-Terms",
                            },
                            "raw_metadata": {"license_proof_reference": str(cert)},
                        },
                    },
                ],
            }

            result = export_asset_sources(project_root=root, assets_manifest=manifest)

            sources = json.loads(Path(result["sources_json"]).read_text(encoding="utf-8"))
            attribution = Path(result["attribution_md"]).read_text(encoding="utf-8")
            youtube_sources = Path(result["youtube_sources_txt"]).read_text(encoding="utf-8")

        self.assertEqual(len(sources["assets"]), 3)
        self.assertIn("Commons Author, CC BY 4.0", attribution)
        self.assertIn("NASA is identified as the source; this does not imply NASA endorsement.", attribution)
        self.assertIn("https://commons.wikimedia.org/wiki/File:Wiki.jpg", youtube_sources)
        self.assertIn("Source: NASA", youtube_sources)
        self.assertNotIn(str(root), youtube_sources)
        self.assertNotIn("secret certificate body", youtube_sources)
        self.assertNotIn("envato-cert.txt", youtube_sources)
        self.assertNotIn("license_proof_reference", youtube_sources)


if __name__ == "__main__":
    unittest.main()
