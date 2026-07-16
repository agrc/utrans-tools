# Name:        (Garfield's script to compare their data with what they sent us last time)
# Description: Perform change detection between newly received road data and
#              existing road data and find the number of new roads and the
#              total length of them.
# Author:      gbunce
# -----------------------------------------------------------------------

# NOTE
### three ### pound signs indicates that the user needs to change a variable before running this code

# Import system modules
import os
import arcpy
from arcpy import env
import time

TEXT_FIELDS = ["NAME", "PREDIR", "POSTDIR", "POSTTYPE", "AN_NAME", "A1_NAME", "A2_NAME"]
NUMERIC_FIELDS = ["FROMADDR_L", "TOADDR_L", "FROMADDR_R", "TOADDR_R"]


def get_field_name_map(feature_class):
    """Return case-insensitive -> actual field name mapping for a feature class."""
    return dict((field.name.lower(), field.name) for field in arcpy.ListFields(feature_class))


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


# Set environment settings
env.overwriteOutput = True
#env.workspace = r"D:\UTRANS\Updates\GarfieldCenterlines_16_02_17.gdb" ### change database name ###

#strTimeNow = time.strftime("%c")

# Set local variables
updateFeatures = r"Z:\Documents\gdb\GARFIELD\Garfield20260427.gdb\Garfield_Streets_Roads"  ### THIS WOULD BE THE NEWEST DATA
baseFeatures = r"Z:\Documents\gdb\GARFIELD\Garfield20250908.gdb\Garfield_Streets_Roads"  ### THIS IS THE DATA THEY SENT US LAST TIME

dirname = os.path.dirname(arcpy.Describe(updateFeatures).catalogPath)
desc = arcpy.Describe(dirname)
if hasattr(desc, "datasetType") and desc.datasetType == 'FeatureDataset':
    dirname = os.path.dirname(dirname)

print("Directory Name: " + str(dirname))
print("Description: " + str(desc))
#dfcOutput = "DFC_RESULT"
#dfcResult = arcpy.Describe(updateFeatures).catalogPath + "\\DFC_RESULT"
#dfcOutput = arcpy.Describe(updateFeatures).catalogPath + "\\DFC_RESULT"
dfcOutput = dirname + "\\DFC_GarfieldToGarfield_legacy"
outFeature = dirname + "\\RoadCenterline_Recents_legacy"

print("begin converting nulls to empty")
# convert nulls to empty in both the update fc and basefeatures fc
list = [updateFeatures, baseFeatures]
for item in list:
    field_map = get_field_name_map(item)
    text_existing = [field_map[name.lower()] for name in TEXT_FIELDS if name.lower() in field_map]
    numeric_existing = [field_map[name.lower()] for name in NUMERIC_FIELDS if name.lower() in field_map]

    rows = arcpy.UpdateCursor(item)
    for row in rows:
        for field_name in text_existing:
            value = getattr(row, field_name)
            if value == ' ' or value == None or value is None:
                setattr(row, field_name, "")

        for field_name in numeric_existing:
            value = getattr(row, field_name)
            if value == ' ' or value == None or value is None:
                setattr(row, field_name, 0)

        rows.updateRow(row)
del row
del rows


print("begin dfc")
#search_distance = "300 Feet" # 300 feet is about 90 meters \ 40 meters = 131.234 feet
search_distance = "200 Feet" # The distance used to search for match candidates. A distance must be specified and it must be greater than zero. You can choose a preferred unit; the default is the feature unit.
#match values
match_fields = "NAME NAME"
#statsTable = arcpy.Describe(updateFeatures).catalogPath + "\\stats_vecc"
statsTable = dirname + "\\stats_Garfield_to_Garfield_legacy"
print("StatsTable: " + str(statsTable))
print("DFC Layer: " + str(dfcOutput))
print()
#statsTable = None

#change_tolerance = "300 Feet"
change_tolerance = "40" # The Change Tolerance serves as the width of a buffer zone around the update features or the base features.  It's the distance used to determine if there is a spatial change. All matched update features and base features are checked against this tolerance. If any portions of update or base features fall outside the zone around the matched feature, it is considered a spatial change.

## compare values
compare_fields = "FROMADDR_L FROMADDR_L; TOADDR_L TOADDR_L; FROMADDR_R FROMADDR_R; TOADDR_R TOADDR_R; NAME NAME; PREDIR PREDIR; POSTDIR POSTDIR; POSTTYPE POSTTYPE; AN_NAME AN_NAME; A1_NAME A1_NAME; A2_NAME A2_NAME"

resolved_match_pairs = resolve_field_pairs(updateFeatures, baseFeatures, match_fields)
if not resolved_match_pairs:
    raise RuntimeError(
        "No valid match field pairs found between update and base feature classes. "
        "Edit match_fields to use fields that exist in both datasets."
    )
match_fields = "; ".join(["{0} {1}".format(update_field, base_field) for update_field, base_field in resolved_match_pairs])

resolved_compare_pairs = resolve_field_pairs(updateFeatures, baseFeatures, compare_fields)
if not resolved_compare_pairs:
    raise RuntimeError(
        "No valid compare field pairs found between update and base feature classes. "
        "Edit compare_fields to use fields that exist in both datasets."
    )
compare_fields = "; ".join(["{0} {1}".format(update_field, base_field) for update_field, base_field in resolved_compare_pairs])

arcpy.AddMessage("Begining detect feature change process for Garfield at: " + time.strftime("%c"))
#print "begining detect feature change process..."
# Clean up prior legacy outputs so repeat runs do not fail on name collisions.
if arcpy.Exists(dfcOutput):
    arcpy.Delete_management(dfcOutput)
if arcpy.Exists(statsTable):
    arcpy.Delete_management(statsTable)

# Perform spatial change detection
arcpy.DetectFeatureChanges_management(updateFeatures, baseFeatures, dfcOutput, search_distance, match_fields, statsTable, change_tolerance, compare_fields)
print("finished detect feature change process!")


print("begin creating seperate feature class named RoadCenterline_Recents_legacy")
# join the dfc output to the newest county data to see what changes have been made
arcpy.env.qualifiedFieldNames = False

# Set local variables
# Make a layer from the feature class
arcpy.MakeFeatureLayer_management(updateFeatures, "roads_lyr")

# Make a layer from the feature class
arcpy.MakeFeatureLayer_management(dfcOutput, "dfc_lyr")

#joinField_roads = "OBJECTID"
joinField_roads = arcpy.Describe("roads_lyr").OIDFieldName
joinField_dfc = "UPDATE_FID"

# Join the feature layer to a table
arcpy.AddJoin_management("roads_lyr", joinField_roads, "dfc_lyr", joinField_dfc)

# Select desired features from veg_layer
dfc_name = arcpy.Describe(dfcOutput).name
expression = "{0}.CHANGE_TYPE <> 'NC'".format(dfc_name)
layerName = "roads_lyr"
arcpy.SelectLayerByAttribute_management(layerName, "NEW_SELECTION", expression)

# Copy the layer to a new permanent feature class
if arcpy.Exists(outFeature):
    arcpy.Delete_management(outFeature)
arcpy.CopyFeatures_management(layerName, outFeature)

arcpy.AddMessage("Finished detect feature change process at: " + time.strftime("%c"))
print("done at: " + time.strftime("%c"))
