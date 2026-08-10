"""Что сцена требует, что кандидат доказуемо показывает, и почему выбран этот.

Подпакет владеет разбором сцены на проверяемые требования, чтением evidence,
которое провайдер действительно дал, оценкой кандидата и единственным
объяснимым verdict'ом. Он работает на метаданных и на уже вычисленных
признаках; сам он ничего не ищет, не скачивает и не вызывает платные сервисы.

Публичные точки входа: ``analyze_scene`` -> ``SemanticScene`` и её типы
(``SCENE_EXACT_SUBJECT``, ``SCENE_EXACT_ACTION``, ``SCENE_ENVIRONMENT``,
``SCENE_RESEARCH_CONTEXT``, ``SCENE_ABSTRACT_EXPLANATION``,
``SCENE_TRANSITION``), ``rank_candidates`` и ``select_best_candidate``,
``decision`` (по-слотовый verdict и его чтение), ``check_continuity``,
``validate_candidate_vision``.

Поток: сцена -> требования -> evidence по каждому кандидату -> оценки, хранимые
раздельно -> ``decision`` -> выбор с сохранённым обоснованием.

Не владеет: строкой, которая уходит провайдеру (``src.assets.query_adapter``),
порядком опроса провайдеров (``src.assets.scene_strategy`` и
``provider_routing``), правами (``src.assets.license_policy``), скачиванием,
completion и манифестом ассетов. Запросы из разобранной сцены строит
``src.content.visual_planning`` (``semantic_scene_queries`` поверх канонической
expansion ladder); собственного генератора запросов здесь больше нет.

Инварианты: поисковый запрос и производные от него теги не считаются evidence;
отсутствие метаданных сообщается как ``metadata_status="unavailable"`` и не
округляется до совпадения; кандидат оценивается по каждому требованию сцены
отдельно, и обоснование сохраняется до записи манифеста; порядок отбора
детерминирован; ``validate_candidate_vision`` потребляет только предвычисленные
теги и платных Vision-вызовов не делает.

Media policy: ``media_policy.select_with_media_policy`` - единственный владелец
решения «какой вид медиа может победить»: hard whitelist через существующий
``allowed_media_kinds`` сцены и bounded video-предпочтение только среди
конкурентных кандидатов (тот же support-класс, не хуже по правам, внутри
review-окна). Это не второй selector: ранжирует по-прежнему
``select_best_candidate``, политика лишь применяет ограничения вида поверх его
результата и вызывается одинаково до и после Vision.

Расширение: новый признак — новое требование сцены и новое правило evidence в
существующих модулях; дополнительный Vision-источник подключается через
``src.assets.semantic_visual_backend``. Второй candidate selector и второй
словарь verdict'ов не создаются.

См. также: ``src/assets/README.md``, ``docs/current/PRODUCT_PLAN.md``.
"""

from __future__ import annotations

from .candidate_ranker import rank_candidates, select_best_candidate
from .continuity_checker import check_continuity
from .media_policy import (
    candidate_media_kind,
    media_kind_restriction,
    select_with_media_policy,
)
from .models import (
    SCENE_ABSTRACT_EXPLANATION,
    SCENE_ENVIRONMENT,
    SCENE_EXACT_ACTION,
    SCENE_EXACT_SUBJECT,
    SCENE_RESEARCH_CONTEXT,
    SCENE_TRANSITION,
    SemanticScene,
)
from .scene_analyzer import analyze_scene
from .vision_validator import validate_candidate_vision

__all__ = [
    "SCENE_ABSTRACT_EXPLANATION",
    "SCENE_ENVIRONMENT",
    "SCENE_EXACT_ACTION",
    "SCENE_EXACT_SUBJECT",
    "SCENE_RESEARCH_CONTEXT",
    "SCENE_TRANSITION",
    "SemanticScene",
    "analyze_scene",
    "candidate_media_kind",
    "check_continuity",
    "media_kind_restriction",
    "rank_candidates",
    "select_best_candidate",
    "select_with_media_policy",
    "validate_candidate_vision",
]
