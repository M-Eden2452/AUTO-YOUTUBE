from __future__ import annotations

from pathlib import Path
from typing import Any

import requests

from .article_parser import extract_article_images, parse_article_html
from .models import INPUT_MODE_TEXT, INPUT_MODE_TOPIC, INPUT_MODE_URL, NewsJob


class ArticleIngestionError(RuntimeError):
    """reason is a short machine-readable tag consumed by
    src.content_creation.service to classify the failure for CLI/wizard callers
    (e.g. "http_429", "timeout", "connection_error", "empty_article",
    "invalid_content") without either side depending on `requests` types."""

    def __init__(self, message: str, *, reason: str = "unknown") -> None:
        super().__init__(message)
        self.reason = reason


def ingest_article(job: NewsJob, *, timeout_sec: int = 20) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if job.input_mode == INPUT_MODE_URL:
        if not job.source_urls:
            raise ArticleIngestionError("URL input mode requires at least one source URL.", reason="missing_url")
        url = job.source_urls[0]
        try:
            response = requests.get(url, timeout=timeout_sec, headers={"User-Agent": "AI-YouTube/0.1"})
            response.raise_for_status()
        except requests.exceptions.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else 0
            reason = {429: "http_429", 403: "http_403"}.get(status, f"http_{status}" if status else "http_error")
            raise ArticleIngestionError(f"Article request failed with HTTP {status}.", reason=reason) from exc
        except requests.exceptions.Timeout as exc:
            raise ArticleIngestionError("Article request timed out.", reason="timeout") from exc
        except requests.exceptions.ConnectionError as exc:
            raise ArticleIngestionError("Could not connect to the article URL.", reason="connection_error") from exc
        except requests.exceptions.RequestException as exc:
            raise ArticleIngestionError(f"Article request failed: {exc}", reason="request_error") from exc
        html = response.text
        if not html or not html.strip():
            raise ArticleIngestionError("Article response body was empty.", reason="empty_article")
        article = parse_article_html(url, html)
        if not str(article.get("text") or "").strip():
            raise ArticleIngestionError(
                "Could not extract article text from the page (it may be a redirect, "
                "login wall, or captcha page).",
                reason="invalid_content",
            )
        return article, extract_article_images(url, html)

    if job.input_mode == INPUT_MODE_TOPIC:
        article = _article_from_text(job.topic, job.topic, language=job.language, source_type="topic")
        return article, []

    if job.input_mode == INPUT_MODE_TEXT:
        title = job.topic or "User provided news text"
        article = _article_from_text(title, job.input_text, language=job.language, source_type="text")
        return article, []

    raise ArticleIngestionError(f"Unsupported input mode: {job.input_mode}")


def _article_from_text(title: str, text: str, *, language: str, source_type: str) -> dict[str, Any]:
    return {
        "url": "",
        "title": title,
        "text": text,
        "published_at": "",
        "author": "user" if source_type == "text" else "",
        "site_name": source_type,
        "language": language,
        "description": "",
        "links": [],
        "primary_source_candidate": "",
    }


def load_text_file(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")

