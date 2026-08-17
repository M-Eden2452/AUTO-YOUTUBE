# ADR 0018: Automation is chosen per stage in the channel template, not fixed in the pipeline

Date: 2026-08-17

Status: accepted as the target shape of the human review boundary; no capability
was enabled by this decision

## Context

On 2026-08-16 the owner stated an architectural requirement that neither product
questionnaire had asked about, and that changes how a third of their answers
read (recorded as the guiding principle of
`docs/audits/PRODUCT_INTERVIEW_MERGED_2026-08-16.md`, and illustrated by the
owner's own first-day scenario in the same document):

> Every stage of the pipeline must offer a choice instead of one hardwired
> behaviour. Free or paid. Manual or automatic. Checked by a human or trusted to
> the machine. The choice is made once, when the channel template is created —
> not asked again on every run.

The reason the owner gave is not hesitation about the product: full unattended
automation can produce bad quality in a niche where the engine has not proved
itself yet, so the switch is a structural replacement of manual checking
*everywhere* with manual checking *where the owner has not yet delegated it*.
Three positions were named for every such switch:

1. **full trust** — no checking, the stage runs unattended;
2. **selective control** — the owner picks the stages where the run stops;
3. **manual input** — the owner performs that stage himself, the rest is the
   application's work.

Half of this already exists, hardwired at one point. Paid voice-over stops the
run and waits for approval (`prepared_awaiting_paid_approval`, produced by the
fullscreen-voiceover use case and rendered as a paid step by the wizard); resume
and force-stage let a run continue from where a human left it; the completion
modes already separate "good enough for a draft" from "good enough to publish"
(`strict` and the opt-in `draft_complete`). What is missing is not the pattern
but its generality: today it is one stage, chosen by the code, and there is no
place where an owner records which stages he wants stopped for his channel.

## Decision

- Automation level is **not one global setting**. Each pipeline stage carries a
  choice along the three axes the owner named: free or paid, manual or
  automatic, human-checked or machine-trusted.
- Each such switch has exactly the three positions above: full trust, selective
  control, manual input.
- The switches are configured **once per channel template** and reused by every
  run of that channel. They are not a questionnaire at launch time; the default
  state is collapsed and behaves the way the pipeline behaves today, so an owner
  who wants to change nothing sees nothing.
- This is an **extension of the existing human review boundary to per-stage
  granularity** — the approval files, resume/force-stage and the existing
  completion modes — and nothing else. It is explicitly **not** a third
  completion ladder and **not** a second vocabulary of states;
  `docs/current/PRODUCT_PLAN.md` section 12 forbids both, and that prohibition
  stands unchanged.
- The paid voice-over approval gate is the existing instance of this pattern.
  The target is to parameterize that one gate so any stage can occupy it, not to
  copy it once per stage.
- A switch set to "paid" or "automatic" is **not** permission to spend or to go
  online. The existing preflight, cost estimate and paid-approval boundary stay
  exactly where they are, and network and payment remain two separate owner
  decisions.
- No public names — of the switches, their positions, the config keys or the CLI
  surface — are fixed by this decision. They are a public-surface tripwire and
  belong to the implementation slice that first needs them.
- This decision enables no capability, schedules no slice and creates no
  PLAN-ID. It records the shape the human review boundary must grow into, so
  that the next slice touching approvals does not invent a parallel one.

## Relationship to earlier decisions

The switch mechanism must live inside the owners that already exist: the
completion-mode vocabulary in `src/assets/completion/`, the approval and resume
mechanics of the active workflow, and the channel configuration. The channel
side is known to be weak today — several channel forms coexist and part of
`channel_config.json` is not read by any code — so the first slice that
implements a switch strengthens the existing channel contract rather than adding
a fourth form of a channel.

## Consequences

- No production code, config schema, CLI command, catalog status or runtime
  project changes in this decision.
- Any future stage that wants to stop for a human reuses the generalized
  approval gate. A new stage-specific stop flag is a defect, not a feature.
- The completion vocabulary does not grow. A switch decides **whether a human is
  asked**, never **what "done" means**; the answer to the second question stays
  with the existing completion modes.
- Product statements that assume one global automation level — "how much human
  work per video" among them — become channel-dependent and must be read that
  way.
- The weakest part is the channel template itself. Until the channel forms are
  reduced to one that the code actually reads, a per-stage switch has nowhere
  durable to live; that ordering is a prerequisite, not a detail.

## Verification

Read-only, on this HEAD. The existing pieces named above were checked in code
before being described as existing: `prepared_awaiting_paid_approval` in
`src/ai_youtube/apps/content_creator/workflows/fullscreen_voiceover/use_case.py:367`
and its paid classification in `src/content_creation/wizard_presentation.py:58`;
the completion modes in `src/assets/completion/modes.py:64-66`. No code, tests,
config, schemas or runtime projects were changed; no network, provider, TTS,
Vision or render call was made.
