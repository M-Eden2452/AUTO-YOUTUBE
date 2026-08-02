---
name: review-change
description: Independently review an immutable commit, commit range, or explicitly supplied diff in AI-YouTube without changing the repository. Use after a bounded implementation or repair when scope, objective completion, contracts, tests, and safety need evidence-based review in a context separate from the implementer.
---

# Review Change

## Purpose

Review one explicit immutable change object independently from its implementer.
Find defects and unmet objectives; do not repair them.

## Inputs

Require all of the following before reviewing:

- the original objective and measurable success criteria;
- the allowed file scope and relevant repository contracts;
- exactly one immutable commit, commit range, saved diff, explicitly supplied
  diff, or synthetic diff in a temporary location.

Do not silently select an arbitrary working tree. If the object, objective, or
scope is ambiguous, return an unknown verdict and name the missing input.

## Mandatory independence

Run in a new context that did not implement the change. Treat implementer
conclusions as claims, not facts. Inspect the complete supplied object; do not
accept a convenient subset or hide changed paths.

## Read-only invariant

The reviewer must not:

- use Write, Edit, NotebookEdit, or another mutating file tool;
- fix a finding or change repository, index, plan, or checkpoint files;
- stage, commit, checkout, reset, clean, stash, move, or delete;
- perform network, provider, paid, download, Vision, TTS, render, or publish
  operations;
- read secrets, credentials, private keys, `.env`, or `.env.*`.

The launcher must set `GIT_OPTIONAL_LOCKS=0`, and every Git read must use the
explicit `git --no-optional-locks ...` form so status refreshes cannot rewrite
the index stat cache. Use Bash only for the minimum safe read-only
Git/search/test commands declared by the active adapter or controlled launcher.
A permitted shell is not a full sandbox: record it as a residual risk. The
launcher proves non-mutation by comparing HEAD, porcelain status, unstaged and
staged diffs, and `.git/index` before and after the review.

## Review dimensions

Check every applicable dimension and explicitly skip the rest with a reason:

- original objective, success criteria, and premature stop;
- allowed scope, unexpected paths, duplicate owner, and duplicated architecture;
- public CLI/API compatibility and error contracts;
- persisted bytes, schema, layout, tolerant readers, and migration;
- destructive behavior, user data, rights, provenance, and protected gates;
- network, paid, provider, download, Vision, TTS, render, and publish behavior;
- resume, cache, idempotency, rollback, and retirement pairing;
- tests, whether they fail without the implementation, and whether they test
  the claimed behavior rather than incidental structure;
- current docs, checkpoint truthfulness, unmet acceptance criteria, and
  out-of-scope regressions.

## Severity

Use only:

- `BLOCKER` — unsafe behavior, contract violation, false completion, mutation,
  or a defect that prevents acceptance;
- `MAJOR` — a material proven defect that makes the result unreliable but does
  not itself create immediate unsafe behavior;
- `MINOR` — a localized proven defect with limited impact.

Do not report style preferences or speculative risks as findings. Put
uncertainty in skipped checks or residual risks.

## Findings format

For every finding provide:

- severity;
- exact `file:line` or diff coordinate;
- evidence from the supplied object;
- impact;
- violated contract or unmet objective;
- smallest safe correction.

Sort findings by severity. An empty findings list is valid only after applicable
checks were performed.

## Final result

Return the complete structured result:

- findings;
- executed checks;
- skipped checks with reasons;
- residual risks;
- scope verdict: `PASS`, `FAIL`, or `UNKNOWN`;
- objective verdict: `PASS`, `FAIL`, or `UNKNOWN`;
- repository-unchanged observations supplied by the launcher or available from
  safe read-only checks.

Do not claim repository immutability from `git diff --check`; it only checks
whitespace and conflict markers.

## Repair cycle

The reviewer never repairs its finding. The implementer performs a separate
bounded repair after review. Review the repaired object in a new independent
context and produce a new complete result; do not continue the implementer
context or treat the earlier verdict as current.
