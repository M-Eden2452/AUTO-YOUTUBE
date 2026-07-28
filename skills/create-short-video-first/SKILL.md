---
name: create-short-video-first
description: Create a new AI-YouTube Short through the existing content-creation workflow, prioritizing an early honest video draft and preserving paid-call, rights, and publish-readiness gates. Use for requests to create, draft, or prototype a Short from a topic, text, script, article, or local visual asset.
---

# Create Short Video First

Use the existing application service; do not build a parallel pipeline.

## Workflow

1. Read [AGENTS.md](../../AGENTS.md) and
   [CURRENT_STATE.md](../../docs/current/CURRENT_STATE.md).
2. Run `git status --short --branch`.
3. Inspect current choices:

   ```powershell
   .\venv\Scripts\python.exe -m src.content_creation.cli capabilities --json
   ```

4. Select only an enabled application, format, template and channel.
   - Prefer `fullscreen_voiceover_v1` for a narrated fullscreen Short.
   - Use `story_card_text_only_v1` only when the user supplies the required local
     visual and card text.
5. Start with `--dry-run` or `--prepare-only` whenever the requested output does not
   require live providers or paid TTS.
6. Before a provider search, download, Vision or TTS call, state the exact external
   action and obtain explicit user approval. Add `--approve-paid-generation` only for
   an approved ElevenLabs generation.
7. Keep `strict` as the default. Use `--completion-mode draft_complete` only when the
   user accepts a non-publish-ready draft. Never describe that output as publish-ready.
8. Inspect the returned project ID, `project status --json`, output manifests and the
   actual video path. Do not infer completion from a top-level status alone.
9. Run only targeted tests if code changed. Do not rerender unrelated projects.

## Guardrails

- Do not edit manifests manually to force completion.
- Do not bypass unknown-license, rights-blocked, `must_avoid`, conflict or misleading
  content gates.
- Do not create a second renderer, provider path, project store or completion ladder.
- Do not overwrite existing MP4/WAV or user media.
