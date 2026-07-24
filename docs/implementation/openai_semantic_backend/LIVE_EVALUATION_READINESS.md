# Live Evaluation Readiness

This stage is ready for a future controlled live evaluation, but live calls remain disabled now.

## Current Status

- OpenAI backend implemented: yes.
- Responses API path implemented through official Python SDK: yes.
- Image inputs supported: yes.
- Strict structured output implemented: yes.
- Budget guard implemented: yes.
- Evaluation harness implemented: yes.
- Dry-run available: yes.
- Mocked evaluation available: yes.
- Live enabled by default: no.
- Paid calls performed in this stage: no.

## Default Gates

The default configuration blocks live calls:

- `openai.enabled=false`;
- `allow_paid_vision=false`;
- `maximum_budget_usd=0`;
- `maximum_calls_per_project=0`;
- `semantic_rerank_enabled=false`.

## Future Live Evaluation Requirements

A future live evaluation must require all CLI gates together:

```powershell
--allow-paid-vision
--budget-usd <value>
--max-calls <value>
--confirm-paid-vision LIVE_VISION_APPROVED
```

It must also use an allowlisted model, allowed detail (`low` or `high`), candidate/frame limits, project-level usage tracking and a non-zero projected budget.

## Data Safety

Future live evaluation should send only:

- scene visual requirements;
- sanitized candidate metadata;
- sampled frame images from existing extracted frames;
- frame index/timestamp/poster markers;
- technical visual context.

It must not send full project manifests, API keys, absolute paths, license certificates, raw provider responses or irrelevant provenance.

## Readiness Caveats

- Real model quality, latency, token usage and cost were not measured in this stage.
- Exact pricing was not asserted because usage from real API responses was not available.
- The local test interpreter did not need the OpenAI package import path because live calls were prohibited; dependency installation should be verified before a future paid run.
