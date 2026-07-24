# Stage 2B: CLI Reference

Independent CLI, not wired into `pipeline.py`:

```bash
./venv/Scripts/python.exe -m src.project_foundation.cli <group> <command> [options]
```

Global options (apply to every command):

- `--channels-root <dir>` - default `channels`
- `--projects-root <dir>` - default `projects`

No command performs network access, rendering, or requires an API key.
Machine-readable commands print JSON to stdout; errors print
`{"error": "..."}` to stderr and the process exits with a non-zero code.

## Channels

```bash
./venv/Scripts/python.exe -m src.project_foundation.cli channels list
./venv/Scripts/python.exe -m src.project_foundation.cli channels show <channel_id>
./venv/Scripts/python.exe -m src.project_foundation.cli channels create --config <path/to/channel.json>
./venv/Scripts/python.exe -m src.project_foundation.cli channels validate --config <path/to/channel.json>
```

`channels create` refuses to overwrite an existing `channel_id`.
`channels validate` never writes anything; it only reports
`{"valid": bool, "errors": [...]}`.

`--config` for `channels create`/`validate` is a JSON file with
`ChannelProfile` fields, e.g.:

```json
{
  "channel_id": "example_channel",
  "display_name": "Example Channel",
  "default_language": "ru",
  "supported_languages": ["ru"],
  "default_application": "content_creator",
  "default_format": "vertical_short",
  "default_template": "story_card_text_only_v1",
  "export_targets": ["youtube_shorts"],
  "output_policy": {"allow_unknown_license": true}
}
```

## Projects

```bash
./venv/Scripts/python.exe -m src.project_foundation.cli projects create --config <path/to/project.json> [--dry-run]
./venv/Scripts/python.exe -m src.project_foundation.cli projects show <project_id>
./venv/Scripts/python.exe -m src.project_foundation.cli projects list
./venv/Scripts/python.exe -m src.project_foundation.cli projects evidence-list <project_id>
./venv/Scripts/python.exe -m src.project_foundation.cli projects rights-report <project_id>
./venv/Scripts/python.exe -m src.project_foundation.cli projects validate <project_id>
```

`projects create` looks up `channel_id` via `--channels-root`, inherits
`default_application` / `default_format` / `default_template` / `language`
/ `export_targets` from the channel profile, and lets the config file
override any of them explicitly. `--dry-run` computes and prints the full
result (including the `project_id` that would be generated) without
writing any file or directory. Without `--dry-run`, it refuses to
overwrite an existing project.

`--config` for `projects create` is a JSON file, e.g.:

```json
{
  "channel_id": "example_channel",
  "title": "My First Project",
  "project_id": "optional_explicit_id",
  "source_type": "manual",
  "metadata": {}
}
```

`projects rights-report` regenerates and saves
`projects/<project_id>/evidence/rights_report.json` and also prints it.

`projects validate` loads the project's channel, parses its
`output_policy`, loads the evidence bundle, and prints a `ValidationResult`
(`exit code 0` when `allowed: true`, `1` otherwise).

## Exit codes

- `0` - success (including `channels/projects validate` reporting `valid`/`allowed: true`).
- `1` - validation failed, entity not found, duplicate creation attempted, or corrupted JSON encountered.
