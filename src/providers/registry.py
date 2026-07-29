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
