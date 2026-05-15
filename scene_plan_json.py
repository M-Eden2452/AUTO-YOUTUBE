from openai import OpenAI
from dotenv import load_dotenv
from pathlib import Path
import os
import json

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

OUTPUT_DIR = Path("outputs")
SCRIPT_PATH = OUTPUT_DIR / "script.txt"

script = SCRIPT_PATH.read_text(encoding="utf-8")

prompt = f"""
Разбей сценарий на монтажные сцены.

Верни ТОЛЬКО валидный JSON без пояснений.

Формат:
{{
  "video_title": "...",
  "style": "dark cinematic psychology",
  "scenes": [
    {{
      "scene_number": 1,
      "estimated_start": "00:00",
      "estimated_end": "00:15",
      "narration_text": "...",
      "emotion": "...",
      "broll_keywords": ["...", "...", "..."],
      "screen_text": "...",
      "editing_note": "..."
    }}
  ]
}}

Сценарий:
{script}
"""

response = client.responses.create(
    model="gpt-5.4-mini",
    input=prompt
)

raw = response.output_text.strip()

data = json.loads(raw)

path = OUTPUT_DIR / "scene_plan.json"

with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"JSON scene plan сохранен: {path}")
print(json.dumps(data, ensure_ascii=False, indent=2))