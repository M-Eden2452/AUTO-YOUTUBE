"""Project / Channel / Evidence Foundation (Stage 2B).

Self-contained package: does not import pipeline.py, src.news, src.audio,
src.production_catalog, or src.production_plan.
"""

from .channels import ChannelRegistry
from .evidence import EvidenceBundle
from .models import (
    SCHEMA_VERSION,
    ChannelBranding,
    ChannelProfile,
    EvidenceRecord,
    EvidenceSummary,
    PROJECT_STATUSES,
    ProjectFoundationError,
    ProjectManifest,
    VERIFICATION_STATUSES,
)
from .policies import ChannelOutputPolicy, ValidationResult
from .policies import validate as validate_output_policy
from .projects import ProjectCreationResult, ProjectFactory

__all__ = [
    "SCHEMA_VERSION",
    "PROJECT_STATUSES",
    "VERIFICATION_STATUSES",
    "ProjectFoundationError",
    "ChannelBranding",
    "ChannelProfile",
    "ChannelRegistry",
    "ChannelOutputPolicy",
    "ValidationResult",
    "validate_output_policy",
    "ProjectManifest",
    "ProjectFactory",
    "ProjectCreationResult",
    "EvidenceRecord",
    "EvidenceSummary",
    "EvidenceBundle",
]
