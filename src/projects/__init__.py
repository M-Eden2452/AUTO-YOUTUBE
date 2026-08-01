"""Read-only view over every project on disk, whichever system created it.

Две публичные границы, каждая подробно описана в собственном модуле:

``repository.py``  общий read API поверх двух persisted форм — ``job.json``
                   (``src.news.project_store``) и ``project.json``
                   (``src.project_foundation``)
``rights.py``      отчёт о правах по манифестам, которые проект уже написал

Оба read-only. Writer сюда не добавляется, схемами и записью владеют
manifest owners, а политикой прав — ``src.assets.license_policy``. Третья
project-система не создаётся.

Карта владельцев — ``docs/current/SYSTEM_MAP.md``.
"""

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
