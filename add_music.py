from pathlib import Path
from moviepy import VideoFileClip, AudioFileClip, CompositeAudioClip

INPUT_VIDEO = Path("outputs/broll_with_text.mp4")
MUSIC_PATH = Path("music/background.mp3")
OUTPUT_VIDEO = Path("outputs/broll_with_text_music.mp4")

video = VideoFileClip(str(INPUT_VIDEO))
music = AudioFileClip(str(MUSIC_PATH))

music = music.subclipped(0, min(video.duration, music.duration))
music = music.with_volume_scaled(0.18)

final_audio = CompositeAudioClip([music])
final_video = video.with_audio(final_audio)

final_video.write_videofile(
    str(OUTPUT_VIDEO),
    fps=24,
    codec="libx264",
    audio_codec="aac",
)

print(f"Готово: {OUTPUT_VIDEO}")