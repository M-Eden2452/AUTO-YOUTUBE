from __future__ import annotations

from pathlib import Path

from moviepy import AudioFileClip, CompositeAudioClip, VideoFileClip


def add_background_music(video_path: str | Path, music_path: str | Path, output_path: str | Path, volume: float) -> bool:
    music_file = Path(music_path)
    if not music_file.exists():
        return False

    video = VideoFileClip(str(video_path))
    music = AudioFileClip(str(music_file))
    music = music.subclipped(0, min(video.duration, music.duration)).with_volume_scaled(volume)
    final = video.with_audio(CompositeAudioClip([music]))
    final.write_videofile(str(output_path), fps=video.fps, codec="libx264", audio_codec="aac")
    video.close()
    music.close()
    final.close()
    return True
