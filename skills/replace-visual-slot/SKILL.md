---
name: replace-visual-slot
description: Replace one visual assembly slot in an existing AI-YouTube project with a local image or video while recording checksum, provenance, rights evidence, and downstream invalidation. Use when asked to swap, fix, or manually supply media for a specific scene and slot.
---

# Replace Visual Slot

Change only the requested scene and slot.

## Workflow

1. Read [AGENTS.md](../../AGENTS.md).
2. Inspect project status plus `replacement/replacement_queue.json`,
   `replacement/timeline_replacement_map.csv` and the assets manifest.
3. Resolve the exact `project_id`, `scene_id` and `slot_id`. Stop if the target is
   ambiguous.
4. Confirm the local file exists and determine the rights evidence:
   - use `--source-url` when provenance has a source page;
   - use `--license-file` for local license proof;
   - use `--confirm-user-owned` only after the user explicitly confirms ownership/control.
5. Run:

   ```powershell
   .\venv\Scripts\python.exe -m src.content_creation.cli assets replace `
     --project-id <id> --scene-id <scene> --slot-id <slot> --file <media>
   ```

   Add only the applicable provenance/rights flags.
6. Verify the replacement record, copied project asset, checksum and stale downstream
   quality/render state.
7. Resume the same project only when the user wants regenerated downstream artifacts.

## Guardrails

- Do not modify or delete the supplied original file.
- Do not invent a license, source URL or ownership confirmation.
- Do not repeat research, script generation or general provider search.
- Do not mark stale quality/render outputs as current.
