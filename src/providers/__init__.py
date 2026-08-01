"""Реализации ``StockProvider`` и canonical registry автоматического набора.

Пакет владеет конкретными провайдерами и тем, какие из них создаются для
активного workflow. Сам контракт, модели ассета, политику прав, HTTP-клиент,
скачивание и валидацию владеет ``src.assets``: провайдеры их используют, а не
переопределяют (ADR 0008).

Публичные точки входа: ``registry.create_default_stock_providers`` и
``registry.environment_enabled``, классы провайдеров
(``PexelsStockProvider``, ``PixabayStockProvider``,
``WikimediaCommonsStockProvider``, ``NasaImageLibraryStockProvider``,
``InternetArchiveStockProvider``, ``LocalLibraryStockProvider``,
``EnvatoManualProvider``, ``FakeStockProvider``) и оставшиеся функции поиска,
сохранённые для совместимости.

Поток: registry читает окружение и создаёт доступный набор -> вызывающая
сторона опрашивает провайдеров в порядке, который определил
``src.assets.provider_routing`` -> провайдер возвращает ``AssetCandidate`` с
лицензией и provenance -> права решает ``src.assets.license_policy`` ->
скачивание и валидация выполняются общими средствами ``src.assets``.

Не владеет: контрактом и моделями ассета, политикой прав, порядком опроса
провайдеров, формированием строки запроса, отбором кандидатов, completion и
манифестом ассетов. Второй provider contract и второй registry не создаются;
news-сторона делегирует сюда, а не собирает свой набор.

Инварианты: каждый провайдер реализует полный ``StockProvider``; провайдер,
которому нужен API-ключ, без ключа не создаётся вовсе, а не возвращает молча
пустой результат, и остальных можно выключить флагом окружения; ни один
провайдер не решает вопрос прав сам —
``apply_policy_to_candidate`` остаётся авторитетом; ``FakeStockProvider`` и
``EnvatoManualProvider`` существуют для offline-путей и ручной поставки
материала и сетевого поиска за автора не выполняют.

Расширение: добавь модуль провайдера, реализуй контракт, зарегистрируй его в
``registry`` и опиши правило прав в ``config/license_policy.json``.

См. также: ``src/assets/README.md``, ``docs/adr/0008-canonical-provider-registry.md``,
``docs/current/SYSTEM_MAP.md``.
"""

from __future__ import annotations

from .fake_provider import FakeStockProvider
from .envato_manual_provider import EnvatoManualProvider
from .internet_archive_provider import InternetArchiveStockProvider
from .local_library_provider import LocalLibraryStockProvider
from .nasa_images_provider import NasaImageLibraryStockProvider
from .pexels_provider import PexelsStockProvider
from .pexels_provider import search_images as search_pexels_images
from .pexels_provider import search_videos as search_pexels_videos
from .pixabay_provider import PixabayStockProvider
from .pixabay_provider import search_images as search_pixabay_images
from .pixabay_provider import search_music as search_pixabay_music
from .pixabay_provider import search_videos as search_pixabay_videos
from .registry import create_default_stock_providers, environment_enabled
from .unsplash_provider import search_images as search_unsplash_images
from .wikimedia_commons_provider import WikimediaCommonsStockProvider

__all__ = [
    "EnvatoManualProvider",
    "FakeStockProvider",
    "InternetArchiveStockProvider",
    "LocalLibraryStockProvider",
    "NasaImageLibraryStockProvider",
    "PexelsStockProvider",
    "PixabayStockProvider",
    "WikimediaCommonsStockProvider",
    "create_default_stock_providers",
    "environment_enabled",
    "search_pexels_images",
    "search_pexels_videos",
    "search_pixabay_images",
    "search_pixabay_music",
    "search_pixabay_videos",
    "search_unsplash_images",
]
