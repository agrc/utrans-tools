"""Profile-driven county transformations for the ArcGIS Pro ETL workflow."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import arcpy

from utrans.etl_common import (
    domain_values,
    field_name_map,
    has_value,
    parse_full_address,
    resolve_domain_value,
)
from utrans.profiles import CountyProfile


def _mapping(profile: CountyProfile, name: str) -> dict[str, str]:
    value = profile.get(name, "")
    if isinstance(value, str):
        pairs = (item.strip() for item in value.split(";") if item.strip())
        try:
            return {
                target.strip(): source.strip()
                for target, source in (pair.split("=", maxsplit=1) for pair in pairs)
            }
        except ValueError as exc:
            raise TypeError(
                f"Profile '{profile.key}' setting '{name}' must use TARGET=SOURCE pairs."
            ) from exc
    if not isinstance(value, Mapping) or not all(
        isinstance(target, str) and isinstance(source, str)
        for target, source in value.items()
    ):
        raise TypeError(
            f"Profile '{profile.key}' setting '{name}' must be an object of strings."
        )
    return dict(value)


def _parse_sources(profile: CountyProfile) -> tuple[tuple[str, str], ...]:
    value = profile.get("parse_sources", "")
    if isinstance(value, str):
        pairs = (item.strip() for item in value.split(";") if item.strip())
        try:
            return tuple(
                (source.strip(), target.strip())
                for source, target in (pair.split("=", maxsplit=1) for pair in pairs)
            )
        except ValueError as exc:
            raise TypeError(
                f"Profile '{profile.key}' setting 'parse_sources' must use SOURCE=TARGET pairs."
            ) from exc
    if not isinstance(value, Sequence) or isinstance(value, str):
        raise TypeError(
            f"Profile '{profile.key}' setting 'parse_sources' must be a list."
        )
    result: list[tuple[str, str]] = []
    for item in value:
        if not isinstance(item, Mapping):
            raise TypeError(f"Profile '{profile.key}' parse sources must be objects.")
        source, target = item.get("source"), item.get("target")
        if not isinstance(source, str) or not isinstance(target, str):
            raise TypeError(
                f"Profile '{profile.key}' parse sources require string source and target."
            )
        result.append((source, target))
    return tuple(result)


def _excluded_values(profile: CountyProfile) -> dict[str, set[str]]:
    value = profile.get("exclude_if_any", "")
    if isinstance(value, str):
        pairs = (item.strip() for item in value.split(";") if item.strip())
        try:
            return {
                field.strip().upper(): {
                    item.strip().upper() for item in values.split(",")
                }
                for field, values in (pair.split("=", maxsplit=1) for pair in pairs)
            }
        except ValueError as exc:
            raise TypeError(
                f"Profile '{profile.key}' setting 'exclude_if_any' must use FIELD=VALUE pairs."
            ) from exc
    if not isinstance(value, Mapping):
        raise TypeError(
            f"Profile '{profile.key}' setting 'exclude_if_any' must be an object."
        )
    return {
        str(field).upper(): {str(item).strip().upper() for item in values}
        for field, values in value.items()
        if isinstance(values, Sequence) and not isinstance(values, str)
    }


def apply_mapper(feature_class: str, profile: CountyProfile, utrans_roads: str) -> None:
    """Apply a county's root-level profile mapping configuration."""
    mappings = _mapping(profile, "field_mappings")
    if not mappings:
        raise RuntimeError(f"Profile '{profile.key}' requires field_mappings for ETL.")
    parse_sources = _parse_sources(profile)
    names = field_name_map(feature_class)
    mappings = {
        **{
            target: f"{target}_"
            for target in names.values()
            if f"{target}_".upper() in names
        },
        **mappings,
    }
    target_fields = list(mappings) + [
        "COUNTY_L",
        "COUNTY_R",
        "STATE_L",
        "STATE_R",
        "UTRANS_NOTES",
        "AN_NAME",
        "AN_POSTDIR",
    ]
    for _, alias in parse_sources:
        prefix = "" if alias == "PRIMARY" else f"{alias}_"
        target_fields.extend(
            f"{prefix}{suffix}" for suffix in ("PREDIR", "NAME", "POSTTYPE", "POSTDIR")
        )
    source_fields = [
        *mappings.values(),
        *(source for source, _ in parse_sources),
    ]
    fields = list(
        dict.fromkeys(
            names[field.upper()]
            for field in target_fields + source_fields
            if field.upper() in names
        )
    )
    indexes = {field.upper(): index for index, field in enumerate(fields)}
    domains = domain_values(utrans_roads)
    posttypes = domains.get("POSTTYPE", {})
    vertical_translation = profile.get("translate_vertical_levels", False)
    if not isinstance(vertical_translation, bool):
        raise TypeError(
            f"Profile '{profile.key}' setting 'translate_vertical_levels' must be true or false."
        )

    with arcpy.da.UpdateCursor(feature_class, fields) as cursor:
        for row in cursor:
            for target, source in mappings.items():
                target_index = indexes.get(target.upper())
                source_index = indexes.get(source.upper())
                if target_index is None or source_index is None:
                    continue
                values = domains.get(target.upper())
                if values is None:
                    row[target_index] = row[source_index]
                    continue
                source_value = row[source_index]
                if vertical_translation and target.upper() == "VERT_LEVEL":
                    source_value = {"1": "0", "2": "1", "3": "2"}.get(
                        str(source_value).strip(), source_value
                    )
                resolved = resolve_domain_value(source_value, values)
                if resolved is not None:
                    row[target_index] = resolved
                elif has_value(row[source_index]):
                    row[target_index] = source_value
                    notes_index = indexes.get("UTRANS_NOTES")
                    if notes_index is not None:
                        row[notes_index] = (
                            f"{row[notes_index] or ''}{target}: {row[source_index]}; "
                        )
            for source, alias in parse_sources:
                source_index = indexes.get(source.upper())
                if source_index is None:
                    continue
                parsed = parse_full_address(row[source_index], posttypes)
                if parsed is None:
                    continue
                if alias != "PRIMARY" and parsed.name.isdigit():
                    numeric_index = indexes.get("AN_NAME")
                    numeric_postdir_index = indexes.get("AN_POSTDIR")
                    if numeric_index is not None and not has_value(row[numeric_index]):
                        row[numeric_index] = parsed.name
                        if numeric_postdir_index is not None:
                            row[numeric_postdir_index] = parsed.postdir
                        continue
                    alias_name_index = indexes.get(f"{alias}_NAME")
                    if alias_name_index is not None:
                        row[alias_name_index] = row[source_index]
                    continue
                prefix = "" if alias == "PRIMARY" else f"{alias}_"
                for suffix, value in (
                    ("PREDIR", parsed.predir),
                    ("NAME", parsed.name),
                    ("POSTTYPE", parsed.posttype),
                    ("POSTDIR", parsed.postdir),
                ):
                    index = indexes.get(f"{prefix}{suffix}".upper())
                    if index is not None:
                        row[index] = value
            for field, value in (
                ("COUNTY_L", profile.require("fips")),
                ("COUNTY_R", profile.require("fips")),
                ("STATE_L", "UT"),
                ("STATE_R", "UT"),
            ):
                index = indexes.get(field)
                if index is not None:
                    row[index] = value
            cursor.updateRow(row)
    _delete_excluded_rows(feature_class, _excluded_values(profile))


def _delete_excluded_rows(
    feature_class: str, excluded_values: dict[str, set[str]]
) -> None:
    if not excluded_values:
        return
    names = field_name_map(feature_class)
    fields = [
        names[field.upper()] for field in excluded_values if field.upper() in names
    ]
    if not fields:
        return
    with arcpy.da.UpdateCursor(feature_class, fields) as cursor:
        for row in cursor:
            if any(
                str(value or "").strip().upper() in excluded_values[field.upper()]
                for field, value in zip(fields, row, strict=True)
            ):
                cursor.deleteRow()
