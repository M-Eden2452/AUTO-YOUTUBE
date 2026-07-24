# Evaluation Dataset Schema

The evaluation dataset lives at:

```text
config/semantic_visual_eval.json
```

It is a mock-only dataset for controlled semantic backend comparison. It does not read or mutate project manifests, production selection or `media_index.json`.

## Top-Level Fields

- `schema_version`: currently `semantic_visual_eval.v1`.
- `models`: model labels available for comparison, including `mock`, `gpt-5.6-terra` and `gpt-5.6-luna`.
- `cases`: list of evaluation cases.

## Case Fields

- `case_id`: stable case identifier.
- `category`: behavioral category such as `wrong_subject` or `negative_element_present`.
- `strictness`: one of `strict`, `balanced`, `illustrative`.
- `frame_count`: number of sampled frames to build for the request.
- `media_type`: `video` or `image`.
- `expected`: expected classification/range fields, not exact floats.

## Expected Fields

The harness interprets expected fields as classifications:

- `subject`: `match` or `mismatch`.
- `action`: `match` or `mismatch`.
- `environment`: `match` or `mismatch`.
- `location`: optional `match` or `mismatch`.
- `exact_entity`: optional `match` or `mismatch`.
- `must_have_present`: boolean.
- `negative_present`: boolean.

Metrics are calculated by comparing expected classifications with score bands and term detections. This avoids overfitting to a single exact float.

## Required Case Coverage

The current dataset includes:

- correct subject/action/environment;
- wrong subject;
- wrong action;
- wrong location;
- exact entity mismatch;
- missing must-have;
- negative element present;
- generic acceptable B-roll;
- one misleading frame;
- poster-only video;
- low confidence;
- strict scene;
- balanced scene;
- illustrative scene.

## Metrics

The harness reports:

- subject classification accuracy;
- action classification accuracy;
- environment accuracy;
- must-have precision and recall;
- negative detection precision and recall;
- hard-reject false-positive rate;
- review-required rate;
- structured-output validity;
- cache hit rate;
- latency;
- estimated cost;
- score stability.
