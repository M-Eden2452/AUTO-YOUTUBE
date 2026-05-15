# Cleanup report

Отчет составлен без удаления файлов. Это список кандидатов и рекомендаций, а не выполненная чистка.

## Файлы, которые точно используются текущим pipeline

- `pipeline.py` - главная точка входа.
- `config/video_style.json` - основной конфиг темы, стиля, путей, ассетов, музыки и Obsidian.
- `src/__init__.py` - пакет `src`.
- `src/config_loader.py` - загрузка конфига и переключение dev/prod/prod-preview режимов.
- `src/quote_generator.py` - создание `quote_plan`.
- `src/youtube_metadata.py` - создание `youtube_metadata.json`.
- `src/scene_planner.py` - создание `scene_plan`.
- `src/intro_generator.py` - создание intro-блока внутри `render_plan`.
- `src/music_finder.py` - создание `music_plan`.
- `src/asset_finder.py` - подбор/скачивание/создание ассетов.
- `src/image_tools.py` - работа с изображениями и placeholder.
- `src/layout_renderer.py` - отрисовка кадров.
- `src/video_renderer.py` - создание `render_plan`, рендер сцен, склейка и добавление музыки.
- `src/music_tools.py` - добавление фоновой музыки.
- `src/self_eval.py` - самопроверка результата.
- `src/obsidian_exporter.py` - экспорт Markdown-заметки в Obsidian или fallback в `outputs/`.
- `src/utils.py` - общие функции путей и JSON.
- `requirements.txt` - зависимости проекта.
- `.gitignore` - правила исключения секретов, venv, медиа и временных файлов.
- `.env.example` - безопасный пример переменных окружения.

## Текущие рабочие JSON outputs

Эти файлы являются рабочими промежуточными структурами текущего pipeline:

- `outputs/quote_plan.json`
- `outputs/scene_plan.json`
- `outputs/asset_plan.json`
- `outputs/render_plan.json`
- `outputs/music_plan.json`
- `outputs/youtube_metadata.json`
- `outputs/self_eval.json`
- `outputs/render_stage.json`

Они сейчас отслеживаются Git и используются как снимок последнего запуска. В будущем можно решить, должны ли они оставаться в репозитории или стать полностью временными артефактами.

## Файлы, которые нельзя трогать

- `.env` - секреты и API-ключи.
- `venv/` - локальное окружение.
- `.git/` - история Git.
- `music/background.mp3` - локальная музыка для текущего рендера; mp3 не коммитить.
- `assets/images/generated/*` - скачанные/сгенерированные изображения для текущих сцен; не удалять без подтверждения.
- `assets/images/jordan_peterson_placeholder.jpg` - автосозданный placeholder, может использоваться как fallback.
- `outputs/final_preview.mp4`, `outputs/final_video.mp4` и другие mp4 - результаты рендера; не коммитить и не удалять без подтверждения.
- `outputs/render_temp/` - временные клипы production-рендера; можно чистить только после подтверждения.

## Файлы, которые возможно устарели

Корневые скрипты относятся к раннему MVP и не вызываются из `pipeline.py`:

- `main.py` - старый генератор YouTube package из `outputs/script.txt` через OpenAI.
- `scene_planner.py` - старый генератор текстового scene plan из `outputs/script.txt`.
- `scene_plan_json.py` - старый генератор `outputs/scene_plan.json` через OpenAI.
- `download_broll.py` - старый скачиватель видео с Pexels в `assets/broll/`.
- `render_from_scene_plan.py` - старый rough render по `outputs/scene_plan.json`.
- `assemble_broll_video.py` - старая склейка mp4 из `assets/broll/`.
- `assemble_broll_with_text.py` - старая сборка b-roll с текстом.
- `add_music.py` - старое добавление музыки к `outputs/broll_with_text.mp4`.

Эти скрипты дублируют функциональность, которая теперь живет в `src/`:

- генерация сцен - `src/scene_planner.py`;
- метаданные - `src/youtube_metadata.py`;
- ассеты - `src/asset_finder.py`;
- рендер - `src/video_renderer.py`;
- музыка - `src/music_finder.py` и `src/music_tools.py`;
- Obsidian export - `src/obsidian_exporter.py`.

## Старые outputs и временные файлы

Кандидаты на временные или старые MVP-файлы:

- `outputs/script.txt` - старый входной сценарий для корневых OpenAI-скриптов.
- `outputs/scene_plan.txt` - старый текстовый план сцен.
- `outputs/youtube_package.txt` - старый YouTube package из `main.py`.
- `outputs/final_preview_silent.mp4` - промежуточный silent-файл dev-рендера.
- `outputs/final_prod_preview.mp4` - production-preview результат, не часть обязательной документации.
- `outputs/final_prod_preview_silent.mp4` - промежуточный silent-файл production-preview.
- `outputs/final_video_silent.mp4` - промежуточный silent-файл production-рендера.
- `outputs/render_temp/` - временные scene clips и concat list.
- `broll_with_text_musicTEMP_MPY_wvf_snd.mp4` - временный файл MoviePy в корне проекта.

## Старые assets

`assets/broll/scene_01.mp4` - `assets/broll/scene_34.mp4` выглядят как старый b-roll из раннего MVP. Текущий `src/asset_finder.py` работает с изображениями в `assets/images/generated/`, а не с видео из `assets/broll/`.

Эти mp4 занимают много места и не должны попадать в Git. Удалять их можно только после подтверждения, потому что они могут быть полезны как архив старых ассетов.

## Папки-заготовки

- `scripts/` - сейчас пустая.
- `subtitles/` - сейчас пустая.
- `assets/images/.gitkeep`, `assets/broll/.gitkeep`, `music/.gitkeep` - полезны, чтобы Git хранил пустые папки.

Пустые папки лучше оставить, если планируются будущие скрипты, субтитры и ассеты.

## Файлы, которые можно удалить после подтверждения

Рекомендуемые кандидаты на удаление после отдельного подтверждения:

- `broll_with_text_musicTEMP_MPY_wvf_snd.mp4` - временный MoviePy-файл в корне.
- `outputs/script.txt` - старый MVP input.
- `outputs/scene_plan.txt` - старый MVP scene plan.
- `outputs/youtube_package.txt` - старый MVP YouTube package.
- `outputs/final_preview_silent.mp4` - промежуточный файл.
- `outputs/final_prod_preview.mp4` - старый preview-результат, если больше не нужен.
- `outputs/final_prod_preview_silent.mp4` - промежуточный файл.
- `outputs/final_video_silent.mp4` - промежуточный файл.
- `outputs/render_temp/` - временные клипы рендера.

Возможные кандидаты, требующие более осторожного решения:

- `assets/broll/*.mp4` - старый b-roll-архив раннего MVP.
- `main.py`
- `scene_planner.py`
- `scene_plan_json.py`
- `download_broll.py`
- `render_from_scene_plan.py`
- `assemble_broll_video.py`
- `assemble_broll_with_text.py`
- `add_music.py`

Корневые Python-скрипты лучше не удалять сразу. Сначала можно перенести их в `legacy/` или `archive/`, если нужен исторический контекст.

## Файлы, которые лучше оставить

- `pipeline.py`
- `src/`
- `config/video_style.json`
- `requirements.txt`
- `.gitignore`
- `.env.example`
- `README.md`
- `docs/`
- `.gitkeep` файлы в пустых рабочих папках
- рабочие JSON в `outputs/`, пока не принято решение о новой политике артефактов

## Рекомендации по следующей чистке

1. Сначала подтвердить список удаления.
2. Удалить явные временные mp4 и `outputs/render_temp/`.
3. Решить, нужны ли старые TXT-файлы в `outputs/`.
4. Решить судьбу корневых MVP-скриптов: удалить или перенести в `legacy/`.
5. Решить, хранить ли рабочие JSON в Git или генерировать их локально.
6. Проверить `.gitignore`, чтобы новые медиа и временные файлы больше не попадали в staging.

