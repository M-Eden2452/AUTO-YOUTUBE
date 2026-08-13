---
status: legacy
---

# Основной YouTube Pipeline

> **LEGACY — не основной пайплайн и не рабочий режим.** Описанный здесь стек
> (`pipeline.py`, `asset_finder`, `video_asset_engine`, `src/voice_engine.py`,
> Obsidian-экспорт) — legacy-путь, назначенный к retirement по **PLAN-L**
> (реестр: C08, C12, C30). Он не проходит canonical rights/network gates.
> Активное приложение — `content_creator`, вход `python -m ai_youtube`.
> Current truth: [SYSTEM_MAP.md](../current/SYSTEM_MAP.md) и
> [CLEANUP_REGISTRY.md](../current/CLEANUP_REGISTRY.md).

## Назначение

Основной пайплайн собирает видео по существующим каналам и задачам из `channels/` и `content/`. Точка входа остается `pipeline.py`.

## Как работает

Последовательность сейчас такая: загрузка конфигурации, создание quote/scene plan, озвучка через существующий `src/voice_engine.py`, подбор ассетов, музыка, render plan, FFmpeg/MoviePy-рендер, self-eval и экспорт заметки Obsidian.

## Основные файлы

- `pipeline.py` - CLI и оркестрация старого пайплайна.
- `src/config_loader.py` - базовая конфигурация и dev/prod режимы.
- `src/channel_loader.py` - объединение профиля канала и конкретного video task.
- `src/quote_generator.py` - текстовая основа ролика.
- `src/scene_planner.py` - сцены и тайминги.
- `src/voice_engine.py` - текущая рабочая озвучка, включая ElevenLabs и MOSS.
- `src/asset_finder.py`, `src/video_asset_engine.py`, `src/media_library.py` - поиск и локальный индекс медиа.
- `src/video_renderer.py` - сборка видео.

## Этап

Рабочий режим. Его нельзя ломать при добавлении новых приложений. Новый `news_to_short` добавлен отдельной веткой CLI и не заменяет этот пайплайн.

## Что стоит доделать позже

- Постепенно перевести озвучку на общий `src/audio/tts/` контракт.
- Разделить приложения физически в `apps/` только после стабилизации границ.
- Унифицировать job/state manifest между длинным пайплайном и новыми режимами.

