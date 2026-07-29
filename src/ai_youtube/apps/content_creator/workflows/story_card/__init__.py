"""Canonical Story Card application boundary.

The application use case lives here. Existing ``src.project_foundation`` and
``src.templates.story_card`` modules remain the owners of project, evidence,
and rendering contracts; they are re-exported rather than duplicated.
"""

from importlib import import_module


_USE_CASE_MODULE = (
    "src.ai_youtube.apps.content_creator.workflows.story_card.use_case"
)
_EXPORT_MODULES = {
    "EvidenceBundle": "src.project_foundation.evidence",
    "EvidenceRecord": "src.project_foundation.models",
    "ProjectCreationResult": "src.project_foundation.projects",
    "ProjectFactory": "src.project_foundation.projects",
    "ProjectManifest": "src.project_foundation.models",
    "STORY_CARD_CANONICAL_TEMPLATE_ID": "src.templates.story_card",
    "STORY_CARD_LEGACY_ALIASES": "src.templates.story_card",
    "STORY_CARD_SUPPORTED_FORMAT_ID": "src.templates.story_card",
    "StoryCardIntegrationError": "src.templates.story_card",
    "StoryCardIntegrationResult": "src.templates.story_card",
    "canonicalize_story_card_template_id": "src.templates.story_card",
    "create_story_card": _USE_CASE_MODULE,
    "prepare_story_card_render": "src.templates.story_card",
    "story_card_rerun_command": _USE_CASE_MODULE,
}


__all__ = [
    "EvidenceBundle",
    "EvidenceRecord",
    "ProjectCreationResult",
    "ProjectFactory",
    "ProjectManifest",
    "STORY_CARD_CANONICAL_TEMPLATE_ID",
    "STORY_CARD_LEGACY_ALIASES",
    "STORY_CARD_SUPPORTED_FORMAT_ID",
    "StoryCardIntegrationError",
    "StoryCardIntegrationResult",
    "canonicalize_story_card_template_id",
    "create_story_card",
    "prepare_story_card_render",
    "story_card_rerun_command",
]


def __getattr__(name: str):
    module_name = _EXPORT_MODULES.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(module_name), name)
    globals()[name] = value
    return value
