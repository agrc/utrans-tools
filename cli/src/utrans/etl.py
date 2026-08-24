"""County road ETL command for ArcGIS Pro/Python 3."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import arcpy

from utrans.etl_common import (
    add_missing_template_fields,
    field_name_map,
    normalize_target_fields,
)
from utrans.etl_mappers import apply_mapper
from utrans.profiles import (
    CountyProfile,
    format_county_help,
    load_profiles,
    resolve_county_profile,
)
from utrans.utilities import log


def _default_output_name(county: str) -> str:
    return f"{county}_etl_{datetime.now(UTC):%Y%m%d}"


def _county_boundary_name(county: str) -> str:
    names = {"boxelder": "BOX ELDER", "saltlake": "SALT LAKE", "sanjuan": "SAN JUAN"}
    return names.get(county, county.upper())


def _unique_name(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:8]}"


def _rename_colliding_fields(source_features: str, utrans_roads: str) -> None:
    source_names = field_name_map(source_features)
    template_names = field_name_map(utrans_roads)
    for name, actual_name in list(source_names.items()):
        if name not in template_names or name in {
            "OBJECTID",
            "SHAPE",
            "SHAPE_LENGTH",
            "SHAPE_AREA",
        }:
            continue
        replacement = f"{actual_name}_"
        if replacement.upper() in source_names:
            raise RuntimeError(
                f"Cannot preserve source field '{actual_name}': '{replacement}' already exists."
            )
        arcpy.management.AlterField(
            source_features, actual_name, replacement, replacement
        )
        source_names[replacement.upper()] = replacement


def _validate_output(output_features: str) -> None:
    if arcpy.Exists(output_features):
        raise RuntimeError(
            f"Output already exists: {output_features}. Choose --output-name with a new name."
        )


def run_etl(
    source_features: str,
    utrans_roads: str,
    output_workspace: str,
    county_boundaries: str,
    county: str,
    profile: CountyProfile,
    output_name: str,
    county_boundary_name: str | None = None,
) -> str:
    """Run the county transformation and export whole roads intersecting its boundary."""
    if not arcpy.Exists(source_features):
        raise RuntimeError(f"Source features do not exist: {source_features}")
    if not arcpy.Exists(utrans_roads):
        raise RuntimeError(f"UTRANS roads do not exist: {utrans_roads}")
    if not arcpy.Exists(county_boundaries):
        raise RuntimeError(f"County boundaries do not exist: {county_boundaries}")
    if not arcpy.Exists(output_workspace):
        raise RuntimeError(f"Output workspace does not exist: {output_workspace}")

    output_features = str(Path(output_workspace) / output_name)
    _validate_output(output_features)
    staging_source = str(Path(output_workspace) / _unique_name("utrans_source"))
    staging_output = str(Path(output_workspace) / _unique_name("utrans_output"))
    arcpy.env.overwriteOutput = True

    try:
        log("Creating ETL staging feature classes")
        arcpy.management.CopyFeatures(source_features, staging_source)
        arcpy.management.CopyFeatures(utrans_roads, staging_output)
        arcpy.management.DeleteRows(staging_output)

        log("Preparing target UTRANS fields")
        _rename_colliding_fields(staging_source, utrans_roads)
        add_missing_template_fields(staging_source, utrans_roads)

        log(f"Applying {county} county field mappings")
        apply_mapper(staging_source, profile, utrans_roads)
        normalize_target_fields(staging_source, utrans_roads)

        log("Appending transformed roads to the target schema")
        arcpy.management.Append(staging_source, staging_output, "NO_TEST")
        arcpy.edit.Densify(staging_output, "ANGLE")
        arcpy.edit.Generalize(staging_output, "2 Meters")

        boundary_name = county_boundary_name or _county_boundary_name(county)
        boundary_field = field_name_map(county_boundaries).get("NAME")
        if boundary_field is None:
            raise RuntimeError("County boundaries must include a NAME field.")
        boundary_layer = _unique_name("county_boundary")
        roads_layer = _unique_name("county_roads")
        expression = f"{arcpy.AddFieldDelimiters(county_boundaries, boundary_field)} = '{boundary_name.replace("'", "''")}'"
        arcpy.management.MakeFeatureLayer(county_boundaries, boundary_layer, expression)
        if int(arcpy.management.GetCount(boundary_layer)[0]) != 1:
            raise RuntimeError(
                f"Expected one county boundary named '{boundary_name}', but found a different count."
            )
        arcpy.management.MakeFeatureLayer(staging_output, roads_layer)
        arcpy.management.SelectLayerByLocation(roads_layer, "INTERSECT", boundary_layer)
        arcpy.management.CopyFeatures(roads_layer, output_features)
        log(f"Created ETL output: {output_features}")
        return output_features
    finally:
        for temporary in (staging_source, staging_output):
            if arcpy.Exists(temporary):
                arcpy.management.Delete(temporary)


def build_parser(prog: str | None = None) -> argparse.ArgumentParser:
    profiles = load_profiles()
    parser = argparse.ArgumentParser(
        prog=prog,
        description="Transform county roads into the UTRANS schema.",
    )
    parser.add_argument(
        "--county", required=True, help=f"County key: {format_county_help(profiles)}."
    )
    parser.add_argument(
        "--source-features", required=True, help="County road feature class."
    )
    parser.add_argument(
        "--utrans-roads",
        required=True,
        help="UTRANS roads feature class used as the target schema.",
    )
    parser.add_argument(
        "--output-workspace", required=True, help="Geodatabase for the ETL output."
    )
    parser.add_argument(
        "--county-boundaries", required=True, help="County boundary feature class."
    )
    parser.add_argument(
        "--output-name",
        help="Output feature class name. Defaults to county_etl_YYYYMMDD.",
    )
    parser.add_argument(
        "--county-boundary-name",
        help="Override the NAME value used to select the county boundary.",
    )
    parser.add_argument(
        "--profiles", metavar="PATH", help="Custom flat profiles JSON file."
    )
    return parser


def main(argv: list[str] | None = None, *, prog: str | None = None) -> int:
    args = build_parser(prog).parse_args(argv)
    try:
        profiles = load_profiles(Path(args.profiles) if args.profiles else None)
        profile = resolve_county_profile(args.county, profiles)
        run_etl(
            args.source_features,
            args.utrans_roads,
            args.output_workspace,
            args.county_boundaries,
            profile.key,
            profile,
            args.output_name or _default_output_name(profile.key),
            args.county_boundary_name,
        )
    except (RuntimeError, TypeError, FileNotFoundError, json.JSONDecodeError) as exc:
        log(str(exc))
        return 2
    return 0
