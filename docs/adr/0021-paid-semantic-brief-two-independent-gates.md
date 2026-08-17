# ADR 0021: A paid capability needs two independent gates — network is not money

Date: 2026-08-17

Status: accepted; backfilled from the completed PLAN-9B-PRODUCER-M-LIVE slice
(2026-08-09); no new capability enabled by this record, the shipped default
configuration keeps the backend disabled

## Context

`PLAN-9B-PRODUCER-M-LIVE` made the model-assisted semantic `VisualBrief`
adapter reachable from production for the first time — the first *paid
network* capability built after ADR 0019's boundary existed, and the first
place the "network approval is not payment approval" principle (already
implicit in the ElevenLabs and Vision paid gates) had to be stated and tested
as a general rule rather than assumed per-provider.

Before this slice, `NETWORK_ACTIONS` had no class for a text-model call, and
the adapter had no reachable production caller: a live call was impossible
under any permission combination. The risk the slice had to close was the
opposite failure mode from a missing gate — a *single* gate that reads as
"paid" and "networked" at once, so approving one silently approves both.

## Decision

- **Network and payment are answered by two structurally independent
  functions, and neither can satisfy the other's question.**
  `build_semantic_brief_adapter` (`src/content/semantic_brief_openai.py:388-429`)
  returns `None` — the adapter simply does not exist for this run — unless
  **both** are true:
  - `network_action_allowed(NETWORK_ACTION_SEMANTIC_BRIEF)` (`:419`), the
    same ADR 0019 boundary, checked with no special case for this call;
  - `paid_call_blockers(settings) == []` (`:417`), which requires
    `allow_paid_calls` **and** `confirm_paid_calls == LIVE_CONFIRMATION_PHRASE`
    (`"LIVE_SEMANTIC_BRIEF_APPROVED"`, a literal phrase, not a boolean anyone
    could set by accident) **and** a positive `maximum_calls_per_project`
    **and** a positive `maximum_budget_usd` **and** a positive
    `estimated_cost_per_call_usd` (`src/content/semantic_brief_openai.py:164-187`).
- **The network check is repeated immediately before the SDK call, not just
  at adapter construction**, because the `ContextVar` approval backing ADR
  0019 can change between build time and call time within one run.
- **A configured `OPENAI_API_KEY` authorizes neither gate.** It only becomes
  relevant, and only read from the environment or a local `.env`, after both
  gates already passed (`:421-424`).
- **An undated budget cannot silently become unenforced.** A positive
  `maximum_budget_usd` with a zero `estimated_cost_per_call_usd` is itself a
  blocker (`estimated_cost_per_call_usd_required`), because a zero
  per-call estimate would let `_projected_cost_usd` add nothing per call and
  the dollar ceiling would never bind however many calls were made.
- **Spend is deducted before the call, not after a successful response**, and
  the client is constructed with `max_retries=0`, so a failed paid call cannot
  be silently retried for free budget it already consumed.
- This decision generalizes, it does not special-case, an existing pattern:
  paid ElevenLabs voice-over and OpenAI Vision already separate a network-style
  reachability question from a payment question; this slice is the first place
  the rule was written down and tested as a property of *any* paid network
  action rather than reverse-engineered per backend.

## Consequences

- Any future paid network capability must implement the same two-gate shape:
  a network class from ADR 0019 that only answers reachability, and a
  separate payment gate with its own confirmation phrase and both a call
  count and a dollar ceiling backed by a positive per-call estimate. A single
  combined flag ("enable this paid online feature") reproduces the failure
  mode this ADR closes.
- `architecture-change`'s ADR trigger is extended (companion change in this
  same package) to name "a new config-gate" and "a new class of network
  action" explicitly, so the next paid capability does not arrive without a
  record of which two gates it needed.
- The model itself never receives rights, ranking, provider identity or the
  selected asset — a scope boundary orthogonal to this ADR, but one a future
  paid-call reviewer should not assume this ADR already covers.

## Verification

Read-only, on this HEAD. `src/content/semantic_brief_openai.py:164-187`
(`paid_call_blockers`), `:388-429` (`build_semantic_brief_adapter`), `:104`
(`LIVE_CONFIRMATION_PHRASE`). `src/runtime_network.py`
(`NETWORK_ACTION_SEMANTIC_BRIEF`, added to the ADR 0019 boundary, not a second
one). Held by `tests/test_semantic_brief_live_activation.py`
(`test_network_approval_alone_does_not_authorise_spending`,
`test_a_paid_flag_without_the_confirmation_phrase_is_not_approval`,
`test_approval_without_a_call_budget_is_not_approval`,
`test_approval_without_a_money_budget_is_not_approval`,
`test_every_missing_paid_condition_is_named`,
`test_a_declared_budget_with_a_zero_estimate_is_not_approval`,
`test_a_failed_call_still_spends_its_place_in_the_budget`,
`test_network_denial_does_not_read_repository_dotenv`,
`test_paid_denial_does_not_read_repository_dotenv`). No code, tests, config,
schemas or runtime projects were changed; no network, provider, model, TTS,
Vision or render call was made, and `config/semantic_brief.json` ships with
the backend disabled.
