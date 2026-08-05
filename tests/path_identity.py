from __future__ import annotations

import os
from pathlib import Path


def resolved(path: str | os.PathLike[str]) -> str:
    """Return a comparable physical-identity form of ``path``.

    The same directory can surface through different string representations
    on Windows - e.g. the 8.3 short name ``RUNNER~1`` that ``tempfile``
    reports for a GitHub Actions runner's ``%TEMP%`` directory versus the
    long name ``runneradmin`` that ``Path.resolve()`` elsewhere returns for
    the identical directory - even though both name the same file.
    ``Path.resolve()`` reconciles both forms to one canonical path, and
    ``os.path.normcase`` neutralizes Windows' case-insensitive drive and
    segment casing so two resolved paths compare equal.
    """
    return os.path.normcase(str(Path(path).resolve(strict=False)))
