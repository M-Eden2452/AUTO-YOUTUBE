"""Canonical boundary контракта стокового провайдера и его типов ошибок.

``StockProvider`` — единственный контракт провайдера в репозитории (ADR 0008).
Всё, что умеет искать, показывать превью, разрешать лицензию и скачивать
материал, реализует именно его.

Responsibilities:
- протокол ``StockProvider``: ``capabilities``, ``search``, ``get_preview``,
  ``resolve_license``, ``download``, ``health_check``;
- формы запроса и контекста: ``AssetSearchRequest``, ``DownloadContext``,
  ``AssetPreview``, ``ProviderHealth``;
- иерархия ``ProviderError`` с машиночитаемыми ``code`` — configuration,
  authentication, rate limit, timeout, network, invalid response, no results,
  download failure, validation failure, ``LicenseReviewRequired``;
- ``ensure_license_allows_render`` — точка, где непрояснённые права
  превращаются в отказ, а не в тихое использование.

Does not own:
- реализации провайдеров и default набор — ``src.providers``;
- правила прав — ``src.assets.license_policy`` (сюда они только вызываются);
- модели ассета — ``src.assets.models``;
- HTTP, скачивание и валидацию файла — ``src.assets.http_client``,
  ``src.assets.download``;
- формирование строки запроса и порядок опроса — ``query_adapter``,
  ``scene_strategy``, ``provider_routing``.

Inputs: описание того, что нужно сцене — запрос, тип медиа, геометрия,
ориентация, ограничения и негативные термины.

Outputs: типы, на которых говорят все провайдеры и все вызывающие стороны;
persisted артефактов модуль не создаёт.

Important invariants:
- второй provider contract не создаётся; новый источник материала реализует
  этот протокол;
- ошибка провайдера классифицируется кодом и признаком ``retryable``, а не
  строкой сообщения;
- ``ensure_license_allows_render`` спрашивает политику, а не поля кандидата, и
  блокирует как ``review_required``, так и запрет рендера;
- ``resolve_license`` провайдера сообщает то, что известно источнику, и решением
  о правах не является.

See also: ``src/assets/README.md``,
``docs/adr/0008-canonical-provider-registry.md``, ``src/providers/__init__.py``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from .models import AssetCandidate, AssetLicense, DownloadedAsset, ProviderCapabilities


@dataclass
class AssetSearchRequest:
    query: str
    media_type: str = "video"
    target_aspect_ratio: str = "9:16"
    orientation_preference: str = "vertical"
    min_width: int = 720
    min_height: int = 1280
    max_results: int = 8
    scene_id: str = ""
    project_id: str = ""
    semantic_scene: dict[str, Any] = field(default_factory=dict)
    negative_terms: list[str] = field(default_factory=list)
    timeout_sec: float = 24.0
    diagnostics: dict[str, Any] = field(default_factory=dict)


@dataclass
class DownloadContext:
    project_id: str
    scene_id: str
    search_query: str = ""
    max_file_size_bytes: int = 500 * 1024 * 1024
    min_file_size_bytes: int = 1024
    timeout_sec: float = 60.0


@dataclass
class AssetPreview:
    candidate_id: str
    url: str = ""
    local_path: str = ""
    width: int = 0
    height: int = 0
    media_type: str = ""
    duration_sec: float = 0.0
    expected_content_type: str = ""
    expected_size_bytes: int = 0
    rendition: str = ""
    original_used: bool = False
    fallback_reason: str = ""


@dataclass
class ProviderHealth:
    provider: str
    configured: bool
    status: str = "unknown"
    message: str = ""


class ProviderError(RuntimeError):
    code = "provider_error"

    def __init__(self, message: str, *, provider: str = "", query: str = "", retryable: bool = False) -> None:
        super().__init__(message)
        self.provider = provider
        self.query = query
        self.retryable = retryable

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "provider": self.provider,
            "query": self.query,
            "retryable": self.retryable,
            "message": str(self),
        }


class ProviderConfigurationError(ProviderError):
    code = "configuration_error"


class ProviderAuthenticationError(ProviderError):
    code = "authentication_error"


class ProviderRateLimitError(ProviderError):
    code = "rate_limit"


class ProviderTimeoutError(ProviderError):
    code = "timeout"


class ProviderNetworkError(ProviderError):
    code = "network_error"


class ProviderInvalidResponseError(ProviderError):
    code = "invalid_response"


class ProviderNoResultsError(ProviderError):
    code = "no_results"


class ProviderDownloadError(ProviderError):
    code = "download_failure"


class ProviderValidationError(ProviderError):
    code = "validation_failure"


class LicenseReviewRequired(ProviderError):
    code = "license_review_required"


class StockProvider(Protocol):
    name: str

    def capabilities(self) -> ProviderCapabilities:
        ...

    def search(self, request: AssetSearchRequest) -> list[AssetCandidate]:
        ...

    def get_preview(self, candidate: AssetCandidate) -> AssetPreview:
        ...

    def resolve_license(self, candidate: AssetCandidate) -> AssetLicense:
        ...

    def download(self, candidate: AssetCandidate, destination: Path, context: DownloadContext) -> DownloadedAsset:
        ...

    def health_check(self) -> ProviderHealth:
        ...


def ensure_license_allows_render(candidate: AssetCandidate) -> None:
    from .license_policy import apply_policy_to_candidate

    decision = apply_policy_to_candidate(candidate)
    if decision.review_required or not decision.allowed_for_render:
        raise LicenseReviewRequired(
            f"Asset {candidate.asset_id} requires license review before render: {decision.reason}.",
            provider=candidate.provider,
            query=candidate.search_query,
            retryable=False,
        )
