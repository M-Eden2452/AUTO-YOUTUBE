"""Canonical legacy-pipeline application boundary.

The root ``pipeline.py`` module remains the compatibility facade and namespace
owner. New application-boundary callers should use the lazy ``adapter`` module.
"""

__all__ = ["adapter"]
