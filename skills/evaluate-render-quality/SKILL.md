---
name: evaluate-render-quality
description: Evaluate an AI-YouTube render using its manifests, local media probing, representative frames, audio presence, and visual review criteria without rerendering or calling external services. Use when asked to inspect, validate, review, compare, or approve an MP4 or project render.
---

# Evaluate Render Quality

Treat technical validity and visual quality as separate gates.

## Workflow

1. Read [AGENTS.md](../../AGENTS.md) and resolve the exact project and MP4.
2. Read, when present:
   - `quality/quality_report.json`;
   - `render/final_render_manifest.json`;
   - `localizations/<language>/output/project_manifest.json`;
   - replacement and visual-review reports.
3. Probe the actual file locally. Confirm at minimum:
   - file exists and is non-empty;
   - video decodes;
   - expected resolution, orientation, duration and frame rate;
   - audio stream exists when the template requires voice;
   - manifest output path points to this file.
4. Inspect representative frames from the beginning, middle, scene boundaries and end.
   Use a temporary directory; do not overwrite project artifacts.
5. Review composition, crop, black frames, frozen/duplicated visuals, subtitle safe zones,
   text clipping, pacing, visual relevance and the final tail.
6. Compare audio duration with video duration and check for premature cut-off, silence,
   clipping and unreadable subtitles.
7. Report one of:
   - `passed` — technical and visual checks passed;
   - `needs_review` — file is usable but a human judgment remains;
   - `blocked` — a concrete technical, rights or content issue prevents delivery.

## Guardrails

- Do not trust a saved `passed` status without inspecting the referenced file.
- Do not call Vision or any external evaluator without explicit approval.
- Do not claim semantic correctness from metadata alone.
- Do not rerender merely to evaluate an existing output.
