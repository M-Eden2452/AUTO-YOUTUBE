from __future__ import annotations

import hashlib
import time
from pathlib import Path
from typing import Any, Callable

import requests

from .provider_contract import (
    ProviderAuthenticationError,
    ProviderDownloadError,
    ProviderError,
    ProviderInvalidResponseError,
    ProviderNetworkError,
    ProviderRateLimitError,
    ProviderTimeoutError,
)


DEFAULT_USER_AGENT = "AI-YouTube/0.2 provider-foundation"


class ProviderHttpClient:
    def __init__(
        self,
        *,
        session: Any | None = None,
        user_agent: str = DEFAULT_USER_AGENT,
        timeout: float = 24.0,
        max_retries: int = 3,
        backoff_base: float = 0.4,
        sleep: Callable[[float], Any] = time.sleep,
    ) -> None:
        self.session = session or requests.Session()
        self.user_agent = user_agent
        self.timeout = timeout
        self.max_retries = max(1, int(max_retries))
        self.backoff_base = max(0.0, float(backoff_base))
        self.sleep = sleep

    def get_json(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        response = self._request("GET", url, headers=headers, params=params, timeout=timeout)
        try:
            data = response.json()
        except ValueError as exc:
            raise ProviderInvalidResponseError(f"Invalid JSON response from {url}") from exc
        if not isinstance(data, dict):
            raise ProviderInvalidResponseError(f"JSON response from {url} is not an object.")
        return data

    def download_stream(
        self,
        url: str,
        target: str | Path,
        *,
        allowed_content_types: set[str] | None = None,
        max_bytes: int = 500 * 1024 * 1024,
        min_bytes: int = 1024,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        target_path = Path(target)
        part_path = target_path.with_suffix(target_path.suffix + ".part")
        last_error: ProviderError | None = None
        for attempt in range(1, self.max_retries + 1):
            response = None
            try:
                response = self._request("GET", url, timeout=timeout, stream=True)
                content_type = str(response.headers.get("Content-Type") or "").split(";", 1)[0].strip().lower()
                if allowed_content_types and content_type and content_type not in {item.lower() for item in allowed_content_types}:
                    raise ProviderDownloadError(f"Unexpected content type for download: {content_type}")
                content_length = _int_header(response.headers.get("Content-Length"))
                if content_length and content_length > max_bytes:
                    raise ProviderDownloadError(f"Download is too large: {content_length} bytes.")
                target_path.parent.mkdir(parents=True, exist_ok=True)
                if part_path.exists():
                    part_path.unlink()
                sha = hashlib.sha256()
                total = 0
                with part_path.open("wb") as handle:
                    for chunk in response.iter_content(chunk_size=1024 * 512):
                        if not chunk:
                            continue
                        total += len(chunk)
                        if total > max_bytes:
                            raise ProviderDownloadError(f"Download exceeded maximum size: {max_bytes} bytes.")
                        sha.update(chunk)
                        handle.write(chunk)
                if total < min_bytes:
                    raise ProviderDownloadError(f"Downloaded file is too small: {total} bytes.")
                part_path.replace(target_path)
                return {"path": str(target_path), "bytes": total, "checksum_sha256": sha.hexdigest(), "content_type": content_type}
            except (requests.Timeout, requests.ConnectionError) as exc:
                last_error = ProviderNetworkError(str(exc), retryable=True)
            except ProviderError as exc:
                last_error = exc
                if not exc.retryable:
                    self._cleanup_part(part_path)
                    raise
            finally:
                if response is not None and hasattr(response, "close"):
                    response.close()
            self._cleanup_part(part_path)
            if attempt >= self.max_retries:
                break
            self.sleep(self._retry_delay(attempt, None))
        self._cleanup_part(part_path)
        if last_error:
            raise ProviderDownloadError(str(last_error), retryable=last_error.retryable) from last_error
        raise ProviderDownloadError(f"Download failed: {url}")

    def _request(self, method: str, url: str, **kwargs: Any) -> Any:
        headers = dict(kwargs.pop("headers", {}) or {})
        headers.setdefault("User-Agent", self.user_agent)
        timeout = kwargs.pop("timeout", None) or self.timeout
        last_error: ProviderError | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.session.request(method, url, headers=headers, timeout=timeout, **kwargs)
            except requests.Timeout as exc:
                last_error = ProviderTimeoutError(str(exc), retryable=True)
                if attempt >= self.max_retries:
                    break
                self.sleep(self._retry_delay(attempt, None))
                continue
            except requests.ConnectionError as exc:
                last_error = ProviderNetworkError(str(exc), retryable=True)
                if attempt >= self.max_retries:
                    break
                self.sleep(self._retry_delay(attempt, None))
                continue
            status = int(getattr(response, "status_code", 0) or 0)
            if 200 <= status < 300:
                return response
            if status in {401, 403}:
                raise ProviderAuthenticationError(f"Provider authentication failed with HTTP {status}.")
            if status == 429:
                last_error = ProviderRateLimitError(f"Provider rate limit exceeded with HTTP {status}.", retryable=True)
                if attempt >= self.max_retries:
                    break
                self.sleep(self._retry_delay(attempt, getattr(response, "headers", {}).get("Retry-After")))
                continue
            if 500 <= status <= 599:
                last_error = ProviderNetworkError(f"Provider returned HTTP {status}.", retryable=True)
                if attempt >= self.max_retries:
                    break
                self.sleep(self._retry_delay(attempt, None))
                continue
            raise ProviderInvalidResponseError(f"Provider returned non-retryable HTTP {status}.")
        if last_error:
            raise last_error
        raise ProviderNetworkError(f"Provider request failed: {url}")

    def _retry_delay(self, attempt: int, retry_after: Any) -> float:
        parsed = _parse_retry_after(retry_after)
        if parsed is not None:
            return parsed
        return self.backoff_base * (2 ** max(0, attempt - 1))

    @staticmethod
    def _cleanup_part(path: Path) -> None:
        try:
            if path.exists():
                path.unlink()
        except OSError:
            return


def _parse_retry_after(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return max(0.0, float(value))
    except (TypeError, ValueError):
        return None


def _int_header(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0

