"""Registered county-specific ETL transformations.

Profiles may select only handlers defined in this module; they cannot import
arbitrary code from a custom profiles file.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from utrans.etl_common import (
    direction,
    has_value,
    parse_full_address,
    resolve_domain_value,
)
from utrans.profiles import CountyProfile

RowHandler = Callable[
    [list[object], Mapping[str, int], Mapping[str, Mapping[str, str]]], None
]


@dataclass(frozen=True)
class Handler:
    required_fields: tuple[str, ...]
    target_fields: tuple[str, ...]
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


def _clear(row: list[object], indexes: Mapping[str, int], prefix: str) -> None:
    for suffix in ("PREDIR", "NAME", "POSTTYPE", "POSTDIR"):
        _set(row, indexes, f"{prefix}_{suffix}", "")


def _assign_parsed_name(
    row: list[object],
    indexes: Mapping[str, int],
    value: object,
    prefix: str,
    posttypes: Mapping[str, str],
) -> None:
    parsed = parse_full_address(value, posttypes)
    if parsed is None:
        return
    if prefix != "" and parsed.name.isdigit():
        _set(row, indexes, "AN_NAME", parsed.name)
        _set(row, indexes, "AN_POSTDIR", parsed.postdir)
        return
    for suffix, part in (
        ("PREDIR", parsed.predir),
        ("NAME", parsed.name),
        ("POSTTYPE", parsed.posttype),
        ("POSTDIR", parsed.postdir),
    ):
        _set(row, indexes, f"{prefix}{suffix}", part)


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


def _davis_alias(
    row: list[object],
    indexes: Mapping[str, int],
    domains: Mapping[str, Mapping[str, str]],
) -> None:
    value = _value(row, indexes, "ROADALIASNAME")
    if not has_value(value) or "&" in str(value):
        return
    alias = str(value).strip()
    parts = alias.split()
    if alias[0].isdigit():
        parsed = _numeric_name_and_direction(alias)
        if parsed is not None:
            _set(row, indexes, "AN_NAME", parsed[0])
            _set(row, indexes, "AN_POSTDIR", parsed[1])
        else:
            _set(row, indexes, "A1_NAME", alias)
        return
    posttype = resolve_domain_value(parts[-1], domains.get("A1_POSTTYPE", {}))
    if posttype is None and parts[-1].upper() == "WY":
        posttype = resolve_domain_value("WAY", domains.get("A1_POSTTYPE", {}))
    if posttype is None:
        _set(row, indexes, "A1_NAME", alias)
        return
    _set(row, indexes, "A1_NAME", " ".join(parts[:-1]))
    _set(row, indexes, "A1_POSTTYPE", posttype)


def _washington_postdir_and_aliases(
    row: list[object],
    indexes: Mapping[str, int],
    domains: Mapping[str, Mapping[str, str]],
) -> None:
    del domains
    for source in ("POSTDIR_", "SUFFIXDIR"):
        value = direction(_value(row, indexes, source))
        if value:
            _set(row, indexes, "POSTDIR", value)
    an_name = _value(row, indexes, "AN_NAME")
    if not has_value(an_name):
        return
    for prefix in ("A1", "A2"):
        alias = _value(row, indexes, f"{prefix}_NAME")
        if has_value(alias) and str(an_name) in str(alias):
            _clear(row, indexes, prefix)


def _weber_alias(
    row: list[object],
    indexes: Mapping[str, int],
    domains: Mapping[str, Mapping[str, str]],
) -> None:
    alias = _value(row, indexes, "ALIAS")
    if (
        not has_value(alias)
        or str(alias).strip() == str(_value(row, indexes, "S_NAME")).strip()
    ):
        return
    alias_text = str(alias).strip()
    if alias_text.isdigit():
        parsed = _numeric_name_and_direction(_value(row, indexes, "ACS_ALIAS"))
        _set(row, indexes, "AN_NAME", parsed[0] if parsed is not None else alias_text)
        _set(
            row,
            indexes,
            "AN_POSTDIR",
            parsed[1]
            if parsed is not None
            else direction(_value(row, indexes, "SUFDIR")),
        )
        return
    parts = alias_text.split()
    posttype = resolve_domain_value(parts[-1], domains.get("A1_POSTTYPE", {}))
    if posttype is None:
        _set(row, indexes, "A1_NAME", alias_text)
        return
    _set(row, indexes, "A1_NAME", " ".join(parts[:-1]))
    _set(row, indexes, "A1_POSTTYPE", posttype)


def _summit_names(
    row: list[object],
    indexes: Mapping[str, int],
    domains: Mapping[str, Mapping[str, str]],
) -> None:
    pre_type = _value(row, indexes, "PRE_TYPE")
    if has_value(pre_type) and has_value(_value(row, indexes, "NAME")):
        _set(row, indexes, "NAME", f"{pre_type} {_value(row, indexes, 'NAME')}")
    other_name = _value(row, indexes, "OTHER_NAME")
    street = _value(row, indexes, "STREET")
    if not has_value(other_name) or not has_value(street):
        return
    if str(other_name).split()[0].upper() != str(street).split()[0].upper():
        _assign_parsed_name(
            row, indexes, other_name, "A1_", domains.get("POSTTYPE", {})
        )


def _tooele_numeric_name(
    row: list[object],
    indexes: Mapping[str, int],
    domains: Mapping[str, Mapping[str, str]],
) -> None:
    name = _value(row, indexes, "NAME_")
    if has_value(name) and str(name).strip()[0].isdigit():
        _assign_parsed_name(row, indexes, name, "", domains.get("POSTTYPE", {}))


def _emery_compact_aliases(
    row: list[object],
    indexes: Mapping[str, int],
    domains: Mapping[str, Mapping[str, str]],
) -> None:
    del domains
    for source, target in (("ACS_ALIAS", None), ("ALIAS1", "A1"), ("ALIAS2", "A2")):
        value = _value(row, indexes, source)
        compact = (
            re.fullmatch(r"(\d+)([NSEW])", str(value).strip().upper())
            if has_value(value)
            else None
        )
        if compact is not None:
            _set(row, indexes, "AN_NAME", compact.group(1))
            _set(row, indexes, "AN_POSTDIR", compact.group(2))
        elif target is None and has_value(value) and str(value).strip().isdigit():
            _set(row, indexes, "AN_NAME", str(value).strip())


def _kane_alias_cleanup(
    row: list[object],
    indexes: Mapping[str, int],
    domains: Mapping[str, Mapping[str, str]],
) -> None:
    del domains
    for prefix in ("A1", "A2"):
        value = str(_value(row, indexes, f"{prefix}_NAME")).strip().upper()
        if len(value) >= 2 and value[0] == "K" and value[1].isdigit():
            _clear(row, indexes, prefix)
    if not str(_value(row, indexes, "AN_NAME")).strip().isdigit():
        _set(row, indexes, "AN_NAME", "")


def _grand_numeric_acs_name(
    row: list[object],
    indexes: Mapping[str, int],
    domains: Mapping[str, Mapping[str, str]],
) -> None:
    del domains
    if not str(_value(row, indexes, "AN_NAME")).strip().isdigit():
        _set(row, indexes, "AN_NAME", "")


def _sevier_postdir_fallback(
    row: list[object],
    indexes: Mapping[str, int],
    domains: Mapping[str, Mapping[str, str]],
) -> None:
    del domains
    if not has_value(_value(row, indexes, "POSTDIR")):
        _set(row, indexes, "POSTDIR", direction(_value(row, indexes, "SUR_DIR")))


def _uintah_exclusion_note(
    row: list[object],
    indexes: Mapping[str, int],
    domains: Mapping[str, Mapping[str, str]],
) -> None:
    del domains
    if str(_value(row, indexes, "EXCLUDE")).strip().upper() == "X":
        notes = str(_value(row, indexes, "UTRANS_NOTES") or "")
        _set(row, indexes, "UTRANS_NOTES", f"{notes}Uintah marked as exclude;"[:200])


def _wayne_acs_alias(
    row: list[object],
    indexes: Mapping[str, int],
    domains: Mapping[str, Mapping[str, str]],
) -> None:
    parsed = parse_full_address(
        _value(row, indexes, "ACS_ALIAS"), domains.get("POSTTYPE", {})
    )
    if parsed is not None and parsed.name.isdigit():
        _set(row, indexes, "AN_NAME", parsed.name)
        _set(row, indexes, "AN_POSTDIR", parsed.postdir)


HANDLERS: Mapping[str, Handler] = {
    "utah_road_names": Handler(
        required_fields=(
            "ROADNAME",
            "ALTROADNAME",
            "ALTROADTYPE",
            "ALTROADNAME2",
        ),
        target_fields=(
            "NAME",
            "POSTDIR",
            "POSTTYPE",
            "A1_NAME",
            "A1_POSTTYPE",
            "A2_NAME",
            "AN_NAME",
            "AN_POSTDIR",
        ),
        apply=_utah_road_names,
    ),
    "davis_alias": Handler(
        required_fields=("ROADALIASNAME",),
        target_fields=("A1_NAME", "A1_POSTTYPE", "AN_NAME", "AN_POSTDIR"),
        apply=_davis_alias,
    ),
    "washington_postdir_and_aliases": Handler(
        required_fields=("POSTDIR_", "SUFFIXDIR"),
        target_fields=(
            "POSTDIR",
            "AN_NAME",
            "A1_PREDIR",
            "A1_NAME",
            "A1_POSTTYPE",
            "A1_POSTDIR",
            "A2_PREDIR",
            "A2_NAME",
            "A2_POSTTYPE",
            "A2_POSTDIR",
        ),
        apply=_washington_postdir_and_aliases,
    ),
    "weber_alias": Handler(
        required_fields=("ALIAS", "ACS_ALIAS", "S_NAME", "SUFDIR"),
        target_fields=("A1_NAME", "A1_POSTTYPE", "AN_NAME", "AN_POSTDIR"),
        apply=_weber_alias,
    ),
    "summit_names": Handler(
        required_fields=("PRE_TYPE", "OTHER_NAME", "STREET"),
        target_fields=(
            "NAME",
            "A1_PREDIR",
            "A1_NAME",
            "A1_POSTTYPE",
            "A1_POSTDIR",
            "AN_NAME",
            "AN_POSTDIR",
        ),
        apply=_summit_names,
    ),
    "tooele_numeric_name": Handler(
        required_fields=("NAME_",),
        target_fields=("PREDIR", "NAME", "POSTTYPE", "POSTDIR"),
        apply=_tooele_numeric_name,
    ),
    "emery_compact_aliases": Handler(
        required_fields=("ACS_ALIAS", "ALIAS1", "ALIAS2"),
        target_fields=("AN_NAME", "AN_POSTDIR"),
        apply=_emery_compact_aliases,
    ),
    "kane_alias_cleanup": Handler(
        required_fields=(),
        target_fields=(
            "A1_PREDIR",
            "A1_NAME",
            "A1_POSTTYPE",
            "A1_POSTDIR",
            "A2_PREDIR",
            "A2_NAME",
            "A2_POSTTYPE",
            "A2_POSTDIR",
            "AN_NAME",
        ),
        apply=_kane_alias_cleanup,
    ),
    "grand_numeric_acs_name": Handler(
        required_fields=(),
        target_fields=("AN_NAME",),
        apply=_grand_numeric_acs_name,
    ),
    "sevier_postdir_fallback": Handler(
        required_fields=("SUR_DIR",),
        target_fields=("POSTDIR",),
        apply=_sevier_postdir_fallback,
    ),
    "uintah_exclusion_note": Handler(
        required_fields=("EXCLUDE",),
        target_fields=("UTRANS_NOTES",),
        apply=_uintah_exclusion_note,
    ),
    "wayne_acs_alias": Handler(
        required_fields=("ACS_ALIAS",),
        target_fields=(
            "A1_PREDIR",
            "A1_NAME",
            "A1_POSTTYPE",
            "A1_POSTDIR",
            "AN_NAME",
            "AN_POSTDIR",
        ),
        apply=_wayne_acs_alias,
    ),
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
