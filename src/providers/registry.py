"""Canonical boundary состава автоматического набора провайдеров (ADR 0008).

Единственное место, которое решает, какие ``StockProvider`` создаются для
активного workflow. Этап 7 (`fb93a05`) перенёс эту ответственность сюда из
news-границы; ``src.news.asset_provider_adapters.create_default_asset_providers``
сохранён как прежний patch-point и делегирует сюда.

Responsibilities:
- ``create_default_stock_providers`` — сборка набора по окружению;
- ``environment_enabled`` — единое чтение флага включённости провайдера.

Does not own:
- контракт ``StockProvider``, модели ассета, HTTP-клиент, скачивание и
  техническую валидацию — ``src.assets``;
- реализации самих провайдеров — соседние модули ``src.providers``;
- порядок опроса провайдеров — ``src.assets.provider_routing``;
- права и лицензии — ``src.assets.license_policy``;
- формирование строки запроса — ``src.assets.query_adapter``;
- ручные и offline-пути (``EnvatoManualProvider``, ``FakeStockProvider``,
  локальная библиотека): в автоматический набор они не входят.

Inputs: ``load_environment`` от вызывающей стороны и переменные окружения
``WIKIMEDIA_ENABLED``, ``NASA_IMAGES_ENABLED``, ``INTERNET_ARCHIVE_ENABLED``,
``PEXELS_API_KEY``, ``PIXABAY_API_KEY``.

Outputs: список готовых к использованию ``StockProvider``. Сеть при сборке не
выполняется — только чтение окружения.

Important invariants:
- провайдер, которому нужен API-ключ, без ключа **не создаётся вовсе**, а не
  создаётся и молча возвращает пустой результат;
- keyless-провайдеры включены по умолчанию и выключаются флагом окружения;
- набор состоит только из полных реализаций контракта; news-only
  compatibility-классы удалены в 9A D01 и не возвращаются;
- второй registry и второй provider contract не создаются;
- отсутствующая переменная означает значение по умолчанию, а не «выключено».

See also: ``src/providers/__init__.py``, ``src/assets/provider_contract.py``,
``docs/adr/0008-canonical-provider-registry.md``.
"""

from __future__ import annotations

import os
from typing import Any, Callable

from src.assets.provider_contract import StockProvider

from .internet_archive_provider import InternetArchiveStockProvider
from .nasa_images_provider import NasaImageLibraryStockProvider
from .pexels_provider import PexelsStockProvider
from .pixabay_provider import PixabayStockProvider
from .wikimedia_commons_provider import WikimediaCommonsStockProvider


def create_default_stock_providers(
    *,
    load_environment: Callable[[], Any],
) -> list[StockProvider]:
    """Create the canonical automatic provider set for active workflows."""

    load_environment()
    providers: list[StockProvider] = []
    if environment_enabled("WIKIMEDIA_ENABLED", default=True):
        providers.append(WikimediaCommonsStockProvider())
    if environment_enabled("NASA_IMAGES_ENABLED", default=True):
        providers.append(NasaImageLibraryStockProvider())
    if environment_enabled("INTERNET_ARCHIVE_ENABLED", default=True):
        providers.append(InternetArchiveStockProvider())

    pexels_key = os.getenv("PEXELS_API_KEY", "")
    if pexels_key:
        providers.append(PexelsStockProvider(pexels_key))

    pixabay_key = os.getenv("PIXABAY_API_KEY", "")
    if pixabay_key:
        providers.append(PixabayStockProvider(pixabay_key))
    return providers


def environment_enabled(name: str, *, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return str(value).strip().lower() not in {
        "0",
        "false",
        "no",
        "off",
        "disabled",
    }
