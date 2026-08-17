"""One place where a test declines candidate-preview materialisation.

Materialising a candidate preview is ffmpeg work: production runs one subprocess per
shortlisted candidate, and a test that drives the whole pipeline pays for all of them
even when it asserts nothing about a preview.

Production already has the switch for it - ``visual_preview.enabled`` - but no request
field reaches it: ``src/news/asset_manifest_builder.py`` calls
``load_visual_preview_config()`` with no argument, so the value always comes from
``config/visual_preview.json`` at a fixed repository path. Flipping that one switch at
its single loading point is therefore the only way a test can decline previews without
editing the repository's own configuration. This module exists so that the modules
doing it share one seam and one reason instead of one copy each.

It changes what a test pays for, never what a test asserts: production still builds the
visual plan, the provider queries, the candidates, the selection and every persisted
manifest. A test that asserts something *about* a preview must not use this.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any
from unittest.mock import patch

from src.assets.visual_preview import load_visual_preview_config

# The single point where the builder reads the switch.
_CONFIG_SEAM = "src.news.asset_manifest_builder.load_visual_preview_config"


def _config_with_materialisation_off() -> dict[str, Any]:
    """The real configuration, with its own ``enabled`` switch turned off."""

    config = load_visual_preview_config()
    config["enabled"] = False
    return config


@contextmanager
def previews_not_materialised() -> Iterator[None]:
    """Block form, for a test that runs production inside a ``with``."""

    with patch(_CONFIG_SEAM, _config_with_materialisation_off):
        yield


def decline_preview_materialisation(test: Any) -> None:
    """``setUp`` form: the switch stays off for one test and is restored after it."""

    patcher = patch(_CONFIG_SEAM, _config_with_materialisation_off)
    patcher.start()
    test.addCleanup(patcher.stop)
