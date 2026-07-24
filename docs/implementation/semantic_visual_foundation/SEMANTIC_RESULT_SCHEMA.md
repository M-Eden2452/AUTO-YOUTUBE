# Semantic Visual Result Schema

Semantic visual analysis is additive to `visual_review_manifest.json`. It does not replace metadata, technical, crop, duplicate or selected-candidate fields.

## SceneVisualRequirements

Normalized scene requirements:

- `scene_id`
- `scene_text`
- `subject`
- `secondary_subjects`
- `action`
- `environment`
- `location`
- `exact_entity`
- `must_have`
- `negative_elements`
- `shot_type`
- `camera_view`
- `mood`
- `time_period`
- `weather`
- `target_aspect_ratio`
- `scene_purpose`
- `acceptable_alternatives`
- `semantic_strictness`: `strict`, `balanced` or `illustrative`

The current `SemanticScene` schema is adapted into this model by `SceneVisualRequirements.from_current_semantic_scene()`.

## SemanticVisualRequest

Public serialized request fields:

- `request_version`
- `project_id`
- `scene_id`
- `backend`
- `requirements`
- `candidate_id`
- `provider`
- `candidate_metadata`
- `sampled_frame_references`
- `technical_metrics_summary`
- `maximum_frames`
- `backend_options`

The public request omits API keys, certificate/proof fields, raw metadata, base64 images and absolute local paths.

## Sampled Frame Reference

Each frame reference includes:

- `frame_index`
- `sha256`
- `perceptual_hash`
- `relative_path`
- `width`
- `height`
- `requested_timestamp_sec`
- `actual_timestamp_sec`
- `extraction_status`
- `is_poster_frame`
- `technical_metrics`

## SemanticVisualResult

Structured result fields:

- `result_version`
- `backend`
- `model`
- `backend_version`
- `request_version`
- `analysed_at`
- `status`
- `confidence`
- `frames_analysed`
- `frame_observations`
- `aggregate_scores`
- `must_have_results`
- `negative_element_results`
- `mismatch_reasons`
- `review_required_reasons`
- `evidence`
- `semantic_score`
- `hard_reject`
- `cache_key`
- `raw_response_reference`
- `error`

`raw_response_reference` may point to a future sanitized diagnostic record. Raw provider responses are not stored in the review bundle.

## Frame Observation

Each observation includes:

- `frame_index`
- `subject_observations`
- `action_observations`
- `environment_observations`
- `location_observations`
- `shot_type_observations`
- `temporal_observations`
- `visible_text_or_logo_risk`
- `unwanted_element_observations`
- `confidence`
- `short_evidence_summary`

## Aggregate Scores

All scores are validated in the `0.0` to `1.0` range:

- `subject_match`
- `action_match`
- `environment_match`
- `location_match`
- `exact_entity_match`
- `must_have_match`
- `negative_element_safety`
- `shot_type_match`
- `mood_match`
- `temporal_match`
- `overall_semantic_match`

Semantic score is not mixed with technical score inside backend results.

## Term Check Result

Must-have and negative term checks use:

- `term`
- `present`
- `confidence`
- `evidence`
- `frame_indices`

## Review Bundle Candidate Fields

When semantic analysis exists, candidate records may include:

- `semantic_analysis`
- `semantic_rank`
- `semantic_score`
- `semantic_status`
- `semantic_review_required`

`semantic_analysis` contains only status, backend, model, confidence, aggregate scores, must-have results, negative results, mismatch reasons, review-required reasons, evidence, semantic score, hard reject and cache key.

## Aggregation Rules

- Multiple frames are preferred; a one-frame video/poster is marked `limited_temporal_evidence`.
- A single frame caps action match at `0.65`.
- Low-confidence must-have misses become review-required instead of hard proof.
- High-confidence negative findings hard reject only at or above `hard_reject_confidence` with consistent frame evidence.
- One anomalous frame creates a review-required reason without dominating the aggregate score.
- Timeout, invalid or configuration failures produce structured fallback results and leave production selection to metadata/technical ranking.

## Cache Record

Semantic cache records are JSON files:

```text
assets/semantic_cache/<sha256>/semantic_result.json
```

Each record stores:

- `schema_version`
- `cache_key`
- `result`

The cache key includes backend, model, backend version, request schema version, normalized requirements, candidate id, provider, frame hashes, semantic config and prompt/template version.
