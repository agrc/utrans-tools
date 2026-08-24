"""Supported declarative post-mapping rules for county ETL profiles."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from utrans.etl_common import has_value
from utrans.profiles import CountyProfile

SUPPORTED_RULES = frozenset({"remove_postdir_if_alpha", "remove_posttype_if_numeric"})


def profile_rules(profile: CountyProfile) -> tuple[str, ...]:
    """Validate and return the ordered post-mapping rules for a profile."""
    value = profile.get("rules", [])
    if (
        not isinstance(value, Sequence)
        or isinstance(value, str)
        or not all(isinstance(rule, str) for rule in value)
    ):
        raise TypeError(
            f"Profile '{profile.key}' setting 'rules' must be a list of strings."
        )
    unknown = set(value) - SUPPORTED_RULES
    if unknown:
        names = ", ".join(sorted(unknown))
        raise ValueError(
            f"Profile '{profile.key}' has unsupported ETL rule(s): {names}."
        )
    if len(set(value)) != len(value):
        raise ValueError(
            f"Profile '{profile.key}' setting 'rules' cannot contain duplicates."
        )
    return tuple(value)


def apply_rules(
    row: list[object], indexes: Mapping[str, int], rules: Sequence[str]
) -> None:
    """Apply supported post-mapping rules to a cursor row in profile order."""
    name_index = indexes.get("NAME")
    if name_index is None or not has_value(row[name_index]):
        return
    name = str(row[name_index]).strip()
    for rule in rules:
        if rule == "remove_postdir_if_alpha" and name[0].isalpha():
            postdir_index = indexes.get("POSTDIR")
            if postdir_index is not None:
                row[postdir_index] = ""
        elif rule == "remove_posttype_if_numeric" and name[0].isdigit():
            posttype_index = indexes.get("POSTTYPE")
            if posttype_index is not None:
                row[posttype_index] = ""
