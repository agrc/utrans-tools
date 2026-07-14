"""Davis County recent edits detection for ArcGIS Pro (Python 3).

Supports both known Davis schemas:
- legacy/truncated field names (PrefixDire, RoadNameTy, ...)
- gdb/full field names (PrefixDirection, RoadNameType, ...)
"""

import argparse
import os
import time

import arcpy


SCHEMAS = {
    "legacy": {
        "description": "Legacy/truncated Davis field names",
        "text_fields": ["PrefixDire", "RoadName", "RoadNameTy", "PostDirect", "RoadAliasN"],
        "numeric_fields": ["LeftFrom", "LeftTo", "RightFrom", "RightTo"],
        "compare_pairs": [
            ("PrefixDire", "PrefixDire"),
            ("RoadName", "RoadName"),
            ("RoadNameTy", "RoadNameTy"),
            ("PostDirect", "PostDirect"),
            ("RoadAliasN", "RoadAliasN"),
            ("LeftFrom", "LeftFrom"),
            ("LeftTo", "LeftTo"),
            ("RightFrom", "RightFrom"),
            ("RightTo", "RightTo"),
        ],
    },
    "gdb": {
        "description": "GDB/full Davis field names",
        "text_fields": [
            "PrefixDirection",
            "RoadName",
            "RoadNameType",
            "PostDirection",
            "RoadAliasName",
        ],
        "numeric_fields": ["LeftFrom", "LeftTo", "RightFrom", "RightTo", "MPH"],
        "compare_pairs": [
            ("PrefixDirection", "PrefixDirection"),
            ("RoadName", "RoadName"),
            ("RoadNameType", "RoadNameType"),
            ("PostDirection", "PostDirection"),
            ("RoadAliasName", "RoadAliasName"),
            ("LeftFrom", "LeftFrom"),
            ("LeftTo", "LeftTo"),
            ("RightFrom", "RightFrom"),
            ("RightTo", "RightTo"),
            ("MPH", "MPH"),
        ],
    },
}


def log(message):
    print(message)


def get_field_name_lookup(feature_class):
    """Return lowercase->actual field name mapping for a feature class."""
    return {field.name.lower(): field.name for field in arcpy.ListFields(feature_class)}


def has_all_fields(feature_class, required_fields):
    """Check if all required fields exist (case-insensitive)."""
    lookup = get_field_name_lookup(feature_class)
    return all(field_name.lower() in lookup for field_name in required_fields)


def build_compare_fields(schema_name, update_features, base_features):
    """Build compare_fields using actual field casing found in both inputs."""
    update_lookup = get_field_name_lookup(update_features)
    base_lookup = get_field_name_lookup(base_features)

    compare_parts = []
    for update_field, base_field in SCHEMAS[schema_name]["compare_pairs"]:
        update_key = update_field.lower()
        base_key = base_field.lower()

        if update_key in update_lookup and base_key in base_lookup:
            compare_parts.append(f"{update_lookup[update_key]} {base_lookup[base_key]}")

    if not compare_parts:
        raise RuntimeError("No comparable fields were found for Detect Feature Changes.")

    return "; ".join(compare_parts)


def resolve_schema(schema_option, update_features, base_features):
    """Resolve schema to use, with auto-detection by available fields."""
    if schema_option in SCHEMAS:
        required = SCHEMAS[schema_option]["text_fields"] + SCHEMAS[schema_option]["numeric_fields"]
        if has_all_fields(update_features, required) and has_all_fields(base_features, required):
            return schema_option
        raise RuntimeError(
            f"Requested schema '{schema_option}' but required fields are missing in one or both inputs."
        )

    gdb_required = SCHEMAS["gdb"]["text_fields"]
    legacy_required = SCHEMAS["legacy"]["text_fields"]

    if has_all_fields(update_features, gdb_required) and has_all_fields(base_features, gdb_required):
        return "gdb"

    if has_all_fields(update_features, legacy_required) and has_all_fields(base_features, legacy_required):
        return "legacy"

    raise RuntimeError(
        "Could not auto-detect Davis schema. Use --schema legacy or --schema gdb."
    )


def get_output_workspace(update_features):
    """Return the parent geodatabase for an update feature class path."""
    dirname = os.path.dirname(arcpy.Describe(update_features).catalogPath)
    desc = arcpy.Describe(dirname)
    if hasattr(desc, "datasetType") and desc.datasetType == "FeatureDataset":
        dirname = os.path.dirname(dirname)
    return dirname


def ensure_detect_feature_changes_license():
    """Fail early with a clear message if Advanced licensing is not active."""
    product_info = str(arcpy.ProductInfo()).strip()
    product_norm = product_info.lower()

    # ArcGIS Pro typically reports Advanced as ArcInfo.
    if product_norm in {"arcinfo", "advanced"}:
        return

    arcinfo_status = str(arcpy.CheckProduct("ArcInfo")).strip()
    raise RuntimeError(
        "Detect Feature Changes requires an ArcGIS Pro Advanced license. "
        f"Current ProductInfo is '{product_info}' and CheckProduct('ArcInfo') is "
        f"'{arcinfo_status}'. Ask your GIS admin to assign an Advanced seat, "
        "then rerun this script."
    )


def normalize_fields(feature_class, text_fields, numeric_fields):
    """Convert null and blank values to deterministic values before DFC.
    
    Match original behavior: convert single space ' ' and None to empty string for text,
    and space/None to 0 for numeric fields.
    """
    field_names = text_fields + numeric_fields
    with arcpy.da.UpdateCursor(feature_class, field_names) as rows:
        for row in rows:
            updated = False

            for idx in range(len(text_fields)):
                value = row[idx]
                # Match original: check for single space or None
                if value == ' ' or value is None:
                    row[idx] = ""
                    updated = True

            for idx in range(len(text_fields), len(field_names)):
                value = row[idx]
                # Match original: check for single space or None
                if value == ' ' or value is None:
                    row[idx] = 0
                    updated = True

            if updated:
                rows.updateRow(row)


def run_change_detection(
    update_features,
    base_features,
    schema_name,
    schema_description,
    text_fields,
    numeric_fields,
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

    log("begin converting nulls to empty")
    # Use actual field casing from each FC to avoid case-sensitivity issues with UpdateCursor
    for feature_class in [update_features, base_features]:
        lookup = get_field_name_lookup(feature_class)
        actual_text_fields = [lookup[f.lower()] for f in text_fields if f.lower() in lookup]
        actual_numeric_fields = [lookup[f.lower()] for f in numeric_fields if f.lower() in lookup]
        normalize_fields(feature_class, actual_text_fields, actual_numeric_fields)

    log("begin detect feature changes")
    log(f"Using Davis schema: {schema_name} ({schema_description})")
    log(f"compare_fields: {compare_fields}")
    log("Beginning detect feature change process for Davis at: " + time.strftime("%c"))
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
    join_field_dfc = "UPDATE_FID"
    arcpy.management.AddJoin(roads_layer, join_field_roads, dfc_layer, join_field_dfc)

    dfc_name = arcpy.Describe(dfc_output).name
    expression = f"{dfc_name}.CHANGE_TYPE <> 'NC'"
    arcpy.management.SelectLayerByAttribute(roads_layer, "NEW_SELECTION", expression)
    arcpy.management.CopyFeatures(roads_layer, out_feature)

    log("Finished detect feature change process at: " + time.strftime("%c"))
    log("done at: " + time.strftime("%c"))


def parse_args():
    parser = argparse.ArgumentParser(
        description="Detect recent edits between Davis update and baseline roads.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python Get_Davis_Recent_Edits.py --help\n"
            "\n"
            "  python Get_Davis_Recent_Edits.py "
            "--update-features \"<parent>\\utrans-tools\\data\\Davis\\DavisCounty_20251021.gdb\\DavisRoads\" "
            "--base-features \"<parent>\\utrans-tools\\data\\Davis\\DavisCounty_20241216.gdb\\DavisRoads\"\n"
            "\n"
            "  python Get_Davis_Recent_Edits.py "
            "--update-features \"<update fc path>\" "
            "--base-features \"<base fc path>\" "
            "--schema auto "
            "--search-distance \"200 Feet\" "
            "--change-tolerance 40"
        ),
    )
    parser.add_argument(
        "--update-features",
        required=True,
        help="Path to the newest county road feature class.",
    )
    parser.add_argument(
        "--base-features",
        required=True,
        help="Path to the previous county road feature class.",
    )
    parser.add_argument(
        "--schema",
        default="auto",
        choices=["auto", "legacy", "gdb"],
        help="Davis field schema to use. Default auto-detects from input fields.",
    )
    parser.add_argument(
        "--search-distance",
        default="200 Feet",
        help="Search distance for candidate matches in Detect Feature Changes.",
    )
    parser.add_argument(
        "--match-fields",
        default="RoadName RoadName",
        help="Semicolon-delimited field mapping string used for matching.",
    )
    parser.add_argument(
        "--change-tolerance",
        default="40",
        help="Change tolerance distance used by Detect Feature Changes.",
    )
    parser.add_argument(
        "--compare-fields",
        default=None,
        help=(
            "Optional explicit semicolon-delimited field mapping string for compare "
            "attributes. If omitted, fields are chosen from the resolved schema."
        ),
    )
    parser.add_argument(
        "--dfc-output-name",
        default="DFC_DavisToDavis",
        help="Output feature class name for Detect Feature Changes result.",
    )
    parser.add_argument(
        "--stats-table-name",
        default="stats_davis_to_davis",
        help="Output table name for Detect Feature Changes statistics.",
    )
    parser.add_argument(
        "--recents-name",
        default="RoadCenterline_Recents",
        help="Output feature class name for selected changed roads.",
    )
    return parser.parse_args()


def main():
    start_time = time.time()
    args = parse_args()

    try:
        ensure_detect_feature_changes_license()

        schema_name = resolve_schema(args.schema, args.update_features, args.base_features)
        schema = SCHEMAS[schema_name]
        compare_fields = args.compare_fields or build_compare_fields(
            schema_name, args.update_features, args.base_features
        )

        run_change_detection(
            update_features=args.update_features,
            base_features=args.base_features,
            schema_name=schema_name,
            schema_description=schema["description"],
            text_fields=schema["text_fields"],
            numeric_fields=schema["numeric_fields"],
            search_distance=args.search_distance,
            match_fields=args.match_fields,
            change_tolerance=args.change_tolerance,
            compare_fields=compare_fields,
            dfc_output_name=args.dfc_output_name,
            stats_table_name=args.stats_table_name,
            recents_name=args.recents_name,
        )
    except RuntimeError as exc:
        log(str(exc))
        return 2

    elapsed = time.time() - start_time
    log("Time elapsed: {:.2f}s".format(elapsed))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


# utrans-tools\cli\Davis: python Get_Davis_Recent_Edits.py --update-features "Z:\Documents\gdb\DavisCounty_20260626.gdb\DavisRoads" --base-features "Z:\Documents\gdb\DavisCounty_20260604.gdb\DavisRoads" --schema auto --dfc-output-name DFC_DavisToDavis_07_14_26 --stats-table-name stats_davis_to_davis_07_14_26 --recents-name RoadCenterline_Recents_07_14_26

# arcpy.management.FeatureCompare(
#     in_base_features="RoadCenterline_Recents_June_2026",
#     in_test_features="RoadCenterline_Recents_07_14_26",
#     sort_field="NAME",
#     compare_type="ALL",
#     ignore_options=None,
#     xy_tolerance="0.003280833333 Feet",
#     m_tolerance=0.001,
#     z_tolerance=0.001,
#     attribute_tolerances=None,
#     omit_field="OBJECTID;GlobalID;OBJECTID_1;UPDATE_FID;LEN_PCT;LEN_ABS",
#     continue_compare="NO_CONTINUE_COMPARE",
#     out_compare_file=None
# )
