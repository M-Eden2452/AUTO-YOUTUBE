# Stock retrieval experiments

Накопительный журнал экспериментов по поиску визуального материала. Одна запись
на эксперимент, кратко. Raw JSON, кадры и медиа сюда не копируются — только
ссылка на artifact directory (он в ignored runtime-кэше).

Назначение: накапливать воспроизводимый evidence, из которого потом
калибруются query generation, provider routing, ranking, Vision policy и
бюджеты. Это не план и не архитектурный документ; при расхождении верны код,
Git и активный execution plan.

---

## EXP-001 — cheetah sprint, NO-AI vs Vision

> **Перенос в canonical docs (2026-08-13).** Четыре подтверждённых дефекта из
> раздела «Root cause» ниже записаны строками **C75–C78**
> [CLEANUP_REGISTRY.md](../current/CLEANUP_REGISTRY.md) с существующим owner
> **PLAN-10B**: mime-гейт Wikimedia, глубина поиска, форма запроса Internet
> Archive и одна строка запроса на провайдеров с разной терпимостью. Структурная
> часть каждого перепроверена по коду при переносе. Текст записи ниже сохранён
> дословно и остаётся evidence; право на работу дают строки реестра, а не он.

- **date:** 2026-08-12
- **HEAD:** `79c604de063da0cbd765bebecbd42d599dda59a4` (governance-reset, worktree clean)
- **target scene:** `cheetah_not_leopard` (PLAN-9D corpus scene_005) — «гепард
  разгоняется до ста километров в час за три секунды»
- **expected visual:** cheetah, running/sprinting, natural/wild, не зоопарк
- **modes tested:** FAST, DEEP, LONG_FORM (без AI) + Vision benchmark + Vision
  segment finding. `FAST` / `DEEP` / `LONG_FORM` — **experimental retrieval
  strategies этого эксперимента, а не product modes.** В `src/` и `config/` их
  нет: это ярлыки трёх настроек harness (число запросов, глубина выдачи,
  длительность материала), которыми я размечал результаты. Они не создают
  config-ключ, не заводят architecture owner и сами по себе ничего не
  утверждают о будущем продукте
- **providers:** pexels, pixabay, wikimedia commons, internet archive
- **artifact directory:** `assets/cache/retrieval_lab/` (ignored через
  `.gitignore:64 assets/cache/`)

### Counts

| strategy | queries | provider calls | candidates | unique | on-subject | elapsed |
|---|---|---|---|---|---|---|
| FAST | 20 | 20 | 68 | 39 | 23 | 12.0 s |
| DEEP | 20 | 20 | 1256 | 849 | 189 | 16.6 s |
| LONG_FORM | 10 | 10 | 131 | 92 | 59 | 8.8 s |

### FULL / HALF

| classification | asset | provider | licence | render | strategy |
|---|---|---|---|---|---|
| FULL | `Cheetahs on the Edge (Director's Cut)` 427 s | wikimedia | CC BY 3.0 | allowed | LONG_FORM |
| HALF | `Rozi the cheetah running at the Cincinnati Zoo` 63 s | wikimedia | CC0 | allowed | FAST |

Полезные сегменты внутри FULL: `02:58–03:06`, `03:58–04:06` (без burned-in
таймера), `00:09–00:16`, `01:00–01:07` (с таймером).

### Root cause прошлого «source scarcity»

Не дефицит источника. Три независимых дефекта Wikimedia-адаптера + форма запроса:

1. **QUERY.** Длинный шаблон `cheetah running at full speed savanna action` даёт
   на Commons **0**; короткий `cheetah running` даёт релевантное видео. Один
   query-owner на все провайдеры не работает: MediaWiki full-text не терпит
   лишних слов, Pixabay/Pexels терпят.
2. **PROVIDER ADAPTER.** `wikimedia_commons_provider.py:124` принимает только
   mime `video/*`; Commons отдаёт `.ogv` как `application/ogg` — файл
   выбрасывается как неизвестный тип.
3. **DEPTH/PAGINATION.** `srsearch` идёт без `filetype:video`, media-type фильтр
   применяется **после** выдачи, `max_results=8` при production `limit=5`. Из 5
   файлов Commons (там ~99% картинки) видео почти не остаётся.

Internet Archive: адаптер исправен, проблема в форме запроса — `(cheetah running)
AND mediatype:movies` без кавычек уводит выдачу в Lamborghini/GTA III.

### Rights

10 из 27 on-subject wikimedia-кандидатов render-clean. CC BY-* проходят, CC BY-SA
блокируются `share_alike_review_required` — корректное поведение политики.
IA `CHEETAHS - Running Out of Time!` найден по точному названию, но
`licenseurl=None` → `review_required`, не скачан как пригодный материал.

Отдельная ловушка harness: политика требует `attribution_text`; если адаптер не
синтезирует его через `_build_attribution`, любой CC BY становится blocked. Две
ранние версии harness дали ложное «blocked» именно по этой причине.

### Vision

- Backend: существующий `src/assets/semantic_visual_openai.py`, model
  `gpt-5.6-terra`, detail `low`, 3 кадра/кандидат, `VisionBudgetGuard` как
  единственный счётчик. `config/semantic_visual.json` не менялся — override
  передан объектом конфигурации.
- 18 вызовов (1 preflight + 12 benchmark + 5 segment), 30 731 in / 26 942 out
  токенов, вычисленная стоимость **$0.318** при лимитах 20 вызовов / $2.00.
- **Benchmark: 12/12 совпадений** — Vision сошёлся с уже существовавшей
  diagnostic-разметкой (человек + Claude) на этих же 12 кандидатах, расхождений
  0. Vision поймал все известные ложные метаданные: «cheetahs chasing prey» без
  гепарда (человек), два леопарда с тегом `cheetah`, `running/speed`-теги на
  шагающих животных, zoo-контекст.
  **Что 12/12 не значит.** Это не independent blind benchmark, не утверждение
  «accuracy = 100%» и не статистическая гарантия: набор из 12 кандидатов мал,
  разметка существовала до прогона и слепой не была, а сравнение шло с ней, а
  не с независимым ground truth. Читать эту строку как «Vision не ошибается»
  нельзя. Строгий счёт даст только PLAN-9D-F/PLAN-9D-G против слепой owner
  ground truth `tests/data/plan9d/current_annotations_v1.json`.
  **При этом сравнение не симметрично, и это существенно:** Vision не просто
  повторил разметку, а добавил к ней — нашёл burned-in таймер, пропущенный при
  первоначальном ручном просмотре кадров (ниже отдельным пунктом). Ошибок
  разметки в обратную сторону не было.
- **Segment finding: работает.** По равномерным окнам 427-секундного видео Vision
  сам локализовал бег в 0–256 s (action 0.88–0.96) и корректно показал его
  отсутствие в 341–427 s (0.00, титры).
- **Vision нашёл то, что пропустил человеческий просмотр кадров:** burned-in
  оверлей «1.00 SECONDS» в левом верхнем углу части FULL-материала
  (`visible_text_or_logo_risk`), и указал окно 170–256 s как чистое. Подтверждено
  визуально.
- **Калибровочная находка:** при `semantic_strictness=strict` и
  `environment=[savanna]` даже идеальный спринт получает `hard_reject=True`
  (environment 0.35 — трава, не саванна). Порог/вес окружения отбросил бы лучший
  ассет.

### Conclusion

LONG_FORM дал единственный FULL. FAST дал единственный HALF. DEEP дал наибольший
объём и ноль FULL/HALF. Vision не нужен, чтобы *найти* материал, но он
существенно повышает precision и умеет находить сегмент внутри длинного видео —
то есть его место в escalation, а не в каждом запросе.

`provider found ≠ reached shortlist ≠ selected ≠ render allowed` — в этом
эксперименте потери были на **query** и **provider adapter**, а не на источнике.
