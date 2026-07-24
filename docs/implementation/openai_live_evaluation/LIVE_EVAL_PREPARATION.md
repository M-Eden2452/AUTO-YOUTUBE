# Live Evaluation Preparation

Date: 2026-07-23
Phase: prepared

## Scope

Prepared a controlled real evaluation set for a future OpenAI Semantic Vision Backend run. This preparation did not execute live OpenAI calls, paid calls, semantic rerank, production selection changes, Envato downloads, original/master downloads, or media index changes.

A correction was applied before owner approval: the future command now uses an explicit `--dataset` path so it cannot accidentally load the default synthetic harness dataset. Still-image candidates now send only one canonical image (`frame_000`) per candidate; crop variants remain visible only in the contact sheet.

Final pre-live blocker correction: the explicit dry-run previously loaded the correct dataset and produced 6 calls / 6 images, but `budget_allowed` stayed false because the persistent config intentionally keeps `openai.enabled=false`, `allow_paid_vision=false`, `maximum_budget_usd=0`, and `maximum_calls_per_project=0`. Runtime authorization is now computed only in memory for the controlled owner-approved CLI gates and does not write back to `config/semantic_visual.json`.

## Dataset Summary

- Dataset path: `docs/implementation/openai_live_evaluation/LIVE_EVAL_DATASET.json`
- Scenes: 3
- Candidates: 6
- Contact-sheet frames: 12
- Future API images: 6
- Future projected calls: 6
- Model: `gpt-5.6-terra`
- Detail: `low`
- Reasoning effort: `low`
- Mode: `analyse_and_report`
- Proposed hard budget cap: 0.50 USD
- Exact cost asserted: false
- Live calls performed: false
- Paid calls performed: false
- Production selection changed: false
- Semantic rerank enabled: false

## Selected Scenes And Sources

- `scene_01_strict_saturn_v` (strict):
  - Candidate A `scene01_A_saturn_v_launch`: wikimedia `6739626`, Apollo 11 Launch2.jpg; source: https://commons.wikimedia.org/wiki/File:Apollo_11_Launch2.jpg; expected: suitable
  - Candidate B `scene01_B_space_shuttle_launch`: wikimedia `199486`, Space Shuttle Columbia launching.jpg; source: https://commons.wikimedia.org/wiki/File:Space_Shuttle_Columbia_launching.jpg; expected: unsuitable
- `scene_02_balanced_bear_salmon` (balanced):
  - Candidate A `scene02_A_bear_catching_salmon`: wikimedia `147045132`, Brown Bear catching Salmon.jpg; source: https://commons.wikimedia.org/wiki/File:Brown_Bear_catching_Salmon.jpg; expected: suitable
  - Candidate B `scene02_B_bear_standing_river`: wikimedia `159122245`, Brown Bear standing in river (50377060656).jpg; source: https://commons.wikimedia.org/wiki/File:Brown_Bear_standing_in_river_%2850377060656%29.jpg; expected: review
- `scene_03_illustrative_forest_broll` (illustrative):
  - Candidate A `scene03_A_misty_forest_canopy`: wikimedia `193453163`, Foggy Forest Canopy in the Anamalai Hills, Valparai 01.jpg; source: https://commons.wikimedia.org/wiki/File:Foggy_Forest_Canopy_in_the_Anamalai_Hills%2C_Valparai_01.jpg; expected: suitable
  - Candidate B `scene03_B_desert_dunes`: wikimedia `145015263`, Utah Dunes Landscape - West Desert District.jpg; source: https://commons.wikimedia.org/wiki/File:Utah_Dunes_Landscape_-_West_Desert_District.jpg; expected: unsuitable

## Corrections

- `--dataset` was added to `semantic-backend evaluate`; without it, the old default `config/semantic_visual_eval.json` remains the backward-compatible default.
- Explicit dataset paths are required to exist; missing paths block evaluation.
- Explicit datasets expose dataset path, scenes, candidates, projected calls and image count in CLI output.
- Still images use `media_type=image`, `is_poster_frame=true` on the canonical API frame, and `limited_temporal_evidence=true`.
- `scene_03_illustrative_forest_broll` now stores `expected_action_match=null` and `expected_exact_entity_match=null`; metrics ignore those not-applicable criteria.
- A controlled runtime gate was added for this prepared dataset only. It authorizes the dry-run budget guard only when the explicit dataset exists, the counts are exactly `scenes=3`, `candidates=6`, `projected_calls=6`, `projected_image_count=6`, the model is `gpt-5.6-terra`, detail is `low`, one canonical image per candidate is used, the paid Vision CLI gates are present, the budget is at most 0.50 USD, max calls are at most 6, the confirmation phrase matches exactly, the API key is configured but never printed, semantic rerank is false, and production selection remains unchanged.


## Verification

- Explicit dry-run via project Python loaded `docs/implementation/openai_live_evaluation/LIVE_EVAL_DATASET.json` and reported `scenes=3`, `candidates=6`, `projected_calls=6`, `projected_image_count=6`, `valid_requests=6`, `invalid_requests=0`, `schema_valid=True`, `runtime_authorized=True`, and `budget_allowed=True`.
- Targeted tests passed with project Python: `.\venv\Scripts\python.exe -B -m unittest tests.test_semantic_visual_evaluation tests.test_semantic_visual_openai_backend` -> `Ran 50 tests`, `OK`.
- Persistent config defaults remain disabled: OpenAI backend disabled, paid Vision disabled, budget 0, call limit 0, semantic rerank disabled.
- Live calls performed: false.
- Paid calls performed: false.

## Future Command

Do not execute this during preparation. It is recorded for a separate owner-approved live task:

```powershell
.\venv\Scripts\python.exe -B pipeline.py semantic-backend evaluate --backend openai --model gpt-5.6-terra --dataset docs/implementation/openai_live_evaluation/LIVE_EVAL_DATASET.json --allow-paid-vision --budget-usd 0.50 --max-calls 6 --confirm-paid-vision LIVE_VISION_APPROVED
```

## Dry-Run Command Used For Preparation

```powershell
.\venv\Scripts\python.exe -B pipeline.py semantic-backend evaluate --backend openai --model gpt-5.6-terra --dataset docs/implementation/openai_live_evaluation/LIVE_EVAL_DATASET.json --dry-run --allow-paid-vision --budget-usd 0.50 --max-calls 6 --confirm-paid-vision LIVE_VISION_APPROVED
```

## Artifacts

- `docs/implementation/openai_live_evaluation/LIVE_EVAL_DATASET.json`
- `docs/implementation/openai_live_evaluation/LIVE_EVAL_PAYLOADS_SANITIZED.json`
- `docs/implementation/openai_live_evaluation/LIVE_EVAL_CONTACT_SHEET.html`
- `docs/implementation/openai_live_evaluation/LIVE_EVAL_DRY_RUN.txt`
- `docs/implementation/openai_live_evaluation/LIVE_EVAL_CHECKPOINT.json`
