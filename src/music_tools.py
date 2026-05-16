from __future__ import annotations

import math
from pathlib import Path

from moviepy import AudioFileClip, CompositeAudioClip, VideoFileClip, concatenate_audioclips


def add_background_music(video_path: str | Path, music_path: str | Path, output_path: str | Path, volume: float) -> bool:
    music_file = Path(music_path)
    if not music_file.exists():
        return False

    video = VideoFileClip(str(video_path))
    source_music = AudioFileClip(str(music_file))
    looped_music = None
    final_music = None
    final_audio = None
    final = None
    try:
        active_music = source_music
        if source_music.duration < video.duration:
            loops = max(1, math.ceil(video.duration / source_music.duration))
            looped_music = concatenate_audioclips([source_music] * loops)
            active_music = looped_music
        final_music = active_music.subclipped(0, video.duration).with_volume_scaled(volume)
        final_audio = CompositeAudioClip([final_music])
        final = video.with_audio(final_audio)
        final.write_videofile(str(output_path), fps=video.fps, codec="libx264", audio_codec="aac", preset="medium")
    finally:
        for clip in (final, final_audio, final_music, looped_music, source_music, video):
            if clip is not None:
                clip.close()
    return True
