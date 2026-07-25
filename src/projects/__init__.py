"""Read-only view over every project on disk, whichever system created it."""

from .repository import (
    PROJECT_KIND_NEWS_JOB,
    PROJECT_KIND_PROJECT_MANIFEST,
    PROJECT_KIND_UNKNOWN,
    ProjectNotFoundError,
    ProjectRepository,
    ProjectStage,
    ProjectView,
)
from .rights import (
    MEDIA_ROLE_MUSIC,
    MEDIA_ROLE_OTHER,
    MEDIA_ROLE_VISUAL,
    MEDIA_ROLE_VOICE,
    MissingSceneRecord,
    ProjectRightsReport,
    RightsItem,
    RightsSummary,
    build_rights_report,
)

__all__ = [
    "MEDIA_ROLE_MUSIC",
    "MEDIA_ROLE_OTHER",
    "MEDIA_ROLE_VISUAL",
    "MEDIA_ROLE_VOICE",
    "PROJECT_KIND_NEWS_JOB",
    "PROJECT_KIND_PROJECT_MANIFEST",
    "PROJECT_KIND_UNKNOWN",
    "MissingSceneRecord",
    "ProjectNotFoundError",
    "ProjectRepository",
    "ProjectRightsReport",
    "ProjectStage",
    "ProjectView",
    "RightsItem",
    "RightsSummary",
    "build_rights_report",
]
