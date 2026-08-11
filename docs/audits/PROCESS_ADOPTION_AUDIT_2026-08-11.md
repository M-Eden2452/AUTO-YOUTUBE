# Аудит внедрения процесса и маршрута — 2026-08-11

- **Объект:** результаты стратегического аудита 2026-08-10 и блока «Mini plan
  reconciliation 2026-08-11»: пакеты WP0-A, M1-A (VA-NEW-01), VA-NEW-03,
  M1-B (VA-NEW-02), M1-C (VA-NEW-04+05) с двумя repair-коммитами, плюс
  процессные правила (машинные гейты, closure одной строкой, review batching,
  findings-как-тесты, ratchet baseline'ов).
- **Вопросы аудита:** что из утверждённого реально внедрено и насколько
  качественно; работаем ли мы теперь по-другому; есть ли нестыковки в
  маршруте и документации; состояние продукта.
- **HEAD:** `2577307` (branch `governance-reset`, worktree чистый,
  синхронизирован с origin). Аудит read-only: ни один существующий файл не
  изменён; создан только этот отчёт.
- **Выполненные проверки:** `scripts/gates.py` → `GATES OK`;
  `tools.qa.check_agent_docs` → OK + 3 advisory NOTE; targeted-тесты шести
  owning-модулей кластера (`test_continuity_evidence_lineage`,
  `test_visual_preview_integration`, `test_semantic_visual_integration`,
  `test_semantic_asset_selection`, `test_asset_foundation_models`,
  `test_media_selection_policy`) → **127 OK**; diffs всех шести коммитов
  пакета; конфиги, hook, CI, зеркала, реестры плана.
- **Ограничения:** RED-статусы characterization-тестов (заявленные в
  closure-блоках) не перевоспроизводились на родительских коммитах; CI runs
  не проверялись (сеть не использовалась); full suite не запускался.

## 1. Резюме

Внедрение **реально и по существу качественно**. Все пять содержательных
пакетов (WP0-A, M1-A, VA-NEW-03, M1-B, M1-C с двумя repair) реализованы в
коде ровно так, как заявлено в plan-блоках, с owning-тестами; гейты зелёные
на HEAD; маршрут («next: Review #1 M1-A…M1-C, не начинать M1-D») согласован
во всех четырёх routing-источниках. Процесс действительно изменился: за один
день (2026-08-11, 01:51–22:04) сделано восемь bounded-коммитов четырёх
слайсов, рост зеркал остановлен (net +1 строка на весь день против прежних
«строк-монстров»), findings независимых review закодированы RED-тестами.

Главные долги: **mypy-ratchet не движется** (0 из 28 подавленных модулей
снято, при том что M1-B/M1-C трогали шесть из них — новый код
identity/evidence-слоя фактически не типизируется); owner-решение по
persisted-полю `replaces_asset_id` не отражено в реестре approvals (две
формулировки «OWNER DECISION REQUIRED» остались в настоящем времени);
запас строк зеркал — 1+2+3 при ≥5 закрытиях до WP0-B.

## 2. Проверка пакетов: заявлено ↔ код

| Пакет | Коммиты | Вердикт |
|---|---|---|
| WP0-A машинные гейты | `98e58fe` + repair `a9bfc11` | внедрён, зелёный; ratchet см. F1 |
| M1-A / VA-NEW-01 | `15cb20d` (PLAN-9C-3) | соответствует полностью |
| VA-NEW-03 | `37ca498` (PLAN-9C-2) | соответствует полностью |
| M1-B / VA-NEW-02 | `1bf7ecc` (PLAN-9A) | соответствует полностью |
| M1-C / VA-NEW-04+05 | `c9537fa` + `a7bec3c` + `2577307` (PLAN-9A) | соответствует, включая оба repair |

### WP0-A — машинные гейты

Проверено фактически, не по описанию:

- `scripts/gates.py:14-20` — пять гейтов (ruff, mypy, `check_agent_docs`,
  `git diff --check`, staged-вариант); full suite сознательно вне гейтов
  (докстринг), остаётся в CI и targeted-прогонах.
- `.githooks/pre-commit` вызывает `venv`-python → `gates.py`;
  `core.hooksPath=.githooks` установлен в этом клоне (проверено
  `git config`). Кэши `.ruff_cache`/`.mypy_cache` существуют на диске и
  самоигнорируются собственным `.gitignore` внутри — гейты реально
  запускались локально, worktree остаётся чистым.
- CI `.github/workflows/offline-tests.yml`: шаги «Install dev tooling for
  machine gates» (`requirements-dev.lock`: ruff 0.16.2, mypy 2.3.0 —
  совпадает с установленным в venv) и «Run machine quality gates».
- `pyproject.toml`: ruff `select = ["F","E9"]` + extend-exclude; per-file
  baseline — 5 осознанных patch-point-поверхностей + F401/F822-список
  (20 записей после снятия одной в M1-B); mypy
  `files = ["src/assets","src/news"]`, override `ignore_errors=true` на
  28 модулей. Стратегия ratchet записана в комментариях и в reconciliation.
- `a9bfc11` — немедленный repair собственной ошибки WP0-A: `98e58fe`
  случайно выпотрошил `.gitattributes` (37 строк), repair восстановил
  reproducibility-атрибуты. Показательно: сами гейты этот класс ошибок не
  ловят; поймано человеком/агентом при просмотре diff — практика «смотри
  свой diff» работает, но защиты на конфиг-файлы нет.
- Прогон сейчас: `GATES OK` на HEAD.

### M1-A / VA-NEW-01 — continuity читает evidence, а не запрос

- `src/assets/semantic_selection/continuity_checker.py` — environment
  выводится из `build_evidence(asset).token_set` (канонический evidence
  owner PLAN-9C-3) вместо прежней склейки
  `title+description+source_url+source_page+keywords+search_query`;
  докстринг явно фиксирует обе границы (Evidence/Authority).
- `src/news/asset_manifest_builder.py:257` — continuity больше не пишет в
  `missing_scenes`; отчёт advisory, единственный owner резолюции сцены —
  `_record_scene`. Обе половины рекомендованного bounded fix аудита
  (observed-only evidence + advisory report) выполнены; инференс намеренно
  не менялся. Owning-тесты: `tests/test_continuity_evidence_lineage.py`
  (+377 строк).

### VA-NEW-03 — technical rerank стал advisory

- Builder больше не импортирует `select_candidate_after_review`; флаг
  `technical_rerank_enabled` теперь лишь запрашивает и записывает анализ
  (`analysis_mode="technical_analysis"`), заменить каноническое
  semantic/media/manual решение не может; комментарий в коде фиксирует
  правило «tie-break — только через канонический decision path».
  Owning-тесты: `tests/test_media_selection_policy.py` (+251).

### M1-B / VA-NEW-02 — preview key v2 привязан к байтам источника

- `src/assets/visual_preview.py` `compute_preview_cache_key`: для локального
  источника `version=2`, `source_sha256` текущих байтов
  (`sha256_file`), `local_preview_transform`
  (`max_dimension`, `video_max_duration_sec` из config). Подмена файла на
  том же пути → другой ключ → cache miss; нечитаемый/отсутствующий источник
  → исключение внутри try в `prepare_candidate_preview_analyses` → кандидат
  честно падает в failed-анализ (fail closed), старое evidence недостижимо.
- Remote-источники остаются v1 — сознательное ограничение bounded fix
  (аудит целил в local/manual/cached). Литерал `max_dimension: 720` в
  payload (строка 252) согласован с дефолтом трансформа (строка 265) в том
  же файле; связка хрупкая, но сегодня истинная (см. F8).
- Ratchet выполнен по ruff: снята baseline-запись `visual_preview` (mypy —
  нет, см. F1). Owning-тесты: `test_visual_preview_integration` (+111).

### M1-C / VA-NEW-04+05 — lineage и Vision envelope

Оригинал `c9537fa`:

- `src/assets/models.py` — аддитивные поля `replaces_asset_id` и envelope
  (`vision_tags`, `vision_tags_asset_id`, `vision_tags_source_sha256`,
  `vision_tags_cache_key`); tolerant `from_dict`/`to_dict`; без migration и
  version bump — как обещано.
- `review_bundle.attach_selected_asset` — entry строится из фактического B
  (совпадение в shortlist или заново), rebind provider/source/license/
  policy, явный `replaces_asset_id=A`, alternatives пересобраны без B.
  Прежний дефект (`setdefault` на протухшем dict) устранён ровно по
  рекомендации VA-NEW-04.
- `evidence.py` — `bind_vision_tags` / `carry_vision_evidence` /
  `current_vision_tags`: единственный канонический envelope, валидность
  решает привязка к asset id и checksum.
- Перенос envelope через все rebuild-пути: `with_policy_decision`,
  `ensure_selected_asset_downloaded` (lineage на fallback),
  `rank_provider_results`, `media_library._normalize_asset`.

Repair `a7bec3c` (закрыл четыре подтверждённых review-gap):

- envelope стал строго fail-closed: обязательны все части (id, bound id,
  текущий sha, source sha, cache key), любое несоответствие/неполнота →
  Vision-авторитет отозван, объект остаётся читаемым;
- draft completion (`asset_scene_completion.complete_scene_assembly`) —
  primary-slot fallback с чужим id проходит download-путь со stamped
  lineage к **оригинальному** A (`original_selected_asset_id`), а не к
  промежуточному;
- `rank_local_assets` переносит envelope (active local ranking);
- compatibility preview rebuild (`prepare_visual_preview_for_project`)
  вызывает `attach_selected_asset` — fallback lineage сохраняется;
- `observed` для semantic reselection считается только по валидному
  envelope (нет вакуумного триггера).

Repair `2577307` (MAJOR-RR-01): `_current_local_checksum` в
`rank_local_assets` пересчитывает SHA-256 текущих локальных байтов
per-asset и подставляет его в проверяемое поле; `OSError` → `""` → Vision
authority отозван fail-closed; persisted-записи не модифицируются.

Тесты трёх волн покрывают все заявленные пути; прогон шести owning-модулей
сейчас — 127 OK. RED-статусы (2 failures + 4 errors; «все четыре пути RED»;
один owning failure) заявлены в plan-блоках и этим аудитом не
перевоспроизводились.

## 3. Работаем ли по-другому — фактические изменения практики

Появилось и работает:

1. **Машинный слой перед review существует**: гейты зелёные локально
   (hook + кэши на диске) и продублированы в CI. Пирамида контроля больше
   не перевёрнута: дешёвый слой ловит первым.
2. **Bounded-темп**: четыре содержательных пакета + docs-сверка + два
   repair за один календарный день восемью маленькими коммитами; каждый
   repair — отдельный bounded-коммит по итогам независимого review.
3. **Trailers**: `Plan-Step` на всех продуктовых коммитах;
   `Owner-Package`/`Finding` впервые применены в `1bf7ecc` (M1-B) — удачная
   практика, пока разовая.
4. **Рост зеркал остановлен**: M1-B — net 0 строк в зеркалах, M1-C —
   net +1; repair-коммиты зеркала не трогают вообще; closure-записи —
   одна-две строки, переписывающие прежнюю next-action-строку. Против
   прежних многокилобайтных журнальных строк это смена режима, а не
   косметика.
5. **Findings-как-тесты**: каждый закрытый review-gap имеет
   RED-воспроизведение в owning-тестах — политика «findings, меняющие
   поведение, кодируются тестами» реально исполняется.

Не прижилось или прижилось частично:

6. **Mypy-ratchet не движется** — см. F1 (главный процессный долг).
7. **Ruff-ratchet** — одно снятие из 20+ (M1-B); лучше, чем ноль, но темп
   символический.
8. **Verdict-строки в коммитах** отсутствуют; вердикты review живут
   фразами в plan-блоках («four confirmed independent-review gaps»,
   «MAJOR-RR-01»). Допустимая вариация принятого правила, но см. F6.
9. **Bootstrap hook'а не документирован** — см. F5.

## 4. Findings

- **F1 · MAJOR (process).** Mypy-baseline (`pyproject.toml`, 28 модулей с
  `ignore_errors=true`) не сдвинулся ни на один модуль, при том что
  M1-B/M1-C правили шесть из них (`visual_preview`, `models`,
  `review_bundle`, `asset_manifest_builder`, `asset_provider_adapters`,
  `asset_scene_completion`) вместе с owning-тестами — то есть ровно в
  условиях, при которых объявленная стратегия ratchet требует снимать
  подавление. Следствие: новый код identity/evidence-слоя — самого
  рискового по классам ошибок K4/K6 — mypy фактически не проверяется.
  Минимальная коррекция: правило «слайс, трогающий baseline-модуль, либо
  снимает его из списка, либо одной строкой в commit body фиксирует, почему
  нет»; иначе baseline станет постоянным.
- **F2 · MINOR (governance/docs).** Owner-решение, разрешившее persisted
  `replaces_asset_id` (M1-C), существует только фразой «Owner permission in
  the M1-C prompt satisfies the earlier decision gate» в closure-блоке.
  Реестр «Уже выданные owner approvals» (план, ~строка 1325) его не
  фиксирует, а две формулировки «OWNER DECISION REQUIRED» (reconciliation
  ~строка 157 и секция PLAN-9A ~строка 4070) остались в настоящем времени —
  свежая сессия, читающая секцию PLAN-9A, сочтёт расширение неразрешённым.
  Коррекция: при closure Review #1 одной строкой пометить decision
  satisfied (для M1-C) в обоих местах; для M1-D требование остаётся в силе.
- **F3 · MINOR (routing risk).** Запас зеркал: START_HERE 99/100,
  SYSTEM_MAP 238/240, CURRENT_STATE 277/280 — суммарно 6 строк, а до WP0-B
  (плановое место — между M2-B и LIVE-5) остаётся ≥5 закрытий (Review #1,
  M1-D, M1-E, Review #2, M2-A, M2-B, Review #3). Фактическая практика
  «closure переписывает существующую next-action-строку, не добавляет
  новую» делает это выполнимым, но правило нигде не записано. Коррекция:
  зафиксировать его одной строкой (или перенести WP0-B раньше при первом
  же отказе вписаться).
- **F4 · MINOR (recoverability).** Файл финального стратегического аудита
  2026-08-10 в репозитории отсутствует (подтверждено: в `docs/audits/` его
  нет, worktree чистый) — владелец намеревался сохранить, но не приложил.
  Содержательно закрыто: маршрут и обоснования пересохранены в
  reconciliation-блоке плана; сам документ — по желанию владельца.
- **F5 · MINOR (bootstrap).** `core.hooksPath=.githooks` — локальная
  настройка; команда установки не документирована ни в `AGENTS.md`
  («Gates»), ни в README (упоминание есть только в reconciliation-блоке).
  Свежий клон молча живёт без pre-commit-гейтов до первого CI. Коррекция:
  одна строка в секции «Gates».
- **F6 · INFO (process).** Вердикты независимых review не записываются ни
  строкой в коммите, ни явным словом в plan-блоках M1-C (только пересказ
  findings). Findings закодированы тестами — этого достаточно для
  recoverability поведения, но связка «какой review что решил» снова живёт
  только в чатах.
- **F7 · INFO (docs freshness).** `check_agent_docs` даёт три advisory
  NOTE: `CURRENT_STATE.md` (last_verified `69af3ca`, 10 файлов дрейфа),
  `CLEANUP_REGISTRY.md` (`72221e1`, 60 файлов), план (`baseline_head`
  `38fed31`, 80 файлов). Метаданные свежести отстают от фактических
  изменений; обновлять — отдельным reviewed-слайсом, как требует checker.
- **F8 · INFO (code).** Литерал `max_dimension: 720` в payload ключа v2 и
  дефолт трансформа — два независимых числа в одном файле
  (`visual_preview.py:252` и `:265`); сегодня согласованы, при изменении
  одного без другого ключ начнёт лгать о transform. Кандидат на общую
  константу при следующем touch этого файла.
- Отдельно проверено и **не является** finding: секция PLAN-9A сохраняет
  `status: pending / not started` при четырёх коммитах `Plan-Step: PLAN-9A`
  — это соответствует записанному правилу «bounded correction не открывает
  и не закрывает контракт секции» (прецедент PLAN-9C-2/9C-3); поле
  `commit: —` при этом дословно устарело — та же будущая docs-правка.

## 5. Состояние продукта и маршрута

- **Checkpoint:** PLAN-9D (in progress); PLAN-9D-D — NOT STARTED/blocked.
  Next exact action — Review #1 (M1-A…M1-C, identity/evidence lineage) —
  согласован дословно во frontmatter плана, START_HERE:99, хвостах
  CURRENT_STATE и SYSTEM_MAP. Противоречий в routing-цепочке нет; прежняя
  ошибка «next = LIVE-5» устранена и не вернулась.
- **Закрыто из обязательного набора до LIVE-5:** VA-NEW-01, 02, 03, 04, 05.
  **Осталось:** M1-D (VA-NEW-08, требует owner decision по resume
  fingerprint — требование в силе), M1-E (VA-NEW-09), M2-A (VA-NEW-06+10),
  M2-B (VA-NEW-12 minimal) и три batched review. После LIVE-5 — M3
  (пользовательский слайс: PLAN-9B-5b, OD-P-2, C58/MOTION-CS1, C63), M4
  (acceptance: PLAN-11 + product checkpoint PLAN-9E), M5 (longform v1.1).
- **Ни одного финального Short канонического пути по-прежнему нет** —
  продуктовая дистанция не изменилась с прошлого аудита; изменилась
  достоверность фундамента: evidence-путь (preview→Vision→review→manifest)
  теперь привязан к байтам и identity, что и было целью M1.
- Опциональный «первый владельческий Short» (draft_complete + ручной бриф
  через script-путь) остаётся доступным в любой момент и не начат.

## 6. Вердикт

- **Внедрение:** PASS — все шесть коммитов делают заявленное; расхождений
  «заявлено ↔ код» не найдено.
- **Процесс:** PASS с оговорками F1 (ratchet) и F5 (bootstrap) — машинный
  слой, bounded-темп, однострочные closure и findings-как-тесты реально
  действуют.
- **Маршрут:** PASS — routing согласован; docs-долги F2/F7 — однострочные
  правки ближайшего docs-слайса.
- **Рекомендованный порядок:** выполнить Review #1 как записано; в его
  closure-слайсе одной строкой закрыть F2 и `commit: —`; правило ratchet
  (F1) и строку bootstrap (F5) — туда же или в WP0-B; M1-D не начинать до
  owner decision по fingerprint.
