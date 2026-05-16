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
У меня есть сценарий YouTube-видео на русском.

Сделай полный production package:

1. 10 вариантов названия
2. Описание для YouTube
3. Главы видео с таймкодами примерно
4. Visual plan: какие кадры/B-roll нужны по сценам
5. Short hook для Shorts/Reels
6. 15 тегов

Сценарий:
{script}
"""

response = client.responses.create(
    model="gpt-5.4-mini",
    input=prompt
)

result = response.output_text

package_path = OUTPUT_DIR / "youtube_package.txt"

package_path.write_text(result, encoding="utf-8")

print(result)
print(f"\nСохранено: {package_path}")