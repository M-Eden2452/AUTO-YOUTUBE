# Autonomous Progress

Журнал автономной работы. Одна запись на этап, не на каждый вызов инструмента.

---

## 2026-07-25 — Аудит (read-only) — ЗАВЕРШЁН

- **Цель:** зафиксировать фактическое состояние репозитория и построить roadmap.
- **Результат:** `docs/handoff/AUTONOMOUS_ARCHITECTURE_AUDIT.md`,
  `docs/handoff/AUTONOMOUS_IMPLEMENTATION_PLAN.md`.
- **Python-код не изменялся.** Сеть, платные вызовы, downloads, renders не выполнялись.
- **Тесты:** `tests.test_content_creation_service`, `test_content_creation_cli`,
  `test_content_creation_wizard`, `test_production_catalog_foundation` — 95 тестов, OK
  (с `PYTHONIOENCODING=utf-8`).
- **Ключевые находки:** см. §14 аудита.

---

## Stage A — Честные статусы и source of truth

- **Цель:** убрать ложные возможности из каталога/capabilities/wizard и привести
  документацию в соответствие с кодом.
- **Проверенные факты:**
  - формат `longform` включён без единого шаблона → wizard аварийно завершается;
  - `capabilities.list_channels()` отдаёт 4 legacy-канала как пригодные для `content_creator`;
  - `story_card_text_only_v1.workflow_binding.workflow = "news_to_short"` — неверно;
  - `config/render_presets/fullscreen_voiceover_v1.json` не существует;
  - `cli project status` падает traceback'ом на news-проекте;
  - `request.timing` / `request.voice.mode` / `request.render` не читаются ни одним workflow.
- **Предполагаемые файлы:** `src/production_catalog/catalog.py`,
  `src/content_creation/capabilities.py`, `src/content_creation/cli.py`,
  `src/content_creation/wizard.py`, `CLAUDE.md`, `COMMANDS.md`, handoff-документы,
  `tests/test_capability_consistency.py`.
- **Риски:** capability-поля читаются тестами `test_content_creation_*`; изменения должны
  быть аддитивными, чтобы не сломать существующие ожидания.
- **Acceptance criteria:** см. Задачу 1 в implementation plan.
- **Тесты:** `tests.test_capability_consistency`, `tests.test_content_creation_*`,
  `tests.test_production_catalog_foundation`, `tests.test_story_card_project_integration`.

### Итог — ЗАВЕРШЁН

**Что изменено**

- `src/production_catalog/catalog.py`
  - `longform` → `enabled=False`, `implementation_status="planned"` (у формата нет шаблонов).
  - `story_card_text_only_v1.workflow_binding` переписан на настоящий workflow
    (`story_card` / `content_creation.service` / `ProjectFactory` / `story_card_short_render`).
  - `fullscreen_voiceover_v1.implementation_status` `experimental` → `active`.
  - `fullscreen_voiceover_v1.render_preset_id` → `""` (файла preset никогда не существовало).
- `src/content_creation/capabilities.py`
  - новый тип канала `legacy_video_pipeline` и классификация по содержимому `channel_config.json`;
  - у каждого канала появились `supported_templates` и `usable_for_content_creation`;
  - новая функция `list_channels_for_template()`.
- `src/content_creation/wizard.py`
  - формат предлагается только если у него есть хотя бы один `enabled` шаблон;
  - канал предлагается только если он совместим с выбранным шаблоном.
- `src/content_creation/cli.py`
  - `project status/validate/rights-report` на news-проекте больше не падает traceback'ом,
    а объясняет разницу между `job.json` и `project.json` и возвращает код 1.
- `tests/test_capability_consistency.py` — новый (11 тестов).
- Документация: `CLAUDE.md` (entrypoints, venv-запуск, ограничения), `COMMANDS.md`
  (все команды через `./venv/Scripts/python.exe`), баннеры «исторический документ» в
  `START_HERE.md`, `CURRENT_STATE.md`, `NEXT_PLAN.md`.

**Тесты (все через `./venv/Scripts/python.exe`, `PYTHONIOENCODING=utf-8`)**

- `tests.test_capability_consistency` — 11, OK (новый).
- `test_content_creation_service`, `test_content_creation_cli`, `test_content_creation_wizard`,
  `test_production_catalog_foundation`, `test_story_card_project_integration`,
  `test_apps_structure` — суммарно 123 теста, OK.

**Что не проверялось**

- Полный набор тестов репозитория.
- Интерактивный wizard в настоящем терминале (проверен только через ScriptedAdapter в тестах).

**Известные ограничения после этапа**

- `project status` для news-проектов пока только объясняет ситуацию, но не показывает статус —
  это Stage C1.
- Экспорт под площадки по-прежнему копии master; `tiktok`/`stories` не создаются.

**API/платные вызовы:** нет. **Git commits:** нет.

**Рекомендуемый следующий этап:** Stage B1 (narration-aligned scene timing).

---

## Stage B1 — Narration-aligned scene timing

- **Цель:** видеоряд и субтитры должны идти по реальной длительности озвучки, а не по
  плановой длительности сцен.
- **Проверенные факты:**
  - `actual_duration_sec` читается в `src/news/final_renderer.py:317` и
    `src/news/subtitles.py:29`, но **не пишется ни одним модулем** (grep по `src/`);
  - `final_renderer._create_scene_segments` вообще игнорирует `actual_duration_sec` и берёт
    только `target_duration_sec`;
  - в подтверждённом живом проекте `visual_duration_sec=51.5` против
    `narration_duration_sec=59.47`; у `scene_001` план 3.5 s, реальная озвучка 7.24 s;
  - `voice_manifest.json` (schema v2) содержит `scenes[].duration_seconds` и
    `narration.pause_total_sec`; паузы формируются
    `pause_policy_for_format(format_id).clamp(scene.pause_after_sec or between_scenes_sec)`
    и вставляются между сценами (`audio_assembler.assemble_narration`).
- **Предполагаемые файлы:** новый `src/audio/scene_timeline.py`, `src/news/pipeline.py`
  (стадия `voice`), `src/news/final_renderer.py`, новый `tests/test_scene_timeline.py`.
- **Риски:** изменение `script.json` влияет на `visual_plan`, `subtitles`, `quality_check` и
  рендер. Митигация: поля только добавляются, старые остаются; при отсутствии озвучки
  поведение не меняется; существующие проекты не переписываются.
- **Acceptance criteria:** см. Задачу 2 в implementation plan.
- **Тесты:** `tests.test_scene_timeline`, `tests.test_news_to_short_renderer`,
  `tests.test_news_to_short_pipeline`, `tests.test_final_renderer_end_tail`,
  `tests.test_news_voice_adapter`.

### Итог — ЗАВЕРШЁН

**Что изменено**

- `src/audio/scene_timeline.py` — **новый** модуль (единственный источник правила
  «реальная озвучка важнее плана»):
  - `build_scene_timeline(voice_manifest, script=, format_id=)` — восстанавливает
    сцена-за-сценой реальный таймлайн из `voice_manifest.scenes[].duration_seconds`
    и пауз, которые действительно вставил `audio_assembler`;
  - `apply_timeline_to_script(script, timeline)` — аддитивно пишет `actual_duration_sec`,
    `speech_duration_sec`, `pause_after_sec`, пересчитанный `start_sec`;
    `target_duration_sec` **сохраняется** как запись плана;
  - `scene_render_duration(scene)` — общий helper для renderer и субтитров;
  - при отсутствии/незавершённости озвучки возвращается пустой таймлайн — поведение
    остаётся прежним, исключения не выбрасываются.
- `src/news/pipeline.py` — стадия `voice` после генерации манифеста записывает таймлайн
  в `script.json` и сохраняет `localizations/<lang>/voice/scene_timeline.json`.
- `src/news/final_renderer.py` — `_create_scene_segments` больше не игнорирует
  `actual_duration_sec` (раньше брал только `target_duration_sec`).
- `src/news/subtitles.py` — использует тот же общий helper.
- `tests/test_scene_timeline.py` — новый (22 теста).
- `tests/test_news_to_short_scene_timing.py` — новый (4 интеграционных теста, mock вместо TTS).

**Эффект.** Раньше: визуальный таймлайн 51.5 s против озвучки 59.47 s, сцена 001 —
план 3.5 s против реальных 7.24 s речи; субтитры делились по плановым длительностям.
Теперь сумма сцен совпадает с длительностью narration в пределах 0.05 s, а субтитры
и видеоряд считаются по одному и тому же источнику.

**Тесты**

- `tests.test_scene_timeline` — 22, OK.
- `tests.test_news_to_short_scene_timing` — 4, OK (включая регрессионный тест:
  до изменения плановая длительность была меньше narration, после — совпадает).
- Регрессия: `test_news_to_short_pipeline`, `test_news_to_short_renderer`,
  `test_final_renderer_end_tail`, `test_news_to_short_delivery`,
  `test_news_to_short_quality_check`, `test_news_to_short_models`,
  `test_capability_consistency`, `test_content_creation_service` — суммарно 72, OK.
- Отдельно ранее: `test_narration_workflow`, `test_voice_manifest_schema`,
  `test_news_voice_adapter` — OK.

**Что не проверялось**

- Настоящий ffmpeg-рендер с новыми длительностями (требует платной озвучки или готового
  проекта; существующие проекты намеренно не перезаписывались).
- Полный набор тестов репозитория.

**Известные ограничения после этапа**

- Существующие проекты не пересчитываются задним числом: таймлайн пишется только при
  следующем прогоне стадии `voice`. Это осознанно — старые артефакты не переписываются.
- Субтитры по-прежнему делятся арифметически внутри сцены (по 5 слов); word-level
  выравнивания нет — но границы сцен теперь верны.

**API/платные вызовы:** нет. **Git commits:** нет.

**Рекомендуемый следующий этап:** Stage B2 (voice profile resolution + мёртвые вопросы wizard).

---

## Stage B2 — Voice profile resolution и мёртвые вопросы wizard

- **Цель:** выбранный голос не должен теряться; wizard не должен задавать вопросов,
  которые ничего не меняют.
- **Проверенные факты:**
  - `capabilities.resolve_voice_profile('nature_pulse', 'ru_dom')` → ошибка
    «Channel has no voices.yaml», тогда как
    `voice_adapter.load_voice_profile_for_channel('nature_pulse', {}, profile_override='ru_dom')`
    → успешно `ru_dom` (проверено прямым прогоном);
  - из-за этого `wizard._resolve_profile_display` очищает `state.voice_profile` и печатает
    предупреждение, после чего override не передаётся дальше и платная генерация не проходит;
  - `request.voice.mode`, `request.timing`, `request.render` не читаются ни одним workflow;
  - `run_news_to_short_cli` не передаёт `voice_profile_override` и не имеет `--execute-voice`.
- **Предполагаемые файлы:** `src/content_creation/capabilities.py`,
  `src/content_creation/wizard.py`, `src/news/pipeline.py`, `pipeline.py`,
  `tests/test_content_creation_wizard.py`, новый `tests/test_voice_profile_resolution.py`.
- **Риски:** wizard-тесты завязаны на порядок вопросов; удаление шагов может их сломать.
  Митигация: удалять только те шаги, у которых нет потребителя, и обновлять тесты явно.
- **Acceptance criteria:** см. Задачу 3 в implementation plan.
- **Тесты:** `tests.test_voice_profile_resolution`, `tests.test_content_creation_wizard`,
  `tests.test_content_creation_cli`, `tests.test_news_voice_adapter`.

### Итог — ЗАВЕРШЁН

**Что изменено**

- `src/content_creation/capabilities.py`
  - `resolve_voice_profile` теперь ищет по цепочке «свой `voices.yaml` → все остальные»,
    ровно как `src.news.voice_adapter.load_voice_profile_for_channel`;
  - `list_voice_profiles(channel_id, include_global=True)` возвращает профили других
    каналов, если у канала нет своего файла, и добавляет `source_channel_id`;
  - `describe_template_capabilities` отдаёт `default_voice_mode` и `default_timing_mode`
    из template audio policy.
- `src/production_catalog/catalog.py` — `story_card_text_only_v1.audio_policy_id`
  подключён к уже существовавшей, но неиспользуемой политике `story_card_no_voice`.
- `src/content_creation/wizard.py`
  - убраны два мёртвых вопроса («Режим озвучки», «Режим тайминга») — их значения
    берутся из template policy; пункт «Изменить timing mode» убран из меню правки;
  - выбранный голос больше не очищается для канала без своего `voices.yaml`;
    в списке и в сводке видно, из какого канала взят профиль;
  - предупреждение теперь честное: «профиль не найден ни там, ни там».
- `src/news/pipeline.py` — `run_news_to_short_cli` пробрасывает `voice_profile_override`
  (раньше молча терялся).
- `pipeline.py` — добавлен флаг `--execute-voice` (платная генерация по-прежнему
  невозможна без approval-записи).
- `tests/test_voice_profile_resolution.py` — новый (8 тестов на паритет UI/runtime).
- `tests/test_content_creation_wizard.py` — обновлён под новый flow; тест
  «канал без voices.yaml» переписан под корректное поведение + новый тест на
  действительно неразрешимый профиль.

**Тесты**

- `tests.test_voice_profile_resolution` — 8, OK.
- `tests.test_content_creation_wizard` — 36, OK.
- Регрессия: `test_content_creation_cli`, `test_content_creation_service`,
  `test_capability_consistency`, `test_production_catalog_foundation`,
  `test_news_voice_adapter`, `test_voice_policy`, `test_voice_profile_registry`,
  `test_story_card_project_integration` — суммарно 153 теста, OK.

**Что не проверялось**

- Реальный платный прогон ElevenLabs (запрещён).
- Полный набор тестов репозитория.

**Известные ограничения после этапа**

- `src/audio/voice_cli.py:28` по-прежнему подменяет `voice_id` любого elevenlabs-профиля
  значением из окружения — при добавлении второго голоса все профили свернутся в один.
  Исправление затрагивает работу с `.env` и вынесено в отдельный этап.
- Локализационный voice override (`channel_config.languages.<lang>.voice`) всё ещё
  не читается — Stage D2.

**API/платные вызовы:** нет. **Git commits:** нет.

**Рекомендуемый следующий этап:** Stage C1 (read-only ProjectRepository).

---

## Stage C1 — Read-only ProjectRepository

- **Цель:** один read-интерфейс над обеими project-системами, чтобы `project status/list`
  работал для любого проекта и появился фундамент для UI.
- **Проверенные факты:** в `projects/` лежат 19 проектов с `job.json`, 1 с `project.json`
  и 1 (`story_card_owl_test`) без манифеста вообще; `ProjectFactory.get` знает только
  `project.json`.
- **Предполагаемые файлы:** новый `src/projects/{__init__,repository}.py`,
  `src/content_creation/cli.py`, новый `tests/test_project_repository.py`.
- **Риски:** соблазн сделать третью project-систему. Митигация: модуль строго read-only,
  без записи, без миграции, без собственного формата хранения.
- **Acceptance criteria:** см. Задачу 4 в implementation plan.
- **Тесты:** `tests.test_project_repository`, `tests.test_content_creation_cli`,
  `tests.test_project_factory`.

### Итог — ЗАВЕРШЁН

**Что изменено**

- `src/projects/repository.py` + `src/projects/__init__.py` — **новый read-only** слой:
  - `ProjectRepository.detect_kind/list/get` понимает `job.json`, `project.json` и
    папки без манифеста (`unknown`);
  - единый `ProjectView`: kind, channel, template, язык, статус, стадии, готовый MP4,
    выходные файлы, quality-статус, файлы лицензий, предупреждения;
  - модуль **ничего не пишет**, не мигрирует и не вводит собственный формат хранения —
    это адаптер, а не третья project-система;
  - объявленный, но отсутствующий на диске MP4 не выдаётся за готовый результат.
- `src/content_creation/cli.py` — `project list` (новая команда) и `project status` теперь
  работают для любого проекта; `validate`/`rights-report` честно сообщают, что пока
  требуют `project.json`; временная заглушка из Stage A заменена настоящей реализацией.
- `tests/test_project_repository.py` — новый (13 тестов, включая проверку «чтение не
  изменяет ни один файл» по mtime).
- `tests/test_content_creation_cli.py` — +6 тестов на новые команды.
- Документация: `COMMANDS.md` раздел 10.9 переписан, `CLAUDE.md` дополнен.

**Практический результат.** `project list` показывает все 21 проект с типом, каналом,
шаблоном, статусом и признаком наличия видео; `project status` для живого проекта выводит
все 12 стадий, `quality=passed`, абсолютный путь к `master_1080x1920.mp4`, 5 выходных
файлов и 3 файла доказательств прав.

**Тесты**

- `tests.test_project_repository` — 13, OK.
- `tests.test_content_creation_cli` — 20, OK.
- Регрессия: `test_project_factory`, `test_project_foundation_cli`,
  `test_project_foundation_models`, `test_content_creation_service`,
  `test_content_creation_wizard`, `test_capability_consistency`, `test_scene_timeline`,
  `test_news_to_short_scene_timing`, `test_voice_profile_resolution` —
  суммарно 168 тестов, OK.

**Что не проверялось**

- Полный набор тестов репозитория.
- Поведение на проектах с манифестами будущих схем (есть tolerant-ветка, но реальных
  примеров нет).

**Известные ограничения после этапа**

- `project validate` / `project rights-report` по-прежнему требуют `project.json`
  (единый rights-report над обеими формами evidence — Stage C2).
- Записи через общий интерфейс нет и намеренно не добавлялось.

**API/платные вызовы:** нет. **Git commits:** нет.

**Рекомендуемый следующий этап:** Stage E1 (music manifest writer).

---

## Stage E1 — Музыка: подключить уже существующий микс

- **Цель:** сделать музыку реально доступной пользователю, не создавая новый audio engine.
- **Проверенные факты:** `src/news/final_renderer.py:_mux_voice_and_music` уже выполняет
  loop + sidechain ducking + микс, но читает `assets/music/music_manifest.json`, который
  **никто не писал** (grep по `src/`); поэтому wizard был вынужден прятать опцию.
- **Риски:** новый вопрос в wizard сдвигает позиционные ответы во всех wizard-тестах.
  Митигация: тесты обновлены явно, порядок вопросов задокументирован в helper'е.

### Итог — ЗАВЕРШЁН

**Что изменено**

- `src/audio/music_manifest.py` — **новый** модуль: валидация локального трека
  (существование, расширение, непустой файл), SHA-256, размер, честная запись прав
  (`unverified_user_supplied`, `commercial_use_status: unknown`), запись и tolerant-чтение
  манифеста. Никакого ffmpeg, скачиваний или микса — только манифест.
- `src/news/final_renderer.py`
  - громкость и `ducking` берутся из манифеста, а не зашиты в фильтр;
  - добавлена ветка микса без ducking;
  - музыкальная подложка теперь покрывает **итоговую** длительность
    (`max(visual, target)`), а не только визуальный таймлайн — иначе при
    `narration_plus_tail` в конце оставался кусок без музыки;
  - `_load_music_manifest` стал тонкой обёрткой над общим tolerant-ридером.
- `src/content_creation/service.py` — пишет музыкальный манифест перед рендером;
  ошибка музыки не рушит рендер, а превращается в `stage music: needs_review` + warning
  (платная озвучка не теряется).
- `src/content_creation/capabilities.py` — `local_file` больше не
  `architecture_supported`, а `targeted_tested`, с указанием поддерживаемого шаблона
  и предупреждением о правах.
- `src/content_creation/wizard.py` — опция музыки больше не спрятана.
- `tests/test_music_manifest.py` — новый (18 тестов, включая проверку аргументов
  ffmpeg-фильтра без запуска ffmpeg).
- `tests/test_content_creation_service.py` — +2 теста; `tests/test_content_creation_wizard.py`
  — обновлён порядок ответов, тест «музыка спрятана» заменён на «музыка предлагается»
  + 2 новых теста на путь к файлу.
- Документация: `COMMANDS.md` (пример команды с музыкой и предупреждение о правах),
  `CLAUDE.md`.

**Тесты**

- `tests.test_music_manifest` — 18, OK.
- `tests.test_content_creation_wizard` — 38, OK.
- **Полный набор тестов репозитория: 645 тестов, OK** (114 s).

**Что не проверялось**

- Реальный ffmpeg-рендер с музыкой (нужен готовый проект с оплаченной озвучкой).
  Проверены аргументы фильтра, но не звучание результата.

**Известные ограничения после этапа**

- Права на музыку не проверяются автоматически и помечены как непроверенные.
- Музыка доступна только для `fullscreen_voiceover_v1` (story-card renderer пишет
  `audio=False`).
- Музыка записывается сервисом, а не отдельной стадией pipeline — намеренно, чтобы не
  менять схему `job.json` и не ломать resume у существующих проектов.

**API/платные вызовы:** нет. **Git commits:** нет.

**Рекомендуемый следующий этап:** Stage C2 (единый rights-report над обеими формами
evidence — теперь у музыки тоже есть запись о правах, которую он должен учитывать).

---

## Stage C2 — Единый отчёт о правах — ЗАВЕРШЁН

- **Цель:** одна read-only команда показывает права на все реально использованные
  материалы проекта независимо от его внутреннего формата — и честно называет то,
  что подтвердить нельзя.
- **Проверенные факты (перед реализацией):**
  - `assets/assets_manifest.json → scenes[].selected_asset` уже содержит provider,
    provider_asset_id, source_page_url, download_url, author, license, checksum_sha256,
    local_path, allowed_for_render, review_required — это единственный настоящий
    источник для 20 из 21 проекта;
  - `selected_asset.json` **не пишется никаким кодом** — это артефакт ручного
    эксперимента в `story_card_owl_test`, из плана исключён;
  - `EvidenceBundle.add()/save()` не вызывается ни одним production-кодом, и на диске
    **ноль** файлов `evidence_manifest.json` — поддержан через tolerant read, но
    реализация вокруг него не строилась;
  - `assets/missing_assets.json` пишется на каждом прогоне и содержит `scene_id` + `reason`.

### Что изменено

- `src/projects/rights.py` — **новый** read-only модуль:
  - `RightsItem`, `MissingSceneRecord`, `RightsSummary`, `ProjectRightsReport`;
  - `build_rights_report()` читает пять источников в порядке приоритета:
    assets_manifest → missing_assets → music_manifest → sources.json → evidence_manifest;
  - `classify_rights()` — единое правило статусов: `verified` только если материал
    разрешён к рендеру **и** есть лицензия, источник и checksum; частичные данные →
    `review_required`; ничего → `unknown`; явный запрет → `blocked`;
  - дедупликация по ключам checksum → provider+id → URL → asset_id → путь, с
    проверкой `contradicts()`: слабый ключ не может склеить материалы, у которых
    сильные признаки (checksum или provider+id) различаются;
  - учитываются только **выбранные** материалы; кандидаты и отклонённые — нет.
- `src/projects/__init__.py` — экспорт новых имён.
- `src/content_creation/cli.py` — `project rights-report` переписан на общий слой:
  работает для обоих типов проектов, текстовый вывод для непрограммиста, `--json`,
  коды возврата, явная оговорка, что отчёт не является юридическим подтверждением.
  Прежний вывод `EvidenceBundle.rights_report()` сохранён целиком в поле
  `evidence_bundle_report` — обратная совместимость не нарушена.
- `tests/test_project_rights_report.py` — новый (35 тестов).

### Найденный дефект (исправлен в ходе этапа)

Первая версия дедупликации сливала материалы при совпадении **любого** ключа. Два разных
клипа с одной страницы-источника, но разными checksum и provider_asset_id, схлопывались в
один. Добавлено правило `contradicts()`: более сильный признак различия всегда побеждает
более слабый признак совпадения. Покрыто отдельным тестом.

### Что отчёт показал на реальных проектах

| Статус | Проектов | Комментарий |
|---|---|---|
| `verified` | 8 | все материалы с лицензией, источником и checksum |
| `review_required` | 5 | старые проекты (18–19 июля): ассеты без `license_name`/`checksum` |
| `blocked` | 3 | dry-run проекты: 6 сцен без материала |
| `unknown` | 4 | записей о материалах нет вообще |

Два вывода, ради которых этап и делался:

1. `почему_леса_охлаждают_планету_20260718T210145` — **готовый MP4 существует, но права
   по его материалам подтвердить нельзя**: старая схема манифеста не записывала лицензию
   и контрольную сумму.
2. `project-61958823` (story card, MP4 готов) — **ноль записей о правах**: story-card
   workflow не сохраняет provenance выбранного файла.

### Тесты

- `tests.test_project_rights_report` — 35, OK.
- Регрессия: `test_project_repository`, `test_content_creation_cli`, `test_evidence_bundle`,
  `test_project_foundation_cli`, `test_project_factory`, `test_news_to_short_quality_check`,
  `test_music_manifest`, `test_asset_foundation_models`, `test_attribution_export` — 123, OK.
- **Полный набор: 680 тестов, OK** (126 с).

### Что не проверялось

- Проекты с непустым `evidence_manifest.json` на реальном диске — таких не существует;
  ветка покрыта только тестом на tempfile.

### Известные ограничения после этапа

- Отчёт показывает только то, что записано. Он не проверяет страницы провайдеров и не
  подтверждает права юридически.
- Голос как отдельный лицензируемый объект не учитывается (осознанно вне рамок этапа).
- Story-card проекты будут давать пустой отчёт, пока workflow не начнёт записывать
  provenance — это отдельная задача.
- Исторические документы (`CLI_CHEATSHEET.md`, `HANDOFF_MANIFEST.json`, `REPO_SNAPSHOT.md`)
  намеренно не трогались — вынесено в отдельную задачу.

**API/платные вызовы:** нет. **Сеть:** нет. **Git commits:** нет.
**Пользовательские проекты не изменялись** (подтверждено тестом read-only по mtime и
сравнением списка файлов до/после прогона CLI).

**Рекомендуемый следующий этап:** записывать provenance в story-card workflow — сейчас это
единственный шаблон, по которому система физически не может доказать право использования
материала. Второй кандидат — LLM-сценарий (см. отдельное обсуждение), он важнее для
качества продукта, но требует платного API.

---

## Stage V1 — Живая проверка Scene Timeline и Music Mix — ЗАВЕРШЁН

**Статус: PASS_WITH_WARNINGS.** Validation stage: Python-код не изменялся (подтверждено
mtime — последняя правка любого файла в `src/`/`tests/` — 21:03, до начала этапа).

### Что проверялось

Настоящим локальным FFmpeg-рендером на **копии** завершённого проекта:
`src/audio/scene_timeline.py`, `src/news/final_renderer.py`, `src/audio/music_manifest.py`,
`src/news/subtitles.py`, `src/audio/end_tail_policy.py`.

Проект: `projects/в_видео_используются_архивные_стоковые_материалы_карты_авторская_20260724T214350`
(103 файла, `narration.wav` 59.47 с, 6 скачанных ассетов, `quality_report.status=passed`,
готовый master MP4). Выбран потому, что его финальный рендер выполнен **24–25 июля 01:21–01:22**,
то есть **старым кодом** — модули B1/E1 изменены 25 июля 16:10–16:33. Это давало прямое
сравнение «до/после» на одних и тех же исходных данных.

### Изоляция

Две независимые копии в scratchpad-каталоге (`.../v1_render_validation/{no_music,with_music}/`),
все пути внутри манифестов переписаны на копию, поэтому рендер физически не мог обратиться
к оригиналу. Отпечаток оригинала (103 файла: размер, `mtime_ns`, sha256 всех JSON/SRT/ASS/TXT,
`narration.wav`, `master_1080x1920.mp4`) снят до и после: **added=0, removed=0, changed=0.**

### Результат: тайминг сцен

| | старый рендер | новый рендер |
|---|---|---|
| visual_duration_sec | 51.50 | **59.475** |
| narration_duration_sec | 59.475 | 59.475 |
| target_duration_sec | 60.225 | 60.225 |
| фактическая длительность MP4 | 60.233 | 60.233 |

Границы сцен теперь совпадают с реальной озвучкой (проверено попиксельным сравнением кадров
до/после каждой границы; порог смены кадра — mean diff > 25):

| граница | mean diff | вердикт |
|---|---|---|
| 7.59 (новая) | 60.0 | СМЕНА |
| 10.50 (старая плановая) | 19.3 | нет смены |
| 20.50 (старая плановая) | 20.7 | нет смены |
| 22.41 / 31.80 / 41.42 / 52.45 (новые) | 69.7 / 78.6 / 107.8 / 88.9 | СМЕНА |

Расхождение итога с целевой длительностью: `|60.2333 − 60.2248| = 0.0085 с` — в 35 раз
меньше критерия 0.3 с. Хвост 0.75 с — застывший последний кадр (`tpad=stop_mode=clone`),
подтверждено: кадры 59.9 и 60.15 идентичны (mean diff 0.001).

Timeline монотонный, сцены не пересекаются, id сцен в `script.json` и `voice_manifest.json`
совпадают один-в-один, дубликатов нет. Предупреждение самого модуля отработало штатно:
сумма сцен 59.690 с против narration 59.475 с → последняя сцена сокращена на 0.215 с.

### Результат: субтитры

6 реплик, ровно по границам нового timeline (Δstart = Δend = 0.00 для всех шести),
без отрицательных и пересекающихся timestamp, последняя заканчивается на 59.475 с —
внутри видео. Вжигание подтверждено численно: mean |master − no_subtitles| = 2.4–4.3
на отрезке 5–59 с и 0.585 (шум перекодирования) после 59.475 с.

### Результат: музыка

Fixture: синтетический тон 220 Гц, 10 с, создан только во временной папке,
`source=test_fixture`, `verification_status=test_fixture`. Пользовательская музыка не
использовалась, в медиатеку ничего не добавлялось.

- Музыкальный вход присутствует в FFmpeg-команде, `volume=0.100` взят из манифеста;
- `aloop=loop=-1` + `atrim=0:60.225` — трек 10 с покрывает 60 с (в окне 52.1 с звучит
  6-й проход петли, уровень тот же);
- **ducking работает:** изолированный замер ducked-дорожки против эталона той же
  громкости — **−7.9 / −7.7 / −7.2 дБ** в окнах речи (3–6 с, 25–28 с, 58–59.4 с) и
  **0.0 дБ** в паузах между сценами (полное восстановление за 0.35 с);
- аудиодорожка присутствует, 48 кГц, AAC 192k.

**Субъективное качество звучания не проверялось** — прослушивания не было, только
технические замеры уровней.

### Дефекты

**W1 (предупреждение, новое). Хвост ролика 0.758 с остаётся без музыки.**
`_mux_voice_and_music` намеренно готовит бед на всю итоговую длительность
(`atrim=0:60.225`, комментарий «The bed must cover the *final* duration»), но финальный
`amix=inputs=2:duration=first` обрезает микс по длине голоса. ffprobe: video 60.233 с,
audio 59.475 с. Собственное намерение кода не достигается.
Минимальное исправление — одна строка в `src/news/final_renderer.py`
(`duration=first` → длительность, покрывающая tail, либо `apad` голоса до target).
Требуется отдельный repair-этап; в V1 не исправлялось.

**W2 (предупреждение, существовало до B1/E1). Субтитры показывают только первые
5 слов каждой сцены.** `src/news/subtitles.py:34` берёт `on_screen_text` раньше
`narration`, а `script_generator._screen_text` возвращает первые 5 слов. В результате
одна реплика висит всю сцену — теперь до 14.8 с вместо прежних 7 с, то есть новый
тайминг сделал уже существующий дефект заметнее. Относится к этапу Q3 роадмапа.

Дефектов класса FAIL (рассинхрон, обрыв аудио, повреждённый MP4, изменение оригинала,
использование старых плановых длительностей) не обнаружено.

### Тесты

`tests.test_scene_timeline`, `test_news_to_short_scene_timing`, `test_music_manifest`,
`test_news_to_short_renderer`, `test_final_renderer_end_tail`, `test_end_tail_policy` —
**60 тестов, OK.** Модуля `tests.test_news_to_short_subtitles` в репозитории нет;
вместо него взят `test_end_tail_policy`. Полный набор не запускался: Python-код не менялся.

### Артефакты

`v1_scene_timeline_music_validation.mp4` в обеих копиях, логи всех 9 FFmpeg-вызовов
(argv, exit code, время) и render-манифесты — в scratchpad-каталоге сессии.
Все 18 вызовов FFmpeg (9 на копию) завершились с кодом 0.

**API/платные вызовы:** нет. **Сеть:** нет. **TTS/Vision/downloads:** нет.
**Git write:** нет. **Оригинальный проект не изменялся** (отпечаток 103 файлов идентичен).

**Рекомендуемый следующий этап:** C3 — Story Card provenance (V1 прошёл).
Отдельно — маленький repair-этап по W1.

---

## Stage W1 Repair — Музыка не покрывала end tail — ЗАВЕРШЁН

Закрывает предупреждение W1, найденное этапом V1.

### Причина (подтверждена по коду)

`src/news/final_renderer.py::_mux_voice_and_music` готовил бед на всю итоговую
длительность (`atrim=0:{max(visual, target)}`) — и это работало. Но финальный
`amix=inputs=2:duration=first` завершает микс вместе со **своим первым входом**,
а первым входом был неподбитый голос. Итог: аудиодорожка обрывалась на длине
narration, и хвост оставался абсолютно тихим, несмотря на подготовленный бед.
Собственный комментарий в коде («The bed must cover the *final* duration»)
описывал намерение, которое `duration=first` отменял.

`_mux_voice_only` не трогался: без музыки хвост нечем заполнять, тишина там — это
и есть смысл tail-политики.

### Исправление (7 строк кода + комментарий)

В обеих ветках (`ducking=True/False`) голосовая цепочка дополнена
`apad=whole_dur={duration_arg}` — тем же значением, что уже используется для беда:

```
[1:a]volume=1.0,aresample=48000,apad=whole_dur=60.225,asplit=2[voice_mix][voice_sidechain]
```

Почему именно так, а не `duration=longest`: в ducking-ветке микс собирается из
`musicduck`, то есть из выхода `sidechaincompress`, а тот ограничен своим
sidechain-входом — голосом. Смена режима `amix` не удлинила бы ducked-дорожку.
Подбивка голоса лечит обе ветки одной правкой и дополнительно подаёт в sidechain
тишину на хвосте, поэтому бед там поднимается до полного уровня, а не остаётся
приглушённым. Когда narration уже длиннее выхода, `apad` — no-op, поэтому рендеры
без хвоста не меняются вообще.

### Доказательство A/B (одни и те же входные данные, реальный FFmpeg)

| | video | audio | разрыв | хвост 59.55–60.20 |
|---|---:|---:|---:|---|
| до исправления | 60.233 | 59.475 | **0.758 с** | **звука нет** |
| после исправления | 60.233 | **60.225** | 0.008 с | **−43.0 дБ** |

−43.0 дБ — это ровно уровень неприглушённого беда, измеренный в V1, то есть
музыка на хвосте звучит в полную силу. Уровень в теле ролика не изменился
(25–28 с: −23.7 дБ до и после) — основной микс не задет.

### Повторная живая проверка (свежая копия проекта V1)

9 вызовов FFmpeg, все с кодом 0, 40.9 с. `status=completed`,
`visual_duration_sec=59.475`, `target_duration_sec=60.2248`.
ffprobe: h264 1080×1920 30 fps, AAC 48 кГц, **video 60.233 / audio 60.225**
(`|60.2333 − 60.2248| = 0.0085 с`, критерий 0.3 с).
Субтитры — 6 реплик, ровно по границам сцен, `problems: none`.
Ducking в паузах между сценами сохранился (замеры совпадают с V1 до дециБела).

**Оригинальный проект не изменялся:** отпечаток 103 файлов идентичен снятому до V1
(added=0, removed=0, changed=0).

### Тесты

Добавлены 4 регрессионных теста:

- `tests/test_music_manifest.py` — `test_narration_is_padded_so_the_mix_covers_the_tail`
  (обе ветки ducking), `test_padding_matches_the_bed_length_exactly`,
  `test_padding_is_applied_to_the_sidechain_too` — без запуска FFmpeg;
- `tests/test_final_renderer_end_tail.py::MusicCoversEndTailTests` — **настоящий рендер**:
  narration 3 с, бед 1 с (проверяет и петлю), выход 3.75 с; проверяется, что
  аудиопоток доходит до конца видео и что хвост не тихий.

Тон-фикстуры генерируются в tempfile (тишина сделала бы проверку «бед присутствует»
бессодержательной). Сети, TTS, downloads и платных вызовов нет.

Прогоны: targeted (`test_scene_timeline`, `test_news_to_short_scene_timing`,
`test_music_manifest`, `test_news_to_short_renderer`, `test_final_renderer_end_tail`,
`test_end_tail_policy`, `test_news_to_short_pipeline`, `test_audio_assembler`) — 74, OK.
**Полный набор: 684 теста, OK** (135 с; было 680 до этого этапа).
В выводе присутствует посторонний шум `AttributeError: 'FFMPEG_AudioReader' object has
no attribute 'proc'` — это сборка мусора moviepy в несвязанных тестах, существовала
раньше и на результат не влияет (`final_renderer` moviepy не использует).

### Изменённые файлы

- `src/news/final_renderer.py` — только `_mux_voice_and_music`;
- `tests/test_music_manifest.py`, `tests/test_final_renderer_end_tail.py`.

**API/платные вызовы:** нет. **Сеть:** нет. **Git write:** нет.

**Оставшееся из V1:** W2 (субтитры показывают первые 5 слов сцены) — не трогалось,
относится к этапу Q3 роадмапа.

**Рекомендуемый следующий этап:** C3 — Story Card provenance.

---

## Stage C3 — Story Card Asset Provenance — ЗАВЕРШЁН

Закрывает дыру, найденную этапом C2: story card делал готовое видео, а
`project rights-report` показывал по нему ноль материалов.

### Фактический путь (проверен по коду перед изменениями)

```
ContentCreationRequest.source_asset_path (--source-asset)
  → service._create_story_card
    → ProjectFactory.create            (project.json + пустая папка evidence/)
      → prepare_story_card_render      ← здесь резолвится конкретный Path
        → render_story_card_short(source_video=…)
```

**Установленный факт:** единственный источник материала сегодня — локальный путь из
`--source-asset`. Провайдерского пути у этого шаблона нет: `service` требует
`source_asset_path`, поиск ассетов в workflow не подключён. Файл никуда не копируется
и не преобразуется — renderer получает ровно тот файл, на который указал пользователь.
Поэтому checksum берётся с него, а provider-ветка сделана как приём уже готового
provenance, а не как предположение о будущем источнике.

### Что изменено

**1. `EvidenceRecord` — схема v2 (`src/project_foundation/models.py`).**
Добавлено 10 необязательных полей: `media_role`, `media_type`, `source_type`,
`provider_asset_id`, `download_url`, `author_url`, `allowed_for_render`,
`review_required`, `provenance`, `technical_validation`.

Границу расширения выбирал не произвольно: это ровно то, что уже моделируют
`src.projects.rights.RightsItem` (единый отчёт) и `src.assets.models.AssetLicense`/
`AssetProvenance` (канонический контракт провайдеров) и чего запись v1 не могла
выразить без потерь. **Второй `rights_status` намеренно не заведён** —
`verification_status` и есть статус прав, дубль позволил бы им разойтись.
Введён отдельный `EVIDENCE_RECORD_SCHEMA_VERSION = 2`, чтобы не пере-версионировать
`ProjectManifest`/`ChannelProfile`, формат которых не менялся.
Записи v1 читаются без изменений: недостающие флаги берут ровно те значения, которые
единый отчёт раньше выводил из `verification_status`.

**2. Адаптер `src/assets/evidence_adapter.py` (новый).**
Превращает «файл, который получил renderer» в `EvidenceRecord`. Принимает
`AssetCandidate`/`DownloadedAsset`/dict/`None`. Checksum всегда считается с файла на
диске; если у ассета записан другой checksum, побеждает файл, а расхождение
записывается в `notes`, а не скрывается. Статус для provider-ассета определяет
**та же** `src.projects.rights.classify_rights`, что и единый отчёт — второй копии
правила не появилось. `technical_validation` заполняется существующим
`validate_local_asset` (ffprobe/Pillow, локально), при неудаче — честный
`status=failed`, а не отказ записать материал.

**3. `src/templates/story_card/integration.py`.**
Новый необязательный параметр `source_asset` (богатый объект) рядом с
`source_asset_path` (какой файл рендерить). Evidence пишется в существующий
`evidence/evidence_manifest.json` через `EvidenceBundle` в момент, когда проект
фиксирует конкретный файл — вместе с `render_request`, до рендера. В `render_request`
добавлены `evidence_id` и `source_asset_checksum_sha256`: вход рендера и запись о
правах связаны явно. Фиксированный `evidence_id = "visual_source_asset"` — у шаблона
ровно один визуал, повторный рендер обновляет запись, а не плодит дубликаты.
При `dry_run` не пишется ничего.

**4. `src/projects/rights.py`.** `_item_from_evidence_record` читает поля v2 и
сохраняет прежнее поведение для v1. `media_role` больше не захардкожен в `other`.
Для `source_type=user_supplied` добавляется предупреждение о непроверенных правах.
Константы `MEDIA_ROLE_*` переехали к `EvidenceRecord` и ре-экспортируются отсюда,
чтобы хранимые записи и отчёт не разошлись.

**5. Вывод для пользователя.** `create` и wizard печатают четыре строки:
`rights_status`, `evidence_path`, `source_type`, `review_required`. Детали лицензий
не дублируются — они в `project rights-report`.

### Правила, зафиксированные тестами

- Локальный файл: `provider=user_supplied`, `source_type=user_supplied`,
  `commercial_use_status=unknown`, `verification_status=review_required`.
  **Никогда не `verified`.** Лицензия, автор и источник остаются пустыми — по имени
  файла и папке ничего не угадывается.
- Provider-ассет: provider, asset id, source page, download url, автор, лицензия,
  `provenance` и `technical_validation` переносятся дословно.
- Checksum — всегда с файла, переданного renderer.

### Проверка вживую (реальный CLI, реальный рендер)

Создан проект в отдельном временном `--projects-root`, исходник — свой mp4:

```
[create] status=completed
[create] output_resolution=1080x1920
[create] rights_status=требует проверки
[create] source_type=user_supplied
[create] review_required=да
```

`project rights-report` по нему: «Всего материалов: 1 (визуал 1)», статус
«требует проверки», подтверждено 0, файл найден, checksum в манифесте совпадает с
sha256 исходного файла (`482ae0a7…`), `technical_validation` содержит реальные
данные ffprobe. Код возврата 0 — отчёт информационный.

Старый story-card проект `projects/project-61958823` читается по-прежнему, отчёт
честно пуст, отпечаток 7 файлов идентичен до и после (added/removed/changed = 0).
Ни один файл в `projects/` за этап не изменился.

### Тесты

Новый модуль `tests/test_story_card_provenance.py` — **24 теста**: адаптер
(user_supplied, checksum, provider без потерь, dict==объект, подмена файла,
отсутствующий файл, неверный тип), схема (v1 читается, round-trip v2), workflow
(запись, связь с render_request, повторный рендер, provider, dry_run, ошибка,
неизменность файла пользователя, сводка в результате), единый отчёт (видит запись,
user_supplied не `verified`, provider может быть `verified`, старый проект,
запись v1). Все на tempfile и mock-объектах; сети, downloads, Vision, TTS и платных
вызовов нет.

Регрессия: `test_story_card_project_integration`, `test_evidence_bundle`,
`test_project_rights_report`, `test_project_foundation_models`,
`test_project_foundation_cli`, `test_project_factory`, `test_project_repository`,
`test_content_creation_service`, `test_content_creation_cli`,
`test_content_creation_wizard`, `test_story_card_short_renderer` — 195, OK.
**Полный набор: 708 тестов, OK** (141 с; было 684).

### Изменённые файлы

`src/project_foundation/models.py`, `src/assets/evidence_adapter.py` (новый),
`src/templates/story_card/integration.py`, `src/projects/rights.py`,
`src/content_creation/{service,cli,wizard}.py`,
`tests/test_story_card_provenance.py` (новый).

**API/платные вызовы:** нет. **Сеть:** нет. **Downloads/Vision/TTS:** нет.
**Git write:** нет. **Пользовательские проекты и файлы не изменялись.**

### Осознанно вне рамок этапа

- Старые проекты не мигрируются: у них по-прежнему нет evidence, и отчёт об этом
  говорит прямо.
- `ContentCreationRequest` не получил поле для богатого ассета — сегодня его некому
  заполнить. API интеграции его принимает, так что подключение поиска ассетов к
  story card не потребует менять формат хранения.
- Восстановление provenance по media library (если файл уже лежит в библиотеке) не
  делалось: это отдельный источник со своим форматом индекса.
- Голос как отдельный лицензируемый объект по-прежнему не учитывается.

**Рекомендуемый следующий этап:** B3 — название проекта, читаемые папки, Resume.

---

## Stage B3 — Название проекта, читаемые идентификаторы и Resume — ЗАВЕРШЁН

### Что было проверено по коду перед изменениями

| Место | Как строилось имя | Что получалось |
|---|---|---|
| `NewsJob.create` | `slugify(topic or input_text)` + компактный timestamp, кириллица сохранялась как есть | `wizard_установил_questionary_единственная_подходящая_библиотека__20260724T210156` — первые 80 символов вставленного сценария |
| `ProjectFactory._slugify` | `re.sub(r"[^a-z0-9]+", "-")` по уже приведённой к нижнему регистру строке | любое русское название схлопывалось в пустоту → `project-61958823` |
| Wizard | название не спрашивалось вовсе | — |
| Wizard | продолжения проекта не было | незавершённый проект найти было нечем |

Дополнительно найдено при разборе resume: `build_or_generate_voice_manifest(execute=False)`
**перезаписывает** `voice_manifest.json` заглушкой (`build_safe_voice_manifest`). То есть
повторный проход по стадии `voice` без подтверждения оплаты не просто не генерировал
заново — он **стирал запись о готовой озвучке**, которая физически лежала на диске.

### Что изменено

**1. `src/project_foundation/naming.py` (новый).** Одно место, которое отвечает на вопрос
«как назвать папку». Чистые функции, без I/O: проверку занятости передаёт вызывающий,
потому что только он знает свой корень.

Формат: `YYYY-MM-DD_transliterated-title`. Дата первой — папки сортируются по времени,
что и делает человек, который ищет «ролик, который я делал во вторник».

- транслитерация кириллицы (плюс `і/ї/є/ґ/ў`, которые попадают из скопированного текста);
- обрезка по границе слова, максимум 48 символов у слага и ≤ 64 у всего id;
- запрещённые для Windows символы и зарезервированные имена (`con`, `lpt1`, …);
- уникальность: `-2`, `-3`, … и только после 99 совпадений — случайный суффикс;
- `suggest_title()` — первое предложение темы или вставленного сценария для подстановки
  в вопрос мастера.

**2. Название стало отдельным полем.** `NewsJob.title` (необязательное — старый `job.json`
читается без изменений), `create_news_to_short_job(title=...)`, `service` передаёт
`request.title`. `topic` остался входом пайплайна и не менялся.

**3. Уникальность проверяется по реальному корню.** `ProjectFactory.create` — против своих
папок; `create_news_to_short_job` — против **всех** папок в `projects/`, включая проекты
другой системы хранения, чтобы новый проект не мог записаться внутрь существующего.

**4. `ProjectView` получил `last_completed_stage` и `is_finished`.** Оба read-only,
`is_finished` определяется наличием готового файла, а не флагом статуса. `title` теперь
берётся из `job.title` с откатом на `topic` для старых проектов.

**5. Мастер.**
- Первый вопрос: «Создать новый ролик» / «Продолжить незавершённый проект».
- Вопрос о названии с подстановкой + строка «Папка проекта будет называться: …»,
  пункт «Изменить название» в меню сводки.
- Список продолжения: название, стадия остановки по-русски, дата; сортировка по
  последнему изменению. Завершённые не показываются. Проекты нерезюмируемых шаблонов
  отфильтрованы с честным пояснением, а не с обещанием, которое сорвётся.
- При продолжении канал, шаблон, язык, название и наличие субтитров **читаются из
  проекта**, а не спрашиваются заново. Музыка не спрашивается вообще: renderer сам читает
  существующий music manifest.

**6. Готовая озвучка защищена.** `service._completed_narration` требует и записи в
манифесте, и реально существующего файла. Если озвучка есть — стадия `voice` не
запускается вовсе (статус `skipped_existing_audio`), платное подтверждение не
запрашивается. Манифест, указывающий на удалённый файл, готовым не считается.

**Границы этапа соблюдены:** `workspace/` не вводился, внутренняя структура папок не
менялась, миграции не было, существующие проекты не переименовывались.

### Проверка вживую

```
[create] project_id=2026-07-25_pochemu-vorony-zapominayut-chelovecheskie-lica
```

`project list` по настоящему `projects/`: все 21 проект читаются как раньше.
Отпечаток 853 файлов до и после — идентичен (added/removed/changed = 0).

### Тесты

Новый `tests/test_project_naming_and_resume.py` — **35 тестов**: транслитерация (включая
полный алфавит и верхний регистр), запрещённые символы и зарезервированные имена, обрезка
по границе слова, fallback, формат и детерминированность id, счётчик коллизий, длина;
`suggest_title`; `NewsJob` (сценарий больше не даёт имя папки, title важнее topic, старый
`job.json` без `title`, две задачи в один день); `ProjectView` (последняя стадия, признак
завершённости, откат title на topic); мастер (подставленное и введённое название, resume
с тем же id и без повторных вопросов, ярлык со стадией, завершённые не предлагаются,
пустой список → создание нового); защита озвучки (стадия не запускается, манифест
байт-в-байт цел, платный гейт не срабатывает, удалённый файл не считается готовым).

В `tests/test_project_factory.py` добавлены 2 теста (коллизия названий, транслитерация)
и обновлён 1: он проверял старый формат `auto-generated-id-<hex>` — теперь проверяет
`YYYY-MM-DD_auto-generated-id`. `ScriptedAdapter` в тестах мастера получил
`auto_title` (по умолчанию включён): вопрос о названии предзаполнен, и «нажать Enter» —
это и есть поведение пользователя, поэтому все существующие сценарии остались валидны.

**Полный набор: 745 тестов, OK** (142 с; было 708).

### Изменённые файлы

`src/project_foundation/naming.py` (новый), `src/project_foundation/projects.py`,
`src/news/models.py`, `src/news/pipeline.py`, `src/projects/repository.py`,
`src/content_creation/{service,wizard}.py`,
`tests/test_project_naming_and_resume.py` (новый), `tests/test_project_factory.py`,
`tests/test_content_creation_wizard.py`, `COMMANDS.md`.

**API/платные вызовы:** нет. **Сеть:** нет. **TTS/Vision/downloads:** нет.
**Git write:** нет. **Существующие проекты не переименованы и не изменены.**

### Осознанно вне рамок этапа

- Resume поддерживает только `fullscreen_voiceover_v1`. У story card нет стадий, а для
  повторного запуска нужны исходный файл и текст карточки, которых нет в `ProjectView`.
- Повтор одной конкретной упавшей стадии из мастера не добавлялся — сейчас продолжение
  идёт с первой незавершённой.
- `topic` для вставленного сценария по-прежнему обрезается до 80 символов: он больше не
  влияет на имя папки, но попадает в заголовок сценария. Это территория этапа Q1.
- `src.news.models.slugify` осталась в коде, хотя больше не используется, — удаление
  публичной функции выходит за рамки этапа именования.

**Рекомендуемый следующий этап:** Q1 — движок сценария.

---

## Git

Все изменения оставлены **незакоммиченными**. Причина: рабочее дерево содержит большой
объём чужого untracked-кода (`src/content_creation/`, `src/news/`, `src/audio/`,
`apps/`, `anime_factory/`, десятки тестов), который существовал до этой сессии. Файлы,
которые я менял, в большинстве своём untracked целиком — коммит любого из них затянул бы
в историю неотносящуюся к этапу реализацию, что запрещено правилами. Единственный
tracked-файл с моими правками — `pipeline.py` (+5 строк: флаг `--execute-voice`).

Полный список изменённых/созданных мной файлов приведён в разделах «Что изменено»
каждого этапа выше.
