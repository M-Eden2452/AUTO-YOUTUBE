from pathlib import Path
import json
import textwrap

from moviepy import ColorClip, TextClip, CompositeVideoClip, concatenate_videoclips

OUTPUT_DIR = Path("outputs")
SCENE_PLAN_PATH = OUTPUT_DIR / "scene_plan.json"

with open(SCENE_PLAN_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

scenes = data["scenes"][:3]

def make_scene_clip(scene, duration=5):
    width, height = 1920, 1080

    bg = ColorClip(
        size=(width, height),
        color=(15, 15, 18),
        duration=duration
    )

    title = f"SCENE {scene['scene_number']} | {scene.get('emotion', '')}"

    narration = scene.get("narration_text", "")
    screen_text = scene.get("screen_text", "")

    wrapped_narration = "\n".join(textwrap.wrap(narration, width=55))
    wrapped_screen = "\n".join(textwrap.wrap(screen_text, width=35))

    title_clip = TextClip(
        text=title,
        font_size=45,
        color="white",
        duration=duration
    ).with_position(("center", 100))

    screen_clip = TextClip(
        text=wrapped_screen,
        font_size=70,
        color="white",
        duration=duration
    ).with_position("center")

    narration_clip = TextClip(
        text=wrapped_narration,
        font_size=36,
        color="gray",
        duration=duration
    ).with_position(("center", 780))

    return CompositeVideoClip([bg, title_clip, screen_clip, narration_clip])


clips = []

for scene in scenes:
    clips.append(make_scene_clip(scene, duration=2))

final = concatenate_videoclips(clips, method="compose")

output_path = OUTPUT_DIR / "rough_cut_from_json.mp4"

final.write_videofile(
    str(output_path),
    fps=15,
    codec="libx264",
    audio_codec="aac"
)

print(f"Готово: {output_path}")