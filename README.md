# AI-YouTube

Local MVP pipeline for structured YouTube video production. The current project renders a short Jordan Peterson quote preview, stores the video data as JSON plans, generates YouTube metadata, and exports a Markdown note for Obsidian.

## Install

```bash
python -m venv venv
source venv/Scripts/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

PowerShell activation:

```powershell
.\venv\Scripts\Activate.ps1
```

## Dev Preview

```bash
python pipeline.py --dev
```

Expected outputs:

- `outputs/final_preview.mp4`
- `outputs/quote_plan.json`
- `outputs/scene_plan.json`
- `outputs/asset_plan.json`
- `outputs/render_plan.json`
- `outputs/self_eval.json`
- `outputs/youtube_metadata.json`
- `outputs/obsidian_note_preview.md` or an Obsidian vault note

Dev mode is intentionally short and fast: 7 seconds, 1280x720, 15 fps by default.

## Production Mode

```bash
python pipeline.py --prod
```

Production mode uses `prod_resolution`, `prod_fps`, and `prod_scene_duration` from `config/video_style.json`. It is a foundation for longer 4-10 minute renders, multiple scenes, intros, transitions, B-roll, and future voice-over.

## Obsidian Export

Obsidian export is configured in:

```text
config/video_style.json
```

Current block:

```json
"obsidian": {
  "enabled": true,
  "vault_path": "G:\\ObsidianBase\\ObsidianBase",
  "folder": "YouTube/Quotes",
  "note_template": "quote_video",
  "write_json_links": true,
  "write_asset_links": true,
  "fallback_to_outputs": true
}
```

If `vault_path` exists, the note is saved to:

```text
G:\ObsidianBase\ObsidianBase\YouTube\Quotes
```

If the vault path does not exist, the pipeline does not fail. It writes:

```text
outputs/obsidian_note_preview.md
```

Run only the export step from existing outputs:

```bash
python pipeline.py --export-obsidian
```

Disable Obsidian export for one run:

```bash
python pipeline.py --dev --no-obsidian
```

Skip rendering and update metadata plus Obsidian:

```bash
python pipeline.py --dev --skip-render
```

## What Goes Into Obsidian

The Markdown note includes:

- Status
- Core video data
- Quote text
- Title ideas
- YouTube description, tags, keywords, thumbnail idea
- Visual style settings
- Assets
- Links to production JSON plans
- Next actions
- Manual notes block
- Self-eval checks and warnings

## Config

Change styles and paths in:

```text
config/video_style.json
```

Important fields:

- `visual_style`
- `image_style`
- `intro_style`
- `layout`
- `resolution`
- `fps`
- `scene_duration`
- `font_path`
- `font_size`
- `text_color`
- `background_color`
- `music_path`
- `music_volume`
- `animation_type`
- `transition_type`

For Cyrillic text, keep a full Windows font path:

```json
"font_path": "C:/Windows/Fonts/arial.ttf"
```

## Assets

Music goes here:

```text
music/background.mp3
```

If music is missing, the pipeline renders a silent fallback.

Images go here:

```text
assets/images/
```

Example:

```text
assets/images/jordan_peterson.jpg
```

If no image is found, the pipeline creates a dark placeholder and continues.

## API Keys

The MVP does not require API keys. Later stages may use:

- `OPENAI_API_KEY` for scripts, structured plans, and intro image generation
- `PEXELS_API_KEY` for asset search
- `ELEVENLABS_API_KEY` for voice-over

Create `.env` from `.env.example`. Never commit `.env`.

## GSD/Superpowers Workflow

The intended implementation loop is:

1. Check `git status`.
2. Commit the known-working state before risky changes.
3. Make a small architectural change.
4. Run `python pipeline.py --dev`.
5. Verify outputs and self-eval.
6. Commit only safe source/config/docs/JSON/Markdown files.

The pipeline favors structured intermediate representations:

- quote plan
- scene plan
- asset plan
- render plan
- YouTube metadata
- Obsidian note

This keeps the system debuggable and makes it easier to expand from previews to production videos.

## Safe Commit Before Large Changes

```bash
git status
git add .
git status --short
git commit -m "working MVP before large change"
```

Before committing, confirm these are not staged:

- `.env`
- `venv/`
- `outputs/*.mp4`
- `outputs/*.mov`
- `outputs/*.wav`
- `outputs/*.mp3`
- `assets/broll/`
- `music/*.mp3`

## Rollback

If you need to throw away local changes and return to the last commit:

```bash
git reset --hard HEAD
```

Use this carefully. It deletes uncommitted changes.
