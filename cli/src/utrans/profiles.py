"""Shared loading and validation for county configuration profiles."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_PROFILES_PATH = Path(__file__).with_name("profiles.json")


@dataclass(frozen=True)
class CountyProfile:
    """A county's reusable root-level configuration values."""

    key: str
    values: dict[str, Any]

    def get(self, name: str, default: Any = None) -> Any:
        return self.values.get(name, default)

    def require(self, name: str) -> Any:
        value = self.values.get(name)
        if value in (None, ""):
            raise RuntimeError(
                f"County profile '{self.key}' is missing required setting '{name}'."
            )
        return value


def load_profiles(path: Path | None = None) -> dict[str, CountyProfile]:
    """Load flat county profiles from JSON."""
    profiles_path = path or DEFAULT_PROFILES_PATH
    with profiles_path.open(encoding="utf-8") as profile_file:
        raw_profiles = json.load(profile_file)

    if not isinstance(raw_profiles, dict):
        raise TypeError("Profiles JSON must contain an object keyed by county.")

    profiles: dict[str, CountyProfile] = {}
    for key, values in raw_profiles.items():
        if not isinstance(key, str) or not isinstance(values, dict):
            raise TypeError("Each county profile must be a JSON object.")
        profiles[key] = CountyProfile(key=key, values=values)
    return profiles


def resolve_county_profile(
    county: str, profiles: dict[str, CountyProfile]
) -> CountyProfile:
    """Resolve an exact county key and provide an actionable unknown-county error."""
    county_key = county.strip()
    try:
        return profiles[county_key]
    except KeyError as exc:
        supported = ", ".join(sorted(profiles))
        raise RuntimeError(
            f"Unknown county '{county}'. Supported counties (exact, case-sensitive): "
            f"{supported}."
        ) from exc


def format_county_help(profiles: dict[str, CountyProfile]) -> str:
    return ", ".join(sorted(profiles))
