from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


SCENE_EXACT_SUBJECT = "exact_subject"
SCENE_EXACT_ACTION = "exact_action"
SCENE_ENVIRONMENT = "environment"
SCENE_RESEARCH_CONTEXT = "research_context"
SCENE_ABSTRACT_EXPLANATION = "abstract_explanation"
SCENE_TRANSITION = "transition"


@dataclass
class SemanticScene:
    scene_id: str = ""
    subject: list[str] = field(default_factory=list)
    secondary_subjects: list[str] = field(default_factory=list)
    action: list[str] = field(default_factory=list)
    environment: list[str] = field(default_factory=list)
    location: list[str] = field(default_factory=list)
    camera: list[str] = field(default_factory=list)
    mood: list[str] = field(default_factory=list)
    must_include: list[str] = field(default_factory=list)
    should_include: list[str] = field(default_factory=list)
    must_not_include: list[str] = field(default_factory=list)
    visual_priority: str = SCENE_EXACT_SUBJECT
    fallback_level: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "scene_id": self.scene_id,
            "subject": self.subject,
            "secondary_subjects": self.secondary_subjects,
            "action": self.action,
            "environment": self.environment,
            "location": self.location,
            "camera": self.camera,
            "mood": self.mood,
            "must_include": self.must_include,
            "should_include": self.should_include,
            "must_not_include": self.must_not_include,
            "visual_priority": self.visual_priority,
            "fallback_level": self.fallback_level,
        }
