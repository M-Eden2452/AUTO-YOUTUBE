---
status: active
plan_revision: 2.1
created_at: 2026-07-30
updated_at: 2026-08-06
baseline_head: 38fed31
working_branch: governance-reset
owner_decisions_date: 2026-08-05
current_checkpoint: PLAN-STAB-6
next_exact_action: PLAN-STAB-6 (Claude permission hardening) implementation is completed 2026-08-06 and its five non-blocking review findings F1-F5 are repaired in a separate bounded repair commit; the next exact action is a short independent re-review of that repair commit only, and it does not close the step. The repair closes F1 (any deny rule that can reach the tracked .env.example is rejected positionally instead of by a two-spelling blacklist), F2 (the media-library record now states that the former leading-wildcard rule was deny while the six replacement entrypoint prefixes are ask, that coverage is limited to those six spellings, and that the real --apply barrier is the runtime confirm_apply contract in src/media_library.py), F3 (tracked governance under .claude/ requires Edit and Write confirmation via ./.claude/agents/** plus the existing exact ./.claude/settings.json, enumerated from git ls-files so a new tracked file cannot appear unguarded, with no broad ./.claude/** rule that would collide with the exact settings.local.json deny), F4 (a literal minimum contract pinned independently of PROTECTED_GOVERNANCE_PATHS, SECRET_ENV_NAMES, DESTRUCTIVE_GIT_DENY, DESTRUCTIVE_GIT_ASK and FORBIDDEN_BROAD_GRANTS, so narrowing settings.json and a constant together now fails) and F5 (only a rule in the tracked .gitignore proves an exclusion - .git/info/exclude, global core.excludesFile and user-level ignore are rejected - plus thirteen exact sensitive .env names added to the tracked .gitignore while .env.example stays tracked and unignored). CI for 3cedff10 is not confirmed green - run 31123722270 was cancelled twice before a windows-latest runner was assigned, with zero steps and zero logs, so neither required step ran; that is an infrastructure residual risk recorded by owner decision 2026-08-06 and CI success for 3cedff10 must not be claimed. Delivered in the implementation slice - the versioned .claude/settings.json is deny/ask-only with permissions.allow absent, the nine protected governance zones (AGENTS.md, CLAUDE.md, skills/**, tools/qa/**, .github/workflows/**, docs/current/PROJECT_EXECUTION_PLAN.md, docs/archive/**, docs/handoff/**, .claude/settings.json) require confirmation on Edit and Write while Read stays open, .claude/settings.local.json is denied to the agent for Read/Write/Edit and stays untracked and ignored, thirteen further secret .env.* names are covered for Read/Write/Edit at the root and recursively while the tracked .env.example keeps the PLAN-6D-1 zero-deny-match property, the untrustworthy leading-wildcard rule for media-library migrate --apply is replaced by six confirmed pipeline.py entrypoint prefixes, destructive Git is split into a deny set (reset --hard, clean, force push, filter-branch, reflog delete/expire, update-ref -d, gc --prune) and an ask set (checkout --, restore, rm, branch -D, worktree remove) per owner decision, and network plus package installation require confirmation. The contract is validated by validate_claude_permissions in the existing governance QA owner tools/qa/check_agent_docs.py, so the existing CI step covers it and no second QA framework or workflow was created; tests/test_claude_permission_contract.py owns the regressions. The seven dangerous local grants (git add *, git commit *, python -c, three python.exe -c variants, python -) were removed by the owner by hand before this slice and a read-only precheck confirmed none of them remain. Recorded residual limitations - exact matcher wildcard semantics and bucket precedence are not empirically proven here, Bash is not path-restricted so global Git options, shell aliases and an arbitrary interpreter remain out of contract, the enumerated .env.* coverage is deliberately incomplete, and the effective merged user/managed/local configuration lives outside the repository and is not claimed to be protected. Blocking gate item 6 remains open until the independent review of PLAN-STAB-6 lands or the owner formally accepts a documented residual risk; PLAN-STAB-7 and PLAN-STAB-8 stay closed and item 7 stays satisfied
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
  - skills/review-change
  - .claude/agents/review-change.md
---

# AI-YouTube Project Execution Plan

Временный orchestration-документ на период согласованной программы работ.
Он задаёт **порядок выполнения** и ничего больше. Он не заменяет `AGENTS.md`,
`CURRENT_STATE.md`, `PRODUCT_PLAN.md` и `CLEANUP_REGISTRY.md` и не является
архитектурной или продуктовой спецификацией.

После полного завершения программы этот файл удаляется из `docs/current/`
и сохраняется одним архивным snapshot — см. «Completion and archive policy».

## Current checkpoint

- **Текущий шаг:** **PLAN-STAB-6 — implementation completed 2026-08-06,
  independent review pending (Claude permission hardening).** Это единственный
  current checkpoint; любой другой шаг,
  названный текущим где-либо ещё, устарел. PLAN-STAB-7 (current-routing и
  reference integrity) и PLAN-STAB-8 (Git-aware documentation freshness)
  **closed 2026-08-06**: implementation commit `42fa741` (совместный слайс,
  trailer `Plan-Step: PLAN-STAB-7`), repair commit `8357402` исправил все
  четыре finding F1-F4 исходного independent review, не меняя ни один
  contract. Initial independent review verdict **ACCEPT WITH MINOR**, repair
  re-review verdict **ACCEPT WITH MINOR** (blocking findings: 0); GitHub
  Actions run `31101208366` (headSha `42fa741`) — offline suite зелёный
  (1693 tests, `OK (skipped=6)`, failures=0, errors=0); repair GitHub Actions
  run `31110155685` (headSha `8357402`) — offline suite зелёный (1702 tests,
  `OK (skipped=6)`, failures=0, errors=0); commits pushed. Пункт 7 blocking
  gate **satisfied**. PLAN-STAB-8 закрыт тем же координированным review и
  остаётся **non-blocking** для PLAN-9B-2; PLAN-ID и contracts
  PLAN-STAB-7/PLAN-STAB-8 остаются раздельными (детали — в их собственных
  разделах ниже). PLAN-STAB-9 (shared rights vocabulary owner) остаётся
  closed и non-blocking (commit `ed4604d`, verdict ACCEPT WITH MINOR).
  PLAN-STAB-5 (C50 rights-review preservation) completed 2026-08-06,
  independently reviewed, verdict **ACCEPT** (findings: нет), GitHub Actions
  run `31084873522` — offline suite зелёный (`Ran 1646 tests in 273.522s`,
  `OK (skipped=6)`, failures=0, errors=0); пункт 5 blocking gate
  **satisfied**. Пункты 6 и 8 blocking gate остаются открытыми; stabilization
  gate целиком не закрыт.

  **Утверждённый активный execution route (owner decision 2026-08-06):**
  PLAN-STAB-5 → PLAN-STAB-9 (closed) → PLAN-STAB-7 + PLAN-STAB-8 (closed) →
  **PLAN-STAB-6** или явное residual-risk decision → отдельный stabilization
  review → PLAN-9B-2. PLAN-STAB-6 (Claude permission hardening) implementation
  **завершена 2026-08-06** и ожидает independent review. Следующее точное
  действие — сам independent review этого implementation commit; он оценивает
  слайс, но шаг не закрывает. Обзор effective merged settings, который прежде
  стоял здесь, выполнен: семь опасных local grants (`git add *`,
  `git commit *`, `python -c`, три варианта `python.exe -c`, `python -`)
  владелец удалил вручную до слайса, read-only precheck подтвердил их
  отсутствие, а versioned `.claude/settings.json` (canonical owner A, tracked)
  переписан этим слайсом.
  `.claude/settings.local.json` (canonical owner B, local) остаётся gitignored
  manual owner action и не редактируется от имени агента.
- **PLAN-STAB-4:** completed 2026-08-06 (commit `0947e51`); independent review
  выполнен, verdict **ACCEPT WITH MINOR**; GitHub Actions run `31053545804`,
  job `offline-tests / unittest` — success, `Ran 1623 tests in 329.132s`,
  `OK (skipped=6)`, failures=0, errors=0; HEAD == `origin/governance-reset`,
  worktree clean на момент review. Два findings review — non-blocking residual
  evidence, не исправлены этим слайсом: (1)
  `tests/test_runtime_network_boundary.py:324-329` содержит тавтологический
  assertion (`assertTrue(callable(prepare_final))`) вместо полной проверки
  denial → readiness; (2) `wizard_presentation.py` показывает неполную
  информационную сводку сетевых действий и не использует
  `required_network_actions()` — это то же предсуществующее поведение, которое
  сам PLAN-STAB-4 уже зафиксировал как не входящее в scope. Commit pushed;
  пункт 4 blocking gate satisfied.
  Реализация 2026-08-06: canonical owner `src/runtime_network.py` объявляет
  runtime-сеть fail-closed по умолчанию — `ContextVar` со значением `DENY_ALL`,
  явное поимённое разрешение классов `provider_search`, `asset_download`,
  `preview_download`, `article_fetch`, `voice_preflight`, проверка
  `require_network` до первого socket/HTTP. Разрешение выдаётся один раз в
  `create_content` из поля `network` запроса, а запрос собирается общим
  request builder одинаково для CLI (`--allow-network`, повторяемый, без
  wildcard) и Wizard (явный шаг подтверждения). Наличие API-ключа, включённый
  по умолчанию keyless-провайдер, `--approve-paid-generation`, `--resume` и
  `--force-stage` разрешением **не являются**; `--dry-run` и `--prepare-only`
  остаются offline. Network approval и paid approval разделены: платное
  разрешение не открывает provider search, article ingestion, preview download
  и preflight.
- **PLAN-STAB-3:** completed 2026-08-05 (commit `9222519`); `tests/network_guard.py` получил
  `network_guard_scope()` context manager, восстанавливающий guard к состоянию
  до входа в scope даже при исключении, и 9 raw install/uninstall call sites
  в трёх owning test-модулях переведены на него — устранена утечка, при
  которой снятие guard одним тестом отключало baseline-защиту для остальных
  тестов процесса. `src/audio/tts/env.py::load_elevenlabs_env` больше не даёт
  локальному `.env` заменить test-owned fake `ELEVENLABS_API_KEY`, когда
  `tests/__init__.py` заранее установил test isolation lock и fake credential;
  production override=True semantics вне test isolation не менялись.
  Independent review выполнен, verdict ACCEPT WITH MINOR; commit pushed;
  пункт 3 blocking gate satisfied.
- **PLAN-STAB-2:** completed 2026-08-05 (commit `0eea5be`); обычный resume/явный `stage=` dispatch
  пропускает уже завершённый `final_render` при наличии обязательного
  final-артефакта; существующий `force_stage` по-прежнему пересобирает его;
  completed status без артефакта продолжает считаться незавершённым через уже
  действующий `NewsProjectStore.is_stage_completed`. Independent review
  выполнен, verdict ACCEPT; commit pushed; пункт 2 blocking gate satisfied.
- **PLAN-STAB-1:** completed 2026-08-05 (commit `f0b69db`); финальный мастер пишется во временный
  файл рядом с целью, проверяется каноническим `ffprobe_media_info` и только
  затем занимает свой путь через `os.replace`. Independent review выполнен,
  verdict ACCEPT WITH MINOR; commit pushed; пункт 1 blocking gate satisfied.
  Review PLAN-STAB-1/2/3 — owner-provided external review evidence, не
  отдельный Git commit.
- **CI repair (PLAN-STAB-16, часть 1):** commits `9f9b6f2`, `bcf6c2a`,
  `8ca755f`, `68acdb2` вернули `.github/workflows/offline-tests.yml` в
  зелёное состояние — GitHub Actions run `31039985187`,
  `offline-tests / unittest` — success, 1/1 checks, failures=0, errors=0;
  локальный полный offline suite на `68acdb2` — 1589 тестов, OK. Срочный
  bounded end-to-end repair по прямому owner decision; исходный scope
  расширен владельцем после новых подтверждённых CI failures — authorized,
  не самовольное расширение. Готовые видео, пользовательские проекты,
  downloaded assets и project outputs в Git не добавлялись; тест теперь
  генерирует synthetic temporary MP4 вместо personal-machine fixture.
  PLAN-STAB-16 остаётся **частично** выполнена: secret scan, dependency
  audit, lint baseline и type-check baseline — pending/non-blocking. Ни
  current checkpoint, ни PLAN-STAB-4 этим не менялись.
- **PLAN-9B-PRODUCER:** completed 2026-08-02; существующий visual-planning owner
  формирует evidence-derived provider-language `VisualBrief`, explicit author
  brief применяется последним, unknown intent остаётся fail-closed. Нового
  planner, query owner, schema/layout, public surface, network/model/paid path
  нет. Текущим checkpoint он больше не является.
- **PLAN-9B-2:** pending / not started и **deferred за post-audit stabilization
  gate** (OD-S-1). Это не отмена Visual Planning work: acceptance criteria,
  expansion ladder, hardcode migration и retirement scope не начинались и не
  менялись. Условия возврата — раздел «POST-AUDIT STABILIZATION PROGRAM».
- **Выполнено:** PLAN-0 — создан этот план; ветка `governance-reset`.
  STEP 0 — архитектурная ревизия перенесена в этот файл и в
  `CLEANUP_REGISTRY.md`. **PLAN-REV-2.1** — ревизия 2.1 канонизирована
  docs-only слайсом; production-код, tests, схемы и public CLI не менялись.
  **PLAN-1D-routing** — routing исправлен в `AGENTS.md`,
  `docs/current/START_HERE.md` и `docs/current/CURRENT_STATE.md`: все три
  current-документа называют текущим execution plan этот файл и больше не
  называют `9B-C01` текущим checkpoint. Исторический
  `docs/handoff/PROJECT_RESCUE_MASTER_PLAN.md` сохранён и не редактировался.
  Findings C51 (`PRODUCT_EVIDENCE_GATE.md`) и C52 (root `skills/` discovery)
  записаны в `CLEANUP_REGISTRY.md` без перемещения файлов и без создания
  второго набора skills. **PLAN-2** — исправлена изоляция fixtures в
  `tests/test_voice_profile_resolution.py`: изменён только этот test-модуль,
  production-код не менялся. **PLAN-3** — fixtures в
  `tests/test_autonomous_completion_pipeline.py` создают реальные минимальные
  outputs для стадий, объявленных completed; изменён только этот test-модуль,
  production-код не менялся. **PLAN-4** — полный offline suite завершился
  зелёным на проверенном исходном HEAD
  `84bdd8b4f64c7adaf7582bdb39b15b18163253fb`; production-код и tests в этом
  verification-only слайсе не менялись. **PLAN-9B-0** — новый in-process
  offline-модуль `tests/test_input_query_truth_characterization.py` через
  canonical `create_content` path зафиксировал pre-fix input/query behavior,
  production-код не менялся. **PLAN-9B-1** — canonical owner
  `src/assets/query_adapter.py` теперь валидирует язык каждого candidate query
  отдельно, стабильно normalizes/deduplicates explicit/brief/intent evidence,
  читает canonical structured `visual_intents` раньше плоского compatibility
  fallback и использует Unicode token boundaries плюс ограниченную безопасную
  морфологию seed-лексикона. Ложные `ice researchers` и одиночный misleading
  `station` устранены; English alternatives рядом с Russian primary и prepared
  VisualBrief доходят до fake providers с существующим provenance. Unknown raw
  intent остаётся `query_translation_required`; adapter переводчиком не стал.
  Первоначальный raw-topic T1 был несовместим с adapter-only scope и по owner
  decision заменён на T1A (prepared provider-ready evidence) + T1B (unsupported
  raw intent fail-closed). Arbitrary raw-topic provider-language generation
  остаётся открытой product capability, а не скрывается generic fallback.
- **PLAN-9B-5a** — canonical `create` получил owner-approved public flags
  `--source-text` / `--source-text-file`; прежние `--pasted-script` /
  `--script-file` сохранены aliases того же parser destination. Общий
  `request_builder` нормализует их в существующие поля `pasted_script` /
  `script_path` и существующие modes `pasted_script` / `script_file`,
  валидирует единственность authoritative input и compatible `--input-mode`.
  Story Card `--text` / `--comment`, request model, script engine, persisted
  schema, wrapper `apps/news_to_short` и `--assets` не менялись.
- **PLAN-9B-4** — factual `strict` связывает существующий
  `allow_legacy_fallback` со strict completion policy и возвращает
  `insufficient_source_material` с вариантами article URL / source text /
  draft / template. Существующие `script_provider`, `fallback_reason`,
  `script_metadata` и `ScriptValidationResult` используются validation и
  quality defense; `content_origin`, новые persisted fields и schema не
  создавались. Явный `legacy_template` сохранён для template/demo/test/draft и
  старых проектов; CLI diagnostics и оба application dry-run/prepare пути
  возвращают классифицированный отказ без traceback.
- **PLAN-6D-1** — permission baseline разделён на точные permanent deny и
  поддерживаемые `ask` rules. `.env` защищён для Read/Write/Edit; broad
  `.env.*`, `*credential*` и `*secret*` patterns, блокировавшие versioned
  examples/source, удалены. Bare/flagged `git clean`, `reset --hard` и force
  push покрыты deny; обычные push/remote-add/stash/amend, прямые WebFetch/
  WebSearch и перечисленные recursive cleanup primitives требуют approval.
  Scope-controlled и mixed directories broad path rules не получили.
- **PLAN-6D-2** — добавлен локальный read-only checker
  `tools/qa/check_task_scope.py`. Конкретная задача передаёт повторяемые
  `--allow` exact paths и/или явные `--allow-dir` directory scopes; checker
  сравнивает их с `git --no-optional-locks status --porcelain=v1 -z
  --untracked-files=all --renames`, учитывает обе колонки staged/unstaged,
  untracked, add/delete и обе стороны rename. Словарь результата — ровно
  `OK`, `STOP_REQUIRED`, `INVALID_INPUT`; exit codes — 0, 1, 2 соответственно.
  Модуль не читает содержимое изменённых файлов, не меняет index/worktree и не
  хранит глобальный PLAN allowlist.
- **PLAN-6D-3** — тонкий `CLAUDE.md` теперь явно сообщает, что repository
  skills находятся в корневом `skills/`, не считаются автоматически
  загруженными только из-за наличия в репозитории и перед специализированной
  задачей требуют ручного открытия релевантного
  `skills/<skill-name>/SKILL.md`. Skill применяется вместе с `AGENTS.md`,
  актуальной документацией, фактическими кодом и тестами; состояние
  репозитория имеет приоритет над предположениями skill. Содержимое skills не
  копировалось, `.claude/skills/` не создавался, утверждения о Codex discovery
  не добавлялись. PLAN-6D завершён полностью.
- **Зелёные проверки:** `tools.qa.check_agent_docs`;
  `tests.test_voice_profile_resolution` — targeted-модуль, exit code 0 в двух
  последовательных прогонах (2026-08-01);
  `tests.test_autonomous_completion_pipeline` — targeted-модуль, exit code 0
  в двух последовательных прогонах (2026-08-01); полный offline suite — 1441
  тест, 231.839 секунды, exit code 0 без failures, errors и skips на проверенном
  исходном HEAD `84bdd8b4f64c7adaf7582bdb39b15b18163253fb` (2026-08-01). Число тестов и
  длительность — измерение, не норматив;
  `tests.test_input_query_truth_characterization` — 2 теста, два
  последовательных прогона с exit code 0 (74.191 и 73.016 секунды), active
  network guard не зафиксировал попыток сети; targeted radius из четырёх
  существующих модулей — 118 тестов, 26.004 секунды, exit code 0 (2026-08-01);
  PLAN-9B-1: `tests.test_input_query_truth_characterization` — 3 теста, два
  окончательных последовательных прогона с exit code 0 (74.852 и 75.004
  секунды); прямой query radius — 75 тестов за 1.574 секунды; caller radius
  через script pipeline, asset manager, canonical content service и provider
  integration — 82 теста за 33.120 секунды, exit code 0. Числа и длительности
  являются измерениями, не нормативами. Network guard оставался чистым; сеть,
  model API, provider HTTP/download, Vision, TTS, paid calls и render не
  выполнялись;
  PLAN-9B-5a: новый regression-модуль — 15 тестов в составе окончательного
  targeted radius; parser/request/service/use-case/Wizard radius — 193 теста
  за 43.183 секунды, exit code 0; `create --help`, inline source-text dry-run и
  file source-text dry-run — три smoke-команды, каждая exit code 0; полный
  offline suite — 1465 тестов за 309.632 секунды, exit code 0, failures/errors
  нет (2026-08-02). Числа и длительности — измерения, не нормативы. Сеть,
  provider/model API, download, Vision, TTS, paid calls и реальный render не
  выполнялись.
  PLAN-9B-4: targeted owner/caller radius — 168 тестов за 135.307 секунды,
  exit code 0; полный offline suite — 1523 теста за 356.527 секунды, exit code
  0, `OK` (2026-08-02). T6/T7/T8, canonical Content Creator, diagnostics,
  persisted quality defense, explicit legacy compatibility, source-text и
  resume/force-stage fixtures покрыты. Числа и длительности — измерения, не
  нормативы. Сеть, provider/model API, download, Vision, TTS и paid calls не
  выполнялись; render-проверки full suite использовали только синтетические
  fixtures во временных каталогах.
  PLAN-6D-1: JSON и локальный Claude Code 2.1.219 parser — exit code 0;
  полный tracked-path collision probe — 0 совпадений; `.env` покрыт
  Read/Write/Edit, `.env.example` и `src/localization/secrets.py` доступны;
  `tools.qa.check_agent_docs` и `tests.test_stage2_agent_onboarding` — exit
  code 0; `git diff --check` — без замечаний (2026-08-02). Сеть, providers,
  download, Vision, TTS, paid API и render не выполнялись.
  PLAN-6D-2: `tests.test_check_task_scope` — 26 тестов, exit code 0;
  `check_task_scope --help`, docs QA, onboarding tests и `compileall tools\qa`
  — exit code 0. Smoke текущего разрешённого diff вернул `OK/0`; smoke во
  временном Git repository с unexpected untracked path вернул
  `STOP_REQUIRED/1`. `git diff --check` — без замечаний. Production code,
  hooks, agents, skills и runtime/user data не менялись; сеть и платные
  действия не выполнялись (2026-08-02). Число тестов и длительность —
  измерения, не нормативы.
  PLAN-6D-3: `check_task_scope` с четырьмя разрешёнными exact paths вернул
  `OK/0`; docs QA, `tests.test_stage2_agent_onboarding` и `git diff --check`
  завершились с exit code 0. Фактическая структура содержит шесть root skills
  и не содержит `.claude/skills/`; `CLAUDE.md` остался тонким adapter,
  содержимое skills не копировалось и не менялось. Сеть, providers, download,
  Vision, TTS, paid API и render не выполнялись (2026-08-02).
- **Почему checkpoint сместился с PLAN-1A на PLAN-1D, затем на PLAN-2,
  PLAN-3, PLAN-4, PLAN-9B-0, PLAN-9B-1, PLAN-9B-5a, PLAN-9B-4, PLAN-9B-2,
  PLAN-6D-2, PLAN-6D-3, PLAN-6E, PLAN-L0, PLAN-9B-PRODUCER и PLAN-STAB-1.**
  Смещение на 1D было
  **не** признаком
  выполненной работы: ревизия 2 разделила монолитный PLAN-1 на три capability
  gates (1A, 1B, 1C′) и выделила routing-фикс 1D как первый самостоятельный
  шаг. Ни один под-slice PLAN-1A/1B/1C′ не выполнен. Переход на PLAN-2 —
  следствие фактически выполненного docs-only слайса PLAN-1D; переход на
  PLAN-3 — следствие фактически выполненного test-only слайса PLAN-2; переход
  на PLAN-4 — следствие фактически выполненного test-only слайса PLAN-3;
  переход на PLAN-9B-0 — следствие зелёного полного offline baseline PLAN-4.
  `baseline_head` обновлён на фактически проверенный исходный HEAD
  `84bdd8b4f64c7adaf7582bdb39b15b18163253fb`; будущий plan-only commit этим
  baseline не является. Переход на PLAN-9B-1 — следствие зелёной
  characterization PLAN-9B-0; full suite в test-only слайсе не запускался,
  поэтому `baseline_head` не менялся. Переход на PLAN-9B-5a — следствие
  выполненного локального PLAN-9B-1; full suite не запускался, потому что public
  signatures, schema/layout и shared architecture boundary не менялись.
  `baseline_head` остаётся прежним.
- Переход на PLAN-L0 — следствие завершённых PLAN-9B-5a, PLAN-9B-4, PLAN-6D,
  PLAN-6E и принятого owner decision OD-P-1. Утверждённый порядок:
  `PLAN-L0 → PLAN-9B-PRODUCER → PLAN-9B-2`.
  `baseline_head` не переписывается на незакоммиченный hash; Git log остаётся
  авторитетом commit evidence.
- Переход на PLAN-9B-PRODUCER — следствие фактически выполненного docs-only
  слайса PLAN-L0: Knowledge Salvage Gate закрыт до destructive retirement, как
  требуют OD-1, OD-7 и OD-10. Full suite не запускался, потому что слайс
  docs-only и не менял production contract, поэтому `baseline_head` не менялся.
- Переход на PLAN-STAB-1 — следствие owner decision 2026-08-05 по read-only
  AI-practices audit от clean HEAD `e4cad2a`: подтверждённые safety findings
  получают исполняемых owners раньше следующего product slice. Это **не**
  оценка качества PLAN-9B-PRODUCER, который завершён и принят, и **не** отмена
  PLAN-9B-2. Смена checkpoint не является разрешением начать PLAN-STAB-1: он
  остаётся pending / not started до отдельного owner-issued implementation
  prompt. `baseline_head` этим docs-only слайсом не менялся.
- **`baseline_head` обновлён на 68acdb2 после PLAN-STAB-1/2/3 и CI repair.**
  PLAN-STAB-1 (`f0b69db`), PLAN-STAB-2 (`0eea5be`) и PLAN-STAB-3 (`9222519`)
  каждый запускал полный offline suite на своём HEAD (1571, затем 1577, затем
  1589 тестов, exit code 0) и получил independent review — verdict ACCEPT WITH
  MINOR, ACCEPT, ACCEPT WITH MINOR соответственно; все три commit pushed.
  CI repair (`9f9b6f2`, `bcf6c2a`, `8ca755f`, `68acdb2`, trailer
  `Plan-Step: PLAN-STAB-16`) — срочный bounded end-to-end repair по прямому
  owner decision после новых подтверждённых CI failures в GitHub Actions;
  scope расширен владельцем, это не самовольное расширение. Result: GitHub
  Actions run `31039985187`, `offline-tests / unittest` — success, 1/1 checks,
  failures=0, errors=0; локальный полный offline suite на `68acdb2` — 1589
  тестов, OK. Готовые видео, пользовательские проекты, downloaded assets и
  project outputs в Git не добавлялись; тест, ранее ссылавшийся на
  personal-machine fixture, теперь генерирует synthetic temporary MP4.
  `baseline_head` обновлён на фактически проверенный `68acdb2` — последний
  commit с зелёным полным offline suite и зелёным GitHub Actions run.
  PLAN-STAB-16 этим **частично** выполнена: первая часть (reproducible green
  offline CI baseline) завершена; secret scan, dependency audit, lint baseline,
  type-check baseline и остальные подпункты остаются pending/non-blocking для
  PLAN-9B-2. Ни один из четырёх commits не меняет current checkpoint: он
  остаётся PLAN-STAB-4 pending / not started, и PLAN-STAB-4 этим не начат.
- Переход на PLAN-6D-2 — owner-approved prerequisite rerouting и следствие
  завершённого PLAN-6D-1. Он не начинает PLAN-9B-2 и не меняет его acceptance
  criteria.
- Переход на PLAN-6D-3 — следствие зелёного локального read-only scope
  checker PLAN-6D-2. Он не начинает PLAN-9B-2/PLAN-6E и не означает завершение
  PLAN-6D.
- PLAN-6E выполнен после завершённого PLAN-6D-3 и полного закрытия PLAN-6D.
  Его закрытие не начинает PLAN-L0, PLAN-9B-PRODUCER или PLAN-9B-2.
- **Текущие зависимости и блокеры (модель ревизии 2.1 — risk-based, не
  линейная цепочка):**
  - **PLAN-9B-1** — completed 2026-08-01; prerequisite-цепочка
    `PLAN-1D-routing → PLAN-2 → PLAN-3 → PLAN-4 → PLAN-9B-0` завершена
    2026-08-01;
  - **PLAN-9B-5a** — completed 2026-08-02; зависит от завершённого PLAN-9B-1;
  - **PLAN-9B-4** — completed 2026-08-02; зависит от завершённого PLAN-9B-5a;
  - **PLAN-L0** — completed 2026-08-02; salvage записан в
    `CLEANUP_REGISTRY.md`, retirement не выполнялся;
  - **PLAN-9B-PRODUCER** — completed 2026-08-02; зависел от завершённых
    PLAN-9B-1 и PLAN-L0, обе зависимости были закрыты до начала;
  - **PLAN-STAB-1** — completed 2026-08-05 (commit `f0b69db`); independent
    review выполнен, verdict ACCEPT WITH MINOR; commit pushed;
  - **PLAN-STAB-2** — completed 2026-08-05 (commit `0eea5be`); зависел от
    завершённого PLAN-STAB-1; independent review выполнен, verdict ACCEPT;
    commit pushed;
  - **PLAN-STAB-3** — completed 2026-08-05 (commit `9222519`); independent
    review выполнен, verdict ACCEPT WITH MINOR; commit pushed. Review
    PLAN-STAB-1/2/3 — owner-provided external review evidence, не отдельный
    Git commit;
  - **PLAN-STAB-4** — completed 2026-08-06 (commit `0947e51`); independent
    review выполнен, verdict ACCEPT WITH MINOR (GitHub Actions run
    `31053545804`, offline suite 1623 tests OK); commit pushed; пункт 4
    blocking gate satisfied; два findings review зафиксированы как
    non-blocking residual evidence и не исправлены;
  - **PLAN-STAB-5** — completed 2026-08-06 (единственный commit слайса,
    trailer `Plan-Step: PLAN-STAB-5`); independent review выполнен, verdict
    **ACCEPT** (findings: нет), GitHub Actions run `31084873522` (1646 tests
    OK); commit pushed; пункт 5 blocking gate satisfied;
  - **PLAN-STAB-9** — completed 2026-08-06 (единственный commit слайса,
    trailer `Plan-Step: PLAN-STAB-9`, `ed4604d`); independent review выполнен,
    verdict ACCEPT WITH MINOR (non-blocking wording finding, исправлен); GitHub
    Actions reviewed headSha `ed4604d` зелёный; non-blocking follow-up для
    PLAN-9B-2; не текущий checkpoint;
  - **PLAN-STAB-7** — completed 2026-08-06 (implementation commit `42fa741`,
    repair commit `8357402`); independent review verdict ACCEPT WITH MINOR,
    repair re-review verdict ACCEPT WITH MINOR (blocking findings: 0); CI run
    `31101208366` (headSha `42fa741`, 1693 tests OK) и repair CI run
    `31110155685` (headSha `8357402`, 1702 tests OK) оба зелёные; commits
    pushed; пункт 7 blocking gate satisfied; не текущий checkpoint;
  - **PLAN-STAB-8** — closed 2026-08-06 тем же координированным review, что и
    PLAN-STAB-7 (implementation commit `42fa741`, repair commit `8357402`);
    non-blocking follow-up для PLAN-9B-2; PLAN-ID и contract остаются
    отдельными от PLAN-STAB-7;
  - **PLAN-STAB-6** — **текущий checkpoint**; implementation completed
    2026-08-06, independent review pending; следующее действие — сам
    independent review implementation commit, шаг им не закрывается;
  - **PLAN-STAB-10…PLAN-STAB-15, PLAN-STAB-17** — pending/not started; состав,
    порядок и blocking-статус каждого — раздел «POST-AUDIT STABILIZATION
    PROGRAM»;
  - **PLAN-STAB-16** — pending/not started как полный слайс, но **частично
    выполнена**: CI repair (`9f9b6f2`, `bcf6c2a`, `8ca755f`, `68acdb2`) закрыл
    первую часть success criteria (green offline suite в GitHub Actions —
    run `31039985187`, 1/1 checks, failures=0, errors=0); secret scan,
    dependency audit, lint baseline и type-check baseline остаются
    pending/non-blocking;
  - **PLAN-9B-2** — pending/not started; PLAN-L0/PLAN-9B-4/PLAN-9B-PRODUCER/
    PLAN-6D/PLAN-6E завершены, но слайс **deferred** за stabilization gate и
    требует отдельного owner-issued implementation prompt;
  - **PLAN-6D-1** — completed 2026-08-02;
  - **PLAN-6D-2** — completed 2026-08-02;
  - **PLAN-6D-3** — completed 2026-08-02;
  - **PLAN-6D** — completed 2026-08-02; evidence commits: `397d338`
    (PLAN-6D-1), `10dd555` (PLAN-6D-2) и commit с trailer
    `Plan-Step: PLAN-6D-3`;
  - **PLAN-6E** — completed 2026-08-02; canonical review policy, два тонких
    adapter и controlled read-only acceptance закрывают reviewer gate для
    destructive/high-risk boundaries;
  - **PLAN-9A** — блокируется `PLAN-9B-2` + `PLAN-1C′`, дополнительно требует
    `PLAN-6E`;
  - **PLAN-9C** — блокируется `PLAN-1C′` + `PLAN-6E`;
  - **PLAN-5, PLAN-6A, PLAN-6B, PLAN-6C, PLAN-7, PLAN-8, PLAN-1A, PLAN-1B,
    PLAN-1C′, PLAN-12\*, PLAN-13\*, PLAN-14\* и PLAN-L1…PLAN-L4** — параллельны и
    **не блокируют первый product fix**;
  - PLAN-11 M2 — до подтверждения бюджета.
- **Следующее точное действие:** PLAN-STAB-7 и PLAN-STAB-8 closed 2026-08-06
  (implementation commit `42fa741`, repair commit `8357402`; independent
  review verdict ACCEPT WITH MINOR, repair re-review verdict ACCEPT WITH
  MINOR, blocking findings: 0; пункт 7 blocking gate satisfied). Следующий
  шаг — independent review implementation commit PLAN-STAB-6 (Claude permission
  hardening); implementation PLAN-STAB-6 завершена 2026-08-06, шаг остаётся
  открытым. PLAN-STAB-9 остаётся closed и non-blocking follow-up для PLAN-9B-2.
- **После PLAN-9B-PRODUCER:** не начинать PLAN-9B-2 до закрытого stabilization
  gate и отдельного implementation prompt; не начинать ни один PLAN-STAB-слайс
  без собственного implementation prompt. PLAN-L1…PLAN-L4 закрытием PLAN-L0 не
  разрешены: каждый остаётся отдельной retirement-веткой со своими gates.
- **Что нельзя повторять:**
  - закрывать шаг без зелёной обязательной проверки;
  - записывать число тестов, длительность прогона или accuracy как норму;
  - менять production-код без закрытого capability gate изменяемой области;
  - создавать третий плановый документ;
  - архивировать `PROJECT_RESCUE_MASTER_PLAN.md` или
    `ARCHITECTURE_BOUNDARY_MAP.md` до PLAN-12;
  - снимать с Git `docs/implementation` целым семейством;
  - заявлять о защите, которая существует только в документах;
  - выполнять destructive retirement knowledge-bearing family до Knowledge
    Salvage Gate (PLAN-L0);
  - требовать KSG для disposable runtime/media: их цепочка — PLAN-14D → 14E;
  - считать «нет caller» доказательством отсутствия ценности;
  - **создавать PLAN-P0 / «Content & Query Reachability Gate»**: evidence уже
    получено двумя deep-dive, повторный диагностический этап запрещён (OD-11);
  - **возвращать опровергнутые механизмы** — см. «Ревизия 2.1: опровергнутые
    формулировки».

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
5. `PRODUCT_PLAN.md` — продуктовое направление, committed capabilities и склад
   идей. **Создан слайсом PRODUCT-PLAN-1**; PLAN-8 его расширяет и проверяет, а
   не создаёт заново. Execution state (checkpoint, next action, порядок,
   prerequisites, статусы) он не хранит — источником остаётся этот файл.
6. `CLEANUP_REGISTRY.md` — переходные пути, owners и exit conditions.
7. `docs/adr/` — зафиксированные долговечные решения.
8. Historical plans и audits — только как context.

**Отношение к `docs/handoff/PROJECT_RESCUE_MASTER_PLAN.md`.** Master plan
остаётся **историческим исходным документом** и источником данных для PLAN-1.
Его разделы «Что делать первым» и «Текущий handoff» отражают состояние на
2026-07-29 и **не являются** текущим порядком работ: порядок задаёт этот файл.
Master plan не обновляется как current plan и не архивируется до PLAN-12C.
Противоречие между двумя документами разрешается в пользу этого файла
только по вопросу порядка выполнения; по фактам архитектуры приоритет у кода.

Если код или tests противоречат этому плану, агент обязан остановиться,
проверить evidence и обновить план после решения владельца.

**Маршрутизация агентов — исправлена PLAN-1D (2026-08-01).** После ревизии 2
`AGENTS.md` и `START_HERE.md` направляли задачу в master plan, а
`CURRENT_STATE.md` называл текущим checkpoint `9B-C01`, которого больше нет.
PLAN-1D добавил в шаг 4 `AGENTS.md` и в `START_HERE.md` ссылку на этот файл как
на активный execution plan и снял stale checkpoint из всех трёх current-документов.
Master plan во всех трёх упоминается только как исторический контекст.

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
    `python -m apps.*`) не являются постоянным пользовательским контрактом.
    **Изменено ревизией 2:** формулировка «сначала PLAN-1» отменена. Каждый
    entrypoint удаляется после **своего** capability gate; для legacy-семейства
    это PLAN-L1, а не глобальный inventory.
11. Владелец подтвердил отсутствие личных `.bat`/`.cmd`/`.ps1`, ярлыков,
    Windows Tasks и IDE Run Configurations, которые нужно сохранять ради старых
    команд. Поиск по компьютеру вне репозитория запрещён.
12. R1–R12 становятся новой governance model (внедрение — PLAN-6). Отдельный
    ADR про переход на новые правила не создаётся.
13. Платные и сетевые операции требуют отдельного разрешения на конкретное
    действие. Для M1: 0 USD и ноль новых платных Vision-вызовов. Бюджет M2 —
    `TBD`, подтверждается отдельно перед первым реальным платным запуском.

## Owner decisions ревизии 2 (2026-07-31)

Ревизия 2 пересмотрела план под явную позицию владельца: существующая
зависимость, существующий owner и существующая архитектура **не являются
доказательством правильности**; тестовое runtime-медиа ценности не имеет;
правила ограничивают исполнение, но не мышление; программа не должна
превратиться в бесконечное строительство governance.

| # | Решение |
|---|---|
| **OD-1** | `channels/{psychology,quotes,survival,size_comparison}` и `content/` не сохраняются как активные workflows. Ретайр вместе с legacy допускается **только после Knowledge Salvage Gate** |
| **OD-2** | `apps/news_to_short` как отдельный CLI не сохраняется. Если его флаги полностью покрыты каноническим CLI — удалить; уникальную возможность сначала перенести в `content_creator`, затем удалить |
| **OD-3** | `assets/voice_samples` — disposable test/runtime media, в source repo не хранится. Если конкретный активный voice profile действительно требует sample — перенести минимально необходимый во внешний Workspace с provenance, иначе удалить |
| **OD-4** | Бюджет M2 остаётся `TBD` и ничего не блокирует |
| **OD-5** | Вся поддерживаемая human/agent-проза со временем становится преимущественно русской, **включая body существующих ADR**. Инкрементально, без одного mass-diff; не блокирует product work |
| **OD-6** | Locked decisions 8 и 9 больше не запрещают пересмотр `config`/`channels`/`assets`/`resources`. Пересмотр — только после классификации, не ради эстетики |
| **OD-7** | **MOSS-TTS не нужен продукту.** Не реинтегрировать как активный TTS provider. KSG → caller audit → удалить `MOSS_TTS_Nano/` и `src/tts_providers/`. Не сохранять 56k файлов «на всякий случай»; vendor repo в `Workspace/models` не переносить |
| **OD-8** | Live-eval — evaluation resource. **`docs/` — неправильный target owner.** Fixture/evidence сохраняется, caller позже переводится на утверждённого owner. `resources/evaluation/` — **только candidate path**; физический target `DEFER` до PLAN-13 |
| **OD-9** | Top-level `resources/` — `DEFER` до PLAN-13, заранее **не создавать**. Сначала классифицировать `channels` · `schemas` · reusable templates · evaluation resources · versioned assets/config, затем решить, уменьшает ли `resources/` число owners |
| **OD-10** | `size_comparison_engine`: L0 сохраняет reusable algorithm, domain knowledge, visual logic, edge cases и полезные тесты. **Capability внутри L3 не мигрируется.** Если формат понадобится — отдельный будущий product slice на новом canonical core |

## Owner decisions ревизии 2.1 (2026-07-31)

Ревизия 2.1 — **перестановка и переадресация**, а не переписывание. Ни один
существующий PLAN-ID не удалён. Источники: `docs/audits/`
`CRITICAL_INPUT_SEARCH_DEEP_DIVE_2026-07-31.md`,
`PROJECT_EXECUTION_PLAN_REVISION_2_1_PROPOSAL_2026-07-31.md` и
`SECONDARY_ARCHITECTURE_FINDINGS_DEEP_DIVE_2026-07-31.md`. **При конфликте
Secondary Deep Dive исправляет Proposal 2.1**; исправленные формулировки
записаны ниже и в разделе «Ревизия 2.1: опровергнутые формулировки».

| # | Решение |
|---|---|
| **OD-11** | **PLAN-P0 (Content & Query Reachability Gate) не создаётся.** Evidence уже получено двумя deep-dive offline, без сети и денег. Тесты T1–T11 из `CRITICAL_INPUT_SEARCH_DEEP_DIVE` становятся regression/product-тестами **внутри соответствующих PLAN-9B слайсов**, а не отдельным диагностическим этапом |
| **OD-12** | CRITICAL-1 — текущий главный product defect в **исправленной** формулировке: не «ноль запросов», а «ложные / чрезмерно общие / пропущенные запросы, и единственный канал доставки provider-ready английского запроса — hardcode на одну тему» |
| **OD-13** | **Не создавать** `TranslatorService`, `SearchEngine`, `QueryOrchestrator` и второй query pipeline. Переиспользуются `VisualBrief`, `SceneVisualPlan`/`VisualSearchIntent`, `build_scene_queries`/`build_slot_queries`, `ProviderQuery`, provider contracts |
| **OD-14** | `src/assets/query_adapter.py` — фактическая canonical boundary, через которую remote-запросы доходят до провайдеров. Allowed zone PLAN-9B исправлена на неё |
| **OD-15** | **PLAN-9B выполняется до PLAN-9A.** Best-so-far persistence бессмысленна до появления provider-ready кандидатов. PLAN-9A не удаляется и состав не меняет |
| **OD-16** | Метод provider-language adaptation **не фиксируется заранее**: deterministic normalization/lexicon, prepared `VisualBrief`, model-assisted adaptation или комбинация. Выбор — по semantic correctness, fail-closed, testability, cost, network/paid boundary и reuse существующих owners. **Model/network вариант требует отдельного owner approval** |
| **OD-17** | CRITICAL-2 исправляется сейчас, **без AI research**. Idea generation, web/AI research, AI script writing, autonomous creative direction — **DEFER**: без PLAN, package, interface и placeholder |
| **OD-18** | Для factual strict workflow `topic` = **intent, не source material**. Silent fallback `topic → insufficient material → generic template → factual production success` запрещён. `LegacyTemplateScriptProvider` **не удаляется**: допустим только в явно выбранном `template`/`demo`/`test`/`draft`. `content_origin` **не создаётся** |
| **OD-19** | Capability `apps/news_to_short --text/--text-file` **мигрирует** в канонический `python -m ai_youtube` + content_creation request path. **Разделено (D-1):** миграция — PLAN-9B-5a (additive), retirement — PLAN-9B-5b. **Исправлено 2026-08-01:** это не единственная возможность wrapper'а — перед retirement обязателен полный **capability parity check** (см. PLAN-9B-5b), минимум `--text`/`--text-file` **и** `--assets` |
| **OD-20** | CRITICAL-3 («в content path мало AI») **не является** current defect и отдельного этапа не получает. Future-proofing rule: downstream pipeline не должен предполагать, что script создан внутри AI-YouTube; prepared external content — first-class input |
| **OD-21** | CRITICAL-4 (double orchestration) сохраняется как architecture debt, **не** prerequisite CRITICAL-1/2. **Исправлено Secondary Deep Dive:** severity **MEDIUM**, не HIGH; finding разделяется на contract defect и возможную позднюю конвергенцию (D-3) |
| **OD-22** | Порядок semantic/Vision: provider-ready query → candidates → semantic/Vision → rank/select. PLAN-9C сохраняется, новый semantic stack не создаётся |
| **OD-23** | Anime Factory — **не** disposable legacy: это source implementation будущего `video_repurposer`. Порядок: Content Creator stable → UI Content Creator → deep audit Anime Factory → KEEP/MIGRATE/REWRITE/SHARE/DELETE → Video Repurposer → его UI. Runtime внутри source repo остаётся дефектом, owner — PLAN-14 |
| **OD-24** | `search_session.json` как отдельный persisted owner **не утверждается**. Сначала проверить `job.json`, asset manifest, project state, completion/resume state. Если существующего owner можно расширить — новый persisted файл запрещён |
| **OD-25** | **Multi-topic regression начинается раньше PLAN-11** и выполняется после каждого существенного product slice, где это релевантно: минимум по одной репрезентативной теме из разных классов (animals/wildlife · energy/technology · geography/infrastructure). PLAN-11 остаётся финальным product evidence gate, но **не первой** multi-topic проверкой |
| **OD-26** | Governance не задерживает дешёвое product-исправление без конкретной защищаемой boundary, **но** safety/reviewer/persisted/paid protections обязаны быть готовы **до своей risk boundary**. Каждый оставшийся blocker имеет однострочное обоснование |
| **D-1** | **ДА** — 9B-5 разделяется на **9B-5a** (additive source-text canonical input; public CLI surface + owner approval; не destructive) и **9B-5b** (retirement `apps/news_to_short`; требует PLAN-6D + PLAN-6E + reversible retirement) |
| **D-2** | **ДА** — PLAN-10B **не является** owner provider-registry convergence; сама гипотеза «пять расходящихся реестров надо свести» **опровергнута**. PLAN-10B возвращается к своей реальной ответственности: pagination / provider exhaustion / provider contract behavior |
| **D-3** | **ДА** — double orchestration finding разделяется на точный idempotency contract defect (owner: ADR 0006 / `src/news/pipeline.py`) и возможную позднюю orchestration convergence (owner: PLAN-13B, только если после исправления contract остаётся архитектурная необходимость). Severity **MEDIUM** |
| **E-13** | CRITICAL-2 остаётся **bounded sub-slices существующего PLAN-9B**. Новый top-level PLAN-ID не создаётся |
| **1C′/6E** | Прямая зависимость `PLAN-1C′ → PLAN-6E` **снята**. Одновременно **явно установлено**: `PLAN-9A` требует `PLAN-6E` (persisted-state boundary), `PLAN-9C` требует `PLAN-6E` (semantic decision boundary). Транзитивная зависимость через PLAN-9B-2 доказательством не считается |
| **export** | PLAN-11 — **evidence gate**, обязанный ловить ложные product capabilities. Implementation owner — будущий bounded `production_catalog` slice. Нового PLAN-ID не создаётся |
| **ffmpeg** | PLAN-8 — **roadmap owner** product-quality item. Implementation owner — будущий bounded renderer slice с characterization первым. Нового PLAN-ID не создаётся |
| **subprocess** | Архитектурное решение по subprocess network kill-switch **сейчас не принимается**: механизм и owner остаются implementation-time evidence/owner decision. **PLAN-6B остаётся report/measurement owner в своей текущей границе** |

### Ревизия 2.1: опровергнутые формулировки

Эти утверждения **опровергнуты** контролируемыми offline-пробами Secondary Deep
Dive. Возвращать их в план, registry, задания и commit-сообщения запрещено.

| Опровергнутая формулировка | Что верно на самом деле |
|---|---|
| «semantic-слой по построению не может влиять на selection»; «`_selection_fingerprint` делает неизменность отбора инвариантом сервиса» | metadata-semantic слой **уже** ranks / rejects / blocks и **может сменить выбранный asset** — доказано synthetic-пробой. `_selection_fingerprint` — защитная самопроверка, а не вето. Дефект — в том, что платный Vision пишет результат **поздно** в review-манифест и не подаёт evidence в decision layer до отбора |
| «два конкурирующих orchestration owner»; «ровно 7 pipeline calls»; «есть риск повторного платного TTS» | ADR 0009 **намеренно** разделяет application orchestration и news pipeline ownership. Вызовов **4–7** в зависимости от режима. Реальный дефект — explicit `stage=` path отключает output-validated idempotency ADR 0006 условием `and not stage` (`src/news/pipeline.py`). Batch-режим idempotency соблюдает. Повторного платного TTS аудит **не обнаружил**: несколько независимых guard'ов плюс существующие тесты |
| «три независимых LocalLibrary implementation»; «#1 допускает `RIGHTS_REFERENCE_ONLY`, поэтому мягче»; «более строгая реализация — та, которую никто не вызывает» | Один `media_index`, один rights-authority `apply_policy_to_candidate`, **два** matcher'а, несколько consumers/wrappers; legacy path #3 использует **ту же** `media_library.search_local_assets`, что и #1. Доказанных расхождений live-путей ровно **два**: missing `provenance` и `review_required=True`. Обратных расхождений — ноль. Аргумент про `RIGHTS_REFERENCE_ONLY` опровергнут: значение перезаписывается политикой |
| «пять расходящихся provider registries, всё свести к `providers/registry`»; «owner конвергенции — PLAN-10B» | Это **разные legitimate facts**, а не дубли: actual constructed providers · provider capabilities · fallback language info · source-class priority · diagnostics inventory · availability. `ProviderCapabilities.query_languages` **уже** имеет приоритет над fallback-таблицей. Остаточный cleanup: declaration mismatch `local_library` → PLAN-10D; вестигиальный `DEFAULT_PROVIDER_ORDER` и осиротевший `unsplash` → opportunistic cleanup. Отдельный PLAN-ID не создаётся |
| «сегменты crf 23 → **конкатенация** crf 20 → субтитры crf 21»; «single-pass — простой fix» | Нормальный путь: segment encode CRF 23 → concat **`-c:v copy`** (не перекодирует) → audio + exact-duration encode CRF 20 → ASS subtitle encode CRF 21 → copies. Три lossy generations возникают **при audio + ASS subtitles**. CRF 20 имеет документированную причину (exact-duration/tpad behavior). Полный single-pass filtergraph — отдельное более крупное исследование |
| «PLAN-5 обязателен до PLAN-9B-5 и PLAN-9B-3» | Targeted, full и все три smoke-команды исполнимы **сегодня** существующими командами. PLAN-5 улучшает uniform runner UX/reproducibility, но техническим blocker product fixes не является |
| «`legacy_broad_query` — единственное, что гарантированно доходит до провайдера» | Не доходит ни разу: `source_is_latin` — свойство всего набора, поэтому русский `primary_query` выбрасывает английский alternative вместе с собой |
| «topic-hardcode сосредоточен в `semantic_selection/query_generator.py`» | Этот модуль **не участвует** в формировании remote-запросов. Canonical boundary — `src/assets/query_adapter.py`; главный носитель hardcode — `src/news/script_generator.py` |
| «канонический CLI не имеет source-text входа»; «`--text`/`--text-file` — единственная уникальная capability `apps/news_to_short`» (**опровергнуто 2026-08-01**) | `create --pasted-script` / `--script-file` при default/legacy unspecified `content_input_mode` уже проводят подготовленный текст в тот же downstream, поэтому PLAN-9B-5a делает вход **явным**, а не создаёт движок. Вторая возможность wrapper'а — `--assets` → `NewsJob.user_assets`, у которой канонического аналога нет; она не может быть молча потеряна при retirement |

### Открытые вопросы ревизии 2.1 (закрываются в момент implementation)

**Закрыты и в списке unresolved больше не значатся:**

- **E-2 — ЗАКРЫТ.** `ProviderQuery.source` — существующее свободное строковое
  telemetry-поле; это **не** schema-level change, tolerant reader не нужен,
  persisted-bytes tripwire не срабатывает. Байты `assets_manifest.json` при этом
  меняются, поэтому characterization PLAN-9B-0 обязан зафиксировать текущее
  содержимое `query_plan` до правки.
- **E-5 — ЗАКРЫТ ОТРИЦАТЕЛЬНО.** PLAN-10B не является owner provider-registry
  convergence, потому что сама registry-convergence гипотеза опровергнута.
- **E-7 — ЗАКРЫТ.** Rights/provenance comparison трёх local-library путей
  выполнен Secondary Deep Dive: ровно два доказанных расхождения.

**Остаются открытыми, каждый — внутри своего слайса, не отдельным аудитом:**

| Вопрос | Кто закрывает |
|---|---|
| полный inventory topic-hardcodes (**PROVISIONAL**, число файлов не invariant) | PLAN-9B-2 |
| миграция всех callers `semantic_selection/query_generator` | PLAN-9B-3 |
| backward compatibility CRITICAL-2 fix со старыми persisted проектами | PLAN-9B-4 |
| метод provider-language adaptation (OD-16) | PLAN-9B-1 |
| механизм и owner subprocess network kill-switch | владелец / PLAN-6B / PLAN-5 |
| public behavior `resume`/`force`/`stop-stage` до крупной orchestration convergence | PLAN-13B |
| реальный ущерб от нескольких FFmpeg-кодирований (никто не рендерил) | будущий renderer slice |
| осуществимость слияния audio/duration encode + subtitle burn в один encode | тот же слайс |
| регистрировать ли `local_library` как `StockProvider` после PLAN-10D | PLAN-10D |
| зелёность baseline | PLAN-4 |

### Сильные foundations — сохраняются

Ревизия 2.1 **не** превращает работающие foundations в кандидатов на rewrite.
Второй competing owner для этих ответственностей не создаётся:

`src/assets/completion/` как canonical completion/readiness owner ·
rights / provenance / `must_avoid` / misleading / conflict gates ·
`VisualBrief` как существующий transport contract ·
`ScriptValidationResult` + `script_metadata` · `DeterministicScriptProvider` ·
`LegacyTemplateScriptProvider` для explicit `legacy`/`template`/`demo`/`test`/
`draft` · subtitles foundation · `src/audio/scene_timeline.py` ·
production catalog foundation · tolerant project readers · final renderer до
отдельного renderer-слайса · `tests/network_guard.py` ·
`route_providers` / `scene_strategy`, пока evidence не докажет их дефект.

**Hard constraints не ослабляются ревизией 2.1:** factual truth · rights ·
provenance · `must_avoid` · misleading/conflict · paid approval остаются
`[HARD]` и heuristics не становятся.

### Никакой новой архитектуры из аудита

Audit evidence обязано **уменьшать** архитектуру, а не порождать абстракции.
Не создавать: `TranslatorService` · `SearchEngine` · `QueryOrchestrator` ·
`search_session.json` · `content_origin` · новый semantic stack · четвёртый
LocalLibrary path · второй completion-state vocabulary · placeholder-пакеты и
speculative interfaces под future AI.

## Owner decisions: motion rendering (2026-08-01)

Источник — read-only rendering / motion-design / AI-directed video аудит от
clean HEAD `35325b4`; findings записаны в `CLEANUP_REGISTRY.md` как C53–C62.
Продуктовая форма направления — `PRODUCT_PLAN.md`, раздел «Motion Design and
Multi-Renderer Composition». **Ни одно решение ниже не меняет current
checkpoint, критический путь, prerequisites и статусы существующих этапов.**

| # | Решение |
|---|---|
| **OD-M-1** | **Несколько специализированных авторов кадра, но не несколько конкурирующих pipelines.** Каноническая модель: `content core → visual/composition intent → canonical author для composition_type → normalized scene artifact → FFmpeg final assembly → существующие quality/rights/export` |
| **OD-M-2** | **FFmpeg остаётся canonical final assembler**: normalization, concat, voice, music, SFX, subtitles, encoding, export. Его роль не оспаривается ни одним motion-инструментом. При этом **`final_renderer` не объявляется неизменным**: его foundation подлежит доработке (C58–C61) |
| **OD-M-3** | **Stock crop/zoom path сохраняется и дорабатывается, а не замещается** (C57). Для стокового кадра FFmpeg — лучший инструмент; широкий renderer cleanup не имеет права его удалить |
| **OD-M-4** | **Один `composition_type` → один canonical production backend.** Разные `composition_type` могут иметь разных специализированных авторов. Бессрочно поддерживать один user outcome в двух реализациях (counter в двух backend одновременно) запрещено |
| **OD-M-5** | **Пользователь и AI выбирают визуальный замысел, а не библиотеку**: stock footage · animated counter · chart · map · comparison · process diagram · text emphasis · scientific animation. Expert/debug режим позднее может отключать web motion, включать безопасный fallback, выбирать backend в сравнительном PoC и диагностировать сбои. **Точные публичные имена не фиксируются** |
| **OD-M-6** | **Порядок AI-режиссуры:** AI Director предлагает 2–4 варианта **разных** `composition_type` → каждый даёт дешёвый poster frame → deterministic QA отсеивает технический брак → Vision или человек выбирает по смыслу → полный motion render только для выбранного → отвергнутые сохраняются как evidence. Аудиция идёт по замыслу, а не по инструментам. **Новый AI orchestration owner не создаётся** — расширяются visual planning, production catalog, semantic evidence, completion/review |
| **OD-M-7** | **PD-11 — Replacement and Retirement Pairing.** Внедрение, замещающее существующую capability, обязано иметь связанный retirement path. Полная формулировка и жизненный цикл — `PRODUCT_PLAN.md`, раздел 4 |
| **OD-M-8** | **Story Card сохраняется как рабочий product template; удаление шаблона запрещено.** Его текущий MoviePy renderer — **временная** implementation, бессрочное закрепление запрещено. Story Card становится **обязательным parity-case** сравнительного PoC (C53) |
| **OD-M-9** | **`generated_infographic` разбирается, а не удаляется целиком** (C56). Сохраняются: правило «нет evidence → нет фактической диаграммы», fingerprint спеки, создание project-owned актива с license/provenance/checksum, technical validation, минимальная offline аварийная карточка. Замещается только рисующая часть |
| **OD-M-10** | **Целевая стратегия инструментов — вариант «Hybrid high-quality».** CORE: FFmpeg + один web motion backend после PoC + ECharts. COMMITTED LATER: MapLibre (после license decision) · Lottie · OTIO только как односторонний export. SPECIALIZED ON DEMAND: Manim · Three.js внутри выбранного backend · Blender после hardware review · Resolve/Fusion как внешний manual finishing |
| **OD-M-11** | **Motion Canvas в первый PoC не включается.** Пересмотр только если Remotion и HyperFrames оба провалят обязательные критерии детерминизма или Windows-надёжности |
| **OD-M-12** | **Не добавлять сейчас:** Vega-Lite как второй runtime · D3 как отдельный chart stack · deck.gl · Rive · PySceneDetect/OpenCV в Content Creator · Shotstack/Creatomate · обязательный cloud rendering · генерация произвольного кода в пользовательском рантайме |
| **OD-M-13** | **`PLAN-9B` — вторая половина формата Hybrid Explainer, а не его предшественник.** Стоковая часть гибридного формата зависит от корректных provider-запросов, поэтому motion-направление её не заменяет и не откладывает |

### Motion rendering: что остаётся `OWNER_DECISION_REQUIRED`

Не утверждено этим слайсом и не может быть выведено из аудита:

1. победитель Remotion vs HyperFrames;
2. актуальные лицензии и коммерческие ограничения любого инструмента;
3. точные публичные имена `composition_type`;
4. владелец хранения design tokens (`channels` либо `config/design_tokens`);
5. место persistence render cache/fingerprint;
6. политика map tiles и styles;
7. момент постановки `MOTION-CS1…CS4` в расписание;
8. удаляется ли проигравший web backend полностью или сохраняется только в
   developer-only PoC archive.

### Motion rendering: что запрещено утверждать без отдельной проверки

Ни один из пунктов ниже не измерялся и не проверялся в этом слайсе, поэтому
записывать их как факт запрещено:

- что MoviePy доказанно медленнее browser backend на текущей машине владельца;
- что HyperFrames не несёт коммерческого риска;
- что Remotion имеет конкретную текущую цену или конкретные условия лицензии;
- что вопрос map tiles/styles решён;
- что RX 570 работает или не работает в конкретном текущем релизе любого
  инструмента.

Такие пункты маркируются
`REQUIRES SEPARATE WEB/LICENSE/HARDWARE VERIFICATION`.

Численные пороги сравнительного PoC (например время рендера сцены, время
poster frame, потолок памяти, доля совпадений perceptual hash, число прогонов,
доля автоматически исправленных сцен) остаются **предлагаемыми критериями
измерения**. Ни один из них ещё не измерялся, поэтому нормой продукта они не
являются — действует общая `Measurement policy` этого плана.

## Safety boundaries

Действуют правила R1–R3 из `AGENTS.md`; здесь они не дублируются.
Дополнительно на период этой программы:

- сеть, provider search, download, Vision, TTS, render и платные API не
  выполняются без отдельного разрешения на конкретное действие;
- synthetic render в tempfile разрешён и обязателен для renderer contract
  tests; реальный render пользовательского проекта — только по необходимости и
  с разрешением;
- в `master` не сливать и ничего не публиковать без отдельного разрешения;
- destructive retirement **knowledge-bearing family** (source, workflow, config,
  prompts, templates, tests, уникальное docs/evidence) выполняется только после
  Knowledge Salvage Gate (PLAN-L0) и с обратимым retirement-механизмом;
- удаление **disposable runtime/media/cache** идёт цепочкой PLAN-14D → PLAN-14E
  и KSG не требует; его gate — классификация, `Preserved runtime corpus`,
  проверенный абсолютный путь и owner approval на конкретное действие.

**Изменено ревизией 2.** Безусловная неприкосновенность `projects/`, `assets/`,
`manual_assets/`, `music/`, `outputs/` снята: владелец объявил тестовое
runtime-медиа disposable. Вместо неё действует точный список сохраняемого.

**Preserved runtime corpus — сохраняется обязательно:**

- отобранный **минимальный representative** набор JSON/SRT/ASS манифестов
  проектов (состав определяет PLAN-14D, см. registry C32);
- `assets/library/metadata/media_index.json` — provenance и rights локальной
  медиатеки;
- versioned SVG в `manual_assets/**`;
- versioned config `config/` (кроме умирающего `video_style.json`) и активные
  `channels/nature_science_news_ru`, `channels/nature_pulse`;
- live-eval dataset/results/frames как evaluation resource (переезжает по OD-8).

**Disposable — удаляется на runtime reset:** медиа во всех перечисленных
каталогах (`*.mp4`, `*.mov`, `*.wav`, `*.mp3`, `*.png`, `*.jpg`, `*.jpeg`),
кэши, `project_solar_vs_nuclear/`, `assets/voice_samples` (OD-3),
`MOSS_TTS_Nano/` (OD-7).

Ни одно удаление не выполняется вне своего bounded slice и без явного
подтверждения абсолютного пути.

## Agent Autonomy Model

Действует на период этой программы. Канонический владелец правил после PLAN-6A —
`AGENTS.md`; здесь модель зафиксирована, чтобы она действовала **до** 6A, и
после 6A этот раздел сворачивается до ссылки. Отдельный документ не создаётся.

### Классы правил

```
[HARD]   нарушать нельзя. Если правило можно enforce технически —
         оно обязано быть enforced, а не только записано.
[ARCH]   архитектурная граница. Пересматривается через evidence,
         ADR и independent review. Оспаривать — можно и нужно.
[HINT]   рекомендуемый способ. Если он не достигает SUCCESS CRITERIA,
         агент обязан искать другой и назвать причину смены.

Правило без класса читается как [HINT].
```

**[HARD].** Secrets · платные и сетевые вызовы без разрешения на конкретное
действие · destructive Git · удаление реальных user data · rights, `must_avoid`,
misleading и conflict gates · публикация · изменение persisted contract без
tolerant reader и migration · второй одновременно живущий canonical owner ·
**доказать canonical owner, callers, persisted contracts, дубли и тесты
изменяемой capability до её изменения**.

**[ARCH].** Канонический CLI `python -m ai_youtube` · два engine (ADR 0016) ·
один owner на capability · направление зависимостей · граница workspace
(ADR 0002) · владение persisted schema · `strict` как default completion mode ·
tolerant readers · размещение пакетов и структура корня.

**[HINT].** Приоритет провайдеров · число и виды запросов · пороги
`minimum_confidence`/`hard_reject_confidence` · `analyse_and_report` и
`semantic_rerank_enabled: false` · предпочтительный тип визуала · порядок
внутренних действий · «только targeted tests» · рекомендуемый размер модуля ·
лимит длины `AGENTS.md`.

### Goal > prescribed method

```
Выполнение инструкции не является выполнением задачи.
Если CURRENT APPROACH не достигает SUCCESS CRITERIA, задача не закрыта.
Агент переходит к поиску альтернативы внутри [HARD] и своих decision rights,
а не сообщает об успехе на основании соблюдённой процедуры.
```

Плохой quality score сам по себе **не** является причиной остановки. Допустимые
причины остановки перечислены в PLAN-10A.

### Decision rights — три tripwire

Owner approval требуется, когда изменение затрагивает:

1. **persisted bytes** — schema, поле манифеста, layout файлов, имя каталога
   проекта (дополнительно обязателен tolerant reader);
2. **внешне наблюдаемую поверхность** — имя команды CLI, флаг, exit code, ключ
   JSON-вывода, имя console script;
3. **деньги, сеть или публикацию** — на каждое конкретное действие.

Всё остальное — решение агента под ответственность reviewer, **включая удаление
реализации, у которой есть callers**, если callers переведены в том же изменении
и ни один tripwire не сработал. Существующая зависимость не является
доказательством, что её нужно сохранять.

**Уже выданные owner approvals.** Tripwire не отменяется и не ослабляется;
approval — это факт, а не исключение из правила. Утверждение владельцем ревизии
2 этого плана является explicit owner approval на persisted-change **ровно в том
объёме, который уже описан в PLAN-9A**: additive schema, tolerant reader,
чтение старых manifests без миграции, best-so-far/persistence contract в
перечисленном там составе. Повторно спрашивать владельца о самом PLAN-9A не
нужно.

Любое расширение за эти границы — non-additive изменение, новый layout файлов,
переименование каталога проекта, второй manifest, схема вне названного состава
или persisted-изменение в другом слайсе — снова требует owner approval. Approval
на PLAN-9A не переносится на PLAN-9B…PLAN-15 и на PLAN-L. **Уточнено ревизией
2.1:** approval PLAN-9A относится **ровно** к составу PLAN-9A и не переносится
на `PLAN-9B*`, `PLAN-9C`, `PLAN-9D`, `PLAN-9E`, `PLAN-10*` и любые новые
persisted / public / network / destructive изменения.

### Challenge / Recovery Protocol

Новые имена состояний завершённости **не вводятся**: словарь уже принадлежит
`src/assets/completion/modes.py` (`usable_in_draft`, `automatic_render_allowed`,
`publish_ready`, `manual_replacement_recommended`, `manual_replacement_required`,
`blocked` + `block_reasons`, tiers `A_exact…F_emergency`). Причины остановки
принадлежат PLAN-10A. Второй словарь создал бы второго canonical owner.

Когда предписанный подход не даёт результата:

1. назвать **root cause**, а не симптом;
2. **не ослаблять [HARD]**;
3. найти **минимум одну жизнеспособную альтернативу**. Сравнение нескольких
   альтернатив обязательно **только** для неоднозначного, архитектурного,
   дорогого или высокорискового решения; в обычном случае одной работающей
   альтернативы достаточно;
4. внутри decision rights — применить и записать причину;
5. вне decision rights — остановиться, показать альтернативу и рекомендацию.

### Owner Lookup — semantic trigger

Проверка существующего владельца обязательна, когда создаётся:

- новая **shared / cross-cutting responsibility**;
- новый **public owner** — то, на что будут ссылаться извне модуля;
- новый **persisted owner** — то, что пишет или владеет форматом на диске.

Имена классов `Service|Registry|Manager|Provider|Store|Engine` — только
эвристика для reviewer, не сам триггер. Для private-функций не применяется.

Процедура — один проход: grep по существительному-ответственности в
`SYSTEM_MAP.md`, `schemas/` и `src/**` → `reuse` / `extend` / `replace`. При
создании нового owner — одно предложение в commit body о том, почему
существующий нельзя расширить. Enforce выполняет reviewer, отдельный QA-модуль
не создаётся: проверка требует суждения.

### Task contract

Формат задания каждого достаточно крупного слайса:

```
OBJECTIVE          что должно измениться для пользователя
SUCCESS CRITERIA   какой конечный результат считается хорошим
HARD CONSTRAINTS   что нельзя нарушать
ALLOWED ZONES      какие файлы/каталоги разрешено менять
CURRENT APPROACH   рекомендуемый способ
ALTERNATIVES       агент вправе искать самостоятельно
STOP CONDITIONS    когда действительно нужно остановиться
VERIFICATION       чем доказан результат
ROLLBACK           как откатить
EXIT CONDITION     когда пункт можно снять с учёта
```

`ALLOWED ZONES` держится отдельно от `HARD CONSTRAINTS`: первое — scope одного
слайса, второе — вечное правило. В прежней редакции оба записывались одинаково
под заголовком «запрещено», и агент не мог отличить оспариваемое от
неоспариваемого.

## Reversible retirement mechanism

Постоянный каталог `trash/` не создаётся: он стал бы вторым source tree.
Механизм обратимого ретайра:

1. **annotated tag** `retired/<family>-<YYYY-MM-DD>` на последний commit, где
   код ещё существовал;
2. **commit body** ретайр-коммита содержит `Retired:`, `Reason:`,
   `Replaced-by:`, `Recovered-from:` (тег), `Salvaged:` (ссылка на решение
   PLAN-L0), `Exit:`;
3. **таблица `Retired`** в `CLEANUP_REGISTRY.md`;
4. **внешняя копия обязательна.** [FACT, обновлено 2026-08-05] Приватный
   remote теперь существует и `governance-reset`/`master` отправлены (OD-S-5);
   это не отменяет правило, потому что retirement-теги не публикуются
   обычным push и остаются локальными, если их не отправить отдельно: перед
   каждым ретайром по-прежнему выполняется `git bundle create` тега во
   внешний workspace.

Archive branch не используется: ветки дрейфуют и требуют обслуживания.

## Test classification

Перед любым удалением или переписыванием test-модуль получает класс:

```
PRODUCT CONTRACT        защищает поведение, обещанное пользователю
ARCHITECTURE INVARIANT  защищает границу, которую мы намеренно держим
CHARACTERIZATION        зафиксировал поведение на время конкретного refactor
LEGACY ANCHOR           замораживает старую реализацию или accidental structure
```

**LEGACY ANCHOR не препятствует сознательному ретайру старой архитектуры** и
удаляется либо переписывается вместе с ней. Зелёный или красный тест сам по себе
контрактом не является: сначала отвечаем, защищает ли он нужное product/public
behavior или замораживает accidental legacy implementation.

Подтверждённые кандидаты в LEGACY ANCHOR записаны в `CLEANUP_REGISTRY.md`,
раздел «Accidental invariants».

**Физический restructure каталога `tests/` не является prerequisite product
work и в критический путь не входит.** [FACT] сейчас 112 плоских модулей,
30 403 строки, `conftest.py` отсутствует, network guard ставится из
`tests/__init__.py`. Плоская структура с осмысленными именами работает;
реструктуризация дала бы большой diff и нулевую product-ценность. Вопрос
пересматривается **после** PLAN-L, когда модулей останется около 106.
Именование вида `test_anime_factory_v3/v4` и `test_stage1…stage4` кодирует
историю rescue, а не ответственность — кандидаты на переименование, но не
приоритет.

**Известный риск, не закрытый классификацией.** [FACT] test-модули запускают CLI
через `subprocess`, где `tests/network_guard.py` **не действует** — guard живёт
внутри test-пакета и дочерним процессом не наследуется. Это касается не только
режима `smoke` из PLAN-5, но и `full`. **Измерение, не invariant:** на audit HEAD
`adcbb19` таких модулей **12** (было записано 7); при изменении tests число
изменится, нормой оно не является (registry C49).

**Механизм закрытия ревизией 2.1 заранее не выбран.** Расширение guard на
subprocess boundary и environment kill-switch — обе альтернативы остаются
открытыми; выбор и owner — implementation-time evidence/owner decision. **PLAN-6B
остаётся report/measurement owner в своей текущей границе** и ничего не мутирует;
если выбранный механизм потребует, чтобы production-код уважал kill-switch, это
production-изменение вне зон 6B и оно получает своего owner отдельным слайсом.

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

Измерение на проверенном исходном HEAD
`84bdd8b4f64c7adaf7582bdb39b15b18163253fb`, 2026-08-01, tracked-дерево
чистое:

- `.\venv\Scripts\python.exe -B -m unittest discover -s tests -p
  "test_*.py"` — 1441 тест, 231.839 секунды, exit code 0; failures: 0,
  errors: 0, skips: 0. Прогон выполнен offline; provider search/download,
  Vision, TTS, платные API-вызовы и реальный пользовательский render не
  выполнялись. Число тестов и длительность — измерение, не норматив.

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
11. **Capability owner gate — обязателен, глобальный inventory — нет.** Перед
    изменением конкретной capability доказываются: canonical owner, фактические
    callers, persisted contracts, duplicate implementations, релевантные tests и
    границы legacy/replacement. Это правило класса `[HARD]`. Оно **заменяет**
    прежнее требование закрыть весь PLAN-1 до любого production-изменения:
    доказывается область, которую меняешь, а не весь репозиторий.
12. **Detail policy.** Подробно описывается только `active` шаг и ближайшие
    один-два следующих. `completed` сворачивается до статуса, commit,
    измеримого результата и фактических проверок. `blocked` держится в виде ID,
    зависимостей, allowed/prohibited zones, gates, verification и rollback.
    Развёрнутые описания PLAN-9…PLAN-15 сворачиваются в момент PLAN-8, когда
    у продуктовых подробностей появится собственный владелец
    `PRODUCT_PLAN.md`, а не раньше: до этого свёртка потеряла бы
    owner-approved решения. Этот файл не превращается во второй Master Plan.

## Execution table

Формат каждого шага одинаков. `commit` заполняется только фактическим hash
после выполнения; заранее hash не придумывается — источником является Git.

### Критический путь (ревизия 2.1)

Принцип владельца: **minimum strong foundation → product slice → feedback →
следующий foundation только если он реально нужен.** Не governance-first и не
product-at-any-cost. Product-слайс не ждёт идеального репозитория, но перед
изменением каждой capability агент обязан доказать её настоящего owner.

**До первого product fix — ровно четыре шага плюс два product-слайса:**

```
PLAN-1D-routing
  → PLAN-2 → PLAN-3 → PLAN-4
  → ► PLAN-9B-0 (characterization) → PLAN-9B-1 (provider-language foundation) ◄
```

Почему остаётся каждый из четырёх — по одной строке:

| Blocker | Почему до первого production fix |
|---|---|
| **PLAN-1D-routing** | Без него новый агент, буквально исполнив `AGENTS.md`, уходит в historical master plan и начинает не ту работу. |
| **PLAN-2** | Красный `test_voice_profile_resolution` не даёт различить «сломал я» и «было сломано» в радиусе изменения. |
| **PLAN-3** | То же для `test_autonomous_completion_pipeline` — модуля, который потом меняет PLAN-9A. |
| **PLAN-4** | Без зелёного воспроизводимого baseline targeted-прогон после query-изменения недоказуем. |

**Параллельно, не блокирует первый product fix** (стартует после зелёного
PLAN-4; PLAN-1C′ — сразу):

```
PLAN-5                        · uniform test runner (UX/reproducibility)
PLAN-6A → PLAN-6D → PLAN-6E   · governance / scope control / independent reviewer
PLAN-6B · PLAN-6C · PLAN-7 · PLAN-8 · инкрементальный перевод прозы (OD-5)
PLAN-L1 → L2 → L3 → L4        · retire legacy content stack после PLAN-L0
PLAN-1A · PLAN-1B · PLAN-1C′  · capability owner gates
```

**Дальше — по risk boundary, а не по линейной цепочке:**

Граф ниже нормализован по фактическим зависимостям detailed sections; он не
является одной линейной цепочкой и новых рёбер не вводит.

```
основная продуктовая последовательность:
  PLAN-9B-0 → PLAN-9B-1 → PLAN-9B-5a → PLAN-9B-4
  → PLAN-L0 → PLAN-9B-PRODUCER
  → [stabilization gate: PLAN-STAB-1…7 + stabilization review] → PLAN-9B-2

  PLAN-9B-3   — отдельный cleanup/destructive path после PLAN-9B-2
  PLAN-9B-5b  — отдельный destructive retirement path после миграции
                capability/callers и своих gates
  Ни PLAN-9B-3, ни PLAN-9B-5b prerequisite PLAN-9A не являются.

две сходящиеся ветки:
  PLAN-9B-2 + PLAN-1C′ + PLAN-6E → PLAN-9A → PLAN-10A → PLAN-10B → PLAN-10C
  PLAN-1C′ + PLAN-6E             → PLAN-9C → PLAN-9D

PLAN-9E   требует PLAN-9D + PLAN-10C + owner approval
PLAN-10D  после PLAN-10C
PLAN-11   после PLAN-9E + PLAN-10C
затем PLAN-12* → PLAN-13* → PLAN-14* → PLAN-15
```

### Risk-based governance model (ревизия 2.1)

Blocker остаётся только если он защищает **конкретную** risk boundary, которую
пересекает **конкретный** слайс. «Стоял в плане» причиной не является (OD-26).

| Слайс | Роль в ревизии 2.1 | Обоснование одной строкой |
|---|---|---|
| **PLAN-5** | **PARALLEL для всех под-слайсов PLAN-9B** | targeted / full / smoke исполнимы **сегодня** существующими командами (PLAN-4 и CI); PLAN-5 улучшает uniform runner UX и воспроизводимость формулировки, но техническим blocker product fixes не является |
| **PLAN-6A** | **PARALLEL относительно PLAN-9B** | Agent Autonomy Model уже действует из текста этого плана; зависимость **6A → 6D — ordering convention, а не техническая необходимость** |
| **PLAN-6D** | **BLOCKER первого multi-owner implementation slice** | `check_task_scope` защищает от выхода diff за allowed zones; у 9B-0/9B-1 allowlist тривиален, первый multi-owner diff — PLAN-9B-2 |
| **PLAN-6E** | **BLOCKER первого destructive retirement / high-risk shared-contract slice** | reviewer обязан существовать до первого удаления реализации, у которой есть callers (PLAN-9B-2, 9B-3, 9B-5b) |
| **PLAN-1C′** | **прямая зависимость от PLAN-6E снята** | docs-only ownership inventory, пишущий в `CLEANUP_REGISTRY.md`, не требует существования reviewer-skill |
| **PLAN-9A** | **явно требует PLAN-6E** плюс PLAN-9B-2 и PLAN-1C′ | persisted-state boundary |
| **PLAN-9C** | **явно требует PLAN-6E** плюс PLAN-1C′ | semantic decision boundary |

**Почему 9A/9C требуют 6E явно, а не транзитивно.** Через PLAN-9B-2 зависимость
существует и без записи, но транзитивные гарантии ломаются при следующем
reorder. Это **не** ослабление safety, а перенос gate на фактическую risk
boundary.

### Risk-boundary таблица safety gates

Заменяет одну линейную цепочку блокеров и делает явным, что защищает каждый gate.

| Пересекаемая boundary | Обязательные gates | Первый слайс, который её пересекает |
|---|---|---|
| локальное поведение, targeted tests, ноль persisted/public/paid/destructive | 1D, 2, 3, 4 | **PLAN-9B-0, PLAN-9B-1** |
| public CLI / input mode | + **owner approval** (`smoke` исполним существующей командой) | **PLAN-9B-5a** |
| наблюдаемое поведение `strict` | + **owner approval** | PLAN-9B-4 |
| значения существующих persisted visual-plan полей без новой schema/layout | + **OD-P-1** + characterization tolerant round-trip | **PLAN-9B-PRODUCER** |
| несколько owners в одном diff | + **PLAN-6D** (`check_task_scope`) | PLAN-9B-2 |
| destructive retirement реализации с callers | + **PLAN-6E** + reversible retirement (annotated tag + `git bundle` + строка `Retired`) | PLAN-9B-2, PLAN-9B-3, PLAN-9B-5b |
| persisted bytes / schema / layout | + tolerant reader + **owner approval** (approval PLAN-9A **не переносится**) + PLAN-6E | PLAN-9A |
| semantic / Vision decision path | + **PLAN-1C′** + **PLAN-6E** | PLAN-9C |
| network / model / paid операция | + **owner approval на конкретное действие** + PLAN-6E | model-assisted вариант PLAN-9B-PRODUCER, PLAN-9E |
| runtime / user data move | + `Preserved runtime corpus` + проверенный абсолютный путь + owner approval | PLAN-14D/14E |

**Что осознанно не оптимизировано.** Путь не сокращался ради меньшего числа
этапов: PLAN-4 сохранён, хотя он «всего лишь измерение»; PLAN-6E сохранён как
blocker первого destructive слайса. Минимизированы только blockers без
конкретной защищаемой boundary.

**Что изменилось относительно ревизии 2.** Первым product-слайсом становится
`PLAN-9B-0/9B-1`, а не `PLAN-9A`: best-so-far persistence бессмысленна, пока
система не получает provider-ready кандидатов (OD-15). В основной **product
order** перевёрнуто одно ключевое ребро: `9A → 9B` становится `9B → 9A`.
Governance dependencies и gates при этом **отдельно перераспределены по
risk-based model**: прямая `1C′ → 6E` снята, `9A → 6E` и `9C → 6E` записаны
явно, `PLAN-5` и `PLAN-6A` стали parallel относительно 9B, 6D/6E переведены на
свои risk boundaries, а PLAN-9B декомпозирован. `PLAN-5`, `PLAN-6A`, `PLAN-6D`,
`PLAN-6E` и `PLAN-1C′` **не удалены**.

PLAN-9B-1 становится первым слайсом, меняющим production-код в продуктовой
ветке; PLAN-L2/L3/L4 меняют production-код независимо, в ретайр-ветке работ, и
на поведение активного `content_creator` не влияют.

Независимые под-slices могут меняться местами только когда их зависимости,
allowed zones и owner approvals не пересекаются; изменение порядка
фиксируется здесь до работы, а не задним числом.

### POST-AUDIT STABILIZATION PROGRAM (PLAN-STAB-*)

- **owner decision date:** 2026-08-05.
- **audit baseline:** clean HEAD `e4cad2a` (read-only AI-practices audit,
  переданный владельцем). Аудит в репозиторий не копируется: здесь остаются
  только executable contracts и disposition. Severity сохраняется по
  фактическому user/security/rights impact и не повышается ради маршрутизации.
- **цель:** подтверждённые audit gaps получают исполняемых owners раньше
  следующего product slice, но не реализуются одним большим diff.
- **чем это не является:** отменой Visual Planning work, новым диагностическим
  этапом, вторым планом и разрешением начать любой из слайсов ниже без
  отдельного owner-issued implementation prompt.

Owner decisions программы:

| # | Решение |
|---|---|
| **OD-S-1** | `PLAN-9B-2` **deferred** за stabilization gate. Это не отмена: статус остаётся pending / not started, acceptance criteria не менялись |
| **OD-S-2** | Каждый PLAN-STAB-слайс — bounded: один canonical owner, один commit, targeted tests, explicit scope, независимый immutable-commit review, отдельный repair/re-review при findings |
| **OD-S-3** | Обязательный блокирующий набор до возврата к `PLAN-9B-2` — PLAN-STAB-1…7 плюс отдельный stabilization review |
| **OD-S-4** | Остальные подтверждённые MAJOR findings попадают в план, но индивидуально `PLAN-9B-2` не блокируют; выполняются после gate либо параллельно при непересекающихся owners |
| **OD-S-5** | Git backup — **completed manual owner action**: private remote существует, `governance-reset` и `master` отправлены, `governance-reset` — default branch. Задача «создать remote» как pending не создаётся |
| **OD-S-6** | Legacy findings не дублируются — см. «No-action и уже покрытые findings» |
| **OD-S-7** | `COMMANDS.md` **удаляется**, а не сокращается; replacement command document запрещён. Контракт PLAN-7 скорректирован ниже |
| **OD-S-8** | Docs freshness не чинится заменой даты: нужен Git-aware contract (PLAN-STAB-8) |
| **OD-S-9** | Не каждый audit finding является BLOCKER; routing не меняет severity |

**Общие требования ко всем PLAN-STAB-слайсам** (не повторяются в каждом):
один bounded commit с trailer `Plan-Step: <ID>`; production-код вне
названного canonical owner — prohibited zone; `docs/current/` входит в allowed
zone только для checkpoint/status/evidence после фактического завершения;
характеризация до изменения наблюдаемого поведения; сеть, provider/model API,
download, Vision, TTS, paid calls и реальный render не выполняются без
отдельного owner approval на конкретное действие; **rollback** — revert одного
commit без миграций данных; **independent review** — обязательный read-only
review одного immutable commit по `skills/review-change/SKILL.md`, с отдельным
repair/re-review при findings.

**Blocking gate: что должно быть закрыто до возврата к PLAN-9B-2.**

1. PLAN-STAB-1 completed and independently accepted — **satisfied**: commit
   `f0b69db`, independent review verdict ACCEPT WITH MINOR, pushed;
2. PLAN-STAB-2 completed and independently accepted — **satisfied**: commit
   `0eea5be`, independent review verdict ACCEPT, pushed;
3. PLAN-STAB-3 completed and independently accepted — **satisfied**: commit
   `9222519`, independent review verdict ACCEPT WITH MINOR, pushed;
4. PLAN-STAB-4 completed and independently accepted — **satisfied**: commit
   `0947e51`, independent review verdict ACCEPT WITH MINOR, pushed; два
   findings зафиксированы как non-blocking residual evidence (см. раздел
   PLAN-STAB-4) и не исправлены этим слайсом;
5. PLAN-STAB-5 completed and independently accepted — **satisfied**:
   единственный commit слайса (trailer `Plan-Step: PLAN-STAB-5`), independent
   review verdict ACCEPT (findings: нет), GitHub Actions run `31084873522` —
   offline suite зелёный (1646 tests, `OK (skipped=6)`, failures=0, errors=0),
   CI headSha == HEAD == `origin/governance-reset`, worktree clean;
6. PLAN-STAB-6 completed **либо** владелец формально принимает
   документированный residual risk;
7. PLAN-STAB-7 — три отдельных, не взаимозаменяемых условия: (a) factual
   routing repair, выполненный слайсом PLAN-STAB-0 — completed; (b) сам
   PLAN-STAB-7 (checker extension + integrity tests) — implementation
   completed 2026-08-06, integrity tests существуют
   (`tests/test_docs_routing_and_freshness.py`) и зелёные; (c) independent
   review этого commit — выполнен: initial verdict ACCEPT WITH MINOR (commit
   `42fa741`, CI run `31101208366`, 1693 tests OK), repair commit `8357402`
   закрыл все четыре finding F1-F4, repair re-review verdict ACCEPT WITH
   MINOR с blocking findings 0 (CI run `31110155685`, 1702 tests OK) —
   **satisfied**: (a), (b) и (c) выполнены;
8. отдельный **stabilization review** подтверждает четыре свойства:
   user-output preservation · offline/paid fail-closed behavior · rights
   safety · однозначный current routing.

**Утверждённый активный execution route (owner decision 2026-08-06).** После
закрытия PLAN-STAB-5, PLAN-STAB-9 и PLAN-STAB-7 + PLAN-STAB-8 приоритетный
порядок выполнения — **PLAN-STAB-6** или явное residual-risk decision →
stabilization review → PLAN-9B-2 (детали — раздел «Current checkpoint» выше).
Это owner-prioritized порядок выполнения, а не blocking dependency:
PLAN-STAB-9 и PLAN-STAB-8 остаются non-blocking для PLAN-9B-2 и не входят в
blocking gate задним числом, а содержание и нумерация пунктов 5–8 blocking
gate этим решением не менялись.

**Non-blocking follow-up.** PLAN-STAB-9…PLAN-STAB-17 находятся в обязательном
stabilization backlog, но индивидуально `PLAN-9B-2` не блокируют.
PLAN-STAB-8 closed 2026-08-06 (non-blocking, см. выше). PLAN-7 желательно
завершить до возврата; он может идти параллельно, если не пересекается с
production safety owners.

**Accepted manual owner actions** (новыми code slices не становятся):
Git backup (OD-S-5, выполнен); изменения `.claude/settings.local.json`, который
намеренно gitignored и остаётся под контролем владельца (PLAN-STAB-6, часть B).

**No-action и уже покрытые findings.** Новый слайс не создаётся:

| Finding | Disposition |
|---|---|
| legacy `src/video_renderer.py` удаляет output до успеха | уже **PLAN-L3** (удаляет root `src/`-модули кроме `media_library.py`/`utils.py`); production callers — legacy `size_comparison_engine` и root `pipeline.py` через compatibility patch-point `legacy_pipeline.workflow` |
| legacy asset/download stack | уже **PLAN-L0 → PLAN-L4** |
| root compatibility shims (`pipeline.py`, `apps/youtube_pipeline/`, `scripts/`, `legacy/`) | существующие retirement-слайсы **PLAN-L3/PLAN-L4** |
| отсутствие MCP | no action |
| недостижимые Git blobs | optional maintenance, не product action |
| `refs/codex/**` | no product action |
| два render stacks (FFmpeg и MoviePy Story Card) | автоматически не объединяются; owner направления — OD-M-4/OD-M-8 и unscheduled `MOTION-CS1/CS2` после отдельного product/format audit |
| размер execution plan | уже **PLAN-8** + правило 12 Execution protocol |
| Git backup | completed manual action (OD-S-5) |

**Порядок возврата к PLAN-9B-2.** Закрытый blocking gate → отдельный
stabilization review с ACCEPT → отдельный owner-issued implementation prompt
для PLAN-9B-2. Ни закрытие отдельного PLAN-STAB-слайса, ни этот amendment
разрешением начать PLAN-9B-2 не являются.

#### PLAN-STAB-0 — post-audit stabilization plan amendment

- **status:** completed · **completed:** 2026-08-05 · **commit:** Git log —
  trailer `Plan-Step: PLAN-STAB-0` (собственный hash внутри того же commit не
  записывается, см. Execution protocol, пункт 3).
- **blocking для PLAN-9B-2:** нет — это сам owner-decision слайс, а не safety
  fix · **зависимости:** —.
- **цель:** канонизировать owner decisions последнего read-only AI-practices
  audit; создать PLAN-STAB-1…17; исправить current routing; отложить
  PLAN-9B-2 за stabilization gate.
- **user impact:** косвенный — подтверждённые safety findings получают
  исполняемых owners и однозначный порядок, а новый агент получает ровно один
  current checkpoint.
- **canonical owner:** `docs/current/PROJECT_EXECUTION_PLAN.md`.
- **changed zones:** current execution plan и его routing mirrors
  (`START_HERE.md`, `CURRENT_STATE.md`, `SYSTEM_MAP.md`).
- **prohibited zones (соблюдены):** production-код, tests, tools, README,
  `COMMANDS.md`, skills, contracts, settings, registry, schemas, configs,
  manifests, GitHub workflow.
- **измеримый результат:** PLAN-STAB-1…17 определены по одному разу и
  разрешаются; blocking gate и no-action disposition записаны; единственный
  current checkpoint — PLAN-STAB-1.
- **implementation safety slices этим шагом не начинались:** PLAN-STAB-1…6 и
  PLAN-STAB-8…17 остаются pending / not started. Для PLAN-STAB-7 этим шагом
  выполнен только factual routing repair в current docs; его integrity checker и
  остальная implementation не начинались, и completed PLAN-STAB-7 не объявляется.
  PLAN-9B-2 остаётся pending / not started и deferred.
- **фактические проверки:** docs QA, `tests.test_check_agent_docs`,
  `tests.test_stage2_agent_onboarding`, `check_task_scope` по exact allowed
  paths и `git diff --check` — exit code 0. Сеть, providers, download, Vision,
  TTS, paid API и render не выполнялись.
- **rollback:** revert одного commit.

#### PLAN-STAB-1 — atomic final-output preservation

- **status:** completed · **completed:** 2026-08-05 · **commit:** Git log —
  trailer `Plan-Step: PLAN-STAB-1` · **blocking для PLAN-9B-2:** пункт 1 gate
  satisfied — independent review выполнен, verdict ACCEPT WITH MINOR, commit
  pushed; overall blocking gate (пункты 4–8) остаётся открытым ·
  **зависимости:** —.
- **цель:** новый финальный MP4 создаётся отдельно, валидируется и только затем
  заменяет предыдущий результат.
- **user impact:** прерванный или неудачный повторный render перестаёт
  уничтожать уже готовое видео пользователя.
- **canonical owner:** `src/news/final_renderer.py`.
- **allowed zones:** `src/news/final_renderer.py` и его owning test-модули.
- **prohibited zones:** `src/news/pipeline.py` и stage orchestration; resume
  semantics; второй renderer; новый artifact, manifest, layout или public flag;
  изменение production render contracts/layout без отдельного owner decision.
- **success criteria:** прежний final output переживает любой сбой render;
  temp-файл лежит на той же файловой системе, что и цель; валидация выполняется
  **до** promotion; promotion атомарный — `os.replace` либо доказанный
  эквивалент; удаляется только temporary output.
- **required tests:** strict и draft режимы; injected failure оставляет hash
  существующего output неизменным; успешный путь заменяет output ровно один
  раз; temporary файлы не остаются после успеха и после сбоя.
- **не входит:** resume orchestration — это PLAN-STAB-2.
- **фактический результат:** `render_final_video` пишет мастер во временный
  `.<имя>.partial.mp4` в той же директории, проверяет его существующим
  `src.assets.frame_sampling.ffprobe_media_info` (тем же probe owner, через
  который повышает нарратив `src.audio.audio_assembler`) и только затем
  выполняет `os.replace`. Временный файл текущей попытки удаляется best-effort
  и не маскирует исходную ошибку. Второй renderer, второй validator, новый
  backup-механизм и правка resume/persisted contracts не создавались; public
  сигнатура и render manifest не менялись.
- **фактические проверки:** новый targeted модуль
  `tests.test_final_renderer_atomic_output` — 10 тестов, все падают на
  неизменённом HEAD `389e1c2`; targeted radius
  (`test_final_renderer_atomic_output`, `test_final_renderer_end_tail`,
  `test_news_to_short_renderer`, `test_autonomous_completion_core`) — 53 теста
  за 57.358 секунды, exit code 0; полный offline suite — 1571 тест за 326.965
  секунды, exit code 0; docs QA — exit code 0. Числа и длительности являются
  измерениями, не нормативами. Сеть, provider/model API, download, Vision, TTS
  и paid calls не выполнялись.
- **rollback / review:** по общим требованиям программы.

#### PLAN-STAB-2 — final-render resume/idempotency guard

- **status:** completed · **completed:** 2026-08-05 · **commit:** Git log —
  trailer `Plan-Step: PLAN-STAB-2` · **blocking для PLAN-9B-2:** пункт 2 gate
  satisfied — independent review выполнен, verdict ACCEPT, commit pushed;
  overall blocking gate (пункты 4–8) остаётся открытым ·
  **зависимости:** PLAN-STAB-1 (completed).
- **цель:** обычный `resume` не перезапускает уже успешно завершённый
  `final_render` без явного force/owner intent.
- **user impact:** продолжение проекта перестаёт молча переснимать готовый
  финальный ролик и тратить время пользователя.
- **canonical owner:** `src/news/pipeline.py` (stage guard ADR 0006).
- **allowed zones:** `src/news/pipeline.py`, минимально необходимый вызывающий
  canonical workflow, owning test-модули.
- **prohibited zones:** порядок стадий; состав `NEWS_TO_SHORT_STAGES`; renderer
  internals; persisted schema; новый public flag без owner approval.
- **success criteria:** characterization фиксирует текущее поведение до правки;
  completed-stage guard действует и на explicit `stage=` path; explicit force
  по-прежнему пересобирает; отсутствующий или непригодный prior output
  запускает render; ранее провалившийся output не считается completed.
- **required tests:** normal resume · force · missing output · failed prior
  output · batch-режим не регрессирует.
- **фактический результат:** `run_news_to_short_job`'s completed-stage skip
  (`src/news/pipeline.py`) применялся только когда вызывающий не указывал
  явный `stage=`; production render/export фаза
  (`FullscreenVoiceoverUseCase._render_and_export`) всегда вызывает
  `run_news_to_short_job(..., stage="final_render")` без `resume`/`force_stage`,
  поэтому каждый resume безусловно перезапускал `final_render`. Skip-условие
  расширено ровно на `stage_name == "final_render"`, не затрагивая explicit-stage
  диспетчеризацию voice/subtitles/preview_render/quality_check/export и не
  меняя `NEWS_TO_SHORT_STAGES`, persisted schema или renderer. Существующий
  `--force-stage` → `ExecutionFlags.force_stage` контракт довязан в тот же
  `stage="final_render"` вызов, поэтому явный force по-прежнему пересобирает
  именно final_render. Missing/invalid artifact продолжает обрабатываться уже
  действующим `NewsProjectStore.is_stage_completed`/`validate_stage_output`
  (ADR 0006) без нового механизма. `src/news/final_renderer.py` не менялся.
- **фактические проверки:** новый класс
  `tests.test_news_stage_idempotency.FinalRenderExplicitStageDispatchTests` —
  5 тестов (completed+valid skip, force reexecutes, missing-artifact
  reexecutes, not-yet-completed still executes, forced failure not recorded
  completed) плюс новый wiring-тест
  `test_force_stage_flows_from_request_to_the_final_render_resume_call` в
  `tests.test_content_creation_service`; targeted radius (idempotency,
  pipeline, renderer, delivery, autonomous completion, manual asset
  replacement, atomic output, end-tail, content-creation service, fullscreen
  boundary, voice adapter, subtitle integration, scene timing) — 116 тестов за
  166.565 секунды, exit code 0; полный offline suite — 1577 тестов за
  317.742 секунды, exit code 0; docs QA — exit code 0. Числа и длительности
  являются измерениями, не нормативами. Сеть, provider/model API, download,
  Vision, TTS и paid calls не выполнялись.
- **rollback / review:** по общим требованиям программы.

#### PLAN-STAB-3 — offline test guard и изоляция test credentials

- **status:** completed · **completed:** 2026-08-05 · **commit:** Git log —
  trailer `Plan-Step: PLAN-STAB-3` · **blocking для PLAN-9B-2:** пункт 3 gate
  satisfied — independent review выполнен, verdict ACCEPT WITH MINOR, commit
  pushed; overall blocking gate (пункты 4–8) остаётся открытым ·
  **зависимости:** —.
- **цель:** network guard нельзя случайно оставить выключенным на остаток test
  process, а test-injected credentials нельзя заменить значениями из `.env`.
- **user impact:** offline-обещание проекта перестаёт зависеть от порядка
  запуска модулей; реальные ключи владельца не попадают в тестовый прогон.
- **canonical owner:** `tests/network_guard.py`; для credential-пути —
  `src/audio/tts/env.py`.
- **allowed zones:** `tests/network_guard.py`, test-модули со scoped
  exception, `src/audio/tts/env.py` и его owning tests.
- **prohibited zones:** production TTS/provider поведение вне загрузки env;
  чтение `.env` и реальных ключей тестами; второй guard-механизм; расширение
  guard на subprocess boundary (остаётся открытым вопросом PLAN-6B).
- **success criteria:** characterization фиксирует фактическое число uninstall
  paths (**измерение**, на baseline 2026-08-05 — 9 вызовов в трёх test modules;
  **не инвариант и не acceptance criterion**, число перепроверяется заново перед
  implementation); после scoped exception guard восстанавливается; module
  cleanup/context-manager contract явный; `load_dotenv(..., override=True)` не
  заменяет заранее заданный test key; отсутствие `.env` не меняет результат.
- **required tests:** guard активен в модуле, выполняемом после модуля со
  scoped exception; scoped exception восстанавливает guard при исключении;
  заранее заданный `ELEVENLABS_API_KEY` переживает загрузку env.
- **фактический результат:** 9 raw `install_network_guard()`/
  `uninstall_network_guard()` call sites (baseline measurement подтверждена)
  в трёх owning test-модулях (`tests/test_localization_voice_integration.py`,
  `tests/test_news_voice_adapter.py`, `tests/test_production_catalog_foundation.py`)
  безусловно снимали process-wide baseline guard, который `tests/__init__.py`
  устанавливает один раз при импорте пакета: любой такой `finally: uninstall_
  network_guard()` отключал защиту для всех тестов, выполняющихся после него в
  том же процессе. `tests/network_guard.py` получил `network_guard_scope()`
  context manager, который восстанавливает guard к состоянию **до входа** в
  scope (успех, исключение или уже-выключенный baseline) вместо безусловного
  uninstall; все 9 call sites переведены на него. Для credential-пути
  `src/audio/tts/env.py::load_elevenlabs_env` всегда вызывал
  `load_dotenv(env_path, override=True)`, включая пути, где api_key передаётся
  явно (`ElevenLabsProvider.__init__` вызывает `load_elevenlabs_env()`
  безусловно) — реальный `.env`, если он существует, заменял бы любой
  test-owned fake `ELEVENLABS_API_KEY` в `os.environ`. Добавлен sentinel
  `TEST_CREDENTIAL_ISOLATION_ENV_VAR`; `override` теперь `not
  _test_credentials_isolated()`, а `tests/__init__.py` устанавливает sentinel и
  fake `ELEVENLABS_API_KEY` до импорта любого test-модуля. Production
  `override=True` semantics вне test isolation не менялись; `src/config_resolver`,
  providers, TTS/Vision/renderer/rights/resume не менялись.
- **фактические проверки (2026-08-05, ветка `governance-reset`):** новые
  `tests.test_test_network_guard.NetworkGuardScopeTests` (5 тестов) и
  `tests.test_tts_env_credential_isolation` (7 тестов); targeted regression —
  `test_localization_voice_integration` + `test_news_voice_adapter` +
  `test_production_catalog_foundation` (72 теста) и TTS/dotenv/provider radius
  (`test_voice_workflow`, `test_config_resolver`, `test_documentary_visual_engine`,
  `test_narration_workflow`, `test_scene_voice_generator`,
  `test_provider_foundation_hardening`, `test_content_creation_service`,
  `test_news_to_short_assets`, 145 тестов) — exit code 0; docs QA — exit code 0;
  полный offline suite — 1589 тестов (1577 + 12 новых), exit code 0. Числа и
  длительности являются измерениями, не нормативами. Сеть, provider/model API,
  download, Vision, TTS, paid calls и реальный `.env` не читались и не
  выполнялись; тесты используют только синтетические временные `.env`-файлы.
- **rollback / review:** по общим требованиям программы.

#### PLAN-STAB-4 — fail-closed runtime network/paid boundary

- **status:** completed 2026-08-06 · **independent review:** выполнен,
  verdict **ACCEPT WITH MINOR** (commit `0947e51`; GitHub Actions run
  `31053545804`, job `offline-tests / unittest` — success, `Ran 1623 tests in
  329.132s`, `OK (skipped=6)`, failures=0, errors=0) · **blocking для
  PLAN-9B-2:** пункт 4 gate satisfied; overall blocking gate (пункты 5–8)
  остаётся открытым · **зависимости:** characterization PLAN-STAB-3
  (completed).
- **non-blocking residual findings review (не исправлены этим слайсом):**
  (1) `tests/test_runtime_network_boundary.py:324-329` —
  `test_preflight_denial_is_not_reported_as_ready_for_generation` содержит
  только `assertTrue(callable(prepare_final))`, тавтологический assertion
  вместо полной проверки denial → readiness; (2) `wizard_presentation.py`
  показывает неполную информационную сводку сетевых действий и не использует
  `required_network_actions()`. Оба зафиксированы как residual evidence по
  independent review; исправление — отдельный будущий слайс, не PLAN-STAB-4 и
  не PLAN-STAB-5.
- **цель:** единый runtime owner запрещает внешние и платные вызовы в offline
  или неодобренном режиме.
- **user impact:** случайный платный или сетевой вызов перестаёт быть возможен
  «по умолчанию»; отказ честный и объяснимый.
- **canonical owner:** определяется owner audit **до** реализации; второй guard
  на провайдера не создаётся.
- **обязательный owner audit до implementation:** ElevenLabs · OpenAI/Vision ·
  stock providers · downloads · будущие model calls.
- **allowed zones:** выбранный canonical boundary и его owning tests;
  минимальные call sites перечисленных путей.
- **prohibited zones:** дублирующий guard в каждом провайдере; новый
  provider contract; изменение provider selection; реальные сетевые вызовы в
  тестах.
- **success criteria:** один canonical boundary; approval явный и на конкретное
  действие; budget/cap там, где применимо; default fail-closed; **наличие API
  key не является approval**; поведение проверяется без реальной сети.
- **required tests:** offline-режим блокирует каждый класс вызова; явное
  approval пропускает ровно один класс; отсутствие approval при настроенном
  провайдере остаётся отказом.
- **фактический canonical owner (2026-08-06):** `src/runtime_network.py` —
  один модуль, один механизм. `ContextVar` со значением `DENY_ALL` делает
  default deny свойством конструкции, а не проверкой, которую можно забыть:
  `NetworkApproval` (frozen) хранит поимённый набор классов и метку источника,
  `network_approval_scope` восстанавливает предыдущее значение через token даже
  при исключении, `require_network` вызывается до первого socket/HTTP,
  неизвестное имя класса — ошибка, а не молчаливое разрешение.
  `NetworkApproval.to_dict()` отдаёт только имена классов и `granted_by`,
  поэтому ключ или токен не может попасть в manifests и approval artifacts.
  Второй guard на провайдера не создавался: все пять сетевых провайдеров ходят
  через общий `ProviderHttpClient` и не менялись.
- **фактически закрытые network families:** `provider_search` и
  `asset_download` — `src/assets/http_client.py` (`get_json` и
  `download_stream`, проверка до `_request` и до создания `.part`, в тексте
  отказа только host без query-параметров); `preview_download` —
  `src/assets/visual_preview.py` передаёт свой класс в тот же
  `download_stream`; `article_fetch` — `src/news/article_ingestor.py` до
  `requests.get`, отказ транслируется в существующий `ArticleIngestionError`
  с `reason="network_approval_required"`, который намеренно не входит в
  `_RETRYABLE_ARTICLE_REASONS`; `voice_preflight` —
  `src/audio/tts/elevenlabs_provider.py` в `preflight` и `list_voices`, причём
  отказ в `preflight` возвращает корректный план с классифицированной ошибкой,
  поэтому `ready_for_final_generation` остаётся False и traceback не возникает.
- **как пользователь даёт разрешение:** повторяемый `--allow-network <класс>`
  (`choices` из `NETWORK_ACTIONS`, wildcard-значения нет) проходит через общий
  `request_builder` в поле `network` запроса; Wizard задаёт явный вопрос
  `confirm_network_access`, перечисляя ровно те классы, которых требует именно
  этот прогон (`required_network_actions`). Оба входа заполняют одно и то же
  поле, поэтому parity выполняется по построению, а `create_content` —
  единственное место установки scope на оба шаблона.
- **явно принятые residual risks:** OpenAI Vision (`semantic_visual_openai.py`)
  в scope не входил и остаётся под существующей защитой —
  `config/semantic_visual.json` с `enabled:false`, `backend:"mock"`,
  `openai.enabled:false`, `allow_paid_vision:false` плюс `VisionBudgetGuard` с
  обязательной фразой подтверждения и budget cap. Legacy
  `pipeline.py --provider-diagnostics --live` и `pipeline.py --voice-action
  preflight/audition` идут через закрытые границы и потому становятся
  fail-closed без собственного approval-флага: это намеренное default-deny для
  путей вне канонического workflow, а не регрессия канонического CLI.
  Платный POST ElevenLabs (`synthesize`) остаётся под существующим
  каноническим paid-owner — hash-bound `VoiceApproval` на диске плюс gates в
  `narration_workflow` и `TTSProviderManager`; отдельного network approval он
  не требует. Информационная строка «Сетевые действия» в
  `wizard_presentation.py` перечисляет не все семейства — предсуществующее
  поведение, в scope PLAN-STAB-4 не входило.
- **фактические проверки (2026-08-06, ветка `governance-reset`):** новый
  `tests/test_runtime_network_boundary.py` — 34 теста, покрывающие default deny
  для каждого класса, keyless default-on провайдеров, article ingestion до
  HTTP, preview download отдельным классом, preflight без GET при настроенном
  ключе, paid approval без network approval, разрешение ровно одного класса,
  dry-run/prepare-only/resume/force-stage offline, отсутствие secrets в
  approval artifact и CLI ↔ Wizard parity. Обновлены owning tests
  `test_asset_foundation_http_download`, `test_voice_workflow` и
  `test_content_creation_wizard` (общий `ScriptedAdapter` также используется
  `test_project_naming_and_resume`): им выдаётся явный scope нужного класса,
  существующий `tests/network_guard.py` не ослаблялся. Полный offline suite —
  1623 теста (1589 + 34), exit code 0; docs QA — exit code 0;
  `git diff --check` — exit code 0. Числа являются измерениями, не нормативами.
  Сеть, provider/model API, download, Vision, TTS, paid calls и реальный `.env`
  не читались и не выполнялись.
- **rollback / review:** по общим требованиям программы.

#### PLAN-STAB-5 — C50 rights-review preservation

- **status:** completed 2026-08-06, independently reviewed, verdict **ACCEPT**
  (findings: нет) · **blocking для PLAN-9B-2:** да — пункт 5 blocking gate
  **satisfied** · **зависимости:** —.
- **реализованный инвариант:** требование ревью monotonic. Уже записанное
  `review_required=True` — вход политики, а не то, что она вправе снять; оно
  даёт причину `record_review_required`, обнуляет `allowed_for_render` и
  переводит статус в `blocked`. Учитываются все фактически присутствующие
  представления записи (корень, `license`, сохранённый `policy_decision`);
  одного `True` достаточно, отсутствующее представление разрешением не
  является. Снимает требование только подтверждённая per-asset
  `rights_declaration` через существующий `_manual_declaration_is_confirmed`.
- **owner decision 2026-08-06 — намеренный safety trade-off.** Происхождение
  требования политика не выясняет. Evidence: сохранённая запись не позволяет
  отличить флаг оператора от прошлого ответа самой политики — комбинация
  «`review_required=True` + чужой `policy_decision`» реально производится
  `media_library._propose_media_record` (`dict(item)` сохраняет `policy_decision`,
  ставит `review_required=True`) и персистится `migrate_media_library` мимо
  `_normalize_asset`, а manifest-ассет всегда несёт `policy_decision`. Принятая
  цена: policy re-evaluation, дозаполнение metadata, resume и rebuild сами по
  себе ревью не снимают. Измерено: единственный вариант, оставлявший
  repair-and-retry, оставлял shape «оператор флагует уже заблокированный ассет»
  fail-open; полный offline suite при выбранном правиле зелёный, ни один
  существующий тест на автоматическом снятии ревью не держался.
- **owner path:** ассет с ревью выходит из блокировки одним способом —
  подтверждённой `rights_declaration`. Это существующий контракт, новых полей,
  vocabulary, CLI и Wizard-шагов слайс не добавляет.
- **цель:** явный `review_required` и owner-review evidence не теряются при
  преобразовании records/candidates и не становятся `allowed` из-за другого
  fallback.
- **user impact:** ассет, помеченный человеком на ревью, не может молча попасть
  в готовое видео. Класс `[HARD]` rights correctness.
- **canonical owner:** `apply_policy_to_candidate` / `with_policy_decision`
  в `src/assets/license_policy.py`.
- **отношение к registry:** это **исполняемый owner finding C50**. Второй
  независимый owner C50 не создаётся; нормализация ссылки в
  `CLEANUP_REGISTRY.md` относится к PLAN-STAB-17, потому что registry не входит
  в allowed zone этого docs-only amendment.
- **allowed zones:** `src/assets/license_policy.py`, минимально необходимые
  rights call sites, owning tests.
- **prohibited zones:** копирование rights gate в legacy loaders; изменение
  `modes.blocking_reasons`; PLAN-10D architectural convergence; новая persisted
  schema.
- **success criteria:** точный C50 mapping зафиксирован; canonical rights
  vocabulary используется; author/user-owned evidence сохраняется; поведение
  local library определено явно; strict и draft gates согласованы; persisted
  совместимость сохранена.
- **required tests:** negative-тесты — explicit `review_required=True` не
  становится `allowed`; отсутствие evidence не даёт fallback-разрешения;
  старые persisted записи читаются без миграции.
- **фактические изменения:** canonical owner `src/assets/license_policy.py`
  (`RECORD_REVIEW_REQUIRED_REASON`, `_record_review_required`, одна причина в
  `evaluate_asset_policy`); два merge owner на той же live-цепочке —
  `rank_local_assets` в `src/news/asset_manifest_builder.py` переносит флаг
  записи в ranked item, `with_policy_decision` в
  `src/news/asset_provider_adapters.py` не теряет флаг, записанный рядом с
  лицензией; `tests/test_rights_review_preservation.py` (23 теста);
  `src/assets/README.md`. `config/license_policy.json`,
  `modes.blocking_reasons`, `ASSET_SCHEMA_VERSION`, CLI, Wizard и network
  boundary не менялись; миграция манифестов не требуется.
- **evidence:** targeted 23 OK; regression radius 204 OK; полный offline suite
  1646 tests OK; `check_agent_docs` — 0; `check_task_scope` с 8-файловым
  allowlist — OK; `git diff --check` — 0. Сеть, provider API, download, Vision,
  TTS, реальный render и `.env` не использовались. Числа — измерения, не
  нормативы. Independent review (отдельный чат) — verdict **ACCEPT**, findings:
  нет; GitHub Actions run `31084873522`, job `offline-tests / unittest` —
  success, `Ran 1646 tests in 273.522s`, `OK (skipped=6)`, failures=0,
  errors=0; CI headSha == `8226a28`; HEAD == `origin/governance-reset`,
  worktree clean.
- **residual risks:** `rank_local_assets` остаётся вторым нормализатором рядом
  с `media_library` (C40 / PLAN-10D); `AssetLicense.from_dict` по-прежнему
  выводит `review_required` из `allowed_for_render`, когда вложенная лицензия
  его не называет — закрыто на уровне merge owner, а не персистируемой модели;
  нормализация ссылки C50 в `CLEANUP_REGISTRY.md` относится к PLAN-STAB-17.
- **rollback / review:** по общим требованиям программы.

#### PLAN-STAB-6 — Claude permission hardening

- **status:** implementation completed 2026-08-06, independent review pending ·
  findings F1–F5 отремонтированы отдельным bounded repair commit 2026-08-06,
  который сам ожидает короткого independent re-review ·
  **blocking для PLAN-9B-2:** да —
  **либо** формально принятый документированный residual risk; пункт 6 gate
  остаётся **open** до independent review · **зависимости:** —.
- **цель:** минимизировать возможность агента читать secrets, обходить
  destructive Git rules, менять governance и коммитить широким wildcard.
- **user impact:** ошибка или сбой агента не превращается в потерю работы
  владельца и незамеченное изменение правил.
- **canonical owner (A, tracked):** `.claude/settings.json`.
- **canonical owner (B, local):** `.claude/settings.local.json` — намеренно
  gitignored, поэтому его правка **manual owner action**, а не code slice.
- **allowed zones:** `.claude/settings.json`; при возможности — tracked
  permission-contract checker и его tests.
- **prohibited zones:** production-код; правка gitignored local settings от
  имени агента; утверждение, что hooks сильнее permission system.
- **success criteria:** effective merged settings проверены; wildcard-грант
  `python -c`, `python -`, `git add *`, `git commit *` удалён или вынесен в
  manual cleanup list; защищены `AGENTS.md`, `CLAUDE.md`, `skills/**`,
  `.claude/**`, `tools/qa/**`; destructive Git matching не зависит от
  необязательных флагов.
- **required tests:** checker tracked permission contract там, где выполнимо;
  иначе — записанная воспроизводимая ручная проверка.
- **manual owner prerequisite (выполнен):** владелец вручную удалил из
  gitignored `.claude/settings.local.json` семь опасных grants —
  `Bash(git add *)`, `Bash(git commit *)`, `Bash(python -c ' *)`,
  `Bash(./venv/Scripts/python.exe -c ' *)`,
  `Bash(./venv/Scripts/python.exe -B -c ' *)`,
  `Bash(G:/Projects/AI-YouTube/venv/Scripts/python.exe -B -c ' *)`,
  `Bash(python -)`. Read-only precheck перед слайсом подтвердил **0**
  совпадений по всем семи; файл целиком не читался и не выводился. Агент
  local settings не правил — это canonical owner B и manual owner action.
- **выполнено (implementation 2026-08-06):**
  - **Versioned contract.** `.claude/settings.json` остаётся deny/ask-only:
    `permissions.allow` отсутствует полностью, top-level ключи — только
    `$schema` и `permissions`, поэтому secret values в versioned файл
    структурно не помещаются.
  - **Protected governance zones** требуют подтверждения на `Edit` и `Write`:
    `AGENTS.md`, `CLAUDE.md`, `skills/**`, `tools/qa/**`,
    `.github/workflows/**`, `docs/current/PROJECT_EXECUTION_PLAN.md`,
    `docs/archive/**`, `docs/handoff/**` и сам `.claude/settings.json`.
    `Read` не ограничивается: агент, который не может прочитать `AGENTS.md`,
    не может ему следовать. Широкое правило на `docs/current/**`
    намеренно не добавлено — обычные docs-only слайсы должны оставаться
    рабочими, а подтверждение на каждый current document кликалось бы не
    глядя и контролем не является.
  - **Project-local settings** закрыты агенту: `Read`, `Write` и `Edit` по
    `./.claude/settings.local.json` — в `deny`.
  - **Secret `.env.*`.** Добавлены точные имена `.env.local`,
    `.env.development(.local)`, `.env.production(.local)`,
    `.env.staging(.local)`, `.env.test(.local)`, `.env.bak`, `.env.backup`,
    `.env.old`, `.env.save` для Read/Write/Edit в корне и рекурсивно.
    Общий `./.env.*` **не** используется: механизма исключения в deny нет, а
    tracked `.env.example` — secret-free template, для которого PLAN-6D-1
    зафиксировал «0 deny matches». Owner decision 2026-08-06 сохранил это
    свойство; checker отдельно отвергает и blanket-pattern, и любое правило,
    накрывающее `.env.example`.
  - **Destructive Git разделён** (owner decision 2026-08-06). `deny` —
    необратимая порча работы владельца или истории: `reset --hard`, `clean`,
    force push, `filter-branch`, `reflog delete/expire`, `update-ref -d`,
    `gc --prune`. `ask` — восстановимое через index/reflog либо нужное самому
    владельцу: `checkout --`, `restore`, `rm`, `branch -D`,
    `worktree remove`. Цена ask-варианта записана честно: одного
    подтверждения достаточно, чтобы стереть незакоммиченную работу.
  - **Leading wildcard удалён — с осознанным ослаблением корзины.** Правило
    `Bash(*media-library migrate*--apply*)` находилось в **`deny`**; шесть
    заменяющих entrypoint prefixes `pipeline.py` находятся в **`ask`**
    (positional `media-library` → `migrate`; флаг `--apply` объявлен в
    `src/legacy_pipeline/cli.py:116`). Это намеренная смена
    `deny` → owner confirmation: прежнее правило опиралось на ведущий `*`,
    чья matcher semantics не установлена, поэтому оно давало запрет, на
    который нельзя было положиться; новое даёт подтверждение, на форму
    которого положиться можно. Эквивалентности здесь нет — одного
    подтверждения теперь достаточно.
    **Покрытие ограничено перечисленными формами.** Шесть prefixes — это
    `python`, `python -B`, `./venv/Scripts/python.exe`,
    `./venv/Scripts/python.exe -B`, `venv/Scripts/python.exe`,
    `venv/Scripts/python.exe -B`. Абсолютные пути (например
    `G:/Projects/AI-YouTube/venv/Scripts/python.exe`), backslash-написание
    `.\venv\Scripts\python.exe`, shell aliases, обёртки и произвольный
    интерпретатор **не покрываются вовсе** — это частный случай общего
    «Bash не защищён path-based правилами» ниже. Полное покрытие не
    заявляется, и media-library rules этим repair не менялись: изменение
    правил потребует нового evidence.
    **Фактическая защита `--apply` лежит в runtime-контракте, а не в
    permissions:** `src/media_library.py:289` бросает `PermissionError` без
    `confirm_apply=True`, а `:291` требует явные `output_path` и
    `backup_path`; CLI-флаг `--confirm-apply` объявлен в
    `src/legacy_pipeline/cli.py:121`. Именно он, а не permission rule,
    остаётся барьером для любого написания команды.
    Checker отвергает любое правило с ведущим `*`.
  - **Сеть и установка пакетов** переведены в `ask`: `curl`, `wget`,
    `Invoke-WebRequest`, `pip install`, `python -m pip install`, venv-форма,
    `npm install`, `npm ci`. `WebFetch`/`WebSearch` остаются `ask`. Локальные
    offline test-команды не затронуты.
  - **Recursive delete** дополнен `rm -fr`, `Remove-Item -Force -Recurse` и
    `Remove-Item -Recurse -Force`. `Bash(*)` и общий запрет shell не
    добавлялись.
  - **Validator.** `validate_claude_permissions` в
    `tools/qa/check_agent_docs.py` — тот же canonical owner, второй QA
    framework и отдельный executable checker не создавались. Существующий CI
    step `python -B -m tools.qa.check_agent_docs` покрывает контракт без
    второго workflow и второго step. Checker read-only, offline,
    детерминирован, **никогда не открывает** `settings.local.json` и смотрит
    только его Git-статус.
- **выполнено (repair 2026-08-06, findings F1–F5 independent review):**
  - **F1 — `.env.example` защищён позиционно, а не списком написаний.**
    Прежний checker отвергал только два перечисленных blanket-паттерна, из-за
    чего `Read(./.env*)` проходил и перекрывал tracked template. Теперь
    отвергается **любое** `Read`/`Write`/`Edit` deny-правило, которое по
    собственной консервативной модели checker'а может дотянуться до
    `.env.example` в корне или во вложенной директории. Модель описана честно:
    `**` пересекает `/`, `*` и `?` — нет; это **repository contract, а не
    доказательство runtime matcher'а**, и она намеренно щедра к тому, что
    правило «может» задеть. На реальном deny-списке — ноль false positives.
  - **F2 — media-library описан честно** (см. выше): корзина сменилась
    `deny` → `ask`, покрытие ограничено шестью написаниями, фактический
    барьер `--apply` — runtime `confirm_apply` contract. Правила не менялись.
  - **F3 — tracked governance под `.claude/`.** Добавлены
    `Edit`/`Write(./.claude/agents/**)`; вместе с существующим exact
    `./.claude/settings.json` это покрывает оба tracked-файла, включая
    reviewer adapter `.claude/agents/review-change.md`, который прежде
    оставался без подтверждения. Широкое `./.claude/**` **намеренно не
    использовано**: precedence между ним и exact deny на
    `settings.local.json` не доказан, а изобретать гарантию запрещено.
    Checker берёт список из `git ls-files -- .claude/`, поэтому новый tracked
    файл без правила — ошибка; `CLAUDE_GOVERNANCE_EXEMPT_PATHS` пуст и служит
    механизмом явного, обозреваемого исключения. Gitignored
    `settings.local.json` в `ls-files` не попадает, поэтому конфликта с его
    exact deny не возникает. `Read` остаётся открытым.
  - **F4 — минимальный контракт зафиксирован независимо.** Новый класс
    `MinimumContractPinnedIndependentlyTests` перечисляет **литерально** и
    **не импортирует** `PROTECTED_GOVERNANCE_PATHS`, `SECRET_ENV_NAMES`,
    `DESTRUCTIVE_GIT_DENY`, `DESTRUCTIVE_GIT_ASK`, `FORBIDDEN_BROAD_GRANTS`:
    десять protected zones × `Edit`/`Write`, требование к tracked
    `.claude/**`, точные sensitive `.env`-имена, оба destructive-Git набора,
    восемь forbidden grants, отсутствие `permissions.allow` и точные записи
    tracked `.gitignore`. Прежде одновременное удаление зоны из
    `settings.json` **и** из константы оставляло suite зелёным.
  - **F5 — источник ignore-правила теперь обязателен.** Checker требует, чтобы
    исключение находилось именно в **tracked `.gitignore`**: `.gitignore`
    обязан быть tracked, а источник, который Git приписывает исключению,
    обязан быть tracked `.gitignore`. `.git/info/exclude`, global
    `core.excludesFile` и user-level ignore доказательством больше не
    считаются — все они per-machine и оставляют CI и остальные клоны
    незащищёнными. `-c core.excludesFile=` сохранён; `--verbose --no-index`
    даёт источник, а строка-негация (`!.env.example`) намеренно **не**
    читается как исключение. Диагностика прямо называет требование tracked
    `.gitignore`.
  - **Sensitive `.env` в tracked `.gitignore`.** Добавлены тринадцать точных
    имён (`.env.local`, `.env.development(.local)`, `.env.production(.local)`,
    `.env.staging(.local)`, `.env.test(.local)`, `.env.bak`, `.env.backup`,
    `.env.old`, `.env.save`); существующий `.env` сохранён, общий `.env.*`
    не используется, `.env.example` остаётся tracked и не ignored. Checker
    проверяет каждое имя поимённо и отдельно требует, чтобы template не был
    ignored. Реальных secret-файлов не создавалось.
- **evidence:** `tests/test_claude_permission_contract.py` (47 tests OK):
  валидный контракт; отсутствие файла; malformed JSON; появившийся
  `permissions.allow`; каждый из восьми запрещённых broad grants; ведущий
  wildcard; правило не формы `Tool(pattern)`; каждая из десяти protected zones
  × `Edit`/`Write` по отдельности; покрытие zone через `deny` вместо `ask`;
  каждый tool local-settings deny; пропавшее env-правило; семь написаний
  deny-правила, дотягивающегося до `.env.example`; отсутствие false positive
  на реальных sensitive-правилах; перенос каждого destructive-Git правила
  между корзинами; непересечение двух Git-наборов; синтетический Git-репозиторий
  (tracked `.gitignore` / untracked `.gitignore` / отсутствующее правило /
  `.git/info/exclude` / global `excludesFile` / пропавшее env-имя / ignored
  template / негация / tracked local settings); tracked governance под
  `.claude/` (без подтверждения / с подтверждением / новый tracked файл /
  local settings не считается tracked governance); независимый литеральный
  минимум контракта; реальный репозиторий; неизменность worktree. Отдельно
  зафиксировано, что env-покрытие требует только Read/Write/Edit и ни одного
  `Bash(...)` правила — полная Bash-защита не заявляется.
  **Test effectiveness против pre-repair версии:** девять новых тестов
  прогнаны против модуля из `3cedff10` — каждый падает; литеральный минимум
  F4 отдельно отвергает сужение, сделанное одновременно в `settings.json` и в
  константе.
- **residual limitations (не закрыты этим слайсом):**
  - точная matcher wildcard semantics и precedence корзин эмпирически не
    доказаны; path-правила в `ask` — inference по грамматике файла, а не
    проверенное runtime-поведение. **Наблюдение слайса:** после записи новых
    `ask`-правил в той же сессии выполнялись `Edit` по `tools/qa/**` и по
    самому execution plan, и подтверждение не запрашивалось. Причина не
    установлена: settings, вероятно, читаются на старте сессии и mid-session
    не перечитываются, но вариант «path-правила в `ask` не применяются» этим
    наблюдением не исключён. Проверка требует нового сеанса и в этом слайсе
    не выполнялась — заявлять срабатывание правил нельзя. Versioned `allow`
    отсутствует, а local settings не содержат ни одного `Write`/`Edit`
    гранта, поэтому эти правила сегодня работают как declared intent и защита
    от будущего широкого local allow, а не как единственный барьер;
  - **Bash не защищён** path-based правилами: глобальные Git options
    (`git -c …`), shell aliases и произвольный интерпретатор остаются вне
    контракта. Абсолютная защита Bash не заявляется;
  - перечисление `.env.*` заведомо неполно: имя вне списка не покрыто. Маски
    внутри имени файла (`./.env.*.local`) не использованы — их синтаксис по
    фактическим settings не подтверждён, а изобретать его запрещено;
  - effective merged user/managed/local configuration лежит вне репозитория,
    различается по средам и **защищённой не объявляется**; checker проверяет
    только versioned contract;
  - модель паттернов checker'а (`_permission_pattern_regex`) — **repository
    contract, а не runtime proof**: она описывает, какие правила репозиторий
    считает опасными, и не утверждает, что Claude matcher разбирает их так же;
  - **CI для `3cedff10` зелёным не подтверждён.** GitHub Actions run
    `31123722270` дважды отменён до выдачи `windows-latest` runner (0 steps,
    0 логов, ~15 минут очереди на попытку); ни один из двух обязательных
    шагов не выполнялся, поэтому `failures`/`errors` не существуют. Это
    инфраструктурный residual risk, а **не** падение commit. Локальное
    evidence на том же дереве: full offline suite `Ran 1729 tests, OK` и
    `tools.qa.check_agent_docs` exit 0. Owner decision 2026-08-06 разрешил
    начать repair на этом основании; заявлять CI success для `3cedff10`
    запрещено.
- **rollback / review:** по общим требованиям программы. Ни implementation, ни
  repair шаг не закрывают: пункт 6 blocking gate остаётся open до короткого
  independent re-review repair commit.

#### PLAN-STAB-7 — current-routing и reference integrity

- **status:** completed 2026-08-06 — implementation commit `42fa741`
  (совместный слайс с PLAN-STAB-8, trailer `Plan-Step: PLAN-STAB-7`), repair
  commit `8357402` закрыл все четыре finding F1-F4 независимого review без
  изменения контракта. Independent review verdict **ACCEPT WITH MINOR**,
  repair re-review verdict **ACCEPT WITH MINOR** (blocking findings: 0);
  GitHub Actions run `31101208366` (headSha `42fa741`) — offline suite
  зелёный (1693 tests OK); repair GitHub Actions run `31110155685` (headSha
  `8357402`) — offline suite зелёный (1702 tests OK); commits pushed. Factual
  routing repair в current docs был выполнен ранее слайсом PLAN-STAB-0 ·
  **blocking для PLAN-9B-2:** да — **satisfied**, пункт 7 blocking gate
  закрыт · **зависимости:** —.
- **цель:** current checkpoint, next action, mirrors и referenced IDs не могут
  молча разойтись.
- **user impact:** новый чат или агент получает ровно одно текущее задание, а
  не три конкурирующих.
- **canonical owner:** `tools/qa/check_agent_docs.py` (расширение существующего
  checker; второй QA framework не создаётся).
- **allowed zones:** `tools/qa/check_agent_docs.py`, его owning tests,
  `docs/current/` для checkpoint/evidence.
- **prohibited zones:** переписывание historical evidence и completed records;
  второй plan; изменение production-кода.
- **success criteria:** ровно один authoritative current checkpoint;
  `START_HERE.md`, `CURRENT_STATE.md`, `SYSTEM_MAP.md` и план согласованы;
  completed шаг не выглядит pending/current; PLAN- и registry-ссылки
  разрешаются; bullet-only слайс не может быть current checkpoint без
  собственного heading.
- **required tests:** duplicate/stale checkpoint statement — error; ссылка на
  несуществующий PLAN-ID — error; heading-less current checkpoint — error.
- **выполнено:** `validate_routing` в `tools/qa/check_agent_docs.py`.
  Authority — `current_checkpoint` в frontmatter активного плана. Проверяется:
  checkpoint имеет **собственный heading** (bullet-only шаг checkpoint быть не
  может); его `- **status:**` не начинается со слова `completed`;
  `next_exact_action` называет текущий checkpoint и ссылается только на
  определённые plan steps; каждый из трёх routing mirrors
  (`START_HERE.md`, `CURRENT_STATE.md`, `SYSTEM_MAP.md`) содержит хотя бы одно
  checkpoint-утверждение и ни одно из них не называет другой PLAN-ID.
  Сообщение об ошибке называет файл, строку, найденный и ожидаемый ID.
- **осознанная граница:** reference integrity ограничена routing-полями.
  Сплошная проверка «каждая PLAN-ID-ссылка имеет heading» дала бы ~33 ложных
  срабатывания: сабы вида `PLAN-12A…PLAN-14F` определяются жирными буллитами
  внутри родительских разделов, а `PLAN-ID` — обычное слово прозы. Для
  `next_exact_action` принимаются оба вида определений, для самого checkpoint —
  только heading.
- **evidence:** `tests/test_docs_routing_and_freshness.py`, класс
  `RoutingTests` (валидный route; heading-less checkpoint; расхождение каждого
  из трёх mirrors по отдельности; mirror без checkpoint-утверждения;
  `next_exact_action` на несуществующий шаг; `next_exact_action` без текущего
  checkpoint; completed шаг как checkpoint; pending-статус, лишь упоминающий
  слово completed, не считается completed) и `RepositoryRoutingAndFreshnessTests`
  на реальном репозитории.
- **rollback / review:** по общим требованиям программы.

#### PLAN-STAB-8 — Git-aware documentation freshness

- **status:** closed 2026-08-06 (тот же совместный commit, что и PLAN-STAB-7,
  `42fa741`, и та же repair commit `8357402`; собственного отдельного commit у
  слайса нет по решению владельца об одном координированном bounded slice).
  Independent review этого commit выполнен вместе с PLAN-STAB-7: verdict
  **ACCEPT WITH MINOR**, repair re-review verdict **ACCEPT WITH MINOR**
  (blocking findings: 0); GitHub Actions run `31101208366` и repair run
  `31110155685` зелёные · **blocking для PLAN-9B-2:** нет · **зависимости:** —.
- **цель:** документ считается current по проверенному Git baseline и
  изменениям в релевантных source paths, а не по декоративному hex string.
- **user impact:** «свежая» метка перестаёт скрывать документ, разошедшийся с
  кодом.
- **canonical owner:** `tools/qa/check_agent_docs.py`.
- **отношение к PLAN-6A:** PLAN-6A остаётся owner расширения `CURRENT_DOCS` и
  governance-правил docs QA; PLAN-STAB-8 отвечает только за семантику
  freshness. Дублирующего checker не создаётся; при пересечении зон слайсы
  выполняются последовательно, а не параллельно.
- **allowed zones:** `tools/qa/check_agent_docs.py`, его owning tests,
  синтетические Git-фикстуры.
- **prohibited zones:** автоматическое обновление metadata без content review;
  массовая правка `last_verified_*` в документах; production-код.
- **success criteria:** semantics baseline self-reference-safe (N−1 либо
  доказанный эквивалент); используется `merge-base --is-ancestor`;
  учитываются изменения в объявленных `source_paths` после baseline; calendar
  age остаётся advisory; coverage расширен на фактические current authority
  docs; design contract фиксируется до реализации.
- **required tests:** синтетические Git-репозитории (ancestor / не-ancestor /
  изменения после baseline / без изменений); один вызов на реальном репозитории.
- **выполнено:** `validate_freshness` в `tools/qa/check_agent_docs.py`.
  Coverage — все пять фактических commit-полей current authority docs:
  `last_verified_commit` в `START_HERE.md`, `SYSTEM_MAP.md`,
  `CURRENT_STATE.md`, `CLEANUP_REGISTRY.md` и `baseline_head` в самом плане.
  Каждое значение обязано быть настоящим commit (`git cat-file -e`) и
  ancestor HEAD (`git merge-base --is-ancestor`). Три класса ошибок разделены:
  некорректная форма, несуществующий commit, commit вне истории HEAD. Сеть и
  GitHub API не используются.
- **N−1 semantics:** контракт — «ancestor HEAD», а не «равно HEAD». Документ
  не может содержать hash того commit, который его записывает, поэтому
  требование равенства было бы невыполнимо по построению.
- **source_paths drift — advisory, не error.** Печатается как `NOTE:` и не
  меняет exit code. Обоснование фактическое, а не стилистическое: с `9f3ddba`
  до HEAD изменился 101 файл из объявленных `source_paths` трёх current docs,
  а всего по репозиторию за тот же интервал — 125 файлов;
  hard error потребовал бы массовой правки `last_verified_*`, которая прямо
  входит в prohibited zones этого слайса.
- **calendar age:** отсчитывается от даты HEAD commit, а не от системных
  часов. Раньше wall clock делал бы дерево красным без единого изменения в
  репозитории, из-за чего оба owning tests замораживали `today=2026-07-29`;
  эти frozen constants удалены, tests и CI теперь проходят один и тот же путь.
- **fail-closed:** отсутствие читаемого Git-репозитория и shallow clone —
  ошибки, а не тихий пропуск. Поэтому `.github/workflows/offline-tests.yml`
  получил `fetch-depth: 0` в существующем `actions/checkout@v4` (owner
  decision 2026-08-06); второй workflow и второй checkout step не создавались.
- **evidence:** `tests/test_docs_routing_and_freshness.py`, класс
  `FreshnessTests` на синтетических локальных Git-репозиториях (ancestor;
  несуществующий commit; malformed commit отдельным сообщением; commit на
  побочной ветке; drift как advisory; отсутствие drift; каталог без `.git`;
  shallow clone через `git clone --depth=1`) и `RepositoryRoutingAndFreshnessTests`
  на реальном репозитории, включая проверку, что checker не трогает worktree.
- **rollback / review:** по общим требованиям программы.

#### PLAN-STAB-9 — shared rights vocabulary owner

- **status:** completed 2026-08-06 (commit `ed4604d`, единственный commit
  слайса, trailer `Plan-Step: PLAN-STAB-9`) · independent review выполнен,
  verdict **ACCEPT WITH MINOR** (blocking findings: нет; один non-blocking
  finding — wording overclaim, исправлен этим docs-only closure слайсом, см.
  «minor finding» ниже); GitHub Actions reviewed headSha `ed4604d` — offline
  suite зелёный, failures=0, errors=0, HEAD == `origin/governance-reset`,
  worktree clean · **blocking для PLAN-9B-2:** нет · **зависимости:**
  PLAN-STAB-5.
- **выполнено:** canonical owner — `src/assets/models.py`. Он объявляет семь
  именованных `RIGHTS_*` и immutable `RIGHTS_ALLOWED_STATUSES`
  (`frozenset`: `user_owned`, `licensed`, `creative_commons`, `public_domain`).
  Удалена независимая копия того же списка — mutable set
  `ALLOWED_RENDER_RIGHTS` в `src/news/models.py` вместе с локальными
  объявлениями `RIGHTS_*`; значения до слайса совпадали, но гарантии этого не
  было. Consumers `src/news/asset_manifest_builder.py` и
  `src/news/asset_provider_adapters.py` переведены на прямой импорт из
  canonical owner. `completion/modes.py` сохраняет единственное санкционированное
  расширение `cleared`, теперь именованное `RIGHTS_LEGACY_CLEARED` в самом owner
  и намеренно не входящее в canonical набор.
- **обратная совместимость:** import paths `src.news.models` сохранены целиком —
  все семь исторических `RIGHTS_*` и `ALLOWED_RENDER_RIGHTS` остаются
  импортируемыми оттуда как compatibility re-exports; alias — тот же объект,
  что и canonical `frozenset`, а не равная копия. Ни один существующий importer
  не менялся; `tests/test_news_to_short_models.py` не правился и служит
  регрессией на re-export.
- **подтверждённый invariant:** словарь задаёт написание статуса и разрешением
  сам по себе не является. Неизвестный, пустой и отсутствующий status
  fail-closed; `review_required=True` и `allowed_for_render=False` блокируют
  canonical status; подтверждённая `rights_declaration` не разрешает структурно
  неполный asset; PLAN-STAB-5 monotonic review сохранён; round-trip не меняет
  значение статуса; legacy manifest читается и остаётся fail-closed.
- **evidence:** новый owning-модуль `tests/test_rights_status_vocabulary.py`
  (21 test OK), включая divergence-защиту как комбинацию проверок: identity
  alias canonical object, compatibility alias tests для каждого re-export,
  AST-проверка исходника `src/news/models.py` на отсутствие независимого
  vocabulary literal (второго set/frozenset словаря) и runtime tests
  существующих consumers (`asset_manifest_builder.py`,
  `asset_provider_adapters.py`). Именно эта комбинация предотвращает
  расхождение словаря; ни один отдельный AST guard не заявляется как
  самостоятельно ловящий все формы независимого возврата копии. Regression
  radius 257 OK; полный offline suite — см. запись в `CURRENT_STATE.md`;
  docs QA 0; scope-check OK; `git diff --check` 0. Сеть, provider API,
  download, Vision, TTS и реальный render не использовались.
- **minor finding (independent review, non-blocking) и его исправление:**
  формулировки в этом плане и в `CURRENT_STATE.md` преувеличивали покрытие
  divergence guard, утверждая, что один AST guard самостоятельно ловит все
  формы возврата независимой копии словаря. Исправлено этим docs-only closure
  слайсом: расхождение словаря предотвращает именно комбинация
  identity-проверок canonical object, compatibility alias tests, AST-проверки
  отсутствия независимого vocabulary literal и runtime tests consumers — не
  один изолированный AST guard.
- **не менялось:** `config/license_policy.json`, schema version, persisted
  поля, CLI, Wizard, provider APIs, network boundary; миграция манифестов не
  требуется; словарь не расширялся.
- **residual risks (не исправлялись):** (1) `completion/modes.py` приводит вход
  к lower-case, а `news`-consumers и `AssetLicense` сравнивают строку как есть —
  расхождение нормализации, на живых данных не проявляется, так как все
  производители пишут lower-case; унификация была бы семантическим изменением
  gate; (2) `AssetLicense.from_dict` / `AssetCandidate.from_dict` не переносят
  корневой `review_required` во вложенную лицензию — вне contract этого слайса,
  живой render-gate читает сырой dict и корневой флаг видит; (3)
  `ALLOWED_RENDER_RIGHTS` остаётся compatibility alias без собственного
  retirement gate — его retirement отдельное решение; (4)
  `RIGHTS_EDITORIAL_REVIEW_REQUIRED` и `RIGHTS_BLOCKED` импортёров не имеют и
  перенесены как есть.
- **цель:** убрать независимые списки допустимых rights statuses у выживающих
  production-модулей.
- **user impact:** rights-решение одинаково во всех точках, где его видит
  пользователь.
- **canonical owner:** `src/assets/models.py` — выбран caller audit слайса и
  подтверждён: у модуля нет ни одного импорта из `src`, поэтому цикл
  `src.news` → `src.assets` → `completion/replacement` невозможен.
- **allowed zones:** выбранный owner, его consumers, owning tests.
- **prohibited zones:** legacy-модули под retirement PLAN-L; новая persisted
  schema; расширение словаря без отдельного решения.
- **success criteria:** один canonical список; намеренные расширения
  документированы отдельно; persisted reader остаётся tolerant; дублирующих
  строковых списков нет.
- **required tests:** divergence-тест — расхождение словарей падает.
- **rollback / review:** по общим требованиям программы; independent review
  выполнен в отдельном контексте, verdict ACCEPT WITH MINOR (см. status выше).

#### PLAN-STAB-10 — canonical timestamp formats

- **status:** pending / not started · **blocking для PLAN-9B-2:** нет ·
  **зависимости:** —.
- **цель:** именованные timestamp contracts вместо нескольких `utc_now_iso`
  с разной точностью.
- **user impact:** сортировка и сравнение записей проекта перестают зависеть от
  того, какой модуль их записал.
- **canonical owner:** один существующий helpers-модуль, выбирается caller
  audit.
- **allowed zones:** выбранный owner и модули с дублирующими helpers, owning
  tests.
- **prohibited zones:** миграция persisted данных без отдельного owner
  approval; новый формат в persisted полях без tolerant reader.
- **success criteria:** различены instant/timestamp и date-only project
  naming; сохранена persisted совместимость; явно решено, где нужен lexical
  sort, а где parsed datetime; миграция не требуется, если tolerant readers
  достаточно.
- **required tests:** round-trip старых записей обоих форматов; стабильность
  сортировки.
- **rollback / review:** по общим требованиям программы.

#### PLAN-STAB-11 — channel manifest convergence

- **status:** pending / not started · **blocking для PLAN-9B-2:** нет ·
  **зависимости:** —.
- **цель:** `channel.json` и `channel_config.json` не образуют два
  несовместимых current contracts.
- **user impact:** канал без «правильного» файла перестаёт молча терять
  настройки голоса и workflow.
- **canonical owner:** `src/config_resolver/layers.py` совместно с фактическим
  reader `src/news/pipeline.py`.
- **allowed zones:** названные readers, `src/channel_loader.py`, owning tests.
- **prohibited zones:** удаление или переписывание существующих
  `channels/**` без отдельного owner approval; второй registry каналов.
- **success criteria:** owner/caller inventory зафиксирован; canonical формат
  выбран; определена compatibility/migration strategy; все существующие каналы
  читаются; молчаливый `{}` fallback заменён честным диагностируемым
  состоянием.
- **required tests:** по одному тесту на каждое существующее семейство каналов;
  отсутствующий и нечитаемый файл дают явный результат, а не пустой конфиг.
- **rollback / review:** по общим требованиям программы.

#### PLAN-STAB-12 — scene-duration owner enforcement

- **status:** pending / not started · **blocking для PLAN-9B-2:** нет ·
  **зависимости:** —.
- **цель:** все живые readers используют общий `scene_timeline` contract либо
  доказанно адаптируются через одного owner.
- **user impact:** длительность сцены в рендере, отчётах и субтитрах перестаёт
  расходиться.
- **canonical owner:** `src/audio/scene_timeline.py`.
- **allowed zones:** `src/audio/scene_timeline.py`, `src/news/final_renderer.py`,
  reports/completion readers, legacy format adapter, owning tests.
- **prohibited zones:** изменение persisted полей длительности; новый timeline
  owner; изменение render layout.
- **success criteria:** final renderer, отчёты и legacy adapter согласованы по
  floor/fallback semantics; фактическая длительность озвучки по-прежнему
  выигрывает у плановой; persisted совместимость сохранена.
- **required tests:** timeline parity — один и тот же проект даёт одинаковые
  длительности у всех readers.
- **rollback / review:** по общим требованиям программы.

#### PLAN-STAB-13 — workspace/media-library resolution

- **status:** pending / not started · **blocking для PLAN-9B-2:** нет ·
  **зависимости:** —.
- **цель:** `--workspace` и настроенные пути определяют один и тот же
  media-library owner.
- **user impact:** выбранный пользователем workspace действительно используется,
  а не подменяется корнем checkout.
- **canonical owner:** `src/config_resolver/paths.py` (`WorkspacePaths`) как
  источник корня; `src/media_library.py` — consumer.
- **отношение к registry:** связано с существующим C29 (`outputs/` артефакт
  того же модуля). Конкурирующий owner не создаётся; C29 остаётся за PLAN-L4.
- **allowed zones:** `src/media_library.py`, его callers
  (`src/news/asset_manifest_builder.py`, `src/providers/local_library_provider.py`,
  `src/news/asset_provider_adapters.py`, `src/news/asset_manager.py`), owning tests.
- **prohibited zones:** физический перенос runtime/медиа; изменение
  `media_index.json` layout; удаление legacy fallback без отдельного gate.
- **success criteria:** на каноническом CLI-пути нет hardcode корня checkout;
  Local Library provider и `media_index` разрешаются от одного корня;
  определена migration/compatibility strategy; legacy default сохранён.
- **required tests:** прогон с non-default workspace находит библиотеку там,
  где её объявил пользователь; default workspace не регрессирует.
- **rollback / review:** по общим требованиям программы.

#### PLAN-STAB-14 — persisted schema round-trip protection

- **status:** pending / not started · **blocking для PLAN-9B-2:** нет ·
  **зависимости:** —.
- **цель:** unknown persisted keys и старые формы не уничтожаются молча при
  read-modify-write.
- **user impact:** проект, записанный более новой или более старой версией, не
  теряет данные при обычном продолжении работы.
- **canonical owner:** `src/news/models.py` и `src/news/project_store.py`.
- **allowed zones:** названные модули, реальные старые фикстуры, owning tests.
- **prohibited zones:** превращение всех schemas в runtime validation без
  отдельного impact audit; массовая миграция persisted данных.
- **success criteria:** используются **реальные старые** фикстуры; отношение
  schema ↔ runtime зафиксировано; readers остаются tolerant; решение о
  сохранении unknown keys принято явно и записано; вложенные state-объекты не
  падают на незнакомом ключе.
- **required tests:** round-trip старого `job.json` не теряет поля;
  рукописный current payload полноценной legacy-фикстурой не считается.
- **rollback / review:** по общим требованиям программы.

#### PLAN-STAB-15 — concurrent project execution guard

- **status:** pending / not started · **blocking для PLAN-9B-2:** нет ·
  **зависимости:** PLAN-STAB-2.
- **цель:** два `resume`/`render` одного проекта не могут одновременно писать
  одни артефакты.
- **user impact:** случайный второй запуск не портит проект и не смешивает два
  результата.
- **canonical owner:** `src/project_foundation/storage.py` (`project_lock`).
- **allowed zones:** названный owner, точки входа выполнения проекта, owning
  tests.
- **prohibited zones:** новый lock-механизм рядом с существующим; блокировка
  read-only status-операций; изменение layout проекта.
- **success criteria:** определён lock scope уровня выполнения, а не одной
  записи; есть ownership token; есть heartbeat либо обоснованный timeout;
  длительность render заведомо больше stale threshold учтена; crash recovery
  определён; read-only операции не блокируются.
- **required tests:** параллельный запуск — второй получает честный отказ;
  brutal-kill владельца освобождает проект по определённому правилу.
- **rollback / review:** по общим требованиям программы.

#### PLAN-STAB-16 — CI и static controls baseline

- **status:** **partially completed** — первый milestone success criteria
  закрыт, остальные подпункты pending · **blocking для PLAN-9B-2:** нет ·
  **зависимости:** OD-S-5 (remote backup выполнен — satisfied).
- **цель:** после появления remote включить реальные repository checks.
- **user impact:** регрессия ловится до того, как владелец увидит её на своём
  проекте.
- **canonical owner:** существующий `.github/workflows/offline-tests.yml`;
  второй workflow того же назначения не создаётся.
- **allowed zones:** `.github/workflows/**` и минимально необходимые config
  files.
- **prohibited zones:** массовое переформатирование; немедленный глобальный
  strict typing; required status check до доказанного зелёного прогона.
- **success criteria:** поэтапное внедрение — существующий offline suite
  фактически зелёный в GitHub Actions → secret scan → dependency audit → lint
  baseline → type-check baseline; branch status check включается последним.
- **required tests:** сам workflow является проверкой; локально —
  синтаксическая валидация и один зелёный прогон.
- **фактический результат (CI repair, 2026-08-05):** четыре bounded commits —
  `9f9b6f2` (pinned ffprobe на Windows runner), `bcf6c2a` (path identity
  long/8.3 form на windows-latest), `8ca755f` (bundled DejaVu Sans для
  детерминированных story-card text metrics), `68acdb2` (synthetic source
  video вместо personal-machine fixture) — закрыли первый пункт success
  criteria: existing offline suite фактически зелёный в GitHub Actions. Работа
  выполнена по прямому owner decision как срочный bounded end-to-end repair;
  исходный scope был расширен владельцем после появления новых подтверждённых
  CI failures — это authorized расширение, не самовольное. Готовые видео,
  пользовательские проекты, downloaded assets и project outputs в Git не
  добавлялись. Второй workflow, secret scan, dependency audit, lint baseline,
  type-check baseline и required status check этим слайсом не создавались и
  остаются pending/non-blocking.
- **фактические проверки:** GitHub Actions run `31039985187`,
  `offline-tests / unittest` — success, 1/1 checks, failures=0, errors=0;
  локальный полный offline suite на `68acdb2` — 1589 тестов, OK. Числа
  являются измерениями, не нормативами.
- **rollback / review:** по общим требованиям программы.

#### PLAN-STAB-17 — cleanup registry и retirement ledger integrity

- **status:** pending / not started · **blocking для PLAN-9B-2:** нет ·
  **зависимости:** —.
- **цель:** registry однозначно определяет status, owner, impact, exit
  condition и фактическое завершение retirement.
- **user impact:** косвенный — решения о удалении принимаются по достоверной
  записи, а не по памяти.
- **canonical owner:** `docs/current/CLEANUP_REGISTRY.md`.
- **allowed zones:** `docs/current/CLEANUP_REGISTRY.md`.
- **prohibited zones:** переписывание historical evidence; изобретение
  несуществующих PLAN-ID; production-код.
- **success criteria:** завершённые D-слайсы отражены в retired ledger; все
  ссылки разрешаются (включая ссылку C50 → PLAN-STAB-5 и C29 → PLAN-L4);
  минимальный набор полей нормализован; принятая история сохранена.
- **required tests:** docs QA; проверка разрешимости ссылок из PLAN-STAB-7.
- **rollback / review:** по общим требованиям программы.

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

### PLAN-1 — capability owner gates (бывший монолитный 9B-C01)

- **status:** split. Ревизия 2 разделила PLAN-1 на четыре независимых слайса.
  **Глобальный inventory перестал быть предусловием любого
  production-изменения**; вместо него действует правило 11 Execution protocol:
  доказывается owner той capability, которую меняешь.
- **зависимости:** PLAN-0. **Не зависит** от зелёного full suite.
- **разрешённые зоны:** 1A, 1B, 1C′ — только `docs/current/CLEANUP_REGISTRY.md`;
  1D дополнительно допускает короткую routing-правку в `AGENTS.md`,
  `docs/current/START_HERE.md` и `docs/current/CURRENT_STATE.md`.
- **запрещено:** production-код, tests, схемы, config, любые move/delete/untrack,
  создание новых документов, правка master plan, изменение поведения.
- **общие требования к любому caller gate.** Проверяются module entrypoints через
  `python -m`, console scripts в `pyproject.toml`, `*.bat`, `*.cmd`, `*.ps1`,
  `.vscode`, `.idea`, task/config files, tests, docs, относительные, динамические
  и строковые вызовы. Статический import-граф **не** является доказательством
  отсутствия внешнего caller. Поиск вне репозитория запрещён. Вывод о
  дублировании бизнес-логики только по совпадению basename запрещён.

#### PLAN-1D-routing — маршрутизация агентов

- **status:** completed · **completed:** 2026-08-01 · **commit:** Git log —
  trailer `Plan-Step: PLAN-1D-routing` (собственный hash внутри того же commit
  не записывается, см. Execution protocol, пункт 3).
- **зависимости:** STEP 0 (перенос ревизии 2 в этот файл и в registry) выполнен.
  **Порядок обязателен:** 1D направляет будущих агентов в этот документ, поэтому
  документ должен сначала содержать утверждённую архитектуру.
- **цель:** шаг 4 `AGENTS.md` и «Текущий rescue plan» в `START_HERE.md`
  перестают направлять задачу в `PROJECT_RESCUE_MASTER_PLAN.md` как в current
  plan; добавляется ссылка на активный execution plan.
- **расширено 2026-08-01 — stale checkpoint в `CURRENT_STATE.md`.** [FACT]
  `docs/current/CURRENT_STATE.md` ссылается на активный execution plan и при
  этом называет текущим checkpoint `9B-C01`, которого после ревизии 2 больше
  нет. Это тот же routing-дефект в третьем current-документе, поэтому он
  чинится здесь же. **Exit condition расширен:** после PLAN-1D все current
  routing docs указывают на `PROJECT_EXECUTION_PLAN.md` как на current
  execution ordering source и **не называют `9B-C01` текущим checkpoint**. В
  `CURRENT_STATE.md` меняется **только** routing/checkpoint statement;
  unrelated docs cleanup там не выполняется.
- **evidence:** [FACT] у активного плана **одна** входящая ссылка во всём
  репозитории — из `CURRENT_STATE.md`; `AGENTS.md`, `START_HERE.md`, `CLAUDE.md`
  и `README.md` его не упоминают.
- **дополнительно записываются в registry** два уже проверенных findings:
  `docs/current/PRODUCT_EVIDENCE_GATE.md` со `status: historical_reference` как
  кандидат PLAN-12A (перемещение выполняет 12A, не 1D); и факт, что `skills/` не
  загружаются Claude Code автоматически, поскольку каталог не является
  `.claude/skills/`.
- **измеримый результат:** достигнут. Шаг 4 `AGENTS.md` направляет агента в этот
  файл и требует выполнять только его `current_checkpoint`; `START_HERE.md`
  называет этот файл текущим execution plan; `CURRENT_STATE.md` называет текущим
  checkpoint PLAN-2. Ни один из трёх документов не называет `9B-C01` текущим
  checkpoint. Master plan во всех трёх фигурирует только как исторический
  контекст. Дополнительно снята инструкция «обнови статус и «Текущий handoff» в
  master plan» из раздела «Завершение работы» `AGENTS.md` — она направляла
  запись current-статуса в исторический документ.
- **фактические проверки (2026-08-01, ветка `governance-reset`, HEAD до слайса
  `b396a50`, tracked-дерево чистое):**
  - `.\venv\Scripts\python.exe -m tools.qa.check_agent_docs` — exit code 0,
    «Agent documentation and skills are current and internally consistent.»;
  - `git diff --check` — пустой вывод, exit code 0;
  - `git grep -n "9B-C01" -- AGENTS.md docs/current/START_HERE.md
    docs/current/CURRENT_STATE.md` — ноль совпадений;
  - `git grep -n "PROJECT_RESCUE_MASTER_PLAN" -- ...` по тем же трём файлам —
    остались только historical/context упоминания и `source_paths`;
  - `git grep -n "PROJECT_EXECUTION_PLAN" -- ...` по тем же трём файлам —
    входящие ссылки появились в `AGENTS.md` и `START_HERE.md` дополнительно к
    существовавшей в `CURRENT_STATE.md`;
  - `git diff --name-only` — ровно пять docs-файлов: `AGENTS.md`,
    `docs/current/START_HERE.md`, `docs/current/CURRENT_STATE.md`,
    `docs/current/CLEANUP_REGISTRY.md`, `docs/current/PROJECT_EXECUTION_PLAN.md`.
  Production-код, tests, схемы, config и runtime не менялись; новых документов
  не создавалось; `docs/handoff/PROJECT_RESCUE_MASTER_PLAN.md` не изменён.
  Baseline run не выполнялся, `baseline_head` остаётся `fe2df5b`.
- **registry:** findings записаны как **C51** (`PRODUCT_EVIDENCE_GATE.md` —
  `status: historical_reference` внутри `docs/current/`, кандидат PLAN-12A, файл
  не перемещался) и **C52** (корневой `skills/` не является `.claude/skills/`,
  поэтому Claude Code не загружает его автоматически; Codex discovery остаётся
  `[ПРЕДП]`; второй набор skills не создаётся). Смысловых дубликатов в registry
  не было.
- **required verification:** `tools.qa.check_agent_docs`, `git diff --check`.
- **rollback:** один commit.

#### PLAN-1C′ — capability owner gate: asset/semantic

- **status:** pending. **BLOCKS PLAN-9A и PLAN-9C.** Первый product-слайс
  (PLAN-9B-0/9B-1) **не** блокирует.
- **зависимости:** — . **Изменено ревизией 2.1:** прямая зависимость от PLAN-6E
  **снята** — это docs-only ownership inventory, пишущий в
  `CLEANUP_REGISTRY.md`, и существование reviewer-skill ему не требуется.
  **Одновременно явно зафиксировано:** `PLAN-9A` требует `PLAN-6E`
  (persisted-state boundary) и `PLAN-9C` требует `PLAN-6E` (semantic decision
  boundary). Полагаться на транзитивную зависимость через PLAN-9B-2 запрещено.
- **остаётся обязательным capability-owner gate перед PLAN-9A и PLAN-9C.**
- **scope:** C01-SEM плюс владельцы persisted asset-manifest, релевантные tests и
  проверка дублей в радиусе PLAN-9A: `src/assets/semantic_selection/*`,
  `src/assets/semantic_visual*`, `src/assets/completion/*`,
  `src/news/asset_manifest_builder.py`, `src/news/asset_scene_completion.py`,
  `src/news/project_store.py`, `schemas/`.
- **C01-SEM.** Ownership для `semantic_selection`, `semantic_visual`, visual
  planner и asset completion: кто принимает решение о пригодности кандидата, где
  заканчивается shared service и начинается workflow policy, какова роль
  заглушки `vision_validator` и подключённого, но не влияющего на отбор
  `semantic_visual_service`.
- **дополнительно:** зафиксировать как дефект production-зависимость на
  `docs/implementation/openai_live_evaluation` (registry C31). **Файлы не
  переносить** — target owner решает PLAN-13 по OD-8/OD-9.
- **вынесено из scope ревизией 2:** пофайловая классификация
  `docs/implementation` (96 файлов) переходит в **PLAN-12B** — она не нужна
  PLAN-9A.
- **измеримый результат:** C01-SEM закрыт; для каждого затронутого модуля
  известны canonical owner, callers, persisted contract, дубли и тесты.
- **required verification:** `tools.qa.check_agent_docs`, `git diff --check`.
- **rollback:** один commit.

#### PLAN-1A — capability gate: entrypoints и package roots

- **status:** pending. **Не блокирует первый product fix и PLAN-9A.**
  Обслуживает PLAN-L и PLAN-13.
- **scope:** C01–C04, C08–C11; `pyproject.toml`, console scripts, module
  entrypoints, `apps/*`, root `ai_youtube/`, `src.content_creation.cli`.
- **примечание:** caller gate для `pipeline.py`, `legacy/` и legacy-семейства
  выполняет **PLAN-L1**, а не 1A. Foundation audit установил [FACT], что
  `legacy/` (8 файлов) не имеет ни одного Python-caller и упоминается только в
  `README.md` и historical docs (registry C17); это **не** закрывает C17.
- **required verification:** `tools.qa.check_agent_docs`, `git diff --check`.

#### PLAN-1B — capability gate: application/shared ownership

- **status:** pending. **Не блокирует первый product fix и PLAN-9A.**
  Обслуживает PLAN-13, включая покрытие HIGH-3 (channel/project formats).
- **scope:** C05–C08 и C12–C16; Fullscreen, Story Card, Anime
  project/transcription/subtitles/FFmpeg/render, music, project/workspace и
  границы shared-сервисов.
- **required verification:** `tools.qa.check_agent_docs`, `git diff --check`.

### PLAN-L — retirement legacy content stack

- **status:** pending · **зависимости:** зелёный PLAN-4. **PLAN-L0 completed
  2026-08-02 и закрывает prerequisite PLAN-9B-PRODUCER/PLAN-9B-2; PLAN-L1…PLAN-L4
  остаются отдельной retirement-веткой, закрытием PLAN-L0 не разрешены и
  напрямую prerequisite PLAN-9A не являются.**
- **цель:** убрать крупнейший disposable блок репозитория до того, как он
  продолжит удерживать docs, packaging, tests и minimalism.
- **evidence [FACT], 2026-07-31:** legacy content-стек — `pipeline.py` →
  `src/legacy_pipeline/workflow.py` → 20 модулей корня `src/` (~4903 строки) —
  имеет **ровно одного** production-caller (`pipeline.py`) и **6** test-модулей
  из 112. `legacy/` (8 файлов, 424 строки) не имеет ни одного Python-caller.
  Исключения, которые остаются: `src/media_library.py` (используется активным
  news-путём) и `src/utils.py` (используется `src/audio/tts/env.py` и
  `src/tts_providers/moss_tts_provider.py`).
- **evidence [FACT]:** `src/legacy_pipeline/maintenance.py` (~500 строк) — **не**
  legacy-генерация контента, а единственный CLI-доступ к visual-preview,
  semantic-backend, semantic-evaluation, semantic-visual, media-library и
  envato-manual. Канонический CLI этих команд не имеет. [INFERENCE] PLAN-9D без
  них не запускается — поэтому L2 обязателен до L3.
- **impact:** −~5700 строк, −6 тестов, −6 top-level путей; закрываются C17, C18,
  C19, C24, C25, C29; PLAN-7, PLAN-13D, PLAN-14B и часть PLAN-14F становятся
  тривиальными.
- **rollback:** один commit на под-slice плюс annotated tag по механизму
  reversible retirement.

#### PLAN-L0 — Knowledge Salvage Gate

- **status:** completed · **completed:** 2026-08-02 · **commit:** — (см. Git log,
  trailer `Plan-Step: PLAN-L0`) · **обязателен до PLAN-9B-PRODUCER и L3** ·
  **зоны:** `docs/current/CLEANUP_REGISTRY.md` (+ этот файл для
  checkpoint/evidence по Execution protocol).
- **фактический результат:** `Knowledge salvage log` в `CLEANUP_REGISTRY.md`
  заполнен; placeholder-строка снята. Аудированы все обязательные families:
  `channels/{psychology,quotes,survival,size_comparison}` и `content/` ·
  20 движков корня `src/` (ровно `src/*.py` кроме `__init__.py`,
  `media_library.py` и `utils.py`, суммарно 4903 строки) ·
  `src/legacy_pipeline/workflow.py` · `config/video_style.json` · `legacy/` ·
  `MOSS_TTS_Nano/` + `src/tts_providers/` + `scripts/test_moss_voices.py` ·
  legacy test-модули · motion owners (`story_card_short_render`,
  `generated_infographic`, `self_eval`, callers `moviepy`).
- **обязательные находки подтверждены фактическим кодом:** все двенадцать —
  C46, C47, C48, `self_eval`, thumbnail, YouTube metadata, size comparison,
  Story Card, `generated_infographic`, `moviepy`, text overlay/title,
  music-by-mood. Два уточнения записаны как измерения, не нормативы:
  legacy test-модулей фактически семь, а не шесть, и legacy-callers `moviepy` —
  шесть, а не три (**C55** по существу не меняется).
- **границы соблюдены:** capability не мигрировалась, retirement не выполнялся,
  tag и bundle не создавались, файлы не удалялись и не перемещались;
  production-код, tests, configs, schemas, manifests, runtime и user data не
  изменялись; сеть, provider search/download, model API, TTS, Vision и render не
  выполнялись. Новый owner, ADR, schema, manifest, interface, package и
  placeholder implementation не создавались. `baseline_head` не менялся.
- **фактические проверки:** `tools.qa.check_task_scope` с двумя разрешёнными
  exact paths — `OK`, exit code 0; `tools.qa.check_agent_docs` — exit code 0;
  `git diff --check` — без замечаний. Full offline suite не запускался: слайс
  docs-only, test discovery, runner и production contract не менялись
  (Execution protocol, пункт 10).
- **правило (OD-1):** отсутствие caller — **не** критерий отсутствия ценности.
  Ретайр legacy допускается только после salvage.
- **scope gate — что проходит через L0.** KSG применяется к
  **knowledge-bearing retirement families**: source code, workflow, config,
  prompts, templates, tests и те docs/evidence, которые содержат уникальное
  инженерное или продуктовое знание.
- **что через L0 НЕ проходит.** Disposable runtime/media/cache — старые `.mp4`,
  `.wav`, `.png`, кэши, generated outputs, runtime-каталоги проектов — идёт
  другой цепочкой: **PLAN-14D** (классификация, отбор representative corpus,
  сверка с `Preserved runtime corpus`) → **PLAN-14E** (cleanup). Спрашивать
  «какое product knowledge содержится в старом mp4» не нужно и запрещено как
  формальность: это превратило бы runtime reset в бесконечный gate.
  **Knowledge Salvage и Runtime Reset не смешиваются.**
- **граница между цепочками.** Решает не каталог, а носитель знания: JSON/SRT/ASS
  манифесты — это persisted **форма**, их ценность проверяется отбором
  representative corpus в 14D, а не salvage-классификацией L0. Если внутри
  runtime-каталога найден source/prompt/template/config — он уходит в L0.
- **что искать в каждом удаляемом family:** reusable algorithm · domain и
  product knowledge · prompts, templates, visual rules · rights и licensing
  knowledge · fallback и recovery logic · edge cases · reusable schema
  knowledge · полезные characterization и product tests.
- **классификация каждой находки:**

  ```
  MIGRATE CAPABILITY        пометить как отдельный будущий product slice.
                            НЕ выполняется внутри PLAN-L (OD-10).
  MIGRATE KNOWLEDGE         перенести знание: ADR, docstring, comment, fixture
  KEEP MINIMAL REGRESSION   оставить минимальный representative fixture
  ARCHIVE ONLY              только retirement tag, в active tree не возвращать
  DELETE                    ничего ценного
  ```

- **граница L0/L3 (OD-10).** L0 сохраняет **знание**, а не переносит capability.
  **L3 остаётся cleanup/retirement-этапом и не превращается в
  product-development.** Если salvage признаёт capability ценной — это отдельный
  будущий product slice на новом canonical core из salvage evidence, а не
  миграция старой реализации внутрь L3.
- **семейства в scope:** `channels/{psychology,quotes,survival,size_comparison}`
  и `content/` (OD-1) · 20 движков корня `src/` · `legacy/` ·
  `src/legacy_pipeline/workflow.py` · `config/video_style.json` ·
  `MOSS_TTS_Nano/` и `src/tts_providers/` (OD-7) · 6 legacy test-модулей.
- **обязательные salvage-находки ревизии 2.1** (сохранить **до** retirement;
  старый pipeline ради них **не** сохраняется):
  1. **legacy `build_query_variants` expansion ladder** — `MIGRATE KNOWLEDGE`,
     потребитель **PLAN-9B-2** (registry C46);
  2. **local-library diversity reserve** (`min_local_diversity_per_scene` /
     `reserved_download_slots`) — `MIGRATE KNOWLEDGE`, потребитель **PLAN-10D**
     (registry C47);
  3. **практика «provider-ready английские visual keywords существуют
     отдельным полем, отделённым от нарратива»** — `MIGRATE KNOWLEDGE`,
     носитель ADR/registry (registry C48).
  4. **анализ качества готового файла** (`src/self_eval.py`) — `MIGRATE
     KNOWLEDGE`. Это единственное в репозитории знание о проверке
     отрендеренного файла, а не метаданных; потребитель — будущее расширение
     существующего quality owner. Новый Quality Engine не создаётся.
  5. **thumbnail generation, YouTube metadata и формат сравнения размеров** —
     `MIGRATE CAPABILITY` по OD-10: это продуктовые возможности, которых у
     нового продукта нет вовсе. Внутри PLAN-L они **не** мигрируются; каждая
     помечается отдельным будущим product slice на новом canonical core.
     Продуктовая запись — `PRODUCT_PLAN.md`, раздел «Legacy knowledge and
     capability salvage».
- **обязательные salvage-находки motion rendering (2026-08-01)** — сохраняются
  **до** замещения соответствующего owner по PD-11; старая реализация ради них
  не сохраняется:
  6. **поведение Story Card** — адаптивный текст, вёрстка по реальным метрикам
     шрифта, работа с длинными строками, вертикальный layout: `MIGRATE
     KNOWLEDGE` + `KEEP MINIMAL REGRESSION`, потребитель — parity case
     `MOTION-CS2` → `MOTION-CS4` (registry C53);
  7. **ценные контракты `generated_infographic`** — «спека → project-owned
     asset с license/provenance/checksum/technical validation», fingerprint
     спеки и правило «нет evidence → нет фактической диаграммы»: `MIGRATE
     KNOWLEDGE`, потребитель — `MOTION-CS4`; новый author встраивается **в**
     этот контракт, а не рядом с ним (registry C56);
  8. **callers и фактическая необходимость `moviepy`** — `MIGRATE KNOWLEDGE`,
     потребитель — dependency gate `MOTION-CS4` (registry C54, C55);
  9. **анализ качества готового файла** (`src/self_eval.py`) уже записан
     находкой 4 выше; дополнительный потребитель — technical QA сегмента в
     `MOTION-CS1`. Новый Quality Engine не создаётся.
- **измеримый результат:** для каждого family записан класс каждой находки и,
  где применимо, что именно потенциально стоит восстановить позже.
- **required verification:** `tools.qa.check_agent_docs`, `git diff --check`.

#### PLAN-L1 — caller gate и retirement manifest

- **status:** pending · **зависимости:** PLAN-L0 · **зоны:** только registry.
- **цель:** полный caller gate по legacy-семейству по общим требованиям PLAN-1.
  Закрывает C17.
- **дополнительно:** зафиксировать retirement-теги, которые будут созданы в
  L3/L4, и подтвердить наличие внешнего `git bundle` перед первым удалением.
- **required verification:** `tools.qa.check_agent_docs`, `git diff --check`.

#### PLAN-L2 — вынести diagnostics из legacy

- **status:** pending · **зависимости:** PLAN-L1 · **обязателен до L3.**
- **цель:** команды `src/legacy_pipeline/maintenance.py` (visual-preview,
  semantic-backend, semantic-evaluation, semantic-visual, media-library,
  envato-manual) переезжают на канонический CLI `diagnostics` либо в `tools/`.
- **запрещено:** менять поведение команд в этом слайсе; смешивать перенос
  diagnostics с удалением движков.
- **required verification:** targeted + `smoke` + `full` — меняется CLI surface.

#### PLAN-L3 — retire движков

- **status:** pending · **зависимости:** PLAN-L0 и PLAN-L2.
- **удаляется:** `src/legacy_pipeline/workflow.py`; 20 модулей корня `src/`
  **кроме** `media_library.py` и `utils.py`; `src/tts_providers/` (OD-7);
  `channels/{psychology,quotes,survival,size_comparison}` и `content/` (OD-1);
  `config/video_style.json`; 6 legacy test-модулей.
- **запрещено:** мигрировать capability внутрь этого слайса (OD-10).
- **required verification:** `full`.

#### PLAN-L4 — retire entrypoint

- **status:** pending · **зависимости:** PLAN-L3.
- **удаляется:** `pipeline.py`, `src/legacy_pipeline/cli.py`,
  `apps/youtube_pipeline/`, `legacy/`, `scripts/`, `MOSS_TTS_Nano/` (OD-7).
- **исправляется:** `py-modules = ["pipeline"]` снимается вместе с импортом
  `scripts.test_moss_voices` (C18, C25); `outputs/*.json` и
  `outputs/asset_library_report.md` снимаются с Git (C19, C29).
- **измеримый результат:** канонический CLI — единственный пользовательский вход;
  wheel собирается и импортируется из произвольного temporary checkout.
- **required verification:** `full` + сборка wheel + `import` в temporary venv
  вне checkout. Установка требует отдельного разрешения.

### PLAN-2 — baseline repair: voice-profile fixtures

- **status:** completed · **completed:** 2026-08-01 · **commit:** — (см. Git log,
  trailer `Plan-Step: PLAN-2`)
- **цель:** убрать устаревшую изоляцию через `os.chdir` и использовать явный
  `channels_dir` либо существующий path seam.
- **зависимости:** PLAN-1D-routing. **Изменено ревизией 2:** зависимость от
  полного PLAN-1 снята — слайс трогает один test-модуль и никакого capability
  ownership не меняет.
- **разрешённые зоны:** `tests/test_voice_profile_resolution.py`.
- **запрещено:** production-код, прочие тесты.
- **диагноз (подтверждён):** изоляция через `os.chdir` перестала действовать
  после того, как versioned resources стали резолвиться от корня репозитория, а
  не от `cwd`; реестр читает настоящий `channels/` и возвращает чужой профиль.
  Production корректен.
- **root cause (фактический):** `src/config_resolver/paths.py` вычисляет
  `_REPOSITORY_ROOT` от расположения модуля (`Path(__file__).resolve().parents[2]`),
  и `ApplicationPaths.channels_root` — это `repository / "channels"`. `cwd` в этой
  цепочке не участвует вообще, поэтому `os.chdir()` во временный каталог не
  изолировал ничего: и `capabilities._channels_root()`, и
  `voice_profile_registry._channels_root()` продолжали читать настоящий
  `channels/`. Доказательство характеризацией: `list_voice_profiles` возвращал
  `['ru_dom']` вместо `['ru_test']` — то есть реальный профиль из
  `channels/nature_science_news_ru/voices.yaml`.
- **применённый seam:** существующий публичный параметр `repository_root=`
  функции `src.config_resolver.paths.resolve_application_paths` — тот же seam,
  которым уже пользуются `tests/test_stage3_workspace_paths.py` и
  `tests/test_legacy_pipeline_internals_contract.py`. Fixture создаёт временный
  `channels/`-каталог и на время блока подменяет `resolve_application_paths`
  обёрткой, подставляющей `repository_root` фикстуры; обе точки входа
  (`capabilities._channels_root`, `voice_profile_registry._channels_root`)
  импортируют эту функцию внутри тела, поэтому один seam покрывает обе.
  `channels_dir` как явный аргумент здесь неприменим: ни
  `capabilities.resolve_voice_profile`, ни `list_voice_profiles`, ни
  `load_voice_profile_for_channel` его не принимают, а добавление параметра было
  бы изменением production-кода вне разрешённых зон. Новый helper, registry или
  второй способ разрешения channels не создавался.
- **измеримый результат:** модуль завершается без failures и errors; сохранены
  паритет UI и runtime, резолв по display_name, borrowed profile с
  `source_channel_id`, `include_global=False`, понятное сообщение об ошибке и
  отсутствие протечки реальных repository-профилей в fixture. `os.chdir()` из
  модуля удалён; `cwd` процесса после прогона не меняется.
- **required verification:** только targeted-модуль. Режим `fast` ещё не
  существует до PLAN-5 и поэтому не может быть prerequisite.
- **фактическая verification (2026-08-01, HEAD до слайса `373daa8`):**
  - до изменения: `.\venv\Scripts\python.exe -B -m unittest
    tests.test_voice_profile_resolution` — exit code 1, 8 тестов, 1 failure и
    3 errors;
  - после изменения: та же команда — exit code 0 двумя последовательными
    прогонами; каждый test-класс отдельно тоже зелёный (зависимости от порядка
    нет);
  - `.\venv\Scripts\python.exe -m tools.qa.check_agent_docs` — exit code 0;
  - `git diff --check` — без замечаний.
  Числа тестов, failures и errors записаны как измерение с датой и проверенным
  HEAD, нормой они не являются (Measurement policy).
- **rollback:** один commit.

### PLAN-3 — baseline repair: completion-wiring fixtures

- **status:** completed · **completed:** 2026-08-01 · **commit:** — (см. Git
  log, trailer `Plan-Step: PLAN-3`)
- **цель:** создавать обязательные stage outputs согласно output-validated
  idempotency ADR 0006.
- **зависимости:** PLAN-2. **Изменено ревизией 2:** зависимость от полного
  PLAN-1 снята. Слайс трогает один test-модуль, но это **тот самый модуль**,
  который меняет PLAN-9A, поэтому он остаётся прямым prerequisite 9A.
- **разрешённые зоны:** `tests/test_autonomous_completion_pipeline.py`.
- **запрещено:** production-код.
- **диагноз (подтверждён):** два test-метода давали три failure-case:
  `test_resume_restarts_asset_search_when_completion_semantics_change` (два
  subtest) и
  `test_resume_keeps_completed_asset_search_when_override_is_unchanged`
  помечали стадии `completed`, не создавая обязательных outputs, и ожидали
  поведение до этапа 5D. `NewsProjectStore.is_stage_completed` после ADR 0006
  признаёт marker только вместе с пригодным output, поэтому production
  корректно повторял `research`, `script` и `visual_plan`; в unchanged-case
  также не существовал пригодный output `asset_search`.
- **исправление:** private helper внутри test-модуля создаёт во временном
  project layout реальные минимальные `research/claims.json`, локализованные
  `script/script.json` и `visual/visual_plan.json`, а также
  `assets/assets_manifest.json`. Fixtures проходят фактические production
  validators; assertions, resume/force-stage semantics и production-код не
  менялись.
- **окончательный resume-факт:** стадия с отсутствующим или непригодным output
  может быть перезапущена; по 28 проверенным проектам платные и сетевые стадии
  не перезапускаются; у 7 проектов могут повториться только локальные
  preview/final render. Старое предположение о повторных платных
  `research`/`script` в current-документы не переносится.
- **измеримый результат:** модуль завершается без failures и errors;
  ожидаемое production-поведение не изменено.
- **required verification:** только targeted-модуль. Совместный полный
  baseline выполняется отдельным PLAN-4.
- **фактическая verification (2026-08-01, HEAD до слайса `a8c40a1`):**
  - до изменения: `.\venv\Scripts\python.exe -B -m unittest
    tests.test_autonomous_completion_pipeline` — exit code 1, 14 тестов,
    3 failures;
  - после изменения: та же команда — exit code 0 в двух последовательных
    прогонах;
  - `.\venv\Scripts\python.exe -m tools.qa.check_agent_docs` — exit code 0;
  - `git diff --check` — без замечаний;
  - full offline suite не запускался; зелёность baseline остаётся предметом
    PLAN-4.
  Числа тестов и failures записаны как измерение с датой и проверенным HEAD,
  нормой они не являются (Measurement policy).
- **rollback:** один commit.

### PLAN-4 — зелёный baseline

- **status:** completed · **completed:** 2026-08-01 · **commit:** —
- **цель:** воспроизводимый зелёный offline baseline.
- **зависимости:** PLAN-2, PLAN-3.
- **разрешённые зоны:** production/tests не меняются; этот plan обновляется
  измерением, проверенным исходным HEAD и новым checkpoint.
- **измеримый результат:** `python -B -m unittest discover -s tests -p "test_*.py"`
  завершается с exit code 0 без неожиданных failures и errors; фактические число
  тестов и время записаны в Measurement policy как измерение с датой и
  проверенным исходным HEAD.
- **required verification:** full offline suite.
- **фактическая verification (2026-08-01):** на проверенном исходном HEAD
  `84bdd8b4f64c7adaf7582bdb39b15b18163253fb` команда
  `.\venv\Scripts\python.exe -B -m unittest discover -s tests -p
  "test_*.py"` завершилась с exit code 0: 1441 тест за 231.839 секунды,
  failures: 0, errors: 0, skips: 0. Unexpected failures/errors отсутствуют;
  прогон был offline, без provider search/download, Vision, TTS, платных
  API-вызовов и реального пользовательского render. Production-код и tests в
  PLAN-4 не менялись. Число тестов и длительность — измерение, не норматив;
  будущий plan-only commit не является проверенным source HEAD.
- **rollback:** один plan-only checkpoint commit.

### PLAN-5 — единый test runner

- **status:** pending · **completed:** — · **commit:** —
- **цель:** один runner вместо трёх разных правил о тестах.
- **зависимости:** PLAN-4. **PARALLEL для всех под-слайсов PLAN-9B** (ревизия
  2.1). [FACT] targeted (`python -B -m unittest <модули>`), full
  (`python -B -m unittest discover -s tests -p "test_*.py"`) и три smoke-команды
  (`python -m ai_youtube --help`, `capabilities --json`, `applications list`)
  исполнимы **сегодня**. PLAN-5 улучшает uniform runner UX и воспроизводимость
  формулировки; техническим blocker product fixes он не является и в required
  verification слайсов 9B подменяется существующими командами.
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
- **разделение ревизией 2.** Только **6A, 6D и 6E** блокируют PLAN-9A.
  **6B и 6C — параллельные**, глобальными prerequisites product-работ не
  являются.
- **переоценка ревизией 2.1 (risk-based).**
  **6A — PARALLEL** относительно PLAN-9B: Agent Autonomy Model уже действует из
  текста этого плана, а routing чинит PLAN-1D; собственные добавления 6A
  (проверка команд в `skills/*/SKILL.md`, расширение `CURRENT_DOCS`, cap
  `AGENTS.md`) обслуживают PLAN-7 и PLAN-12, не 9B. Зависимость **6A → 6D —
  ordering convention, а не техническая необходимость**.
  **6D — blocker первого multi-owner implementation slice** (PLAN-9B-2).
  **6E — blocker первого destructive retirement / high-risk shared-contract
  slice** (PLAN-9B-2, 9B-3, 9B-5b), плюс **обязателен для PLAN-9A и PLAN-9C**.
- **bounded sub-slices:**
  - **PLAN-6A — governance R1–R12, Agent Autonomy Model и docs QA:**
    - **PARALLEL относительно PLAN-9B** (ревизия 2.1);
    - разрешённые зоны: `AGENTS.md`, `tools/qa/check_agent_docs.py`, связанные
      onboarding и reproducibility tests;
    - R1–R12 в согласованной редакции с категориями A/B/C/D;
    - **переносит в `AGENTS.md` Agent Autonomy Model этого плана:** классы
      `[HARD]/[ARCH]/[HINT]`, «выполнение инструкции не является выполнением
      задачи», Decision rights (три tripwire), Challenge/Recovery Protocol,
      semantic Owner Lookup, Task contract. После переноса соответствующий
      раздел этого плана сворачивается до ссылки: один canonical owner на
      правило;
    - **исправляет три формулировки, ошибочно оформленные как HARD:**
      (a) «сначала добавляй characterization test» → `[HINT]` с условием
      «когда меняешь наблюдаемое поведение, у которого есть caller»;
      (b) «не создавай второй provider contract / voice registry / subtitle
      engine / config resolver / completion ladder» → `[ARCH]`: запрещён
      **второй одновременно живущий** canonical owner, **замена** owner через
      evidence + ADR + review разрешена;
      (c) «сохраняй tolerant readers, resume/force-stage и approval gates» →
      разделить: approval gates `[HARD]`, tolerant readers `[ARCH]`;
    - **cap 120 строк `AGENTS.md`** (`tests/test_stage2_agent_onboarding.py:26`)
      переклассифицируется в measurement/warning. Число не является
      архитектурным решением; `AGENTS.md` остаётся коротким по responsibility.
      Если Engineering Conventions окажутся отдельной responsibility, отдельный
      owner допускается **после доказательства необходимости** и не
      запрещается числом строк. `docs/architecture/ENGINEERING_CONVENTIONS.md`
      заранее не создаётся;
    - **минимальный gap-набор conventions**, у которого сегодня нет владельца и
      который закрывается здесь как `[ARCH]`: правило размещения пакета
      (`src/foo.py` против `src/foo/`); процедура deprecation; политика fixtures
      (versioned / synthetic / временный каталог); именование и категории тестов;
      условие появления нового top-level каталога. Уже покрытое (naming, errors,
      logging, config, persistence, schemas, typing, imports, dependency
      direction, public/private API) повторно не документируется — владельцы
      существуют в коде, ADR и `SYSTEM_MAP`;
    - QA не требует вечного существования конкретных архивных handoff;
    - exact-count проверка skills заменяется минимальным обязательным набором
      критичных skills плюс автоматической проверкой всех найденных;
    - broken link, missing source path и invalid commit — error;
    - возраст документа и превышение рекомендуемого размера — warning;
    - onboarding-лимит `START_HERE.md` может остаться жёстким;
    - `README.md` и `COMMANDS.md` обязаны упоминать канонический CLI;
    - `CURRENT_DOCS` перестаёт быть вшитым кортежем из трёх путей: проверяются
      все файлы `docs/current/` со `status: current` плюс активный execution
      plan. Сейчас QA покрывает три файла из семи, и активный план не
      проверяется вовсе;
    - файл в `docs/current/` со `status`, отличным от `current` или `active`,
      становится error: это делает findings PLAN-1D самопроверяемыми;
    - `max_age_days` перестаёт быть вшитой в код нормой — приходит аргументом,
      дефолт остаётся warning, а не error;
    - снимается требование «`docs/handoff` содержит ровно один файл»: оно
      конфликтует с PLAN-12C, который этот каталог архивирует;
    - **добавляется проверка команд внутри `skills/*/SKILL.md`**: команды,
      которым skill обучает агента, обязаны соответствовать каноническому
      CLI. Foundation audit [FACT]: три из шести skills
      (`create-short-video-first`, `resume-project`, `replace-visual-slot`)
      учат `python -m src.content_creation.cli`, а текущий QA проверяет только
      frontmatter, локальные ссылки и `TODO`. PLAN-7 чинит эти три файла
      однократно; без проверки ничто не мешает им разойтись снова;
  - **PLAN-6B — ранний report-only minimalism baseline:**
    - зависимость: PLAN-6A. **Параллельный: product-работу не блокирует;**
    - **subprocess network-guard measurement (ревизия 2.1, registry C49):**
      guard из test-пакета дочерним процессом **не наследуется**. На audit HEAD
      `adcbb19` subprocess-модулей **12** (ранее записано 7) — это
      **measurement, не invariant**. Архитектурное решение по kill-switch
      сейчас **не принимается**: расширение guard на subprocess boundary и
      environment kill-switch остаются открытыми альтернативами,
      механизм/owner — implementation-time evidence/owner decision. **6B
      остаётся report/measurement owner в своей текущей границе и ничего не
      мутирует**; production-side механизм получает своего owner отдельным
      слайсом;
    - **сохранить как candidates для architecture fitness enforcement**
      (внедрение — здесь и в существующих test-владельцах, второй QA framework
      не создаётся): unknown top-level directories · runtime writes внутрь
      source repo · tracked generated media · absolute machine paths ·
      более одного canonical public CLI · запрещённые application → application
      зависимости · владение persisted manifests и schema · consistency
      provider registry · network boundary · paid calls через approval
      gateway · stale commands и невалидный agent routing.
      Владельцы: детекторы репозитория — `check_repository_minimalism.py`;
      инварианты кода — существующие `tests/test_asset_import_boundaries.py`,
      `tests/test_capability_consistency.py`, `tests/test_artifact_schemas.py`,
      `tests/network_guard.py`; переписываемый `tests/test_apps_structure.py`
      становится тестом «нет второго canonical public CLI»;
    - разрешённые зоны: `tools/qa/check_repository_minimalism.py`, его
      targeted tests, `docs/current/CLEANUP_REGISTRY.md`;
    - отчёт покрывает tracked cache/generated outputs, top-level paths вне
      draft allowlist, exact duplicates, wrappers без registry, retired
      imports, hardcoded machine paths, empty directories и orphan-кандидатов;
    - **три детектора добавляются по проверенным findings Foundation audit:**
      (a) tracked ∩ ignored — `git ls-files -i -c --exclude-standard`; сейчас
      9 файлов: 8 × `outputs/*.json` и `assets/broll/.gitkeep`, где директорное
      правило обесценивает последующее отрицание (registry C19, C21);
      (b) top-level untracked вне allowlist; сейчас `output/` и `tmp/`, не
      покрытые ни одним правилом `.gitignore` (registry C20);
      (c) hardcoded drive-paths **в versioned config**, а не только в коде;
      сейчас `config/video_style.json` и `channels/psychology/style.json`
      (registry C24). Детектор tracked generated outputs обязан находить и
      `outputs/asset_library_report.md`, который под `.gitignore` не подпадает,
      но порождается `src/media_library.py` (registry C29);
    - detector ничего не удаляет; orphan/duplicate остаются review evidence;
  - **PLAN-6C — dependency/toolchain ownership audit:**
    - зависимость: PLAN-6B. **Параллельный: product-работу не блокирует.**
      Ревизия 2 сняла с 6C роль предусловия PLAN-6E: skills discovery
      verification для Codex невыполнима (Codex не установлен) и больше не
      блокирует reviewer — см. PLAN-6E;
    - **installed-package defect C25 и `scripts/` (C18) закрывает PLAN-L4**, а
      не 6C: их носители удаляются вместе с legacy-стеком. За 6C остаётся
      distribution boundary `tools/` (C26) и dependency ownership;
    - read-only по `pyproject.toml`, `requirements.txt`, `requirements.lock`,
      CI/task/config files, Anime/ML optional dependencies, `venv/`,
      MOSS/Whisper/model weights и agent-specific adapters;
    - обновляется только `docs/current/CLEANUP_REGISTRY.md`;
    - фиксируются direct/resolved/optional/toolchain owners, callers,
      воспроизводимость, replacement и exit conditions до package
      consolidation;
    - **обязательная проверка installed-package defect (registry C25).**
      [FACT] `py-modules = ["pipeline"]` включает `pipeline.py` в дистрибутив,
      `packages.find.include` не содержит `scripts*`, а `pipeline.py:9`
      импортирует `scripts.test_moss_voices`. [INFERENCE] non-editable
      установка ломает `import pipeline`; `pip install .` не выполнялся, и CI
      это не ловит, потому что использует `--editable`. Проверяется сборкой
      wheel и импортом в temporary venv вне checkout; требует отдельного
      разрешения на установку. Это прямой блокер критерия PLAN-15
      «installed package из произвольного temporary checkout»;
    - **обязательное решение по intended distribution boundary `tools/`
      (registry C26).** [FACT] `tools*` не входит в `packages.find.include`;
      все известные callers находятся внутри checkout. Отсутствие в wheel
      **не является дефектом по умолчанию**. Если решение — «только checkout»,
      правка идёт в формулировку `AGENTS.md`, а не в `pyproject.toml`.
      Добавлять `tools*` в wheel только ради того, чтобы repository QA
      работал из установленного пакета, запрещено;
    - **обязательная skills discovery verification (совместно с PLAN-6E).**
      Различать четыре разных состояния: наличие файлов, manual loading,
      auto-discovery, actual invocation. [FACT] Claude Code не обнаруживает
      корневой `skills/` автоматически: `.claude/` содержит только
      `settings.json`, `settings.local.json` и `scheduled_tasks.lock`.
      **[ПРЕДП]** утверждение «Codex обнаруживает эти skills через
      `skills/*/agents/openai.yaml`» не проверено: Codex в среде не установлен,
      discovery-check не выполнялся, tracked codex-конфигов в репозитории нет.
      Наличие `agents/openai.yaml` не является доказательством discovery.
      Проверка: получить фактический список project skills установленного
      Codex; выполнить явный вызов одного repo skill; определить обнаруженный
      path; проверить фактическую роль `agents/openai.yaml`; сравнить корневой
      `skills/` со стандартным discovery path. **До получения результата
      второй набор skills не создаётся.**
  - **PLAN-6D — scope control foundation:** см. отдельный раздел ниже;
  - **PLAN-6E — independent reviewer foundation:** см. отдельный раздел ниже.
- **измеримый результат:** docs QA зелёный при новых правилах; `AGENTS.md`
  в районе ста строк; первый minimalism report сохранён как baseline;
  dependency/toolchain решения известны до PLAN-13C и PLAN-14B; scope-контроль
  и независимый reviewer существуют технически, а не только в тексте правил.
- **required verification:** PLAN-6A — docs QA + `full`; PLAN-6B — targeted
  tests detector + docs QA; PLAN-6C — docs QA; PLAN-6D — targeted tests
  `check_task_scope` + docs QA; PLAN-6E — docs QA; `git diff --check` всегда.
- **rollback:** один commit на под-slice.

### PLAN-6D — scope control foundation

- **status:** completed · **completed:** 2026-08-02 · **commit:** Git log —
  commits `397d338` (PLAN-6D-1), `10dd555` (PLAN-6D-2) и trailer
  `Plan-Step: PLAN-6D-3` для завершающего commit.
- **цель:** перевести защиту от выхода за scope и от порчи пользовательских
  данных с уровня «агент помнит правило» на уровень технического ограничения.
- **роль в ревизии 2.1:** **BLOCKER первого multi-owner implementation slice**
  — по фактическим footprint'ам это PLAN-9B-2 (`query_adapter` +
  `script_generator` + `visual_planning` + `semantic_selection`). Для PLAN-9B-0
  (один новый test-модуль) и PLAN-9B-1 (один модуль и его тесты) allowlist
  тривиален и проверяется глазами.
- **зависимости:** PLAN-6A — **ordering convention, не техническая
  необходимость** (ревизия 2.1): 6D-1 пишет `.claude/settings.json`, 6D-2
  создаёт `tools/qa/check_task_scope.py`, 6D-3 правит `CLAUDE.md`, и ни одному
  из них не требуется, чтобы R1–R12 уже лежали в `AGENTS.md`. **Исправлено
  ревизией 2:** прежняя зависимость от
  PLAN-6C возвращала параллельные 6B и 6C в критический путь через 6D и
  противоречила разделению «блокируют только 6A, 6D и 6E». Содержательной
  зависимости от dependency/toolchain аудита у 6D нет; единственное касание 6C —
  Codex-часть skills discovery, которая в `CLAUDE.md` не записывается (6D-3).
- **разрешённые зоны:** `.claude/settings.json`, `CLAUDE.md`,
  `tools/qa/check_task_scope.py` и его targeted tests.
- **запрещено:** production-код, создание hooks, создание `.claude/skills/`,
  дублирование содержимого `skills/` в adapter-файлах, блокировка versioned
  resources, fixtures, `.gitkeep` и документации.
- **evidence, на котором построен slice** (проверено 2026-07-30 от clean HEAD
  `2379444`): механизма сравнения allowlist задачи с фактическим Git diff в
  репозитории нет; единственный QA-модуль — `tools/qa/check_agent_docs.py`;
  hooks, `.claude/agents/`, `.claude/skills/` и git-hooks отсутствуют.
- **bounded под-slices:**
  - **6D-1 — permissions: четыре раздельных класса действий.** Классы не
    смешиваются. **status: completed 2026-08-02.** **Исправлено ревизией 2:**
    прежняя редакция ставила permanent
    hard deny на `projects/**`, `music/**`, `assets/library/**`,
    `assets/cache/**`, `anime_factory/episodes/**`. Владелец объявил это
    тестовое runtime-медиа disposable, а PLAN-14E обязан его удалить — правило
    пришлось бы обходить ради собственного утверждённого шага. Permission,
    которое придётся обходить, защитой не является.
    - *Hard deny — вечное:* secrets — существующие `.env`/credentials/pem/key
      плюс `Write` и `Edit` по `.env`;
      destructive Git — `reset --hard`, `clean` по непроверенным путям, force
      operations, включая починку голого `git clean`, который текущий шаблон
      `Bash(git clean *)` не ловит; удаление реальных user data, **не**
      классифицированных владельцем как disposable.
    - *Scope / explicit cleanup authorization:* legacy и test runtime/media,
      уже объявленные disposable, — `projects/**`, `music/**`,
      `assets/library/**`, `assets/cache/**`, `anime_factory/episodes/**`.
      Вне своего bounded cleanup slice эти пути остаются закрытыми; удаление
      разрешено **только** внутри PLAN-14C/14D/14E (или PLAN-L для legacy
      носителей), только по проверенному абсолютному пути и только после
      сверки с `Preserved runtime corpus` в `CLEANUP_REGISTRY.md`.
      Классификация «disposable» **не** является разрешением удалить: она лишь
      снимает вечность запрета.
    - *Смешанные каталоги:* `outputs/**` и `manual_assets/**` **не**
      блокируются целиком — под ними лежат tracked versioned-файлы. Для них
      используются точные подпути или типы runtime-файлов. `channels/**` и
      `content/**` не блокируются вовсе.
    - *Ask / explicit owner approval:* `git push`, создание remote,
      `git stash`, `git commit --amend`, сеть, provider search/download и
      paid API. Бессрочный hard deny для них не применяется, если permission
      system поддерживает ask-policy. Поддержка ключа `ask` проверяется внутри
      этого под-slice до записи правил; если ключ недоступен, эти действия
      остаются instruction-level требованием и в hard deny **не** переводятся.
    - *Записанная граница:* Claude permissions не защищают от произвольного
      Python-кода, запущенного через Bash. Выдавать deny-list за полную защиту
      запрещено.
    - *Limitation и fallback для scope-класса:* `.claude/settings.json` не
      знает, какой plan-step выполняется, поэтому «deny везде, кроме
      утверждённого cleanup slice» декларативно не выражается. Проверяется
      внутри под-slice: если доступен `ask`, disposable-пути получают `ask`, а
      не `deny`; если `ask` недоступен — они остаются в `deny`, и cleanup slice
      снимает правило **своим** commit, а не обходит его. Постоянный `deny`,
      который исполнитель PLAN-14E обязан обойти, не записывается: это ложная
      защита. Фактическую границу удержания держат `check_task_scope` (6D-2),
      `Preserved runtime corpus` и требование абсолютного пути.
    - *Почему не hook:* `.claude/settings.json` уже является владельцем этого
      ограничения и покрывает требуемое декларативно. Hook стал бы вторым
      владельцем одного правила.
    - *Фактический результат:* локальный Claude Code 2.1.219 подтвердил
      поддержку `permissions.ask` и распарсил итоговый settings. Permanent
      deny ограничен точными secret families для Read/Write/Edit,
      `git reset --hard`, bare/flagged `git clean`, force push и существующим
      `media-library migrate --apply`. Поддерживаемые ask rules добавлены для
      push/remote-add/stash/amend, WebFetch/WebSearch и перечисленных
      recursive cleanup primitives. Пять scope-controlled families и четыре
      mixed directories broad path rules не получили.
    - *Оставшееся instruction-level:* arbitrary Python/PowerShell/Bash не
      позволяет надёжно распознать любой network/provider/paid вызов или
      условие «только в активном cleanup slice». Эти границы продолжают
      удерживать owner approval, проверенный абсолютный путь и
      `Preserved runtime corpus`; частичные эвристики не добавлялись.
    - *Verification evidence (2026-08-02, исходный HEAD `3ee4e98`):*
      `python -m json.tool` и локальный Claude parser — exit code 0;
      permission structure — 15 ask и 43 deny rules; full tracked-path
      collision probe — 0; `.env` покрыт Read/Write/Edit; `.env.example` и
      `src/localization/secrets.py` имеют 0 deny matches; destructive Git и
      ask command probes зелёные; docs QA, onboarding tests и
      `git diff --check` — exit code 0. Production code, tests, hooks, agents,
      skills, tools и runtime data не менялись; сеть и платные действия не
      выполнялись.

#### PLAN-6D-2 — task-scope checker

- **status:** completed 2026-08-02.
- **CLI:** `python -m tools.qa.check_task_scope [--root REPO] --allow PATH
  [--allow PATH ...] [--allow-dir DIR ...]`. `--allow` означает exact
  repository path; `--allow-dir` — явный component-bounded directory scope.
- **contract:** allowlist передаётся конкретной задачей; рабочее дерево
  читается через `git --no-optional-locks status --porcelain=v1 -z
  --untracked-files=all --renames`. Учитываются staged и unstaged изменения,
  untracked, add, delete и rename; rename разрешён только когда разрешены old и
  new path. Неожиданный путь даёт `STOP_REQUIRED` и требует остановки/owner
  decision. Статусы `OK` / `STOP_REQUIRED` / `INVALID_INPUT` имеют exit codes
  0 / 1 / 2. Порядок rules, changes и unexpected paths стабилен.
- **path policy:** `\` и `/`, `.` и duplicate separators нормализуются;
  сравнение на Windows case-insensitive. Абсолютный путь принимается только
  внутри repository root; traversal, drive-relative path, путь вне root и
  разрешение всего root отклоняются. Простого строкового prefix нет:
  `src/news` не разрешает `src/news_backup`. Glob patterns не реализованы.
- **read-only boundary:** checker не читает содержимое изменённых файлов, не
  исправляет diff, не меняет index/worktree, не выполняет staging/commit и не
  хранит постоянного глобального списка файлов всех задач. Активный execution
  plan разрешён только когда вызывающая задача передала его путь.
- **residual limitations:** это working-tree scope checker, не commit-range
  reviewer PLAN-6E; он вызывается явно, а не hook/harness; ignored paths не
  входят в change set, который Git сообщает как working-tree status; rename
  classification использует read-only Git rename detection.
- **verification evidence:** `tests.test_check_task_scope` — 26 тестов,
  exit code 0: empty/allowed/unexpected, modified/added/deleted/renamed,
  staged/unstaged/untracked, обе стороны rename, stable multi-path output,
  Windows separators/case, boundary, traversal, inside/outside absolute paths,
  duplicate rules, Git failure, CLI statuses/exit codes и побайтовая
  неизменность временного `.git/index`. Current-diff smoke — `OK/0`; synthetic
  temporary Git smoke с unexpected path — `STOP_REQUIRED/1`; CLI help, docs
  QA, onboarding tests, `compileall tools\qa` и `git diff --check` — exit code
  0. Full offline suite не запускался: production/runtime behavior не менялся.

  *Owner:* пакет `tools/qa` уже является владельцем QA. Модуль
  `check_agent_docs.py` расширить нельзя: у него другой вход (статические
  инварианты репозитория против allowlist конкретной задачи) и другой
  lifecycle. Прецедент sibling-модуля уже утверждён в PLAN-6B
  (`check_repository_minimalism.py`), поэтому второго source of truth не
  возникает. *Exit condition:* модуль удаляется, если scope-контроль станет
  частью harness.

#### PLAN-6D-3 — Claude skill loading note

- **status:** completed 2026-08-02.
- **scope:** `CLAUDE.md`. Одно предложение о том, что `skills/` не
  загружаются автоматически и релевантный `SKILL.md` нужно открыть перед
  задачей. Содержимое skills не дублируется. `.claude/skills/` не создаётся:
  это был бы второй набор skills и нарушение ADR 0001.
  **Границы утверждения:** формулировка про отсутствие auto-discovery
  доказана для Claude Code [FACT]. Утверждение о поведении Codex в
  `CLAUDE.md` не записывается до skills discovery verification PLAN-6C/6E:
  оно пока имеет статус **[ПРЕДП]**.
- **фактический результат:** `CLAUDE.md` сохранил роль тонкого adapter и
  добавил только короткое правило: root `skills/` не считается автоматически
  загруженным; перед специализированной задачей Claude Code вручную открывает
  релевантный `skills/<skill-name>/SKILL.md`, применяет его вместе с
  `AGENTS.md`, актуальными repository docs, кодом и тестами, а фактическое
  состояние репозитория имеет приоритет над предположениями skill. Перечень и
  workflows skills не копировались; `.claude/skills/` не создан;
  Codex discovery не описывался.
- **verification evidence:** `check_task_scope` с разрешёнными `CLAUDE.md` и
  тремя current docs вернул `OK/0`; docs QA,
  `tests.test_stage2_agent_onboarding` и `git diff --check` завершились с exit
  code 0. Фактически существуют шесть root skills, `.claude/skills/`
  отсутствует; skills/tools/tests/src не менялись.
- **измеримый результат:** deny/ask отражают проверенные пути и не блокируют ни
  один tracked versioned-файл; `check_task_scope` возвращает `STOP_REQUIRED` на
  неожиданный файл и `OK` на разрешённый; `CLAUDE.md` объясняет загрузку
  skills; ни одного нового hook, agent или документа не создано.
- **required verification:** targeted tests `check_task_scope`, docs QA,
  `git diff --check`.
- **rollback:** один commit на под-slice.

### PLAN-6E — independent reviewer foundation

- **status:** completed · **completed:** 2026-08-02 · **commit:** Git log,
  trailer `Plan-Step: PLAN-6E`
- **цель:** один независимый read-only reviewer до первого destructive и
  high-risk production-slice.
- **роль в ревизии 2.1:** **BLOCKER первого destructive retirement / high-risk
  shared-contract slice** — PLAN-9B-2 (orca-hardcode с собственным тестом),
  PLAN-9B-3 (query-path cleanup), PLAN-9B-5b (retirement `apps/news_to_short`,
  у которого есть test-callers). **Дополнительно обязателен для PLAN-9A**
  (persisted bytes) **и PLAN-9C** (semantic decision path) — обе позиции уже
  входят в список «когда reviewer обязателен» ниже. Для PLAN-9B-0/9B-1
  необязателен: они не пересекают ни одну из этих boundary.
- **зависимости:** PLAN-6D. **Не является** blocker первого product fix.
- **разрешённые зоны:** `skills/review-change/`, `.claude/agents/`,
  `tools/qa/check_agent_docs.py` в части регистрации нового skill.
- **запрещено:** production-код, раздельные review policies для Claude и
  Codex, orchestrator, постоянная команда агентов, reviewer, исправляющий
  собственный finding.
- **обязательный порядок:** сначала доказать overlap с существующими skills.
  Новый owner создаётся только если ни один существующий skill не может быть
  безопасно доработан. `skills/architecture-change` для этого не подходит: он
  принадлежит implementer, и расширение сделало бы implementer собственным
  reviewer.
- **предусловие — разделено ревизией 2 (снят deadlock).** Прежняя формулировка
  блокировала 6E на skills discovery verification для Codex внутри PLAN-6C.
  [FACT] Codex в среде не установлен, discovery-check выполнить невозможно, а
  6E обязателен до PLAN-9A — план не мог продвинуться. Теперь:
  - **Claude-часть выполнима и обязательна сейчас.** [FACT] `skills/` не
    является `.claude/skills/`, auto-discovery нет: создаётся canonical
    `skills/review-change/SKILL.md` и тонкий adapter
    `.claude/agents/review-change.md`, поведение подтверждается controlled
    read-only acceptance ниже;
  - **Codex-adapter остаётся `[ПРЕДП]`** до фактической проверки discovery и
    6E не блокирует. Второй набор skills не создаётся ни при каком результате.
- **canonical policy — одна, model-independent:**
  - `skills/review-change/SKILL.md` — единственный источник review rules;
  - `skills/review-change/agents/openai.yaml` — тонкий adapter для Codex по уже
    существующему в репозитории шаблону;
  - `.claude/agents/review-change.md` — тонкий adapter для Claude, который
    ссылается на canonical skill и не дублирует правила.
- **поведение reviewer:** работает read-only; проверяет конкретный immutable
  commit или явно заданный diff; не редактирует файлы; не исправляет findings;
  не создаёт commit; не обновляет этот план; не меняет checkpoint; выдаёт
  findings по severity с `file:line`, evidence, impact и smallest safe
  correction; отдельно перечисляет executed checks, skipped checks и residual
  risks; проверяет task scope, duplicate owner, compatibility, persisted state,
  paid/network behavior и фактическую эффективность тестов; после repair
  выполняет повторный review.
- **разделение ролей (уточнено ревизией 2).** Implementer **активно ищет лучший
  способ** решить задачу, свободен внутри allowed scope, вправе оспорить план и
  предложить альтернативу. Reviewer работает **консервативно**: ищет нарушения,
  duplicate owner, contract break, architecture drift, unsafe data handling,
  rights violations, unverified success, regression. Implementer и reviewer не
  являются одним контекстом; repair выполняет implementer после подтверждения
  findings владельцем.
- **обязательный класс findings «unmet objective / premature stop».** Reviewer
  проверяет не только нарушения, но и обратное: не остановился ли implementer на
  соблюдении процедуры, не достигнув SUCCESS CRITERIA и не попытавшись найти
  альтернативу. Без этого класса reviewer не ловит именно тот сбой, ради
  которого пересмотрена модель автономии.
- **техническое подтверждение read-only, определяется до реализации:**
  отсутствие Write/Edit в наборе инструментов adapter; безопасный набор
  read-only Git/search команд; сравнение `git status` и `git diff` до и после
  review. Review считается неуспешным, если working tree изменён reviewer-ом.
- **когда reviewer обязателен:** persisted state, manifests, resume, providers,
  asset selection, semantic/Vision, rights/provenance, paid/TTS, rendering,
  package boundaries, shared contracts, compatibility retirement, runtime
  migration. Для простой Markdown-правки не требуется.
- **измеримый результат:** существует ровно одна canonical review policy и не
  более двух тонких adapters; read-only подтверждается технически, а не
  обещанием; reviewer не может закрыть собственный finding.
- **controlled read-only acceptance (обязательна).** `docs QA` и
  `git diff --check` доказывают только целостность документов: `--check` ищет
  whitespace-ошибки и конфликтные маркеры и не сравнивает состояние дерева.
  Поэтому поведение reviewer проверяется отдельной контролируемой процедурой,
  результат которой записывается как evidence слайса:
  1. зафиксировать `git status --short --branch` и `git diff --stat` до review;
  2. запустить reviewer на конкретном immutable commit;
  3. повторно снять `git status` и `git diff` и доказать отсутствие изменений;
  4. прогнать один заведомо безопасный diff — ожидается отсутствие findings
     или только информационные;
  5. прогнать один synthetic diff с известным нарушением — ожидается, что
     нарушение найдено с `file:line`, evidence, impact и smallest safe
     correction;
  6. подтвердить, что reviewer нарушение **не исправил**, файлов не изменил и
     commit не создал.
  Review считается неуспешным, если working tree изменён reviewer-ом.
  Synthetic diff создаётся во временном каталоге вне репозитория и в Git не
  попадает. Отдельная автоматизация и новый QA-модуль для этого не создаются:
  процедура выполняется один раз при закрытии слайса.
- **реализовано:** canonical owner — `skills/review-change/SKILL.md`; тонкие
  adapters — `skills/review-change/agents/openai.yaml` и
  `.claude/agents/review-change.md`. Claude adapter использует `model: sonnet`,
  `permissionMode: plan`, только `Read/Glob/Grep/Bash` и прямо запрещает
  Write/Edit, сеть и repair. Canonical policy требует независимый контекст,
  read-only before/after proof, review scope/objective, duplicate owners,
  compatibility, persisted/network/rights boundaries, tests, findings и
  повторный review после repair. Для Git-read launcher устанавливает
  `GIT_OPTIONAL_LOCKS=0`, а reviewer использует `git --no-optional-locks`.
- **QA contract:** `tools.qa.check_agent_docs` регистрирует седьмой skill,
  проверяет обязательные canonical/adapter поля, точный read-only toolset,
  отсутствие дублирования policy и обязательное отключение optional Git locks.
  `tests.test_check_agent_docs` содержит positive и negative characterization.
- **controlled acceptance evidence (2026-08-02):** Claude Code 2.1.218,
  `--model sonnet --effort high`; фактически выбран `claude-sonnet-5`. Сеть была
  разрешена только к Anthropic; WebSearch/WebFetch, другие providers, downloads,
  Vision, TTS и render не выполнялись.
  - Case A на immutable commit `619c817cb1d7234799a32c8fd7d567633b2b470b`:
    первый model-run вернул PASS без findings, но launcher доказал изменение
    только `.git/index` stat cache при неизменных HEAD/status/diff. Acceptance
    объявлена FAIL; policy и adapter дополнены обязательным отключением optional
    locks. Свежая независимая re-review session после repair вернула PASS/PASS,
    findings `[]`; HEAD, porcelain, staged/unstaged diff и байты/mtime index
    совпали до/после.
  - Case B во внешнем временном synthetic repository: безопасный bounded diff
    принят, findings `[]`, scope PASS, objective PASS; authoritative launcher
    подтвердил byte-stable index и неизменные HEAD/status/diff.
  - Case C в отдельном внешнем synthetic repository: неизвестное reviewer-у
    нарушение найдено как BLOCKER в новом `src/second_owner.py`; evidence —
    второй owner нормализации вне allowed scope с расходящейся семантикой;
    smallest safe correction — удалить весь hunk. Scope/objective — FAIL/FAIL;
    launcher подтвердил, что reviewer ничего не исправил и repository не изменил.
  - Repair cycle выполнен новым Claude session; shell-capability остаётся
    residual risk, сдерживаемый exact tool allowlist, plan mode, запретом сети и
    внешним byte-level proof. Два ранних `--json-schema` запуска завершились
    локальной parser-ошибкой до model call; successful model calls — четыре,
    суммарная reported cost `$1.4021283`.
- **verification evidence:** `tests.test_check_agent_docs` — 58 тестов;
  `tests.test_stage2_agent_onboarding` — 3 теста; docs QA,
  `compileall tools\qa`, task-scope checker по восьми разрешённым путям и
  `git diff --check` — exit code 0. Числа тестов — измерения, не нормативы.
- **required verification:** controlled read-only acceptance (шаги 1–6),
  docs QA, `git diff --check`.
- **rollback:** один commit.

### PLAN-7 — канонический пользовательский CLI в документации

- **status:** pending · **completed:** — · **commit:** —
- **цель:** документация перестаёт обучать устаревшему entrypoint.
- **зависимости:** PLAN-6A. **Параллельный: product-работу не блокирует**
  (изменено ревизией 2).
- **взаимодействие с PLAN-L.** L4 удаляет `pipeline.py`, поэтому 24 упоминания
  `pipeline.py` в `COMMANDS.md` исчезают как факт, а не переписываются. Если L4
  выполнен раньше PLAN-7 — сверять по фактическому `--help`, а не по этому
  списку.
- **язык (OD-5).** `README.md` сокращается примерно до 150 строк; русская
  редакция получается **побочно при переписывании**, отдельным переводом это не
  оформляется и mass-diff не создаёт. Правило: не переводить filenames,
  directory names, identifiers, CLI/API, JSON/YAML keys, точные команды, имена
  библиотек, литералы, блоки кода, third-party licenses и historical artifacts.
  Каталоги `docs/archive/`, `docs/audits/` и `docs/implementation/` в scope
  перевода не входят как historical.
- **исправлено owner decision 2026-08-05 (OD-S-7).** Прежнее требование
  «`COMMANDS.md` — 100–150 строк» отменено: файл **удаляется**, а не
  сокращается. Новый контракт:
  - canonical command reference — `python -m ai_youtube --help`;
  - quick start — `README.md` (около 150 строк: фактический продукт,
    active/planned/disabled, быстрый старт);
  - workflows — существующие `skills/`;
  - contracts — канонический CLI;
  - `COMMANDS.md` — deletion target;
  - **replacement command document запрещён**: второй каталог команд не
    создаётся ни под каким именем;
  - краткая semantics `project rights-report` переносится в существующий
    `skills/replace-visual-slot/SKILL.md`;
  - historical archive/audit evidence массово не переписывается.
- **разрешённые зоны:** `README.md`, `COMMANDS.md` (только удаление),
  `skills/create-short-video-first/SKILL.md`, `skills/resume-project/SKILL.md`,
  `skills/replace-visual-slot/SKILL.md`,
  `docs/contracts/STAGE1_PUBLIC_CONTRACTS.md`.
- **запрещено:** production-код, **удаление старых entrypoints**, создание
  нового command-каталога взамен `COMMANDS.md`.
- **требования:** команды сверять с фактическим `--help`, а не по памяти; после
  удаления `COMMANDS.md` ни один оставшийся документ не должен на него
  ссылаться как на current source.
- **измеренный масштаб расхождения** (Foundation audit, [FACT] от `4ca3655`):
  `README.md` — 405 строк, упоминаний `ai_youtube` **0**, учит bare `python`
  и `pip` вопреки `AGENTS.md`; `COMMANDS.md` — 681 строка, упоминаний
  `ai_youtube` **0** против 49 × `src.content_creation.cli` и 24 ×
  `pipeline.py`; три `SKILL.md` учат `src.content_creation.cli`;
  `docs/contracts/STAGE1_PUBLIC_CONTRACTS.md` называет
  `src.content_creation.cli` «current CLI» и канонический CLI не упоминает.
  Это измерение, а не норма.
- **`docs/contracts/` — порядок:** файл добавлен в зоны потому, что обучает
  устаревшему entrypoint и до сих пор не входил ни в один slice (registry
  C22). Его **target responsibility** решает PLAN-12E по содержимому; PLAN-7
  правит только утверждения о каноническом CLI и не перемещает файл.
- **измеримый результат:** ни один из этих файлов не обучает устаревшему пути.
- **required verification:** docs QA + `smoke`.
- **rollback:** один commit.

### PLAN-8 — PRODUCT_PLAN.md

- **status:** pending · **completed:** — · **commit:** —
- **цель:** отделить продуктовую цель и evidence от архитектурного порядка.
- **зависимости:** PLAN-7. **Параллельный: product-работу не блокирует**
  (изменено ревизией 2 — прежде PLAN-8 стоял в prerequisite-цепочке 9A).
- **разрешённые зоны:** `docs/current/PRODUCT_PLAN.md`.
- **запрещено:** создание `ARCHITECTURE_DEBT.md` до того, как PLAN-1 докажет
  фактический пробел относительно `CLEANUP_REGISTRY.md`.
- **измеримый результат:** продуктовый приоритет, измеренная база и критерии
  M1/M2/M3 зафиксированы; отдельно записан post-rescue roadmap:
  `video_repurposer` через migration Anime Factory и будущий
  longform/documentary workflow `content_creator`, с entry/enable evidence и
  без создания новых engine stacks. Ориентир до 250 строк.
- **обязательные roadmap-записи ревизии 2.1** (PLAN-8 — **roadmap owner**, не
  implementation owner ни одной из них):
  - **post-rescue roadmap `video_repurposer` (OD-23):** Content Creator stable →
    UI Content Creator → отдельный deep audit Anime Factory → классификация
    каждой capability `KEEP · MIGRATE · REWRITE · SHARE · DELETE` → Video
    Repurposer из существующего Anime Factory + shared core → его UI. Второй
    clip pipeline с нуля запрещён; deep audit Anime Factory ближайшим шагом
    **не** является;
  - **future AI / advanced editing note (OD-17, OD-20):** `NO IMPLEMENTATION ·
    NO PLACEHOLDER PACKAGES · NO SPECULATIVE INTERFACES · NO NEW BLOCKERS`.
    Future AI layer подключается **сверху** к существующему production
    pipeline: `AI research / script layer → тот же prepared content contract →
    существующий downstream video production engine`. `LLMScriptProvider` уже
    зарегистрирован как `planned` — этой точки подключения достаточно;
  - **future-proofing rule:** downstream production pipeline не должен
    предполагать, что script создан внутри AI-YouTube. Prepared external
    content (человек, внешний AI, ручной ввод) — **first-class input**;
  - **product-quality item «несколько lossy generations в final render»**
    (registry C45). Фактический нормальный путь: segment encode CRF 23 →
    concat **`-c:v copy`** → audio + exact-duration encode CRF 20 → ASS
    subtitle encode CRF 21 → copies. Concat **не перекодирует**; CRF 20
    принадлежит duration-control mux и имеет документированную причину
    (`-shortest` + `-c:v copy` промахивается по длительности). Три lossy
    generations возникают при **audio + ASS subtitles**. «Single-pass как
    простой fix» — неверно. Первый разумный кандидат будущего renderer-слайса:
    объединить audio/duration encode и subtitle burn в один encode, **если
    characterization докажет эквивалентность**; полный filtergraph single-pass —
    отдельное более крупное исследование. **PLAN-8 хранит запись; implementation
    owner — будущий bounded renderer slice с characterization первым. Нового
    PLAN-ID сейчас не создаётся.**
    **Уточнено 2026-08-01:** этот «будущий bounded renderer slice» теперь имеет
    предложенную форму — candidate slice `MOTION-CS1` (см. «Unscheduled
    candidate slices — Motion family»). Он остаётся unscheduled и PLAN-ID не
    получает. Дополнительное условие: characterization C45 невозможна без
    baseline visual regression (registry C61), поэтому регрессия идёт первой;
  - **roadmap Motion Design and Multi-Renderer Composition (2026-08-01).**
    PLAN-8 — **roadmap owner** и этого направления тоже, implementation owner —
    нет. Продуктовая запись находится в `PRODUCT_PLAN.md`, раздел «Motion
    Design and Multi-Renderer Composition»; owner decisions — в разделе «Owner
    decisions: motion rendering» этого файла; findings — C53–C62 реестра.
    Обязательное содержание roadmap-записи: несколько специализированных
    авторов кадра при **одном** FFmpeg-сборщике · один `composition_type` —
    один canonical backend · stock FFmpeg path сохраняется и дорабатывается ·
    **новый video pipeline не создаётся** · Node остаётся опциональным с
    безопасным fallback. Longform и horizontal по-прежнему остаются форматом и
    шаблоном поверх общего core, а не отдельным pipeline;
- **решение по отдельному `EVALUATION_STRATEGY`:** принимается **после** того,
  как `PRODUCT_PLAN.md` написан, и **по качественным критериям**, а не по
  объёму файла: отдельная responsibility; отдельные readers; отдельный
  lifecycle; смешение контрактов; routing ambiguity; maintenance coupling.
  Количество строк — measurement и warning signal, оно может подтверждать
  проблему, но само по себе новый файл не создаёт. Числовой порог объёма как
  условие extraction не задаётся.
- **`PRODUCT_PLAN.md` уже существует (слайс PRODUCT-ROADMAP → PRODUCT-PLAN-1,
  2026-08-01).** PLAN-8 **расширяет и проверяет существующий документ** и
  **не создаёт второй competing planning document**: третий плановый документ
  по-прежнему запрещён. Разрешённая зона не меняется — это тот же путь.
  Уже записанные там owner-approved решения (committed capabilities, границы
  Vision, UI direction, MSP direction, warehouse, candidate slices, owner
  decisions pending) при расширении сохраняются, а не переписываются.
  Status, порядок и prerequisites PLAN-8 этим не меняются.
- **зафиксировано продуктовым документом, здесь только как non-goal:** longform
  и documentary остаются **форматом/шаблоном/workspace поверх общего core** и
  не становятся отдельным pipeline или третьим приложением; расширение проверки
  качества по готовому файлу принадлежит существующему quality owner и **новым
  Quality Engine не оформляется**.
- **обязательное завершение:** продуктовые подробности PLAN-9–PLAN-11
  (лестницы, M1/M2/M3, reference domains и quality evidence) переносятся в
  `PRODUCT_PLAN.md`. В этом execution plan остаются только ID, зависимости,
  allowed/prohibited zones, gates, verification и rollback.
  До проверенного переноса текущие подробности не удалять.
- **required verification:** docs QA.
- **rollback:** один commit.

### Продуктовая рамка PLAN-9 и PLAN-10: где именно дыра в asset-search

Зафиксировано ревизией 2, чтобы будущий агент не начал строить то, что уже
построено.

**Не является дырой.** `src/assets/completion/` уже владеет лестницей выбора
`A_exact → B_composite → C_good_context → D_partial → E_generated → F_emergency`
с жёстким фильтром `modes.blocking_reasons` (неизвестные или запрещённые права,
битый файл, `must_avoid`, заявленное противоречие, evidence на другой предмет) и
детерминированным `tie_break_key`, не зависящим от того, какой provider ответил
первым. Rung E — сгенерированная по спецификации сцены диаграмма, rung F —
project-owned нейтральная карточка, которая ничего не утверждает. Это canonical
owner completion-состояний; он сохраняется, пока дальнейшее evidence не докажет
дефект boundary. Второй словарь состояний не вводится.

**Является дырой — всё выше по потоку** (карта исправлена ревизией 2.1: над
генерацией запросов находятся ещё две ступени):

```
prepared content / topic
  → [CRITICAL-2] source material: topic не является материалом; thin input
                 молча уходит в LegacyTemplateScriptProvider, а
                 script_validation остаётся "passed"
  → research     (в текущем scope дефектом не является)
  → script       (DeterministicScriptProvider исправен при наличии материала)
  → visual plan  (intents на языке сценария; translation_required выставляется
                  и никем не читается)
  → [CRITICAL-1] provider language: единственный канал доставки английского
                 запроса — visual_brief, а заполняет его только topic-hardcode.
                 GLOSSARY матчится подстрокой → ложные срабатывания и
                 морфологические пропуски. source_is_latin — свойство набора,
                 поэтому английский alternative выбрасывается вместе с русским
  → providers    (нет pagination — PLAN-10B/10C; эффект только после CRITICAL-1)
  → semantic     (metadata-слой РЕШАЕТ; платный Vision подаёт evidence поздно —
                  PLAN-9C)
  → completion   (работает; canonical owner; не трогать)
```

| Что | Owner-слайс |
|---|---|
| честность источника сценария (`topic` → template) | **PLAN-9B-4** |
| канонический вход «исходный текст» | **PLAN-9B-5a** |
| integrity provider-language query adapter | **PLAN-9B-1** |
| provider-language VisualBrief producer | **PLAN-9B-PRODUCER** |
| лестница расширения и снятие topic-hardcodes | **PLAN-9B-2** |
| retirement устаревших query-путей | **PLAN-9B-3** |
| semantic/Vision producer → existing consumer wiring | PLAN-9C |
| best-so-far persistence через `resume` | PLAN-9A |
| ledger попыток и причины остановки | PLAN-10A |
| pagination и provider exhaustion | PLAN-10B |
| adaptive budget, plateau, порядок эскалации | PLAN-10C |
| global local stock library convergence | PLAN-10D |
| альтернативная правдивая визуальная стратегия | PLAN-9B + PLAN-10C |

**Скрытая связь двух findings.** Сегодня шаблонный сценарий не доезжает до
publish только потому, что все сцены `missing` из-за CRITICAL-1. Как только
CRITICAL-1 починят, шаблонный сценарий поедет в publish беспрепятственно.
Поэтому CRITICAL-2 **не откладывается** за CRITICAL-1, а идёт внутри той же
цепочки PLAN-9B.

**Hard constraints отбора** (класс `[HARD]`, не предмет торга ни при каком
качестве): factual truth · rights и provenance · `must_avoid` ·
misleading/conflict · paid approval.

**Heuristics отбора** (класс `[HINT]`, агент вправе изменить с обоснованием,
пока не доказано обратное): приоритет провайдеров · число и виды запросов ·
пороги `minimum_confidence` и `hard_reject_confidence` · предпочтительный тип
визуала для сцены · размер shortlist.

### PLAN-9A — best-so-far foundation и tolerant persistence/resume

- **status:** blocked · **commit:** —
- **prerequisite chain (единственная действующая, ревизия 2.1):**
  `PLAN-9B-2` + `PLAN-1C′` + **`PLAN-6E`**. Прежняя цепочка
  `…PLAN-5 → PLAN-6A → PLAN-6D → PLAN-6E → PLAN-1C′` отменена ревизией 2.1:
  PLAN-5 и PLAN-6A параллельны, PLAN-6D входит транзитивно как предусловие
  PLAN-9B-2, а PLAN-6E записан **явно** из-за persisted-state boundary, а не
  транзитивно. Отдельный owner approval на сам слайс не требуется, потому что он
  **уже выдан**: persisted-bytes tripwire срабатывает, и утверждение ревизии 2
  покрывает его ровно в описанном здесь объёме — см. «Decision rights → Уже
  выданные owner approvals». Tripwire этим не отменён: любое
  persisted-изменение сверх состава и ограничений ниже требует нового approval.
- **изменено ревизией 2.1 — только место, не состав.** PLAN-9A выполняется
  **после** PLAN-9B: best-so-far persistence бессмысленна до того, как система
  получает нормальные provider-ready candidates (OD-15). Состав, ограничения,
  additive schema, tolerant reader, уже выданный owner approval и success
  criteria сохраняются дословно. Первым product-слайсом программы становится
  PLAN-9B-0/9B-1.
- **цель:** до расширения поиска гарантировать, что лучший найденный материал
  не теряется между итерациями и при `resume`.
- **состав:** top candidates по сцене, best-so-far с обоснованием, semantic
  score, rights status, Vision/evaluation result, manual approvals, выбранный
  fallback. Расширяет существующие `rejected_candidates`/`rejected_reasons`;
  второй manifest или project system не создаётся.
- **логическая когезия search-session state (OD-24).** PLAN-9A, PLAN-10A,
  PLAN-10B и PLAN-10C логически описывают **одно** состояние одного поиска.
  Это проектное требование, а **не** новый файл: `search_session.json` как
  отдельный persisted owner **не создаётся и не утверждается**; четыре
  независимые persisted schemas заранее не утверждаются. До выбора physical
  representation обязательно проверить существующих owners — `job.json`, asset
  manifest, project state, completion/resume state. **Если существующего owner
  можно расширить, новый persisted файл запрещён.** Разбиение implementation на
  bounded commits когезии не нарушает: она относится к схеме и владению.
- **ограничения:** additive schema/tolerant reader; старые manifests и resume
  читаются без миграции; characterization-first.
- **измеримый результат:** после остановки, ошибки или resume сохранённый
  best-so-far не ухудшается и остаётся объяснимым.
- **required verification:** targeted persisted-contract tests + `full`.
- **rollback:** один commit.

### PLAN-9B — input/query truth (bounded family)

- **status:** pending. **Первый product-этап программы** (ревизия 2.1);
  PLAN-9A его больше не блокирует.
- **цель семейства:** **input/query truth — provider-language adaptation,
  query expansion, truthful source input и cleanup старых query paths.**
- **зависимости семейства:** `PLAN-1D-routing → PLAN-2 → PLAN-3 → PLAN-4`.
  Дальнейшие gates — **по risk boundary каждого под-слайса**, см. таблицу
  «Risk-boundary таблица safety gates».
- **новый top-level PLAN-ID не создаётся (E-13):** CRITICAL-2 размещается
  bounded под-слайсами внутри PLAN-9B.
- **порядок выполнения** (идентификаторы под-слайсов — **не** порядок; прецедент
  PLAN-6D/PLAN-12/PLAN-13):

  ```
  PLAN-9B-0 → PLAN-9B-1 → PLAN-9B-5a → PLAN-9B-4
  → PLAN-L0 → PLAN-9B-PRODUCER
  → [post-audit stabilization gate: PLAN-STAB-1…7
     + independent stabilization review] → PLAN-9B-2 → PLAN-9B-3
  PLAN-9B-5b — после успешной миграции capability и готовности его
               destructive gates
  ```

  PLAN-L0 остаётся отдельным knowledge-salvage owner, а
  PLAN-9B-PRODUCER — отдельным visual-planning user outcome; включение их в
  последовательность не смешивает scope трёх слайсов.

- **фактический owner remote-запросов (OD-14).** [FACT]
  `src/assets/semantic_selection/query_generator.py` **не участвует** в
  формировании запросов к remote-провайдерам: его callers питают
  envato-метаданные и отчёты. Единственные точки контакта с провайдером —
  `build_scene_queries` и `build_slot_queries` в `src/assets/query_adapter.py`;
  других путей к remote-провайдеру в активном workflow нет. Прежняя allowed
  zone ревизии 2 была ошибочной и заменена.
- **граница семейства сохраняется:** лестница заканчивается на генерации
  запросов. Переход к локальной медиатеке, к другому provider и к разрешённому
  fallback — routing/completion policy; владельцы — PLAN-10C (порядок
  эскалации), PLAN-10B (provider contract), PLAN-10D (global local library).
- **regression по разным доменам (OD-25):** после каждого существенного
  под-слайса, где это релевантно, проверять репрезентативные темы минимум из
  разных классов (animals/wildlife · energy/technology · geography/
  infrastructure). PLAN-11 остаётся финальным product evidence gate, но не
  первой multi-topic проверкой.
- **тесты T1–T11** из `docs/audits/CRITICAL_INPUT_SEARCH_DEEP_DIVE_2026-07-31.md`
  распределены как regression/product tests по под-слайсам ниже. Отдельный
  диагностический этап под них **не создаётся** (OD-11).
- **отношение к motion-направлению (OD-M-13, добавлено 2026-08-01).** PLAN-9B
  является **стоковой/провайдерской половиной** будущего формата Hybrid
  Explainer, а не его предшественником: гибридная сцена совмещает стоковый
  материал с motion-композицией, и стоковая часть зависит именно от корректных
  provider-запросов. Motion-направление эту семью **не заменяет, не откладывает
  и не ускоряет**; порядок, состав и статусы PLAN-9B этой записью не меняются.
- **rollback:** один commit на под-slice.

#### PLAN-9B-0 — characterization текущего поведения

- **status:** completed · **completed:** 2026-08-01 · **commit:** —
- **зависимости:** PLAN-4.
- **цель:** зафиксировать фактическое поведение **до** правки, чтобы диффы были
  доказуемы. **Ноль production-изменений**, ноль сети, ноль денег.
- **разрешённые зоны:** новый offline test-модуль и evidence в этом плане.
- **фиксируется:** фактическое число provider `search()`-вызовов на тему ·
  source каждого запроса · уникальные отправленные строки, включая ложные
  `ice researchers` и чрезмерно общий `station` · число провайдеров,
  пропущенных по `translation_required` · `legacy_template` при
  `script_validation == passed` · **persisted содержимое `query_plan` до
  изменения** (байты `assets_manifest.json` меняются даже при
  не-schema-level правке).
- **тесты deep-dive:** T10, T11.
- **risk boundary:** нет.
- **required verification:** targeted + активный `network_guard`.
- **зафиксированное текущее поведение:** через canonical application chain
  `create_content → fullscreen_voiceover → run_news_to_short_job →
  build_news_asset_manifest → build_scene_queries → search_provider` пять
  English-only fake providers получили production-built `AssetSearchRequest`.
  Для тем про ворон / солнечную электростанцию / канал через пустыню выполнено
  соответственно 10 / 50 / 10 вызовов `search()`; уникальные строки —
  `ice researchers` / (`station`, `ice researchers station`) /
  `ice researchers`. Source всех отправленных `ProviderQuery` —
  `deterministic_glossary`. Пропущено по `query_translation_required`
  соответственно 25 provider-scene попыток в 5 сценах / 5 попыток в 1 сцене /
  25 попыток в 5 сценах; source пропущенных entries — `visual_brief_fields`.
  Это characterization известных дефектов, а не их исправление.
- **persisted characterization:** тест читает реальный temporary
  `assets/assets_manifest.json`; для каждой темы проверен минимальный subset 30
  `query_plan.queries`, включая provider, query, status, source и
  `untranslatable_providers`. Manifest writer и query builders не patch'ились.
- **input/script characterization:** недостаточный topic-only factual input
  сохраняет `script_provider == "legacy_template"`, metadata
  `fallback_reason == "insufficient_source_material"` и одновременно
  `script_validation.status == "passed"`. Поведение только зафиксировано.
- **фактическая verification (2026-08-01, HEAD до слайса `c4aeff6`):**
  - `.\venv\Scripts\python.exe -B -m unittest
    tests.test_input_query_truth_characterization` — exit code 0 двумя
    последовательными прогонами: 2 теста за 74.191 и 73.016 секунды;
  - `.\venv\Scripts\python.exe -B -m unittest
    tests.test_visual_retrieval_repair tests.test_script_engine_pipeline
    tests.test_news_asset_manager_contract tests.test_content_creation_service`
    — exit code 0, 118 тестов за 26.004 секунды;
  - package-wide `tests/network_guard.py` оставался активным; fake providers не
    выполняют HTTP, `blocked_attempts` не изменился; сеть, download, Vision,
    TTS, paid calls и render не выполнялись;
  - production-код не менялся; full suite не запускался, `baseline_head`
    остаётся `84bdd8b4f64c7adaf7582bdb39b15b18163253fb`.

#### PLAN-9B-1 — provider-language / query foundation

- **status:** completed · **completed:** 2026-08-01 · **зависимости:**
  PLAN-9B-0.
- **фактический owner:** `src/assets/query_adapter.py`.
- **исправленный контракт (owner decision 2026-08-01).** Первоначальный T1
  требовал от adapter-only слайса тематически переводить произвольный raw
  Russian topic и поэтому был невыполним без topic literals, translator/model
  или upstream producer. Он заменён на **T1A:** prepared VisualBrief, explicit
  provider queries и безопасные English intents/alternatives дают несколько
  provider-ready candidates; **T1B:** unknown raw source-language intent без
  такого evidence остаётся fail-closed. PLAN-9B-1 закрывает integrity adapter,
  а **не** создание перевода.
- **разрешённые зоны:** `src/assets/query_adapter.py` и его тесты.
- **reuse (OD-13) — новых сущностей не создаётся:** `VisualBrief` ·
  `SceneVisualPlan` / `VisualSearchIntent` · `ProviderQuery` ·
  `build_scene_queries` / `build_slot_queries` · provider contracts.
  **Не создавать** `TranslatorService`, `SearchEngine`, `QueryOrchestrator` и
  второй query pipeline.
- **реализованный механизм:** explicit provider queries → English VisualBrief
  fields → structured/source intents → bounded deterministic seed. Для каждого
  candidate отдельно определяется фактический язык; затем выполняются Unicode
  NFKC normalization, whitespace/casefold key и stable deduplication. Canonical
  `visual_intents` являются structured provenance; добавленный upstream только
  в flat `alternative_queries` generic legacy broad fallback не считается
  semantic evidence. Для tolerant старых flat plans четыре существующих
  compatibility outputs также не повышаются до успешной adaptation.
- **deterministic seed:** substring matcher заменён Unicode-aware token/phrase
  matcher. Ограниченное suffix matching распознаёт доказанные формы
  `пустыню` / `пустыни` / `пустыней`, но `лед` больше не совпадает внутри
  `исследователи`. Generic roles/modifiers/facilities вроде `researchers` и
  `station` без semantic anchor не выпускаются как успешный query.
- **fail-closed сохранён.** При неуверенности по-прежнему
  `translation_required`, а не догадка. Догадки как factual query не
  отправляются. «Просто отправлять русский текст провайдеру» — откат к уже
  измеренному нулевому результату и запрещён.
- **`ProviderQuery.source` — E-2 закрыт.** Это существующее свободное строковое
  telemetry-поле: **не** schema-level change, tolerant reader не требуется,
  persisted-bytes tripwire не срабатывает. Temporary real
  `assets_manifest.json` подтвердил новые values в существующем `query_plan`
  без нового field/version/layout.
- **T1A/T1B–T5:** T1A — два explicit VisualBrief queries и два structured
  English alternatives реально получены каждым из пяти fake providers;
  normalized duplicate и Cyrillic explicit entry отфильтрованы, sources равны
  `explicit_override` / `provider_supports_source_language`. T1B — raw Russian
  intent с одним generic legacy broad fallback не отправляет fallback и даёт
  `query_translation_required`. T2 — «Исследователи…» не даёт `ice`. T3 — два
  English alternatives переживают Russian primary. T4 — три формы пустыни дают
  `desert` с source `deterministic_glossary`. T5 — unknown intent без evidence
  остаётся `query_translation_required` и не вызывает provider.
- **characterization migration:** query/provider assertions в
  `tests/test_input_query_truth_characterization.py` стали regression contract
  PLAN-9B-1; отдельный topic-only assertion по-прежнему требует
  `legacy_template`, `fallback_reason="insufficient_source_material"` и
  `script_validation.status="passed"` как pre-fix evidence будущего PLAN-9B-4.
  Instrumented canonical measurement: вороны — 0 calls, 30 translation skips;
  солнечная станция — 0 calls, 30 translation skips; канал — 50 fake-provider
  search calls, unique `desert` / `desert researchers`, 25 completed entries с
  source `deterministic_glossary` и 5 translation skips. Это измерение, не
  invariant; ни один случай не выпустил `ice`, misleading `station` или
  `nature science wildlife observation`.
- **оставшийся product gap / follow-up constraint:** arbitrary raw-topic
  provider-language generation **не реализована** и не заявляется. Реальный
  producer должен заполнять существующий VisualBrief contract до product
  evidence gate или утверждения поддержки произвольной русской темы. Точный
  механизм — manual/prepared, local model или optional separately approved
  model — требует отдельного owner decision; новый query owner в этом слайсе не
  создавался. Upstream `legacy_broad_query` не удалён; его окончательный
  retirement остаётся follow-up cleanup после работающей замены.
- **фактическая verification:**
  - `.\venv\Scripts\python.exe -B -m unittest
    tests.test_input_query_truth_characterization` — два окончательных
    последовательных прогона, 3 теста, exit code 0 за 74.852 и 75.004 секунды;
  - `.\venv\Scripts\python.exe -B -m unittest
    tests.test_visual_retrieval_repair tests.test_visual_retrieval_regression
    tests.test_slot_aware_retrieval` — 75 тестов за 1.574 секунды, exit code 0;
  - `.\venv\Scripts\python.exe -B -m unittest
    tests.test_script_engine_pipeline tests.test_news_asset_manager_contract
    tests.test_content_creation_service
    tests.test_news_to_short_provider_integration` — 82 теста за 33.120
    секунды, exit code 0;
  - active package network guard остался чистым; сеть, model/provider API,
    download, Vision, TTS, paid calls и render не выполнялись;
  - full suite не запускался: public signatures и schema/layout не менялись,
    production diff остался внутри одного canonical owner, targeted radius
    зелёный; `baseline_head` остаётся
    `84bdd8b4f64c7adaf7582bdb39b15b18163253fb`.
- **risk boundary:** локальное поведение одного owner; ноль public/paid/
  destructive. Достаточно 1D/2/3/4.
- **required verification:** выполнена targeted verification; full не требовался
  по фактическому diff.

#### PLAN-9B-5a — additive source-text canonical input (CRITICAL-2, часть 1)

- **status:** completed · **completed:** 2026-08-02 · **commit:** — ·
  **зависимости:** PLAN-9B-1.
- **исправлено 2026-08-01 — source text уже частично существует.** [FACT]
  канонический `python -m ai_youtube create` через `--pasted-script` /
  `--script-file` при текущем default/legacy unspecified `content_input_mode`
  уже проводит подготовленный исходный текст в тот же downstream
  (`text` / `text_file` → deterministic/extractive script path). Формулировки
  «канонический CLI не имеет source-text входа» и «`--text`/`--text-file` —
  единственная уникальная capability» **опровергнуты** и не возвращаются.
- **цель (переопределена):** сделать source-material input **явным first-class
  canonical contract**: выбрать owner-approved public naming; убрать
  зависимость от implicit/legacy unspecified mode; валидировать intent;
  документировать; покрыть smoke/test public behavior; сохранить prepared
  external content как first-class input. Слайс **не** создаёт новый script
  engine и **не** создаёт capability с нуля.
- **additive: `apps/news_to_short` в этом слайсе не удаляется.**
- **реализованное owner-approved public naming:** `--source-text` и
  `--source-text-file`. `--pasted-script` и `--script-file` остаются видимыми
  compatibility aliases тех же destinations. `--text` не менялся и остаётся
  Story Card headline. Новые persisted/internal enum-like значения не
  вводились: используются существующие `pasted_script` / `script_file`.
- **normalization/validation owner:** общий
  `src/content_creation/request_builder.py`; только CLI request получает
  explicit mode при source-text input. Legacy programmatic request с
  `content_input_mode=""` остаётся tolerant и проходит прежнюю unspecified
  ветку. Existing `input_validation` проверяет пустой inline input и файл;
  conflicting authoritative inputs и несовместимый `--input-mode` дают
  прежний structured CLI error shape до application service/pipeline.
- **risk boundary:** **PUBLIC CLI SURFACE → отдельный owner approval в момент
  implementation.** Слайс **не** destructive; 6D/6E им не требуются.
- **тесты deep-dive:** T9.
- **required verification:** targeted + smoke (существующими командами) +
  `full`.
- **фактическая verification (2026-08-02):** targeted radius — 193 теста,
  exit code 0; canonical `create --help`, inline/file temp dry-run smoke — по
  exit code 0; full offline suite — 1465 тестов за 309.632 секунды, exit code
  0, `OK`; docs QA после checkpoint update — exit code 0. Числа и длительности —
  измерения, не нормативы. Network/provider/download/Vision/TTS/paid/render
  operations не выполнялись.

#### PLAN-9B-4 — truthful source/script behavior (CRITICAL-2, часть 2)

- **status:** completed 2026-08-02 · **зависимости:** PLAN-9B-5a (выполняется вместе или
  сразу после — иначе пользователь теряет offline-путь подачи материала).
- **цель:** для factual strict workflow `topic` = **intent, не usable source
  material**. Запрещённая цепочка `topic → insufficient source →
  LegacyTemplate → validation passed → production success` перестаёт
  существовать. При недостаточном материале — truthful blocking state
  `insufficient_source_material`.
- **reuse — новых сущностей не создаётся:** `allow_legacy_fallback` ·
  `ScriptValidationResult` · `script_provider` · `fallback_reason` ·
  `script_metadata`. **`content_origin` не создаётся** (OD-18): информация уже
  выражена существующими полями, дефект в том, что их **никто не читает**.
- **`LegacyTemplateScriptProvider` не удаляется.** Он остаётся эталоном
  регрессии и воспроизводимости старых проектов; разрешён только явным режимам
  `template` / `demo` / `test` / `draft`. Меняется условие его **молчаливого**
  вызова, а не он сам.
- **AI research не добавляется** (OD-17).
- **тесты deep-dive:** T6, T7, T8.
- **backward compatibility:** старые persisted проекты и test fixtures с явным
  `script_provider == "legacy_template"` продолжают воспроизводить старую форму;
  defense-in-depth блокирует только metadata, явно фиксирующие неявный fallback
  из-за `insufficient_source_material`.
- **risk boundary:** наблюдаемое поведение `strict` → **owner approval**.
- **required verification:** targeted + `full`.
- **фактическая verification (2026-08-02):** targeted owner/caller radius —
  168 тестов за 135.307 секунды, exit code 0; full offline suite — 1523 теста
  за 356.527 секунды, exit code 0, `OK`. T6/T7/T8, clean application/diagnostic
  errors, persisted quality defense, explicit legacy compatibility, source-text
  и resume/force-stage fixtures зелёные; docs QA и
  `tests.test_stage2_agent_onboarding` — exit code 0. Числа и длительности — измерения, не
  нормативы; network/provider/download/Vision/TTS/paid calls не выполнялись,
  synthetic render fixtures создавались только во временных каталогах.

#### PLAN-9B-PRODUCER — Provider-language VisualBrief producer

- **status:** completed · **completed:** 2026-08-02 · scheduled owner decision
  **OD-P-1** 2026-08-02.
- **dependencies:** completed **PLAN-9B-1**; completed **PLAN-L0** до начала
  execution согласно утверждённому порядку.
- **owner:** `src/content/visual_planning/**`.
- **objective:** из доказанного source/script/research evidence сформировать в
  существующем visual-planning owner provider-language содержание существующего
  `VisualBrief`, не перенося semantic intent в `query_adapter` и не создавая
  второго planner/query pipeline.
- **user outcome:** подготовленный материал разных доменов получает
  осмысленный provider-ready visual brief/query; при недостатке evidence
  состояние остаётся честным, fail-closed и редактируемым, а explicit author
  brief всегда выигрывает.
- **implementation zones:**
  - `src/content/visual_planning/**`;
  - exact owning test modules, доказанные pre-implementation caller audit;
  - current docs только для checkpoint/evidence после фактического completion.
  Фактический diff остался в этих зонах; caller production вне owner не менялся.
- **prohibited zones:** любой production owner вне
  `src/content/visual_planning/**`; `query_adapter`, provider implementations,
  script/research owners, public CLI/API, schemas, project/storage layout и
  asset pipeline. Не создавать `TranslatorService`, `SearchEngine`,
  `QueryOrchestrator`, `VisualBriefManager`, `VisualBriefEngine`, второй visual
  planner, второй query pipeline, второй semantic stack, новый repository,
  artifact, manifest, evidence store или project state.
- **canonical contracts — только существующие:** `VisualBrief`;
  `SceneVisualPlan.brief`; `provider_queries`; `claim_ids`; `source_refs`;
  visual-plan serializers; `master/master_visual_plan.json`; локализованный
  `visual/visual_plan.json`; существующая downstream copy `query_plan` /
  `visual_brief` в `assets/assets_manifest.json`.
- **author override priority:** automatic planner result → explicit author
  brief applied last → author brief wins. `NewsJob.visual_briefs` остаётся
  author input; producer не выдаёт automatic result за author input и не
  перезаписывает prepared brief.
- **truthful fail-closed boundary:** producer использует source text, script,
  research evidence, template/channel brief и существующую structured scene
  semantics. Factual provider query только из topic literal запрещён. При
  недостаточном evidence не создаются generic plausible substitute,
  topic-specific literals или misleading query; unknown intent остаётся
  fail-closed.
- **method is not frozen:** implementation-time варианты могут включать
  deterministic evidence-derived adaptation, template/channel briefs и local
  bounded adapter. Текущая approved implementation boundary — offline, без
  сети, paid API и новой обязательной model dependency. Local model либо
  optional paid/model-assisted adapter не утверждены этим слайсом; любой
  network/paid/model-assisted вызов требует отдельного owner approval на
  конкретное действие. Конкретная библиотека или модель заранее не выбирается.
- **tripwires:**
  - *persisted bytes:* OD-P-1 разрешает будущие изменения **только значений**
    существующих `visual_brief`, `provider_queries`, существующих visual-plan
    JSON objects и существующей downstream copy в assets manifest. Новый field,
    schema version, файл, layout, manifest, project state, provenance field или
    query-adapter-specific storage запрещены; старые проекты читаются
    tolerant/default readers. Если нужен новый schema/layout/public contract —
    **STOP** и новое owner decision;
  - *public:* нового CLI/API/console surface нет; его необходимость требует
    **STOP** и отдельного owner decision;
  - *network/paid:* в первом implementation slice отсутствуют; отдельное
    approval требуется на каждое конкретное действие;
  - *destructive:* отсутствует; hardcode/query-path retirement остаётся
    PLAN-9B-2/PLAN-9B-3 и этим слайсом не разрешён.
- **success criteria:**
  1. Для подготовленного материала минимум из классов animals/wildlife,
     energy/technology и geography/infrastructure producer создаёт
     evidence-derived provider-language content.
  2. Хотя бы один поддерживающий provider получает осмысленный query из
     evidence, а не из topic literal.
  3. Unknown intent остаётся fail-closed.
  4. Explicit author brief всегда выигрывает.
  5. Topic-specific hardcodes не добавлены.
  6. Второй query/planning owner не создан.
  7. Новые fields/artifacts/layout отсутствуют.
  8. Old/tolerant reading продолжает работать.
  9. Network/paid calls в первом implementation slice отсутствуют.
- **characterization requirements — до изменения поведения:**
  1. Зафиксировать current automatic planner result и порядок author override.
  2. Охарактеризовать текущий persisted round-trip. В частности,
     `from_legacy_visual_plan()` может реконструировать scene semantics/intents
     без восстановления `SceneVisualPlan.brief`; определить, требуется ли
     model-level/editor/read-model round-trip на фактическом пути.
  3. Если brief теряется на необходимом current path, исправить существующий
     tolerant reader **внутри visual-planning ownership**, не создавая нового
     storage owner. Заранее утверждать необходимость reader-изменения нельзя.
  4. Зафиксировать существующие master/localized/assets-manifest copies,
     `provider_queries`, `claim_ids`, `source_refs` и отсутствие новой
     schema/layout.
  5. Добавить multi-domain, explicit-author-override и fail-closed
     unknown-intent characterization/regression.
- **реализованный механизм:** существующий `build_plan()` после planner и до
  author overlay вызывает bounded producer существующего `brief.py`. Он берёт
  только provider-language structured intents, отдельные script keywords и
  связанные через `claim_ids` safe research excerpts; topic/title/channel не
  являются query source. Строки нормализуются и ограничиваются восемью термами
  и тремя candidates; Cyrillic/mixed, URL/slug, single-term и generic production
  vocabulary fail closed. `query_adapter` остался consumer без изменений.
- **override/round-trip:** automatic brief не записывается обратно в author
  `ScriptScene.visual_brief`; explicit author brief применяется последним и
  выигрывает. Existing writer сохраняет final `visual_brief` /
  `provider_queries`, `claim_ids` и `source_refs`; tolerant reader теперь
  восстанавливает existing `SceneVisualPlan.brief` и refs, а pre-Q2 missing
  values продолжают читаться defaults. Schema version/layout/artifact не менялись.
- **фактическая verification:** characterization-first red — 5 тестов, 4
  failures + 1 error ожидаемо зафиксировали отсутствующий producer и потерю
  round-trip; после реализации owning modules — 81 тест за 0.899 с, consumer /
  script / manifest radius — 166 тестов за 38.876 с, canonical temporary manifest
  — 4 теста за 102.235 с, все exit code 0. Первый full выявил только исходный
  onboarding limit (`CURRENT_STATE.md` 282 > 280 строк); после обязательного
  compact current-doc update onboarding — 3 теста за 0.214 с, финальный full
  offline suite — 1561 тест за 356.026 с, exit code 0. Package network guard
  активен; network/provider API/download/Vision/TTS/paid и реальный project
  render не выполнялись; media-проверки full suite использовали только temporary
  synthetic fixtures.
  Task-scope checker, `git diff --check`, docs QA и onboarding docs test — exit
  code 0. `baseline_head` остаётся без изменений.
- **rollback:** один bounded implementation commit; revert этого commit.
  Миграции данных, нового artifact/layout и irreversible действий нет.
- **relation to PLAN-L0 and PLAN-9B-2:** PLAN-L0 сохраняет knowledge, включая
  C46 и C48, но producer не реализует. PLAN-9B-PRODUCER реализует отдельный
  user outcome. PLAN-9B-2 после него реализует expansion ladder и hardcode
  migration. Три ответственности не смешиваются.

#### PLAN-9B-2 — expansion + hardcode migration

- **status:** pending / not started; **deferred за post-audit stabilization
  gate** (OD-S-1, состав — OD-S-3 и раздел «Blocking gate: что должно быть
  закрыто до возврата к PLAN-9B-2») и **blocked** до отдельного owner-issued
  implementation prompt · **зависимости:** completed PLAN-9B-4, **PLAN-L0**,
  **PLAN-9B-PRODUCER**, **PLAN-6D**, **PLAN-6E** — это technical prerequisites
  слайса, и их completed status PLAN-9B-2 автоматически не открывает.
- **цель:** контролируемая лестница расширения плюс снятие topic-specific
  hardcodes из shared engine.
- **лестница запросов:** точный субъект → субъект и действие → субъект,
  действие и локация → синонимы → альтернативные названия сущности → более
  широкий, но не меняющий смысл контекст → другой допустимый визуальный план
  той же идеи. **Предваряется источником provider-языка (9B-1):** без него
  лестница расширяет ноль.
- **salvage knowledge, без восстановления старого pipeline:** legacy
  `build_query_variants` expansion ladder (через PLAN-L0) · semantic query
  ladder `exact → broad → environment → atmospheric` · orca `provider_queries`
  (трёхуровневая структура «точный субъект → группа → среда») · `must_avoid`
  как часть смысла запроса.
- **topic-hardcode inventory — PROVISIONAL.** Число файлов **не фиксируется как
  invariant**: это измерение, а не контракт.
- **порядок обязателен:** replacement working → callers migrated → targeted и
  `full` зелёные → reviewer/gates → **затем** retirement. Удаление любого
  hardcode до переноса полезной capability запрещено.
- **`[HARD]` gate неприкосновенен:** снятие topic-литералов, живущих внутри
  safety gate `modes.blocking_reasons`, требует отдельного обоснования и **не**
  является разрешением менять сам gate.
- **non-goals (добавлено PRODUCT-PLAN-1, scope слайса не расширен):**
  `query_adapter` **не становится** producer provider-language evidence и не
  становится visual planner; `TranslatorService`, `SearchEngine` и
  `QueryOrchestrator` не создаются (OD-13). Канонические направления —
  `visual planning → существующий VisualBrief → query_adapter`.
- **источник provider-языка получил отдельного owner-слайса.** OD-P-1
  запланировал PLAN-9B-PRODUCER внутри существующего visual-planning ownership.
  Он не добавлен в scope PLAN-9B-2: producer и лестница расширения остаются
  двумя независимо проверяемыми user outcome, а PLAN-9B-2 по-прежнему
  пересекает multi-owner, persisted и destructive boundary. Completed PLAN-L0 и
  completed PLAN-9B-PRODUCER достаточным условием не являются: PLAN-9B-2 не
  начинается до закрытого post-audit stabilization gate, отдельного
  independent stabilization review с ACCEPT и отдельного owner-issued
  implementation prompt.
- **тесты deep-dive:** — (T3 перенесён в PLAN-9B-1 вместе с исправлением
  `source_is_latin`, registry C36; тест не потерян и нового тестового этапа не
  создаётся).
- **risk boundary:** multi-owner diff + persisted содержимое visual plan +
  destructive → **PLAN-6D + PLAN-6E + reversible retirement**.
- **required verification:** targeted + `full`.

#### PLAN-9B-3 — query-path cleanup

- **status:** pending · **зависимости:** PLAN-9B-2, **PLAN-6E**.
- **выполняется только ПОСЛЕ работающей замены.**
- **кандидаты на retirement** (ни один не удаляется раньше переноса уникального
  knowledge и всех callers): obsolete GLOSSARY matcher · orca topic hardcode ·
  `legacy_broad_query` · deprecated `make_stock_query` · superseded semantic
  `query_generator` — **только после миграции всех callers**.
- **risk boundary:** destructive retirement → **PLAN-6E + reversible retirement
  mechanism** (annotated tag + внешний `git bundle` + строка `Retired`).
- **required verification:** targeted + `full`.

#### PLAN-9B-5b — retirement `apps/news_to_short`

- **status:** pending · **зависимости:** PLAN-9B-5a **и** миграция всех
  callers; **PLAN-6D**, **PLAN-6E**.
- **порядок обязателен: capability сначала мигрируется, wrapper удаляется
  только потом** (OD-2, OD-19, registry K08, C42).
- **capability parity check — обязателен перед retirement (2026-08-01).**
  Список уникальных возможностей wrapper'а в прежней редакции был неполон,
  поэтому перед удалением проводится полный parity inventory
  `apps/news_to_short`. Минимум уже известных возможностей:
  **A.** named source-text input (`--text` / `--text-file`) → canonical
  first-class source-material contract (PLAN-9B-5a);
  **B.** user supplied assets at project creation (`--assets` →
  `NewsJob.user_assets`) → либо мигрировать в canonical Content Creator create
  path, либо получить **явное owner decision** о намеренном retirement этой
  capability. [FACT] у канонического `create` доказанного эквивалентного
  create-time входа нет; второй носитель `pipeline.py --news-to-short --assets`
  умирает в PLAN-L4. **Молчаливо потерять `--assets` запрещено.**
  Точный public CLI для user-assets сейчас не проектируется: это
  implementation decision и public-surface tripwire.
- **user outcome (добавлено PRODUCT-PLAN-1).** Owner decision по пункту **B**
  принят: user assets **мигрируют**, а не ретайрятся. Требуемый результат —
  пользовательские материалы становятся **first-class canonical Content Creator
  input**, доступным через канонический CLI/application request, а не
  сохраняются «ради wrapper parity». Переиспользуются существующие
  `ContentCreationRequest` и `NewsJob.user_assets`; новая логика отбора и
  хранения не создаётся. Точное публичное имя входа остаётся public-surface
  tripwire и решается в момент implementation (`PRODUCT_PLAN.md`, OD-P-5).
- **разрешается только после:** parity inventory wrapper'а; миграции всех
  сохраняемых capabilities; миграции callers; PLAN-6D; PLAN-6E; reversible
  retirement; targeted + smoke + `full`.
- **risk boundary:** destructive retirement реализации, у которой есть callers
  (test-callers и собственный README) → **PLAN-6D + PLAN-6E + reversible
  retirement**.
- **required verification:** targeted + smoke + `full`.

### PLAN-9C — semantic decision wiring

- **status:** blocked (**PLAN-1C′** и закрытый C01-SEM; **PLAN-6E** —
  semantic decision boundary; фактическое наполнение даёт PLAN-9B) ·
  **commit:** —
- **порядок подтверждён (OD-22):**
  `provider-ready query → candidates → semantic/Vision → rank/select`.
  Подключать Vision к ранжированию кандидатов, которых ноль, бессмысленно.
- **исправлено ревизией 2.1 — механизм.** Формулировки «semantic не может
  влиять на selection» и «selection fingerprint запрещает rerank»
  **опровергнуты**. [FACT] metadata-semantic слой уже **ranks**, **rejects**,
  **blocks** и **может изменить выбранный asset** — доказано synthetic-пробой
  через живой ingestion seam. `_selection_fingerprint` — защитная
  самопроверка, а не вето.
- **фактическая проблема:** платный Vision-сервис пишет результат **поздно** — в
  review-манифест после цикла отбора — и **не подаёт evidence в decision layer
  до selection**.
- **цель:** **producer → existing semantic consumer wiring.** Target:
  `provider-ready candidates → Vision/semantic evidence → существующее semantic
  ranking → selection`. **Новый semantic stack не создаётся.**
- **отдельно зафиксированный дефект отчётности:** `_semantic_visual_summary`
  жёстко пишет `semantic_rerank_enabled=False` независимо от фактического
  конфига. Это дефект **отчётности**, а не решения; читателей этого поля из
  манифеста нет.
- **user outcome и acceptance criteria (добавлено PRODUCT-PLAN-1).** Vision —
  **committed product capability** (`PRODUCT_PLAN.md`, раздел «Vision AI»), и
  этот слайс является её wiring owner. Требуемый порядок: `provider search →
  deterministic normalization/ranking → **bounded shortlist** лучших кандидатов
  → Vision evidence → существующее semantic decision/selection → human review
  при необходимости`. Evidence обязано попадать в существующий decision layer
  **до** отбора; выполнение Vision после окончательного выбора, когда её вывод
  уже не способен повлиять на результат, приёмкой не считается. Размер
  shortlist и бюджет принадлежат PLAN-10C.
- **разрешённые зоны:** production asset selection path.
- **запрещено:** создавать второй visual planner, Vision stack или asset
  pipeline; изменять default-поведение в этом slice; **использовать mock
  semantic backend как влияющий на production selection** — mock допустим
  только в wiring-тестах и не является доказательством визуального качества.
- **non-goals Vision (добавлено PRODUCT-PLAN-1):** не создавать
  `VisionAssetManager`, `VisionSearchEngine`, второй candidate selector, вторую
  completion ladder, отдельный project state и новый semantic manifest, пока не
  доказано, что существующих evidence/review manifests недостаточно.
  Состояние «требуется проверка человеком» берётся из существующего словаря
  `src/assets/completion/modes.py`; второй словарь не вводится.
- **второй момент использования того же evidence (добавлено 2026-08-01,
  OD-M-6).** Помимо review кандидатов-ассетов, тот же Vision evidence-провайдер
  позднее применяется к **poster frame собранной композиции сцены**: смысл
  сцены, читаемость, визуальная иерархия, misleading, «недоделанный вид».
  Это **тот же producer в той же роли**, а не второй Vision stack, не второй
  selector и не отдельный pipeline; verdict попадает в существующий
  decision/review слой, а «требуется проверка человеком» — в существующий
  словарь. **Реализация принадлежит candidate slice `MOTION-CS4`** и требует
  рабочего scene preview (`MOTION-CS1`, registry C58); scope, статус и
  зависимости PLAN-9C этой записью не меняются.
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
- **implementation-time verification моделей (2026-08-01).** До первого
  разрешённого live/paid semantic/Vision вызова configured semantic/Vision
  model identifiers обязаны быть сверены с **фактическим provider/backend
  contract** и актуально поддерживаемыми model IDs: проверить configured model
  IDs; сверить их с provider contract; **fail closed** при unknown/unsupported
  model; не выполнять paid call при invalid или непроверенной model config.
  Точная network/provider validation требует owner approval на конкретное
  действие. До такой проверки **нельзя утверждать**, что конкретный model ID
  валиден или невалиден; это implementation-time verification, а не новый
  architecture finding и не новый PLAN-ID.
- **продуктовые режимы Vision (добавлено PRODUCT-PLAN-1).** Концептуально
  продукт различает **off · local · optional paid**. Это **продуктовые
  концепции, а не публичный контракт**: точные публичные имена CLI/API/enum
  здесь намеренно **не фиксируются** и требуют отдельного owner decision в
  момент implementation (`PRODUCT_PLAN.md`, OD-P-3). Режимы обязаны стать
  понятным названием уже существующей конфигурации, а не вторым контрактом.
  `optional paid` требует предварительного расчёта, отображения модели, числа
  проверяемых кандидатов, ожидаемой стоимости, явного подтверждения
  пользователя, кеша, resume без повторного расхода и fail-closed при
  неизвестном результате. `local` — отдельный adapter в той же роли
  evidence-провайдера, а не отдельная capability.
- **Vision не является обязательной runtime-зависимостью.** Продукт обязан
  полностью работать при выключенной Vision; отсутствие backend, бюджета или
  результата даёт безопасный fallback, а не отказ пайплайна.
- **то же правило распространяется на motion backend (добавлено 2026-08-01).**
  Node/браузерный author никогда не становится обязательной runtime-зависимостью
  продукта: его отсутствие, сбой или таймаут дают безопасный fallback по
  существующей completion ladder, а не отказ пайплайна. Активация Vision-review
  композиции подчиняется тем же гейтам этого этапа, что и Vision-review
  кандидатов; отдельный activation-контракт не вводится.
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
- **PLAN-10B не является owner provider-registry convergence (D-2).** Гипотеза
  «пять расходящихся реестров надо свести к `providers/registry`»
  **опровергнута**: это разные legitimate facts (actual constructed providers ·
  provider capabilities · fallback language info · source-class priority ·
  diagnostics inventory · availability), а `ProviderCapabilities.query_languages`
  **уже** имеет приоритет над fallback-таблицей. Остаточный cleanup:
  `local_library` declaration mismatch → **PLAN-10D**; вестигиальный
  `DEFAULT_PROVIDER_ORDER` и осиротевшее имя `unsplash` → opportunistic cleanup
  внутри слайса, который и так трогает routing. Отдельный PLAN-ID не создаётся.
  Ответственность PLAN-10B — **pagination / provider exhaustion / provider
  contract behavior**, и загружать её чужой работой запрещено.
- **required verification:** contract-foundation — targeted + `full`; каждый
  provider adapter — targeted; один итоговый `full` при закрытии family.
- **rollback:** один commit на contract и один на provider-family.

### PLAN-10C — adaptive budget и plateau policy

- **status:** blocked (PLAN-9B, PLAN-10B) · **commit:** —
- **цель:** политика `quick` / `standard` / `deep` вместо одного фиксированного
  лимита. Бюджет учитывает важность и длительность сцены, сложность субъекта,
  число новых уникальных кандидатов, улучшение best-so-far, число providers,
  стоимость вызовов, strict или draft mode.
- **владеет порядком эскалации** за пределами query variants: исчерпаны
  разрешённые запросы → локальная медиатека → другой provider → разрешённый
  fallback. Эти ступени сняты с PLAN-9B, потому что относятся к
  routing/completion policy, а не к генерации запросов. Включение локальной
  медиатеки остаётся за PLAN-10D и его аудитом, provider contract — за
  PLAN-10B; PLAN-10C определяет только момент перехода и его причину.
- **измеримый результат:** поиск продолжается, пока улучшает best-so-far;
  plateau останавливает; одна сложная сцена не останавливает остальные, не
  удаляет найденные assets, не сбрасывает проект и не блокирует reviewable draft.
- **acceptance criterion «partial preview» (добавлено PRODUCT-PLAN-1).**
  Черновое preview обязано быть возможным и тогда, когда часть сцен не
  разрешена: неразрешённые сцены занимает **безопасный project-owned
  placeholder** существующей completion ladder (ступени `E_generated` /
  `F_emergency`). Это продолжение уже принадлежащего этому слайсу порядка
  эскалации «разрешённый fallback», а не новая политика.
- **запрещено:** случайный нерелевантный asset ради `completed`, misleading
  visual, `must_avoid` conflict, нарушение rights, ложный `publish_ready`.
- **non-goals partial preview (добавлено PRODUCT-PLAN-1):** placeholder в
  preview **никогда** не означает `publish_ready`, `quality passed` или
  коммерческий выпуск и не ослабляет gate финального рендера; **второй preview
  pipeline не создаётся** — расширяется существующий preview/escalation путь;
  второй словарь состояний завершённости не вводится.
- **bounded repair сцены — потребитель этой политики (добавлено 2026-08-01,
  OD-M-6).** Будущий цикл «poster frame → technical QA → Vision review →
  structured repair → эскалация к человеку» **не вводит собственную политику
  бюджета**: число итераций, потолок расходов, детекция plateau и момент
  эскалации остаются за этим этапом. Repair-действия ограничены закрытым
  списком структурированных изменений (сменить утверждённый template той же
  `composition_type` · изменить валидируемые props · изменить длительность или
  порядок слотов · сменить background из существующего shortlist · понизить
  интенсивность motion · отказаться от композиции в пользу стока · эскалировать
  к человеку). Прямое редактирование production-кода агентом в этот список не
  входит. Реализация принадлежит `MOTION-CS4`; scope и статус PLAN-10C этой
  записью не меняются.
- **required verification:** targeted policy tests после каждого slice;
  `full` один раз при закрытии adaptive-search family.
- **rollback:** один commit.

### PLAN-10D — convergence глобальной локальной стоковой библиотеки

- **status:** blocked (PLAN-10C + аудит) · **commit:** —
- **переформулирован ревизией 2.1.** Прежняя цель «регистрация
  `LocalLibraryStockProvider` в автоматическом поиске» была слишком узкой, а
  формулировка «три независимых LocalLibrary implementation» — **неверной**.
- **[FACT], установленные Secondary Deep Dive:** один `media_index` · один
  rights-authority `apply_policy_to_candidate` · **два** matcher'а · несколько
  consumers/wrappers; legacy path #3 использует **ту же**
  `media_library.search_local_assets`, что и path #1. Аргумент про
  `RIGHTS_REFERENCE_ONLY` **опровергнут**: интерим-значение перезаписывается
  политикой.
- **[FACT] ровно два доказанных расхождения live local-library путей:**
  1. missing `provenance`;
  2. `review_required=True`.
  Обратных расхождений — **ноль**.
- **scope — только GLOBAL LOCAL STOCK LIBRARY.** Соседние legitimate
  capabilities **не объединяются и в конвергенцию не входят**:
  - user/manual project assets (`--assets`);
  - project pool уже скачанных в проект ассетов;
  - глобальная локальная стоковая библиотека — **это и есть scope PLAN-10D**.
- **цель:**
  1. определить canonical matcher / provider boundary;
  2. harmonize provenance и review semantics;
  3. salvage **diversity reserve** из legacy (`min_local_diversity_per_scene` /
     `reserved_download_slots`, через PLAN-L0) — прямо релевантен проблеме
     повторяющихся визуалов; современного эквивалента нет;
  4. удалить superseded wrappers/path после переноса knowledge и callers;
  5. **не создать четвёртый путь.**
- **сопутствующие записи:** `query_adapter` объявляет `local_library`
  провайдером с поддержкой русского, чего не происходит, — declaration mismatch
  закрывается здесь (а не в PLAN-10B). `duplicate_penalty` в
  `rank_local_assets` — фактически **мёртвый код** (`used_asset_ids` вызывает
  `continue` раньше применения penalty); убирается вместе с этим bounded
  слайсом и отдельным PLAN не становится.
- **не смешивать с C50.** Fail-open на явном `review_required=True` — отдельный
  rights correctness defect и отдельный bounded fix, не часть architectural
  convergence.
- **deadline C50 (2026-08-01).** Новый top-level PLAN-ID не создаётся; C50
  остаётся отдельным bounded rights-fix слайсом и может быть выполнен
  независимо после зелёного PLAN-4, когда его bounded scope и tests
  подтверждены. Но как `[HARD]` rights correctness он **обязан быть CLOSED**:
  (1) до расширения / convergence / повторного включения Global Local Library
  в PLAN-10D; (2) до финального product evidence PLAN-11 / M1; (3) до любого
  live/publish-ready workflow, реально способного использовать Global Local
  Library asset с policy normalization. PLAN-9E искусственным owner C50 не
  делается — semantic activation и rights correctness разные
  responsibilities; если PLAN-9E фактически использует LocalLibrary
  publish-ready path, общий `[HARD]` rights gate применяется и без добавления
  формальной dependency.
- **открытый вопрос:** нужно ли вообще регистрировать `local_library` как
  `StockProvider` — решается по исходу конвергенции.
- **измеримый результат:** одна canonical local-library capability без
  расхождений в rights/provenance; diversity reserve сохранён; четвёртый путь
  не создан; при отрицательном решении о регистрации registry не усложняется.
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
- **early multi-topic regression (OD-25).** Первая проверка на разных доменах
  **не ждёт PLAN-11**: после каждого существенного product slice, где это
  релевантно, проверяются репрезентативные темы минимум из разных классов —
  animals/wildlife · energy/technology · geography/infrastructure. PLAN-11
  остаётся финальным product evidence gate, но **не первой** multi-topic
  проверкой.
- **PLAN-11 как EVIDENCE GATE ложных product capabilities.** Требование «нет
  ложного `publish_ready`» расширяется до «каталог не обещает несуществующий
  output». [FACT] catalog объявляет **5** active export targets, тогда как три
  production-owner согласованно работают с **3**; `supported_export_targets` и
  `safe_zone_profile` в render decision **не участвуют** (ноль production-
  читателей), то есть каталог — единственный outlier.
  **Цель — truthful catalog.** Создавать бессмысленные byte-identical
  TikTok/Stories outputs только ради соответствия каталогу **запрещено**.
  **PLAN-11 не является implementation owner:** у него `required verification:
  product gate`, `rollback: —` и нет allowed zones для source. Implementation —
  будущий небольшой bounded `production_catalog` slice, который либо убирает
  несуществующие targets из `active`, либо переводит их в `planned`, в
  зависимости от фактического intended product contract на момент
  implementation. Нового PLAN-ID не создаётся.
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
- **motion / hybrid evidence — future criterion (добавлено 2026-08-01).**
  Когда появится первый hybrid-формат, требование «каталог не обещает
  несуществующий output» распространяется и на `composition_type`: объявленный
  тип композиции обязан иметь работающего canonical author, иначе он остаётся
  `planned`. Это **будущий** критерий: пока `MOTION-CS1…CS4` не запланированы и
  не выполнены, он не применяется и состав, статус и gates PLAN-11 не меняет.
  PLAN-11 по-прежнему **не является implementation owner** ни каталога, ни
  motion-направления.
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

- **status:** blocked (PLAN-1B) · **commit:** —
- **изменено ревизией 2.** Прежний блокер «PLAN-1» больше не существует: PLAN-1
  разделён на capability gates. **Вся family PLAN-12 не блокирует первый
  product slice** — она выполняется параллельно или после PLAN-9A. Внутренняя
  последовательная цепочка `12E → 12A → 12B → 12C` сохраняется без изменений.
- **добавлено в PLAN-12B (перенесено из PLAN-1C):** пофайловая классификация
  `docs/implementation` (96 файлов), `docs/audits` (9), `docs/architecture` (5),
  `docs/apps` (3) — registry C27, C28. PLAN-9A её не требует.
- **порядок внутри этапа:** `12E → 12A → 12B → 12C`.
  **Буквы под-slices — идентификаторы, а не порядок выполнения.** Цепочка
  последовательная: каждый под-slice зависит от **непосредственно
  предыдущего** звена, а не от 12E напрямую. Пропуск звена запрещён.
  Существующие ID не переименовываются.
- **цель:** current navigation ведёт только к актуальным документам.
- **bounded sub-slices** (перечислены в порядке выполнения):
  - **PLAN-12E — document ownership model.** *Выполняется первым внутри
    PLAN-12.* **Зависимости: PLAN-1B.**
    Решение владельца от 2026-07-31: принято **направление B** —
    `current` (волатильное состояние и активные планы) / `architecture`
    (долговечные границы) / `product` (цель, quality, evaluation) /
    `runbooks` (операционные пути запуска) / `adr` / `archive` /
    `implementation`.
    **Направление — это ownership *direction*, а не разрешение перемещать
    конкретные файлы.** Все размещения ниже — candidate, не назначение:
    - `docs/apps/*` — candidate source для `docs/runbooks/`; exact per-file
      migration только после PLAN-12B evidence; каталог не архивируется;
    - `docs/architecture/visual_rendering_policy.md` — candidate source для
      `docs/product/QUALITY_BAR.md`; move/extract только после подтверждения
      PLAN-12B, что competing quality owner не существует (registry C23);
    - `docs/contracts/*` — target responsibility решается **по содержимому
      каждого файла**, не автоматически по каталогу (registry C22);
    - `SYSTEM_MAP.md` — target `docs/architecture/` принят концептуально;
      физический move выполняется только вместе с обновлением всех callers
      в соответствующем bounded slice.
    Категории `architecture/`, `apps/` и `contracts/` не удаляются ради
    меньшего числа каталогов. Число каталогов и число Markdown-файлов
    метриками качества не являются. Критерии — один canonical owner на
    responsibility, понятный lifecycle, отделение current от historical,
    отделение runtime data от source, сохранность product knowledge,
    тематичность документов и создание нового owner только при доказанной
    необходимости.
    *Измерение Foundation audit, не gate:* `docs/current/` — 2639 строк, из
    них 1616 (61%) приходится на два волатильных плановых документа.
    Разрешённые зоны: только `docs/current/CLEANUP_REGISTRY.md` и этот файл.
    Никаких move в этом под-slice.
  - **PLAN-12A — current docs. Зависимости: PLAN-12E.** Перенести уникальные
    подтверждённые данные `ARCHITECTURE_BOUNDARY_MAP.md` в `SYSTEM_MAP.md`,
    затем удалить current-копию; убрать дубли CURRENT_STATE/START_HERE.
    `docs/current/PRODUCT_EVIDENCE_GATE.md` **обязан переехать**, а не просто
    сменить `status`: [FACT] пять его `source_paths` указывают внутрь
    gitignored `projects/`, поэтому его evidence неверсионируемо и файл не
    может остаться в `docs/current/`.
    После слияния `SYSTEM_MAP` ← `ARCHITECTURE_BOUNDARY_MAP` **измерить
    результат как measurement**. Решение о `RUNTIME_FLOWS` принимается по
    качественным критериям, а не по числу строк — см. отдельный пункт
    «`RUNTIME_FLOWS` — CONDITIONAL NEW OWNER CANDIDATE» ниже.
  - **PLAN-12B — данные внутри docs. Зависимости: PLAN-12A.** Перенести
    production/evaluation fixtures из `docs/implementation` в versioned
    fixture/data owner и обновить callers; paid evidence сохранять без
    переписывания истории.
  - **PLAN-12C — archive. Зависимости: PLAN-12B.** `PROJECT_RESCUE_MASTER_PLAN.md`
    и подтверждённо исторические plans/audits/reports переместить в
    `docs/archive`, обновив navigation и links.
    **Не начинается, пока не закрыты 12E, 12A и 12B:** archive/move без
    утверждённой модели владения и без выполненных предшествующих шагов
    запрещён.
    Персональные ограничения состава:
    - `docs/architecture/visual_rendering_policy.md` — **временно защищён от
      archive и delete** до подтверждения PLAN-12B, что competing quality
      owner не существует (registry C23);
    - `docs/architecture/localization_and_voice_architecture.md` — **не
      объявляется заранее ни `keep`, ни archive-кандидатом**: DEFER вместе с
      остальными `docs/architecture/*` до полного per-file evidence
      (registry C28);
    - состав `docs/implementation`, `docs/audits`, `docs/architecture` и
      `docs/apps` — **DEFER до PLAN-12B** (registry C27).
- **`RUNTIME_FLOWS` — CONDITIONAL NEW OWNER CANDIDATE.** Не «justified».
  Создаётся только при выполнении всех пяти условий: пофайловая классификация
  `docs/*` завершена (PLAN-12B, ревизия 2 — прежде PLAN-1C);
  фактические runtime-flow sources прочитаны полностью (`docs/apps/*`,
  `COMMANDS.md` §10, `skills/resume-project`, `skills/create-short-video-first`,
  ADR 0006); PLAN-12A выполнил merge; итоговый `SYSTEM_MAP` измерен как
  measurement; **качественно** доказано, что runtime execution / stage /
  resume / failure information не помещается туда без смешения
  ответственности. Если после merge `SYSTEM_MAP` остаётся тематичным и его
  ответственности не смешиваются — новый owner не создаётся, независимо от
  числа строк.
- **действия по классам:** keep, move, archive, backup_then_untrack, delete,
  defer. Целое семейство одним действием не архивируется и не удаляется.
- **запрещено:** untrack двенадцати reference jpg до переноса dataset;
  переписывать historical snapshot как current; оставлять битые ссылки;
  начинать 12C раньше закрытия 12E/12A/12B; трактовать буквенную нумерацию
  под-slices как порядок выполнения.
- **required verification:** PLAN-12E — docs QA; PLAN-12A/12C — docs QA;
  PLAN-12B — targeted production callers + `full`; `git diff --check` всегда.
- **rollback:** один commit на семейство.

### PLAN-13 — ownership migration, retirement и root-structure classification

- **status:** blocked (PLAN-1B) · **commit:** —
- **изменено ревизией 2.** Блокеры PLAN-6C и PLAN-12 сняты как механические:
  прямой зависимостью является только capability gate PLAN-1B. **PLAN-9A не
  блокирует.** Значительная часть прежнего scope PLAN-13D переехала в PLAN-L.
- **цель:** один owner бизнес-логики, один установленный package root и один
  канонический CLI без потери compatibility/persisted contracts.
- **root-structure classification (OD-6, OD-9) — новый обязательный под-slice
  PLAN-13E, выполняется до любого move.** Старое допущение «существующий path —
  аргумент сохранить path» отменено; locked decisions 8 и 9 больше не запрещают
  пересмотр. Но переносить ради эстетики запрещено: **сначала классификация пяти
  групп, потом решение.**

  | Группа | Что известно | Действие |
  |---|---|---|
  | `channels/` | после L3 остаются `nature_science_news_ru` (активный) и `nature_pulse` | классифицировать вместе с template policy |
  | `schemas/` | 8 versioned contracts, читаются `test_artifact_schemas` | классифицировать |
  | reusable templates | `config/render_presets/`, `channels/*/templates/`, versioned SVG | классифицировать |
  | evaluation resources | live-eval dataset/results/frames — registry C31 | классифицировать; `docs/` подтверждён неправильным owner (OD-8) |
  | versioned assets/config | [FACT] после L3 все 5 оставшихся файлов `config/` активны, 8–21 caller каждый | **оставить на месте**, отдельной причины двигать нет |

  **Top-level `resources/` заранее не создаётся (OD-9).** Решение принимается по
  результату классификации и только если `resources/` реально уменьшает число
  owners и делает структуру понятнее. `resources/evaluation/` — candidate path,
  не назначение.
- **PLAN-13E также назначает physical target для C31** и переводит caller
  `src/assets/semantic_visual_evaluation_tooling.py:26,38,695` плюс
  `tests/test_semantic_decision_policy.py`, освобождая `docs/` от production
  dependency. Синтетический генератор
  `tests/test_semantic_visual_evaluation.py:458 _write_prepared_dataset` уже
  существует и повторно не создаётся.
- **applications против developer tools.** Это разные responsibilities:
  `apps/*` и `anime_factory/` — applications; `tools/` — developer tooling, QA,
  диагностика и maintenance. `anime_factory` остаётся **migration source**
  будущего `video_repurposer` (ADR 0016), а не постоянной параллельной
  архитектурой приложения; его runtime (`episodes/`, `input/`, `config.yaml`)
  живёт внутри source tree и переезжает во внешний workspace.
  `apps/news_to_short` вторым CLI не остаётся (OD-2, registry K08).
- **bounded sub-slices:**
  - **PLAN-13A — caller migration:** одно семейство production callers, затем
    current docs/examples, затем tests;
  - **PLAN-13B — ownership transfer:** переносить implementation, не
    копировать; Fullscreen, Story Card, Anime, projects, assets/providers,
    audio/music, subtitles и rendering — разные commits.
    **Orchestration finding (D-3, ревизия 2.1) — разделён на две
    ответственности; формулировка «два конкурирующих orchestration owner»
    опровергнута.** ADR 0009 **намеренно** разделяет application orchestration
    и news pipeline ownership.
    - **A. Точный idempotency contract defect.** [FACT] explicit `stage=` path
      отключает output-validated idempotency ADR 0006 через условие
      `and not stage`; batch-режим (`until_stage=`) idempotency **соблюдает**,
      explicit-режим повторно исполняет завершённые локальные стадии. Контракт
      для `stage=` не покрыт ни одним тестом. Owner — **ADR 0006 /
      `src/news/pipeline.py`**, отдельный будущий bounded slice.
      **Severity: MEDIUM.** [FACT] повторного платного TTS аудит **не
      обнаружил**: существуют несколько независимых guard'ов и существующие
      тесты; повторяются только локальные preview/final render.
      Вызовов — **4–7** в зависимости от режима, не «ровно 7».
    - **B. Возможная поздняя orchestration convergence.** Owner — PLAN-13B,
      **только если** после исправления contract остаётся архитектурная
      необходимость. «Один orchestration owner» **не** является уже принятым
      решением; правильный target — один контракт идемпотентности, действующий
      во всех режимах вызова.
    - **обязательное предусловие любой из двух работ:** подтвердить фактических
      `resume` / `force-stage` / `stop-stage` callers и публичное поведение до
      изменения — условная логика существует ради сосуществования двух режимов;
- **HIGH-3 (channel/project formats) — новый этап не создаётся.** Несколько
  форм канала и две системы проектов покрыты существующими **PLAN-1B** и
  **PLAN-13** (M02, C10, PLAN-13E). Позже: inventory channel formats → inventory
  project/state formats → tolerant readers → migrate callers → delete
  transitional duplicates. **Prerequisite текущих search/input fixes это не
  является;**
  - **PLAN-13C — wrapper/package retirement:** один wrapper/package family
    после zero-production-caller gate и dependency/toolchain audit PLAN-6C;
    root `ai_youtube/` и `src/ai_youtube/` свести к одному installable
    src-layout package;
  - **PLAN-13D — legacy pipeline: перенесён в PLAN-L ревизией 2.** Весь его
    прежний scope — сохранение maintenance-команд (теперь PLAN-L2), удаление
    `pipeline.py` (PLAN-L4), снятие production-импорта `scripts.test_moss_voices`
    (PLAN-L4, registry C18) — выполняется в параллельном этапе PLAN-L, потому
    что ждать здесь было незачем: у legacy-стека ровно один production-caller.
    Здесь под-slice сохранён как якорь ссылок и собственного содержания не имеет.
  - **PLAN-13E — root-structure classification:** см. выше в этом разделе.
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
- **Anime Factory: два разных предмета, смешивать запрещено (OD-23,
  ревизия 2.1).**

  | Предмет | Классификация | Owner |
  |---|---|---|
  | Anime Factory **capability** | **PRESERVE FOR FUTURE PRODUCTIZATION** — source implementation будущего `video_repurposer`, **не** disposable legacy | post-UI roadmap; запись — PLAN-8, преждевременной миграции в PLAN-13 нет |
  | Anime **runtime внутри source repo** (`input/`, `episodes/`, `artifacts/`, `outputs/media`) | **FIX LATER VIA WORKSPACE** — дефект расположения runtime | **PLAN-14**, registry C15 |

  `enabled=False` / `implementation_status="planned"` **не является
  доказательством ненужности**: capability выключена, а не отвергнута (усиление
  locked decision 5). Productize Anime сейчас не нужно; deep audit Anime
  Factory идёт **после** UI Content Creator.
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
    требует отдельного network approval.
    За 14B остаётся distribution boundary `tools/` (registry C26).
    **Изменено ревизией 2:** installed-package defect C25,
    `scripts/test_moss_voices.py` C18 и hardcoded `G:/` C24 закрываются в
    PLAN-L, потому что их носители (`pipeline.py`, `scripts/`,
    `config/video_style.json`, `channels/psychology/`) там удаляются. Здесь они
    не дублируются; 14B только проверяет, что после L4 в выжившем versioned
    config не осталось hardcoded drive;
  - **PLAN-14C — generated/cache/empty directories:** удалять только
    воспроизводимые cache/temp и подтверждённо пустые runtime directories по
    проверенному абсолютному пути; пустой `__init__.py` не мусор;
  - **PLAN-14D — runtime inventory и отбор representative corpus.**
    **Переписан ревизией 2 (OWNER: тестовое медиа disposable).** Inventory
    counts, manifests, project/media/model/toolchain roots и target workspace —
    как раньше, ничего не копируя и не удаляя. **Добавлено:** классификация и
    дедупликация 749 legacy JSON-манифестов (registry C32) по `schema_version`,
    manifest shape, completion state, resume state, legacy edge case и
    malformed/partial; отбор **минимального representative corpus**,
    достаточного tolerant-reader tests. Полный набор — во внешний retirement
    bundle как historical evidence. **749 файлов не становятся permanent
    architecture anchor.** Checksum-верификация применяется только к
    отобранному корпусу;
  - **PLAN-14E — workspace migration.** **Переписан ревизией 2.** Прежний
    `copy → verify counts/manifests/checksums → switch` для всего дерева
    заменён на: сохранить отобранный corpus, `media_index.json`, versioned SVG
    и, если нужно, минимальный voice sample с provenance (OD-3) → создать
    внешний workspace → переключить default → удалить disposable медиа.
    Выполняется только по отдельному owner approval; dual-read legacy roots
    сохраняется.
    **`MOSS_TTS_Nano/` не переносится (OD-7):** это цельный вендоренный
    сторонний репозиторий, а Runtime Workspace не является хранилищем исходного
    кода. Он ретайрится в PLAN-L4 вместе с `src/tts_providers/` после Knowledge
    Salvage Gate;
  - **PLAN-14F — root allowlist и правила `.gitignore`:** по одному top-level
    family за commit; tracked source, runtime/user data и generated output
    классифицируются раздельно.
    **Разрешённые зоны включают `.gitignore`** — это единственный slice,
    которому оно разрешено. Причина: `.gitignore` описывает именно root
    allowlist, а C20 и C21 — правила о top-level путях. **PLAN-6B остаётся
    detector/report-only owner и `.gitignore` не правит**; молчаливое
    превращение report-слайса в mutation-слайс запрещено. Нового PLAN ради двух
    правил не создаётся.
    Здесь исполняются exit conditions:
    (a) **C21** — директорное правило `assets/broll/` заменяется на
    `assets/broll/*`, после чего `git ls-files -i -c --exclude-standard` не
    содержит `.gitkeep`;
    (b) **C20** — `output/` и `tmp/` получают правила `.gitignore`. Удаление
    самих untracked артефактов в commit не входит и выполняется отдельно
    (PLAN-14C для воспроизводимого cache/temp), потому что untracked-файлы
    Git-состояние не меняют.
    **Изменено ревизией 2:** 8 × `outputs/*.json` (C19) и
    `outputs/asset_library_report.md` (C29) снимаются с Git в **PLAN-L4**
    вместе с их producer `pipeline.py --asset-report`, поэтому здесь остаётся
    только `assets/broll/.gitkeep` (C21) и остаток root allowlist. Обратить
    внимание: `src/media_library.py` при этом **сохраняется** — он используется
    активным news-путём;
- **измеримый результат:** report-only QA зелёный по утверждённому allowlist;
  runtime default не зависит от repo root/drive; сохранён именно
  `Preserved runtime corpus`, а не всё дерево runtime.
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

## Unscheduled candidate slices — Motion family

Записано 2026-08-01 слайсом `MOTION-ROADMAP-1`. Это **не этапы программы**.

Статус всей семьи:

- **не получают PLAN-ID** и не занимают номера существующих этапов;
- **не становятся** `current_checkpoint`;
- **не входят** в критический путь и ни один существующий этап не блокируют;
- **требуют отдельного owner approval** перед планированием;
- подчиняются общему правилу `PRODUCT_PLAN.md` раздела 18: до approval
  candidate slice не планируется и PLAN-ID не получает.

Временные метки — `MOTION-CS1`, `MOTION-CS2`, `MOTION-CS3`, `MOTION-CS4`.
Продуктовое обоснование каждой — `PRODUCT_PLAN.md`, раздел «Motion Design and
Multi-Renderer Composition». Findings — C53–C62 реестра.

### MOTION-CS1 — Renderer Foundation

- **user outcome:** пользователь видит сцену **до** дорогого финального
  рендера; неизменённые сцены не перерендериваются; будущий второй author
  получает единый segment contract.
- **предлагаемый scope:** characterization и baseline visual regression
  **первыми** (registry C61) · рабочий scene/poster preview (C58) · единый
  контракт canvas / FPS / pixel format / duration (C59) · per-scene
  fingerprint и кэш сегментов (C60) · technical QA готового сегмента.
- **`OWNER_DECISION_REQUIRED` — место persistence fingerprint.** Исходный
  аудит содержит **противоречие**: он одновременно требует «не менять persisted
  schema» и «добавить fingerprint в `assets_manifest`». Оба утверждения
  одновременно невыполнимы, поэтому фиксируется только следующее: fingerprint и
  кэш **обязательны**; точное место их persistence **не утверждено**; сначала
  проверяются существующий render manifest, project state и tolerant readers;
  `assets_manifest` **не выбирается автоматически**; любое изменение persisted
  schema является owner tripwire и требует отдельного разрешения.
- **предлагаемые non-goals:** не добавлять зависимости · не менять concat/mux/
  subtitle-логику · не создавать второй preview pipeline · не создавать второй
  project state · не замещать stock FFmpeg path (C57).
- **отношение к существующим этапам:** это и есть предполагавшийся PLAN-8
  «будущий bounded renderer slice» для C45; PLAN-8 остаётся roadmap owner.

### MOTION-CS2 — Isolated Comparative PoC

- **user outcome:** решение о motion backend принимается по измерениям, а не по
  внешнему рейтингу.
- **участники:** Remotion · HyperFrames · текущий MoviePy-рендерер Story Card
  как baseline. **Motion Canvas не участвует** (OD-M-11) и добавляется только
  если оба web-кандидата провалят обязательные критерии детерминизма или
  Windows-надёжности.
- **предлагаемые кейсы:** animated title · highlighted captions · statistic
  counter · comparison card · ECharts line chart · stock background + motion
  overlay · process diagram · вертикальный вариант · горизонтальный вариант ·
  alpha/transparent overlay · **Story Card parity case** (обязателен, OD-M-8).
- **обязательная изоляция:** не меняет активный Content Creator, persisted
  manifests, Python-зависимости и активный renderer; не выполняет платных
  вызовов и сетевых операций без отдельного разрешения; **не становится
  автоматическим fallback**.
- **измерения остаются измерениями,** а не архитектурными правилами и не
  нормами продукта — действует общая `Measurement policy`.

### MOTION-CS3 — Shared Design Tokens

- **user outcome:** один канал/тема выглядит одинаково у FFmpeg/Python-автора и
  у будущего web-автора.
- **предлагаемый scope:** один владелец для colors · typography · spacing ·
  safe zones · canvas/FPS · radii · shadows · motion durations · easing ·
  intensity levels · encoding profiles. Отдельно — развести design tokens и
  контент конкретного ролика в существующем render preset (registry C62).
- **`OWNER_DECISION_REQUIRED` — место хранения:** `channels` либо
  `config/design_tokens`. Не выбрано.
- **предлагаемый non-goal:** отдельная design system на каждый backend
  запрещена; внешний вид существующих проектов не меняется молча.

### MOTION-CS4 — SceneComposer and First Hybrid Explainer

- **зависимости:** `MOTION-CS1` + `MOTION-CS2` + `MOTION-CS3` + owner-решение
  по backend + релевантная query/asset foundation **PLAN-9B** (OD-M-13).
- **user outcome:** первая production-сцена совмещает стоковый материал и
  качественный motion.
- **предлагаемое направление scope:** additive composition intent в
  **существующих** визуальных контрактах · **`production_plan.json` не
  создаётся** · расширение существующего `production_catalog`, а не второй
  registry · один выбранный web backend · первая chart-композиция на ECharts ·
  первый hybrid explainer формат/шаблон · переиспользование существующих
  rights / completion / project / timeline / subtitle owners · Node остаётся
  опциональным с безопасным fallback.
- **парный retirement (PD-11):** рисующая часть `generated_infographic`
  (C56) · MoviePy-рендерер Story Card **после** parity gate (C53) ·
  зависимость `moviepy` **после** caller gate (C54, C55). Шаблон Story Card
  при этом сохраняется.
- **не фиксируется без owner approval:** точная persisted-схема и публичные
  имена `composition_type`.

## Результат после каждого этапа

Это краткая карта состояния, а не второй набор критериев готовности. Полные
gates и проверки остаются в соответствующих разделах выше.

| После этапа | Что фактически получаем |
|---|---|
| PLAN-0 | Один активный versioned execution plan на отдельной локальной ветке. |
| PLAN-1D-routing | Новый агент попадает в этот план, а не в historical master plan. |
| PLAN-1C′ | Закрыт C01-SEM: у asset/semantic capability известны owner, callers, persisted contracts, дубли и тесты. Снят один из двух gates PLAN-9A и PLAN-9C. |
| PLAN-1A / PLAN-1B | Capability gates для PLAN-L и PLAN-13; product-работу не блокируют. |
| PLAN-L | Legacy content stack ретайрен после Knowledge Salvage Gate: −~5700 строк, −6 тестов, −6 top-level путей; закрыты C17, C18, C19, C24, C25, C29; знание сохранено, retirement обратим. |
| PLAN-2 | Исправленные voice-profile fixtures без изменения рабочего production resolver. |
| PLAN-3 | Исправленные completion/resume fixtures, соответствующие output-validated idempotency. |
| PLAN-4 | Зелёный и воспроизводимый полный offline baseline на зафиксированном source HEAD. |
| PLAN-5 | Один test runner с режимами `smoke`, `fast`, `targeted`, `full`; локальные проверки и offline CI используют одну командную модель. **Параллелен PLAN-9B.** |
| PLAN-9B-0 / 9B-1 | **Первый product-этап:** зафиксировано фактическое поведение до правки; произвольная тема получает несколько provider-ready queries без topic-hardcode, fail-closed сохранён. |
| PLAN-6A / 6D / 6E | Короткие единые правила с классами `[HARD]/[ARCH]/[HINT]`, приоритет цели над предписанным методом, технический scope-контроль и один независимый read-only reviewer, ловящий в том числе «unmet objective / premature stop». 6A параллелен; 6D — gate первого multi-owner слайса; 6E — gate первого destructive слайса, плюс PLAN-9A и PLAN-9C. |
| PLAN-6B / 6C | Ранний отчёт о мусоре и дублях с зафиксированными кандидатами fitness-проверок; проверенная карта dependency/toolchain ownership. Параллельны product-работе. |
| PLAN-STAB-1…7 | Закрыт blocking stabilization gate: готовый финальный ролик переживает сбой и обычный resume; offline/paid граница fail-closed; явный rights-review не теряется; permissions ужесточены либо residual risk принят; current routing однозначен. |
| PLAN-STAB-8…17 | Обязательный stabilization backlog: честная docs freshness, один owner rights-словаря, timestamps, channel manifests, длительностей сцен, workspace/media-library, persisted round-trip, lock выполнения, CI baseline и целостный registry. Индивидуально PLAN-9B-2 не блокируют. |
| PLAN-7 | README и рабочие skills обучают только каноническому `python -m ai_youtube`; `COMMANDS.md` удалён без замены, canonical reference — `--help`; старые entrypoints пока лишь совместимы. |
| PLAN-8 | Отдельный `PRODUCT_PLAN.md` с приоритетами, evidence gates и roadmap двух engines; execution plan становится короче. |
| PLAN-9 | Честный источник сценария и канонический вход «исходный текст»; универсальные provider-ready queries без topic-hardcode; сохранение best-so-far, переносимое через resume; semantic evidence доходит до существующего decision layer и включается только opt-in. |
| PLAN-10 | Ограниченный и объяснимый search loop с ledger, stop reasons, pagination и adaptive budget; глобальная локальная библиотека сведена к одной capability с одной rights/provenance семантикой и сохранённым diversity reserve. |
| PLAN-11 | Проверенное offline M1 evidence на нескольких темах без новых платных Vision-вызовов и без ложных claims по Story Card; каталог не обещает несуществующий output. |
| PLAN-12 | Утверждённая модель владения документами (12E) фиксируется **до** любых archive/move; затем current docs содержат только актуальные знания, fixtures получают правильного владельца, а historical материалы находятся в archive. Порядок внутри этапа — последовательная цепочка `12E → 12A → 12B → 12C`. |
| PLAN-13 | Один владелец бизнес-логики на capability, один physical package root, один канонический CLI; классификация пяти групп root structure выполнена, решение о `resources/` принято по evidence, `docs/` свободен от production dependency. |
| PLAN-14 | Минимальный root allowlist, согласованные dependency/toolchain files и переносимый runtime workspace; сохранён отобранный representative corpus и versioned resources, disposable медиа удалено. |
| PLAN-15 | Финально доказанный чистый, понятный, переносимый offline-проект с честным catalog и закрытым cleanup registry. |

## Decisions and discoveries

Только новые факты, меняющие порядок или scope. Не журнал команд.

### Ревизия 2.1 плана, 2026-07-31

Источники: `CRITICAL_INPUT_SEARCH_DEEP_DIVE_2026-07-31.md` (контролируемые
offline-пробы под активным `network_guard`, ноль сети и денег),
`PROJECT_EXECUTION_PLAN_REVISION_2_1_PROPOSAL_2026-07-31.md` и
`SECONDARY_ARCHITECTURE_FINDINGS_DEEP_DIVE_2026-07-31.md`. При конфликте
Secondary Deep Dive исправляет Proposal 2.1.

- **[FACT]** единственный канал доставки provider-ready английского запроса —
  `visual_brief`, и заполняет его только topic-hardcode на одну тему. Следствие:
  произвольная тема получает ложный запрос, чрезмерное обобщение либо
  `translation_required`. Это CRITICAL-1 в исправленной формулировке: проблема
  **не** «ноль запросов» — отправляются **ложные** запросы, что хуже нуля.
- **[FACT]** `src/assets/semantic_selection/query_generator.py` **не участвует**
  в формировании remote-запросов; canonical boundary — `src/assets/
  query_adapter.py` (`build_scene_queries` / `build_slot_queries`). Allowed
  zone PLAN-9B ревизии 2 была ошибочной.
- **[FACT]** `Translator` / `def translate` / `to_english` — **0 commits** за всю
  историю: полноценного translate-слоя не существовало никогда, восстанавливать
  нечего. Английские `visual_keywords` в legacy `content/**` — **входные
  данные**, а не выход кода.
- **[FACT]** `topic → article["text"] == сама тема → thin input →
  LegacyTemplateScriptProvider → шесть фиксированных фраз →
  `script_validation == passed`; downstream не читает `script_warnings` /
  `fallback_reason`. Это CRITICAL-2. Как только CRITICAL-1 починят, шаблонный
  сценарий поедет в publish беспрепятственно, поэтому CRITICAL-2 идёт внутри
  той же цепочки PLAN-9B.
- **[FACT, исправлено 2026-08-01]** у `apps/news_to_short` **две** возможности
  вне явного контракта канонического `create`: (1) `--text` / `--text-file` —
  **именованный** source-text вход; функционально тот же downstream уже
  достижим как `create --pasted-script/--script-file` при default/legacy
  unspecified `content_input_mode`, поэтому PLAN-9B-5a даёт имя, валидацию и
  документацию, а не новый движок; (2) `--assets` — пользовательские ассеты при
  создании проекта (`NewsJob.user_assets`), **доказанного аналога в
  каноническом `create` нет**. Прежняя формулировка «единственная уникальная
  бизнес-возможность — `--text`/`--text-file`» **опровергнута**. PLAN-9B-5b не
  выполняется, пока не пройден capability parity check.
- **[FACT]** `ProviderQuery.source` попадает в persisted manifest, но схема
  типизирует сцены как свободные объекты без `enum`, поле не валидируется и
  **не имеет ни одного читателя**. E-2 закрыт: не schema-level change, tolerant
  reader не нужен. Байты манифеста при этом меняются → characterization 9B-0
  обязан зафиксировать `query_plan` до правки.
- **[FACT]** targeted, full и три smoke-команды исполнимы **сегодня** без
  PLAN-5 (проверено исполнением). PLAN-5 переведён в parallel для всех
  под-слайсов PLAN-9B.
- **[FACT]** зависимость `PLAN-6A → PLAN-6D` — **декларативная**: 6D-1/6D-2/6D-3
  не требуют, чтобы R1–R12 уже лежали в `AGENTS.md`.
- **[FACT]** synthetic-проба сменила выбранный asset через живой semantic
  ingestion seam. Формулировки «semantic не может влиять на selection» и
  «fingerprint запрещает rerank» **опровергнуты**: `_selection_fingerprint` —
  самопроверка. Проблема — платный Vision пишет результат поздно в review-
  манифест. Отдельно: `_semantic_visual_summary` жёстко пишет
  `semantic_rerank_enabled=False` — дефект отчётности.
- **[FACT]** double orchestration: ADR 0009 намеренно разделяет application и
  news pipeline ownership; вызовов 4–7 в зависимости от режима; реальный дефект
  — `and not stage` в `src/news/pipeline.py`, отключающий output-validated
  idempotency ADR 0006 в explicit-режиме, не покрытый ни одним тестом.
  Повторного платного TTS **нет** (несколько guard'ов + тесты). Severity
  снижена HIGH → MEDIUM.
- **[FACT]** LocalLibrary: один `media_index`, один rights-authority
  `apply_policy_to_candidate`, два matcher'а; legacy path использует ту же
  `search_local_assets`, что и канонический. Ровно два расхождения
  (`provenance`, `review_required`), ноль обратных. Формулировка «три
  независимых implementation» и аргумент про `RIGHTS_REFERENCE_ONLY`
  опровергнуты. **Новый дефект:** явный `review_required=True` может пройти
  канонический путь, потому что policy позднее сбрасывает исходный флаг —
  registry C50, класс `[HARD]`. Дополнительно: `duplicate_penalty` в
  `rank_local_assets` — мёртвый код.
- **[FACT]** provider registry: `local_library` не попадает в
  `ordered_providers`, таблицы корректно фильтруются по availability,
  `ProviderCapabilities.query_languages` перекрывает таблицу. Гипотеза «пять
  расходящихся реестров» **опровергнута**; PLAN-10B как owner конвергенции
  снят (E-5 закрыт отрицательно).
- **[FACT]** export: каталог объявляет 5 active targets, три production-owner
  согласованно работают с 3; `supported_export_targets` и `safe_zone_profile`
  имеют ноль production-читателей и в render decision не участвуют. Каталог —
  единственный outlier.
- **[FACT]** FFmpeg: concat выполняется с `-c:v copy` и **не перекодирует**;
  CRF 20 принадлежит duration-control mux и имеет документированную причину.
  Три lossy generations — при audio + ASS subtitles. Величина ущерба **никем не
  измерялась** — ни один аудит не рендерил.
- **[FACT]** subprocess-модулей, запускающих CLI мимо `network_guard`, на audit
  HEAD `adcbb19` — **12**, а не 7. Это measurement, не invariant.
- **[owner decision]** OD-11…OD-26, D-1, D-2, D-3 и E-13 приняты; см. «Owner
  decisions ревизии 2.1».
- **[owner decision]** PLAN-P0 не создаётся: evidence уже получено, тесты
  T1–T11 распределены по PLAN-9B слайсам.
- **[FACT]** `baseline_head` остаётся `fe2df5b`: ни один из трёх аудитов и ни
  ревизия 2.1 полный offline suite не запускали. Подменять `baseline_head`
  текущим HEAD запрещено до нового full baseline run в PLAN-4.

### Ревизия 2 плана, 2026-07-31

- **[FACT]** legacy content stack — `pipeline.py` → `src/legacy_pipeline/workflow.py`
  → 20 модулей корня `src/` (~4903 строки) — имеет **ровно одного**
  production-caller и 6 test-модулей из 112. `legacy/` (424 строки) не имеет ни
  одного Python-caller. Исключения, которые остаются: `src/media_library.py`
  (активный news-путь) и `src/utils.py` (`src/audio/tts/env.py`,
  `src/tts_providers/moss_tts_provider.py`). Это основание для раннего PLAN-L.
- **[FACT]** `src/legacy_pipeline/maintenance.py` — не legacy-генерация, а
  единственный CLI-доступ к visual-preview, semantic-backend,
  semantic-evaluation, semantic-visual, media-library и envato-manual;
  канонический CLI этих команд не имеет. Поэтому L2 обязателен до L3.
- **[FACT]** `channels/{psychology,quotes,survival,size_comparison}` и
  `content/survival/juliane_koepcke_001.json` читаются
  `tests/test_channel_profiles.py` и `tests/test_documentary_visual_engine.py` —
  это fixtures legacy-стека, а не user data. Registry N04 изменён.
- **[FACT]** `MOSS_TTS_Nano/` — цельный вендоренный сторонний репозиторий
  (собственные `pyproject.toml`, `venv/`, `tests/`, `finetuning/`, 45 `.exe`);
  активный `src/audio/tts/provider_manager.py` MOSS не регистрирует.
  **[INFERENCE]** после L3/L4 у него и у `src/tts_providers/` ноль callers.
  Делить на weights и vendor code нечего — OD-7 ретайрит целиком.
- **[FACT]** production-зависимость на `docs/implementation/openai_live_evaluation`
  — три строки `semantic_visual_evaluation_tooling.py:26,38,695` плюс
  `tests/test_semantic_decision_policy.py`. Синтетический генератор
  `_write_prepared_dataset` уже существует. Дефект зафиксирован как C31.
- **[FACT]** после L3 все пять оставшихся файлов `config/` активны, 8–21 caller
  каждый. Повода переносить каталог нет; открыты только `channels/`, `schemas/`
  и reusable templates.
- **[FACT]** `apps/news_to_short/main.py` — 83 строки собственного argparse,
  дублирующего флаги канонического `create`/`resume`; два других wrapper —
  8-строчные делегации. Registry K08 уточнён.
- **[FACT]** PLAN-6E был заблокирован невыполнимым предусловием: Codex не
  установлен, discovery-check выполнить нельзя, а 6E обязателен до PLAN-9A.
  Deadlock снят разделением Claude-части и Codex-части.
- **[FACT]** `src/assets/completion/` уже владеет лестницей выбора A–F,
  `blocking_reasons` и словарём состояний завершённости. Второй словарь
  (`PASS/DEGRADED/…`) не вводится: это создало бы второго canonical owner.
  Продуктовая дыра находится **выше по потоку** — см. «Продуктовая рамка
  PLAN-9 и PLAN-10».
- **[owner decision]** OD-1…OD-10 приняты; см. раздел «Owner decisions
  ревизии 2».
- **[owner decision]** порядок первых действий изменён: STEP 0 (перенос ревизии
  в этот файл и в registry) выполняется **до** PLAN-1D-routing, потому что 1D
  направляет будущих агентов именно сюда.
- **[FACT]** `baseline_head` остаётся `fe2df5b`: нового full baseline run не
  выполнялось. Смещение `current_checkpoint` с PLAN-1A на PLAN-1D-routing —
  следствие reorder, а не выполненной работы.

- **2026-07-30** targeted re-search ограничен одной фазой **на сцену**, а не на
  проект: `targeted_search_done` — локальная переменная
  `complete_scene_assembly` в `src/news/asset_scene_completion.py`, вызываемой
  из per-scene цикла `src/news/asset_manifest_builder.py`.
- **2026-07-30** `config/semantic_visual.json` содержит `enabled: false`,
  `backend: mock`, `semantic_rerank_enabled: false`; режим по умолчанию
  `analyse_and_report`. **Исправлено ревизией 2.1:** прежний вывод «semantic-слой
  существует, но не влияет на отбор» относился к **платному Vision-сервису** и в
  общем виде **опровергнут** — metadata-semantic слой является каноническим
  владельцем решения и может сменить выбранный asset. См. PLAN-9C.
- **2026-07-30** `src/assets/semantic_selection/vision_validator.py` —
  заглушка, безусловно возвращающая `vision_validation_enabled: False`;
  production-callers отсутствуют.
- **2026-07-30** `src/assets/semantic_selection/query_generator.py` содержит
  topic-specific hardcode под один субъект и литерал `"nature"` в atmospheric
  fallback. **Уточнено ревизией 2.1:** этот модуль **не участвует** в
  формировании remote-запросов; главный носитель topic-hardcode —
  `src/news/script_generator.py`, canonical boundary —
  `src/assets/query_adapter.py`.
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
- **2026-08-05 [SUPERSEDED]** Оба факта выше устарели и не описывают текущее
  состояние. Приватный remote существует, `governance-reset`/`master`
  отправлены, `governance-reset` — default branch (OD-S-5). CI repair
  (`9f9b6f2`, `bcf6c2a`, `8ca755f`, `68acdb2`, `Plan-Step: PLAN-STAB-16`)
  вернул `.github/workflows/offline-tests.yml` в доказанно зелёное состояние:
  GitHub Actions run `31039985187`, `offline-tests / unittest` — success,
  1/1 checks, failures=0, errors=0. Локальный полный offline suite остаётся
  основной проверкой для non-CI-repair слайсов; для CI-репозитория теперь
  существует и независимое GitHub Actions подтверждение.
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
- **2026-07-30** governance-аудит от clean HEAD `2379444`: независимого
  reviewer в репозитории нет ни в какой форме — отсутствуют `.claude/agents/`,
  `.claude/skills/`, `.claude/commands/`, hooks, Codex-конфиг, git-hooks
  (в `.git/hooks` только samples), `.vscode`, `.idea`, `*.bat`, `*.cmd`, `*.ps1`.
- **2026-07-30** механизма scope-контроля нет: ничто не сравнивает allowlist
  задачи с фактическим `git diff --name-only`. Технически enforced сейчас ровно
  три вещи: `tools/qa/check_agent_docs.py`, deny-list `.claude/settings.json`
  и `tests/network_guard.py`. Остальные правила зависят от памяти модели.
- **2026-07-30** `skills/` не является `.claude/skills/`, поэтому Claude Code
  не загружает эти skills автоматически; они доступны только при ручном чтении
  файла. Codex-адаптер существует как `skills/*/agents/openai.yaml`.
- **2026-07-30** `docs/current/PRODUCT_EVIDENCE_GATE.md` имеет
  `status: historical_reference` внутри `docs/current/` — единственный такой
  файл. `tools.qa.check_agent_docs` проверяет три файла из семи в
  `docs/current/` и не проверяет активный execution plan.
- **2026-07-30** лестница PLAN-9B противоречила собственным разрешённым зонам:
  `src/assets/semantic_selection/query_generator.py` — 55 строк, возвращает
  только строки запросов, а ступени «локальная медиатека», «другой provider» и
  «разрешённый fallback» живут в `src/providers/registry.py`,
  `src/providers/local_library_provider.py` и
  `src/news/asset_scene_completion.py`. Реализовать их внутри слайса было
  невозможно без выхода за scope, и они пересекались с PLAN-10D. Три ступени
  перенесены к PLAN-10C как порядок эскалации; PLAN-9B оставлен только за
  генерацией запросов. **Уточнено ревизией 2.1:** граница «лестница
  заканчивается на генерации запросов» сохраняется, но сама allowed zone была
  ошибочной — canonical owner remote-запросов `src/assets/query_adapter.py`,
  а не `semantic_selection/query_generator.py`.
- **2026-07-30** `git diff --check` проверяет whitespace-ошибки и конфликтные
  маркеры и не сравнивает состояние дерева, поэтому не может доказать
  read-only поведение reviewer. PLAN-6E получил отдельную controlled read-only
  acceptance вместо недоказуемого требования.
- **2026-07-30** карта tracked-файлов под кандидатами protected paths:
  `projects/` — 0; `music/` — 1 `.gitkeep`; `assets/library`+`assets/cache` — 1
  example; `anime_factory/episodes/` — 1 `.gitkeep`; `outputs/` — 9 плановых
  JSON и отчёт; `manual_assets/` — 7, включая 3 versioned SVG; `channels/` — 19
  versioned; `content/` — 13 versioned. Поэтому `outputs/**` и
  `manual_assets/**` нельзя блокировать целиком, а `channels/**` и `content/**`
  нельзя блокировать вовсе. 79 из 112 тестовых модулей используют
  `TemporaryDirectory`/`mkdtemp` вне репозитория, поэтому repo-relative
  deny-list synthetic tempfile не задевает.

### Repository Foundation audit, 2026-07-31

Read-only bounded аудит каркаса (root, `docs`, agent infrastructure,
developer tooling, QA, dev config) от clean HEAD `4ca3655`. Каждая запись
имеет класс: **FACT** — проверено командой; **INFERENCE** — вывод, исполнением
не проверенный; **[ПРЕДП]** — не проверено вовсе; **DEFER** — evidence
недостаточно.

- **2026-07-31 [FACT]** аудит выполнен от `audit_head` `4ca3655`.
  `baseline_head` остаётся `fe2df5b`: полный offline suite на `4ca3655` не
  запускался, промежуточные commits docs-only. Происхождение измерения не
  переписывается без повторного full run.
- **2026-07-31 [FACT]** покрытие аудита: 183 tracked файла в scope, 61
  прочитан построчно, 108 проверены программно, 14 metadata-only, 1 исключён
  по security. **`docs/implementation` (96 файлов) построчно не читался**,
  `docs/audits` (9) и `docs/architecture` (5) прочитаны заголовками. Поэтому
  archive/move/delete внутри этих семейств — DEFER до PLAN-12B.
- **2026-07-31 [FACT]** `git ls-files -i -c --exclude-standard`: 9 tracked
  файлов совпадают с `.gitignore` — 8 × `outputs/*.json` и
  `assets/broll/.gitkeep`. Директорное правило `assets/broll/` обесценивает
  последующее `!assets/broll/.gitkeep`.
- **2026-07-31 [FACT]** `output/` и `tmp/` не покрыты `.gitignore`.
  `output/` содержит один файл — `output/pdf/PROJECT_EXECUTION_PLAN_mobile.pdf`,
  280 820 байт; `tmp/pdfs/` пуст. **[INFERENCE]** это generated artifact:
  имя и размер соответствуют рендеру активного плана, содержимое PDF не
  парсилось. Владелец подтвердил удаление; оно выполняется отдельно от
  commit, поскольку файлы untracked.
- **2026-07-31 [FACT]** `pipeline.py:9` импортирует `scripts.test_moss_voices`;
  `packages.find.include` не содержит `scripts*` при `py-modules=["pipeline"]`.
  **[INFERENCE]** non-editable install ломает `import pipeline` — `pip install .`
  не выполнялся, CI использует `--editable` и дефект не ловит.
  **Отдельный вопрос [DEFER]:** отсутствие `tools*` в wheel дефектом по
  умолчанию не является — сначала PLAN-6C определяет intended distribution
  boundary. Предварительно `tools/` остаётся вне wheel.
- **2026-07-31 [FACT]** `legacy/` (8 файлов) не имеет ни одного Python-caller
  repo-wide; ссылки только в `README.md` и historical docs. **[DEFER]**
  архивирование требует caller gate PLAN-L1: статический граф не доказывает
  отсутствия внешнего или строкового caller.
- **2026-07-31 [FACT]** link-checker по всем 100 tracked `.md`: 0 битых
  локальных ссылок. Hash-скан по всем 664 tracked: единственный содержательный
  exact-дубликат — `ai_youtube/__main__.py` == `src/ai_youtube/__main__.py`,
  то есть симптом двух package roots (C01/C11), а не удаляемый дубль.
  Остальные совпадения — 15 пустых `.gitkeep` и 3 корректных
  `apps/*/__main__.py` boilerplate.
- **2026-07-31 [FACT]** активный execution plan имеет **одну** входящую ссылку
  во всём репозитории — `CURRENT_STATE.md`. `AGENTS.md`, `START_HERE.md`,
  `CLAUDE.md` и `README.md` его не упоминают. Routing чинит PLAN-1D.
  `docs/architecture/visual_rendering_policy.md` — единственный документ,
  задающий визуальный quality bar, — имеет **ноль** входящих ссылок.
- **2026-07-31 [FACT]** `README.md` (405 строк) и `COMMANDS.md` (681 строка)
  не упоминают `ai_youtube` ни разу; `COMMANDS.md` содержит 49 упоминаний
  `src.content_creation.cli` и 24 × `pipeline.py`; `README.md` учит bare
  `python`/`pip` вопреки `AGENTS.md`. `docs/contracts/STAGE1_PUBLIC_CONTRACTS.md`
  называет `src.content_creation.cli` «current CLI» и до сих пор не входил ни
  в один slice — добавлен в зоны PLAN-7.
- **2026-07-31 [FACT]** Claude Code не обнаруживает корневой `skills/`
  автоматически: `.claude/` содержит только `settings.json`,
  `settings.local.json` и `scheduled_tasks.lock`. **[ПРЕДП]** утверждение
  «Codex обнаруживает эти skills через `skills/*/agents/openai.yaml`» **не
  проверено**: Codex в среде не установлен, discovery-check не выполнялся,
  tracked codex-конфигов нет. Наличие файла не является доказательством
  discovery. Различать четыре состояния: наличие файлов, manual loading,
  auto-discovery, actual invocation.
- **2026-07-31 [FACT]** три из шести `SKILL.md` учат
  `python -m src.content_creation.cli`, а `tools/qa/check_agent_docs.py`
  проверяет только frontmatter, локальные ссылки и `TODO` — команды внутри
  skills не проверяются. PLAN-7 чинит файлы, PLAN-6A добавляет проверку.
- **2026-07-31 [FACT]** `docs/current/PRODUCT_EVIDENCE_GATE.md` указывает в
  `source_paths` пять путей внутри gitignored `projects/`. Смена `status` его
  не чинит: файл обязан переехать (PLAN-12A).
- **2026-07-31 [FACT]** `docs/current/` — 2639 строк, из них 1616 (61%)
  приходится на два волатильных плановых документа. **[INFERENCE]** слияние
  `SYSTEM_MAP` + `ARCHITECTURE_BOUNDARY_MAP` + `docs/apps/` + `docs/contracts/`
  дало бы 793 строки до вычета перекрытий. Это **measurement**, а не gate:
  решения о создании отдельного owner принимаются по responsibility, readers,
  lifecycle, смешению контрактов, routing ambiguity и maintenance coupling.
  Число строк может подтверждать проблему, но само по себе новый файл не
  создаёт.
- **2026-07-31 [owner decision]** принято **направление B** модели владения
  документами; зафиксировано как PLAN-12E. Направление — ownership direction,
  не разрешение перемещать файлы. Обязательная последовательная цепочка
  внутри этапа: `12E → 12A → 12B → 12C`, каждое звено зависит от предыдущего.
- **2026-07-31 [FACT]** из восьми кандидатов на новых document owners
  (`RUNTIME_FLOWS`, `QUALITY_BAR`, `EVALUATION_STRATEGY`, `TESTING`,
  `RECOVERY_AND_RESUME`, `STATE_AND_SCHEMAS`, `SECURITY_AND_APPROVALS`,
  `RUNTIME_WORKSPACE`) сейчас не создаётся ни один:
  1 CONDITIONAL NEW OWNER CANDIDATE (`RUNTIME_FLOWS`, пять evidence gates),
  1 EXTRACT CANDIDATE (`QUALITY_BAR`), 2 EXTEND EXISTING OWNER
  (`TESTING` → `tools/qa/run_tests.py`, `STATE_AND_SCHEMAS` → `schemas/` и
  существующий индекс), 2 DEFER (`EVALUATION_STRATEGY`, `RECOVERY_AND_RESUME`),
  2 NOT NEEDED (`SECURITY_AND_APPROVALS` — уже имеет корректное трёхуровневое
  владение instruction + permission + test; `RUNTIME_WORKSPACE` — ADR 0002 +
  PLAN-14 + `CURRENT_STATE`). Ни один не запрещён заранее.

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
