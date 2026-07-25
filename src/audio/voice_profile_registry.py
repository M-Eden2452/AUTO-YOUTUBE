from __future__ import annotations

from pathlib import Path

from .tts.models import VoiceProfile
from .voice_cli import load_voice_profiles


# Small in-code seed table (lowercased query -> profile_id). Kept in-code rather than in
# voices.yaml because there is currently exactly one channel/one profile; if a second
# channel introduces its own aliases this should move to a `voice_aliases:` block in
# voices.yaml instead of growing indefinitely here.
ALIASES: dict[str, str] = {
    "дом": "ru_dom",
    "dom": "ru_dom",
}


class VoiceProfileRegistryError(ValueError):
    """Raised when a voice profile cannot be resolved or registered."""


class VoiceProfileRegistry:
    def __init__(self, profiles: dict[str, VoiceProfile]) -> None:
        self._profiles = dict(profiles)

    @classmethod
    def from_yaml(cls, path: str | Path) -> "VoiceProfileRegistry":
        return cls(load_voice_profiles(path))

    def profiles(self) -> dict[str, VoiceProfile]:
        return dict(self._profiles)

    def get(self, profile_id: str) -> VoiceProfile:
        if profile_id not in self._profiles:
            raise VoiceProfileRegistryError(f"Voice profile is not registered: {profile_id}")
        return self._profiles[profile_id]

    def find_by_display_name(self, name: str, language: str | None = None) -> VoiceProfile | None:
        normalized = name.strip().casefold()
        for profile in self._profiles.values():
            if profile.display_name.strip().casefold() != normalized:
                continue
            if language and profile.language != language:
                continue
            return profile
        return None

    def find_by_alias(self, alias: str) -> VoiceProfile | None:
        target = ALIASES.get(alias.strip().casefold())
        if target and target in self._profiles:
            return self._profiles[target]
        return None

    def resolve(self, query: str) -> VoiceProfile:
        """Resolve a profile_id, alias ("Дом"/"Dom"), or display name to a VoiceProfile.

        Tries, in order: exact profile_id, alias table, case-insensitive display_name.
        """
        if not query:
            raise VoiceProfileRegistryError("Voice profile query must not be empty.")
        if query in self._profiles:
            return self._profiles[query]
        by_alias = self.find_by_alias(query)
        if by_alias is not None:
            return by_alias
        by_name = self.find_by_display_name(query)
        if by_name is not None:
            return by_name
        raise VoiceProfileRegistryError(f"Could not resolve voice profile for: {query!r}")

    def enabled_profiles(self) -> dict[str, VoiceProfile]:
        return {profile_id: profile for profile_id, profile in self._profiles.items() if profile.enabled}


def validate_no_conflicting_voice_ids(profiles: dict[str, VoiceProfile]) -> list[str]:
    warnings: list[str] = []
    seen: dict[str, str] = {}
    for profile_id, profile in profiles.items():
        if not profile.voice_id:
            continue
        existing = seen.get(profile.voice_id)
        if existing and existing != profile_id:
            warnings.append(
                f"Profiles {existing!r} and {profile_id!r} share the same voice_id ({profile.voice_id!r})."
            )
        else:
            seen[profile.voice_id] = profile_id
    return warnings
