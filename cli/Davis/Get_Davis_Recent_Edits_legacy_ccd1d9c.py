# Name:        (Davis's script to compare their data with what they sent us last time)
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
# Set environment settings
env.overwriteOutput = True
#env.workspace = r"D:\UTRANS\Updates\DavisCenterlines_16_02_17.gdb" ### change database name ###

#strTimeNow = time.strftime("%c")

# Set local variables
updateFeatures = r"Z:\Documents\gdb\DavisCounty_20260626.gdb\DavisRoads" ### THIS WOULD BE THE NEWEST DATA
baseFeatures = r"Z:\Documents\gdb\DavisCounty_20260604.gdb\DavisRoads" ### THIS IS THE DATA THEY SENT US LAST TIME


def _field_map(feature_class):
    return dict((field.name.lower(), field.name) for field in arcpy.ListFields(feature_class))


def _resolve_field(feature_class, candidates):
    fields = _field_map(feature_class)
    for candidate in candidates:
        actual = fields.get(candidate.lower())
        if actual:
            return actual
    return None

dirname = os.path.dirname(arcpy.Describe(updateFeatures).catalogPath)
desc = arcpy.Describe(dirname)
if hasattr(desc, "datasetType") and desc.datasetType=='FeatureDataset':
    dirname = os.path.dirname(dirname)

print ("Directory Name: " + str(dirname))
print ("Description: " + str(desc))
#dfcOutput = "DFC_RESULT"
#dfcResult = arcpy.Describe(updateFeatures).catalogPath + "\\DFC_RESULT"
#dfcOutput = arcpy.Describe(updateFeatures).catalogPath + "\\DFC_RESULT"
dfcOutput = dirname + "\\DFC_DavisToDavis_legacy"

print ("begin converting nulls to empty")
# convert nulls to empty in both the update fc and basefeatures fc
list = [updateFeatures, baseFeatures]

text_candidates = [
    ["PrefixDire", "PrefixDirection"],
    ["RoadName"],
    ["RoadNameTy", "RoadNameType"],
    ["PostDirect", "PostDirection"],
    ["RoadAliasN", "RoadAliasName"],
]
numeric_candidates = [["LeftFrom"], ["LeftTo"], ["RightFrom"], ["RightTo"]]

for item in list:
    text_fields = [field for field in [_resolve_field(item, c) for c in text_candidates] if field]
    numeric_fields = [field for field in [_resolve_field(item, c) for c in numeric_candidates] if field]

    rows = arcpy.UpdateCursor (item)
    for row in rows:
        for field_name in text_fields:
            value = getattr(row, field_name)
            if value == ' ' or value == None or value is None:
                setattr(row, field_name, "")

        for field_name in numeric_fields:
            value = getattr(row, field_name)
            if value == ' ' or value == None or value is None:
                setattr(row, field_name, 0)

        rows.updateRow(row)
del row
del rows


print ("begin dfc")
#search_distance = "300 Feet" # 300 feet is about 90 meters \ 40 meters = 131.234 feet
search_distance = "200 Feet" # The distance used to search for match candidates. A distance must be specified and it must be greater than zero. You can choose a preferred unit; the default is the feature unit.
#match values
match_fields = "RoadName RoadName"
#statsTable = arcpy.Describe(updateFeatures).catalogPath + "\\stats_vecc"
statsTable = dirname + "\\stats_davis_to_davis_legacy"
print ("StatsTable: " + str(statsTable))
print ("DFC Layer: " + str(dfcOutput))
print()
#statsTable = None

#change_tolerance = "300 Feet"
change_tolerance = "40" # The Change Tolerance serves as the width of a buffer zone around the update features or the base features.  It's the distance used to determine if there is a spatial change. All matched update features and base features are checked against this tolerance. If any portions of update or base features fall outside the zone around the matched feature, it is considered a spatial change.

## compare values
update_compare_fields = [
    _resolve_field(updateFeatures, ["PrefixDire", "PrefixDirection"]),
    _resolve_field(updateFeatures, ["RoadName"]),
    _resolve_field(updateFeatures, ["RoadNameTy", "RoadNameType"]),
    _resolve_field(updateFeatures, ["PostDirect", "PostDirection"]),
    _resolve_field(updateFeatures, ["RoadAliasN", "RoadAliasName"]),
    _resolve_field(updateFeatures, ["LeftFrom"]),
    _resolve_field(updateFeatures, ["LeftTo"]),
    _resolve_field(updateFeatures, ["RightFrom"]),
    _resolve_field(updateFeatures, ["RightTo"]),
]
base_compare_fields = [
    _resolve_field(baseFeatures, ["PrefixDire", "PrefixDirection"]),
    _resolve_field(baseFeatures, ["RoadName"]),
    _resolve_field(baseFeatures, ["RoadNameTy", "RoadNameType"]),
    _resolve_field(baseFeatures, ["PostDirect", "PostDirection"]),
    _resolve_field(baseFeatures, ["RoadAliasN", "RoadAliasName"]),
    _resolve_field(baseFeatures, ["LeftFrom"]),
    _resolve_field(baseFeatures, ["LeftTo"]),
    _resolve_field(baseFeatures, ["RightFrom"]),
    _resolve_field(baseFeatures, ["RightTo"]),
]

compare_pairs = []
for update_field, base_field in zip(update_compare_fields, base_compare_fields):
    if update_field and base_field:
        compare_pairs.append("{0} {1}".format(update_field, base_field))

compare_fields = "; ".join(compare_pairs)

update_match_field = _resolve_field(updateFeatures, ["RoadName"])
base_match_field = _resolve_field(baseFeatures, ["RoadName"])
if update_match_field and base_match_field:
    match_fields = "{0} {1}".format(update_match_field, base_match_field)

arcpy.AddMessage("Begining detect feature change process for Davis at: " + time.strftime("%c"))
#print "begining detect feature change process..."
# Perform spatial change detection
arcpy.DetectFeatureChanges_management(updateFeatures, baseFeatures, dfcOutput, search_distance, match_fields, statsTable, change_tolerance, compare_fields)
print ("finished detect feature change process!")


print ("begin creating seperate feature class named RoadCenterline_Recents_legacy")
# join the dfc output to the newest county data to see what changes have been made
arcpy.env.qualifiedFieldNames = False

# Set local variables
# Make a layer from the feature class
arcpy.MakeFeatureLayer_management(updateFeatures,"roads_lyr")

# Make a layer from the feature class
arcpy.MakeFeatureLayer_management(dfcOutput,"dfc_lyr")

#joinField_roads = "OBJECTID"
joinField_roads = arcpy.Describe("roads_lyr").OIDFieldName
joinField_dfc = "UPDATE_FID"

# Join the feature layer to a table
print ("Begin joining tables...")
arcpy.AddJoin_management("roads_lyr", joinField_roads, "dfc_lyr", joinField_dfc)

# Select desired features from veg_layer
dfc_name = arcpy.Describe(dfcOutput).name
expression = "{0}.CHANGE_TYPE <> 'NC'".format(dfc_name)
layerName = "roads_lyr"
print ("Perform selection...")
arcpy.SelectLayerByAttribute_management(layerName, "NEW_SELECTION", expression)

# Copy the layer to a new permanent feature class
outFeature = dirname + "\\RoadCenterline_Recents_legacy"
print ("Write features out...")
arcpy.CopyFeatures_management(layerName, outFeature)

arcpy.AddMessage("Finished detect feature change process at: " + time.strftime("%c"))
print ("done at: " + time.strftime("%c"))
