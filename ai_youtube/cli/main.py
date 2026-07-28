from __future__ import annotations

from ai_youtube.cli.commands.content_creator import main as run_content_creator


def main(argv: list[str] | None = None) -> int:
    """Dispatch the active application without advertising planned apps."""
    return run_content_creator(argv)


__all__ = ["main"]
