# news_to_short App

Entrypoint wrapper for the `news_to_short` mode.

Implementation lives in `src/news/`. This wrapper exists so future UI, API, or worker runners can call the app without depending on the legacy root CLI layout.

Example:

```powershell
.\venv\Scripts\python.exe -m apps.news_to_short --topic "Почему киты поют?" --until-stage export
```

