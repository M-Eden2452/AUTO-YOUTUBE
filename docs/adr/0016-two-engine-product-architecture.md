# ADR 0016: Two application engines over one shared production platform

Date: 2026-07-29

Status: accepted as the target boundary for rescue stage 9B; no capability was
enabled by this decision

## Context

The owner wants two product families:

1. create short and long videos from a topic, script, text, URL, stock media,
   local media, and other approved asset methods;
2. extract and reframe clips from long source videos such as streams,
   animation, films, and podcasts.

The repository already contains the necessary foundations:

- active `content_creator` workflows and a production catalog with short and
  planned longform formats;
- a planned/disabled `video_repurposer` catalog entry;
- the working local-MP4 Anime Factory pipeline for transcription, audio/scene
  analysis, candidate selection, crop, subtitles, preview, and render;
- shared project, workspace, rights, provider/assets, audio/TTS/music,
  subtitles, rendering, and export components.

Creating new project systems, provider contracts, subtitle engines, audio
stacks, or render pipelines for either product family would duplicate existing
code. Treating documentary as a third application would also encourage a third
copy of the same platform.

## Decision

- The target product has two application engines:
  `content_creator` and `video_repurposer`.
- `content_creator` owns creation of both short and long videos. Documentary is
  a future workflow/template in this application, not a separate application.
- `video_repurposer` is a required target application. The existing Anime
  Factory is its migration source and must be generalized or moved, not
  reimplemented.
- Anime, stream, film, and podcast differences are expressed as templates,
  policies, and bounded strategies over one source-to-clips workflow. A new
  source type does not receive a copied pipeline.
- Both applications reuse the existing catalog, project/workspace, rights,
  assets/providers, audio/TTS/music, subtitles, rendering/FFmpeg, quality, and
  export owners.
- App-specific candidate scoring, crop/reframing, layout, and orchestration may
  remain inside the owning workflow. A component moves to a shared service only
  after callers prove that it is genuinely shared.
- `video_repurposer` remains disabled until its existing workflow is integrated
  with canonical project/workspace/catalog contracts and targeted evidence
  supports enabling it.
- Project-specific agent documentation and skills remain versioned in the
  repository. An external AI-YouTube-System directory may hold personal/global
  agent resources and generated mirrors, but is not required to run or
  understand the project.

## Relationship to earlier decisions

- ADR 0011 remains the current compatibility boundary: Anime Factory still owns
  runtime behavior until bounded ownership-transfer slices are completed.
- ADR 0013 remains the safety gate for the legacy documentary/Solar paths. This
  ADR changes only the future target: a safe documentary implementation belongs
  under `content_creator` instead of creating a third application.

## Consequences

- No production code, catalog status, CLI command, schema, runtime project, or
  user media changes in this decision.
- Stage 9B must inventory Anime project paths, transcription, subtitles,
  FFmpeg/render helpers, and legacy/shared music paths before selecting moves.
- Stage 9D transfers existing implementation one subsystem at a time without
  copying it; stage 9E retires old owners and wrappers after caller gates.
- New templates are registered only with a real workflow binding and tests;
  placeholder directories and speculative engines are prohibited.
