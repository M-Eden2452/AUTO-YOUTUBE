from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from urllib.parse import urlparse

MAX_URL_LENGTH = 2048
SUPPORTED_SCRIPT_EXTENSIONS = {".txt", ".md"}
SUPPORTED_MUSIC_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"}

# Minimal, explicit rule set for the search engines named in the Stage 2E.1 spec.
# Intentionally simple (host substring + path prefix) rather than a general web
# crawler heuristic - it only has to catch obvious search-result URLs before any
# network call, not classify arbitrary pages.
_SEARCH_ENGINE_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("google.", ("/search",)),
    ("bing.com", ("/search",)),
    ("yandex.", ("/search",)),
    ("duckduckgo.com", ("", "/", "/html", "/html/")),
)


@dataclass
class ValidationResult:
    valid: bool
    reason: str = "ok"
    message: str = ""


def is_search_engine_url(url: str) -> bool:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    path = (parsed.path or "").lower()
    if not host:
        return False
    for host_needle, paths in _SEARCH_ENGINE_RULES:
        if host_needle not in host:
            continue
        if host_needle == "duckduckgo.com":
            return path in paths
        if any(path.startswith(prefix) for prefix in paths):
            return True
    return False


def validate_article_url(url: str) -> ValidationResult:
    """Pre-flight, no-network validation for an article URL.

    Must reject search-result URLs (google/bing/yandex/duckduckgo) and other
    obviously-invalid URLs *before* any request is made - see
    src.news.article_ingestor.ingest_article for what happens once a URL passes
    this check and a real HTTP request is attempted.
    """
    text = str(url or "").strip()
    if not text:
        return ValidationResult(False, "empty", "Ссылка не может быть пустой.")
    if len(text) > MAX_URL_LENGTH:
        return ValidationResult(False, "too_long", "Ссылка слишком длинная.")
    parsed = urlparse(text)
    if parsed.scheme not in ("http", "https"):
        return ValidationResult(False, "bad_scheme", "Ссылка должна начинаться с http:// или https://.")
    if not parsed.hostname:
        return ValidationResult(False, "no_host", "Не удалось определить домен в ссылке.")
    if is_search_engine_url(text):
        return ValidationResult(
            False,
            "search_engine_url",
            "Это ссылка на страницу поиска, а не на статью.",
        )
    return ValidationResult(True, "ok", "")


def validate_script_file(path: str) -> ValidationResult:
    text = str(path or "").strip()
    if not text:
        return ValidationResult(False, "empty", "Путь к файлу не может быть пустым.")
    file_path = Path(text)
    if not file_path.is_file():
        return ValidationResult(False, "not_found", f"Файл не найден: {text!r}.")
    if file_path.suffix.lower() not in SUPPORTED_SCRIPT_EXTENSIONS:
        return ValidationResult(
            False,
            "unsupported_extension",
            f"Неподдерживаемое расширение {file_path.suffix!r}. Поддерживаются: {sorted(SUPPORTED_SCRIPT_EXTENSIONS)}.",
        )
    try:
        file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return ValidationResult(False, "bad_encoding", "Файл не удалось прочитать как UTF-8.")
    except OSError as exc:
        return ValidationResult(False, "read_error", f"Не удалось прочитать файл: {exc}.")
    return ValidationResult(True, "ok", "")


def validate_visual_brief_file(path: str) -> ValidationResult:
    """One JSON file mapping scene -> visual brief. The only entry point for briefs.

    Rejected early and by message rather than by traceback, because this file is hand
    written: a typo in it must say what is wrong, not fail three stages later with an
    empty plan.
    """
    text = str(path or "").strip()
    if not text:
        return ValidationResult(False, "empty", "Путь к файлу visual brief не может быть пустым.")
    file_path = Path(text)
    if not file_path.is_file():
        return ValidationResult(False, "not_found", f"Файл не найден: {text!r}.")
    if file_path.suffix.lower() != ".json":
        return ValidationResult(False, "unsupported_extension", "Visual brief должен быть .json файлом.")
    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
    except UnicodeDecodeError:
        return ValidationResult(False, "bad_encoding", "Файл не удалось прочитать как UTF-8.")
    except json.JSONDecodeError as exc:
        return ValidationResult(False, "invalid_json", f"Некорректный JSON: {exc}.")
    except OSError as exc:
        return ValidationResult(False, "read_error", f"Не удалось прочитать файл: {exc}.")
    if not isinstance(data, dict):
        return ValidationResult(
            False, "invalid_shape", "Ожидается объект вида {\"1\": {...}} или {\"scene_001\": {...}}."
        )
    for key, value in data.items():
        if not isinstance(value, dict):
            return ValidationResult(
                False, "invalid_scene_brief", f"Бриф сцены {key!r} должен быть объектом, а не {type(value).__name__}."
            )
    return ValidationResult(True, "ok", "")


def load_visual_briefs(path: str) -> dict[str, dict]:
    """Read a validated visual brief file. Call ``validate_visual_brief_file`` first."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return {str(key): dict(value) for key, value in data.items() if isinstance(value, dict)}


def validate_music_path(path: str) -> ValidationResult:
    text = str(path or "").strip()
    if not text:
        return ValidationResult(False, "empty", "Для local_file нужен путь к аудиофайлу.")
    file_path = Path(text)
    if not file_path.is_file():
        return ValidationResult(False, "not_found", f"Файл не найден: {text!r}.")
    if file_path.suffix.lower() not in SUPPORTED_MUSIC_EXTENSIONS:
        return ValidationResult(
            False,
            "unsupported_extension",
            f"Неподдерживаемое расширение {file_path.suffix!r}. Поддерживаются: {sorted(SUPPORTED_MUSIC_EXTENSIONS)}.",
        )
    return ValidationResult(True, "ok", "")


def validate_pasted_script(text: str) -> ValidationResult:
    cleaned = str(text or "").strip()
    if not cleaned:
        return ValidationResult(False, "empty", "Текст сценария не может быть пустым.")
    return ValidationResult(True, "ok", "")
