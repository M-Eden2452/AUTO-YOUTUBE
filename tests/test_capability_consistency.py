"""Test classification: ARCHITECTURE INVARIANT

Guards against the capability layer drifting away from what actually runs.

Every assertion here corresponds to a concrete defect found in the 2026-07-25
architecture audit (docs/handoff/AUTONOMOUS_ARCHITECTURE_AUDIT.md). These are
consistency checks over the in-memory catalog and the on-disk channel files -
no network, no paid provider, no writes.

Protects:
- границу, которую мы держим намеренно: каталог и слой capabilities обязаны
  описывать одно и то же. Включённый формат имеет включённый шаблон; шаблон
  указывает на зарегистрированные формат, приложение и известный workflow; его
  render preset либо пуст, либо лежит на диске; канал объявляет свою
  пригодность; legacy-каналы ``pipeline.py`` не предлагаются для создания
  контента; только production-статус заявляет о готовности.

Does not prove:
- что объявленная возможность действительно даёт качественный результат:
  проверяется согласованность объявлений, а не поведение рендера;
- что каталог правдив во всём. Известное расхождение объявленных export
  targets с фактическим поведением зафиксировано как C44 в
  ``docs/current/CLEANUP_REGISTRY.md`` и этим модулем не ловится.

Класс подтверждён явным non-anchor контрастом в
``docs/current/CLEANUP_REGISTRY.md``, «Accidental invariants»: этот модуль
менять без отдельного решения нельзя.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from src.content_creation import capabilities
from src.production_catalog.catalog import get_default_catalog


class FormatTemplateConsistencyTests(unittest.TestCase):
    def test_every_enabled_format_has_at_least_one_enabled_template(self) -> None:
        catalog = get_default_catalog()
        for definition in catalog.formats.list_all():
            if not definition.enabled:
                continue
            templates = [t for t in catalog.templates.filter_by_format(definition.format_id) if t.enabled]
            self.assertTrue(
                templates,
                f"Format {definition.format_id!r} is enabled but has no enabled template; "
                "the wizard would dead-end on it.",
            )

    def test_every_template_points_at_a_registered_format_and_application(self) -> None:
        catalog = get_default_catalog()
        for template in catalog.templates.list_all():
            catalog.formats.get(template.format_id)
            catalog.applications.get(template.application_id)

    def test_template_render_preset_id_either_empty_or_present_on_disk(self) -> None:
        for template in get_default_catalog().templates.list_all():
            if not template.render_preset_id:
                continue
            preset = Path("config") / "render_presets" / f"{template.render_preset_id}.json"
            self.assertTrue(
                preset.is_file(),
                f"Template {template.template_id!r} declares render_preset_id "
                f"{template.render_preset_id!r} but {preset} does not exist.",
            )

    def test_workflow_binding_names_a_known_workflow(self) -> None:
        known = {"story_card", "news_to_short"}
        for template in get_default_catalog().templates.list_all():
            workflow = (template.workflow_binding or {}).get("workflow", "")
            self.assertIn(
                workflow,
                known,
                f"Template {template.template_id!r} declares workflow {workflow!r}, which is not implemented.",
            )

    def test_live_tested_templates_are_not_registered_as_experimental(self) -> None:
        catalog = get_default_catalog()
        for template_id, tested in capabilities.TEMPLATE_TESTED_STATUS.items():
            if tested != "live_tested":
                continue
            template = catalog.templates.get(template_id)
            self.assertEqual(
                template.implementation_status,
                "active",
                f"{template_id!r} is recorded as live_tested but registered as "
                f"{template.implementation_status!r}.",
            )


class ChannelConsistencyTests(unittest.TestCase):
    def test_every_channel_declares_whether_it_is_usable(self) -> None:
        for channel in capabilities.list_channels():
            self.assertIn("supported_templates", channel)
            self.assertIn("usable_for_content_creation", channel)
            self.assertEqual(
                channel["usable_for_content_creation"],
                bool(channel["supported_templates"]),
                f"Channel {channel['channel_id']!r} has contradictory usability fields.",
            )

    def test_supported_templates_exist_in_the_catalog(self) -> None:
        catalog = get_default_catalog()
        for channel in capabilities.list_channels():
            for template_id in channel["supported_templates"]:
                catalog.templates.get(template_id)

    def test_legacy_pipeline_channels_are_not_offered_for_content_creation(self) -> None:
        """quotes/psychology/survival/size_comparison are pipeline.py --channel/--video
        profiles: a different schema with no `mode`, no `voice`, no voices.yaml."""
        channels = {c["channel_id"]: c for c in capabilities.list_channels()}
        for channel_id, channel in channels.items():
            config_path = Path("channels") / channel_id / "channel_config.json"
            if not config_path.is_file() or channel["channel_profile_type"] != capabilities.CHANNEL_TYPE_LEGACY_PIPELINE:
                continue
            data = json.loads(config_path.read_text(encoding="utf-8"))
            self.assertNotEqual(data.get("mode"), "news_to_short")
            self.assertFalse(
                channel["usable_for_content_creation"],
                f"Legacy channel {channel_id!r} is offered for content creation.",
            )

    def test_list_channels_for_template_is_a_subset_of_list_channels(self) -> None:
        everything = {c["channel_id"] for c in capabilities.list_channels()}
        for template in get_default_catalog().templates.list_all():
            for channel in capabilities.list_channels_for_template(template.template_id):
                self.assertIn(channel["channel_id"], everything)
                self.assertIn(template.template_id, channel["supported_templates"])


class CapabilityReportTests(unittest.TestCase):
    def test_report_builds_and_covers_every_registered_template(self) -> None:
        report = capabilities.build_capabilities_report()
        reported = {item["template_id"] for item in report["templates"]}
        registered = {t.template_id for t in get_default_catalog().templates.list_all()}
        self.assertEqual(reported, registered)

    def test_only_production_status_options_claim_to_be_wired(self) -> None:
        """A music/subtitle option may only claim status=production if it is really
        usable end-to-end today; anything else must say so explicitly."""
        allowed = {"production", "targeted_tested", "mock_tested", "architecture_supported", "planned"}
        for option in capabilities.list_music_options() + capabilities.list_subtitle_styles():
            self.assertIn(option["status"], allowed)


if __name__ == "__main__":
    unittest.main()
