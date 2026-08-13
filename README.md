# AI-YouTube

Локальная система создания видео для YouTube. На входе — тема, свой текст,
готовый сценарий или ссылка на статью; дальше система пишет сценарий, разбивает
его на сцены, подбирает под каждую сцену визуальный материал и проверяет права на
него, озвучивает, накладывает субтитры, рендерит вертикальный ролик и сохраняет
evidence: чем именно доказано, что в кадре то, что заявлено.

По умолчанию всё офлайн и бесплатно. Сеть, платная озвучка и платный анализ
кадров включаются явными флагами и конфигами — не «сами» и не по факту наличия
ключа в `.env`.

## Статус на 2026-08-13

- Работает одно приложение — **`content_creator`**. `video_repurposer`
  (нарезка и переработка чужого видео) объявлен в каталоге как `planned` и
  не работает.
- Работает один формат — вертикальный short **1080×1920**. `longform` и
  `horizontal_clip` объявлены `planned`.
- Работают два шаблона: **`story_card_text_only_v1`** (карточка с текстом,
  озвучка не обязательна) и **`fullscreen_voiceover_v1`** (полноэкранное видео
  с обязательной озвучкой).
- Канонический publish-ready ролик **ещё не выпущен**: режим `strict` по
  умолчанию не пропускает результат, который не доказан. Черновик получить
  можно — `--completion-mode draft_complete`, у него всегда
  `publish_ready=false`.
- `pipeline.py`, `src.content_creation.cli` и `apps/*` — **переходные**
  compatibility-входы прежних поколений. Новую работу через них не начинают.

Что делается прямо сейчас и что следующее — [docs/current/START_HERE.md](docs/current/START_HERE.md).

## Установка

Windows, Python ≥ 3.11. Все команды запускаются интерпретатором venv; системный
`python` может быть другой версии.

```powershell
python -m venv venv
.\venv\Scripts\python.exe -m pip install --upgrade pip
.\venv\Scripts\python.exe -m pip install -r requirements.lock
```

`requirements.lock` — воспроизводимая установка, `requirements.txt` — верхний
уровень зависимостей, `requirements-dev.lock` — инструменты разработки.

FFmpeg отдельно ставить не нужно: бинарь приходит с пакетом `imageio-ffmpeg`.
`ffprobe` вызывается из `PATH` (`src/assets/frame_sampling.py:90`); без него
часть проверок медиа вернёт `failed`, рендер продолжит работать.

Ключи провайдеров и голосов живут в `.env`. Он не коммитится и не читается
агентами. Без ключей поиск работает на бесплатных источниках (Wikimedia Commons,
NASA, Internet Archive); Pexels и Pixabay подключаются только при наличии ключа.

В свежем клоне включите репозиторные гейты:

```bash
git config core.hooksPath .githooks
```

## Первая команда

```bash
./venv/Scripts/python.exe -B -m ai_youtube capabilities
```

Печатает то, что доступно **сегодня**: приложения, шаблоны, голоса, стили
субтитров, музыку и каналы — со статусом каждого. Это честный ответ системы о
себе, а не список планов.

## Канонический вход

Единственная точка входа — `python -m ai_youtube`.

| Команда | Что делает |
|---|---|
| `create` | создать ролик (флаги, без вопросов) |
| `resume` | продолжить существующий проект |
| `run-stage` | выполнить одну стадию существующего проекта |
| `wizard` | тот же `create`, но с вопросами в терминале |
| `project` | список проектов, статус, валидация, отчёт по правам |
| `assets` | заменить визуальный слот сцены своим файлом |
| `capabilities` | что реально доступно сегодня |
| `applications` · `formats` · `templates` · `channels` | каталог производства |
| `voices` · `subtitles` | голоса и субтитры, включая объяснение выбора |
| `script` · `visual-plan` | сценарий и план сцен офлайн, без рендера |

У любой команды есть `--json` для машинного чтения и `--help`.

## Как сделать ролик

Карточка с текстом на своём видео — без озвучки и без сети:

```bash
./venv/Scripts/python.exe -B -m ai_youtube create --template story_card_text_only_v1 --text "Осьминоги видят кожей" --source-asset "G:/media/octopus.mp4" --comment "Природа умеет странное"
```

Полноэкранное видео с озвучкой по теме — здесь нужны сеть на поиск материала и
явное разрешение на платную озвучку:

```bash
./venv/Scripts/python.exe -B -m ai_youtube create --template fullscreen_voiceover_v1 --topic "Почему киты поют" --target-duration 50 --allow-network provider_search --allow-network asset_download --approve-paid-generation
```

Продолжить прерванный проект:

```bash
./venv/Scripts/python.exe -B -m ai_youtube resume --project-id <id>
```

Заменить неудачный визуал сцены своим файлом:

```bash
./venv/Scripts/python.exe -B -m ai_youtube assets replace --project-id <id> --scene-id <scene> --slot-id <slot> --file "G:/media/better.mp4" --confirm-user-owned
```

Результат каждого запуска — каталог `projects/<project_id>/` с манифестами,
evidence, правами, промежуточными планами и итоговым MP4. Корень рабочего
пространства переопределяется `--workspace` или `AI_YOUTUBE_WORKSPACE`.

## Что защищено по умолчанию

- **Сеть запрещена по классам.** Разрешение выдаётся отдельно на каждый класс:
  `provider_search`, `asset_download`, `preview_download`, `article_fetch`,
  `voice_preflight`, `semantic_brief` (`src/runtime_network.py`). Наличие ключа
  в `.env` разрешением не является.
- **Платное — отдельно от сети.** Озвучка не запускается без
  `--approve-paid-generation`; платный анализ кадров имеет собственный бюджет и
  выключен в конфиге.
- **Права fail-closed.** Материал без доказанной лицензии не попадает в ролик;
  политика прав одна — `config/license_policy.json`.
- **`strict` — режим по умолчанию.** `draft_complete` включается явно, всегда
  даёт `publish_ready=false` и не ослабляет проверки прав и запретов канала.

## Структура

```text
src/                 движок: сценарий, сцены, поиск материала, права, озвучка, субтитры, рендер
src/ai_youtube/cli/  канонический CLI
apps/                переходные compatibility-входы прежних поколений
config/              versioned-конфигурация (права, превью, семантика, стиль)
channels/            профили каналов
schemas/             объявленные формы артефактов проекта
docs/                документация; начинать с docs/current/
skills/              процедуры для AI-агентов
tests/               офлайн-тесты, запускаются без сети и без ключей
projects/            результаты запусков (не коммитятся)
```

## Проверки перед коммитом

```bash
./venv/Scripts/python.exe scripts/gates.py
```

Гейты запускают ruff, mypy, проверку документации агентов и `git diff --check`.
Тесты текущего изменения запускаются точечно; полный офлайн-набор — на границе
этапа или в CI:

```bash
./venv/Scripts/python.exe -B -m unittest discover -s tests -p "test_*.py"
```

## Документация

- [AGENTS.md](AGENTS.md) — контракт работы с репозиторием (он же для людей);
- [docs/current/START_HERE.md](docs/current/START_HERE.md) — текущее состояние и
  следующий шаг;
- [docs/current/SYSTEM_MAP.md](docs/current/SYSTEM_MAP.md) — кто чем владеет в коде;
- [docs/current/CLEANUP_REGISTRY.md](docs/current/CLEANUP_REGISTRY.md) — что
  устарело, что дублируется и на каких условиях удаляется;
- [docs/adr/README.md](docs/adr/README.md) — принятые архитектурные решения;
- [docs/audits/README.md](docs/audits/README.md) — аудиты и их статусы.

При расхождении между документами и кодом верны код и Git.
