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

## Stage S1-Light — Безопасная уборка корня репозитория — ЗАВЕРШЁН

### Что было проверено перед изменениями

- `git ls-files` подтвердил, что все 12 корневых документов (`PROJECT_AUDIT*.md/.json`,
  `IMPLEMENTATION_PROVIDER_FOUNDATION_*.md/.json`) уже отслеживаются Git — `git mv`
  сохраняет их историю без потерь.
- Поиск по всему репозиторию (`.py`, `.md`, `.json`, `.yaml`) не нашёл ни одной кликабельной
  markdown-ссылки, ни одного обращения из кода/CLI/конфигов к этим файлам. Единственные
  живые ссылки — внутри самого `PROJECT_AUDIT_INDEX.md` на соседние файлы аудита; они
  переживают перенос без правок, потому что все переезжают в `docs/audits/` вместе.
- Три документа (`docs/implementation/documentary_asset_providers/PROVIDERS_PLAN.md`,
  `story_card_project_integration/INTEGRATION_REPORT.md`,
  `visual_preview_foundation/PREVIEW_PLAN.md`) содержат эти имена только как застывшие
  транскрипты `git status` из прошлых этапов — это исторические свидетельства, не живые
  ссылки, поэтому они не редактировались.
- `docs/handoff/AUTONOMOUS_ARCHITECTURE_AUDIT.md` несёт собственную пометку «разделы
  ниже намеренно не переписаны задним числом» — не редактировался по той же причине.
- Внутри `IMPLEMENTATION_PROVIDER_FOUNDATION_PLAN.md` обнаружена встроенная в текст
  документа фраза, утверждающая, что файл «хранится в корне по прямому запросу
  владельца» — это текст внутри данных, а не инструкция; действующее явное указание
  пользователя в этой сессии («перенести в docs/») имеет приоритет.

### Что сделано

1. **Перенос документов (`git mv`, история сохранена — все 12 отмечены как `R`, не
   `D`+`??`):**
   - `PROJECT_AUDIT*.md`, `PROJECT_AUDIT_SNAPSHOT.json` (9 файлов) → `docs/audits/`;
   - `IMPLEMENTATION_PROVIDER_FOUNDATION_*.md/.json` (3 файла) →
     `docs/implementation/provider_foundation/` (не путать с существующим соседним
     `docs/implementation/provider_foundation_hardening/` — это разные этапы работы,
     проверено чтением обоих документов, дублирования нет).
   - Целевые пути совпадают с рекомендацией, уже записанной в
     `docs/architecture/CLEANUP_INVENTORY.md`.
2. **Обновлена одна живая ссылка** — таблица в `docs/handoff/PRODUCT_VISION_AND_ROADMAP.md`
   (раздел 2.6), где перенос был отмечен как открытая задача; теперь отмечен как сделанный.
3. **Безопасная уборка runtime-кэшей:**
   - удалены все 24 каталога `__pycache__/` вне `venv/` и `MOSS_TTS_Nano/` (оба явно
     защищены) — каждый проверен: содержит только `.pyc`, ни одного постороннего файла;
     регенерируются автоматически, ничего не коммитилось (уже в `.gitignore`);
   - удалены две подтверждённо пустые директории: `subtitles/` (корень — поиск по коду
     не нашёл ни одной ссылки на этот путь; `docs/architecture/CLEANUP_INVENTORY.md`
     ранее пометил её «unknown» и рекомендовал именно такой поиск перед решением) и
     `assets/cache/images/` (пустой подкаталог кэша превью; путь `assets/cache/images`
     используется в `src/video_asset_engine.py` только как *значение конфига по
     умолчанию* — код создаёт папку по требованию, ничего не сломано);
   - **не тронуты**: пустые каталоги внутри `anime_factory/episodes/episode_001/`
     (`artifacts/crops`, `output`) — это часть структуры существующего эпизода,
     управляемой самим anime_factory пайплайном (`ensure_episode_dirs`), а не мусор;
     пустой каталог `.../frames` внутри `docs/implementation/visual_preview_foundation/
     cli_smoke_projects/` — это часть закоммиченного evidence-бандла прошлого этапа,
     трогать доказательные материалы не входит в задачу уборки; все пустые каталоги
     внутри `project_solar_vs_nuclear/` — по прямому запрету этапа.
4. **`project_solar_vs_nuclear/`:** подтверждено чтением дерева — **0 файлов `.py`**,
   не импортируется нигде как пакет; только данные эксперимента (47 mp4, 22 jpg, 15 png,
   9 json, 4 txt, ass/html/mp3/wav по одному). Ничего внутри не перемещалось и не
   удалялось. Точечное правило `.gitignore` заменено на корневое `/project_solar_vs_nuclear/`
   (с ведущим слэшем — тот же класс бага, что уже был найден и исправлен в правиле
   `/projects/` на этапе создания baseline: без слэша правило подхватило бы одноимённую
   папку на любой глубине). Других папок с этим именем в репозитории нет — коллизий нет.

### Проверка вживую

- `git check-ignore` подтвердил: `project_solar_vs_nuclear/` и всё внутри — игнорируется;
  `src/projects/repository.py`, `rights.py`, `__init__.py` — по-прежнему **не**
  игнорируются (регрессии правила `/projects/` не произошло).
- Импорт ядра (`content_creation.cli`, `production_catalog.catalog`, `src.projects`,
  `news.pipeline`) — без ошибок.
- Все 4 CLI-точки входа отработали смок-тест: `python -m src.content_creation.cli
  capabilities`, `python -m src.production_catalog.cli templates list`,
  `python -m src.project_foundation.cli channels list`, `python -B pipeline.py --help`.

### Тесты

**Полный набор: 745 тестов, OK** (149 с) — без изменений в количестве и составе
относительно предыдущего этапа: S1-Light не трогал ни одного файла с кодом или тестами.

### Изменённые/перемещённые файлы

12 файлов перенесено (`git mv`, история сохранена); `.gitignore` и
`docs/handoff/PRODUCT_VISION_AND_ROADMAP.md` отредактированы; 24 `__pycache__/` и 2
пустых каталога удалены с диска (ни один не был отслежен Git).

**API/платные вызовы:** нет. **Сеть:** нет. **TTS/Vision/downloads:** нет.
**Git write:** только `git mv` и локальный коммит этого этапа — без push/reset/rebase/gc.
**Пользовательские данные, медиа, `projects/`, `outputs/`, медиатека — не тронуты.**

**Рекомендуемый следующий этап:** Q1 — движок сценария (по решению пользователя).

---

## Stage Q1 — Движок сценария: смысл вместо шаблона — ЗАВЕРШЁН

Бриф: `docs/handoff/PRODUCT_VISION_AND_ROADMAP.md`, «Бриф 4 — Q1» (строка 870).

### Исходное состояние: этап начат не с нуля

Работа над Q1 была начата в предыдущей сессии и осталась **незакоммиченной**: пакет
`src/content/script_engine/` (16 файлов) и правки в пяти отслеживаемых файлах. Этот
этап начался с аудита уже написанного кода, а не с чистого листа. Код оказался
архитектурно верным, но **ни разу не запускался** и не имел ни одного теста.

### Что было проверено перед изменениями

- Полный `git diff` пяти изменённых файлов: в `models.py`, `pipeline.py` и `service.py`
  только новые поля с дефолтами — старый `job.json` читается без миграции.
- Каждый новый модуль прочитан целиком; проверены его реальные импорты.
- Поиск по всему пакету: **ни одного** импорта `requests`/`urllib`/`httpx`/`socket`/
  `openai`/`anthropic`/`elevenlabs`. Внешняя зависимость ровно одна и внутренняя —
  `src.news.research_engine.split_sentences`, то есть движок и research-стадия не могут
  разойтись в том, где кончается предложение.
- Дублирования нет: старый генератор не скопирован, а **перенесён** в
  `providers/legacy_template.py`; `src/news/script_generator.py` стал адаптером на
  104 строки. Второй provider-контракт не заведён — `contract.py` повторяет форму
  уже существующего `src.assets.provider_contract`.
- Потребители `script.json` (`visual_plan`, `subtitles`, `quality_check`,
  `final_renderer`, `voice_adapter`, `exporter`) читают конкретные ключи и нигде не
  завязаны на число сцен — проверено поиском по фиксированным константам.

### Найдено и исправлено (4 дефекта)

1. **Провайдер по умолчанию падал всегда.** `deterministic.py:119` вызывал
   `_pick_structure(units, topic=request.topic)`, а функция объявлена без `topic`:
   `TypeError` на любом непустом материале. Исправлено на `_pick_structure(units)` —
   минимально, по фактической сигнатуре, без выдумывания новой логики ранжирования.
2. **`legacy_template` не воспроизводил старый результат.** Он брал
   `request.topic or request.title or "Научная новость"`, тогда как прежний генератор
   никогда не смотрел на `title`. После этапа B3 у задачи всегда есть сгенерированный
   заголовок (в худшем случае «Без названия»), поэтому константа была недостижима, и
   при пустой теме заголовок молча подменялся. Приведено к прежней цепочке
   `request.topic or "Научная новость"`.
3. **Отката при отказе LLM не существовало** — бриф его требует. Добавлен явный
   `fallback_provider_id` в `generate_script` (по умолчанию пустой: молчаливая подмена
   движка прятала бы настоящую ошибку). Подключён в `generate_for_job` **только** для
   провайдера, объявившего `requires_network`/`requires_paid_api`: удалённый провайдер
   может отказать по причине, неподвластной пользователю, а ошибка локального ввода
   (пустой текст) обязана всплыть. Подмена фиксируется в `used_fallback`, `warnings`
   и `metadata`.
4. **Ошибка LLM-провайдера вводила в заблуждение.** `supports()` складывал «умею ли я
   такой источник» с «подключён ли я здесь», из-за чего неподключённый провайдер
   сообщал о неподдерживаемом источнике. Переопределение убрано; `generate()` называет
   настоящую причину. Побочно исправлено определение `requested_id` при явно переданном
   `provider` — иначе отчёт назвал бы не тот движок, а откат совпал бы с упавшим
   провайдером (найдено тестом).

### Проверка вживую

- **Байт-в-байт:** вывод `legacy_template` сверен с `build_script` из коммита `3021b83`
  (извлечён через `git show`) на **9 наборах входных данных** — без claims, 1/2/3/6
  claims, гипотеза, небезопасный claim, пустая тема, тема с `Почему`. Совпадение полное,
  включая порядок ключей (от него зависит `json.dumps`).
- **18 существующих `script.json`** в `projects/` прочитаны движком без ошибок и без
  изменения файлов (сверены байты до и после). Среди них проект с 10 сценами и
  реальными `actual_duration_sec` — роли восстановлены корректно.
- **Настоящий пайплайн** (`create_news_to_short_job` → `run_news_to_short_job
  --until-stage script --dry-run`) на временной папке: 6 сцен из реальных предложений
  статьи, длительности `[3.42, 5.84, 5.44, 5.17, 6.31, 5.37]` вместо таблицы
  `[3.5, 7.0, 10.0, 13.0, 10.0, 8.0]`, `narration.txt` записан.
- **CLI** `script providers` / `generate` / `validate` — отработали без сети и записи.

### Тесты

**Добавлено 114 тестов в двух файлах** (ни один существующий тест не изменён):

- `tests/test_script_engine.py` — 73 теста: регрессия legacy-шаблона (golden-снимок
  вывода коммита `3021b83` + порядок ключей + таблица длительностей), deterministic
  (офлайн, воспроизводимость, число сцен от материала, каждое предложение из
  источника, дедупликация, откат при скудном материале), user_supplied (границы по
  пустым строкам и маркерам, ни одно слово не переписано), LLM (только через mock:
  неподключён / без подтверждения / валидный ответ / битый JSON / нет сцен / сцена без
  текста / неизвестная роль / ```-обёртка / длительности считает движок, а не модель),
  откаты, реестр, валидация (пустой текст, дословный и почти-повтор, слабый и
  отсутствующий hook, отсутствующий payoff, слишком длинная сцена, ноль/минус/NaN
  длительность, порядок сцен, CTA не последним, несовпадение языка), формат
  `script.json` (старая схема, вывод ролей, приоритет реальных длительностей, round-trip).
- `tests/test_script_engine_pipeline.py` — 41 тест: публичный контракт `build_script`,
  разрешение источника (в т.ч. что готовый сценарий больше не перемалывается в
  research), обратная совместимость `job.json`, **scene timeline на 3/4/6/7/11/18
  сценах разной длины**, чтение всех реальных `script.json` только на чтение, CLI.

**Полный набор: 859 тестов, OK** (180 с) — было 745 на `3021b83`, добавлено ровно 114.

### Отклонения от брифа (осознанные)

1. **Провайдеров четыре, а не два** — по прямому решению пользователя:
   `legacy_template` (точная обратная совместимость и эталон регрессии),
   `deterministic_local` (бесплатный офлайн-путь и тестовая опора), `llm` (интерфейс без
   платных вызовов), `user_supplied` (готовый сценарий и narration).
2. **Движок по умолчанию — `deterministic_local`, а не шаблонный.** Бриф в графе
   «приёмка» говорит «по умолчанию поведение не изменилось», но его же цель — «ролики
   перестают быть одинаковыми». Шаблон по умолчанию оставлял бы цель недостижимой без
   ручного переключения. `deterministic_local` удовлетворяет ограничению, ради которого
   шаблон предлагался по умолчанию (бесплатно, офлайн, воспроизводимо), и при этом
   выполняет цель. Прежнее поведение доступно точно и полностью по
   `--provider legacy_template`; при скудном материале оно включается само.
3. **`research_engine.py` не изменён.** Бриф называет его среди модулей, но его claims —
   это и есть первые восемь предложений статьи (проверено по коду), то есть материал,
   которого движку достаточно. Переписывать его без нужды — вне рамок этапа.

### Изменённые/созданные файлы

Создано: `src/content/` (17 файлов: `__init__.py`, `script_engine/` с `contract`,
`models`, `engine`, `registry`, `validation`, `text_analysis`, `legacy_format` и
`providers/` из четырёх реализаций), `tests/test_script_engine.py`,
`tests/test_script_engine_pipeline.py`.
Изменено: `src/news/script_generator.py` (генератор → адаптер), `src/news/models.py`,
`src/news/pipeline.py`, `src/content_creation/service.py`, `src/content_creation/cli.py`.

**API/платные вызовы:** нет. **Сеть:** нет. **TTS/Vision/downloads:** нет.
**Git write:** только локальный коммит этого этапа — без push/reset/rebase/clean.
**`.env`, пользовательские проекты, медиа, `outputs/`, модели — не тронуты**
(подтверждено `git status --short` по этим путям).

**Рекомендуемый следующий этап:** Q2 — визуальный план по смыслу (зависит от Q1).
На этом этапе не начинался по прямому указанию пользователя.

---

## Stage Q2 — Визуальный план по смыслу — ЗАВЕРШЁН

Бриф: `docs/handoff/PRODUCT_VISION_AND_ROADMAP.md`, «Q2. Визуальный план по смыслу».
Начат от коммита Q1 `c1f0bc0` при чистом дереве (859 тестов, OK).

### Что было проверено перед изменениями

Аудит показал, что часть визуального планирования **уже существовала**, и её
устройство определило всю интеграцию:

- `src/news/visual_plan.py` — реальный планировщик: `make_stock_query` из четырёх
  `if` возвращала одну из **четырёх** фиксированных английских строк на все ролики
  проекта, а `visual_type` чередовался по `index % 3`.
- `src/assets/semantic_selection/` (коммит `24afa97`) — прототип с **правильной
  формой** контракта (`SemanticScene`: subject/action/environment/location/camera/
  must_include/must_not_include/visual_priority/fallback_level) и **неправильным
  наполнением**: `WHALE_NEGATIVES`, `OCEAN_TERMS`, `_infer_subject`, знающий только
  «whale»/«right whale», `_infer_location`, знающий только Австралию. Работал он
  вообще не по русскому тексту сцены, а по захардкоженному английскому
  `primary_query`, который ему подавала `make_stock_query`.
- **Ключевое открытие:** `analyze_scene` уже читает явный блок
  `scene.get("semantic")` как приоритетный override, и этим уже пользуется
  `src/production_plan/youtube_shorts.py` и два существующих теста. Значит план
  можно подать во весь существующий поисковый слой, **не трогая ни одного
  провайдера** — что и сделано.
- Потребители `visual_plan.json` (`asset_manager`, `stock_video_downloader`,
  `final_renderer`, `visual_preview`) читают конкретные ключи; список ключей снят с
  реального файла на диске и сохранён целиком.
- Механизма перевода в проекте **нет** ни одного (проверено поиском по `src/`).

### Что сделано

Создан `src/content/visual_planning/` — рядом со `script_engine`, внутри пакета
`src/content/`, назначение которого («format-agnostic building blocks, которые
longform или repurposer смогут переиспользовать») задано ещё в Q1.

- **Контракты** (`models.py`): `VisualPlanRequest`, `VisualPlanResult`,
  `SceneVisualPlan`, `VisualSearchIntent`, `VisualEntity`,
  `VisualPlanValidationResult`; `VisualPlanner` + capabilities в `contract.py`.
  Словарь `SEVERITY_*` **импортирован** из script_engine, а не заведён заново.
- **Извлечение сущностей** (`entities.py`): группировка словоформ по общему
  префиксу, salience по повторяемости в сценах/теме/заголовке/claims, глаголо- и
  топонимо-подобные токены, годы и века. Разбиение на слова, стоп-слова и сходство
  переиспользованы из `script_engine.text_analysis`.
- **Планировщик** (`planners/deterministic.py`): предмет, действие, место, эпоха,
  тип кадра, допустимые типы материала, `must_include` и цепочка intents
  «точно → без действия → окружение → тема». Офлайн, бесплатно, воспроизводимо.
- **Адаптер** (`legacy_format.py`): `SceneVisualPlan` → тот же `visual_plan.json`
  плюс блок `semantic`, который существующий `analyze_scene` уже умеет читать, плюс
  структурные `visual_intents`. Провайдеры получают обычные строки, как и раньше.
- **Валидация** (`validation.py`) и **CLI** `visual-plan planners|build|validate|intents`.

### Найдено и исправлено в существующем коде (2 дефекта)

1. **Китовые негативы применялись ко всем роликам.**
   `scene_analyzer._infer_must_not` возвращал `WHALE_NEGATIVES` при условии
   `if subject or _has_ocean(environment)` — то есть для **любой** сцены, где вообще
   определился предмет. Для ролика про ворон это запрещало `city`, `road`, `farm` —
   ровно те места, где вороны живут; `candidate_ranker` штрафовал такие кандидаты, а
   `asset_manager` передавал их как negative terms. Условие сужено до реально морской
   сцены, список честно переименован в `MARINE_CONTEXT_NEGATIVES`. Ни один
   существующий тест на прежнее поведение не опирался (проверено).
2. **`supports()` смешивал «умею такой материал» с «материал не пуст»** — пустой
   сценарий сообщал «планировщик недоступен» вместо «в сценарии нет сцен». Тот же
   класс ошибки, что исправлен в Q1 у LLM-провайдера; исправлено так же.

### Проверка вживую

- Настоящий пайплайн до стадии `visual_plan` (dry-run, временная папка): шесть сцен,
  у каждой **свой** запрос из собственного предложения — `ворон узнают лица`,
  `маску надевали Вашингтонском птиц`, `ворон запоминали маску`,
  `ворон передавали информацию`, `ворон работает знания` — вместо одной строки
  `nature science wildlife observation` на все шесть.
- Стадия `asset_search` на новом плане отрабатывает, манифест пишется.
- **19 существующих `visual_plan.json`** прочитаны без ошибок и без изменения файлов
  (сверены байты до и после).
- CLI `visual-plan planners|build|intents|validate` — без сети и без записи вне `--out`.

### Тесты

**Добавлено 73 теста в двух файлах** (существующие тесты не изменялись):

- `tests/test_visual_planning.py` — 47: извлечение сущностей (словоформы, тема,
  отсев служебных слов, место только после предлога, предпочтение строчного глагола,
  эпоха только когда написана), планировщик (одна запись на сцену, порядок,
  1/2/3/6/9/14 сцен, воспроизводимость, запросы сцен различаются, **каждый термин
  есть в сценарии**, место не становится предметом, тип кадра от роли, архив для
  датированной сцены, fallback'и расширяются и не повторяются, язык intent и
  требование перевода, негативы не выдумываются), валидация (все коды из брифа,
  разделение errors/warnings), формат (все старые ключи, `semantic` читается
  `analyze_scene`, старый план читается без миграции, round-trip).
- `tests/test_visual_planning_pipeline.py` — 26: контракт `build_visual_plan`,
  интеграция с asset-слоем (запросы — обычные строки, китовые негативы больше не
  срабатывают, план не объявляет ассет выбранным или лицензированным), стадии
  пайплайна `visual_plan` и `asset_search`, чтение реальных проектов только на
  чтение, CLI.

**Полный набор: 932 теста, OK** — было 859 на `c1f0bc0`, добавлено ровно 73.

### Отклонения от задания (осознанные)

1. **LLM-планировщик не добавлен.** Задание разрешало подготовить интерфейс, но не
   требовало его. В Q1 у LLM-провайдера была самостоятельная ценность — контракт
   ответа и его парсер. Здесь аналогичной ценности нет: seam уже задан протоколом
   `VisualPlanner` и реестром, а модуль без единого вызывающего был бы
   спекулятивным кодом. Задание прямо просит «минимально и без преждевременной
   универсальности».
2. **Запросы выводятся на языке сценария, а не по-английски.** Слоя перевода в
   проекте нет; самодельный переводчик задание запрещает, и он подменял бы
   названное в тексте животное или страну приблизительным аналогом. Поэтому intent
   отделён от строки запроса, язык проставлен явно, выставлен флаг
   `requires_translation`, а прежняя английская строка `legacy_broad_query`
   сохранена **последним** запасным запросом — чтобы поиск мог только выиграть по
   сравнению с прежним состоянием, но не проиграть. Контракт под будущий
   provider-specific адаптер подготовлен.
3. **`must_avoid` по умолчанию пуст.** Выдумывать негативы без знания предметной
   области — это ровно та ошибка, из-за которой прототип запрещал городу
   появляться в ролике про ворон. Поле работает для авторских планов и будущих
   планировщиков, валидация его проверяет.
4. **Качество извлечения ограничено морфологией.** Без морфоанализатора и без LLM
   суффиксные признаки иногда ошибаются (`Исследователи` выглядит как глагол);
   смягчено предпочтением строчных форм и списком нефильмуемых слов. Дальнейшее
   улучшение требует именно LLM-планировщика, и это отдельный этап.

### Изменённые/созданные файлы

Создано: `src/content/visual_planning/` (8 файлов), `tests/test_visual_planning.py`,
`tests/test_visual_planning_pipeline.py`.
Изменено: `src/news/visual_plan.py` (планировщик → адаптер), `src/news/pipeline.py`
(+ чтение `claims.json` на стадии visual_plan), `src/content_creation/cli.py`
(команда `visual-plan`), `src/assets/semantic_selection/scene_analyzer.py`
(дефект с негативами), `COMMANDS.md`, эта страница и роадмап.

**API/платные вызовы:** нет. **Сеть:** нет. **TTS/Vision/downloads/render:** нет.
**Git write:** только локальный коммит этапа — без push/reset/rebase/clean.
**`.env`, пользовательские проекты, медиа, `outputs/`, `assets/library/`,
`assets/cache/`, `manual_assets/`, `music/`, `MOSS_TTS_Nano/`, модели — не тронуты.**

**Рекомендуемый следующий этап:** Q3 — субтитры по словам. На этом этапе не
начинался по прямому указанию пользователя.

---

## Stage D1 — Единый ConfigResolver — ЗАВЕРШЁН

Бриф: `docs/handoff/PRODUCT_VISION_AND_ROADMAP.md`, «Бриф 5 — D1. Единый ConfigResolver».
Начат от коммита Q2 `66b2e13` при чистом дереве (932 теста, OK).

### Что было проверено перед изменениями

Полная карта — `docs/implementation/config_resolver/CONFIG_MAP.md`
(настройка → источники → текущий приоритет → потребители). Главное:

- **Похожего механизма в проекте не было.** `src/config_loader.py` — это legacy-загрузчик
  `config/video_style.json` для старого пайплайна, а не резолвер. Ближайший
  родственник — `src/audio/voice_policy.resolve_voice_policy`: четырёхслойное слияние,
  но только для звука и без ответа «откуда взято». Он не заменён и не изменён — резолвер
  строится **над** ним и обязан выдавать тот же результат.
- **Порядок слоёв в брифе не совпадает с кодом.** `resolve_voice_policy` сливает
  `channel_defaults`, затем `template_defaults` — то есть **шаблон перекрывает канал**,
  а не наоборот. У `nature_science_news_ru` это реально работает:
  `never_auto_fallback_to_paid: true` проигрывает шаблонному
  `fallback_policy: manual_audio`.
- **Бо́льшая часть `channel_config.json` не читается никем**: `target_duration_sec`,
  `min/max_duration_sec`, `resolution`, `fps`, `language`, `subtitles`, `music`,
  `languages`, `content`, `assets`, `approval`. Пайплайн берёт из этого файла только
  `voice`, `voice_workflow` и `asset_selection`.
- **Один и тот же параметр разрешается двумя разными способами.** `language`: story-card
  путь — `request.language or channel.default_language`; news-путь —
  `request.language or "ru"`, канальный `language` не смотрится вовсе.
  `target_duration_sec`: `request → project_overrides → 55`, канальные 55 не при чём.
- **Окружение в этом проекте — только провайдеры.** 44 чтения `os.getenv` в `src/`,
  все до одного — ключи API и тюнинг эндпоинтов. Ни одна продуктовая настройка через
  окружение не задаётся. `.env` не открывался (запрещено CLAUDE.md); список переменных
  снят с кода.

### Что сделано

Создан `src/config_resolver/` — читающий слой поверх существующих компонентов.
Ни один файл конфигурации не изменён, ни один старый читатель не удалён, в пайплайн
резолвер **не подключён** (это следующий шаг, D2).

- `keys.py` — реестр настроек. У каждой: тип, значение по умолчанию, **повторяющее тот
  литерал, на который код падает сегодня**, и список модулей-потребителей. Настройка
  без потребителей помечается предупреждением `no_consumer_yet` вместо того, чтобы
  делать вид, что она на что-то влияет.
- `models.py` — `ConfigSource` (9 констант с приоритетами), `ResolvedValue`,
  `ResolutionStep`, `ResolvedConfig`, `ConfigResolutionRequest`, `ConfigResolutionError`.
- `layers.py` — по одному читателю на слой: каталог форматов/шаблонов, `ChannelRegistry`,
  `channel_config.json` (ровно тем же разбором, что `voice_policy_from_channel_config`),
  `AUDIO_POLICY_DEFAULTS`, оба вида project-манифеста через `ProjectRepository`,
  блок `languages.<lang>`, runtime-флаги, окружение.
- `resolver.py` — приоритет, приведение типов, trace.
- `adapters.py` — `to_voice_policy`, `to_render_settings`, `secret_presence`:
  совместимость для постепенной миграции потребителей.
- CLI: `channels show --channel <id> --explain [--trace] [--json]` — таблица
  «параметр → значение → откуда взято». Только чтение, без сети и без оплаты.

**Приоритет (слабый → сильный):**
`global_default → format_policy → channel_profile → channel_config → template_policy
→ project_override → localization_override → runtime_override` (+ `environment`,
только секреты).

### Секреты

Ключ API не может попасть в резолвер физически: у секретных ключей тип
`secret_presence`, и слой окружения хранит результат `bool(os.getenv(...))` — сам
строковый ключ никуда не сохраняется. `ResolvedConfig.get()` для секретного ключа
**отказывается** отвечать, `overrides` с секретом отклоняются, в JSON стоит `***`,
в тексте — «настроен / не настроен». `--explain` можно без опаски вставлять в отчёт.
Тест сериализует весь `ResolvedConfig` вместе с trace и убеждается, что подставленного
секрета в выводе нет.

### Осознанные отклонения от брифа

1. **`template_policy` выше канальных слоёв, а не ниже** — как в коде сегодня. Порядок
   из брифа поменял бы поведение озвучки, а D1 менять поведение не имеет права.
   Конфликт не спрятан: перекрытое канальное значение получает предупреждение
   `template_policy_overrode_channel`, и это ровно тот случай, который разбирается в D2.
2. **Добавлен слой `runtime_override` выше локализации** — семь слоёв вместо шести.
   Явный флаг CLI сегодня бьёт любой файл, и это место за ним сохранено.
3. **`ConfigValidationResult` как отдельная сущность не заведена.** Ошибки — это
   `ConfigResolutionError` с полем `reason` (`unknown_channel` / `unknown_template` /
   `unknown_format` / `unknown_project` / `unknown_key` / `secret_override` /
   `secret_access`), предупреждения живут на самих значениях и на `ResolvedConfig`.
   Отдельный тип без потребителя был бы спекулятивным.
4. **Секретами резолвер занимается только в объёме «настроен / не настроен» и только
   для четырёх ключей.** Тюнинг эндпоинтов провайдеров (`WIKIMEDIA_*`, `NASA_IMAGES_*`,
   `INTERNET_ARCHIVE_*`) не втянут: у него уже есть свой отчёт
   `src/assets/provider_diagnostics.py`, и дублировать его — значит заводить вторую
   систему.
5. **`channel_config.json` разбирается на два слоя** (`channel_profile` для
   `channel.json` и `channel_config` для `channel_config.json`), потому что это
   физически два разных файла с разными схемами; сливать их в один «канальный» слой
   означало бы врать в колонке «откуда взято».

### Проверка вживую

- `channels show --channel nature_science_news_ru --explain --trace` — 33 строки,
  у каждой источник и путь к файлу; видно, что `voice.fallback_policy` пришёл от
  шаблона и перекрыл канал, а `fps`/`min_duration_sec`/`max_duration_sec` разрешаются,
  но ни на что не влияют.
- То же для `nature_pulse` (канал только с `channel.json`, без `channel_config.json`) —
  слои честно отчитываются, почему они пусты.
- Неизвестный канал → понятное сообщение и код возврата 1, без traceback.
- Все проекты в `projects/` обоих видов читаются как слой; байты `job.json`/`project.json`
  сверены до и после — не изменились.

### Тесты

**Добавлено 54 теста в двух файлах** (существующие тесты не изменялись):

- `tests/test_config_resolver.py` — 46: реестр ключей (значения по умолчанию сверяются
  с `VoicePolicy()` и `NewsJob.create()`, а не выписаны от руки), приоритет на всех
  семи слоях, trace, конфликт «шаблон перекрыл канал», пустая строка и пустой словарь
  как «не задано», выключенный язык, приведение типов и невалидное значение, секреты
  (8 тестов: слой окружения выдаёт только `bool`, presence вместо значения, отсутствие
  секрета в сериализации и в `explain_rows`, redaction, запрет `get()` и `overrides`,
  отключаемое чтение окружения), понятные ошибки на неизвестные
  канал/шаблон/формат/проект/ключ и на нечитаемый `channel.json`, нечитаемый
  `channel_config.json` трактуется как отсутствующий — так же, как это делает
  `_load_channel_config`, все origin в posix-виде и на Windows, чтение
  ничего не пишет и воспроизводимо, адаптеры, CLI `--explain`.
- `tests/test_config_resolver_parity.py` — 8 характеристических: для **каждого**
  канала на диске `to_voice_policy(resolve_config(...))` совпадает с
  `resolve_voice_policy_for_channel(...)` **по всем 24 полям**; отдельный тест
  доказывает, что это не совпадение — любое поле `VoicePolicy`, которое умеют задавать
  `AUDIO_POLICY_DEFAULTS` или канальный адаптер, обязано быть ключом резолвера.
  Плюс совпадение по `language`, `voice_profile`, геометрии формата и возможностям
  шаблона, legacy-алиас `story_card_short_v1` и чтение всех 20 реальных проектов.

**Полный набор: 986 тестов, OK** — было 932 на `66b2e13`, добавлено ровно 54.

### Изменённые/созданные файлы

Создано: `src/config_resolver/` (6 файлов), `tests/test_config_resolver.py`,
`tests/test_config_resolver_parity.py`,
`docs/implementation/config_resolver/CONFIG_MAP.md`.
Изменено: `src/content_creation/cli.py` (флаги `--explain/--trace/--template/--format/
--language/--project-id` у `channels show` и функция `_channels_explain`), `COMMANDS.md`,
`CLAUDE.md`, эта страница и роадмап.

**API/платные вызовы:** нет. **Сеть:** нет. **TTS/Vision/downloads/render:** нет.
**Git write:** только локальный коммит этапа — без push/reset/rebase/clean.
**`.env` не открывался** (список переменных снят с кода, не из файла). **Пользовательские
проекты, медиа, `outputs/`, `assets/library/`, `assets/cache/`, `manual_assets/`,
`music/`, файлы каналов — не тронуты.**

**Рекомендуемый следующий этап:** D2 + E2 — голоса по языкам и стили субтитров канала.
Слой `localization_override` уже есть и покрыт тестами; D2 — это подключение
потребителей к нему и решение конфликта «шаблон перекрывает канал» для
`fallback_policy`.

---

## Stage D2/E2 — Локализация и голос: подключение ConfigResolver — ЗАВЕРШЁН

Бриф: `docs/handoff/PRODUCT_VISION_AND_ROADMAP.md`, «Бриф 6 — D2 + E2».
Начат от коммита D1 `81e63e0` при чистом дереве (986 тестов, OK).

### Фактическая архитектура локализации/голоса до изменений

Карта — `docs/implementation/localization_voice/LOCALIZATION_VOICE_MAP.md`. Главное:

- **Голос разрешался в трёх независимых местах.** `src/news/voice_stage.py`,
  `src/content_creation/service._build_paid_preflight_summary` и
  `service._create_paid_voice_approval` каждое само вызывали
  `resolve_voice_policy_for_channel` + `load_voice_profile_for_channel`. Approval мог
  быть записан против одного голоса, а сгенерирован другой.
- **Поиск профиля был выписан трижды** — в `voice_adapter`, в
  `capabilities.resolve_voice_profile` и через них в мастере, причём с разными
  правилами глобального поиска.
- **`channel_config.json → languages.<id>.voice` не читал никто** (слово `languages`
  не встречалось ни в `src/news/`, ни в `src/audio/`).
- **`voice.fallback_policy` не читал никто.** Значение разрешалось (D1), но ни один
  модуль не принимал по нему решения: отсутствие ключа приводило к попытке платного
  вызова, которая падала внутри `ElevenLabsProvider`.
- **Язык нигде не нормализовался.** `ru`, `ru-RU`, `Russian` — три разных значения;
  папка локализации и код языка были одним и тем же полем.
- **Профиль не проверялся на язык.** Английскую локализацию можно было озвучить
  русским голосом молча.
- **`build_safe_voice_manifest` хардкодил русский голос** (`ru_dom`,
  `hDfThiytYnsDMuVgm6Qy`, `Dom`, `eleven_multilingual_v2`) как значения по умолчанию.
- **Готовая озвучка защищалась только вызывающим.** `service._completed_narration`
  пропускал стадию, но сама стадия при повторном вызове перезаписывала манифест
  заглушкой.
- **`ELEVENLABS_VOICE_ID` перекрывал `voice_id` каждого elevenlabs-профиля** в любом
  `voices.yaml` — то есть все языки говорили одним голосом.

### Что переиспользовано, а не создано заново

`src/config_resolver/` (все девять слоёв и порядок приоритета), `to_voice_policy`,
`src/audio/voice_policy` (`VoicePolicy`, `AUDIO_POLICY_DEFAULTS`, `FALLBACK_POLICIES`,
`OUTPUT_MODE_*`), `channels/*/voices.yaml` + `VoiceProfileRegistry`,
`src/audio/voice_manifest` (в том числе терпимый `read_voice_manifest`),
`src/audio/voice_workflow` (`import_manual_audio`, approval), `narration_workflow`,
`scene_voice_generator.generation_output_paths`, `EXTENDED_VOICE_STATES` как словарь
статусов, `NewsJob.localizations` как хранилище нескольких языковых версий.

Второй системы локализаций, второго реестра голосов, второго контракта провайдера и
второй конфигурационной системы не создано.

### Что добавлено

- **`src/localization/`** — runtime-контракт локализации поверх резолвера:
  - `locales.py` — единственная таблица «код → locale → написания». Список языков
    `src/content_creation/languages.py` теперь берётся отсюда, чтобы списка не стало два.
  - `models.py` — `ResolvedLocalization`, `LocalizationIssue`, константы источников
    озвучки и коды проблем. Статусы взяты из существующего
    `EXTENDED_VOICE_STATES` — нового словаря статусов нет (проверяется тестом).
  - `resolver.py` — `resolve_localization()`: единственное место, где решается язык,
    locale, провайдер, профиль, `voice_id`, модель, fallback и источник озвучки.
  - `secrets.py` — признак «ключ настроен», только `bool`.
  - `validation.py` — проверки набора локализаций: дубли id, дубли путей вывода,
    секрет в конфигурации, путь за пределами проекта, один активный источник.
- **`src/audio/voice_profile_registry.lookup_profile`** — единственная реализация
  поиска профиля; `voice_adapter` и `capabilities` теперь делегируют ей.
- **`src/news/voice_adapter.resolve_localization_for_channel`** — compatibility-обёртка,
  возвращающая `None` для канала, которого резолвер не знает.
- **CLI `voices explain`** — read-only объяснение локализации/голоса.
- **Сводка мастера** показывает разрешённый голос, откуда он взят, наличие ключа,
  источник озвучки и причину, по которой TTS не будет запущен.

### Потребители, переведённые на ConfigResolver

`src/news/pipeline.py` (стадия `voice` — одна резолюция на стадию),
`src/news/voice_stage.py` (выбор голоса, fallback, защита готовой озвучки),
`src/news/voice_adapter.py`, `src/content_creation/service.py`
(`_resolve_localization`, `_resolve_voice_inputs`, preflight-сводка, запись approval,
определение готовой озвучки), `src/content_creation/cli.py`,
`src/content_creation/wizard.py`, `src/content_creation/languages.py`.

### Потребители, намеренно оставленные на compatibility path

Story Card (шаблон без озвучки — `story_card_no_voice`), legacy channel pipeline
(`pipeline.py --channel/--video`, `src/voice_engine.py` — своя система голосов),
documentary, Anime Factory, `src/audio/voice_cli.py` (обслуживающий CLI).
Причина одна и та же: их миграция расширяет scope этапа и ничего не добавляет к
вертикальному пути «выбор пользователя → стадия озвучки». Подробнее — §8 карты.

### Порядок разрешения

Порядок D1 **не изменён**, включая `template_policy > channel_config`; конфликт
по-прежнему помечается предупреждением `template_policy_overrode_channel`, и теперь
оно печатается в `voices explain`. Явный выбор пользователя подаётся в резолвер как
слой `runtime_override`, поэтому «runtime бьёт localization» — свойство резолвера.

### Осознанные отклонения от промпта

1. **Стили субтитров канала (`channels/*/subtitle_style.json`) не подключены.**
   Роадмап относит их к E2, но этот промпт прямо запрещает менять subtitle renderer
   и переходить к Q3. Передаётся только язык субтитров
   (`ResolvedLocalization.subtitle_language`). Стили остаются задачей отдельного этапа.
2. **Отдельного поля `voice_style` нет.** В проекте стиль подачи — это
   `settings.style` ElevenLabs; отдельное поле означало бы хранить одно значение
   дважды. Доступно как производное свойство и печатается в explain.
3. **`narration_text` в контракт не вынесен.** Текст живёт в `script.json`, который и
   так передаётся стадии; дублировать его в runtime-объекте не нужно.
4. **`LocalizationState` (job.json) не получил новых полей.** Provider, профиль,
   `voice_id` и признак платного вызова уже хранит `voice_manifest.json`; добавлять
   их второй раз означало бы завести второй источник правды. `script_locale` теперь
   поддерживается в актуальном виде.
5. **`request.voice.provider` не подаётся как runtime-override.** У
   `VoiceRequestConfig.provider` значение по умолчанию `"disabled"`, и трактовка
   этого дефолта как явного выбора молча отключила бы озвучку у шаблона, который её
   требует. Платный гейт по-прежнему смотрит на это поле, как и раньше.
6. **Статус манифеста озвучки не изменён.** `status`/`voice_stage_status` остались
   описанием результата стадии («ничего не сгенерировано»), потому что на этом смысле
   держатся `quality_check`, `preview_render` и `project status`. Разрешённый план
   лежит рядом, в новом поле `localization_status`.
7. **Мастер по-прежнему спрашивает провайдера и голос.** Это не «уже известный»
   ответ, а решение на конкретный запуск (нет озвучки / ручной WAV / платная
   генерация). Убрано другое: голоса чужого языка больше не предлагаются, а вместо
   тихого падения на `ru_dom` печатается понятное предупреждение.
8. **Проверка наличия ключа не берётся из слоя окружения резолвера.** См. §6 карты:
   иначе «ключ есть в `.env`, но процесс его не загрузил» выглядело бы как «ключа
   нет» и ломало бы работающую сегодня генерацию.

### Исправленные ошибки прежней архитектуры

Шесть штук, перечислены в §9 карты. Существенные: env-переменная
`ELEVENLABS_VOICE_ID` больше не перекрывает `voice_id` всех профилей;
`fallback_policy` реально применяется; профиль проверяется на язык; стадия озвучки
сама защищает готовый артефакт.

### Тесты

**Добавлен `tests/test_localization_voice_integration.py` — 42 теста**
(существующие тесты не изменялись): нормализация языка и locale, единый список
языков, `localization_id` не переименовывается; характеристическая проверка, что для
каждого канала на диске разрешённый `selection` и `VoicePolicy` совпадают с
пре-D2-читателями; неизменность порядка слоёв D1 и `template_policy > channel_config`;
`localization_override` побеждает канал, `runtime_override` побеждает локализацию;
секрет не сериализуется и не печатается (включая CLI и trace); отсутствие ключа даёт
ожидаемый fallback без сети; manual audio и готовый артефакт не вызывают TTS; готовая
озвучка переиспользуется, её манифест не перезаписывается (сверка байтов); артефакт
чужого языка не переиспользуется; несовместимый профиль, неизвестный провайдер,
`local_tts` без провайдера, `fallback_policy=none` дают понятные ошибки; несколько
локализаций получают разные пути вывода, дубль пути и дубль id — ошибка; старые
манифесты без новых полей читаются; все news-проекты на диске читаются, байты
`job.json` сверены до и после; старые подписи стадии дают прежний результат;
мастер предлагает только голоса выбранного языка; `voices explain` не раскрывает
секрет и возвращает 1 на ошибочной локализации.

**Полный набор: 1028 тестов, OK** — было 986 на `81e63e0`, добавлено ровно 42.

### Проверка вживую

- `voices explain --channel nature_science_news_ru --language ru` — видно, что
  провайдер, профиль и модель пришли из `languages.ru` (слой, который до этого этапа
  не читал никто), fallback — из шаблона с предупреждением, ключ показан как
  «настроен», TTS будет вызван.
- То же с `--language en` — явная ошибка «профиль `ru_dom` рассчитан на язык `ru`» и
  код возврата 1 вместо тихого русского голоса.
- Сеть, TTS, Vision, downloads, платные вызовы, рендер — не выполнялись.
  Пользовательские проекты, медиа, `outputs/`, `assets/`, `music/`, `.env` — не
  открывались и не изменялись (кроме read-only чтения `job.json` для проверки
  совместимости, со сверкой байтов).

### Изменённые/созданные файлы

Создано: `src/localization/` (6 файлов),
`tests/test_localization_voice_integration.py`,
`docs/implementation/localization_voice/LOCALIZATION_VOICE_MAP.md`.
Изменено: `src/audio/voice_profile_registry.py`, `src/audio/voice_cli.py`,
`src/news/voice_adapter.py`, `src/news/voice_stage.py`, `src/news/pipeline.py`,
`src/content_creation/{service,cli,wizard,languages,capabilities}.py`, `COMMANDS.md`,
`docs/implementation/config_resolver/CONFIG_MAP.md`, `CLAUDE.md`, эта страница и роадмап.

**API/платные вызовы:** нет. **Сеть:** нет. **TTS/Vision/downloads/render:** нет.
**Git write:** только локальный коммит этапа — без push/reset/rebase/clean.

**Рекомендуемый следующий этап:** Q3 (word-level subtitles) либо оставшаяся половина
E2 — стили субтитров канала. Автоматически к Q3 не переходить.

---

## Stage Q3 — Единый движок субтитров с локализацией — ЗАВЕРШЁН

Бриф: `docs/handoff/PRODUCT_VISION_AND_ROADMAP.md`, «Q3. Субтитры по словам».
Начат от коммита D2/E2 `3973f27` при чистом дереве (1028 тестов, OK).
Полная карта: `docs/implementation/subtitle_engine/SUBTITLE_ENGINE_MAP.md`.

### Фактическая архитектура субтитров до изменений

Весь движок — 98 строк в `src/news/subtitles.py`:

```
scene["on_screen_text"] или scene["narration"]  (первое непустое)
  → куски строго по 5 слов
  → длительность сцены / число кусков (равномерно, включая паузу)
  → subtitles.srt + subtitles.ass (ASS-заголовок зашит в код)
  → final_renderer вжигает ass_path
```

Ни валидации, ни resume, ни ссылки на озвучку или сценарий, ни знания о
предложениях и пунктуации. Стиль канала (`channels/*/subtitle_style.json`) не
читался — оставшаяся половина этапа E2.

Реализации субтитров в репозитории на момент аудита: `src/news/subtitles.py`
(продуктовый путь), `src/layout_renderer.py` (текст на кадре в legacy channel
pipeline), `src/production_plan/solar_vs_nuclear_render.py` (свой ASS-писатель для
одного зафиксированного ролика), `anime_factory/` (Whisper → SRT, отдельное
приложение). В продуктовом пайплайне движок был ровно один — второго Q3 не создал.

### Найденные и исправленные дефекты

1. **W2 из аудита V1 закрыт: в кадре была только первая пятёрка слов сцены.**
   `on_screen_text` читался раньше `narration`, а провайдеры сценария заполняют его
   через `text_analysis.first_words` (первые 5 слов). Одна реплика висела всю сцену —
   после B1 до 14.8 с. Теперь субтитр — полная реплика сцены; полнота покрытия
   проверяется валидатором (`text_not_covered`) и тестами по токенам.
2. **Реплика висела и в паузе между сценами.** Раньше нарезка делила
   `scene_render_duration` целиком, включая `pause_after_sec`. Теперь текст живёт
   внутри речевого отрезка (`speech_duration_sec`), пауза остаётся без субтитра.
3. **Равномерное деление игнорировало длину кусков.** Теперь время распределяется
   пропорционально числу символов — тому же предсказателю, что уже используется в
   `text_analysis.estimate_duration_sec`.
4. **Стиль канала был мёртв (остаток E2).** `subtitle_style.json` подключён через
   `src/subtitles/style.py`. Значения по умолчанию дают байт-идентичную строку
   `Style:` тому, что вжигалось до Q3, и для `nature_science_news_ru` файл канала с
   ними совпадает — картинка не изменилась (проверяется тестом).
5. **Ничего не проверялось.** Появились ошибки/предупреждения со стабильными кодами:
   пересечения, выход за сцену и за озвучку, NaN/отрицательное время, потерянный или
   продублированный текст, чужой язык, скорость чтения, длина строк.
6. **Стадия перегенерировала субтитры каждый запуск.** Появился resume по
   `script_fingerprint` + `narration_fingerprint`; защищённый пользовательский
   артефакт (`"protected": true`) не перезаписывается никогда.

### Что переиспользовано, а не написано заново

- Границы сцен — только `src/audio/scene_timeline.py` (B1): `build_scene_timeline`,
  `scene_render_duration`, `SceneTiming`. Второго расчёта длительностей нет.
- Язык и язык субтитров — `ResolvedLocalization` из `src/localization/` (D2/E2),
  через тот же `resolve_localization_for_channel`, что использует стадия voice.
- Список существующих стилей — по-прежнему один,
  `capabilities.list_subtitle_styles`; второго реестра не появилось.
- Имена файлов (`subtitles.srt`, `subtitles.ass`), путь
  `localizations/<id>/subtitles/` и все ключи манифеста, которые читают
  `final_renderer`, `quality_check` и `exporter`, — без изменений.

### Новые контракты

`src/subtitles/`: `models.py` (`SubtitleCue`, `SubtitleSegment`, `SubtitlePolicy`,
`SubtitleStyle`, `SubtitleRequest`, `SubtitleResult`, `SubtitleValidationResult`,
`SubtitleIssue`, коды), `segmentation.py`, `timing.py` (`SceneSpan`,
`SceneTimingPlan`), `validation.py`, `style.py`, `serialization.py`, `manifest.py`
(`SubtitleArtifact`, `SubtitleResumeDecision`), `engine.py`.

`src/news/subtitles.py` стал адаптером: `build_subtitles(script, output_dir)`
сохранила подпись и все ключи результата, добавлена
`build_subtitles_for_localization(...)` для пайплайна.

### Иерархия источников тайминга (фактическая)

`word_timestamps` → `segment_timestamps` → `scene_timeline` → `legacy_planned`.

Первые два уровня **не имеет ни одного производителя** в репозитории (проверено
поиском по `src/`). Читатели включаются только при физическом наличии данных и
совпадении числа слов со сценой; любая некорректность отбрасывает уровень целиком.
Ручной WAV даёт длительность, но не потайминги слов — это уровень сцены.
Whisper, forced alignment и скачивание моделей в Q3 не входили и не появились.

### Что переведено, а что осталось на compat-пути

Переведено: стадия `subtitles` пайплайна News-to-Short, `capabilities`,
CLI (`subtitles explain` / `subtitles validate`). Потребители артефакта
(`final_renderer`, `quality_check`, `exporter`, `preview_renderer`,
`content_creation/service`) не менялись вообще — контракт файла тот же.

Осталось как было (осознанно): `src/layout_renderer.py` — это текст на кадре, а не
файл субтитров; `src/production_plan/solar_vs_nuclear_render.py` — зафиксированный
исторический ролик; `anime_factory/` — отдельное приложение со своим STT-путём;
Story Card — субтитров не имеет (`subtitles_allowed=false`).

### Совместимость

Прочитано read-only 7 исторических манифестов и 7 SRT из `projects/`: все читаются,
ошибок валидации — 0 (только предупреждения, включая
`legacy_artifact_without_metadata`). Ни один файл в `projects/` не изменён.
Артефакт до Q3 не считается совместимым для resume и пересоздаётся текущим движком —
но читать и валидировать его можно.

### Тесты

`tests/test_subtitle_engine.py` (42) и `tests/test_subtitle_pipeline_integration.py`
(9) — 51 новый тест. Regression: `test_news_to_short_scene_timing`,
`test_news_to_short_delivery`, `test_news_to_short_pipeline`,
`test_news_to_short_quality_check`, `test_news_to_short_renderer`,
`test_final_renderer_end_tail`, `test_scene_timeline`,
`test_capability_consistency`, `test_content_creation_{cli,service}`,
`test_config_resolver_parity`, `test_localization_voice_integration` — OK.

**Полный набор: 1079 тестов, OK** — было 1028 на `3973f27`, добавлено ровно 51.

### Осознанные отклонения от брифа

- Название этапа в роадмапе — «субтитры по словам», но потаймингов слов в проекте
  физически нет. Цель («субтитры совпадают с голосом») достигнута уровнем сцены из
  реального timeline B1; уровень слов оставлен как включаемый читатель без
  производителя, потому что выдумывать потайминги запрещено, а STT/alignment — вне Q3.
- `safe_zone_bottom` канала (320) не превращён в ASS `MarginV` (260): это сдвинуло бы
  уже принятый пользователем кадр. Отступ меняется только явным `margin_v`.
- CLI получил только `subtitles explain` и `subtitles validate` (оба read-only).
  `subtitles generate` не добавлен: генерация уже есть у стадии пайплайна, а вторая
  команда, пишущая в `projects/`, полезной работы не добавляет.
- VTT не поддержан: его в репозитории не читает ничто.

**API/платные вызовы:** нет. **Сеть:** нет. **TTS/STT/Vision/alignment/downloads/
render:** нет. **Git write:** только локальный коммит этапа.

**Рекомендуемый следующий этап:** F1 (`narrated_documentary_16x9_v1`, зависел от Q3)
либо W1-класса ремонт экспорта под площадки. Автоматически не переходить.

---

## Real Shorts E2E-A — контрольный прогон продукта — ВЫПОЛНЕН, ОСТАНОВЛЕН ПЕРЕД TTS

Первый сквозной прогон существующего пайплайна на реальной теме (нанопластик в почвах
Сухих долин Мак-Мердо) с готовым пользовательским сценарием через `user_supplied`.
Проект: `projects/2026-07-26_nanoplastik-nayden-v-pochvah-antarktidy`. Кода не менял.

Что сработало: сценарий из 8 сцен принят дословно; факты проверены по четырём
независимым источникам; права всех 8 материалов подтверждены (Pexels, коммерческое
использование разрешено, обязательной атрибуции нет, checksum и provenance записаны);
файлы технически валидны и вертикальны.

Что провалилось: **0 из 8 материалов соответствовали своим сценам.** Антарктида →
камни на столе; Сухие долины → осенний лес в Кайсери; нанопластик → реклама волос;
54% проб → собака в поле; масс-спектрометр → буквенные плитки; финал → женщина
с плакатом. Все 8 сцен оставлены `unresolved`; подмена «похожим по теме» клипом не
выполнялась. Отчёт: `assets/review/e2e_review_package.html` внутри проекта.

Этот прогон и породил ремонтный этап Q2.1.

---

## Stage Q2.1 — Ремонт маршрутизации провайдеров и визуального поиска — ЗАВЕРШЁН

Ремонтный этап, а не продуктовый: чинит то, что сломал Real Shorts E2E-A. Нового asset
pipeline, второго планировщика и новых провайдеров не создавалось.

### Подтверждённые по коду причины провала

1. **Нет слоя перевода.** Прямо признано в `legacy_format.py`: русский intent уходил
   в англоязычные индексы. Wikimedia и NASA получили по 16 запросов и вернули 0.
2. **Извлечение сущностей на русском.** `одном` как subject, `Результат` как action,
   `которую` в secondary; `location` пуст в 7 сценах из 8.
3. **География не сохранялась** как именованная сущность.
4. **Query-echo — шире, чем считалось.** Дефект не ограничен тегами Pexels:
   `_candidate_text` включал `search_query`, поэтому subject сцены был подстрокой
   текста кандидата у **любого** провайдера. Все 40 кандидатов получили ровно 100.0.
5. **`must_avoid` пуст** — и вдобавок токенизация `[a-z0-9]+` выбрасывала кириллицу,
   так что русский запрет не сработал бы и при заполненном поле.
6. **Semantic Visual выключен**, backend `mock`.
7. **Маршрутизации по типу сцены не было.** Все провайдеры набирали 10 очков; порядок
   решал единственный бонус «+10 за видео». Для всех 8 сцен порядок был идентичен.
8. **Длительность не проверялась** — `scene_006` получила 6.54 с на сцену 7.92 с.
9. **Оценки расходились**: `asset_search` выбирал по своей формуле, review board
   показывал `metadata 100 / technical`, и режим доски (`analyse_and_report`) на выбор
   не влиял.
10. **Генератора инфографики не было.**

Дополнительно найдено при аудите и в отчёте не значилось: **`asset_manager` при пустом
отборе скачивал `candidates[0]`**, то есть отклонённого кандидата. Это обесценивало
любой отказ и было главным механизмом, по которому смыслово неверные клипы попадали
в проект.

### Что сделано

- `src/assets/scene_strategy.py` — классификация сцены в один из девяти source class
  и порядок провайдеров под класс. `provider_routing.route_providers` переписан как
  тонкий адаптер над ним и сохранил прежний контракт.
- `src/assets/query_adapter.py` — запрос под конкретного провайдера с явным языком;
  русский запрос в англоязычный провайдер не отправляется, вместо этого
  `query_translation_required`.
- `src/content/visual_planning/brief.py` + `ScriptScene.visual_brief` +
  `ScriptRequest.visual_briefs` — явный визуальный бриф сцены, additive, в озвучку
  не попадает, проходит через существующий блок `semantic`.
- `candidate_ranker` — доказательством считаются только метаданные провайдера;
  раздельные оценки; `must_avoid` как жёсткий отказ; кириллическая токенизация;
  различие «не подходит» / «невозможно проверить»; проверка длительности.
- `src/assets/generated_infographic.py` — детерминированный статичный SVG для сцен
  с числом; права `user_owned`, provenance `generated_by_project`.
- Провайдеры: Pexels берёт настоящий заголовок из slug страницы вместо эха запроса и
  помечает `tags_source`; Wikimedia/NASA/Internet Archive/Pixabay перестали
  подмешивать токены запроса в теги. `ProviderCapabilities.query_languages`.
- `asset_manager`: удалён скрытый fallback на `candidates[0]`; права-блокировка теперь
  фиксируется без скачивания; в манифест пишутся `asset_strategy`, `source_class`,
  `query_plan`, `required_duration_sec`, `rejected_reasons`.

### Тесты

`tests/test_visual_retrieval_repair.py` (43) и `tests/test_visual_retrieval_regression.py`
(14) — восемь сцен провалившегося прогона офлайн, с настоящими заголовками неверных
клипов. Полный suite: **1136 тестов, OK** (было 1079).

Правки в существующих тестах и фикстурах, вызванные реальностью, а не удобством:
`test_script_engine_pipeline` перестал требовать `schema_version == 1` от всех проектов
на диске (первый проект, созданный самим движком, сделал это утверждение ложным);
`FakeStockProvider` отдаёт 30 с вместо 5 с и не эхом запроса в тегах.

### Live smoke test

Wikimedia на `McMurdo Dry Valleys Antarctica` вернула точные снимки Сухих долин,
NASA — `Dry Valleys, Antarctica`; до Q2.1 те же сцены давали 0 результатов. Pexels на
`antarctic landscape` вернул `frozen antarctic landscape under blue sky` с настоящим
заголовком вместо `Pexels video <id>`. Скачиваний не выполнялось.

**Ограничения зафиксированы** в `docs/implementation/visual_retrieval_repair/VISUAL_RETRIEVAL_MAP.md`.

**API/платные вызовы:** нет. **TTS/Vision/render:** нет. **Сеть:** только бесплатный
поиск в smoke-тесте. **Git write:** только локальный коммит этапа.

**Рекомендуемый следующий этап:** повторный прогон того же проекта с нанопластиком
и сравнение подбора. Автоматически не переходить.

---

## Real Shorts E2E-A Retest — контрольный прогон после Q2.1 — ВЫПОЛНЕН

Проект: `projects/2026-07-26_nanoplastik-v-antarktide-q2-1-retest`. Тот же сценарий
дословно, тот же канал. Кода не менял.

Результат: было 0 подходящих из 8 и 8 принятых неверных файлов; стало 2 сцены готовы,
1 требует подтверждения, 2 честно пусты, 3 файла отклонены вручную как формально прошедшие,
но неверные по смыслу. Wikimedia, NASA и Internet Archive начали возвращать полезные
результаты; лучший материал для сцены 006 (`PTR-TOF1000 Ultra Ionicon mass spectrometer`)
найден в Wikimedia и заблокирован license policy из-за share-alike. Сцены 002 и 003
остались без файлов — подтверждение, что удалённая ветка `candidates[0]` больше не
скачивает отклонённого кандидата.

Ретест вскрыл пять разрывов, три из которых закрыл этап Q2.2A.
Пакет сравнения: `assets/review/q21_retest_review.html` внутри проекта.

---

## Stage Q2.2A — Проводка визуального брифа и жёсткие гейты — ЗАВЕРШЁН

Точечный ремонт по итогам ретеста. Новых систем не создавалось.

### Разрыв 1 — брифы нельзя было передать штатно

Q2.1 добавил контракт, но ни один путь его не заполнял: в ретесте бриф пришлось писать
в `script.json` вручную. Добавлен **один** вход — JSON-файл:
`create --visual-brief FILE` → `ContentCreationRequest.visual_briefs` →
`create_news_to_short_job` → `NewsJob.visual_briefs` (в `job.json`) →
`build_script_request` → `ScriptRequest.visual_briefs` → `user_supplied` → `script.json`.
Тот же флаг у офлайн-проверки `script generate --visual-brief`: печатает применённый бриф
по сценам, без сети и без записи. Файл валидируется до запуска
(`validate_visual_brief_file`). Старые команды и `job.json` без поля работают как прежде.

### Разрыв 2 — спецификация инфографики терялась

У `VisualBrief` не было поля `infographic`, поэтому `parse_brief` его отбрасывал и
`spec_from_scene` на сцене плана всегда возвращал `None`. Поле добавлено; значения
проходят round-trip без изменений (54%, 13 точек, 7 активных, 7 и 2 метки слоёв).
Дополнительно: сгенерированный ассет больше не отправляется в путь скачивания — он уже
локальный, и попытка «скачать» его сбрасывала выбор.

### Разрыв 3 — `data_infographic` опрашивал внешние провайдеры

`build_strategy` дописывал «всех остальных доступных» после предпочтительного списка,
и сцена с процентом ушла в Wikimedia, NASA и Internet Archive. Введён
`RESTRICTED_TO_PREFERRED`: для `data_infographic` и `manual_required` список провайдеров
исчерпывающий. Сцена заканчивается собственной инфографикой либо
`unresolved_generator_failed`.

### Жёсткие гейты

- **Semantic.** Кандидат не выбирается автоматически, если нет метаданных провайдера
  или требование `must_include` написано письменностью, которой в них быть не может
  (`semantic_unverified:<термины>`). Побочное непроверяемое поле фиксируется, но выбор
  не блокирует — иначе отказ получал бы материал, все требования которого выполнены.
- **Framing.** Кадр обрезается до 9:16; если остаётся меньше 540 px по ширине (растяжение
  больше 2×), кандидат отклоняется (`framing_unusable`). `1280×720` даёт 405 px и
  отклоняется, `1920×1080` даёт 607 px и проходит. Вердикт пишется всегда.

### Тесты

`tests/test_visual_retrieval_wiring.py` — 24 теста. Полный suite: **1160 тестов, OK**
(было 1136). Изменено одно утверждение в тесте Q2.1: универсальный гейт даёт причину
`semantic_unverified` вместо прежней `no_semantic_evidence`.

### Что осталось открытым

Два ложных принятия ретеста Q2.2A не закрывает и закрыть не может на метаданных:
пресс-день миссии на Марс содержал «mass spectrometer», описание раскола айсберга —
«Antarctica». Оба прошли честно по описанию провайдера. Различить их способен только
анализ самого кадра — отдельный этап.

**API/платные вызовы:** нет. **Сеть:** нет. **TTS/Vision/render:** нет.
**Git write:** только локальный коммит этапа.

**Рекомендуемый следующий этап:** повторный прогон ретеста уже через `--visual-brief`,
либо semantic vision для оставшихся ложных принятий. Автоматически не переходить.

---

## Git

Baseline-коммит `chore: establish tested project baseline through B3` зафиксировал всю
существовавшую на тот момент кодовую базу и работу этапов через B3 (745 тестов, OK).
Следом закоммичен этап S1-Light (`chore: clean repository root and organize
documentation`) — перенос корневой документации и безопасная уборка кэшей. Третьим
идёт `feat(scripts): introduce extensible script engine foundation` — этап Q1
(859 тестов, OK); он включает и код, начатый в предыдущей сессии, и исправления,
найденные его аудитом, одним коммитом, потому что незакоммиченный код был
неработоспособен и отдельного осмысленного состояния не образует. Четвёртым идёт
`feat(visual-planning): add semantic scene planning foundation` — этап Q2
(932 теста, OK). `.gitignore`
дважды точечно исправлен: сначала `/projects/` (не затрагивая `src/projects/`), затем
`/project_solar_vs_nuclear/` (не затрагивая ничего с похожим именем в другом месте).
Remote не настроен, push не выполнялся ни разу; `git gc`/`reset`/`rebase`/`clean` не
запускались.

До этих двух коммитов рабочее дерево долго оставалось незакоммиченным по историческим
причинам: оно содержало большой объём чужого untracked-кода (`src/content_creation/`,
`src/news/`, `src/audio/`, `apps/`, `anime_factory/`, десятки тестов), существовавшего
до автономной сессии, и коммит любого точечного изменения затянул бы в историю
неотносящуюся к этапу реализацию. Единственный tracked-файл с точечными правками того
периода — `pipeline.py` (+5 строк: флаг `--execute-voice`), включённый в baseline.

Полный список изменённых/созданных файлов по каждому этапу — в разделах «Что изменено»
выше.
