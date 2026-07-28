from __future__ import annotations


def main(
    argv: list[str] | None = None,
    *,
    prog: str = "python -m ai_youtube",
) -> int:
    """Run the active content_creator command surface."""
    from src.content_creation.cli import (
        build_parser,
        configure_console_encoding,
        run_content_creation_cli,
    )

    configure_console_encoding()
    parser = build_parser(prog=prog)
    args = parser.parse_args(argv)
    return run_content_creation_cli(args)


__all__ = ["main"]
