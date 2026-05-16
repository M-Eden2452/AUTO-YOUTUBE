from dotenv import load_dotenv
from pathlib import Path
import requests
import json
import os

load_dotenv()

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")

OUTPUT_DIR = Path("outputs")
ASSETS_DIR = Path("assets/broll")
ASSETS_DIR.mkdir(parents=True, exist_ok=True)

SCENE_PLAN_PATH = OUTPUT_DIR / "scene_plan.json"

with open(SCENE_PLAN_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

headers = {
    "Authorization": PEXELS_API_KEY
}

def search_pexels_video(query: str):
    url = "https://api.pexels.com/videos/search"

    params = {
        "query": query,
        "per_page": 1,
        "orientation": "landscape"
    }

    response = requests.get(url, headers=headers, params=params, timeout=30)
    response.raise_for_status()

    result = response.json()

    if not result.get("videos"):
        return None

    video = result["videos"][0]
    files = video["video_files"]

    best_file = sorted(
        files,
        key=lambda x: x.get("width", 0),
        reverse=True
    )[0]

    return best_file["link"]

def download_file(url: str, path: Path):
    response = requests.get(url, timeout=120)
    response.raise_for_status()

    with open(path, "wb") as f:
        f.write(response.content)

for scene in data["scenes"]:
    scene_number = scene["scene_number"]
    keywords = scene.get("broll_keywords", [])

    if not keywords:
        print(f"Scene {scene_number}: нет keywords")
        continue

    query = keywords[0]

    print(f"Scene {scene_number}: ищу видео по запросу: {query}")

    video_url = search_pexels_video(query)

    if not video_url:
        print(f"Scene {scene_number}: видео не найдено")
        continue

    output_path = ASSETS_DIR / f"scene_{scene_number:02d}.mp4"

    print(f"Scene {scene_number}: скачиваю {output_path}")
    download_file(video_url, output_path)

print("B-roll скачан.")