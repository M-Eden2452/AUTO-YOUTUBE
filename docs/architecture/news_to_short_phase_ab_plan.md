# News To Short Phase A+B Architecture

## Решение

Фаза A+B реализована как новый пакет `src/news/` и guarded CLI-ветка в `pipeline.py`. Существующие файлы физически не переносятся в `apps/` и `packages/`.

После продолжения работы добавлены физические app-границы:

- `apps/news_to_short/`
- `apps/youtube_pipeline/`
- `apps/anime_factory/`
- `packages/`

Это wrapper-структура: старый код пока остается на месте, но новые точки входа уже существуют.

## Границы

- `src/news/` владеет job manifest, стадиями, article/research/script/visual artifacts.
- `src/audio/tts/` владеет общим контрактом TTS-провайдеров.
- `src/voice_engine.py` остается рабочим старым движком и не заменяется.
- `src/providers/` остается текущей базой для будущего подключения asset providers.

## Будущие провайдеры

Storyblocks и Envato учитываются только как будущие элементы provider order. Ключи будут читаться из `.env` после отдельной задачи, не из JSON профиля канала.

## Этап C

Подбор исходников добавлен через `src/news/asset_manager.py`. Он не заменяет существующие `src/providers/` и `src/media_library.py`, а адаптирует их к формату `news_to_short`.

Приоритет:

1. Пользовательские файлы с `rights_status=user_owned`.
2. Локальная библиотека с разрешенными правами.
3. Бесплатные провайдеры Pexels, Pixabay, Unsplash, если ключи уже доступны в окружении.
4. Будущие платные провайдеры Storyblocks/Envato только как архитектурные слоты.

Материалы `reference_only`, `blocked`, `unknown` и `editorial_review_required` не выбираются для рендера.

## Обратная совместимость

Новый режим включается только флагом `--news-to-short`. Без него `pipeline.py` продолжает выполнять старую последовательность.

Также доступен запуск:

```powershell
.\venv\Scripts\python.exe -m apps.news_to_short --topic "..." --until-stage export
.\venv\Scripts\python.exe -m apps.youtube_pipeline --channel quotes --video example
.\venv\Scripts\python.exe -m apps.anime_factory --input anime_factory/input/source.mp4 --episode episode_001
```
