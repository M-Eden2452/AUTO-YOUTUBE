# Visual Review Bundle Schema

Static review bundles are written under a project asset folder:

- JSON manifest: `assets/review/visual_review_manifest.json`
- HTML board: `assets/review/visual_review_board.html`

The bundle is additive. It does not replace or mutate `assets_manifest.json`; the news asset manifest may include a pointer to this review output.

## Top-Level Manifest

```json
{
  "schema_version": "visual_review_bundle.v1",
  "generated_at": "ISO-8601 UTC timestamp",
  "project_id": "string",
  "scenes": [],
  "summary": {
    "scene_count": 0,
    "analysed_candidates": 0,
    "preview_cache_hits": 0,
    "preview_cache_misses": 0,
    "failed_previews": 0,
    "exact_duplicates": 0,
    "near_duplicates": 0,
    "review_required_candidates": 0,
    "selected_candidates": 0,
    "missing_scenes": 0
  },
  "html_board_path": "relative path when generated"
}
```

## Scene Bundle

Each `scenes[]` entry contains:

- `project_id`: project identifier.
- `scene_id`: scene identifier.
- `scene_text`: source scene text.
- `semantic_scene`: existing semantic scene payload when present.
- `target_duration_sec`: target scene duration.
- `target_aspect_ratio`: requested output aspect ratio.
- `metadata_queries`: semantic/provider query records when present.
- `provider_routing`: provider routing diagnostics when present.
- `shortlist`: top metadata candidates analysed for previews.
- `candidates`: analysed candidate records.
- `selected_candidate`: candidate selected after metadata rank or explicit technical rerank.
- `alternatives`: remaining shortlist candidates.
- `manual_fallback_status`: Envato/manual fallback status when applicable.

## Candidate Record

Each candidate record includes:

- `candidate`: public candidate metadata, license and provenance summary.
- `metadata_rank`: 1-based metadata shortlist rank.
- `metadata_score`: existing metadata score.
- `preview`: resolved preview/cache status.
- `sampled_frames`: image frame or extracted video frames.
- `technical_metrics`: local heuristic metrics.
- `perceptual_signature`: SHA-256 and perceptual hashes.
- `similarity`: exact and near-duplicate comparison results.
- `duplicate_penalty`: duplicate/repetition penalty.
- `neighbor_similarity_penalty`: similarity penalty against neighboring/project assets.
- `project_repetition_count`: count of prior matching references.
- `crop_suitability`: separate heuristic crop scores for target ratios.
- `technical_rank`: rank after deterministic technical scoring.
- `combined_deterministic_score`: reproducible score used only when rerank is enabled.
- `score_breakdown`: metadata, technical, crop, duplicate and neighbor components.
- `rejection_reasons`: hard rejection reasons such as blocked license or invalid preview.
- `review_required_reasons`: reasons that should be inspected by a human.
- `analysis_status`: `analysed`, `failed`, or fallback status.
- `analysis_error`: captured error text when analysis fails.

## HTML Board Rules

The generated HTML board is static and local:

- Uses relative paths for local previews and sampled frames.
- Does not include secrets or raw `.env` values.
- Does not embed Envato certificate/proof content.
- Does not run external JavaScript requests.
- Does not contain controls that mutate manifests or project files.
- May link to public source pages.

## Compatibility Notes

This schema deliberately avoids semantic content claims. Crop, blur, sharpness and repetition fields are technical heuristics, not object, face, logo or subject detection.
