from __future__ import annotations

import dataclasses
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image


@dataclass
class SampledFrame:
    frame_index: int
    requested_timestamp_sec: float = 0.0
    actual_timestamp_sec: float = 0.0
    local_frame_path: str = ""
    width: int = 0
    height: int = 0
    sha256: str = ""
    extraction_status: str = "pending"
    extraction_error: str = ""
    perceptual_hash: str = ""
    technical_metrics: dict[str, Any] = dataclasses.field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


def sha256_file(path: str | Path) -> str:
    sha = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            sha.update(chunk)
    return sha.hexdigest()


def image_perceptual_hash(path: str | Path, *, hash_size: int = 8) -> str:
    with Image.open(path) as image:
        gray = image.convert("L").resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
        pixels = list(gray.getdata())
    bits = []
    width = hash_size + 1
    for y in range(hash_size):
        row = y * width
        for x in range(hash_size):
            bits.append(1 if pixels[row + x] > pixels[row + x + 1] else 0)
    value = 0
    for bit in bits:
        value = (value << 1) | bit
    return f"{value:0{hash_size * hash_size // 4}x}"
