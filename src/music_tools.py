from __future__ import annotations

import math
from pathlib import Path

from typing import Any

from moviepy import AudioFileClip, CompositeAudioClip, VideoFileClip, concatenate_audioclips


def add_background_music(
    video_path: str | Path,
    music_path: str | Path,
    output_path: str | Path,
    volume: float,
    voice_manifest: dict[str, Any] | None = None,
    duck_music: bool = True,
) -> bool:
    music_file = Path(music_path)
    if not music_file.exists():
        return False

    video = VideoFileClip(str(video_path))
    source_music = AudioFileClip(str(music_file))
    looped_music = None
    final_music = None
    final_audio = None
    final = None
    voice_clips = []
    try:
        active_music = source_music
        if source_music.duration < video.duration:
            loops = max(1, math.ceil(video.duration / source_music.duration))
            looped_music = concatenate_audioclips([source_music] * loops)
            active_music = looped_music
        has_voice = bool((voice_manifest or {}).get("enabled") and (voice_manifest or {}).get("scenes"))
        music_volume = volume * (0.42 if has_voice and duck_music else 1.0)
        final_music = active_music.subclipped(0, video.duration).with_volume_scaled(music_volume)
        audio_layers = [final_music]
        for item in (voice_manifest or {}).get("scenes", []):
            path = Path(item.get("path", ""))
            if not path.exists():
                continue
            voice_clip = AudioFileClip(str(path)).with_start(float(item.get("start", 0))).with_volume_scaled(float(item.get("volume", 1.0)))
            voice_clips.append(voice_clip)
            audio_layers.append(voice_clip)
        final_audio = CompositeAudioClip(audio_layers)
        final = video.with_audio(final_audio)
        final.write_videofile(str(output_path), fps=video.fps, codec="libx264", audio_codec="aac", preset="medium")
    finally:
        for clip in (final, final_audio, final_music, looped_music, source_music, *voice_clips, video):
            if clip is not None:
                clip.close()
    return True
