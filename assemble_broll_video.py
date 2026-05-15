from pathlib import Path
from moviepy import VideoFileClip, concatenate_videoclips

BROLL_DIR = Path("assets/broll")
OUTPUT_DIR = Path("outputs")

clips = []

video_files = sorted(BROLL_DIR.glob("*.mp4"))

print(f"Найдено видео: {len(video_files)}")

for file in video_files:
    print(f"Добавляю: {file.name}")

    clip = VideoFileClip(str(file))

    # берем первые 5 секунд
    clip = clip.subclipped(0, min(5, clip.duration))

    # resize
    clip = clip.resized((1920, 1080))

    clips.append(clip)

final = concatenate_videoclips(clips, method="compose")

output_path = OUTPUT_DIR / "broll_rough_cut.mp4"

final.write_videofile(
    str(output_path),
    fps=30,
    codec="libx264",
    audio_codec="aac"
)

print(f"\nГотово: {output_path}")