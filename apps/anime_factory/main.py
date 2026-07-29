from __future__ import annotations


def main() -> int:
    from src.ai_youtube.apps.video_repurposer.workflows.anime_clipper import (
        main as anime_main,
    )

    anime_main()
    return 0
