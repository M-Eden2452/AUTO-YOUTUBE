# Audits

Этот каталог — **evidence аудитов**: что было измерено, когда, от какого HEAD и
какие выводы из этого следовали. Он не является ни планом, ни картой архитектуры,
ни источником истины о текущем поведении кода.

Приоритет при конфликте: фактический код и Git → [AGENTS.md](../../AGENTS.md) →
`docs/current/` → [ADR](../adr/README.md) → материалы этого каталога.

Отчёт здесь **не даёт права на действие**. Находка превращается в работу только
через [CLEANUP_REGISTRY.md](../current/CLEANUP_REGISTRY.md) или
[PROJECT_EXECUTION_PLAN.md](../current/PROJECT_EXECUTION_PLAN.md).

## Как пользоваться

1. Сначала [START_HERE.md](../current/START_HERE.md) и `docs/current/`. Начинать
   отсюда нельзя.
2. Заходить с вопросом «что было измерено и чем это доказано», а не за
   инструкцией.
3. Дата и commit внутри отчёта — момент его написания. Любое утверждение
   перепроверять по текущему коду до того, как на него опереться.
4. Ничего здесь не переписывать задним числом: массовая правка evidence
   запрещена (`tools/qa/check_agent_docs.py`, блок «current vs historical» —
   каталог намеренно выведен из strict-политики current-документов).

## Статусы

| Статус | Значение |
|---|---|
| `current` | Проверено на текущем HEAD; выводы ещё не устарели. |
| `historical` | Полезное свидетельство прежнего состояния. **Не текущая инструкция.** |
| `superseded` | Заменено другим документом или решением; замена указана явно. |
| `unknown` | Не перепроверялось; читать только как гипотезу. |

## Индекс

| Документ | Дата | Статус | Где current truth | О чём |
|---|---|---|---|---|
| [STOCK_SEMANTIC_REPEAT_2026-08-14.md](STOCK_SEMANTIC_REPEAT_2026-08-14.md) | 2026-08-14 | `current` | [PROJECT_EXECUTION_PLAN.md](../current/PROJECT_EXECUTION_PLAN.md) (PLAN-9B-PRODUCER-M-LIVE bounded correction) | STOCK repeat: 5/5 semantic briefs accepted, provider-language retrieval became live, 3/5 scenes received licensed image slots, no MP4/quality evidence; the `.env` reachability and persisted usage defects found by the run are closed. |
| [FIRST_OWNER_SHORT_LOCAL_SOLAR_AFTER_CYRILLIC_FIX_2026-08-14.md](FIRST_OWNER_SHORT_LOCAL_SOLAR_AFTER_CYRILLIC_FIX_2026-08-14.md) | 2026-08-14 | `current` | [CLEANUP_REGISTRY.md](../current/CLEANUP_REGISTRY.md) (C79, C80, C81; C47/C69/C74 — существующие), [PROJECT_EXECUTION_PLAN.md](../current/PROJECT_EXECUTION_PLAN.md) | A/B повтор того же LOCAL diagnostic на HEAD `a8549ff` — bounded Cyrillic-tokenization correction, **не** завершённый PLAN-10D: 5/5 сцен получили usable slot (было 0/5), ElevenLabs вызван один раз, `draft_1080x1920.mp4` создан (publish-ready evidence нет). Визуальная проверка кадров: 2 GOOD, 1 ACCEPTABLE, 2 BAD. Разделяет tokenizer (исправлен), morphology (`C79`: pre-v1 bounded correction) и diversity reserve (`C47` → PLAN-10D, post-v1); `C81` — post-v1 product discovery, а дубликат кадра сцены 3 дополнительно объяснён режимом `draft_complete`. |
| [FIRST_OWNER_SHORT_LOCAL_SOLAR_2026-08-14.md](FIRST_OWNER_SHORT_LOCAL_SOLAR_2026-08-14.md) | 2026-08-14 | `current` | [CLEANUP_REGISTRY.md](../current/CLEANUP_REGISTRY.md) (C40, C79), план (PLAN-10D) | LOCAL diagnostic на теме под покрытие библиотеки: 0/5 сцен, ElevenLabs не вызывался, MP4 нет. Доказано, что коарс-поиск локальной библиотеки не видит кириллицу — шортлист RU-проекта равен «10 самых длинных видео индекса». Корректирует вывод про нехватку покрытия из предыдущего отчёта. |
| [FIRST_OWNER_SHORT_LOCAL_REPEAT_2026-08-14.md](FIRST_OWNER_SHORT_LOCAL_REPEAT_2026-08-14.md) | 2026-08-14 | `current` | commit `fbf223a` (ranking defect **исправлен** 2026-08-14) | Повтор LOCAL diagnostic после курации библиотеки: rights-blocker снят, 1/5 сцен получила слот, ElevenLabs дошёл, MP4 нет. Воспроизведён ranking defect — нерелевантный кандидат берёт 92.5 при undecidable subject; закрыт `fbf223a`, PLAN-ID при этом не закрыт. |
| [RETRIEVAL_ENGINE_AUDIT_2026-08-13.md](RETRIEVAL_ENGINE_AUDIT_2026-08-13.md) | 2026-08-13 | `current` | [SYSTEM_MAP.md](../current/SYSTEM_MAP.md), [CLEANUP_REGISTRY.md](../current/CLEANUP_REGISTRY.md) (C64–C72) | Полный аудит retrieval/material engine: три стека, владельцы, конфиги, тесты, docs. Часть находок опровергнута при переносе — см. errata в шапке файла. |
| [AI_DEVELOPMENT_SYSTEM_AUDIT_2026-08-12.md](AI_DEVELOPMENT_SYSTEM_AUDIT_2026-08-12.md) | 2026-08-12 | `current` | [PROJECT_EXECUTION_PLAN.md](../current/PROJECT_EXECUTION_PLAN.md) (WP0-B) | Аудит самой системы управления разработкой: цена правил, дубли, дыры enforcement, R1–R9 (включая ADR-паузу). |
| [STOCK_RETRIEVAL_EXPERIMENTS.md](STOCK_RETRIEVAL_EXPERIMENTS.md) | с 2026-08-12 | `current` | [CLEANUP_REGISTRY.md](../current/CLEANUP_REGISTRY.md) (C75–C78 из EXP-001) | Накопительный журнал retrieval-экспериментов: одна запись на эксперимент. |
| [PROCESS_ADOPTION_AUDIT_2026-08-11.md](PROCESS_ADOPTION_AUDIT_2026-08-11.md) | 2026-08-11 | `current` | [PROJECT_EXECUTION_PLAN.md](../current/PROJECT_EXECUTION_PLAN.md) | Проверка внедрения маршрута и пакетов WP0-A / M1-A…M1-C. |
| [VISUAL_ASSET_INTEGRITY_AUDIT_2026-08-10.md](VISUAL_ASSET_INTEGRITY_AUDIT_2026-08-10.md) | 2026-08-10 | `historical` | [CLEANUP_REGISTRY.md](../current/CLEANUP_REGISTRY.md), план (M1-A…M1-E) | Целостность визуальных ассетов и evidence; породил семейство VA-NEW. |
| [VISUAL_ASSETS_COMPARATIVE_AUDIT_2026-08-10.md](VISUAL_ASSETS_COMPARATIVE_AUDIT_2026-08-10.md) | 2026-08-10 | `historical` | те же | Сравнение фактического отбора визуала с ожидаемым. |
| [CANONICAL_REVISION_2_1_INDEPENDENT_VERIFICATION_2026-08-01.md](CANONICAL_REVISION_2_1_INDEPENDENT_VERIFICATION_2026-08-01.md) | 2026-08-01 | `historical` | план (ревизия 2.1) | Независимая верификация ревизии 2.1 перед её принятием. |
| [PROJECT_EXECUTION_PLAN_REVISION_2_1_PROPOSAL_2026-07-31.md](PROJECT_EXECUTION_PLAN_REVISION_2_1_PROPOSAL_2026-07-31.md) | 2026-07-31 | `superseded` | [PROJECT_EXECUTION_PLAN.md](../current/PROJECT_EXECUTION_PLAN.md) | Предложение ревизии 2.1; принято и растворено в самом плане. |
| [SECONDARY_ARCHITECTURE_FINDINGS_DEEP_DIVE_2026-07-31.md](SECONDARY_ARCHITECTURE_FINDINGS_DEEP_DIVE_2026-07-31.md) | 2026-07-31 | `historical` | [CLEANUP_REGISTRY.md](../current/CLEANUP_REGISTRY.md) (C34–C50) | Deep-dive: local library, provider declarations, FFmpeg, knowledge salvage. |
| [CRITICAL_INPUT_SEARCH_DEEP_DIVE_2026-07-31.md](CRITICAL_INPUT_SEARCH_DEEP_DIVE_2026-07-31.md) | 2026-07-31 | `historical` | [SYSTEM_MAP.md](../current/SYSTEM_MAP.md) | Deep-dive по input/query truth; часть выводов позже опровергнута ревизией 2.1. |
| [INDEPENDENT_REPOSITORY_REVIEW_2026-07-31.md](INDEPENDENT_REPOSITORY_REVIEW_2026-07-31.md) | 2026-07-31 | `historical` | [CLEANUP_REGISTRY.md](../current/CLEANUP_REGISTRY.md) (C17–C29) | Repository Foundation review. |
| `PROJECT_AUDIT*.md` + [PROJECT_AUDIT_SNAPSHOT.json](PROJECT_AUDIT_SNAPSHOT.json) (9 файлов) | 2026-07-22 | `historical` | [SYSTEM_MAP.md](../current/SYSTEM_MAP.md), [ARCHITECTURE_BOUNDARY_MAP.md](../current/ARCHITECTURE_BOUNDARY_MAP.md) | Первая серия аудитов до governance-reset: [INDEX](PROJECT_AUDIT_INDEX.md), [OVERVIEW](PROJECT_AUDIT_OVERVIEW.md), [ARCHITECTURE](PROJECT_AUDIT_ARCHITECTURE.md), [COMPONENTS](PROJECT_AUDIT_COMPONENTS.md), [PIPELINES](PROJECT_AUDIT_PIPELINES.md), [RISKS_TESTS](PROJECT_AUDIT_RISKS_TESTS.md), [ROADMAP](PROJECT_AUDIT_ROADMAP.md), [PROJECT_AUDIT.md](PROJECT_AUDIT.md). Описывают до-канонический `pipeline.py`-мир: как current не читать. |

## Новый аудит

Минимум, чтобы он не стал источником путаницы:

1. frontmatter `status` · `audit_date` · `audit_head` (полный SHA) ·
   `working_branch`;
2. строка в таблице выше;
3. вывод, который должен пережить отчёт, — в
   [CLEANUP_REGISTRY.md](../current/CLEANUP_REGISTRY.md) или в план; сам отчёт
   остаётся evidence.

Машиночитаемые компаньоны (findings/classification JSON) в репозиторий не
копируются без отдельного решения владельца: они дублируют текст отчёта и
устаревают быстрее него.
