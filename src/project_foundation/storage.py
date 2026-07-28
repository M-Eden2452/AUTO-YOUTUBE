from __future__ import annotations

from contextlib import contextmanager
import json
import os
import tempfile
import time
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from .models import ProjectFoundationError


PROJECT_LOCK_FILENAME = ".project.lock"
PROJECT_LOCK_STALE_AFTER_SECONDS = 5 * 60


class ProjectLockError(RuntimeError):
    """Raised when a project writer cannot acquire its exclusive lock."""


def ensure_dir(path: str | Path) -> Path:
    target = Path(path)
    target.mkdir(parents=True, exist_ok=True)
    return target


def _read_lock_token(lock_path: Path) -> str:
    try:
        payload = json.loads(lock_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return ""
    if not isinstance(payload, dict):
        return ""
    return str(payload.get("token") or "")


def _remove_stale_lock(lock_path: Path, *, stale_after_seconds: float) -> bool:
    try:
        observed_stat = lock_path.stat()
    except FileNotFoundError:
        return True

    age_seconds = time.time() - observed_stat.st_mtime
    if age_seconds <= stale_after_seconds:
        return False

    observed_token = _read_lock_token(lock_path)
    try:
        current_stat = lock_path.stat()
    except FileNotFoundError:
        return True
    if current_stat.st_mtime_ns != observed_stat.st_mtime_ns:
        return False
    if observed_token and _read_lock_token(lock_path) != observed_token:
        return False

    try:
        lock_path.unlink()
    except FileNotFoundError:
        pass
    except OSError:
        return False
    return True


def _release_owned_lock(lock_path: Path, token: str) -> None:
    if _read_lock_token(lock_path) != token:
        return
    try:
        lock_path.unlink()
    except FileNotFoundError:
        pass


@contextmanager
def project_lock(
    project_root: str | Path,
    *,
    stale_after_seconds: float = PROJECT_LOCK_STALE_AFTER_SECONDS,
) -> Iterator[Path]:
    """Acquire the fail-fast writer lock for one project.

    A lock younger than ``stale_after_seconds`` is treated as active. An older
    lock is considered abandoned and may be reclaimed. The owner token prevents
    a writer that lost an already-stale lock from deleting a newer owner's lock
    during cleanup.
    """

    if stale_after_seconds < 0:
        raise ValueError("stale_after_seconds must be zero or greater.")

    root = ensure_dir(project_root)
    lock_path = root / PROJECT_LOCK_FILENAME
    token = uuid.uuid4().hex
    payload = (
        json.dumps(
            {
                "token": token,
                "pid": os.getpid(),
                "created_at_unix": time.time(),
            },
            ensure_ascii=True,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")

    for attempt in range(2):
        try:
            descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc:
            if attempt == 0 and _remove_stale_lock(
                lock_path,
                stale_after_seconds=stale_after_seconds,
            ):
                continue
            raise ProjectLockError(
                f"Project {root.name!r} is locked for writing at {lock_path}. "
                f"Locks older than {stale_after_seconds:g} seconds are reclaimed automatically."
            ) from exc
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(payload)
        except BaseException:
            try:
                lock_path.unlink()
            except FileNotFoundError:
                pass
            raise
        break
    else:  # pragma: no cover - the two explicit attempts either acquire or raise
        raise ProjectLockError(f"Could not acquire project lock at {lock_path}.")

    try:
        yield lock_path
    finally:
        _release_owned_lock(lock_path, token)


def atomic_write_json(path: str | Path, data: dict[str, Any]) -> Path:
    """Write JSON deterministically (sorted keys off, insertion order kept) via temp file + os.replace."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=False) + "\n"

    fd, tmp_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=str(target.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(tmp_name, target)
    finally:
        if os.path.exists(tmp_name):
            os.remove(tmp_name)
    return target


def read_json(path: str | Path) -> dict[str, Any]:
    target = Path(path)
    try:
        raw = target.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ProjectFoundationError(f"Corrupted JSON file at {target}: {exc}") from exc
    if not isinstance(data, dict):
        raise ProjectFoundationError(f"Expected a JSON object at {target}, got {type(data).__name__}.")
    return data


def read_json_if_exists(path: str | Path) -> dict[str, Any] | None:
    target = Path(path)
    if not target.exists():
        return None
    return read_json(target)
