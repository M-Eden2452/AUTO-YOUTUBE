---
status: active
plan_revision: 2.1
created_at: 2026-07-30
updated_at: 2026-08-18
baseline_head: 38fed31
working_branch: governance-reset
owner_decisions_date: 2026-08-11
current_checkpoint: PLAN-9D
next_exact_action: >-
  Checkpoint PLAN-9D, in progress. C98 is closed 2026-08-18 in
  src/assets/query_adapter.py: a plan-level TopicAnchor keeps the video's topic in
  every query (PD-13, ADR 0022). Census on the frozen scenes 15 of 42 -> 0; blind
  agreement unchanged at 2 / 10 on v2 and 4 / 14 on v1, which is the guard, not the
  acceptance. NEXT is an independent review-change in a clean context over that
  immutable commit - the slice is HIGH risk (selection). Then C99, the largest
  measured class left. No live run is authorised here. WHO DECIDES: the owner, at
  entry.
# PLAN-9C-2-B1 correction (2026-08-10): the preceding historical summary
# describes implementation commit 388b9b1. This repair completed canonical
# policy application through draft completion; the routing field above records
# the later retrieval-symmetry closure and supersedes this historical comment.
source_paths:
  - AGENTS.md
  - pyproject.toml
  - requirements.txt
  - requirements.lock
  - .gitignore
  - docs/current/CURRENT_STATE.md
  - docs/current/START_HERE.md
  - docs/current/SYSTEM_MAP.md
  - docs/current/ARCHITECTURE_BOUNDARY_MAP.md
  - docs/current/CLEANUP_REGISTRY.md
  - docs/handoff/PROJECT_RESCUE_MASTER_PLAN.md
  - src/production_catalog
  - src/config_resolver
  - src/assets
  - src/news
  - src/providers
  - src/audio
  - src/subtitles
  - anime_factory
  - apps
  - tests
  - tools/qa
  - skills/review-change
  - .claude/agents/review-change.md
---

# AI-YouTube Project Execution Plan

Временный orchestration-документ на период согласованной программы работ.
Он задаёт **порядок выполнения** и ничего больше. Он не заменяет `AGENTS.md`,
`CURRENT_STATE.md`, `PRODUCT_PLAN.md` и `CLEANUP_REGISTRY.md` и не является
архитектурной или продуктовой спецификацией.

После полного завершения программы этот файл удаляется из `docs/current/`
и сохраняется одним архивным snapshot — см. «Completion and archive policy».

## Current checkpoint

### Mini plan reconciliation 2026-08-11

Авторитетная сводка маршрута: новый чат обязан восстанавливать route отсюда, а
не из внешней истории. Блок **не создаёт PLAN-ID**. `WP0-A`, `WP0-B`,
`M1-A…M1-E`, `M2-A`, `M2-B`, `M3`, `M4`, `M5` и `LIVE-5` — owner packaging
labels и owner-issued действия, а не plan steps; canonical traceability
остаётся на существующих PLAN owners.

**CURRENT CHECKPOINT.** **PLAN-9D** (in progress). Этой сверкой не менялся.

**WHAT JUST COMPLETED.** `WP0-A` machine gates существуют фактически:
`requirements-dev.lock`, Ruff (`F`, `E9`) и Mypy (`files = src/assets`,
`src/news`) baselines в `pyproject.toml`, `scripts/gates.py` (ruff · mypy ·
`check_agent_docs` · `git diff --check` · `git diff --cached --check`),
git hook `.githooks/pre-commit` через `core.hooksPath`, CI-шаг «Run machine
quality gates» и правило «Gates» в `AGENTS.md` — commits `98e58fe` и
`a9bfc11`. Стратегия — ratchet: подавленный модуль снимается из baseline тем
слайсом, который и так трогает файл вместе с его owning tests; численные
baseline-счётчики живут в `pyproject.toml` и в routing-документы не
копируются. `VA-NEW-01` / `M1-A` закрыт commit `15cb20d` как post-audit
correction внутри `PLAN-9C-3`; `VA-NEW-03` — commit `37ca498` внутри
`PLAN-9C-2`. `VA-NEW-02` / `M1-B` закрыт содержащим эту запись commit:
локальный preview key v2 связывает evidence с SHA-256 текущих source bytes и
фактическим local transform (`max_dimension`, `video_preview_max_duration_sec`),
а missing/unreadable source fail closed. Evidence: baseline RED на `104e5a3`,
targeted radius 206 OK, full offline suite 2170 OK, gates OK. Checkpoint не двигался.

**M1-C CLOSURE.** VA-NEW-04 and VA-NEW-05 are closed by the bounded PLAN-9A
correction in the commit containing this record. Normal materialization keeps one
logical asset identity; fallback from reviewed A to downloaded B persists
replaces_asset_id=A, rebinds the review to B, and carries only the canonical
Vision envelope bound to candidate id, observed-source SHA-256 and the existing
semantic cache key. A checksum mismatch invalidates the tags. The extension is
additive and tolerant: no migration, schema-version bump, resume change, new
repository or second evidence owner. Evidence: characterization RED (2 failures,
4 errors), targeted 217 OK, full canonical offline suite 2177 OK. Owner permission
in the M1-C prompt satisfies the earlier decision gate. Next: Review #1 for M1-A...
M1-C; do not start M1-D. Checkpoint remains PLAN-9D.

**M1-C REPAIR CLOSURE.** The bounded PLAN-9A repair in the commit containing
this record closes the four confirmed independent-review gaps without changing
selection, readiness or schema ownership. Vision tags now have content-evidence
authority only when asset id, observed-source SHA-256, semantic cache key and
current representation checksum form a complete matching envelope; old/partial
objects remain readable but fail closed. Draft completion preserves the
original A identity when materializing fallback B, active local ranking carries
the canonical envelope, and compatibility preview rebuild keeps existing
fallback lineage. No migration, schema-version bump, new evidence store or
second selector/readiness owner was added. Evidence: all four paths reproduced
RED; owning radius 85 OK, expanded targeted radius 407 OK, full canonical
offline suite 2186 OK. Next remains one focused independent re-review of these
four repairs and shared M1-A...M1-C invariants; do not start M1-D.

**M1-C MAJOR-RR-01 REPAIR CLOSURE.** The local representation adapter now
hashes current local bytes once per included asset and exposes that observed checksum
to the unchanged canonical Vision-envelope validator. Persisted checksum/envelope
fields remain readable and unmodified; changed, missing or unreadable sources fail
closed for Vision authority. RED: one owning failure; GREEN: owning 6, targeted 146,
full canonical offline suite 2190. Checkpoint and next focused re-review are unchanged.

**REVIEW #1 CLOSURE (2026-08-11).** Independent read-only review of the exact
M1-A (`15cb20d`), M1-B (`1bf7ecc`), M1-C original (`c9537fa`), M1-C repair
(`a7bec3c`) and M1-C MAJOR-RR-01 repair (`2577307`) commits, plus the net
production identity/evidence path, is complete. Verdict: cluster ACCEPT,
MAJOR-RR-01 CLOSED, 0 remaining BLOCKER/MAJOR findings; CI run `31526039612`
(headSha `2577307`) conclusion success. This supersedes the "Next: Review #1
... do not start M1-D" wording earlier in this section (the M1-C and repair
closure records above are not rewritten). Next exact action is **M1-D /
VA-NEW-08**; checkpoint remains PLAN-9D.

**M1-D CLOSURE (2026-08-12).** `VA-NEW-08` is closed by the bounded PLAN-9A
correction in the commit containing this record. A completed `asset_search`
may now only be reused when the stored manifest can prove which inputs
produced it: `assets_manifest.json` carries an additive
`asset_search_fingerprint`, and resume compares it against the current inputs
before it reads the completed-stage set.

**Owner decision on the persisted field set — issued in the M1-D prompt,
composition recorded here.** The fingerprint is a SHA-256 over exactly the
arguments that decide what `build_asset_search_manifest` retrieves and
selects: the visual plan on disk, `user_assets`, `channel_id`, the channel's
resolved `asset_selection` policy, the normalized completion `mode`,
`dry_run`, and a `version` so a later change to this composition stops
matching deterministically instead of comparing two different questions.
`project_root`/`project_id` are excluded because they say where a project
lives rather than what it asks for — a moved project must still match — and
the reuse ledger is scratch state of a single run.

**Two declared boundaries, recorded rather than left silent.** Live provider
identity is *not* in the fingerprint: determining it is not a pure input read
(it constructs providers and loads the process environment), and making resume
depend on which API keys happen to be present would invalidate every project
whenever one is absent. `dry_run` — the provider-set difference the pipeline
itself controls, and the one that turns a no-provider preview into something
that must never serve a real run — is covered. Provider composition stays with
`VA-NEW-06` / M2-A inside PLAN-10B. The local media index is likewise excluded:
it is a growing library, not a decision policy, and hashing it would invalidate
every project on every addition.

**Fail-safe and legacy.** Missing, unparseable and mismatching fingerprints all
mean the same thing — compatibility unknown is not permission — so none of them
is silently reused. A legacy manifest stays fully readable and
`is_stage_completed` is unchanged; it is recomputed once and then carries a
fingerprint like any other. Deliberate behavior change: existing projects
re-run `asset_search` on their first resume. When the search is recomputed the
existing `STALE_STAGES` set (`preview_render`, `quality_check`, `final_render`,
`export`) goes stale with it; `voice` and `subtitles` are built from the script
and are untouched. Result files stay on disk as audit evidence.

**Causal loop — checked, latent, not live.** The `completed` snapshot in
`run_news_to_short_job` is still taken once before the stage loop, but nothing
in the loop invalidates a stage today (`_mark_job_stale` belongs to visual-slot
replacement, reachable only from the CLI). The new check is therefore placed
before the snapshot, so it cannot open that hole; no scheduler was built.

Additive and tolerant: no schema-version bump, no migration, no new persistence
subsystem, no second reuse owner, no breaking API. Evidence: characterization
RED through the real production path (7 failures, 2 errors) — a project carried
to a completed `asset_search` by `dry_run`, the owner attaching footage, the
plan genuinely re-planned by production, and the search still skipped; GREEN 8
owning checks, targeted radius 114, full canonical offline suite 2216, gates OK.
Mypy ratchet not applicable: `src.news.pipeline` is not in the baseline
suppression list and no suppressed module was touched. Next: **M1-E /
VA-NEW-09**, then Review #2 over M1-D and M1-E; none of Review #2 is done.
Checkpoint remains PLAN-9D.

> **Routing correction (2026-08-14).** The "Next" sentence above records the
> route as it stood when M1-D closed and is **no longer the current next
> action**: the owner decision of 2026-08-14 put the product sequence ahead of
> it, and the authoritative next action is the `next_exact_action` field of this
> document's frontmatter — today the STOCK repeat through `semantic_brief`,
> after which M1-E / VA-NEW-09 and Review #2 follow unchanged. The historical
> record above is left intact; the checkpoint is still PLAN-9D.


**M1-E CLOSURE (2026-08-14).** `VA-NEW-09` is closed by the bounded PLAN-9E
correction in the commit containing this record. The canonical final renderer
now calls the existing `evaluate_usability` owner for every visual slot
immediately before segment creation in both completion modes. Strict render can
no longer rely on a saved quality verdict after current bytes, checksum,
technical validation, rights, policy or semantic decision changed.

Modern manifests carrying an assembly or semantic decision must still be
`publish_ready` at that fresh boundary. Tolerant legacy readers are preserved:
a pre-assembly manifest without a semantic decision is not required to invent
one, but its current file, checksum, technical validation and rights must pass.
No new readiness owner, persisted field, schema version, migration, provider,
network call or render primitive was added; PLAN-9E remains blocked as a full
activation contract and Vision activation is unchanged.

Evidence: characterization RED reproduced both valid-byte replacement and
rights-revocation bypasses (2 failures); GREEN owning module 38 OK, expanded
render/quality/resume radius 124 OK including two real FFmpeg end-tail renders,
and gates OK. Next: **independent Review #2 over M1-D and M1-E**. Checkpoint
remains PLAN-9D.

**M1-E REVIEW #2 REPAIR (2026-08-14).** The first Review #2 verdict was
**REJECT** on two M1-E blockers and found no M1-D blocker. First, ordinary local
validation used an LRU key of path, media type, size and mtime, so replacing
bytes while preserving size and mtime could reuse an old decode/checksum result.
Final render now explicitly bypasses that metadata-keyed cache and recomputes
decode plus SHA-256 immediately before segment creation. Second, treating every
assembly as a new semantic authorization contract regressed the canonical
manually approved user-asset path. The publish-ready requirement remains for
authoritative semantic decisions; only the existing
`selected_by=user_asset_priority_manual` compatibility path retains its prior
strict behavior after upstream quality approval, while fresh bytes, checksum,
technical, rights, policy and safety hard gates still apply. Characterization
warms the cache before a same-size/same-mtime byte replacement; the real
manual-user-asset render E2E is restored. Expanded targeted radius: 126 OK.
Next: **focused independent Review #2 re-review over M1-D and M1-E**.

**M1-E REVIEW #2 SECOND REPAIR (2026-08-15).** Review #2 stayed **REJECT** on
one remaining M1-E blocker and reported no new M1-D finding. Fresh final-render
validation compared the current bytes against every stored checksum, and
`all([])` is true, so an asset carrying neither the root nor the provenance
copy authorized itself: quality could pass with a recorded checksum, both copies
could then be dropped, the bytes replaced, and the renderer still ran.
`_local_file_is_valid` now fails closed at the fresh boundary when no
expectation is recorded. The asymmetry is deliberate and covered by test: the
non-final gates (quality, draft completion, replacement, report, scene
completion) stay tolerant of manifests written before a checksum was persisted,
because only the final boundary is a render authorization. Characterization RED
reproduced the bypass end to end (`RuntimeError not raised`, renderer reached);
GREEN adds the `checksums_removed` renderer regression — quality PASS → both
checksum copies removed → bytes replaced → renderer not called — plus a unit
test pinning the fresh/non-fresh asymmetry. Three renderer fixtures that had
never recorded a checksum now record one, matching what
`DownloadedAsset.from_candidate` writes for every real download. Stored projects
were scanned before the change: 152 manifest assets carry a checksum, and all 35
that do not are empty placeholders or point at files no longer on disk, so no
existing project changes verdict. Targeted radius: 174 OK, gates OK. Next:
**focused independent Review #2 re-review over M1-D and M1-E**. Checkpoint
remains PLAN-9D.

**REVIEW #2 CLOSURE (2026-08-15).** Focused independent read-only re-review of
the exact M1-D commit (`f3b607a`) and the three M1-E commits (`0a05c7e`,
`35688dd`, `e03ad9e`) is complete. Verdict: **ACCEPT WITH MINOR NOTES**, 0
BLOCKER, 0 MAJOR. **M1-D and M1-E are both closed**, their composition is safe,
and the owner accepted this verdict as sufficient without a further repair or
re-review. The 23 unrelated commits between `f3b607a` and `e03ad9e` were not a
review range and were not audited. Accepted HEAD `e03ad9e` is pushed to
`origin/governance-reset`; exact-head CI is run `31866721908` (`offline-tests`),
`in_progress` at the single permitted lookup and not polled.

What the re-review established independently rather than accepting from the
implementation record: RED was reproduced for all four commits by extracting the
parent tree with `git archive` into a scratch directory and running the newer
tests against it, without touching the worktree — `f3b607a` 7 failures/2 errors
(matching its commit body), `0a05c7e` 2 failures, `35688dd` 1 failure/2 errors
(`bytes_replaced` reaching the renderer through the metadata-keyed cache), and
`e03ad9e` 2 failures. `projects/` was rescanned from scratch over every
renderable `selected_asset` (assembly slots plus the legacy root key): 40
manifests, 146 reachable records, 35 without any stored checksum, and **zero** of
those 35 present on disk — 25 carry no local path at all and 10 point at files
that no longer exist, so both classes were already blocked before this change and
no stored project changes verdict. Every production writer of a renderable
`selected_asset` was enumerated from the call graph and each records a checksum;
the only writer that does not, `generated_fallback_asset`, emits `path: ""`, is
already `BLOCK_MISSING_FILE`, and is disabled on the canonical path. Draft was
verified separately from strict by running `_create_scene_segments` in both modes
against byte replacement, checksum removal and both together — draft blocks
identically and is not weaker. Owning tests 61 OK, adjacent radius 94 OK; no
network, paid, Vision, TTS or production render call was made by the review.

Three MINOR notes, recorded here as the accounting home and deliberately **not**
repaired by a separate slice; no new PLAN-ID and no owner is assigned:

- **MINOR-1 (docs/accounting).** The M1-E SECOND REPAIR block above, and the
  `e03ad9e` commit body, both say the non-final gates «quality, draft completion,
  replacement, report, scene completion» stay tolerant of a missing checksum.
  That is accurate for the readiness helpers (`blocking_reasons` /
  `evaluate_usability` with `fresh_local_file_validation=False`) but **not** for
  the quality stage: `src/news/quality_check.py:232` already makes a missing root
  `checksum_sha256` a hard error, and did so before M1-E. Runtime is correct; only
  the wording overstates what «quality» refers to. The code comment in
  `modes.py` and the mirror documents say «earlier gates» / «non-final gates» and
  are accurate as written.
- **MINOR-2 (code accounting).** `35688dd` narrowed `semantic_contract_present`
  in `src/news/final_renderer.py` twice — it dropped the `explicit_assembly` term
  and added the `selected_by != "user_asset_priority_manual"` carve-out — under an
  empty commit body, with the rationale living only in that commit's docs entry.
  The renderer is therefore more permissive than `quality_check.py:246` for two
  classes (assembly without a semantic decision; manual user assets). Not
  exploitable on the canonical path: strict `final_render` requires
  `quality.status == "passed"` (`src/news/pipeline.py:717`) and the canonical
  workflow re-runs `quality_check` immediately before the render
  (`fullscreen_voiceover/use_case.py:529`), and quality carries no carve-out. Both
  branches remain strictly stronger than the pre-`0a05c7e` state, where strict did
  not re-evaluate the slot at all.
- **MINOR-3 (test coverage).** There is no committed draft-mode regression for
  byte replacement; only strict has one. The code path is shared — the readiness
  call sits above the draft/strict branch — and the review verified draft
  empirically, so this is a coverage gap rather than a defect.

Next: **resume FIRST OWNER SHORT** on the accepted HEAD, offline, to a real
`draft_1080x1920.mp4`. Checkpoint remains PLAN-9D.

**PRE-M2 CLOSURE (docs/accounting, 2026-08-15).** Three facts recorded before
M2-A starts. No PLAN-ID is created, no step changes status, and no production
code, test, config or schema is touched by this record.

- **Exact-head CI is not green, and the cause is not this repository.** Run
  `31866721908` (`e03ad9e`, the accepted Review #2 HEAD) and run `31867069337`
  (`3633e0a`) both completed with conclusion **failure**, both at the same step —
  «Install FFmpeg (ffmpeg-full 8.1.2, pinned via Chocolatey)» — against the
  external Chocolatey feed: `503 Service Unavailable` on the first, `504 Gateway
  Timeout` on the second. Every later step, «Run offline unit and integration
  suite» included, is `skipped`, so **not one test ran**. Recorded as an external
  setup outage; it is not CI green, it is not a product defect, and no code was
  changed because of it.
- **The full local offline suite has exactly one failure, and it predates this
  step.** 2261 tests at `3633e0a`, one failure:
  `tests/test_stage2_agent_onboarding.py::test_onboarding_documents_stay_short` —
  `START_HERE.md` is 154 lines against a 100-line limit. `SYSTEM_MAP.md`
  (294/240) and `CURRENT_STATE.md` (348/280) are over their own limits too and
  are masked by that first assertion. This is the documentation line-count
  governance contract, grown by the CLOSURE blocks added between `6dcce78` and
  `e03ad9e`. It is not a product regression and touches no M1-D or M1-E contract.
  It is deliberately **not repaired here**: the owner decision on how to hold that
  contract has not been made, and this record and the M2-A closure add further
  lines to the same documents.
- **FIRST OWNER SHORT resume-run is done — diagnostic evidence, not acceptance.**
  It ran offline on the accepted HEAD through the canonical workflow and produced
  a real `draft_1080x1920.mp4` (`d5b86fb3…`, 10 128 608 bytes) that is
  **byte-identical** to the render taken before Review #2, so M1-E tightened
  authorization without breaking the legitimate path. 5 of 5 scenes are
  `usable_in_draft`, **0 of 5** are `publish_ready`, and `quality_report.status`
  is `needs_review`; no publish-ready evidence is claimed. Three findings, each
  with an existing owner and none of them M2-A scope: scene 3 reuses scene 1's
  asset (`pexels_9788590`) — **C47** under **PLAN-10D**; `crop_not_verified` on
  all five slots; `missing:action` on four scenes with `missing_required:action`
  on one. Subtitles were not built in this diagnostic run.

The next exact action is **M2-A** — `VA-NEW-06` + `VA-NEW-10` inside
**PLAN-10B** — not «resume FIRST OWNER SHORT». Checkpoint remains PLAN-9D.

**M2-A CLOSURE (2026-08-15).** `VA-NEW-06` and `VA-NEW-10` are closed by the
bounded **PLAN-10B** correction in the commit containing this record. Nothing
else in that section starts: the pagination / exhaustion contract is untouched,
the section keeps its `blocked` status, and no PLAN-ID is created.

**VA-NEW-06 — a failing media kind no longer erases the one that answered.**
Since retrieval symmetry (`ae6d46c`) a mixed scene sends `search_provider`
(`src/news/asset_provider_adapters.py`) one request per allowed media kind, and
the kinds shared a single `try` at the call sites: one failing request aborted
the whole call and discarded candidates that had already come back, so a provider
whose video endpoint was down also cost the scene its images. Each kind is now
its own provider attempt. Results already collected are kept, the failing kind is
recorded, and the call raises only when **every** requested kind failed — so a
single-kind scene, and a provider that is down entirely, behave exactly as
before, raising the same first error. The isolation covers the whole attempt,
including the rights/policy normalisation of what the provider returned.

**The failure stays visible; nothing is swallowed.** `search_provider` takes an
opt-in `media_attempts` collector and appends one record per kind — `completed`
with its `result_count`, or `failed` carrying the provider's own machine-readable
`code` and `retryable` plus the `media_type`. Both production call sites pass it.
`_run_provider_query` (`asset_manifest_builder.py`) attaches it to the existing
provider attempt and, when the call did *not* raise, also reports the failed kind
into the existing `provider_errors` list, so a partial outage stays a real
provider error instead of a silent gap; the raising path already reported it and
is not double-counted. `targeted_slot_search` (`asset_scene_completion.py`)
attaches the same record to its own attempt. No new ledger and no new status
vocabulary: the attempt's `status` keeps meaning «the query ran», and
`media_attempts` is one additive key. Selection, ranking, rights, media policy
and the query path are unchanged — this correction moves error isolation only.

**VA-NEW-10 — one owner of «send this request again».** The R² lived inside
`ProviderHttpClient` (`src/assets/http_client.py`), not between the client and
the ladder: `download_stream` retried the whole request in its own loop while
`_request` independently retried the same request, so one download URL cost up to
`max_retries` **squared** HTTP requests — measured at 9 with the default 3, and
16 with 4. A provider that was rate-limiting got hit nine times for one file.
`_request` is now the single owner of that decision and takes an explicit attempt
budget; `download_stream` creates one budget for the whole download and passes it
in, so the request stage and the body stage draw from the same count. One
download URL now costs at most `max_retries` requests. Body-transfer retry is
preserved — a stream that dies mid-body still gets another attempt, from the same
budget — `Retry-After` still governs the wait, a non-retryable status still costs
exactly one request, and `get_json` is unchanged: with no budget passed
`_request` creates its own of exactly `max_retries`, with the same backoff.

**Two retry layers remain, and that is the intended shape.** Retrying the same
request belongs to `ProviderHttpClient`; trying a *different* candidate belongs
to the download ladder (`ensure_selected_asset_downloaded`, `max_attempts` — 3
from the builder, 1 from draft completion). Those are different questions about
different URLs and are deliberately not collapsed, because collapsing them would
delete genuine try-next-candidate behaviour. What was removed is the third,
hidden layer inside the client. No new retry loop was created anywhere.

**Resume — `ASSET_SEARCH_FINGERPRINT_VERSION` deliberately stays 1.** The
question was answered rather than assumed. `VA-NEW-06` *can* change what
`search_provider` returns for identical inputs, but only when a provider request
fails, and the version field does not answer that question: its contract is
stated where it lives (`src/news/pipeline.py:106`) — bump when *the payload*
changes — and the payload is the inputs the search runs on (`visual_plan`,
`user_assets`, `channel`, `asset_selection`, `completion_mode`, `dry_run`), none
of which changes here. The M1-D CLOSURE already declared that things which vary
without the inputs varying stay outside the fingerprint (live provider identity,
the local media index); a provider being down is exactly that kind of runtime
variation, and two runs of the same completed search could already differ before
this change. A bump would force every existing project to re-run `asset_search`
for a change that can only *preserve* results previously discarded and can never
authorize anything — rights, usability, checksum and render gates are untouched
and still re-evaluated downstream. Repo precedent agrees: `a8549ff` changed
local-library retrieval results for identical inputs after M1-D landed and did
not bump. M1-D compatibility semantics are used unchanged and no second resume
contract exists.

**What deliberately stays out of this slice.** The PLAN-10B pagination /
exhaustion / provider-contract work itself. `C75`–`C78` (EXP-001 provider
defects): same owner, but not in the authorised bounded-correction set — same
owner is not permission, their registry attribution is already correct and
nothing there is touched. `VA-NEW-12` budget guards — that is **M2-B** inside
**PLAN-10C**. `C47` duplicate frame — **PLAN-10D**. Provider-registry
convergence — closed negatively as `D-2`, there is nothing to implement. The
`crop_not_verified` and required-action findings of the resume-run, and the
documentation line-count failure, all keep the homes recorded in PRE-M2 CLOSURE.

**Evidence.** RED first on `3633e0a` through the real production path, not an
isolated fake: 8 checks over `search_provider` and both of its call sites — 2
failures (`[] != ['image']`: the surviving image candidates lost at the manifest
builder and again at `targeted_slot_search`), 5 errors (three of them the
`ProviderNetworkError` escaping and destroying the results, two the
not-yet-existing ledger), and 1 correctly green guard proving a single-kind scene
still raises; plus 5 retry-ownership checks with 3 failures on real numbers
(9 requests where 3 were configured, 16 where 4 were). GREEN after: 16 owning
checks OK, owning radius 135 OK, retrieval/completion/resume radius 236 OK,
rights/evidence radius 121 OK, full canonical offline suite 2274 (2261 baseline
plus 13 new) with the one pre-existing doc-length failure of PRE-M2 CLOSURE and
nothing else, gates OK. No network, paid, Vision, TTS or render call was made.
**Ratchet not taken:** `src.news.asset_provider_adapters`,
`src.news.asset_manifest_builder` and `src.news.asset_scene_completion` keep
their mypy baseline suppression — the 11 measured errors under it are pre-existing
type debt in functions this correction does not touch, and clearing them is the
mass cleanup that may not share a slice with a behaviour change. (The count read
7 until 2026-08-15; re-measured independently at `3633e0a`, `36f23cc` and HEAD it
is 11 at all three, so the delta this slice adds is still 0 and the decision not
to take the ratchet is unchanged.)
`src.assets.http_client` is not suppressed and is fully checked.

Next: **M2-B** (`VA-NEW-12`, minimal per-scene request budget and stop guard)
inside **PLAN-10C**, after which **Review #3** covers M2-A and M2-B together per
the recorded batching strategy; none of Review #3 has been performed. Checkpoint
remains PLAN-9D.

**M2-A side effect, recorded here because M2-B is where it is paid.** Before
M2-A a failing preferred media kind aborted the loop inside `search_provider`
and the second kind was never asked: one request. After M2-A the second kind is
asked: two. The behaviour is correct and bounded by the number of allowed kinds
(at most two), but `VA-NEW-10` changed no `get_json` budget, so a scene whose
preferred kind fails costs up to `2 × max_retries` HTTP requests where it used
to cost `1 × max_retries`. This is a fact about cost, not a defect in M2-A — and
it is exactly why the M2-B unit below is the request rather than the query
attempt. It was not written into M2-A CLOSURE.

**M2-B CLOSURE (2026-08-15).** `VA-NEW-12` is closed by the bounded **PLAN-10C**
correction in the commit containing this record. Nothing else in that section
starts: the adaptive `quick`/`standard`/`deep` contract, scene weight, subject
complexity, plateau detection on best-so-far, "enough candidates already", the
escalation order to the local library or another provider, and the
`partial preview` / `E_generated` / `F_emergency` acceptance criterion are all
untouched. The section keeps its `blocked` status and no PLAN-ID is created.

**The defect was the composition, not the retries.** `VA-NEW-10` (M2-A) was
about sending one request repeatedly; `VA-NEW-12` is about how many *different*
requests one scene sends. Per-source caps existed — `limit=5` bounds the results
of a single query — but nothing bounded provider × query after composition:
`_search_scene_providers` (`src/news/asset_manifest_builder.py`) walked every
routed provider against every allowed query to the end of the plan, regardless
of what had already come back. Measured on the real production path at
`36f23cc`, not modelled: one scene with three providers sent **36** provider
search requests, and two such scenes sent **72**. The widest fan-out in any
project on disk is 30 query attempts across five providers
(`2026-08-09_diagnostic-ru-semantic-live-2`, `scene_002`), which under current
retrieval symmetry costs up to **60** requests; the audit's analytical worst
case is 5 providers × 19 queries × 2 kinds = 190.

**The unit is one `provider.search` call — one query against one media kind.**
That is what a provider rate-limits and bills for. A *query attempt* is
deliberately not the unit: since `ae6d46c` a mixed scene sends one request per
allowed media kind, so counting attempts undercounts real cost by exactly that
multiplier — the side effect recorded above. An *HTTP request* is not the unit
either: a single search may retry inside `ProviderHttpClient`, which M2-A made
the sole owner of that decision, and a retry is a different question about the
same request. `provider attempt`, `candidate attempt` and `HTTP request` stay
three separate things.

**One counter, one hard stop, and the primitive is not called when it is spent.**
`SceneRequestBudget` (`src/news/asset_provider_adapters.py`) is created once per
scene by the builder and travels down; the general search and the draft ladder
share the same object, so a nested layer cannot open a second full allowance and
re-create a hidden N². The ceiling is enforced inside `search_provider`, the last
owner before the wire: a kind with nothing left is never sent rather than sent
and discarded. `_search_scene_providers` also checks before starting a query, so
an exhausted scene adds no empty rows to the ledger. A failed request is spent —
failure does not refill, or a provider that is down would cost less than one that
answers. `build_scene_queries` is untouched: the budget decides how many queries
are *sent*, never how many are *built*.

**`targeted_slot_search` is inside the budget, deliberately.** It is the scene's
second route to a provider. Rule 7 already bounds it to one pass per scene, but a
pass is not a cost, and a ceiling one route can walk past is not a ceiling. It
draws from the same object and records its own refusal when there is nothing left.

**The stop is honest and is not a failure.** It rides the existing attempt ledger
as `status: skipped` with `reason: request_budget_exhausted`, carrying
`request_budget` (limit and spent) and how many planned queries never went out —
distinguishable from provider failure, rights rejection, no results, semantic
abstain, malformed response and `query_translation_required`. No new status
vocabulary, no new persisted artifact: the full stop-reason dictionary remains
**PLAN-10A**. An untranslatable provider is recorded before any request is sent,
so a budget stop can never suppress that plan-level fact.

**Nothing found is lost, and partial success from M2-A survives.** Reaching the
ceiling keeps every candidate already collected, does not reset the scene, does
not block the next scene — each scene gets its own budget — and does not prevent
a reviewable draft. When the budget cuts between two media kinds, the kind that
answered keeps its candidates and the kind that was cut is honestly unresolved.
Rights, semantic and quality thresholds are untouched; no `publish_ready` is
granted, `strict` is not weakened, and network default-deny is unchanged.

**Determinism.** No wall clock, no hidden reset. The ceiling is
`asset_selection.max_provider_requests_per_scene`, default **64** — above the
widest run the product has actually performed (60) so no real scene changes
behaviour, below the analytical worst case it truncates. "Unlimited" is refused
in every spelling: a negative or non-integer value is replaced by the default
rather than interpreted, because `-1` means unlimited in enough other systems
that honouring it would reintroduce this defect; an explicit `0` is a real choice
and is honoured.

**Resume — `ASSET_SEARCH_FINGERPRINT_VERSION` deliberately stays 1, and this was
proved rather than assumed.** A *configured* ceiling lives in `asset_selection`,
which `asset_search_fingerprint` (`src/news/pipeline.py:127`) already hashes
verbatim in its payload, so a changed configured budget already stops a stale
search being reused — covered by its own test. The code default **64** is not in
the payload, and no channel sets `max_provider_requests_per_scene` today, so
changing that default in code does not invalidate a completed `asset_search` —
exactly the same class as every other code default in `_selection_config`, and
not a gap this slice leaves open. The version field's contract
(`src/news/pipeline.py:106`) is "bump when the payload changes", and the payload
does not change. The default is a code constant, which is not an input, exactly
as M2-A reasoned. No second resume contract and no persisted cross-process budget
state exist: the budget is per-scene, in-process, created once per scene, and a
resumed run re-creates it once — resume cannot refill it inside one active
operation.

**Draft vs strict.** Identical ceiling, and `strict` is not weakened by it.
`draft_complete` simply has a second route to a provider (the ladder), and that
route is inside the same budget. `dry_run` sends nothing and is unchanged.

**What the ceiling is hard over (wording corrected 2026-08-15).** One *search
invocation*. `draft_complete` runs the adaptation pass after the first manifest
(`src/news/pipeline.py:586` → `run_adaptation_pass` → a second
`build_asset_search_manifest`), and a second builder creates a second
`SceneRequestBudget` for a changed scene. So across the whole `asset_search`
stage a re-researched scene can spend up to **2 x budget**, and an unchanged
scene still spends at most one. That is bounded and deterministic —
`MAX_ADAPTATION_PASSES = 1` (`src/content/script_engine/adaptation.py:46`) — and
the behaviour is correct; only the earlier phrasing, which read as a per-stage
ceiling, was not.

**What deliberately stays out.** The full PLAN-10C adaptive contract and plateau
policy. The PLAN-10A attempt ledger and stop-reason dictionary. Pagination and
exhaustion, `C75`–`C78`, `VA-NEW-13` — **PLAN-10B**. `C47` and the local library
— **PLAN-10D**. Vision and semantic default activation — **PLAN-9E**. Ranking
and semantic quality, required-action matching, crop verification. The
documentation line-count failure — still its own owner decision, still not
repaired here. No provider was removed and no rights, semantic or quality
threshold was lowered to fit the budget.

**One network path continues after a budget stop, by design.** The budget is a
*search request* budget. Downloading a candidate already found, and preview /
Vision analysis of the shortlist, keep running — they have their own existing
caps and owners (the download ladder's `max_attempts`, `ProviderHttpClient` from
M2-A, `shortlist_size`, `maximum_candidates`, and the separate paid-approval
gates), and stopping them would delete the "nothing found is lost" property. No
*search* path continues. `src/news/asset_manager.py::_complete_scene_assembly`
is an unbudgeted compatibility wrapper with zero callers in `src/` and `tests/`;
it was left untouched rather than quietly changed.

**Evidence.** RED first on `36f23cc` through the real production path
(`build_assets_manifest` → `_search_scene_providers`), not an isolated fake
counter: **15 failures and 2 errors across the 13 owning checks** — every one of
the 13 was RED — on real numbers: 36 requests where 10 was configured, 36 again
in each of the five exact-ceiling subTests (1, 2, 3, 7 and 12), 72 across two
scenes, 36 where 0 was configured, 28 from two always-failing providers — plus 2
failures over the draft ladder (5 requests where 3 were configured, and no stop
recorded at all). GREEN after: 13 owning checks plus 3 draft-ladder checks and 1
fingerprint check OK. Exactly two of those 17 never had a RED state and are
honest guards rather than reproductions: the fingerprint check, which would have
passed before the change too and exists to prove *why* no version bump is owed,
and the draft-ladder check that the ceiling bounds the ladder without disabling
it. `test_an_untranslatable_provider_survives_a_budget_stop` is **not** one of
them — it was RED at `36f23cc` like the other twelve. (This corrects both earlier
accountings of the same run: 16/2, then 14/2 across 12 checks, with the
untranslatable-provider check named as the second guard. The counts were
re-derived by re-running the current checks against an extracted `36f23cc` tree,
not read from a report.) M2-A regression radius (`PartialMixedMediaRetrievalTests`,
`TargetedSearchPartialMediaTests`, `DownloadRetryOwnershipTests`) 13 OK; owning
targeted radius 91 OK; media-policy radius 35 OK; full canonical offline suite
**2291** (2274 baseline plus exactly the 17 new checks) with the same single
pre-existing doc-length failure of PRE-M2 CLOSURE and nothing else — failures
before 1, failures after 1, no new failure; gates OK. That failure is now 183
lines against the 100-line limit because this record and its three mirrors add
to the same documents; it is still the documentation governance contract and is
still deliberately not repaired here. No network, paid, Vision, TTS or render
call was made. **Ratchet not taken:**
`src.news.asset_manifest_builder`, `src.news.asset_provider_adapters` and
`src.news.asset_scene_completion` keep their mypy baseline suppression — measured
at 11 errors both at `36f23cc` and after this change, so this slice adds none,
and all 11 are pre-existing debt in functions it does not touch (the
`AssetProvider`/`StockProvider` protocol mismatch), whose repair is the mass
cleanup that may not share a slice with a behaviour change.

**REVIEW #3 CLOSURE (2026-08-15).** Independent review over M2-A and M2-B
together, per the recorded batching strategy, is complete. Owner-provided verdict
**ACCEPT WITH MINOR NOTES**, **0 BLOCKER / 0 MAJOR**, no repair slice before the
next one — the same class of evidence as the earlier externally-run reviews, so
it leaves no review commit of its own in Git. Retrieval code is not touched by
this record. Its MINOR notes are absorbed by the WP0-B slice containing this
block rather than by a slice of their own, and each was re-verified against the
repository first rather than accepted as stated:

- the mypy count in **M2-A CLOSURE** said 7; independently re-measured it is 11,
  identically at `3633e0a`, `36f23cc` and HEAD — corrected above, delta still 0;
- the **M2-B CLOSURE** RED accounting said 14 failures and 2 errors across 12
  checks and named the untranslatable-provider check as a never-RED guard; the
  measured run is 15 failures and 2 errors across 13 checks, that check *was*
  RED, and the second honest guard is the draft-ladder one — corrected above;
- "hard ceiling" is per *search invocation*: in `draft_complete` the adaptation
  pass can spend a second bounded budget on a changed scene — scoped above;
- the fingerprint carries the *configured* ceiling, not the code default 64, and
  no channel sets the key today — scoped above;
- the targeted-search stop reaching manifest-level `provider_attempts` but not
  the scene entry's is a pre-existing ledger shape M2-B did not introduce; it now
  has a registry row (**C82**) under the existing ledger owner **PLAN-10A**
  instead of a new PLAN-ID.

Next: **LIVE-5**, the owner-issued live provider diagnostic — the whole set the
audit named as mandatory before it (`VA-NEW-01`…`VA-NEW-06`, `VA-NEW-08`,
`VA-NEW-09` plus the minimal `VA-NEW-10`/`VA-NEW-12` budget guards) is closed. It
is a paid network action and needs its own explicit owner approval; nothing here
grants it. `WP0-B` part two stays open. Checkpoint remains PLAN-9D.


**AUD-DELTA-CLOSE (docs/accounting, 2026-08-13).** Three docs-only commits
landed the two finished audits and changed no route: `6224c6f` copied both
reports into `docs/audits/` as evidence, gave the directory its first index and
banner-labelled fifteen documents that were teaching a pre-canonical world;
`a577c22` corrected `C01-SEM` after PLAN-9C and registered the retrieval
findings as registry rows `C64`–`C74`, rejecting three of the report's own
proposals that did not survive re-verification; `1f67e29` rewrote the root
README from the code. None carried a `Plan-Step` trailer and none was recorded
here — this block is that record. The commit containing it closes the last five
accounting defects found by the 2026-08-13 reconciliation (stale `PLAN-9D-D`
status in both routing mirrors, this file's `updated_at`, the
`ARCHITECTURE_BOUNDARY_MAP` claim that a deleted file is preserved, and the
missing accounting above), deletes `COMMANDS.md` under **OD-S-7** / **PLAN-7**,
and moves the confirmed EXP-001 provider defects out of the experiment journal
into registry rows `C75`–`C78` under the existing owner **PLAN-10B**. No
PLAN-ID is created, no step changes status, `PLAN-7` stays `pending` — its
README half is delivered, its three `SKILL.md` files still teach
`src.content_creation.cli`. Production code, config, schemas and tests are
unchanged.

**Owner decision 2026-08-13 on C65 (legacy network bypass).** A temporary
`require_network` gate over the legacy call sites is **not authorized**. The
question is deferred to after Review #2 and re-framed: first establish whether
the legacy retrieval stacks can simply be retired, because improving code that
is about to disappear buys nothing. Registry row **C65** records this; the
finding stays open and no bounded correction is started.

**RETRIEVAL DIAGNOSTIC PACKAGING — PROPOSAL, NOT AN OWNER DECISION
(2026-08-12).** The owner-authorized read-only retrieval diagnostic proposed
seven separate fixes, and the grouping recorded here is that diagnostic's own
recommendation, kept so a new chat can find it. It is **not** an owner decision:
it creates no PLAN-ID, does not change `current_checkpoint` or
`next_exact_action`, and authorises no implementation. Proposed grouping:
**RD-A** video observability, **RD-B** query recall quality (short primary query
· subject/action-preserving fallback · orientation widening), **RD-C** source
routing (`source_class` and the provider budget it spends), then a repeated
image+video evaluation before any threshold / provider-trust / license-policy
work. The proposal further suggests that RD-B improve the existing expansion
owner rather than place a second synonym dictionary beside it, and that duration
vs multi-slot stay a separate problem. **Every one of those points still needs a
separate owner decision, and RD-B/RD-C are not implemented.** The owner bounded
the 2026-08-12 session to exactly two items — the confirmed Pixabay preview
defect and the review-bundle selected-asset invariant — and only those are
closed below. Cheetah source scarcity remains unproven in either direction: it
was judged from a single preview frame while half of the Pixabay videos carried
no preview at all, which is the defect VA-NEW-22 closes.

**RD-A CLOSURE.** Both authorised corrections are closed by the commit
containing this record; neither starts its section's own contract. `RD-A` here is
the proposal's label, used only to name the pair.

- **VA-NEW-22** (`src/providers/pixabay_provider.py`, inside **PLAN-10B**). The
  video preview URL was derived from the top-level `picture_id`, which current
  Pixabay responses no longer carry. The preview came back empty, the candidate
  fell through to downloading a video variant, and the 5 MB preview cap then
  refused it — the video existed, was ranked, and could not be looked at. The
  adapter now reads the thumbnail of the rendition it actually chose, then the
  largest rendition carrying one, and keeps `picture_id` as the reader for older
  payloads. This is the precondition for any video benchmark, and for retesting
  cheetah retrieval.
- **VA-NEW-23** (`src/assets/review_bundle.py`, its production seam
  `_prepare_visual_review` and the compatibility rebuild
  `prepare_visual_preview_for_project` — all three reachable callers, inside
  **PLAN-9A**, the same selected-asset lineage family as VA-NEW-04). The bundle
  could name a selection it did not show: an
  asset found by download retry or the draft-completion ladder after the review
  window was frozen became `selected_candidate` while the board rendered only
  the frozen shortlist, and a scene where selection honestly abstained was
  relabelled with the top-ranked candidate. The named asset is now placed on the
  board, and an abstention stays an abstention in the bundle and in the
  `selected_candidate_before/after_rerank` report. Additive and tolerant: one
  extra entry in the existing `shortlist`, one existing `preview_status` value,
  no new persisted field, no schema-version bump, no migration.
  **Declared boundary, not an oversight:** `_apply_fallbacks` runs after the
  bundle is attached, so a scene answered by `generated_fallback_asset` (a
  synthetic text card, `selected_by: generated_fallback`, no provider material,
  no preview, no rights review) still leaves the board showing no selection.
  That is retrieved-material scope: the candidate board's whole vocabulary —
  provider, license, framing, vision tags — describes nothing about a generated
  card, and the manifest plus missing/fallback reporting already own that fact.
  Closing it would move the attach call in the scene build order and belongs to
  an owner decision, not to RD-A.

Evidence: RED first on `a52103e` — Pixabay preview 1 failure, review-bundle
invariant 2 failures, production abstention seam 1 failure, compatibility
rebuild 1 failure. GREEN after: owning radius 146 OK, full canonical offline
suite 2208 OK, gates OK. Ratchet not taken: `src.assets.review_bundle`
and `src.news.asset_manifest_builder` keep their mypy baseline suppression,
because the owner bounded this session to the two corrections above and the
typing cleanup that would lift them is not part of either. Ranking, rights,
media policy, the review window and the query path are unchanged. Checkpoint
remains PLAN-9D.

**WHY NOT LIVE-5 YET.** LIVE-5 — owner-issued live provider diagnostic, а не
plan step. Он измеряет качество отбора по persisted evidence, а
`docs/audits/VISUAL_ASSET_INTEGRITY_AUDIT_2026-08-10.md` доказал, что часть
этого evidence сегодня недостоверна (candidate A против downloaded B, preview
о старых bytes, потерянные partial mixed-media результаты) и что бюджет
запросов не ограничен. Аудит (`40, ответ 12; «Краткий отчёт владельцу») прямо
называет обязательный до LIVE-5 набор: **VA-NEW-01, 02, 03, 04, 05, 06, 08,
09 плюс минимальные budget guards 10/12**. Из него закрыты 01, 02, 03, 04 и 05.

> **Статус-коррекция набора (2026-08-15):** строка выше отражает состояние до
> M1-D/M1-E и M2-A/M2-B и больше не актуальна. Фактически закрыт **весь**
> перечисленный набор: 01, 02, 03, 04, 05 (блоки M1-A…M1-C), 08 (M1-D), 09
> (M1-E), 06 и 10 (M2-A, commit `36f23cc`), 12 (M2-B, commit `7e2b85c`).
> Необходимых по контракту аудита блокеров LIVE-5 не осталось; классы A/A′/B
> и состав набора при этом не пересматривались.

**LIVE-5 CLOSURE (2026-08-15).** LIVE-5 выполнен и записан в
[docs/audits/LIVE_5_2026-08-15.md](../audits/LIVE_5_2026-08-15.md) от HEAD
`68c46cd`; проект
`projects/2026-08-15_solnechnaya-panel-lovit-svet-tolko-dnem-nochyu-2`.
Новый PLAN-ID не создан, checkpoint остаётся PLAN-9D, providers/retrieval/ranking
не менялись.

Измерено: прогон дошёл до конца (`draft_completed`), 5 из 5 сцен получили слот
против 3 из 5 в baseline 14.08, 7 слотов, все — реальные provider-ассеты, без
generated/emergency карточек и без дублей. Права чистые: 7 из 7 verified,
0 blocked. Видео-слотов по-прежнему 0, `publish_ready` false, субтитры в MP4
не попали (оба выходных файла байт-идентичны). Платное: 15 вызовов semantic
brief на $0.15 и одна генерация ElevenLabs.

Вердикт **PARTIAL**: покрытие и права выросли, но по смыслу верны только 2 из 5
сцен (сцены 002, 003 и 004 — подмены), а PASS требует 4 из 5. Визуальную оценку
владелец выставляет сам по review board и итоговым кадрам.

Открытым осталось: `C79` (самый дорогой дефект прогона — смысловые слова сцены
остаются по-русски в matchable-полях), `C75`/`C76` (Wikimedia video: 44 попытки,
0 результатов), `C77`, `C78`, `C82` (стоп на 64 запросах не виден в scene-level
реестре) — измерены и не исправлены. Два новых дефекта записаны строками в
registry: `C83` (`use_local_library` — мёртвый ключ, локальная библиотека
участвовала в скоринге вопреки выключению) и `C84` (потолок вызовов semantic
brief действует на адаптер, а не на проект: 15 при заявленных 12).

**WHAT MUST HAPPEN BEFORE LIVE-5.** Каждый пункт — bounded correction внутри
уже существующего owner; новых PLAN-ID нет. Класс **A** — прямо искажает
evidence самого LIVE-5; **A′** — не искажает evidence, но делает сам live-run
небезопасным по стоимости/rate-limit; **B** — обязателен до Vision / render /
resume acceptance, но не до LIVE-5 по контракту аудита.

| Label | Finding | Canonical owner | Existing PLAN step | Почему там | Класс | До LIVE-5 | До v1 |
|---|---|---|---|---|---|---|---|
| M1-A | VA-NEW-01 continuity self-evidence | `continuity_checker` → `evidence.build_evidence` | **PLAN-9C-3** (correction) | evidence ownership границы 9C-3 | A | **закрыт** `15cb20d` | да |
| — | VA-NEW-03 technical rerank | `_prepare_visual_review` | **PLAN-9C-2** (correction) | второй post-selection owner | A | **закрыт** `37ca498` | да |
| M1-B | VA-NEW-02 preview cache не идентифицирует source snapshot | `src/assets/visual_preview.py` | **PLAN-9A** | persistence/provenance | A | **закрыт этим M1-B commit** | да |
| M1-C | VA-NEW-04 review artifact mixed candidate A with downloaded B | src/assets/review_bundle.py | **PLAN-9A** | selected-asset lineage | A | **closed by this M1-C commit** | yes |
| M1-C | VA-NEW-05 Vision tags were lost during download rebuild | asset_manifest_builder / asset_provider_adapters | **PLAN-9A** | snapshot-bound evidence carry | B (Vision blocker) | **closed by this M1-C commit** | yes for Vision |
| M1-D | VA-NEW-08 resume без input/policy fingerprints | `src/news/pipeline.py` | **PLAN-9A** | persisted resume contract | B (до опоры на resume в LIVE) | **закрыт этим M1-D commit**; provider identity вынесена к VA-NEW-06/M2-A — см. M1-D CLOSURE | да |
| M1-E | VA-NEW-09 strict render TOCTOU | `src/news/final_renderer.py` | **PLAN-9E** | render authorization gate | B (до LIVE render) | да | да |
> **M1-E status correction (2026-08-14):** the row above is closed by the M1-E
> commit containing this record; the historical pending marker is superseded.

| M2-A | VA-NEW-06 partial mixed-media success теряется | `search_provider` | **PLAN-10B** | provider error composition | A | **закрыт** `36f23cc` | да |
| M2-A | VA-NEW-10 nested retries R² | `src/assets/http_client.py` | **PLAN-10B** | один retry owner | A′ | **закрыт** `36f23cc` | да |
| M2-B | VA-NEW-12 uncapped request budget/stop | retrieval budget | **PLAN-10C** | budget/plateau policy | A′ | **закрыт** `7e2b85c` | да |
| RD-A | VA-NEW-22 Pixabay video preview reads a field current responses no longer carry | `src/providers/pixabay_provider.py` | **PLAN-10B** (correction) | provider contract behavior | A | **closed by this commit** | yes |
| RD-A | VA-NEW-23 review bundle named a selection it did not show | `src/assets/review_bundle.py` | **PLAN-9A** (correction) | selected-asset lineage | A | **closed by this commit** | yes |

Уточнения к mapping аудита, проверенные по репозиторию:

- **Все шесть пакетов — bounded corrections внутри чужих секций, а не старт их
  контрактов.** Это уже действующий паттерн: VA-NEW-01 и VA-NEW-03 закрыты
  именно так. Порядок «M1-B…M2-B раньше PLAN-9D-D» — owner-approved reorder,
  зафиксированный здесь **до** работы, как требует правило порядка в разделе
  «Что осознанно не оптимизировано».
- **PLAN-9A** достижим: его prerequisite chain (`PLAN-9B-2` + `PLAN-1C′` +
  `PLAN-6E`) закрыта 2026-08-07. Выданный ему owner approval покрывает только
  перечисленный в его секции состав полей. `replaces_asset_id` из `VA-NEW-04`
  вышел за этот состав, и owner decision на него был выдан текстом M1-C
  prompt — **satisfied**, closed commit `c9537fa` (Review #1 ACCEPT
  2026-08-11). `VA-NEW-08` fingerprint тоже вышел за этот состав, и owner
  decision на него выдан текстом M1-D prompt — **satisfied**, closed этим
  M1-D commit; фактический состав полей записан в блоке «M1-D CLOSURE».
- **PLAN-9E** (M1-E) и **PLAN-10B/PLAN-10C** (M2-A/M2-B) формально blocked
  своими секциями. Bounded correction выполняется под их ID, статус секции при
  этом не переводится в completed — так же, как PLAN-9C-2/9C-3 приняли
  corrections после closure.
- **VA-NEW-18** и **VA-NEW-19** остаются `NO OWNER` → **OWNER DECISION
  REQUIRED**; новый PLAN-ID автоматически не создаётся.

**WHAT MUST HAPPEN BEFORE V1.** Проверено по `PRODUCT_PLAN.md` разделы 5, 6,
10 (MSP direction и критерии выхода в beta) и по ADR: канонический CLI/Wizard
путь · достоверный decision/evidence путь (набор LIVE-5 выше) · bounded
retrieval · user assets как канонический вход (**PLAN-9B-5b**, PD-4) ·
обязательный human review · работоспособный preview (registry **C58**, owner
**MOTION-CS1**) · rights · voice · субтитры · render · truthful export
(registry **C44**: owner gate **PLAN-11** + будущий bounded catalog slice) ·
resume без потери результата · реальные acceptance-evidence и несколько
настоящих Shorts без правки кода между обычными прогонами.

**WHAT DOES NOT BLOCK V1.** Платный Vision · Vision A/B · semantic model
default-on · longform · legacy retirement · полная governance diet · крупный
structural cleanup. Основание: `PRODUCT_PLAN.md` раздел 8 («Vision никогда не
mandatory runtime dependency», статус `COMMITTED_LATER`), раздел 7.1 (longform
`COMMITTED_LATER`) и раздел 10 (MSP не содержит ни одного из них).

**WHERE VISION LIVES.** Wiring — **PLAN-9C** (закрыт). Offline evidence и A/B —
**PLAN-9D-F** / **PLAN-9D-G**, оба остаются optional quality track и v1 не
блокируют. Активация — **PLAN-9E**, default OFF, отдельные network и paid
gates. Обязательные до активации: `VA-NEW-02`, `04`, `05`, `08` и единый
post-review decision invariant (аудит `40, ответ 15).

**WHERE SEMANTIC DEFAULT ACTIVATION LIVES.** Там же — **PLAN-9E**. Для v1
semantic assistance остаётся opt-in: `semantic_brief` в
`src.runtime_network.NETWORK_ACTIONS` (default deny) плюс
`config/semantic_brief.json` (в репозитории выключено). v1 обязан проходить
acceptance через manual / provider-metadata / human-review путь.

**WHAT FIRST OWNER SHORT LEFT WITHOUT AN OWNER (запись 2026-08-14; маршрут,
статусы и checkpoint не меняются).** Первый черновой MP4 этой программы
существует, и три дефекта за его слабыми кадрами получили строки реестра
вместо владельца по ошибке:

- **`C79`** — русская морфология: extraction стеммит (`entities.py:94`),
  evidence-матчинг умеет только префикс (`evidence.py:181`). Это **не**
  `PLAN-10C` (adaptive budget / plateau policy) и **не** `C40`/`PLAN-10D`
  (глобальная локальная библиотека); прежняя атрибуция в отчёте была ошибочной
  и исправлена. `MISSING OWNER CANDIDATE` → **OWNER DECISION REQUIRED**.
- **`C81`** — визуальный hook: `hook_score` существует для первого предложения
  сценария и не имеет эквивалента для первых секунд кадра. Владелец
  автоматически не назначается: сначала нужно решение, продуктовое ли это
  требование v1. `MISSING OWNER CANDIDATE` → **OWNER DECISION REQUIRED**.
- **`C80`** — Vision мимо `runtime_network` default-deny: записан внутри
  существующего **PLAN-9E**, нового PLAN-ID не требует.
- **повтор кадра** (сцена 1 = сцена 3) — это `C47` под **PLAN-10D**, а
  PLAN-10D стоит в списке **WHAT IS POST-V1** ниже. Если владелец считает
  повторяющийся кадр блокером v1, это **отдельное owner decision**: данная
  запись порядок работ не меняет и PLAN-10D вперёд не выносит.
> **Owner-decision correction (2026-08-14).** This supersedes the unresolved
> classifications in the bullets above: `C79` is a pre-v1 bounded correction
> after STOCK diagnostic and before M4/PLAN-11 in existing `entities.stem` /
> `semantic_selection.evidence` owners, characterization-first and without a
> second stemmer or RU path. `C81` is not a v1 requirement and remains post-v1
> product discovery without an implementation owner. The repeated frame blocks
> publish-ready for its artifact without manual replacement/approval, not
> platform v1; PLAN-10D stays post-v1. This docs slice does not authorize STOCK
> repeat: a separate execution prompt must name network/paid scopes. The paid
> bounds of live `semantic_brief` as this decision found them were corrected by
> `C84`/`C85`/`C86`; what each bound now does is stated in the `C84–C86` block of
> `CLEANUP_REGISTRY.md`.


**WHEN M3 / M4 / M5.** `M3` (user product slice) начинается после LIVE-5:
user assets в canonical create (**PLAN-9B-5b**), pre-search/pre-paid control
point (**PRODUCT_PLAN** 16.3.2, требует **OD-P-2** → OWNER DECISION REQUIRED),
preview (**C58** / **MOTION-CS1**, требует **OD-P-12**), **C63** (author brief
на topic/article paths — `MISSING OWNER CANDIDATE` в реестре → OWNER DECISION
REQUIRED). `M4` (acceptance / v1) — существующий product evidence gate
**PLAN-11** плюс product test-video checkpoint секции **PLAN-9E**. `M5`
(longform / v1.1) — после v1.

**WHEN LONGFORM V1.1 STARTS.** После v1, и подтверждено репозиторием:
ADR 0016 («`content_creator` owns creation of both short and long videos;
documentary — future workflow/template, not a separate application»),
`PRODUCT_PLAN.md` PD-9 и раздел 7.1 («один `content_creator` с format/workflow
profiles»; общее ядро — input · script · scenes · visual planning · query
planning · retrieval · rights · ranking/selection · evidence · audio ·
persistence; различается только format policy: aspect ratio, длительность,
pacing, плотность сцен, главы, crop, раскладка субтитров, render profile,
motion policy). **Route-level requirement:** все shared-core исправления
M1–M3 обязаны быть **format-neutral** — новые portrait/1080x1920 допущения в
shared services без продуктовой необходимости запрещены. Второй video engine
запрещён (ADR 0016, PD-9). **Существующие входы (запись 2026-08-13, маршрут не
меняется):** выбор отрезка внутри клипа начинается с переиспользования
`src/assets/temporal_video_analysis.py` (**C73** реестра), а недостающее звено —
источниковый временной диапазон: `clip_start`/`clip_end` в модели кандидата и
`-ss` по источнику в render path. Второй segment engine не создаётся; рабочий
образец сегментного извлечения уже есть в `anime_factory` (**C07**).

**WHAT IS POST-V1.** `M5` longform/v1.1 · retirement legacy (**PLAN-L1…L4**,
**PLAN-9B-5b** wrapper retirement) · Vision activation при желании владельца ·
**PLAN-10D** · **PLAN-12**…**PLAN-15** · Motion (`MOTION-CS1…CS4`).
`WP0-B` в этом списке **не стоит**: он current и открыт — единственный его
статус записан в блоке «WP0-B (governance/docs diet) — placement» ниже.

**REVIEW BATCHING STRATEGY.** Recommended execution policy; контракт review в
`AGENTS.md` и `skills/review-change/` не меняется. Review #1 — M1-A…M1-C
(identity / evidence lineage: один и тот же вопрос «доказывает ли evidence
именно тот asset»). Review #2 — M1-D…M1-E (authorization над persisted
state: resume и strict render). Review #3 — M2-A…M2-B, до LIVE-5 (retrieval
resilience и budget). Границы совпадают с фактическими risk boundaries:
каждая тройка меняет один класс инвариантов и один набор owners.

**WP0-B (governance/docs diet) — placement. Это единственный статус `WP0-B` в
current-документах: current и открыт, не post-v1.** Окно «parallel, между M2-B и
LIVE-5» израсходовано — LIVE-5 прошёл 2026-08-15 без WP0-B. Прежнее обоснование
(запас routing mirrors в пять строк) израсходовано тоже: REVIEW #3 ужал зеркала
до 87/94/148 при лимитах 100/280/240. Действующее обоснование измерено
2026-08-16: журнал не исчез, а переехал сюда — план вырос с 7 471 строки на
`f3b607a` до 8 275 за три дня, секция «Current checkpoint» держит 1 578 строк,
`next_exact_action` — 142 строки с девятью «IS DONE / closed by». **Последнее
закрыто 2026-08-17 пакетом B:** поле сокращено с 10 227 символов до 545, журнал
перенесён дословно в «Routing journal» ниже, а `NEXT_EXACT_ACTION_MAX_CHARS`
в `tools/qa/check_agent_docs.py` не даёт ему вырасти снова. Остальная часть
обоснования в силе: секция по-прежнему длинная. Состав WP0-B
(ROUTE.md, упрощение mirrors, архив журналов и completed-секций, docs diet,
README/COMMANDS truth, size guards) ни одной сверкой не выполнен. **Порядковое ограничение
(добавлено 2026-08-13, governance audit R9):** ADR-бэкфилл выполняется **до**
переноса закрытых секций в архив, иначе обоснования долговечных решений уедут в
архивный snapshot вместе с временным документом. Кандидаты названы аудитом
(`docs/audits/AI_DEVELOPMENT_SYSTEM_AUDIT_2026-08-12.md`, раздел 12): все ADR
созданы одной волной 2026-07-28/29, с начала программы новых нет, потому что
триггер `skills/architecture-change` требует ADR только при смене публичного
контракта или границы системы. Расширение триггера (новый module-owner · новое
persisted-поле · новый config-gate · новый класс сетевых действий) — часть того
же пакета. Номера будущих ADR здесь не резервируются: ссылка на несуществующий
ADR роняет `tools/qa/check_agent_docs.py`.

**G-1 ADR-бэкфилл закрыт (2026-08-17), C92.** Три ADR по составу, подтверждённому
владельцем: `docs/adr/0019-network-default-deny-by-named-action-class.md`
(PLAN-STAB-4), `docs/adr/0020-rights-and-render-authorization-fail-closed.md`
(PLAN-STAB-5/9 + M1-E fresh checksum) и
`docs/adr/0021-paid-semantic-brief-two-independent-gates.md`
(PLAN-9B-PRODUCER-M-LIVE). Триггер `skills/architecture-change` расширен тем
же пакетом (см. выше). **Четвёртый кандидат аудита — «единый владелец
отбора» (9C-2, media-selection owner) — в этот слайс не входит и ADR не
получает: владелец решением G-1 подтвердил, что он уже описан closure-блоками
плана и самим кодом (`src/assets/semantic_selection`), отдельной ADR-записи не
требует.** Из шести кандидатов R9 два (versioned permission-контракт
STAB-6 и resume fingerprint M1-D) этим слайсом отдельного ADR тоже не
получили — они не входили в подтверждённый состав G-1 и остаются
неадресованным остатком долга R9, если владелец не примет иное решение.

**FIRST OWNER SHORT (optional product diagnostic).** Владелец может получить
первый настоящий draft Short раньше acceptance, не выдавая его за
publish-ready: manual assets плюс ручной `visual_brief` по сценам, режим
`draft_complete` (всегда `publish_ready=false`), script/text path вместо
произвольной темы. Ограничения, которые нужно знать заранее: `C63` — author
brief не доходит до сцен на topic/article paths, поэтому нужен user-supplied
script; `C58` — честного pre-final preview нет, оценивать придётся готовый
`draft_1080x1920.mp4`. Это диагностика продукта, а не acceptance; сеть и
платные действия требуют отдельного owner approval. Этой сверкой не
запускается.

- **Текущий шаг:** **PLAN-9D — offline visual-quality evidence.**
  Шаг **in progress**: `04fe035` выполнен под `Plan-Step: PLAN-9D` и дал
  benchmark harness и historical corpus, но шаг не закрыт. Оба его blocking
  prerequisite сняты: семейство **PLAN-9B** закрыто через свои под-слайсы
  PLAN-9B-2 (`66fd2431`/`8c60295`) и PLAN-9B-3 (`72221e1`), **PLAN-9C** закрыт
  2026-08-08 (см. ниже).
  **Owner direction 2026-08-08** переформулировал цель шага: decision quality
  измеряется на candidate pools, представляющих current retrieval behaviour, а
  не на historical polluted pools. Шаг разбит на под-слайсы
  PLAN-9D-A…PLAN-9D-G; top-level route
  `PLAN-9D → PLAN-9A → PLAN-10A → PLAN-10B → PLAN-10C → PLAN-9E` сохранён
  дословно, и current retrieval capture реализацией PLAN-10B не является.
  **PLAN-9D-A (historical evidence curation) closed 2026-08-08**, commit
  `2bae6f6d23d8cbf874fcf71883334a7ea4d8619d` — см. секцию PLAN-9D-A ниже. Это
  закрывает только PLAN-9D-A; **PLAN-9D в целом остаётся in progress** и
  ничего не утверждает о decision quality.
  **PLAN-9D-B (current-HEAD retrieval capture) closed 2026-08-08**, commit
  `69af3ca7387fa9fe649fabf0fd464ec519f76400` — см. секцию PLAN-9D-B ниже.
  Current corpus (14 сцен, 1064 наблюдения, 64 кадра) снят и заморожен;
  capture-integrity verdict этого docs closure — **VALID_CAPTURE**. Это
  закрывает только PLAN-9D-B; **PLAN-9D в целом остаётся in progress** и
  ничего не утверждает о том, хороший retrieval или плохой.
  **PLAN-9D-C (retrieval quality gate) closed 2026-08-09** — см. секцию
  PLAN-9D-C ниже. Gate прошёл: current retrieval действительно доводит
  заявленный субъект до провайдера и возвращает subject-relevant pool во всех
  14 сценах, дефекты CRITICAL-1/C35/C36 не повторились. Это закрывает только
  PLAN-9D-C; **PLAN-9D в целом остаётся in progress**, и качество *решения*
  этим не доказано — gate зафиксировал обратное для нескольких сцен.
  **Следующее точное действие** — отдельный owner-issued implementation slice
  **PLAN-9D-D** (human ground truth) в отдельном новом чате, строго по его
  contract; предварительно владельцу нужно принять два решения, записанные в
  секции PLAN-9D-C (неполный preview shortlist и selected-кандидат вне
  просмотренного набора). PLAN-9D-D этим слайсом **не запускается**.
  **Уточнено owner decision 2026-08-09:** до отдельного owner decision PLAN-9D-D
  остаётся **BLOCKED / NOT STARTED**. Diagnostic Short после PLAN-9D-C оказался
  заблокирован не retrieval-логикой, а тем, что обычный подготовленный русский
  сценарий вообще не несёт provider-language evidence: deterministic extraction
  выбрала субъектами грамматические дополнения, `produce_brief` честно вернул
  пусто, и большая часть сцен пришла в `query_adapter` со статусом
  `query_translation_required`. Root cause — отсутствующая semantic capability,
  а не сломанная проводка producer; deterministic fail-closed контракт остаётся
  верным и не ослаблен, PLAN-9D-C не переписывается. Владелец утвердил bounded
  capability-слайс **PLAN-9B-PRODUCER-M** (model-assisted semantic VisualBrief
  adapter внутри существующего visual-planning ownership) — **closed
  2026-08-09**, см. его секцию ниже. Ручной авторский бриф остаётся override, а
  не обязательной частью нормального workflow; **C63** остаётся открытым и не
  трогался; live model/network/paid активация остаётся будущим prerequisite и
  здесь не выполнялась. `current_checkpoint` не менялся.
  **Plan reconciliation 2026-08-10 (docs-only):** review activation commit,
  live-3 и live-4 выполнены (см. `next_exact_action` и секцию
  PLAN-9B-PRODUCER-M-LIVE); comparative audit принят как evidence
  (`docs/audits/VISUAL_ASSETS_COMPARATIVE_AUDIT_2026-08-10.md`). Следующее
  точное действие — owner-issued слайс **PLAN-9C-2** (unified media-selection
  policy foundation), затем **PLAN-9C-3** (metadata evidence repair); acceptance
  gate обоих — повтор того же diagnostic против LIVE-4 baseline; после него —
  owner decision о возврате к PLAN-9D-D.

  **PLAN-9C (semantic decision wiring) закрыт 2026-08-08.** Owner-issued
  implementation slice выполнен тремя immutable commits, все с trailer
  `Plan-Step: PLAN-9C`: `8932957` (feat — Vision evidence подключён внутри
  цикла отбора сцены к bounded shortlist, до скачивания, а не только после
  него в `_write_reviews`; evidence попадает в поле, которое уже читает
  decision owner — `vision_tags` через `evidence.build_evidence` →
  `candidate_ranker`; `select_best_candidate` остаётся единственным decision
  owner; закрыт также ранее зафиксированный дефект отчётности
  `semantic_rerank_enabled=False`), `668ff10` (fix — закрыт blocking finding
  review: шипованный default `MockSemanticVisualBackend` подтверждал любое
  требование из самого запроса и мог включить `publish_ready` на fixture
  evidence; `_apply_semantic_visual_evidence` теперь отказывается применять
  evidence, если сконфигурированный backend — fixture, по имени backend, а не
  по `paid_backend`; mock сохраняет только report/test роль), `8c1186f`
  (test — закрыт второй finding: guard-тест был вакуумно зелёным, потому что
  использовал `_WIRED` fixture с именем `"scripted"`, резолвящимся в
  `ExternalSemanticVisualBackend`, а не в mock; тест переведён на резолвер
  реального default backend, mutation-proof владельца подтвердил провал теста
  без guard `668ff10`; production-код не менялся). Final independent review
  вердикт **ACCEPT**, blocking findings **0** — owner-provided review evidence,
  тот же паттерн что PLAN-STAB-1/2/3, отдельного review-commit в Git нет.
  GitHub Actions run `31250693048` (headSha `8c1186f`, workflow
  `offline-tests`) — conclusion **success**, owner-provided evidence; этот
  docs-only closure commit получает собственную единственную read-only CI
  existence/status check на свой headSha после push. Default-конфигурация не
  менялась: `semantic_visual.enabled` и `semantic_rerank_enabled` остаются
  `false` по умолчанию, активация — по-прежнему gate **PLAN-9E**. Mock backend
  сохраняет только report/test роль и не имеет production reselection
  authority; `candidate_ranker` остаётся единственным decision owner, второй
  selector не создан. **F2** (review: после semantic demotion состав bounded
  shortlist/review window может измениться — pre-rerank preview set не равен
  post-rerank review bundle set, демотированный кандидат может выпасть из
  review artifact, новый кандидат — войти без preview, возможен
  дополнительный backend call и cost/evidence drift) — рейтинг **MAJOR**, но
  **NON-BLOCKING** для PLAN-9C, потому что acceptance PLAN-9C — это
  wiring/order, а размер shortlist и бюджет прямо названы контрактом
  `PLAN-10C` в самой секции PLAN-9C ниже; F2 записан bounded follow-up
  bullet'ом в существующей секции `### PLAN-10C`, не исправлялся, новый
  PLAN-ID не создавался. Другие findings review, упомянутые владельцем только
  по меткам (R2-R5), зафиксированы как non-blocking по тому же final verdict;
  их содержание этому closure слайсу не передавалось и ни в одном Git-артефакте
  не найдено, поэтому кроме F2 ничего не детализировано, не исправлялось и не
  придумывалось. Production-код, tests, схемы, config и runtime этим
  docs-only слайсом не менялись; новый owner, selector, service, abstraction,
  persisted-поле или PLAN-ID не создавались.

  **PLAN-1C′ (capability owner gate: asset/semantic) закрыт 2026-08-07.**
  Docs-only ownership inventory выполнен одним bounded commit: секция
  **C01-SEM** в `CLEANUP_REGISTRY.md` фиксирует по каждому модулю declared
  scope canonical owner, фактических callers, decision authority, persisted
  contract, owning tests и duplicate/overlap. Подтверждено кодом от clean HEAD
  `b0e99a7`: единственный владелец решения об отборе — `rank_candidates` /
  `select_best_candidate` в `src/assets/semantic_selection/candidate_ranker.py`
  на метаданных провайдера; `src/news/asset_manifest_builder.py` — только
  orchestration owner; `src/news/project_store.py` вместе с
  `src/news/pipeline.py` — persistence owner. `semantic_visual_service`
  подключён, но на отбор не влияет: `analyse_semantic_visual_for_project`
  вызывается из `_write_reviews` после отбора всех сцен и пишет evidence только
  в review-манифест; `vision_validator` — заглушка без единого caller и без
  owning test; `semantic_decision_policy` не подключён ни к одному
  production-пути. Seam для PLAN-9C уже существует и новым не является:
  bounded shortlist плюс `select_candidate_after_review` в
  `_prepare_visual_review`, и приём `vision_tags` существующим decision owner
  (`evidence.build_evidence` → `candidate_ranker`, reject `vision_mismatch`).
  **C31** перепроверен и подтверждён как неустранённый
  (`semantic_visual_evaluation_tooling.py:26,38,695` плюс tests); строка
  остаётся за **PLAN-13**, файлы не перемещались. Production-код, tests, схемы,
  config, manifests и runtime этим слайсом **не изменялись**; новый owner,
  selector, service, abstraction и persisted-поле не создавались; найденные
  дефекты записаны как evidence и **не исправлялись**.

  **PLAN-9B-3 (query-path cleanup) закрыт 2026-08-07.** Owner-issued
  implementation slice выполнен одним immutable commit
  `72221e1861f7c62de01aa09056cfaf6f56ef99a7`; independent review verdict
  **ACCEPT WITH MINOR** (blocking findings **0**), CI run `31195789804`
  (headSha `72221e1861f7c62de01aa09056cfaf6f56ef99a7`) — conclusion
  **success**. Implementer verification: targeted 243 OK, expanded radius
  209 OK, full offline suite 1780 OK, `check_agent_docs` exit 0,
  `check_task_scope` OK, `git diff --check` clean. **Все пять retirement
  candidates контракта PLAN-9B-3 закрыты** — obsolete GLOSSARY substring
  matcher (**C34**, harmful substring implementation ретайрена ранее commit
  `141beae` в **PLAN-9B-1**; текущий Unicode-aware token/phrase matcher и
  seed-словарь `GLOSSARY` являются replacement и сохраняются намеренно),
  orca topic hardcode `_apply_video_first_topic_briefs` (**C35**),
  `legacy_broad_query` (**C36**), deprecated `make_stock_query` (**C37**) и
  superseded `semantic_selection/query_generator.py` (**C38**) — последние
  четыре ретайрены этим commit и записаны строкой **R01** реестра.
  Формулировка «четыре из пяти закрыты» фактически неверна и не
  используется. Reversible retirement mechanism выполнен целиком: annotated
  tag `retired/query-paths-2026-08-07` на `1bbfcad` (последний commit, где
  код существовал), commit body с `Retired`/`Reason`/`Replaced-by`/
  `Recovered-from`/`Salvaged`/`Exit`, строка R01 в том же commit и внешний
  bundle `query-paths-2026-08-07.bundle` вне worktree. Envato manual query
  source сохранён: `manual_request` в `src/news/asset_manifest_builder.py`
  переведён с `ordered_queries` на `semantic_scene_queries`, а не потерян.
  Exclusion-список `_LEGACY_BROAD_QUERIES` в `src/assets/query_adapter.py`
  **шестым кандидатом не является и никогда им не был**: это
  persisted-compatibility guard, созданный самим PLAN-9B-1 в commit
  `141beae`, он запросов не производит и лишь отфильтровывает четыре
  ретайренных литерала из планов, записанных до слайса; сохраняется
  намеренно с exit condition «снимается, когда pre-slice persisted планы
  перестают читаться». Findings **F1** (вакуумный assertion
  `semantic_queries` в `tests/test_youtube_shorts_production_plan.py`) —
  follow-up в уже записанном backlog `src/production_plan/**`; **F2**
  (`semantic_queries` пуст для legacy scenes без provider-language evidence,
  production reader не найден) — INFO, заявленное fail-closed поведение
  границы PLAN-9B-PRODUCER; **F3** (pre-existing: legacy broad literal может
  вернуться через no-brief `_latin_terms` fallback) — follow-up рядом с
  существующей историей C36/R01; **F4** (pre-existing: Envato consumer cap
  `[:3]` перед provider synthetic completion) — follow-up в существующем
  unscheduled candidate **ENVATO-CS1**. Ни один не blocking, ни один не
  исправлялся этим слайсом, новых PLAN-ID и finding-ID не создавалось.

  **PLAN-9B-2
  (expansion + hardcode migration) закрыт 2026-08-07.** Owner-issued
  implementation slice выполнен 2026-08-07 одним immutable commit
  `66fd2431`; independent review verdict **ACCEPT WITH MINOR** (blocking
  findings **0**), implementation CI run `31164020130` (headSha `66fd2431`)
  зелёный — full offline suite 1772 tests OK, failures=0, errors=0.
  Единственный review finding **F1** — `_mentions_avoided` в
  `src/content/visual_planning/expansion.py` сравнивал `must_avoid` с query
  через raw whitespace-split, из-за чего punctuation вокруг avoided phrase
  (например `"Panama Canal,"` или переживший truncation rung
  `"Panama Canal."`) могла обойти блокировку — закрыт bounded repair commit
  `8c60295`: обе стороны сравнения используют единую provider-token
  normalization через существующий `_PROVIDER_TOKEN_RE`, consecutive-phrase
  matching и case-insensitive поведение сохранены, query не мутируется.
  Independent re-review verdict **ACCEPT** (findings **0**), repair CI run
  `31172361739` (headSha `8c60295`) зелёный. Known non-blocking limitation
  **F2** — `must_avoid` на non-provider языке (например русском) не
  сопоставляется семантически с provider-language query без перевода —
  зафиксирован как limitation PLAN-9B-2; `TranslatorService` не создавался и
  не планируется. `current_checkpoint` тогда перешёл на `PLAN-9B-3`, который
  выполнен и закрыт 2026-08-07 (см. выше). Bounded owner-driven
  **stabilization review**
  результатов PLAN-STAB-1..9 (пункт 8 blocking gate, без собственного
  PLAN-ID) **завершён 2026-08-07**, read-only (ничего не редактировал, не
  commit и не push), final verdict **CLEAR TO PROCEED TO PLAN-9B-2**,
  blocking findings **0**; подтверждены все четыре свойства
  (user-output preservation · offline/paid fail-closed behavior · rights
  safety · однозначный current routing) и зафиксировано, что
  предварительный архитектурный repair перед PLAN-9B-2 **не требуется**.
  Targeted evidence review: `tools.qa.check_agent_docs` exit 0;
  permission/routing/governance tests — 140 OK; rights/network
  cross-contract tests — 78 OK; уже подтверждённый closure CI run
  `31149780652` (headSha `2186b20c5592a264ab6d100c44eaa6dd664aae91`) —
  governance step success, full offline suite 1749 tests OK, failures=0,
  errors=0. Пункт 8 blocking gate **satisfied**, весь post-audit
  stabilization gate **пройден**; нового PLAN-ID для review не создавалось.
  PLAN-STAB-6 (Claude permission
  hardening) **closed 2026-08-07**: implementation `3cedff10`, repair
  `b0a3547` закрыл review findings F1-F5, independent re-review verdict
  **ACCEPT WITH MINOR** (blocking findings: 0), GitHub Actions run
  `31147454618` (headSha `49385dd`) зелёный (`Ran 1749 tests`,
  `OK (skipped=6)`, failures=0, errors=0); пункт 6 blocking gate
  **satisfied**. Это единственный
  current checkpoint; любой другой шаг,
  названный текущим где-либо ещё, устарел. PLAN-STAB-7 (current-routing и
  reference integrity) и PLAN-STAB-8 (Git-aware documentation freshness)
  **closed 2026-08-06**: implementation commit `42fa741` (совместный слайс,
  trailer `Plan-Step: PLAN-STAB-7`), repair commit `8357402` исправил все
  четыре finding F1-F4 исходного independent review, не меняя ни один
  contract. Initial independent review verdict **ACCEPT WITH MINOR**, repair
  re-review verdict **ACCEPT WITH MINOR** (blocking findings: 0); GitHub
  Actions run `31101208366` (headSha `42fa741`) — offline suite зелёный
  (1693 tests, `OK (skipped=6)`, failures=0, errors=0); repair GitHub Actions
  run `31110155685` (headSha `8357402`) — offline suite зелёный (1702 tests,
  `OK (skipped=6)`, failures=0, errors=0); commits pushed. Пункт 7 blocking
  gate **satisfied**. PLAN-STAB-8 закрыт тем же координированным review и
  остаётся **non-blocking** для PLAN-9B-2; PLAN-ID и contracts
  PLAN-STAB-7/PLAN-STAB-8 остаются раздельными (детали — в их собственных
  разделах ниже). PLAN-STAB-9 (shared rights vocabulary owner) остаётся
  closed и non-blocking (commit `ed4604d`, verdict ACCEPT WITH MINOR).
  PLAN-STAB-5 (C50 rights-review preservation) completed 2026-08-06,
  independently reviewed, verdict **ACCEPT** (findings: нет), GitHub Actions
  run `31084873522` — offline suite зелёный (`Ran 1646 tests in 273.522s`,
  `OK (skipped=6)`, failures=0, errors=0); пункт 5 blocking gate
  **satisfied**. Все пункты 1–8 blocking gate **satisfied**; stabilization
  gate закрыт целиком.

  **Утверждённый активный execution route (owner decision 2026-08-06):**
  PLAN-STAB-5 → PLAN-STAB-9 (closed) → PLAN-STAB-7 + PLAN-STAB-8 (closed) →
  **PLAN-STAB-6** (closed 2026-08-07) → отдельный stabilization review
  (**завершён 2026-08-07**, verdict CLEAR TO PROCEED TO PLAN-9B-2, blocking
  findings 0) → **PLAN-9B-2** (closed 2026-08-07: implementation `66fd2431`,
  review ACCEPT WITH MINOR blocking findings 0, repair `8c60295` закрыл finding
  F1, re-review ACCEPT findings 0, CI зелёный на обоих commits) →
  **PLAN-9B-3** (query-path cleanup, closed 2026-08-07: implementation
  `72221e1`, review ACCEPT WITH MINOR blocking findings 0, CI run
  `31195789804` success, все пять retirement candidates закрыты) →
  **PLAN-1C′** (capability owner gate: asset/semantic, closed 2026-08-07,
  C01-SEM закрыт) → **PLAN-9C** (semantic decision wiring, pending / not
  started). Route пройден до PLAN-1C′ включительно; авторитетный
  `current_checkpoint` — `PLAN-9C`. Следующее точное действие — отдельный
  owner-issued implementation slice PLAN-9C в новом чате. Обзор effective merged settings,
  который прежде
  стоял здесь, выполнен: семь опасных local grants (`git add *`,
  `git commit *`, `python -c`, три варианта `python.exe -c`, `python -`)
  владелец удалил вручную до слайса, read-only precheck подтвердил их
  отсутствие, а versioned `.claude/settings.json` (canonical owner A, tracked)
  переписан этим слайсом.
  `.claude/settings.local.json` (canonical owner B, local) остаётся gitignored
  manual owner action и не редактируется от имени агента.
- **PLAN-STAB-4:** completed 2026-08-06 (commit `0947e51`); independent review
  выполнен, verdict **ACCEPT WITH MINOR**; GitHub Actions run `31053545804`,
  job `offline-tests / unittest` — success, `Ran 1623 tests in 329.132s`,
  `OK (skipped=6)`, failures=0, errors=0; HEAD == `origin/governance-reset`,
  worktree clean на момент review. Два findings review — non-blocking residual
  evidence, не исправлены этим слайсом: (1)
  `tests/test_runtime_network_boundary.py:324-329` содержит тавтологический
  assertion (`assertTrue(callable(prepare_final))`) вместо полной проверки
  denial → readiness; (2) `wizard_presentation.py` показывает неполную
  информационную сводку сетевых действий и не использует
  `required_network_actions()` — это то же предсуществующее поведение, которое
  сам PLAN-STAB-4 уже зафиксировал как не входящее в scope. Commit pushed;
  пункт 4 blocking gate satisfied.
  Реализация 2026-08-06: canonical owner `src/runtime_network.py` объявляет
  runtime-сеть fail-closed по умолчанию — `ContextVar` со значением `DENY_ALL`,
  явное поимённое разрешение классов `provider_search`, `asset_download`,
  `preview_download`, `article_fetch`, `voice_preflight`, проверка
  `require_network` до первого socket/HTTP. Разрешение выдаётся один раз в
  `create_content` из поля `network` запроса, а запрос собирается общим
  request builder одинаково для CLI (`--allow-network`, повторяемый, без
  wildcard) и Wizard (явный шаг подтверждения). Наличие API-ключа, включённый
  по умолчанию keyless-провайдер, `--approve-paid-generation`, `--resume` и
  `--force-stage` разрешением **не являются**; `--dry-run` и `--prepare-only`
  остаются offline. Network approval и paid approval разделены: платное
  разрешение не открывает provider search, article ingestion, preview download
  и preflight.
- **PLAN-STAB-3:** completed 2026-08-05 (commit `9222519`); `tests/network_guard.py` получил
  `network_guard_scope()` context manager, восстанавливающий guard к состоянию
  до входа в scope даже при исключении, и 9 raw install/uninstall call sites
  в трёх owning test-модулях переведены на него — устранена утечка, при
  которой снятие guard одним тестом отключало baseline-защиту для остальных
  тестов процесса. `src/audio/tts/env.py::load_elevenlabs_env` больше не даёт
  локальному `.env` заменить test-owned fake `ELEVENLABS_API_KEY`, когда
  `tests/__init__.py` заранее установил test isolation lock и fake credential;
  production override=True semantics вне test isolation не менялись.
  Independent review выполнен, verdict ACCEPT WITH MINOR; commit pushed;
  пункт 3 blocking gate satisfied.
- **PLAN-STAB-2:** completed 2026-08-05 (commit `0eea5be`); обычный resume/явный `stage=` dispatch
  пропускает уже завершённый `final_render` при наличии обязательного
  final-артефакта; существующий `force_stage` по-прежнему пересобирает его;
  completed status без артефакта продолжает считаться незавершённым через уже
  действующий `NewsProjectStore.is_stage_completed`. Independent review
  выполнен, verdict ACCEPT; commit pushed; пункт 2 blocking gate satisfied.
- **PLAN-STAB-1:** completed 2026-08-05 (commit `f0b69db`); финальный мастер пишется во временный
  файл рядом с целью, проверяется каноническим `ffprobe_media_info` и только
  затем занимает свой путь через `os.replace`. Independent review выполнен,
  verdict ACCEPT WITH MINOR; commit pushed; пункт 1 blocking gate satisfied.
  Review PLAN-STAB-1/2/3 — owner-provided external review evidence, не
  отдельный Git commit.
- **CI repair (PLAN-STAB-16, часть 1):** commits `9f9b6f2`, `bcf6c2a`,
  `8ca755f`, `68acdb2` вернули `.github/workflows/offline-tests.yml` в
  зелёное состояние — GitHub Actions run `31039985187`,
  `offline-tests / unittest` — success, 1/1 checks, failures=0, errors=0;
  локальный полный offline suite на `68acdb2` — 1589 тестов, OK. Срочный
  bounded end-to-end repair по прямому owner decision; исходный scope
  расширен владельцем после новых подтверждённых CI failures — authorized,
  не самовольное расширение. Готовые видео, пользовательские проекты,
  downloaded assets и project outputs в Git не добавлялись; тест теперь
  генерирует synthetic temporary MP4 вместо personal-machine fixture.
  PLAN-STAB-16 остаётся **частично** выполнена: secret scan, dependency
  audit, lint baseline и type-check baseline — pending/non-blocking. Ни
  current checkpoint, ни PLAN-STAB-4 этим не менялись.
- **PLAN-9B-PRODUCER:** completed 2026-08-02; существующий visual-planning owner
  формирует evidence-derived provider-language `VisualBrief`, explicit author
  brief применяется последним, unknown intent остаётся fail-closed. Нового
  planner, query owner, schema/layout, public surface, network/model/paid path
  нет. Текущим checkpoint он больше не является.
- **PLAN-9B-2:** **closed 2026-08-07.** Owner-issued implementation slice
  (commit `66fd2431`) delivered the expansion ladder и hardcode-migration
  capability; independent review verdict **ACCEPT WITH MINOR** (blocking
  findings **0**); implementation CI run `31164020130` зелёный. Repair commit
  `8c60295` закрыл единственный review finding F1 (must_avoid punctuation
  bypass); independent re-review verdict **ACCEPT** (findings **0**); repair
  CI run `31172361739` зелёный. F2 (non-provider-language must_avoid требует
  translator для сопоставления с provider-language query) зафиксирован как
  non-blocking known limitation; `TranslatorService` не создавался. Текущим
  checkpoint он больше не является.
- **PLAN-9B-3:** **closed 2026-08-07.** Owner-issued implementation slice
  (commit `72221e1`) ретайрил superseded query-generation paths после
  доказанной замены и миграции всех живых callers; independent review verdict
  **ACCEPT WITH MINOR** (blocking findings **0**); CI run `31195789804`
  (headSha `72221e1861f7c62de01aa09056cfaf6f56ef99a7`) — conclusion success.
  Все пять retirement candidates контракта закрыты: **C34** (obsolete GLOSSARY
  substring matcher — ретайрен ранее commit `141beae` в PLAN-9B-1, replacement
  и seed-словарь сохранены намеренно), **C35**, **C36**, **C37**, **C38** —
  последние четыре ретайрены этим commit, строка **R01** реестра. Reversible
  retirement mechanism выполнен целиком (annotated tag
  `retired/query-paths-2026-08-07` на `1bbfcad`, commit body, строка R01,
  внешний bundle). `_LEGACY_BROAD_QUERIES` — persisted-compatibility guard
  PLAN-9B-1, не retirement candidate, сохранён с exit condition. Findings
  F1-F4 — non-blocking, не исправлялись. Текущим checkpoint он больше не
  является.
- **Выполнено:** PLAN-0 — создан этот план; ветка `governance-reset`.
  STEP 0 — архитектурная ревизия перенесена в этот файл и в
  `CLEANUP_REGISTRY.md`. **PLAN-REV-2.1** — ревизия 2.1 канонизирована
  docs-only слайсом; production-код, tests, схемы и public CLI не менялись.
  **PLAN-1D-routing** — routing исправлен в `AGENTS.md`,
  `docs/current/START_HERE.md` и `docs/current/CURRENT_STATE.md`: все три
  current-документа называют текущим execution plan этот файл и больше не
  называют `9B-C01` текущим checkpoint. Исторический
  `docs/handoff/PROJECT_RESCUE_MASTER_PLAN.md` сохранён и не редактировался.
  Findings C51 (`PRODUCT_EVIDENCE_GATE.md`) и C52 (root `skills/` discovery)
  записаны в `CLEANUP_REGISTRY.md` без перемещения файлов и без создания
  второго набора skills. **PLAN-2** — исправлена изоляция fixtures в
  `tests/test_voice_profile_resolution.py`: изменён только этот test-модуль,
  production-код не менялся. **PLAN-3** — fixtures в
  `tests/test_autonomous_completion_pipeline.py` создают реальные минимальные
  outputs для стадий, объявленных completed; изменён только этот test-модуль,
  production-код не менялся. **PLAN-4** — полный offline suite завершился
  зелёным на проверенном исходном HEAD
  `84bdd8b4f64c7adaf7582bdb39b15b18163253fb`; production-код и tests в этом
  verification-only слайсе не менялись. **PLAN-9B-0** — новый in-process
  offline-модуль `tests/test_input_query_truth_characterization.py` через
  canonical `create_content` path зафиксировал pre-fix input/query behavior,
  production-код не менялся. **PLAN-9B-1** — canonical owner
  `src/assets/query_adapter.py` теперь валидирует язык каждого candidate query
  отдельно, стабильно normalizes/deduplicates explicit/brief/intent evidence,
  читает canonical structured `visual_intents` раньше плоского compatibility
  fallback и использует Unicode token boundaries плюс ограниченную безопасную
  морфологию seed-лексикона. Ложные `ice researchers` и одиночный misleading
  `station` устранены; English alternatives рядом с Russian primary и prepared
  VisualBrief доходят до fake providers с существующим provenance. Unknown raw
  intent остаётся `query_translation_required`; adapter переводчиком не стал.
  Первоначальный raw-topic T1 был несовместим с adapter-only scope и по owner
  decision заменён на T1A (prepared provider-ready evidence) + T1B (unsupported
  raw intent fail-closed). Arbitrary raw-topic provider-language generation
  остаётся открытой product capability, а не скрывается generic fallback.
- **PLAN-9B-5a** — canonical `create` получил owner-approved public flags
  `--source-text` / `--source-text-file`; прежние `--pasted-script` /
  `--script-file` сохранены aliases того же parser destination. Общий
  `request_builder` нормализует их в существующие поля `pasted_script` /
  `script_path` и существующие modes `pasted_script` / `script_file`,
  валидирует единственность authoritative input и compatible `--input-mode`.
  Story Card `--text` / `--comment`, request model, script engine, persisted
  schema, wrapper `apps/news_to_short` и `--assets` не менялись.
- **PLAN-9B-4** — factual `strict` связывает существующий
  `allow_legacy_fallback` со strict completion policy и возвращает
  `insufficient_source_material` с вариантами article URL / source text /
  draft / template. Существующие `script_provider`, `fallback_reason`,
  `script_metadata` и `ScriptValidationResult` используются validation и
  quality defense; `content_origin`, новые persisted fields и schema не
  создавались. Явный `legacy_template` сохранён для template/demo/test/draft и
  старых проектов; CLI diagnostics и оба application dry-run/prepare пути
  возвращают классифицированный отказ без traceback.
- **PLAN-6D-1** — permission baseline разделён на точные permanent deny и
  поддерживаемые `ask` rules. `.env` защищён для Read/Write/Edit; broad
  `.env.*`, `*credential*` и `*secret*` patterns, блокировавшие versioned
  examples/source, удалены. Bare/flagged `git clean`, `reset --hard` и force
  push покрыты deny; обычные push/remote-add/stash/amend, прямые WebFetch/
  WebSearch и перечисленные recursive cleanup primitives требуют approval.
  Scope-controlled и mixed directories broad path rules не получили.
- **PLAN-6D-2** — добавлен локальный read-only checker
  `tools/qa/check_task_scope.py`. Конкретная задача передаёт повторяемые
  `--allow` exact paths и/или явные `--allow-dir` directory scopes; checker
  сравнивает их с `git --no-optional-locks status --porcelain=v1 -z
  --untracked-files=all --renames`, учитывает обе колонки staged/unstaged,
  untracked, add/delete и обе стороны rename. Словарь результата — ровно
  `OK`, `STOP_REQUIRED`, `INVALID_INPUT`; exit codes — 0, 1, 2 соответственно.
  Модуль не читает содержимое изменённых файлов, не меняет index/worktree и не
  хранит глобальный PLAN allowlist.
- **PLAN-6D-3** — тонкий `CLAUDE.md` теперь явно сообщает, что repository
  skills находятся в корневом `skills/`, не считаются автоматически
  загруженными только из-за наличия в репозитории и перед специализированной
  задачей требуют ручного открытия релевантного
  `skills/<skill-name>/SKILL.md`. Skill применяется вместе с `AGENTS.md`,
  актуальной документацией, фактическими кодом и тестами; состояние
  репозитория имеет приоритет над предположениями skill. Содержимое skills не
  копировалось, `.claude/skills/` не создавался, утверждения о Codex discovery
  не добавлялись. PLAN-6D завершён полностью.
- **Зелёные проверки:** `tools.qa.check_agent_docs`;
  `tests.test_voice_profile_resolution` — targeted-модуль, exit code 0 в двух
  последовательных прогонах (2026-08-01);
  `tests.test_autonomous_completion_pipeline` — targeted-модуль, exit code 0
  в двух последовательных прогонах (2026-08-01); полный offline suite — 1441
  тест, 231.839 секунды, exit code 0 без failures, errors и skips на проверенном
  исходном HEAD `84bdd8b4f64c7adaf7582bdb39b15b18163253fb` (2026-08-01). Число тестов и
  длительность — измерение, не норматив;
  `tests.test_input_query_truth_characterization` — 2 теста, два
  последовательных прогона с exit code 0 (74.191 и 73.016 секунды), active
  network guard не зафиксировал попыток сети; targeted radius из четырёх
  существующих модулей — 118 тестов, 26.004 секунды, exit code 0 (2026-08-01);
  PLAN-9B-1: `tests.test_input_query_truth_characterization` — 3 теста, два
  окончательных последовательных прогона с exit code 0 (74.852 и 75.004
  секунды); прямой query radius — 75 тестов за 1.574 секунды; caller radius
  через script pipeline, asset manager, canonical content service и provider
  integration — 82 теста за 33.120 секунды, exit code 0. Числа и длительности
  являются измерениями, не нормативами. Network guard оставался чистым; сеть,
  model API, provider HTTP/download, Vision, TTS, paid calls и render не
  выполнялись;
  PLAN-9B-5a: новый regression-модуль — 15 тестов в составе окончательного
  targeted radius; parser/request/service/use-case/Wizard radius — 193 теста
  за 43.183 секунды, exit code 0; `create --help`, inline source-text dry-run и
  file source-text dry-run — три smoke-команды, каждая exit code 0; полный
  offline suite — 1465 тестов за 309.632 секунды, exit code 0, failures/errors
  нет (2026-08-02). Числа и длительности — измерения, не нормативы. Сеть,
  provider/model API, download, Vision, TTS, paid calls и реальный render не
  выполнялись.
  PLAN-9B-4: targeted owner/caller radius — 168 тестов за 135.307 секунды,
  exit code 0; полный offline suite — 1523 теста за 356.527 секунды, exit code
  0, `OK` (2026-08-02). T6/T7/T8, canonical Content Creator, diagnostics,
  persisted quality defense, explicit legacy compatibility, source-text и
  resume/force-stage fixtures покрыты. Числа и длительности — измерения, не
  нормативы. Сеть, provider/model API, download, Vision, TTS и paid calls не
  выполнялись; render-проверки full suite использовали только синтетические
  fixtures во временных каталогах.
  PLAN-6D-1: JSON и локальный Claude Code 2.1.219 parser — exit code 0;
  полный tracked-path collision probe — 0 совпадений; `.env` покрыт
  Read/Write/Edit, `.env.example` и `src/localization/secrets.py` доступны;
  `tools.qa.check_agent_docs` и `tests.test_stage2_agent_onboarding` — exit
  code 0; `git diff --check` — без замечаний (2026-08-02). Сеть, providers,
  download, Vision, TTS, paid API и render не выполнялись.
  PLAN-6D-2: `tests.test_check_task_scope` — 26 тестов, exit code 0;
  `check_task_scope --help`, docs QA, onboarding tests и `compileall tools\qa`
  — exit code 0. Smoke текущего разрешённого diff вернул `OK/0`; smoke во
  временном Git repository с unexpected untracked path вернул
  `STOP_REQUIRED/1`. `git diff --check` — без замечаний. Production code,
  hooks, agents, skills и runtime/user data не менялись; сеть и платные
  действия не выполнялись (2026-08-02). Число тестов и длительность —
  измерения, не нормативы.
  PLAN-6D-3: `check_task_scope` с четырьмя разрешёнными exact paths вернул
  `OK/0`; docs QA, `tests.test_stage2_agent_onboarding` и `git diff --check`
  завершились с exit code 0. Фактическая структура содержит шесть root skills
  и не содержит `.claude/skills/`; `CLAUDE.md` остался тонким adapter,
  содержимое skills не копировалось и не менялось. Сеть, providers, download,
  Vision, TTS, paid API и render не выполнялись (2026-08-02).
- **Почему checkpoint сместился с PLAN-1A на PLAN-1D, затем на PLAN-2,
  PLAN-3, PLAN-4, PLAN-9B-0, PLAN-9B-1, PLAN-9B-5a, PLAN-9B-4, PLAN-9B-2,
  PLAN-6D-2, PLAN-6D-3, PLAN-6E, PLAN-L0, PLAN-9B-PRODUCER и PLAN-STAB-1.**
  Смещение на 1D было
  **не** признаком
  выполненной работы: ревизия 2 разделила монолитный PLAN-1 на три capability
  gates (1A, 1B, 1C′) и выделила routing-фикс 1D как первый самостоятельный
  шаг. Ни один под-slice PLAN-1A/1B/1C′ не выполнен. Переход на PLAN-2 —
  следствие фактически выполненного docs-only слайса PLAN-1D; переход на
  PLAN-3 — следствие фактически выполненного test-only слайса PLAN-2; переход
  на PLAN-4 — следствие фактически выполненного test-only слайса PLAN-3;
  переход на PLAN-9B-0 — следствие зелёного полного offline baseline PLAN-4.
  `baseline_head` обновлён на фактически проверенный исходный HEAD
  `84bdd8b4f64c7adaf7582bdb39b15b18163253fb`; будущий plan-only commit этим
  baseline не является. Переход на PLAN-9B-1 — следствие зелёной
  characterization PLAN-9B-0; full suite в test-only слайсе не запускался,
  поэтому `baseline_head` не менялся. Переход на PLAN-9B-5a — следствие
  выполненного локального PLAN-9B-1; full suite не запускался, потому что public
  signatures, schema/layout и shared architecture boundary не менялись.
  `baseline_head` остаётся прежним.
- Переход на PLAN-L0 — следствие завершённых PLAN-9B-5a, PLAN-9B-4, PLAN-6D,
  PLAN-6E и принятого owner decision OD-P-1. Утверждённый порядок:
  `PLAN-L0 → PLAN-9B-PRODUCER → PLAN-9B-2`.
  `baseline_head` не переписывается на незакоммиченный hash; Git log остаётся
  авторитетом commit evidence.
- Переход на PLAN-9B-PRODUCER — следствие фактически выполненного docs-only
  слайса PLAN-L0: Knowledge Salvage Gate закрыт до destructive retirement, как
  требуют OD-1, OD-7 и OD-10. Full suite не запускался, потому что слайс
  docs-only и не менял production contract, поэтому `baseline_head` не менялся.
- Переход на PLAN-STAB-1 — следствие owner decision 2026-08-05 по read-only
  AI-practices audit от clean HEAD `e4cad2a`: подтверждённые safety findings
  получают исполняемых owners раньше следующего product slice. Это **не**
  оценка качества PLAN-9B-PRODUCER, который завершён и принят, и **не** отмена
  PLAN-9B-2. Смена checkpoint не является разрешением начать PLAN-STAB-1: он
  остаётся pending / not started до отдельного owner-issued implementation
  prompt. `baseline_head` этим docs-only слайсом не менялся.
- **`baseline_head` обновлён на 68acdb2 после PLAN-STAB-1/2/3 и CI repair.**
  PLAN-STAB-1 (`f0b69db`), PLAN-STAB-2 (`0eea5be`) и PLAN-STAB-3 (`9222519`)
  каждый запускал полный offline suite на своём HEAD (1571, затем 1577, затем
  1589 тестов, exit code 0) и получил independent review — verdict ACCEPT WITH
  MINOR, ACCEPT, ACCEPT WITH MINOR соответственно; все три commit pushed.
  CI repair (`9f9b6f2`, `bcf6c2a`, `8ca755f`, `68acdb2`, trailer
  `Plan-Step: PLAN-STAB-16`) — срочный bounded end-to-end repair по прямому
  owner decision после новых подтверждённых CI failures в GitHub Actions;
  scope расширен владельцем, это не самовольное расширение. Result: GitHub
  Actions run `31039985187`, `offline-tests / unittest` — success, 1/1 checks,
  failures=0, errors=0; локальный полный offline suite на `68acdb2` — 1589
  тестов, OK. Готовые видео, пользовательские проекты, downloaded assets и
  project outputs в Git не добавлялись; тест, ранее ссылавшийся на
  personal-machine fixture, теперь генерирует synthetic temporary MP4.
  `baseline_head` обновлён на фактически проверенный `68acdb2` — последний
  commit с зелёным полным offline suite и зелёным GitHub Actions run.
  PLAN-STAB-16 этим **частично** выполнена: первая часть (reproducible green
  offline CI baseline) завершена; secret scan, dependency audit, lint baseline,
  type-check baseline и остальные подпункты остаются pending/non-blocking для
  PLAN-9B-2. Ни один из четырёх commits не меняет current checkpoint: он
  остаётся PLAN-STAB-4 pending / not started, и PLAN-STAB-4 этим не начат.
- Переход на PLAN-6D-2 — owner-approved prerequisite rerouting и следствие
  завершённого PLAN-6D-1. Он не начинает PLAN-9B-2 и не меняет его acceptance
  criteria.
- Переход на PLAN-6D-3 — следствие зелёного локального read-only scope
  checker PLAN-6D-2. Он не начинает PLAN-9B-2/PLAN-6E и не означает завершение
  PLAN-6D.
- PLAN-6E выполнен после завершённого PLAN-6D-3 и полного закрытия PLAN-6D.
  Его закрытие не начинает PLAN-L0, PLAN-9B-PRODUCER или PLAN-9B-2.
- **Текущие зависимости и блокеры (модель ревизии 2.1 — risk-based, не
  линейная цепочка):**
  - **PLAN-9B-1** — completed 2026-08-01; prerequisite-цепочка
    `PLAN-1D-routing → PLAN-2 → PLAN-3 → PLAN-4 → PLAN-9B-0` завершена
    2026-08-01;
  - **PLAN-9B-5a** — completed 2026-08-02; зависит от завершённого PLAN-9B-1;
  - **PLAN-9B-4** — completed 2026-08-02; зависит от завершённого PLAN-9B-5a;
  - **PLAN-L0** — completed 2026-08-02; salvage записан в
    `CLEANUP_REGISTRY.md`, retirement не выполнялся;
  - **PLAN-9B-PRODUCER** — completed 2026-08-02; зависел от завершённых
    PLAN-9B-1 и PLAN-L0, обе зависимости были закрыты до начала;
  - **PLAN-STAB-1** — completed 2026-08-05 (commit `f0b69db`); independent
    review выполнен, verdict ACCEPT WITH MINOR; commit pushed;
  - **PLAN-STAB-2** — completed 2026-08-05 (commit `0eea5be`); зависел от
    завершённого PLAN-STAB-1; independent review выполнен, verdict ACCEPT;
    commit pushed;
  - **PLAN-STAB-3** — completed 2026-08-05 (commit `9222519`); independent
    review выполнен, verdict ACCEPT WITH MINOR; commit pushed. Review
    PLAN-STAB-1/2/3 — owner-provided external review evidence, не отдельный
    Git commit;
  - **PLAN-STAB-4** — completed 2026-08-06 (commit `0947e51`); independent
    review выполнен, verdict ACCEPT WITH MINOR (GitHub Actions run
    `31053545804`, offline suite 1623 tests OK); commit pushed; пункт 4
    blocking gate satisfied; два findings review зафиксированы как
    non-blocking residual evidence и не исправлены;
  - **PLAN-STAB-5** — completed 2026-08-06 (единственный commit слайса,
    trailer `Plan-Step: PLAN-STAB-5`); independent review выполнен, verdict
    **ACCEPT** (findings: нет), GitHub Actions run `31084873522` (1646 tests
    OK); commit pushed; пункт 5 blocking gate satisfied;
  - **PLAN-STAB-9** — completed 2026-08-06 (единственный commit слайса,
    trailer `Plan-Step: PLAN-STAB-9`, `ed4604d`); independent review выполнен,
    verdict ACCEPT WITH MINOR (non-blocking wording finding, исправлен); GitHub
    Actions reviewed headSha `ed4604d` зелёный; non-blocking follow-up для
    PLAN-9B-2; не текущий checkpoint;
  - **PLAN-STAB-7** — completed 2026-08-06 (implementation commit `42fa741`,
    repair commit `8357402`); independent review verdict ACCEPT WITH MINOR,
    repair re-review verdict ACCEPT WITH MINOR (blocking findings: 0); CI run
    `31101208366` (headSha `42fa741`, 1693 tests OK) и repair CI run
    `31110155685` (headSha `8357402`, 1702 tests OK) оба зелёные; commits
    pushed; пункт 7 blocking gate satisfied; не текущий checkpoint;
  - **PLAN-STAB-8** — closed 2026-08-06 тем же координированным review, что и
    PLAN-STAB-7 (implementation commit `42fa741`, repair commit `8357402`);
    non-blocking follow-up для PLAN-9B-2; PLAN-ID и contract остаются
    отдельными от PLAN-STAB-7;
  - **PLAN-STAB-6** — closed 2026-08-07 (`3cedff10` + repair `b0a3547`,
    re-review ACCEPT WITH MINOR, blocking findings 0). Прежняя формулировка
    «текущий checkpoint» устарела и исправлена сверкой 2026-08-11:
    авторитетом остаётся `current_checkpoint` во frontmatter;
  - **PLAN-STAB-10…PLAN-STAB-15, PLAN-STAB-17** — pending/not started; состав,
    порядок и blocking-статус каждого — раздел «POST-AUDIT STABILIZATION
    PROGRAM»;
  - **PLAN-STAB-16** — pending/not started как полный слайс, но **частично
    выполнена**: CI repair (`9f9b6f2`, `bcf6c2a`, `8ca755f`, `68acdb2`) закрыл
    первую часть success criteria (green offline suite в GitHub Actions —
    run `31039985187`, 1/1 checks, failures=0, errors=0); secret scan,
    dependency audit, lint baseline и type-check baseline остаются
    pending/non-blocking;
  - **PLAN-9B-2** — closed 2026-08-07 (`66fd2431` + repair `8c60295`);
    прежняя запись «pending/not started» устарела и исправлена сверкой
    2026-08-11;
  - **PLAN-6D-1** — completed 2026-08-02;
  - **PLAN-6D-2** — completed 2026-08-02;
  - **PLAN-6D-3** — completed 2026-08-02;
  - **PLAN-6D** — completed 2026-08-02; evidence commits: `397d338`
    (PLAN-6D-1), `10dd555` (PLAN-6D-2) и commit с trailer
    `Plan-Step: PLAN-6D-3`;
  - **PLAN-6E** — completed 2026-08-02; canonical review policy, два тонких
    adapter и controlled read-only acceptance закрывают reviewer gate для
    destructive/high-risk boundaries;
  - **PLAN-9A** — блокируется `PLAN-9B-2` + `PLAN-1C′`, дополнительно требует
    `PLAN-6E`;
  - **PLAN-9C** — блокируется `PLAN-1C′` + `PLAN-6E`;
  - **PLAN-5, PLAN-6A, PLAN-6B, PLAN-6C, PLAN-7, PLAN-8, PLAN-1A, PLAN-1B,
    PLAN-1C′, PLAN-12\*, PLAN-13\*, PLAN-14\* и PLAN-L1…PLAN-L4** — параллельны и
    **не блокируют первый product fix**;
  - PLAN-11 M2 — до подтверждения бюджета.
- **Следующее точное действие:** запись этого буллета устарела и снята сверкой
  2026-08-11. Единственный авторитет следующего действия — поле
  `next_exact_action` во frontmatter и блок «Mini plan reconciliation
  2026-08-11» выше. Историческая часть, остающаяся верной: PLAN-STAB-7 и
  PLAN-STAB-8 closed 2026-08-06 (`42fa741`, repair `8357402`, verdicts ACCEPT
  WITH MINOR, blocking findings 0, пункт 7 gate satisfied), PLAN-STAB-6 closed
  2026-08-07, PLAN-STAB-9 остаётся closed и non-blocking.
- **После PLAN-9B-PRODUCER:** не начинать PLAN-9B-2 до закрытого stabilization
  gate и отдельного implementation prompt; не начинать ни один PLAN-STAB-слайс
  без собственного implementation prompt. PLAN-L1…PLAN-L4 закрытием PLAN-L0 не
  разрешены: каждый остаётся отдельной retirement-веткой со своими gates.
- **Что нельзя повторять:**
  - закрывать шаг без зелёной обязательной проверки;
  - записывать число тестов, длительность прогона или accuracy как норму;
  - менять production-код без закрытого capability gate изменяемой области;
  - создавать третий плановый документ;
  - архивировать `PROJECT_RESCUE_MASTER_PLAN.md` или
    `ARCHITECTURE_BOUNDARY_MAP.md` до PLAN-12;
  - снимать с Git `docs/implementation` целым семейством;
  - заявлять о защите, которая существует только в документах;
  - выполнять destructive retirement knowledge-bearing family до Knowledge
    Salvage Gate (PLAN-L0);
  - требовать KSG для disposable runtime/media: их цепочка — PLAN-14D → 14E;
  - считать «нет caller» доказательством отсутствия ценности;
  - **создавать PLAN-P0 / «Content & Query Reachability Gate»**: evidence уже
    получено двумя deep-dive, повторный диагностический этап запрещён (OD-11);
  - **возвращать опровергнутые механизмы** — см. «Ревизия 2.1: опровергнутые
    формулировки».

### Маршрут после 2026-08-17

Порядок внедрения находок 15–17.08 —
[docs/audits/ROLLOUT_PLAN_2026-08-17.md](../audits/ROLLOUT_PLAN_2026-08-17.md),
статус `proposal`: он задаёт порядок, но не выдаёт разрешение и **PLAN-ID не
создаёт** — вход в каждый пакет объявляет владелец. Checkpoint не двигается:
остаётся **PLAN-9D**.

```
0 ─ A ─ B ─┬─ C ─ D ─ E ─ F …
           ├─ ADR (+P)   параллельно, не на критическом пути
           ├─ T
           └─ G          governance-полоса, когда удобно
```

| Пакет | Что | Состояние |
|---|---|---|
| **0** Сохранность | отчёты 15–17.08 в git и в индексе | закрыт `d05d5ec` |
| **A** Точка истины `C89` | независимое ревью `ec369f8`, `ede8c4b` | закрыт `3619fe1`, verdict scope PASS · objective PASS |
| **B** План перестаёт себе противоречить | это поле, замок, база замера, строка `C92` | закрыт коммитом, содержащим эту запись |
| **C** Прибор | корпус v2 видит язык | **PLAN-9D-H**, измерено 2026-08-18: разметка владельца легла, blind agreement **2 / 10** scorable, v1 прежние 4/14 |
| **D** Доказуемость | `is_undecidable` пофайлово | **PLAN-9C-4** закрыт 2026-08-17 этим слайсом: v1 `changed_winners 0`, v2 — 2 сцены из 11 поимённо; agreement не измерялся (разметки v2 нет), `4/14` остаётся последним числом. Класс HIGH — независимый `review-change` после |
| **E** Безопасность | `synthesize` под `require_network`, `C87` | закрыт `d7fb378` (`C94`, `C87`), [ревью](../audits/REVIEW_PACKAGE_E_2026-08-17.md) scope PASS · objective PASS, findings 0 |
| **F**, **ADR**, **T**, **G** | смысл · движение · витрина; долговечные решения **и перенос ответов владельца 2026-08-16 в `PRODUCT_PLAN.md`** (пакет **P**, строка `C93`); тесты; governance | **P** закрыт `52f4cee`, **T** — `407afe1`+`48266a5`, **ADR** — 2 из 5–6 (`666c296`), остаток состава за владельцем (`C92`); **F** и **G** — по маршруту |

**C строго перед D** — правило сработало и уточнилось на исполнении: D измерялся
на **собранном** корпусе v2, а не на размеченном. Смена победителя видна без
ground truth, поэтому оба числа приёмки получены до слепой разметки; сама
разметка нужна для `blind agreement`, и без неё нельзя сказать, что новые
победители лучше. На v1 приёмка действительно прошла бы на любой правке —
`changed_winners 0` там означает только аддитивность. **ADR не ждёт**: три решения владельца существуют только в
отчёте. MAJOR из [ревью C79/C89](../audits/REVIEW_C79_C89_2026-08-17.md)
принадлежит пакету D.

### Routing journal — перенесено из `next_exact_action` 2026-08-17

Хронология закрытий, дословно перенесённая пакетом B из `next_exact_action`, где
она накопилась девятью «IS DONE / closed by» и довела поле-указатель до 10 227
символов. Ни одно слово не изменено и ничего не удалено: это история, а не
маршрут — маршрут выше.

Review #1 (M1-A...M1-C, identity/evidence lineage) is closed: verdict cluster
ACCEPT, MAJOR-RR-01 CLOSED, 0 remaining BLOCKER/MAJOR; CI run 31526039612
(headSha 2577307) conclusion success. Owner decision 2026-08-12 closed
PLAN-9D-D (blind ground truth landed under the canonical name) and
PLAN-9D-E (metadata-only baseline measured: 4/14 agreement, 2 owner-rejected
picks, 3 wrong abstentions, 1/14 auto_safe). PLAN-9D-F/PLAN-9D-G stay
optional quality track behind a separate paid-Vision approval, so PLAN-9D
no longer blocks the route. The current checkpoint remains PLAN-9D.
M1-D / VA-NEW-08 (resume fingerprints) is implemented and closed inside
PLAN-9A: the owner decision on the persisted field set was issued in the
M1-D prompt and the resulting composition is recorded in the M1-D CLOSURE
block. THE NEXT EXACT ACTION is M1-E / VA-NEW-09 (strict render TOCTOU)
inside PLAN-9E, after which Review #2 covers M1-D and M1-E together; no
part of Review #2 has been performed. The owner-authorized targeted
retrieval diagnostic (read-only, no commit) changes no route and closes no
step; the two bounded corrections VA-NEW-22 and VA-NEW-23 it led to are
closed inside PLAN-10B and PLAN-9A and move neither the checkpoint nor this
action. Owner decision 2026-08-13 (AUD-DELTA-CLOSE) inserts one step ahead of
M1-E without changing it: FIRST OWNER SHORT — the offline draft diagnostic
already described below — runs first, because in three months no video has
been looked at through the canonical path and the diagnostic is read-only to
the route. So the order is FIRST OWNER SHORT, then M1-E / VA-NEW-09, then
Review #2 over M1-D and M1-E. The current checkpoint stays PLAN-9D and no
PLAN-ID is created by either the diagnostic or this record.
FIRST OWNER SHORT ran on 2026-08-13 and is recorded in
docs/audits/FIRST_OWNER_SHORT_2026-08-13.md: neither the LOCAL nor the STOCK
path reached an MP4, both stopped at assembly_has_no_slots, and no paid call
was made. Owner decision 2026-08-14 orders the route that follows from it and
puts the product ahead of further cleanup: CURATED LOCAL LIBRARY, then the
LOCAL diagnostic repeat and the STOCK repeat through semantic_brief. The LOCAL
repeat has already reached the first finished draft MP4 milestone; M1-E /
VA-NEW-09 and Review #2 over M1-D and M1-E remain after the STOCK repeat.
CURATED LOCAL LIBRARY is executed and recorded in
docs/audits/CURATED_LIBRARY_2026-08-14.md - 72 curated records with frame
content, provenance, rights and checksums, versioned in
assets/library/metadata/curated_library.json and applied to the runtime index
by tools/library/curated_index.py. BLOCKER-L2 is closed: the records carry
rights, and owner decision 2026-08-14 gave provider local_library in
config/license_policy.json the same two contexts the pexels and pixabay
providers already have - internal_content_production allowed at
requires_schema_version 1, public_multi_user_product blocked until the future
commercial audit - so all 72 evaluate as allowed. The nine clips whose source
page was recorded nowhere were confirmed against the providers under a separate
owner-approved read-only network check and added with verified canonical URLs
and credits. Making the library live
immediately exposed the ranker debt already recorded in FIRST OWNER SHORT: the
query "orca" returned a solar-farm clip, because _score_asset admitted a
candidate on type, aspect and duration with zero keyword hits. Two bounded
corrections closed that and the blocker under it - fbf223a stopped scoring
"nothing could be checked" as a perfect match, and a8549ff gave both local
matchers one Unicode-aware tokenizer, so a Russian query participates in
selection at all. Neither commit closes a PLAN-ID: C40 and PLAN-10D keep their
open scope (one canonical matcher/provider, and the C47 diversity reserve).
THE LOCAL DIAGNOSTIC REPEAT IS DONE - three runs, the last recorded in
docs/audits/FIRST_OWNER_SHORT_LOCAL_SOLAR_AFTER_CYRILLIC_FIX_2026-08-14.md
from HEAD a8549ff: 5 of 5 scenes got a usable visual slot where the same
script had got 0 of 5, all five shortlists differ, one ElevenLabs call, and
the first draft_1080x1920.mp4 of this program exists (23.93s, 1080x1920,
audio present). That is a draft, not a product: quality_check is
needs_review, all five slots are marked draft-only requiring replacement,
publish_ready is false, and owner frame review scored 2 GOOD, 1 ACCEPTABLE,
2 BAD. No publish-ready evidence is claimed by this record. The three defects
behind the BAD frames now have registry rows instead of a wrong owner - C79
(extraction stems Russian, evidence matching does not; both bad scenes share
the extracted subject "панель"), C80 (the canonical paid Vision backend
bypasses runtime_network default-deny; legacy bypasses remain C65) and C81 (a
hook score exists for text and has no visual equivalent). Owner decision
2026-08-14 makes C79 a pre-v1 bounded correction after the STOCK diagnostic
and before M4/PLAN-11; C81 is post-v1 product discovery without an
implementation owner; C80 belongs to PLAN-9E. The duplicate frame in scene 3
is C47 under PLAN-10D, which stays post-v1: it blocks publish-ready approval
for that artifact without manual replacement/approval, not platform v1. THE
STOCK REPEAT THROUGH semantic_brief IS DONE and recorded in
docs/audits/STOCK_SEMANTIC_REPEAT_2026-08-14.md. All 5 scenes received accepted
provider-language briefs and real provider retrieval ran, but only 3/5 scenes
received licensed image slots; two scenes stayed unresolved, no video slot won,
and no MP4 or quality evidence was produced. The run stopped at the paid voice
gate. It also exposed two live-wiring defects: repository .env was not visible
before visual_plan, and semantic usage was not persisted. Both are closed by a
bounded correction inside the existing PLAN-9B-PRODUCER-M-LIVE owners:
only OPENAI_API_KEY is copied from repository .env after paid+network gates;
a still-missing key is visible as semantic_brief_unavailable, and secret-free
cumulative counters are stored under planning_metadata.semantic_brief_usage in the localized plan while master keeps the planning-stage snapshot. Default
fail-closed policy is unchanged. M1-E / VA-NEW-09 is closed by the bounded
PLAN-9E correction recorded below. Review #2 rejected its first implementation
on two M1-E blockers and its second on one remaining fresh-checksum blocker;
all three are repaired. Review #2 is now CLOSED: focused independent re-review
over M1-D and M1-E returned ACCEPT WITH MINOR NOTES, 0 BLOCKER/MAJOR, and the
owner accepted that verdict as sufficient to close both slices. Its three MINOR
notes are recorded in REVIEW #2 CLOSURE below and are explicitly NOT repaired by
a separate slice. The FIRST OWNER SHORT resume-run that had to precede M2-A IS
DONE: it ran offline on the accepted HEAD to a real draft_1080x1920.mp4, byte
identical to the render taken before Review #2, with 5 of 5 scenes usable in
draft, 0 of 5 publish-ready and quality needs_review — diagnostic evidence, not
publish-ready acceptance. It is recorded in the PRE-M2 CLOSURE block below
together with the two accounting facts that belong beside it (exact-head CI is
red on an external Chocolatey/FFmpeg outage before any test ran, and the full
local suite has exactly one known pre-existing doc-length failure).
M2-A IS CLOSED by the bounded PLAN-10B correction recorded in the M2-A CLOSURE
block below: a media kind that fails no longer erases the kind that answered,
and one download URL no longer costs max_retries squared HTTP requests because
the request stage and the body stage now share one attempt budget. Nothing else
in PLAN-10B starts, its status stays blocked, and
ASSET_SEARCH_FINGERPRINT_VERSION deliberately stays 1 - the reasoning is in
that block. M2-B IS CLOSED by the bounded PLAN-10C correction recorded in the
M2-B CLOSURE block below: one scene now has a hard ceiling on provider search
requests within one search invocation, the unit is one provider.search call
rather than a query attempt, and the draft ladder draws from the same counter
instead of a second private allowance. In draft_complete the adaptation pass
may run a second bounded search over a changed scene, so that scene's ceiling
across the whole asset_search stage is 2 x budget - bounded and deterministic
(MAX_ADAPTATION_PASSES = 1). Nothing else in PLAN-10C starts, its status stays
blocked, and ASSET_SEARCH_FINGERPRINT_VERSION deliberately stays 1 because a
configured ceiling lives in asset_selection, which the fingerprint payload
already carries verbatim.
REVIEW #3 over M2-A and M2-B IS CLOSED: owner-provided verdict ACCEPT WITH
MINOR NOTES, 0 BLOCKER and 0 MAJOR, no repair slice. Its MINOR notes are
absorbed by the WP0-B governance slice recorded in REVIEW #3 CLOSURE below,
which also shortened the three routing mirrors and added a line-length guard
beside the existing line-count one; WP0-B is not closed by it.
LIVE-5 IS DONE and recorded in docs/audits/LIVE_5_2026-08-15.md: the run
completed end to end to a draft MP4, 5 of 5 scenes got a slot against the 3 of
5 baseline, rights are verified 7 of 7, there are no duplicates and no
generated fallbacks, and the paid spend was 15 semantic-brief calls at $0.15
plus one ElevenLabs pass. Verdict PARTIAL, not PASS: only 2 of 5 selections are
right by meaning, video slots are still 0, publish_ready is false and the MP4
carries no subtitles. Selection quality, not coverage, is now the binding
constraint. The run reproduced C79, C75/C76, C77, C78 and C82 with evidence and
repaired none of them, and it added two registry rows - C83 (use_local_library
is a dead key, so the local library was never actually disabled and still
scored candidates) and C84 (the semantic-brief ceiling is per adapter, not per
project, so 12 became 15). THE NEXT EXACT ACTION is the owner's choice between
C79 as the pre-v1 bounded correction already scheduled after the STOCK
diagnostic and before M4/PLAN-11, and a second LIVE run on the LIVE-4 animal
script for a second data point; the owner has stated that more runs are needed
and one diagnostic does not establish a trend.
BLOCKER-L1 remains separate and untouched.
The current checkpoint stays PLAN-9D; no new PLAN-ID is created.

## Шаблон задания для нового чата

Историю предыдущих чатов пересказывать не нужно. Достаточно отправить:

```text
Работай в G:\Projects\AI-YouTube.
Сначала выполни git status --short --branch, git log -5 --oneline и
git diff --stat. Прочитай AGENTS.md и полностью
docs/current/PROJECT_EXECUTION_PLAN.md. Исторический
docs/handoff/PROJECT_RESCUE_MASTER_PLAN.md читай как context согласно AGENTS.md,
но не обновляй как current plan.

Продолжи только current_checkpoint активного execution plan и выполни один
bounded sub-slice. Перед изменением проверь фактические callers, tests,
contracts и существующих owners; не создавай дублирующую реализацию.
Запусти только required/targeted проверки этого slice; full offline suite —
только когда его требует план или меняется shared boundary.

Не выполняй сеть, provider download/search, Vision, TTS, платные вызовы,
реальный render, удаление/перенос runtime или user data без моего отдельного
разрешения. После зелёных проверок обнови checkpoint/evidence в активном плане,
покажи diff summary и закоммить slice отдельным commit с
Plan-Step: <ID>. В конце сообщи результат, проверки, commit и следующий
точный checkpoint.
```

Если задача только на review, в последнем абзаце следует заменить
«выполни/закоммить slice» на «ничего не меняй и дай вывод».

## Source-of-truth precedence

1. Git и фактический код.
2. Реальные tests и artifacts.
3. **Этот файл — порядок выполнения текущей программы.**
4. `CURRENT_STATE.md` — фактическое состояние продукта.
5. `PRODUCT_PLAN.md` — продуктовое направление, committed capabilities и склад
   идей. **Создан слайсом PRODUCT-PLAN-1**; PLAN-8 его расширяет и проверяет, а
   не создаёт заново. Execution state (checkpoint, next action, порядок,
   prerequisites, статусы) он не хранит — источником остаётся этот файл.
6. `CLEANUP_REGISTRY.md` — переходные пути, owners и exit conditions.
7. `docs/adr/` — зафиксированные долговечные решения.
8. Historical plans и audits — только как context.

**Отношение к `docs/handoff/PROJECT_RESCUE_MASTER_PLAN.md`.** Master plan
остаётся **историческим исходным документом** и источником данных для PLAN-1.
Его разделы «Что делать первым» и «Текущий handoff» отражают состояние на
2026-07-29 и **не являются** текущим порядком работ: порядок задаёт этот файл.
Master plan не обновляется как current plan и не архивируется до PLAN-12C.
Противоречие между двумя документами разрешается в пользу этого файла
только по вопросу порядка выполнения; по фактам архитектуры приоритет у кода.

Если код или tests противоречат этому плану, агент обязан остановиться,
проверить evidence и обновить план после решения владельца.

**Маршрутизация агентов — исправлена PLAN-1D (2026-08-01).** После ревизии 2
`AGENTS.md` и `START_HERE.md` направляли задачу в master plan, а
`CURRENT_STATE.md` называл текущим checkpoint `9B-C01`, которого больше нет.
PLAN-1D добавил в шаг 4 `AGENTS.md` и в `START_HERE.md` ссылку на этот файл как
на активный execution plan и снял stale checkpoint из всех трёх current-документов.
Master plan во всех трёх упоминается только как исторический контекст.

## Locked owner decisions

Подтверждено владельцем на 2026-07-30:

1. Ближайший продуктовый приоритет — визуальная релевантность и завершённость
   Shorts.
2. Проект должен представлять несколько понятных инструментов поверх общего
   переиспользуемого ядра.
3. `content_creator` — основной инструмент создания новых видео; longform и
   documentary развиваются как workflows/templates внутри него, а не как третья
   платформа.
4. `video_repurposer` — подтверждённая долгосрочная часть продукта: нарезка
   стримов, подкастов, мультфильмов, фильмов и локальных длинных видео.
   Развивается из существующего Anime Factory. **Второй clip pipeline с нуля
   запрещён.**
5. Отсутствие `video_repurposer`-проектов сейчас не доказывает отсутствие
   потребности: capability выключена. Приоритетом он при этом не является и
   остаётся disabled до migration и product evidence.
6. Runtime Workspace остаётся целевой архитектурой: код и пользовательские
   данные должны быть физически разделены. Физическая runtime migration сейчас
   отложена; `WorkspacePaths`, tolerant legacy reads и цель
   `copy → verify → switch` сохраняются.
7. Внешний `AI-YouTube-System` допустим только как необязательный
   пользовательский mirror и не является source of truth.
8. Обязательное дерево `core/services/infrastructure` отменено. Структура
   остаётся настолько плоской, насколько позволяет продукт; новый уровень
   каталогов создаётся только при доказанной границе, нескольких реальных
   callers и измеримой пользе.
9. Для каждой capability не должно быть двух реализаций, способных разойтись в
   поведении. Физическое расположение кода само по себе дефектом не является;
   переносить рабочие файлы ради соответствия дереву запрещено.
10. Канонический пользовательский путь — `python -m ai_youtube`. Старые
    entrypoints (`python -m src.content_creation.cli`, `python pipeline.py`,
    `python -m apps.*`) не являются постоянным пользовательским контрактом.
    **Изменено ревизией 2:** формулировка «сначала PLAN-1» отменена. Каждый
    entrypoint удаляется после **своего** capability gate; для legacy-семейства
    это PLAN-L1, а не глобальный inventory.
11. Владелец подтвердил отсутствие личных `.bat`/`.cmd`/`.ps1`, ярлыков,
    Windows Tasks и IDE Run Configurations, которые нужно сохранять ради старых
    команд. Поиск по компьютеру вне репозитория запрещён.
12. R1–R12 становятся новой governance model (внедрение — PLAN-6). Отдельный
    ADR про переход на новые правила не создаётся.
13. Платные и сетевые операции требуют отдельного разрешения на конкретное
    действие. Для M1: 0 USD и ноль новых платных Vision-вызовов. Бюджет M2 —
    `TBD`, подтверждается отдельно перед первым реальным платным запуском.

## Owner decisions ревизии 2 (2026-07-31)

Ревизия 2 пересмотрела план под явную позицию владельца: существующая
зависимость, существующий owner и существующая архитектура **не являются
доказательством правильности**; тестовое runtime-медиа ценности не имеет;
правила ограничивают исполнение, но не мышление; программа не должна
превратиться в бесконечное строительство governance.

| # | Решение |
|---|---|
| **OD-1** | `channels/{psychology,quotes,survival,size_comparison}` и `content/` не сохраняются как активные workflows. Ретайр вместе с legacy допускается **только после Knowledge Salvage Gate** |
| **OD-2** | `apps/news_to_short` как отдельный CLI не сохраняется. Если его флаги полностью покрыты каноническим CLI — удалить; уникальную возможность сначала перенести в `content_creator`, затем удалить |
| **OD-3** | `assets/voice_samples` — disposable test/runtime media, в source repo не хранится. Если конкретный активный voice profile действительно требует sample — перенести минимально необходимый во внешний Workspace с provenance, иначе удалить |
| **OD-4** | Бюджет M2 остаётся `TBD` и ничего не блокирует |
| **OD-5** | Вся поддерживаемая human/agent-проза со временем становится преимущественно русской, **включая body существующих ADR**. Инкрементально, без одного mass-diff; не блокирует product work |
| **OD-6** | Locked decisions 8 и 9 больше не запрещают пересмотр `config`/`channels`/`assets`/`resources`. Пересмотр — только после классификации, не ради эстетики |
| **OD-7** | **MOSS-TTS не нужен продукту.** Не реинтегрировать как активный TTS provider. KSG → caller audit → удалить `MOSS_TTS_Nano/` и `src/tts_providers/`. Не сохранять 56k файлов «на всякий случай»; vendor repo в `Workspace/models` не переносить |
| **OD-8** | Live-eval — evaluation resource. **`docs/` — неправильный target owner.** Fixture/evidence сохраняется, caller позже переводится на утверждённого owner. `resources/evaluation/` — **только candidate path**; физический target `DEFER` до PLAN-13 |
| **OD-9** | Top-level `resources/` — `DEFER` до PLAN-13, заранее **не создавать**. Сначала классифицировать `channels` · `schemas` · reusable templates · evaluation resources · versioned assets/config, затем решить, уменьшает ли `resources/` число owners |
| **OD-10** | `size_comparison_engine`: L0 сохраняет reusable algorithm, domain knowledge, visual logic, edge cases и полезные тесты. **Capability внутри L3 не мигрируется.** Если формат понадобится — отдельный будущий product slice на новом canonical core |

## Owner decisions ревизии 2.1 (2026-07-31)

Ревизия 2.1 — **перестановка и переадресация**, а не переписывание. Ни один
существующий PLAN-ID не удалён. Источники: `docs/audits/`
`CRITICAL_INPUT_SEARCH_DEEP_DIVE_2026-07-31.md`,
`PROJECT_EXECUTION_PLAN_REVISION_2_1_PROPOSAL_2026-07-31.md` и
`SECONDARY_ARCHITECTURE_FINDINGS_DEEP_DIVE_2026-07-31.md`. **При конфликте
Secondary Deep Dive исправляет Proposal 2.1**; исправленные формулировки
записаны ниже и в разделе «Ревизия 2.1: опровергнутые формулировки».

| # | Решение |
|---|---|
| **OD-11** | **PLAN-P0 (Content & Query Reachability Gate) не создаётся.** Evidence уже получено двумя deep-dive offline, без сети и денег. Тесты T1–T11 из `CRITICAL_INPUT_SEARCH_DEEP_DIVE` становятся regression/product-тестами **внутри соответствующих PLAN-9B слайсов**, а не отдельным диагностическим этапом |
| **OD-12** | CRITICAL-1 — текущий главный product defect в **исправленной** формулировке: не «ноль запросов», а «ложные / чрезмерно общие / пропущенные запросы, и единственный канал доставки provider-ready английского запроса — hardcode на одну тему» |
| **OD-13** | **Не создавать** `TranslatorService`, `SearchEngine`, `QueryOrchestrator` и второй query pipeline. Переиспользуются `VisualBrief`, `SceneVisualPlan`/`VisualSearchIntent`, `build_scene_queries`/`build_slot_queries`, `ProviderQuery`, provider contracts |
| **OD-14** | `src/assets/query_adapter.py` — фактическая canonical boundary, через которую remote-запросы доходят до провайдеров. Allowed zone PLAN-9B исправлена на неё |
| **OD-15** | **PLAN-9B выполняется до PLAN-9A.** Best-so-far persistence бессмысленна до появления provider-ready кандидатов. PLAN-9A не удаляется и состав не меняет |
| **OD-16** | Метод provider-language adaptation **не фиксируется заранее**: deterministic normalization/lexicon, prepared `VisualBrief`, model-assisted adaptation или комбинация. Выбор — по semantic correctness, fail-closed, testability, cost, network/paid boundary и reuse существующих owners. **Model/network вариант требует отдельного owner approval** |
| **OD-17** | CRITICAL-2 исправляется сейчас, **без AI research**. Idea generation, web/AI research, AI script writing, autonomous creative direction — **DEFER**: без PLAN, package, interface и placeholder |
| **OD-18** | Для factual strict workflow `topic` = **intent, не source material**. Silent fallback `topic → insufficient material → generic template → factual production success` запрещён. `LegacyTemplateScriptProvider` **не удаляется**: допустим только в явно выбранном `template`/`demo`/`test`/`draft`. `content_origin` **не создаётся** |
| **OD-19** | Capability `apps/news_to_short --text/--text-file` **мигрирует** в канонический `python -m ai_youtube` + content_creation request path. **Разделено (D-1):** миграция — PLAN-9B-5a (additive), retirement — PLAN-9B-5b. **Исправлено 2026-08-01:** это не единственная возможность wrapper'а — перед retirement обязателен полный **capability parity check** (см. PLAN-9B-5b), минимум `--text`/`--text-file` **и** `--assets` |
| **OD-20** | CRITICAL-3 («в content path мало AI») **не является** current defect и отдельного этапа не получает. Future-proofing rule: downstream pipeline не должен предполагать, что script создан внутри AI-YouTube; prepared external content — first-class input |
| **OD-21** | CRITICAL-4 (double orchestration) сохраняется как architecture debt, **не** prerequisite CRITICAL-1/2. **Исправлено Secondary Deep Dive:** severity **MEDIUM**, не HIGH; finding разделяется на contract defect и возможную позднюю конвергенцию (D-3) |
| **OD-22** | Порядок semantic/Vision: provider-ready query → candidates → semantic/Vision → rank/select. PLAN-9C сохраняется, новый semantic stack не создаётся |
| **OD-23** | Anime Factory — **не** disposable legacy: это source implementation будущего `video_repurposer`. Порядок: Content Creator stable → UI Content Creator → deep audit Anime Factory → KEEP/MIGRATE/REWRITE/SHARE/DELETE → Video Repurposer → его UI. Runtime внутри source repo остаётся дефектом, owner — PLAN-14 |
| **OD-24** | `search_session.json` как отдельный persisted owner **не утверждается**. Сначала проверить `job.json`, asset manifest, project state, completion/resume state. Если существующего owner можно расширить — новый persisted файл запрещён |
| **OD-25** | **Multi-topic regression начинается раньше PLAN-11** и выполняется после каждого существенного product slice, где это релевантно: минимум по одной репрезентативной теме из разных классов (animals/wildlife · energy/technology · geography/infrastructure). PLAN-11 остаётся финальным product evidence gate, но **не первой** multi-topic проверкой |
| **OD-26** | Governance не задерживает дешёвое product-исправление без конкретной защищаемой boundary, **но** safety/reviewer/persisted/paid protections обязаны быть готовы **до своей risk boundary**. Каждый оставшийся blocker имеет однострочное обоснование |
| **D-1** | **ДА** — 9B-5 разделяется на **9B-5a** (additive source-text canonical input; public CLI surface + owner approval; не destructive) и **9B-5b** (retirement `apps/news_to_short`; требует PLAN-6D + PLAN-6E + reversible retirement) |
| **D-2** | **ДА** — PLAN-10B **не является** owner provider-registry convergence; сама гипотеза «пять расходящихся реестров надо свести» **опровергнута**. PLAN-10B возвращается к своей реальной ответственности: pagination / provider exhaustion / provider contract behavior |
| **D-3** | **ДА** — double orchestration finding разделяется на точный idempotency contract defect (owner: ADR 0006 / `src/news/pipeline.py`) и возможную позднюю orchestration convergence (owner: PLAN-13B, только если после исправления contract остаётся архитектурная необходимость). Severity **MEDIUM** |
| **E-13** | CRITICAL-2 остаётся **bounded sub-slices существующего PLAN-9B**. Новый top-level PLAN-ID не создаётся |
| **1C′/6E** | Прямая зависимость `PLAN-1C′ → PLAN-6E` **снята**. Одновременно **явно установлено**: `PLAN-9A` требует `PLAN-6E` (persisted-state boundary), `PLAN-9C` требует `PLAN-6E` (semantic decision boundary). Транзитивная зависимость через PLAN-9B-2 доказательством не считается |
| **export** | PLAN-11 — **evidence gate**, обязанный ловить ложные product capabilities. Implementation owner — будущий bounded `production_catalog` slice. Нового PLAN-ID не создаётся |
| **ffmpeg** | PLAN-8 — **roadmap owner** product-quality item. Implementation owner — будущий bounded renderer slice с characterization первым. Нового PLAN-ID не создаётся |
| **subprocess** | Архитектурное решение по subprocess network kill-switch **сейчас не принимается**: механизм и owner остаются implementation-time evidence/owner decision. **PLAN-6B остаётся report/measurement owner в своей текущей границе** |

### Ревизия 2.1: опровергнутые формулировки

Эти утверждения **опровергнуты** контролируемыми offline-пробами Secondary Deep
Dive. Возвращать их в план, registry, задания и commit-сообщения запрещено.

| Опровергнутая формулировка | Что верно на самом деле |
|---|---|
| «semantic-слой по построению не может влиять на selection»; «`_selection_fingerprint` делает неизменность отбора инвариантом сервиса» | metadata-semantic слой **уже** ranks / rejects / blocks и **может сменить выбранный asset** — доказано synthetic-пробой. `_selection_fingerprint` — защитная самопроверка, а не вето. Дефект — в том, что платный Vision пишет результат **поздно** в review-манифест и не подаёт evidence в decision layer до отбора |
| «два конкурирующих orchestration owner»; «ровно 7 pipeline calls»; «есть риск повторного платного TTS» | ADR 0009 **намеренно** разделяет application orchestration и news pipeline ownership. Вызовов **4–7** в зависимости от режима. Реальный дефект — explicit `stage=` path отключает output-validated idempotency ADR 0006 условием `and not stage` (`src/news/pipeline.py`). Batch-режим idempotency соблюдает. Повторного платного TTS аудит **не обнаружил**: несколько независимых guard'ов плюс существующие тесты |
| «три независимых LocalLibrary implementation»; «#1 допускает `RIGHTS_REFERENCE_ONLY`, поэтому мягче»; «более строгая реализация — та, которую никто не вызывает» | Один `media_index`, один rights-authority `apply_policy_to_candidate`, **два** matcher'а, несколько consumers/wrappers; legacy path #3 использует **ту же** `media_library.search_local_assets`, что и #1. Доказанных расхождений live-путей ровно **два**: missing `provenance` и `review_required=True`. Обратных расхождений — ноль. Аргумент про `RIGHTS_REFERENCE_ONLY` опровергнут: значение перезаписывается политикой |
| «пять расходящихся provider registries, всё свести к `providers/registry`»; «owner конвергенции — PLAN-10B» | Это **разные legitimate facts**, а не дубли: actual constructed providers · provider capabilities · fallback language info · source-class priority · diagnostics inventory · availability. `ProviderCapabilities.query_languages` **уже** имеет приоритет над fallback-таблицей. Остаточный cleanup: declaration mismatch `local_library` → PLAN-10D; вестигиальный `DEFAULT_PROVIDER_ORDER` и осиротевший `unsplash` → opportunistic cleanup. Отдельный PLAN-ID не создаётся |
| «сегменты crf 23 → **конкатенация** crf 20 → субтитры crf 21»; «single-pass — простой fix» | Нормальный путь: segment encode CRF 23 → concat **`-c:v copy`** (не перекодирует) → audio + exact-duration encode CRF 20 → ASS subtitle encode CRF 21 → copies. Три lossy generations возникают **при audio + ASS subtitles**. CRF 20 имеет документированную причину (exact-duration/tpad behavior). Полный single-pass filtergraph — отдельное более крупное исследование |
| «PLAN-5 обязателен до PLAN-9B-5 и PLAN-9B-3» | Targeted, full и все три smoke-команды исполнимы **сегодня** существующими командами. PLAN-5 улучшает uniform runner UX/reproducibility, но техническим blocker product fixes не является |
| «`legacy_broad_query` — единственное, что гарантированно доходит до провайдера» | Не доходит ни разу: `source_is_latin` — свойство всего набора, поэтому русский `primary_query` выбрасывает английский alternative вместе с собой |
| «topic-hardcode сосредоточен в `semantic_selection/query_generator.py`» | Этот модуль **не участвует** в формировании remote-запросов. Canonical boundary — `src/assets/query_adapter.py`; главный носитель hardcode — `src/news/script_generator.py` |
| «канонический CLI не имеет source-text входа»; «`--text`/`--text-file` — единственная уникальная capability `apps/news_to_short`» (**опровергнуто 2026-08-01**) | `create --pasted-script` / `--script-file` при default/legacy unspecified `content_input_mode` уже проводят подготовленный текст в тот же downstream, поэтому PLAN-9B-5a делает вход **явным**, а не создаёт движок. Вторая возможность wrapper'а — `--assets` → `NewsJob.user_assets`, у которой канонического аналога нет; она не может быть молча потеряна при retirement |

### Открытые вопросы ревизии 2.1 (закрываются в момент implementation)

**Закрыты и в списке unresolved больше не значатся:**

- **E-2 — ЗАКРЫТ.** `ProviderQuery.source` — существующее свободное строковое
  telemetry-поле; это **не** schema-level change, tolerant reader не нужен,
  persisted-bytes tripwire не срабатывает. Байты `assets_manifest.json` при этом
  меняются, поэтому characterization PLAN-9B-0 обязан зафиксировать текущее
  содержимое `query_plan` до правки.
- **E-5 — ЗАКРЫТ ОТРИЦАТЕЛЬНО.** PLAN-10B не является owner provider-registry
  convergence, потому что сама registry-convergence гипотеза опровергнута.
- **E-7 — ЗАКРЫТ.** Rights/provenance comparison трёх local-library путей
  выполнен Secondary Deep Dive: ровно два доказанных расхождения.

**Остаются открытыми, каждый — внутри своего слайса, не отдельным аудитом:**

| Вопрос | Кто закрывает |
|---|---|
| полный inventory topic-hardcodes (**PROVISIONAL**, число файлов не invariant) | PLAN-9B-2 |
| миграция всех callers `semantic_selection/query_generator` | PLAN-9B-3 |
| backward compatibility CRITICAL-2 fix со старыми persisted проектами | PLAN-9B-4 |
| метод provider-language adaptation (OD-16) | PLAN-9B-1 |
| механизм и owner subprocess network kill-switch | владелец / PLAN-6B / PLAN-5 |
| public behavior `resume`/`force`/`stop-stage` до крупной orchestration convergence | PLAN-13B |
| реальный ущерб от нескольких FFmpeg-кодирований (никто не рендерил) | будущий renderer slice |
| осуществимость слияния audio/duration encode + subtitle burn в один encode | тот же слайс |
| регистрировать ли `local_library` как `StockProvider` после PLAN-10D | PLAN-10D |
| зелёность baseline | PLAN-4 |

### Сильные foundations — сохраняются

Ревизия 2.1 **не** превращает работающие foundations в кандидатов на rewrite.
Второй competing owner для этих ответственностей не создаётся:

`src/assets/completion/` как canonical completion/readiness owner ·
rights / provenance / `must_avoid` / misleading / conflict gates ·
`VisualBrief` как существующий transport contract ·
`ScriptValidationResult` + `script_metadata` · `DeterministicScriptProvider` ·
`LegacyTemplateScriptProvider` для explicit `legacy`/`template`/`demo`/`test`/
`draft` · subtitles foundation · `src/audio/scene_timeline.py` ·
production catalog foundation · tolerant project readers · final renderer до
отдельного renderer-слайса · `tests/network_guard.py` ·
`route_providers` / `scene_strategy`, пока evidence не докажет их дефект.

**Hard constraints не ослабляются ревизией 2.1:** factual truth · rights ·
provenance · `must_avoid` · misleading/conflict · paid approval остаются
`[HARD]` и heuristics не становятся.

### Никакой новой архитектуры из аудита

Audit evidence обязано **уменьшать** архитектуру, а не порождать абстракции.
Не создавать: `TranslatorService` · `SearchEngine` · `QueryOrchestrator` ·
`search_session.json` · `content_origin` · новый semantic stack · четвёртый
LocalLibrary path · второй completion-state vocabulary · placeholder-пакеты и
speculative interfaces под future AI.

## Owner decisions: motion rendering (2026-08-01)

Источник — read-only rendering / motion-design / AI-directed video аудит от
clean HEAD `35325b4`; findings записаны в `CLEANUP_REGISTRY.md` как C53–C62.
Продуктовая форма направления — `PRODUCT_PLAN.md`, раздел «Motion Design and
Multi-Renderer Composition». **Ни одно решение ниже не меняет current
checkpoint, критический путь, prerequisites и статусы существующих этапов.**

| # | Решение |
|---|---|
| **OD-M-1** | **Несколько специализированных авторов кадра, но не несколько конкурирующих pipelines.** Каноническая модель: `content core → visual/composition intent → canonical author для composition_type → normalized scene artifact → FFmpeg final assembly → существующие quality/rights/export` |
| **OD-M-2** | **FFmpeg остаётся canonical final assembler**: normalization, concat, voice, music, SFX, subtitles, encoding, export. Его роль не оспаривается ни одним motion-инструментом. При этом **`final_renderer` не объявляется неизменным**: его foundation подлежит доработке (C58–C61) |
| **OD-M-3** | **Stock crop/zoom path сохраняется и дорабатывается, а не замещается** (C57). Для стокового кадра FFmpeg — лучший инструмент; широкий renderer cleanup не имеет права его удалить |
| **OD-M-4** | **Один `composition_type` → один canonical production backend.** Разные `composition_type` могут иметь разных специализированных авторов. Бессрочно поддерживать один user outcome в двух реализациях (counter в двух backend одновременно) запрещено |
| **OD-M-5** | **Пользователь и AI выбирают визуальный замысел, а не библиотеку**: stock footage · animated counter · chart · map · comparison · process diagram · text emphasis · scientific animation. Expert/debug режим позднее может отключать web motion, включать безопасный fallback, выбирать backend в сравнительном PoC и диагностировать сбои. **Точные публичные имена не фиксируются** |
| **OD-M-6** | **Порядок AI-режиссуры:** AI Director предлагает 2–4 варианта **разных** `composition_type` → каждый даёт дешёвый poster frame → deterministic QA отсеивает технический брак → Vision или человек выбирает по смыслу → полный motion render только для выбранного → отвергнутые сохраняются как evidence. Аудиция идёт по замыслу, а не по инструментам. **Новый AI orchestration owner не создаётся** — расширяются visual planning, production catalog, semantic evidence, completion/review |
| **OD-M-7** | **PD-11 — Replacement and Retirement Pairing.** Внедрение, замещающее существующую capability, обязано иметь связанный retirement path. Полная формулировка и жизненный цикл — `PRODUCT_PLAN.md`, раздел 4 |
| **OD-M-8** | **Story Card сохраняется как рабочий product template; удаление шаблона запрещено.** Его текущий MoviePy renderer — **временная** implementation, бессрочное закрепление запрещено. Story Card становится **обязательным parity-case** сравнительного PoC (C53) |
| **OD-M-9** | **`generated_infographic` разбирается, а не удаляется целиком** (C56). Сохраняются: правило «нет evidence → нет фактической диаграммы», fingerprint спеки, создание project-owned актива с license/provenance/checksum, technical validation, минимальная offline аварийная карточка. Замещается только рисующая часть |
| **OD-M-10** | **Целевая стратегия инструментов — вариант «Hybrid high-quality».** CORE: FFmpeg + один web motion backend после PoC + ECharts. COMMITTED LATER: MapLibre (после license decision) · Lottie · OTIO только как односторонний export. SPECIALIZED ON DEMAND: Manim · Three.js внутри выбранного backend · Blender после hardware review · Resolve/Fusion как внешний manual finishing |
| **OD-M-11** | **Motion Canvas в первый PoC не включается.** Пересмотр только если Remotion и HyperFrames оба провалят обязательные критерии детерминизма или Windows-надёжности |
| **OD-M-12** | **Не добавлять сейчас:** Vega-Lite как второй runtime · D3 как отдельный chart stack · deck.gl · Rive · PySceneDetect/OpenCV в Content Creator · Shotstack/Creatomate · обязательный cloud rendering · генерация произвольного кода в пользовательском рантайме |
| **OD-M-13** | **`PLAN-9B` — вторая половина формата Hybrid Explainer, а не его предшественник.** Стоковая часть гибридного формата зависит от корректных provider-запросов, поэтому motion-направление её не заменяет и не откладывает |

### Motion rendering: что остаётся `OWNER_DECISION_REQUIRED`

Не утверждено этим слайсом и не может быть выведено из аудита:

1. победитель Remotion vs HyperFrames;
2. актуальные лицензии и коммерческие ограничения любого инструмента;
3. точные публичные имена `composition_type`;
4. владелец хранения design tokens (`channels` либо `config/design_tokens`);
5. место persistence render cache/fingerprint;
6. политика map tiles и styles;
7. момент постановки `MOTION-CS1…CS4` в расписание;
8. удаляется ли проигравший web backend полностью или сохраняется только в
   developer-only PoC archive.

### Motion rendering: что запрещено утверждать без отдельной проверки

Ни один из пунктов ниже не измерялся и не проверялся в этом слайсе, поэтому
записывать их как факт запрещено:

- что MoviePy доказанно медленнее browser backend на текущей машине владельца;
- что HyperFrames не несёт коммерческого риска;
- что Remotion имеет конкретную текущую цену или конкретные условия лицензии;
- что вопрос map tiles/styles решён;
- что RX 570 работает или не работает в конкретном текущем релизе любого
  инструмента.

Такие пункты маркируются
`REQUIRES SEPARATE WEB/LICENSE/HARDWARE VERIFICATION`.

Численные пороги сравнительного PoC (например время рендера сцены, время
poster frame, потолок памяти, доля совпадений perceptual hash, число прогонов,
доля автоматически исправленных сцен) остаются **предлагаемыми критериями
измерения**. Ни один из них ещё не измерялся, поэтому нормой продукта они не
являются — действует общая `Measurement policy` этого плана.

## Safety boundaries

Действуют правила R1–R3 из `AGENTS.md`; здесь они не дублируются.
Дополнительно на период этой программы:

- сеть, provider search, download, Vision, TTS, render и платные API не
  выполняются без отдельного разрешения на конкретное действие;
- synthetic render в tempfile разрешён и обязателен для renderer contract
  tests; реальный render пользовательского проекта — только по необходимости и
  с разрешением;
- в `master` не сливать и ничего не публиковать без отдельного разрешения;
- destructive retirement **knowledge-bearing family** (source, workflow, config,
  prompts, templates, tests, уникальное docs/evidence) выполняется только после
  Knowledge Salvage Gate (PLAN-L0) и с обратимым retirement-механизмом;
- удаление **disposable runtime/media/cache** идёт цепочкой PLAN-14D → PLAN-14E
  и KSG не требует; его gate — классификация, `Preserved runtime corpus`,
  проверенный абсолютный путь и owner approval на конкретное действие.

**Изменено ревизией 2.** Безусловная неприкосновенность `projects/`, `assets/`,
`manual_assets/`, `music/`, `outputs/` снята: владелец объявил тестовое
runtime-медиа disposable. Вместо неё действует точный список сохраняемого.

**Preserved runtime corpus — сохраняется обязательно:**

- отобранный **минимальный representative** набор JSON/SRT/ASS манифестов
  проектов (состав определяет PLAN-14D, см. registry C32);
- `assets/library/metadata/media_index.json` — provenance и rights локальной
  медиатеки;
- versioned SVG в `manual_assets/**`;
- versioned config `config/` (кроме умирающего `video_style.json`) и активные
  `channels/nature_science_news_ru`, `channels/nature_pulse`;
- live-eval dataset/results/frames как evaluation resource (переезжает по OD-8).

**Disposable — удаляется на runtime reset:** медиа во всех перечисленных
каталогах (`*.mp4`, `*.mov`, `*.wav`, `*.mp3`, `*.png`, `*.jpg`, `*.jpeg`),
кэши, `project_solar_vs_nuclear/`, `assets/voice_samples` (OD-3),
`MOSS_TTS_Nano/` (OD-7).

**Оговорка PLAN-9D evidence (обновлено PLAN-9D-A, commit `2bae6f6`,
2026-08-08).** Пока PLAN-9D открыт, runtime-пути под `projects/`, на которые
ссылается текущее curated historical evidence PLAN-9D, disposable **не
считаются**, хотя формально подпадают под `*.jpeg` и «кэши» выше. После
PLAN-9D-A это не 107 путей прежнего замороженного `corpus_v1.json` по всему
дереву `projects/`, а ровно curated runtime dependency, которую отчитывает
implementation-owned `historical_runtime_paths()` над
`tests/data/plan9d/historical_failure_evidence_v1.json` — этот файл и функция
остаются единственным detailed source, список путей здесь не дублируется.
Оговорка снимается автоматически на шаге (4) cleanup sequencing PLAN-9D —
после того как historical failure evidence curated (**PLAN-9D-A, closed**),
current corpus снят и заморожен (PLAN-9D-B) и ground truth заморожен
(PLAN-9D-D). До этого удаление любого из этих путей выполняется только по
явному owner approval на конкретный путь; сокращение состава путей
PLAN-9D-A не является разрешением на их cleanup сейчас. Отдельный PLAN-ID и
вторая строка `Preserved runtime corpus` не создаются: это ограничение
порядка, а владелец порядка — этот файл.

Ни одно удаление не выполняется вне своего bounded slice и без явного
подтверждения абсолютного пути.

## Agent Autonomy Model

Действует на период этой программы. Канонический владелец правил после PLAN-6A —
`AGENTS.md`; здесь модель зафиксирована, чтобы она действовала **до** 6A, и
после 6A этот раздел сворачивается до ссылки. Отдельный документ не создаётся.

### Классы правил

```
[HARD]   нарушать нельзя. Если правило можно enforce технически —
         оно обязано быть enforced, а не только записано.
[ARCH]   архитектурная граница. Пересматривается через evidence,
         ADR и independent review. Оспаривать — можно и нужно.
[HINT]   рекомендуемый способ. Если он не достигает SUCCESS CRITERIA,
         агент обязан искать другой и назвать причину смены.

Правило без класса читается как [HINT].
```

**[HARD].** Secrets · платные и сетевые вызовы без разрешения на конкретное
действие · destructive Git · удаление реальных user data · rights, `must_avoid`,
misleading и conflict gates · публикация · изменение persisted contract без
tolerant reader и migration · второй одновременно живущий canonical owner ·
**доказать canonical owner, callers, persisted contracts, дубли и тесты
изменяемой capability до её изменения**.

**[ARCH].** Канонический CLI `python -m ai_youtube` · два engine (ADR 0016) ·
один owner на capability · направление зависимостей · граница workspace
(ADR 0002) · владение persisted schema · `strict` как default completion mode ·
tolerant readers · размещение пакетов и структура корня.

**[HINT].** Приоритет провайдеров · число и виды запросов · пороги
`minimum_confidence`/`hard_reject_confidence` · `analyse_and_report` и
`semantic_rerank_enabled: false` · предпочтительный тип визуала · порядок
внутренних действий · «только targeted tests» · рекомендуемый размер модуля ·
лимит длины `AGENTS.md`.

### Goal > prescribed method

```
Выполнение инструкции не является выполнением задачи.
Если CURRENT APPROACH не достигает SUCCESS CRITERIA, задача не закрыта.
Агент переходит к поиску альтернативы внутри [HARD] и своих decision rights,
а не сообщает об успехе на основании соблюдённой процедуры.
```

Плохой quality score сам по себе **не** является причиной остановки. Допустимые
причины остановки перечислены в PLAN-10A.

### Decision rights — три tripwire

Owner approval требуется, когда изменение затрагивает:

1. **persisted bytes** — schema, поле манифеста, layout файлов, имя каталога
   проекта (дополнительно обязателен tolerant reader);
2. **внешне наблюдаемую поверхность** — имя команды CLI, флаг, exit code, ключ
   JSON-вывода, имя console script;
3. **деньги, сеть или публикацию** — на каждое конкретное действие.

Всё остальное — решение агента под ответственность reviewer, **включая удаление
реализации, у которой есть callers**, если callers переведены в том же изменении
и ни один tripwire не сработал. Существующая зависимость не является
доказательством, что её нужно сохранять.

**Уже выданные owner approvals.** Tripwire не отменяется и не ослабляется;
approval — это факт, а не исключение из правила. Утверждение владельцем ревизии
2 этого плана является explicit owner approval на persisted-change **ровно в том
объёме, который уже описан в PLAN-9A**: additive schema, tolerant reader,
чтение старых manifests без миграции, best-so-far/persistence contract в
перечисленном там составе. Повторно спрашивать владельца о самом PLAN-9A не
нужно.

**M1-C extension (2026-08-11).** Отдельное owner approval, выданное текстом
M1-C prompt, расширило этот состав ровно на `replaces_asset_id` и Vision
evidence envelope (`vision_tags`, `vision_tags_asset_id`,
`vision_tags_source_sha256`, `vision_tags_cache_key`) в `AssetCandidate`;
closed commits `c9537fa`/`a7bec3c`/`2577307`, Review #1 ACCEPT. Дальнейшее
расширение вне этого состава снова требует отдельного owner decision.

Любое расширение за эти границы — non-additive изменение, новый layout файлов,
переименование каталога проекта, второй manifest, схема вне названного состава
или persisted-изменение в другом слайсе — снова требует owner approval. Approval
на PLAN-9A не переносится на PLAN-9B…PLAN-15 и на PLAN-L. **Уточнено ревизией
2.1:** approval PLAN-9A относится **ровно** к составу PLAN-9A и не переносится
на `PLAN-9B*`, `PLAN-9C`, `PLAN-9D`, `PLAN-9E`, `PLAN-10*` и любые новые
persisted / public / network / destructive изменения.

### Challenge / Recovery Protocol

Новые имена состояний завершённости **не вводятся**: словарь уже принадлежит
`src/assets/completion/modes.py` (`usable_in_draft`, `automatic_render_allowed`,
`publish_ready`, `manual_replacement_recommended`, `manual_replacement_required`,
`blocked` + `block_reasons`, tiers `A_exact…F_emergency`). Причины остановки
принадлежат PLAN-10A. Второй словарь создал бы второго canonical owner.

Когда предписанный подход не даёт результата:

1. назвать **root cause**, а не симптом;
2. **не ослаблять [HARD]**;
3. найти **минимум одну жизнеспособную альтернативу**. Сравнение нескольких
   альтернатив обязательно **только** для неоднозначного, архитектурного,
   дорогого или высокорискового решения; в обычном случае одной работающей
   альтернативы достаточно;
4. внутри decision rights — применить и записать причину;
5. вне decision rights — остановиться, показать альтернативу и рекомендацию.

### Owner Lookup — semantic trigger

Проверка существующего владельца обязательна, когда создаётся:

- новая **shared / cross-cutting responsibility**;
- новый **public owner** — то, на что будут ссылаться извне модуля;
- новый **persisted owner** — то, что пишет или владеет форматом на диске.

Имена классов `Service|Registry|Manager|Provider|Store|Engine` — только
эвристика для reviewer, не сам триггер. Для private-функций не применяется.

Процедура — один проход: grep по существительному-ответственности в
`SYSTEM_MAP.md`, `schemas/` и `src/**` → `reuse` / `extend` / `replace`. При
создании нового owner — одно предложение в commit body о том, почему
существующий нельзя расширить. Enforce выполняет reviewer, отдельный QA-модуль
не создаётся: проверка требует суждения.

### Task contract

Формат задания каждого достаточно крупного слайса:

```
OBJECTIVE          что должно измениться для пользователя
SUCCESS CRITERIA   какой конечный результат считается хорошим
HARD CONSTRAINTS   что нельзя нарушать
ALLOWED ZONES      какие файлы/каталоги разрешено менять
CURRENT APPROACH   рекомендуемый способ
ALTERNATIVES       агент вправе искать самостоятельно
STOP CONDITIONS    когда действительно нужно остановиться
VERIFICATION       чем доказан результат
ROLLBACK           как откатить
EXIT CONDITION     когда пункт можно снять с учёта
```

`ALLOWED ZONES` держится отдельно от `HARD CONSTRAINTS`: первое — scope одного
слайса, второе — вечное правило. В прежней редакции оба записывались одинаково
под заголовком «запрещено», и агент не мог отличить оспариваемое от
неоспариваемого.

## Reversible retirement mechanism

Постоянный каталог `trash/` не создаётся: он стал бы вторым source tree.
Механизм обратимого ретайра:

1. **annotated tag** `retired/<family>-<YYYY-MM-DD>` на последний commit, где
   код ещё существовал;
2. **commit body** ретайр-коммита содержит `Retired:`, `Reason:`,
   `Replaced-by:`, `Recovered-from:` (тег), `Salvaged:` (ссылка на решение
   PLAN-L0), `Exit:`;
3. **таблица `Retired`** в `CLEANUP_REGISTRY.md`;
4. **внешняя копия обязательна.** [FACT, обновлено 2026-08-05] Приватный
   remote теперь существует и `governance-reset`/`master` отправлены (OD-S-5);
   это не отменяет правило, потому что retirement-теги не публикуются
   обычным push и остаются локальными, если их не отправить отдельно: перед
   каждым ретайром по-прежнему выполняется `git bundle create` тега во
   внешний workspace.

Archive branch не используется: ветки дрейфуют и требуют обслуживания.

## Test classification

Перед любым удалением или переписыванием test-модуль получает класс:

```
PRODUCT CONTRACT        защищает поведение, обещанное пользователю
ARCHITECTURE INVARIANT  защищает границу, которую мы намеренно держим
CHARACTERIZATION        зафиксировал поведение на время конкретного refactor
LEGACY ANCHOR           замораживает старую реализацию или accidental structure
```

**LEGACY ANCHOR не препятствует сознательному ретайру старой архитектуры** и
удаляется либо переписывается вместе с ней. Зелёный или красный тест сам по себе
контрактом не является: сначала отвечаем, защищает ли он нужное product/public
behavior или замораживает accidental legacy implementation.

Подтверждённые кандидаты в LEGACY ANCHOR записаны в `CLEANUP_REGISTRY.md`,
раздел «Accidental invariants».

**Физический restructure каталога `tests/` не является prerequisite product
work и в критический путь не входит.** [FACT] на 2026-08-17, HEAD `3619fe1`, —
**137 модулей `test_*.py` и 48 852 строки в них**; всего в каталоге 144 файла
`*.py` и **53 495 строк** (`wc -l tests/*.py`). Две базы названы раздельно
намеренно: прежняя запись давала одно число «53 221» под подписью `wc -l
tests/*.py`, и по нему нельзя было понять, посчитаны модули тестов или весь
каталог, — а с 2026-08-16 оно к тому же разошлось с фактом на 274 строки.
Ещё более ранняя запись «112 плоских модулей, 30 403 строки» устарела и
занижала объём на 75 % по строкам. `conftest.py` отсутствует, network guard
ставится из `tests/__init__.py`. Плоская структура с осмысленными именами
работает; реструктуризация дала бы большой diff и нулевую product-ценность.
Вопрос пересматривается **после** PLAN-L.
Именование вида `test_anime_factory_v3/v4` и `test_stage1…stage4` кодирует
историю rescue, а не ответственность — кандидаты на переименование, но не
приоритет.

**Известный риск, не закрытый классификацией.** [FACT] test-модули запускают CLI
через `subprocess`, где `tests/network_guard.py` **не действует** — guard живёт
внутри test-пакета и дочерним процессом не наследуется. Это касается не только
режима `smoke` из PLAN-5, но и `full`. **Измерение, не invariant:** на audit HEAD
`adcbb19` таких модулей **12** (было записано 7); при изменении tests число
изменится, нормой оно не является (registry C49).

**Механизм закрытия ревизией 2.1 заранее не выбран.** Расширение guard на
subprocess boundary и environment kill-switch — обе альтернативы остаются
открытыми; выбор и owner — implementation-time evidence/owner decision. **PLAN-6B
остаётся report/measurement owner в своей текущей границе** и ничего не мутирует;
если выбранный механизм потребует, чтобы production-код уважал kill-switch, это
production-изменение вне зон 6B и оно получает своего owner отдельным слайсом.

## Measurement policy

Число тестов, длительность прогона и accuracy моделей — **изменчивые
наблюдения**. Они записываются только как измерение с датой и проверяемым
состоянием Git и никогда не становятся нормой в правилах, тестах или
документах. Критерий успеха проверки — «команда завершилась с exit code 0 без
неожиданных failures/errors», а не совпадение с записанным числом.

Точные **контрактные** значения разрешены и иногда обязательны: `schema_version`,
budget cap, timeout, количество обязательных artifacts, лимиты провайдеров.

Измерения на HEAD `fe2df5b`, 2026-07-30, дерево чистое:

- полный offline suite: 1441 теста, около 245 секунд, 4 failures и 3 errors;
- `tests.test_voice_profile_resolution`: 8 тестов, 1 failure и 3 errors;
- `tests.test_autonomous_completion_pipeline`: 14 тестов, 3 failures;
- кандидат `fast`-режима без десяти render-тяжёлых модулей: около 1350 тестов,
  около 34 секунд;
- канонический CLI: `--help`, `capabilities --json`, `applications list` —
  примерно по одной секунде каждая;
- сохранённая калибровка live-eval: 3 сцены, 6 кандидатов, 12 кадров;
  индикативное измерение, **не** production evidence.

Измерение на проверенном исходном HEAD
`84bdd8b4f64c7adaf7582bdb39b15b18163253fb`, 2026-08-01, tracked-дерево
чистое:

- `.\venv\Scripts\python.exe -B -m unittest discover -s tests -p
  "test_*.py"` — 1441 тест, 231.839 секунды, exit code 0; failures: 0,
  errors: 0, skips: 0. Прогон выполнен offline; provider search/download,
  Vision, TTS, платные API-вызовы и реальный пользовательский render не
  выполнялись. Число тестов и длительность — измерение, не норматив.

## Execution protocol

1. Разрешённые зоны каждого шага неявно включают этот файл только для
   обновления checkpoint, статуса, фактических проверок и новых evidence.
2. Один bounded slice — один commit. Commit message содержит trailer
   `Plan-Step: <ID>`; Git log является авторитетом для hash.
3. Собственный hash невозможно записать внутри того же commit без
   самоссылочного amend-цикла. Поэтому поле `commit` может заполняться
   последующим plan-only уточнением, но его отсутствие не делает проверенный
   slice незавершённым.
4. Verification-only checkpoint может иметь plan-only commit с измерением и
   указанием **проверенного исходного HEAD**. Последующий docs-only commit не
   выдаётся за проверенный production HEAD.
5. Если один шаг требует нескольких независимых изменений или затрагивает
   больше одной ownership/behavior boundary, он делится на под-slices до
   реализации. Заголовок-этап закрывается только после всех его под-slices.
6. После каждого commit повторяются `git status --short --branch`,
   `git diff --check` и проверки, указанные для slice. Сеть и платные действия
   не считаются проверкой без отдельного owner approval.
7. Targeted tests выполняются после каждого behavior/code slice. Full offline
   suite не запускается автоматически после локального leaf-изменения.
8. Full offline suite обязателен на границе shared contract, persisted schema,
   paths/package root, provider registry, compatibility retirement и при
   закрытии крупного этапа, который объединяет несколько product slices.
9. Если этап состоит из contract-foundation и нескольких adapters, `full`
   выполняется после contract slice и один раз при закрытии семейства; каждый
   adapter между ними проверяется targeted tests.
10. Docs-only и report-only slices не требуют `full`, если не меняют test
    discovery, runner или production contract. Для них обязательны собственные
    QA/tests и `git diff --check`.
11. **Capability owner gate — обязателен, глобальный inventory — нет.** Перед
    изменением конкретной capability доказываются: canonical owner, фактические
    callers, persisted contracts, duplicate implementations, релевантные tests и
    границы legacy/replacement. Это правило класса `[HARD]`. Оно **заменяет**
    прежнее требование закрыть весь PLAN-1 до любого production-изменения:
    доказывается область, которую меняешь, а не весь репозиторий.
12. **Detail policy.** Подробно описывается только `active` шаг и ближайшие
    один-два следующих. `completed` сворачивается до статуса, commit,
    измеримого результата и фактических проверок. `blocked` держится в виде ID,
    зависимостей, allowed/prohibited zones, gates, verification и rollback.
    Развёрнутые описания PLAN-9…PLAN-15 сворачиваются в момент PLAN-8, когда
    у продуктовых подробностей появится собственный владелец
    `PRODUCT_PLAN.md`, а не раньше: до этого свёртка потеряла бы
    owner-approved решения. Этот файл не превращается во второй Master Plan.

## Execution table

Формат каждого шага одинаков. `commit` заполняется только фактическим hash
после выполнения; заранее hash не придумывается — источником является Git.

### Критический путь (ревизия 2.1)

Принцип владельца: **minimum strong foundation → product slice → feedback →
следующий foundation только если он реально нужен.** Не governance-first и не
product-at-any-cost. Product-слайс не ждёт идеального репозитория, но перед
изменением каждой capability агент обязан доказать её настоящего owner.

**До первого product fix — ровно четыре шага плюс два product-слайса:**

```
PLAN-1D-routing
  → PLAN-2 → PLAN-3 → PLAN-4
  → ► PLAN-9B-0 (characterization) → PLAN-9B-1 (provider-language foundation) ◄
```

Почему остаётся каждый из четырёх — по одной строке:

| Blocker | Почему до первого production fix |
|---|---|
| **PLAN-1D-routing** | Без него новый агент, буквально исполнив `AGENTS.md`, уходит в historical master plan и начинает не ту работу. |
| **PLAN-2** | Красный `test_voice_profile_resolution` не даёт различить «сломал я» и «было сломано» в радиусе изменения. |
| **PLAN-3** | То же для `test_autonomous_completion_pipeline` — модуля, который потом меняет PLAN-9A. |
| **PLAN-4** | Без зелёного воспроизводимого baseline targeted-прогон после query-изменения недоказуем. |

**Параллельно, не блокирует первый product fix** (стартует после зелёного
PLAN-4; PLAN-1C′ — сразу):

```
PLAN-5                        · uniform test runner (UX/reproducibility)
PLAN-6A → PLAN-6D → PLAN-6E   · governance / scope control / independent reviewer
PLAN-6B · PLAN-6C · PLAN-7 · PLAN-8 · инкрементальный перевод прозы (OD-5)
PLAN-L1 → L2 → L3 → L4        · retire legacy content stack после PLAN-L0
PLAN-1A · PLAN-1B · PLAN-1C′  · capability owner gates
```

**Дальше — по risk boundary, а не по линейной цепочке:**

Граф ниже нормализован по фактическим зависимостям detailed sections; он не
является одной линейной цепочкой и новых рёбер не вводит.

```
основная продуктовая последовательность:
  PLAN-9B-0 → PLAN-9B-1 → PLAN-9B-5a → PLAN-9B-4
  → PLAN-L0 → PLAN-9B-PRODUCER
  → [stabilization gate: PLAN-STAB-1…7 + stabilization review] → PLAN-9B-2

  PLAN-9B-3   — отдельный cleanup/destructive path после PLAN-9B-2
  PLAN-9B-5b  — отдельный destructive retirement path после миграции
                capability/callers и своих gates
  Ни PLAN-9B-3, ни PLAN-9B-5b prerequisite PLAN-9A не являются.

две сходящиеся ветки:
  PLAN-9B-2 + PLAN-1C′ + PLAN-6E → PLAN-9A → PLAN-10A → PLAN-10B → PLAN-10C
  PLAN-1C′ + PLAN-6E             → PLAN-9C → PLAN-9D

PLAN-9E   требует PLAN-9D + PLAN-10C + owner approval
PLAN-10D  после PLAN-10C
PLAN-11   после PLAN-9E + PLAN-10C
затем PLAN-12* → PLAN-13* → PLAN-14* → PLAN-15
```

### Risk-based governance model (ревизия 2.1)

Blocker остаётся только если он защищает **конкретную** risk boundary, которую
пересекает **конкретный** слайс. «Стоял в плане» причиной не является (OD-26).

| Слайс | Роль в ревизии 2.1 | Обоснование одной строкой |
|---|---|---|
| **PLAN-5** | **PARALLEL для всех под-слайсов PLAN-9B** | targeted / full / smoke исполнимы **сегодня** существующими командами (PLAN-4 и CI); PLAN-5 улучшает uniform runner UX и воспроизводимость формулировки, но техническим blocker product fixes не является |
| **PLAN-6A** | **PARALLEL относительно PLAN-9B** | Agent Autonomy Model уже действует из текста этого плана; зависимость **6A → 6D — ordering convention, а не техническая необходимость** |
| **PLAN-6D** | **BLOCKER первого multi-owner implementation slice** | `check_task_scope` защищает от выхода diff за allowed zones; у 9B-0/9B-1 allowlist тривиален, первый multi-owner diff — PLAN-9B-2 |
| **PLAN-6E** | **BLOCKER первого destructive retirement / high-risk shared-contract slice** | reviewer обязан существовать до первого удаления реализации, у которой есть callers (PLAN-9B-2, 9B-3, 9B-5b) |
| **PLAN-1C′** | **прямая зависимость от PLAN-6E снята** | docs-only ownership inventory, пишущий в `CLEANUP_REGISTRY.md`, не требует существования reviewer-skill |
| **PLAN-9A** | **явно требует PLAN-6E** плюс PLAN-9B-2 и PLAN-1C′ | persisted-state boundary |
| **PLAN-9C** | **явно требует PLAN-6E** плюс PLAN-1C′ | semantic decision boundary |

**Почему 9A/9C требуют 6E явно, а не транзитивно.** Через PLAN-9B-2 зависимость
существует и без записи, но транзитивные гарантии ломаются при следующем
reorder. Это **не** ослабление safety, а перенос gate на фактическую risk
boundary.

### Risk-boundary таблица safety gates

Заменяет одну линейную цепочку блокеров и делает явным, что защищает каждый gate.

| Пересекаемая boundary | Обязательные gates | Первый слайс, который её пересекает |
|---|---|---|
| локальное поведение, targeted tests, ноль persisted/public/paid/destructive | 1D, 2, 3, 4 | **PLAN-9B-0, PLAN-9B-1** |
| public CLI / input mode | + **owner approval** (`smoke` исполним существующей командой) | **PLAN-9B-5a** |
| наблюдаемое поведение `strict` | + **owner approval** | PLAN-9B-4 |
| значения существующих persisted visual-plan полей без новой schema/layout | + **OD-P-1** + characterization tolerant round-trip | **PLAN-9B-PRODUCER** |
| несколько owners в одном diff | + **PLAN-6D** (`check_task_scope`) | PLAN-9B-2 |
| destructive retirement реализации с callers | + **PLAN-6E** + reversible retirement (annotated tag + `git bundle` + строка `Retired`) | PLAN-9B-2, PLAN-9B-3, PLAN-9B-5b |
| persisted bytes / schema / layout | + tolerant reader + **owner approval** (approval PLAN-9A **не переносится**) + PLAN-6E | PLAN-9A |
| semantic / Vision decision path | + **PLAN-1C′** + **PLAN-6E** | PLAN-9C |
| network / model / paid операция | + **owner approval на конкретное действие** + PLAN-6E | model-assisted вариант PLAN-9B-PRODUCER, PLAN-9E |
| runtime / user data move | + `Preserved runtime corpus` + проверенный абсолютный путь + owner approval | PLAN-14D/14E |

**Что осознанно не оптимизировано.** Путь не сокращался ради меньшего числа
этапов: PLAN-4 сохранён, хотя он «всего лишь измерение»; PLAN-6E сохранён как
blocker первого destructive слайса. Минимизированы только blockers без
конкретной защищаемой boundary.

**Что изменилось относительно ревизии 2.** Первым product-слайсом становится
`PLAN-9B-0/9B-1`, а не `PLAN-9A`: best-so-far persistence бессмысленна, пока
система не получает provider-ready кандидатов (OD-15). В основной **product
order** перевёрнуто одно ключевое ребро: `9A → 9B` становится `9B → 9A`.
Governance dependencies и gates при этом **отдельно перераспределены по
risk-based model**: прямая `1C′ → 6E` снята, `9A → 6E` и `9C → 6E` записаны
явно, `PLAN-5` и `PLAN-6A` стали parallel относительно 9B, 6D/6E переведены на
свои risk boundaries, а PLAN-9B декомпозирован. `PLAN-5`, `PLAN-6A`, `PLAN-6D`,
`PLAN-6E` и `PLAN-1C′` **не удалены**.

PLAN-9B-1 становится первым слайсом, меняющим production-код в продуктовой
ветке; PLAN-L2/L3/L4 меняют production-код независимо, в ретайр-ветке работ, и
на поведение активного `content_creator` не влияют.

Независимые под-slices могут меняться местами только когда их зависимости,
allowed zones и owner approvals не пересекаются; изменение порядка
фиксируется здесь до работы, а не задним числом.

### POST-AUDIT STABILIZATION PROGRAM (PLAN-STAB-*)

- **owner decision date:** 2026-08-05.
- **audit baseline:** clean HEAD `e4cad2a` (read-only AI-practices audit,
  переданный владельцем). Аудит в репозиторий не копируется: здесь остаются
  только executable contracts и disposition. Severity сохраняется по
  фактическому user/security/rights impact и не повышается ради маршрутизации.
- **цель:** подтверждённые audit gaps получают исполняемых owners раньше
  следующего product slice, но не реализуются одним большим diff.
- **чем это не является:** отменой Visual Planning work, новым диагностическим
  этапом, вторым планом и разрешением начать любой из слайсов ниже без
  отдельного owner-issued implementation prompt.

Owner decisions программы:

| # | Решение |
|---|---|
| **OD-S-1** | `PLAN-9B-2` **deferred** за stabilization gate. Это не отмена: статус остаётся pending / not started, acceptance criteria не менялись |
| **OD-S-2** | Каждый PLAN-STAB-слайс — bounded: один canonical owner, один commit, targeted tests, explicit scope, независимый immutable-commit review, отдельный repair/re-review при findings |
| **OD-S-3** | Обязательный блокирующий набор до возврата к `PLAN-9B-2` — PLAN-STAB-1…7 плюс отдельный stabilization review |
| **OD-S-4** | Остальные подтверждённые MAJOR findings попадают в план, но индивидуально `PLAN-9B-2` не блокируют; выполняются после gate либо параллельно при непересекающихся owners |
| **OD-S-5** | Git backup — **completed manual owner action**: private remote существует, `governance-reset` и `master` отправлены, `governance-reset` — default branch. Задача «создать remote» как pending не создаётся |
| **OD-S-6** | Legacy findings не дублируются — см. «No-action и уже покрытые findings» |
| **OD-S-7** | `COMMANDS.md` **удаляется**, а не сокращается; replacement command document запрещён. Контракт PLAN-7 скорректирован ниже |
| **OD-S-8** | Docs freshness не чинится заменой даты: нужен Git-aware contract (PLAN-STAB-8) |
| **OD-S-9** | Не каждый audit finding является BLOCKER; routing не меняет severity |

**Общие требования ко всем PLAN-STAB-слайсам** (не повторяются в каждом):
один bounded commit с trailer `Plan-Step: <ID>`; production-код вне
названного canonical owner — prohibited zone; `docs/current/` входит в allowed
zone только для checkpoint/status/evidence после фактического завершения;
характеризация до изменения наблюдаемого поведения; сеть, provider/model API,
download, Vision, TTS, paid calls и реальный render не выполняются без
отдельного owner approval на конкретное действие; **rollback** — revert одного
commit без миграций данных; **independent review** — обязательный read-only
review одного immutable commit по `skills/review-change/SKILL.md`, с отдельным
repair/re-review при findings.

**Blocking gate: что должно быть закрыто до возврата к PLAN-9B-2.**

1. PLAN-STAB-1 completed and independently accepted — **satisfied**: commit
   `f0b69db`, independent review verdict ACCEPT WITH MINOR, pushed;
2. PLAN-STAB-2 completed and independently accepted — **satisfied**: commit
   `0eea5be`, independent review verdict ACCEPT, pushed;
3. PLAN-STAB-3 completed and independently accepted — **satisfied**: commit
   `9222519`, independent review verdict ACCEPT WITH MINOR, pushed;
4. PLAN-STAB-4 completed and independently accepted — **satisfied**: commit
   `0947e51`, independent review verdict ACCEPT WITH MINOR, pushed; два
   findings зафиксированы как non-blocking residual evidence (см. раздел
   PLAN-STAB-4) и не исправлены этим слайсом;
5. PLAN-STAB-5 completed and independently accepted — **satisfied**:
   единственный commit слайса (trailer `Plan-Step: PLAN-STAB-5`), independent
   review verdict ACCEPT (findings: нет), GitHub Actions run `31084873522` —
   offline suite зелёный (1646 tests, `OK (skipped=6)`, failures=0, errors=0),
   CI headSha == HEAD == `origin/governance-reset`, worktree clean;
6. PLAN-STAB-6 completed and independently accepted — **satisfied**: repair
   commit `b0a3547` closed review findings F1-F5, independent re-review
   verdict ACCEPT WITH MINOR (blocking findings: 0), GitHub Actions run
   `31147454618` (headSha `49385dd`) — offline suite зелёный (1749 tests OK,
   failures=0, errors=0), HEAD == `origin/governance-reset`, worktree clean;
7. PLAN-STAB-7 — три отдельных, не взаимозаменяемых условия: (a) factual
   routing repair, выполненный слайсом PLAN-STAB-0 — completed; (b) сам
   PLAN-STAB-7 (checker extension + integrity tests) — implementation
   completed 2026-08-06, integrity tests существуют
   (`tests/test_docs_routing_and_freshness.py`) и зелёные; (c) independent
   review этого commit — выполнен: initial verdict ACCEPT WITH MINOR (commit
   `42fa741`, CI run `31101208366`, 1693 tests OK), repair commit `8357402`
   закрыл все четыре finding F1-F4, repair re-review verdict ACCEPT WITH
   MINOR с blocking findings 0 (CI run `31110155685`, 1702 tests OK) —
   **satisfied**: (a), (b) и (c) выполнены;
8. отдельный **stabilization review** подтверждает четыре свойства:
   user-output preservation · offline/paid fail-closed behavior · rights
   safety · однозначный current routing — **satisfied**: bounded owner-driven
   stabilization review результатов PLAN-STAB-1..9 завершён **2026-08-07**
   read-only (без правок, commit и push), final verdict **CLEAR TO PROCEED TO
   PLAN-9B-2**, blocking findings **0**, все четыре свойства подтверждены,
   предварительный архитектурный repair перед PLAN-9B-2 не требуется;
   targeted evidence — `tools.qa.check_agent_docs` exit 0,
   permission/routing/governance tests 140 OK, rights/network cross-contract
   tests 78 OK, closure CI run `31149780652` (headSha
   `2186b20c5592a264ab6d100c44eaa6dd664aae91`) — governance step success,
   full offline suite 1749 tests OK, failures=0, errors=0.

**Утверждённый активный execution route (owner decision 2026-08-06).** После
закрытия PLAN-STAB-5, PLAN-STAB-9, PLAN-STAB-7 + PLAN-STAB-8, **PLAN-STAB-6**
(closed 2026-08-07) и завершённого **stabilization review** (2026-08-07,
verdict CLEAR TO PROCEED TO PLAN-9B-2) открытых пунктов blocking gate не
осталось: пункты 1–8 **satisfied**, stabilization gate пройден. У review не
было собственного PLAN-ID, и нового PLAN-ID он не создал; единственный
оставшийся prerequisite перед PLAN-9B-2 — отдельный owner-issued
implementation prompt (детали — раздел «Current checkpoint»
выше). Это owner-prioritized порядок выполнения, а не blocking dependency:
PLAN-STAB-9 и PLAN-STAB-8 остаются non-blocking для PLAN-9B-2 и не входят в
blocking gate задним числом, а содержание и нумерация пунктов 5–8 blocking
gate этим решением не менялись.

**Non-blocking follow-up.** PLAN-STAB-9…PLAN-STAB-17 находятся в обязательном
stabilization backlog, но индивидуально `PLAN-9B-2` не блокируют.
PLAN-STAB-8 closed 2026-08-06 (non-blocking, см. выше). PLAN-7 желательно
завершить до возврата; он может идти параллельно, если не пересекается с
production safety owners.

**Accepted manual owner actions** (новыми code slices не становятся):
Git backup (OD-S-5, выполнен); изменения `.claude/settings.local.json`, который
намеренно gitignored и остаётся под контролем владельца (PLAN-STAB-6, часть B).

**No-action и уже покрытые findings.** Новый слайс не создаётся:

| Finding | Disposition |
|---|---|
| legacy `src/video_renderer.py` удаляет output до успеха | уже **PLAN-L3** (удаляет root `src/`-модули кроме `media_library.py`/`utils.py`); production callers — legacy `size_comparison_engine` и root `pipeline.py` через compatibility patch-point `legacy_pipeline.workflow` |
| legacy asset/download stack | уже **PLAN-L0 → PLAN-L4** |
| root compatibility shims (`pipeline.py`, `apps/youtube_pipeline/`, `scripts/`, `legacy/`) | существующие retirement-слайсы **PLAN-L3/PLAN-L4** |
| отсутствие MCP | no action |
| недостижимые Git blobs | optional maintenance, не product action |
| `refs/codex/**` | no product action |
| два render stacks (FFmpeg и MoviePy Story Card) | автоматически не объединяются; owner направления — OD-M-4/OD-M-8 и unscheduled `MOTION-CS1/CS2` после отдельного product/format audit |
| размер execution plan | уже **PLAN-8** + правило 12 Execution protocol |
| Git backup | completed manual action (OD-S-5) |

**Порядок возврата к PLAN-9B-2.** Закрытый blocking gate (**выполнен**) →
отдельный stabilization review с положительным verdict (**выполнен
2026-08-07**, CLEAR TO PROCEED TO PLAN-9B-2, blocking findings 0) → отдельный
owner-issued implementation prompt для PLAN-9B-2 (**остаётся обязательным**).
Ни закрытие отдельного PLAN-STAB-слайса, ни этот amendment, ни завершённый
stabilization review, ни его docs-only recording разрешением начать
PLAN-9B-2 не являются.

#### PLAN-STAB-0 — post-audit stabilization plan amendment

- **status:** completed · **completed:** 2026-08-05 · **commit:** Git log —
  trailer `Plan-Step: PLAN-STAB-0` (собственный hash внутри того же commit не
  записывается, см. Execution protocol, пункт 3).
- **blocking для PLAN-9B-2:** нет — это сам owner-decision слайс, а не safety
  fix · **зависимости:** —.
- **цель:** канонизировать owner decisions последнего read-only AI-practices
  audit; создать PLAN-STAB-1…17; исправить current routing; отложить
  PLAN-9B-2 за stabilization gate.
- **user impact:** косвенный — подтверждённые safety findings получают
  исполняемых owners и однозначный порядок, а новый агент получает ровно один
  current checkpoint.
- **canonical owner:** `docs/current/PROJECT_EXECUTION_PLAN.md`.
- **changed zones:** current execution plan и его routing mirrors
  (`START_HERE.md`, `CURRENT_STATE.md`, `SYSTEM_MAP.md`).
- **prohibited zones (соблюдены):** production-код, tests, tools, README,
  `COMMANDS.md`, skills, contracts, settings, registry, schemas, configs,
  manifests, GitHub workflow.
- **измеримый результат:** PLAN-STAB-1…17 определены по одному разу и
  разрешаются; blocking gate и no-action disposition записаны; единственный
  current checkpoint — PLAN-STAB-1.
- **implementation safety slices этим шагом не начинались:** PLAN-STAB-1…6 и
  PLAN-STAB-8…17 остаются pending / not started. Для PLAN-STAB-7 этим шагом
  выполнен только factual routing repair в current docs; его integrity checker и
  остальная implementation не начинались, и completed PLAN-STAB-7 не объявляется.
  PLAN-9B-2 остаётся pending / not started и deferred.
- **фактические проверки:** docs QA, `tests.test_check_agent_docs`,
  `tests.test_stage2_agent_onboarding`, `check_task_scope` по exact allowed
  paths и `git diff --check` — exit code 0. Сеть, providers, download, Vision,
  TTS, paid API и render не выполнялись.
- **rollback:** revert одного commit.

#### PLAN-STAB-1 — atomic final-output preservation

- **status:** completed · **completed:** 2026-08-05 · **commit:** Git log —
  trailer `Plan-Step: PLAN-STAB-1` · **blocking для PLAN-9B-2:** пункт 1 gate
  satisfied — independent review выполнен, verdict ACCEPT WITH MINOR, commit
  pushed; overall blocking gate (пункты 4–8) остаётся открытым ·
  **зависимости:** —.
- **цель:** новый финальный MP4 создаётся отдельно, валидируется и только затем
  заменяет предыдущий результат.
- **user impact:** прерванный или неудачный повторный render перестаёт
  уничтожать уже готовое видео пользователя.
- **canonical owner:** `src/news/final_renderer.py`.
- **allowed zones:** `src/news/final_renderer.py` и его owning test-модули.
- **prohibited zones:** `src/news/pipeline.py` и stage orchestration; resume
  semantics; второй renderer; новый artifact, manifest, layout или public flag;
  изменение production render contracts/layout без отдельного owner decision.
- **success criteria:** прежний final output переживает любой сбой render;
  temp-файл лежит на той же файловой системе, что и цель; валидация выполняется
  **до** promotion; promotion атомарный — `os.replace` либо доказанный
  эквивалент; удаляется только temporary output.
- **required tests:** strict и draft режимы; injected failure оставляет hash
  существующего output неизменным; успешный путь заменяет output ровно один
  раз; temporary файлы не остаются после успеха и после сбоя.
- **не входит:** resume orchestration — это PLAN-STAB-2.
- **фактический результат:** `render_final_video` пишет мастер во временный
  `.<имя>.partial.mp4` в той же директории, проверяет его существующим
  `src.assets.frame_sampling.ffprobe_media_info` (тем же probe owner, через
  который повышает нарратив `src.audio.audio_assembler`) и только затем
  выполняет `os.replace`. Временный файл текущей попытки удаляется best-effort
  и не маскирует исходную ошибку. Второй renderer, второй validator, новый
  backup-механизм и правка resume/persisted contracts не создавались; public
  сигнатура и render manifest не менялись.
- **фактические проверки:** новый targeted модуль
  `tests.test_final_renderer_atomic_output` — 10 тестов, все падают на
  неизменённом HEAD `389e1c2`; targeted radius
  (`test_final_renderer_atomic_output`, `test_final_renderer_end_tail`,
  `test_news_to_short_renderer`, `test_autonomous_completion_core`) — 53 теста
  за 57.358 секунды, exit code 0; полный offline suite — 1571 тест за 326.965
  секунды, exit code 0; docs QA — exit code 0. Числа и длительности являются
  измерениями, не нормативами. Сеть, provider/model API, download, Vision, TTS
  и paid calls не выполнялись.
- **rollback / review:** по общим требованиям программы.

#### PLAN-STAB-2 — final-render resume/idempotency guard

- **status:** completed · **completed:** 2026-08-05 · **commit:** Git log —
  trailer `Plan-Step: PLAN-STAB-2` · **blocking для PLAN-9B-2:** пункт 2 gate
  satisfied — independent review выполнен, verdict ACCEPT, commit pushed;
  overall blocking gate (пункты 4–8) остаётся открытым ·
  **зависимости:** PLAN-STAB-1 (completed).
- **цель:** обычный `resume` не перезапускает уже успешно завершённый
  `final_render` без явного force/owner intent.
- **user impact:** продолжение проекта перестаёт молча переснимать готовый
  финальный ролик и тратить время пользователя.
- **canonical owner:** `src/news/pipeline.py` (stage guard ADR 0006).
- **allowed zones:** `src/news/pipeline.py`, минимально необходимый вызывающий
  canonical workflow, owning test-модули.
- **prohibited zones:** порядок стадий; состав `NEWS_TO_SHORT_STAGES`; renderer
  internals; persisted schema; новый public flag без owner approval.
- **success criteria:** characterization фиксирует текущее поведение до правки;
  completed-stage guard действует и на explicit `stage=` path; explicit force
  по-прежнему пересобирает; отсутствующий или непригодный prior output
  запускает render; ранее провалившийся output не считается completed.
- **required tests:** normal resume · force · missing output · failed prior
  output · batch-режим не регрессирует.
- **фактический результат:** `run_news_to_short_job`'s completed-stage skip
  (`src/news/pipeline.py`) применялся только когда вызывающий не указывал
  явный `stage=`; production render/export фаза
  (`FullscreenVoiceoverUseCase._render_and_export`) всегда вызывает
  `run_news_to_short_job(..., stage="final_render")` без `resume`/`force_stage`,
  поэтому каждый resume безусловно перезапускал `final_render`. Skip-условие
  расширено ровно на `stage_name == "final_render"`, не затрагивая explicit-stage
  диспетчеризацию voice/subtitles/preview_render/quality_check/export и не
  меняя `NEWS_TO_SHORT_STAGES`, persisted schema или renderer. Существующий
  `--force-stage` → `ExecutionFlags.force_stage` контракт довязан в тот же
  `stage="final_render"` вызов, поэтому явный force по-прежнему пересобирает
  именно final_render. Missing/invalid artifact продолжает обрабатываться уже
  действующим `NewsProjectStore.is_stage_completed`/`validate_stage_output`
  (ADR 0006) без нового механизма. `src/news/final_renderer.py` не менялся.
- **фактические проверки:** новый класс
  `tests.test_news_stage_idempotency.FinalRenderExplicitStageDispatchTests` —
  5 тестов (completed+valid skip, force reexecutes, missing-artifact
  reexecutes, not-yet-completed still executes, forced failure not recorded
  completed) плюс новый wiring-тест
  `test_force_stage_flows_from_request_to_the_final_render_resume_call` в
  `tests.test_content_creation_service`; targeted radius (idempotency,
  pipeline, renderer, delivery, autonomous completion, manual asset
  replacement, atomic output, end-tail, content-creation service, fullscreen
  boundary, voice adapter, subtitle integration, scene timing) — 116 тестов за
  166.565 секунды, exit code 0; полный offline suite — 1577 тестов за
  317.742 секунды, exit code 0; docs QA — exit code 0. Числа и длительности
  являются измерениями, не нормативами. Сеть, provider/model API, download,
  Vision, TTS и paid calls не выполнялись.
- **rollback / review:** по общим требованиям программы.

#### PLAN-STAB-3 — offline test guard и изоляция test credentials

- **status:** completed · **completed:** 2026-08-05 · **commit:** Git log —
  trailer `Plan-Step: PLAN-STAB-3` · **blocking для PLAN-9B-2:** пункт 3 gate
  satisfied — independent review выполнен, verdict ACCEPT WITH MINOR, commit
  pushed; overall blocking gate (пункты 4–8) остаётся открытым ·
  **зависимости:** —.
- **цель:** network guard нельзя случайно оставить выключенным на остаток test
  process, а test-injected credentials нельзя заменить значениями из `.env`.
- **user impact:** offline-обещание проекта перестаёт зависеть от порядка
  запуска модулей; реальные ключи владельца не попадают в тестовый прогон.
- **canonical owner:** `tests/network_guard.py`; для credential-пути —
  `src/audio/tts/env.py`.
- **allowed zones:** `tests/network_guard.py`, test-модули со scoped
  exception, `src/audio/tts/env.py` и его owning tests.
- **prohibited zones:** production TTS/provider поведение вне загрузки env;
  чтение `.env` и реальных ключей тестами; второй guard-механизм; расширение
  guard на subprocess boundary (остаётся открытым вопросом PLAN-6B).
- **success criteria:** characterization фиксирует фактическое число uninstall
  paths (**измерение**, на baseline 2026-08-05 — 9 вызовов в трёх test modules;
  **не инвариант и не acceptance criterion**, число перепроверяется заново перед
  implementation); после scoped exception guard восстанавливается; module
  cleanup/context-manager contract явный; `load_dotenv(..., override=True)` не
  заменяет заранее заданный test key; отсутствие `.env` не меняет результат.
- **required tests:** guard активен в модуле, выполняемом после модуля со
  scoped exception; scoped exception восстанавливает guard при исключении;
  заранее заданный `ELEVENLABS_API_KEY` переживает загрузку env.
- **фактический результат:** 9 raw `install_network_guard()`/
  `uninstall_network_guard()` call sites (baseline measurement подтверждена)
  в трёх owning test-модулях (`tests/test_localization_voice_integration.py`,
  `tests/test_news_voice_adapter.py`, `tests/test_production_catalog_foundation.py`)
  безусловно снимали process-wide baseline guard, который `tests/__init__.py`
  устанавливает один раз при импорте пакета: любой такой `finally: uninstall_
  network_guard()` отключал защиту для всех тестов, выполняющихся после него в
  том же процессе. `tests/network_guard.py` получил `network_guard_scope()`
  context manager, который восстанавливает guard к состоянию **до входа** в
  scope (успех, исключение или уже-выключенный baseline) вместо безусловного
  uninstall; все 9 call sites переведены на него. Для credential-пути
  `src/audio/tts/env.py::load_elevenlabs_env` всегда вызывал
  `load_dotenv(env_path, override=True)`, включая пути, где api_key передаётся
  явно (`ElevenLabsProvider.__init__` вызывает `load_elevenlabs_env()`
  безусловно) — реальный `.env`, если он существует, заменял бы любой
  test-owned fake `ELEVENLABS_API_KEY` в `os.environ`. Добавлен sentinel
  `TEST_CREDENTIAL_ISOLATION_ENV_VAR`; `override` теперь `not
  _test_credentials_isolated()`, а `tests/__init__.py` устанавливает sentinel и
  fake `ELEVENLABS_API_KEY` до импорта любого test-модуля. Production
  `override=True` semantics вне test isolation не менялись; `src/config_resolver`,
  providers, TTS/Vision/renderer/rights/resume не менялись.
- **фактические проверки (2026-08-05, ветка `governance-reset`):** новые
  `tests.test_test_network_guard.NetworkGuardScopeTests` (5 тестов) и
  `tests.test_tts_env_credential_isolation` (7 тестов); targeted regression —
  `test_localization_voice_integration` + `test_news_voice_adapter` +
  `test_production_catalog_foundation` (72 теста) и TTS/dotenv/provider radius
  (`test_voice_workflow`, `test_config_resolver`, `test_documentary_visual_engine`,
  `test_narration_workflow`, `test_scene_voice_generator`,
  `test_provider_foundation_hardening`, `test_content_creation_service`,
  `test_news_to_short_assets`, 145 тестов) — exit code 0; docs QA — exit code 0;
  полный offline suite — 1589 тестов (1577 + 12 новых), exit code 0. Числа и
  длительности являются измерениями, не нормативами. Сеть, provider/model API,
  download, Vision, TTS, paid calls и реальный `.env` не читались и не
  выполнялись; тесты используют только синтетические временные `.env`-файлы.
- **rollback / review:** по общим требованиям программы.

#### PLAN-STAB-4 — fail-closed runtime network/paid boundary

- **status:** completed 2026-08-06 · **independent review:** выполнен,
  verdict **ACCEPT WITH MINOR** (commit `0947e51`; GitHub Actions run
  `31053545804`, job `offline-tests / unittest` — success, `Ran 1623 tests in
  329.132s`, `OK (skipped=6)`, failures=0, errors=0) · **blocking для
  PLAN-9B-2:** пункт 4 gate satisfied; overall blocking gate (пункты 5–8)
  остаётся открытым · **зависимости:** characterization PLAN-STAB-3
  (completed).
- **non-blocking residual findings review (не исправлены этим слайсом):**
  (1) `tests/test_runtime_network_boundary.py:324-329` —
  `test_preflight_denial_is_not_reported_as_ready_for_generation` содержит
  только `assertTrue(callable(prepare_final))`, тавтологический assertion
  вместо полной проверки denial → readiness; (2) `wizard_presentation.py`
  показывает неполную информационную сводку сетевых действий и не использует
  `required_network_actions()`. Оба зафиксированы как residual evidence по
  independent review; исправление — отдельный будущий слайс, не PLAN-STAB-4 и
  не PLAN-STAB-5.
- **цель:** единый runtime owner запрещает внешние и платные вызовы в offline
  или неодобренном режиме.
- **user impact:** случайный платный или сетевой вызов перестаёт быть возможен
  «по умолчанию»; отказ честный и объяснимый.
- **canonical owner:** определяется owner audit **до** реализации; второй guard
  на провайдера не создаётся.
- **обязательный owner audit до implementation:** ElevenLabs · OpenAI/Vision ·
  stock providers · downloads · будущие model calls.
- **allowed zones:** выбранный canonical boundary и его owning tests;
  минимальные call sites перечисленных путей.
- **prohibited zones:** дублирующий guard в каждом провайдере; новый
  provider contract; изменение provider selection; реальные сетевые вызовы в
  тестах.
- **success criteria:** один canonical boundary; approval явный и на конкретное
  действие; budget/cap там, где применимо; default fail-closed; **наличие API
  key не является approval**; поведение проверяется без реальной сети.
- **required tests:** offline-режим блокирует каждый класс вызова; явное
  approval пропускает ровно один класс; отсутствие approval при настроенном
  провайдере остаётся отказом.
- **фактический canonical owner (2026-08-06):** `src/runtime_network.py` —
  один модуль, один механизм. `ContextVar` со значением `DENY_ALL` делает
  default deny свойством конструкции, а не проверкой, которую можно забыть:
  `NetworkApproval` (frozen) хранит поимённый набор классов и метку источника,
  `network_approval_scope` восстанавливает предыдущее значение через token даже
  при исключении, `require_network` вызывается до первого socket/HTTP,
  неизвестное имя класса — ошибка, а не молчаливое разрешение.
  `NetworkApproval.to_dict()` отдаёт только имена классов и `granted_by`,
  поэтому ключ или токен не может попасть в manifests и approval artifacts.
  Второй guard на провайдера не создавался: все пять сетевых провайдеров ходят
  через общий `ProviderHttpClient` и не менялись.
- **фактически закрытые network families:** `provider_search` и
  `asset_download` — `src/assets/http_client.py` (`get_json` и
  `download_stream`, проверка до `_request` и до создания `.part`, в тексте
  отказа только host без query-параметров); `preview_download` —
  `src/assets/visual_preview.py` передаёт свой класс в тот же
  `download_stream`; `article_fetch` — `src/news/article_ingestor.py` до
  `requests.get`, отказ транслируется в существующий `ArticleIngestionError`
  с `reason="network_approval_required"`, который намеренно не входит в
  `_RETRYABLE_ARTICLE_REASONS`; `voice_preflight` —
  `src/audio/tts/elevenlabs_provider.py` в `preflight` и `list_voices`, причём
  отказ в `preflight` возвращает корректный план с классифицированной ошибкой,
  поэтому `ready_for_final_generation` остаётся False и traceback не возникает.
- **как пользователь даёт разрешение:** повторяемый `--allow-network <класс>`
  (`choices` из `NETWORK_ACTIONS`, wildcard-значения нет) проходит через общий
  `request_builder` в поле `network` запроса; Wizard задаёт явный вопрос
  `confirm_network_access`, перечисляя ровно те классы, которых требует именно
  этот прогон (`required_network_actions`). Оба входа заполняют одно и то же
  поле, поэтому parity выполняется по построению, а `create_content` —
  единственное место установки scope на оба шаблона.
- **явно принятые residual risks:** OpenAI Vision (`semantic_visual_openai.py`)
  в scope не входил и остаётся под существующей защитой —
  `config/semantic_visual.json` с `enabled:false`, `backend:"mock"`,
  `openai.enabled:false`, `allow_paid_vision:false` плюс `VisionBudgetGuard` с
  обязательной фразой подтверждения и budget cap. Legacy
  `pipeline.py --provider-diagnostics --live` и `pipeline.py --voice-action
  preflight/audition` идут через закрытые границы и потому становятся
  fail-closed без собственного approval-флага: это намеренное default-deny для
  путей вне канонического workflow, а не регрессия канонического CLI.
  Платный POST ElevenLabs (`synthesize`) остаётся под существующим
  каноническим paid-owner — hash-bound `VoiceApproval` на диске плюс gates в
  `narration_workflow` и `TTSProviderManager`; отдельного network approval он
  не требует. Информационная строка «Сетевые действия» в
  `wizard_presentation.py` перечисляет не все семейства — предсуществующее
  поведение, в scope PLAN-STAB-4 не входило.
- **фактические проверки (2026-08-06, ветка `governance-reset`):** новый
  `tests/test_runtime_network_boundary.py` — 34 теста, покрывающие default deny
  для каждого класса, keyless default-on провайдеров, article ingestion до
  HTTP, preview download отдельным классом, preflight без GET при настроенном
  ключе, paid approval без network approval, разрешение ровно одного класса,
  dry-run/prepare-only/resume/force-stage offline, отсутствие secrets в
  approval artifact и CLI ↔ Wizard parity. Обновлены owning tests
  `test_asset_foundation_http_download`, `test_voice_workflow` и
  `test_content_creation_wizard` (общий `ScriptedAdapter` также используется
  `test_project_naming_and_resume`): им выдаётся явный scope нужного класса,
  существующий `tests/network_guard.py` не ослаблялся. Полный offline suite —
  1623 теста (1589 + 34), exit code 0; docs QA — exit code 0;
  `git diff --check` — exit code 0. Числа являются измерениями, не нормативами.
  Сеть, provider/model API, download, Vision, TTS, paid calls и реальный `.env`
  не читались и не выполнялись.
- **rollback / review:** по общим требованиям программы.

#### PLAN-STAB-5 — C50 rights-review preservation

- **status:** completed 2026-08-06, independently reviewed, verdict **ACCEPT**
  (findings: нет) · **blocking для PLAN-9B-2:** да — пункт 5 blocking gate
  **satisfied** · **зависимости:** —.
- **реализованный инвариант:** требование ревью monotonic. Уже записанное
  `review_required=True` — вход политики, а не то, что она вправе снять; оно
  даёт причину `record_review_required`, обнуляет `allowed_for_render` и
  переводит статус в `blocked`. Учитываются все фактически присутствующие
  представления записи (корень, `license`, сохранённый `policy_decision`);
  одного `True` достаточно, отсутствующее представление разрешением не
  является. Снимает требование только подтверждённая per-asset
  `rights_declaration` через существующий `_manual_declaration_is_confirmed`.
- **owner decision 2026-08-06 — намеренный safety trade-off.** Происхождение
  требования политика не выясняет. Evidence: сохранённая запись не позволяет
  отличить флаг оператора от прошлого ответа самой политики — комбинация
  «`review_required=True` + чужой `policy_decision`» реально производится
  `media_library._propose_media_record` (`dict(item)` сохраняет `policy_decision`,
  ставит `review_required=True`) и персистится `migrate_media_library` мимо
  `_normalize_asset`, а manifest-ассет всегда несёт `policy_decision`. Принятая
  цена: policy re-evaluation, дозаполнение metadata, resume и rebuild сами по
  себе ревью не снимают. Измерено: единственный вариант, оставлявший
  repair-and-retry, оставлял shape «оператор флагует уже заблокированный ассет»
  fail-open; полный offline suite при выбранном правиле зелёный, ни один
  существующий тест на автоматическом снятии ревью не держался.
- **owner path:** ассет с ревью выходит из блокировки одним способом —
  подтверждённой `rights_declaration`. Это существующий контракт, новых полей,
  vocabulary, CLI и Wizard-шагов слайс не добавляет.
- **цель:** явный `review_required` и owner-review evidence не теряются при
  преобразовании records/candidates и не становятся `allowed` из-за другого
  fallback.
- **user impact:** ассет, помеченный человеком на ревью, не может молча попасть
  в готовое видео. Класс `[HARD]` rights correctness.
- **canonical owner:** `apply_policy_to_candidate` / `with_policy_decision`
  в `src/assets/license_policy.py`.
- **отношение к registry:** это **исполняемый owner finding C50**. Второй
  независимый owner C50 не создаётся; нормализация ссылки в
  `CLEANUP_REGISTRY.md` относится к PLAN-STAB-17, потому что registry не входит
  в allowed zone этого docs-only amendment.
- **allowed zones:** `src/assets/license_policy.py`, минимально необходимые
  rights call sites, owning tests.
- **prohibited zones:** копирование rights gate в legacy loaders; изменение
  `modes.blocking_reasons`; PLAN-10D architectural convergence; новая persisted
  schema.
- **success criteria:** точный C50 mapping зафиксирован; canonical rights
  vocabulary используется; author/user-owned evidence сохраняется; поведение
  local library определено явно; strict и draft gates согласованы; persisted
  совместимость сохранена.
- **required tests:** negative-тесты — explicit `review_required=True` не
  становится `allowed`; отсутствие evidence не даёт fallback-разрешения;
  старые persisted записи читаются без миграции.
- **фактические изменения:** canonical owner `src/assets/license_policy.py`
  (`RECORD_REVIEW_REQUIRED_REASON`, `_record_review_required`, одна причина в
  `evaluate_asset_policy`); два merge owner на той же live-цепочке —
  `rank_local_assets` в `src/news/asset_manifest_builder.py` переносит флаг
  записи в ranked item, `with_policy_decision` в
  `src/news/asset_provider_adapters.py` не теряет флаг, записанный рядом с
  лицензией; `tests/test_rights_review_preservation.py` (23 теста);
  `src/assets/README.md`. `config/license_policy.json`,
  `modes.blocking_reasons`, `ASSET_SCHEMA_VERSION`, CLI, Wizard и network
  boundary не менялись; миграция манифестов не требуется.
- **evidence:** targeted 23 OK; regression radius 204 OK; полный offline suite
  1646 tests OK; `check_agent_docs` — 0; `check_task_scope` с 8-файловым
  allowlist — OK; `git diff --check` — 0. Сеть, provider API, download, Vision,
  TTS, реальный render и `.env` не использовались. Числа — измерения, не
  нормативы. Independent review (отдельный чат) — verdict **ACCEPT**, findings:
  нет; GitHub Actions run `31084873522`, job `offline-tests / unittest` —
  success, `Ran 1646 tests in 273.522s`, `OK (skipped=6)`, failures=0,
  errors=0; CI headSha == `8226a28`; HEAD == `origin/governance-reset`,
  worktree clean.
- **residual risks:** `rank_local_assets` остаётся вторым нормализатором рядом
  с `media_library` (C40 / PLAN-10D); `AssetLicense.from_dict` по-прежнему
  выводит `review_required` из `allowed_for_render`, когда вложенная лицензия
  его не называет — закрыто на уровне merge owner, а не персистируемой модели;
  нормализация ссылки C50 в `CLEANUP_REGISTRY.md` относится к PLAN-STAB-17.
- **rollback / review:** по общим требованиям программы.

#### PLAN-STAB-6 — Claude permission hardening

- **status:** **closed 2026-08-07.** Implementation completed 2026-08-06;
  bounded repair commit `b0a3547` закрыл review findings F1–F5; independent
  re-review verdict **ACCEPT WITH MINOR** (blocking findings: 0); GitHub
  Actions run `31147454618` (headSha `49385dd`) зелёный — оба обязательных
  шага success, `Ran 1749 tests`, `OK (skipped=6)`, failures=0, errors=0 ·
  **blocking для PLAN-9B-2:** да — **satisfied**; пункт 6 gate **closed** ·
  **зависимости:** —.
- **цель:** минимизировать возможность агента читать secrets, обходить
  destructive Git rules, менять governance и коммитить широким wildcard.
- **user impact:** ошибка или сбой агента не превращается в потерю работы
  владельца и незамеченное изменение правил.
- **canonical owner (A, tracked):** `.claude/settings.json`.
- **canonical owner (B, local):** `.claude/settings.local.json` — намеренно
  gitignored, поэтому его правка **manual owner action**, а не code slice.
- **allowed zones:** `.claude/settings.json`; при возможности — tracked
  permission-contract checker и его tests.
- **prohibited zones:** production-код; правка gitignored local settings от
  имени агента; утверждение, что hooks сильнее permission system.
- **success criteria:** effective merged settings проверены; wildcard-грант
  `python -c`, `python -`, `git add *`, `git commit *` удалён или вынесен в
  manual cleanup list; защищены `AGENTS.md`, `CLAUDE.md`, `skills/**`,
  `.claude/**`, `tools/qa/**`; destructive Git matching не зависит от
  необязательных флагов.
- **required tests:** checker tracked permission contract там, где выполнимо;
  иначе — записанная воспроизводимая ручная проверка.
- **manual owner prerequisite (выполнен):** владелец вручную удалил из
  gitignored `.claude/settings.local.json` семь опасных grants —
  `Bash(git add *)`, `Bash(git commit *)`, `Bash(python -c ' *)`,
  `Bash(./venv/Scripts/python.exe -c ' *)`,
  `Bash(./venv/Scripts/python.exe -B -c ' *)`,
  `Bash(G:/Projects/AI-YouTube/venv/Scripts/python.exe -B -c ' *)`,
  `Bash(python -)`. Read-only precheck перед слайсом подтвердил **0**
  совпадений по всем семи; файл целиком не читался и не выводился. Агент
  local settings не правил — это canonical owner B и manual owner action.
- **выполнено (implementation 2026-08-06):**
  - **Versioned contract.** `.claude/settings.json` остаётся deny/ask-only:
    `permissions.allow` отсутствует полностью, top-level ключи — только
    `$schema` и `permissions`, поэтому secret values в versioned файл
    структурно не помещаются.
  - **Protected governance zones** требуют подтверждения на `Edit` и `Write`:
    `AGENTS.md`, `CLAUDE.md`, `skills/**`, `tools/qa/**`,
    `.github/workflows/**`, `docs/current/PROJECT_EXECUTION_PLAN.md`,
    `docs/archive/**`, `docs/handoff/**` и сам `.claude/settings.json`.
    `Read` не ограничивается: агент, который не может прочитать `AGENTS.md`,
    не может ему следовать. Широкое правило на `docs/current/**`
    намеренно не добавлено — обычные docs-only слайсы должны оставаться
    рабочими, а подтверждение на каждый current document кликалось бы не
    глядя и контролем не является.
  - **Project-local settings** закрыты агенту: `Read`, `Write` и `Edit` по
    `./.claude/settings.local.json` — в `deny`.
  - **Secret `.env.*`.** Добавлены точные имена `.env.local`,
    `.env.development(.local)`, `.env.production(.local)`,
    `.env.staging(.local)`, `.env.test(.local)`, `.env.bak`, `.env.backup`,
    `.env.old`, `.env.save` для Read/Write/Edit в корне и рекурсивно.
    Общий `./.env.*` **не** используется: механизма исключения в deny нет, а
    tracked `.env.example` — secret-free template, для которого PLAN-6D-1
    зафиксировал «0 deny matches». Owner decision 2026-08-06 сохранил это
    свойство; checker отдельно отвергает и blanket-pattern, и любое правило,
    накрывающее `.env.example`.
  - **Destructive Git разделён** (owner decision 2026-08-06). `deny` —
    необратимая порча работы владельца или истории: `reset --hard`, `clean`,
    force push, `filter-branch`, `reflog delete/expire`, `update-ref -d`,
    `gc --prune`. `ask` — восстановимое через index/reflog либо нужное самому
    владельцу: `checkout --`, `restore`, `rm`, `branch -D`,
    `worktree remove`. Цена ask-варианта записана честно: одного
    подтверждения достаточно, чтобы стереть незакоммиченную работу.
  - **Leading wildcard удалён — с осознанным ослаблением корзины.** Правило
    `Bash(*media-library migrate*--apply*)` находилось в **`deny`**; шесть
    заменяющих entrypoint prefixes `pipeline.py` находятся в **`ask`**
    (positional `media-library` → `migrate`; флаг `--apply` объявлен в
    `src/legacy_pipeline/cli.py:116`). Это намеренная смена
    `deny` → owner confirmation: прежнее правило опиралось на ведущий `*`,
    чья matcher semantics не установлена, поэтому оно давало запрет, на
    который нельзя было положиться; новое даёт подтверждение, на форму
    которого положиться можно. Эквивалентности здесь нет — одного
    подтверждения теперь достаточно.
    **Покрытие ограничено перечисленными формами.** Шесть prefixes — это
    `python`, `python -B`, `./venv/Scripts/python.exe`,
    `./venv/Scripts/python.exe -B`, `venv/Scripts/python.exe`,
    `venv/Scripts/python.exe -B`. Абсолютные пути (например
    `G:/Projects/AI-YouTube/venv/Scripts/python.exe`), backslash-написание
    `.\venv\Scripts\python.exe`, shell aliases, обёртки и произвольный
    интерпретатор **не покрываются вовсе** — это частный случай общего
    «Bash не защищён path-based правилами» ниже. Полное покрытие не
    заявляется, и media-library rules этим repair не менялись: изменение
    правил потребует нового evidence.
    **Фактическая защита `--apply` лежит в runtime-контракте, а не в
    permissions:** `src/media_library.py:289` бросает `PermissionError` без
    `confirm_apply=True`, а `:291` требует явные `output_path` и
    `backup_path`; CLI-флаг `--confirm-apply` объявлен в
    `src/legacy_pipeline/cli.py:121`. Именно он, а не permission rule,
    остаётся барьером для любого написания команды.
    Checker отвергает любое правило с ведущим `*`.
  - **Сеть и установка пакетов** переведены в `ask`: `curl`, `wget`,
    `Invoke-WebRequest`, `pip install`, `python -m pip install`, venv-форма,
    `npm install`, `npm ci`. `WebFetch`/`WebSearch` остаются `ask`. Локальные
    offline test-команды не затронуты.
  - **Recursive delete** дополнен `rm -fr`, `Remove-Item -Force -Recurse` и
    `Remove-Item -Recurse -Force`. `Bash(*)` и общий запрет shell не
    добавлялись.
  - **Validator.** `validate_claude_permissions` в
    `tools/qa/check_agent_docs.py` — тот же canonical owner, второй QA
    framework и отдельный executable checker не создавались. Существующий CI
    step `python -B -m tools.qa.check_agent_docs` покрывает контракт без
    второго workflow и второго step. Checker read-only, offline,
    детерминирован, **никогда не открывает** `settings.local.json` и смотрит
    только его Git-статус.
- **выполнено (repair 2026-08-06, findings F1–F5 independent review):**
  - **F1 — `.env.example` защищён позиционно, а не списком написаний.**
    Прежний checker отвергал только два перечисленных blanket-паттерна, из-за
    чего `Read(./.env*)` проходил и перекрывал tracked template. Теперь
    отвергается **любое** `Read`/`Write`/`Edit` deny-правило, которое по
    собственной консервативной модели checker'а может дотянуться до
    `.env.example` в корне или во вложенной директории. Модель описана честно:
    `**` пересекает `/`, `*` и `?` — нет; это **repository contract, а не
    доказательство runtime matcher'а**, и она намеренно щедра к тому, что
    правило «может» задеть. На реальном deny-списке — ноль false positives.
  - **F2 — media-library описан честно** (см. выше): корзина сменилась
    `deny` → `ask`, покрытие ограничено шестью написаниями, фактический
    барьер `--apply` — runtime `confirm_apply` contract. Правила не менялись.
  - **F3 — tracked governance под `.claude/`.** Добавлены
    `Edit`/`Write(./.claude/agents/**)`; вместе с существующим exact
    `./.claude/settings.json` это покрывает оба tracked-файла, включая
    reviewer adapter `.claude/agents/review-change.md`, который прежде
    оставался без подтверждения. Широкое `./.claude/**` **намеренно не
    использовано**: precedence между ним и exact deny на
    `settings.local.json` не доказан, а изобретать гарантию запрещено.
    Checker берёт список из `git ls-files -- .claude/`, поэтому новый tracked
    файл без правила — ошибка; `CLAUDE_GOVERNANCE_EXEMPT_PATHS` пуст и служит
    механизмом явного, обозреваемого исключения. Gitignored
    `settings.local.json` в `ls-files` не попадает, поэтому конфликта с его
    exact deny не возникает. `Read` остаётся открытым.
  - **F4 — минимальный контракт зафиксирован независимо.** Новый класс
    `MinimumContractPinnedIndependentlyTests` перечисляет **литерально** и
    **не импортирует** `PROTECTED_GOVERNANCE_PATHS`, `SECRET_ENV_NAMES`,
    `DESTRUCTIVE_GIT_DENY`, `DESTRUCTIVE_GIT_ASK`, `FORBIDDEN_BROAD_GRANTS`:
    десять protected zones × `Edit`/`Write`, требование к tracked
    `.claude/**`, точные sensitive `.env`-имена, оба destructive-Git набора,
    восемь forbidden grants, отсутствие `permissions.allow` и точные записи
    tracked `.gitignore`. Прежде одновременное удаление зоны из
    `settings.json` **и** из константы оставляло suite зелёным.
  - **F5 — источник ignore-правила теперь обязателен.** Checker требует, чтобы
    исключение находилось именно в **tracked `.gitignore`**: `.gitignore`
    обязан быть tracked, а источник, который Git приписывает исключению,
    обязан быть tracked `.gitignore`. `.git/info/exclude`, global
    `core.excludesFile` и user-level ignore доказательством больше не
    считаются — все они per-machine и оставляют CI и остальные клоны
    незащищёнными. `-c core.excludesFile=` сохранён; `--verbose --no-index`
    даёт источник, а строка-негация (`!.env.example`) намеренно **не**
    читается как исключение. Диагностика прямо называет требование tracked
    `.gitignore`.
  - **Sensitive `.env` в tracked `.gitignore`.** Добавлены тринадцать точных
    имён (`.env.local`, `.env.development(.local)`, `.env.production(.local)`,
    `.env.staging(.local)`, `.env.test(.local)`, `.env.bak`, `.env.backup`,
    `.env.old`, `.env.save`); существующий `.env` сохранён, общий `.env.*`
    не используется, `.env.example` остаётся tracked и не ignored. Checker
    проверяет каждое имя поимённо и отдельно требует, чтобы template не был
    ignored. Реальных secret-файлов не создавалось.
- **evidence:** `tests/test_claude_permission_contract.py` (47 tests OK):
  валидный контракт; отсутствие файла; malformed JSON; появившийся
  `permissions.allow`; каждый из восьми запрещённых broad grants; ведущий
  wildcard; правило не формы `Tool(pattern)`; каждая из десяти protected zones
  × `Edit`/`Write` по отдельности; покрытие zone через `deny` вместо `ask`;
  каждый tool local-settings deny; пропавшее env-правило; семь написаний
  deny-правила, дотягивающегося до `.env.example`; отсутствие false positive
  на реальных sensitive-правилах; перенос каждого destructive-Git правила
  между корзинами; непересечение двух Git-наборов; синтетический Git-репозиторий
  (tracked `.gitignore` / untracked `.gitignore` / отсутствующее правило /
  `.git/info/exclude` / global `excludesFile` / пропавшее env-имя / ignored
  template / негация / tracked local settings); tracked governance под
  `.claude/` (без подтверждения / с подтверждением / новый tracked файл /
  local settings не считается tracked governance); независимый литеральный
  минимум контракта; реальный репозиторий; неизменность worktree. Отдельно
  зафиксировано, что env-покрытие требует только Read/Write/Edit и ни одного
  `Bash(...)` правила — полная Bash-защита не заявляется.
  **Test effectiveness против pre-repair версии:** девять новых тестов
  прогнаны против модуля из `3cedff10` — каждый падает; литеральный минимум
  F4 отдельно отвергает сужение, сделанное одновременно в `settings.json` и в
  константе.
- **residual limitations (не закрыты этим слайсом):**
  - точная matcher wildcard semantics и precedence корзин эмпирически не
    доказаны; path-правила в `ask` — inference по грамматике файла, а не
    проверенное runtime-поведение. **Наблюдение слайса:** после записи новых
    `ask`-правил в той же сессии выполнялись `Edit` по `tools/qa/**` и по
    самому execution plan, и подтверждение не запрашивалось. Причина не
    установлена: settings, вероятно, читаются на старте сессии и mid-session
    не перечитываются, но вариант «path-правила в `ask` не применяются» этим
    наблюдением не исключён. Проверка требует нового сеанса и в этом слайсе
    не выполнялась — заявлять срабатывание правил нельзя. Versioned `allow`
    отсутствует, а local settings не содержат ни одного `Write`/`Edit`
    гранта, поэтому эти правила сегодня работают как declared intent и защита
    от будущего широкого local allow, а не как единственный барьер;
  - **Bash не защищён** path-based правилами: глобальные Git options
    (`git -c …`), shell aliases и произвольный интерпретатор остаются вне
    контракта. Абсолютная защита Bash не заявляется;
  - перечисление `.env.*` заведомо неполно: имя вне списка не покрыто. Маски
    внутри имени файла (`./.env.*.local`) не использованы — их синтаксис по
    фактическим settings не подтверждён, а изобретать его запрещено;
  - effective merged user/managed/local configuration лежит вне репозитория,
    различается по средам и **защищённой не объявляется**; checker проверяет
    только versioned contract;
  - модель паттернов checker'а (`_permission_pattern_regex`) — **repository
    contract, а не runtime proof**: она описывает, какие правила репозиторий
    считает опасными, и не утверждает, что Claude matcher разбирает их так же;
  - **CI для `3cedff10` и `b0a3547` зелёным не подтверждён — подтверждённый
    внешний GitHub Actions incident, а не test failure.** Implementation
    commit `3cedff10`: run `31123722270` дважды отменён до выдачи
    `windows-latest` runner (0 steps, 0 логов); ни один обязательный шаг не
    выполнялся. Repair commit `b0a3547`: push-triggered run вообще не был
    создан. Независимое подтверждение GitHub Status зафиксировало внешний
    infrastructure incident GitHub Actions 2026-08-06/07 (queued hosted jobs
    без runner, throttled webhook-triggered runs, часть push/pull_request
    events без workflow run вообще, часть потерянных trigger events без
    автоматического replay). Оба commit прошли local evidence на своём
    дереве (`3cedff10`: full offline suite `Ran 1729 tests, OK`; `b0a3547`:
    `1749 tests OK`, `tools.qa.check_agent_docs` exit 0) и независимый
    review; ни для `3cedff10`, ни для `b0a3547` CI success не заявляется.
    Docs-only retrigger commit `49385dd` после восстановления Actions получил
    зелёный CI (run `31147454618`, 1749 tests OK, failures=0, errors=0) —
    incident зафиксирован как **historical infrastructure evidence**, а не
    текущая незакрытая проблема; CI success для `3cedff10` и `b0a3547`
    по-прежнему не заявляется, заявляется только для `49385dd`.
- **rollback / review:** по общим требованиям программы. Implementation и
  repair шаг закрыты independent review (verdict ACCEPT WITH MINOR, blocking
  findings: 0) и зелёным CI (run `31147454618`, headSha `49385dd`, 1749 tests
  OK, failures=0, errors=0); шаг **closed**, пункт 6 blocking gate
  **satisfied**.

#### PLAN-STAB-7 — current-routing и reference integrity

- **status:** completed 2026-08-06 — implementation commit `42fa741`
  (совместный слайс с PLAN-STAB-8, trailer `Plan-Step: PLAN-STAB-7`), repair
  commit `8357402` закрыл все четыре finding F1-F4 независимого review без
  изменения контракта. Independent review verdict **ACCEPT WITH MINOR**,
  repair re-review verdict **ACCEPT WITH MINOR** (blocking findings: 0);
  GitHub Actions run `31101208366` (headSha `42fa741`) — offline suite
  зелёный (1693 tests OK); repair GitHub Actions run `31110155685` (headSha
  `8357402`) — offline suite зелёный (1702 tests OK); commits pushed. Factual
  routing repair в current docs был выполнен ранее слайсом PLAN-STAB-0 ·
  **blocking для PLAN-9B-2:** да — **satisfied**, пункт 7 blocking gate
  закрыт · **зависимости:** —.
- **цель:** current checkpoint, next action, mirrors и referenced IDs не могут
  молча разойтись.
- **user impact:** новый чат или агент получает ровно одно текущее задание, а
  не три конкурирующих.
- **canonical owner:** `tools/qa/check_agent_docs.py` (расширение существующего
  checker; второй QA framework не создаётся).
- **allowed zones:** `tools/qa/check_agent_docs.py`, его owning tests,
  `docs/current/` для checkpoint/evidence.
- **prohibited zones:** переписывание historical evidence и completed records;
  второй plan; изменение production-кода.
- **success criteria:** ровно один authoritative current checkpoint;
  `START_HERE.md`, `CURRENT_STATE.md`, `SYSTEM_MAP.md` и план согласованы;
  completed шаг не выглядит pending/current; PLAN- и registry-ссылки
  разрешаются; bullet-only слайс не может быть current checkpoint без
  собственного heading.
- **required tests:** duplicate/stale checkpoint statement — error; ссылка на
  несуществующий PLAN-ID — error; heading-less current checkpoint — error.
- **выполнено:** `validate_routing` в `tools/qa/check_agent_docs.py`.
  Authority — `current_checkpoint` в frontmatter активного плана. Проверяется:
  checkpoint имеет **собственный heading** (bullet-only шаг checkpoint быть не
  может); его `- **status:**` не начинается со слова `completed`;
  `next_exact_action` называет текущий checkpoint и ссылается только на
  определённые plan steps; каждый из трёх routing mirrors
  (`START_HERE.md`, `CURRENT_STATE.md`, `SYSTEM_MAP.md`) содержит хотя бы одно
  checkpoint-утверждение и ни одно из них не называет другой PLAN-ID.
  Сообщение об ошибке называет файл, строку, найденный и ожидаемый ID.
- **осознанная граница:** reference integrity ограничена routing-полями.
  Сплошная проверка «каждая PLAN-ID-ссылка имеет heading» дала бы ~33 ложных
  срабатывания: сабы вида `PLAN-12A…PLAN-14F` определяются жирными буллитами
  внутри родительских разделов, а `PLAN-ID` — обычное слово прозы. Для
  `next_exact_action` принимаются оба вида определений, для самого checkpoint —
  только heading.
- **evidence:** `tests/test_docs_routing_and_freshness.py`, класс
  `RoutingTests` (валидный route; heading-less checkpoint; расхождение каждого
  из трёх mirrors по отдельности; mirror без checkpoint-утверждения;
  `next_exact_action` на несуществующий шаг; `next_exact_action` без текущего
  checkpoint; completed шаг как checkpoint; pending-статус, лишь упоминающий
  слово completed, не считается completed) и `RepositoryRoutingAndFreshnessTests`
  на реальном репозитории.
- **rollback / review:** по общим требованиям программы.

#### PLAN-STAB-8 — Git-aware documentation freshness

- **status:** closed 2026-08-06 (тот же совместный commit, что и PLAN-STAB-7,
  `42fa741`, и та же repair commit `8357402`; собственного отдельного commit у
  слайса нет по решению владельца об одном координированном bounded slice).
  Independent review этого commit выполнен вместе с PLAN-STAB-7: verdict
  **ACCEPT WITH MINOR**, repair re-review verdict **ACCEPT WITH MINOR**
  (blocking findings: 0); GitHub Actions run `31101208366` и repair run
  `31110155685` зелёные · **blocking для PLAN-9B-2:** нет · **зависимости:** —.
- **цель:** документ считается current по проверенному Git baseline и
  изменениям в релевантных source paths, а не по декоративному hex string.
- **user impact:** «свежая» метка перестаёт скрывать документ, разошедшийся с
  кодом.
- **canonical owner:** `tools/qa/check_agent_docs.py`.
- **отношение к PLAN-6A:** PLAN-6A остаётся owner расширения `CURRENT_DOCS` и
  governance-правил docs QA; PLAN-STAB-8 отвечает только за семантику
  freshness. Дублирующего checker не создаётся; при пересечении зон слайсы
  выполняются последовательно, а не параллельно.
- **allowed zones:** `tools/qa/check_agent_docs.py`, его owning tests,
  синтетические Git-фикстуры.
- **prohibited zones:** автоматическое обновление metadata без content review;
  массовая правка `last_verified_*` в документах; production-код.
- **success criteria:** semantics baseline self-reference-safe (N−1 либо
  доказанный эквивалент); используется `merge-base --is-ancestor`;
  учитываются изменения в объявленных `source_paths` после baseline; calendar
  age остаётся advisory; coverage расширен на фактические current authority
  docs; design contract фиксируется до реализации.
- **required tests:** синтетические Git-репозитории (ancestor / не-ancestor /
  изменения после baseline / без изменений); один вызов на реальном репозитории.
- **выполнено:** `validate_freshness` в `tools/qa/check_agent_docs.py`.
  Coverage — все пять фактических commit-полей current authority docs:
  `last_verified_commit` в `START_HERE.md`, `SYSTEM_MAP.md`,
  `CURRENT_STATE.md`, `CLEANUP_REGISTRY.md` и `baseline_head` в самом плане.
  Каждое значение обязано быть настоящим commit (`git cat-file -e`) и
  ancestor HEAD (`git merge-base --is-ancestor`). Три класса ошибок разделены:
  некорректная форма, несуществующий commit, commit вне истории HEAD. Сеть и
  GitHub API не используются.
- **N−1 semantics:** контракт — «ancestor HEAD», а не «равно HEAD». Документ
  не может содержать hash того commit, который его записывает, поэтому
  требование равенства было бы невыполнимо по построению.
- **source_paths drift — advisory, не error.** Печатается как `NOTE:` и не
  меняет exit code. Обоснование фактическое, а не стилистическое: с `9f3ddba`
  до HEAD изменился 101 файл из объявленных `source_paths` трёх current docs,
  а всего по репозиторию за тот же интервал — 125 файлов;
  hard error потребовал бы массовой правки `last_verified_*`, которая прямо
  входит в prohibited zones этого слайса.
- **calendar age:** отсчитывается от даты HEAD commit, а не от системных
  часов. Раньше wall clock делал бы дерево красным без единого изменения в
  репозитории, из-за чего оба owning tests замораживали `today=2026-07-29`;
  эти frozen constants удалены, tests и CI теперь проходят один и тот же путь.
- **fail-closed:** отсутствие читаемого Git-репозитория и shallow clone —
  ошибки, а не тихий пропуск. Поэтому `.github/workflows/offline-tests.yml`
  получил `fetch-depth: 0` в существующем `actions/checkout@v4` (owner
  decision 2026-08-06); второй workflow и второй checkout step не создавались.
- **evidence:** `tests/test_docs_routing_and_freshness.py`, класс
  `FreshnessTests` на синтетических локальных Git-репозиториях (ancestor;
  несуществующий commit; malformed commit отдельным сообщением; commit на
  побочной ветке; drift как advisory; отсутствие drift; каталог без `.git`;
  shallow clone через `git clone --depth=1`) и `RepositoryRoutingAndFreshnessTests`
  на реальном репозитории, включая проверку, что checker не трогает worktree.
- **rollback / review:** по общим требованиям программы.

#### PLAN-STAB-9 — shared rights vocabulary owner

- **status:** completed 2026-08-06 (commit `ed4604d`, единственный commit
  слайса, trailer `Plan-Step: PLAN-STAB-9`) · independent review выполнен,
  verdict **ACCEPT WITH MINOR** (blocking findings: нет; один non-blocking
  finding — wording overclaim, исправлен этим docs-only closure слайсом, см.
  «minor finding» ниже); GitHub Actions reviewed headSha `ed4604d` — offline
  suite зелёный, failures=0, errors=0, HEAD == `origin/governance-reset`,
  worktree clean · **blocking для PLAN-9B-2:** нет · **зависимости:**
  PLAN-STAB-5.
- **выполнено:** canonical owner — `src/assets/models.py`. Он объявляет семь
  именованных `RIGHTS_*` и immutable `RIGHTS_ALLOWED_STATUSES`
  (`frozenset`: `user_owned`, `licensed`, `creative_commons`, `public_domain`).
  Удалена независимая копия того же списка — mutable set
  `ALLOWED_RENDER_RIGHTS` в `src/news/models.py` вместе с локальными
  объявлениями `RIGHTS_*`; значения до слайса совпадали, но гарантии этого не
  было. Consumers `src/news/asset_manifest_builder.py` и
  `src/news/asset_provider_adapters.py` переведены на прямой импорт из
  canonical owner. `completion/modes.py` сохраняет единственное санкционированное
  расширение `cleared`, теперь именованное `RIGHTS_LEGACY_CLEARED` в самом owner
  и намеренно не входящее в canonical набор.
- **обратная совместимость:** import paths `src.news.models` сохранены целиком —
  все семь исторических `RIGHTS_*` и `ALLOWED_RENDER_RIGHTS` остаются
  импортируемыми оттуда как compatibility re-exports; alias — тот же объект,
  что и canonical `frozenset`, а не равная копия. Ни один существующий importer
  не менялся; `tests/test_news_to_short_models.py` не правился и служит
  регрессией на re-export.
- **подтверждённый invariant:** словарь задаёт написание статуса и разрешением
  сам по себе не является. Неизвестный, пустой и отсутствующий status
  fail-closed; `review_required=True` и `allowed_for_render=False` блокируют
  canonical status; подтверждённая `rights_declaration` не разрешает структурно
  неполный asset; PLAN-STAB-5 monotonic review сохранён; round-trip не меняет
  значение статуса; legacy manifest читается и остаётся fail-closed.
- **evidence:** новый owning-модуль `tests/test_rights_status_vocabulary.py`
  (21 test OK), включая divergence-защиту как комбинацию проверок: identity
  alias canonical object, compatibility alias tests для каждого re-export,
  AST-проверка исходника `src/news/models.py` на отсутствие независимого
  vocabulary literal (второго set/frozenset словаря) и runtime tests
  существующих consumers (`asset_manifest_builder.py`,
  `asset_provider_adapters.py`). Именно эта комбинация предотвращает
  расхождение словаря; ни один отдельный AST guard не заявляется как
  самостоятельно ловящий все формы независимого возврата копии. Regression
  radius 257 OK; полный offline suite — см. запись в `CURRENT_STATE.md`;
  docs QA 0; scope-check OK; `git diff --check` 0. Сеть, provider API,
  download, Vision, TTS и реальный render не использовались.
- **minor finding (independent review, non-blocking) и его исправление:**
  формулировки в этом плане и в `CURRENT_STATE.md` преувеличивали покрытие
  divergence guard, утверждая, что один AST guard самостоятельно ловит все
  формы возврата независимой копии словаря. Исправлено этим docs-only closure
  слайсом: расхождение словаря предотвращает именно комбинация
  identity-проверок canonical object, compatibility alias tests, AST-проверки
  отсутствия независимого vocabulary literal и runtime tests consumers — не
  один изолированный AST guard.
- **не менялось:** `config/license_policy.json`, schema version, persisted
  поля, CLI, Wizard, provider APIs, network boundary; миграция манифестов не
  требуется; словарь не расширялся.
- **residual risks (не исправлялись):** (1) `completion/modes.py` приводит вход
  к lower-case, а `news`-consumers и `AssetLicense` сравнивают строку как есть —
  расхождение нормализации, на живых данных не проявляется, так как все
  производители пишут lower-case; унификация была бы семантическим изменением
  gate; (2) `AssetLicense.from_dict` / `AssetCandidate.from_dict` не переносят
  корневой `review_required` во вложенную лицензию — вне contract этого слайса,
  живой render-gate читает сырой dict и корневой флаг видит; (3)
  `ALLOWED_RENDER_RIGHTS` остаётся compatibility alias без собственного
  retirement gate — его retirement отдельное решение; (4)
  `RIGHTS_EDITORIAL_REVIEW_REQUIRED` и `RIGHTS_BLOCKED` импортёров не имеют и
  перенесены как есть.
- **цель:** убрать независимые списки допустимых rights statuses у выживающих
  production-модулей.
- **user impact:** rights-решение одинаково во всех точках, где его видит
  пользователь.
- **canonical owner:** `src/assets/models.py` — выбран caller audit слайса и
  подтверждён: у модуля нет ни одного импорта из `src`, поэтому цикл
  `src.news` → `src.assets` → `completion/replacement` невозможен.
- **allowed zones:** выбранный owner, его consumers, owning tests.
- **prohibited zones:** legacy-модули под retirement PLAN-L; новая persisted
  schema; расширение словаря без отдельного решения.
- **success criteria:** один canonical список; намеренные расширения
  документированы отдельно; persisted reader остаётся tolerant; дублирующих
  строковых списков нет.
- **required tests:** divergence-тест — расхождение словарей падает.
- **rollback / review:** по общим требованиям программы; independent review
  выполнен в отдельном контексте, verdict ACCEPT WITH MINOR (см. status выше).

#### PLAN-STAB-10 — canonical timestamp formats

- **status:** pending / not started · **blocking для PLAN-9B-2:** нет ·
  **зависимости:** —.
- **цель:** именованные timestamp contracts вместо нескольких `utc_now_iso`
  с разной точностью.
- **user impact:** сортировка и сравнение записей проекта перестают зависеть от
  того, какой модуль их записал.
- **canonical owner:** один существующий helpers-модуль, выбирается caller
  audit.
- **allowed zones:** выбранный owner и модули с дублирующими helpers, owning
  tests.
- **prohibited zones:** миграция persisted данных без отдельного owner
  approval; новый формат в persisted полях без tolerant reader.
- **success criteria:** различены instant/timestamp и date-only project
  naming; сохранена persisted совместимость; явно решено, где нужен lexical
  sort, а где parsed datetime; миграция не требуется, если tolerant readers
  достаточно.
- **required tests:** round-trip старых записей обоих форматов; стабильность
  сортировки.
- **rollback / review:** по общим требованиям программы.

#### PLAN-STAB-11 — channel manifest convergence

- **status:** pending / not started · **blocking для PLAN-9B-2:** нет ·
  **зависимости:** —.
- **цель:** `channel.json` и `channel_config.json` не образуют два
  несовместимых current contracts.
- **user impact:** канал без «правильного» файла перестаёт молча терять
  настройки голоса и workflow.
- **canonical owner:** `src/config_resolver/layers.py` совместно с фактическим
  reader `src/news/pipeline.py`.
- **allowed zones:** названные readers, `src/channel_loader.py`, owning tests.
- **prohibited zones:** удаление или переписывание существующих
  `channels/**` без отдельного owner approval; второй registry каналов.
- **success criteria:** owner/caller inventory зафиксирован; canonical формат
  выбран; определена compatibility/migration strategy; все существующие каналы
  читаются; молчаливый `{}` fallback заменён честным диагностируемым
  состоянием.
- **required tests:** по одному тесту на каждое существующее семейство каналов;
  отсутствующий и нечитаемый файл дают явный результат, а не пустой конфиг.
- **rollback / review:** по общим требованиям программы.

#### PLAN-STAB-12 — scene-duration owner enforcement

- **status:** pending / not started · **blocking для PLAN-9B-2:** нет ·
  **зависимости:** —.
- **цель:** все живые readers используют общий `scene_timeline` contract либо
  доказанно адаптируются через одного owner.
- **user impact:** длительность сцены в рендере, отчётах и субтитрах перестаёт
  расходиться.
- **canonical owner:** `src/audio/scene_timeline.py`.
- **allowed zones:** `src/audio/scene_timeline.py`, `src/news/final_renderer.py`,
  reports/completion readers, legacy format adapter, owning tests.
- **prohibited zones:** изменение persisted полей длительности; новый timeline
  owner; изменение render layout.
- **success criteria:** final renderer, отчёты и legacy adapter согласованы по
  floor/fallback semantics; фактическая длительность озвучки по-прежнему
  выигрывает у плановой; persisted совместимость сохранена.
- **required tests:** timeline parity — один и тот же проект даёт одинаковые
  длительности у всех readers.
- **rollback / review:** по общим требованиям программы.

#### PLAN-STAB-13 — workspace/media-library resolution

- **status:** pending / not started · **blocking для PLAN-9B-2:** нет ·
  **зависимости:** —.
- **цель:** `--workspace` и настроенные пути определяют один и тот же
  media-library owner.
- **user impact:** выбранный пользователем workspace действительно используется,
  а не подменяется корнем checkout.
- **canonical owner:** `src/config_resolver/paths.py` (`WorkspacePaths`) как
  источник корня; `src/media_library.py` — consumer.
- **отношение к registry:** связано с существующим C29 (`outputs/` артефакт
  того же модуля). Конкурирующий owner не создаётся; C29 остаётся за PLAN-L4.
- **allowed zones:** `src/media_library.py`, его callers
  (`src/news/asset_manifest_builder.py`, `src/providers/local_library_provider.py`,
  `src/news/asset_provider_adapters.py`, `src/news/asset_manager.py`), owning tests.
- **prohibited zones:** физический перенос runtime/медиа; изменение
  `media_index.json` layout; удаление legacy fallback без отдельного gate.
- **success criteria:** на каноническом CLI-пути нет hardcode корня checkout;
  Local Library provider и `media_index` разрешаются от одного корня;
  определена migration/compatibility strategy; legacy default сохранён.
- **required tests:** прогон с non-default workspace находит библиотеку там,
  где её объявил пользователь; default workspace не регрессирует.
- **rollback / review:** по общим требованиям программы.

#### PLAN-STAB-14 — persisted schema round-trip protection

- **status:** pending / not started · **blocking для PLAN-9B-2:** нет ·
  **зависимости:** —.
- **цель:** unknown persisted keys и старые формы не уничтожаются молча при
  read-modify-write.
- **user impact:** проект, записанный более новой или более старой версией, не
  теряет данные при обычном продолжении работы.
- **canonical owner:** `src/news/models.py` и `src/news/project_store.py`.
- **allowed zones:** названные модули, реальные старые фикстуры, owning tests.
- **prohibited zones:** превращение всех schemas в runtime validation без
  отдельного impact audit; массовая миграция persisted данных.
- **success criteria:** используются **реальные старые** фикстуры; отношение
  schema ↔ runtime зафиксировано; readers остаются tolerant; решение о
  сохранении unknown keys принято явно и записано; вложенные state-объекты не
  падают на незнакомом ключе.
- **required tests:** round-trip старого `job.json` не теряет поля;
  рукописный current payload полноценной legacy-фикстурой не считается.
- **rollback / review:** по общим требованиям программы.

#### PLAN-STAB-15 — concurrent project execution guard

- **status:** pending / not started · **blocking для PLAN-9B-2:** нет ·
  **зависимости:** PLAN-STAB-2.
- **цель:** два `resume`/`render` одного проекта не могут одновременно писать
  одни артефакты.
- **user impact:** случайный второй запуск не портит проект и не смешивает два
  результата.
- **canonical owner:** `src/project_foundation/storage.py` (`project_lock`).
- **allowed zones:** названный owner, точки входа выполнения проекта, owning
  tests.
- **prohibited zones:** новый lock-механизм рядом с существующим; блокировка
  read-only status-операций; изменение layout проекта.
- **success criteria:** определён lock scope уровня выполнения, а не одной
  записи; есть ownership token; есть heartbeat либо обоснованный timeout;
  длительность render заведомо больше stale threshold учтена; crash recovery
  определён; read-only операции не блокируются.
- **required tests:** параллельный запуск — второй получает честный отказ;
  brutal-kill владельца освобождает проект по определённому правилу.
- **rollback / review:** по общим требованиям программы.

#### PLAN-STAB-16 — CI и static controls baseline

- **status:** **partially completed** — первый milestone success criteria
  закрыт, остальные подпункты pending · **blocking для PLAN-9B-2:** нет ·
  **зависимости:** OD-S-5 (remote backup выполнен — satisfied).
- **цель:** после появления remote включить реальные repository checks.
- **user impact:** регрессия ловится до того, как владелец увидит её на своём
  проекте.
- **canonical owner:** существующий `.github/workflows/offline-tests.yml`;
  второй workflow того же назначения не создаётся.
- **allowed zones:** `.github/workflows/**` и минимально необходимые config
  files.
- **prohibited zones:** массовое переформатирование; немедленный глобальный
  strict typing; required status check до доказанного зелёного прогона.
- **success criteria:** поэтапное внедрение — существующий offline suite
  фактически зелёный в GitHub Actions → secret scan → dependency audit → lint
  baseline → type-check baseline; branch status check включается последним.
- **required tests:** сам workflow является проверкой; локально —
  синтаксическая валидация и один зелёный прогон.
- **фактический результат (CI repair, 2026-08-05):** четыре bounded commits —
  `9f9b6f2` (pinned ffprobe на Windows runner), `bcf6c2a` (path identity
  long/8.3 form на windows-latest), `8ca755f` (bundled DejaVu Sans для
  детерминированных story-card text metrics), `68acdb2` (synthetic source
  video вместо personal-machine fixture) — закрыли первый пункт success
  criteria: existing offline suite фактически зелёный в GitHub Actions. Работа
  выполнена по прямому owner decision как срочный bounded end-to-end repair;
  исходный scope был расширен владельцем после появления новых подтверждённых
  CI failures — это authorized расширение, не самовольное. Готовые видео,
  пользовательские проекты, downloaded assets и project outputs в Git не
  добавлялись. Второй workflow, secret scan, dependency audit, lint baseline,
  type-check baseline и required status check этим слайсом не создавались и
  остаются pending/non-blocking.
- **фактические проверки:** GitHub Actions run `31039985187`,
  `offline-tests / unittest` — success, 1/1 checks, failures=0, errors=0;
  локальный полный offline suite на `68acdb2` — 1589 тестов, OK. Числа
  являются измерениями, не нормативами.
- **rollback / review:** по общим требованиям программы.

#### PLAN-STAB-17 — cleanup registry и retirement ledger integrity

- **status:** pending / not started · **blocking для PLAN-9B-2:** нет ·
  **зависимости:** —.
- **цель:** registry однозначно определяет status, owner, impact, exit
  condition и фактическое завершение retirement.
- **user impact:** косвенный — решения о удалении принимаются по достоверной
  записи, а не по памяти.
- **canonical owner:** `docs/current/CLEANUP_REGISTRY.md`.
- **allowed zones:** `docs/current/CLEANUP_REGISTRY.md`.
- **prohibited zones:** переписывание historical evidence; изобретение
  несуществующих PLAN-ID; production-код.
- **success criteria:** завершённые D-слайсы отражены в retired ledger; все
  ссылки разрешаются (включая ссылку C50 → PLAN-STAB-5 и C29 → PLAN-L4);
  минимальный набор полей нормализован; принятая история сохранена.
- **required tests:** docs QA; проверка разрешимости ссылок из PLAN-STAB-7.
- **rollback / review:** по общим требованиям программы.

### PLAN-0 — versioned execution plan

- **status:** completed · **completed:** 2026-07-30 ·
  **commit:** `4027269`
- **цель:** один отслеживаемый план для Claude, Codex и других агентов.
- **зависимости:** —
- **разрешённые зоны:** `docs/current/PROJECT_EXECUTION_PLAN.md`,
  одна короткая ссылка в `docs/current/CURRENT_STATE.md`.
- **запрещено:** всё прочее, включая правку master plan.
- **измеримый результат:** план существует, checkpoint виден, ссылка добавлена.
- **required verification:** `tools.qa.check_agent_docs`, `git diff --check`.
- **фактические проверки:** обе команды повторно завершились с exit code 0 на
  clean HEAD `4027269`.
- **rollback:** один commit.

### PLAN-1 — capability owner gates (бывший монолитный 9B-C01)

- **status:** split. Ревизия 2 разделила PLAN-1 на четыре независимых слайса.
  **Глобальный inventory перестал быть предусловием любого
  production-изменения**; вместо него действует правило 11 Execution protocol:
  доказывается owner той capability, которую меняешь.
- **зависимости:** PLAN-0. **Не зависит** от зелёного full suite.
- **разрешённые зоны:** 1A, 1B, 1C′ — только `docs/current/CLEANUP_REGISTRY.md`;
  1D дополнительно допускает короткую routing-правку в `AGENTS.md`,
  `docs/current/START_HERE.md` и `docs/current/CURRENT_STATE.md`.
- **запрещено:** production-код, tests, схемы, config, любые move/delete/untrack,
  создание новых документов, правка master plan, изменение поведения.
- **общие требования к любому caller gate.** Проверяются module entrypoints через
  `python -m`, console scripts в `pyproject.toml`, `*.bat`, `*.cmd`, `*.ps1`,
  `.vscode`, `.idea`, task/config files, tests, docs, относительные, динамические
  и строковые вызовы. Статический import-граф **не** является доказательством
  отсутствия внешнего caller. Поиск вне репозитория запрещён. Вывод о
  дублировании бизнес-логики только по совпадению basename запрещён.

#### PLAN-1D-routing — маршрутизация агентов

- **status:** completed · **completed:** 2026-08-01 · **commit:** Git log —
  trailer `Plan-Step: PLAN-1D-routing` (собственный hash внутри того же commit
  не записывается, см. Execution protocol, пункт 3).
- **зависимости:** STEP 0 (перенос ревизии 2 в этот файл и в registry) выполнен.
  **Порядок обязателен:** 1D направляет будущих агентов в этот документ, поэтому
  документ должен сначала содержать утверждённую архитектуру.
- **цель:** шаг 4 `AGENTS.md` и «Текущий rescue plan» в `START_HERE.md`
  перестают направлять задачу в `PROJECT_RESCUE_MASTER_PLAN.md` как в current
  plan; добавляется ссылка на активный execution plan.
- **расширено 2026-08-01 — stale checkpoint в `CURRENT_STATE.md`.** [FACT]
  `docs/current/CURRENT_STATE.md` ссылается на активный execution plan и при
  этом называет текущим checkpoint `9B-C01`, которого после ревизии 2 больше
  нет. Это тот же routing-дефект в третьем current-документе, поэтому он
  чинится здесь же. **Exit condition расширен:** после PLAN-1D все current
  routing docs указывают на `PROJECT_EXECUTION_PLAN.md` как на current
  execution ordering source и **не называют `9B-C01` текущим checkpoint**. В
  `CURRENT_STATE.md` меняется **только** routing/checkpoint statement;
  unrelated docs cleanup там не выполняется.
- **evidence:** [FACT] у активного плана **одна** входящая ссылка во всём
  репозитории — из `CURRENT_STATE.md`; `AGENTS.md`, `START_HERE.md`, `CLAUDE.md`
  и `README.md` его не упоминают.
- **дополнительно записываются в registry** два уже проверенных findings:
  `docs/current/PRODUCT_EVIDENCE_GATE.md` со `status: historical_reference` как
  кандидат PLAN-12A (перемещение выполняет 12A, не 1D); и факт, что `skills/` не
  загружаются Claude Code автоматически, поскольку каталог не является
  `.claude/skills/`.
- **измеримый результат:** достигнут. Шаг 4 `AGENTS.md` направляет агента в этот
  файл и требует выполнять только его `current_checkpoint`; `START_HERE.md`
  называет этот файл текущим execution plan; `CURRENT_STATE.md` называет текущим
  checkpoint PLAN-2. Ни один из трёх документов не называет `9B-C01` текущим
  checkpoint. Master plan во всех трёх фигурирует только как исторический
  контекст. Дополнительно снята инструкция «обнови статус и «Текущий handoff» в
  master plan» из раздела «Завершение работы» `AGENTS.md` — она направляла
  запись current-статуса в исторический документ.
- **фактические проверки (2026-08-01, ветка `governance-reset`, HEAD до слайса
  `b396a50`, tracked-дерево чистое):**
  - `.\venv\Scripts\python.exe -m tools.qa.check_agent_docs` — exit code 0,
    «Agent documentation and skills are current and internally consistent.»;
  - `git diff --check` — пустой вывод, exit code 0;
  - `git grep -n "9B-C01" -- AGENTS.md docs/current/START_HERE.md
    docs/current/CURRENT_STATE.md` — ноль совпадений;
  - `git grep -n "PROJECT_RESCUE_MASTER_PLAN" -- ...` по тем же трём файлам —
    остались только historical/context упоминания и `source_paths`;
  - `git grep -n "PROJECT_EXECUTION_PLAN" -- ...` по тем же трём файлам —
    входящие ссылки появились в `AGENTS.md` и `START_HERE.md` дополнительно к
    существовавшей в `CURRENT_STATE.md`;
  - `git diff --name-only` — ровно пять docs-файлов: `AGENTS.md`,
    `docs/current/START_HERE.md`, `docs/current/CURRENT_STATE.md`,
    `docs/current/CLEANUP_REGISTRY.md`, `docs/current/PROJECT_EXECUTION_PLAN.md`.
  Production-код, tests, схемы, config и runtime не менялись; новых документов
  не создавалось; `docs/handoff/PROJECT_RESCUE_MASTER_PLAN.md` не изменён.
  Baseline run не выполнялся, `baseline_head` остаётся `fe2df5b`.
- **registry:** findings записаны как **C51** (`PRODUCT_EVIDENCE_GATE.md` —
  `status: historical_reference` внутри `docs/current/`, кандидат PLAN-12A, файл
  не перемещался) и **C52** (корневой `skills/` не является `.claude/skills/`,
  поэтому Claude Code не загружает его автоматически; Codex discovery остаётся
  `[ПРЕДП]`; второй набор skills не создаётся). Смысловых дубликатов в registry
  не было.
- **required verification:** `tools.qa.check_agent_docs`, `git diff --check`.
- **rollback:** один commit.

#### PLAN-1C′ — capability owner gate: asset/semantic

- **status:** completed · **completed:** 2026-08-07 · **commit:** Git log —
  trailer `Plan-Step: PLAN-1C′` (собственный hash внутри того же commit не
  записывается, см. Execution protocol, пункт 3). Прежде: pending, **BLOCKS
  PLAN-9A и PLAN-9C**; первый product-слайс (PLAN-9B-0/9B-1) не блокировал.
- **зависимости:** — . **Изменено ревизией 2.1:** прямая зависимость от PLAN-6E
  **снята** — это docs-only ownership inventory, пишущий в
  `CLEANUP_REGISTRY.md`, и существование reviewer-skill ему не требуется.
  **Одновременно явно зафиксировано:** `PLAN-9A` требует `PLAN-6E`
  (persisted-state boundary) и `PLAN-9C` требует `PLAN-6E` (semantic decision
  boundary). Полагаться на транзитивную зависимость через PLAN-9B-2 запрещено.
- **остаётся обязательным capability-owner gate перед PLAN-9A и PLAN-9C.**
- **scope:** C01-SEM плюс владельцы persisted asset-manifest, релевантные tests и
  проверка дублей в радиусе PLAN-9A: `src/assets/semantic_selection/*`,
  `src/assets/semantic_visual*`, `src/assets/completion/*`,
  `src/news/asset_manifest_builder.py`, `src/news/asset_scene_completion.py`,
  `src/news/project_store.py`, `schemas/`.
- **C01-SEM.** Ownership для `semantic_selection`, `semantic_visual`, visual
  planner и asset completion: кто принимает решение о пригодности кандидата, где
  заканчивается shared service и начинается workflow policy, какова роль
  заглушки `vision_validator` и подключённого, но не влияющего на отбор
  `semantic_visual_service`.
- **дополнительно:** зафиксировать как дефект production-зависимость на
  `docs/implementation/openai_live_evaluation` (registry C31). **Файлы не
  переносить** — target owner решает PLAN-13 по OD-8/OD-9.
- **вынесено из scope ревизией 2:** пофайловая классификация
  `docs/implementation` (96 файлов) переходит в **PLAN-12B** — она не нужна
  PLAN-9A.
- **измеримый результат:** C01-SEM закрыт; для каждого затронутого модуля
  известны canonical owner, callers, persisted contract, дубли и тесты.
- **фактический результат (2026-08-07, от clean HEAD `b0e99a7`):** достигнут.
  Секция `C01-SEM — ownership inventory asset/semantic (PLAN-1C′)` в
  `docs/current/CLEANUP_REGISTRY.md` содержит 22 строки владения по всему
  declared scope (`semantic_selection/*`, `semantic_visual*`, `completion/*`,
  `asset_manifest_builder.py`, `asset_scene_completion.py`, `project_store.py`,
  `schemas/`), каждая с canonical owner, фактическими production callers,
  decision authority, persisted contract, owning tests и duplicate/overlap.
  Три вопроса контракта закрыты фактическим кодом:
  - **кто решает о пригодности кандидата** — один владелец,
    `rank_candidates`/`select_best_candidate` в
    `src/assets/semantic_selection/candidate_ranker.py`, и только на метаданных
    провайдера. `src/news/asset_manifest_builder.py` добавляет лишь
    video-preference и приоритет пользовательского ассета; собственного
    критерия пригодности у него нет. Исторически второй точкой, способной
    изменить выбор, был `select_candidate_after_review` в
    `_prepare_visual_review`, включаемый только `technical_rerank_enabled` (по
    умолчанию `false`) и работающий на технических признаках. Post-audit
    correction **VA-NEW-03** 2026-08-10 удалил этот production caller:
    technical analysis сохраняется в review evidence, но больше не меняет
    canonical semantic/media/manual winner. Роли разведены: evidence producers
    (`scene_analyzer`, `evidence`, `visual_preview`, `semantic_visual_service`)
    · decision owner (`candidate_ranker`, плюс `completion/ladder` и
    `completion/modes`) · orchestration owner (`asset_manifest_builder`) ·
    persistence owner (`project_store` + `news/pipeline`);
  - **граница shared service / workflow policy** — по `src/assets/*` против
    `src/news/*`: shared-сервисы не знают о стадиях, `job.json` и порядке
    провайдеров. Обратные пересечения границы (`completion/replacement.py:250`
    импортирует `src.news.asset_manager`; `completion/replacement.py` и
    `assets/visual_preview.py` читают `assets_manifest.json`) записаны как
    evidence уровня INFERENCE и **не исправлялись**;
  - **`vision_validator` и `semantic_visual_service`** — первый является
    заглушкой без единого caller и без owning test (флаг
    `vision_validation_enabled` тоже никем не читается); второй подключён, но
    вызывается из `_write_reviews` после отбора всех сцен и пишет evidence
    только в `assets/review/visual_review_manifest.json`.
    `_selection_fingerprint` — защитная самопроверка (`selection_warning`), а
    не вето. Уже записанный дефект отчётности `_semantic_visual_summary`
    (`semantic_rerank_enabled` жёстко `False`) подтверждён и оставлен PLAN-9C.
  Persisted contracts зафиксированы, включая **трёх писателей**
  `assets/assets_manifest.json` (`news/pipeline.py:437`,
  `news/draft_completion.py:256`, `assets/completion/replacement.py:294`).
  Duplicate/overlap классифицированы: живого второго owner нет; фактические
  находки — построчный дубль video-preference в
  `news/asset_manager._select_best_candidate` (compatibility patch-point,
  закреплённый `test_news_asset_manager_contract.py`), совпадение имени
  `semantic_score` при разном смысле, неподключённый `semantic_decision_policy`
  и неиспользуемый `vision_validator`. **C31** перепроверен: production-зависимость
  на `docs/implementation/openai_live_evaluation` существует
  (`semantic_visual_evaluation_tooling.py:26,38,695` плюс tests) и записана как
  подтверждённый дефект; **файлы не переносились**, imports не менялись, target
  owner не выбирался — physical target остаётся **PLAN-13** по OD-8/OD-9,
  пофайловая классификация `docs/implementation` остаётся **PLAN-12B**.
- **границы соблюдены:** production-код, tests, схемы, config, manifests,
  runtime и user data не изменялись; файлы не перемещались и не удалялись;
  новый selector, semantic service, abstraction, persisted-поле и PLAN-ID не
  создавались; Vision wiring, `candidate_ranker` и completion logic не
  трогались; сеть, provider search, Vision, TTS и render не выполнялись.
  Найденные дефекты записаны как evidence и не исправлялись.
- **фактические проверки (2026-08-07, ветка `governance-reset`, HEAD до слайса
  `b0e99a7`, tracked-дерево чистое):**
  - `.\venv\Scripts\python.exe -m tools.qa.check_agent_docs` — exit code 0;
  - `git --no-optional-locks diff --check` — пустой вывод, exit code 0;
  - `.\venv\Scripts\python.exe -m tools.qa.check_task_scope` с фактическим
    docs-allowlist — `OK`;
  - `git diff --name-only` — ровно пять docs-файлов:
    `docs/current/CLEANUP_REGISTRY.md`,
    `docs/current/PROJECT_EXECUTION_PLAN.md`, `docs/current/START_HERE.md`,
    `docs/current/SYSTEM_MAP.md`, `docs/current/CURRENT_STATE.md`.
  Full offline suite не запускался и не требуется: Execution protocol,
  пункт 10 — production contract, test discovery и runner не менялись.
- **примечание к allowed zones.** Зона слайса — `CLEANUP_REGISTRY.md` плюс этот
  файл по Execution protocol, пункт 1. Три routing mirror
  (`START_HERE.md`, `SYSTEM_MAP.md`, `CURRENT_STATE.md`) изменены **только** в
  предложении о current checkpoint: это механическое следствие
  current-routing-integrity контракта PLAN-STAB-7, который валидирует
  `check_agent_docs` — required verification этого же слайса. Иной правки в
  них не выполнялось.
- **required verification:** `tools.qa.check_agent_docs`, `git diff --check`.
- **rollback:** один commit.

#### PLAN-1A — capability gate: entrypoints и package roots

- **status:** pending. **Не блокирует первый product fix и PLAN-9A.**
  Обслуживает PLAN-L и PLAN-13.
- **scope:** C01–C04, C08–C11; `pyproject.toml`, console scripts, module
  entrypoints, `apps/*`, root `ai_youtube/`, `src.content_creation.cli`.
- **примечание:** caller gate для `pipeline.py`, `legacy/` и legacy-семейства
  выполняет **PLAN-L1**, а не 1A. Foundation audit установил [FACT], что
  `legacy/` (8 файлов) не имеет ни одного Python-caller и упоминается только в
  `README.md` и historical docs (registry C17); это **не** закрывает C17.
- **required verification:** `tools.qa.check_agent_docs`, `git diff --check`.

#### PLAN-1B — capability gate: application/shared ownership

- **status:** pending. **Не блокирует первый product fix и PLAN-9A.**
  Обслуживает PLAN-13, включая покрытие HIGH-3 (channel/project formats).
- **scope:** C05–C08 и C12–C16; Fullscreen, Story Card, Anime
  project/transcription/subtitles/FFmpeg/render, music, project/workspace и
  границы shared-сервисов.
- **required verification:** `tools.qa.check_agent_docs`, `git diff --check`.

### PLAN-L — retirement legacy content stack

- **status:** pending · **зависимости:** зелёный PLAN-4. **PLAN-L0 completed
  2026-08-02 и закрывает prerequisite PLAN-9B-PRODUCER/PLAN-9B-2; PLAN-L1…PLAN-L4
  остаются отдельной retirement-веткой, закрытием PLAN-L0 не разрешены и
  напрямую prerequisite PLAN-9A не являются.**
- **цель:** убрать крупнейший disposable блок репозитория до того, как он
  продолжит удерживать docs, packaging, tests и minimalism.
- **evidence [FACT], 2026-07-31:** legacy content-стек — `pipeline.py` →
  `src/legacy_pipeline/workflow.py` → 20 модулей корня `src/` (~4903 строки) —
  имеет **ровно одного** production-caller (`pipeline.py`) и **6** test-модулей
  из 112. `legacy/` (8 файлов, 424 строки) не имеет ни одного Python-caller.
  Исключения, которые остаются: `src/media_library.py` (используется активным
  news-путём) и `src/utils.py` (используется `src/audio/tts/env.py` и
  `src/tts_providers/moss_tts_provider.py`).
- **evidence [FACT]:** `src/legacy_pipeline/maintenance.py` (~500 строк) — **не**
  legacy-генерация контента, а единственный CLI-доступ к visual-preview,
  semantic-backend, semantic-evaluation, semantic-visual, media-library и
  envato-manual. Канонический CLI этих команд не имеет. [INFERENCE] PLAN-9D без
  них не запускается — поэтому L2 обязателен до L3.
- **impact:** −~5700 строк, −6 тестов, −6 top-level путей; закрываются C17, C18,
  C19, C24, C25, C29; PLAN-7, PLAN-13D, PLAN-14B и часть PLAN-14F становятся
  тривиальными.
- **rollback:** один commit на под-slice плюс annotated tag по механизму
  reversible retirement.

#### PLAN-L0 — Knowledge Salvage Gate

- **status:** completed · **completed:** 2026-08-02 · **commit:** — (см. Git log,
  trailer `Plan-Step: PLAN-L0`) · **обязателен до PLAN-9B-PRODUCER и L3** ·
  **зоны:** `docs/current/CLEANUP_REGISTRY.md` (+ этот файл для
  checkpoint/evidence по Execution protocol).
- **фактический результат:** `Knowledge salvage log` в `CLEANUP_REGISTRY.md`
  заполнен; placeholder-строка снята. Аудированы все обязательные families:
  `channels/{psychology,quotes,survival,size_comparison}` и `content/` ·
  20 движков корня `src/` (ровно `src/*.py` кроме `__init__.py`,
  `media_library.py` и `utils.py`, суммарно 4903 строки) ·
  `src/legacy_pipeline/workflow.py` · `config/video_style.json` · `legacy/` ·
  `MOSS_TTS_Nano/` + `src/tts_providers/` + `scripts/test_moss_voices.py` ·
  legacy test-модули · motion owners (`story_card_short_render`,
  `generated_infographic`, `self_eval`, callers `moviepy`).
- **обязательные находки подтверждены фактическим кодом:** все двенадцать —
  C46, C47, C48, `self_eval`, thumbnail, YouTube metadata, size comparison,
  Story Card, `generated_infographic`, `moviepy`, text overlay/title,
  music-by-mood. Два уточнения записаны как измерения, не нормативы:
  legacy test-модулей фактически семь, а не шесть, и legacy-callers `moviepy` —
  шесть, а не три (**C55** по существу не меняется).
- **границы соблюдены:** capability не мигрировалась, retirement не выполнялся,
  tag и bundle не создавались, файлы не удалялись и не перемещались;
  production-код, tests, configs, schemas, manifests, runtime и user data не
  изменялись; сеть, provider search/download, model API, TTS, Vision и render не
  выполнялись. Новый owner, ADR, schema, manifest, interface, package и
  placeholder implementation не создавались. `baseline_head` не менялся.
- **фактические проверки:** `tools.qa.check_task_scope` с двумя разрешёнными
  exact paths — `OK`, exit code 0; `tools.qa.check_agent_docs` — exit code 0;
  `git diff --check` — без замечаний. Full offline suite не запускался: слайс
  docs-only, test discovery, runner и production contract не менялись
  (Execution protocol, пункт 10).
- **правило (OD-1):** отсутствие caller — **не** критерий отсутствия ценности.
  Ретайр legacy допускается только после salvage.
- **scope gate — что проходит через L0.** KSG применяется к
  **knowledge-bearing retirement families**: source code, workflow, config,
  prompts, templates, tests и те docs/evidence, которые содержат уникальное
  инженерное или продуктовое знание.
- **что через L0 НЕ проходит.** Disposable runtime/media/cache — старые `.mp4`,
  `.wav`, `.png`, кэши, generated outputs, runtime-каталоги проектов — идёт
  другой цепочкой: **PLAN-14D** (классификация, отбор representative corpus,
  сверка с `Preserved runtime corpus`) → **PLAN-14E** (cleanup). Спрашивать
  «какое product knowledge содержится в старом mp4» не нужно и запрещено как
  формальность: это превратило бы runtime reset в бесконечный gate.
  **Knowledge Salvage и Runtime Reset не смешиваются.**
- **граница между цепочками.** Решает не каталог, а носитель знания: JSON/SRT/ASS
  манифесты — это persisted **форма**, их ценность проверяется отбором
  representative corpus в 14D, а не salvage-классификацией L0. Если внутри
  runtime-каталога найден source/prompt/template/config — он уходит в L0.
- **что искать в каждом удаляемом family:** reusable algorithm · domain и
  product knowledge · prompts, templates, visual rules · rights и licensing
  knowledge · fallback и recovery logic · edge cases · reusable schema
  knowledge · полезные characterization и product tests.
- **классификация каждой находки:**

  ```
  MIGRATE CAPABILITY        пометить как отдельный будущий product slice.
                            НЕ выполняется внутри PLAN-L (OD-10).
  MIGRATE KNOWLEDGE         перенести знание: ADR, docstring, comment, fixture
  KEEP MINIMAL REGRESSION   оставить минимальный representative fixture
  ARCHIVE ONLY              только retirement tag, в active tree не возвращать
  DELETE                    ничего ценного
  ```

- **граница L0/L3 (OD-10).** L0 сохраняет **знание**, а не переносит capability.
  **L3 остаётся cleanup/retirement-этапом и не превращается в
  product-development.** Если salvage признаёт capability ценной — это отдельный
  будущий product slice на новом canonical core из salvage evidence, а не
  миграция старой реализации внутрь L3.
- **семейства в scope:** `channels/{psychology,quotes,survival,size_comparison}`
  и `content/` (OD-1) · 20 движков корня `src/` · `legacy/` ·
  `src/legacy_pipeline/workflow.py` · `config/video_style.json` ·
  `MOSS_TTS_Nano/` и `src/tts_providers/` (OD-7) · 6 legacy test-модулей.
- **обязательные salvage-находки ревизии 2.1** (сохранить **до** retirement;
  старый pipeline ради них **не** сохраняется):
  1. **legacy `build_query_variants` expansion ladder** — `MIGRATE KNOWLEDGE`,
     потребитель **PLAN-9B-2** (registry C46);
  2. **local-library diversity reserve** (`min_local_diversity_per_scene` /
     `reserved_download_slots`) — `MIGRATE KNOWLEDGE`, потребитель **PLAN-10D**
     (registry C47);
  3. **практика «provider-ready английские visual keywords существуют
     отдельным полем, отделённым от нарратива»** — `MIGRATE KNOWLEDGE`,
     носитель ADR/registry (registry C48).
  4. **анализ качества готового файла** (`src/self_eval.py`) — `MIGRATE
     KNOWLEDGE`. Это единственное в репозитории знание о проверке
     отрендеренного файла, а не метаданных; потребитель — будущее расширение
     существующего quality owner. Новый Quality Engine не создаётся.
  5. **thumbnail generation, YouTube metadata и формат сравнения размеров** —
     `MIGRATE CAPABILITY` по OD-10: это продуктовые возможности, которых у
     нового продукта нет вовсе. Внутри PLAN-L они **не** мигрируются; каждая
     помечается отдельным будущим product slice на новом canonical core.
     Продуктовая запись — `PRODUCT_PLAN.md`, раздел «Legacy knowledge and
     capability salvage».
- **обязательные salvage-находки motion rendering (2026-08-01)** — сохраняются
  **до** замещения соответствующего owner по PD-11; старая реализация ради них
  не сохраняется:
  6. **поведение Story Card** — адаптивный текст, вёрстка по реальным метрикам
     шрифта, работа с длинными строками, вертикальный layout: `MIGRATE
     KNOWLEDGE` + `KEEP MINIMAL REGRESSION`, потребитель — parity case
     `MOTION-CS2` → `MOTION-CS4` (registry C53);
  7. **ценные контракты `generated_infographic`** — «спека → project-owned
     asset с license/provenance/checksum/technical validation», fingerprint
     спеки и правило «нет evidence → нет фактической диаграммы»: `MIGRATE
     KNOWLEDGE`, потребитель — `MOTION-CS4`; новый author встраивается **в**
     этот контракт, а не рядом с ним (registry C56);
  8. **callers и фактическая необходимость `moviepy`** — `MIGRATE KNOWLEDGE`,
     потребитель — dependency gate `MOTION-CS4` (registry C54, C55);
  9. **анализ качества готового файла** (`src/self_eval.py`) уже записан
     находкой 4 выше; дополнительный потребитель — technical QA сегмента в
     `MOTION-CS1`. Новый Quality Engine не создаётся.
- **измеримый результат:** для каждого family записан класс каждой находки и,
  где применимо, что именно потенциально стоит восстановить позже.
- **required verification:** `tools.qa.check_agent_docs`, `git diff --check`.

#### PLAN-L1 — caller gate и retirement manifest

- **status:** pending · **зависимости:** PLAN-L0 · **зоны:** только registry.
- **цель:** полный caller gate по legacy-семейству по общим требованиям PLAN-1.
  Закрывает C17.
- **дополнительно:** зафиксировать retirement-теги, которые будут созданы в
  L3/L4, и подтвердить наличие внешнего `git bundle` перед первым удалением.
- **required verification:** `tools.qa.check_agent_docs`, `git diff --check`.

#### PLAN-L2 — вынести diagnostics из legacy

- **status:** pending · **зависимости:** PLAN-L1 · **обязателен до L3.**
- **цель:** команды `src/legacy_pipeline/maintenance.py` (visual-preview,
  semantic-backend, semantic-evaluation, semantic-visual, media-library,
  envato-manual) переезжают на канонический CLI `diagnostics` либо в `tools/`.
- **запрещено:** менять поведение команд в этом слайсе; смешивать перенос
  diagnostics с удалением движков.
- **required verification:** targeted + `smoke` + `full` — меняется CLI surface.

#### PLAN-L3 — retire движков

- **status:** pending · **зависимости:** PLAN-L0 и PLAN-L2.
- **удаляется:** `src/legacy_pipeline/workflow.py`; 20 модулей корня `src/`
  **кроме** `media_library.py` и `utils.py`; `src/tts_providers/` (OD-7);
  `channels/{psychology,quotes,survival,size_comparison}` и `content/` (OD-1);
  `config/video_style.json`; 6 legacy test-модулей.
- **запрещено:** мигрировать capability внутрь этого слайса (OD-10).
- **required verification:** `full`.

#### PLAN-L4 — retire entrypoint

- **status:** pending · **зависимости:** PLAN-L3.
- **удаляется:** `pipeline.py`, `src/legacy_pipeline/cli.py`,
  `apps/youtube_pipeline/`, `legacy/`, `scripts/`, `MOSS_TTS_Nano/` (OD-7).
- **исправляется:** `py-modules = ["pipeline"]` снимается вместе с импортом
  `scripts.test_moss_voices` (C18, C25); `outputs/*.json` и
  `outputs/asset_library_report.md` снимаются с Git (C19, C29).
- **измеримый результат:** канонический CLI — единственный пользовательский вход;
  wheel собирается и импортируется из произвольного temporary checkout.
- **required verification:** `full` + сборка wheel + `import` в temporary venv
  вне checkout. Установка требует отдельного разрешения.

### PLAN-2 — baseline repair: voice-profile fixtures

- **status:** completed · **completed:** 2026-08-01 · **commit:** — (см. Git log,
  trailer `Plan-Step: PLAN-2`)
- **цель:** убрать устаревшую изоляцию через `os.chdir` и использовать явный
  `channels_dir` либо существующий path seam.
- **зависимости:** PLAN-1D-routing. **Изменено ревизией 2:** зависимость от
  полного PLAN-1 снята — слайс трогает один test-модуль и никакого capability
  ownership не меняет.
- **разрешённые зоны:** `tests/test_voice_profile_resolution.py`.
- **запрещено:** production-код, прочие тесты.
- **диагноз (подтверждён):** изоляция через `os.chdir` перестала действовать
  после того, как versioned resources стали резолвиться от корня репозитория, а
  не от `cwd`; реестр читает настоящий `channels/` и возвращает чужой профиль.
  Production корректен.
- **root cause (фактический):** `src/config_resolver/paths.py` вычисляет
  `_REPOSITORY_ROOT` от расположения модуля (`Path(__file__).resolve().parents[2]`),
  и `ApplicationPaths.channels_root` — это `repository / "channels"`. `cwd` в этой
  цепочке не участвует вообще, поэтому `os.chdir()` во временный каталог не
  изолировал ничего: и `capabilities._channels_root()`, и
  `voice_profile_registry._channels_root()` продолжали читать настоящий
  `channels/`. Доказательство характеризацией: `list_voice_profiles` возвращал
  `['ru_dom']` вместо `['ru_test']` — то есть реальный профиль из
  `channels/nature_science_news_ru/voices.yaml`.
- **применённый seam:** существующий публичный параметр `repository_root=`
  функции `src.config_resolver.paths.resolve_application_paths` — тот же seam,
  которым уже пользуются `tests/test_stage3_workspace_paths.py` и
  `tests/test_legacy_pipeline_internals_contract.py`. Fixture создаёт временный
  `channels/`-каталог и на время блока подменяет `resolve_application_paths`
  обёрткой, подставляющей `repository_root` фикстуры; обе точки входа
  (`capabilities._channels_root`, `voice_profile_registry._channels_root`)
  импортируют эту функцию внутри тела, поэтому один seam покрывает обе.
  `channels_dir` как явный аргумент здесь неприменим: ни
  `capabilities.resolve_voice_profile`, ни `list_voice_profiles`, ни
  `load_voice_profile_for_channel` его не принимают, а добавление параметра было
  бы изменением production-кода вне разрешённых зон. Новый helper, registry или
  второй способ разрешения channels не создавался.
- **измеримый результат:** модуль завершается без failures и errors; сохранены
  паритет UI и runtime, резолв по display_name, borrowed profile с
  `source_channel_id`, `include_global=False`, понятное сообщение об ошибке и
  отсутствие протечки реальных repository-профилей в fixture. `os.chdir()` из
  модуля удалён; `cwd` процесса после прогона не меняется.
- **required verification:** только targeted-модуль. Режим `fast` ещё не
  существует до PLAN-5 и поэтому не может быть prerequisite.
- **фактическая verification (2026-08-01, HEAD до слайса `373daa8`):**
  - до изменения: `.\venv\Scripts\python.exe -B -m unittest
    tests.test_voice_profile_resolution` — exit code 1, 8 тестов, 1 failure и
    3 errors;
  - после изменения: та же команда — exit code 0 двумя последовательными
    прогонами; каждый test-класс отдельно тоже зелёный (зависимости от порядка
    нет);
  - `.\venv\Scripts\python.exe -m tools.qa.check_agent_docs` — exit code 0;
  - `git diff --check` — без замечаний.
  Числа тестов, failures и errors записаны как измерение с датой и проверенным
  HEAD, нормой они не являются (Measurement policy).
- **rollback:** один commit.

### PLAN-3 — baseline repair: completion-wiring fixtures

- **status:** completed · **completed:** 2026-08-01 · **commit:** — (см. Git
  log, trailer `Plan-Step: PLAN-3`)
- **цель:** создавать обязательные stage outputs согласно output-validated
  idempotency ADR 0006.
- **зависимости:** PLAN-2. **Изменено ревизией 2:** зависимость от полного
  PLAN-1 снята. Слайс трогает один test-модуль, но это **тот самый модуль**,
  который меняет PLAN-9A, поэтому он остаётся прямым prerequisite 9A.
- **разрешённые зоны:** `tests/test_autonomous_completion_pipeline.py`.
- **запрещено:** production-код.
- **диагноз (подтверждён):** два test-метода давали три failure-case:
  `test_resume_restarts_asset_search_when_completion_semantics_change` (два
  subtest) и
  `test_resume_keeps_completed_asset_search_when_override_is_unchanged`
  помечали стадии `completed`, не создавая обязательных outputs, и ожидали
  поведение до этапа 5D. `NewsProjectStore.is_stage_completed` после ADR 0006
  признаёт marker только вместе с пригодным output, поэтому production
  корректно повторял `research`, `script` и `visual_plan`; в unchanged-case
  также не существовал пригодный output `asset_search`.
- **исправление:** private helper внутри test-модуля создаёт во временном
  project layout реальные минимальные `research/claims.json`, локализованные
  `script/script.json` и `visual/visual_plan.json`, а также
  `assets/assets_manifest.json`. Fixtures проходят фактические production
  validators; assertions, resume/force-stage semantics и production-код не
  менялись.
- **окончательный resume-факт:** стадия с отсутствующим или непригодным output
  может быть перезапущена; по 28 проверенным проектам платные и сетевые стадии
  не перезапускаются; у 7 проектов могут повториться только локальные
  preview/final render. Старое предположение о повторных платных
  `research`/`script` в current-документы не переносится.
- **измеримый результат:** модуль завершается без failures и errors;
  ожидаемое production-поведение не изменено.
- **required verification:** только targeted-модуль. Совместный полный
  baseline выполняется отдельным PLAN-4.
- **фактическая verification (2026-08-01, HEAD до слайса `a8c40a1`):**
  - до изменения: `.\venv\Scripts\python.exe -B -m unittest
    tests.test_autonomous_completion_pipeline` — exit code 1, 14 тестов,
    3 failures;
  - после изменения: та же команда — exit code 0 в двух последовательных
    прогонах;
  - `.\venv\Scripts\python.exe -m tools.qa.check_agent_docs` — exit code 0;
  - `git diff --check` — без замечаний;
  - full offline suite не запускался; зелёность baseline остаётся предметом
    PLAN-4.
  Числа тестов и failures записаны как измерение с датой и проверенным HEAD,
  нормой они не являются (Measurement policy).
- **rollback:** один commit.

### PLAN-4 — зелёный baseline

- **status:** completed · **completed:** 2026-08-01 · **commit:** —
- **цель:** воспроизводимый зелёный offline baseline.
- **зависимости:** PLAN-2, PLAN-3.
- **разрешённые зоны:** production/tests не меняются; этот plan обновляется
  измерением, проверенным исходным HEAD и новым checkpoint.
- **измеримый результат:** `python -B -m unittest discover -s tests -p "test_*.py"`
  завершается с exit code 0 без неожиданных failures и errors; фактические число
  тестов и время записаны в Measurement policy как измерение с датой и
  проверенным исходным HEAD.
- **required verification:** full offline suite.
- **фактическая verification (2026-08-01):** на проверенном исходном HEAD
  `84bdd8b4f64c7adaf7582bdb39b15b18163253fb` команда
  `.\venv\Scripts\python.exe -B -m unittest discover -s tests -p
  "test_*.py"` завершилась с exit code 0: 1441 тест за 231.839 секунды,
  failures: 0, errors: 0, skips: 0. Unexpected failures/errors отсутствуют;
  прогон был offline, без provider search/download, Vision, TTS, платных
  API-вызовов и реального пользовательского render. Production-код и tests в
  PLAN-4 не менялись. Число тестов и длительность — измерение, не норматив;
  будущий plan-only commit не является проверенным source HEAD.
- **rollback:** один plan-only checkpoint commit.

### PLAN-5 — единый test runner

- **status:** pending · **completed:** — · **commit:** —
- **цель:** один runner вместо трёх разных правил о тестах.
- **зависимости:** PLAN-4. **PARALLEL для всех под-слайсов PLAN-9B** (ревизия
  2.1). [FACT] targeted (`python -B -m unittest <модули>`), full
  (`python -B -m unittest discover -s tests -p "test_*.py"`) и три smoke-команды
  (`python -m ai_youtube --help`, `capabilities --json`, `applications list`)
  исполнимы **сегодня**. PLAN-5 улучшает uniform runner UX и воспроизводимость
  формулировки; техническим blocker product fixes он не является и в required
  verification слайсов 9B подменяется существующими командами.
- **разрешённые зоны:** `tools/qa/run_tests.py`,
  `.github/workflows/offline-tests.yml` и targeted runner tests.
- **запрещено:** production-код, изменение существующих product-test
  contracts, замена `unittest` как движка, правка network guard. Новые тесты
  самого runner разрешены.
- **режимы:**
  - `smoke` — несколько секунд: import канонического пакета,
    `python -m ai_youtube --help`, `capabilities --json`, `applications list`,
    один безопасный synthetic dry-run при наличии. Только allowlist проверенных
    read-only CLI paths. Учитывать, что tests network guard **не действует**
    автоматически на прямой subprocess CLI;
  - `fast` — suite без render-тяжёлых модулей, ориентир 30–40 секунд;
  - `targeted` — радиус изменённой зависимости;
  - `full` — весь offline suite, включая synthetic renderer contracts.
- **измеримый результат:** четыре режима работают и печатают фактический бюджет;
  вшитых ожидаемых чисел тестов в коде runner нет; каждое исключение из `fast`
  выводится с причиной, а `full` динамически обнаруживает все `test_*.py`;
  offline workflow вызывает тот же `full`, а не поддерживает вторую команду.
  Smoke содержит только доказанно read-only subprocess paths; test-package
  network guard не считается защитой subprocess CLI.
- **required verification:** `smoke` + `fast` + `full`.
- **rollback:** один commit.

### PLAN-6 — governance, ранний minimalism baseline и toolchain audit

- **status:** pending · **completed:** — · **commit:** —
- **цель:** до product/refactor работ закрепить единые правила, измерить
  фактическое загрязнение репозитория и определить владельцев зависимостей.
- **зависимости:** PLAN-5.
- **запрещено:** production-код, удаление/перенос файлов и runtime data,
  создание ADR про governance, обновление lock или скачивание зависимостей.
- **разделение ревизией 2.** Только **6A, 6D и 6E** блокируют PLAN-9A.
  **6B и 6C — параллельные**, глобальными prerequisites product-работ не
  являются.
- **переоценка ревизией 2.1 (risk-based).**
  **6A — PARALLEL** относительно PLAN-9B: Agent Autonomy Model уже действует из
  текста этого плана, а routing чинит PLAN-1D; собственные добавления 6A
  (проверка команд в `skills/*/SKILL.md`, расширение `CURRENT_DOCS`, cap
  `AGENTS.md`) обслуживают PLAN-7 и PLAN-12, не 9B. Зависимость **6A → 6D —
  ordering convention, а не техническая необходимость**.
  **6D — blocker первого multi-owner implementation slice** (PLAN-9B-2).
  **6E — blocker первого destructive retirement / high-risk shared-contract
  slice** (PLAN-9B-2, 9B-3, 9B-5b), плюс **обязателен для PLAN-9A и PLAN-9C**.
- **bounded sub-slices:**
  - **PLAN-6A — governance R1–R12, Agent Autonomy Model и docs QA:**
    - **PARALLEL относительно PLAN-9B** (ревизия 2.1);
    - разрешённые зоны: `AGENTS.md`, `tools/qa/check_agent_docs.py`, связанные
      onboarding и reproducibility tests;
    - R1–R12 в согласованной редакции с категориями A/B/C/D;
    - **переносит в `AGENTS.md` Agent Autonomy Model этого плана:** классы
      `[HARD]/[ARCH]/[HINT]`, «выполнение инструкции не является выполнением
      задачи», Decision rights (три tripwire), Challenge/Recovery Protocol,
      semantic Owner Lookup, Task contract. После переноса соответствующий
      раздел этого плана сворачивается до ссылки: один canonical owner на
      правило;
    - **исправляет три формулировки, ошибочно оформленные как HARD:**
      (a) «сначала добавляй characterization test» → `[HINT]` с условием
      «когда меняешь наблюдаемое поведение, у которого есть caller»;
      (b) «не создавай второй provider contract / voice registry / subtitle
      engine / config resolver / completion ladder» → `[ARCH]`: запрещён
      **второй одновременно живущий** canonical owner, **замена** owner через
      evidence + ADR + review разрешена;
      (c) «сохраняй tolerant readers, resume/force-stage и approval gates» →
      разделить: approval gates `[HARD]`, tolerant readers `[ARCH]`;
    - **cap 120 строк `AGENTS.md`** (`tests/test_stage2_agent_onboarding.py:26`)
      переклассифицируется в measurement/warning. Число не является
      архитектурным решением; `AGENTS.md` остаётся коротким по responsibility.
      Если Engineering Conventions окажутся отдельной responsibility, отдельный
      owner допускается **после доказательства необходимости** и не
      запрещается числом строк. `docs/architecture/ENGINEERING_CONVENTIONS.md`
      заранее не создаётся;
    - **минимальный gap-набор conventions**, у которого сегодня нет владельца и
      который закрывается здесь как `[ARCH]`: правило размещения пакета
      (`src/foo.py` против `src/foo/`); процедура deprecation; политика fixtures
      (versioned / synthetic / временный каталог); именование и категории тестов;
      условие появления нового top-level каталога. Уже покрытое (naming, errors,
      logging, config, persistence, schemas, typing, imports, dependency
      direction, public/private API) повторно не документируется — владельцы
      существуют в коде, ADR и `SYSTEM_MAP`;
    - QA не требует вечного существования конкретных архивных handoff;
    - exact-count проверка skills заменяется минимальным обязательным набором
      критичных skills плюс автоматической проверкой всех найденных;
    - broken link, missing source path и invalid commit — error;
    - возраст документа и превышение рекомендуемого размера — warning;
    - onboarding-лимит `START_HERE.md` может остаться жёстким;
    - `README.md` обязан упоминать канонический CLI (`COMMANDS.md` снят из
      этого пункта 2026-08-13: файл удалён по OD-S-7, и проверка удалённого
      файла означала бы вечный error либо молчаливый пропуск);
    - `CURRENT_DOCS` перестаёт быть вшитым кортежем из трёх путей: проверяются
      все файлы `docs/current/` со `status: current` плюс активный execution
      plan. Сейчас QA покрывает три файла из семи, и активный план не
      проверяется вовсе;
    - файл в `docs/current/` со `status`, отличным от `current` или `active`,
      становится error: это делает findings PLAN-1D самопроверяемыми;
    - `max_age_days` перестаёт быть вшитой в код нормой — приходит аргументом,
      дефолт остаётся warning, а не error;
    - снимается требование «`docs/handoff` содержит ровно один файл»: оно
      конфликтует с PLAN-12C, который этот каталог архивирует;
    - **добавляется проверка команд внутри `skills/*/SKILL.md`**: команды,
      которым skill обучает агента, обязаны соответствовать каноническому
      CLI. Foundation audit [FACT]: три из шести skills
      (`create-short-video-first`, `resume-project`, `replace-visual-slot`)
      учат `python -m src.content_creation.cli`, а текущий QA проверяет только
      frontmatter, локальные ссылки и `TODO`. PLAN-7 чинит эти три файла
      однократно; без проверки ничто не мешает им разойтись снова;
  - **PLAN-6B — ранний report-only minimalism baseline:**
    - зависимость: PLAN-6A. **Параллельный: product-работу не блокирует;**
    - **subprocess network-guard measurement (ревизия 2.1, registry C49):**
      guard из test-пакета дочерним процессом **не наследуется**. На audit HEAD
      `adcbb19` subprocess-модулей **12** (ранее записано 7) — это
      **measurement, не invariant**. Архитектурное решение по kill-switch
      сейчас **не принимается**: расширение guard на subprocess boundary и
      environment kill-switch остаются открытыми альтернативами,
      механизм/owner — implementation-time evidence/owner decision. **6B
      остаётся report/measurement owner в своей текущей границе и ничего не
      мутирует**; production-side механизм получает своего owner отдельным
      слайсом;
    - **сохранить как candidates для architecture fitness enforcement**
      (внедрение — здесь и в существующих test-владельцах, второй QA framework
      не создаётся): unknown top-level directories · runtime writes внутрь
      source repo · tracked generated media · absolute machine paths ·
      более одного canonical public CLI · запрещённые application → application
      зависимости · владение persisted manifests и schema · consistency
      provider registry · network boundary · paid calls через approval
      gateway · stale commands и невалидный agent routing.
      Владельцы: детекторы репозитория — `check_repository_minimalism.py`;
      инварианты кода — существующие `tests/test_asset_import_boundaries.py`,
      `tests/test_capability_consistency.py`, `tests/test_artifact_schemas.py`,
      `tests/network_guard.py`; переписываемый `tests/test_apps_structure.py`
      становится тестом «нет второго canonical public CLI»;
    - разрешённые зоны: `tools/qa/check_repository_minimalism.py`, его
      targeted tests, `docs/current/CLEANUP_REGISTRY.md`;
    - отчёт покрывает tracked cache/generated outputs, top-level paths вне
      draft allowlist, exact duplicates, wrappers без registry, retired
      imports, hardcoded machine paths, empty directories и orphan-кандидатов;
    - **три детектора добавляются по проверенным findings Foundation audit:**
      (a) tracked ∩ ignored — `git ls-files -i -c --exclude-standard`; сейчас
      9 файлов: 8 × `outputs/*.json` и `assets/broll/.gitkeep`, где директорное
      правило обесценивает последующее отрицание (registry C19, C21);
      (b) top-level untracked вне allowlist; сейчас `output/` и `tmp/`, не
      покрытые ни одним правилом `.gitignore` (registry C20);
      (c) hardcoded drive-paths **в versioned config**, а не только в коде;
      сейчас `config/video_style.json` и `channels/psychology/style.json`
      (registry C24). Детектор tracked generated outputs обязан находить и
      `outputs/asset_library_report.md`, который под `.gitignore` не подпадает,
      но порождается `src/media_library.py` (registry C29);
    - detector ничего не удаляет; orphan/duplicate остаются review evidence;
  - **PLAN-6C — dependency/toolchain ownership audit:**
    - зависимость: PLAN-6B. **Параллельный: product-работу не блокирует.**
      Ревизия 2 сняла с 6C роль предусловия PLAN-6E: skills discovery
      verification для Codex невыполнима (Codex не установлен) и больше не
      блокирует reviewer — см. PLAN-6E;
    - **installed-package defect C25 и `scripts/` (C18) закрывает PLAN-L4**, а
      не 6C: их носители удаляются вместе с legacy-стеком. За 6C остаётся
      distribution boundary `tools/` (C26) и dependency ownership;
    - read-only по `pyproject.toml`, `requirements.txt`, `requirements.lock`,
      CI/task/config files, Anime/ML optional dependencies, `venv/`,
      MOSS/Whisper/model weights и agent-specific adapters;
    - обновляется только `docs/current/CLEANUP_REGISTRY.md`;
    - фиксируются direct/resolved/optional/toolchain owners, callers,
      воспроизводимость, replacement и exit conditions до package
      consolidation;
    - **обязательная проверка installed-package defect (registry C25).**
      [FACT] `py-modules = ["pipeline"]` включает `pipeline.py` в дистрибутив,
      `packages.find.include` не содержит `scripts*`, а `pipeline.py:9`
      импортирует `scripts.test_moss_voices`. [INFERENCE] non-editable
      установка ломает `import pipeline`; `pip install .` не выполнялся, и CI
      это не ловит, потому что использует `--editable`. Проверяется сборкой
      wheel и импортом в temporary venv вне checkout; требует отдельного
      разрешения на установку. Это прямой блокер критерия PLAN-15
      «installed package из произвольного temporary checkout»;
    - **обязательное решение по intended distribution boundary `tools/`
      (registry C26).** [FACT] `tools*` не входит в `packages.find.include`;
      все известные callers находятся внутри checkout. Отсутствие в wheel
      **не является дефектом по умолчанию**. Если решение — «только checkout»,
      правка идёт в формулировку `AGENTS.md`, а не в `pyproject.toml`.
      Добавлять `tools*` в wheel только ради того, чтобы repository QA
      работал из установленного пакета, запрещено;
    - **обязательная skills discovery verification (совместно с PLAN-6E).**
      Различать четыре разных состояния: наличие файлов, manual loading,
      auto-discovery, actual invocation. [FACT] Claude Code не обнаруживает
      корневой `skills/` автоматически: `.claude/` содержит только
      `settings.json`, `settings.local.json` и `scheduled_tasks.lock`.
      **[ПРЕДП]** утверждение «Codex обнаруживает эти skills через
      `skills/*/agents/openai.yaml`» не проверено: Codex в среде не установлен,
      discovery-check не выполнялся, tracked codex-конфигов в репозитории нет.
      Наличие `agents/openai.yaml` не является доказательством discovery.
      Проверка: получить фактический список project skills установленного
      Codex; выполнить явный вызов одного repo skill; определить обнаруженный
      path; проверить фактическую роль `agents/openai.yaml`; сравнить корневой
      `skills/` со стандартным discovery path. **До получения результата
      второй набор skills не создаётся.**
  - **PLAN-6D — scope control foundation:** см. отдельный раздел ниже;
  - **PLAN-6E — independent reviewer foundation:** см. отдельный раздел ниже.
- **измеримый результат:** docs QA зелёный при новых правилах; `AGENTS.md`
  в районе ста строк; первый minimalism report сохранён как baseline;
  dependency/toolchain решения известны до PLAN-13C и PLAN-14B; scope-контроль
  и независимый reviewer существуют технически, а не только в тексте правил.
- **required verification:** PLAN-6A — docs QA + `full`; PLAN-6B — targeted
  tests detector + docs QA; PLAN-6C — docs QA; PLAN-6D — targeted tests
  `check_task_scope` + docs QA; PLAN-6E — docs QA; `git diff --check` всегда.
- **rollback:** один commit на под-slice.

### PLAN-6D — scope control foundation

- **status:** completed · **completed:** 2026-08-02 · **commit:** Git log —
  commits `397d338` (PLAN-6D-1), `10dd555` (PLAN-6D-2) и trailer
  `Plan-Step: PLAN-6D-3` для завершающего commit.
- **цель:** перевести защиту от выхода за scope и от порчи пользовательских
  данных с уровня «агент помнит правило» на уровень технического ограничения.
- **роль в ревизии 2.1:** **BLOCKER первого multi-owner implementation slice**
  — по фактическим footprint'ам это PLAN-9B-2 (`query_adapter` +
  `script_generator` + `visual_planning` + `semantic_selection`). Для PLAN-9B-0
  (один новый test-модуль) и PLAN-9B-1 (один модуль и его тесты) allowlist
  тривиален и проверяется глазами.
- **зависимости:** PLAN-6A — **ordering convention, не техническая
  необходимость** (ревизия 2.1): 6D-1 пишет `.claude/settings.json`, 6D-2
  создаёт `tools/qa/check_task_scope.py`, 6D-3 правит `CLAUDE.md`, и ни одному
  из них не требуется, чтобы R1–R12 уже лежали в `AGENTS.md`. **Исправлено
  ревизией 2:** прежняя зависимость от
  PLAN-6C возвращала параллельные 6B и 6C в критический путь через 6D и
  противоречила разделению «блокируют только 6A, 6D и 6E». Содержательной
  зависимости от dependency/toolchain аудита у 6D нет; единственное касание 6C —
  Codex-часть skills discovery, которая в `CLAUDE.md` не записывается (6D-3).
- **разрешённые зоны:** `.claude/settings.json`, `CLAUDE.md`,
  `tools/qa/check_task_scope.py` и его targeted tests.
- **запрещено:** production-код, создание hooks, создание `.claude/skills/`,
  дублирование содержимого `skills/` в adapter-файлах, блокировка versioned
  resources, fixtures, `.gitkeep` и документации.
- **evidence, на котором построен slice** (проверено 2026-07-30 от clean HEAD
  `2379444`): механизма сравнения allowlist задачи с фактическим Git diff в
  репозитории нет; единственный QA-модуль — `tools/qa/check_agent_docs.py`;
  hooks, `.claude/agents/`, `.claude/skills/` и git-hooks отсутствуют.
- **bounded под-slices:**
  - **6D-1 — permissions: четыре раздельных класса действий.** Классы не
    смешиваются. **status: completed 2026-08-02.** **Исправлено ревизией 2:**
    прежняя редакция ставила permanent
    hard deny на `projects/**`, `music/**`, `assets/library/**`,
    `assets/cache/**`, `anime_factory/episodes/**`. Владелец объявил это
    тестовое runtime-медиа disposable, а PLAN-14E обязан его удалить — правило
    пришлось бы обходить ради собственного утверждённого шага. Permission,
    которое придётся обходить, защитой не является.
    - *Hard deny — вечное:* secrets — существующие `.env`/credentials/pem/key
      плюс `Write` и `Edit` по `.env`;
      destructive Git — `reset --hard`, `clean` по непроверенным путям, force
      operations, включая починку голого `git clean`, который текущий шаблон
      `Bash(git clean *)` не ловит; удаление реальных user data, **не**
      классифицированных владельцем как disposable.
    - *Scope / explicit cleanup authorization:* legacy и test runtime/media,
      уже объявленные disposable, — `projects/**`, `music/**`,
      `assets/library/**`, `assets/cache/**`, `anime_factory/episodes/**`.
      Вне своего bounded cleanup slice эти пути остаются закрытыми; удаление
      разрешено **только** внутри PLAN-14C/14D/14E (или PLAN-L для legacy
      носителей), только по проверенному абсолютному пути и только после
      сверки с `Preserved runtime corpus` в `CLEANUP_REGISTRY.md`.
      Классификация «disposable» **не** является разрешением удалить: она лишь
      снимает вечность запрета.
    - *Смешанные каталоги:* `outputs/**` и `manual_assets/**` **не**
      блокируются целиком — под ними лежат tracked versioned-файлы. Для них
      используются точные подпути или типы runtime-файлов. `channels/**` и
      `content/**` не блокируются вовсе.
    - *Ask / explicit owner approval:* `git push`, создание remote,
      `git stash`, `git commit --amend`, сеть, provider search/download и
      paid API. Бессрочный hard deny для них не применяется, если permission
      system поддерживает ask-policy. Поддержка ключа `ask` проверяется внутри
      этого под-slice до записи правил; если ключ недоступен, эти действия
      остаются instruction-level требованием и в hard deny **не** переводятся.
    - *Записанная граница:* Claude permissions не защищают от произвольного
      Python-кода, запущенного через Bash. Выдавать deny-list за полную защиту
      запрещено.
    - *Limitation и fallback для scope-класса:* `.claude/settings.json` не
      знает, какой plan-step выполняется, поэтому «deny везде, кроме
      утверждённого cleanup slice» декларативно не выражается. Проверяется
      внутри под-slice: если доступен `ask`, disposable-пути получают `ask`, а
      не `deny`; если `ask` недоступен — они остаются в `deny`, и cleanup slice
      снимает правило **своим** commit, а не обходит его. Постоянный `deny`,
      который исполнитель PLAN-14E обязан обойти, не записывается: это ложная
      защита. Фактическую границу удержания держат `check_task_scope` (6D-2),
      `Preserved runtime corpus` и требование абсолютного пути.
    - *Почему не hook:* `.claude/settings.json` уже является владельцем этого
      ограничения и покрывает требуемое декларативно. Hook стал бы вторым
      владельцем одного правила.
    - *Фактический результат:* локальный Claude Code 2.1.219 подтвердил
      поддержку `permissions.ask` и распарсил итоговый settings. Permanent
      deny ограничен точными secret families для Read/Write/Edit,
      `git reset --hard`, bare/flagged `git clean`, force push и существующим
      `media-library migrate --apply`. Поддерживаемые ask rules добавлены для
      push/remote-add/stash/amend, WebFetch/WebSearch и перечисленных
      recursive cleanup primitives. Пять scope-controlled families и четыре
      mixed directories broad path rules не получили.
    - *Оставшееся instruction-level:* arbitrary Python/PowerShell/Bash не
      позволяет надёжно распознать любой network/provider/paid вызов или
      условие «только в активном cleanup slice». Эти границы продолжают
      удерживать owner approval, проверенный абсолютный путь и
      `Preserved runtime corpus`; частичные эвристики не добавлялись.
    - *Verification evidence (2026-08-02, исходный HEAD `3ee4e98`):*
      `python -m json.tool` и локальный Claude parser — exit code 0;
      permission structure — 15 ask и 43 deny rules; full tracked-path
      collision probe — 0; `.env` покрыт Read/Write/Edit; `.env.example` и
      `src/localization/secrets.py` имеют 0 deny matches; destructive Git и
      ask command probes зелёные; docs QA, onboarding tests и
      `git diff --check` — exit code 0. Production code, tests, hooks, agents,
      skills, tools и runtime data не менялись; сеть и платные действия не
      выполнялись.

#### PLAN-6D-2 — task-scope checker

- **status:** completed 2026-08-02.
- **CLI:** `python -m tools.qa.check_task_scope [--root REPO] --allow PATH
  [--allow PATH ...] [--allow-dir DIR ...]`. `--allow` означает exact
  repository path; `--allow-dir` — явный component-bounded directory scope.
- **contract:** allowlist передаётся конкретной задачей; рабочее дерево
  читается через `git --no-optional-locks status --porcelain=v1 -z
  --untracked-files=all --renames`. Учитываются staged и unstaged изменения,
  untracked, add, delete и rename; rename разрешён только когда разрешены old и
  new path. Неожиданный путь даёт `STOP_REQUIRED` и требует остановки/owner
  decision. Статусы `OK` / `STOP_REQUIRED` / `INVALID_INPUT` имеют exit codes
  0 / 1 / 2. Порядок rules, changes и unexpected paths стабилен.
- **path policy:** `\` и `/`, `.` и duplicate separators нормализуются;
  сравнение на Windows case-insensitive. Абсолютный путь принимается только
  внутри repository root; traversal, drive-relative path, путь вне root и
  разрешение всего root отклоняются. Простого строкового prefix нет:
  `src/news` не разрешает `src/news_backup`. Glob patterns не реализованы.
- **read-only boundary:** checker не читает содержимое изменённых файлов, не
  исправляет diff, не меняет index/worktree, не выполняет staging/commit и не
  хранит постоянного глобального списка файлов всех задач. Активный execution
  plan разрешён только когда вызывающая задача передала его путь.
- **residual limitations:** это working-tree scope checker, не commit-range
  reviewer PLAN-6E; он вызывается явно, а не hook/harness; ignored paths не
  входят в change set, который Git сообщает как working-tree status; rename
  classification использует read-only Git rename detection.
- **verification evidence:** `tests.test_check_task_scope` — 26 тестов,
  exit code 0: empty/allowed/unexpected, modified/added/deleted/renamed,
  staged/unstaged/untracked, обе стороны rename, stable multi-path output,
  Windows separators/case, boundary, traversal, inside/outside absolute paths,
  duplicate rules, Git failure, CLI statuses/exit codes и побайтовая
  неизменность временного `.git/index`. Current-diff smoke — `OK/0`; synthetic
  temporary Git smoke с unexpected path — `STOP_REQUIRED/1`; CLI help, docs
  QA, onboarding tests, `compileall tools\qa` и `git diff --check` — exit code
  0. Full offline suite не запускался: production/runtime behavior не менялся.

  *Owner:* пакет `tools/qa` уже является владельцем QA. Модуль
  `check_agent_docs.py` расширить нельзя: у него другой вход (статические
  инварианты репозитория против allowlist конкретной задачи) и другой
  lifecycle. Прецедент sibling-модуля уже утверждён в PLAN-6B
  (`check_repository_minimalism.py`), поэтому второго source of truth не
  возникает. *Exit condition:* модуль удаляется, если scope-контроль станет
  частью harness.

#### PLAN-6D-3 — Claude skill loading note

- **status:** completed 2026-08-02.
- **scope:** `CLAUDE.md`. Одно предложение о том, что `skills/` не
  загружаются автоматически и релевантный `SKILL.md` нужно открыть перед
  задачей. Содержимое skills не дублируется. `.claude/skills/` не создаётся:
  это был бы второй набор skills и нарушение ADR 0001.
  **Границы утверждения:** формулировка про отсутствие auto-discovery
  доказана для Claude Code [FACT]. Утверждение о поведении Codex в
  `CLAUDE.md` не записывается до skills discovery verification PLAN-6C/6E:
  оно пока имеет статус **[ПРЕДП]**.
- **фактический результат:** `CLAUDE.md` сохранил роль тонкого adapter и
  добавил только короткое правило: root `skills/` не считается автоматически
  загруженным; перед специализированной задачей Claude Code вручную открывает
  релевантный `skills/<skill-name>/SKILL.md`, применяет его вместе с
  `AGENTS.md`, актуальными repository docs, кодом и тестами, а фактическое
  состояние репозитория имеет приоритет над предположениями skill. Перечень и
  workflows skills не копировались; `.claude/skills/` не создан;
  Codex discovery не описывался.
- **verification evidence:** `check_task_scope` с разрешёнными `CLAUDE.md` и
  тремя current docs вернул `OK/0`; docs QA,
  `tests.test_stage2_agent_onboarding` и `git diff --check` завершились с exit
  code 0. Фактически существуют шесть root skills, `.claude/skills/`
  отсутствует; skills/tools/tests/src не менялись.
- **измеримый результат:** deny/ask отражают проверенные пути и не блокируют ни
  один tracked versioned-файл; `check_task_scope` возвращает `STOP_REQUIRED` на
  неожиданный файл и `OK` на разрешённый; `CLAUDE.md` объясняет загрузку
  skills; ни одного нового hook, agent или документа не создано.
- **required verification:** targeted tests `check_task_scope`, docs QA,
  `git diff --check`.
- **rollback:** один commit на под-slice.

### PLAN-6E — independent reviewer foundation

- **status:** completed · **completed:** 2026-08-02 · **commit:** Git log,
  trailer `Plan-Step: PLAN-6E`
- **цель:** один независимый read-only reviewer до первого destructive и
  high-risk production-slice.
- **роль в ревизии 2.1:** **BLOCKER первого destructive retirement / high-risk
  shared-contract slice** — PLAN-9B-2 (orca-hardcode с собственным тестом),
  PLAN-9B-3 (query-path cleanup), PLAN-9B-5b (retirement `apps/news_to_short`,
  у которого есть test-callers). **Дополнительно обязателен для PLAN-9A**
  (persisted bytes) **и PLAN-9C** (semantic decision path) — обе позиции уже
  входят в список «когда reviewer обязателен» ниже. Для PLAN-9B-0/9B-1
  необязателен: они не пересекают ни одну из этих boundary.
- **зависимости:** PLAN-6D. **Не является** blocker первого product fix.
- **разрешённые зоны:** `skills/review-change/`, `.claude/agents/`,
  `tools/qa/check_agent_docs.py` в части регистрации нового skill.
- **запрещено:** production-код, раздельные review policies для Claude и
  Codex, orchestrator, постоянная команда агентов, reviewer, исправляющий
  собственный finding.
- **обязательный порядок:** сначала доказать overlap с существующими skills.
  Новый owner создаётся только если ни один существующий skill не может быть
  безопасно доработан. `skills/architecture-change` для этого не подходит: он
  принадлежит implementer, и расширение сделало бы implementer собственным
  reviewer.
- **предусловие — разделено ревизией 2 (снят deadlock).** Прежняя формулировка
  блокировала 6E на skills discovery verification для Codex внутри PLAN-6C.
  [FACT] Codex в среде не установлен, discovery-check выполнить невозможно, а
  6E обязателен до PLAN-9A — план не мог продвинуться. Теперь:
  - **Claude-часть выполнима и обязательна сейчас.** [FACT] `skills/` не
    является `.claude/skills/`, auto-discovery нет: создаётся canonical
    `skills/review-change/SKILL.md` и тонкий adapter
    `.claude/agents/review-change.md`, поведение подтверждается controlled
    read-only acceptance ниже;
  - **Codex-adapter остаётся `[ПРЕДП]`** до фактической проверки discovery и
    6E не блокирует. Второй набор skills не создаётся ни при каком результате.
- **canonical policy — одна, model-independent:**
  - `skills/review-change/SKILL.md` — единственный источник review rules;
  - `skills/review-change/agents/openai.yaml` — тонкий adapter для Codex по уже
    существующему в репозитории шаблону;
  - `.claude/agents/review-change.md` — тонкий adapter для Claude, который
    ссылается на canonical skill и не дублирует правила.
- **поведение reviewer:** работает read-only; проверяет конкретный immutable
  commit или явно заданный diff; не редактирует файлы; не исправляет findings;
  не создаёт commit; не обновляет этот план; не меняет checkpoint; выдаёт
  findings по severity с `file:line`, evidence, impact и smallest safe
  correction; отдельно перечисляет executed checks, skipped checks и residual
  risks; проверяет task scope, duplicate owner, compatibility, persisted state,
  paid/network behavior и фактическую эффективность тестов; после repair
  выполняет повторный review.
- **разделение ролей (уточнено ревизией 2).** Implementer **активно ищет лучший
  способ** решить задачу, свободен внутри allowed scope, вправе оспорить план и
  предложить альтернативу. Reviewer работает **консервативно**: ищет нарушения,
  duplicate owner, contract break, architecture drift, unsafe data handling,
  rights violations, unverified success, regression. Implementer и reviewer не
  являются одним контекстом; repair выполняет implementer после подтверждения
  findings владельцем.
- **обязательный класс findings «unmet objective / premature stop».** Reviewer
  проверяет не только нарушения, но и обратное: не остановился ли implementer на
  соблюдении процедуры, не достигнув SUCCESS CRITERIA и не попытавшись найти
  альтернативу. Без этого класса reviewer не ловит именно тот сбой, ради
  которого пересмотрена модель автономии.
- **техническое подтверждение read-only, определяется до реализации:**
  отсутствие Write/Edit в наборе инструментов adapter; безопасный набор
  read-only Git/search команд; сравнение `git status` и `git diff` до и после
  review. Review считается неуспешным, если working tree изменён reviewer-ом.
- **когда reviewer обязателен:** persisted state, manifests, resume, providers,
  asset selection, semantic/Vision, rights/provenance, paid/TTS, rendering,
  package boundaries, shared contracts, compatibility retirement, runtime
  migration. Для простой Markdown-правки не требуется.
- **измеримый результат:** существует ровно одна canonical review policy и не
  более двух тонких adapters; read-only подтверждается технически, а не
  обещанием; reviewer не может закрыть собственный finding.
- **controlled read-only acceptance (обязательна).** `docs QA` и
  `git diff --check` доказывают только целостность документов: `--check` ищет
  whitespace-ошибки и конфликтные маркеры и не сравнивает состояние дерева.
  Поэтому поведение reviewer проверяется отдельной контролируемой процедурой,
  результат которой записывается как evidence слайса:
  1. зафиксировать `git status --short --branch` и `git diff --stat` до review;
  2. запустить reviewer на конкретном immutable commit;
  3. повторно снять `git status` и `git diff` и доказать отсутствие изменений;
  4. прогнать один заведомо безопасный diff — ожидается отсутствие findings
     или только информационные;
  5. прогнать один synthetic diff с известным нарушением — ожидается, что
     нарушение найдено с `file:line`, evidence, impact и smallest safe
     correction;
  6. подтвердить, что reviewer нарушение **не исправил**, файлов не изменил и
     commit не создал.
  Review считается неуспешным, если working tree изменён reviewer-ом.
  Synthetic diff создаётся во временном каталоге вне репозитория и в Git не
  попадает. Отдельная автоматизация и новый QA-модуль для этого не создаются:
  процедура выполняется один раз при закрытии слайса.
- **реализовано:** canonical owner — `skills/review-change/SKILL.md`; тонкие
  adapters — `skills/review-change/agents/openai.yaml` и
  `.claude/agents/review-change.md`. Claude adapter использует `model: sonnet`,
  `permissionMode: plan`, только `Read/Glob/Grep/Bash` и прямо запрещает
  Write/Edit, сеть и repair. Canonical policy требует независимый контекст,
  read-only before/after proof, review scope/objective, duplicate owners,
  compatibility, persisted/network/rights boundaries, tests, findings и
  повторный review после repair. Для Git-read launcher устанавливает
  `GIT_OPTIONAL_LOCKS=0`, а reviewer использует `git --no-optional-locks`.
- **QA contract:** `tools.qa.check_agent_docs` регистрирует седьмой skill,
  проверяет обязательные canonical/adapter поля, точный read-only toolset,
  отсутствие дублирования policy и обязательное отключение optional Git locks.
  `tests.test_check_agent_docs` содержит positive и negative characterization.
- **controlled acceptance evidence (2026-08-02):** Claude Code 2.1.218,
  `--model sonnet --effort high`; фактически выбран `claude-sonnet-5`. Сеть была
  разрешена только к Anthropic; WebSearch/WebFetch, другие providers, downloads,
  Vision, TTS и render не выполнялись.
  - Case A на immutable commit `619c817cb1d7234799a32c8fd7d567633b2b470b`:
    первый model-run вернул PASS без findings, но launcher доказал изменение
    только `.git/index` stat cache при неизменных HEAD/status/diff. Acceptance
    объявлена FAIL; policy и adapter дополнены обязательным отключением optional
    locks. Свежая независимая re-review session после repair вернула PASS/PASS,
    findings `[]`; HEAD, porcelain, staged/unstaged diff и байты/mtime index
    совпали до/после.
  - Case B во внешнем временном synthetic repository: безопасный bounded diff
    принят, findings `[]`, scope PASS, objective PASS; authoritative launcher
    подтвердил byte-stable index и неизменные HEAD/status/diff.
  - Case C в отдельном внешнем synthetic repository: неизвестное reviewer-у
    нарушение найдено как BLOCKER в новом `src/second_owner.py`; evidence —
    второй owner нормализации вне allowed scope с расходящейся семантикой;
    smallest safe correction — удалить весь hunk. Scope/objective — FAIL/FAIL;
    launcher подтвердил, что reviewer ничего не исправил и repository не изменил.
  - Repair cycle выполнен новым Claude session; shell-capability остаётся
    residual risk, сдерживаемый exact tool allowlist, plan mode, запретом сети и
    внешним byte-level proof. Два ранних `--json-schema` запуска завершились
    локальной parser-ошибкой до model call; successful model calls — четыре,
    суммарная reported cost `$1.4021283`.
- **verification evidence:** `tests.test_check_agent_docs` — 58 тестов;
  `tests.test_stage2_agent_onboarding` — 3 теста; docs QA,
  `compileall tools\qa`, task-scope checker по восьми разрешённым путям и
  `git diff --check` — exit code 0. Числа тестов — измерения, не нормативы.
- **required verification:** controlled read-only acceptance (шаги 1–6),
  docs QA, `git diff --check`.
- **rollback:** один commit.

### PLAN-7 — канонический пользовательский CLI в документации

- **status:** pending · **completed:** — · **commit:** —
- **частичное исполнение вне слайса (учёт 2026-08-13, статус не меняется).**
  Две из четырёх зон уже приведены в целевое состояние отдельными docs-only
  commits, и это записано здесь, чтобы шаг не выглядел нетронутым: `README.md`
  переписан по факту кода до 174 строк commit `1f67e29`, а `COMMANDS.md`
  **удалён** commit AUD-DELTA-CLOSE по **OD-S-7** — без замены, canonical
  command reference остаётся `python -m ai_youtube --help`. Проверено, что ни
  один оставшийся документ не ссылается на него как на current source:
  упоминания живут только в `docs/archive/**`, `docs/audits/**`, в контракте
  этого шага и в исторических измерениях — historical evidence массово не
  переписывается. Шаг **остаётся pending**: три `skills/*/SKILL.md`
  (`create-short-video-first`, `resume-project`, `replace-visual-slot`) всё ещё
  учат `python -m src.content_creation.cli`, упоминаний `ai_youtube` в skills
  ноль, и `docs/contracts/STAGE1_PUBLIC_CONTRACTS.md` получил только баннер, а
  не правку утверждений. Оставшийся объём и есть PLAN-7.
- **цель:** документация перестаёт обучать устаревшему entrypoint.
- **зависимости:** PLAN-6A. **Параллельный: product-работу не блокирует**
  (изменено ревизией 2).
- **взаимодействие с PLAN-L.** L4 удаляет `pipeline.py`, поэтому 24 упоминания
  `pipeline.py` в `COMMANDS.md` исчезают как факт, а не переписываются. Если L4
  выполнен раньше PLAN-7 — сверять по фактическому `--help`, а не по этому
  списку.
- **язык (OD-5).** `README.md` сокращается примерно до 150 строк; русская
  редакция получается **побочно при переписывании**, отдельным переводом это не
  оформляется и mass-diff не создаёт. Правило: не переводить filenames,
  directory names, identifiers, CLI/API, JSON/YAML keys, точные команды, имена
  библиотек, литералы, блоки кода, third-party licenses и historical artifacts.
  Каталоги `docs/archive/`, `docs/audits/` и `docs/implementation/` в scope
  перевода не входят как historical.
- **исправлено owner decision 2026-08-05 (OD-S-7).** Прежнее требование
  «`COMMANDS.md` — 100–150 строк» отменено: файл **удаляется**, а не
  сокращается. Новый контракт:
  - canonical command reference — `python -m ai_youtube --help`;
  - quick start — `README.md` (около 150 строк: фактический продукт,
    active/planned/disabled, быстрый старт);
  - workflows — существующие `skills/`;
  - contracts — канонический CLI;
  - `COMMANDS.md` — deletion target;
  - **replacement command document запрещён**: второй каталог команд не
    создаётся ни под каким именем;
  - краткая semantics `project rights-report` переносится в существующий
    `skills/replace-visual-slot/SKILL.md`;
  - historical archive/audit evidence массово не переписывается.
- **разрешённые зоны:** `README.md`, `COMMANDS.md` (только удаление),
  `skills/create-short-video-first/SKILL.md`, `skills/resume-project/SKILL.md`,
  `skills/replace-visual-slot/SKILL.md`,
  `docs/contracts/STAGE1_PUBLIC_CONTRACTS.md`.
- **запрещено:** production-код, **удаление старых entrypoints**, создание
  нового command-каталога взамен `COMMANDS.md`.
- **требования:** команды сверять с фактическим `--help`, а не по памяти; после
  удаления `COMMANDS.md` ни один оставшийся документ не должен на него
  ссылаться как на current source.
- **измеренный масштаб расхождения** (Foundation audit, [FACT] от `4ca3655`):
  `README.md` — 405 строк, упоминаний `ai_youtube` **0**, учит bare `python`
  и `pip` вопреки `AGENTS.md`; `COMMANDS.md` — 681 строка, упоминаний
  `ai_youtube` **0** против 49 × `src.content_creation.cli` и 24 ×
  `pipeline.py`; три `SKILL.md` учат `src.content_creation.cli`;
  `docs/contracts/STAGE1_PUBLIC_CONTRACTS.md` называет
  `src.content_creation.cli` «current CLI» и канонический CLI не упоминает.
  Это измерение, а не норма.
- **`docs/contracts/` — порядок:** файл добавлен в зоны потому, что обучает
  устаревшему entrypoint и до сих пор не входил ни в один slice (registry
  C22). Его **target responsibility** решает PLAN-12E по содержимому; PLAN-7
  правит только утверждения о каноническом CLI и не перемещает файл.
- **измеримый результат:** ни один из этих файлов не обучает устаревшему пути.
- **required verification:** docs QA + `smoke`.
- **rollback:** один commit.

### PLAN-8 — PRODUCT_PLAN.md

- **status:** pending · **completed:** — · **commit:** —
- **цель:** отделить продуктовую цель и evidence от архитектурного порядка.
- **зависимости:** PLAN-7. **Параллельный: product-работу не блокирует**
  (изменено ревизией 2 — прежде PLAN-8 стоял в prerequisite-цепочке 9A).
- **разрешённые зоны:** `docs/current/PRODUCT_PLAN.md`.
- **запрещено:** создание `ARCHITECTURE_DEBT.md` до того, как PLAN-1 докажет
  фактический пробел относительно `CLEANUP_REGISTRY.md`.
- **измеримый результат:** продуктовый приоритет, измеренная база и критерии
  M1/M2/M3 зафиксированы; отдельно записан post-rescue roadmap:
  `video_repurposer` через migration Anime Factory и будущий
  longform/documentary workflow `content_creator`, с entry/enable evidence и
  без создания новых engine stacks. Ориентир до 250 строк.
- **обязательные roadmap-записи ревизии 2.1** (PLAN-8 — **roadmap owner**, не
  implementation owner ни одной из них):
  - **post-rescue roadmap `video_repurposer` (OD-23):** Content Creator stable →
    UI Content Creator → отдельный deep audit Anime Factory → классификация
    каждой capability `KEEP · MIGRATE · REWRITE · SHARE · DELETE` → Video
    Repurposer из существующего Anime Factory + shared core → его UI. Второй
    clip pipeline с нуля запрещён; deep audit Anime Factory ближайшим шагом
    **не** является;
  - **future AI / advanced editing note (OD-17, OD-20):** `NO IMPLEMENTATION ·
    NO PLACEHOLDER PACKAGES · NO SPECULATIVE INTERFACES · NO NEW BLOCKERS`.
    Future AI layer подключается **сверху** к существующему production
    pipeline: `AI research / script layer → тот же prepared content contract →
    существующий downstream video production engine`. `LLMScriptProvider` уже
    зарегистрирован как `planned` — этой точки подключения достаточно;
  - **future-proofing rule:** downstream production pipeline не должен
    предполагать, что script создан внутри AI-YouTube. Prepared external
    content (человек, внешний AI, ручной ввод) — **first-class input**;
  - **product-quality item «несколько lossy generations в final render»**
    (registry C45). Фактический нормальный путь: segment encode CRF 23 →
    concat **`-c:v copy`** → audio + exact-duration encode CRF 20 → ASS
    subtitle encode CRF 21 → copies. Concat **не перекодирует**; CRF 20
    принадлежит duration-control mux и имеет документированную причину
    (`-shortest` + `-c:v copy` промахивается по длительности). Три lossy
    generations возникают при **audio + ASS subtitles**. «Single-pass как
    простой fix» — неверно. Первый разумный кандидат будущего renderer-слайса:
    объединить audio/duration encode и subtitle burn в один encode, **если
    characterization докажет эквивалентность**; полный filtergraph single-pass —
    отдельное более крупное исследование. **PLAN-8 хранит запись; implementation
    owner — будущий bounded renderer slice с characterization первым. Нового
    PLAN-ID сейчас не создаётся.**
    **Уточнено 2026-08-01:** этот «будущий bounded renderer slice» теперь имеет
    предложенную форму — candidate slice `MOTION-CS1` (см. «Unscheduled
    candidate slices — Motion family»). Он остаётся unscheduled и PLAN-ID не
    получает. Дополнительное условие: characterization C45 невозможна без
    baseline visual regression (registry C61), поэтому регрессия идёт первой;
  - **roadmap Motion Design and Multi-Renderer Composition (2026-08-01).**
    PLAN-8 — **roadmap owner** и этого направления тоже, implementation owner —
    нет. Продуктовая запись находится в `PRODUCT_PLAN.md`, раздел «Motion
    Design and Multi-Renderer Composition»; owner decisions — в разделе «Owner
    decisions: motion rendering» этого файла; findings — C53–C62 реестра.
    Обязательное содержание roadmap-записи: несколько специализированных
    авторов кадра при **одном** FFmpeg-сборщике · один `composition_type` —
    один canonical backend · stock FFmpeg path сохраняется и дорабатывается ·
    **новый video pipeline не создаётся** · Node остаётся опциональным с
    безопасным fallback. Longform и horizontal по-прежнему остаются форматом и
    шаблоном поверх общего core, а не отдельным pipeline;
- **решение по отдельному `EVALUATION_STRATEGY`:** принимается **после** того,
  как `PRODUCT_PLAN.md` написан, и **по качественным критериям**, а не по
  объёму файла: отдельная responsibility; отдельные readers; отдельный
  lifecycle; смешение контрактов; routing ambiguity; maintenance coupling.
  Количество строк — measurement и warning signal, оно может подтверждать
  проблему, но само по себе новый файл не создаёт. Числовой порог объёма как
  условие extraction не задаётся.
- **`PRODUCT_PLAN.md` уже существует (слайс PRODUCT-ROADMAP → PRODUCT-PLAN-1,
  2026-08-01).** PLAN-8 **расширяет и проверяет существующий документ** и
  **не создаёт второй competing planning document**: третий плановый документ
  по-прежнему запрещён. Разрешённая зона не меняется — это тот же путь.
  Уже записанные там owner-approved решения (committed capabilities, границы
  Vision, UI direction, MSP direction, warehouse, candidate slices, owner
  decisions pending) при расширении сохраняются, а не переписываются.
  Status, порядок и prerequisites PLAN-8 этим не меняются.
- **зафиксировано продуктовым документом, здесь только как non-goal:** longform
  и documentary остаются **форматом/шаблоном/workspace поверх общего core** и
  не становятся отдельным pipeline или третьим приложением; расширение проверки
  качества по готовому файлу принадлежит существующему quality owner и **новым
  Quality Engine не оформляется**.
- **обязательное завершение:** продуктовые подробности PLAN-9–PLAN-11
  (лестницы, M1/M2/M3, reference domains и quality evidence) переносятся в
  `PRODUCT_PLAN.md`. В этом execution plan остаются только ID, зависимости,
  allowed/prohibited zones, gates, verification и rollback.
  До проверенного переноса текущие подробности не удалять.
- **required verification:** docs QA.
- **rollback:** один commit.

### Продуктовая рамка PLAN-9 и PLAN-10: где именно дыра в asset-search

Зафиксировано ревизией 2, чтобы будущий агент не начал строить то, что уже
построено.

**Не является дырой.** `src/assets/completion/` уже владеет лестницей выбора
`A_exact → B_composite → C_good_context → D_partial → E_generated → F_emergency`
с жёстким фильтром `modes.blocking_reasons` (неизвестные или запрещённые права,
битый файл, `must_avoid`, заявленное противоречие, evidence на другой предмет) и
детерминированным `tie_break_key`, не зависящим от того, какой provider ответил
первым. Rung E — сгенерированная по спецификации сцены диаграмма, rung F —
project-owned нейтральная карточка, которая ничего не утверждает. Это canonical
owner completion-состояний; он сохраняется, пока дальнейшее evidence не докажет
дефект boundary. Второй словарь состояний не вводится.

**Является дырой — всё выше по потоку** (карта исправлена ревизией 2.1: над
генерацией запросов находятся ещё две ступени):

```
prepared content / topic
  → [CRITICAL-2] source material: topic не является материалом; thin input
                 молча уходит в LegacyTemplateScriptProvider, а
                 script_validation остаётся "passed"
  → research     (в текущем scope дефектом не является)
  → script       (DeterministicScriptProvider исправен при наличии материала)
  → visual plan  (intents на языке сценария; translation_required выставляется
                  и никем не читается)
  → [CRITICAL-1] provider language: единственный канал доставки английского
                 запроса — visual_brief, а заполняет его только topic-hardcode.
                 GLOSSARY матчится подстрокой → ложные срабатывания и
                 морфологические пропуски. source_is_latin — свойство набора,
                 поэтому английский alternative выбрасывается вместе с русским
  → providers    (нет pagination — PLAN-10B/10C; эффект только после CRITICAL-1)
  → semantic     (metadata-слой РЕШАЕТ; платный Vision подаёт evidence поздно —
                  PLAN-9C)
  → completion   (работает; canonical owner; не трогать)
```

| Что | Owner-слайс |
|---|---|
| честность источника сценария (`topic` → template) | **PLAN-9B-4** |
| канонический вход «исходный текст» | **PLAN-9B-5a** |
| integrity provider-language query adapter | **PLAN-9B-1** |
| provider-language VisualBrief producer | **PLAN-9B-PRODUCER** |
| лестница расширения и снятие topic-hardcodes | **PLAN-9B-2** |
| retirement устаревших query-путей | **PLAN-9B-3** |
| semantic/Vision producer → existing consumer wiring | PLAN-9C |
| best-so-far persistence через `resume` | PLAN-9A |
| ledger попыток и причины остановки | PLAN-10A |
| pagination и provider exhaustion | PLAN-10B |
| adaptive budget, plateau, порядок эскалации | PLAN-10C |
| global local stock library convergence | PLAN-10D |
| альтернативная правдивая визуальная стратегия | PLAN-9B + PLAN-10C |

**Скрытая связь двух findings.** Сегодня шаблонный сценарий не доезжает до
publish только потому, что все сцены `missing` из-за CRITICAL-1. Как только
CRITICAL-1 починят, шаблонный сценарий поедет в publish беспрепятственно.
Поэтому CRITICAL-2 **не откладывается** за CRITICAL-1, а идёт внутри той же
цепочки PLAN-9B.

**Hard constraints отбора** (класс `[HARD]`, не предмет торга ни при каком
качестве): factual truth · rights и provenance · `must_avoid` ·
misleading/conflict · paid approval.

**Heuristics отбора** (класс `[HINT]`, агент вправе изменить с обоснованием,
пока не доказано обратное): приоритет провайдеров · число и виды запросов ·
пороги `minimum_confidence` и `hard_reject_confidence` · предпочтительный тип
визуала для сцены · размер shortlist.

### PLAN-9A — best-so-far foundation и tolerant persistence/resume

- **status:** pending / not started · **commit:** — (bounded corrections
  `1bf7ecc`/`c9537fa`/`a7bec3c`/`2577307` closed inside this section; full
  contract not started). Prerequisite chain
  выполнена целиком 2026-08-07 (`PLAN-9B-2` closed, `PLAN-1C′` closed,
  `PLAN-6E` completed). Прежняя формулировка «текущим checkpoint становится
  PLAN-9C» устарела: PLAN-9C закрыт 2026-08-08, и по действующему route
  (`PLAN-9D → PLAN-9A → PLAN-10A → PLAN-10B → PLAN-10C → PLAN-9E`) текущим
  checkpoint остаётся **PLAN-9D**, а не этот шаг. Исправлено сверкой
  2026-08-11.
- **bounded corrections до полного контракта (сверка 2026-08-11).** Этот owner
  принимает три post-audit correction, не начиная свой полный contract:
  **VA-NEW-02** (M1-B, source-snapshot identity preview cache), **VA-NEW-04**
  (M1-C, review artifact A→B rebind) и **VA-NEW-08** (M1-D, resume
  fingerprints); **VA-NEW-05** (M1-C, Vision-tag carry) идёт пакетом с 04.
  Таблица классов и порядок — блок «Mini plan reconciliation 2026-08-11».
  Уже выданный этому шагу persisted approval покрывает только перечисленный
  ниже состав полей: `replaces_asset_id` вышел за этот состав, и owner
  decision на него выдан и закрыт (M1-C, commit `c9537fa`, Review #1 ACCEPT
  2026-08-11); resume fingerprint (M1-D) также вышел за этот состав, его owner
  decision выдан текстом M1-D prompt и закрыт — состав полей, два declared
  boundary и fail-safe записаны в блоке «M1-D CLOSURE».
- **bounded correction VA-NEW-23 (RD-A, 2026-08-12) — closed.** Тот же
  selected-asset lineage family, что и VA-NEW-04: review bundle не имеет права
  называть выбранным то, чего не показал. Ассет, найденный после заморозки
  review window (download retry, draft-completion ladder), теперь попадает в тот
  же `shortlist`, который рендерит доска, а честный abstention остаётся
  abstention и в bundle, и в `selected_candidate_before/after_rerank`. Additive:
  новых persisted полей, schema-version bump и миграции нет, полный contract
  PLAN-9A этим не начат. Детали — блок «RD-A CLOSURE».
- **prerequisite chain (единственная действующая, ревизия 2.1):**
  `PLAN-9B-2` + `PLAN-1C′` + **`PLAN-6E`**. Прежняя цепочка
  `…PLAN-5 → PLAN-6A → PLAN-6D → PLAN-6E → PLAN-1C′` отменена ревизией 2.1:
  PLAN-5 и PLAN-6A параллельны, PLAN-6D входит транзитивно как предусловие
  PLAN-9B-2, а PLAN-6E записан **явно** из-за persisted-state boundary, а не
  транзитивно. Отдельный owner approval на сам слайс не требуется, потому что он
  **уже выдан**: persisted-bytes tripwire срабатывает, и утверждение ревизии 2
  покрывает его ровно в описанном здесь объёме — см. «Decision rights → Уже
  выданные owner approvals». Tripwire этим не отменён: любое
  persisted-изменение сверх состава и ограничений ниже требует нового approval.
- **изменено ревизией 2.1 — только место, не состав.** PLAN-9A выполняется
  **после** PLAN-9B: best-so-far persistence бессмысленна до того, как система
  получает нормальные provider-ready candidates (OD-15). Состав, ограничения,
  additive schema, tolerant reader, уже выданный owner approval и success
  criteria сохраняются дословно. Первым product-слайсом программы становится
  PLAN-9B-0/9B-1.
- **цель:** до расширения поиска гарантировать, что лучший найденный материал
  не теряется между итерациями и при `resume`.
- **состав:** top candidates по сцене, best-so-far с обоснованием, semantic
  score, rights status, Vision/evaluation result, manual approvals, выбранный
  fallback. Расширяет существующие `rejected_candidates`/`rejected_reasons`;
  второй manifest или project system не создаётся.
- **логическая когезия search-session state (OD-24).** PLAN-9A, PLAN-10A,
  PLAN-10B и PLAN-10C логически описывают **одно** состояние одного поиска.
  Это проектное требование, а **не** новый файл: `search_session.json` как
  отдельный persisted owner **не создаётся и не утверждается**; четыре
  независимые persisted schemas заранее не утверждаются. До выбора physical
  representation обязательно проверить существующих owners — `job.json`, asset
  manifest, project state, completion/resume state. **Если существующего owner
  можно расширить, новый persisted файл запрещён.** Разбиение implementation на
  bounded commits когезии не нарушает: она относится к схеме и владению.
- **ограничения:** additive schema/tolerant reader; старые manifests и resume
  читаются без миграции; characterization-first.
- **измеримый результат:** после остановки, ошибки или resume сохранённый
  best-so-far не ухудшается и остаётся объяснимым.
- **required verification:** targeted persisted-contract tests + `full`.
- **rollback:** один commit.

### PLAN-9B — input/query truth (bounded family)

- **status:** in progress — открыт только `PLAN-9B-5b` · **обновлено сверкой
  2026-08-11.** Прежнее `pending` устарело: все capability-под-слайсы
  семейства закрыты — PLAN-9B-0, PLAN-9B-1, PLAN-9B-5a, PLAN-9B-4,
  PLAN-9B-PRODUCER, PLAN-9B-PRODUCER-M, PLAN-9B-PRODUCER-M-LIVE, PLAN-9B-2 и
  PLAN-9B-3. Заголовок-этап не объявляется `completed`, потому что Execution
  protocol п.5 закрывает его только после **всех** под-слайсов, а открытым
  остаётся **PLAN-9B-5b** — отдельный destructive retirement path wrapper'а
  `apps/news_to_short`. Сам этот раздел prerequisite PLAN-9A из него не делает,
  поэтому для потребителей, объявлявших `PLAN-9B` своим blocker, capability-
  содержание семейства **удовлетворено**, и блокировать их может только
  собственный retirement gate PLAN-9B-5b, если он им действительно нужен.
  **Первый product-этап программы** (ревизия 2.1); PLAN-9A его больше не
  блокирует.
- **цель семейства:** **input/query truth — provider-language adaptation,
  query expansion, truthful source input и cleanup старых query paths.**
- **зависимости семейства:** `PLAN-1D-routing → PLAN-2 → PLAN-3 → PLAN-4`.
  Дальнейшие gates — **по risk boundary каждого под-слайса**, см. таблицу
  «Risk-boundary таблица safety gates».
- **новый top-level PLAN-ID не создаётся (E-13):** CRITICAL-2 размещается
  bounded под-слайсами внутри PLAN-9B.
- **порядок выполнения** (идентификаторы под-слайсов — **не** порядок; прецедент
  PLAN-6D/PLAN-12/PLAN-13):

  ```
  PLAN-9B-0 → PLAN-9B-1 → PLAN-9B-5a → PLAN-9B-4
  → PLAN-L0 → PLAN-9B-PRODUCER
  → [post-audit stabilization gate: PLAN-STAB-1…7
     + independent stabilization review] → PLAN-9B-2 → PLAN-9B-3
  PLAN-9B-5b — после успешной миграции capability и готовности его
               destructive gates
  ```

  PLAN-L0 остаётся отдельным knowledge-salvage owner, а
  PLAN-9B-PRODUCER — отдельным visual-planning user outcome; включение их в
  последовательность не смешивает scope трёх слайсов.

- **фактический owner remote-запросов (OD-14).** [FACT]
  `src/assets/semantic_selection/query_generator.py` **не участвует** в
  формировании запросов к remote-провайдерам: его callers питают
  envato-метаданные и отчёты. Единственные точки контакта с провайдером —
  `build_scene_queries` и `build_slot_queries` в `src/assets/query_adapter.py`;
  других путей к remote-провайдеру в активном workflow нет. Прежняя allowed
  zone ревизии 2 была ошибочной и заменена.
- **граница семейства сохраняется:** лестница заканчивается на генерации
  запросов. Переход к локальной медиатеке, к другому provider и к разрешённому
  fallback — routing/completion policy; владельцы — PLAN-10C (порядок
  эскалации), PLAN-10B (provider contract), PLAN-10D (global local library).
- **regression по разным доменам (OD-25):** после каждого существенного
  под-слайса, где это релевантно, проверять репрезентативные темы минимум из
  разных классов (animals/wildlife · energy/technology · geography/
  infrastructure). PLAN-11 остаётся финальным product evidence gate, но не
  первой multi-topic проверкой.
- **тесты T1–T11** из `docs/audits/CRITICAL_INPUT_SEARCH_DEEP_DIVE_2026-07-31.md`
  распределены как regression/product tests по под-слайсам ниже. Отдельный
  диагностический этап под них **не создаётся** (OD-11).
- **отношение к motion-направлению (OD-M-13, добавлено 2026-08-01).** PLAN-9B
  является **стоковой/провайдерской половиной** будущего формата Hybrid
  Explainer, а не его предшественником: гибридная сцена совмещает стоковый
  материал с motion-композицией, и стоковая часть зависит именно от корректных
  provider-запросов. Motion-направление эту семью **не заменяет, не откладывает
  и не ускоряет**; порядок, состав и статусы PLAN-9B этой записью не меняются.
- **rollback:** один commit на под-slice.

#### PLAN-9B-0 — characterization текущего поведения

- **status:** completed · **completed:** 2026-08-01 · **commit:** —
- **зависимости:** PLAN-4.
- **цель:** зафиксировать фактическое поведение **до** правки, чтобы диффы были
  доказуемы. **Ноль production-изменений**, ноль сети, ноль денег.
- **разрешённые зоны:** новый offline test-модуль и evidence в этом плане.
- **фиксируется:** фактическое число provider `search()`-вызовов на тему ·
  source каждого запроса · уникальные отправленные строки, включая ложные
  `ice researchers` и чрезмерно общий `station` · число провайдеров,
  пропущенных по `translation_required` · `legacy_template` при
  `script_validation == passed` · **persisted содержимое `query_plan` до
  изменения** (байты `assets_manifest.json` меняются даже при
  не-schema-level правке).
- **тесты deep-dive:** T10, T11.
- **risk boundary:** нет.
- **required verification:** targeted + активный `network_guard`.
- **зафиксированное текущее поведение:** через canonical application chain
  `create_content → fullscreen_voiceover → run_news_to_short_job →
  build_news_asset_manifest → build_scene_queries → search_provider` пять
  English-only fake providers получили production-built `AssetSearchRequest`.
  Для тем про ворон / солнечную электростанцию / канал через пустыню выполнено
  соответственно 10 / 50 / 10 вызовов `search()`; уникальные строки —
  `ice researchers` / (`station`, `ice researchers station`) /
  `ice researchers`. Source всех отправленных `ProviderQuery` —
  `deterministic_glossary`. Пропущено по `query_translation_required`
  соответственно 25 provider-scene попыток в 5 сценах / 5 попыток в 1 сцене /
  25 попыток в 5 сценах; source пропущенных entries — `visual_brief_fields`.
  Это characterization известных дефектов, а не их исправление.
- **persisted characterization:** тест читает реальный temporary
  `assets/assets_manifest.json`; для каждой темы проверен минимальный subset 30
  `query_plan.queries`, включая provider, query, status, source и
  `untranslatable_providers`. Manifest writer и query builders не patch'ились.
- **input/script characterization:** недостаточный topic-only factual input
  сохраняет `script_provider == "legacy_template"`, metadata
  `fallback_reason == "insufficient_source_material"` и одновременно
  `script_validation.status == "passed"`. Поведение только зафиксировано.
- **фактическая verification (2026-08-01, HEAD до слайса `c4aeff6`):**
  - `.\venv\Scripts\python.exe -B -m unittest
    tests.test_input_query_truth_characterization` — exit code 0 двумя
    последовательными прогонами: 2 теста за 74.191 и 73.016 секунды;
  - `.\venv\Scripts\python.exe -B -m unittest
    tests.test_visual_retrieval_repair tests.test_script_engine_pipeline
    tests.test_news_asset_manager_contract tests.test_content_creation_service`
    — exit code 0, 118 тестов за 26.004 секунды;
  - package-wide `tests/network_guard.py` оставался активным; fake providers не
    выполняют HTTP, `blocked_attempts` не изменился; сеть, download, Vision,
    TTS, paid calls и render не выполнялись;
  - production-код не менялся; full suite не запускался, `baseline_head`
    остаётся `84bdd8b4f64c7adaf7582bdb39b15b18163253fb`.

#### PLAN-9B-1 — provider-language / query foundation

- **status:** completed · **completed:** 2026-08-01 · **зависимости:**
  PLAN-9B-0.
- **фактический owner:** `src/assets/query_adapter.py`.
- **исправленный контракт (owner decision 2026-08-01).** Первоначальный T1
  требовал от adapter-only слайса тематически переводить произвольный raw
  Russian topic и поэтому был невыполним без topic literals, translator/model
  или upstream producer. Он заменён на **T1A:** prepared VisualBrief, explicit
  provider queries и безопасные English intents/alternatives дают несколько
  provider-ready candidates; **T1B:** unknown raw source-language intent без
  такого evidence остаётся fail-closed. PLAN-9B-1 закрывает integrity adapter,
  а **не** создание перевода.
- **разрешённые зоны:** `src/assets/query_adapter.py` и его тесты.
- **reuse (OD-13) — новых сущностей не создаётся:** `VisualBrief` ·
  `SceneVisualPlan` / `VisualSearchIntent` · `ProviderQuery` ·
  `build_scene_queries` / `build_slot_queries` · provider contracts.
  **Не создавать** `TranslatorService`, `SearchEngine`, `QueryOrchestrator` и
  второй query pipeline.
- **реализованный механизм:** explicit provider queries → English VisualBrief
  fields → structured/source intents → bounded deterministic seed. Для каждого
  candidate отдельно определяется фактический язык; затем выполняются Unicode
  NFKC normalization, whitespace/casefold key и stable deduplication. Canonical
  `visual_intents` являются structured provenance; добавленный upstream только
  в flat `alternative_queries` generic legacy broad fallback не считается
  semantic evidence. Для tolerant старых flat plans четыре существующих
  compatibility outputs также не повышаются до успешной adaptation.
- **deterministic seed:** substring matcher заменён Unicode-aware token/phrase
  matcher. Ограниченное suffix matching распознаёт доказанные формы
  `пустыню` / `пустыни` / `пустыней`, но `лед` больше не совпадает внутри
  `исследователи`. Generic roles/modifiers/facilities вроде `researchers` и
  `station` без semantic anchor не выпускаются как успешный query.
- **fail-closed сохранён.** При неуверенности по-прежнему
  `translation_required`, а не догадка. Догадки как factual query не
  отправляются. «Просто отправлять русский текст провайдеру» — откат к уже
  измеренному нулевому результату и запрещён.
- **`ProviderQuery.source` — E-2 закрыт.** Это существующее свободное строковое
  telemetry-поле: **не** schema-level change, tolerant reader не требуется,
  persisted-bytes tripwire не срабатывает. Temporary real
  `assets_manifest.json` подтвердил новые values в существующем `query_plan`
  без нового field/version/layout.
- **T1A/T1B–T5:** T1A — два explicit VisualBrief queries и два structured
  English alternatives реально получены каждым из пяти fake providers;
  normalized duplicate и Cyrillic explicit entry отфильтрованы, sources равны
  `explicit_override` / `provider_supports_source_language`. T1B — raw Russian
  intent с одним generic legacy broad fallback не отправляет fallback и даёт
  `query_translation_required`. T2 — «Исследователи…» не даёт `ice`. T3 — два
  English alternatives переживают Russian primary. T4 — три формы пустыни дают
  `desert` с source `deterministic_glossary`. T5 — unknown intent без evidence
  остаётся `query_translation_required` и не вызывает provider.
- **characterization migration:** query/provider assertions в
  `tests/test_input_query_truth_characterization.py` стали regression contract
  PLAN-9B-1; отдельный topic-only assertion по-прежнему требует
  `legacy_template`, `fallback_reason="insufficient_source_material"` и
  `script_validation.status="passed"` как pre-fix evidence будущего PLAN-9B-4.
  Instrumented canonical measurement: вороны — 0 calls, 30 translation skips;
  солнечная станция — 0 calls, 30 translation skips; канал — 50 fake-provider
  search calls, unique `desert` / `desert researchers`, 25 completed entries с
  source `deterministic_glossary` и 5 translation skips. Это измерение, не
  invariant; ни один случай не выпустил `ice`, misleading `station` или
  `nature science wildlife observation`.
- **оставшийся product gap / follow-up constraint:** arbitrary raw-topic
  provider-language generation **не реализована** и не заявляется. Реальный
  producer должен заполнять существующий VisualBrief contract до product
  evidence gate или утверждения поддержки произвольной русской темы. Точный
  механизм — manual/prepared, local model или optional separately approved
  model — требует отдельного owner decision; новый query owner в этом слайсе не
  создавался. Upstream `legacy_broad_query` не удалён; его окончательный
  retirement остаётся follow-up cleanup после работающей замены.
- **фактическая verification:**
  - `.\venv\Scripts\python.exe -B -m unittest
    tests.test_input_query_truth_characterization` — два окончательных
    последовательных прогона, 3 теста, exit code 0 за 74.852 и 75.004 секунды;
  - `.\venv\Scripts\python.exe -B -m unittest
    tests.test_visual_retrieval_repair tests.test_visual_retrieval_regression
    tests.test_slot_aware_retrieval` — 75 тестов за 1.574 секунды, exit code 0;
  - `.\venv\Scripts\python.exe -B -m unittest
    tests.test_script_engine_pipeline tests.test_news_asset_manager_contract
    tests.test_content_creation_service
    tests.test_news_to_short_provider_integration` — 82 теста за 33.120
    секунды, exit code 0;
  - active package network guard остался чистым; сеть, model/provider API,
    download, Vision, TTS, paid calls и render не выполнялись;
  - full suite не запускался: public signatures и schema/layout не менялись,
    production diff остался внутри одного canonical owner, targeted radius
    зелёный; `baseline_head` остаётся
    `84bdd8b4f64c7adaf7582bdb39b15b18163253fb`.
- **risk boundary:** локальное поведение одного owner; ноль public/paid/
  destructive. Достаточно 1D/2/3/4.
- **required verification:** выполнена targeted verification; full не требовался
  по фактическому diff.

#### PLAN-9B-5a — additive source-text canonical input (CRITICAL-2, часть 1)

- **status:** completed · **completed:** 2026-08-02 · **commit:** — ·
  **зависимости:** PLAN-9B-1.
- **исправлено 2026-08-01 — source text уже частично существует.** [FACT]
  канонический `python -m ai_youtube create` через `--pasted-script` /
  `--script-file` при текущем default/legacy unspecified `content_input_mode`
  уже проводит подготовленный исходный текст в тот же downstream
  (`text` / `text_file` → deterministic/extractive script path). Формулировки
  «канонический CLI не имеет source-text входа» и «`--text`/`--text-file` —
  единственная уникальная capability» **опровергнуты** и не возвращаются.
- **цель (переопределена):** сделать source-material input **явным first-class
  canonical contract**: выбрать owner-approved public naming; убрать
  зависимость от implicit/legacy unspecified mode; валидировать intent;
  документировать; покрыть smoke/test public behavior; сохранить prepared
  external content как first-class input. Слайс **не** создаёт новый script
  engine и **не** создаёт capability с нуля.
- **additive: `apps/news_to_short` в этом слайсе не удаляется.**
- **реализованное owner-approved public naming:** `--source-text` и
  `--source-text-file`. `--pasted-script` и `--script-file` остаются видимыми
  compatibility aliases тех же destinations. `--text` не менялся и остаётся
  Story Card headline. Новые persisted/internal enum-like значения не
  вводились: используются существующие `pasted_script` / `script_file`.
- **normalization/validation owner:** общий
  `src/content_creation/request_builder.py`; только CLI request получает
  explicit mode при source-text input. Legacy programmatic request с
  `content_input_mode=""` остаётся tolerant и проходит прежнюю unspecified
  ветку. Existing `input_validation` проверяет пустой inline input и файл;
  conflicting authoritative inputs и несовместимый `--input-mode` дают
  прежний structured CLI error shape до application service/pipeline.
- **risk boundary:** **PUBLIC CLI SURFACE → отдельный owner approval в момент
  implementation.** Слайс **не** destructive; 6D/6E им не требуются.
- **тесты deep-dive:** T9.
- **required verification:** targeted + smoke (существующими командами) +
  `full`.
- **фактическая verification (2026-08-02):** targeted radius — 193 теста,
  exit code 0; canonical `create --help`, inline/file temp dry-run smoke — по
  exit code 0; full offline suite — 1465 тестов за 309.632 секунды, exit code
  0, `OK`; docs QA после checkpoint update — exit code 0. Числа и длительности —
  измерения, не нормативы. Network/provider/download/Vision/TTS/paid/render
  operations не выполнялись.

#### PLAN-9B-4 — truthful source/script behavior (CRITICAL-2, часть 2)

- **status:** completed 2026-08-02 · **зависимости:** PLAN-9B-5a (выполняется вместе или
  сразу после — иначе пользователь теряет offline-путь подачи материала).
- **цель:** для factual strict workflow `topic` = **intent, не usable source
  material**. Запрещённая цепочка `topic → insufficient source →
  LegacyTemplate → validation passed → production success` перестаёт
  существовать. При недостаточном материале — truthful blocking state
  `insufficient_source_material`.
- **reuse — новых сущностей не создаётся:** `allow_legacy_fallback` ·
  `ScriptValidationResult` · `script_provider` · `fallback_reason` ·
  `script_metadata`. **`content_origin` не создаётся** (OD-18): информация уже
  выражена существующими полями, дефект в том, что их **никто не читает**.
- **`LegacyTemplateScriptProvider` не удаляется.** Он остаётся эталоном
  регрессии и воспроизводимости старых проектов; разрешён только явным режимам
  `template` / `demo` / `test` / `draft`. Меняется условие его **молчаливого**
  вызова, а не он сам.
- **AI research не добавляется** (OD-17).
- **тесты deep-dive:** T6, T7, T8.
- **backward compatibility:** старые persisted проекты и test fixtures с явным
  `script_provider == "legacy_template"` продолжают воспроизводить старую форму;
  defense-in-depth блокирует только metadata, явно фиксирующие неявный fallback
  из-за `insufficient_source_material`.
- **risk boundary:** наблюдаемое поведение `strict` → **owner approval**.
- **required verification:** targeted + `full`.
- **фактическая verification (2026-08-02):** targeted owner/caller radius —
  168 тестов за 135.307 секунды, exit code 0; full offline suite — 1523 теста
  за 356.527 секунды, exit code 0, `OK`. T6/T7/T8, clean application/diagnostic
  errors, persisted quality defense, explicit legacy compatibility, source-text
  и resume/force-stage fixtures зелёные; docs QA и
  `tests.test_stage2_agent_onboarding` — exit code 0. Числа и длительности — измерения, не
  нормативы; network/provider/download/Vision/TTS/paid calls не выполнялись,
  synthetic render fixtures создавались только во временных каталогах.

#### PLAN-9B-PRODUCER — Provider-language VisualBrief producer

- **status:** completed · **completed:** 2026-08-02 · scheduled owner decision
  **OD-P-1** 2026-08-02.
- **dependencies:** completed **PLAN-9B-1**; completed **PLAN-L0** до начала
  execution согласно утверждённому порядку.
- **owner:** `src/content/visual_planning/**`.
- **objective:** из доказанного source/script/research evidence сформировать в
  существующем visual-planning owner provider-language содержание существующего
  `VisualBrief`, не перенося semantic intent в `query_adapter` и не создавая
  второго planner/query pipeline.
- **user outcome:** подготовленный материал разных доменов получает
  осмысленный provider-ready visual brief/query; при недостатке evidence
  состояние остаётся честным, fail-closed и редактируемым, а explicit author
  brief всегда выигрывает.
- **implementation zones:**
  - `src/content/visual_planning/**`;
  - exact owning test modules, доказанные pre-implementation caller audit;
  - current docs только для checkpoint/evidence после фактического completion.
  Фактический diff остался в этих зонах; caller production вне owner не менялся.
- **prohibited zones:** любой production owner вне
  `src/content/visual_planning/**`; `query_adapter`, provider implementations,
  script/research owners, public CLI/API, schemas, project/storage layout и
  asset pipeline. Не создавать `TranslatorService`, `SearchEngine`,
  `QueryOrchestrator`, `VisualBriefManager`, `VisualBriefEngine`, второй visual
  planner, второй query pipeline, второй semantic stack, новый repository,
  artifact, manifest, evidence store или project state.
- **canonical contracts — только существующие:** `VisualBrief`;
  `SceneVisualPlan.brief`; `provider_queries`; `claim_ids`; `source_refs`;
  visual-plan serializers; `master/master_visual_plan.json`; локализованный
  `visual/visual_plan.json`; существующая downstream copy `query_plan` /
  `visual_brief` в `assets/assets_manifest.json`.
- **author override priority:** automatic planner result → explicit author
  brief applied last → author brief wins. `NewsJob.visual_briefs` остаётся
  author input; producer не выдаёт automatic result за author input и не
  перезаписывает prepared brief.
- **truthful fail-closed boundary:** producer использует source text, script,
  research evidence, template/channel brief и существующую structured scene
  semantics. Factual provider query только из topic literal запрещён. При
  недостаточном evidence не создаются generic plausible substitute,
  topic-specific literals или misleading query; unknown intent остаётся
  fail-closed.
- **method is not frozen:** implementation-time варианты могут включать
  deterministic evidence-derived adaptation, template/channel briefs и local
  bounded adapter. Текущая approved implementation boundary — offline, без
  сети, paid API и новой обязательной model dependency. Local model либо
  optional paid/model-assisted adapter не утверждены этим слайсом; любой
  network/paid/model-assisted вызов требует отдельного owner approval на
  конкретное действие. Конкретная библиотека или модель заранее не выбирается.
- **tripwires:**
  - *persisted bytes:* OD-P-1 разрешает будущие изменения **только значений**
    существующих `visual_brief`, `provider_queries`, существующих visual-plan
    JSON objects и существующей downstream copy в assets manifest. Новый field,
    schema version, файл, layout, manifest, project state, provenance field или
    query-adapter-specific storage запрещены; старые проекты читаются
    tolerant/default readers. Если нужен новый schema/layout/public contract —
    **STOP** и новое owner decision;
  - *public:* нового CLI/API/console surface нет; его необходимость требует
    **STOP** и отдельного owner decision;
  - *network/paid:* в первом implementation slice отсутствуют; отдельное
    approval требуется на каждое конкретное действие;
  - *destructive:* отсутствует; hardcode/query-path retirement остаётся
    PLAN-9B-2/PLAN-9B-3 и этим слайсом не разрешён.
- **success criteria:**
  1. Для подготовленного материала минимум из классов animals/wildlife,
     energy/technology и geography/infrastructure producer создаёт
     evidence-derived provider-language content.
  2. Хотя бы один поддерживающий provider получает осмысленный query из
     evidence, а не из topic literal.
  3. Unknown intent остаётся fail-closed.
  4. Explicit author brief всегда выигрывает.
  5. Topic-specific hardcodes не добавлены.
  6. Второй query/planning owner не создан.
  7. Новые fields/artifacts/layout отсутствуют.
  8. Old/tolerant reading продолжает работать.
  9. Network/paid calls в первом implementation slice отсутствуют.
- **characterization requirements — до изменения поведения:**
  1. Зафиксировать current automatic planner result и порядок author override.
  2. Охарактеризовать текущий persisted round-trip. В частности,
     `from_legacy_visual_plan()` может реконструировать scene semantics/intents
     без восстановления `SceneVisualPlan.brief`; определить, требуется ли
     model-level/editor/read-model round-trip на фактическом пути.
  3. Если brief теряется на необходимом current path, исправить существующий
     tolerant reader **внутри visual-planning ownership**, не создавая нового
     storage owner. Заранее утверждать необходимость reader-изменения нельзя.
  4. Зафиксировать существующие master/localized/assets-manifest copies,
     `provider_queries`, `claim_ids`, `source_refs` и отсутствие новой
     schema/layout.
  5. Добавить multi-domain, explicit-author-override и fail-closed
     unknown-intent characterization/regression.
- **реализованный механизм:** существующий `build_plan()` после planner и до
  author overlay вызывает bounded producer существующего `brief.py`. Он берёт
  только provider-language structured intents, отдельные script keywords и
  связанные через `claim_ids` safe research excerpts; topic/title/channel не
  являются query source. Строки нормализуются и ограничиваются восемью термами
  и тремя candidates; Cyrillic/mixed, URL/slug, single-term и generic production
  vocabulary fail closed. `query_adapter` остался consumer без изменений.
- **override/round-trip:** automatic brief не записывается обратно в author
  `ScriptScene.visual_brief`; explicit author brief применяется последним и
  выигрывает. Existing writer сохраняет final `visual_brief` /
  `provider_queries`, `claim_ids` и `source_refs`; tolerant reader теперь
  восстанавливает existing `SceneVisualPlan.brief` и refs, а pre-Q2 missing
  values продолжают читаться defaults. Schema version/layout/artifact не менялись.
- **фактическая verification:** characterization-first red — 5 тестов, 4
  failures + 1 error ожидаемо зафиксировали отсутствующий producer и потерю
  round-trip; после реализации owning modules — 81 тест за 0.899 с, consumer /
  script / manifest radius — 166 тестов за 38.876 с, canonical temporary manifest
  — 4 теста за 102.235 с, все exit code 0. Первый full выявил только исходный
  onboarding limit (`CURRENT_STATE.md` 282 > 280 строк); после обязательного
  compact current-doc update onboarding — 3 теста за 0.214 с, финальный full
  offline suite — 1561 тест за 356.026 с, exit code 0. Package network guard
  активен; network/provider API/download/Vision/TTS/paid и реальный project
  render не выполнялись; media-проверки full suite использовали только temporary
  synthetic fixtures.
  Task-scope checker, `git diff --check`, docs QA и onboarding docs test — exit
  code 0. `baseline_head` остаётся без изменений.
- **rollback:** один bounded implementation commit; revert этого commit.
  Миграции данных, нового artifact/layout и irreversible действий нет.
- **relation to PLAN-L0 and PLAN-9B-2:** PLAN-L0 сохраняет knowledge, включая
  C46 и C48, но producer не реализует. PLAN-9B-PRODUCER реализует отдельный
  user outcome. PLAN-9B-2 после него реализует expansion ladder и hardcode
  migration. Три ответственности не смешиваются.

#### PLAN-9B-PRODUCER-M — model-assisted semantic VisualBrief adapter

- **status:** completed · **completed:** 2026-08-09 · owner-issued implementation
  slice, owner decision 2026-08-09.
- **routing.** `current_checkpoint` остаётся **PLAN-9D**: это capability-слайс,
  снимающий prerequisite для **PLAN-9D-D**, а не новый checkpoint и не под-слайс
  evidence-семейства PLAN-9D-A…PLAN-9D-G. Слайс закрыт тем же commit, поэтому
  checkpoint'ом быть не может (Execution protocol: completed шаг не может быть
  текущим).
- **почему новый PLAN-ID.** PLAN-9B-PRODUCER закрыт 2026-08-02 и своим же
  текстом исключил эту capability: «Local model либо optional
  paid/model-assisted adapter не утверждены этим слайсом». В
  [PRODUCT_PLAN.md](PRODUCT_PLAN.md) раздел 6 A «локальная модель» и
  «опциональная платная модель после отдельного approval» перечислены как
  adapters той же capability, а таблица 11.5 держит `Local translation /
  adaptation` со статусом `EXPERIMENTAL` и критерием возврата «вместе с
  producer» — то есть продуктовое направление было утверждено, а исполняемого
  PLAN-ID у него не было. Зарезервированного ID не найдено: строка
  `PLAN-9B-PRODUCER-M` до этого слайса в репозитории не встречалась. Ни один из
  трёх decision-tripwire не сработал — persisted bytes не менялись, публичной
  CLI/API-поверхности не добавлено, сеть и деньги не использовались.
- **dependencies:** completed PLAN-9B-PRODUCER, PLAN-9B-2, PLAN-9B-3.
- **owner:** `src/content/visual_planning/**`.
- **objective:** обычный подготовленный не-английский сценарий получает
  осмысленный provider-language `VisualBrief` там, где deterministic extraction
  недостаточно. Ручной английский бриф на каждую сцену перестаёт быть
  обязательной частью нормального автоматического workflow и остаётся
  override/коррекцией.
- **[FACT] перепроверенный diagnostic (offline, clean HEAD `b2aae9c`).** На
  обычном русском сценарии из четырёх сцен deterministic planner выбрал
  субъектами грамматические дополнения — `бежать`, `воздухе`, `живот`, `воды`.
  `produce_brief` вернул пустой бриф во всех четырёх сценах (это заявленный
  fail-closed контракт, а не дефект проводки), три сцены пришли в
  `build_scene_queries` со статусом `query_translation_required`, четвёртая
  получила единственный glossary-хит `snow`. Root cause — **отсутствующая
  semantic capability**, не сломанный producer и не сломанный `query_adapter`.
- **реализованный механизм.** Новый `src/content/visual_planning/semantic_brief.py`
  внутри существующего owner: `SceneBriefEvidence` собирает evidence одной сцены
  (narration, on-screen text, подготовленные keywords, safe claims, связанные
  через `claim_ids`, существующие `must_include`/`must_avoid`, `shot_type`;
  topic/title/channel намеренно отсутствуют), `build_prompt` строит инструкцию,
  `parse_response` — строгий закрытый парсер, `ModelSemanticBriefAdapter` —
  injection-only обёртка над переданным callable. Существующий
  `_produce_scene_briefs` в `engine.py` вызывает adapter **только** для сцен, где
  deterministic `produce_brief` вернул пусто; результат накладывается тем же
  существующим `apply_brief` + `rebuild_intents`, после чего повторно
  запускается тот же `produce_brief`. Поэтому каждую строку запроса по-прежнему
  строит единственный владелец `expansion`: adapter формулирует смысл и не
  пишет ни одного query. Наложение сначала репетируется на копии сцены — ответ,
  из которого лестница не может собрать запрос, обязан оставить сцену ровно
  такой, какой её оставил planner.
- **model contract и validation.** Ответ закрыт пятью существующими полями
  `VisualBrief` (`subject`, `action`, `place`, `context`, `shot_type`). Полей,
  несущих authority, модель не получает: `must_include` — жёсткое требование,
  `must_avoid` — ограничение смысла и прав, `provider_queries` вообще обходят
  сборку запроса. Отказ вместо починки: неизвестное поле, неверный тип,
  неизвестный `shot_type`, фраза длиннее восьми слов, утечка исходного языка,
  субъект только из производственной лексики (`NON_FACTUAL_QUERY_TERMS`) и
  ответ, просящий запрещённое сценой, — всё это `SemanticBriefResponseError`.
  Пустой `subject` — это не ошибка, а «evidence не говорит, что показывать»:
  возвращается пустой бриф. Новая JSON-schema в `schemas/` не создавалась.
- **fail-closed.** Нет adapter → deterministic план байт-в-байт прежний. Adapter
  без callable или без `approved=True` → недоступен. Любое исключение
  injected callable → controlled `SemanticBriefUnavailableError`. Невалидный
  ответ → сцена остаётся нетронутой и сохраняет честный
  `query_translation_required`. Generic stock fallback не добавлен.
- **author override.** Порядок не изменился: automatic deterministic →
  model-assisted → explicit author brief последним. `_apply_scene_briefs`
  по-прежнему применяется после `_produce_scene_briefs` и выигрывает; automatic
  бриф не записывается обратно в авторский `ScriptScene.visual_brief`.
  **C63 остаётся открытым и не трогался**: на topic/article paths авторский бриф
  до visual planning не доходит, поэтому parity для них не заявляется.
- **network/paid — future prerequisite, не выполнено здесь.** Реальный вызов
  модели этим слайсом запрещён и не выполнялся; production-callers
  (`src/news/visual_plan.py`, `src/ai_youtube/cli/commands/authoring.py`)
  adapter не передают, поэтому live-путь не активирован. Для будущей активации
  нужны **два раздельных** owner decision: (1) класс сетевого действия для
  text-model вызова — в `src.runtime_network.NETWORK_ACTIONS` его сегодня нет, и
  собственный budget gate Vision таким разрешением не является; (2) отдельное
  paid approval, если модель платная. `src/runtime_network.py` этим слайсом не
  изменялся.
- **что намеренно не делалось.** Второй planner, второй query owner,
  `TranslatorService`, запись в `PLANNER_FACTORIES`, новая schema/layout/artifact,
  новое project state, изменение default-конфигурации, активация Vision/PLAN-9E,
  правки selection/ranking/rights/pagination, изменение
  `tests/data/plan9d/**` и `projects/**`. Diagnostic-литералов в production-коде
  нет — это проверяется статически по строковым константам всего пакета.
- **фактическая verification.** Characterization-first: новый
  `tests/test_visual_planning_semantic_brief.py` сначала красный
  (`ModuleNotFoundError`), после реализации — 30 тестов OK. Owning radius
  (`test_visual_planning`, `test_visual_query_expansion`,
  `test_visual_planning_pipeline`, `test_visual_retrieval_wiring`,
  `test_visual_retrieval_regression`, `test_visual_retrieval_repair`,
  `test_input_query_truth_characterization`, новый модуль) — 226 OK. Consumer
  radius (12 модулей: content creation service, news_to_short assets, script
  engine/adaptation, slot-aware retrieval, semantic slot decisions, manual asset
  replacement, autonomous completion, runtime network boundary, PLAN-9D capture
  и historical evidence) — 328 OK. Governance/gate radius
  (`test_plan9d_retrieval_gate`, `test_docs_routing_and_freshness`,
  `test_check_agent_docs`, `test_capability_consistency`) — 133 OK. Сеть,
  provider API, download, Vision, TTS, платные вызовы, реальная модель и render
  не выполнялись; package network guard активен.
- **independent review и bounded repair (2026-08-09, до live activation).**
  Independent read-only review implementation commit `5979321` дал verdict
  **ACCEPT WITH NON-BLOCKING FINDINGS** и **принял архитектуру**: один владелец
  `VisualBrief`, второго planner нет, второго query owner нет, `query_adapter`
  остаётся consumer, adapter действительно optional, поведение без adapter не
  изменилось, скрытого сетевого/платного поведения нет. Три MAJOR findings
  закрыты одним bounded repair commit под **тем же PLAN-ID** (та же конвенция,
  что у PLAN-9B-2 `66fd2431` + `8c60295` и PLAN-STAB-7 `42fa741` + `8357402`);
  архитектура не перепроектировалась.
  - **MAJOR-1 — readiness.** Помощь включалась только при `brief.is_empty`.
    Воспроизведено offline: русская сцена с одной связанной английской claim
    даёт `provider_queries` `{'en': ['Field observations recorded during survey
    season.', ...]}`, то есть формально непустой бриф **без** `subject`, при
    `scene.subject` = `воды` — модель не спрашивалась никогда, провайдер получал
    текст claim. То же со слабыми prepared keywords (`amazing animal moments`).
    Repair: критерий — **не** пустота, а отсутствие provider-language `subject`.
    Это не quality score и не новый классификатор: это тот же критерий, который
    `parse_response` уже применяет к ответу модели («place или action без
    subject не повышаются до брифа»), заданный теперь и deterministic брифу.
    Правило строго шире прежнего — у пустого брифа `subject` тоже нет, поэтому
    ни один ранее работавший путь не сузился; бриф с provider-language subject
    (обычный английский материал) модель по-прежнему не вызывает. Прежний тест
    «достаточных prepared keywords» переписан: keywords дают исполнимый запрос,
    но не сообщают плану субъект, и premise «keywords = достаточно» и была
    дефектом. Отдельный regression: refused ответ больше не может стоить сцене
    того deterministic evidence, которое у неё уже было.
  - **MAJOR-2 — hard constraints.** Воспроизведено: сцена с
    `must_include=['McMurdo']` (планировщик ставит его сам, когда имя записано
    латиницей) после semantic overlay получала `must_include=[]`. Причина —
    overlay использовал авторский `apply_brief`, где несформулированное поле
    является осознанным ответом автора. Модели поля authority не предлагаются
    вовсе (`RESPONSE_CONTRACT` их не содержит), поэтому её молчание ответом не
    является. Repair: новый bounded helper `semantic_brief.apply_semantic_brief`
    внутри того же owner — тот же `apply_brief` с восстановлением
    `must_include`/`must_avoid`, поэтому mapping «поле брифа → поле сцены»
    остаётся в одном месте. Авторская семантика `apply_brief` не менялась и
    закреплена отдельным тестом. Второй `VisualBrief` contract не создавался.
  - **MAJOR-3 — programmer defect vs model failure.** Воспроизведено: callable с
    неверной сигнатурой (`TypeError`) и дефект внутри callable одинаково
    становились `SemanticBriefUnavailableError(retryable=True)`, после чего
    engine молча получал пустой бриф. Repair: fail-closed остаётся для
    controlled-ошибок этого пакета (backend сам объявляет себя недоступным),
    для `OSError`, включая `TimeoutError`, и для невалидного ответа
    (`SemanticBriefResponseError`); всё остальное пробрасывается, как это уже
    делает соседний `script_engine.providers.llm`, на который этот модуль
    ссылается как на образец. Новая иерархия исключений не вводилась.
  - **observability.** Ожидаемые исходы пишутся в **существующее** поле
    `SceneVisualPlan.warnings` в уже принятом формате `code: message`
    (`no_concrete_subject` там же): `semantic_brief_no_answer`,
    `semantic_brief_unavailable`, `semantic_brief_response`. Схема не менялась —
    `planning_warnings` уже round-trip'ится через `legacy_format`, ни в одном
    файле `schemas/` не описан и ни одним gate не считается blocking. Adapter,
    который не запускался (не подключён, не approved, нет evidence), не пишет
    ничего: unwired adapter обязан оставлять план байт-в-байт прежним, и это
    закреплено тестом. Дефект интеграции в этот список не входит — он сюда не
    доходит.
  - **MINOR — стоимость.** Сцена с explicit авторским брифом больше не
    отправляется в модель: этот бриф применяется последним и всё равно
    перезапишет ответ. Карта авторских брифов читается один раз и разделяется
    обоими проходами, чтобы они не разошлись в том, какие сцены автор уже
    закрыл. **C63 не чинился**: пропускаются только сцены, чей авторский бриф
    фактически доходит до visual planning.
  - **что repair не трогал:** live model activation (не начата), реальный
    diagnostic Short (не запускался), `runtime_network.py`, PLAN-9D-D, selection
    /ranking/shortlist findings, zero-byte preview, prompt data fencing,
    нормализация `shot_type` регистра и прочие MINOR/NOTES исходного review.
  - **verification repair:** targeted тесты сначала красные (10 failures/errors
    против pre-repair поведения по всем четырём findings), после repair
    `tests/test_visual_planning_semantic_brief.py` — 44 OK; owning radius 240 OK.
- **второй independent review и второй bounded repair (2026-08-09, до live
  activation).** Independent read-only review repair commit `a7ef6a5` подтвердил
  архитектуру ещё раз и оставил два repository-confirmed препятствия перед live
  semantic-model activation. Оба закрыты одним bounded repair commit под **тем же
  PLAN-ID**; архитектура снова не перепроектировалась, MAJOR-1…MAJOR-3 не
  пересматривались.
  - **BLOCK-1 — provider-language subject ≠ понятый subject.** Воспроизведено
    offline на repository-reachable сценах: `An emperor penguin colony crosses the
    antarctic sea ice.` → `subject` = `antarctic`; `The orca breaches completely
    out of the cold water off the coast.` → `breaches`; `The penguin slides on its
    belly across the deep snow and ice.` → `across`. Во всех трёх бриф формально
    называет subject на языке провайдера, поэтому MAJOR-1 критерий считал сцену
    достаточной и модель не вызывалась ни разу — то есть неверный, но латинский
    subject глушил единственную помощь, способную его исправить. Repair:
    достаточность решается **provenance**, а не видом слова. `collect_entities`
    уже помечает сущность `ENTITY_KIND_TOPIC`, когда её называет **заявленная тема
    видео**; это декларация о материале (та же природа, что у авторского брифа,
    на шаг слабее), а не подсчёт повторов. Никакого lexical quality classifier,
    POS, scoring и blacklist не вводилось: `antarctic` отклоняется не за то, что
    он топоним, а за то, что его никто не заявлял. `VisualPlanResult.topic_entity`
    намеренно **не** используется — это лишь самая частотная сущность скрипта,
    то есть тот же подсчёт под именем provenance. `VisualEntity.source_refs` тоже
    отклонён как второй маршрут и это закреплено регрессией: на воспроизведённой
    orca-сцене связанная claim подтверждает `coast`, то есть ровно ту же ошибку.
    Единственная новая production-константа — общее имя уже существующего
    строкового значения `topic_entity` в `models.py`.
  - **BLOCK-2 — невидимый non-retryable отказ реально вызванного backend.**
    Воспроизведено: approved adapter вызывает backend, backend поднимает
    controlled `SemanticBriefUnavailableError(retryable=False)` (класс постоянного
    отказа — отклонённый ключ, недоступная модель), и сцена остаётся с
    `warnings == []`, то есть байт-в-байт как при отсутствующем adapter. Причина —
    `retryable` использовался как признак «был ли вызов». Repair: вопрос «был ли
    достигнут backend» решается **до** вызова, по собственным preconditions
    adapter (`is_available()` и `SceneBriefEvidence.is_empty`); всё, что случилось
    после этой точки, записывается независимо от `retryable`. Not attempted (нет
    adapter, не подключён, не approved, нечего спрашивать) по-прежнему не пишет
    ничего и оставляет план прежним. Новых полей, схем, telemetry и project state
    не добавлено: используется то же `SceneVisualPlan.warnings` и тот же код
    `semantic_brief_unavailable`.
  - **стоимость.** Provider-language сцена, чей subject темой не заявлен, теперь
    стоит один model call там, где раньше не стоила ничего. Это принятый обмен:
    именно эти сцены и получали неверный subject. Русские сцены не подорожали —
    у них `brief.subject` пуст и модель вызывалась уже раньше. Prepared keywords
    как отдельный маршрут достаточности не вводились: они не сообщают плану, что
    его subject верен, и premature cost saving здесь проигрывает корректности.
  - **что repair не трогал:** live model activation (не начата), diagnostic Short
    (не запускался), `runtime_network.py`, PLAN-9D-D, MAJOR-2 семантика authority
    (`must_include`, установленный планировщиком из собственной экстракции,
    по-прежнему переживает overlay — это принятое поведение, а не regression
    этого слайса), selection/ranking/shortlist findings, zero-byte preview,
    `select_best_with_video`, C63.
  - **verification второго repair:** targeted тесты сначала красные (3 failures
    против pre-repair поведения по обоим findings), после repair
    `tests/test_visual_planning_semantic_brief.py` — 51 OK; owning radius 247 OK.
- **третий independent review и третий bounded repair (2026-08-09, до live
  activation).** Independent read-only review repair commit `2275528` оставил один
  repository-confirmed blocker и один owner-решённый вопрос о provenance. Оба
  закрыты одним bounded repair commit под **тем же PLAN-ID**; архитектура снова не
  перепроектировалась, MAJOR-1…MAJOR-3 и BLOCK-1/BLOCK-2 не пересматривались.
  - **BLOCK-3 — эвристика получала авторитет автора.** `must_include` — hard
    requirement: `rank_candidates` отклоняет кандидата, чьи provider metadata не
    содержат каждый термин, каким бы ни был score, и весь
    `src/assets/semantic_selection` называет это полем «того, что явно потребовал
    автор» (`decision.py`, `evidence.py`, `candidate_ranker.py`). При этом
    `deterministic._plan_scene` заполнял его сам — `must_include = [subject]`,
    когда subject латиницей, плюс `place` для `establishing`/`evidence`. Ничего
    явного в этом нет: функция ранжирует слова, которые предложение употребило,
    поэтому её subject регулярно оказывается местом, прибором или агентством,
    упомянутым мимоходом. Воспроизведено end-to-end на production-reachable русской
    сцене «Спутники NASA показали, как пингвины на льду собираются в большую
    колонию»: deterministic `subject` = `NASA`, `must_include` = `['NASA']`;
    semantic adapter исправляет предмет на `penguin colony`; корректный penguin
    candidate получает `subject_match=100.0` и всё равно отклоняется —
    `blocking_reject_reasons=['must_include_missing:NASA']`. Semantic correction не
    могла это исправить by design: модели поля authority не предлагаются
    (`RESPONSE_CONTRACT`), поэтому устаревшая догадка переживала исправление и
    отклоняла именно того кандидата, ради которого оно делалось. Repair
    исправляет **источник авторитета**, а не убирает мусор после overlay:
    планировщик больше не пишет `must_include` вообще. Извлечённые subject и place
    не теряются — они по-прежнему едут в своих слотах и ведут intents, где
    оцениваются частичным совпадением вместо буквального требования, поэтому
    неверная догадка стоит позиции в ранжировании, а не отказа сцене.
  - **что осталось hard.** Явный авторский `must_include` (и несущий его
    `exact_entities`) остаётся hard и blocking — закреплено парой регрессий на том
    же fixture: кандидат, не удовлетворяющий авторскому требованию, отклоняется с
    `must_include_missing`, удовлетворяющий — нет. `must_avoid` не трогался.
    Semantic model права записывать `must_include`/`must_avoid` не получила.
    `apply_semantic_brief` (MAJOR-2) сохранён без изменений; поскольку constraints
    теперь бывают только у авторски-брифованных сцен, а те в модель не идут, его
    восстановление стало защитой контракта, а не воспроизводимым production-путём —
    это записано в его owning-тесте.
  - **BLOCK-4 — owner decision о topic provenance.** Слово внутри **глобальной**
    строки `topic` признано недостаточным scene-level основанием подавлять
    semantic understanding. Воспроизведено: `Antarctic penguin colonies` помечает
    `ENTITY_KIND_TOPIC` и `antarctic`, и `penguin`, экстракция берёт `antarctic`,
    и прежнее правило BLOCK-1 читало эту метку как «продюсер заявил такой subject»
    — неверный subject защищался присутствием верного. Repair: маршрут отозван.
    `_needs_semantic_help` больше не спрашивает ничего, выведенного из текста
    сценария; остаётся вопрос авторитета, и единственный scene-level источник с
    ним — авторский `visual_brief`, который модель пропускает и так. Другого
    структурированного источника в репозитории нет: `ScriptScene.keywords` во всех
    трёх провайдерах строятся `text_analysis.keywords(narration)`, то есть та же
    эвристика; это записано честно, и новый источник не выдумывался. Ни POS, ни
    lexical blacklist, ни scoring, ни `subject_confidence`, ни новая persisted
    provenance-схема не вводились. `ENTITY_KIND_TOPIC`, `VisualPlanResult.topic_entity`
    и `topic_stems` сохраняют прежний глобальный смысл — отозвано только их
    использование как bypass evidence, entity-система не рефакторилась.
  - **стоимость.** Верхняя граница при будущей активации — **один вызов модели на
    сцену без авторского брифа**, то есть до N вызовов на план из N сцен (раньше
    сцены с topic-заявленным subject не стоили ничего). Ожидаемое значение для
    обычного русского Short — по вызову на сцену, как и до BLOCK-1. Никакой
    активации это не выполняет: adapter доступен только через injection, ни один
    production caller его не передаёт, и `adapter.is_available()` по-прежнему
    решает, будет ли backend достигнут. Преждевременная оптимизация отложена до
    реального diagnostic evidence.
  - **намеренная смена default-поведения.** Deterministic-only выход изменился, и
    байт-идентичность **не** заявляется. Точная дельта: `scene.must_include` → `[]`;
    следом `visual_brief.must_include`/`exact_entities` и `semantic.must_include` в
    legacy-плане; в англоязычной сцене исчезает один расширенный
    `alternative_queries` rung, собиравшийся из `context`. `primary_query`, порядок
    и состав `intents`, validation-issues и полностью кириллическая сцена
    (`must_include` там и раньше был пуст) не изменились. Прочая семантика по
    умолчанию не трогалась.
  - **что repair не трогал:** live model activation (не начата), diagnostic Short
    (не запускался), `runtime_network.py`, PLAN-9D-D, реализация
    `candidate_ranker` (дефект был выше по течению, ранжирование не подгонялось под
    тест), C63, zero-byte preview, `select_best_with_video`, shortlist/review drift,
    non-provider-language `must_avoid`, SigLIP, Vision activation,
    pagination/adaptive retry.
  - **verification третьего repair:** targeted тесты сначала красные (5 failures
    против pre-repair поведения по обоим findings), после repair
    `tests/test_visual_planning_semantic_brief.py` — 56 OK; owning radius 354 OK;
    полный offline suite — 2018 OK.
- **rollback:** implementation commit плюс три bounded repair commit; revert в
  обратном порядке. Миграций данных, новых artifact/layout и необратимых
  действий нет.
- **next:** independent read-only review именно **третьего** repair commit.
  Свежий diagnostic Short следующим действием **не является**: live
  semantic-model activation не существует, поэтому diagnostic прогнал бы только
  deterministic путь и ничего не сказал бы о чинимой capability. Возврат к
  **PLAN-9D-D** остаётся отдельным owner decision после активации.
  **Исполнено 2026-08-09** слайсом **PLAN-9B-PRODUCER-M-LIVE** (ниже).

#### PLAN-9B-PRODUCER-M-LIVE — live semantic-model activation

- **status:** completed · **completed:** 2026-08-09 · owner-issued
  implementation slice, **один commit**, trailer `Plan-Step:
  PLAN-9B-PRODUCER-M-LIVE`.
- **routing.** `current_checkpoint` остаётся **PLAN-9D**. Это второй и
  последний capability-слайс той же линии: PLAN-9B-PRODUCER-M построил адаптер,
  этот слайс сделал его достижимым. Новый ID взят потому, что
  PLAN-9B-PRODUCER-M закрыт 2026-08-09 собственным commit, а закрытый шаг не
  дополняется; суффикс следует существующей конвенции родственных ID
  (`PLAN-9B-2`, `PLAN-9B-3`, `PLAN-9D-A…G`). Evidence-семейством PLAN-9D это не
  является.
- **цель.** Один approved text-model backend, реально достижимый из production
  orchestration, без второго model framework, без второго query owner и без
  расширения persisted schema.
- **что было.** `ModelSemanticBriefAdapter` принимал вызов модели инъекцией, и
  ни один production caller инъекции не делал. `NETWORK_ACTIONS` не имел класса
  для текстовой модели. Живого пути не существовало ни при каком наборе
  разрешений.
- **реализованный механизм.**
  - `src/content/semantic_brief_openai.py` — единственный backend и единственная
    граница SDK. `src/content/visual_planning/**` не импортирует ни OpenAI, ни
    его исключения: направление зависимости одностороннее.
  - `NETWORK_ACTION_SEMANTIC_BRIEF = "semantic_brief"` добавлен в существующий
    единственный owner `src/runtime_network.py`. Второй network guard не
    создавался; `--allow-network semantic_brief` и вопрос Wizard работают через
    уже существующий `choices`-из-`NETWORK_ACTIONS` путь без изменений CLI.
  - `config/semantic_brief.json` — стоящая платная политика по образцу
    `config/semantic_visual.json`. В репозитории **всё выключено**.
  - `src/news/visual_plan.py` вызывает `build_semantic_brief_adapter()`; тот
    возвращает `None`, если не выполнено хотя бы одно условие, и `None` означает
    ровно сегодняшний детерминированный план.
- **два gate, ни один не подразумевает другой.**
  - **сеть:** `semantic_brief` в разрешении прогона. Проверяется дважды — при
    сборке адаптера и через общий `require_network` непосредственно перед
    вызовом SDK, потому что разрешение живёт в `ContextVar` и к моменту вызова
    может отличаться.
  - **оплата:** `allow_paid_calls` **и** фраза `LIVE_SEMANTIC_BRIEF_APPROVED`
    **и** положительный `maximum_calls_per_project` **и** положительный
    `maximum_budget_usd`. Булев флаг ставят случайно, фразу — нет.
  - инвариант закреплён тестами в обе стороны: сеть без оплаты — 0 вызовов,
    оплата без сети — 0 вызовов. Наличие `OPENAI_API_KEY` разрешением не
    является ни для одного из gate.
- **MAJOR-A закрыт.** Любой непустой author `visual_brief` подавлял смысловую
  помощь целиком, включая бриф из одних `must_include` / `must_avoid` / `notes`.
  Это разные вопросы: constraint ограничивает ответ, но ответом не является.
  Новый предикат `brief.author_semantics_are_sufficient` (владелец —
  `VisualBrief`, не engine) считает вопрос «что показывать» отвеченным только
  для `visual_description`, `subject`, `provider_queries`. `action` и `place` по
  отдельности недостаточны по той же причине, по которой `parse_response` уже
  отказывает модели в месте без предмета. Побочно закрыт вытекающий дефект:
  author-констрейнты теперь передаются в evidence (`evidence_for_scene(...,
  author_brief=...)`), иначе сцена с одним `must_avoid` уходила бы модели без
  самого запрета, и проверке парсера было бы не с чем сверяться.
- **что модель НЕ получает.** `must_include`, `must_avoid`, `provider_queries`,
  provider, выбранный ассет, ranking score, права. Схема запроса **выводится**
  из существующего `RESPONSE_CONTRACT` и `SHOT_TYPES`, поэтому новой JSON schema
  не появилось и разойтись с парсером она не может.
- **call bound и retry.** Не более одного вызова на сцену, у которой смысл не
  задан автором; сверх этого — `maximum_calls_per_project` как жёсткий потолок
  **проекта**: с `C84` потраченное переносится между build'ами плана через
  `prior_usage`, поэтому ни новый экземпляр backend, ни replan, ни
  `--force-stage`, ни resume новой квоты не выдают (до `C84` потолок фактически
  действовал на один build). `maximum_budget_usd` с `C85` проверяется перед
  каждым запросом как **оценочный** предел из `estimated_cost_per_call_usd`;
  фактическую сумму счёта провайдера система не знает и не гарантирует.
  Клиент создаётся с `max_retries=0`, место в бюджете расходуется
  **до** вызова, поэтому упавший платный запрос не может быть повторён молча.
  Скрытых retry нет ни на одном уровне.
- **секреты.** Ключ только из `OPENAI_API_KEY`, только по факту наличия
  (`bool(os.getenv(...))`). В project JSON, отчёты и ошибки не попадает. Текст
  исключения провайдера намеренно **не переносится** в warning сцены: сообщение
  OpenAI об отклонённом ключе содержит сам ключ, а warning уезжает на диск в
  `visual_plan.json`. Записываются класс ошибки и HTTP-статус — этого достаточно,
  чтобы различить все случаи. Реальное значение в `.env.example` не добавлялось.
- **что осталось нетронутым.** Vision, `candidate_ranker`,
  `select_best_with_video`, shortlist/review drift, SigLIP, provider ranking,
  adaptive retrieval, C63, zero-byte preview, persisted schema `job.json` и
  `visual_plan.json`, CLI-поверхность.
- **verification.** Сначала красный (`ModuleNotFoundError`), затем
  `tests/test_semantic_brief_live_activation.py` — **38 OK** (случаи A…J
  промпта плюс отдельный тест на утечку ключа, который нашёл реальный дефект
  первой реализации и заставил убрать текст исключения провайдера из warning);
  owning radius `tests/test_visual_planning_semantic_brief.py` +
  `tests/test_runtime_network_boundary.py` — **90 OK**; полный offline suite —
  **2056 OK** (запущен, потому что затронуты сетевая и платная production-обвязка).
  Реальный вызов модели, сеть, provider, Vision, TTS и render в этом слайсе
  **не выполнялись**.
- **bounded repair 2026-08-09 — response contract alignment (после первого
  real Russian diagnostic).** Owner-issued bounded slice, **один commit**,
  тот же trailer `Plan-Step: PLAN-9B-PRODUCER-M-LIVE`. Нового PLAN-ID не
  создавалось: это repair уже закрытого слайса по механизму, которым закрывался
  finding F1 в PLAN-9B-2, а не новый checkpoint и не evidence-подшаг PLAN-9D.
  - **что показал diagnostic.** Проект
    `projects/2026-08-09_diagnostic-ru-semantic-live-1` (не изменялся). Live
    `gpt-4.1` понял все шесть сцен, но **3 из 6** ответов отклонены целиком, и
    каждый — по ограничению, о котором модель не была предупреждена:
    `scene_001` — элемент `context` длиннее `MAX_FIELD_TERMS`; `scene_004` —
    `action` длиннее `MAX_FIELD_TERMS`; `scene_006` — в `context` попал
    показанный модели on-screen text на языке сцены. Принятые ответы
    (`scene_002/003/005`) дали корректные английские запросы, то есть дефект —
    в формулировке запроса, а не в модели и не в парсере.
  - **что изменено.** Только asking side. `build_prompt` теперь явно
    сообщает: язык провайдера, потолок слов на поле, потолок элементов
    `context`, что значения — короткие поисковые фразы, запрет цитировать
    закадровый текст, запрет переносить on-screen text, запрет пояснений, и что
    нарушение любого правила отменяет весь ответ. `RESPONSE_CONTRACT`
    формулируется **из** `MAX_FIELD_TERMS`/`MAX_CONTEXT_ITEMS`, а не рядом с
    ними; `response_schema()` носит те же описания полей, взятые у владельца
    контракта. Word-count в JSON Schema не выражается точно, regex-суррогат не
    вводился: схема фиксирует структуру, промпт — семантику длины, парсер
    остаётся окончательным судьёй.
  - **чего НЕ менялось.** Парсер не ослаблен: `MAX_FIELD_TERMS = 8`,
    `MAX_CONTEXT_ITEMS = 4`, provider-language validation, all-or-nothing
    parsing, отказ по `must_avoid`, отказ по production-лексике — всё как было,
    и три отклонённых live-ответа остаются отклонёнными (закреплено тестами).
    Selection не трогался: required slots, `candidate_ranker`, action/context
    blocking, `fallback_level`, metadata thresholds, права, Vision. `action` не
    понижен до advisory. Модель для следующего diagnostic остаётся `gpt-4.1`.
  - **regression evidence, оставленная намеренно.** При отклонённом брифе
    `scene_004` деградировала до запроса `snow` и выбрала зимний лес без
    пингвинов (`assets_manifest.json`, `provider_attempts`). Fallback в этом
    слайсе не чинился: следующий diagnostic должен показать, исчезает ли этот
    отказ сам по принятому брифу.
  - **verification.** Новые targeted тесты сначала красные против
    pre-repair кода (19 failures/errors), после repair
    `tests/test_visual_planning_semantic_brief.py` +
    `tests/test_semantic_brief_live_activation.py` — **114 OK**; owning radius
    (`test_visual_planning`, `test_visual_planning_pipeline`,
    `test_semantic_asset_selection` сверх них) — **205 OK**; docs QA и scope QA
    зелёные. Полный offline suite не запускался: изменены только формулировка
    запроса к модели и описания в схеме запроса, ни один shared contract,
    persisted schema, network- или paid-gate не затронут. Реальный вызов
    модели, сеть, provider, Vision, TTS, render и платные вызовы в этом слайсе
    **не выполнялись (0)**.
- **bounded repair 2026-08-09 — родовая среда перестала быть `exact_location`
  (после второго real Russian diagnostic).** Owner-issued bounded slice, **один
  commit**, тот же trailer `Plan-Step: PLAN-9B-PRODUCER-M-LIVE`. Нового PLAN-ID
  не создавалось, `current_checkpoint` остаётся **PLAN-9D**.
  - **что показал diagnostic.** Проект
    `projects/2026-08-09_diagnostic-ru-semantic-live-2` (read-only, не
    изменялся). Модель ответила по всем сценам, но **5 из 6** сцен получили
    класс `exact_location` и маршрут NASA/Wikimedia вместо stock. Причина не в
    модели: `_named_place` в `src/assets/scene_strategy.py` проверял только
    непустоту `visual_brief.place`, поэтому `open ocean`, `nature outdoors`,
    `snowy icy ground`, `outdoor natural setting` и `indoor glass wall`
    считались названным местом. Второй, отдельный дефект — evidence лгал:
    `classified_from` записывался как `glossary`, хотя `_LOCATION_TERMS` не
    совпал на этих сценах **ни разу** (перепроверено на самих сценах: 0
    совпадений при `_named_place = True`).
  - **owner decision.** Непустой `place` сам по себе достаточным evidence для
    `exact_location` не является. Репозиторий это уже говорил в другом месте:
    `place` описан как «where it happens», короткая поисковая фраза, а
    `brief.author_semantics_are_sufficient` и `semantic_brief.parse_response`
    отказывают месту без предмета ровно по этой причине.
  - **что изменено.** Одно условие в существующем владельце `classify_scene`:
    ветка `exact_location` держится теперь только на существующем словаре
    `_LOCATION_TERMS`. `_named_place` удалён как потерявший смысл — его вторая
    половина, `semantic.location`, есть тот же `scene.place`, зеркалированный
    `legacy_format.semantic_block`, то есть не второй источник, а та же
    строка. Reason приведён к фактически сработавшему правилу: «scene names
    geography» вместо «scene is set in a named place»; `classified_from`
    остаётся `glossary` только когда словарь действительно совпал.
  - **какое evidence рассмотрено и отвергнуто.** `exact_entities` — это имена,
    и `brief` прямо относит их к метаданным, а не к смыслу сцены; одно и то же
    поле несёт и «McMurdo Dry Valleys», и название субъекта, поэтому location
    specificity оно не доказывает. `source_class` авторитетен, но он уже первая
    ветка `classify_scene`, отдельным evidence не является и не трогался.
  - **чего НЕ менялось.** `PROVIDER_PRIORITY`, `REQUIRED_SLOT_KINDS`,
    `requires_provider_metadata`, `MIN_SCORE`, `EXACT_SUBJECT_MIN_SCORE`,
    fallback levels, `candidate_ranker` и всё scoring, права и `license_policy`,
    Vision (остаётся OFF), semantic brief / model layer, persisted schema.
    Родовые сцены получают существующий generic маршрут сами собой, потому что
    исправлен класс, а не таблица провайдеров.
  - **остаточное наблюдение, намеренно не исправлялось.** `_LOCATION_TERMS`
    содержит и родовые слова ландшафта (`landscape`, `terrain`, `ландшафт`,
    `местност`), поэтому узкий остаток того же класса ошибки через словарь
    по-прежнему достижим. Это отдельный дефект словаря, а не подтверждённый
    дефект этого слайса; зафиксирован как evidence и не чинился.
  - **verification.** Новые characterization тесты сначала красные против
    pre-repair кода (**12 failures**), после repair
    `tests/test_visual_retrieval_repair.py` — **56 OK**; owning radius
    (`test_visual_retrieval_regression`, `test_slot_aware_retrieval`,
    `test_semantic_slot_decisions`, `test_visual_retrieval_wiring`,
    `test_visual_planning`, `test_visual_query_expansion`,
    `test_semantic_brief_live_activation` сверх них) — **274 OK**; полный
    offline suite — **2083 OK** (запущен, потому что изменено shared-default
    правило классификации сцен). Реальный вызов модели, сеть, provider, Vision,
    TTS, render и платные вызовы в этом слайсе **не выполнялись (0)**.
- **rollback:** implementation commit плюс два bounded repair commit; revert в
  обратном порядке. Миграций данных, новых artifact/layout и необратимых
  действий нет.
- **next (исполнено; обновлено plan reconciliation 2026-08-10):** повторные
  прогоны выполнены отдельными owner-issued действиями. **live-3**
  (`projects/2026-08-09_diagnostic-ru-semantic-live-3`): 6/6 брифов принято,
  0 parser warnings — parser-contract repair подтверждён; деградация
  `scene_004` до `snow` исчезла; но все шесть subject-слотов несли действие
  внутри субъекта (role overlap), и scene_005 выбрала NASA radar вместо орок.
  После role-contract repair (`19d2c94`) — **live-4**
  (`projects/2026-08-09_diagnostic-ru-semantic-live-4`): роли чисты в 5/6 сцен,
  орки выбраны верно, NASA radar исчез из пула; остаточные ложные выборы
  (scene_003 «Life On Earth» видео 65.75 вместо hovering-кадра 80.72 ранга 1;
  scene_004 zoo-видео 70.0 вместо snow-кадров 80.0) локализованы в
  selection-слое (`select_best_with_video`) и в metadata evidence (lava
  subject=100). Сравнительный аудит:
  `docs/audits/VISUAL_ASSETS_COMPARATIVE_AUDIT_2026-08-10.md`. Следующий шаг
  линии — **PLAN-9C-2**, затем **PLAN-9C-3** (секции ниже); acceptance gate —
  повтор того же diagnostic против LIVE-4 baseline. Отдельный independent
  review ни для одного из двух repair не назначался: они не меняют сеть,
  платные gate, авторитет selection, persisted schema и права. **PLAN-9D-D**
  остаётся NOT STARTED / blocked.

- **bounded correction after STOCK repeat (2026-08-14).** Diagnostic evidence:
  `docs/audits/STOCK_SEMANTIC_REPEAT_2026-08-14.md`, project
  `projects/2026-08-14_solnechnaya-panel-lovit-svet-tolko-dnem-nochyu-3`.
  The run proved 5/5 accepted semantic briefs and live provider-language
  retrieval, then stopped at the paid voice gate with 3/5 licensed image slots,
  two unresolved scenes, no MP4 and no quality evidence. It also proved two
  defects in this existing live capability: the canonical create path did not
  load repository `.env` before `visual_plan`, so an approved adapter silently
  disappeared unless the caller used `python -m dotenv run`; and the backend's
  `usage_summary()` had no production caller, so the five attempts could only be
  inferred from scene artifacts.
  The correction stays inside the same owners and creates no PLAN-ID:
  `src/content/semantic_brief_openai.py` reads only `OPENAI_API_KEY` from
  repository `.env`, and only after both paid and network gates pass. A process
  environment value wins; neighbouring provider and TTS secrets are not copied
  into `os.environ`. If the key remains absent, the adapter stays visible and
  the existing `semantic_brief_unavailable` warning records the controlled
  refusal without a paid attempt. `src/news/visual_plan.py` persists the
  secret-free summary under `planning_metadata.semantic_brief_usage`;
  `src/news/draft_completion.py` accumulates calls and estimated cost across
  both adaptation replans. The localized visual plan is the cumulative project
  record, while `master_visual_plan.json` remains the planning-stage snapshot.
  Tolerant readers and schema version are unchanged. Default config remains
  fail-closed. Characterization was red
  first (4 errors); targeted semantic + visual-plan radius is 75 OK, with no
  network, provider, Vision, TTS or render call. Routing returns to M1-E /
  VA-NEW-09 inside PLAN-9E; checkpoint remains PLAN-9D.
  Known fail-safe limitation: `asset_search_fingerprint` still hashes the whole
  visual plan, so a cost-only telemetry change can invalidate `asset_search` even
  when provider queries are unchanged. Fingerprint composition is not changed by
  this repair and remains a later owner decision.
  Repair characterization, after correcting the test fixture itself, was red
  with one failure and one error against pre-repair behavior. The requested
  offline regression radius is 236 OK; mypy on both changed production modules,
  targeted Ruff, docs QA and gates are green. No network, provider, OpenAI,
  Vision, TTS, download or render call ran during the repair.

#### PLAN-9B-2 — expansion + hardcode migration

- **status:** **closed 2026-08-07.** Owner-issued implementation slice —
  один immutable commit `66fd2431`, trailer `Plan-Step: PLAN-9B-2` — прошёл
  **PLAN-6E** independent review, verdict **ACCEPT WITH MINOR** (blocking
  findings **0**), implementation CI run `31164020130` (headSha `66fd2431`)
  зелёный (full offline suite 1772 tests OK, failures=0, errors=0). Review
  finding **F1** (`_mentions_avoided` сравнивал `must_avoid` с query через raw
  whitespace-split, из-за чего punctuation вокруг avoided phrase могла обойти
  блокировку — live-reachable через author `provider_queries`) закрыт bounded
  repair commit `8c60295`: обе стороны сравнения теперь используют единую
  provider-token normalization через существующий `_PROVIDER_TOKEN_RE`,
  consecutive-phrase matching, case-insensitive поведение и non-mutation
  query сохранены. Independent re-review verdict **ACCEPT** (findings **0**),
  repair CI run `31172361739` (headSha `8c60295`) зелёный. Оба commit pushed
  в `governance-reset`. Known non-blocking limitation **F2** — `must_avoid` на
  non-provider языке не сопоставляется семантически с provider-language query
  без translator — зафиксирован как limitation этого шага; `TranslatorService`
  не создавался и не создаётся. Findings F3-F8 исходного review остаются
  non-blocking observations и не превращены в новые обязательные этапы.
  Post-audit stabilization gate (OD-S-1, состав — OD-S-3 и раздел «Blocking
  gate: что должно быть закрыто до возврата к PLAN-9B-2») был **пройден
  2026-08-07**; owner-issued implementation prompt **выдан и исполнен**.
  Retirement пяти мигрированных hardcode-кандидатов остаётся **PLAN-9B-3** ·
  **зависимости:** completed PLAN-9B-4, **PLAN-L0**, **PLAN-9B-PRODUCER**,
  **PLAN-6D**, **PLAN-6E**.
- **цель:** контролируемая лестница расширения плюс снятие topic-specific
  hardcodes из shared engine.
- **лестница запросов:** точный субъект → субъект и действие → субъект,
  действие и локация → синонимы → альтернативные названия сущности → более
  широкий, но не меняющий смысл контекст → другой допустимый визуальный план
  той же идеи. **Предваряется источником provider-языка (9B-1):** без него
  лестница расширяет ноль.
- **salvage knowledge, без восстановления старого pipeline:** legacy
  `build_query_variants` expansion ladder (через PLAN-L0) · semantic query
  ladder `exact → broad → environment → atmospheric` · orca `provider_queries`
  (трёхуровневая структура «точный субъект → группа → среда») · `must_avoid`
  как часть смысла запроса.
- **topic-hardcode inventory — PROVISIONAL.** Число файлов **не фиксируется как
  invariant**: это измерение, а не контракт.
- **порядок обязателен:** replacement working → callers migrated → targeted и
  `full` зелёные → reviewer/gates → **затем** retirement. Удаление любого
  hardcode до переноса полезной capability запрещено.
- **`[HARD]` gate неприкосновенен:** снятие topic-литералов, живущих внутри
  safety gate `modes.blocking_reasons`, требует отдельного обоснования и **не**
  является разрешением менять сам gate.
- **non-goals (добавлено PRODUCT-PLAN-1, scope слайса не расширен):**
  `query_adapter` **не становится** producer provider-language evidence и не
  становится visual planner; `TranslatorService`, `SearchEngine` и
  `QueryOrchestrator` не создаются (OD-13). Канонические направления —
  `visual planning → существующий VisualBrief → query_adapter`.
- **источник provider-языка получил отдельного owner-слайса.** OD-P-1
  запланировал PLAN-9B-PRODUCER внутри существующего visual-planning ownership.
  Он не добавлен в scope PLAN-9B-2: producer и лестница расширения остаются
  двумя независимо проверяемыми user outcome, а PLAN-9B-2 по-прежнему
  пересекает multi-owner, persisted и destructive boundary. Completed PLAN-L0 и
  completed PLAN-9B-PRODUCER достаточным условием не являются: PLAN-9B-2 не
  начинается до закрытого post-audit stabilization gate (**закрыт
  2026-08-07**), отдельного independent stabilization review с положительным
  verdict (**выполнен 2026-08-07**, CLEAR TO PROCEED TO PLAN-9B-2, blocking
  findings 0) и отдельного owner-issued implementation prompt (**выдан и
  исполнен 2026-08-07**).
- **тесты deep-dive:** — (T3 перенесён в PLAN-9B-1 вместе с исправлением
  `source_is_latin`, registry C36; тест не потерян и нового тестового этапа не
  создаётся).
- **risk boundary:** multi-owner diff + persisted содержимое visual plan +
  destructive → **PLAN-6D + PLAN-6E + reversible retirement**. Фактический
  слайс **destructive не выполнял**: ни один hardcode не удалён, reversible
  retirement mechanism не требовался и не применялся.
- **required verification:** targeted + `full`.
- **реализованный механизм (2026-08-07).** Новый canonical reusable owner
  `src/content/visual_planning/expansion.py` держит нормализованный
  provider-language planning input (`QueryPlanningInput`) и саму лестницу:
  точный субъект → субъект и действие → субъект, действие и локация →
  другие **заявленные** имена сущности → более широкий контекст без смены
  смысла → та же идея как её среда → усечение ведущего заявленного запроса до
  двух самых конкретных термов. Синонимы берутся только из
  `exact_entities`/`secondary_subjects`/`must_include`; словарь синонимов,
  translator и второй vocabulary owner **не создавались**. Лестница
  format-neutral: она получает смысл, а не сцену, бриф или план.
  `produce_brief` подаёт в неё seeds — то, что evidence уже сказал дословно
  (structured intents, prepared script keywords, safe claim excerpts) — и
  сохраняет не более четырёх provider queries вместо трёх.
  `query_adapter` остался consumer и не менялся.
- **hardcode migration — фактический результат.** `legacy_broad_query`
  (четыре фиксированные строки про китов, океан и исследователей) **больше не
  имеет живого caller** в canonical writer path: `scene_to_legacy` вместо него
  зеркалит лестницу в плоские `primary_query`/`alternative_queries`. Сама
  функция и `make_stock_query` на момент этого слайса **сохранены**, потому
  что планы, записанные до него, эти строки всё ещё содержат; вместе с ними
  сохранён и exclusion-список из четырёх строк в `query_adapter`
  (`_LEGACY_BROAD_QUERIES`), который отфильтровывает эти литералы при чтении
  старых планов. **Уточнение 2026-08-07 (docs accuracy, contract не
  меняется):** прежняя редакция этого абзаца и `next_exact_action` слайса
  ошибочно включали exclusion-список в перечисление «пяти кандидатов». Это
  ошибка изложения: список retirement candidates задан контрактом PLAN-9B-3 и
  его пятый элемент — obsolete GLOSSARY matcher, а `_LEGACY_BROAD_QUERIES` —
  persisted-compatibility guard, созданный самим PLAN-9B-1 (commit `141beae`)
  уже после составления списка, topic-hardcode не являющийся. Orca topic
  hardcode `_apply_video_first_topic_briefs` — мигрирована **capability**
  (форма ответа, трёхуровневая структура запросов, `must_avoid` как часть
  смысла); он больше не единственный источник этой формы, но этим слайсом
  **не удалён**. Удаление кандидатов принадлежало **PLAN-9B-3** по
  обязательному порядку и выполнено там (closed 2026-08-07, commit
  `72221e1`).
- **salvage consumed:** C46 — порядок, усечение, общий и меньший executed
  лимиты, дедупликация по нормализованной форме. **Намеренно не перенесены:**
  channel-hardcode `survival`, production-суффиксы (`cinematic`,
  `documentary footage`, …) и требование готовых английских ключей на входе.
  Также consumed: semantic ladder `exact → broad → environment → atmospheric`,
  orca `provider_queries` (три уровня) и `must_avoid` как часть смысла запроса
  (сопоставление последовательной фразы, поэтому `Suez Canal` не блокирует
  запрос про Panama Canal).
- **вне scope и не тронуто:** GLOSSARY matcher · `semantic_selection/
  query_generator` · orca-литералы внутри `[HARD]` gate
  `modes.blocking_reasons` · `candidate_ranker` · legacy raw HTTP backlog
  (`src/asset_finder.py`, `src/video_asset_engine.py`, `src/music_engine.py`,
  `src/production_plan/**`).
- **persisted/public impact:** изменились только **значения** существующих
  полей `visual_brief.provider_queries`, `primary_query` и
  `alternative_queries`. Новых полей, schema version, layout, artifact,
  public CLI/API, manifest, rights- и network-семантики нет; tripwire OD-P-1
  не сработал.
- **фактическая verification (2026-08-07):** targeted owner/caller radius —
  321 тест, exit code 0; downstream consumers — 56 тестов, exit code 0;
  canonical characterization suite — 4 теста, exit code 0; full offline suite —
  1772 теста, exit code 0, `OK`, failures=0, errors=0;
  `tools.qa.check_agent_docs` — exit code 0; `tools.qa.check_task_scope` с
  точным allowlist — `OK`; `git diff --check` — без замечаний. Числа и
  длительности — измерения, не нормативы. Package network guard активен;
  network, provider search, download, model API, Vision, TTS, paid calls и
  реальный render не выполнялись. Test effectiveness: pre-change owning тест
  `test_the_old_broad_english_query_survives_as_the_last_resort` падал ровно на
  мигрированной строке, а синтетическая мутация (лестница отключена, остаются
  только seeds) дала 11 failures + 2 errors в новых owning тестах; мутация
  снята, репозиторий не портился.

#### PLAN-9B-3 — query-path cleanup

- **status:** completed · **completed:** 2026-08-07 · **commit:** `72221e1`
  (`72221e1861f7c62de01aa09056cfaf6f56ef99a7`) · **зависимости:** PLAN-9B-2,
  **PLAN-6E**.
- **выполняется только ПОСЛЕ работающей замены.**
- **кандидаты на retirement** (ни один не удаляется раньше переноса уникального
  knowledge и всех callers): obsolete GLOSSARY matcher · orca topic hardcode ·
  `legacy_broad_query` · deprecated `make_stock_query` · superseded semantic
  `query_generator` — **только после миграции всех callers**.
- **risk boundary:** destructive retirement → **PLAN-6E + reversible retirement
  mechanism** (annotated tag + внешний `git bundle` + строка `Retired`).
- **required verification:** targeted + `full`.
- **note (добавлено 2026-08-07, docs-only, contract не расширяет).**
  Read-only аудит подтвердил на факт HEAD `4ffdc48892a`: envato-manual
  request construction в `src/news/asset_manifest_builder.py` (метод,
  строящий `manual_request` при `envato_manual_fallback_enabled`) берёт
  запросы через `ordered_queries(state.semantic_scene)`, а `ordered_queries`
  определён именно в **superseded** `src/assets/semantic_selection/
  query_generator.py` — том же кандидате на retirement, что перечислен выше.
  Это напоминание уже действующего правила «выполняется только ПОСЛЕ
  работающей замены» и «ни один кандидат не удаляется раньше переноса
  уникального knowledge и всех callers»: при retirement superseded
  `query_generator` этот envato-manual caller обязан быть мигрирован на
  canonical query output (после PLAN-9B-2 expansion), иначе envato-manual
  query source будет молча потерян. Новое условие/зависимость этим не
  добавляется.
- **фактический результат (2026-08-07, commit `72221e1`).** Owner-issued
  implementation slice выполнен одним immutable commit. Порядок соблюдён:
  замена (PLAN-9B-2 ladder через `src/content/visual_planning/expansion.py`,
  достижимая из `SemanticScene` через `legacy_format.semantic_scene_queries`)
  работала до retirement, и все живые callers мигрированы до удаления —
  `src/news/asset_manifest_builder.py` (четыре call site, включая
  envato-manual `manual_request`) и `src/production_plan/youtube_shorts.py`.
  Envato manual query source сохранён, а не потерян: предупреждение note выше
  выполнено буквально. Retirement выполнен физически: `legacy_broad_query`
  (`src/content/visual_planning/legacy_format.py`), `make_stock_query`
  (`src/news/visual_plan.py`), `_apply_video_first_topic_briefs`
  (`src/news/script_generator.py`) и весь модуль
  `src/assets/semantic_selection/query_generator.py`.
- **disposition пяти retirement candidates — все пять закрыты.**
  **Формулировка «четыре из пяти закрыты» фактически неверна и запрещена.**
  1. **obsolete GLOSSARY matcher (registry C34)** — harmful substring
     implementation (строка `if russian in text and english not in matched:`)
     физически удалена **раньше**, commit `141beae` (`Plan-Step: PLAN-9B-1`),
     и заменена матчингом по границам токенов с ограниченной морфологией
     (`_word_tokens` / `_contains_lexicon_phrase` / `_lexicon_token_matches` /
     `_GLOSSARY_STEMS`). Словарь `GLOSSARY` сохранён намеренно — этого прямо
     требует сам action C34 («состав терминов сохраняется как seed»). На HEAD
     substring-матчинга против `GLOSSARY` не осталось, поэтому у PLAN-9B-3 по
     C34 объекта удаления не было; строка исполнена, а не пропущена.
  2. **orca topic hardcode `_apply_video_first_topic_briefs` (C35)** —
     ретайрен этим commit, строка **R01**.
  3. **`legacy_broad_query` (C36)** — ретайрен этим commit, строка **R01**.
  4. **deprecated `make_stock_query` (C37)** — ретайрен этим commit, строка
     **R01**.
  5. **superseded `semantic_selection/query_generator.py` (C38)** — ретайрен
     этим commit, строка **R01**.
- **`_LEGACY_BROAD_QUERIES` — compatibility guard, а не шестой candidate.**
  Exclusion-список из четырёх строк в `src/assets/query_adapter.py`
  retirement candidate'ом PLAN-9B-3 **не является и никогда не являлся**:
  он создан commit `141beae` в **PLAN-9B-1**, то есть позже составления
  списка кандидатов (ревизия 2.1, 2026-07-31); он не производит запросы, а
  только отфильтровывает ретайренные литералы при tolerant flat read планов,
  записанных до слайса. Сохраняется намеренно. **Exit condition:** guard
  снимается, когда pre-slice persisted планы перестают читаться; до этого
  снятие вернуло бы legacy broad literal в живой запрос. Записан в
  `CLEANUP_REGISTRY.md` рядом с историей C36/R01; отдельный PLAN-ID под него
  не создавался.
- **reversible retirement mechanism — выполнен целиком и проверен.**
  (1) annotated tag `retired/query-paths-2026-08-07` на `1bbfcad` —
  последний commit, где ретайренный код ещё существовал; (2) commit body
  несёт `Retired:`, `Reason:`, `Replaced-by:`, `Recovered-from:`,
  `Salvaged:`, `Exit:`; (3) строка **R01** добавлена в таблицу `Retired`
  реестра тем же commit; (4) внешняя копия — `git bundle`
  `query-paths-2026-08-07.bundle` записан во внешний workspace вне worktree
  и вне репозитория (owner decision по пути зафиксирован в
  `CLEANUP_REGISTRY.md`). До этого слайса механизм ни разу не исполнялся.
- **фактическая verification (2026-08-07):** targeted 243 OK; expanded
  regression radius 209 OK; полный offline suite 1780 OK;
  `tools.qa.check_agent_docs` exit 0; `tools.qa.check_task_scope` OK;
  `git diff --check` clean. Сеть, provider search, download, model API,
  Vision, TTS, платные вызовы и реальный render не выполнялись.
- **independent review и CI.** Independent review verdict **ACCEPT WITH
  MINOR**, blocking findings **0**. GitHub Actions run `31195789804`,
  headSha `72221e1861f7c62de01aa09056cfaf6f56ef99a7`, conclusion
  **success**.
- **findings review — все non-blocking, ни один не исправлялся этим слайсом
  и ни один не получил новый PLAN-ID.**
  **F1 — FOLLOW-UP / BACKLOG.** Assertion `semantic_queries` в
  `tests/test_youtube_shorts_production_plan.py` проходит вакуумно на пустом
  списке. Дом — уже записанный в PLAN-9B-2 backlog `src/production_plan/**`.
  **F2 — INFO / NO ACTION.** `semantic_queries` пуст для legacy scenes без
  provider-language evidence, production reader этого поля не найден. Это
  заявленное fail-closed поведение границы PLAN-9B-PRODUCER, а не регрессия.
  **F3 — FOLLOW-UP / BACKLOG, pre-existing.** Legacy broad literal может
  вернуться через no-brief `_latin_terms` fallback в
  `src/assets/query_adapter.py`; вне diff этого слайса. Записан как
  non-blocking observation рядом с историей C36/R01 и exit condition
  `_LEGACY_BROAD_QUERIES`.
  **F4 — FOLLOW-UP / BACKLOG, pre-existing.** Envato consumer cap `[:3]`
  применяется до provider synthetic completion; cap этим слайсом не менялся.
  Дом — существующий unscheduled candidate **ENVATO-CS1**.

#### PLAN-9B-5b — retirement `apps/news_to_short`

- **status:** pending · **зависимости:** PLAN-9B-5a **и** миграция всех
  callers; **PLAN-6D**, **PLAN-6E**.
- **порядок обязателен: capability сначала мигрируется, wrapper удаляется
  только потом** (OD-2, OD-19, registry K08, C42).
- **capability parity check — обязателен перед retirement (2026-08-01).**
  Список уникальных возможностей wrapper'а в прежней редакции был неполон,
  поэтому перед удалением проводится полный parity inventory
  `apps/news_to_short`. Минимум уже известных возможностей:
  **A.** named source-text input (`--text` / `--text-file`) → canonical
  first-class source-material contract (PLAN-9B-5a);
  **B.** user supplied assets at project creation (`--assets` →
  `NewsJob.user_assets`) → либо мигрировать в canonical Content Creator create
  path, либо получить **явное owner decision** о намеренном retirement этой
  capability. [FACT] у канонического `create` доказанного эквивалентного
  create-time входа нет; второй носитель `pipeline.py --news-to-short --assets`
  умирает в PLAN-L4. **Молчаливо потерять `--assets` запрещено.**
  Точный public CLI для user-assets сейчас не проектируется: это
  implementation decision и public-surface tripwire.
- **user outcome (добавлено PRODUCT-PLAN-1).** Owner decision по пункту **B**
  принят: user assets **мигрируют**, а не ретайрятся. Требуемый результат —
  пользовательские материалы становятся **first-class canonical Content Creator
  input**, доступным через канонический CLI/application request, а не
  сохраняются «ради wrapper parity». Переиспользуются существующие
  `ContentCreationRequest` и `NewsJob.user_assets`; новая логика отбора и
  хранения не создаётся. Точное публичное имя входа остаётся public-surface
  tripwire и решается в момент implementation (`PRODUCT_PLAN.md`, OD-P-5).
- **разрешается только после:** parity inventory wrapper'а; миграции всех
  сохраняемых capabilities; миграции callers; PLAN-6D; PLAN-6E; reversible
  retirement; targeted + smoke + `full`.
- **risk boundary:** destructive retirement реализации, у которой есть callers
  (test-callers и собственный README) → **PLAN-6D + PLAN-6E + reversible
  retirement**.
- **required verification:** targeted + smoke + `full`.

### PLAN-9C — semantic decision wiring

- **status:** completed · **completed:** 2026-08-08 · **commit:** Git log —
  trailer `Plan-Step: PLAN-9C` on three commits `8932957`, `668ff10`,
  `8c1186f` (собственный hash докс-only closure commit внутри того же commit
  не записывается, см. Execution protocol, пункт 3). Прежде: pending, оба
  gate сняты — **PLAN-6E** завершён 2026-08-02 (semantic decision boundary),
  **PLAN-1C′** и **C01-SEM** закрыты 2026-08-07.
- **фактический результат closure (2026-08-08).** `8932957` подключил
  существующий Vision/semantic evidence producer (`semantic_visual_service`)
  внутри цикла отбора сцены к bounded shortlist — до скачивания, а не только
  после него из `_write_reviews`, как раньше; evidence достигает
  существующего decision owner через поле, которое тот уже читает
  (`vision_tags` → `evidence.build_evidence` → `candidate_ranker`,
  reject `must_avoid_match`/`vision_mismatch`); `select_best_candidate`
  остаётся единственным decision owner, второй selector/Vision stack/scoring
  system/budget mechanism/manifest не создан; попутно закрыт ранее
  зафиксированный дефект отчётности `semantic_rerank_enabled=False`.
  `668ff10` закрыл blocking finding независимого review: шипованный default
  `MockSemanticVisualBackend` подтверждал любое требование прямо из запроса,
  так что включение `semantic_visual.enabled`+`semantic_rerank_enabled` могло
  превратить `publish_ready` в `true` на fixture evidence; исправление
  отказывается применять evidence, когда сконфигурированный backend —
  fixture (проверка по имени backend, не по `paid_backend`); mock сохраняет
  только report/test роль без production reselection authority. `8c1186f`
  закрыл второй finding: guard-регрессионный тест был вакуумно зелёным
  (использовал `_WIRED` fixture с именем `"scripted"`, резолвящимся в
  `ExternalSemanticVisualBackend`, а не в mock); тест переведён на резолвер
  реального default backend, mutation-proof владельца (временное обнуление
  `FIXTURE_SEMANTIC_BACKENDS` вне commit) подтвердил провал теста без guard
  `668ff10`; production-код этим commit не менялся. Final independent review
  на `8c1186f` — verdict **ACCEPT**, blocking findings **0**
  (owner-provided evidence, отдельного review-commit в Git нет, тот же
  паттерн что PLAN-STAB-1/2/3). GitHub Actions run `31250693048` (headSha
  `8c1186f`, workflow `offline-tests`) — conclusion **success**
  (owner-provided evidence); отдельная read-only CI check на headSha этого
  docs-only closure commit выполняется после push. Default-конфигурация не
  менялась — `semantic_visual.enabled` и `semantic_rerank_enabled` остаются
  `false`, активация остаётся gate **PLAN-9E**. **F2** (после semantic
  demotion состав bounded shortlist/review window может измениться —
  pre-rerank preview set не равен post-rerank review bundle set) — MAJOR,
  **NON-BLOCKING** для этого contract (wiring/order, не budget/размер
  shortlist), задокументирован bounded follow-up bullet'ом в `### PLAN-10C`
  ниже, не исправлялся, новый PLAN-ID не создавался. Другие findings review
  (метки R2-R5) зафиксированы как non-blocking по тому же final verdict; их
  содержание не передавалось и в Git не найдено, поэтому не детализированы.
  Production-код, tests, схемы, config и runtime этим docs-only closure
  слайсом не менялись.
- **что зафиксировал PLAN-1C′ для этого слайса (evidence, не проект решения):**
  единственный владелец решения об отборе — `rank_candidates` /
  `select_best_candidate` в `src/assets/semantic_selection/candidate_ranker.py`;
  Vision сегодня вызывается из `_write_reviews` **после** отбора всех сцен и
  пишет evidence только в `assets/review/visual_review_manifest.json`. Два уже
  существующих seam: bounded shortlist плюс `select_candidate_after_review` в
  `_prepare_visual_review` (единственная точка внутри цикла сцены, где evidence
  способно изменить выбор до скачивания) и приём `vision_tags` существующим
  decision owner (`evidence.build_evidence` → `candidate_ranker`, reject
  `vision_mismatch`, покрыт offline-тестом). Заглушка `vision_validator` не
  вызывается ниоткуда, `semantic_decision_policy` не подключён ни к одному
  production-пути. Детали — секция `C01-SEM` в `CLEANUP_REGISTRY.md`.
- **порядок подтверждён (OD-22):**
  `provider-ready query → candidates → semantic/Vision → rank/select`.
  Подключать Vision к ранжированию кандидатов, которых ноль, бессмысленно.
- **исправлено ревизией 2.1 — механизм.** Формулировки «semantic не может
  влиять на selection» и «selection fingerprint запрещает rerank»
  **опровергнуты**. [FACT] metadata-semantic слой уже **ranks**, **rejects**,
  **blocks** и **может изменить выбранный asset** — доказано synthetic-пробой
  через живой ingestion seam. `_selection_fingerprint` — защитная
  самопроверка, а не вето.
- **фактическая проблема:** платный Vision-сервис пишет результат **поздно** — в
  review-манифест после цикла отбора — и **не подаёт evidence в decision layer
  до selection**.
- **цель:** **producer → existing semantic consumer wiring.** Target:
  `provider-ready candidates → Vision/semantic evidence → существующее semantic
  ranking → selection`. **Новый semantic stack не создаётся.**
- **отдельно зафиксированный дефект отчётности:** `_semantic_visual_summary`
  жёстко пишет `semantic_rerank_enabled=False` независимо от фактического
  конфига. Это дефект **отчётности**, а не решения; читателей этого поля из
  манифеста нет.
- **user outcome и acceptance criteria (добавлено PRODUCT-PLAN-1).** Vision —
  **committed product capability** (`PRODUCT_PLAN.md`, раздел «Vision AI»), и
  этот слайс является её wiring owner. Требуемый порядок: `provider search →
  deterministic normalization/ranking → **bounded shortlist** лучших кандидатов
  → Vision evidence → существующее semantic decision/selection → human review
  при необходимости`. Evidence обязано попадать в существующий decision layer
  **до** отбора; выполнение Vision после окончательного выбора, когда её вывод
  уже не способен повлиять на результат, приёмкой не считается. Размер
  shortlist и бюджет принадлежат PLAN-10C.
- **разрешённые зоны:** production asset selection path.
- **запрещено:** создавать второй visual planner, Vision stack или asset
  pipeline; изменять default-поведение в этом slice; **использовать mock
  semantic backend как влияющий на production selection** — mock допустим
  только в wiring-тестах и не является доказательством визуального качества.
- **non-goals Vision (добавлено PRODUCT-PLAN-1):** не создавать
  `VisionAssetManager`, `VisionSearchEngine`, второй candidate selector, вторую
  completion ladder, отдельный project state и новый semantic manifest, пока не
  доказано, что существующих evidence/review manifests недостаточно.
  Состояние «требуется проверка человеком» берётся из существующего словаря
  `src/assets/completion/modes.py`; второй словарь не вводится.
- **второй момент использования того же evidence (добавлено 2026-08-01,
  OD-M-6).** Помимо review кандидатов-ассетов, тот же Vision evidence-провайдер
  позднее применяется к **poster frame собранной композиции сцены**: смысл
  сцены, читаемость, визуальная иерархия, misleading, «недоделанный вид».
  Это **тот же producer в той же роли**, а не второй Vision stack, не второй
  selector и не отдельный pipeline; verdict попадает в существующий
  decision/review слой, а «требуется проверка человеком» — в существующий
  словарь. **Реализация принадлежит candidate slice `MOTION-CS4`** и требует
  рабочего scene preview (`MOTION-CS1`, registry C58); scope, статус и
  зависимости PLAN-9C этой записью не меняются.
- **измеримый результат:** wiring доказан тестами; default-конфигурация
  поведения не меняет.
- **required verification:** targeted selection/wiring tests + `full`, так как
  меняется shared production decision path.
- **rollback:** один commit.

### PLAN-9C-2 — unified media-selection policy foundation (рабочий ярлык R-2a)

- **status:** completed 2026-08-10 · owner-issued 2026-08-10 (plan
  reconciliation после LIVE-4 и comparative audit) · unified policy commit
  `388b9b1`; blocking repair **PLAN-9C-2-B1** commit `709eaec`; retrieval
  symmetry — `ae6d46c`; post-audit correction **VA-NEW-03** — **этот commit**.
  Других обязательных sub-slices секция не содержит.
- **policy implementation `388b9b1`.** Канонический decision owner —
  `src/assets/semantic_selection/media_policy.py`
  (`select_with_media_policy`): ранжирование остаётся у
  `select_best_candidate`; политика поверх его результата применяет hard
  whitelist существующего `allowed_media_kinds` (единственный допустимый вид
  без допустимого кандидата → честный abstain, не скрытая подмена) и bounded
  video-предпочтение только среди конкурентных кандидатов — тот же
  `SUPPORT_RANK`-класс, что у лучшего, права/review не хуже,
  mode-independent `blocking_reasons` молчит, и только внутри review-окна
  (`shortlist_size`; в builder один owner окна `_review_window_size`).
  Безусловная подмена «первое не-отклонённое видео любого ранга» удалена:
  `select_best_with_video` — thin-делегация к политике (имя сохранено для
  PLAN-9D harnesses до retirement gate), facade-дубль
  `asset_manager._select_best_candidate` — та же делегация, его закрепляющий
  тест перенацелен на bounded-контракт; post-Vision reselection идёт через ту
  же политику с тем же окном. Числовой score-gap не вводился; новых
  persisted/config полей нет — trace пишется существующим полем
  `selected_by` (`media_policy_video_preference` /
  `media_policy_video_preference_fallback`). Красные-сначала характеризации
  сняты на HEAD `bbe5147`: CASE 1, CASE 5 и оба LIVE-4 кейса падали
  (production выбирал partial-видео поверх full-кадра и видео вне
  превью-окна); контракт-файл `tests/test_media_selection_policy.py` (21
  тестов) закрепляет все пять acceptance cases, LIVE-4 регрессии, rights и
  делегацию обоих entry points.
- **blocking repair PLAN-9C-2-B1.** Independent review доказал, что
  `completion/ladder.py` оставался вторым reachable video-first selector:
  после canonical выбора draft-ветка сужала pool до любого usable video и
  возвращала его primary с trace `video_first:video_pool`. RED на baseline
  `388b9b1`: canonical FULL image сохранялся перед completion, но B1-1
  завершался PARTIAL video; B1-2 позволял video обойти
  `allowed_media_kinds=["image"]`; B1-4 воскрешал video за review-window;
  competitive FULL/FULL B1-3 оставался green. Выбран вариант A: переданный
  builder-ом `strict_selection` становится `authoritative_primary`, ladder
  может добавлять complementary slots вокруг него и выполнять usability /
  reuse / emergency fallback, но не переизбирает primary. Собственные
  `prefer_video` parameter, video-pool narrowing и `video_first:*` trace из
  ladder/completion удалены; hard whitelist fallback-pool применяет те же
  primitives canonical `media_policy`, без копии `_competitive_video` или
  score/window правил. Builder integration test закрепляет передачу уже
  выбранного primary вместо прокладки второго policy-input набора. Evidence:
  policy + completion radius 64 OK; owning radius 243 OK; PLAN-9D
  characterization 167 OK; полный offline suite 2123 OK.
- **post-audit correction VA-NEW-03.** Integrity audit доказал ещё один
  config-reachable post-selection owner: `_prepare_visual_review` при
  `technical_rerank_enabled=true` заменял уже выбранный manual/media-policy
  asset результатом `select_candidate_after_review`, который не применял
  semantic rejection/conflict/must-avoid и `allowed_media_kinds`. RED на
  baseline `963bfff`: 5 из 7 production-builder checks заменяли manual,
  rejected/conflicting, image-only и canonical media-policy winner технически
  более сильным video. Builder больше не вызывает legacy helper и не присваивает
  новый winner после preview; flag сохранён default OFF как compatibility
  advisory/report input, technical scores/crop/duplicate/reasons остаются в
  существующем review bundle, а честный `analysis_mode=technical_analysis`
  отличает evidence от rerank. Rights-blocked и default-false contracts не
  ослаблены; Vision, nonsemantic mode, download/completion, continuity и
  providers не менялись. GREEN: новые checks 7/7, owning offline radius 431 OK,
  полный offline suite 2150 OK.
- **routing.** `current_checkpoint` остаётся **PLAN-9D**. Bounded
  correctness-слайс decision-слоя; суффикс родственного ID следует существующей
  конвенции (PLAN-9B-2, PLAN-9D-A…G). Evidence-семейством PLAN-9D не является;
  выполняется **до** PLAN-9D-D. Evidence:
  `docs/audits/VISUAL_ASSETS_COMPARATIVE_AUDIT_2026-08-10.md` (части I-II),
  секция PLAN-9D-C (SELECTED-CANDIDATE verdict WEAK), LIVE-4 manifests.
- **зачем.** Production-выбор сцены проходит через `select_best_with_video`
  (`src/news/asset_manifest_builder.py:1239`): первое не-отклонённое видео на
  **любом** ранге подменяет выбор `select_best_candidate`. Измерено: 9D-C —
  7 из 12 сцен (ранги до 14, выборы вне превью-окна в 3 сценах); LIVE-4 —
  scene_003 (видео 65.75 вместо hovering-кадра 80.72 ранга 1), scene_004
  (zoo-видео 70.0 вместо snow-кадров 80.0). Продуктового мандата у безусловного
  `prefer_video=True` (`src/news/asset_manager.py:146`) нет: ни в PRODUCT_PLAN,
  ни в ADR, ни в contracts; «предпочтительный тип визуала для сцены» — [HINT].
- **цель.** Одна каноническая media-selection policy вместо безусловной
  подмены. Canonical pipeline сохраняется; legacy pipeline не возвращается;
  **четвёртый selector не пишется** — переиспользуются существующие semantics:
  `SUPPORT_RANK`, `evaluate_usability`, `tie_break_key`, `allowed_media_kinds`,
  decision records (строгая support-gated ветка `completion/ladder.py` —
  готовая основа, сегодня мёртвая в production). Режимы: AUTO/BEST MATCH (без
  глобального video-bias), PREFER_VIDEO (только среди конкурентных допустимых
  кандидатов — тот же support/slot-класс, не хуже по rights/review, технически
  пригоден), VIDEO_ONLY / IMAGE_ONLY (hard constraints: нет допустимого типа →
  abstain/review). Media selection не может обходить rights / semantic
  admissibility / required slots; post-Vision использует **того же** decision
  owner; пользовательский/manual authority не переизбирается автоматически.
  Дубль `asset_manager._select_best_candidate` ретайрится внутри слайса с
  перенацеливанием закрепляющих тестов.
- **acceptance cases (поведение, не implementation):** (1) full-support image
  не вытесняется partial-support video только из-за типа; (2) при равно
  допустимых full/full PREFER_VIDEO может выбрать видео; (3) в AUTO тип media
  сам по себе не переопределяет лучший semantic result; (4) VIDEO_ONLY /
  IMAGE_ONLY — hard: нет допустимого кандидата нужного типа → abstain/review,
  а не скрытая подмена другим типом; (5) после preview/Vision кандидат вне
  evaluated decision set не может стать финальным победителем. Числовой
  score-gap не вводится без evidence.
- **retrieval symmetry (этот commit).** RED на baseline `709eaec` подтвердил
  асимметрию: preferred=image при allowed image+video запрашивал только image;
  opposing preference обходил single-kind hard boundary. Retrieval owner
  `search_provider` теперь строит запросы из пересечения routable
  `allowed_media_kinds` и `ProviderCapabilities.media_types`; preference только
  задаёт порядок (image→video или video→image). IMAGE_ONLY/VIDEO_ONLY делают
  ровно один поддерживаемый запрос. Missing/empty список либо список без
  routable kinds сохраняет legacy preferred-only fallback;
  отсутствующий `visual_type` по-прежнему даёт legacy default video. Результаты
  обоих вызовов объединяются прежним `extend` без нового ranker; каждый запрос
  остаётся `AssetSearchRequest(max_results=limit)`. Query/provider attempt
  accounting, classified provider errors, per-provider caps и default-deny
  `provider_search` network gate не ослаблены; paid gate не затрагивался.
  Production integration доказывает путь scene → builder → adapter → оба
  запроса. Evidence: новые checks 8/8 OK (на RED 6 failures), owning offline
  radius 226 OK, полный offline suite 2131 OK.
- **не входит:** metadata-evidence repair (**PLAN-9C-3**); shortlist/dedup/
  evidence-set identity (**PLAN-10C**, включая записанный F2); download
  replacement persistence (**PLAN-9A**); LocalLibrary convergence / diversity
  reserve (**PLAN-10D**); cleanup/retirement legacy-контуров; Motion
  (MOTION-CS1..CS4, Remotion/HyperFrames); Vision activation (**PLAN-9E**);
  права.
- **required verification:** выполнено по каждому sub-slice: красные-сначала
  characterization tests, B1 draft-completion regressions, owning
  selection/manifest/provider/network radius и полный offline suite. Для
  retrieval symmetry: 8/8 новых checks, 226 owning tests и 2131 full-suite
  tests — OK; docs/scope QA фиксируются этим commit.
- **rollback:** этот correction commit + `ae6d46c` + `709eaec` + `388b9b1`,
  revert в обратном порядке; миграций данных нет.

### PLAN-9C-3 — metadata evidence repair (рабочий ярлык R-2b)

- **status:** completed 2026-08-10 · owner-issued 2026-08-10 · **commit:**
  `7e9b34a`; post-audit correction **VA-NEW-01** — **этот commit** ·
  **зависимость:** PLAN-9C-2 выполнена; общий acceptance gate остаётся
  отдельным LIVE-5 diagnostic.
- **routing.** `current_checkpoint` остаётся **PLAN-9D**; PLAN-9D-D остаётся
  NOT STARTED / blocked до LIVE-5 и owner decision. С PLAN-9C-2 не смешан:
  media policy, completion ladder и retrieval symmetry не менялись.
- **causal root.** `provider_evidence_text` терял field boundaries, после чего
  один global token set питал `concept_score`, `_field_match` и slot verdict.
  Поэтому слова многословного concept из разных частей catalogue prose и одно
  случайное имя внутри series synopsis получали тот же score 100, что title.
- **repair.** Canonical owner `src/assets/semantic_selection/evidence.py`
  сохраняет provider-authored поля отдельно. `title`, provider `tags`/
  compatibility `keywords` и Vision tags остаются strong; multiword concept в
  `description` получает full evidence только из coherent lexical window
  (не более шести intervening tokens), а одиночное слово только в broad
  description даёт supporting 75, не matched 100. Общая длина description
  ничего сама по себе не запрещает: локальная многословная фраза остаётся 100.
  `candidate_ranker` и positive subject/action/location/context slots используют
  один этот owner; hard `must_include`, `must_avoid` и declared conflicts
  намеренно сохраняют прежний strict corpus-wide matcher.
- **field synchronization.** `METADATA_FIELDS` теперь соответствует canonical
  `AssetCandidate`: `title`, `description`; `tags` и `keywords` обрабатываются
  отдельной существующей label-веткой. Мёртвые flat fields `categories`,
  `depicts`, `location` удалены из evidence contract; schema не расширялась.
- **IA normalizer.** Не изменён: он уже честно отображает `title`, `description`
  и `subject → tags`; defect был provider-neutral в shared evidence owner.
- **provider_confidence disposition.** Не подключён к semantic/final score и
  не менялся. Repository truth: поле уже persisted и служит поздним tie-break
  completion ladder; превращать provider brand в evidence penalty запрещено.
- **negative_terms disposition.** `AssetSearchRequest.negative_terms` сохранён
  как публичное dormant compatibility field; producer остаётся прежним,
  provider-consumer не добавлялся и поле не удалялось, поскольку это было бы
  новым provider behavior, не causal repair.
- **LIVE-4 acceptance evidence.** Persisted manifests перепроверены read-only:
  Sierra Negra subject `100/matched → 50/partial`, natural-habitat evidence тоже
  `100 → 50`; Life On Earth hummingbird `100/matched → 75/partial`. Positive
  Pexels hummingbird и orca остаются `100/matched`; rights неизменны.
- **RED/GREEN/verification.** На baseline первые 10 checks дали 5 failures;
  итоговый contract — 12/12. Owning + integration + PLAN-9D radius — 375 OK;
  full offline suite — 2143 OK. PLAN-9D frozen raw pool не менялся; только
  recomputable scene_004 category `regression_capable → no_acceptable_candidate`,
  два derived counters и corpus checksum re-finalized до
  `bfb4d02437f3c52879c98367558de339ffb8e352d6dd4ef743e14c4185ccf1b4`.
- **unchanged/out of scope.** Rights, semantic-brief parser, Vision/backend,
  media policy/PLAN-9C-2, PLAN-10C, PLAN-9A, PLAN-10D, shortlist/dedup,
  download walk, LocalLibrary, Motion/legacy cleanup не менялись.
- **post-audit correction VA-NEW-01.** Integrity audit нашёл последнего
  consumer, читавшего evidence мимо canonical owner этой секции.
  `_environment_for_scene` (`continuity_checker.py`) склеивал `search_query`,
  `source_url` и `source_page` с provider prose, поэтому запрос к провайдеру и
  папка хранения доказывали *содержание* кадра, а `build` дописывал уже
  **resolved** сцену в `missing_scenes` — а это попадает в
  `missing_assets.json` и делает `src/projects/rights.py` отчёт `blocked`
  вместе с exit code CLI. На замороженном реальном capture
  `tests/data/plan9d/current_corpus_v1.json` (1064 кандидата текущего HEAD)
  непустой `search_query` и source URL несут **все** кандидаты; environment-
  слово присутствует только в `search_query` у 55 и только в source URL у 6, а
  инференс среды меняется под canonical evidence у 63. Repair: continuity
  читает `evidence.build_evidence` этой же секции (provider `title`/
  `description`/`tags`/`keywords` без query-эха и без `tags_source=
  "query_derived"`, плюс validated Vision tags), а builder больше не пишет
  `missing_scenes` из continuity. Authority: единственный владелец
  разрешённости сцены — `_record_scene`; блок `continuity` манифеста не
  менялся и остаётся отчётом. Инференс (три английских набора слов и один
  переход) намеренно не трогался, второй matcher не создан. RED на `a9bfc11`:
  11 из 16 новых checks; GREEN 16/16, targeted radius 568 OK, полный offline
  suite 2166 OK, `scripts/gates.py` зелёный без новых ruff/mypy suppressions.
  Отбор, media policy, rights, `must_avoid`, conflicts, strict/draft, Vision
  activation, providers и schema не менялись.
- **rollback:** один commit, revert; миграций данных и provider calls нет.

### PLAN-9C-4 — пофайловая доказуемость

- **status:** done (этим слайсом, 2026-08-17) · **commit:** слайс пакета **D**,
  ищется в `git log` по `C91` · **зависимость снята не так, как ожидалось:**
  требовался «корпус v2 закрыт и размечен», фактически хватило собранного
  корпуса v2 без разметки — оба числа приёмки считаются по победителям, а
  разметка нужна для agreement, а не для смены победителя. Owner decision
  2026-08-17 — **вариант A**. Пакет **D** маршрута
  [ROLLOUT_PLAN_2026-08-17.md](../audits/ROLLOUT_PLAN_2026-08-17.md).
- **цель:** корневая причина `C91` — вердикт «доказуемо или нет» выносится по
  склеенному тексту записи, а не по полю, дающему балл. `is_undecidable`
  становится пофайловым, один примитив на все пять точек вызова.
- **состав:** characterization-тест первым — он именует `script_mismatch` и
  `is_undecidable`, которых до `3aff877` не было ни в одном файле `tests/`
  (сделано отдельным слайсом, см. ниже); затем правка
  `src/assets/semantic_selection/evidence.py`; расширение формулировки `C91` на
  слой запретов **до** начала работ, потому что вариант A шире её нынешней
  редакции; авторский запрет начинает видеть склонения — MAJOR независимого
  ревью [REVIEW_C79_C89_2026-08-17.md](../audits/REVIEW_C79_C89_2026-08-17.md).
- **запрещено:** второй примитив доказуемости — строка `C91` запрещает его
  прямо; приёмка на корпусе v1; смешивание с PLAN-9D-H в одном слайсе.
- **измеримый результат:** на корпусе v1 ноль изменившихся победителей
  (аддитивность), на v2 сдвиг назван поимённо. Приписка к `C91`: исправлено,
  коммит, числа до и после.
- **класс риска:** **HIGH** (отбор и слой запретов). Owner decision до работы
  получен; независимый `review-change` после обязателен; findings закрываются
  тестами, а не отдельным слайсом.
- **сделано до начала пакета — commit `3aff877` (LOW, тест-only, поведение
  отбора не менялось, checkpoint не двигался).** Прибор для этого шага
  существует: `GluedEvidenceDecidabilityCharacterizationTest` в
  `tests/test_metadata_evidence_repair.py` (owner-модуль `evidence.py`, как у
  `C79`/`C89`). Заморожено на двух записях, различающихся ровно языком поля
  `tags`: `is_undecidable` = True при literal/semantic 100.0, `semantic_score`
  0.0 против 100.0, `final_score` 13.875 против 98.875, отказ `score_below_75`,
  слот `subject` — `undecidable`, `must_include` из `title` —
  `semantic_unverified`. Пятый тест — guard: русское направление разрешимо
  сегодня и обязано остаться разрешимым. Под вариантом A, подставленным в
  память, краснеют 3 теста из 5; два зелёных — баллы по полям и guard.
- **уточнение к «один примитив на все пять точек вызова», измерено тем же
  слайсом.** Подстановки в `CandidateEvidence.is_undecidable` **недостаточно**.
  Цикл `must_include` в `candidate_ranker` зовёт модульный `script_mismatch` по
  склейке напрямую, минуя evidence: при исправленном методе слот требования
  становится `matched`, а отказ `semantic_unverified:<термин>` остаётся — запись
  по-прежнему отклонена за требование, стоящее в её `title` дословно, и уже без
  слота, который бы это объяснил. Пятая точка входит в состав правки отдельной
  строкой; иначе приёмка D пройдёт при неисправленном отказе.
- **сделано и измерено этим слайсом.** Правок две: `is_undecidable` спрашивает
  каждое поле (`all(script_mismatch(concept, f.text) for f in fields)`, отдельной
  веткой — запись без полей, потому что `all()` по пустому даёт `True`), и цикл
  `must_include` в `candidate_ranker` спрашивает evidence вместо модульного
  примитива по склейке. Алиас `_script_mismatch` удалён вместе с последним
  вызывающим — иначе слайс сам заводит второй `C90`. Характеризация `3aff877`
  покраснела ровно в трёх предсказанных тестах и переписана с «до» на «после»;
  два записи, различающиеся языком одного тега, теперь равны (98.875 против
  98.875 при 13.875 до правки), а отказ `semantic_unverified` исчез полностью —
  это вклад именно пятой точки, при одной первой правке он оставался.
- **числа приёмки, оба измерены.** **v1: `changed_winners 0`**
  (`measure --baseline`, корпус `bfb4d02437f3c528`) — правка аддитивна, а
  `blind agreement` остался `4/14`, потому что v1 языка не проверяет (`K12`).
  **v2: 2 сцены из 11, поимённо** — `live_5/scene_003` победитель `C5` → `C7`;
  `local_after_fix/scene_002` воздержание → `C2` (`partial_support`,
  `slot_verdict incomplete`, `semantic_match_status matched`).
- **чего эти числа не доказывают.** Что новые победители лучше прежних. На v2
  нет слепой разметки владельца, agreement по нему не считается, и последним
  измеренным числом продукта остаётся `4/14` на v1. Пока PLAN-9D-H не размечен,
  ни один агент не вправе называть эту правку улучшением отбора.
- **побочная находка и решение владельца 2026-08-17 — строка `C95`.** Правка
  сдвинула одно производное поле замороженного корпуса v1: `scene_010` потеряла
  категорию `ambiguous_needs_review`, и `finalize` стал давать другой
  `corpus_sha256`. Пересчитать корпус нельзя — слепая разметка владельца
  записывает хеш, против которого делалась, и harness отказывается мерить при
  несовпадении, то есть пересчёт осиротил бы единственную размеченную истину.
  Владелец выбрал: дрейф назвать, корпус и разметку не трогать. Пин
  `KNOWN_DERIVED_DRIFT` требует, чтобы дрейф был ровно этим — шире и уже
  одинаково краснеют. Настоящее исправление (вынести код-производные поля из
  хеша) принадлежит прибору, пакет **C**, и встанет там сразу после разметки v2.
- **метод замера v2.** Состояние «до» воспроизведено подстановкой прежнего тела
  примитива, а не checkout'ом старого коммита: `git worktree` этого репозитория
  на Windows не создаётся (длина путей в
  `docs/implementation/openai_live_evaluation/`). Подстановка точна для обеих
  точек вызова и самопроверяется — скрипт сначала заново выводит три числа,
  замороженные `3aff877` на неисправленном HEAD, и отказывается печатать
  результат, если не воспроизвёл их.
- **независимое ревью выполнено — `2b636ab`, отчёт
  [REVIEW_PACKAGE_D_2026-08-17.md](../audits/REVIEW_PACKAGE_D_2026-08-17.md).**
  Scope PASS · objective PASS, два MINOR, ни одного BLOCKER/MAJOR. Оба числа
  приёмки рецензент получил собственным прогоном, а не принял из тела коммита.
  MINOR закрыты этой же сессией и тестами, а не отдельным слайсом: недостижимая
  ветка `if not self.fields` покрыта прямым тестом и оставлена (её удаление
  сделало бы запись без полей неразрешимой для любого термина), шестая точка
  вызова — дисквалифицирующий `must_avoid_match` в `candidate_ranker.py:233`,
  который доказуемость не спрашивает ни до правки, ни после, — заведена строкой
  `C97`, а формулировка `C91` про «весь слой запретов» сужена. Полный офлайн на
  границе пакета после пина: 2377 тестов, 980 с, два падения, оба `C96`.
- **required verification:** targeted tests + независимое ревью + gates.

### PLAN-9D — offline visual-quality evidence

- **status:** in progress · **commit:** `04fe035` (benchmark harness и
  historical corpus; шаг **не** закрыт). Оба blocking prerequisite сняты:
  **PLAN-9B** закрыт через свои под-слайсы PLAN-9B-2 (`66fd2431`/`8c60295`) и
  PLAN-9B-3 (`72221e1`), **PLAN-9C** закрыт 2026-08-08 (commits
  `8932957`/`668ff10`/`8c1186f`; независимый review — ACCEPT, blocking
  findings 0). PLAN-9D-A closed 2026-08-08 (`2bae6f6`), PLAN-9D-B closed
  2026-08-08 (`69af3ca`) — current corpus снят и заморожен, capture-integrity
  verdict этого docs closure: **VALID_CAPTURE**. Шаг разбит на под-слайсы
  PLAN-9D-A…PLAN-9D-G по Execution protocol п.5; каждый требует собственного
  owner-issued implementation slice; **PLAN-9D в целом остаётся in progress**
  и ничего не утверждает о качестве retrieval.
- **цель:** доказать улучшение decision path на candidate pools, которые
  представляют **фактическое retrieval-поведение текущего HEAD**.

**Owner direction 2026-08-08 (plan reconciliation).** Прежняя цель «доказать
улучшение на уже имеющихся данных» переформулирована владельцем после
read-only architecture / data-hygiene / stock-pipeline аудита. Состав шага и
его место в route не менялись; изменилось происхождение корпуса, на котором
измеряется decision quality. Historical projects сохраняют ценность как
historical failure / compatibility evidence, но перестают быть основным
current-quality benchmark. Production logic этой записью не меняется.

- **[FACT] аудит от clean HEAD `04fe035`, почему прежняя формулировка не
  работает.** Ни один runtime project на диске не создан текущим query stack:
  самый новый файл в `projects/` — 2026-07-28, тогда как PLAN-9B-1 (`141beae`)
  датирован 2026-08-01, а PLAN-9B-2/9B-3/9C — 2026-08-07/08; файлов новее
  2026-08-01 в `projects/` ноль. Замороженный `tests/data/plan9d/corpus_v1.json`
  целиком собран из этих проектов: 6 из 16 сцен (30 из 75 наблюдений) получены
  ретайренным subject-free литералом `nature science wildlife observation` из
  `_LEGACY_BROAD_QUERIES` (registry C36), 2 — ретайренным orca topic hardcode
  (C35), ещё 4 — вырожденными pools `orca` / `close` / `scientists` /
  `ocean aerial`, одна — русским запросом `пластик воздуху оставили`
  (CRITICAL-1 до PLAN-9B-1). Сцены «геккон», «колибри» и «пингвины» объявляют
  пустой `subject` и делят **один и тот же** набор из пяти кандидатов, ни один
  из которых не изображает заявленный субъект. На таком корпусе измеряется не
  качество решения, а выбор наименее неподходящего кандидата.
- **источники (изменено owner direction 2026-08-08).** Прежний закрытый
  offline-список расширяется явно, а не молчаливо: свежий candidate corpus,
  снятый одним bounded прогоном **текущего production retrieval**; уже
  сохранённые кадры; сохранённые результаты предыдущего Vision-прогона;
  вручную размеченные fixtures; существующий live-eval dataset. Прежняя
  редакция такой capture не допускала, поэтому она зафиксирована здесь как
  поправка формулировки, а не как обход контракта.
- **PLAN-9D остаётся offline benchmark.** Итоговое evaluation выполняется
  offline. Bounded provider capture допустим **только** для подготовки current
  candidate corpus; после capture корпус замораживается своим `corpus_sha256`,
  и дальнейшее измерение от сети не зависит. Превращение PLAN-9D в live
  mutable benchmark запрещено.
- **запрещено:** новые платные вызовы; paid Vision / model / TTS / render
  внутри capture; изменение retrieval-поведения (pagination, deep search,
  состав провайдеров, ranking tuning) — это contracts PLAN-10A, PLAN-10B,
  PLAN-10C и PLAN-10D; mock, scripted и любой fixture backend как
  доказательство визуального качества; заполнение owner annotation от имени
  владельца.
- **current retrieval capture ≠ PLAN-10B implementation.** Capture запускает
  существующий production-путь как есть и ничего в нём не настраивает.
  PLAN-10A, PLAN-10B, PLAN-10C, PLAN-10D и PLAN-9E не подтягиваются в PLAN-9D
  и остаются в прежнем порядке route. Результаты retrieval gate PLAN-9D-C
  могут стать основанием для будущего owner decision о порядке работ, но
  **не раньше** получения current baseline evidence.
- **cleanup sequencing.** Historical runtime data не остаётся неявным current
  evaluation source, но массовое удаление здесь не выполняется. Порядок:
  (1) curate compact historical failure evidence; (2) capture fresh current
  corpus; (3) freeze current corpus и ground truth; (4) только после снятия
  evidence dependency разрешается historical runtime cleanup цепочкой
  PLAN-14 → registry N02/C32/D04/C20; (5) legacy production code ретайрится
  только через PLAN-L и существующие retirement gates. Единая свалка
  `old_everything/` внутри active repo не создаётся: historical heavy runtime
  либо удаляется, либо архивируется **вне** active runtime paths, либо
  превращается в compact versioned fixture.
- **[FACT] evidence dependency, которую обязан снять шаг (4) (обновлено
  PLAN-9D-A, `2bae6f6`).** Текущее curated `historical_failure_evidence_v1.json`
  адресует ровно те runtime-пути, что возвращает implementation-owned
  `historical_runtime_paths()` — детальный список даёт сам этот отчёт/функция,
  не перечисление здесь. Раздел «Safety boundaries» относит `*.jpeg` и кэши
  под `projects/` к disposable и не перечисляет эти пути в
  `Preserved runtime corpus`. До закрытия PLAN-9D они защищены оговоркой в
  «Safety boundaries», см. там же; сокращение состава этих путей PLAN-9D-A
  разрешением на их cleanup сейчас не является.
- **измеримый результат:** улучшение решения зафиксировано на корпусе,
  представляющем current retrieval; mock как доказательство не используется.
- **required verification:** targeted evaluation tests + offline product
  fixture gate; повторный `full` не нужен без изменения shared contract.
- **rollback:** один commit на под-slice.

#### PLAN-9D-A — historical evidence curation

- **status:** completed · **completed:** 2026-08-08 · **commit:**
  `2bae6f6d23d8cbf874fcf71883334a7ea4d8619d` (trailer `Plan-Step: PLAN-9D`).
  Закрывает только PLAN-9D-A; **PLAN-9D в целом остаётся in progress** и
  ничего не утверждает о decision quality.
- **фактический результат.** `corpus_v1.json` (9777 строк, 16 сцен,
  benchmark-shaped данные, собранные из `projects/`) и пустой шаблон
  `annotations_v1.json` удалены, а не переименованы — точное содержимое
  остаётся доступным на `04fe035e6ac07dbbe4a80257c3ed9d971976457e`, якорь
  записан в самом fixture. На их месте —
  `tests/data/plan9d/historical_failure_evidence_v1.json`: 7 cases, 31
  candidate, по одному representative frame на кандидата, явно historical
  failure / compatibility evidence, никогда не current-quality benchmark —
  gecko/hummingbird/penguin (нет visual brief, retired subject-free литерал,
  registry C36), CRITICAL-1 (русский запрос напрямую в latin stock индекс),
  usable primary query с последующим единословным `close` от каждого
  provider, и retired one-topic orca hardcode (registry C35). 9 из 16
  исходных сцен исключены, каждая с причиной в `dropped_source_scenes`.
  Historical и current разделены contract'ом, а не именованием:
  `generation_class`/`fixture_kind` плюс единственный gate
  `assert_current_benchmark_input`; неразмеченный payload читается как
  historical по умолчанию, восстановление старого corpus из Git gate не
  открывает.
- **runtime dependency (независимо перепроверено этим docs closure).**
  `historical_runtime_paths()` над текущим fixture возвращает ровно 45 путей —
  14 манифестов и 31 кадр, 33.47 MB, 7 projects; все 45 присутствуют на диске.
  До этого fixture адресовал 107 frame-путей по всему untracked дереву
  `projects/`. Ничего под `projects/` не удалено этим слайсом; сокращение
  зависимости — не разрешение на cleanup, см. «Safety boundaries» выше.
- **required verification (независимо перепроверено этим docs closure):**
  targeted `tests.test_plan9d_historical_evidence` +
  `tests.test_plan9d_ground_truth_baseline` — 80 OK. Full offline suite
  1875 OK, `check_agent_docs` exit 0, `check_task_scope` OK, `git diff --check`
  clean — implementation-commit claim, owner-provided; полный прогон в этом
  docs-only closure не требуется (Execution protocol, п.10) и не выполнялся.
- **запрещено:** удалять или перезаписывать оставшиеся 45 evidence-путей до
  снятия PLAN-9D dependency (шаг (4) cleanup sequencing); выдавать historical
  evidence за current-quality benchmark.

#### PLAN-9D-B — current-HEAD retrieval capture

- **status:** completed · **completed:** 2026-08-08 · **commit:**
  `69af3ca7387fa9fe649fabf0fd464ec519f76400` (trailer `Plan-Step: PLAN-9D`).
  Закрывает только PLAN-9D-B; **PLAN-9D в целом остаётся in progress** и
  ничего не утверждает о том, хороший retrieval или плохой.
- **фактический результат.** Один bounded прогон текущего production
  retrieval-пути (через `AssetManifestBuilder`, без единой написанной вручную
  строки запроса и без изменения `src`/`config`/`schemas`) заморожен в
  `tests/data/plan9d/current_corpus_v1.json` — 14 сцен, 1064 наблюдения, 1052
  уникальных ассета, 64 кадра, original capture-time `corpus_sha256`
  `da8e50a968afc72fcc427ffeb9b0e58fe264119f9d191d17849ce2265fa89b35` (значение
  прочитано из самого файла и независимо перепроверено этим docs closure, а не
  взято из implementation report). PLAN-9C-3 позднее re-finalized только
  recomputable derived categories/counters под новым evidence contract; текущий
  checksum файла —
  `bfb4d02437f3c52879c98367558de339ffb8e352d6dd4ef743e14c4185ccf1b4`, raw
  retrieval pools/queries/frames не менялись. `capture_head_sha` =
  `d01914d77822057569a491216cfecf21b08f5d0c` — этим closure подтверждено, что
  это production HEAD, чьё поведение снято, а не отдельная ревизия harness:
  `git diff --stat d01914d 69af3ca -- src/ config/ schemas/` пуст.
- **two-run provenance (независимо перепроверено этим docs closure, не принято
  на веру из implementation report).** Первый прогон дошёл до конца всех 14
  сцен и был остановлен собственным freeze-time secret scan — ложное
  срабатывание на слове "authorization" в описании провайдера и в approval
  note; ни один corpus не был записан, ни один candidate не был отобран из
  этого прогона, и ни одного артефакта первой попытки нет ни в untracked
  capture workspace, ни в Git. Второй прогон — единственный, который что-либо
  сохранил: raw capture (`projects/plan9d_current_capture_v1/capture_raw.json`,
  untracked) несёт `capture_timestamp_utc` `2026-08-08T15:57:57+00:00` и
  scene/observation counts (14/1064), идентичные замороженному corpus, то есть
  corpus построен ровно из одного raw capture и кросс-run смешивания метаданных
  структурно нет. Preview-cache integrity проверена программно по всем 56
  previewed candidates: 56 различных `cache_key`, ноль совпадений/переиспользо-
  вания между разными `asset_id`, все 56 preview SHA256 совпадают с
  заявленными, каждый `preview_record.json` присутствует — stale или
  чужой-asset preview структурно невозможен, потому что
  `compute_preview_cache_key` (`src/assets/visual_preview.py`) — детермини-
  рованный SHA256 от полей идентичности кандидата (provider,
  provider_asset_id, asset_id, preview_source_url, media_type, rendition,
  target_aspect_ratio, sample_count, top_k), а не от номера прогона.
- **capture-integrity verdict:** **VALID_CAPTURE**. Retry — документированный
  non-quality recovery после инфраструктурного false positive, а не попытка
  улучшить результат: сам модуль capture прямо запрещает второй прогон "to get
  a better pool" (`tests/plan9d_current_capture.py`), и ни один факт на диске
  этому не противоречит.
- **baseline CI (независимая read-only проверка этим docs closure):**
  GitHub Actions check-run `unittest` на точный SHA
  `69af3ca7387fa9fe649fabf0fd464ec519f76400` — `completed`/`success`.
- **required verification (независимо перепроверено этим docs closure):**
  targeted `tests.test_plan9d_current_capture` + `tests.test_plan9d_ground_truth_baseline` —
  100 OK. Полный offline suite и любые provider/network тесты этим docs-only
  closure не запускались (Execution protocol, п.10).
- **классификация:** DATA CAPTURE / EVALUATION PREPARATION. Это не
  implementation PLAN-10A, PLAN-10B, PLAN-10C или PLAN-10D.
- **No quality claim.** Этим closure не утверждается: free providers
  достаточны; Envato не нужен; retrieval succeeded; candidate selection
  улучшилась. Подтверждено только: subjectful current queries сформированы,
  provider capture состоялся, frozen current corpus существует.
- **запрещено:** менять состав провайдеров, pagination, пороги и ranking;
  повторные capture-прогоны ради лучшего результата; менять уже
  зафиксированный `corpus_sha256`.

#### PLAN-9D-C — retrieval quality gate

- **status:** completed · **completed:** 2026-08-09 · **commit:** см. trailer
  `Plan-Step: PLAN-9D`. Закрывает только PLAN-9D-C; **PLAN-9D в целом остаётся
  in progress**.
- **цель:** до любого Vision evaluation доказать, что простые subject scenes
  действительно получают subject-relevant candidate pools.
- **object scope (уточнено при закрытии PLAN-9D-B, чтобы снять двусмысленность
  прежней формулировки; scope PLAN-9D-C этим не расширяется).** Current corpus
  несёт три разных уровня: (1) **RAW PROVIDER RETRIEVAL** — 1064 candidate
  observations по 14 сценам, только provider metadata, без preview; (2)
  **RANKED / RIGHTS-FILTERED CANDIDATE POOL** — те же 1064 после
  `rank_provider_results`/`apply_policy_to_candidate` (745 licensed, 319
  review_required); (3) **VISUALLY PREVIEWED SHORTLIST** — 56 из 1064,
  production `shortlist_size=5` на сцену, ровно то, что видит decision owner.
  PLAN-9D-C вправе оценивать query integrity и raw retrieval evidence по
  метаданным всех 1064 наблюдений и **визуально** — только 56 previewed
  кандидатов; визуальное заключение об остальных 1008 (без preview) current
  contract не допускает. Selection quality (выбранный кандидат
  `selected_asset_id` относительно своего shortlist, 12 из 14 сцен) — в объёме
  current contract, если PLAN-9D-C её проверяет.
- **обязательный evaluation set:** как минимум `gecko`, `hummingbird`,
  `penguin`, `orca`, плюс несколько сложных сцен с environment, `must_avoid`
  и заявленным контекстом.
- **stop condition:** если current retrieval не даёт разумный candidate pool,
  PLAN-9D-D…PLAN-9D-G не начинаются. Vision comparison не имеет права
  маскировать retrieval failure под улучшение decision quality.
- **владелец gate:** `tests/plan9d_retrieval_gate.py` (offline, только
  замороженный corpus), лок — `tests/test_plan9d_retrieval_gate.py`. Второго
  selector, score или ranking слоя не создано; `src`, `config`, `schemas`,
  `projects/` и сам corpus этим слайсом не менялись.
- **integrity входа (перепроверено этим слайсом, не принято из отчёта
  PLAN-9D-B).** `validate_corpus`, `validate_current_capture` и
  `assert_current_benchmark_input` проходят; пересчитанный `corpus_digest`
  совпадал с capture-time `corpus_sha256`
  `da8e50a968afc72fcc427ffeb9b0e58fe264119f9d191d17849ce2265fa89b35`;
  после PLAN-9C-3 current checksum re-finalized до
  `bfb4d02437f3c52879c98367558de339ffb8e352d6dd4ef743e14c4185ccf1b4` без
  изменения raw pool/queries/frames; все 64
  кадра присутствуют на диске и их SHA256 совпадают с заявленными; 14 сцен,
  1064 наблюдения, 56 previewed candidates, 745 licensed / 319
  review_required.
- **RAW RETRIEVAL verdict: PASS.** Ни в одной из 220 фактически отправленных
  provider-строк нет кириллицы (CRITICAL-1 не повторяется) и нет ни одного
  ретайренного broad-литерала (C35/C36 не повторяются). В каждой из 14 сцен
  хотя бы один отправленный запрос дословно несёт заявленный субъект, и в
  каждом pool есть хотя бы один кандидат, у которого субъект стоит в
  **собственных** provider-метаданных (заголовок/описание/теги; отправленный
  запрос из сопоставляемого текста исключён намеренно — иначе измерение
  подтверждало бы само себя). По phrase-совпадению 396 из 1064, по
  token-совпадению 697 из 1064; две величины приводятся раздельно и не
  смешиваются в один score.
- **дилюция subject-free рунгами (измеренная величина, не оценка).** 35 из 220
  запросов не несут субъекта вообще — это рунги `forest`, `bay`, `Antarctica`,
  `open ocean`, `low Earth orbit`, `savanna`, `laboratory`, `river waterfall
  salmon`, `tundra white winter coat`. Они вернули 301 результат. Ни один
  кандидат, впервые пришедший таким рунгом, **не** дошёл до previewed
  shortlist: ранжирование их отсекает. То есть это стоимость запросов, а не
  загрязнение решения.
- **PREVIEW SHORTLIST verdict: PASS с одним структурным дефектом.** Все 56
  previewed кандидатов — `licensed`/`allowed_for_render`, и все 56 несут
  субъект в собственных метаданных. Визуально (агентский просмотр всех 56, см.
  ниже) субъект сцены присутствует у подавляющего большинства. **Дефект:**
  `_prepare_visual_review` превьюирует `state.candidates[:5]`, а этот список
  ещё содержит повторные наблюдения одного и того же asset, поэтому повтор
  внутри окна съедает слот превью. Итог — 14 из 70 слотов (9 сцен из 14)
  остались без превью; в scene_004 (orca) и scene_007 (pangolin) видно только
  **2** кандидата, в scene_014 — 3.
- **SELECTED-CANDIDATE verdict: WEAK — это самое слабое звено, и оно не
  retrieval.** Выбор есть в 12 сценах из 14; в 2 (`cheetah_not_leopard`,
  `arctic_fox_winter_coat`) владелец решения корректно вернул «нет приемлемого
  кандидата» вместо натягивания. В 7 из 12 выбранный кандидат — ровно первое
  непроваленное **видео** в ранжированном списке: `select_best_with_video`
  (`src/news/asset_manifest_builder.py:1239`) подменяет выбор
  `select_best_candidate` первым видео на **любом** ранге. Следствия: в 3
  сценах (`gecko` ранг 14, `solar_farm` ранг 6, `laboratory_pipetting` ранг 5)
  выбранный кандидат вообще не превьюировался, и визуально о нём сказать
  нечего; в scene_002 выбран сидящий на ветке колибри при двух зависших в
  полёте на рангах 0–1; в scene_007 выбран титр-кадр `LIFE ON EARTH` при
  реальном панголине на ранге 1; в scene_013 выбран conspiracy-ролик
  `Nuke Van Allen Belt Nazi Freemasons Man On Moon` (визуально — человек с
  микрофоном на сцене) при реальном Saturn V на стартовом столе на ранге 2.
- **агентский визуальный просмотр 56 кадров (evidence, не ground truth и не
  замена PLAN-9D-D).** Хорошо: `tiger_wild_not_captive` — выбран тигр, идущий
  по лесу, точное попадание subject+action+environment;
  `brown_bear_catching_salmon` — выбран медведь с лососем в пасти на пороге,
  точное попадание вместе с `must_include: salmon`; `iss_orbit` — выбраны
  реальные кадры МКС над Землёй, а не рендер. Плохо: `suspension_bridge` —
  выбран Howrah Bridge, это **консольно-ферменный**, а не висячий мост, при
  настоящем висячем мосте на ранге 1 (misleading visual risk); scene_013 и
  scene_007 см. выше. Отдельно: у выбранных кандидатов scene_004 и scene_014
  в кадре видимый водяной знак фотографа, а в shortlist scene_011 присутствуют
  два кандидата с явной подписью «Artist Rendering» и с графическими
  подписями — то есть заявленный `conflicting_context` отсеял их на выборе,
  но не на shortlist. Ни одного нарушения `must_avoid` в выбранных кандидатах
  нет (проверено и по метаданным, и глазами).
- **честная граница.** Визуальные утверждения относятся только к 56
  previewed кандидатам. Об оставшихся 1008 визуально не утверждается ничего.
  В частности не утверждается, что в pool не было лучшего кадра: для
  `cheetah` в пуле 32 кандидата с субъектом в метаданных, для `arctic fox` —
  14, и был ли среди них бегущий гепард или белый зимний окрас, замороженные
  данные ответить не могут.
- **stop condition НЕ сработал.** Current retrieval даёт разумный candidate
  pool, поэтому PLAN-9D-D…PLAN-9D-G не блокируются этим шагом. Найденные
  дефекты относятся к shortlist и selection, а не к retrieval, и **не
  исправляются здесь**: PLAN-10B (pagination), PLAN-10C (shortlist/бюджет,
  включая уже записанный follow-up F2), Vision activation и любой пересмотр
  `select_best_with_video` остаются за своими шагами и вперёд не выносятся.
- **два owner decision перед PLAN-9D-D (не выполнены этим слайсом).** (1)
  Аннотатор увидит 2–5 кандидатов вместо 5; принимать ли разметку на неполном
  shortlist. (2) В 3 сценах выбранный системой кандидат не входит в
  просмотренный набор, поэтому сравнение решения с разметкой в PLAN-9D-E для
  них не определено. Оба вопроса — про порядок и валидность измерения, а не
  про качество retrieval.
- **required verification:** targeted retrieval-gate tests на замороженном
  current corpus; сеть не требуется. Фактически выполнено:
  `tests.test_plan9d_retrieval_gate` + `tests.test_plan9d_current_capture` +
  `tests.test_plan9d_ground_truth_baseline` + `tests.test_plan9d_historical_evidence`
  — 167 OK. Ни одного provider-, download-, Vision-, TTS-, render- или иного
  платного вызова; gate прогоняется в том числе под repository socket guard.
- **product test-video checkpoint после закрытия PLAN-9D-C (owner direction
  2026-08-08).** После закрытия шага владелец собирает один **diagnostic
  vertical Short** и смотрит его глазами, чтобы проверить, стал ли current
  retrieval/selection действительно лучше. Это **diagnostic baseline, а не
  production acceptance**: `publish_ready`, quality gate и product evidence им
  не объявляются. Действие лежит **вне scope PLAN-9D-C**, выполняется
  отдельным owner-issued слайсом и требует собственных разрешений на сеть,
  платные вызовы и render; scope, статус и offline-контракт PLAN-9D-C этой
  записью не меняются.

#### PLAN-9D-D — human ground truth

- **status:** completed 2026-08-12 · **commit:** — (заполняется plan-only
  уточнением, Execution protocol п.3).
  **Owner decision 2026-08-12:** владелец снял оба входных вопроса, приняв
  разметку на неполном shortlist, выполнил слепой проход сам и разрешил
  привести файл к каноническому имени. Прежний блокер LIVE-5 снят этим же
  решением: диагностический Short остаётся отдельным owner-issued действием и
  ground truth больше не ждёт.
  **История блокировки (не переписывается).** Прежний блокер
  **PLAN-9B-PRODUCER-M-LIVE**
  закрыт 2026-08-09, поэтому запись устарела. Фактический блокер теперь —
  owner-issued **LIVE-5** acceptance diagnostic, а до него — bounded
  corrections VA-NEW-02, 04, 05, 06, 08, 09 и минимальные budget guards 10/12
  (`docs/audits/VISUAL_ASSET_INTEGRITY_AUDIT_2026-08-10.md` `40, ответы 12 и
  14: ядро к PLAN-9D-D не готово, пока current offline evidence может быть
  загрязнено continuity/preview/override gaps). Диагностический Short по
  этому слайсу так и **не запускался**; владелец принял это как остаточный
  риск измерения, а не как основание держать ground truth незакрытым.
- **цель:** blind owner annotation ровно один раз, затем freeze и hash.
- **фактический результат.** Слепой проход выполнен владельцем
  (`annotator: Test2`, `annotated_at_utc: 2026-08-12T08:05:31Z`) по всем 14
  сценам: 14 `preferred_candidate`, 4 сцены с `unacceptable_candidates`
  (7 отметок), 5 сцен с текстовой заметкой. Разметка привязана к
  `corpus_sha256 = bfb4d024…ccf1b4` — тому же, что несёт замороженный корпус.
  Per-candidate flags владелец не заполнял; контракт этого и не требует
  (`validate_annotations` проверяет словарь значений, а не полноту), поэтому
  измеряются оси preference/unacceptable/abstention, а не per-field coverage.
- **дефект имени, из-за которого разметка чуть не пропала.** Пакет разметки
  сохранял файл как `annotations_v1.json`, а harness читает
  `CURRENT_ANNOTATIONS_PATH` — `current_annotations_v1.json`. Законченный
  слепой проход лежал на диске, пока `annotation_status()` продолжал отвечать
  `WAITING_FOR_OWNER_ANNOTATION`, и ни один шаг после PLAN-9D-D не мог
  стартовать. Файл переведён под каноническое имя **побайтово**
  (`os.replace`, sha256 `7f8afddb…24928e` до и после, 20497 байт, одна копия —
  вторая постоянная копия owner ground truth не создавалась), содержимое не
  трогалось. Имя в пакете больше не пишется вторым написанием: оно берётся из
  `CURRENT_ANNOTATIONS_PATH.name`, и characterization test
  `test_the_pack_saves_under_the_name_the_harness_reads` падал до фикса.
- **фактическая поправка Phase 0.** Docstring `render_pack` утверждал
  «previewed 54 images and 2 videos». Корпус говорит другое, и корпус верен:
  56 карточек кандидатов = 43 image + 13 video, 64 кадра = 43 image + 21
  video. Единицы разные, и прежняя фраза их смешивала. Ограничение, ради
  которого фраза писалась, от поправки только усилилось: 11 из 13 video-карт
  несут **один** сэмплированный кадр и лишь 2 несут пять, поэтому метка на
  video-карточке — суждение об одном кадре, а не о движении. Числа залочены
  тестом `test_preview_coverage_is_counted_in_the_units_it_is_quoted_in`.
- **вход от PLAN-9D-C.** Просматриваемых кандидатов 56 на 14 сцен, но не по 5
  на сцену: в 9 сценах часть слотов превью съедена повторными наблюдениями
  (минимум 2 кандидата — scene_004 и scene_007). В 3 сценах выбранный
  системой кандидат вообще не превьюирован. Оба факта требуют owner decision
  **до** разметки, потому что они меняют не качество данных, а то, что именно
  измеряет PLAN-9D-E.
- **граница:** аннотация выполняется владельцем; агент её не заполняет и не
  восстанавливает. Пока `current_annotations_v1.json` в состоянии
  `WAITING_FOR_OWNER_ANNOTATION`, harness возвращает тот же статус и ничего не
  измеряет. Пересборка корпуса после разметки запрещена: изменится
  `corpus_sha256`. Содержимое разметки после заморозки не редактируется — этим
  слайсом изменено только имя файла.
- **что эта ground truth НЕ доказывает** (граница не расширена закрытием
  шага): она говорит о лучшем визуально проверяемом кандидате внутри
  captured preview shortlist, а не о лучшем ассете пула; не измеряет retrieval
  до shortlist; и, поскольку 11 из 13 video-карт — один кадр, не измеряет
  video selection, video-first и composite assembly.
- **required verification:** targeted annotation-contract tests. Фактически
  выполнено: `tests.test_plan9d_ground_truth_baseline` — 49 OK (было 46: три
  новых лока и один переписанный — `CurrentBenchmarkSlotTests` больше не
  утверждает, что разметки нет, а утверждает, что она есть и привязана к
  этому корпусу). Сеть, платные вызовы, Vision, render не использовались.

#### PLAN-9D-E — offline metadata-only baseline

- **status:** completed 2026-08-12 · **commit:** — (заполняется plan-only
  уточнением, Execution protocol п.3).
- **цель:** измерить current metadata-only решение против замороженного
  human ground truth.
- **граница:** через существующий decision owner
  (`select_best_with_video` → `select_best_candidate`, `vision_tags` пуст).
  Второй selector, собственный score и выдуманный confidence запрещены.
  Соблюдено: второго selector нет, своего score нет, confidence не выдуман,
  новый формат отчёта не заводился — измерение выполняет существующий
  `run_metadata_baseline` → `evaluate_arm`.
- **измеренный результат** (14 сцен, все 14 scorable):

  | ось | значение |
  |---|---|
  | совпадение с owner preference | **4 / 14** (`scene_003`, `scene_009`, `scene_012`, `scene_014`) |
  | выбран кандидат, вычеркнутый владельцем | **2** (`scene_007`, `scene_013`) |
  | abstention при наличии приемлемого у владельца | **3** (`scene_004`, `scene_005`, `scene_008`) |
  | correct abstention | 0 |
  | `auto_safe` (`full_support`) | **1 / 14** (`scene_011`) |
  | safe escalation to review | 10 |
  | `unscorable_winner_not_visible` | **0** |

- **что именно измерено, а что нет.** Arm прогоняет **сегодняшний**
  decision owner по пулу, снятому на `d01914d7`, поэтому число описывает
  текущий HEAD, а не решение, записанное в корпусе. Расхождение намеренное и
  измеримое: `388b9b1` (PLAN-9C-2, после capture) убрал безусловную video-first
  подмену, и сравнение с записанным в корпусе выбором даёт
  `matches 2 → 4`, `winner never previewed 3 → 0`, `abstained 2 → 3`,
  `picked owner-rejected 2 → 2`. То есть дефект «выбранный кандидат вообще не
  превьюирован», найденный PLAN-9D-C, закрыт, согласие с владельцем удвоилось,
  а обе сцены, где система выбирает вычеркнутое владельцем, изменение пережили.
- **нули на flag-осях — это незаполненность, а не проверка.**
  `must_avoid_escaped` и `non_real_footage_selected` считаются по
  per-candidate flags, а владелец заполнил только preference и unacceptable.
  Обе величины структурно нулевые для этой ground truth, и PLAN-9D-G не имеет
  права читать их как «baseline не нарушил ни одного гейта». Залочено
  тестом вместе с проверкой, что ни один flag действительно не заполнен.
- **чего этот baseline не доказывает.** Он не говорит о retrieval до
  shortlist, не говорит о video selection (11 из 13 video-карточек — один
  кадр) и не является product acceptance. Отдельного persisted-отчёта шаг не
  требует и не создаёт: результат зафиксирован тестами, как и написано в
  required verification.
- **required verification:** targeted evaluation tests. Фактически выполнено:
  `tests.test_plan9d_ground_truth_baseline.FrozenBaselineMeasurementTests` —
  5 OK; модуль целиком 54 OK; PLAN-9D radius 178 OK. Сеть, платные вызовы,
  Vision, TTS, render не использовались.

#### PLAN-9D-F — real Vision evidence capture

- **status:** blocked (PLAN-9D-E + отдельный explicit owner approval) ·
  **commit:** —
- **цель:** сохранить real Vision evidence по замороженному current corpus.
- **граница:** любой новый model / Vision paid capture остаётся **отдельным
  explicit owner-approved action**; автоматических платных вызовов нет.
  Применяется implementation-time verification моделей из PLAN-9E: configured
  model IDs сверяются с фактическим provider/backend contract, unknown или
  unsupported model — fail closed. Результат сохраняется как evidence, после
  чего evaluation снова не зависит от сети.
- **required verification:** targeted evidence-contract tests.

#### PLAN-9D-G — offline A/B

- **status:** blocked (PLAN-9D-F) · **commit:** —
- **цель:** offline сравнение `metadata-only` против
  `metadata + saved real Vision evidence` через **один** существующий
  candidate decision owner.
- **запрещено:** mock, scripted и fixture backend как arm сравнения;
  повторный live-прогон вместо сохранённого evidence.
- **измеримый результат:** улучшение или его отсутствие зафиксировано на
  current corpus и объяснимо; нарушение rights, `must_avoid`, заявленного
  конфликта, misleading-content gate или технического hard reject считается
  blocking regression.
- **required verification:** targeted evaluation tests + offline product
  fixture gate.

#### PLAN-9D-H — двуязычный ground truth (корпус v2)

- **status:** in progress · **commit:** сборка корпуса и доска — коммит,
  содержащий эту запись · **зависимость:** нет блокирующей; решения владельца
  получены 2026-08-17 (состав корпуса, размер шортлиста). Пакет **C** маршрута
  [ROLLOUT_PLAN_2026-08-17.md](../audits/ROLLOUT_PLAN_2026-08-17.md).
- **сделано 2026-08-17 (evidence:
  [PLAN_9D_H_CORPUS_V2_2026-08-17.md](../audits/PLAN_9D_H_CORPUS_V2_2026-08-17.md)).**
  Корпус `tests/data/plan9d/current_corpus_v2.json` заморожен: 11 сцен,
  **78 карточек** (73 уникальных из десяти снятых сцен + 5 инцидентной), картинки
  у 55, кириллических записей кандидатов 30 против 2 в v1 — `K12` закрыт. Класс
  корпуса добавлен полем схемы `plan9d-corpus-1` и переопределяется у сцены;
  корпус без поля читается как «слепая разметка», поэтому v1 валидируется байт в
  байт и даёт прежние **4/14** с теми же 14 победителями. Названный случай в
  корпусе поимённо (`pexels_32386564`, `live_5/scene_003`, `local_library`,
  `semantic 0.0`, `final 7.5` против 72.968). Случай с запретом собран
  синтетически одной инцидентной сценой с русским требованием на настоящих
  кандидатах: на слове «градирня» одна запись поймана буквально и уходит
  последней, её близнец не поймана и идёт первой. `measure --baseline` печатает
  изменившихся победителей поимённо. `K9` исправлен: отброшенный по языку запрос
  пишется в план как `query_language_unsupported`, остаётся неотправляемым и
  бюджет не тратит. Доска — существующий `render_pack` плюс каталог слепых медиа;
  второй доски не создано.
- **три правки прибора, тот же день (§12 отчёта).** Оба внешних ревью дали
  «готово» и ни одно не нашло ни одного из трёх дефектов, а одно сослалось на
  прогон тестов, которого не было (заявлено 16 тестов и 1.5 с; та же команда даёт
  82 теста и 135 с, один класс baseline — 127 с). Исправлено: (1) сцена больше не
  называет себя на странице — `scene_key` стоял в `data-key` и в имени каждой
  картинки, а он несёт имя прогона и слаг инцидентного случая; теперь непрозрачный
  токен `S<10 hex>`, обратное отображение делает harness; (2) инцидентная сцена
  больше не входит в знаменатель отношения, которое цитируют как поведение в поле —
  `measure` печатает `blind agreement`, `incident scenes` и `all scenes together`
  раздельно, плюс `cards not shown to anyone`; (3) **на доске не открывалась ни
  одна картинка** — нашёл владелец при первом её открытии: в `src` стояло голое имя
  файла, а медиа лежат в подкаталоге рядом со страницей, поэтому браузер не находил
  ни одной из 117. Пропущено это было потому, что моя же проверка «117 refs, missing
  0» сама подставляла `media/` перед проверкой существования файла — то есть
  проверяла каталог, а не страницу, и содержала в себе проверяемое предположение.
  Теперь `media_urls_relative_to` считает путь от страницы, тест открывает каждую
  ссылку относительно html, доска подтверждена скриншотом headless-браузера. Доска
  пересобрана трижды; годна только последняя. На v1 оба чтения числа совпадают,
  число прежнее 4/14.
- **что учитывать в следующих шагах (записано здесь, чтобы не потерялось).**
  1. Число, которое можно цитировать как качество отбора, — только `blind
     agreement`; `all scenes together` включает сцены с требованием, написанным
     рукой.
  2. `cards not shown to anyone` обязано стоять рядом с любым отношением: 1008 из
     1064 в v1 и 23 из 78 в v2 никому не показывали, и это «не спрашивали», а не
     «владелец отказал».
  3. Полнота поиска (recall) не измеряется ни одним прибором и офлайн измерена
     быть не может — нужен отдельный платный прогон и отдельное решение владельца;
     до тех пор ни одно число v2 не является оценкой полноты.
  4. Чужой вердикт (в том числе агента-ревьюера) принимается по числам, которые
     воспроизводятся командой; число тестов и время прогона — такие же числа.
     Второе правило того же происхождения: проверка не должна содержать
     предположение, которое проверяет — артефакт, который открывает человек,
     проверяется так, как его открывает человек.
  5. Порядок пакета D подтверждается или пересматривается **после** разметки, по
     крупнейшему измеренному классу ошибок, а не по номеру PLAN-ID.
- **сделано 2026-08-18: разметка владельца легла, корпус измерен.**
  `tests/data/plan9d/current_annotations_v2.json` — 11 сцен, annotator
  `PLAN_9D_TEST`, 25 карточек помечены неприемлемыми, две сцены владелец назвал
  `undecidable`. Привязка — `annotation_identity_sha256` (`C95`), поэтому
  пересчёт производных полей корпуса разметку больше не осиротляет. Числа
  metadata-only арма на v2, зафиксированные тестом
  `FrozenBilingualMeasurementTests`: **blind agreement 2 / 10 scorable**
  (10 снятых сцен), инцидентная сцена — 1, agreement 0, печатается отдельно;
  `all scenes together` 2 / 11; **cards not shown to anyone 23 из 78**.
  Разбор десяти слепых сцен: match 2, miss 4, выбрана карточка, которую
  владелец назвал неприемлемой — 2 (плюс третья на сцене, где владелец
  воздержался: `live_5/scene_002` C5, `local_after_fix/scene_003` C4,
  `live_5/scene_004` C9), воздержание против названного предпочтения — 1,
  `undecidable` — 1. `must_avoid_escaped` 0, `non_real_footage_selected` 0,
  `safe_escalations_to_review` 9, `auto_safe` 0. Про `C91` разметка говорит
  ровно одно: из двух сцен, где правка сменила победителя, владелец согласен с
  новым победителем в `live_5/scene_003` (`C7`) и не согласен в
  `local_after_fix/scene_002` (система `C2`, владелец `C5`) — то есть правка
  купила одно совпадение и оставила вторую сцену неверной по-другому. Это
  меньше, чем «стало лучше вообще», и больше, чем «сдвинулось».
- **сделано 2026-08-18: слайс C98 — запрос больше не теряет предмет темы.**
  Один слайс на существующих владельцах, класс риска HIGH (отбор). Сначала
  characterization: `tests/test_query_topic_anchor.py` переигрывает запросы обоих
  замороженных прогонов через самого владельца (`build_scene_queries`), сходится
  с сохранённым `query_plan` запись в запись и воспроизводит измеренное число —
  **15 из 42** уникальных запросов без предмета. Затем правка:
  `src/assets/query_adapter.py` получил `TopicAnchor` и
  `plan_topic_anchor(visual_plan)`. Английская форма якоря берётся либо из
  `topic_entity`, когда он английский, либо из английских `subject` /
  `exact_entities` сцен **того же плана**, повторяющихся минимум в двух сценах;
  для обоих прогонов из русского «панель» вышел `solar panel` — английское
  свидетельство плана, а не перевод. Каждый английский запрос, не называющий
  якорь, получает его в начало, а исходная строка пишется в `notes`. `K9` не
  ослаблен: русский `topic_entity` не переводится, русский запрос локальной
  библиотеки якорем не склеивается. Когда тема названа, но английской формы в
  плане нет, запрос не уходит молча — сцена получает нерассылаемую запись
  `query_subject_unverified`. Якорь считается один раз на план
  (`AssetManifestBuilder.topic_anchor`) и идёт и в `build_scene_queries`, и в
  `build_slot_queries`. **Приёмка:** та же перепись на тех же сценах — **15 из 42
  → 0**; число «до» осталось воспроизводимым (тот же прогон без якоря по-прежнему
  даёт 15). Уникальных запросов 42 → 41: один якорённый совпал с уже имевшимся,
  новых запросов якорь не добавляет; 27 запросов, уже называвших тему, не
  изменились. Существующий потолок `_MAX_QUERY_TERMS` (8 слов) якорь не поднимал,
  поэтому один самый длинный запрос из пятнадцати ужался с хвоста
  (`…industrial power storage facility` → `…industrial power`): предмет темы
  дороже двух последних слов контекста. **Guard зелёный:** `blind agreement` 2 / 10 на v2 и 4 / 14 на v1 —
  до и после, потому что прибор переигрывает отбор по замороженному пулу и
  запросов не переотправляет. **Не заявляется:** улучшение отбора — по разбору
  правка двигает 2–3 сцены из восьми, в шести нужный кандидат и так лежал в пуле
  и проигрывал ранжированию (`C99`). Продуктовый эффект на пуле покажет только
  новый живой прогон — платное действие и отдельное решение владельца; в этом
  слайсе не делалось. **Не покрыто:** локальная библиотека приходит в пул вообще
  без запроса, «подтверждённый эквивалент» пункта 1 ADR 0022 не реализован
  (совпадение считается по общей основе слова — ровно как считает перепись), путь
  `build_slot_queries` заякорен, но переписью не измерен и проверен модульно.
  **Ratchet:** `src.assets.query_adapter` снят из mypy baseline в `pyproject.toml`
  — все 16 подавленных ошибок модуля были одним идиомом чтения вложенного словаря,
  вынесенным в `_sub_dict`. **Найдено попутно и не чинилось:** строка `C100` —
  `test_plan9d_retrieval_gate` красный и на чистом HEAD, пин sha корпуса v1 отстал
  от корпуса после `20f02cd`. Строка `C98` закрыта.
- **ревью слайса C98 закрыто 2026-08-18.** Независимый `review-change` в чистом
  контексте по неизменяемому коммиту `7b6a169`: **Scope PASS · Objective PASS**,
  ноль BLOCKER/MAJOR/MINOR. Вердикт принят потому, что ревью перепроверило числа
  своими прогонами, а не пересказом: перепись пересчитана независимым скриптом
  (42 до, 41 после, 27 неизменившихся, 15 убранных, 14 новых якорённых),
  `blind agreement` 2 / 10 и 4 / 14 получены своей командой, `topic_entity` =
  «панель» сверен с обоими некоммитимыми `visual_plan.json`, и структурно
  подтверждено, что `tests/plan9d_ground_truth` вообще не импортирует
  `query_adapter` — то есть «guard, а не приёмка» верно по построению. Ревью
  назвало один residual risk (не дефект коммита): строка `C101`, два мёртвых
  wrapper'а `asset_manager` обошли бы якорь, если их подключить. Их отсутствие
  вызывающих перепроверено отдельно. Ревью также поймало неточность в счёте
  тестов внутри строки `C100` — исправлено там же.
- **выполнено (было: ждёт владельца):** слепая разметка **55 карточек с картинками**
  по доске (`%TEMP%\plan9d_h\plan9d_h_pack.html`, медиа —
  `%TEMP%\plan9d_h\media\`, пересобирается командой `pack` из
  `tests/data/plan9d/README.md`). Кнопка сохраняет
  `tests/data/plan9d/current_annotations_v2.json`; до этого файла `measure` на v2
  отвечает `WAITING_FOR_OWNER_ANNOTATION`. Ограничение, записанное в сам корпус:
  это хвост сохранённой десятки, а не пул (234 попытки и 1303 результата LIVE-5
  против 100 сохранённых записей), и глубже офлайн-материала нет.
- **цель:** корпус, способный увидеть языковой дефект. Существующий v1 этого не
  может: 14/14 английских субъектов, пустой `media_index`, поэтому приёмка
  правки доказуемости прошла бы на нём при любой правке (`K12` языкового
  аудита).
- **состав:** класс корпуса полем схемы `plan9d-corpus-1` («слепая разметка» ·
  «разбор инцидента»), harness принимает оба; корпус v2 из сохранённых
  кандидатов LIVE-5 и LOCAL after fix — 73 уникальные карточки на 10 сцен;
  слепая доска на существующем `visual_review_board.html`; синтетический случай
  с `must_not_include` (в обоих прогонах запретов ноль); `measure --baseline`
  печатает изменившихся победителей поимённо; след отброшенного по языку
  запроса (`K9`).
- **запрещено:** сеть, повторный прогон и любой платный вызов; перегенерация
  корпуса v1; вторая доска ревью; разметка кандидатов агентом — это входная
  работа владельца, и подменить её нельзя.
- **измеримый результат:** `measure` на v1 даёт прежние 4/14; корпус v2
  содержит поимённо `pexels_32386564` (сцена 003 LIVE-5, `provider`
  `local_library`, `semantic_score` 0.0, `final_score` 7.5, проигравший
  картинке с 72.968) — исход, который обязан перевернуть PLAN-9C-4.
- **required verification:** targeted tests изменённых модулей + gates.
- **вход владельца:** слепая разметка 73 карточек. Шаг закрывается только
  после неё; подготовка доски — не закрытие.

### PLAN-9E — controlled semantic activation

- **status:** blocked (PLAN-9D, PLAN-10C + owner approval) · **commit:** —
- **bounded correction до полного контракта (сверка 2026-08-11).** Этот owner
  принимает **VA-NEW-09** (M1-E: strict render получает тот же fresh
  authorization snapshot, что и draft — сегодня draft-ветка сильнее strict) как
  bounded correction до LIVE render, не начиная activation contract и не
  переводя статус в completed. Активация Vision этим не приближается.
  Дополнительно зафиксировано аудитом (`40, ответ 15): архитектурная готовность
  к Vision после PLAN-10C требует ещё **VA-NEW-02/04/05/08** и единого
  post-review decision invariant. Классы и порядок — блок «Mini plan
  reconciliation 2026-08-11».

- **closure update (2026-08-14).** **VA-NEW-09 / M1-E is closed**: strict render
  now obtains the same fresh canonical `evaluate_usability` snapshot as draft
  immediately before segment creation. This bounded correction does not start
  the activation contract, does not move PLAN-9E to completed and does not
  enable Vision. Full scope and evidence are recorded in M1-E CLOSURE; Review #2
  over M1-D and M1-E is the next exact action.

- **v1 boundary (owner decision D0.4/D0.5, 2026-08-11).** Платный Vision не
  является blocker v1; PLAN-9D-F / PLAN-9D-G остаются optional quality track.
  Semantic assistance для v1 остаётся opt-in за двумя раздельными gates
  (`semantic_brief` в `NETWORK_ACTIONS`, default deny; `config/semantic_brief.json`).
  Это совместимо с уже записанным здесь контрактом «Vision не является
  обязательной runtime-зависимостью» и с `PRODUCT_PLAN.md` разделом 8; статус,
  зависимости и запреты этого шага не меняются.
- **латентное расхождение с этим контрактом, зафиксировано 2026-08-14 (`C80`).**
  Маршрут обещает для semantic assistance два **раздельных** gate — network и
  paid. Для `semantic_brief` так и есть: класс в `NETWORK_ACTIONS`, default deny,
  плюс собственный конфиг. Для **Vision это не выполнено**:
  `src/assets/semantic_visual_openai.py:440` создаёт клиент напрямую, класса под
  Vision в `NETWORK_ACTIONS` нет, `require_network` не вызывается, и единственный
  сторож — paid-гейт `VisionBudgetGuard` (`:170`). Сейчас не эксплуатируется:
  Vision выключен четырьмя независимыми гейтами `config/semantic_visual.json`.
  Практическое следствие — включение Vision на этом шаге **не потребует**
  `--allow-network`, в отличие от всего остального. Это **не** новый PLAN-ID и
  **не** разрешение править код: строка `C80` реестра ждёт своего шага внутри
  этого owner. Статус PLAN-9E не меняется.
- **цель:** включить доказанный semantic decision path только для явно
  выбранного template/project policy.
- **implementation-time verification моделей (2026-08-01).** До первого
  разрешённого live/paid semantic/Vision вызова configured semantic/Vision
  model identifiers обязаны быть сверены с **фактическим provider/backend
  contract** и актуально поддерживаемыми model IDs: проверить configured model
  IDs; сверить их с provider contract; **fail closed** при unknown/unsupported
  model; не выполнять paid call при invalid или непроверенной model config.
  Точная network/provider validation требует owner approval на конкретное
  действие. До такой проверки **нельзя утверждать**, что конкретный model ID
  валиден или невалиден; это implementation-time verification, а не новый
  architecture finding и не новый PLAN-ID.
- **продуктовые режимы Vision (добавлено PRODUCT-PLAN-1).** Концептуально
  продукт различает **off · local · optional paid**. Это **продуктовые
  концепции, а не публичный контракт**: точные публичные имена CLI/API/enum
  здесь намеренно **не фиксируются** и требуют отдельного owner decision в
  момент implementation (`PRODUCT_PLAN.md`, OD-P-3). Режимы обязаны стать
  понятным названием уже существующей конфигурации, а не вторым контрактом.
  `optional paid` требует предварительного расчёта, отображения модели, числа
  проверяемых кандидатов, ожидаемой стоимости, явного подтверждения
  пользователя, кеша, resume без повторного расхода и fail-closed при
  неизвестном результате. `local` — отдельный adapter в той же роли
  evidence-провайдера, а не отдельная capability.
- **Vision не является обязательной runtime-зависимостью.** Продукт обязан
  полностью работать при выключенной Vision; отсутствие backend, бюджета или
  результата даёт безопасный fallback, а не отказ пайплайна.
- **то же правило распространяется на motion backend (добавлено 2026-08-01).**
  Node/браузерный author никогда не становится обязательной runtime-зависимостью
  продукта: его отсутствие, сбой или таймаут дают безопасный fallback по
  существующей completion ladder, а не отказ пайплайна. Активация Vision-review
  композиции подчиняется тем же гейтам этого этапа, что и Vision-review
  кандидатов; отдельный activation-контракт не вводится.
- **запрещено:** глобально включать paid backend, менять default всех старых
  проектов, использовать mock, ослаблять rights/`must_avoid`/misleading gates.
- **измеримый результат:** opt-in policy имеет безопасный fallback при
  отсутствии результата/бюджета/backend; старые проекты и default config
  сохраняют прежнее поведение; выбор и причина записываются в manifest.
- **product test-video checkpoint (owner direction 2026-08-08).** После
  закрытия этого шага и его prerequisites собирается первый **meaningful
  end-to-end acceptance Short**. В отличие от diagnostic Short после
  PLAN-9D-C, это именно acceptance-проверка продукта; она не заменяет
  multi-topic evidence gate PLAN-11 и не ослабляет его требования.
- **required verification:** targeted policy/integration tests + `smoke` +
  `full` как общий activation gate.
- **rollback:** один commit.

### PLAN-10A — query/provider attempt ledger и stop reasons

- **status:** blocked (PLAN-9A) · **commit:** —
- **цель:** каждая попытка и остановка сохранена; best-so-far можно объяснить
  и продолжить после `resume`.
- **допустимые stop reasons:** исчерпаны разрешённые query variants; исчерпаны
  providers и pagination; достигнут budget; несколько итераций не улучшили
  best-so-far; следующий шаг требует отдельного платного разрешения; достигнут
  strict threshold. Бесконечный поиск запрещён.
- **non-blocking follow-up: network denial не должен выглядеть как provider
  error (записано docs-only reconciliation 2026-08-08).** [FACT от HEAD
  `7a8142f`] `require_network` (`src/runtime_network.py`) поднимает
  `NetworkAccessDeniedError(PermissionError)`, а `_search_provider`
  (`src/news/asset_manifest_builder.py:476`) и аналогичный обработчик
  `src/news/asset_scene_completion.py:352` ловят его широким `except Exception`
  и записывают в ledger как `provider_unexpected_error`. Отказ по разрешению
  владельца и настоящий сбой провайдера становятся неразличимы в attempt
  ledger. Естественный владелец — этот шаг: stop reason «требует отдельного
  разрешения» уже входит в его список допустимых причин. Не исправлялось,
  отдельный PLAN-ID не создавался, поведение сети не менялось.
- **required verification:** targeted persisted-contract tests + `full`.
- **rollback:** один commit.

### PLAN-10B — pagination и provider contract

- **status:** blocked (PLAN-10A) · **commit:** —
- **bounded corrections до полного контракта (сверка 2026-08-11).** Этот owner
  принимает **VA-NEW-06** (M2-A: partial mixed-media success не теряется из-за
  соседнего failure — регрессия, появившаяся именно после retrieval symmetry
  `ae6d46c`) и **VA-NEW-10** (M2-A: один retry owner вместо вложенных R²
  попыток) как bounded corrections до LIVE-5, не начиная pagination contract и
  не переводя статус в completed. Класс и порядок — блок «Mini plan
  reconciliation 2026-08-11».
- **bounded correction VA-NEW-22 (RD-A, 2026-08-12) — closed.** Этот owner
  принял и закрыл adapter-дефект `src/providers/pixabay_provider.py`: video
  preview строился из `picture_id`, которого в текущих ответах Pixabay нет,
  поэтому кандидат уходил в скачивание video variant и упирался в preview cap.
  Читается thumbnail выбранного rendition, затем крупнейшего с thumbnail;
  `picture_id` сохранён как reader старых payload. Pagination contract этим не
  начат, статус секции не меняется. Детали — блок «RD-A CLOSURE».
- **цель:** поиск не ограничен первой страницей результатов и фиксированным
  лимитом на пару provider × query.
- **граница:** сначала additive pagination/cursor contract и
  characterization старых adapters; затем каждый active provider переводится
  отдельным под-slice. Провайдер без pagination сохраняет bounded single-page
  adapter и честно сообщает exhaustion.
- **PLAN-10B не является owner provider-registry convergence (D-2).** Гипотеза
  «пять расходящихся реестров надо свести к `providers/registry`»
  **опровергнута**: это разные legitimate facts (actual constructed providers ·
  provider capabilities · fallback language info · source-class priority ·
  diagnostics inventory · availability), а `ProviderCapabilities.query_languages`
  **уже** имеет приоритет над fallback-таблицей. Остаточный cleanup:
  `local_library` declaration mismatch → **PLAN-10D**; вестигиальный
  `DEFAULT_PROVIDER_ORDER` и осиротевшее имя `unsplash` → opportunistic cleanup
  внутри слайса, который и так трогает routing. Отдельный PLAN-ID не создаётся.
  Ответственность PLAN-10B — **pagination / provider exhaustion / provider
  contract behavior**, и загружать её чужой работой запрещено.
- **required verification:** contract-foundation — targeted + `full`; каждый
  provider adapter — targeted; один итоговый `full` при закрытии family.
- **rollback:** один commit на contract и один на provider-family.

### PLAN-10C — adaptive budget и plateau policy

- **status:** blocked (PLAN-10B) · **commit:** — · **обновлено сверкой
  2026-08-11:** `PLAN-9B` снят из блокеров — семейство закрыто, кроме
  отдельного destructive path PLAN-9B-5b, который к бюджету поиска отношения
  не имеет. Шаг остаётся blocked своим вторым блокером **PLAN-10B**.
- **bounded correction до полного контракта (сверка 2026-08-11) — closed
  2026-08-15.** Этот owner принял и закрыл **VA-NEW-12** (M2-B: минимальный hard
  per-scene request budget и stop guard) как bounded correction до LIVE-5, не
  начиная свой полный adaptive-budget contract и не переводя статус в completed.
  Единица бюджета — один `provider.search` (один запрос × один media kind);
  единственный владелец — `SceneRequestBudget` в
  `src/news/asset_provider_adapters.py`, один объект на сцену, общий для general
  search и draft ladder. Adaptive policy, plateau, порядок эскалации и
  `partial preview` этим слайсом не начаты. Детали — блок «M2-B CLOSURE».
- **цель:** политика `quick` / `standard` / `deep` вместо одного фиксированного
  лимита. Бюджет учитывает важность и длительность сцены, сложность субъекта,
  число новых уникальных кандидатов, улучшение best-so-far, число providers,
  стоимость вызовов, strict или draft mode.
- **владеет порядком эскалации** за пределами query variants: исчерпаны
  разрешённые запросы → локальная медиатека → другой provider → разрешённый
  fallback. Эти ступени сняты с PLAN-9B, потому что относятся к
  routing/completion policy, а не к генерации запросов. Включение локальной
  медиатеки остаётся за PLAN-10D и его аудитом, provider contract — за
  PLAN-10B; PLAN-10C определяет только момент перехода и его причину.
- **измеримый результат:** поиск продолжается, пока улучшает best-so-far;
  plateau останавливает; одна сложная сцена не останавливает остальные, не
  удаляет найденные assets, не сбрасывает проект и не блокирует reviewable draft.
- **acceptance criterion «partial preview» (добавлено PRODUCT-PLAN-1).**
  Черновое preview обязано быть возможным и тогда, когда часть сцен не
  разрешена: неразрешённые сцены занимает **безопасный project-owned
  placeholder** существующей completion ladder (ступени `E_generated` /
  `F_emergency`). Это продолжение уже принадлежащего этому слайсу порядка
  эскалации «разрешённый fallback», а не новая политика.
- **запрещено:** случайный нерелевантный asset ради `completed`, misleading
  visual, `must_avoid` conflict, нарушение rights, ложный `publish_ready`.
- **non-goals partial preview (добавлено PRODUCT-PLAN-1):** placeholder в
  preview **никогда** не означает `publish_ready`, `quality passed` или
  коммерческий выпуск и не ослабляет gate финального рендера; **второй preview
  pipeline не создаётся** — расширяется существующий preview/escalation путь;
  второй словарь состояний завершённости не вводится.
- **bounded repair сцены — потребитель этой политики (добавлено 2026-08-01,
  OD-M-6).** Будущий цикл «poster frame → technical QA → Vision review →
  structured repair → эскалация к человеку» **не вводит собственную политику
  бюджета**: число итераций, потолок расходов, детекция plateau и момент
  эскалации остаются за этим этапом. Repair-действия ограничены закрытым
  списком структурированных изменений (сменить утверждённый template той же
  `composition_type` · изменить валидируемые props · изменить длительность или
  порядок слотов · сменить background из существующего shortlist · понизить
  интенсивность motion · отказаться от композиции в пользу стока · эскалировать
  к человеку). Прямое редактирование production-кода агентом в этот список не
  входит. Реализация принадлежит `MOTION-CS4`; scope и статус PLAN-10C этой
  записью не меняются.
- **non-blocking follow-up F2 из PLAN-9C review (добавлено docs-only closure
  2026-08-08).** После semantic demotion (PLAN-9C wiring) состав bounded
  shortlist/review window может измениться: pre-rerank preview set не
  гарантированно равен post-rerank review bundle set — кандидат, демотированный
  Vision, может выпасть из позднего review artifact; новый кандидат может
  войти в review bundle без предварительного preview analysis; любой из этих
  случаев может означать дополнительный semantic/backend call и cost/evidence
  drift. Review-вердикт — MAJOR, но NON-BLOCKING для PLAN-9C, так как
  acceptance PLAN-9C — wiring/order, а размер shortlist и бюджет уже
  принадлежат этому contract (см. запись выше «владеет порядком эскалации»).
  Не исправлялся; отдельного PLAN-ID не создавалось; учитывается при
  проектировании adaptive shortlist/budget policy этого этапа.
- **существующие quality-producers — вход, а не новый движок (добавлено
  2026-08-13).** Пиксельные метрики уже вычисляются на каждом preview
  (`src/assets/visual_metrics.py`: `estimate_crop_suitability`, покадровый
  `_score_frame`) и сегодня не влияют ни на один выбор, а конфиг-веса к ним
  мертвы (**C74**, **C69** реестра). Любая работа по quality-aware отбору
  начинается с переиспользования этих producers; новый quality engine не
  пишется без доказанного gap, пороги и веса этой записью не назначаются.
  Класс, статус и scope PLAN-10C не меняются.
- **required verification:** targeted policy tests после каждого slice;
  `full` один раз при закрытии adaptive-search family.
- **rollback:** один commit.

### PLAN-10D — convergence глобальной локальной стоковой библиотеки

- **status:** blocked (PLAN-10C + аудит) · **commit:** —
- **переформулирован ревизией 2.1.** Прежняя цель «регистрация
  `LocalLibraryStockProvider` в автоматическом поиске» была слишком узкой, а
  формулировка «три независимых LocalLibrary implementation» — **неверной**.
- **[FACT], установленные Secondary Deep Dive:** один `media_index` · один
  rights-authority `apply_policy_to_candidate` · **два** matcher'а · несколько
  consumers/wrappers; legacy path #3 использует **ту же**
  `media_library.search_local_assets`, что и path #1. Аргумент про
  `RIGHTS_REFERENCE_ONLY` **опровергнут**: интерим-значение перезаписывается
  политикой.
- **[FACT] ровно два доказанных расхождения live local-library путей:**
  1. missing `provenance`;
  2. `review_required=True`.
  Обратных расхождений — **ноль**.
- **scope — только GLOBAL LOCAL STOCK LIBRARY.** Соседние legitimate
  capabilities **не объединяются и в конвергенцию не входят**:
  - user/manual project assets (`--assets`);
  - project pool уже скачанных в проект ассетов;
  - глобальная локальная стоковая библиотека — **это и есть scope PLAN-10D**.
- **цель:**
  1. определить canonical matcher / provider boundary;
  2. harmonize provenance и review semantics;
  3. salvage **diversity reserve** из legacy (`min_local_diversity_per_scene` /
     `reserved_download_slots`, через PLAN-L0) — прямо релевантен проблеме
     повторяющихся визуалов; современного эквивалента нет;
  4. удалить superseded wrappers/path после переноса knowledge и callers;
  5. **не создать четвёртый путь.**
- **сопутствующие записи:** `query_adapter` объявляет `local_library`
  провайдером с поддержкой русского, чего не происходит, — declaration mismatch
  закрывается здесь (а не в PLAN-10B). `duplicate_penalty` в
  `rank_local_assets` — фактически **мёртвый код** (`used_asset_ids` вызывает
  `continue` раньше применения penalty); убирается вместе с этим bounded
  слайсом и отдельным PLAN не становится.
- **не смешивать с C50.** Fail-open на явном `review_required=True` — отдельный
  rights correctness defect и отдельный bounded fix, не часть architectural
  convergence.
- **deadline C50 (2026-08-01).** Новый top-level PLAN-ID не создаётся; C50
  остаётся отдельным bounded rights-fix слайсом и может быть выполнен
  независимо после зелёного PLAN-4, когда его bounded scope и tests
  подтверждены. Но как `[HARD]` rights correctness он **обязан быть CLOSED**:
  (1) до расширения / convergence / повторного включения Global Local Library
  в PLAN-10D; (2) до финального product evidence PLAN-11 / M1; (3) до любого
  live/publish-ready workflow, реально способного использовать Global Local
  Library asset с policy normalization. PLAN-9E искусственным owner C50 не
  делается — semantic activation и rights correctness разные
  responsibilities; если PLAN-9E фактически использует LocalLibrary
  publish-ready path, общий `[HARD]` rights gate применяется и без добавления
  формальной dependency.
- **открытый вопрос:** нужно ли вообще регистрировать `local_library` как
  `StockProvider` — решается по исходу конвергенции.
- **измеримый результат:** одна canonical local-library capability без
  расхождений в rights/provenance; diversity reserve сохранён; четвёртый путь
  не создан; при отрицательном решении о регистрации registry не усложняется.
- **required verification:** при изменении shared provider registry —
  targeted + `full`; для решения `defer/reject` — docs QA.
- **rollback:** один commit.

### PLAN-11 — multi-topic product evidence

- **status:** blocked (PLAN-9E, PLAN-10C) · **commit:** —
- **scope:** текущий automatic asset-search path относится прежде всего к
  `fullscreen_voiceover_v1`. `story_card_text_only_v1` сейчас требует
  явный local `source_asset`; PLAN-11 не выдаёт улучшение одного workflow за
  доказательство качества всех templates.
- **примечание о зависимости:** PLAN-10D не является обязательным условием
  M1, если аудит не доказал ценность/безопасность локальной библиотеки.
  Evidence запускается после каждого product slice на сохранённых fixtures;
  итоговый multi-topic gate не является первой проверкой результата.
- **early multi-topic regression (OD-25).** Первая проверка на разных доменах
  **не ждёт PLAN-11**: после каждого существенного product slice, где это
  релевантно, проверяются репрезентативные темы минимум из разных классов —
  animals/wildlife · energy/technology · geography/infrastructure. PLAN-11
  остаётся финальным product evidence gate, но **не первой** multi-topic
  проверкой.
- **PLAN-11 как EVIDENCE GATE ложных product capabilities.** Требование «нет
  ложного `publish_ready`» расширяется до «каталог не обещает несуществующий
  output». [FACT] catalog объявляет **5** active export targets, тогда как три
  production-owner согласованно работают с **3**; `supported_export_targets` и
  `safe_zone_profile` в render decision **не участвуют** (ноль production-
  читателей), то есть каталог — единственный outlier.
  **Цель — truthful catalog.** Создавать бессмысленные byte-identical
  TikTok/Stories outputs только ради соответствия каталогу **запрещено**.
  **PLAN-11 не является implementation owner:** у него `required verification:
  product gate`, `rollback: —` и нет allowed zones для source. Implementation —
  будущий небольшой bounded `production_catalog` slice, который либо убирает
  несуществующие targets из `active`, либо переводит их в `planned`, в
  зависимости от фактического intended product contract на момент
  implementation. Нового PLAN-ID не создаётся.
- **три reference domains:**
  1. животные и строгий контекст среды: кит или косатка в открытом океане;
     бассейн, шоу и трибуны исключены;
  2. энергетика и технологии: солнечная электростанция, аккумуляторное
     хранилище, энергосеть;
  3. география и инфраструктура: строительство крупного канала через пустыню;
     точные карты, satellite imagery и infographic допустимы, если правдивее
     случайного видео.
- **gate не использует единый глобальный процент видео.** Соотношение
  video / still / infographic определяет template policy.
- **motion / hybrid evidence — future criterion (добавлено 2026-08-01).**
  Когда появится первый hybrid-формат, требование «каталог не обещает
  несуществующий output» распространяется и на `composition_type`: объявленный
  тип композиции обязан иметь работающего canonical author, иначе он остаётся
  `planned`. Это **будущий** критерий: пока `MOTION-CS1…CS4` не запланированы и
  не выполнены, он не применяется и состав, статус и gates PLAN-11 не меняет.
  PLAN-11 по-прежнему **не является implementation owner** ни каталога, ни
  motion-направления.
- **общие требования:** все обязательные сцены имеют безопасный usable visual;
  ноль `must_avoid`; ноль misleading conflicts; ноль нарушений
  rights/provenance; нет новых topic-specific hardcodes; best-so-far и
  rejection evidence сохранены; `resume` не ухудшает результат.
- **M1:** 0 USD, ноль новых платных Vision-вызовов.
  По умолчанию M1 использует сохранённые/local fixtures; новый provider search,
  download или иной сетевой вызов требует отдельного разрешения даже при
  нулевой стоимости.
- **M2:** бюджет платных вызовов — **TBD, owner approval before M2**. Числовые
  лимиты не согласованы и здесь не фиксируются.
- **M3:** `strict` выставляет `publish_ready=true` только после реальной
  визуальной проверки. Бюджет не утверждается до анализа M2.
- **product test-video checkpoint (owner direction 2026-08-08).** После
  acceptance Short шага PLAN-9E продуктовым evidence/regression материалом
  этого gate становятся **5–10 real-world Shorts на разных темах**. Состав тем
  подчиняется трём reference domains выше; числовой ориентир не отменяет ни
  одно общее требование gate и не является отдельным разрешением на платные
  или сетевые вызовы.
- **required verification:** product gate. **rollback:** —

### PLAN-12 — классификация и архивирование документации

- **status:** blocked (PLAN-1B) · **commit:** —
- **изменено ревизией 2.** Прежний блокер «PLAN-1» больше не существует: PLAN-1
  разделён на capability gates. **Вся family PLAN-12 не блокирует первый
  product slice** — она выполняется параллельно или после PLAN-9A. Внутренняя
  последовательная цепочка `12E → 12A → 12B → 12C` сохраняется без изменений.
- **добавлено в PLAN-12B (перенесено из PLAN-1C):** пофайловая классификация
  `docs/implementation` (96 файлов), `docs/audits` (9), `docs/architecture` (5),
  `docs/apps` (3) — registry C27, C28. PLAN-9A её не требует.
- **порядок внутри этапа:** `12E → 12A → 12B → 12C`.
  **Буквы под-slices — идентификаторы, а не порядок выполнения.** Цепочка
  последовательная: каждый под-slice зависит от **непосредственно
  предыдущего** звена, а не от 12E напрямую. Пропуск звена запрещён.
  Существующие ID не переименовываются.
- **цель:** current navigation ведёт только к актуальным документам.
- **bounded sub-slices** (перечислены в порядке выполнения):
  - **PLAN-12E — document ownership model.** *Выполняется первым внутри
    PLAN-12.* **Зависимости: PLAN-1B.**
    Решение владельца от 2026-07-31: принято **направление B** —
    `current` (волатильное состояние и активные планы) / `architecture`
    (долговечные границы) / `product` (цель, quality, evaluation) /
    `runbooks` (операционные пути запуска) / `adr` / `archive` /
    `implementation`.
    **Направление — это ownership *direction*, а не разрешение перемещать
    конкретные файлы.** Все размещения ниже — candidate, не назначение:
    - `docs/apps/*` — candidate source для `docs/runbooks/`; exact per-file
      migration только после PLAN-12B evidence; каталог не архивируется;
    - `docs/architecture/visual_rendering_policy.md` — candidate source для
      `docs/product/QUALITY_BAR.md`; move/extract только после подтверждения
      PLAN-12B, что competing quality owner не существует (registry C23);
    - `docs/contracts/*` — target responsibility решается **по содержимому
      каждого файла**, не автоматически по каталогу (registry C22);
    - `SYSTEM_MAP.md` — target `docs/architecture/` принят концептуально;
      физический move выполняется только вместе с обновлением всех callers
      в соответствующем bounded slice.
    Категории `architecture/`, `apps/` и `contracts/` не удаляются ради
    меньшего числа каталогов. Число каталогов и число Markdown-файлов
    метриками качества не являются. Критерии — один canonical owner на
    responsibility, понятный lifecycle, отделение current от historical,
    отделение runtime data от source, сохранность product knowledge,
    тематичность документов и создание нового owner только при доказанной
    необходимости.
    *Измерение Foundation audit, не gate:* `docs/current/` — 2639 строк, из
    них 1616 (61%) приходится на два волатильных плановых документа.
    Разрешённые зоны: только `docs/current/CLEANUP_REGISTRY.md` и этот файл.
    Никаких move в этом под-slice.
  - **PLAN-12A — current docs. Зависимости: PLAN-12E.** Перенести уникальные
    подтверждённые данные `ARCHITECTURE_BOUNDARY_MAP.md` в `SYSTEM_MAP.md`,
    затем удалить current-копию; убрать дубли CURRENT_STATE/START_HERE.
    `docs/current/PRODUCT_EVIDENCE_GATE.md` **обязан переехать**, а не просто
    сменить `status`: [FACT] пять его `source_paths` указывают внутрь
    gitignored `projects/`, поэтому его evidence неверсионируемо и файл не
    может остаться в `docs/current/`.
    После слияния `SYSTEM_MAP` ← `ARCHITECTURE_BOUNDARY_MAP` **измерить
    результат как measurement**. Решение о `RUNTIME_FLOWS` принимается по
    качественным критериям, а не по числу строк — см. отдельный пункт
    «`RUNTIME_FLOWS` — CONDITIONAL NEW OWNER CANDIDATE» ниже.
  - **PLAN-12B — данные внутри docs. Зависимости: PLAN-12A.** Перенести
    production/evaluation fixtures из `docs/implementation` в versioned
    fixture/data owner и обновить callers; paid evidence сохранять без
    переписывания истории.
  - **PLAN-12C — archive. Зависимости: PLAN-12B.** `PROJECT_RESCUE_MASTER_PLAN.md`
    и подтверждённо исторические plans/audits/reports переместить в
    `docs/archive`, обновив navigation и links.
    **Не начинается, пока не закрыты 12E, 12A и 12B:** archive/move без
    утверждённой модели владения и без выполненных предшествующих шагов
    запрещён.
    Персональные ограничения состава:
    - `docs/architecture/visual_rendering_policy.md` — **временно защищён от
      archive и delete** до подтверждения PLAN-12B, что competing quality
      owner не существует (registry C23);
    - `docs/architecture/localization_and_voice_architecture.md` — **не
      объявляется заранее ни `keep`, ни archive-кандидатом**: DEFER вместе с
      остальными `docs/architecture/*` до полного per-file evidence
      (registry C28);
    - состав `docs/implementation`, `docs/audits`, `docs/architecture` и
      `docs/apps` — **DEFER до PLAN-12B** (registry C27).
- **`RUNTIME_FLOWS` — CONDITIONAL NEW OWNER CANDIDATE.** Не «justified».
  Создаётся только при выполнении всех пяти условий: пофайловая классификация
  `docs/*` завершена (PLAN-12B, ревизия 2 — прежде PLAN-1C);
  фактические runtime-flow sources прочитаны полностью (`docs/apps/*`,
  `COMMANDS.md` `10, `skills/resume-project`, `skills/create-short-video-first`,
  ADR 0006); PLAN-12A выполнил merge; итоговый `SYSTEM_MAP` измерен как
  measurement; **качественно** доказано, что runtime execution / stage /
  resume / failure information не помещается туда без смешения
  ответственности. Если после merge `SYSTEM_MAP` остаётся тематичным и его
  ответственности не смешиваются — новый owner не создаётся, независимо от
  числа строк.
- **действия по классам:** keep, move, archive, backup_then_untrack, delete,
  defer. Целое семейство одним действием не архивируется и не удаляется.
- **запрещено:** untrack двенадцати reference jpg до переноса dataset;
  переписывать historical snapshot как current; оставлять битые ссылки;
  начинать 12C раньше закрытия 12E/12A/12B; трактовать буквенную нумерацию
  под-slices как порядок выполнения.
- **required verification:** PLAN-12E — docs QA; PLAN-12A/12C — docs QA;
  PLAN-12B — targeted production callers + `full`; `git diff --check` всегда.
- **rollback:** один commit на семейство.

### PLAN-13 — ownership migration, retirement и root-structure classification

- **status:** blocked (PLAN-1B) · **commit:** —
- **изменено ревизией 2.** Блокеры PLAN-6C и PLAN-12 сняты как механические:
  прямой зависимостью является только capability gate PLAN-1B. **PLAN-9A не
  блокирует.** Значительная часть прежнего scope PLAN-13D переехала в PLAN-L.
- **цель:** один owner бизнес-логики, один установленный package root и один
  канонический CLI без потери compatibility/persisted contracts.
- **root-structure classification (OD-6, OD-9) — новый обязательный под-slice
  PLAN-13E, выполняется до любого move.** Старое допущение «существующий path —
  аргумент сохранить path» отменено; locked decisions 8 и 9 больше не запрещают
  пересмотр. Но переносить ради эстетики запрещено: **сначала классификация пяти
  групп, потом решение.**

  | Группа | Что известно | Действие |
  |---|---|---|
  | `channels/` | после L3 остаются `nature_science_news_ru` (активный) и `nature_pulse` | классифицировать вместе с template policy |
  | `schemas/` | 8 versioned contracts, читаются `test_artifact_schemas` | классифицировать |
  | reusable templates | `config/render_presets/`, `channels/*/templates/`, versioned SVG | классифицировать |
  | evaluation resources | live-eval dataset/results/frames — registry C31 | классифицировать; `docs/` подтверждён неправильным owner (OD-8) |
  | versioned assets/config | [FACT] после L3 все 5 оставшихся файлов `config/` активны, 8–21 caller каждый | **оставить на месте**, отдельной причины двигать нет |

  **Top-level `resources/` заранее не создаётся (OD-9).** Решение принимается по
  результату классификации и только если `resources/` реально уменьшает число
  owners и делает структуру понятнее. `resources/evaluation/` — candidate path,
  не назначение.
- **PLAN-13E также назначает physical target для C31** и переводит caller
  `src/assets/semantic_visual_evaluation_tooling.py:26,38,695` плюс
  `tests/test_semantic_decision_policy.py`, освобождая `docs/` от production
  dependency. Синтетический генератор
  `tests/test_semantic_visual_evaluation.py:458 _write_prepared_dataset` уже
  существует и повторно не создаётся.
- **applications против developer tools.** Это разные responsibilities:
  `apps/*` и `anime_factory/` — applications; `tools/` — developer tooling, QA,
  диагностика и maintenance. `anime_factory` остаётся **migration source**
  будущего `video_repurposer` (ADR 0016), а не постоянной параллельной
  архитектурой приложения; его runtime (`episodes/`, `input/`, `config.yaml`)
  живёт внутри source tree и переезжает во внешний workspace.
  `apps/news_to_short` вторым CLI не остаётся (OD-2, registry K08).
- **bounded sub-slices:**
  - **PLAN-13A — caller migration:** одно семейство production callers, затем
    current docs/examples, затем tests;
  - **PLAN-13B — ownership transfer:** переносить implementation, не
    копировать; Fullscreen, Story Card, Anime, projects, assets/providers,
    audio/music, subtitles и rendering — разные commits.
    **Orchestration finding (D-3, ревизия 2.1) — разделён на две
    ответственности; формулировка «два конкурирующих orchestration owner»
    опровергнута.** ADR 0009 **намеренно** разделяет application orchestration
    и news pipeline ownership.
    - **A. Точный idempotency contract defect.** [FACT] explicit `stage=` path
      отключает output-validated idempotency ADR 0006 через условие
      `and not stage`; batch-режим (`until_stage=`) idempotency **соблюдает**,
      explicit-режим повторно исполняет завершённые локальные стадии. Контракт
      для `stage=` не покрыт ни одним тестом. Owner — **ADR 0006 /
      `src/news/pipeline.py`**, отдельный будущий bounded slice.
      **Severity: MEDIUM.** [FACT] повторного платного TTS аудит **не
      обнаружил**: существуют несколько независимых guard'ов и существующие
      тесты; повторяются только локальные preview/final render.
      Вызовов — **4–7** в зависимости от режима, не «ровно 7».
    - **B. Возможная поздняя orchestration convergence.** Owner — PLAN-13B,
      **только если** после исправления contract остаётся архитектурная
      необходимость. «Один orchestration owner» **не** является уже принятым
      решением; правильный target — один контракт идемпотентности, действующий
      во всех режимах вызова.
    - **обязательное предусловие любой из двух работ:** подтвердить фактических
      `resume` / `force-stage` / `stop-stage` callers и публичное поведение до
      изменения — условная логика существует ради сосуществования двух режимов;
- **HIGH-3 (channel/project formats) — новый этап не создаётся.** Несколько
  форм канала и две системы проектов покрыты существующими **PLAN-1B** и
  **PLAN-13** (M02, C10, PLAN-13E). Позже: inventory channel formats → inventory
  project/state formats → tolerant readers → migrate callers → delete
  transitional duplicates. **Prerequisite текущих search/input fixes это не
  является;**
  - **PLAN-13C — wrapper/package retirement:** один wrapper/package family
    после zero-production-caller gate и dependency/toolchain audit PLAN-6C;
    root `ai_youtube/` и `src/ai_youtube/` свести к одному installable
    src-layout package;
  - **PLAN-13D — legacy pipeline: перенесён в PLAN-L ревизией 2.** Весь его
    прежний scope — сохранение maintenance-команд (теперь PLAN-L2), удаление
    `pipeline.py` (PLAN-L4), снятие production-импорта `scripts.test_moss_voices`
    (PLAN-L4, registry C18) — выполняется в параллельном этапе PLAN-L, потому
    что ждать здесь было незачем: у legacy-стека ровно один production-caller.
    Здесь под-slice сохранён как якорь ссылок и собственного содержания не имеет.
  - **PLAN-13E — root-structure classification:** см. выше в этом разделе.
- **предусловие удаления любого старого entrypoint:** переведены или удалены
  tests, актуальные docs, console scripts, module entrypoints и подтверждённые
  внешние callers в том же изменении. Красные tests или лгущая документация
  после retirement недопустимы.
- **измеримый результат:** один physical package root и один канонический CLI.
- **запрещено:** смешивать caller migration, ownership transfer, runtime
  migration и cleanup в одном diff.
- **required verification:** targeted contract + ближайший integration smoke;
  `full` на package/shared-contract boundaries.
- **rollback:** один commit на семейство.

### PLAN-14 — repository/runtime minimalism и переносимость

- **status:** blocked (PLAN-6B, PLAN-6C, PLAN-12, PLAN-13) · **commit:** —
- **цель:** кодовый репозиторий содержит только source/config/tests/versioned
  docs, а runtime/toolchain/user data имеют явных владельцев вне code root.
- **Anime Factory: два разных предмета, смешивать запрещено (OD-23,
  ревизия 2.1).**

  | Предмет | Классификация | Owner |
  |---|---|---|
  | Anime Factory **capability** | **PRESERVE FOR FUTURE PRODUCTIZATION** — source implementation будущего `video_repurposer`, **не** disposable legacy | post-UI roadmap; запись — PLAN-8, преждевременной миграции в PLAN-13 нет |
  | Anime **runtime внутри source repo** (`input/`, `episodes/`, `artifacts/`, `outputs/media`) | **FIX LATER VIA WORKSPACE** — дефект расположения runtime | **PLAN-14**, registry C15 |

  `enabled=False` / `implementation_status="planned"` **не является
  доказательством ненужности**: capability выключена, а не отвергнута (усиление
  locked decision 5). Productize Anime сейчас не нужно; deep audit Anime
  Factory идёт **после** UI Content Creator.
- **bounded sub-slices:**
  - **PLAN-14A — финальный minimalism QA:** повторно запустить и при
    необходимости усилить созданный в PLAN-6B
    `tools/qa/check_repository_minimalism.py`; сравнить результат с ранним
    baseline и закрыть только подтверждённые нарушения. Orphan/duplicate —
    review evidence, не автоматическое разрешение удалить;
  - **PLAN-14B — dependency/toolchain convergence:** реализовать решения
    аудита PLAN-6C: `pyproject.toml` — владелец direct dependencies,
    `requirements.lock` — проверенный lock; `requirements.txt` оставить,
    генерировать или удалить только по зафиксированному caller/docs gate.
    Anime/ML optional dependencies, `venv/`, MOSS/Whisper/model weights и
    agent-specific adapters имеют раздельных owners. Обновление lock/download
    требует отдельного network approval.
    За 14B остаётся distribution boundary `tools/` (registry C26).
    **Изменено ревизией 2:** installed-package defect C25,
    `scripts/test_moss_voices.py` C18 и hardcoded `G:/` C24 закрываются в
    PLAN-L, потому что их носители (`pipeline.py`, `scripts/`,
    `config/video_style.json`, `channels/psychology/`) там удаляются. Здесь они
    не дублируются; 14B только проверяет, что после L4 в выжившем versioned
    config не осталось hardcoded drive;
  - **PLAN-14C — generated/cache/empty directories:** удалять только
    воспроизводимые cache/temp и подтверждённо пустые runtime directories по
    проверенному абсолютному пути; пустой `__init__.py` не мусор;
  - **PLAN-14D — runtime inventory и отбор representative corpus.**
    **Переписан ревизией 2 (OWNER: тестовое медиа disposable).** Inventory
    counts, manifests, project/media/model/toolchain roots и target workspace —
    как раньше, ничего не копируя и не удаляя. **Добавлено:** классификация и
    дедупликация 749 legacy JSON-манифестов (registry C32) по `schema_version`,
    manifest shape, completion state, resume state, legacy edge case и
    malformed/partial; отбор **минимального representative corpus**,
    достаточного tolerant-reader tests. Полный набор — во внешний retirement
    bundle как historical evidence. **749 файлов не становятся permanent
    architecture anchor.** Checksum-верификация применяется только к
    отобранному корпусу;
  - **PLAN-14E — workspace migration.** **Переписан ревизией 2.** Прежний
    `copy → verify counts/manifests/checksums → switch` для всего дерева
    заменён на: сохранить отобранный corpus, `media_index.json`, versioned SVG
    и, если нужно, минимальный voice sample с provenance (OD-3) → создать
    внешний workspace → переключить default → удалить disposable медиа.
    Выполняется только по отдельному owner approval; dual-read legacy roots
    сохраняется.
    **`MOSS_TTS_Nano/` не переносится (OD-7):** это цельный вендоренный
    сторонний репозиторий, а Runtime Workspace не является хранилищем исходного
    кода. Он ретайрится в PLAN-L4 вместе с `src/tts_providers/` после Knowledge
    Salvage Gate;
  - **PLAN-14F — root allowlist и правила `.gitignore`:** по одному top-level
    family за commit; tracked source, runtime/user data и generated output
    классифицируются раздельно.
    **Разрешённые зоны включают `.gitignore`** — это единственный slice,
    которому оно разрешено. Причина: `.gitignore` описывает именно root
    allowlist, а C20 и C21 — правила о top-level путях. **PLAN-6B остаётся
    detector/report-only owner и `.gitignore` не правит**; молчаливое
    превращение report-слайса в mutation-слайс запрещено. Нового PLAN ради двух
    правил не создаётся.
    Здесь исполняются exit conditions:
    (a) **C21** — директорное правило `assets/broll/` заменяется на
    `assets/broll/*`, после чего `git ls-files -i -c --exclude-standard` не
    содержит `.gitkeep`;
    (b) **C20** — `output/` и `tmp/` получают правила `.gitignore`. Удаление
    самих untracked артефактов в commit не входит и выполняется отдельно
    (PLAN-14C для воспроизводимого cache/temp), потому что untracked-файлы
    Git-состояние не меняют.
    **Изменено ревизией 2:** 8 × `outputs/*.json` (C19) и
    `outputs/asset_library_report.md` (C29) снимаются с Git в **PLAN-L4**
    вместе с их producer `pipeline.py --asset-report`, поэтому здесь остаётся
    только `assets/broll/.gitkeep` (C21) и остаток root allowlist. Обратить
    внимание: `src/media_library.py` при этом **сохраняется** — он используется
    активным news-путём;
- **измеримый результат:** report-only QA зелёный по утверждённому allowlist;
  runtime default не зависит от repo root/drive; сохранён именно
  `Preserved runtime corpus`, а не всё дерево runtime.
- **required verification:** targeted paths/contracts; `full` после path/
  package/toolchain changes; без реального render и сети.
- **rollback:** один commit на под-slice; data copy не совмещается с source
  retirement.

### PLAN-15 — final rescue acceptance

- **status:** blocked (PLAN-11–PLAN-14) · **commit:** —
- **цель:** доказать чистоту, понятность и переносимость, а не только закрыть
  строки плана.
- **обязательные проверки:**
  - clean Git и отсутствие незаписанного handoff;
  - docs QA, repository minimalism QA, smoke, fast и full offline;
  - canonical CLI и installed package из произвольного temporary checkout/path
    без hardcoded username/drive; сеть не требуется;
  - один owner на capability, один package root/CLI, закрытые wrappers и
    отсутствие доказанных duplicate implementations;
  - старые persisted projects/manifests читаются tolerant readers;
  - runtime/user media counts/checksums не ухудшились;
  - product gate M1 и честный active/planned/disabled catalog.
- **измеримый результат:** `CURRENT_STATE.md` описывает фактический финальный
  продукт; `CLEANUP_REGISTRY.md` не содержит бессрочных переходных состояний
  без owner evidence; post-rescue roadmap для `video_repurposer` и
  longform/documentary находится в `PRODUCT_PLAN.md`, а не в placeholder-коде.
- **required verification:** все перечисленные offline checks.
- **rollback:** финальный docs/checkpoint commit; проблемный implementation
  откатывается по его собственному bounded commit.

## Unscheduled candidate slices — Motion family

Записано 2026-08-01 слайсом `MOTION-ROADMAP-1`. Это **не этапы программы**.

Статус всей семьи:

- **не получают PLAN-ID** и не занимают номера существующих этапов;
- **не становятся** `current_checkpoint`;
- **не входят** в критический путь и ни один существующий этап не блокируют;
- **требуют отдельного owner approval** перед планированием;
- подчиняются общему правилу `PRODUCT_PLAN.md` раздела 18: до approval
  candidate slice не планируется и PLAN-ID не получает.

Временные метки — `MOTION-CS1`, `MOTION-CS2`, `MOTION-CS3`, `MOTION-CS4`.
Продуктовое обоснование каждой — `PRODUCT_PLAN.md`, раздел «Motion Design and
Multi-Renderer Composition». Findings — C53–C62 реестра.

### MOTION-CS1 — Renderer Foundation

- **user outcome:** пользователь видит сцену **до** дорогого финального
  рендера; неизменённые сцены не перерендериваются; будущий второй author
  получает единый segment contract.
- **предлагаемый scope:** characterization и baseline visual regression
  **первыми** (registry C61) · рабочий scene/poster preview (C58) · единый
  контракт canvas / FPS / pixel format / duration (C59) · per-scene
  fingerprint и кэш сегментов (C60) · technical QA готового сегмента.
- **`OWNER_DECISION_REQUIRED` — место persistence fingerprint.** Исходный
  аудит содержит **противоречие**: он одновременно требует «не менять persisted
  schema» и «добавить fingerprint в `assets_manifest`». Оба утверждения
  одновременно невыполнимы, поэтому фиксируется только следующее: fingerprint и
  кэш **обязательны**; точное место их persistence **не утверждено**; сначала
  проверяются существующий render manifest, project state и tolerant readers;
  `assets_manifest` **не выбирается автоматически**; любое изменение persisted
  schema является owner tripwire и требует отдельного разрешения.
- **предлагаемые non-goals:** не добавлять зависимости · не менять concat/mux/
  subtitle-логику · не создавать второй preview pipeline · не создавать второй
  project state · не замещать stock FFmpeg path (C57).
- **отношение к существующим этапам:** это и есть предполагавшийся PLAN-8
  «будущий bounded renderer slice» для C45; PLAN-8 остаётся roadmap owner.

### MOTION-CS2 — Isolated Comparative PoC

- **user outcome:** решение о motion backend принимается по измерениям, а не по
  внешнему рейтингу.
- **участники:** Remotion · HyperFrames · текущий MoviePy-рендерер Story Card
  как baseline. **Motion Canvas не участвует** (OD-M-11) и добавляется только
  если оба web-кандидата провалят обязательные критерии детерминизма или
  Windows-надёжности.
- **предлагаемые кейсы:** animated title · highlighted captions · statistic
  counter · comparison card · ECharts line chart · stock background + motion
  overlay · process diagram · вертикальный вариант · горизонтальный вариант ·
  alpha/transparent overlay · **Story Card parity case** (обязателен, OD-M-8).
- **обязательная изоляция:** не меняет активный Content Creator, persisted
  manifests, Python-зависимости и активный renderer; не выполняет платных
  вызовов и сетевых операций без отдельного разрешения; **не становится
  автоматическим fallback**.
- **измерения остаются измерениями,** а не архитектурными правилами и не
  нормами продукта — действует общая `Measurement policy`.

### MOTION-CS3 — Shared Design Tokens

- **user outcome:** один канал/тема выглядит одинаково у FFmpeg/Python-автора и
  у будущего web-автора.
- **предлагаемый scope:** один владелец для colors · typography · spacing ·
  safe zones · canvas/FPS · radii · shadows · motion durations · easing ·
  intensity levels · encoding profiles. Отдельно — развести design tokens и
  контент конкретного ролика в существующем render preset (registry C62).
- **`OWNER_DECISION_REQUIRED` — место хранения:** `channels` либо
  `config/design_tokens`. Не выбрано.
- **предлагаемый non-goal:** отдельная design system на каждый backend
  запрещена; внешний вид существующих проектов не меняется молча.

### MOTION-CS4 — SceneComposer and First Hybrid Explainer

- **зависимости:** `MOTION-CS1` + `MOTION-CS2` + `MOTION-CS3` + owner-решение
  по backend + релевантная query/asset foundation **PLAN-9B** (OD-M-13).
- **user outcome:** первая production-сцена совмещает стоковый материал и
  качественный motion.
- **предлагаемое направление scope:** additive composition intent в
  **существующих** визуальных контрактах · **`production_plan.json` не
  создаётся** · расширение существующего `production_catalog`, а не второй
  registry · один выбранный web backend · первая chart-композиция на ECharts ·
  первый hybrid explainer формат/шаблон · переиспользование существующих
  rights / completion / project / timeline / subtitle owners · Node остаётся
  опциональным с безопасным fallback.
- **парный retirement (PD-11):** рисующая часть `generated_infographic`
  (C56) · MoviePy-рендерер Story Card **после** parity gate (C53) ·
  зависимость `moviepy` **после** caller gate (C54, C55). Шаблон Story Card
  при этом сохраняется.
- **не фиксируется без owner approval:** точная persisted-схема и публичные
  имена `composition_type`.

## Unscheduled candidate slices — Premium/Envato family

Записано 2026-08-07 owner-approved read-only аудитом «AI Visual Selection +
Envato Personal Browser Agent». Это **не этапы программы**.

Статус всей семьи:

- **не получают PLAN-ID** и не занимают номера существующих этапов;
- **не становятся** `current_checkpoint`;
- **не входят** в критический путь и ни один существующий этап не блокируют;
- **требуют отдельного owner approval** перед планированием;
- подчиняются общему правилу `PRODUCT_PLAN.md` раздела 18: до approval
  candidate slice не планируется и PLAN-ID не получает.

Временные метки — `ENVATO-CS1`, `ENVATO-CS2`, `ENVATO-CS3`. Продуктовое
обоснование — `PRODUCT_PLAN.md`, раздел 11.7 «Premium asset sources» и раздел
17 (`OD-P-14`, `OD-P-15`, `OD-P-16`).

**Отношение к FUNCTION 1 аудита (AI visual asset selection).** Общий
semantic/Vision evaluator новой candidate family не является: он уже
покрывается существующим route `PLAN-1C′ → PLAN-9C → PLAN-9D → PLAN-9A →
PLAN-10A → PLAN-10B → PLAN-10C → PLAN-9E`. Ни один из этапов этого route этим
разделом не меняется; `ENVATO-CS3` только подключает Envato-кандидатов к уже
существующему `PLAN-9C` wiring.

### ENVATO-CS1 — canonical premium manual fallback

- **objective:** довести уже существующий `EnvatoManualProvider` fallback до
  канонического config/CLI execution path.
- **фактический existing flag (проверено 2026-08-07):**
  `selection_config["envato_manual_fallback_enabled"]` в
  `src/news/asset_manifest_builder.py`.
- **предлагаемый scope:** canonical config path · canonical CLI/config
  enablement · reuse существующего `EnvatoManualProvider` · reuse
  существующего manual import (`EnvatoManualProvider.import_asset`) ·
  targeted offline tests.
- **не включает:** сеть · браузер · новый provider · AI Vision · commercial
  API integration.
- **test strategy:** deterministic offline unit/contract tests.

### ENVATO-CS2 — personal interactive browser agent

- **classification:** `EXPERIMENTAL` · personal-only.
- **objective:** автоматизировать поиск Envato для локального владельца
  приложения через видимый interactive browser workflow.
- **предлагаемая архитектура (design direction, не immutable public
  contract):** headed Playwright · отдельный persistent browser profile,
  управляемый приложением (default личный Chrome profile не автоматизируется)
  · deterministic DOM/browser actions там, где они надёжны ·
  visual/computer-use reasoning только там, где действительно нужно
  интерпретировать UI/content · visible browser, пользователь видит действия
  · login выполняет человек · MFA выполняет человек · CAPTCHA выполняет
  человек · challenge: PAUSE → human takeover → continue · пароль Envato
  AI-YouTube не хранит.
- **download handoff:** browser workflow → licensed user download → asset
  file + available license/project evidence → **существующий** envato-manual
  import path (`EnvatoManualProvider.import_asset`) → SHA-256 → provenance →
  license proof → `rights_declaration` → `review_required` → обычный
  downstream scene/render path. Новый manifest importer, rights stack или
  downloader поверх существующего manual import owner не пишется.
- **strict anti-evasion boundary.** Implementation не должна включать:
  fingerprint spoofing · намеренное сокрытие webdriver · stealth-плагины для
  обхода detection · proxy rotation ради обхода ограничений · CAPTCHA bypass
  · MFA bypass · rate-limit bypass · mass downloading · identity/device
  impersonation. Security challenge требует human takeover.
- **network boundary.** Interactive browser — network-capable execution.
  Implementation требует нового именованного action class через существующего
  единственного owner `src/runtime_network.py` (проверено 2026-08-09:
  закрытый словарь `NETWORK_ACTIONS` содержит `provider_search`,
  `asset_download`, `preview_download`, `article_fetch`, `voice_preflight`,
  `semantic_brief`); отдельный permission bypass не создаётся.
- **test strategy.** Offline CI: unit tests · contract tests ·
  browser-controller logic через mocks/fixtures · manual-import handoff
  tests. Real Envato browser tests: **local opt-in / manual only**; реальный
  Envato account в обычном CI никогда не требуется.
- **dependencies:** `ENVATO-CS1`, `OD-P-14`, `OD-P-16`.

### ENVATO-CS3 — AI evaluation of premium candidates

- **objective:** подключить Envato preview/candidates к **общему**
  semantic/Vision evaluator.
- **не создаёт:** `EnvatoVisionEvaluator` или любой отдельный
  Envato-specific Vision stack. Envato использует тот же evidence/decision
  owner, который активируется через **PLAN-9C**.
- **dependencies:** `PLAN-9C`, `ENVATO-CS2`.
- **test strategy:** fixture-based offline tests.

## Результат после каждого этапа

Это краткая карта состояния, а не второй набор критериев готовности. Полные
gates и проверки остаются в соответствующих разделах выше.

| После этапа | Что фактически получаем |
|---|---|
| PLAN-0 | Один активный versioned execution plan на отдельной локальной ветке. |
| PLAN-1D-routing | Новый агент попадает в этот план, а не в historical master plan. |
| PLAN-1C′ | Закрыт C01-SEM: у asset/semantic capability известны owner, callers, persisted contracts, дубли и тесты. Снят один из двух gates PLAN-9A и PLAN-9C. |
| PLAN-1A / PLAN-1B | Capability gates для PLAN-L и PLAN-13; product-работу не блокируют. |
| PLAN-L | Legacy content stack ретайрен после Knowledge Salvage Gate: −~5700 строк, −6 тестов, −6 top-level путей; закрыты C17, C18, C19, C24, C25, C29; знание сохранено, retirement обратим. |
| PLAN-2 | Исправленные voice-profile fixtures без изменения рабочего production resolver. |
| PLAN-3 | Исправленные completion/resume fixtures, соответствующие output-validated idempotency. |
| PLAN-4 | Зелёный и воспроизводимый полный offline baseline на зафиксированном source HEAD. |
| PLAN-5 | Один test runner с режимами `smoke`, `fast`, `targeted`, `full`; локальные проверки и offline CI используют одну командную модель. **Параллелен PLAN-9B.** |
| PLAN-9B-0 / 9B-1 | **Первый product-этап:** зафиксировано фактическое поведение до правки; произвольная тема получает несколько provider-ready queries без topic-hardcode, fail-closed сохранён. |
| PLAN-6A / 6D / 6E | Короткие единые правила с классами `[HARD]/[ARCH]/[HINT]`, приоритет цели над предписанным методом, технический scope-контроль и один независимый read-only reviewer, ловящий в том числе «unmet objective / premature stop». 6A параллелен; 6D — gate первого multi-owner слайса; 6E — gate первого destructive слайса, плюс PLAN-9A и PLAN-9C. |
| PLAN-6B / 6C | Ранний отчёт о мусоре и дублях с зафиксированными кандидатами fitness-проверок; проверенная карта dependency/toolchain ownership. Параллельны product-работе. |
| PLAN-STAB-1…7 | Закрыт blocking stabilization gate: готовый финальный ролик переживает сбой и обычный resume; offline/paid граница fail-closed; явный rights-review не теряется; permissions ужесточены либо residual risk принят; current routing однозначен. |
| PLAN-STAB-8…17 | Обязательный stabilization backlog: честная docs freshness, один owner rights-словаря, timestamps, channel manifests, длительностей сцен, workspace/media-library, persisted round-trip, lock выполнения, CI baseline и целостный registry. Индивидуально PLAN-9B-2 не блокируют. |
| PLAN-7 | README и рабочие skills обучают только каноническому `python -m ai_youtube`; `COMMANDS.md` удалён без замены, canonical reference — `--help`; старые entrypoints пока лишь совместимы. |
| PLAN-8 | Отдельный `PRODUCT_PLAN.md` с приоритетами, evidence gates и roadmap двух engines; execution plan становится короче. |
| PLAN-9 | Честный источник сценария и канонический вход «исходный текст»; универсальные provider-ready queries без topic-hardcode; сохранение best-so-far, переносимое через resume; semantic evidence доходит до существующего decision layer и включается только opt-in. |
| PLAN-10 | Ограниченный и объяснимый search loop с ledger, stop reasons, pagination и adaptive budget; глобальная локальная библиотека сведена к одной capability с одной rights/provenance семантикой и сохранённым diversity reserve. |
| PLAN-11 | Проверенное offline M1 evidence на нескольких темах без новых платных Vision-вызовов и без ложных claims по Story Card; каталог не обещает несуществующий output. |
| PLAN-12 | Утверждённая модель владения документами (12E) фиксируется **до** любых archive/move; затем current docs содержат только актуальные знания, fixtures получают правильного владельца, а historical материалы находятся в archive. Порядок внутри этапа — последовательная цепочка `12E → 12A → 12B → 12C`. |
| PLAN-13 | Один владелец бизнес-логики на capability, один physical package root, один канонический CLI; классификация пяти групп root structure выполнена, решение о `resources/` принято по evidence, `docs/` свободен от production dependency. |
| PLAN-14 | Минимальный root allowlist, согласованные dependency/toolchain files и переносимый runtime workspace; сохранён отобранный representative corpus и versioned resources, disposable медиа удалено. |
| PLAN-15 | Финально доказанный чистый, понятный, переносимый offline-проект с честным catalog и закрытым cleanup registry. |

## Decisions and discoveries

Только новые факты, меняющие порядок или scope. Не журнал команд.

### Ревизия 2.1 плана, 2026-07-31

Источники: `CRITICAL_INPUT_SEARCH_DEEP_DIVE_2026-07-31.md` (контролируемые
offline-пробы под активным `network_guard`, ноль сети и денег),
`PROJECT_EXECUTION_PLAN_REVISION_2_1_PROPOSAL_2026-07-31.md` и
`SECONDARY_ARCHITECTURE_FINDINGS_DEEP_DIVE_2026-07-31.md`. При конфликте
Secondary Deep Dive исправляет Proposal 2.1.

- **[FACT]** единственный канал доставки provider-ready английского запроса —
  `visual_brief`, и заполняет его только topic-hardcode на одну тему. Следствие:
  произвольная тема получает ложный запрос, чрезмерное обобщение либо
  `translation_required`. Это CRITICAL-1 в исправленной формулировке: проблема
  **не** «ноль запросов» — отправляются **ложные** запросы, что хуже нуля.
- **[FACT]** `src/assets/semantic_selection/query_generator.py` **не участвует**
  в формировании remote-запросов; canonical boundary — `src/assets/
  query_adapter.py` (`build_scene_queries` / `build_slot_queries`). Allowed
  zone PLAN-9B ревизии 2 была ошибочной.
- **[FACT]** `Translator` / `def translate` / `to_english` — **0 commits** за всю
  историю: полноценного translate-слоя не существовало никогда, восстанавливать
  нечего. Английские `visual_keywords` в legacy `content/**` — **входные
  данные**, а не выход кода.
- **[FACT]** `topic → article["text"] == сама тема → thin input →
  LegacyTemplateScriptProvider → шесть фиксированных фраз →
  `script_validation == passed`; downstream не читает `script_warnings` /
  `fallback_reason`. Это CRITICAL-2. Как только CRITICAL-1 починят, шаблонный
  сценарий поедет в publish беспрепятственно, поэтому CRITICAL-2 идёт внутри
  той же цепочки PLAN-9B.
- **[FACT, исправлено 2026-08-01]** у `apps/news_to_short` **две** возможности
  вне явного контракта канонического `create`: (1) `--text` / `--text-file` —
  **именованный** source-text вход; функционально тот же downstream уже
  достижим как `create --pasted-script/--script-file` при default/legacy
  unspecified `content_input_mode`, поэтому PLAN-9B-5a даёт имя, валидацию и
  документацию, а не новый движок; (2) `--assets` — пользовательские ассеты при
  создании проекта (`NewsJob.user_assets`), **доказанного аналога в
  каноническом `create` нет**. Прежняя формулировка «единственная уникальная
  бизнес-возможность — `--text`/`--text-file`» **опровергнута**. PLAN-9B-5b не
  выполняется, пока не пройден capability parity check.
- **[FACT]** `ProviderQuery.source` попадает в persisted manifest, но схема
  типизирует сцены как свободные объекты без `enum`, поле не валидируется и
  **не имеет ни одного читателя**. E-2 закрыт: не schema-level change, tolerant
  reader не нужен. Байты манифеста при этом меняются → characterization 9B-0
  обязан зафиксировать `query_plan` до правки.
- **[FACT]** targeted, full и три smoke-команды исполнимы **сегодня** без
  PLAN-5 (проверено исполнением). PLAN-5 переведён в parallel для всех
  под-слайсов PLAN-9B.
- **[FACT]** зависимость `PLAN-6A → PLAN-6D` — **декларативная**: 6D-1/6D-2/6D-3
  не требуют, чтобы R1–R12 уже лежали в `AGENTS.md`.
- **[FACT]** synthetic-проба сменила выбранный asset через живой semantic
  ingestion seam. Формулировки «semantic не может влиять на selection» и
  «fingerprint запрещает rerank» **опровергнуты**: `_selection_fingerprint` —
  самопроверка. Проблема — платный Vision пишет результат поздно в review-
  манифест. Отдельно: `_semantic_visual_summary` жёстко пишет
  `semantic_rerank_enabled=False` — дефект отчётности.
- **[FACT]** double orchestration: ADR 0009 намеренно разделяет application и
  news pipeline ownership; вызовов 4–7 в зависимости от режима; реальный дефект
  — `and not stage` в `src/news/pipeline.py`, отключающий output-validated
  idempotency ADR 0006 в explicit-режиме, не покрытый ни одним тестом.
  Повторного платного TTS **нет** (несколько guard'ов + тесты). Severity
  снижена HIGH → MEDIUM.
- **[FACT]** LocalLibrary: один `media_index`, один rights-authority
  `apply_policy_to_candidate`, два matcher'а; legacy path использует ту же
  `search_local_assets`, что и канонический. Ровно два расхождения
  (`provenance`, `review_required`), ноль обратных. Формулировка «три
  независимых implementation» и аргумент про `RIGHTS_REFERENCE_ONLY`
  опровергнуты. **Новый дефект:** явный `review_required=True` может пройти
  канонический путь, потому что policy позднее сбрасывает исходный флаг —
  registry C50, класс `[HARD]`. Дополнительно: `duplicate_penalty` в
  `rank_local_assets` — мёртвый код.
- **[FACT]** provider registry: `local_library` не попадает в
  `ordered_providers`, таблицы корректно фильтруются по availability,
  `ProviderCapabilities.query_languages` перекрывает таблицу. Гипотеза «пять
  расходящихся реестров» **опровергнута**; PLAN-10B как owner конвергенции
  снят (E-5 закрыт отрицательно).
- **[FACT]** export: каталог объявляет 5 active targets, три production-owner
  согласованно работают с 3; `supported_export_targets` и `safe_zone_profile`
  имеют ноль production-читателей и в render decision не участвуют. Каталог —
  единственный outlier.
- **[FACT]** FFmpeg: concat выполняется с `-c:v copy` и **не перекодирует**;
  CRF 20 принадлежит duration-control mux и имеет документированную причину.
  Три lossy generations — при audio + ASS subtitles. Величина ущерба **никем не
  измерялась** — ни один аудит не рендерил.
- **[FACT]** subprocess-модулей, запускающих CLI мимо `network_guard`, на audit
  HEAD `adcbb19` — **12**, а не 7. Это measurement, не invariant.
- **[owner decision]** OD-11…OD-26, D-1, D-2, D-3 и E-13 приняты; см. «Owner
  decisions ревизии 2.1».
- **[owner decision]** PLAN-P0 не создаётся: evidence уже получено, тесты
  T1–T11 распределены по PLAN-9B слайсам.
- **[FACT]** `baseline_head` остаётся `fe2df5b`: ни один из трёх аудитов и ни
  ревизия 2.1 полный offline suite не запускали. Подменять `baseline_head`
  текущим HEAD запрещено до нового full baseline run в PLAN-4.

### Ревизия 2 плана, 2026-07-31

- **[FACT]** legacy content stack — `pipeline.py` → `src/legacy_pipeline/workflow.py`
  → 20 модулей корня `src/` (~4903 строки) — имеет **ровно одного**
  production-caller и 6 test-модулей из 112. `legacy/` (424 строки) не имеет ни
  одного Python-caller. Исключения, которые остаются: `src/media_library.py`
  (активный news-путь) и `src/utils.py` (`src/audio/tts/env.py`,
  `src/tts_providers/moss_tts_provider.py`). Это основание для раннего PLAN-L.
- **[FACT]** `src/legacy_pipeline/maintenance.py` — не legacy-генерация, а
  единственный CLI-доступ к visual-preview, semantic-backend,
  semantic-evaluation, semantic-visual, media-library и envato-manual;
  канонический CLI этих команд не имеет. Поэтому L2 обязателен до L3.
- **[FACT]** `channels/{psychology,quotes,survival,size_comparison}` и
  `content/survival/juliane_koepcke_001.json` читаются
  `tests/test_channel_profiles.py` и `tests/test_documentary_visual_engine.py` —
  это fixtures legacy-стека, а не user data. Registry N04 изменён.
- **[FACT]** `MOSS_TTS_Nano/` — цельный вендоренный сторонний репозиторий
  (собственные `pyproject.toml`, `venv/`, `tests/`, `finetuning/`, 45 `.exe`);
  активный `src/audio/tts/provider_manager.py` MOSS не регистрирует.
  **[INFERENCE]** после L3/L4 у него и у `src/tts_providers/` ноль callers.
  Делить на weights и vendor code нечего — OD-7 ретайрит целиком.
- **[FACT]** production-зависимость на `docs/implementation/openai_live_evaluation`
  — три строки `semantic_visual_evaluation_tooling.py:26,38,695` плюс
  `tests/test_semantic_decision_policy.py`. Синтетический генератор
  `_write_prepared_dataset` уже существует. Дефект зафиксирован как C31.
- **[FACT]** после L3 все пять оставшихся файлов `config/` активны, 8–21 caller
  каждый. Повода переносить каталог нет; открыты только `channels/`, `schemas/`
  и reusable templates.
- **[FACT]** `apps/news_to_short/main.py` — 83 строки собственного argparse,
  дублирующего флаги канонического `create`/`resume`; два других wrapper —
  8-строчные делегации. Registry K08 уточнён.
- **[FACT]** PLAN-6E был заблокирован невыполнимым предусловием: Codex не
  установлен, discovery-check выполнить нельзя, а 6E обязателен до PLAN-9A.
  Deadlock снят разделением Claude-части и Codex-части.
- **[FACT]** `src/assets/completion/` уже владеет лестницей выбора A–F,
  `blocking_reasons` и словарём состояний завершённости. Второй словарь
  (`PASS/DEGRADED/…`) не вводится: это создало бы второго canonical owner.
  Продуктовая дыра находится **выше по потоку** — см. «Продуктовая рамка
  PLAN-9 и PLAN-10».
- **[owner decision]** OD-1…OD-10 приняты; см. раздел «Owner decisions
  ревизии 2».
- **[owner decision]** порядок первых действий изменён: STEP 0 (перенос ревизии
  в этот файл и в registry) выполняется **до** PLAN-1D-routing, потому что 1D
  направляет будущих агентов именно сюда.
- **[FACT]** `baseline_head` остаётся `fe2df5b`: нового full baseline run не
  выполнялось. Смещение `current_checkpoint` с PLAN-1A на PLAN-1D-routing —
  следствие reorder, а не выполненной работы.

- **2026-07-30** targeted re-search ограничен одной фазой **на сцену**, а не на
  проект: `targeted_search_done` — локальная переменная
  `complete_scene_assembly` в `src/news/asset_scene_completion.py`, вызываемой
  из per-scene цикла `src/news/asset_manifest_builder.py`.
- **2026-07-30** `config/semantic_visual.json` содержит `enabled: false`,
  `backend: mock`, `semantic_rerank_enabled: false`; режим по умолчанию
  `analyse_and_report`. **Исправлено ревизией 2.1:** прежний вывод «semantic-слой
  существует, но не влияет на отбор» относился к **платному Vision-сервису** и в
  общем виде **опровергнут** — metadata-semantic слой является каноническим
  владельцем решения и может сменить выбранный asset. См. PLAN-9C.
- **2026-07-30** `src/assets/semantic_selection/vision_validator.py` —
  заглушка, безусловно возвращающая `vision_validation_enabled: False`;
  production-callers отсутствуют.
- **2026-07-30** `src/assets/semantic_selection/query_generator.py` содержит
  topic-specific hardcode под один субъект и литерал `"nature"` в atmospheric
  fallback. **Уточнено ревизией 2.1:** этот модуль **не участвует** в
  формировании remote-запросов; главный носитель topic-hardcode —
  `src/news/script_generator.py`, canonical boundary —
  `src/assets/query_adapter.py`.
- **2026-07-30** provider-поиск выполняется без pagination с жёстким лимитом
  результатов на пару provider × query.
- **2026-07-30** `LocalLibraryStockProvider` существует, но не зарегистрирован
  в `create_default_stock_providers`.
- **2026-07-30** production читает данные из
  `docs/implementation/openai_live_evaluation/` через
  `src/assets/semantic_visual_evaluation_tooling.py`; это семейство содержит
  active fixtures и не подлежит массовому untrack.
- **2026-07-30** в репозитории не найдено `.bat`, `.cmd`, `.ps1` и IDE
  launch-конфигураций; владелец подтвердил отсутствие личных внешних команд,
  но старые entrypoints до PLAN-1 и PLAN-13 не удаляются.
- **2026-07-30** нет настроенного remote; действующего CI и доказательств его
  запусков нет; workflow для этого клона выполниться не мог. Локальный запуск
  `full` является основной проверкой.
- **2026-08-05 [SUPERSEDED]** Оба факта выше устарели и не описывают текущее
  состояние. Приватный remote существует, `governance-reset`/`master`
  отправлены, `governance-reset` — default branch (OD-S-5). CI repair
  (`9f9b6f2`, `bcf6c2a`, `8ca755f`, `68acdb2`, `Plan-Step: PLAN-STAB-16`)
  вернул `.github/workflows/offline-tests.yml` в доказанно зелёное состояние:
  GitHub Actions run `31039985187`, `offline-tests / unittest` — success,
  1/1 checks, failures=0, errors=0. Локальный полный offline suite остаётся
  основной проверкой для non-CI-repair слайсов; для CI-репозитория теперь
  существует и независимое GitHub Actions подтверждение.
- **2026-07-30** PLAN-0 уже зафиксирован commit `4027269`; post-commit docs QA
  и `git diff --check` завершились с exit code 0, дерево чистое.
- **2026-07-30** текущий `AGENTS.md` всё ещё направляет rescue-задачу в master
  plan. Пока оба документа указывают C01, конфликт не меняет действие; перед
  переходом на PLAN-2 routing обязан быть исправлен PLAN-1D.
- **2026-07-30** `fast` runner отсутствует; поэтому он удалён из prerequisites
  PLAN-2/PLAN-3 и впервые появляется/проверяется в PLAN-5.
- **2026-07-30** `pyproject.toml` и `requirements.txt` повторяют direct runtime
  dependencies, а `requirements.lock` хранит resolved environment. Это
  кандидат ownership/convergence PLAN-14B, не основание удалять файл сейчас.
- **2026-07-30** `story_card_text_only_v1` требует переданный local
  `source_asset`; automatic asset search в этот workflow не подключён.
  Визуальные PLAN-9–PLAN-11 не считаются доказательством Story Card без
  отдельного workflow evidence.
- **2026-07-30** product sequence изменён: tolerant best-so-far persistence
  предшествует query expansion, pagination и semantic activation, чтобы новые
  попытки не могли терять уже найденный результат.
- **2026-07-30** minimalism QA выполняется дважды: ранний report-only baseline
  после test runner/governance и финальный gate после ownership/docs cleanup.
  Dependency/toolchain audit также перенесён до package consolidation.
- **2026-07-30** verification budget уточнён: targeted tests после каждого
  code slice; `full` — на shared boundaries и при закрытии крупных families,
  а не после каждого локального product leaf.
- **2026-07-30** governance-аудит от clean HEAD `2379444`: независимого
  reviewer в репозитории нет ни в какой форме — отсутствуют `.claude/agents/`,
  `.claude/skills/`, `.claude/commands/`, hooks, Codex-конфиг, git-hooks
  (в `.git/hooks` только samples), `.vscode`, `.idea`, `*.bat`, `*.cmd`, `*.ps1`.
- **2026-07-30** механизма scope-контроля нет: ничто не сравнивает allowlist
  задачи с фактическим `git diff --name-only`. Технически enforced сейчас ровно
  три вещи: `tools/qa/check_agent_docs.py`, deny-list `.claude/settings.json`
  и `tests/network_guard.py`. Остальные правила зависят от памяти модели.
- **2026-07-30** `skills/` не является `.claude/skills/`, поэтому Claude Code
  не загружает эти skills автоматически; они доступны только при ручном чтении
  файла. Codex-адаптер существует как `skills/*/agents/openai.yaml`.
- **2026-07-30** `docs/current/PRODUCT_EVIDENCE_GATE.md` имеет
  `status: historical_reference` внутри `docs/current/` — единственный такой
  файл. `tools.qa.check_agent_docs` проверяет три файла из семи в
  `docs/current/` и не проверяет активный execution plan.
- **2026-07-30** лестница PLAN-9B противоречила собственным разрешённым зонам:
  `src/assets/semantic_selection/query_generator.py` — 55 строк, возвращает
  только строки запросов, а ступени «локальная медиатека», «другой provider» и
  «разрешённый fallback» живут в `src/providers/registry.py`,
  `src/providers/local_library_provider.py` и
  `src/news/asset_scene_completion.py`. Реализовать их внутри слайса было
  невозможно без выхода за scope, и они пересекались с PLAN-10D. Три ступени
  перенесены к PLAN-10C как порядок эскалации; PLAN-9B оставлен только за
  генерацией запросов. **Уточнено ревизией 2.1:** граница «лестница
  заканчивается на генерации запросов» сохраняется, но сама allowed zone была
  ошибочной — canonical owner remote-запросов `src/assets/query_adapter.py`,
  а не `semantic_selection/query_generator.py`.
- **2026-07-30** `git diff --check` проверяет whitespace-ошибки и конфликтные
  маркеры и не сравнивает состояние дерева, поэтому не может доказать
  read-only поведение reviewer. PLAN-6E получил отдельную controlled read-only
  acceptance вместо недоказуемого требования.
- **2026-07-30** карта tracked-файлов под кандидатами protected paths:
  `projects/` — 0; `music/` — 1 `.gitkeep`; `assets/library`+`assets/cache` — 1
  example; `anime_factory/episodes/` — 1 `.gitkeep`; `outputs/` — 9 плановых
  JSON и отчёт; `manual_assets/` — 7, включая 3 versioned SVG; `channels/` — 19
  versioned; `content/` — 13 versioned. Поэтому `outputs/**` и
  `manual_assets/**` нельзя блокировать целиком, а `channels/**` и `content/**`
  нельзя блокировать вовсе. 79 из 112 тестовых модулей используют
  `TemporaryDirectory`/`mkdtemp` вне репозитория, поэтому repo-relative
  deny-list synthetic tempfile не задевает.

### Repository Foundation audit, 2026-07-31

Read-only bounded аудит каркаса (root, `docs`, agent infrastructure,
developer tooling, QA, dev config) от clean HEAD `4ca3655`. Каждая запись
имеет класс: **FACT** — проверено командой; **INFERENCE** — вывод, исполнением
не проверенный; **[ПРЕДП]** — не проверено вовсе; **DEFER** — evidence
недостаточно.

- **2026-07-31 [FACT]** аудит выполнен от `audit_head` `4ca3655`.
  `baseline_head` остаётся `fe2df5b`: полный offline suite на `4ca3655` не
  запускался, промежуточные commits docs-only. Происхождение измерения не
  переписывается без повторного full run.
- **2026-07-31 [FACT]** покрытие аудита: 183 tracked файла в scope, 61
  прочитан построчно, 108 проверены программно, 14 metadata-only, 1 исключён
  по security. **`docs/implementation` (96 файлов) построчно не читался**,
  `docs/audits` (9) и `docs/architecture` (5) прочитаны заголовками. Поэтому
  archive/move/delete внутри этих семейств — DEFER до PLAN-12B.
- **2026-07-31 [FACT]** `git ls-files -i -c --exclude-standard`: 9 tracked
  файлов совпадают с `.gitignore` — 8 × `outputs/*.json` и
  `assets/broll/.gitkeep`. Директорное правило `assets/broll/` обесценивает
  последующее `!assets/broll/.gitkeep`.
- **2026-07-31 [FACT]** `output/` и `tmp/` не покрыты `.gitignore`.
  `output/` содержит один файл — `output/pdf/PROJECT_EXECUTION_PLAN_mobile.pdf`,
  280 820 байт; `tmp/pdfs/` пуст. **[INFERENCE]** это generated artifact:
  имя и размер соответствуют рендеру активного плана, содержимое PDF не
  парсилось. Владелец подтвердил удаление; оно выполняется отдельно от
  commit, поскольку файлы untracked.
- **2026-07-31 [FACT]** `pipeline.py:9` импортирует `scripts.test_moss_voices`;
  `packages.find.include` не содержит `scripts*` при `py-modules=["pipeline"]`.
  **[INFERENCE]** non-editable install ломает `import pipeline` — `pip install .`
  не выполнялся, CI использует `--editable` и дефект не ловит.
  **Отдельный вопрос [DEFER]:** отсутствие `tools*` в wheel дефектом по
  умолчанию не является — сначала PLAN-6C определяет intended distribution
  boundary. Предварительно `tools/` остаётся вне wheel.
- **2026-07-31 [FACT]** `legacy/` (8 файлов) не имеет ни одного Python-caller
  repo-wide; ссылки только в `README.md` и historical docs. **[DEFER]**
  архивирование требует caller gate PLAN-L1: статический граф не доказывает
  отсутствия внешнего или строкового caller.
- **2026-07-31 [FACT]** link-checker по всем 100 tracked `.md`: 0 битых
  локальных ссылок. Hash-скан по всем 664 tracked: единственный содержательный
  exact-дубликат — `ai_youtube/__main__.py` == `src/ai_youtube/__main__.py`,
  то есть симптом двух package roots (C01/C11), а не удаляемый дубль.
  Остальные совпадения — 15 пустых `.gitkeep` и 3 корректных
  `apps/*/__main__.py` boilerplate.
- **2026-07-31 [FACT]** активный execution plan имеет **одну** входящую ссылку
  во всём репозитории — `CURRENT_STATE.md`. `AGENTS.md`, `START_HERE.md`,
  `CLAUDE.md` и `README.md` его не упоминают. Routing чинит PLAN-1D.
  `docs/architecture/visual_rendering_policy.md` — единственный документ,
  задающий визуальный quality bar, — имеет **ноль** входящих ссылок.
- **2026-07-31 [FACT]** `README.md` (405 строк) и `COMMANDS.md` (681 строка)
  не упоминают `ai_youtube` ни разу; `COMMANDS.md` содержит 49 упоминаний
  `src.content_creation.cli` и 24 × `pipeline.py`; `README.md` учит bare
  `python`/`pip` вопреки `AGENTS.md`. `docs/contracts/STAGE1_PUBLIC_CONTRACTS.md`
  называет `src.content_creation.cli` «current CLI» и до сих пор не входил ни
  в один slice — добавлен в зоны PLAN-7.
- **2026-07-31 [FACT]** Claude Code не обнаруживает корневой `skills/`
  автоматически: `.claude/` содержит только `settings.json`,
  `settings.local.json` и `scheduled_tasks.lock`. **[ПРЕДП]** утверждение
  «Codex обнаруживает эти skills через `skills/*/agents/openai.yaml`» **не
  проверено**: Codex в среде не установлен, discovery-check не выполнялся,
  tracked codex-конфигов нет. Наличие файла не является доказательством
  discovery. Различать четыре состояния: наличие файлов, manual loading,
  auto-discovery, actual invocation.
- **2026-07-31 [FACT]** три из шести `SKILL.md` учат
  `python -m src.content_creation.cli`, а `tools/qa/check_agent_docs.py`
  проверяет только frontmatter, локальные ссылки и `TODO` — команды внутри
  skills не проверяются. PLAN-7 чинит файлы, PLAN-6A добавляет проверку.
- **2026-07-31 [FACT]** `docs/current/PRODUCT_EVIDENCE_GATE.md` указывает в
  `source_paths` пять путей внутри gitignored `projects/`. Смена `status` его
  не чинит: файл обязан переехать (PLAN-12A).
- **2026-07-31 [FACT]** `docs/current/` — 2639 строк, из них 1616 (61%)
  приходится на два волатильных плановых документа. **[INFERENCE]** слияние
  `SYSTEM_MAP` + `ARCHITECTURE_BOUNDARY_MAP` + `docs/apps/` + `docs/contracts/`
  дало бы 793 строки до вычета перекрытий. Это **measurement**, а не gate:
  решения о создании отдельного owner принимаются по responsibility, readers,
  lifecycle, смешению контрактов, routing ambiguity и maintenance coupling.
  Число строк может подтверждать проблему, но само по себе новый файл не
  создаёт.
- **2026-07-31 [owner decision]** принято **направление B** модели владения
  документами; зафиксировано как PLAN-12E. Направление — ownership direction,
  не разрешение перемещать файлы. Обязательная последовательная цепочка
  внутри этапа: `12E → 12A → 12B → 12C`, каждое звено зависит от предыдущего.
- **2026-07-31 [FACT]** из восьми кандидатов на новых document owners
  (`RUNTIME_FLOWS`, `QUALITY_BAR`, `EVALUATION_STRATEGY`, `TESTING`,
  `RECOVERY_AND_RESUME`, `STATE_AND_SCHEMAS`, `SECURITY_AND_APPROVALS`,
  `RUNTIME_WORKSPACE`) сейчас не создаётся ни один:
  1 CONDITIONAL NEW OWNER CANDIDATE (`RUNTIME_FLOWS`, пять evidence gates),
  1 EXTRACT CANDIDATE (`QUALITY_BAR`), 2 EXTEND EXISTING OWNER
  (`TESTING` → `tools/qa/run_tests.py`, `STATE_AND_SCHEMAS` → `schemas/` и
  существующий индекс), 2 DEFER (`EVALUATION_STRATEGY`, `RECOVERY_AND_RESUME`),
  2 NOT NEEDED (`SECURITY_AND_APPROVALS` — уже имеет корректное трёхуровневое
  владение instruction + permission + test; `RUNTIME_WORKSPACE` — ADR 0002 +
  PLAN-14 + `CURRENT_STATE`). Ни один не запрещён заранее.

## Completion and archive policy

Пока PLAN-15 не закрыт, файл имеет `status: active`.

После полного выполнения программы:

1. Выполнить финальную проверку: `smoke`, `fast`, full offline, docs QA,
   canonical CLI smoke, `git diff --check`, проверку неизменности
   пользовательских данных и утверждённые product evidence gates.
2. Обновить `CURRENT_STATE.md`, `PRODUCT_PLAN.md` и `CLEANUP_REGISTRY.md`
   только если их фактическое состояние изменилось.
3. Сделать финальную версию этого файла со `status: completed`.
4. Переместить её в
   `docs/archive/handoff/PROJECT_EXECUTION_PLAN_<start-date>_<finish-date>.md`.
5. Удалить активный путь `docs/current/PROJECT_EXECUTION_PLAN.md`.
6. Удалить ссылки на активный план из `AGENTS.md`, `START_HERE.md`,
   `CURRENT_STATE.md` и других current-документов.

Новый активный план поверх завершённого не создаётся. Следующая крупная
программа при необходимости получает собственный `PROJECT_EXECUTION_PLAN.md`.
