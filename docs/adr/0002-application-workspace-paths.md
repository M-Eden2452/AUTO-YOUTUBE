# ADR 0002: Application workspace paths

## Status

Accepted on 2026-07-28; implemented by `0cd0e11`.

## Context

Production entrypoints resolved runtime and versioned paths independently. Several
depended on the process cwd or a developer-machine absolute path, while old projects
and outputs already existed under the repository root. Stage 3 requires arbitrary
workspaces without moving or invalidating those legacy artifacts.

## Decision

- Extend the existing `src.config_resolver` boundary with `WorkspacePaths` and
  `ApplicationPaths`; do not introduce another configuration system.
- Resolve the workspace in precedence order: explicit CLI value,
  `AI_YOUTUBE_WORKSPACE`, JSON path config, then the legacy repository root.
- Keep versioned application resources anchored to the repository.
- Resolve runtime projects, outputs, exports, artifacts, media, cache, temp and
  reports under the selected workspace.
- Read from the selected primary root before compatible legacy roots. New writes go
  only to the selected primary workspace.
- Keep an explicit `--projects-root` isolated and authoritative for compatibility.
- Do not physically move runtime files. Changing the default storage location remains
  a separate migration decision for rescue stage 9.

## Consequences

Entrypoints work independently of cwd and can use a temporary or external workspace.
Existing repository projects and outputs remain readable. Until migration is
explicitly approved, an unconfigured installation preserves its previous paths.

## Verification

Run the stage 3 path characterization and the affected CLI, repository, workflow and
integration tests with `.\venv\Scripts\python.exe`. Also invoke content capabilities
from a directory outside the repository and run:

```powershell
.\venv\Scripts\python.exe -m tools.qa.check_agent_docs
```
