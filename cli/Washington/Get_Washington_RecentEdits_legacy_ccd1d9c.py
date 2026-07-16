# Name:        (Washington's script to compare their data with what they sent us last time)
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
#env.workspace = r"D:\UTRANS\Updates\WashingtonCenterlines_16_02_17.gdb" ### change database name ###

#strTimeNow = time.strftime("%c")

# Set local variables
updateFeatures = r"Z:\Documents\gdb\Washington20260624.gdb\WashCo_RoadCenterlines" ### THIS WOULD BE THE NEWEST DATA
baseFeatures = r"Z:\Documents\gdb\Washington20260521.gdb\WashCo_RoadCenterlines" ### THIS IS THE DATA THEY SENT US LAST TIME


dirname = os.path.dirname(arcpy.Describe(updateFeatures).catalogPath)
desc = arcpy.Describe(dirname)
if hasattr(desc, "datasetType") and desc.datasetType == 'FeatureDataset':
    dirname = os.path.dirname(dirname)

print("Directory Name: " + str(dirname))
print("Description: " + str(desc))
#dfcOutput = "DFC_RESULT"
#dfcResult = arcpy.Describe(updateFeatures).catalogPath + "\\DFC_RESULT"
#dfcOutput = arcpy.Describe(updateFeatures).catalogPath + "\\DFC_RESULT"
dfcOutput = dirname + "\\DFC_WashToWash_legacy"
outFeature = dirname + "\\RoadCenterline_Recents_legacy"

print("begin converting nulls to empty")
# convert nulls to empty in both the update fc and basefeatures fc
list = [updateFeatures, baseFeatures]
for item in list:
    rows = arcpy.UpdateCursor(item)
    for row in rows:
        if row.FROMADDR_L == ' ' or row.FROMADDR_L == None or row.FROMADDR_L is None:
            row.FROMADDR_L = 0
        if row.TOADDR_L == ' ' or row.TOADDR_L == None or row.TOADDR_L is None:
            row.TOADDR_L = 0
        if row.FROMADDR_R == ' ' or row.FROMADDR_R == None or row.FROMADDR_R is None:
            row.FROMADDR_R = 0
        if row.TOADDR_R == ' ' or row.TOADDR_R == None or row.TOADDR_R is None:
            row.TOADDR_R = 0
        if row.PREDIR == ' ' or row.PREDIR == None or row.PREDIR is None:
            row.PREDIR = ""
        if row.NAME == ' ' or row.NAME == None or row.NAME is None:
            row.NAME = ""
        if row.POSTTYPE == ' ' or row.POSTTYPE == None or row.POSTTYPE is None:
            row.POSTTYPE = ""
        if row.SUFFIXDIR == ' ' or row.SUFFIXDIR == None or row.SUFFIXDIR is None:
            row.SUFFIXDIR = ""
        if row.POSTDIR == ' ' or row.POSTDIR == None or row.POSTDIR is None:
            row.POSTDIR = ""
        if row.AN_NAME == ' ' or row.AN_NAME == None or row.AN_NAME is None:
            row.AN_NAME = ""
        if row.AN_POSTDIR == ' ' or row.AN_POSTDIR == None or row.AN_POSTDIR is None:
            row.AN_POSTDIR = ""
        if row.A1_NAME == ' ' or row.A1_NAME == None or row.A1_NAME is None:
            row.A1_NAME = ""
        if row.A1_POSTTYPE == ' ' or row.A1_POSTTYPE == None or row.A1_POSTTYPE is None:
            row.A1_POSTTYPE = ""
        if row.A2_NAME == ' ' or row.A2_NAME == None or row.A2_NAME is None:
            row.A2_NAME = ""
        if row.A2_POSTTYPE == ' ' or row.A2_POSTTYPE == None or row.A2_POSTTYPE is None:
            row.A2_POSTTYPE = ""
        rows.updateRow(row)
del row
del rows


print("begin dfc")
#search_distance = "300 Feet" # 300 feet is about 90 meters \ 40 meters = 131.234 feet
search_distance = "200 Feet" # The distance used to search for match candidates. A distance must be specified and it must be greater than zero. You can choose a preferred unit; the default is the feature unit.
#match values
match_fields = "NAME NAME"  # This is actually the StreetName  ### Must be changed prior to update.
#statsTable = arcpy.Describe(updateFeatures).catalogPath + "\\stats_vecc"
statsTable = dirname + "\\stats_Wash_to_Wash_legacy"
print("StatsTable: " + str(statsTable))
print("DFC Layer: " + str(dfcOutput))
print()
#statsTable = None

#change_tolerance = "300 Feet"
change_tolerance = "40" # The Change Tolerance serves as the width of a buffer zone around the update features or the base features.  It's the distance used to determine if there is a spatial change. All matched update features and base features are checked against this tolerance. If any portions of update or base features fall outside the zone around the matched feature, it is considered a spatial change.

## compare values
compare_fields = "FROMADDR_L FROMADDR_L; TOADDR_L TOADDR_L; FROMADDR_R FROMADDR_R; TOADDR_R TOADDR_R; PREDIR PREDIR; NAME NAME; POSTTYPE POSTTYPE; POSTDIR POSTDIR; SUFFIXDIR SUFFIXDIR; AN_NAME AN_NAME; AN_POSTDIR AN_POSTDIR; A1_NAME A1_NAME; A1_POSTTYPE A1_POSTTYPE; A2_NAME A2_NAME; A2_POSTTYPE A2_POSTTYPE"

arcpy.AddMessage("Begining detect feature change process for Washington at: " + time.strftime("%c"))
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
