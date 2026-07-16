# Name:        (Weber's script to compare their data with what they sent us last time)
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
#env.workspace = r"D:\UTRANS\Updates\WeberCenterlines_16_02_17.gdb" ### change database name ###

#strTimeNow = time.strftime("%c")

# Set local variables
updateFeatures = r"Z:\Documents\gdb\WeberCounty_20260427.gdb\centerline" ### THIS WOULD BE THE NEWEST DATA
baseFeatures = r"Z:\Documents\gdb\WeberCounty_20260330.gdb\Roads" ### THIS IS THE DATA THEY SENT US LAST TIME

dirname = os.path.dirname(arcpy.Describe(updateFeatures).catalogPath)
desc = arcpy.Describe(dirname)
if hasattr(desc, "datasetType") and desc.datasetType == 'FeatureDataset':
    dirname = os.path.dirname(dirname)

print("Directory Name: " + str(dirname))
print("Description: " + str(desc))
#dfcOutput = "DFC_RESULT"
#dfcResult = arcpy.Describe(updateFeatures).catalogPath + "\\DFC_RESULT"
#dfcOutput = arcpy.Describe(updateFeatures).catalogPath + "\\DFC_RESULT"
dfcOutput = dirname + "\\DFC_WeberToWeber_legacy"

print ("begin converting nulls to emtpy")
# convert nulls to empty in both the update fc and basefeatures fc
list = [updateFeatures, baseFeatures]
for item in list:
    rows = arcpy.UpdateCursor(item)
    for row in rows:
        if row.PREDIR == ' ' or row.PREDIR == None or row.PREDIR is None:
            row.PREDIR = ""
        if row.S_NAME == ' ' or row.S_NAME == None or row.S_NAME is None:
            row.S_NAME = ""
        if row.STREETTYPE == ' ' or row.STREETTYPE == None or row.STREETTYPE is None:
            row.STREETTYPE = ""
        if row.SUFDIR == ' ' or row.SUFDIR == None or row.SUFDIR is None:
            row.SUFDIR = ""
        if row.ALIAS == ' ' or row.ALIAS == None or row.ALIAS is None:
            row.ALIAS = ""
        if row.ACS_ALIAS == ' ' or row.ACS_ALIAS == None or row.ACS_ALIAS is None:
            row.ACS_ALIAS = ""
        if row.SUFFIX_911 == ' ' or row.SUFFIX_911 == None or row.SUFFIX_911 is None:
            row.SUFFIX_911 = ""
        if row.LEFTFROM == ' ' or row.LEFTFROM == None or row.LEFTFROM is None:
            row.LEFTFROM = 0
        if row.LEFTTO == ' ' or row.LEFTTO == None or row.LEFTTO is None:
            row.LEFTTO = 0
        if row.RIGHTFROM == ' ' or row.RIGHTFROM == None or row.RIGHTFROM is None:
            row.RIGHTFROM = 0
        if row.RIGHTTO == ' ' or row.RIGHTTO == None or row.RIGHTTO is None:
            row.RIGHTTO = 0

        rows.updateRow(row)
del row
del rows


print ("begin dfc")
#search_distance = "300 Feet" # 300 feet is about 90 meters \ 40 meters = 131.234 feet
search_distance = "200 Feet" # The distance used to search for match candidates. A distance must be specified and it must be greater than zero. You can choose a preferred unit; the default is the feature unit.
#match values
match_fields = "S_NAME S_NAME"
#statsTable = arcpy.Describe(updateFeatures).catalogPath + "\\stats_vecc"
statsTable = dirname + "\\stats_weber_to_weber_legacy"
print("StatsTable: " + str(statsTable))
print("DFC Layer: " + str(dfcOutput))
print()
#statsTable = None

#change_tolerance = "300 Feet"
change_tolerance = "40" # The Change Tolerance serves as the width of a buffer zone around the update features or the base features.  It's the distance used to determine if there is a spatial change. All matched update features and base features are checked against this tolerance. If any portions of update or base features fall outside the zone around the matched feature, it is considered a spatial change.

## compare values
compare_fields = "PREDIR PREDIR; S_NAME S_NAME; STREETTYPE STREETTYPE; SUFDIR SUFDIR; ALIAS ALIAS; ACS_ALIAS ACS_ALIAS; SUFFIX_911 SUFFIX_911; LEFTFROM LEFTFROM; LEFTTO LEFTTO; RIGHTFROM RIGHTFROM; RIGHTTO RIGHTTO"

arcpy.AddMessage("Begining detect feature change process for Weber at: " + time.strftime("%c"))
#print "begining detect feature change process..."
# Perform spatial change detection
arcpy.DetectFeatureChanges_management(updateFeatures, baseFeatures, dfcOutput, search_distance, match_fields, statsTable, change_tolerance, compare_fields)
print ("finished detect feature change process!")


print ("Begin creating seperate feature class named RoadCenterline_Recents_legacy")
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
print ("Begin joining features...")
arcpy.AddJoin_management("roads_lyr", joinField_roads, "dfc_lyr", joinField_dfc)

# Select desired features from veg_layer
dfc_name = arcpy.Describe(dfcOutput).name
expression = "{0}.CHANGE_TYPE <> 'NC'".format(dfc_name)
layerName = "roads_lyr"
arcpy.SelectLayerByAttribute_management(layerName, "NEW_SELECTION", expression)

# Copy the layer to a new permanent feature class
print ("Write features out...")
outFeature = dirname + "\\RoadCenterline_Recents_legacy"
arcpy.CopyFeatures_management(layerName, outFeature)

arcpy.AddMessage("Finished detect feature change process at: " + time.strftime("%c"))
print("done at: " + time.strftime("%c"))
