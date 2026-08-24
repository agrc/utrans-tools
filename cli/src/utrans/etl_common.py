"""Shared ArcGIS Pro/Python 3 helpers for county-to-UTRANS ETL."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import arcpy

CORE_TEXT_FIELDS = (
    "STATUS",
    "CARTOCODE",
    "FULLNAME",
    "PREDIR",
    "NAME",
    "POSTTYPE",
    "POSTDIR",
    "AN_NAME",
    "AN_POSTDIR",
    "A1_PREDIR",
    "A1_NAME",
    "A1_POSTTYPE",
    "A1_POSTDIR",
    "A2_PREDIR",
    "A2_NAME",
    "A2_POSTTYPE",
    "A2_POSTDIR",
    "COUNTY_L",
    "COUNTY_R",
    "STATE_L",
    "STATE_R",
    "UTRANS_NOTES",
)
CORE_NUMERIC_FIELDS = ("FROMADDR_L", "TOADDR_L", "FROMADDR_R", "TOADDR_R")
NAME_FIELDS = ("NAME", "A1_NAME", "A2_NAME")
DIRECTIONS = {"N", "S", "E", "W", "NORTH", "SOUTH", "EAST", "WEST"}


@dataclass(frozen=True)
class ParsedAddress:
    predir: str = ""
    name: str = ""
    posttype: str = ""
    postdir: str = ""


def has_value(value: object) -> bool:
    return value is not None and bool(str(value).strip())


def direction(value: object) -> str:
    normalized = str(value).strip().upper() if has_value(value) else ""
    return normalized[:1] if normalized in DIRECTIONS else ""


def parse_full_address(
    value: object, posttypes: set[str] | dict[str, str]
) -> ParsedAddress | None:
    """Parse the legacy primary/alias address formats into UTRANS components."""
    if not has_value(value):
        return None
    parts = str(value).strip().upper().split()
    if len(parts) < 2:
        return None
    predir = direction(parts[0])
    if predir:
        parts = parts[1:]
    postdir = direction(parts[-1])
    if postdir:
        parts = parts[:-1]
    posttype = ""
    if parts and parts[-1] in posttypes:
        posttype = parts.pop()
        if isinstance(posttypes, dict):
            posttype = posttypes[posttype]
    name = " ".join(parts).strip()
    if not name or not (predir or postdir or posttype):
        return None
    return ParsedAddress(predir=predir, name=name, posttype=posttype, postdir=postdir)


def domain_values(utrans_roads: str) -> dict[str, dict[str, str]]:
    """Return target field values keyed by accepted coded-value aliases.

    The target feature class supplies the domain assignments, avoiding the legacy
    hard-coded schema geodatabase.
    """
    workspace_path = Path(arcpy.Describe(utrans_roads).catalogPath).parent
    workspace_desc = arcpy.Describe(str(workspace_path))
    if getattr(workspace_desc, "datasetType", None) == "FeatureDataset":
        workspace_path = workspace_path.parent
    workspace = str(workspace_path)
    domains = {domain.name: domain for domain in arcpy.da.ListDomains(workspace)}
    resolved: dict[str, dict[str, str]] = {}
    for field in arcpy.ListFields(utrans_roads):
        if not field.domain or field.domain not in domains:
            continue
        accepted: dict[str, str] = {}
        for code, description in domains[field.domain].codedValues.items():
            code_text = str(code).strip().upper()
            accepted[code_text] = str(code)
            accepted[str(description).strip().upper()] = str(code)
        resolved[field.name.upper()] = accepted
    return resolved


def resolve_domain_value(value: object, values: dict[str, str]) -> str | None:
    if not has_value(value):
        return ""
    normalized = str(value).strip().upper()
    return values.get(normalized)


def field_name_map(feature_class: str) -> dict[str, str]:
    """Return actual field names keyed by case-insensitive names."""
    return {field.name.upper(): field.name for field in arcpy.ListFields(feature_class)}


def add_missing_template_fields(source_features: str, utrans_roads: str) -> None:
    """Add target fields missing from the working county copy.

    Existing county fields are renamed by the caller before this function runs.
    """
    source_names = field_name_map(source_features)
    for field in arcpy.ListFields(utrans_roads):
        if field.type in {"OID", "Geometry", "GlobalID", "Raster", "Blob"}:
            continue
        if field.name.upper() in source_names:
            continue
        kwargs: dict[str, object] = {}
        if field.type == "String":
            kwargs["field_length"] = field.length
        try:
            arcpy.management.AddField(source_features, field.name, field.type, **kwargs)
        except arcpy.ExecuteError as exc:
            details = str(exc) or arcpy.GetMessages(2)
            length = f", length={field.length}" if field.type == "String" else ""
            raise RuntimeError(
                f"Failed to add target field '{field.name}' "
                f"(type={field.type}{length}): {details}"
            ) from exc


def normalize_target_fields(feature_class: str) -> None:
    """Normalize target nulls, casing, and legacy name conventions in place."""
    names = field_name_map(feature_class)
    text_fields = [names[name] for name in CORE_TEXT_FIELDS if name in names]
    numeric_fields = [names[name] for name in CORE_NUMERIC_FIELDS if name in names]
    fields = text_fields + numeric_fields
    if not fields:
        return

    with arcpy.da.UpdateCursor(feature_class, fields) as cursor:
        for row in cursor:
            for index, _ in enumerate(text_fields):
                value = row[index]
                row[index] = "" if value is None else str(value).strip()
            for index in range(len(text_fields), len(fields)):
                if row[index] is None:
                    row[index] = 0

            row = _normalize_names(row, fields)
            cursor.updateRow(row)


def _normalize_names(row: list[object], fields: list[str]) -> list[object]:
    indexes = {name.upper(): index for index, name in enumerate(fields)}
    for field_name in NAME_FIELDS:
        index = indexes.get(field_name)
        if index is None or not row[index]:
            continue
        value = str(row[index]).upper().replace("'", "")
        if field_name == "NAME":
            value = _format_highway(value, row, indexes)
        row[index] = value

    for prefix in ("A1", "A2"):
        name_index = indexes.get(f"{prefix}_NAME")
        if name_index is None or not str(row[name_index]).isdigit():
            continue
        numeric_index = indexes.get("AN_NAME")
        if numeric_index is not None:
            row[numeric_index] = row[name_index]
        for suffix in ("PREDIR", "NAME", "POSTTYPE"):
            alias_index = indexes.get(f"{prefix}_{suffix}")
            if alias_index is not None:
                row[alias_index] = ""
    return row


def _format_highway(value: str, row: list[object], indexes: dict[str, int]) -> str:
    compact = value.replace(" ", "")
    if compact.startswith(("US", "SR", "HWY")) and compact[2:].isdigit():
        prefix = "HWY" if compact.startswith("HWY") else compact[:2]
        number = compact[len(prefix) :]
        highway_index = indexes.get("DOT_HWYNAM")
        posttype_index = indexes.get("POSTTYPE")
        if highway_index is not None:
            row[highway_index] = f"{prefix} {number}"
        if posttype_index is not None:
            row[posttype_index] = ""
        return f"HIGHWAY {number}"
    if compact in {"I15", "I70", "I80", "I84"}:
        return f"I-{compact[1:]}"
    return value


def required_source_fields(feature_class: str, fields: Iterable[str]) -> None:
    names = field_name_map(feature_class)
    missing = [field for field in fields if field.upper() not in names]
    if missing:
        raise RuntimeError(
            f"Source features are missing required fields: {', '.join(missing)}"
        )
