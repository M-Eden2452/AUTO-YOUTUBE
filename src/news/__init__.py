"""Рабочий workflow шаблона ``fullscreen_voiceover_v1`` (исторически news_to_short).

Пакет владеет стадийным выполнением от входа до экспорта и persisted формой
``job.json``. Application-уровень этого шаблона вынесен в canonical boundary
``src.ai_youtube.apps.content_creator.workflows.fullscreen_voiceover`` (ADR 0009);
здесь остаётся сам workflow, а не выбор шаблона и не CLI-контракт.

Публичные точки входа: ``pipeline.create_news_to_short_job``,
``pipeline.run_news_to_short_job``, ``pipeline.run_news_to_short_cli``,
``project_store.NewsProjectStore``, ``models.NewsJob``,
``asset_manager.build_news_asset_manifest``, ``final_renderer.render_final_video``.

Поток стадий: ``input`` -> ``article_ingestion`` -> ``research`` -> ``script``
-> ``visual_plan`` -> ``asset_search`` -> ``voice`` -> ``subtitles`` ->
``preview_render`` -> ``quality_check`` -> ``final_render`` -> ``export``.
Каноническое имя и порядок стадий — ``models.NEWS_TO_SHORT_STAGES``.

Persisted artifacts: ``job.json`` со stage state (``schema_version=1``,
ADR 0004), ``article/``, ``research/``, ``localizations/<lang>/`` со script,
visual plan, voice, subtitles и output, ``assets/assets_manifest.json``,
``quality/quality_report.json``, ``render/final_render_manifest.json``,
``export/``.

Не владеет: контрактом провайдера и общими asset-сервисами
(``src.assets``, ``src.providers``), voice/TTS и approval (``src.audio``),
SceneTimeline (``src.audio.scene_timeline``), движком субтитров
(``src.subtitles``), production catalog, общим read API проектов
(``src.projects``) и atomic storage/lock (``src.project_foundation``).
Модули ``script_generator``, ``visual_plan``, ``subtitles`` и ``voice_adapter``
здесь — адаптеры над общими движками, а не вторые реализации.

Инварианты: ``NewsProjectStore`` — единственный writer этой persisted формы,
пишет атомарно и под fail-fast project lock (ADR 0005); повторяемые стадии от
``research`` до ``export`` идемпотентны по проверке фактического output
(ADR 0006); ``input`` и потенциально сетевой ``article_ingestion`` в эту
policy намеренно не входят; платная генерация озвучки требует валидного
approval на диске, и один только ``--execute-voice`` её не запускает.

Расширение: новую стадию добавляй в ``models.NEWS_TO_SHORT_STAGES`` и
``pipeline._dispatch_stage`` вместе с проверкой её output; новую возможность
подбора материала — в ``src.assets``/``src.providers``, а не рядом здесь;
второй project writer, второй pipeline и второй renderer не создаются.

См. также: ``docs/current/SYSTEM_MAP.md``,
``docs/current/ARCHITECTURE_BOUNDARY_MAP.md``, ADR 0004, 0005, 0006, 0009.
"""

