# ADR 0019: Runtime network access is default-deny, granted per named action class

Date: 2026-08-17

Status: accepted; backfilled from the completed PLAN-STAB-4 slice
(2026-08-06) and its PLAN-9B-PRODUCER-M-LIVE extension (2026-08-09); no new
capability enabled by this record

## Context

Before PLAN-STAB-4 there was no single answer to "is this run allowed to go
online". Each of five network-capable paths (provider search, asset
download, preview download, article fetch, ElevenLabs voice preflight) could
in principle grow its own ad-hoc guard, and a keyless default-on provider or a
configured API key could be mistaken for permission. `AGENTS.md`'s safety
section states the resulting requirement directly: no network, provider
search, download, Vision or TTS call without a separate explicit user
permission, and a configured provider is not that permission.

An owner audit (required by the PLAN-STAB-4 slice before implementation)
picked one canonical boundary instead of a per-provider guard, so a second
guard would not diverge from the first over time.

## Decision

- One canonical owner: `src/runtime_network.py`. No other module decides
  whether a network call may proceed.
- Default deny is a property of the storage, not a checked convention: the
  `ContextVar` backing `current_network_approval()` defaults to `DENY_ALL`
  (`src/runtime_network.py:147-152`), so an approval that is never set denies
  every action rather than defaulting open.
- Permission is granted per **named action class**, not globally. `NETWORK_ACTIONS`
  (`:73-81`) is a closed, ordered tuple; `require_network(action)` is the one
  check every call site makes, immediately before the first socket/HTTP call,
  and an unknown class name is a `ValueError`, never a silent allow
  (`:207-219`).
- An approved class does not open a neighbouring one. This was tested against
  itself on 2026-08-17: voice preflight (reads the account, spends nothing)
  and voice synthesis (generates, costs money) were deliberately split into
  two classes, `voice_preflight` and `voice_synthesis`, specifically because
  one class covering both would let approval for the free check silently
  authorize the paid call (`:63-68`).
- The set of authorizing facts is closed and does not include: a configured
  or keyless-default-on provider, a present API key, `resume`, `--force-stage`,
  or a running preflight. The only source of approval is explicit user input,
  captured once at the top of a run and threaded through
  `network_approval_scope` (`:34-39`, `:188-200`).
- `NetworkApproval.to_dict()` serializes only class names and a `granted_by`
  label (`:139-144`), so a key, token or query string cannot reach a manifest
  or approval artifact through this boundary.
- This boundary does not own payment authorization. A network class granted
  for a paid action (`voice_synthesis`, `semantic_brief`) answers "may this
  run reach the network", never "may this run spend money" — that is a
  second, independent gate owned elsewhere (ADR 0021).
- Adding a new network-capable call site means adding a new named constant to
  `NETWORK_ACTIONS` and calling `require_network` before the socket call, not
  creating a second boundary. This was exercised, not just stated: the first
  paid text-model integration (PLAN-9B-PRODUCER-M-LIVE, 2026-08-09) added
  `NETWORK_ACTION_SEMANTIC_BRIEF` to this same tuple and reused
  `require_network` and `network_action_allowed` unchanged
  (`src/content/semantic_brief_openai.py:419`).

## Consequences

- A new provider, downloader or model call is fail-closed by construction the
  moment it is wired to this module; forgetting to call `require_network` is
  the only way to bypass it, not a missing per-provider guard.
- CLI (`--allow-network <class>`, repeatable, `choices=NETWORK_ACTIONS`) and
  the Wizard's `confirm_network_access` question both fill the same
  `NetworkApproval`, so the two entry points cannot drift into different
  permission models.
- `architecture-change`'s ADR trigger is extended (see the companion change in
  this same package) to name "a new class of network action" explicitly,
  because adding one is a boundary decision even when the surrounding code
  looks like an additive field.

## Verification

Read-only, on this HEAD. `src/runtime_network.py` in full: `NETWORK_ACTIONS`
(`:73-81`), `DENY_ALL` / `_current_approval` (`:147-152`),
`network_approval_scope` (`:188-200`), `require_network` (`:207-219`).
Consumers checked at their call sites: `src/assets/http_client.py`,
`src/news/article_ingestor.py`, `src/audio/tts/elevenlabs_provider.py`,
`src/content/semantic_brief_openai.py:419`. Held by
`tests/test_runtime_network_boundary.py`
(`test_default_approval_denies_every_known_action`,
`test_explicit_approval_allows_only_the_expected_action`,
`test_unknown_action_name_is_rejected_not_silently_ignored`,
`test_keyless_default_on_provider_also_requires_approval`,
`test_approval_artifact_carries_no_secret_material`) and by
`tests/test_semantic_brief_live_activation.py`
(`test_the_text_model_has_its_own_network_action`,
`test_without_network_approval_the_backend_is_never_called`,
`test_a_neighbouring_network_approval_does_not_open_the_model`). No code,
tests, config or runtime projects were changed; no network, provider, TTS,
Vision or render call was made.
