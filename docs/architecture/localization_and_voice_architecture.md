# Localization And Voice Architecture

## Локализации

Один `news_to_short` job содержит общий master-проект и отдельные языковые версии. Сейчас создаются директории `ru`, `en`, `es`, а другие языки можно добавить в модель `NewsJob.localizations`.

Локализованный сценарий должен ссылаться на те же `claim_id`, что и master research. Перевод не должен добавлять новые факты.

## TTS-контракт

Общий контракт находится в `src/audio/tts/`:

- `TTSRequest` описывает job, язык, сцену, провайдера, голос, модель, текст, формат и настройки.
- `TTSResult` описывает файл, длительность, sample rate, каналы, cache hit и `source_type`.
- `TTSProvider` задает общий интерфейс `preflight()` и `synthesize()`.
- `TTSProviderManager` регистрирует провайдеров по имени и блокирует paid provider без approval.

## Провайдеры

- `audio_file` реализован для пользовательского WAV и возвращает `source_type=user_provided`.
- `elevenlabs` сейчас поддерживает безопасный preflight/catalog без synthesis endpoint.

## Защита ElevenLabs

API-ключ читается только из `ELEVENLABS_API_KEY`. Значение ключа не сохраняется и не печатается. Paid TTS требует явного approval. Голос Dom зарегистрирован как кандидат `ru_dom`, но не используется автоматически.

## Текущее поведение стадии voice

В `news_to_short` стадия `voice` сейчас создает `voice_selection.json` и `voice_manifest.json` со статусом `provider_selection_required`. Это намеренно: без чернового `audio_file` или отдельного утверждения ElevenLabs система не вызывает платный TTS и не подставляет платный fallback.

Полная генерация ElevenLabs должна быть добавлена отдельной ручной командой audition/final после проверки preflight и записи `approval.json`.

Ручная озвучка уже может быть импортирована командой `--voice-action import-audio`. Такой файл копируется в `localizations/<language>/voice/narration.wav`, получает `source_type=user_provided`, обновляет `voice_manifest.json` и синхронизирует `job.json`.

Когда ручной голос импортирован и quality check проходит, `news_to_short_final_renderer_v1` может собрать локальный vertical MP4 без платных TTS-вызовов.
