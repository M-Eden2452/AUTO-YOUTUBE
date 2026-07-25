"""MVP pipeline for turning a local anime MP4 into vertical Shorts."""

from __future__ import annotations

import sys


for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")
