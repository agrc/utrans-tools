"""Unified recent-edits runner for county road change detection.

Requires explicit full feature class paths:
- `--update-features`
- `--base-features`

County wrappers can dispatch here with a fixed `--county` value.
"""

import argparse
import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path

import arcpy


@dataclass
class CountyProfile:
    aliases: list[str]
    display_name: str
    default_match_fields: str
    default_compare_fields: str | None
    text_fields: list[str] = field(default_factory=list)
    numeric_fields: list[str] = field(default_factory=list)
    uppercase_normalize_fields: set[str] = field(default_factory=set)
    apply_legacy_text_standardization: bool = False
    default_dfc_output_name: str = "DFC_CountyToCounty"
    default_stats_table_name: str = "stats_county_to_county"
    default_recents_name: str = "RoadCenterline_Recents"
    required_fields: list[str] = field(default_factory=list)


def _load_profiles(path: Path | None = None) -> dict[str, CountyProfile]:
    profiles_path = path or Path(__file__).parent / "profiles.json"
    with profiles_path.open(encoding="utf-8") as f:
        raw = json.load(f)

    profiles = {}
    for key, data in raw.items():
        profiles[key] = CountyProfile(
            aliases=data["aliases"],
            display_name=data["display_name"],
            default_match_fields=data["default_match_fields"],
            default_compare_fields=data.get("default_compare_fields"),
            text_fields=data.get("text_fields", []),
            numeric_fields=data.get("numeric_fields", []),
            uppercase_normalize_fields=set(data.get("uppercase_normalize_fields", [])),
            apply_legacy_text_standardization=data.get("apply_legacy_text_standardization", False),
            default_dfc_output_name=data.get("default_dfc_output_name", "DFC_CountyToCounty"),
            default_stats_table_name=data.get("default_stats_table_name", "stats_county_to_county"),
            default_recents_name=data.get("default_recents_name", "RoadCenterline_Recents"),
            required_fields=data.get("required_fields", []),
        )
    return profiles


PROFILES = _load_profiles()


def log(message):
    print(message)


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
    for update_field, base_field in parse_field_pairs(field_mapping):
        update_actual = update_map.get(update_field.lower())
        base_actual = base_map.get(base_field.lower())
        if update_actual and base_actual:
            resolved_pairs.append((update_actual, base_actual))
    return resolved_pairs


def get_output_workspace(update_features):
    dirname = os.path.dirname(arcpy.Describe(update_features).catalogPath)
    desc = arcpy.Describe(dirname)
    if hasattr(desc, "datasetType") and desc.datasetType == "FeatureDataset":
        dirname = os.path.dirname(dirname)
    return dirname


def _blank_like(value):
    if value is None:
        return True
    return str(value).strip() in {"", "None", "NULL"}


def _normalize_text_value(value, force_uppercase, apply_legacy_text_standardization=False):
    if _blank_like(value):
        return ""
    if apply_legacy_text_standardization:
        normalized = " ".join(str(value).split())
        if force_uppercase:
            return normalized.upper()
        return normalized
    if force_uppercase:
        return " ".join(str(value).split()).upper()
    return value


def normalize_fields(feature_class, profile, text_fields=None, numeric_fields=None):
    field_map = get_field_name_map(feature_class)
    text_source = text_fields if text_fields is not None else profile.text_fields
    numeric_source = numeric_fields if numeric_fields is not None else profile.numeric_fields

    text_existing = [field_map[name.lower()] for name in text_source if name.lower() in field_map]
    numeric_existing = [field_map[name.lower()] for name in numeric_source if name.lower() in field_map]
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
                    force_uppercase=field_name.upper() in profile.uppercase_normalize_fields,
                    apply_legacy_text_standardization=profile.apply_legacy_text_standardization,
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
    county_key = county.lower().strip()
    for profile_key, profile in profiles.items():
        aliases = {alias.lower() for alias in profile.aliases}
        aliases.add(profile_key.lower())
        if county_key in aliases:
            return profile
    raise RuntimeError(f"Unknown county '{county}'. Supported counties: {', '.join(sorted(profiles.keys()))}")


def resolve_feature_inputs(args):
    if not args.update_features or not args.base_features:
        raise RuntimeError(
            "Missing required input paths. Provide both --update-features and --base-features."
        )
    return args.update_features, args.base_features


def ensure_required_fields(feature_class, required_fields, dataset_label):
    lookup = get_field_name_map(feature_class)
    missing = [field_name for field_name in required_fields if field_name.lower() not in lookup]
    if missing:
        raise RuntimeError(
            f"{dataset_label} is missing required fields: {', '.join(missing)}"
        )


def run_change_detection(
    profile,
    update_features,
    base_features,
    search_distance,
    match_fields,
    change_tolerance,
    compare_fields,
    dfc_output_name,
    stats_table_name,
    recents_name,
):
    arcpy.env.overwriteOutput = True
    output_workspace = get_output_workspace(update_features)
    dfc_output = os.path.join(output_workspace, dfc_output_name)
    stats_table = os.path.join(output_workspace, stats_table_name)
    out_feature = os.path.join(output_workspace, recents_name)

    active_text_fields = profile.text_fields
    active_numeric_fields = profile.numeric_fields

    if profile.required_fields:
        ensure_required_fields(update_features, profile.required_fields, "Update features")
        ensure_required_fields(base_features, profile.required_fields, "Base features")

    if not compare_fields:
        raise RuntimeError("Compare fields were not provided and county profile has no default compare mapping.")

    resolved_match_pairs = resolve_field_pairs(update_features, base_features, match_fields)
    if not resolved_match_pairs:
        raise RuntimeError(
            "No valid match field pairs found between update and base feature classes. "
            "Pass --match-fields with fields that exist in both datasets."
        )
    match_fields = "; ".join([f"{update_field} {base_field}" for update_field, base_field in resolved_match_pairs])

    resolved_compare_pairs = resolve_field_pairs(update_features, base_features, compare_fields)
    if not resolved_compare_pairs:
        raise RuntimeError(
            "No valid compare field pairs found between update and base feature classes. "
            "Pass --compare-fields with fields that exist in both datasets."
        )
    compare_fields = "; ".join([f"{update_field} {base_field}" for update_field, base_field in resolved_compare_pairs])

    log("begin converting nulls to empty")
    for feature_class in [update_features, base_features]:
        normalize_fields(
            feature_class,
            profile,
            text_fields=active_text_fields,
            numeric_fields=active_numeric_fields,
        )

    log("begin detect feature changes")
    log(f"Beginning detect feature change process for {profile.display_name} at: {time.strftime('%c')}")
    arcpy.management.DetectFeatureChanges(
        update_features,
        base_features,
        dfc_output,
        search_distance,
        match_fields,
        stats_table,
        change_tolerance,
        compare_fields,
    )
    log("finished detect feature change process")

    log(f"begin creating separate feature class named {recents_name}")
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

    log("Finished detect feature change process at: " + time.strftime("%c"))
    log("done at: " + time.strftime("%c"))


def build_parser():
    parser = argparse.ArgumentParser(
        description="Detect recent edits between county update and baseline roads.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python Get_Recent_Edits.py --county Grand "
            "--update-features \"Z:\\Documents\\gdb\\GRAND\\GrandCo_20260514.gdb\\GC__RDS_05_01_26\" "
            "--base-features \"Z:\\Documents\\gdb\\GRAND\\GrandCo_20240812.gdb\\GRANDROADS_24\"\n"
            "\n"
            "  python Get_Recent_Edits.py --county Davis "
            "--update-features \"Z:\\Documents\\gdb\\DavisCounty_20260626.gdb\\DavisRoads\" "
            "--base-features \"Z:\\Documents\\gdb\\DavisCounty_20260604.gdb\\DavisRoads\""
        ),
    )
    parser.add_argument("--county", required=True, help="County key, such as Beaver or Davis.")

    parser.add_argument("--update-features", required=True, help="Full path to newest county road feature class.")
    parser.add_argument("--base-features", required=True, help="Full path to previous county road feature class.")

    parser.add_argument(
        "--search-distance",
        default="200 Feet",
        help="Search distance for candidate matches in Detect Feature Changes.",
    )
    parser.add_argument("--match-fields", help="Semicolon-delimited field mapping string used for matching.")
    parser.add_argument("--change-tolerance", default="40", help="Change tolerance used by Detect Feature Changes.")
    parser.add_argument(
        "--compare-fields",
        help=(
            "Optional semicolon-delimited field mapping string for compare attributes. "
            "When omitted, county defaults are used."
        ),
    )
    parser.add_argument("--dfc-output-name", help="Output feature class name for Detect Feature Changes result.")
    parser.add_argument("--stats-table-name", help="Output table name for Detect Feature Changes statistics.")
    parser.add_argument("--recents-name", help="Output feature class name for selected changed roads.")
    parser.add_argument(
        "--profiles",
        default=None,
        metavar="PATH",
        help="Path to a custom profiles JSON file. Defaults to profiles.json next to this script.",
    )
    return parser


def main(argv=None):
    start_time = time.time()
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        profiles = _load_profiles(Path(args.profiles) if args.profiles else None)
        profile = resolve_county_profile(args.county, profiles)
        update_features, base_features = resolve_feature_inputs(args)

        ensure_detect_feature_changes_license()

        match_fields = args.match_fields or profile.default_match_fields
        compare_fields = args.compare_fields if args.compare_fields is not None else profile.default_compare_fields
        dfc_output_name = args.dfc_output_name or profile.default_dfc_output_name
        stats_table_name = args.stats_table_name or profile.default_stats_table_name
        recents_name = args.recents_name or profile.default_recents_name

        run_change_detection(
            profile=profile,
            update_features=update_features,
            base_features=base_features,
            search_distance=args.search_distance,
            match_fields=match_fields,
            change_tolerance=args.change_tolerance,
            compare_fields=compare_fields,
            dfc_output_name=dfc_output_name,
            stats_table_name=stats_table_name,
            recents_name=recents_name,
        )
    except RuntimeError as exc:
        log(str(exc))
        return 2

    elapsed = time.time() - start_time
    log("Time elapsed: {:.2f}s".format(elapsed))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
