# Story Card Product Validation Plan

## Goal

Prove the practical quality of the existing AI-YouTube semantic, provider, preview, shadow-ranking, and render modules by producing one isolated vertical Shorts test in `projects/story_card_owl_test/`.

Final topic: "Почему сова может так далеко поворачивать голову".

## Non-Goals

- No new provider, preview, semantic, or render architecture.
- No changes to provider foundation or license foundation unless a concrete bug is found.
- No global automatic semantic selection.
- No production selection changes in existing projects.
- No `.env` changes, API key exposure, Envato downloads, media-index migration apply, browser automation, destructive git operations, or automatic commit.
- No full unittest discovery until the final verification phase.

## Phases

1. `baseline`: Record repo state, media index fingerprint, safe defaults, project target, and resume checkpoint.
2. `decision_calibration`: Add a small semantic decision policy over raw `SemanticVisualResult`, keep raw OpenAI results unchanged, create offline calibration report, and test pairwise ranking on the saved live dataset.
3. `owl_candidate_search`: Create `projects/story_card_owl_test/`, use existing provider routing/search patterns only, collect policy-safe preview candidates, and limit the shortlist to four videos.
4. `temporal_preview_analysis`: Select two best videos, extract frames at approximately 15%, 50%, and 85%, verify SHA-256/perceptual hash diversity, build a contact sheet, and record temporal independence and crop suitability.
5. `controlled_semantic_test`: Run at most one controlled OpenAI temporal test only if the exact gates pass: explicit two-candidate dataset, at most six images, model `gpt-5.6-terra`, detail `low`, paid budget cap 0.20 USD, retries disabled, OpenAI key present, runtime authorization present, and exact confirmation phrase accepted by existing guard.
6. `shadow_ranking`: Compare metadata, technical, crop, temporal semantic, and calibrated semantic winners without changing global production selection.
7. `story_card_render`: Add reusable preset `config/render_presets/story_card_short_v1.json` over existing render modules and render the isolated `final_test.mp4` only if the shadow winner satisfies subject, action, license, margin, original validation, and quality gates.
8. `verification`: Run targeted calibration, temporal, story-card renderer, provider/quality tests, then one full unittest discovery.
9. `reports`: Write project reports and the product-validation snapshot with sanitized paths, costs, calls, source attribution, and known issues.

## Target Scene

- Subject: owl.
- Action: owl visibly turning its head far to the side or backwards.
- Environment: natural-looking close-up or wildlife environment.
- Must-have: owl clearly visible; head visibly changes direction across frames; head-turn movement; no severe obstruction; sufficient resolution for central 9:16 card.
- Negative elements: owl remains completely static; unrelated bird; illustration/cartoon; dead/injured animal; zoo bars dominating frame; text/watermark dominating frame; extreme blur; camera cut instead of actual head movement.
- Semantic strictness: balanced.
- Target aspect ratio: 9:16.

## Output Contract

Project files:

- `projects/story_card_owl_test/final_test.mp4`
- `projects/story_card_owl_test/frame_preview.png`
- `projects/story_card_owl_test/selected_asset.json`
- `projects/story_card_owl_test/visual_review_manifest.json`
- `projects/story_card_owl_test/semantic_temporal_results.json`
- `projects/story_card_owl_test/shadow_recommendation.json`
- `projects/story_card_owl_test/render_manifest.json`
- `projects/story_card_owl_test/story_card_layout.json`
- `projects/story_card_owl_test/sources.json`
- `projects/story_card_owl_test/ATTRIBUTION.md`
- `projects/story_card_owl_test/TEST_REPORT.md`

Product-validation docs:

- `docs/implementation/story_card_product_validation/CALIBRATION_REPORT.md`
- `docs/implementation/story_card_product_validation/TEMPORAL_TEST_REPORT.md`
- `docs/implementation/story_card_product_validation/SHADOW_RANKING_REPORT.md`
- `docs/implementation/story_card_product_validation/STORY_CARD_REPORT.md`
- `docs/implementation/story_card_product_validation/PRODUCT_VALIDATION_SNAPSHOT.json`
- `docs/implementation/story_card_product_validation/TEST_RESULTS.txt`

## Safety Notes

- `assets/library/metadata/media_index.json` is fingerprinted before work and must not change.
- Existing projects under `projects/` and `project_solar_vs_nuclear/` must not be modified.
- Reports must not contain API keys, base64 image payloads, data URLs, or private raw provider responses.
- If no real owl head-turn video is confirmed from previews, create a review board/report and stop before final render.
