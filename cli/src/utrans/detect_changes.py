"""Detect and publish changes from an ETL-produced UTRANS feature class."""

from __future__ import annotations

import argparse
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

import arcpy

from utrans.profiles import format_county_help, load_profiles, resolve_county_profile
from utrans.recent_edits import (
    ensure_detect_feature_changes_license,
)
from utrans.utilities import get_output_workspace, log

MATCH_FIELDS = "NAME NAME"
COMPARE_FIELDS = (
    "PREDIR PREDIR; POSTTYPE POSTTYPE; NAME NAME; POSTDIR POSTDIR; "
    "FROMADDR_L FROMADDR_L; TOADDR_L TOADDR_L; FROMADDR_R FROMADDR_R; "
    "TOADDR_R TOADDR_R; A1_PREDIR A1_PREDIR; A1_NAME A1_NAME; "
    "A1_POSTTYPE A1_POSTTYPE; A1_POSTDIR A1_POSTDIR; A2_PREDIR A2_PREDIR; "
    "A2_NAME A2_NAME; A2_POSTTYPE A2_POSTTYPE; A2_POSTDIR A2_POSTDIR; "
    "AN_NAME AN_NAME; AN_POSTDIR AN_POSTDIR"
)
DFC_OUTPUT_NAME = "DFC_RESULT"
STATS_TABLE_NAME = "new_roads_stats"
TEST_OUTPUT_NAME = "TEST_DFC_RESULT"
CHANGE_FILTER = "CHANGE_TYPE NOT IN ('NC', 'D')"
SEARCH_DISTANCE = "50"
CHANGE_TOLERANCE = "50"
APPEND_TARGET = (
    r"Database Connections\DC_TRANSADMIN@UTRANS@utrans.agrc.utah.gov.sde"
    "\\"
    r"UTRANS.TRANSADMIN.Centerlines_Edit\UTRANS.TRANSADMIN.DFC_RESULT"
)


def extract_fips(fips_setting: str) -> str:
    """Extract the five-digit FIPS code from a profile value."""
    match = re.search(r"\b\d{5}\b", str(fips_setting))
    if not match:
        raise RuntimeError(f"Invalid county FIPS setting: '{fips_setting}'.")
    return match.group(0)


def _field_exists(feature_class: str, field_name: str) -> bool:
    return any(
        field.name.upper() == field_name for field in arcpy.ListFields(feature_class)
    )


def add_dfc_fields(dfc_output: str, fips: str) -> None:
    fields: tuple[tuple[str, Literal["TEXT", "DATE"], int | None], ...] = (
        ("CURRENT_NOTES", "TEXT", 50),
        ("PREV__NOTES", "TEXT", 50),
        ("EDITOR", "TEXT", 20),
        ("EDIT_DATE", "DATE", None),
        ("DATE_ADDED", "DATE", None),
        ("COFIPS", "TEXT", 5),
    )
    for name, field_type, length in fields:
        if not _field_exists(dfc_output, name):
            if length is None:
                arcpy.management.AddField(dfc_output, name, field_type)
            else:
                arcpy.management.AddField(
                    dfc_output, name, field_type, field_length=length
                )

    with arcpy.da.UpdateCursor(dfc_output, ["DATE_ADDED", "COFIPS"]) as rows:
        for row in rows:
            row[0] = datetime.now(UTC)
            row[1] = fips
            rows.updateRow(row)


def _resolve_field_mapping(feature_classes: tuple[str, ...], mapping: str) -> str:
    available_fields = [
        {field.name.upper() for field in arcpy.ListFields(feature_class)}
        for feature_class in feature_classes
    ]
    pairs = []
    for token in mapping.split(";"):
        update_field, base_field = token.strip().split()
        if all(
            update_field.upper() in fields and base_field.upper() in fields
            for fields in available_fields
        ):
            pairs.append(f"{update_field} {base_field}")
    if not pairs:
        raise RuntimeError(
            "No fields from the fixed mapping were found in both datasets."
        )
    return "; ".join(pairs)


def run_detect_changes(
    update_features: str,
    base_features: str,
    fips: str,
) -> tuple[str, str]:
    arcpy.env.overwriteOutput = True
    output_workspace = get_output_workspace(update_features)
    dfc_output = os.path.join(output_workspace, DFC_OUTPUT_NAME)
    stats_table = os.path.join(output_workspace, STATS_TABLE_NAME)
    test_output = os.path.join(output_workspace, TEST_OUTPUT_NAME)
    base_layer = "detect_changes_base"

    arcpy.management.MakeFeatureLayer(
        base_features,
        base_layer,
        f"COUNTY_L = '{fips}' OR COUNTY_R = '{fips}'",
    )
    try:
        datasets = (update_features, base_features)
        match_fields = _resolve_field_mapping(datasets, MATCH_FIELDS)
        compare_fields = _resolve_field_mapping(datasets, COMPARE_FIELDS)
        log("Running DetectFeatureChanges")
        arcpy.management.DetectFeatureChanges(
            update_features,
            base_layer,
            dfc_output,
            SEARCH_DISTANCE,
            match_fields,
            stats_table,
            CHANGE_TOLERANCE,
            compare_fields,
        )
        add_dfc_fields(dfc_output, fips)
        arcpy.AlterAliasName(dfc_output, "DFC_RESULT")

        changed_layer = "detect_changes_output"
        arcpy.management.MakeFeatureLayer(dfc_output, changed_layer, CHANGE_FILTER)
        arcpy.management.CopyFeatures(changed_layer, test_output)
        arcpy.management.Append(changed_layer, APPEND_TARGET, "NO_TEST")
        log(f"Appended changed features to {APPEND_TARGET}")
        return dfc_output, test_output
    finally:
        if arcpy.Exists(base_layer):
            arcpy.management.Delete(base_layer)


def build_parser(prog: str | None = None):
    profiles = load_profiles()
    parser = argparse.ArgumentParser(
        prog=prog,
        description="Detect changes in ETL-produced UTRANS roads.",
    )
    parser.add_argument(
        "--county",
        required=True,
        help=f"County profile key: {format_county_help(profiles)}.",
    )
    parser.add_argument(
        "--update-features", required=True, help="ETL-produced road feature class."
    )
    parser.add_argument(
        "--utrans-features", required=True, help="UTRANS baseline road feature class."
    )
    parser.add_argument(
        "--profiles", type=Path, help="Path to a custom profiles JSON file."
    )
    return parser


def main(argv=None, *, prog: str | None = None):
    parser = build_parser(prog=prog)
    args = parser.parse_args(argv)
    try:
        profiles = load_profiles(args.profiles)
        profile = resolve_county_profile(args.county, profiles)
        fips = extract_fips(profile.require("fips"))
        ensure_detect_feature_changes_license()
        run_detect_changes(
            args.update_features,
            args.utrans_features,
            fips,
        )
    except RuntimeError as exc:
        log(str(exc))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
