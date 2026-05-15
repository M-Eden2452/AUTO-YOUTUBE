from openai import OpenAI
from dotenv import load_dotenv
from pathlib import Path
import os

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

OUTPUT_DIR = Path("outputs")
SCRIPT_PATH = OUTPUT_DIR / "script.txt"

script = SCRIPT_PATH.read_text(encoding="utf-8")

prompt = f"""
Разбей сценарий YouTube-видео на монтажные сцены.

Для каждой сцены дай:
- номер сцены
- примерное время
- текст/смысл сцены
- эмоцию
- B-roll keywords на английском
- текст на экране
- заметку для монтажа

Формат сделай удобным для монтажера.

Сценарий:
{script}
"""

response = client.responses.create(
    model="gpt-5.4-mini",
    input=prompt
)

result = response.output_text

path = OUTPUT_DIR / "scene_plan.txt"
path.write_text(result, encoding="utf-8")

print(result)
print(f"\nСохранено: {path}")