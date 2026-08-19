---
status: evidence
verified_commit: 75c15be
verified_date: 2026-08-19
scope: офлайн-перепроверка причины 2 отчёта CONTENT_CREATOR_E2E_2026-08-19 на сохранённом проекте
---

# BLOCKER 1 — якорь темы против предмета сцены: замер до и после

Ни одного сетевого и ни одного платного вызова. Источник — сохранённый план
`projects/2026-08-19_chto-proishodit-s-telom-vo-vremya-sna-3/localizations/ru/visual/visual_plan.json`,
владелец — `src.assets.query_adapter.build_scene_queries` через
`plan_topic_anchor`. «ДО» снято тем же владельцем с правилом до `C124`
(предмет сцены не читается), «ПОСЛЕ» — с правилом `C124`.

Якорь плана: `'sleeping person'` (источник `plan_scene_subjects`, тема `'тело'`).

| сцена | subject сцены | запросов с якорем ДО | ПОСЛЕ | искал свой предмет ДО | ПОСЛЕ |
|---|---|---|---|---|---|
| scene_001 | `sleeping woman` | 1/5 | 1/5 | да | да |
| scene_002 | `sleeping person` | 2/4 | 2/4 | да | да |
| scene_003 | `sleeping man` | 1/5 | 1/5 | да | да |
| scene_004 | `human brain` | 5/5 | 1/5 | **нет** | да |
| scene_005 | `alarm clock at night` | 5/5 | 1/5 | **нет** | да |
| scene_006 | `neurons` | 5/5 | 2/5 | **нет** | да |
| scene_007 | `brain scan` | 5/5 | 1/5 | **нет** | да |
| scene_008 | `neural connections` | 5/5 | 2/5 | **нет** | да |
| scene_009 | `person practicing a skill` | 2/5 | 2/5 | да | да |
| scene_010 | `closed eyes` | 3/5 | 1/5 | да | да |
| scene_011 | `sleeping person` | 2/4 | 2/4 | да | да |
| scene_012 | `morning light on a bed` | 5/5 | 1/5 | **нет** | да |
| scene_013 | `tired person waking` | 2/5 | 1/5 | да | да |

**Итог по 13 сценам:**

- сцен, не способных искать собственный предмет ни на одной ступени: **6 из 13 → 0 из 13**;
- запросов, уходящих с чужим предметом впереди: **43 из 63 → 18 из 63**;
- отправляемых запросов всего: **63 → 63** — ступеней у лестницы не прибавилось
  и не убавилось, новых обращений к провайдеру нет.

## Что изменилось в самих запросах

Пять сцен, где менялась каждая ступень:

| сцена | ДО (ступень 1) | ПОСЛЕ (ступень 1) |
|---|---|---|
| scene_004 | `sleeping person human brain anatomy animation` | `human brain anatomy animation` |
| scene_005 | `sleeping person alarm clock night bedside dark` | `alarm clock night bedside dark` |
| scene_006 | `sleeping person neurons synapse animation dark` | `neurons synapse animation dark` |
| scene_007 | `sleeping person MRI brain scan rotating` | `MRI brain scan rotating` |
| scene_012 | `sleeping person morning sunlight through bedroom window bed` | `morning sunlight through bedroom window bed` |

Последняя ступень каждой сцены (`sleeping person dark studio`,
`sleeping person bedside table`, `sleeping person abstract dark space`) якорь
сохраняет: она построена из одного `place` и не называет ничего, что сцена
объявила своим предметом. Это ровно тот случай, ради которого `C98` вводила
якорь, и он не тронут.

## Что этот замер не показывает

- **Заполнение сцен.** Правило снимает запрет искать свой предмет, а не
  гарантирует находку. Сколько сцен получит ассет — вопрос следующего платного
  прогона, и здесь он не отвечен.
- **Синонимы.** Совпадение считается по стеблям слов. В `scene_006` ступень
  `brain neural network animation` осталась с якорем, потому что сцена объявила
  предмет `neurons`: правило видит слова, а не смысл. Часть из оставшихся 18
  запросов — такие промахи.
- **Причины 1, 3, 4 и 5 отчёта.** Смысловой бриф, ранжирование, дефицит
  длительности и `topic`-вход этим слайсом не трогались.
