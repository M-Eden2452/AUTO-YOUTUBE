from __future__ import annotations

from pathlib import Path

from .models import ChannelProfile, ProjectFoundationError, utc_now_iso
from .storage import atomic_write_json, ensure_dir, read_json_if_exists

CHANNEL_FILENAME = "channel.json"


class ChannelRegistry:
    """Filesystem-backed registry of ChannelProfile records.

    Storage layout: <base_dir>/<channel_id>/channel.json
    """

    def __init__(self, base_dir: str | Path = "channels") -> None:
        self.base_dir = Path(base_dir)

    def _channel_dir(self, channel_id: str) -> Path:
        return self.base_dir / channel_id

    def _channel_file(self, channel_id: str) -> Path:
        return self._channel_dir(channel_id) / CHANNEL_FILENAME

    def exists(self, channel_id: str) -> bool:
        return self._channel_file(channel_id).is_file()

    def create(self, profile: ChannelProfile) -> ChannelProfile:
        if self.exists(profile.channel_id):
            raise ProjectFoundationError(f"Channel {profile.channel_id!r} already exists.")
        ensure_dir(self._channel_dir(profile.channel_id))
        atomic_write_json(self._channel_file(profile.channel_id), profile.to_dict())
        return profile

    def get(self, channel_id: str) -> ChannelProfile:
        data = read_json_if_exists(self._channel_file(channel_id))
        if data is None:
            raise ProjectFoundationError(f"Channel {channel_id!r} was not found.")
        return ChannelProfile.from_dict(data)

    def list(self) -> list[ChannelProfile]:
        if not self.base_dir.is_dir():
            return []
        profiles: list[ChannelProfile] = []
        for entry in sorted(self.base_dir.iterdir(), key=lambda item: item.name):
            channel_file = entry / CHANNEL_FILENAME
            if entry.is_dir() and channel_file.is_file():
                profiles.append(ChannelProfile.from_dict(read_json_if_exists(channel_file)))
        return profiles

    def update(self, channel_id: str, profile: ChannelProfile) -> ChannelProfile:
        if not self.exists(channel_id):
            raise ProjectFoundationError(f"Channel {channel_id!r} does not exist and cannot be updated.")
        if profile.channel_id != channel_id:
            raise ProjectFoundationError(
                f"Cannot update channel {channel_id!r} with a profile for {profile.channel_id!r}."
            )
        profile.updated_at = utc_now_iso()
        atomic_write_json(self._channel_file(channel_id), profile.to_dict())
        return profile
