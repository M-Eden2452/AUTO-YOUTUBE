"""Canonical boundary создания контента: единственный вход ``create_content``.

Facade остаётся общей точкой входа канонического CLI, compatibility CLI и
Wizard. Он разрешает и проверяет запрос один раз, после чего делегирует
существующей application boundary шаблона.

Responsibilities:
- разрешение шаблона: явный ``template_id`` либо ``default_template`` канала;
- проверка совместимости ``format_id`` с шаблоном;
- валидация музыкального входа запроса;
- маршрутизация в
  ``src.ai_youtube.apps.content_creator.workflows.story_card`` или
  ``...workflows.fullscreen_voiceover``;
- явная ошибка для шаблона, который каталог знает, но реализации у него нет.

Does not own:
- сами workflow, их стадии, project state и рендер;
- состав каталога — ``src.production_catalog``;
- сборку запроса из аргументов — ``src.content_creation.request_builder``;
- каналы и их конфигурацию — ``src.project_foundation.channels``;
- ассеты, права, озвучку, субтитры и экспорт.

Inputs: ``ContentCreationRequest`` и необязательный ``progress_callback``.

Outputs: ``ContentCreationResult`` от выбранного use case. Файлы создают
workflow и их storage owners, а не этот модуль.

Important invariants:
- ``create_content`` остаётся единственной точкой входа создания;
- реализованы ровно два шаблона — ``story_card_text_only_v1`` и
  ``fullscreen_voiceover_v1``; остальное в каталоге architecture-supported и
  создание для него завершается явной ``ContentCreationError``;
- запрос отвергается до начала работы, а не в середине выполнения;
- import pipeline остаётся ленивым внутри use case, чтобы граница CLI не тянула
  весь workflow;
- ``fullscreen_voiceover_use_case`` и ``story_card_use_case`` в этом пакете —
  compatibility wrappers; новая логика добавляется в canonical boundaries.

See also: ``src/content_creation/__init__.py``,
``docs/adr/0009-fullscreen-voiceover-application-boundary.md``,
``docs/adr/0010-story-card-application-boundary.md``.
"""

from __future__ import annotations

from src.content_creation import input_validation
from src.ai_youtube.apps.content_creator.workflows.fullscreen_voiceover.use_case import (
    _RETRYABLE_ARTICLE_REASONS,
    build_paid_preflight_summary as _build_paid_preflight_summary,
    completed_narration as _completed_narration,
    create_fullscreen_voiceover as _create_fullscreen_voiceover,
    create_paid_voice_approval as _create_paid_voice_approval,
    fullscreen_rerun_command as _fullscreen_rerun_command,
    resolve_content_inputs as _resolve_content_inputs,
    resolve_localization as _resolve_localization,
    resolve_script_source as _resolve_script_source,
    resolve_voice_inputs as _resolve_voice_inputs,
)
from src.ai_youtube.apps.content_creator.workflows.story_card.use_case import (
    create_story_card as _create_story_card,
    story_card_rerun_command as _story_card_rerun_command,
)
from src.content_creation.models import (
    ContentCreationError,
    ContentCreationRequest,
    ContentCreationResult,
)
from src.content_creation.service_support import (
    ProgressCallback,
    notify as _notify,
    request_path_context as _request_path_context,
)
from src.production_catalog.catalog import get_default_catalog
from src.production_catalog.models import CatalogValidationError
from src.project_foundation.channels import ChannelRegistry
from src.project_foundation.models import ProjectFoundationError
from src.templates.story_card.integration import (
    STORY_CARD_CANONICAL_TEMPLATE_ID,
)


FULLSCREEN_VOICEOVER_TEMPLATE_ID = "fullscreen_voiceover_v1"

# The two templates this application layer actually knows how to create today.
# Anything else in the catalog is architecture-supported only.
_SUPPORTED_TEMPLATE_IDS = {
    STORY_CARD_CANONICAL_TEMPLATE_ID,
    FULLSCREEN_VOICEOVER_TEMPLATE_ID,
}


def _resolve_template(request: ContentCreationRequest):
    catalog = get_default_catalog()
    template_query = request.template_id
    if not template_query and request.channel_id:
        try:
            _projects_root, _fallback_roots, channels_root = (
                _request_path_context(request)
            )
            channel = ChannelRegistry(channels_root).get(request.channel_id)
            template_query = channel.default_template
        except ProjectFoundationError:
            template_query = ""
    if not template_query:
        raise ContentCreationError(
            "template_id is required (explicitly, or via the channel's "
            "default_template)."
        )
    try:
        template = catalog.templates.get(template_query)
    except CatalogValidationError as exc:
        raise ContentCreationError(str(exc)) from exc
    if request.format_id and request.format_id != template.format_id:
        raise ContentCreationError(
            f"format_id {request.format_id!r} is not compatible with template "
            f"{template.template_id!r} (expects {template.format_id!r})."
        )
    return template


def _validate_music_request(request: ContentCreationRequest) -> None:
    if request.music.mode == "disabled":
        return
    if request.music.mode == "local_file":
        result = input_validation.validate_music_path(request.music.path)
        if not result.valid:
            raise ContentCreationError(
                result.message,
                reason=result.reason,
            )
        return
    raise ContentCreationError(
        f"Unknown music mode: {request.music.mode!r}.",
        reason="invalid_music_mode",
    )


def create_content(
    request: ContentCreationRequest,
    *,
    progress_callback: ProgressCallback | None = None,
) -> ContentCreationResult:
    """Create content through the application service's tested use cases.

    This remains the single entrypoint used by the canonical CLI, compatibility
    CLI and Wizard. It resolves and validates the request once, then delegates to
    the existing Story Card or Fullscreen Voiceover workflow boundary.
    """
    template = _resolve_template(request)
    _validate_music_request(request)
    canonical_template_id = template.template_id

    if canonical_template_id == STORY_CARD_CANONICAL_TEMPLATE_ID:
        return _create_story_card(request, template, progress_callback)
    if canonical_template_id == FULLSCREEN_VOICEOVER_TEMPLATE_ID:
        return _create_fullscreen_voiceover(
            request,
            template,
            progress_callback,
        )
    raise ContentCreationError(
        f"template {canonical_template_id!r} is registered in the production "
        f"catalog (implementation_status={template.implementation_status!r}) "
        "but has no create workflow implemented yet - it is "
        "architecture-supported only."
    )
