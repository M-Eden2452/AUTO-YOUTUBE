# Temporal Video Test Report

## Preview Temporal Analysis

- Candidate count: 4
- Positions: [0.15, 0.5, 0.85]
- Preview-only phase: true
- Original downloads during preview phase: 0
- Contact sheet: `projects/story_card_owl_test/assets/review/owl_temporal_contact_sheet.html`

- `pixabay_video_95059`: temporal_independence=true; visible_motion=true; mean_hash_distance=2.666667; mean_pixel_difference=5.598452; crop=0.6
- `pexels_video_34457347`: temporal_independence=true; visible_motion=true; mean_hash_distance=15.333333; mean_pixel_difference=31.02105; crop=0.15
- `pixabay_video_18244`: temporal_independence=true; visible_motion=true; mean_hash_distance=16.0; mean_pixel_difference=32.301432; crop=0.15
- `pexels_video_12709245`: temporal_independence=true; visible_motion=true; mean_hash_distance=5.333333; mean_pixel_difference=7.987196; crop=0.066562

## Controlled OpenAI Temporal Test

- Status: completed
- Model/detail: gpt-5.6-terra / low
- Logical calls: 2
- External HTTP attempts: 2
- Images sent: 6
- Actual cost USD: 0.06904
- Stop reasons: []

- `pixabay_video_18244`: status=success; semantic_score=0.9566; confidence=0.92; calibrated=suitable_with_limitations (0.9566)
  Evidence: A clear owl occupies most of each frame in a tight close-up.; The owl changes from nearly front-facing in the first two frames to a pronounced side-facing orientation in the final frame.; A dark, blurred green foliage background provides a natural-looking wildlife setting.; Consistent scale, background, and composition support a continuous close-up, although still-frame sampling cannot conclusively rule out a cut.; The visible source framing is landscape and the supplied geometry-only 9:16 crop suitability is low.
- `pixabay_video_95059`: status=success; semantic_score=0.6285000000000001; confidence=0.91; calibrated=unsuitable (0.25)
  Evidence: A clear close-up owl is consistently visible and occupies most of the frame.; The sampled head pose remains substantially unchanged; no far sideward or backward turn is visibly established.; The stable tight framing matches a wildlife-style close-up, but the background is too dark to verify habitat context.; No visible text, watermark, bars, cartoon styling, severe blur, or obstruction appears in the sampled frames.
