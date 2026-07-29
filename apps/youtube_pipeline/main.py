from __future__ import annotations


def main() -> int:
    from src.ai_youtube.apps.legacy_pipeline.adapter import (
        main as legacy_main,
    )

    legacy_main()
    return 0
