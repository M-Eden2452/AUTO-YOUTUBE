# PLAN-9D-A — offline ground-truth benchmark

Evaluation-only. Ничего здесь не является production-контрактом, не включается в
runtime и не меняет поведение кода. Owner каталога — `tests/plan9d_ground_truth.py`
(контракт данных и измерение) и `tests/plan9d_corpus_builder.py` (сборка корпуса и
рендер пакета разметки). Локи — `tests/test_plan9d_ground_truth_baseline.py`.

**PLAN-9D НЕ закрыт.** Этот slice готовит основание для измерения и ничего об
улучшении decision path не утверждает.

## Зачем

PLAN-9D требует доказать улучшение decision path на уже имеющихся данных.
Единственный выполненный реальный Vision-прогон покрывает 3 сцены и 6 кандидатов,
и ни в одной из них metadata-only ветка не даёт сильного ответа — значит, на этом
корпусе изменение физически не может стать хуже, и «улучшение» там недоказуемо.
Нужен независимый корпус, на котором регрессия возможна.

## Файлы

| Файл | Что это |
|---|---|
| `corpus_v1.json` | Замороженный корпус: 16 независимых сцен, 75 candidate-in-scene наблюдений, blind id, кадры с SHA256 |
| `annotations_v1.json` | Разметка владельца. Сейчас `status = WAITING_FOR_OWNER_ANNOTATION` — шаблон, а не результат |

Изображения в репозиторий **не копируются**: это чужой лицензированный
provider-материал, а `projects/` намеренно untracked. Корпус несёт путь, размеры и
SHA256 каждого кадра, поэтому все тесты, кроме одного явно пропускаемого, работают
на машине, которая `projects/` никогда не видела.

## Порядок работы

Разметка выполняется **один раз**. После этого benchmark работает полностью
автоматически: harness читает `annotations_v1.json` и никогда ничего не
спрашивает у человека во время прогона.

1. Сгенерировать слепой пакет (пишите **вне репозитория**, файл одноразовый):

   ```
   .\venv\Scripts\python.exe -B -m tests.plan9d_corpus_builder pack --out %TEMP%\plan9d_pack.html
   ```

2. Открыть пакет в браузере, пройти сцены, для каждой выбрать
   `BEST: C… / none_acceptable / undecidable`, отметить неприемлемых кандидатов и
   заполнить categorical-флаги. Кнопка сохраняет `annotations_v1.json`.
3. Положить полученный файл на место `tests/data/plan9d/annotations_v1.json`.
4. Прогнать targeted-тесты. Дальнейшие измерения повторяемы и автоматичны.

Пересобирать корпус (`build --force`) после разметки нельзя: изменится
`corpus_sha256`, и harness откажется считать разметку валидной — это защита, а не
неудобство.

## Что видит и чего не видит аннотатор

Видит: текст сцены, заявленные subject / action / environment / location,
`must_include`, `must_not_include`, заявленный контекст и противоречие, целевой
кадр и длительность, а также сами изображения кандидатов.

Не видит: провайдера, заголовок, описание, теги, лицензию, любые score,
`metadata_rank`, результат ranker, результат Vision, выбранный системой кандидат,
категории корпуса и исходный порядок кандидатов. Идентификаторы обезличены:
`C1..Cn` назначаются по `sha256(salt ‖ scene_key ‖ asset_id)` — детерминированно и
без связи с ранжированием.

Аннотатор **не** оценивает права, лицензионную политику, качество метаданных,
надёжность провайдера, технические размеры и внутренние score. Это решает система.

## Как считается baseline

`run_metadata_baseline` вызывает production-путь как есть:
`select_best_with_video` → `select_best_candidate`. Второго selector нет, своего
score нет, confidence не выдумывается. Кандидаты подаются без `vision_tags` —
это metadata-only ветка.

Заявленные evaluation-константы:

- `used_asset_ids` пуст: каждая сцена оценивается независимо;
- кандидаты **хранятся** в blind-порядке, но **подаются** в порядке манифеста,
  потому что ранжирование — стабильная сортировка и порядок входа разрешает
  ничьи. Подача в blind-порядке однажды сделала так, что хэш решал каждую ничью;
  это исправлено и залочено тестом;
- framing-гейт судит **заявленные provider-размеры** из записи кандидата, а не
  разрешение локального превью. Кандидаты без объявленных размеров дают
  `framing_unknown` (не hard reject) и помечаются `technical_dimensions_unknown`.
  Production-гейт не отключался.

## Покрытие категорий

Покрыто: `subject_mismatch_risk`, `must_include_declared`, `must_avoid_declared`,
`environment_conflict_risk`, `declared_conflicting_context`, `crop_framing_concern`,
`visible_text_or_logo_risk`, `ambiguous_needs_review`, `rights_blocked_candidate`,
`technical_dimensions_unknown`, `no_acceptable_candidate`, `regression_capable`.

**Не покрыто:** `non_real_footage_risk`. Ни один кандидат ни в одном локальном
проекте не несёт non-real-footage формулировок в provider-evidence (0 из 88
пригодных сцен). Синтезировать такую сцену запрещено, поэтому пробел зафиксирован,
а не заполнен.

`regression_capable` — сцены, где metadata-only ветка уже даёт непровальный ответ
с `support_status ∈ {full_support, partial_support}`. Без них A/B мог бы выглядеть
только нейтральным или лучшим.

## Готовность к будущим режимам Review и Auto

Оба будущих режима могут опираться на **один** decision owner. Разница — в
approval/escalation policy поверх уже существующих выходов, а не в ранжировании.
Здесь ничего из этого не реализовано.

Уже существующие сигналы, пригодные для такой политики: выбранный кандидат либо
его отсутствие; `blocking_reject_reasons` и `advisory_reject_reasons`;
`support_status` и `support_requirements`; `slot_verdict`; `rights_status`,
`allowed_for_render`, `review_required`; `semantic_match_status`,
`semantic_evidence`, `undecidable_fields`, `must_include_unverifiable`,
`metadata_status`; `framing_status`, `duration_status`; на уровне проекта —
`resolution_status`, `missing_scenes`, `completion`, `publish_ready`.

Чего не хватает — зафиксировано как **отсутствующий контракт, не добавлено**:

1. **Abstain и fallback неразличимы одним полем.** Когда decision owner
   возвращает `None`, оркестрация подставляет сгенерированный backdrop, и «нет
   приемлемого кандидата» отличается от «закрыто fallback'ом» только по
   `selected_by`. Явного scene-level поля нет.
2. **Нет поля disposition.** `support_status` описывает достаточность evidence, а
   не принятое решение; «принято автоматически» и «отправлено на review» нигде не
   записываются.
3. **Нет продуктового порога auto-safe.** Чтение `full_support` как «можно
   принимать автоматически» — соглашение этого benchmark (`AUTO_SAFE_SUPPORT`), а
   не объявленный контракт.
4. **Нет записи действия ревьюера** (принял / заменил / оставил нерешённым),
   с которой будущий benchmark мог бы сравнивать autonomous-режим.

Ни один режим не имеет права обходить rights blockers, `must_avoid`, заявленные
конфликты, misleading-content гейты, технические hard reject и явные ограничения
пользователя. Benchmark считает нарушение любого из них **blocking regression**.

## Что запрещено этому каталогу

Mock, scripted и любой fixture-backend не могут служить доказательством
визуального качества — `assert_admissible_evidence` отказывает такому arm'у до
любого измерения. Разметка от имени владельца не заполняется. Пока
`annotations_v1.json` в состоянии `WAITING_FOR_OWNER_ANNOTATION`, harness
возвращает этот же статус и не измеряет ничего.
