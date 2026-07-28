from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .http_client import ProviderHttpClient
from .license_policy import load_license_policy, policy_status_for_provider
from .provider_contract import AssetSearchRequest, ProviderError
from .provider_routing import route_providers
from src.providers.envato_manual_provider import EnvatoManualProvider
from src.providers.fake_provider import FakeStockProvider
from src.providers.internet_archive_provider import InternetArchiveStockProvider
from src.providers.local_library_provider import LocalLibraryStockProvider
from src.providers.nasa_images_provider import NasaImageLibraryStockProvider
from src.providers.pexels_provider import PexelsStockProvider
from src.providers.pixabay_provider import PixabayStockProvider
from src.providers.wikimedia_commons_provider import WikimediaCommonsStockProvider
from src.config_resolver.paths import repository_path


ENV_FILE = repository_path(".env")


def collect_provider_diagnostics(
    *,
    live: bool = False,
    timeout_sec: float = 5.0,
    provider: str | None = None,
) -> dict[str, Any]:
    policy = load_license_policy()
    env_values = _read_env_presence()
    routing = route_providers(
        {"scene_id": "diagnostics", "visual_type": "video", "primary_query": "cinematic nature historical NASA Earth observation"},
        provider_names=[spec["name"] for spec in _provider_specs()],
    )
    routing_priority = {name: index + 1 for index, name in enumerate(routing["ordered_providers"])}
    providers = [
        _diagnose_provider(
            spec=spec,
            env_values=env_values,
            policy=policy,
            live=live,
            timeout_sec=timeout_sec,
            routing_priority=routing_priority.get(spec["name"]),
        )
        for spec in _provider_specs()
    ]
    if provider:
        normalized = provider.strip().lower()
        aliases = {"nasa": "nasa_images", "internet-archive": "internet_archive", "wikimedia_commons": "wikimedia"}
        target = aliases.get(normalized, normalized)
        providers = [item for item in providers if item["provider"] == target]
    return {"live": live, "providers": providers}


def diagnostics_to_text(diagnostics: dict[str, Any]) -> str:
    return json.dumps(diagnostics, ensure_ascii=False, indent=2)


def _diagnose_provider(
    *,
    spec: dict[str, Any],
    env_values: dict[str, str],
    policy: dict[str, Any],
    live: bool,
    timeout_sec: float,
    routing_priority: int | None,
) -> dict[str, Any]:
    name = spec["name"]
    key_name = spec.get("key_name", "")
    key_configured = _is_configured(key_name, env_values) if key_name else False
    api_key_required = bool(key_name)
    configured = key_configured if api_key_required else True
    capabilities = spec["capabilities"]().to_dict() if callable(spec["capabilities"]) else dict(spec["capabilities"])
    policy_status = policy_status_for_provider(name, policy=policy)
    enabled = configured and bool(capabilities.get("supports_search") or capabilities.get("supports_download") or spec.get("manual_import"))
    live_status = _live_status(name, env_values, timeout_sec) if live else None
    health = live_status or {
        "status": "not_checked",
        "http_status": None,
        "message": "Offline diagnostics only. Pass --live for one small provider health request.",
    }
    user_agent_key = spec.get("user_agent_key", "")
    return {
        "provider": name,
        "enabled": enabled,
        "configured": configured,
        "api_key_required": api_key_required,
        "api_key_configured": key_configured,
        "key_configured": key_configured,
        "user_agent_configured": _is_configured(user_agent_key, env_values) if user_agent_key else False,
        "supported_media_types": capabilities.get("media_types", []),
        "search": bool(capabilities.get("supports_search", False)),
        "search_support": bool(capabilities.get("supports_search", False)),
        "preview": bool(capabilities.get("supports_preview", False)),
        "preview_support": bool(capabilities.get("supports_preview", False)),
        "download": bool(capabilities.get("supports_download", False)),
        "download_support": bool(capabilities.get("supports_download", False)),
        "manual_import": bool(spec.get("manual_import", False)),
        "license_support": bool(capabilities.get("supports_license_metadata", False)),
        "timeout": timeout_sec if live else 24,
        "retry_count": 1 if live else 3,
        "health_status": health.get("status", "unknown"),
        "live_status": health.get("status", "unknown"),
        "http_status": health.get("http_status"),
        "health_message": health.get("message", ""),
        "policy_status": policy_status["policy_status"],
        "policy_version": policy_status["policy_version"],
        "owner_approval_status": policy_status["owner_approval_status"],
        "owner_review_required": policy_status["owner_review_required"],
        "current_routing_priority": routing_priority,
    }


def _provider_specs() -> list[dict[str, Any]]:
    return [
        {"name": "wikimedia", "key_name": "", "user_agent_key": "WIKIMEDIA_USER_AGENT", "capabilities": lambda: WikimediaCommonsStockProvider(http=_offline_http()).capabilities()},
        {"name": "nasa_images", "key_name": "", "capabilities": lambda: NasaImageLibraryStockProvider(http=_offline_http()).capabilities()},
        {"name": "internet_archive", "key_name": "", "user_agent_key": "INTERNET_ARCHIVE_USER_AGENT", "capabilities": lambda: InternetArchiveStockProvider(http=_offline_http()).capabilities()},
        {"name": "envato_manual", "key_name": "", "manual_import": True, "capabilities": lambda: EnvatoManualProvider().capabilities()},
        {"name": "pexels", "key_name": "PEXELS_API_KEY", "capabilities": lambda: PexelsStockProvider("", http=_offline_http()).capabilities()},
        {"name": "pixabay", "key_name": "PIXABAY_API_KEY", "capabilities": lambda: PixabayStockProvider("", http=_offline_http()).capabilities()},
        {"name": "local_library", "key_name": "", "capabilities": lambda: LocalLibraryStockProvider(index={"version": 1, "items": []}).capabilities()},
        {"name": "fake", "key_name": "", "capabilities": lambda: FakeStockProvider().capabilities()},
    ]


def _offline_http() -> ProviderHttpClient:
    return ProviderHttpClient(timeout=1, max_retries=1)


def _read_env_presence() -> dict[str, str]:
    values: dict[str, str] = {}
    if ENV_FILE.exists():
        try:
            from dotenv import dotenv_values

            loaded = dotenv_values(ENV_FILE)
            values.update({key: str(value or "") for key, value in loaded.items() if key})
        except Exception:
            values = {}
    for key in (
        "PEXELS_API_KEY",
        "PIXABAY_API_KEY",
        "UNSPLASH_ACCESS_KEY",
        "WIKIMEDIA_API_BASE",
        "WIKIMEDIA_USER_AGENT",
        "NASA_IMAGES_API_BASE",
        "INTERNET_ARCHIVE_USER_AGENT",
    ):
        if os.getenv(key):
            values[key] = str(os.getenv(key) or "")
    return values


def _is_configured(key: str, env_values: dict[str, str]) -> bool:
    return bool(key and str(env_values.get(key) or "").strip())


def _live_status(name: str, env_values: dict[str, str], timeout_sec: float) -> dict[str, Any]:
    try:
        if name == "wikimedia":
            client = ProviderHttpClient(timeout=timeout_sec, max_retries=1)
            data = client.get_json(
                os.getenv("WIKIMEDIA_API_BASE") or "https://commons.wikimedia.org/w/api.php",
                params={"action": "query", "format": "json", "list": "search", "srnamespace": 6, "srsearch": "Moon", "srlimit": 1},
                timeout=timeout_sec,
            )
            count = len(data.get("query", {}).get("search", []))
            return {"status": "ok", "http_status": 200, "message": f"One Wikimedia File namespace search request returned {count} result(s); no media was downloaded."}
        if name == "nasa_images":
            client = ProviderHttpClient(timeout=timeout_sec, max_retries=1)
            data = client.get_json(
                (os.getenv("NASA_IMAGES_API_BASE") or "https://images-api.nasa.gov").rstrip("/") + "/search",
                params={"q": "Earth", "media_type": "image", "page_size": 1},
                timeout=timeout_sec,
            )
            count = len(data.get("collection", {}).get("items", []))
            return {"status": "ok", "http_status": 200, "message": f"One NASA Images search request returned {count} result(s); no asset rendition was downloaded."}
        if name == "internet_archive":
            client = ProviderHttpClient(timeout=timeout_sec, max_retries=1)
            data = client.get_json(
                os.getenv("INTERNET_ARCHIVE_SEARCH_BASE") or "https://archive.org/advancedsearch.php",
                params={"q": "(public domain educational film) AND mediatype:movies", "fl[]": ["identifier", "title"], "rows": 1, "page": 1, "output": "json"},
                timeout=timeout_sec,
            )
            count = len(data.get("response", {}).get("docs", []))
            return {"status": "ok", "http_status": 200, "message": f"One Internet Archive advanced search request returned {count} result(s); no item files were downloaded."}
        if name == "envato_manual":
            url = EnvatoManualProvider().search_url("documentary footage")
            return {"status": "ok", "http_status": None, "message": f"Public search URL generated only: {url}"}
        if name == "pexels":
            api_key = str(env_values.get("PEXELS_API_KEY") or "")
            if not api_key:
                return {"status": "missing_api_key", "http_status": None, "message": "PEXELS_API_KEY is not configured."}
            return _live_search_status(PexelsStockProvider(api_key, http=ProviderHttpClient(timeout=timeout_sec, max_retries=1)), query="test", media_type="image", timeout_sec=timeout_sec)
        if name == "pixabay":
            api_key = str(env_values.get("PIXABAY_API_KEY") or "")
            if not api_key:
                return {"status": "missing_api_key", "http_status": None, "message": "PIXABAY_API_KEY is not configured."}
            return _live_search_status(PixabayStockProvider(api_key, http=ProviderHttpClient(timeout=timeout_sec, max_retries=1)), query="test", media_type="image", timeout_sec=timeout_sec)
        if name in {"local_library", "fake"}:
            return {"status": "ready", "http_status": None, "message": "No external live request is required."}
    except Exception as exc:
        return {"status": "failed", "http_status": None, "message": str(exc)}
    return {"status": "skipped", "http_status": None, "message": "No live diagnostic implemented."}


def _live_search_status(provider: Any, *, query: str, media_type: str, timeout_sec: float) -> dict[str, Any]:
    try:
        candidates = provider.search(
            AssetSearchRequest(
                query=query,
                media_type=media_type,
                min_width=1,
                min_height=1,
                max_results=1,
                timeout_sec=timeout_sec,
            )
        )
    except ProviderError as exc:
        return {"status": exc.code, "http_status": None, "message": str(exc)}
    except Exception as exc:
        return {"status": "failed", "http_status": None, "message": str(exc)}
    return {"status": "ok", "http_status": 200, "message": f"Small search request returned {len(candidates)} candidate(s); no media was downloaded."}
