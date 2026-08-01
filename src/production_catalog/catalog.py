"""Canonical boundary фактического состава продукта: приложения, форматы, шаблоны.

``get_default_catalog`` — единственная сборка default каталога и единственный
ответ на вопрос «что продукт умеет прямо сейчас». Результат кэширован, каталог
неизменяем и не зависит от окружения.

Responsibilities:
- регистрация ``ApplicationDefinition``, ``FormatDefinition``,
  ``TemplateDefinition`` и ``ExportTargetDefinition`` с их ``enabled`` и
  ``implementation_status``;
- объявление ``workflow_binding`` шаблона: какой workflow, service entrypoint,
  integration, project system и renderer за ним стоят;
- объявление ``output_contract``, требования evidence, policy id и render
  preset id шаблона.

Does not own:
- реализацию workflow и рендереров — каталог только называет существующих
  владельцев по import path;
- разрешение шаблона для конкретного запроса — ``src.content_creation.service``;
- render presets и design tokens — ``config/render_presets/`` и владельцы
  конфигурации;
- права, провайдеров, озвучку, субтитры и project state.

Inputs: отсутствуют — состав задан кодом этого модуля.

Outputs: ``ProductionCatalog`` из четырёх in-memory реестров. Ни одного файла
не создаётся и не читается.

Important invariants:
- каталог описывает фактическое, а не планируемое состояние: ``enabled=False``
  означает выключенную возможность, а не отвергнутую;
- формат без зарегистрированного шаблона остаётся выключенным, иначе
  вызывающая сторона получает формат, для которого нельзя выбрать шаблон;
- ``active`` присваивается только шаблону с подтверждённым сквозным
  результатом; сегодня это ``story_card_text_only_v1`` и
  ``fullscreen_voiceover_v1``;
- согласованность каталога с ``src.content_creation.capabilities`` проверяет
  ``tests/test_capability_consistency.py``;
- ``video_repurposer`` остаётся ``planned``/выключенным, пока миграция не
  выполнена.

Расхождение объявленных export targets с фактическим поведением рендера
зафиксировано в ``docs/current/CLEANUP_REGISTRY.md`` и здесь не дублируется.

See also: ``src/production_catalog/__init__.py``,
``docs/adr/0016-two-engine-product-architecture.md``,
``docs/current/SYSTEM_MAP.md``.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from .models import ApplicationDefinition, ExportTargetDefinition, FormatDefinition, TemplateDefinition
from .registry import ApplicationRegistry, ExportTargetCatalog, FormatCatalog, TemplateRegistry


@dataclass(frozen=True)
class ProductionCatalog:
    applications: ApplicationRegistry
    formats: FormatCatalog
    templates: TemplateRegistry
    export_targets: ExportTargetCatalog


def _build_applications() -> ApplicationRegistry:
    registry = ApplicationRegistry()
    registry.register(
        ApplicationDefinition(
            application_id="content_creator",
            display_name="Создание контента",
            description=(
                "Создание нового видео из темы, сценария, текста или ссылки: сценарий, "
                "подбор визуала, озвучка и финальный рендер."
            ),
            supported_input_types=("topic", "script", "text", "url"),
            supported_format_ids=("vertical_short", "longform"),
            enabled=True,
            implementation_status="active",
        )
    )
    registry.register(
        ApplicationDefinition(
            application_id="video_repurposer",
            display_name="Нарезка и переработка видео",
            description=(
                "Планируемое приложение для нарезки и переработки уже существующего видео "
                "в короткие вертикальные или горизонтальные ролики. Workflow пока не реализован."
            ),
            supported_input_types=("local_video", "source_url"),
            supported_format_ids=("vertical_short", "horizontal_clip"),
            enabled=False,
            implementation_status="planned",
        )
    )
    return registry


def _build_formats() -> FormatCatalog:
    catalog = FormatCatalog()
    catalog.register(
        FormatDefinition(
            format_id="vertical_short",
            display_name="Короткое вертикальное видео",
            width=1080,
            height=1920,
            aspect_ratio="9:16",
            enabled=True,
            implementation_status="active",
        )
    )
    catalog.register(
        # enabled=False on purpose: no template is registered for this format yet, so
        # offering it would dead-end any caller that filters formats by `enabled` and
        # then asks for a template (the terminal wizard used to abort the whole run
        # here). Flip to True in the same change that registers the first real
        # longform template - tests/test_capability_consistency.py enforces the rule.
        FormatDefinition(
            format_id="longform",
            display_name="Длинное видео",
            width=1920,
            height=1080,
            aspect_ratio="16:9",
            enabled=False,
            implementation_status="planned",
        )
    )
    catalog.register(
        FormatDefinition(
            format_id="horizontal_clip",
            display_name="Горизонтальная нарезка",
            width=1920,
            height=1080,
            aspect_ratio="16:9",
            enabled=False,
            implementation_status="planned",
        )
    )
    return catalog


def _build_templates() -> TemplateRegistry:
    registry = TemplateRegistry()
    registry.register(
        TemplateDefinition(
            template_id="story_card_text_only_v1",
            application_id="content_creator",
            format_id="vertical_short",
            display_name="Карточка с текстом",
            description=(
                "Короткое вертикальное видео без обязательной озвучки: верхний смысловой "
                "текст, центральное видео, блок канала и авторский комментарий."
            ),
            version=1,
            enabled=True,
            implementation_status="active",
            supported_input_types=("topic", "script", "text"),
            supported_export_targets=(
                "youtube_shorts",
                "instagram_reels",
                "tiktok",
                "facebook_reels",
                "stories",
            ),
            requires_voice=False,
            supports_topic_input=True,
            supports_script_input=True,
            recommended_for=(
                "короткие факты",
                "животные",
                "природные явления",
                "одно визуально понятное событие",
                "короткий ролик без обязательной озвучки",
            ),
            render_preset_id="story_card_short_v1",
            legacy_aliases=("story_card_short_v1",),
            # This template does NOT go through news_to_short (that was a copy/paste
            # error in the original registration): src.content_creation.service routes
            # story_card_text_only_v1 to ProjectFactory + templates.story_card.integration,
            # which calls the renderer below directly. See
            # tests/test_story_card_project_integration.py.
            workflow_binding={
                "workflow": "story_card",
                "cli_entrypoint": "ai_youtube",
                "service_entrypoint": "src.content_creation.service.create_content",
                "integration": "src.templates.story_card.integration.prepare_story_card_render",
                "project_system": "src.project_foundation.projects.ProjectFactory",
                "renderer": "src.production_plan.story_card_short_render",
                "renderer_entrypoints": [
                    "load_story_card_preset",
                    "render_story_card_short",
                ],
            },
            output_contract={
                "final_video": {"type": "mp4", "orientation": "vertical", "required": True},
                "render_manifest": {"type": "json", "required": True},
                "layout_manifest": {"type": "json", "required": True},
                "preview_image": {"type": "png", "required": True},
                "technical_validation": {"type": "json", "required": True},
            },
            evidence_required=True,
            script_policy_id=None,
            asset_policy_id=None,
            # src.audio.voice_policy.AUDIO_POLICY_DEFAULTS already defined this policy
            # (voice disabled, visual-driven timing) but nothing referenced it, so the
            # template fell back to an empty policy dict.
            audio_policy_id="story_card_no_voice",
            duration_policy_id=None,
            selection_policy_id=None,
            quality_policy_id=None,
        )
    )
    registry.register(
        TemplateDefinition(
            template_id="fullscreen_voiceover_v1",
            application_id="content_creator",
            format_id="vertical_short",
            display_name="Полноэкранное видео с озвучкой",
            description=(
                "Короткое вертикальное видео с обязательной озвучкой на весь кадр: без "
                "крупного текстового оверлея, покадровая (scene-level) генерация озвучки, "
                "субтитры опциональны по policy. Использует существующий News-to-Short "
                "renderer через workflow_binding - отдельный renderer не создавался."
            ),
            version=1,
            enabled=True,
            # "active", not "experimental": this is the one path with a confirmed
            # end-to-end result on disk (real narration.wav, burned-in subtitles,
            # quality_report status=passed and a rendered master MP4). It used to be
            # registered as experimental while capabilities.TEMPLATE_TESTED_STATUS
            # called it live_tested - the two now agree.
            implementation_status="active",
            supported_input_types=("topic", "script", "text"),
            supported_export_targets=(
                "youtube_shorts",
                "instagram_reels",
                "tiktok",
                "facebook_reels",
                "stories",
            ),
            requires_voice=True,
            supports_topic_input=True,
            supports_script_input=True,
            recommended_for=(
                "полноэкранное видео без текстового оверлея",
                "форматы, где озвучка обязательна",
                "документальные факты",
            ),
            # Deliberately empty: there is no config/render_presets/fullscreen_voiceover_v1.json
            # and never was. This template's geometry comes from the channel config
            # (resolution/fps) and the visual plan, not from a render preset file.
            render_preset_id="",
            workflow_binding={
                "workflow": "news_to_short",
                "cli_entrypoint": "src.news.pipeline.run_news_to_short_cli",
                "renderer": "src.news.final_renderer",
                "renderer_entrypoints": ["render_final_video"],
            },
            output_contract={
                "final_video": {"type": "mp4", "orientation": "vertical", "required": True},
                "render_manifest": {"type": "json", "required": True},
                "voice_manifest": {"type": "json", "required": True},
                "technical_validation": {"type": "json", "required": True},
            },
            evidence_required=True,
            script_policy_id=None,
            asset_policy_id=None,
            audio_policy_id="fullscreen_voiceover_default",
            duration_policy_id=None,
            selection_policy_id=None,
            quality_policy_id=None,
        )
    )
    return registry


def _build_export_targets() -> ExportTargetCatalog:
    catalog = ExportTargetCatalog()
    catalog.register(
        ExportTargetDefinition(
            target_id="youtube_shorts",
            display_name="YouTube Shorts",
            format_id="vertical_short",
            width=1080,
            height=1920,
            aspect_ratio="9:16",
            max_duration_sec=None,
            safe_zone_profile="vertical_9x16_standard",
            output_filename="youtube_shorts.mp4",
            enabled=True,
            implementation_status="active",
        )
    )
    catalog.register(
        ExportTargetDefinition(
            target_id="instagram_reels",
            display_name="Instagram Reels",
            format_id="vertical_short",
            width=1080,
            height=1920,
            aspect_ratio="9:16",
            max_duration_sec=None,
            safe_zone_profile="vertical_9x16_standard",
            output_filename="instagram_reels.mp4",
            enabled=True,
            implementation_status="active",
        )
    )
    catalog.register(
        ExportTargetDefinition(
            target_id="tiktok",
            display_name="TikTok",
            format_id="vertical_short",
            width=1080,
            height=1920,
            aspect_ratio="9:16",
            max_duration_sec=None,
            safe_zone_profile="vertical_9x16_standard",
            output_filename="tiktok.mp4",
            enabled=True,
            implementation_status="active",
        )
    )
    catalog.register(
        ExportTargetDefinition(
            target_id="facebook_reels",
            display_name="Facebook Reels",
            format_id="vertical_short",
            width=1080,
            height=1920,
            aspect_ratio="9:16",
            max_duration_sec=None,
            safe_zone_profile="vertical_9x16_standard",
            output_filename="facebook_reels.mp4",
            enabled=True,
            implementation_status="active",
        )
    )
    catalog.register(
        ExportTargetDefinition(
            target_id="stories",
            display_name="Stories (Instagram/Facebook)",
            format_id="vertical_short",
            width=1080,
            height=1920,
            aspect_ratio="9:16",
            max_duration_sec=None,
            safe_zone_profile="vertical_9x16_standard",
            output_filename="stories.mp4",
            enabled=True,
            implementation_status="active",
        )
    )
    return catalog


@lru_cache(maxsize=1)
def get_default_catalog() -> ProductionCatalog:
    return ProductionCatalog(
        applications=_build_applications(),
        formats=_build_formats(),
        templates=_build_templates(),
        export_targets=_build_export_targets(),
    )
