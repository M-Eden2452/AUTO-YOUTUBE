# ADR 0020: Rights review and the final render checksum are fail-closed authorizations, never cached permissions

Date: 2026-08-17

Status: accepted; backfilled from the completed PLAN-STAB-5 / PLAN-STAB-9
slices (2026-08-06) and the M1-E fresh-checksum correction and its Review #2
repairs (2026-08-14/15); no new capability enabled by this record

## Context

Two independently discovered defects share one root cause: a render gate that
treats a **stored answer** as if it were still true, instead of re-deriving
the answer from what is on disk right now.

- **Rights.** A record's `review_required=True` is evidence that a human
  flagged an asset. `PLAN-STAB-5` found that this evidence could be silently
  overwritten: `media_library._propose_media_record` could attach a foreign
  `policy_decision` next to a `review_required=True` flag it did not itself
  produce, and a policy re-evaluation could then read the foreign decision as
  permission and clear the flag it never set.
- **Checksum.** `PLAN-9E`/M1-E found that the final renderer could reuse a
  quality verdict recorded against *different bytes* than the ones currently
  at that path (a metadata-keyed cache reused a decode result when size and
  mtime were unchanged but content was replaced), and — after that was
  fixed — that an asset whose stored checksum expectations had all been
  removed authorized itself anyway, because `all([])` is vacuously `True`.

Both defects have the same shape: an absence (of a real check, or of a stored
expectation) was read as a positive answer. Both were closed by making the
**final** boundary recompute and fail closed on absence, while explicitly
keeping earlier, non-final gates tolerant of legacy manifests that predate the
stricter contract.

## Decision

- **Rights are resolved conservatively across every present copy, never by
  the most permissive one.** `_rights_are_allowed`
  (`src/assets/completion/modes.py:465-557`) collects whichever of root,
  `license`, `policy_decision` and the stored semantic decision are actually
  present on the candidate, and each present copy has veto power: a positive
  verdict from one copy does not override a negative or missing one from
  another. A structurally unknown, empty or negative status is a block;
  nothing here manufactures "allowed" out of absence.
- **`review_required` is monotonic.** Once recorded, it is a policy **input**,
  not something the policy is allowed to clear on its own. The canonical
  owner, `apply_policy_to_candidate` / `_record_review_required`
  (`src/assets/license_policy.py:71`, `:203-204`, `:368`), only lifts it
  through one path: a confirmed per-asset `rights_declaration`
  (`_manual_declaration_is_confirmed`). Re-evaluation, metadata backfill,
  resume and rebuild do not clear it by themselves.
- **The final render boundary recomputes bytes; it does not trust a cached
  decode.** `_local_file_is_valid`
  (`src/assets/completion/modes.py:567-610`) accepts a `fresh` flag; final
  render passes `fresh_local_file_validation=True`
  (`src/news/final_renderer.py:330`), which routes to
  `_validate_local_file_uncached` instead of the stat-keyed
  `_validate_local_file_cached` — same size and mtime after a byte swap can no
  longer reuse a stale checksum.
- **An asset with no recorded checksum expectation fails closed at that
  boundary, not open.** `_local_file_is_valid` treats an empty
  `expected_checksums` as authorization only when `fresh` is `False`; at the
  fresh (final-render) boundary it returns `False` instead of satisfying
  `all()` vacuously (`:602-609`). Non-final gates — quality, draft completion,
  replacement, report, scene completion — stay tolerant of manifests written
  before a checksum was persisted; **only the final boundary is a render
  authorization**, and that asymmetry is deliberate, not an oversight to
  reconcile.
- Both mechanisms compose through the same public surface,
  `blocking_reasons` / `evaluate_usability`, so a future caller gets both
  protections by using the existing gate rather than assembling checks itself.

## Consequences

- A new render or export path must call the existing `evaluate_usability` /
  `blocking_reasons` with `fresh_local_file_validation=True` at its final
  boundary. Inventing a second readiness check, or reusing the non-fresh,
  cache-tolerant path for a final decision, reproduces the exact defect this
  ADR backfills.
- A rights-clearing mechanism that does not go through a confirmed
  `rights_declaration` is a regression of PLAN-STAB-5, whatever else it is
  called.
- The canonical rights vocabulary (`RIGHTS_*`, `RIGHTS_ALLOWED_STATUSES`) has
  exactly one owner, `src/assets/models.py` (PLAN-STAB-9); a second
  independent list of allowed statuses anywhere else is the defect PLAN-STAB-9
  removed, not a pattern to repeat.

## Verification

Read-only, on this HEAD. `src/assets/completion/modes.py:465-557`
(`_rights_are_allowed`), `:567-610` (`_local_file_is_valid`);
`src/assets/license_policy.py:71,203-204,368`
(`RECORD_REVIEW_REQUIRED_REASON`, `_record_review_required`);
`src/news/final_renderer.py:330` (`fresh_local_file_validation=True`).
Held by `tests/test_autonomous_completion_core.py`
(`test_render_gate_rejects_stale_checksum_and_corrupt_passed_file`,
`test_final_render_gate_refuses_an_asset_with_no_recorded_checksum`) and by
`tests/test_rights_review_preservation.py`
(`test_the_policy_cannot_clear_a_requirement_the_record_states`,
`test_a_rule_that_says_nothing_about_review_does_not_clear_it`,
`test_the_render_gate_refuses_the_flagged_asset`). No code, tests, schemas or
runtime projects were changed; no network, provider, TTS, Vision or render
call was made.
