# OpenAI Semantic Vision Controlled Live Evaluation

## Summary

- Live evaluation executed: true
- Calls attempted/succeeded/failed: 6/6/0
- External HTTP attempts: 6
- Images sent: 6
- Retries observed: 0
- Total calculated cost USD: 0.11225
- Classification accuracy: 0.666667
- Status normalization: OpenAI structured result status `completed` was treated as successful; no additional API calls were made.
- Pricing basis: gpt-5.6-terra short-context rates from OpenAI model pricing, input $2.50/1M tokens and output $15.00/1M tokens; cached tokens were 0.

## Metrics

- suitable_accuracy: 0.333333
- unsuitable_accuracy: 1.0
- review_case_result: review
- subject_accuracy: 1.0
- action_accuracy: 1.0
- environment_accuracy: 1.0
- exact_entity_accuracy: 1.0
- must_have_accuracy: 1.0
- negative_element_accuracy: 1.0
- false_hard_reject_count: 0
- false_suitable_count: 0
- structured_response_validity: 1.0
- failed_calls: 0
- total_input_tokens: 9338
- total_output_tokens: 5927
- total_calculated_cost_usd: 0.11225

## Required Answers

- Отличила ли модель Saturn V от Space Shuttle: yes
- Отличила ли модель медведя с рыбой от медведя без рыбы: yes
- Отличила ли модель лес от пустыни: yes
- Не завысила ли confidence для действия на одном изображении: yes
- Корректно ли обработала illustrative scene: yes
- Подходит ли detail=low для дальнейшего использования: no
- Нужен ли повтор отдельных случаев на detail=high: yes

## Candidate Results

- scene_01_strict_saturn_v / scene01_A_saturn_v_launch: expected=suitable, returned=review, score=0.74, confidence=0.96, status=success, request_id=req_45e31fbbde6b4b3e83f08a65a48c34b7
  mismatch_reasons: The viewpoint is elevated and relatively close/moderate rather than clearly a ground-level or telephoto wide launch shot.
  review_required_reasons: Exact Saturn V identification is strongly supported by visible vehicle geometry but is not independently confirmed by legible markings or text in the frame., Only one still frame is available, so temporal launch progression cannot be assessed.
  evidence: Large white launch vehicle visibly matches the characteristic overall form of a Saturn V more closely than a Space Shuttle stack.
- scene_01_strict_saturn_v / scene01_B_space_shuttle_launch: expected=unsuitable, returned=unsuitable, score=0.666667, confidence=0.99, status=success, request_id=req_c32868f85e614c00a781680aa68514ed
  mismatch_reasons: The required exact entity, a Saturn V rocket, is not visible., The visible vehicle is a Space Shuttle launch system., A Space Shuttle orbiter is explicitly listed as a negative element under the strict scene requirements.
  review_required_reasons: Visible 'USA' marking on the orbiter creates text/logo review risk., Only one still frame is available, so temporal evidence is limited.
  evidence: Vehicle geometry visibly matches a Space Shuttle configuration—orbiter, external tank, and twin solid rocket boosters—and does not match Saturn V.
- scene_02_balanced_bear_salmon / scene02_A_bear_catching_salmon: expected=suitable, returned=suitable, score=1.0, confidence=0.98, status=success, request_id=req_43b791f57a944661a0a2811f45748bed
  mismatch_reasons: The fish is visibly present but cannot be confirmed as salmon rather than another fish species from this image alone., A single still frame cannot conclusively verify the complete catching sequence, though the visible composition strongly depicts an attempted catch.
  evidence: A brown bear is clearly visible as the primary subject.
- scene_02_balanced_bear_salmon / scene02_B_bear_standing_river: expected=review, returned=review, score=0.666667, confidence=0.96, status=success, request_id=req_55528c7158ea4bd8bf338762afdd44d0
  mismatch_reasons: The required action, catching salmon, is not visibly shown., A salmon or other fish is required but absent from the visible frame., The exact requested entity/action combination, a brown bear catching salmon, is not met., Waterfall or rapids are not visible; only shallow river water and a rocky bank are shown., The frame visibly matches the prohibited condition of a bear only standing.
  review_required_reasons: Only one still frame is available, so an event outside this visible instant cannot be evaluated., The bear's species is visually consistent with a brown bear, but species-level certainty from one image is not absolute.
  evidence: A single brown-furred bear is centered in the frame.
- scene_03_illustrative_forest_broll / scene03_A_misty_forest_canopy: expected=suitable, returned=review, score=0.74, confidence=0.95, status=success, request_id=req_8c52842301c041cfab199503065db2c0
  mismatch_reasons: The requested camera view allows a wide or elevated landscape view, while the visible frame is a more enclosed upward-looking view through trees and canopy., The frame does not visibly establish a broad landscape canopy vista; it primarily shows trunks, branches, and fog from within the forest.
  review_required_reasons: Only one still frame was provided, so temporal characteristics cannot be evaluated beyond the visible static image., Mist is strongly suggested by the pale diffuse background and haze among trees, but its density and extent cannot be assessed outside the visible frame.
  evidence: A dense stand of trees and leafy canopy is visibly present throughout the frame.
- scene_03_illustrative_forest_broll / scene03_B_desert_dunes: expected=unsuitable, returned=unsuitable, score=0.5, confidence=0.99, status=success, request_id=req_6d1a623c2c7041708c0bd976f06e89ee
  mismatch_reasons: The required forest-canopy subject is absent., The required green, humid or misty natural woodland environment is absent., Desert and sand dunes, both listed negative elements, are prominently visible., Although the frame is a wide atmospheric landscape view, it depicts an arid dune field rather than the requested forest setting.
  evidence: No trees or forest canopy are visible; the primary visible subject is a dune landscape.
