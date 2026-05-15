from pathlib import Path
import json
import textwrap

FONT_PATH = "C:/Windows/Fonts/arial.ttf"

from moviepy import (
    VideoFileClip,
    TextClip,
    CompositeVideoClip,
    concatenate_videoclips,
)

OUTPUT_DIR = Path("outputs")
BROLL_DIR = Path("assets/broll")
SCENE_PLAN_PATH = OUTPUT_DIR / "scene_plan.json"

with open(SCENE_PLAN_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

scenes = data["scenes"]

def make_scene(scene):
    scene_number = scene["scene_number"]
    video_path = BROLL_DIR / f"scene_{scene_number:02d}.mp4"

    if not video_path.exists():
        print(f"Нет видео для сцены {scene_number}: {video_path}")
        return None

    clip = VideoFileClip(str(video_path))
    clip = clip.subclipped(0, min(5, clip.duration))
    clip = clip.resized((1920, 1080))

    screen_text = scene.get("screen_text", "")
    wrapped_text = "\n".join(textwrap.wrap(screen_text, width=28))

    text_clip = (
        TextClip(
            text=wrapped_text,
            font=FONT_PATH,
            font_size=72,
            color="white",
            stroke_color="black",
            stroke_width=3,
            duration=clip.duration,
        )
        .with_position("center")
    )

    return CompositeVideoClip([clip, text_clip])


clips = []

for scene in scenes:
    result = make_scene(scene)
    if result:
        clips.append(result)

final = concatenate_videoclips(clips, method="compose")

output_path = OUTPUT_DIR / "broll_with_text.mp4"

final.write_videofile(
    str(output_path),
    fps=24,
    codec="libx264",
    audio_codec="aac",
)

print(f"Готово: {output_path}")