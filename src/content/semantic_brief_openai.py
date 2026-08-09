"""Один текстовый backend для смыслового брифа сцены, и обе двери перед ним.

``src.content.visual_planning.semantic_brief`` знает, *что спросить у модели* и *как
разобрать ответ*, и по-прежнему не знает ни одного SDK: он принимает вызов модели
инъекцией. Этот модуль — единственная реализация такого вызова и единственное место,
где живёт OpenAI SDK для текстовой модели. Направление зависимости одностороннее:
``visual_planning`` не импортирует ничего отсюда.

Responsibilities:
- ``SemanticBriefModelConfig`` — минимальная политика: backend, модель, лимиты, оплата;
- ``paid_call_blockers`` — платный gate, отдельный от сетевого;
- ``OpenAISemanticBriefBackend`` — вызов SDK и перевод его ожидаемых отказов в уже
  существующие ошибки ``semantic_brief``;
- ``build_semantic_brief_adapter`` — единственный способ получить работающий адаптер.

Does not own:
- контракт ответа модели и его парсер — ``visual_planning.semantic_brief``
  (``RESPONSE_CONTRACT``, ``parse_response``). Здесь схема запроса **выводится** из
  него, а не объявляется заново, поэтому разойтись они не могут;
- построение запроса к провайдеру — ``visual_planning.expansion``. Модель называет
  смысл, строки запросов по-прежнему собирает лестница расширения;
- разрешение на сеть — ``src.runtime_network``;
- Vision, отбор кандидатов и ранжирование — ``src.assets.*``.

Два разрешения, и ни одно не подразумевает другое:

- **сеть** — ``NETWORK_ACTION_SEMANTIC_BRIEF``, явный per-run ввод пользователя
  (``--allow-network semantic_brief``). Проверяется через общий ``require_network``
  непосредственно перед вызовом SDK, а не при сборке адаптера;
- **оплата** — стоящая политика в ``config/semantic_brief.json``: ``allow_paid_calls``,
  подтверждающая фраза, положительный потолок вызовов и денег. В репозитории всё это
  выключено, и наличие ``OPENAI_API_KEY`` разрешением не является.

Секрет читается только из окружения, только по факту наличия, и никогда не попадает ни
в конфиг, ни в отчёт, ни в текст ошибки.

Ретраев нет: клиент создаётся с ``max_retries=0``, бюджет расходуется *до* вызова,
поэтому упавший платный запрос не может быть повторён молча.

See also: ``docs/current/PROJECT_EXECUTION_PLAN.md`` (PLAN-9B-PRODUCER-M-LIVE),
``src/content/visual_planning/semantic_brief.py``, ``src/runtime_network.py``.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.config_resolver.paths import repository_path
from src.content.visual_planning.semantic_brief import (
    ADAPTER_ID,
    MAX_CONTEXT_ITEMS,
    ModelSemanticBriefAdapter,
    SemanticBriefUnavailableError,
)
from src.content.visual_planning.models import SHOT_TYPES
from src.runtime_network import (
    NETWORK_ACTION_SEMANTIC_BRIEF,
    NetworkAccessDeniedError,
    network_action_allowed,
    require_network,
)

BACKEND_ID = "openai"
BACKEND_VERSION = "openai.responses.semantic_brief.v1"
DEFAULT_CONFIG_PATH = repository_path("config", "semantic_brief.json")

# Тот же приём, что у платного Vision: одного булева флага мало, потому что булев флаг
# ставят случайно. Фраза набирается осознанно.
LIVE_CONFIRMATION_PHRASE = "LIVE_SEMANTIC_BRIEF_APPROVED"

API_KEY_ENV_VAR = "OPENAI_API_KEY"

SCHEMA_NAME = "visual_semantic_brief"


@dataclass(frozen=True)
class SemanticBriefModelConfig:
    """Ровно то, что нужно, чтобы один раз спросить модель — и ни поля больше."""

    enabled: bool = False
    backend: str = BACKEND_ID
    model: str = ""
    timeout_sec: float = 30.0
    max_output_tokens: int = 400
    # Платные условия. Ноль и пусто — значение по умолчанию, то есть отказ.
    allow_paid_calls: bool = False
    confirm_paid_calls: str = ""
    maximum_calls_per_project: int = 0
    maximum_budget_usd: float = 0.0
    estimated_cost_per_call_usd: float = 0.0
    model_allowlist: frozenset[str] = field(default_factory=frozenset)

    @classmethod
    def from_config(cls, config: dict[str, Any] | None) -> "SemanticBriefModelConfig":
        raw = dict(config or {})
        model = str(raw.get("model") or "")
        allowlist = {str(item) for item in (raw.get("model_allowlist") or []) if str(item)}
        if model:
            allowlist.add(model)
        return cls(
            enabled=bool(raw.get("enabled", False)),
            backend=str(raw.get("backend") or BACKEND_ID),
            model=model,
            timeout_sec=max(1.0, float(raw.get("timeout_sec") or 30.0)),
            max_output_tokens=max(1, int(raw.get("max_output_tokens") or 400)),
            allow_paid_calls=bool(raw.get("allow_paid_calls", False)),
            confirm_paid_calls=str(raw.get("confirm_paid_calls") or ""),
            maximum_calls_per_project=max(0, int(raw.get("maximum_calls_per_project") or 0)),
            maximum_budget_usd=max(0.0, float(raw.get("maximum_budget_usd") or 0.0)),
            estimated_cost_per_call_usd=max(
                0.0, float(raw.get("estimated_cost_per_call_usd") or 0.0)
            ),
            model_allowlist=frozenset(allowlist),
        )


def load_semantic_brief_config(path: Path | None = None) -> dict[str, Any]:
    """Стоящая политика с диска. Отсутствующий файл — это отказ, а не ошибка."""
    target = Path(path or DEFAULT_CONFIG_PATH)
    if not target.is_file():
        return {}
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def paid_call_blockers(config: SemanticBriefModelConfig) -> list[str]:
    """Почему платить нельзя. Пустой список — единственное «можно».

    Отдельно от сетевого разрешения намеренно: сеть отвечает на вопрос «этому прогону
    вообще разрешено выходить наружу», оплата — «этой возможности разрешено тратить и
    сколько». Один ответ никогда не выдаёт другой.
    """
    reasons: list[str] = []
    if not config.allow_paid_calls:
        reasons.append("allow_paid_calls_required")
    if config.confirm_paid_calls != LIVE_CONFIRMATION_PHRASE:
        reasons.append("confirm_paid_calls_required")
    if config.maximum_calls_per_project <= 0:
        reasons.append("maximum_calls_per_project_required")
    if config.maximum_budget_usd <= 0:
        reasons.append("maximum_budget_usd_required")
    return reasons


def response_schema() -> dict[str, Any]:
    """Схема запроса, выведенная из существующего контракта ответа.

    Ничего нового не объявляет: поля и словарь ``shot_type`` берутся у владельца
    контракта, поэтому строгий парсер и то, что просят у модели, не могут разойтись.
    """
    return {
        "type": "json_schema",
        "name": SCHEMA_NAME,
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["subject", "action", "place", "context", "shot_type"],
            "properties": {
                "subject": {"type": "string"},
                "action": {"type": "string"},
                "place": {"type": "string"},
                "context": {
                    "type": "array",
                    "maxItems": MAX_CONTEXT_ITEMS,
                    "items": {"type": "string"},
                },
                "shot_type": {"type": "string", "enum": ["", *SHOT_TYPES]},
            },
        },
    }


class OpenAISemanticBriefBackend:
    """Инъектируемый вызов модели: подпись ``SemanticBriefCompletionFn``.

    Экземпляр живёт один прогон, потому что счётчик вызовов — это и есть бюджет.
    """

    backend_id = BACKEND_ID
    backend_version = BACKEND_VERSION

    def __init__(
        self,
        config: SemanticBriefModelConfig,
        *,
        client: Any | None = None,
    ) -> None:
        self.config = config
        self.client = client
        self.calls = 0

    def __call__(self, prompt: str, options: dict[str, Any]) -> str:
        scene_id = str(options.get("scene_id") or "?")
        blockers = paid_call_blockers(self.config)
        if blockers:
            raise SemanticBriefUnavailableError(
                "Платный вызов смысловой модели не разрешён: " + ", ".join(sorted(blockers)),
                planner=ADAPTER_ID,
            )
        if self.calls >= self.config.maximum_calls_per_project:
            raise SemanticBriefUnavailableError(
                f"Бюджет вызовов модели исчерпан ({self.config.maximum_calls_per_project}): "
                f"сцена {scene_id} не отправлена.",
                planner=ADAPTER_ID,
            )
        try:
            require_network(NETWORK_ACTION_SEMANTIC_BRIEF, detail=f"scene {scene_id}")
        except NetworkAccessDeniedError as exc:
            raise SemanticBriefUnavailableError(str(exc), planner=ADAPTER_ID) from exc

        client = self.client if self.client is not None else self._default_client()
        model = str(options.get("model_id") or self.config.model)
        # Место в бюджете тратится до вызова: упавший платный запрос уже стоил денег,
        # и повторить его молча нельзя.
        self.calls += 1
        try:
            response = client.responses.create(
                model=model,
                input=[{"role": "user", "content": [{"type": "input_text", "text": prompt}]}],
                text={"format": response_schema()},
                max_output_tokens=self.config.max_output_tokens,
                timeout=self.config.timeout_sec,
            )
        except _sdk_error_types() as exc:  # noqa: B030 - кортеж классов, собранный лениво
            raise _translated(exc, scene_id=scene_id) from exc
        except (TimeoutError, ConnectionError) as exc:
            raise SemanticBriefUnavailableError(
                f"Модель не ответила для сцены {scene_id} "
                f"(backend={BACKEND_ID}, error={type(exc).__name__}).",
                planner=ADAPTER_ID,
                retryable=True,
            ) from exc
        return _text_from_response(response)

    def usage_summary(self) -> dict[str, Any]:
        """Что этот прогон потратил. Только числа и идентификаторы."""
        return {
            "backend": self.backend_id,
            "backend_version": self.backend_version,
            "model": self.config.model,
            "calls": self.calls,
            "maximum_calls_per_project": self.config.maximum_calls_per_project,
            "estimated_cost_usd": round(
                self.calls * self.config.estimated_cost_per_call_usd, 6
            ),
        }

    def _default_client(self) -> Any:
        if not os.getenv(API_KEY_ENV_VAR):
            raise SemanticBriefUnavailableError(
                f"Переменная окружения {API_KEY_ENV_VAR} не задана: вызов модели невозможен.",
                planner=ADAPTER_ID,
            )
        try:
            from openai import OpenAI  # type: ignore
        except ImportError as exc:  # pragma: no cover - зависимость закреплена в lock
            raise SemanticBriefUnavailableError(
                f"OpenAI SDK недоступен: {exc}", planner=ADAPTER_ID
            ) from exc
        return OpenAI(
            api_key=os.getenv(API_KEY_ENV_VAR),
            timeout=self.config.timeout_sec,
            max_retries=0,
        )


def build_semantic_brief_adapter(
    config: SemanticBriefModelConfig | None = None,
    *,
    client: Any | None = None,
) -> ModelSemanticBriefAdapter | None:
    """Адаптер, который действительно может позвонить модели — либо ``None``.

    ``None`` — это ровно то состояние, в котором репозиторий находится по умолчанию, и
    оно означает «плана касается только детерминированный путь»: ``build_plan`` без
    адаптера строит тот же план, что и всегда.

    Проверяются обе двери. Сетевая проверяется здесь, чтобы адаптер вообще не появлялся
    в неразрешённом прогоне, и ещё раз в самом backend перед вызовом SDK — разрешение
    живёт в ``ContextVar`` и может отличаться к моменту вызова.
    """
    settings = config if config is not None else SemanticBriefModelConfig.from_config(
        load_semantic_brief_config()
    )
    if not settings.enabled:
        return None
    if settings.backend != BACKEND_ID:
        return None
    if not settings.model or settings.model not in settings.model_allowlist:
        return None
    if paid_call_blockers(settings):
        return None
    if not network_action_allowed(NETWORK_ACTION_SEMANTIC_BRIEF):
        return None
    if client is None and not os.getenv(API_KEY_ENV_VAR):
        return None
    return ModelSemanticBriefAdapter(
        OpenAISemanticBriefBackend(settings, client=client),
        approved=True,
        model_id=settings.model,
    )


def activation_diagnostics(config: SemanticBriefModelConfig | None = None) -> dict[str, Any]:
    """Почему живой вызов возможен или нет. Без значений секретов."""
    settings = config if config is not None else SemanticBriefModelConfig.from_config(
        load_semantic_brief_config()
    )
    return {
        "backend": settings.backend,
        "backend_version": BACKEND_VERSION,
        "model": settings.model,
        "enabled": settings.enabled,
        "network_action": NETWORK_ACTION_SEMANTIC_BRIEF,
        "network_allowed": network_action_allowed(NETWORK_ACTION_SEMANTIC_BRIEF),
        "paid_blockers": paid_call_blockers(settings),
        "maximum_calls_per_project": settings.maximum_calls_per_project,
        "maximum_budget_usd": settings.maximum_budget_usd,
        "api_key_configured": bool(os.getenv(API_KEY_ENV_VAR)),
    }


def _sdk_error_types() -> tuple[type[BaseException], ...]:
    """Классы ошибок SDK, собранные лениво.

    Импортировать их на уровне модуля значило бы требовать SDK там, где вызова нет.
    Ловить ``Exception`` — значило бы объявить ошибкой модели свой собственный дефект
    интеграции: ``TypeError`` от неверной подписи и ``AttributeError`` от неверного
    клиента должны остаться громкими, ровно как их оставляет ``semantic_brief``.
    """
    try:
        import openai  # type: ignore
    except ImportError:  # pragma: no cover - зависимость закреплена в lock
        return ()
    names = ("APIError", "APIStatusError", "APIConnectionError", "APITimeoutError", "OpenAIError")
    found = []
    for name in names:
        candidate = getattr(openai, name, None)
        if isinstance(candidate, type) and issubclass(candidate, BaseException):
            found.append(candidate)
    return tuple(found)


def _translated(exc: BaseException, *, scene_id: str) -> SemanticBriefUnavailableError:
    """Ожидаемый отказ backend → уже существующая ошибка контракта.

    ``retryable`` отвечает ровно на один вопрос — «поможет ли спросить ещё раз». Отказ
    ключа и отклонённая модель отвечают «нет» навсегда; таймаут, обрыв, лимит частоты и
    5xx — «возможно». Записывается это в любом случае: вызов состоялся.

    Текст исключения провайдера сюда **не переносится**. Сообщение об отказе ключа у
    OpenAI содержит сам ключ («Incorrect API key provided: sk-…»), а это сообщение
    становится warning сцены и уезжает на диск в ``visual_plan.json``. Класс ошибки и
    HTTP-статус различают все случаи, которые здесь нужно различать, и утечь не могут.
    """
    status = _status_code(exc)
    retryable = status in {408, 409, 429} or status >= 500 or status == 0
    return SemanticBriefUnavailableError(
        f"Вызов модели для сцены {scene_id} не выполнен "
        f"(backend={BACKEND_ID}, status={status or 'unknown'}, error={type(exc).__name__}).",
        planner=ADAPTER_ID,
        retryable=retryable,
    )


def _status_code(exc: BaseException) -> int:
    value = getattr(exc, "status_code", None)
    if value is None and getattr(exc, "response", None) is not None:
        value = getattr(exc.response, "status_code", None)
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _text_from_response(response: Any) -> str:
    """Текст ответа в том виде, в каком его ждёт существующий парсер."""
    text = str(getattr(response, "output_text", "") or "").strip()
    if text:
        return text
    for item in getattr(response, "output", None) or []:
        contents = item.get("content") if isinstance(item, dict) else getattr(item, "content", None)
        for content in contents or []:
            value = (
                content.get("text")
                if isinstance(content, dict)
                else getattr(content, "text", None)
            )
            if isinstance(value, str) and value.strip():
                return value.strip()
    raise SemanticBriefUnavailableError(
        "Модель вернула пустой ответ.", planner=ADAPTER_ID, retryable=True
    )


__all__ = [
    "API_KEY_ENV_VAR",
    "BACKEND_ID",
    "BACKEND_VERSION",
    "DEFAULT_CONFIG_PATH",
    "LIVE_CONFIRMATION_PHRASE",
    "OpenAISemanticBriefBackend",
    "SemanticBriefModelConfig",
    "activation_diagnostics",
    "build_semantic_brief_adapter",
    "load_semantic_brief_config",
    "paid_call_blockers",
    "response_schema",
]
