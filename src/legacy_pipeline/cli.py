from __future__ import annotations

import argparse


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Structured AI-YouTube pipeline")
    parser.add_argument(
        "command",
        nargs="?",
        choices=[
            "media-library",
            "provider-diagnostics",
            "envato-manual",
            "visual-preview",
            "semantic-visual",
            "semantic-backend",
            "applications",
            "formats",
            "templates",
            "export-targets",
        ],
        help="Optional maintenance command.",
    )
    parser.add_argument("subcommand", nargs="?", help="Maintenance subcommand, for example analyse or migrate.")
    parser.add_argument("--workspace", default=None, help="Runtime workspace root.")
    parser.add_argument("--paths-config", default=None, help="Optional JSON path configuration.")
    parser.add_argument("--config", default=None, help="Path to base video style config.")
    parser.add_argument(
        "--obsidian-vault",
        default=None,
        help="Optional Obsidian vault root (or set AI_YOUTUBE_OBSIDIAN_VAULT).",
    )
    parser.add_argument("--channel", help="Channel profile id, for example quotes.")
    parser.add_argument("--video", help="Video task id, for example thoughts_too_late_001.")
    parser.add_argument("--dev", action="store_true", help="Build a fast preview render.")
    parser.add_argument("--prod", action="store_true", help="Use production render settings.")
    parser.add_argument("--prod-preview", action="store_true", help="Run production settings on the first scenes.")
    parser.add_argument("--cinematic-preview", action="store_true", help="Render a higher-quality cinematic documentary preview.")
    parser.add_argument("--export-obsidian", action="store_true", help="Only export an Obsidian note from existing outputs.")
    parser.add_argument("--no-obsidian", action="store_true", help="Disable Obsidian export for this run.")
    parser.add_argument("--skip-render", action="store_true", help="Skip render and update only plans/metadata/Obsidian.")
    parser.add_argument("--find-music", action="store_true", help="Update only music_plan.json.")
    parser.add_argument("--refresh-assets", action="store_true", help="Search/download assets again.")
    parser.add_argument("--index-assets", action="store_true", help="Scan assets/library and update media_index.json.")
    parser.add_argument("--clean-temp", action="store_true", help="Remove render_temp and partial temporary files.")
    parser.add_argument("--asset-report", action="store_true", help="Create outputs/asset_library_report.md.")
    parser.add_argument("--test-moss-tts", action="store_true", help="Generate a short Russian audio sample with MOSS-TTS-Nano.")
    parser.add_argument("--test-moss-voices", action="store_true", help="Generate MOSS-TTS-Nano voice-clone tests for local reference samples.")
    parser.add_argument("--reuse-voice", action="store_true", default=True, help="Reuse cached scene voice files when text/settings match.")
    parser.add_argument("--skip-voice", action="store_true", help="Skip voice generation and render with music/subtitles only.")
    parser.add_argument("--news-to-short", action="store_true", help="Run the news_to_short mode instead of the legacy pipeline.")
    parser.add_argument("--news-action", choices=["create", "run", "resume"], default="create", help="news_to_short action.")
    parser.add_argument("--projects-root", default=None, help="Root folder for news_to_short jobs.")
    parser.add_argument("--job-id", help="Existing news_to_short job id for run/resume.")
    parser.add_argument("--news-channel", default="nature_science_news_ru", help="Channel profile for news_to_short.")
    parser.add_argument("--url", help="Article URL for news_to_short.")
    parser.add_argument("--urls", action="append", help="Additional article URL for news_to_short.")
    parser.add_argument("--topic", help="Topic or idea for news_to_short.")
    parser.add_argument("--text", help="Inline text input for news_to_short.")
    parser.add_argument("--text-file", help="Text file input for news_to_short.")
    parser.add_argument("--assets", action="append", help="User-owned image/video/audio asset for news_to_short.")
    parser.add_argument("--language", default="ru", help="Localization language for news_to_short.")
    parser.add_argument("--target-duration", type=int, default=55, help="Target duration in seconds for news_to_short.")
    parser.add_argument("--until-stage", help="Run news_to_short until this stage.")
    parser.add_argument("--stage", help="Run only one news_to_short stage.")
    parser.add_argument("--resume", action="store_true", help="Resume a news_to_short job.")
    parser.add_argument("--force-stage", action="store_true", help="Force regeneration of the requested news_to_short stage.")
    parser.add_argument("--dry-run", action="store_true", help="Create cheap news_to_short artifacts without paid APIs or heavy downloads.")
    parser.add_argument(
        "--completion-mode",
        choices=["strict", "draft_complete"],
        default="",
        help="strict (default) or opt-in autonomous draft completion.",
    )
    parser.add_argument(
        "--script-adaptation",
        choices=["none", "light"],
        default="",
        help="Asset-aware script adaptation; empty keeps the project/default setting.",
    )
    parser.add_argument(
        "--execute-voice",
        action="store_true",
        help="Allow the news_to_short voice stage to run real generation. Still requires an existing approval record; without one the safe stub manifest is produced.",
    )
    parser.add_argument("--live", action="store_true", help="Run explicit live diagnostics where supported.")
    parser.add_argument("--open-browser", action="store_true", help="Open Envato public search URL after explicit user request.")
    parser.add_argument("--query", action="append", help="Manual provider query; can be passed more than once.")
    parser.add_argument("--limit", type=int, default=6, help="Manual provider query/result limit.")
    parser.add_argument("--top-k", type=int, default=5, help="Visual preview metadata shortlist size.")
    parser.add_argument("--all-scenes", action="store_true", help="Prepare visual previews for all known scenes.")
    parser.add_argument("--refresh", action="store_true", help="Refresh visual preview cache records.")
    parser.add_argument("--technical-rerank", action="store_true", help="Enable deterministic technical reranking for visual preview.")
    parser.add_argument("--target-aspect", default="9:16", help="Target aspect ratio for visual preview analysis.")
    parser.add_argument("--no-html", action="store_true", help="Skip static HTML visual preview board generation.")
    parser.add_argument("--offline", action="store_true", help="Use cached/local preview assets only.")
    parser.add_argument("--backend", default="", help="Semantic visual backend name for semantic-visual commands.")
    parser.add_argument("--model", default="", help="Semantic backend model for diagnostics/evaluation.")
    parser.add_argument("--dataset", default="", help="Explicit semantic backend evaluation dataset path.")
    parser.add_argument("--allow-paid-vision", action="store_true", help="Future explicit paid Vision gate. Does not enable live calls alone.")
    parser.add_argument("--budget-usd", type=float, default=0.0, help="Future explicit paid Vision budget gate.")
    parser.add_argument("--max-calls", type=int, default=0, help="Future explicit paid Vision call-limit gate.")
    parser.add_argument("--confirm-paid-vision", default="", help="Future explicit paid Vision confirmation phrase.")
    parser.add_argument("--mocked", action="store_true", help="Run semantic backend evaluation using mocked provider responses.")
    parser.add_argument("--maximum-candidates", type=int, help="Maximum candidates for semantic visual analysis.")
    parser.add_argument("--maximum-frames", type=int, help="Maximum sampled frames per candidate for semantic visual analysis.")
    parser.add_argument("--project-id", help="Project id for manual provider commands.")
    parser.add_argument("--scene-id", help="Scene id for manual provider commands.")
    parser.add_argument("--file", help="Local file to import for manual provider commands.")
    parser.add_argument("--source-url", help="Source item URL for manual provider import.")
    parser.add_argument("--item-id", help="Provider item id for manual provider import.")
    parser.add_argument("--author", help="Provider author for manual provider import.")
    parser.add_argument("--license-proof", help="Local certificate/proof file for manual provider import.")
    parser.add_argument("--confirm-project-registration", action="store_true", help="Confirm manual asset is registered to this project.")
    parser.add_argument("--apply", dest="apply_migration", action="store_true", help="Apply media-library migration with explicit safeguards.")
    parser.add_argument("--index-path", help="Media-library index path for analyse/migrate commands.")
    parser.add_argument("--output-path", help="Output path for proposed migrated media index.")
    parser.add_argument("--report-path", help="Output path for media-library analyse/migration report.")
    parser.add_argument("--backup-path", help="Backup path required for media-library migrate --apply.")
    parser.add_argument("--confirm-apply", action="store_true", help="Required with media-library migrate --apply.")
    parser.add_argument("--voice-action", choices=["list", "inspect", "preflight", "import-audio", "approve", "audition"], help="Run safe voice catalog/preflight commands.")
    parser.add_argument("--voice-profile", help="Saved local voice profile id, for example ru_dom.")
    parser.add_argument("--voice-id", help="Provider voice id for voice inspect/preflight.")
    parser.add_argument("--provider", help="Voice provider name for voice commands.")
    parser.add_argument("--audio-file", help="Manual WAV narration file for --voice-action import-audio.")
    parser.add_argument("--approval-scope", choices=["once", "job", "channel_voice_default"], default="job", help="Voice approval scope.")
    parser.add_argument("--application", help="Application id for applications/templates catalog commands.")
    parser.add_argument("--format", help="Format id for formats/templates catalog commands.")
    parser.add_argument("--template", help="Template id or legacy alias for templates inspect.")
    parser.add_argument("--target", help="Export target id for export-targets inspect.")
    parser.add_argument("--json", dest="json_output", action="store_true", help="Print machine-readable JSON for read-only catalog commands.")
    parser.add_argument("--production-plan", choices=["solar_vs_nuclear"], help="Create a reusable YouTube Shorts production plan.")
    parser.add_argument("--production-plan-root", default=None, help="Folder where the production plan project folder will be created.")
    parser.add_argument("--render-production-plan", help="Render an existing production plan project folder.")
    return parser.parse_args(argv)
