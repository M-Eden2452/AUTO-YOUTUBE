# ADR 0010: Story Card application boundary

## Status

Accepted on 2026-07-29 as the second vertical slice of rescue stage 8.

## Context

`src.content_creation.service` already delegated the
`story_card_text_only_v1` template to a separate application use case, but that
use case still lived beside the compatibility CLI and Wizard modules in
`src.content_creation`.

The working `project.json` model and writer are owned by
`src.project_foundation`, while evidence and Story Card render preparation are
owned by `src.project_foundation.evidence` and
`src.templates.story_card`. Moving or copying those implementations into the
application package would create competing contracts and exceed the bounded
vertical slice.

## Decision

- The canonical Story Card application boundary is
  `src.ai_youtube.apps.content_creator.workflows.story_card`.
- Its application-level orchestration lives in `story_card/use_case.py`.
- `src.content_creation.service` imports the canonical use case.
- `src.content_creation.story_card_use_case` remains a compatibility wrapper
  and re-exports the previous functions with the same objects and signatures.
- The boundary re-exports the existing `ProjectFactory`,
  `ProjectCreationResult`, `ProjectManifest`, `EvidenceBundle`,
  `EvidenceRecord`, and Story Card integration contracts. Their ownership
  remains in the existing modules; no duplicate writer, schema, evidence
  bundle, or renderer is introduced.
- The canonical CLI and Wizard continue to use
  `src.content_creation.service` as their single creation entrypoint.

## Compatibility and migration

Existing imports continue to work:

```python
from src.content_creation.story_card_use_case import create_story_card
from src.project_foundation.projects import ProjectFactory
from src.templates.story_card import prepare_story_card_render
```

New application code should import:

```python
from src.ai_youtube.apps.content_creator.workflows.story_card import (
    create_story_card,
)
```

`project.json`, evidence manifests/records, render requests, runtime projects,
and user media are unchanged and are not migrated.

## Consequences

1. Both active Content Creator workflows now have explicit canonical
   application boundaries.
2. The old Story Card use-case path remains compatible while callers migrate.
3. `src.project_foundation` and `src.templates.story_card` remain the sole
   owners of persisted project/evidence and renderer integration contracts.
4. Anime Clipper remains the next separate vertical slice of rescue stage 8.
5. No network, provider search/download, TTS, render, or paid action is
   required to verify this decision.

## Verification

```powershell
$env:PYTHONUTF8='1'
.\venv\Scripts\python.exe -m unittest tests.test_story_card_application_boundary tests.test_content_creation_service_internals_contract
.\venv\Scripts\python.exe -m unittest tests.test_content_creation_service.TemplateResolutionTests tests.test_content_creation_service.StoryCardCreateTests tests.test_content_creation_service.FullscreenVoiceoverCreateTests.test_progress_callback_is_invoked_for_story_card tests.test_project_factory tests.test_project_repository tests.test_artifact_schemas tests.test_story_card_provenance
.\venv\Scripts\python.exe -m compileall -q src/ai_youtube/apps/content_creator/workflows/story_card src/content_creation/story_card_use_case.py src/content_creation/service.py tests/test_story_card_application_boundary.py
```
