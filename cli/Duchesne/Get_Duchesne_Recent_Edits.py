# Name:        (Cache's script to compare their data with what they sent us last time)
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
#env.workspace = r"D:\UTRANS\Updates\DuchesneCenterlines_16_02_17.gdb" ### change database name ###

#strTimeNow = time.strftime("%c")

# Set local variables
updateFeatures = r"L:\agrc\data\county_obtained\Duchesne\DuchesneCo_20191009.gdb\Centerlines" ### THIS WOULD BE THE NEWEST DATA
baseFeatures = r"L:\agrc\data\county_obtained\Duchesne\DuchesneCo_20190405.gdb\Centerlines" ### THIS IS THE DATA THEY SENT US LAST TIME

dirname = os.path.dirname(arcpy.Describe(updateFeatures).catalogPath)
desc = arcpy.Describe(dirname)
if hasattr(desc, "datasetType") and desc.datasetType=='FeatureDataset':
    dirname = os.path.dirname(dirname)

print "Directory Name: " + str(dirname)
print "Description: " + str(desc)
#dfcOutput = "DFC_RESULT"
#dfcResult = arcpy.Describe(updateFeatures).catalogPath + "\\DFC_RESULT"
#dfcOutput = arcpy.Describe(updateFeatures).catalogPath + "\\DFC_RESULT"
dfcOutput = dirname + "\\DFC_DuchesneToDuchesne"

print "begin converting nulls to emtpy"
# convert nulls to empty in both the update fc and basefeatures fc
list = [updateFeatures, baseFeatures]
for item in list:
    rows = arcpy.UpdateCursor (item)
    for row in rows:
        if row.PREDIR == ' ' or row.PREDIR == None or row.PREDIR is None:
            row.PREDIR = ""
        if row.STREETNAME == ' ' or row.STREETNAME == None or row.STREETNAME is None:
            row.STREETNAME = ""
        if row.STREETTYPE == ' ' or row.STREETTYPE == None or row.STREETTYPE is None:
            row.STREETTYPE = ""
        if row.SUFDIR == ' ' or row.SUFDIR == None or row.SUFDIR is None:
            row.SUFDIR = ""
        if row.ALIAS1 == ' ' or row.ALIAS1 == None or row.ALIAS1 is None:
            row.ALIAS1 = ""
        if row.ALIAS1TYPE == ' ' or row.ALIAS1TYPE == None or row.ALIAS1TYPE is None:
            row.ALIAS1TYPE = ""
        if row.ALIAS2 == ' ' or row.ALIAS2 == None or row.ALIAS2 is None:
            row.ALIAS2 = ""
        if row.ALIAS2TYPE == ' ' or row.ALIAS2TYPE == None or row.ALIAS2TYPE is None:
            row.ALIAS2TYPE = ""
        if row.ACSNAME == ' ' or row.ACSNAME == None or row.ACSNAME is None:
            row.ACSNAME = ""
        if row.ACSSUF == ' ' or row.ACSSUF == None or row.ACSSUF is None:
            row.ACSSUF = ""
        if row.L_F_ADD == ' ' or row.L_F_ADD == None or row.L_F_ADD is None:
            row.L_F_ADD = 0
        if row.L_T_ADD == ' ' or row.L_T_ADD == None or row.L_T_ADD is None:
            row.L_T_ADD = 0
        if row.R_F_ADD == ' ' or row.R_F_ADD == None or row.R_F_ADD is None:
            row.R_F_ADD = 0
        if row.R_T_ADD == ' ' or row.R_T_ADD == None or row.R_T_ADD is None:
            row.R_T_ADD = 0

        rows.updateRow(row)
del row
del rows


print "begin dfc"
#search_distance = "300 Feet" # 300 feet is about 90 meters \ 40 meters = 131.234 feet
search_distance = "200 Feet" # The distance used to search for match candidates. A distance must be specified and it must be greater than zero. You can choose a preferred unit; the default is the feature unit.
#match values
match_fields = "STREETNAME STREETNAME"
#statsTable = arcpy.Describe(updateFeatures).catalogPath + "\\stats_vecc"
statsTable = dirname + "\\stats_cache_to_cache"
print "StatsTable: " + str(statsTable)
print "DFC Layer: " + str(dfcOutput)
print
#statsTable = None

#change_tolerance = "300 Feet"
change_tolerance = "40" # The Change Tolerance serves as the width of a buffer zone around the update features or the base features.  It's the distance used to determine if there is a spatial change. All matched update features and base features are checked against this tolerance. If any portions of update or base features fall outside the zone around the matched feature, it is considered a spatial change.

## compare values
compare_fields = "PREDIR PREDIR; STREETNAME STREETNAME; STREETTYPE STREETTYPE; L_F_ADD L_F_ADD; L_T_ADD L_T_ADD; R_F_ADD R_F_ADD; R_T_ADD R_T_ADD; ALIAS1 ALIAS1; ALIAS1TYPE ALIAS1TYPE; ALIAS2 ALIAS2; ALIAS2TYPE ALIAS2TYPE; ACSNAME ACSNAME; ACSSUF ACSSUF; SUFDIR SUFDIR"

arcpy.AddMessage("Begining detect feature change process for Duchesne at: " + time.strftime("%c"))
#print "begining detect feature change process..."
# Perform spatial change detection
arcpy.DetectFeatureChanges_management(updateFeatures, baseFeatures, dfcOutput, search_distance, match_fields, statsTable, change_tolerance, compare_fields)
print "finished detect feature change process!"


print "begin creating seperate feature class named RoadsCenterlines_Recents"
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
arcpy.AddJoin_management("roads_lyr", joinField_roads, "dfc_lyr", joinField_dfc)

# Select desired features from veg_layer
expression = r"DFC_DuchesneToDuchesne.CHANGE_TYPE <> 'NC'"
layerName = "roads_lyr"
arcpy.SelectLayerByAttribute_management(layerName, "NEW_SELECTION", expression)

# Copy the layer to a new permanent feature class
outFeature = dirname + "\\RoadCenterline_Recents"
arcpy.CopyFeatures_management(layerName, outFeature)

arcpy.AddMessage("Finished detect feature change process at: " + time.strftime("%c"))
print "done at: " + time.strftime("%c")
