"""Unified recent-edits runner for county road change detection.

Requires explicit full feature class paths:
- `--update-features`
- `--base-features`
- `--county` (to select the correct field mapping profile)
"""

import argparse
import os
import time
from dataclasses import dataclass, field
from pathlib import Path

import arcpy

from utrans.profiles import load_profiles as load_shared_profiles
from utrans.utilities import get_output_workspace, log

NUMERIC_TYPES = {"SmallInteger", "Integer", "Single", "Double", "BigInteger"}
DEFAULT_SEARCH_DISTANCE = "200 Feet"
DEFAULT_CHANGE_TOLERANCE = "40"
DEFAULT_DFC_OUTPUT_NAME = "DFC_CountyToCounty"
DEFAULT_STATS_TABLE_NAME = "stats_county_to_county"
DEFAULT_RECENTS_NAME = "RoadCenterline_Recents"


def _detect_field_groups(feature_class: str) -> tuple[list[str], list[str]]:
    """Detect text and numeric field groups from a feature class.

    Args:
        feature_class: Path to the feature class.

    Returns:
        Tuple of (text_field_names, numeric_field_names).
    """
    desc = arcpy.da.Describe(feature_class)
    fields = desc["fields"]

    text_fields = [f.name for f in fields if f.type == "String"]
    numeric_fields = [f.name for f in fields if f.type in NUMERIC_TYPES]

    return text_fields, numeric_fields


@dataclass
class CountyProfile:
    match_fields: str = ""
    compare_fields: str | None = None
    uppercase_normalize_fields: set[str] = field(default_factory=set)
    required_fields: list[str] = field(default_factory=list)


def _load_profiles(path: Path | None = None) -> dict[str, CountyProfile]:
    profiles = {}
    for key, shared_profile in load_shared_profiles(path).items():
        data = shared_profile.values
        profiles[key] = CountyProfile(
            match_fields=data["match_fields"],
            compare_fields=data.get("compare_fields"),
            uppercase_normalize_fields=set(data.get("uppercase_normalize_fields", [])),
            required_fields=data.get("required_fields", []),
        )

    return profiles


PROFILES = _load_profiles()


def get_field_name_map(feature_class):
    return {field.name.lower(): field.name for field in arcpy.ListFields(feature_class)}


def ensure_detect_feature_changes_license():
    product_info = str(arcpy.ProductInfo()).strip()
    if product_info.lower() in {"arcinfo", "advanced"}:
        return
    arcinfo_status = str(arcpy.CheckProduct("ArcInfo")).strip()
    raise RuntimeError(
        "Detect Feature Changes requires an ArcGIS Pro Advanced license. "
        f"Current ProductInfo is '{product_info}' and CheckProduct('ArcInfo') is "
        f"'{arcinfo_status}'. Ask your GIS admin to assign an Advanced seat, then rerun this script."
    )


def parse_field_pairs(field_mapping):
    pairs = []
    for token in field_mapping.split(";"):
        parts = token.strip().split()
        if len(parts) >= 2:
            pairs.append((parts[0], parts[1]))
    return pairs


def resolve_field_pairs(update_features, base_features, field_mapping):
    update_map = get_field_name_map(update_features)
    base_map = get_field_name_map(base_features)
    resolved_pairs = []
    dropped_pairs = []
    for update_field, base_field in parse_field_pairs(field_mapping):
        update_actual = update_map.get(update_field.lower())
        base_actual = base_map.get(base_field.lower())
        if update_actual and base_actual:
            resolved_pairs.append((update_actual, base_actual))
        else:
            dropped_pairs.append((update_field, base_field))

    if dropped_pairs:
        dropped_pairs_text = "; ".join(
            [
                f"{update_field} {base_field}"
                for update_field, base_field in dropped_pairs
            ]
        )
        log(
            "Warning: dropping "
            f"{len(dropped_pairs)} field pair(s) not found in both datasets: {dropped_pairs_text}"
        )

    return resolved_pairs


def _blank_like(value):
    if value is None:
        return True
    return str(value).strip() in {"", "None", "NULL"}


def _normalize_text_value(value, force_uppercase):
    if _blank_like(value):
        return ""
    normalized = " ".join(str(value).split())
    if force_uppercase:
        return normalized.upper()
    return normalized


def normalize_fields(feature_class, profile, text_fields=None, numeric_fields=None):
    field_map = get_field_name_map(feature_class)
    text_source = text_fields if text_fields is not None else []
    numeric_source = numeric_fields if numeric_fields is not None else []

    text_existing = [
        field_map[name.lower()] for name in text_source if name.lower() in field_map
    ]
    numeric_existing = [
        field_map[name.lower()] for name in numeric_source if name.lower() in field_map
    ]
    field_names = text_existing + numeric_existing

    if not field_names:
        return

    with arcpy.da.UpdateCursor(feature_class, field_names) as rows:
        for row in rows:
            updated = False
            for idx in range(len(text_existing)):
                value = row[idx]
                field_name = text_existing[idx]
                replacement = _normalize_text_value(
                    value,
                    force_uppercase=field_name.upper()
                    in profile.uppercase_normalize_fields,
                )

                if replacement != value:
                    row[idx] = replacement
                    updated = True

            for idx in range(len(text_existing), len(field_names)):
                value = row[idx]
                replacement = 0 if _blank_like(value) else value

                if replacement != value:
                    row[idx] = replacement
                    updated = True

            if updated:
                rows.updateRow(row)


def resolve_county_profile(county, profiles=None):
    if profiles is None:
        profiles = PROFILES
    county_key = county.strip()
    if county_key in profiles:
        return county_key, profiles[county_key]
    raise RuntimeError(
        f"Unknown county '{county}'. Supported counties (exact, case-sensitive): "
        f"{', '.join(sorted(profiles.keys()))}. Aliases and spaced variants are not supported."
    )


def resolve_required_inputs(args):
    if not args.county:
        raise RuntimeError(
            "Missing required input. Provide --county to select a field mapping profile."
        )
    if not args.update_features or not args.base_features:
        raise RuntimeError(
            "Missing required input paths. Provide both --update-features and --base-features."
        )
    return args.county, args.update_features, args.base_features


def ensure_required_fields(feature_class, required_fields, dataset_label):
    lookup = get_field_name_map(feature_class)
    missing = [
        field_name for field_name in required_fields if field_name.lower() not in lookup
    ]
    if missing:
        raise RuntimeError(
            f"{dataset_label} is missing required fields: {', '.join(missing)}"
        )


def format_county_help(profiles=None):
    active_profiles = profiles or PROFILES
    return ", ".join(sorted(active_profiles.keys()))


def run_change_detection(
    profile_key,
    profile,
    update_features,
    base_features,
    match_fields,
    compare_fields,
):
    arcpy.env.overwriteOutput = True
    output_workspace = get_output_workspace(update_features)
    dfc_output = os.path.join(output_workspace, DEFAULT_DFC_OUTPUT_NAME)
    stats_table = os.path.join(output_workspace, DEFAULT_STATS_TABLE_NAME)
    out_feature = os.path.join(output_workspace, DEFAULT_RECENTS_NAME)

    if profile.required_fields:
        ensure_required_fields(
            update_features, profile.required_fields, "Update features"
        )
        ensure_required_fields(base_features, profile.required_fields, "Base features")

    if not compare_fields:
        raise RuntimeError(
            "Compare fields were not provided and county profile has no default compare mapping."
        )

    resolved_match_pairs = resolve_field_pairs(
        update_features, base_features, match_fields
    )
    if not resolved_match_pairs:
        raise RuntimeError(
            "No valid match field pairs found between update and base feature classes. "
            "Update the county profile with fields that exist in both datasets."
        )
    resolved_match_fields = "; ".join(
        [
            f"{update_field} {base_field}"
            for update_field, base_field in resolved_match_pairs
        ]
    )

    resolved_compare_pairs = resolve_field_pairs(
        update_features, base_features, compare_fields
    )
    if not resolved_compare_pairs:
        raise RuntimeError(
            "No valid compare field pairs found between update and base feature classes. "
            "Update the county profile with fields that exist in both datasets."
        )
    resolved_compare_fields = "; ".join(
        [
            f"{update_field} {base_field}"
            for update_field, base_field in resolved_compare_pairs
        ]
    )

    log("Normalizing blank and null-like values before change detection")
    text_fields_update, numeric_fields_update = _detect_field_groups(update_features)
    text_fields_base, numeric_fields_base = _detect_field_groups(base_features)

    for dataset_label, feature_class, text_fields, numeric_fields in [
        ("Update features", update_features, text_fields_update, numeric_fields_update),
        ("Base features", base_features, text_fields_base, numeric_fields_base),
    ]:
        dataset_name = arcpy.Describe(feature_class).name
        log(
            f"Normalizing {dataset_label} ({dataset_name}): blank text values to empty strings, blank numeric values to 0"
        )
        normalize_fields(
            feature_class,
            profile,
            text_fields=text_fields,
            numeric_fields=numeric_fields,
        )

    log("Running DetectFeatureChanges")
    log(
        f"Beginning detect feature change process for {profile_key} at: {time.strftime('%c')}"
    )
    arcpy.management.DetectFeatureChanges(
        update_features,
        base_features,
        dfc_output,
        DEFAULT_SEARCH_DISTANCE,
        resolved_match_fields,
        stats_table,
        DEFAULT_CHANGE_TOLERANCE,
        resolved_compare_fields,
    )
    log("DetectFeatureChanges finished")

    log(f"Creating changed-road output feature class: {DEFAULT_RECENTS_NAME}")
    arcpy.env.qualifiedFieldNames = False

    roads_layer = "roads_lyr"
    dfc_layer = "dfc_lyr"
    arcpy.management.MakeFeatureLayer(update_features, roads_layer)
    arcpy.management.MakeFeatureLayer(dfc_output, dfc_layer)

    join_field_roads = arcpy.Describe(roads_layer).OIDFieldName
    arcpy.management.AddJoin(roads_layer, join_field_roads, dfc_layer, "UPDATE_FID")

    dfc_name = arcpy.Describe(dfc_output).name
    expression = f"{dfc_name}.CHANGE_TYPE <> 'NC'"
    arcpy.management.SelectLayerByAttribute(roads_layer, "NEW_SELECTION", expression)
    arcpy.management.CopyFeatures(roads_layer, out_feature)

    log("Finished change detection and recents export at: " + time.strftime("%c"))


def build_parser(prog: str | None = None):
    county_help = format_county_help()
    parser = argparse.ArgumentParser(
        prog=prog,
        description="Detect recent edits between county update and baseline roads.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python Get_Recent_Edits.py --county grand "
            '--update-features "Z:\\Documents\\gdb\\GRAND\\GrandCo_20260514.gdb\\GC__RDS_05_01_26" '
            '--base-features "Z:\\Documents\\gdb\\GRAND\\GrandCo_20240812.gdb\\GRANDROADS_24"\n'
            "\n"
            "  python Get_Recent_Edits.py --county davis "
            '--update-features "Z:\\Documents\\gdb\\DavisCounty_20260626.gdb\\DavisRoads" '
            '--base-features "Z:\\Documents\\gdb\\DavisCounty_20260604.gdb\\DavisRoads"'
        ),
    )
    parser.add_argument(
        "--county",
        required=True,
        help=(
            "Required. Case-sensitive county key used to select the field mapping profile "
            "from the active profiles file (default: profiles.json, override with --profiles). "
            "Only exact top-level profile keys are accepted (aliases are not supported). "
            f"Available county keys: {county_help}."
        ),
    )

    parser.add_argument(
        "--update-features",
        required=True,
        help="Full path to newest county road feature class.",
    )
    parser.add_argument(
        "--base-features",
        required=True,
        help="Full path to previous county road feature class.",
    )

    parser.add_argument(
        "--profiles",
        default=None,
        metavar="PATH",
        help="Path to a custom profiles JSON file. Defaults to profiles.json next to this script.",
    )
    return parser


def main(argv=None, *, prog: str | None = None):
    start_time = time.time()
    parser = build_parser(prog=prog)
    args = parser.parse_args(argv)

    try:
        profiles = _load_profiles(Path(args.profiles) if args.profiles else None)
        county, update_features, base_features = resolve_required_inputs(args)
        profile_key, profile = resolve_county_profile(county, profiles)

        ensure_detect_feature_changes_license()

        run_change_detection(
            profile_key=profile_key,
            profile=profile,
            update_features=update_features,
            base_features=base_features,
            match_fields=profile.match_fields,
            compare_fields=profile.compare_fields,
        )
    except RuntimeError as exc:
        log(str(exc))
        return 2

    elapsed = time.time() - start_time
    log(f"Time elapsed: {elapsed:.2f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
