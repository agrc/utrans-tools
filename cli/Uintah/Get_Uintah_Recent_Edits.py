# Name:        (Uintah's script to compare their data with what they sent us last time)
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

#strTimeNow = time.strftime("%c")

# Set local variables
updateFeatures = r"L:\agrc\data\county_obtained\Uintah\UintahCountyAddressRoads_20260512\UintahCountyAddressRoads.shp" ### THIS WOULD BE THE NEWEST DATA
# baseFeatures = r"L:\agrc\data\county_obtained\Uintah\UintahCo20260423.gdb\Roads" ### THIS IS THE DATA THEY SENT US LAST TIME
baseFeatures = r"L:\agrc\data\county_obtained\Uintah\UintaCo_20190921.gdb\RoadAddress" ### THIS IS THE DATA THEY SENT US LAST TIME

dirname = os.path.dirname(arcpy.Describe(updateFeatures).catalogPath)
desc = arcpy.Describe(dirname)
if hasattr(desc, "datasetType") and desc.datasetType=='FeatureDataset':
    dirname = os.path.dirname(dirname)

print("Directory Name: " + str(dirname))
print("Description: " + str(desc))
#dfcOutput = "DFC_RESULT"
#dfcResult = arcpy.Describe(updateFeatures).catalogPath + "\\DFC_RESULT"
#dfcOutput = arcpy.Describe(updateFeatures).catalogPath + "\\DFC_RESULT"
dfcOutput = dirname + "\\DFC_UintahToUintah"

print("begin converting nulls to emtpy")
# convert nulls to empty in both the update fc and basefeatures fc
list = [updateFeatures, baseFeatures]
for item in list:
    rows = arcpy.UpdateCursor (item)
    for row in rows:
        if row.toleft == None or row.toleft is None:
            row.toleft = 0
        if row.toright == None or row.toright is None:
            row.toright = 0
        if row.fromleft == None or row.fromleft is None:
            row.fromleft = 0
        if row.fromright == None or row.fromright is None:
            row.fromright = 0
        if row.S_NAME == ' ' or row.S_NAME == None or row.S_NAME is None:
            row.S_NAME = ""
        else:
            row.S_NAME = row.S_NAME.upper().strip()
        if row.ALIAS1 == ' ' or row.ALIAS1 == None or row.ALIAS1 is None:
            row.ALIAS1 = ""
        else:
            row.ALIAS1 = row.ALIAS1.upper().strip()
        rows.updateRow(row)
del row
del rows


print("begin dfc")
#search_distance = "300 Feet" # 300 feet is about 90 meters \ 40 meters = 131.234 feet
search_distance = "200 Feet" # The distance used to search for match candidates. A distance must be specified and it must be greater than zero. You can choose a preferred unit; the default is the feature unit.
#match values
match_fields = "S_NAME S_NAME"
#statsTable = arcpy.Describe(updateFeatures).catalogPath + "\\stats_vecc"
statsTable = dirname + "\\stats_uintah_to_uintah"
print("StatsTable: " + str(statsTable))
print("DFC Layer: " + str(dfcOutput))

#statsTable = None

#change_tolerance = "300 Feet"
change_tolerance = "40" # The Change Tolerance serves as the width of a buffer zone around the update features or the base features.  It's the distance used to determine if there is a spatial change. All matched update features and base features are checked against this tolerance. If any portions of update or base features fall outside the zone around the matched feature, it is considered a spatial change.

## compare values (think about testing for STATUS once a year to add anything is now marked as active)
compare_fields = "toleft toleft; toright toright; fromleft fromleft; fromright fromright; S_NAME S_NAME; ALIAS1 ALIAS1"


arcpy.AddMessage("Begining detect feature change process for Uintah at: " + time.strftime("%c"))
#print("begining detect feature change process..."
# Perform spatial change detection
arcpy.DetectFeatureChanges_management(updateFeatures, baseFeatures, dfcOutput, search_distance, match_fields, statsTable, change_tolerance, compare_fields)
print("finished detect feature change process!")


print("begin creating seperate feature class named RoadsCenterlines_Recents")
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
print("Begin joining features...")
arcpy.AddJoin_management("roads_lyr", joinField_roads, "dfc_lyr", joinField_dfc)

# Select desired features from veg_layer
# expression = r"DFC_UintahToUintah.CHANGE_TYPE <> 'NC'"
expression = r"DFC_UintahToUintah.CHANGE_TYP <> 'NC'"  # for a shapefile, due to truncated field name
layerName = "roads_lyr"
print("Perform selection from joined tables...")
arcpy.SelectLayerByAttribute_management(layerName, "NEW_SELECTION", expression)

# Copy the layer to a new permanent feature class
outFeature = dirname + "\\RoadCenterline_Recents"
print("Write features out...")
arcpy.CopyFeatures_management(layerName, outFeature)

arcpy.AddMessage("Finished detect feature change process at: " + time.strftime("%c"))
print("done at: " + time.strftime("%c"))
