"""Argument-parser definitions for the active content_creator application.

The command implementations remain behind ``src.content_creation.cli`` during
the compatibility period. Keeping parser ownership here gives the canonical
dispatcher small, domain-specific command modules without moving workflow code.
"""

from . import authoring, catalog, content, projects

__all__ = ["authoring", "catalog", "content", "projects"]
