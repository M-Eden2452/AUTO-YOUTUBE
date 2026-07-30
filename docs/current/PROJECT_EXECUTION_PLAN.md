---
status: active
created_at: 2026-07-30
updated_at: 2026-07-30
baseline_head: fe2df5b
working_branch: governance-reset
owner_decisions_date: 2026-07-30
current_checkpoint: PLAN-1A
next_exact_action: git status --short --branch
source_paths:
  - AGENTS.md
  - pyproject.toml
  - requirements.txt
  - requirements.lock
  - .gitignore
  - docs/current/CURRENT_STATE.md
  - docs/current/START_HERE.md
  - docs/current/SYSTEM_MAP.md
  - docs/current/ARCHITECTURE_BOUNDARY_MAP.md
  - docs/current/CLEANUP_REGISTRY.md
  - docs/handoff/PROJECT_RESCUE_MASTER_PLAN.md
  - src/production_catalog
  - src/config_resolver
  - src/assets
  - src/news
  - src/providers
  - src/audio
  - src/subtitles
  - anime_factory
  - apps
  - tests
  - tools/qa
---

# AI-YouTube Project Execution Plan

Временный orchestration-документ на период согласованной программы работ.
Он задаёт **порядок выполнения** и ничего больше. Он не заменяет `AGENTS.md`,
`CURRENT_STATE.md`, `PRODUCT_PLAN.md` и `CLEANUP_REGISTRY.md` и не является
архитектурной или продуктовой спецификацией.

После полного завершения программы этот файл удаляется из `docs/current/`
и сохраняется одним архивным snapshot — см. «Completion and archive policy».

## Current checkpoint

- **Текущий шаг:** PLAN-1A (первая часть checkpoint 9B-C01), не начат.
- **Выполнено:** PLAN-0 — создан этот план; ветка `governance-reset`.
- **Зелёные проверки:** `tools.qa.check_agent_docs`.
- **Заблокировано:** PLAN-9* и далее до завершения PLAN-1A–1D
  (включая C01-SEM), PLAN-8 и отдельного owner approval.
  PLAN-11 M2 — до подтверждения бюджета.
- **Следующая точная команда:** `git status --short --branch`
- **После проверки Git выполнить:** PLAN-1A inventory.
- **Что нельзя повторять:**
  - закрывать шаг без зелёной обязательной проверки;
  - записывать число тестов, длительность прогона или accuracy как норму;
  - менять production-код до завершения PLAN-1 и owner approval;
  - создавать третий плановый документ;
  - архивировать `PROJECT_RESCUE_MASTER_PLAN.md` или
    `ARCHITECTURE_BOUNDARY_MAP.md` до завершения PLAN-1;
  - снимать с Git `docs/implementation` целым семейством.

## Шаблон задания для нового чата

Историю предыдущих чатов пересказывать не нужно. Достаточно отправить:

```text
Работай в G:\Projects\AI-YouTube.
Сначала выполни git status --short --branch, git log -5 --oneline и
git diff --stat. Прочитай AGENTS.md и полностью
docs/current/PROJECT_EXECUTION_PLAN.md. Исторический
docs/handoff/PROJECT_RESCUE_MASTER_PLAN.md читай как context согласно AGENTS.md,
но не обновляй как current plan.

Продолжи только current_checkpoint активного execution plan и выполни один
bounded sub-slice. Перед изменением проверь фактические callers, tests,
contracts и существующих owners; не создавай дублирующую реализацию.
Запусти только required/targeted проверки этого slice; full offline suite —
только когда его требует план или меняется shared boundary.

Не выполняй сеть, provider download/search, Vision, TTS, платные вызовы,
реальный render, удаление/перенос runtime или user data без моего отдельного
разрешения. После зелёных проверок обнови checkpoint/evidence в активном плане,
покажи diff summary и закоммить slice отдельным commit с
Plan-Step: <ID>. В конце сообщи результат, проверки, commit и следующий
точный checkpoint.
```

Если задача только на review, в последнем абзаце следует заменить
«выполни/закоммить slice» на «ничего не меняй и дай вывод».

## Source-of-truth precedence

1. Git и фактический код.
2. Реальные tests и artifacts.
3. **Этот файл — порядок выполнения текущей программы.**
4. `CURRENT_STATE.md` — фактическое состояние продукта.
5. `PRODUCT_PLAN.md` — продуктовая цель и evidence (создаётся в PLAN-8).
6. `CLEANUP_REGISTRY.md` — переходные пути, owners и exit conditions.
7. `docs/adr/` — зафиксированные долговечные решения.
8. Historical plans и audits — только как context.

**Отношение к `docs/handoff/PROJECT_RESCUE_MASTER_PLAN.md`.** Master plan
остаётся **историческим исходным документом** и источником данных для PLAN-1.
Его разделы «Что делать первым» и «Текущий handoff» отражают состояние на
2026-07-29 и **не являются** текущим порядком работ: порядок задаёт этот файл.
Master plan не обновляется как current plan и не архивируется до завершения
PLAN-1. Противоречие между двумя документами разрешается в пользу этого файла
только по вопросу порядка выполнения; по фактам архитектуры приоритет у кода.

Если код или tests противоречат этому плану, агент обязан остановиться,
проверить evidence и обновить план после решения владельца.

**Временная маршрутизация агентов.** До закрытия PLAN-1 master plan и этот
файл указывают один следующий checkpoint — 9B-C01. В заключительном slice
PLAN-1D в `AGENTS.md` и `START_HERE.md` добавляется короткая ссылка на активный
execution plan. До этой ссылки checkpoint нельзя переводить на PLAN-2:
иначе новый агент, буквально выполнив текущий `AGENTS.md`, снова начнёт C01.

## Locked owner decisions

Подтверждено владельцем на 2026-07-30:

1. Ближайший продуктовый приоритет — визуальная релевантность и завершённость
   Shorts.
2. Проект должен представлять несколько понятных инструментов поверх общего
   переиспользуемого ядра.
3. `content_creator` — основной инструмент создания новых видео; longform и
   documentary развиваются как workflows/templates внутри него, а не как третья
   платформа.
4. `video_repurposer` — подтверждённая долгосрочная часть продукта: нарезка
   стримов, подкастов, мультфильмов, фильмов и локальных длинных видео.
   Развивается из существующего Anime Factory. **Второй clip pipeline с нуля
   запрещён.**
5. Отсутствие `video_repurposer`-проектов сейчас не доказывает отсутствие
   потребности: capability выключена. Приоритетом он при этом не является и
   остаётся disabled до migration и product evidence.
6. Runtime Workspace остаётся целевой архитектурой: код и пользовательские
   данные должны быть физически разделены. Физическая runtime migration сейчас
   отложена; `WorkspacePaths`, tolerant legacy reads и цель
   `copy → verify → switch` сохраняются.
7. Внешний `AI-YouTube-System` допустим только как необязательный
   пользовательский mirror и не является source of truth.
8. Обязательное дерево `core/services/infrastructure` отменено. Структура
   остаётся настолько плоской, насколько позволяет продукт; новый уровень
   каталогов создаётся только при доказанной границе, нескольких реальных
   callers и измеримой пользе.
9. Для каждой capability не должно быть двух реализаций, способных разойтись в
   поведении. Физическое расположение кода само по себе дефектом не является;
   переносить рабочие файлы ради соответствия дереву запрещено.
10. Канонический пользовательский путь — `python -m ai_youtube`. Старые
    entrypoints (`python -m src.content_creation.cli`, `python pipeline.py`,
    `python -m apps.*`) не являются постоянным пользовательским контрактом, но
    **сейчас не удаляются**: сначала PLAN-1 и перевод tests/docs.
11. Владелец подтвердил отсутствие личных `.bat`/`.cmd`/`.ps1`, ярлыков,
    Windows Tasks и IDE Run Configurations, которые нужно сохранять ради старых
    команд. Поиск по компьютеру вне репозитория запрещён.
12. R1–R12 становятся новой governance model (внедрение — PLAN-6). Отдельный
    ADR про переход на новые правила не создаётся.
13. Платные и сетевые операции требуют отдельного разрешения на конкретное
    действие. Для M1: 0 USD и ноль новых платных Vision-вызовов. Бюджет M2 —
    `TBD`, подтверждается отдельно перед первым реальным платным запуском.

## Safety boundaries

Действуют правила R1–R3 из `AGENTS.md`; здесь они не дублируются.
Дополнительно на период этой программы:

- пользовательские данные не изменяются: `projects/`, `assets/`,
  `manual_assets/`, `music/`, `outputs/`, media, manifests, evidence,
  license proof, voice samples, `.env`;
- сеть, provider search, download, Vision, TTS, render и платные API не
  выполняются без отдельного разрешения на конкретное действие;
- synthetic render в tempfile разрешён и обязателен для renderer contract
  tests; реальный render пользовательского проекта — только по необходимости и
  с разрешением;
- в `master` не сливать и ничего не публиковать без отдельного разрешения.

## Measurement policy

Число тестов, длительность прогона и accuracy моделей — **изменчивые
наблюдения**. Они записываются только как измерение с датой и проверяемым
состоянием Git и никогда не становятся нормой в правилах, тестах или
документах. Критерий успеха проверки — «команда завершилась с exit code 0 без
неожиданных failures/errors», а не совпадение с записанным числом.

Точные **контрактные** значения разрешены и иногда обязательны: `schema_version`,
budget cap, timeout, количество обязательных artifacts, лимиты провайдеров.

Измерения на HEAD `fe2df5b`, 2026-07-30, дерево чистое:

- полный offline suite: 1441 теста, около 245 секунд, 4 failures и 3 errors;
- `tests.test_voice_profile_resolution`: 8 тестов, 1 failure и 3 errors;
- `tests.test_autonomous_completion_pipeline`: 14 тестов, 3 failures;
- кандидат `fast`-режима без десяти render-тяжёлых модулей: около 1350 тестов,
  около 34 секунд;
- канонический CLI: `--help`, `capabilities --json`, `applications list` —
  примерно по одной секунде каждая;
- сохранённая калибровка live-eval: 3 сцены, 6 кандидатов, 12 кадров;
  индикативное измерение, **не** production evidence.

## Execution protocol

1. Разрешённые зоны каждого шага неявно включают этот файл только для
   обновления checkpoint, статуса, фактических проверок и новых evidence.
2. Один bounded slice — один commit. Commit message содержит trailer
   `Plan-Step: <ID>`; Git log является авторитетом для hash.
3. Собственный hash невозможно записать внутри того же commit без
   самоссылочного amend-цикла. Поэтому поле `commit` может заполняться
   последующим plan-only уточнением, но его отсутствие не делает проверенный
   slice незавершённым.
4. Verification-only checkpoint может иметь plan-only commit с измерением и
   указанием **проверенного исходного HEAD**. Последующий docs-only commit не
   выдаётся за проверенный production HEAD.
5. Если один шаг требует нескольких независимых изменений или затрагивает
   больше одной ownership/behavior boundary, он делится на под-slices до
   реализации. Заголовок-этап закрывается только после всех его под-slices.
6. После каждого commit повторяются `git status --short --branch`,
   `git diff --check` и проверки, указанные для slice. Сеть и платные действия
   не считаются проверкой без отдельного owner approval.
7. Targeted tests выполняются после каждого behavior/code slice. Full offline
   suite не запускается автоматически после локального leaf-изменения.
8. Full offline suite обязателен на границе shared contract, persisted schema,
   paths/package root, provider registry, compatibility retirement и при
   закрытии крупного этапа, который объединяет несколько product slices.
9. Если этап состоит из contract-foundation и нескольких adapters, `full`
   выполняется после contract slice и один раз при закрытии семейства; каждый
   adapter между ними проверяется targeted tests.
10. Docs-only и report-only slices не требуют `full`, если не меняют test
    discovery, runner или production contract. Для них обязательны собственные
    QA/tests и `git diff --check`.

## Execution table

Формат каждого шага одинаков. `commit` заполняется только фактическим hash
после выполнения; заранее hash не придумывается — источником является Git.

Критический путь:

`PLAN-1 → PLAN-2/3 → PLAN-4 → PLAN-5 → PLAN-6A/6B/6C →
PLAN-7/8 → PLAN-9A → (PLAN-9B/9C и PLAN-10A/10B/10C) →
PLAN-9D/9E → PLAN-11 → PLAN-12 → PLAN-13 → PLAN-14 → PLAN-15`.

Независимые под-slices могут меняться местами только когда их зависимости,
allowed zones и owner approvals не пересекаются; изменение порядка
фиксируется здесь до работы, а не задним числом.

### PLAN-0 — versioned execution plan

- **status:** completed · **completed:** 2026-07-30 ·
  **commit:** `4027269`
- **цель:** один отслеживаемый план для Claude, Codex и других агентов.
- **зависимости:** —
- **разрешённые зоны:** `docs/current/PROJECT_EXECUTION_PLAN.md`,
  одна короткая ссылка в `docs/current/CURRENT_STATE.md`.
- **запрещено:** всё прочее, включая правку master plan.
- **измеримый результат:** план существует, checkpoint виден, ссылка добавлена.
- **required verification:** `tools.qa.check_agent_docs`, `git diff --check`.
- **фактические проверки:** обе команды повторно завершились с exit code 0 на
  clean HEAD `4027269`.
- **rollback:** один commit.

### PLAN-1 — checkpoint 9B-C01: caller/ownership inventory

- **status:** in_progress; следующий slice PLAN-1A.
- **цель:** зафиксировать точных callers, owners, replacement и exit condition
  для всех переходных путей. Read-only относительно production behavior.
- **зависимости:** PLAN-0. **Не зависит** от зелёного full suite.
- **разрешённые зоны:** PLAN-1A–1C — только
  `docs/current/CLEANUP_REGISTRY.md`; PLAN-1D дополнительно допускает короткую
  routing-ссылку в `AGENTS.md` и `docs/current/START_HERE.md`.
- **запрещено:** production-код, tests, схемы, config, любые move/delete/untrack,
  создание новых документов, правка master plan, изменение поведения.
- **bounded sub-slices:**
  - **PLAN-1A — entrypoints и package roots:** C01–C04, C08–C11;
    `pyproject.toml`, console scripts, module entrypoints, `apps/*`, root
    `ai_youtube/`, `src.content_creation.cli`, `pipeline.py`, `legacy/`,
    tests/docs/string/dynamic callers и repository-local task/IDE configs;
  - **PLAN-1B — application/shared ownership:** C05–C08 и C12–C16;
    Fullscreen, Story Card, Anime project/transcription/subtitles/FFmpeg/render,
    music, project/workspace и shared-service границы;
  - **PLAN-1C — C01-SEM и evidence/docs:** semantic selection/visual service,
    visual planner, asset completion, `vision_validator`,
    `docs/implementation` пофайлово и production dependencies на docs;
  - **PLAN-1D — closure:** exact-duplicate hash report, orphan/empty-directory
    candidates как review-only evidence, итоговые owners/exit conditions,
    выбор первых bounded migration/product slices и короткая маршрутизация
    агентов на этот активный plan.
- **обязательные части:**
  - **C01-SEM** — ownership для `semantic_selection`, `semantic_visual`, visual
    planner и asset completion: кто принимает решение о пригодности кандидата,
    где заканчивается shared service и начинается workflow policy, какова роль
    заглушки `vision_validator` и подключённого, но не влияющего на отбор
    `semantic_visual_service`. **Жёсткий gate для PLAN-9\* и PLAN-10\*.**
  - пофайловая классификация `docs/implementation`: current source of truth,
    active fixture, production/evaluation dependency, невоспроизводимое paid
    evidence, historical report, generated output, runtime artifact, exact
    duplicate, obsolete plan, safe delete candidate;
  - внешние callers внутри репозитория: module entrypoints через `python -m`,
    console scripts в `pyproject.toml`, `*.bat`, `*.cmd`, `*.ps1`, `.vscode`,
    `.idea`, task/config files, tests, docs, относительные, динамические и
    строковые вызовы. Статический import-граф **не** является доказательством
    отсутствия внешнего caller. Поиск вне репозитория запрещён;
  - семейства: root `ai_youtube/` против `src/ai_youtube/`,
    `src.content_creation.cli`, `apps/*`, `pipeline.py` и `src.legacy_pipeline`,
    `anime_factory` с `EpisodePaths`/transcription/subtitles/FFmpeg,
    `src.audio.music_manifest` против `src.music_*`, `legacy/`, semantic
    evaluation facade и прочие re-export пути;
  - exact-duplicate hash report по tracked production-файлам; вывод о
    дублировании бизнес-логики только по совпадению basename запрещён.
- **измеримый результат:** C01–C16 имеют точных callers, current и target owner,
  persisted/runtime зависимость, public promise, replacement, класс и точное
  exit condition; C01-SEM закрыт; классификация `docs/implementation` полная;
  назван первый bounded slice для перехода, но не выполнен; следующий агент
  однозначно попадает в PLAN-2, а не в historical master plan.
- **required verification:** после каждого под-slice
  `tools.qa.check_agent_docs`, `git diff --check`.
- **rollback:** один commit на под-slice.

### PLAN-2 — baseline repair: voice-profile fixtures

- **status:** pending · **completed:** — · **commit:** —
- **цель:** убрать устаревшую изоляцию через `os.chdir` и использовать явный
  `channels_dir` либо существующий path seam.
- **зависимости:** PLAN-1.
- **разрешённые зоны:** `tests/test_voice_profile_resolution.py`.
- **запрещено:** production-код, прочие тесты.
- **диагноз:** изоляция через `os.chdir` перестала действовать после того, как
  versioned resources стали резолвиться от корня репозитория, а не от `cwd`;
  реестр читает настоящий `channels/` и возвращает чужой профиль. Production
  корректен.
- **измеримый результат:** модуль завершается без failures и errors; сохранены
  паритет UI и runtime, резолв по display_name, borrowed profile с
  `source_channel_id`, `include_global=False`, понятное сообщение об ошибке.
- **required verification:** только targeted-модуль. Режим `fast` ещё не
  существует до PLAN-5 и поэтому не может быть prerequisite.
- **rollback:** один commit.

### PLAN-3 — baseline repair: completion-wiring fixtures

- **status:** pending · **completed:** — · **commit:** —
- **цель:** создавать обязательные stage outputs согласно output-validated
  idempotency ADR 0006.
- **зависимости:** PLAN-1.
- **разрешённые зоны:** `tests/test_autonomous_completion_pipeline.py`.
- **запрещено:** production-код.
- **диагноз:** три теста помечают стадии `completed`, не создавая обязательных
  outputs, и ожидают поведение до этапа 5D.
- **окончательный resume-факт:** стадия с отсутствующим или непригодным output
  может быть перезапущена; по 28 проверенным проектам платные и сетевые стадии
  не перезапускаются; у 7 проектов могут повториться только локальные
  preview/final render. Старое предположение о повторных платных
  `research`/`script` в current-документы не переносится.
- **измеримый результат:** модуль завершается без failures и errors;
  ожидаемое production-поведение не изменено.
- **required verification:** только targeted-модуль. Совместный полный
  baseline выполняется отдельным PLAN-4.
- **rollback:** один commit.

### PLAN-4 — зелёный baseline

- **status:** pending · **completed:** — · **commit:** —
- **цель:** воспроизводимый зелёный offline baseline.
- **зависимости:** PLAN-2, PLAN-3.
- **разрешённые зоны:** production/tests не меняются; этот plan обновляется
  измерением, проверенным исходным HEAD и новым checkpoint.
- **измеримый результат:** `python -B -m unittest discover -s tests -p "test_*.py"`
  завершается с exit code 0 без неожиданных failures и errors; фактические число
  тестов и время записаны в Measurement policy как измерение с датой и
  проверенным исходным HEAD.
- **required verification:** full offline suite.
- **rollback:** один plan-only checkpoint commit.

### PLAN-5 — единый test runner

- **status:** pending · **completed:** — · **commit:** —
- **цель:** один runner вместо трёх разных правил о тестах.
- **зависимости:** PLAN-4.
- **разрешённые зоны:** `tools/qa/run_tests.py`,
  `.github/workflows/offline-tests.yml` и targeted runner tests.
- **запрещено:** production-код, изменение существующих product-test
  contracts, замена `unittest` как движка, правка network guard. Новые тесты
  самого runner разрешены.
- **режимы:**
  - `smoke` — несколько секунд: import канонического пакета,
    `python -m ai_youtube --help`, `capabilities --json`, `applications list`,
    один безопасный synthetic dry-run при наличии. Только allowlist проверенных
    read-only CLI paths. Учитывать, что tests network guard **не действует**
    автоматически на прямой subprocess CLI;
  - `fast` — suite без render-тяжёлых модулей, ориентир 30–40 секунд;
  - `targeted` — радиус изменённой зависимости;
  - `full` — весь offline suite, включая synthetic renderer contracts.
- **измеримый результат:** четыре режима работают и печатают фактический бюджет;
  вшитых ожидаемых чисел тестов в коде runner нет; каждое исключение из `fast`
  выводится с причиной, а `full` динамически обнаруживает все `test_*.py`;
  offline workflow вызывает тот же `full`, а не поддерживает вторую команду.
  Smoke содержит только доказанно read-only subprocess paths; test-package
  network guard не считается защитой subprocess CLI.
- **required verification:** `smoke` + `fast` + `full`.
- **rollback:** один commit.

### PLAN-6 — governance, ранний minimalism baseline и toolchain audit

- **status:** pending · **completed:** — · **commit:** —
- **цель:** до product/refactor работ закрепить единые правила, измерить
  фактическое загрязнение репозитория и определить владельцев зависимостей.
- **зависимости:** PLAN-5.
- **запрещено:** production-код, удаление/перенос файлов и runtime data,
  создание ADR про governance, обновление lock или скачивание зависимостей.
- **bounded sub-slices:**
  - **PLAN-6A — governance R1–R12 и docs QA:**
    - разрешённые зоны: `AGENTS.md`, `tools/qa/check_agent_docs.py`, связанные
      onboarding и reproducibility tests;
    - R1–R12 в согласованной редакции с категориями A/B/C/D;
    - QA не требует вечного существования конкретных архивных handoff;
    - exact-count проверка skills заменяется минимальным обязательным набором
      критичных skills плюс автоматической проверкой всех найденных;
    - broken link, missing source path и invalid commit — error;
    - возраст документа и превышение рекомендуемого размера — warning;
    - onboarding-лимит `START_HERE.md` может остаться жёстким;
    - `README.md` и `COMMANDS.md` обязаны упоминать канонический CLI;
  - **PLAN-6B — ранний report-only minimalism baseline:**
    - зависимость: PLAN-6A;
    - разрешённые зоны: `tools/qa/check_repository_minimalism.py`, его
      targeted tests, `docs/current/CLEANUP_REGISTRY.md`;
    - отчёт покрывает tracked cache/generated outputs, top-level paths вне
      draft allowlist, exact duplicates, wrappers без registry, retired
      imports, hardcoded machine paths, empty directories и orphan-кандидатов;
    - detector ничего не удаляет; orphan/duplicate остаются review evidence;
  - **PLAN-6C — dependency/toolchain ownership audit:**
    - зависимость: PLAN-6B;
    - read-only по `pyproject.toml`, `requirements.txt`, `requirements.lock`,
      CI/task/config files, Anime/ML optional dependencies, `venv/`,
      MOSS/Whisper/model weights и agent-specific adapters;
    - обновляется только `docs/current/CLEANUP_REGISTRY.md`;
    - фиксируются direct/resolved/optional/toolchain owners, callers,
      воспроизводимость, replacement и exit conditions до package
      consolidation.
- **измеримый результат:** docs QA зелёный при новых правилах; `AGENTS.md`
  в районе ста строк; первый minimalism report сохранён как baseline;
  dependency/toolchain решения известны до PLAN-13C и PLAN-14B.
- **required verification:** PLAN-6A — docs QA + `full`; PLAN-6B — targeted
  tests detector + docs QA; PLAN-6C — docs QA; `git diff --check` всегда.
- **rollback:** один commit на под-slice.

### PLAN-7 — канонический пользовательский CLI в документации

- **status:** pending · **completed:** — · **commit:** —
- **цель:** документация перестаёт обучать устаревшему entrypoint.
- **зависимости:** PLAN-6.
- **разрешённые зоны:** `README.md`, `COMMANDS.md`,
  `skills/create-short-video-first/SKILL.md`, `skills/resume-project/SKILL.md`,
  `skills/replace-visual-slot/SKILL.md`.
- **запрещено:** production-код, **удаление старых entrypoints**.
- **требования:** `COMMANDS.md` — 100–150 строк, основные команды и ссылка на
  `--help`; `README.md` — около 150 строк, фактический продукт,
  active/planned/disabled и быстрый старт. Команды сверять с фактическим
  `--help`, а не по памяти.
- **измеримый результат:** ни один из этих файлов не обучает устаревшему пути.
- **required verification:** docs QA + `smoke`.
- **rollback:** один commit.

### PLAN-8 — PRODUCT_PLAN.md

- **status:** pending · **completed:** — · **commit:** —
- **цель:** отделить продуктовую цель и evidence от архитектурного порядка.
- **зависимости:** PLAN-7.
- **разрешённые зоны:** `docs/current/PRODUCT_PLAN.md`.
- **запрещено:** создание `ARCHITECTURE_DEBT.md` до того, как PLAN-1 докажет
  фактический пробел относительно `CLEANUP_REGISTRY.md`.
- **измеримый результат:** продуктовый приоритет, измеренная база и критерии
  M1/M2/M3 зафиксированы; отдельно записан post-rescue roadmap:
  `video_repurposer` через migration Anime Factory и будущий
  longform/documentary workflow `content_creator`, с entry/enable evidence и
  без создания новых engine stacks. Ориентир до 250 строк.
- **обязательное завершение:** после commit `PRODUCT_PLAN.md` продуктовые
  подробности PLAN-9–PLAN-11 (лестницы, M1/M2/M3, reference domains и quality
  evidence) переносятся туда. В этом execution plan остаются только ID,
  зависимости, allowed/prohibited zones, gates, verification и rollback.
  До появления проверенного `PRODUCT_PLAN.md` текущие подробности не удалять.
- **required verification:** docs QA.
- **rollback:** один commit.

### PLAN-9A — best-so-far foundation и tolerant persistence/resume

- **status:** blocked (PLAN-1 включая C01-SEM, PLAN-8 + owner approval) ·
  **commit:** —
- **цель:** до расширения поиска гарантировать, что лучший найденный материал
  не теряется между итерациями и при `resume`.
- **состав:** top candidates по сцене, best-so-far с обоснованием, semantic
  score, rights status, Vision/evaluation result, manual approvals, выбранный
  fallback. Расширяет существующие `rejected_candidates`/`rejected_reasons`;
  второй manifest или project system не создаётся.
- **ограничения:** additive schema/tolerant reader; старые manifests и resume
  читаются без миграции; characterization-first.
- **измеримый результат:** после остановки, ошибки или resume сохранённый
  best-so-far не ухудшается и остаётся объяснимым.
- **required verification:** targeted persisted-contract tests + `full`.
- **rollback:** один commit.

### PLAN-9B — query expansion и снятие topic-hardcodes

- **status:** blocked (PLAN-9A) · **commit:** —
- **цель:** контролируемая лестница расширения запросов вместо фиксированного
  набора; убрать topic-specific hardcodes.
- **разрешённые зоны:** `src/assets/semantic_selection/query_generator.py`
  и его тесты. Characterization-first.
- **лестница:** точный субъект → субъект и действие → субъект, действие и
  локация → синонимы → альтернативные названия сущности → более широкий
  контекст → другой допустимый план той же идеи → локальная медиатека →
  другой provider → разрешённый fallback.
- **измеримый результат:** topic-specific hardcodes отсутствуют; расширение не
  меняет смысл сцены; `must_avoid` и misleading-gates действуют на каждом уровне.
- **required verification:** targeted query-generator tests; `full` здесь не
  нужен, если shared contract не изменился.
- **rollback:** один commit.

### PLAN-9C — semantic decision wiring

- **status:** blocked (PLAN-9A и закрытый C01-SEM) · **commit:** —
- **цель:** результат semantic-анализа действительно влияет на ranking и отбор.
- **разрешённые зоны:** production asset selection path.
- **запрещено:** создавать второй visual planner, Vision stack или asset
  pipeline; изменять default-поведение в этом slice; **использовать mock
  semantic backend как влияющий на production selection** — mock допустим
  только в wiring-тестах и не является доказательством визуального качества.
- **измеримый результат:** wiring доказан тестами; default-конфигурация
  поведения не меняет.
- **required verification:** targeted selection/wiring tests + `full`, так как
  меняется shared production decision path.
- **rollback:** один commit.

### PLAN-9D — offline visual-quality evidence

- **status:** blocked (PLAN-9B, PLAN-9C) · **commit:** —
- **цель:** доказать улучшение decision path на уже имеющихся данных.
- **источники:** существующий live-eval dataset, уже сохранённые кадры,
  сохранённые результаты предыдущего Vision-прогона, вручную размеченные
  fixtures.
- **запрещено:** новые платные вызовы.
- **измеримый результат:** улучшение решения на известных данных
  зафиксировано; mock как доказательство не используется.
- **required verification:** targeted evaluation tests + offline product
  fixture gate; повторный `full` не нужен без изменения shared contract.
- **rollback:** один commit.

### PLAN-9E — controlled semantic activation

- **status:** blocked (PLAN-9D, PLAN-10C + owner approval) · **commit:** —
- **цель:** включить доказанный semantic decision path только для явно
  выбранного template/project policy.
- **запрещено:** глобально включать paid backend, менять default всех старых
  проектов, использовать mock, ослаблять rights/`must_avoid`/misleading gates.
- **измеримый результат:** opt-in policy имеет безопасный fallback при
  отсутствии результата/бюджета/backend; старые проекты и default config
  сохраняют прежнее поведение; выбор и причина записываются в manifest.
- **required verification:** targeted policy/integration tests + `smoke` +
  `full` как общий activation gate.
- **rollback:** один commit.

### PLAN-10A — query/provider attempt ledger и stop reasons

- **status:** blocked (PLAN-9A) · **commit:** —
- **цель:** каждая попытка и остановка сохранена; best-so-far можно объяснить
  и продолжить после `resume`.
- **допустимые stop reasons:** исчерпаны разрешённые query variants; исчерпаны
  providers и pagination; достигнут budget; несколько итераций не улучшили
  best-so-far; следующий шаг требует отдельного платного разрешения; достигнут
  strict threshold. Бесконечный поиск запрещён.
- **required verification:** targeted persisted-contract tests + `full`.
- **rollback:** один commit.

### PLAN-10B — pagination и provider contract

- **status:** blocked (PLAN-10A) · **commit:** —
- **цель:** поиск не ограничен первой страницей результатов и фиксированным
  лимитом на пару provider × query.
- **граница:** сначала additive pagination/cursor contract и
  characterization старых adapters; затем каждый active provider переводится
  отдельным под-slice. Провайдер без pagination сохраняет bounded single-page
  adapter и честно сообщает exhaustion.
- **required verification:** contract-foundation — targeted + `full`; каждый
  provider adapter — targeted; один итоговый `full` при закрытии family.
- **rollback:** один commit на contract и один на provider-family.

### PLAN-10C — adaptive budget и plateau policy

- **status:** blocked (PLAN-9B, PLAN-10B) · **commit:** —
- **цель:** политика `quick` / `standard` / `deep` вместо одного фиксированного
  лимита. Бюджет учитывает важность и длительность сцены, сложность субъекта,
  число новых уникальных кандидатов, улучшение best-so-far, число providers,
  стоимость вызовов, strict или draft mode.
- **измеримый результат:** поиск продолжается, пока улучшает best-so-far;
  plateau останавливает; одна сложная сцена не останавливает остальные, не
  удаляет найденные assets, не сбрасывает проект и не блокирует reviewable draft.
- **запрещено:** случайный нерелевантный asset ради `completed`, misleading
  visual, `must_avoid` conflict, нарушение rights, ложный `publish_ready`.
- **required verification:** targeted policy tests после каждого slice;
  `full` один раз при закрытии adaptive-search family.
- **rollback:** один commit.

### PLAN-10D — регистрация локальной медиатеки

- **status:** blocked (PLAN-10C + аудит) · **commit:** —
- **предусловие:** аудит paths, rights, provenance и dedup для локальных файлов.
- **цель:** `LocalLibraryStockProvider` участвует в автоматическом поиске
  только если аудит доказал ценность и безопасность.
- **измеримый результат:** при включении провайдер отдаёт только rights-clean
  кандидатов без дублей; при отрицательном решении registry не усложняется.
- **required verification:** при изменении shared provider registry —
  targeted + `full`; для решения `defer/reject` — docs QA.
- **rollback:** один commit.

### PLAN-11 — multi-topic product evidence

- **status:** blocked (PLAN-9E, PLAN-10C) · **commit:** —
- **scope:** текущий automatic asset-search path относится прежде всего к
  `fullscreen_voiceover_v1`. `story_card_text_only_v1` сейчас требует
  явный local `source_asset`; PLAN-11 не выдаёт улучшение одного workflow за
  доказательство качества всех templates.
- **примечание о зависимости:** PLAN-10D не является обязательным условием
  M1, если аудит не доказал ценность/безопасность локальной библиотеки.
  Evidence запускается после каждого product slice на сохранённых fixtures;
  итоговый multi-topic gate не является первой проверкой результата.
- **три reference domains:**
  1. животные и строгий контекст среды: кит или косатка в открытом океане;
     бассейн, шоу и трибуны исключены;
  2. энергетика и технологии: солнечная электростанция, аккумуляторное
     хранилище, энергосеть;
  3. география и инфраструктура: строительство крупного канала через пустыню;
     точные карты, satellite imagery и infographic допустимы, если правдивее
     случайного видео.
- **gate не использует единый глобальный процент видео.** Соотношение
  video / still / infographic определяет template policy.
- **общие требования:** все обязательные сцены имеют безопасный usable visual;
  ноль `must_avoid`; ноль misleading conflicts; ноль нарушений
  rights/provenance; нет новых topic-specific hardcodes; best-so-far и
  rejection evidence сохранены; `resume` не ухудшает результат.
- **M1:** 0 USD, ноль новых платных Vision-вызовов.
  По умолчанию M1 использует сохранённые/local fixtures; новый provider search,
  download или иной сетевой вызов требует отдельного разрешения даже при
  нулевой стоимости.
- **M2:** бюджет платных вызовов — **TBD, owner approval before M2**. Числовые
  лимиты не согласованы и здесь не фиксируются.
- **M3:** `strict` выставляет `publish_ready=true` только после реальной
  визуальной проверки. Бюджет не утверждается до анализа M2.
- **required verification:** product gate. **rollback:** —

### PLAN-12 — классификация и архивирование документации

- **status:** blocked (PLAN-1) · **commit:** —
- **цель:** current navigation ведёт только к актуальным документам.
- **bounded sub-slices:**
  - **PLAN-12A — current docs:** перенести уникальные подтверждённые данные
    `ARCHITECTURE_BOUNDARY_MAP.md` в `SYSTEM_MAP.md`, затем удалить
    current-копию; убрать дубли CURRENT_STATE/START_HERE;
  - **PLAN-12B — данные внутри docs:** перенести production/evaluation fixtures
    из `docs/implementation` в versioned fixture/data owner и обновить callers;
    paid evidence сохранять без переписывания истории;
  - **PLAN-12C — archive:** `PROJECT_RESCUE_MASTER_PLAN.md` и подтверждённо
    исторические plans/audits/reports переместить в `docs/archive`, обновив
    navigation и links.
- **действия по классам:** keep, move, archive, backup_then_untrack, delete,
  defer. Целое семейство одним действием не архивируется и не удаляется.
- **запрещено:** untrack двенадцати reference jpg до переноса dataset;
  переписывать historical snapshot как current; оставлять битые ссылки.
- **required verification:** PLAN-12A/12C — docs QA; PLAN-12B — targeted
  production callers + `full`; `git diff --check` всегда.
- **rollback:** один commit на семейство.

### PLAN-13 — ownership migration и retirement

- **status:** blocked (PLAN-1, PLAN-6C, PLAN-12) · **commit:** —
- **цель:** один owner бизнес-логики, один установленный package root и один
  канонический CLI без потери compatibility/persisted contracts.
- **bounded sub-slices:**
  - **PLAN-13A — caller migration:** одно семейство production callers, затем
    current docs/examples, затем tests;
  - **PLAN-13B — ownership transfer:** переносить implementation, не
    копировать; Fullscreen, Story Card, Anime, projects, assets/providers,
    audio/music, subtitles и rendering — разные commits;
  - **PLAN-13C — wrapper/package retirement:** один wrapper/package family
    после zero-production-caller gate и dependency/toolchain audit PLAN-6C;
    root `ai_youtube/` и `src/ai_youtube/` свести к одному installable
    src-layout package;
  - **PLAN-13D — legacy pipeline:** сохранить только подтверждённые
    maintenance/migration commands; `pipeline.py` удалить последним.
- **предусловие удаления любого старого entrypoint:** переведены или удалены
  tests, актуальные docs, console scripts, module entrypoints и подтверждённые
  внешние callers в том же изменении. Красные tests или лгущая документация
  после retirement недопустимы.
- **измеримый результат:** один physical package root и один канонический CLI.
- **запрещено:** смешивать caller migration, ownership transfer, runtime
  migration и cleanup в одном diff.
- **required verification:** targeted contract + ближайший integration smoke;
  `full` на package/shared-contract boundaries.
- **rollback:** один commit на семейство.

### PLAN-14 — repository/runtime minimalism и переносимость

- **status:** blocked (PLAN-6B, PLAN-6C, PLAN-12, PLAN-13) · **commit:** —
- **цель:** кодовый репозиторий содержит только source/config/tests/versioned
  docs, а runtime/toolchain/user data имеют явных владельцев вне code root.
- **bounded sub-slices:**
  - **PLAN-14A — финальный minimalism QA:** повторно запустить и при
    необходимости усилить созданный в PLAN-6B
    `tools/qa/check_repository_minimalism.py`; сравнить результат с ранним
    baseline и закрыть только подтверждённые нарушения. Orphan/duplicate —
    review evidence, не автоматическое разрешение удалить;
  - **PLAN-14B — dependency/toolchain convergence:** реализовать решения
    аудита PLAN-6C: `pyproject.toml` — владелец direct dependencies,
    `requirements.lock` — проверенный lock; `requirements.txt` оставить,
    генерировать или удалить только по зафиксированному caller/docs gate.
    Anime/ML optional dependencies, `venv/`, MOSS/Whisper/model weights и
    agent-specific adapters имеют раздельных owners. Обновление lock/download
    требует отдельного network approval;
  - **PLAN-14C — generated/cache/empty directories:** удалять только
    воспроизводимые cache/temp и подтверждённо пустые runtime directories по
    проверенному абсолютному пути; пустой `__init__.py` не мусор;
  - **PLAN-14D — runtime dry-run inventory:** counts, manifests, checksums,
    project/media/model/toolchain roots и target workspace; ничего не
    копировать, не переключать и не удалять;
  - **PLAN-14E — workspace migration:** только по отдельному owner approval:
    `copy → verify counts/manifests/checksums → switch`, dual-read legacy roots,
    новые записи во внешний workspace; source остаётся до отдельного retirement;
  - **PLAN-14F — root allowlist:** по одному top-level family за commit;
    tracked source, runtime/user data и generated output классифицируются
    раздельно.
- **измеримый результат:** report-only QA зелёный по утверждённому allowlist;
  runtime default не зависит от repo root/drive; пользовательские данные
  сохранены.
- **required verification:** targeted paths/contracts; `full` после path/
  package/toolchain changes; без реального render и сети.
- **rollback:** один commit на под-slice; data copy не совмещается с source
  retirement.

### PLAN-15 — final rescue acceptance

- **status:** blocked (PLAN-11–PLAN-14) · **commit:** —
- **цель:** доказать чистоту, понятность и переносимость, а не только закрыть
  строки плана.
- **обязательные проверки:**
  - clean Git и отсутствие незаписанного handoff;
  - docs QA, repository minimalism QA, smoke, fast и full offline;
  - canonical CLI и installed package из произвольного temporary checkout/path
    без hardcoded username/drive; сеть не требуется;
  - один owner на capability, один package root/CLI, закрытые wrappers и
    отсутствие доказанных duplicate implementations;
  - старые persisted projects/manifests читаются tolerant readers;
  - runtime/user media counts/checksums не ухудшились;
  - product gate M1 и честный active/planned/disabled catalog.
- **измеримый результат:** `CURRENT_STATE.md` описывает фактический финальный
  продукт; `CLEANUP_REGISTRY.md` не содержит бессрочных переходных состояний
  без owner evidence; post-rescue roadmap для `video_repurposer` и
  longform/documentary находится в `PRODUCT_PLAN.md`, а не в placeholder-коде.
- **required verification:** все перечисленные offline checks.
- **rollback:** финальный docs/checkpoint commit; проблемный implementation
  откатывается по его собственному bounded commit.

## Результат после каждого этапа

Это краткая карта состояния, а не второй набор критериев готовности. Полные
gates и проверки остаются в соответствующих разделах выше.

| После этапа | Что фактически получаем |
|---|---|
| PLAN-0 | Один активный versioned execution plan на отдельной локальной ветке. |
| PLAN-1 | Проверенный реестр всех старых путей, callers, owners, замен и условий удаления; production ещё не перемещается. |
| PLAN-2 | Исправленные voice-profile fixtures без изменения рабочего production resolver. |
| PLAN-3 | Исправленные completion/resume fixtures, соответствующие output-validated idempotency. |
| PLAN-4 | Зелёный и воспроизводимый полный offline baseline на зафиксированном source HEAD. |
| PLAN-5 | Один test runner с режимами `smoke`, `fast`, `targeted`, `full`; локальные проверки и offline CI используют одну командную модель. |
| PLAN-6 | Короткие единые правила для любых AI-агентов, ранний отчёт о мусоре/дублях и проверенная карта dependency/toolchain ownership. |
| PLAN-7 | README, COMMANDS и рабочие skills обучают только каноническому `python -m ai_youtube`; старые entrypoints пока лишь совместимы. |
| PLAN-8 | Отдельный `PRODUCT_PLAN.md` с приоритетами, evidence gates и roadmap двух engines; execution plan становится короче. |
| PLAN-9 | Сохранение best-so-far, переносимое через resume; универсальные queries; semantic decision path доказан и включается только opt-in. |
| PLAN-10 | Ограниченный и объяснимый search loop с ledger, stop reasons, pagination и adaptive budget; локальная библиотека включается только после rights-аудита. |
| PLAN-11 | Проверенное offline M1 evidence на нескольких темах без новых платных Vision-вызовов и без ложных claims по Story Card. |
| PLAN-12 | Current docs содержат только актуальные знания; fixtures получают правильного владельца; historical материалы находятся в archive. |
| PLAN-13 | Один владелец бизнес-логики на capability, один physical package root и один канонический CLI; лишние wrappers retired доказанными slices. |
| PLAN-14 | Минимальный root allowlist, согласованные dependency/toolchain files и переносимый runtime workspace; пользовательские данные сохранены. |
| PLAN-15 | Финально доказанный чистый, понятный, переносимый offline-проект с честным catalog и закрытым cleanup registry. |

## Decisions and discoveries

Только новые факты, меняющие порядок или scope. Не журнал команд.

- **2026-07-30** targeted re-search ограничен одной фазой **на сцену**, а не на
  проект: `targeted_search_done` — локальная переменная
  `complete_scene_assembly` в `src/news/asset_scene_completion.py`, вызываемой
  из per-scene цикла `src/news/asset_manifest_builder.py`.
- **2026-07-30** `config/semantic_visual.json` содержит `enabled: false`,
  `backend: mock`, `semantic_rerank_enabled: false`; режим по умолчанию
  `analyse_and_report`, и в builder на ранжирование влияет только
  `technical_rerank_enabled`. Semantic-слой существует, но не влияет на отбор.
- **2026-07-30** `src/assets/semantic_selection/vision_validator.py` —
  заглушка, безусловно возвращающая `vision_validation_enabled: False`.
- **2026-07-30** `src/assets/semantic_selection/query_generator.py` содержит
  topic-specific hardcode под один субъект и литерал `"nature"` в atmospheric
  fallback.
- **2026-07-30** provider-поиск выполняется без pagination с жёстким лимитом
  результатов на пару provider × query.
- **2026-07-30** `LocalLibraryStockProvider` существует, но не зарегистрирован
  в `create_default_stock_providers`.
- **2026-07-30** production читает данные из
  `docs/implementation/openai_live_evaluation/` через
  `src/assets/semantic_visual_evaluation_tooling.py`; это семейство содержит
  active fixtures и не подлежит массовому untrack.
- **2026-07-30** в репозитории не найдено `.bat`, `.cmd`, `.ps1` и IDE
  launch-конфигураций; владелец подтвердил отсутствие личных внешних команд,
  но старые entrypoints до PLAN-1 и PLAN-13 не удаляются.
- **2026-07-30** нет настроенного remote; действующего CI и доказательств его
  запусков нет; workflow для этого клона выполниться не мог. Локальный запуск
  `full` является основной проверкой.
- **2026-07-30** PLAN-0 уже зафиксирован commit `4027269`; post-commit docs QA
  и `git diff --check` завершились с exit code 0, дерево чистое.
- **2026-07-30** текущий `AGENTS.md` всё ещё направляет rescue-задачу в master
  plan. Пока оба документа указывают C01, конфликт не меняет действие; перед
  переходом на PLAN-2 routing обязан быть исправлен PLAN-1D.
- **2026-07-30** `fast` runner отсутствует; поэтому он удалён из prerequisites
  PLAN-2/PLAN-3 и впервые появляется/проверяется в PLAN-5.
- **2026-07-30** `pyproject.toml` и `requirements.txt` повторяют direct runtime
  dependencies, а `requirements.lock` хранит resolved environment. Это
  кандидат ownership/convergence PLAN-14B, не основание удалять файл сейчас.
- **2026-07-30** `story_card_text_only_v1` требует переданный local
  `source_asset`; automatic asset search в этот workflow не подключён.
  Визуальные PLAN-9–PLAN-11 не считаются доказательством Story Card без
  отдельного workflow evidence.
- **2026-07-30** product sequence изменён: tolerant best-so-far persistence
  предшествует query expansion, pagination и semantic activation, чтобы новые
  попытки не могли терять уже найденный результат.
- **2026-07-30** minimalism QA выполняется дважды: ранний report-only baseline
  после test runner/governance и финальный gate после ownership/docs cleanup.
  Dependency/toolchain audit также перенесён до package consolidation.
- **2026-07-30** verification budget уточнён: targeted tests после каждого
  code slice; `full` — на shared boundaries и при закрытии крупных families,
  а не после каждого локального product leaf.

## Completion and archive policy

Пока PLAN-15 не закрыт, файл имеет `status: active`.

После полного выполнения программы:

1. Выполнить финальную проверку: `smoke`, `fast`, full offline, docs QA,
   canonical CLI smoke, `git diff --check`, проверку неизменности
   пользовательских данных и утверждённые product evidence gates.
2. Обновить `CURRENT_STATE.md`, `PRODUCT_PLAN.md` и `CLEANUP_REGISTRY.md`
   только если их фактическое состояние изменилось.
3. Сделать финальную версию этого файла со `status: completed`.
4. Переместить её в
   `docs/archive/handoff/PROJECT_EXECUTION_PLAN_<start-date>_<finish-date>.md`.
5. Удалить активный путь `docs/current/PROJECT_EXECUTION_PLAN.md`.
6. Удалить ссылки на активный план из `AGENTS.md`, `START_HERE.md`,
   `CURRENT_STATE.md` и других current-документов.

Новый активный план поверх завершённого не создаётся. Следующая крупная
программа при необходимости получает собственный `PROJECT_EXECUTION_PLAN.md`.
