---
status: active
created_at: 2026-07-30
updated_at: 2026-07-30
baseline_head: fe2df5b
working_branch: governance-reset
owner_decisions_date: 2026-07-30
current_checkpoint: PLAN-1
next_exact_action: git status --short --branch
source_paths:
  - AGENTS.md
  - docs/current/CURRENT_STATE.md
  - docs/current/CLEANUP_REGISTRY.md
  - docs/handoff/PROJECT_RESCUE_MASTER_PLAN.md
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

- **Текущий шаг:** PLAN-1 (checkpoint 9B-C01), не начат.
- **Выполнено:** PLAN-0 — создан этот план; ветка `governance-reset`.
- **Зелёные проверки:** `tools.qa.check_agent_docs`.
- **Заблокировано:** PLAN-9* и далее до завершения PLAN-1 (включая C01-SEM) и
  отдельного owner approval. PLAN-11 M2 до подтверждения бюджета.
- **Следующая точная команда:** `git status --short --branch`
- **После проверки Git выполнить:** PLAN-1 inventory.
- **Что нельзя повторять:**
  - закрывать шаг без зелёной обязательной проверки;
  - записывать число тестов, длительность прогона или accuracy как норму;
  - менять production-код до завершения PLAN-1 и owner approval;
  - создавать третий плановый документ;
  - архивировать `PROJECT_RESCUE_MASTER_PLAN.md` или
    `ARCHITECTURE_BOUNDARY_MAP.md` до завершения PLAN-1;
  - снимать с Git `docs/implementation` целым семейством.

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

## Execution table

Формат каждого шага одинаков. `commit` заполняется только фактическим hash
после выполнения; заранее hash не придумывается — источником является Git.

### PLAN-0 — versioned execution plan

- **status:** completed · **completed:** 2026-07-30 · **commit:** —
- **цель:** один отслеживаемый план для Claude, Codex и других агентов.
- **зависимости:** —
- **разрешённые зоны:** `docs/current/PROJECT_EXECUTION_PLAN.md`,
  одна короткая ссылка в `docs/current/CURRENT_STATE.md`.
- **запрещено:** всё прочее, включая правку master plan.
- **измеримый результат:** план существует, checkpoint виден, ссылка добавлена.
- **required verification:** `tools.qa.check_agent_docs`, `git diff --check`.
- **фактические проверки:** заполняется при commit.
- **rollback:** один commit.

### PLAN-1 — checkpoint 9B-C01: caller/ownership inventory

- **status:** pending · **completed:** — · **commit:** —
- **цель:** зафиксировать точных callers, owners, replacement и exit condition
  для всех переходных путей. Read-only относительно production behavior.
- **зависимости:** PLAN-0. **Не зависит** от зелёного full suite.
- **разрешённые зоны:** только `docs/current/CLEANUP_REGISTRY.md`.
- **запрещено:** production-код, tests, схемы, config, любые move/delete/untrack,
  создание новых документов, правка master plan.
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
  назван первый bounded slice для перехода, но не выполнен.
- **required verification:** `tools.qa.check_agent_docs`, `git diff --check`.
- **rollback:** один commit.

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
- **required verification:** модуль + `fast`.
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
- **required verification:** модуль + `fast`.
- **rollback:** один commit.

### PLAN-4 — зелёный baseline

- **status:** pending · **completed:** — · **commit:** —
- **цель:** воспроизводимый зелёный offline baseline.
- **зависимости:** PLAN-2, PLAN-3.
- **разрешённые зоны:** только запуск, изменений файлов нет.
- **измеримый результат:** `python -B -m unittest discover -s tests -p "test_*.py"`
  завершается с exit code 0 без неожиданных failures и errors; фактические число
  тестов и время записаны в Measurement policy как измерение с датой.
- **required verification:** full offline suite.
- **rollback:** —

### PLAN-5 — единый test runner

- **status:** pending · **completed:** — · **commit:** —
- **цель:** один runner вместо трёх разных правил о тестах.
- **зависимости:** PLAN-4.
- **разрешённые зоны:** `tools/qa/run_tests.py`.
- **запрещено:** production-код, tests, замена `unittest` как движка, правка
  network guard.
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
  вшитых ожидаемых чисел тестов в коде runner нет.
- **required verification:** `smoke` + `fast` + `full`.
- **rollback:** один commit.

### PLAN-6 — governance R1–R12 и QA

- **status:** pending · **completed:** — · **commit:** —
- **цель:** заменить накопленный набор правил на R1–R12 и привести QA в
  соответствие.
- **зависимости:** PLAN-5.
- **разрешённые зоны:** `AGENTS.md`, `tools/qa/check_agent_docs.py`, связанные
  onboarding и reproducibility тесты.
- **запрещено:** production-код, создание ADR про governance.
- **требования:**
  - R1–R12 в согласованной редакции с категориями A/B/C/D;
  - QA не требует вечного существования конкретных архивных handoff;
  - exact-count проверка skills заменяется минимальным обязательным набором
    критичных skills плюс автоматической проверкой всех найденных;
  - broken link, missing source path и invalid commit — error;
  - возраст документа и превышение рекомендуемого размера — warning;
  - onboarding-лимит `START_HERE.md` может остаться жёстким;
  - `README.md` и `COMMANDS.md` обязаны упоминать канонический CLI.
- **измеримый результат:** docs QA зелёный при новых правилах; `AGENTS.md`
  в районе ста строк.
- **required verification:** docs QA + `full`.
- **rollback:** один commit.

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
  M1/M2/M3 зафиксированы; ориентир до 250 строк.
- **required verification:** docs QA.
- **rollback:** один commit.

### PLAN-9A — query expansion и снятие topic-hardcodes

- **status:** blocked (PLAN-1 + owner approval) · **commit:** —
- **цель:** контролируемая лестница расширения запросов вместо фиксированного
  набора; убрать topic-specific hardcodes.
- **зависимости:** PLAN-1. **Не** зависит от PLAN-9B.
- **разрешённые зоны:** `src/assets/semantic_selection/query_generator.py`
  и его тесты. Characterization-first.
- **лестница:** точный субъект → субъект и действие → субъект, действие и
  локация → синонимы → альтернативные названия сущности → более широкий
  контекст → другой допустимый план той же идеи → локальная медиатека →
  другой provider → разрешённый fallback.
- **измеримый результат:** topic-specific hardcodes отсутствуют; расширение не
  меняет смысл сцены; `must_avoid` и misleading-gates действуют на каждом уровне.
- **required verification:** targeted + `full`.
- **rollback:** один commit.

### PLAN-9B — semantic decision wiring

- **status:** blocked (PLAN-1 включая C01-SEM + owner approval) · **commit:** —
- **цель:** результат semantic-анализа действительно влияет на ranking и отбор.
- **зависимости:** PLAN-1 и закрытый C01-SEM.
- **разрешённые зоны:** production asset selection path.
- **запрещено:** создавать второй visual planner, Vision stack или asset
  pipeline; изменять default-поведение в этом slice; **использовать mock
  semantic backend как влияющий на production selection** — mock допустим
  только в wiring-тестах и не является доказательством визуального качества.
- **измеримый результат:** wiring доказан тестами; default-конфигурация
  поведения не меняет.
- **required verification:** targeted + `full`.
- **rollback:** один commit.

### PLAN-9C — offline visual-quality evidence

- **status:** blocked (PLAN-9B) · **commit:** —
- **цель:** доказать улучшение decision path на уже имеющихся данных.
- **источники:** существующий live-eval dataset, уже сохранённые кадры,
  сохранённые результаты предыдущего Vision-прогона, вручную размеченные
  fixtures.
- **запрещено:** новые платные вызовы.
- **измеримый результат:** улучшение решения на известных данных
  зафиксировано; mock как доказательство не используется.
- **required verification:** targeted + `full`.
- **rollback:** один commit.

### PLAN-10A — best-so-far и tolerant persistence/resume

- **status:** blocked (PLAN-9C) · **commit:** —
- **цель:** лучший найденный материал не теряется между итерациями и при
  `resume`.
- **состав:** top candidates по сцене, best-so-far с обоснованием, semantic
  score, rights status, Vision/evaluation result, manual approvals, выбранный
  fallback. Расширяет существующие `rejected_candidates`/`rejected_reasons`,
  второй manifest не создаётся.
- **required verification:** targeted + `full`. **rollback:** один commit.

### PLAN-10B — query/provider attempt ledger и stop reasons

- **status:** blocked (PLAN-10A) · **commit:** —
- **цель:** каждая остановка имеет сохранённую причину.
- **допустимые stop reasons:** исчерпаны разрешённые query variants; исчерпаны
  providers и pagination; достигнут budget; несколько итераций не улучшили
  best-so-far; следующий шаг требует отдельного платного разрешения; достигнут
  strict threshold. Бесконечный поиск запрещён.
- **required verification:** targeted + `full`. **rollback:** один commit.

### PLAN-10C — pagination и provider contract

- **status:** blocked (PLAN-10B) · **commit:** —
- **цель:** поиск не ограничен первой страницей результатов и фиксированным
  лимитом на пару provider × query.
- **required verification:** targeted + `full`. **rollback:** один commit.

### PLAN-10D — adaptive budget и plateau policy

- **status:** blocked (PLAN-10C) · **commit:** —
- **цель:** политика `quick` / `standard` / `deep` вместо одного фиксированного
  лимита. Бюджет учитывает важность и длительность сцены, сложность субъекта,
  число новых уникальных кандидатов, улучшение best-so-far, число providers,
  стоимость вызовов, strict или draft mode.
- **измеримый результат:** поиск продолжается, пока улучшает best-so-far;
  plateau останавливает; одна сложная сцена не останавливает остальные, не
  удаляет найденные assets, не сбрасывает проект и не блокирует reviewable draft.
- **запрещено:** случайный нерелевантный asset ради `completed`, misleading
  visual, `must_avoid` conflict, нарушение rights, ложный `publish_ready`.
- **required verification:** targeted + `full`. **rollback:** один commit.

### PLAN-10E — регистрация локальной медиатеки

- **status:** blocked (PLAN-10D + аудит) · **commit:** —
- **предусловие:** аудит paths, rights, provenance и dedup для локальных файлов.
- **цель:** `LocalLibraryStockProvider` участвует в автоматическом поиске.
- **измеримый результат:** провайдер отдаёт только rights-clean кандидатов без
  дублей.
- **required verification:** targeted + `full`. **rollback:** один commit.

### PLAN-11 — multi-topic product evidence

- **status:** blocked (PLAN-10E) · **commit:** —
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
- **M2:** бюджет платных вызовов — **TBD, owner approval before M2**. Числовые
  лимиты не согласованы и здесь не фиксируются.
- **M3:** `strict` выставляет `publish_ready=true` только после реальной
  визуальной проверки. Бюджет не утверждается до анализа M2.
- **required verification:** product gate. **rollback:** —

### PLAN-12 — классификация и архивирование документации

- **status:** blocked (PLAN-1) · **commit:** —
- **цель:** current navigation ведёт только к актуальным документам.
- **порядок:** перенести подтверждённые актуальные данные
  `ARCHITECTURE_BOUNDARY_MAP.md` в `SYSTEM_MAP.md`, затем удалить current-копию;
  `PROJECT_RESCUE_MASTER_PLAN.md` переместить в `docs/archive/handoff/` как
  historical snapshot; исторические планы, audits и implementation reports
  классифицировать пофайлово.
- **действия по классам:** keep, move, archive, backup_then_untrack, delete,
  defer. Целое семейство одним действием не архивируется и не удаляется.
- **запрещено:** untrack двенадцати reference jpg до переноса dataset;
  переписывать historical snapshot как current; оставлять битые ссылки.
- **required verification:** docs QA + `full`. **rollback:** один commit на
  семейство.

### PLAN-13 — ownership migration и retirement

- **status:** blocked (PLAN-1, PLAN-12) · **commit:** —
- **порядок:** caller migration → ownership transfer → wrapper retirement →
  package-root consolidation → `pipeline.py` retirement последним → runtime
  inventory → `copy → verify → switch`.
- **предусловие удаления любого старого entrypoint:** переведены или удалены
  tests, актуальные docs, console scripts, module entrypoints и подтверждённые
  внешние callers в том же изменении. Красные tests или лгущая документация
  после retirement недопустимы.
- **измеримый результат:** один physical package root и один канонический CLI.
- **required verification:** `full`. **rollback:** один commit на семейство.

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

## Completion and archive policy

Пока работа продолжается, файл имеет `status: active`.

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
