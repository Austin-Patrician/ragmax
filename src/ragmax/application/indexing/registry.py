from ragmax.application.indexing.dtos import ProfileOverrides
from ragmax.core.exceptions import InvalidRequestError
from ragmax.domain.indexing.profiles import IndexingProfile


class IndexingProfileRegistry:
    def __init__(self, profiles: tuple[IndexingProfile, ...]) -> None:
        self._profiles = {profile.name.value: profile for profile in profiles}

    def list(self) -> tuple[IndexingProfile, ...]:
        return tuple(self._profiles.values())

    def get(self, profile_name: str) -> IndexingProfile:
        profile = self._profiles.get(profile_name)
        if profile is None:
            raise InvalidRequestError(f"Unknown indexing profile: {profile_name}")
        return profile

    def resolve(self, profile_name: str, overrides: ProfileOverrides) -> IndexingProfile:
        profile = self.get(profile_name)
        return profile.with_overrides(
            chunk_size=overrides.chunk_size,
            chunk_overlap=overrides.chunk_overlap,
            option_overrides=overrides.options,
        )

