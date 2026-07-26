# Локализация и голос: что где решается

Снято по коду на этапе D2/E2 (после `81e63e0`).
Формат: **настройка → ConfigResolver key → потребитель → runtime-результат**.

Этот документ дополняет `docs/implementation/config_resolver/CONFIG_MAP.md`: там —
вся конфигурация проекта, здесь — только путь «язык и голос до стадии озвучки».

---

## 1. Вертикальный путь

```
Wizard/CLI input
  → ContentCreationRequest (language, voice.profile, voice.audio_file)
  → NewsJob.language / NewsJob.localizations[<id>]
  → ConfigResolver (src/config_resolver)
  → ResolvedLocalization (src/localization)
  → voice adapter (src/news/voice_adapter.resolve_localization_for_channel)
  → voice stage (src/news/voice_stage)
  → localizations/<id>/voice/voice_manifest.json
```

Ровно один объект (`ResolvedLocalization`) отвечает на вопросы «какой язык, какой
голос, какой источник звука, будет ли вызван TTS». До D2 на них отвечали три
независимых места: стадия озвучки, preflight-сводка и запись approval.

---

## 2. Настройка → ключ → потребитель

| Настройка | ConfigResolver key | Откуда может прийти | Потребитель | Runtime-результат |
|---|---|---|---|---|
| язык | — (нормализуется в `src/localization/locales.py`) | CLI `--language`, `job.json:language`, `channel_config.json:language`, `channel.json:default_language` | `ResolvedLocalization.language` | нормализованный код (`ru-RU` → `ru`) |
| locale | — | `channel_config.json:languages.<id>.script_locale`, таблица locales | `LocalizationState.script_locale`, explain | `ru-RU` |
| localization_id (папка) | — | `job.json:localizations`, CLI | пути `localizations/<id>/...` | **никогда не нормализуется** |
| язык субтитров | — | по умолчанию равен языку озвучки | `ResolvedLocalization.subtitle_language` | подготовлено для Q3 |
| провайдер | `voice.provider` | `channel_config.json:voice`, `languages.<id>.voice`, `AUDIO_POLICY_DEFAULTS`, runtime | `voice_stage`, `narration_workflow` | `elevenlabs` / `audio_file` / `disabled` |
| профиль голоса | `voice.voice_profile` | те же + CLI `--voice-profile` | `voice_profile_registry.lookup_profile` | `VoiceProfile` |
| voice_id | — (из `voices.yaml`) | `channels/<id>/voices.yaml`, `ELEVENLABS_VOICE_ID` как **fallback** | `TTSRequest.voice_id`, approval, manifest | строка, не секрет |
| модель TTS | `voice.model_id` | `voices.yaml:model_id`, `channel_config.json:voice.model`, шаблон | `TTSRequest.model_id` | `eleven_multilingual_v2` |
| параметры провайдера | `voice.provider_settings` | `voices.yaml:settings`, `channel_config.json:voice.settings` | `narration_workflow._combined_settings` | dict без секретов |
| стиль подачи | часть `voice.provider_settings` | `settings.style` | ElevenLabs | `ResolvedLocalization.voice_style` (производное, не хранится дважды) |
| fallback | `voice.fallback_policy` | `AUDIO_POLICY_DEFAULTS`, `voice_workflow.never_auto_fallback_to_paid` | **новый потребитель:** `src/localization/resolver._apply_secret_fallback` | `none` / `manual_audio` / `local_tts` |
| наличие ключа | `secrets.elevenlabs_api_key` | окружение | `ResolvedLocalization.secret_configured` | **только `bool`** |
| источник narration | — | решение резолвера | `voice_stage` | `tts` / `manual_audio` / `existing_artifact` / `none` |
| ручной файл | — | CLI `--audio-file` | `voice_workflow.import_manual_audio` | путь |
| готовая озвучка | — | `voice_manifest.json` + файл на диске | `voice_stage`, `service` | путь или `""` |
| путь вывода | — | `scene_voice_generator.generation_output_paths` | сборка narration | `localizations/<id>/voice/narration.wav` |

---

## 3. Приоритет

Порядок слоёв — **тот же, что установил D1, без изменений**:

```
global_default → format_policy → channel_profile → channel_config
    → template_policy → project_override → localization_override
    → runtime_override            (+ environment: только секреты)
```

- `template_policy > channel_config` **сохранено**. Практический эффект тот же, что
  описан в D1: `never_auto_fallback_to_paid: true` у `nature_science_news_ru`
  проигрывает шаблонному `fallback_policy: manual_audio`. D2 это не меняет, а
  показывает: у настройки стоит предупреждение `template_policy_overrode_channel`,
  и `voices explain` его печатает. Рекомендация на будущее: если канал должен уметь
  запретить fallback, это отдельный этап с планом совместимости — молча менять
  порядок нельзя.
- Явный выбор пользователя (`--voice-profile`, `--voice-provider` у `voices explain`)
  подаётся в резолвер как слой `runtime_override`, поэтому «runtime бьёт
  localization» — свойство резолвера, а не отдельная ветка в коде локализации.

---

## 4. Три источника озвучки

| Источник | Когда выбирается | Что делает стадия |
|---|---|---|
| `existing_artifact` | `voice_manifest.json` объявляет аудиофайл, файл существует, язык совпадает | ничего не генерирует, **не перезаписывает** манифест, возвращает его как есть |
| `manual_audio` | провайдер `audio_file`, или `output_mode=manual_audio`, или передан `--audio-file`, или fallback после отсутствия ключа | ждёт файл, TTS не вызывает |
| `tts` | провайдер требует ключ, ключ настроен, готовой озвучки нет | генерация возможна, но только после `approval.json` |
| `none` | `voice.enabled=false` или `output_mode=disabled` | стадия пропускается |

Локальный TTS: в `FALLBACK_POLICIES` значение `local_tts` есть, но **ни один
локальный провайдер не зарегистрирован** в `TTSProviderManager`
(`src/voice_engine.py local_stub` и MOSS — legacy dev-only, и по `CLAUDE.md` не
могут предлагаться как production). Поэтому `fallback_policy=local_tts` даёт
явную ошибку `local_tts_unavailable`, а не тихое ничегонеделание.

---

## 5. Fallback при отсутствии ключа

```
провайдер elevenlabs → ключ ELEVENLABS_API_KEY не настроен
  → fallback_policy=manual_audio  → источник manual_audio, статус provider_selection_required,
                                     сеть не вызывается, в сообщении — команда import-audio
  → fallback_policy=local_tts     → ошибка local_tts_unavailable, статус blocked
  → fallback_policy=none          → ошибка fallback_unavailable, статус blocked
```

Голос и провайдер при fallback **не подменяются**: меняется только источник звука,
и причина всегда записывается (`fallback_reason`, `tts_blocked_reason`).

---

## 6. Секреты

Ключ не может попасть в контракт локализации физически: `ResolvedLocalization`
хранит имя переменной окружения и два `bool` (`secret_required`,
`secret_configured`). `voices explain` печатает «настроен / не настроен», в JSON у
секретных ключей резолвера стоит `***`. Проверка наличия живёт в
`src/localization/secrets.py` и берёт от результата только `bool`.

Почему проверка отдельная, а не только слой окружения резолвера:
`environment_layer` намеренно не открывает `.env`, а `ElevenLabsProvider` при
создании открывает (`load_elevenlabs_env`). Если решать про fallback по слою
окружения, «ключ есть в `.env`, но процесс его не загрузил» выглядело бы как
«ключа нет», и озвучка перестала бы генерироваться там, где сегодня она
генерируется.

---

## 7. Совместимость

- Старые `job.json` / `project.json` / `voice_manifest.json` читаются без миграции.
  Новые поля манифеста (`localization_id`, `locale`, `localization_status`,
  `narration_source`, `narration_output_path`, `tts_blocked_reason`,
  `fallback_policy`, `fallback_applied`, `secret_configured`) — **аддитивные**;
  `status` и `voice_stage_status` не изменились, потому что на их прежнем смысле
  («результат стадии») держатся `quality_check`, `preview_render` и `project status`.
- Старые подписи работают: `build_safe_voice_manifest` и
  `build_or_generate_voice_manifest` без параметра `localization` дают ровно
  прежний результат (проверяется тестом).
- `resolve_localization_for_channel` возвращает `None` для канала, которого
  резолвер не знает, и вызывающий продолжает работать на старых читателях.
- Исторические проекты не изменяются: тест сверяет байты `job.json` до и после
  чтения для каждого проекта на диске.

---

## 8. Что осталось на compatibility path

| Потребитель | Почему не переведён |
|---|---|
| Story Card (`src/templates/story_card/`, `src/production_plan/story_card_short_render.py`) | шаблон без озвучки (`story_card_no_voice`); подключение расширило бы scope без пользы |
| Legacy channel pipeline (`pipeline.py --channel/--video`, `src/voice_engine.py`) | своя система голосов и каналов; миграция — отдельный этап с планом удаления legacy |
| Documentary / Anime Factory | не входят в vertical slice D2/E2 |
| `src/audio/voice_cli.py` (`--voice-action`) | обслуживающий CLI; профили читает через тот же `load_voice_profiles`, поведение не менялось (кроме исправления env-fallback) |
| Стили субтитров канала (`channels/*/subtitle_style.json`) | часть E2 по роадмапу, но этот этап явно запрещает менять subtitle renderer; язык субтитров уже передаётся |

---

## 9. Найденные и исправленные ошибки прежней архитектуры

1. **`ELEVENLABS_VOICE_ID` перекрывал `voice_id` каждого elevenlabs-профиля** в
   любом `voices.yaml` (`src/audio/voice_cli.load_voice_profiles`). При двух
   профилях это означало, что все языки говорят одним голосом — англоязычный
   профиль молча получал русский `voice_id`. Теперь переменная окружения —
   fallback для профиля без собственного `voice_id`, как это уже читает
   `solar_vs_nuclear_render.py`. Для единственного настроенного канала значения
   совпадают, поэтому его поведение не изменилось.
2. **`fallback_policy` разрешался, но не читался никем** (проверено поиском по
   `src/` и `pipeline.py`). Отсутствие ключа приводило к попытке платного вызова,
   которая падала внутри провайдера. Теперь политика реально применяется до любого
   обращения к сети.
3. **Блок `channel_config.json:languages.<id>.voice` не читался никем.** Теперь это
   слой `localization_override`, и он побеждает канальный `voice`.
4. **Профиль голоса не проверялся на язык.** Английский текст можно было отправить
   русским голосом. Теперь это ошибка с указанием, что именно исправить.
5. **Поиск профиля был выписан трижды** (`voice_adapter`, `capabilities`, через них
   мастер). Единственная реализация —
   `src/audio/voice_profile_registry.lookup_profile`.
6. **Стадия озвучки могла перезаписать готовый манифест заглушкой.** Раньше от
   этого защищал только вызывающий (`service._completed_narration`); теперь защита
   есть и в самой стадии.

---

## 10. Команды

```bash
./venv/Scripts/python.exe -m src.content_creation.cli voices explain --channel nature_science_news_ru
./venv/Scripts/python.exe -m src.content_creation.cli voices explain --channel nature_science_news_ru --language en
./venv/Scripts/python.exe -m src.content_creation.cli voices explain --channel nature_science_news_ru --language ru --trace --json
```

Только чтение: без сети, TTS, Vision, downloads, рендера и записи в проект.
