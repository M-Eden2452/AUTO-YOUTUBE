from __future__ import annotations

import ast
import tempfile
import unittest
from pathlib import Path

from PIL import Image


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
FRAME_SAMPLING_MODULE = "src.assets.frame_sampling"
PERCEPTUAL_SIMILARITY_MODULE = "src.assets.perceptual_similarity"
SHARED_PRIMITIVES_MODULE = "src.assets.frame_primitives"


class AssetImportCompatibilityTests(unittest.TestCase):
    def test_public_frame_and_hash_imports_remain_compatible(self) -> None:
        from src.assets import SampledFrame as PackageSampledFrame
        from src.assets.frame_sampling import SampledFrame, sha256_file
        from src.assets.perceptual_similarity import (
            SampledFrame as SimilaritySampledFrame,
            image_perceptual_hash,
            sha256_file as similarity_sha256_file,
        )

        self.assertIs(PackageSampledFrame, SampledFrame)
        self.assertIs(SimilaritySampledFrame, SampledFrame)
        self.assertIs(similarity_sha256_file, sha256_file)
        self.assertTrue(callable(image_perceptual_hash))

    def test_image_sampling_and_signature_contract(self) -> None:
        from src.assets.frame_sampling import SampledFrame, sample_frames, sha256_file
        from src.assets.perceptual_similarity import image_perceptual_hash, signature_from_frames

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "sample.jpg"
            Image.new("RGB", (32, 48), (20, 80, 140)).save(source)

            frames = sample_frames(source, media_type="image", output_dir=root / "frames")
            signature = signature_from_frames("asset_1", frames)
            expected_sha256 = sha256_file(source)
            expected_perceptual_hash = image_perceptual_hash(source)

        self.assertEqual(len(frames), 1)
        self.assertIsInstance(frames[0], SampledFrame)
        self.assertEqual(frames[0].extraction_status, "extracted")
        self.assertEqual(frames[0].sha256, expected_sha256)
        self.assertEqual(frames[0].perceptual_hash, expected_perceptual_hash)
        self.assertEqual(signature.frame_hashes, [frames[0].perceptual_hash])
        self.assertEqual(signature.frame_sha256, [frames[0].sha256])


class AssetImportBoundaryTests(unittest.TestCase):
    def test_frame_modules_depend_only_on_shared_primitives(self) -> None:
        imports = {
            FRAME_SAMPLING_MODULE: _module_imports("src/assets/frame_sampling.py"),
            PERCEPTUAL_SIMILARITY_MODULE: _module_imports("src/assets/perceptual_similarity.py"),
        }

        self.assertNotIn(PERCEPTUAL_SIMILARITY_MODULE, imports[FRAME_SAMPLING_MODULE])
        self.assertNotIn(FRAME_SAMPLING_MODULE, imports[PERCEPTUAL_SIMILARITY_MODULE])
        self.assertIn(SHARED_PRIMITIVES_MODULE, imports[FRAME_SAMPLING_MODULE])
        self.assertIn(SHARED_PRIMITIVES_MODULE, imports[PERCEPTUAL_SIMILARITY_MODULE])


def _module_imports(relative_path: str) -> set[str]:
    path = REPOSITORY_ROOT / relative_path
    module_name = relative_path.removesuffix(".py").replace("/", ".")
    is_package = module_name.endswith(".__init__")
    if is_package:
        module_name = module_name.removesuffix(".__init__")
    package_parts = module_name.split(".") if is_package else module_name.split(".")[:-1]
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                prefix = package_parts[: len(package_parts) - node.level + 1]
                base = ".".join([*prefix, node.module] if node.module else prefix)
            elif node.module:
                base = node.module
            else:
                continue
            imports.add(base)
            imports.update(f"{base}.{alias.name}" for alias in node.names)
    return imports


if __name__ == "__main__":
    unittest.main()
