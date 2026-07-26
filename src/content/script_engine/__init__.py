"""Script engine: one extensible way to write a script for any template.

Replaces the six hard-coded phrases and the fixed
``[3.5, 7.0, 10.0, 13.0, 10.0, 8.0]`` duration table that every news_to_short
video used to be assembled from.

    request  = ScriptRequest(source_kind=..., raw_text=..., constraints=...)
    outcome  = generate_script(request)          # -> ScriptGeneration
    script   = outcome.to_legacy_script()        # -> the script.json the pipeline stores

Providers behind one contract:

- ``deterministic_local`` - default; offline, free, reproducible; builds the script
  out of the source material itself;
- ``user_supplied`` - the user already wrote it; keeps their words;
- ``legacy_template`` - the previous generator, preserved for reproducibility and
  as the regression reference;
- ``llm`` - interface only. No API client, no key, no network on this stage.

The stored ``script.json`` format is extended, never replaced: see
``legacy_format``. A project created before this engine existed is read by
``from_legacy_script`` without migration.
"""

from __future__ import annotations

from .contract import (
    BaseScriptProvider,
    ScriptProvider,
    ScriptProviderCapabilities,
    ScriptProviderError,
    ScriptProviderInputError,
    ScriptProviderResponseError,
    ScriptProviderUnavailableError,
)
from .engine import ScriptGeneration, generate_script
from .legacy_format import from_legacy_script, to_legacy_script
from .models import (
    SCENE_ROLE_CTA,
    SCENE_ROLE_DEVELOPMENT,
    SCENE_ROLE_HOOK,
    SCENE_ROLE_PAYOFF,
    SCENE_ROLES,
    SCRIPT_SCHEMA_VERSION,
    SOURCE_KINDS,
    SOURCE_NARRATION_TEXT,
    SOURCE_RESEARCH,
    SOURCE_TOPIC,
    SOURCE_USER_SCRIPT,
    ScriptConstraints,
    ScriptRequest,
    ScriptResult,
    ScriptScene,
    ScriptValidationIssue,
    ScriptValidationResult,
)
from .registry import (
    DEFAULT_PROVIDER_ID,
    get_provider,
    list_capabilities,
    list_provider_ids,
    resolve_provider_id,
)
from .validation import validate_script

__all__ = [
    "DEFAULT_PROVIDER_ID",
    "SCENE_ROLES",
    "SCENE_ROLE_CTA",
    "SCENE_ROLE_DEVELOPMENT",
    "SCENE_ROLE_HOOK",
    "SCENE_ROLE_PAYOFF",
    "SCRIPT_SCHEMA_VERSION",
    "SOURCE_KINDS",
    "SOURCE_NARRATION_TEXT",
    "SOURCE_RESEARCH",
    "SOURCE_TOPIC",
    "SOURCE_USER_SCRIPT",
    "BaseScriptProvider",
    "ScriptConstraints",
    "ScriptGeneration",
    "ScriptProvider",
    "ScriptProviderCapabilities",
    "ScriptProviderError",
    "ScriptProviderInputError",
    "ScriptProviderResponseError",
    "ScriptProviderUnavailableError",
    "ScriptRequest",
    "ScriptResult",
    "ScriptScene",
    "ScriptValidationIssue",
    "ScriptValidationResult",
    "from_legacy_script",
    "generate_script",
    "get_provider",
    "list_capabilities",
    "list_provider_ids",
    "resolve_provider_id",
    "to_legacy_script",
    "validate_script",
]
