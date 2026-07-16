"""Washington County recent edits detection for ArcGIS Pro (Python 3).

Compares current county roads against a prior delivery using Detect Feature
Changes, then exports changed features into a fixed output feature class.
"""

import argparse
import os
import time

import arcpy


DEFAULT_COMPARE_FIELDS = (
    "FROMADDR_L FROMADDR_L; TOADDR_L TOADDR_L; FROMADDR_R FROMADDR_R; "
    "TOADDR_R TOADDR_R; PREDIR PREDIR; NAME NAME; POSTTYPE POSTTYPE; "
    "POSTDIR POSTDIR; SUFFIXDIR SUFFIXDIR; AN_NAME AN_NAME; "
    "AN_POSTDIR AN_POSTDIR; A1_NAME A1_NAME; A1_POSTTYPE A1_POSTTYPE; "
    "A2_NAME A2_NAME; A2_POSTTYPE A2_POSTTYPE"
)
TEXT_FIELDS = [
    "PREDIR",
    "NAME",
    "POSTTYPE",
    "SUFFIXDIR",
    "POSTDIR",
    "AN_NAME",
    "AN_POSTDIR",
    "A1_NAME",
    "A1_POSTTYPE",
    "A2_NAME",
    "A2_POSTTYPE",
]
NUMERIC_FIELDS = ["FROMADDR_L", "TOADDR_L", "FROMADDR_R", "TOADDR_R"]


def log(message):
    print(message)


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
    field_names = TEXT_FIELDS + NUMERIC_FIELDS
    with arcpy.da.UpdateCursor(feature_class, field_names) as rows:
        for row in rows:
            updated = False

            for idx in range(len(TEXT_FIELDS)):
                value = row[idx]
                # Preserve legacy behavior: only NULL or a single-space string.
                if value is None or value == " ":
                    row[idx] = ""
                    updated = True

            for idx in range(len(TEXT_FIELDS), len(field_names)):
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

    log("begin converting nulls to empty")
    for feature_class in [update_features, base_features]:
        normalize_fields(feature_class)

    log("begin detect feature changes")
    log("Beginning detect feature change process for Washington at: " + time.strftime("%c"))
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
        description="Detect recent edits between Washington update and baseline roads.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python Get_Washington_Recent_Edits.py --help\n"
            "\n"
            "  python Get_Washington_Recent_Edits.py "
            "--update-features \"Z:\\Documents\\gdb\\Washington20260624.gdb\\WashCo_RoadCenterlines\" "
            "--base-features \"Z:\\Documents\\gdb\\Washington20260521.gdb\\WashCo_RoadCenterlines\"\n"
            "\n"
            "  python Get_Washington_Recent_Edits.py "
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
        default="NAME NAME",
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
        default="DFC_WashToWash",
        help="Output feature class name for Detect Feature Changes result.",
    )
    parser.add_argument(
        "--stats-table-name",
        default="stats_Wash_to_Wash",
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


# utrans-tools\cli\Washington: python Get_Washington_Recent_Edits.py --update-features "Z:\Documents\gdb\Washington20260624.gdb\WashCo_RoadCenterlines" --base-features "Z:\Documents\gdb\Washington20260521.gdb\WashCo_RoadCenterlines" --dfc-output-name DFC_WashToWash_07_15_26 --stats-table-name stats_Wash_to_Wash_07_15_26 --recents-name RoadCenterline_Recents_07_15_26
