"""Canonical boundary разрешения рантайм-доступа в сеть (PLAN-STAB-4).

Единственное место, которое решает, разрешено ли конкретное сетевое действие в
текущем прогоне. Проверка выполняется **до** первого socket/HTTP-вызова, а
разрешение выдаётся один раз наверху — из явного пользовательского ввода.

Responsibilities:
- ``NETWORK_ACTIONS`` — закрытый словарь классов сетевых действий;
- ``NetworkApproval`` — что именно разрешил пользователь и кто это выдал;
- ``network_approval_scope`` — установка разрешения на время одного прогона;
- ``require_network`` — единственная проверка, вызываемая с call sites;
- ``NetworkAccessDeniedError`` — классифицированный отказ с безопасным
  следующим действием.

Does not own:
- платные разрешения: озвучка — ``src.audio.voice_workflow.VoiceApproval`` и
  ``src.audio.tts.provider_manager``; OpenAI Vision — ``VisionBudgetGuard`` в
  ``src.assets.semantic_visual_openai``; текстовая модель смыслового брифа —
  ``src.content.semantic_brief_openai.paid_call_blockers``. Network approval их
  не заменяет и не выдаёт: разрешение на оплату и разрешение на сеть — разные
  вещи, и ``semantic_brief`` открывает только сеть;
- права на медиа — ``src.assets.license_policy``;
- сам HTTP, retry, timeout и валидацию скачанного — ``src.assets.http_client``
  и ``src.assets.download``;
- состав набора провайдеров — ``src.providers.registry``;
- разбор аргументов и сборку запроса — ``src.content_creation.commands.content``
  и ``src.content_creation.request_builder``.

Inputs: список имён классов действий, выбранных пользователем.

Outputs: разрешение или ``NetworkAccessDeniedError``. Модуль не создаёт файлов,
не читает окружение и не обращается в сеть сам.

Important invariants:
- **default deny**: значение ``ContextVar`` по умолчанию — ``DENY_ALL``, поэтому
  отсутствие явного разрешения всегда означает отказ, а не «разрешено»;
- наличие API-ключа, включённый по умолчанию провайдер, запущенный preflight,
  ``resume`` и ``--force-stage`` разрешением **не являются** — единственный
  источник разрешения здесь один, и это явный ввод пользователя;
- неизвестное имя класса действия — ошибка, а не молчаливое разрешение;
- разрешение выдаётся поимённо: одобренный класс не открывает соседние;
- ``to_dict`` отдаёт только имена классов и метку источника, поэтому в
  manifests и approval artifacts не может попасть ключ, токен или URL с
  параметрами.

See also: ``docs/current/PROJECT_EXECUTION_PLAN.md`` (PLAN-STAB-4),
``src/assets/http_client.py``, ``src/news/article_ingestor.py``,
``src/audio/tts/elevenlabs_provider.py``.
"""

from __future__ import annotations

import contextlib
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Iterable, Iterator


NETWORK_ACTION_PROVIDER_SEARCH = "provider_search"
NETWORK_ACTION_ASSET_DOWNLOAD = "asset_download"
NETWORK_ACTION_PREVIEW_DOWNLOAD = "preview_download"
NETWORK_ACTION_ARTICLE_FETCH = "article_fetch"
NETWORK_ACTION_VOICE_PREFLIGHT = "voice_preflight"
NETWORK_ACTION_SEMANTIC_BRIEF = "semantic_brief"

# Порядок фиксирован: он же используется как порядок `choices` в CLI и в
# сообщениях об отказе, поэтому подсказка пользователю стабильна.
NETWORK_ACTIONS: tuple[str, ...] = (
    NETWORK_ACTION_PROVIDER_SEARCH,
    NETWORK_ACTION_ASSET_DOWNLOAD,
    NETWORK_ACTION_PREVIEW_DOWNLOAD,
    NETWORK_ACTION_ARTICLE_FETCH,
    NETWORK_ACTION_VOICE_PREFLIGHT,
    NETWORK_ACTION_SEMANTIC_BRIEF,
)

NETWORK_ACTION_DESCRIPTIONS: dict[str, str] = {
    NETWORK_ACTION_PROVIDER_SEARCH: "Поиск ассетов у провайдеров (HTTP-запросы к их API).",
    NETWORK_ACTION_ASSET_DOWNLOAD: "Скачивание выбранного ассета.",
    NETWORK_ACTION_PREVIEW_DOWNLOAD: "Скачивание превью кандидатов для визуальной проверки.",
    NETWORK_ACTION_ARTICLE_FETCH: "Загрузка исходной статьи по URL.",
    NETWORK_ACTION_VOICE_PREFLIGHT: "Проверка аккаунта, голосов и моделей ElevenLabs (без генерации).",
    NETWORK_ACTION_SEMANTIC_BRIEF: (
        "Запрос к текстовой модели о смысле сцены для визуального брифа "
        "(без генерации сценария и без Vision). Разрешением на оплату не является."
    ),
}

DENIED_REASON = "network_approval_required"


class NetworkAccessDeniedError(PermissionError):
    """Отказ до выхода в сеть.

    ``action`` — класс запрошенного действия, ``reason`` — машиночитаемый тег
    для вызывающей стороны, ``next_action`` — готовая безопасная подсказка.
    """

    def __init__(self, action: str, *, detail: str = "") -> None:
        self.action = str(action or "")
        self.reason = DENIED_REASON
        self.detail = str(detail or "")
        self.next_action = f"--allow-network {self.action}"
        description = NETWORK_ACTION_DESCRIPTIONS.get(self.action, "")
        target = f" ({self.detail})" if self.detail else ""
        message = (
            f"Сетевое действие {self.action!r} не разрешено{target}. "
            f"{description} "
            f"Разрешите его явно: {self.next_action}. "
            "Наличие API-ключа или включённого по умолчанию провайдера "
            "разрешением не является."
        )
        super().__init__(" ".join(message.split()))


@dataclass(frozen=True)
class NetworkApproval:
    """Что именно разрешено в текущем прогоне.

    Пустой набор — полный запрет; это и есть значение по умолчанию.
    """

    actions: frozenset[str] = field(default_factory=frozenset)
    granted_by: str = ""

    def allows(self, action: str) -> bool:
        return str(action or "") in self.actions

    def to_dict(self) -> dict[str, object]:
        """Безопасное представление для manifests и evidence: только имена."""
        return {
            "actions": sorted(self.actions),
            "granted_by": self.granted_by,
        }


DENY_ALL = NetworkApproval()

_current_approval: ContextVar[NetworkApproval] = ContextVar(
    "ai_youtube_network_approval",
    default=DENY_ALL,
)


def approval_for_actions(
    actions: Iterable[str] | None,
    *,
    granted_by: str,
) -> NetworkApproval:
    """Собрать разрешение из явно названных классов действий.

    Неизвестное имя — ``ValueError``: опечатка в разрешении не должна тихо
    превращаться ни в «разрешено всё», ни в «разрешено молча ничего».
    """
    names = [str(item or "").strip() for item in (actions or ())]
    selected = [name for name in names if name]
    unknown = sorted({name for name in selected if name not in NETWORK_ACTIONS})
    if unknown:
        raise ValueError(
            "Unknown network action(s): "
            + ", ".join(unknown)
            + ". Known actions: "
            + ", ".join(NETWORK_ACTIONS)
            + "."
        )
    if not selected:
        return DENY_ALL
    return NetworkApproval(
        actions=frozenset(selected),
        granted_by=str(granted_by or ""),
    )


def current_network_approval() -> NetworkApproval:
    return _current_approval.get()


@contextlib.contextmanager
def network_approval_scope(approval: NetworkApproval | None) -> Iterator[NetworkApproval]:
    """Установить разрешение на время одного прогона и снять его после.

    Восстановление предыдущего значения выполняется через ``ContextVar`` token,
    поэтому вложенные scope и исключения не оставляют разрешение включённым.
    """
    active = approval or DENY_ALL
    token = _current_approval.set(active)
    try:
        yield active
    finally:
        _current_approval.reset(token)


def network_action_allowed(action: str) -> bool:
    return current_network_approval().allows(action)


def require_network(action: str, *, detail: str = "") -> None:
    """Единственная проверка перед выходом в сеть.

    Вызывать до открытия сокета, а не после получения ответа.
    """
    if action not in NETWORK_ACTIONS:
        raise ValueError(
            f"Unknown network action: {action!r}. Known actions: "
            + ", ".join(NETWORK_ACTIONS)
            + "."
        )
    if not current_network_approval().allows(action):
        raise NetworkAccessDeniedError(action, detail=detail)


__all__ = [
    "DENIED_REASON",
    "DENY_ALL",
    "NETWORK_ACTIONS",
    "NETWORK_ACTION_ARTICLE_FETCH",
    "NETWORK_ACTION_ASSET_DOWNLOAD",
    "NETWORK_ACTION_DESCRIPTIONS",
    "NETWORK_ACTION_PREVIEW_DOWNLOAD",
    "NETWORK_ACTION_PROVIDER_SEARCH",
    "NETWORK_ACTION_SEMANTIC_BRIEF",
    "NETWORK_ACTION_VOICE_PREFLIGHT",
    "NetworkAccessDeniedError",
    "NetworkApproval",
    "approval_for_actions",
    "current_network_approval",
    "network_action_allowed",
    "network_approval_scope",
    "require_network",
]
