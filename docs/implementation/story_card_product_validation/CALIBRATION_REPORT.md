# Semantic Calibration Report

- Raw classification accuracy: 0.666667
- Calibrated classification accuracy: 0.833333
- Pairwise ranking accuracy: 3/3
- API calls performed: 0

## Pairwise Rankings

- scene_01_strict_saturn_v: winner `scene01_A_saturn_v_launch`, runner-up `scene01_B_space_shuttle_launch`, margin 0.63, correct=true
- scene_02_balanced_bear_salmon: winner `scene02_A_bear_catching_salmon`, runner-up `scene02_B_bear_standing_river`, margin 0.85, correct=true
- scene_03_illustrative_forest_broll: winner `scene03_A_misty_forest_canopy`, runner-up `scene03_B_desert_dunes`, margin 0.63, correct=true

## Calibrated Decisions

- `scene01_A_saturn_v_launch`: raw `review` (0.74), calibrated `suitable_with_limitations` (0.78); reasons: camera_view_mismatch_non_blocking, raw_review_reclassified_as_suitable_material; limitations: visual_specificity_limited, limited_temporal_evidence
- `scene01_B_space_shuttle_launch`: raw `unsuitable` (0.666667), calibrated `unsuitable` (0.15); reasons: camera_view_mismatch_non_blocking, exact_entity_or_subject_mismatch, confirmed_negative_element, required_element_missing; limitations: limited_temporal_evidence
- `scene02_A_bear_catching_salmon`: raw `suitable` (1.0), calibrated `suitable_with_limitations` (1.0); reasons: none; limitations: visual_specificity_limited, limited_temporal_evidence
- `scene02_B_bear_standing_river`: raw `review` (0.666667), calibrated `unsuitable` (0.15); reasons: exact_entity_or_subject_mismatch, confirmed_negative_element, required_element_missing; limitations: visual_specificity_limited
- `scene03_A_misty_forest_canopy`: raw `review` (0.74), calibrated `suitable_with_limitations` (0.78); reasons: camera_view_mismatch_non_blocking, raw_review_reclassified_as_suitable_material; limitations: limited_temporal_evidence
- `scene03_B_desert_dunes`: raw `unsuitable` (0.5), calibrated `unsuitable` (0.15); reasons: exact_entity_or_subject_mismatch, confirmed_negative_element, required_element_missing; limitations: none
