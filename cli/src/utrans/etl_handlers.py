"""Registered county-specific ETL transformations.

Profiles may select only handlers defined in this module; they cannot import
arbitrary code from a custom profiles file.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from utrans.etl_common import direction, has_value, resolve_domain_value
from utrans.profiles import CountyProfile

RowHandler = Callable[
    [list[object], Mapping[str, int], Mapping[str, Mapping[str, str]]], None
]


@dataclass(frozen=True)
class Handler:
    required_fields: tuple[str, ...]
    apply: RowHandler


def _value(row: list[object], indexes: Mapping[str, int], field: str) -> object:
    index = indexes.get(field.upper())
    return row[index] if index is not None else ""


def _set(
    row: list[object], indexes: Mapping[str, int], field: str, value: object
) -> None:
    index = indexes.get(field.upper())
    if index is not None:
        row[index] = value


def _numeric_name_and_direction(value: object) -> tuple[str, str] | None:
    if not has_value(value):
        return None
    parts = str(value).strip().upper().split()
    if len(parts) < 2 or not parts[0].isdigit():
        return None
    postdir = direction(parts[-1])
    return (parts[0], postdir) if postdir else None


def _utah_road_names(
    row: list[object],
    indexes: Mapping[str, int],
    domains: Mapping[str, Mapping[str, str]],
) -> None:
    """Preserve Utah County's legacy numeric primary and alternate road parsing."""
    primary = _numeric_name_and_direction(_value(row, indexes, "ROADNAME"))
    if primary is not None:
        _set(row, indexes, "NAME", primary[0])
        _set(row, indexes, "POSTDIR", primary[1])
        _set(row, indexes, "POSTTYPE", "")

    numeric_alias: tuple[str, str] | None = None
    for source, target in (("ALTROADNAME2", "A2_NAME"), ("ALTROADNAME", "A1_NAME")):
        parsed = _numeric_name_and_direction(_value(row, indexes, source))
        if parsed is None:
            continue
        numeric_alias = parsed
        _set(row, indexes, target, "")
        _set(row, indexes, "A1_POSTTYPE", "")
    if numeric_alias is not None:
        _set(row, indexes, "AN_NAME", numeric_alias[0])
        _set(row, indexes, "AN_POSTDIR", numeric_alias[1])

    alias_name = _value(row, indexes, "A1_NAME")
    if not has_value(alias_name):
        _set(row, indexes, "A1_POSTTYPE", "")
        return
    alias_type = _value(row, indexes, "ALTROADTYPE")
    first_word = (
        str(alias_type).strip().split(maxsplit=1)[0] if has_value(alias_type) else ""
    )
    resolved = resolve_domain_value(first_word, domains.get("A1_POSTTYPE", {}))
    if resolved is not None:
        _set(row, indexes, "A1_POSTTYPE", resolved)


HANDLERS: Mapping[str, Handler] = {
    "utah_road_names": Handler(
        required_fields=(
            "ROADNAME",
            "ALTROADNAME",
            "ALTROADTYPE",
            "ALTROADNAME2",
        ),
        apply=_utah_road_names,
    )
}


def profile_handler(profile: CountyProfile) -> Handler | None:
    """Resolve an optional handler name from the closed registry."""
    value = profile.get("custom_handler")
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise TypeError(
            f"Profile '{profile.key}' setting 'custom_handler' must be a string."
        )
    try:
        return HANDLERS[value]
    except KeyError as exc:
        names = ", ".join(sorted(HANDLERS))
        raise ValueError(
            f"Profile '{profile.key}' has unsupported custom_handler '{value}'. "
            f"Supported handlers: {names}."
        ) from exc
