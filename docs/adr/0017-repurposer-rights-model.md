# ADR 0017: Video Repurposer declares personal-use provenance instead of inheriting the rights contract

Date: 2026-08-17

Status: accepted as the rights boundary of the second application engine; no
capability was enabled by this decision and `video_repurposer` stays
`enabled=False` (ADR 0016)

## Context

The owner answered the blocking legal question about `video_repurposer` on
2026-08-16 (`Q91`, recorded in
`docs/audits/PRODUCT_INTERVIEW_MERGED_2026-08-16.md`): the engine cuts any
content the owner hands it, in a personal-use mode, rights are not checked, and
monetization is not expected. The owner named the consequence himself — such
videos are not monetized, so a sellable-rights posture is not what this engine
is for.

`content_creator` sits at the opposite end. Its second product principle is that
rights and provenance are provable: every fragment carries provider, source,
licence and checksum, the rights report classifies each item, and
`publish_ready` is only reachable when nothing is missing. Applying that
contract to an engine whose every output is, by the owner's decision, unchecked
would produce one of two lies: either a permanent `rights_verified=false` that
blocks a product the owner deliberately wants, or a `publish_ready` that means
something different than it does in `content_creator`.

There is one existing precedent for the honest-marker approach, and it is
smaller than it looks. A locally supplied music track cannot have its licence
verified, so `src/audio/music_manifest.py:38-46` writes
`license.name = "unverified_user_supplied"` with
`commercial_use_status: "unknown"`, and the rights layer does pick it up:
`_music_item` (`src/projects/rights.py:407-446`) always attaches the warning
"Права на музыкальный файл не проверялись автоматически." and, through
`classify_rights` plus the explicit downgrade at `:444-445`, lands on
`review_required`. So the repository does not stay silent about unverified
music. What it does is carry that honesty in **one nested field of one
manifest**, discovered by one reader that knows to look for it. That is enough
for a single optional track inside a `content_creator` project. It is not enough
for a whole engine in which *every* output is in the unchecked mode, because a
reader who does not know the field exists sees a manifest that looks like any
other.

## Decision

- `video_repurposer` **does not inherit** the `content_creator` rights
  contract. It is not required to reach `rights_verified`, and a fail-closed
  rights gate is not the mechanism used to express its legal position.
- Instead, the engine carries an explicit provenance mode,
  `repurposed_personal_use`. The mode states what is true — the material was
  supplied by the owner for personal use and its rights were not checked — and
  it never states or implies that anything was cleared.
- The mode is **positively declared in the manifest**. It is written as an
  explicit field, never inferred from the absence of another marker. A manifest
  without the field is a defect, not a personal-use manifest; and a reader that
  does not find the field must not infer verified rights either.
- `publish_ready` in the `content_creator` sense is **never true** for
  repurposed output. The repurposer's own definition of done lives in
  `docs/current/PRODUCT_PLAN.md` section 10 and does not borrow that flag.
- Per-clip origin evidence (source file, timecode, checksum) is still recorded.
  It is evidence of where a clip came from, not a claim about rights.
- No second rights owner is created. `src/projects/rights.py` remains the single
  owner of rights classification and reporting; if and when the engine is
  integrated, it gains this mode inside the existing owner and the existing
  report, not a parallel one.
- The `content_creator` gates are **not weakened** by this decision. `strict`
  remains the default completion mode, `draft_complete` remains an opt-in that
  never sets `publish_ready`, and the `must_avoid`, conflict and
  misleading-content gates are untouched.
- This decision enables nothing. `video_repurposer` remains `enabled=False` and
  `implementation_status="planned"` in the production catalog (ADR 0016); the
  legal responsibility for the supplied source material stays with the owner.

## Relationship to earlier decisions

ADR 0016 defines the two application engines and keeps `video_repurposer`
disabled until its workflow is integrated with the canonical
project/workspace/catalog contracts. This ADR does not change that gate; it only
records which rights model the engine will carry when the gate is reached, so
the first integration slice does not have to invent one under time pressure.

## Consequences

- No production code, catalog status, CLI command, schema, runtime project or
  user media changes in this decision.
- Any future repurposer slice must write the provenance field before an
  exported clip is produced; a missing field fails the slice rather than
  defaulting to personal use.
- The rights report must be able to render this mode without claiming
  verification. That is an extension of the existing report, not a second
  report.
- The two engines now have deliberately different definitions of done. Anyone
  comparing them must read `PRODUCT_PLAN.md` section 10, where both sets of
  criteria are written next to each other.
- Nothing here makes the underlying use lawful or unlawful; it makes the
  repository stop pretending it knows.

## Verification

Read-only, on this HEAD. The precedent above was checked in code before being
written down: `src/audio/music_manifest.py:38-46` (the
`unverified_user_supplied` licence block) and `src/projects/rights.py:407-446`
(the unconditional warning and the `review_required` classification). The
catalog entry keeping the engine disabled was checked at
`src/production_catalog/catalog.py:83-95`. No code, tests, schemas, manifests or
runtime projects were changed; no network, provider, TTS, Vision or render call
was made.
