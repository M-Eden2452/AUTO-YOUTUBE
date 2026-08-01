"""Общая аудио-подсистема: voice/TTS, approval, манифесты, тайминг, музыка.

Пакет владеет всей звуковой частью продукта и переиспользуется workflow, а не
копируется в них. Здесь же находится единственный источник реального
по-сценного тайминга, которым пользуются рендер и субтитры.

Публичные точки входа: ``narration_workflow.prepare_final`` и
``narration_workflow.generate_final`` (единственный gated путь к платной
генерации), ``voice_workflow`` (состояния и approval), ``voice_policy``
(режимы вывода и policy канала), ``voice_profile_registry`` и ``voice_cli``
(профили голоса), ``narration_models`` (request к TTS),
``scene_timeline.build_scene_timeline`` и ``apply_timeline_to_script``,
``audio_assembler`` (сборка narration), ``pause_policy``, ``end_tail_policy``,
``voice_manifest``, ``music_manifest``, подпакет ``tts`` (контракт провайдера
и ``TTSProviderManager``).

Поток: policy и профиль канала -> ``NarrationRequest`` -> preflight и проверка
approval -> по-сценная генерация с кэшем -> сборка narration с паузами ->
``voice_manifest.json`` -> ``SceneTimeline`` для рендера и субтитров.

Persisted artifacts: ``localizations/<lang>/voice/voice_manifest.json``
(schema v2, читает legacy v1), по-сценные файлы и их sidecar-кэш,
``narration.wav``, ``localizations/<lang>/voice/scene_timeline.json``,
approval-запись и ``assets/music/music_manifest.json``.

Не владеет: подбором визуального материала (``src.assets``, ``src.providers``),
сценарием (``src.content``), движком субтитров (``src.subtitles``), финальной
сборкой ролика (``src.news.final_renderer``), состоянием проекта и порядком
стадий (``src.news.pipeline``, ``src.projects``, ``src.project_foundation``).
Микширование музыки остаётся в рендерере: ``music_manifest`` только пишет
манифест и не вызывает ffmpeg для микса.

Инварианты: платная генерация выполняется только при approval, привязанном к
текущему тексту, настройкам, голосу, модели и языку — иначе ``PermissionError``;
частичный сбой оставляет статус ``partially_completed`` и сохраняет уже
сгенерированные сцены; narration считается завершённой только при полном
наборе сцен, ненулевой длительности и совпадении checksum; ``SceneTimeline``
остаётся единственным владельцем фактических длительностей сцен.

Расширение: новый TTS-провайдер регистрируется в ``tts.provider_manager`` через
существующий контракт; новая policy — через ``voice_policy``; новое правило
пауз — через ``pause_policy``. Второй voice registry, второй approval-механизм
и второй timeline owner не создаются.

См. также: ``docs/current/SYSTEM_MAP.md``,
``docs/current/ARCHITECTURE_BOUNDARY_MAP.md``, ``AGENTS.md``.
"""

