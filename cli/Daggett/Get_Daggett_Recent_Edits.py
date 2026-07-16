"""Daggett County recent edits detection for ArcGIS Pro (Python 3).

Compares current county roads against a prior delivery using Detect Feature
Changes, then exports changed features into a fixed output feature class.
"""

import argparse
import os
import time

import arcpy


DEFAULT_COMPARE_FIELDS = (
    "PRE_DIR PRE_DIR; S_NAME S_NAME; S_TYPE S_TYPE; L_F_ADD L_F_ADD; "
    "L_T_ADD L_T_ADD; R_F_ADD R_F_ADD; R_T_ADD R_T_ADD; ACS_ALIAS ACS_ALIAS; "
    "SUF_DIR SUF_DIR"
)
TEXT_FIELDS = ["PRE_DIR", "S_NAME", "S_TYPE", "SUF_DIR", "ACS_ALIAS"]
NUMERIC_FIELDS = ["L_F_ADD", "L_T_ADD", "R_F_ADD", "R_T_ADD"]


def log(message):
    print(message)


def get_field_name_map(feature_class):
    """Return case-insensitive -> actual field name mapping for a feature class."""
    return {field.name.lower(): field.name for field in arcpy.ListFields(feature_class)}


def parse_field_pairs(field_mapping):
    """Parse a semicolon-delimited mapping string into field-name pairs."""
    pairs = []
    for token in field_mapping.split(";"):
        parts = token.strip().split()
        if len(parts) >= 2:
            pairs.append((parts[0], parts[1]))
    return pairs


def resolve_field_pairs(update_features, base_features, field_mapping):
    """Keep only mappings where both fields exist and return actual-cased names."""
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

    if product_norm in {"arcinfo", "advanced"}:
        return

    arcinfo_status = str(arcpy.CheckProduct("ArcInfo")).strip()
    raise RuntimeError(
        "Detect Feature Changes requires an ArcGIS Pro Advanced license. "
        f"Current ProductInfo is '{product_info}' and CheckProduct('ArcInfo') is "
        f"'{arcinfo_status}'. Ask your GIS admin to assign an Advanced seat, "
        "then rerun this script."
    )


def normalize_fields(feature_class):
    """Convert legacy null/blank values to deterministic values before DFC."""
    field_map = get_field_name_map(feature_class)
    text_existing = [field_map[name.lower()] for name in TEXT_FIELDS if name.lower() in field_map]
    numeric_existing = [field_map[name.lower()] for name in NUMERIC_FIELDS if name.lower() in field_map]
    field_names = text_existing + numeric_existing

    if not field_names:
        return

    with arcpy.da.UpdateCursor(feature_class, field_names) as rows:
        for row in rows:
            updated = False

            for idx in range(len(text_existing)):
                value = row[idx]
                # Preserve legacy behavior: only NULL or a single-space string.
                if value is None or value == " ":
                    row[idx] = ""
                    updated = True

            for idx in range(len(text_existing), len(field_names)):
                value = row[idx]
                # Preserve legacy behavior: only NULL or a single-space string.
                if value is None or value == " ":
                    row[idx] = 0
                    updated = True

            if updated:
                rows.updateRow(row)


def run_change_detection(
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

    resolved_match_pairs = resolve_field_pairs(update_features, base_features, match_fields)
    if not resolved_match_pairs:
        raise RuntimeError(
            "No valid match field pairs found between update and base feature classes. "
            "Pass --match-fields with fields that exist in both datasets."
        )
    match_fields = "; ".join(["{0} {1}".format(update_field, base_field) for update_field, base_field in resolved_match_pairs])

    resolved_compare_pairs = resolve_field_pairs(update_features, base_features, compare_fields)
    if not resolved_compare_pairs:
        raise RuntimeError(
            "No valid compare field pairs found between update and base feature classes. "
            "Pass --compare-fields with fields that exist in both datasets."
        )
    compare_fields = "; ".join(["{0} {1}".format(update_field, base_field) for update_field, base_field in resolved_compare_pairs])

    log("begin converting nulls to empty")
    for feature_class in [update_features, base_features]:
        normalize_fields(feature_class)

    log("begin detect feature changes")
    log("Beginning detect feature change process for Daggett at: " + time.strftime("%c"))
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
        description="Detect recent edits between Daggett update and baseline roads.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python Get_Daggett_Recent_Edits.py --help\n"
            "\n"
            "  python Get_Daggett_Recent_Edits.py "
            "--update-features \"Z:\\Documents\\gdb\\DAGGETT\\DaggettCoMay31st2017.gdb\\Centerlines_Project\" "
            "--base-features \"Z:\\Documents\\gdb\\DAGGETT\\DaggettJuly15th2016.gdb\\DaggettRoads20\"\n"
            "\n"
            "  python Get_Daggett_Recent_Edits.py "
            "--update-features \"<update fc path>\" "
            "--base-features \"<base fc path>\" "
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
        "--search-distance",
        default="200 Feet",
        help="Search distance for candidate matches in Detect Feature Changes.",
    )
    parser.add_argument(
        "--match-fields",
        default="S_NAME S_NAME",
        help="Semicolon-delimited field mapping string used for matching.",
    )
    parser.add_argument(
        "--change-tolerance",
        default="40",
        help="Change tolerance distance used by Detect Feature Changes.",
    )
    parser.add_argument(
        "--compare-fields",
        default=DEFAULT_COMPARE_FIELDS,
        help="Semicolon-delimited field mapping string used for compare attributes.",
    )
    parser.add_argument(
        "--dfc-output-name",
        default="DFC_DaggettToDaggett",
        help="Output feature class name for Detect Feature Changes result.",
    )
    parser.add_argument(
        "--stats-table-name",
        default="stats_daggett_to_daggett",
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

        run_change_detection(
            update_features=args.update_features,
            base_features=args.base_features,
            search_distance=args.search_distance,
            match_fields=args.match_fields,
            change_tolerance=args.change_tolerance,
            compare_fields=args.compare_fields,
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


# utrans-tools\cli\Daggett: python Get_Daggett_Recent_Edits.py --update-features "Z:\Documents\gdb\DAGGETT\DaggettCoMay31st2017.gdb\DaggettRoads" --base-features "Z:\Documents\gdb\DAGGETT\DaggettJuly15th2016.gdb\DaggettRoads2016" --dfc-output-name DFC_DaggettToDaggett_07_16_26 --stats-table-name stats_daggett_to_daggett_07_16_26 --recents-name RoadCenterline_Recents_07_16_26
