"""Content-level engines shared by every template (script, and later others).

Deliberately separate from ``src/news``: that package is the news_to_short
*pipeline*, while this one holds the format-agnostic building blocks a longform
template or the repurposer can reuse without importing a pipeline.
"""
