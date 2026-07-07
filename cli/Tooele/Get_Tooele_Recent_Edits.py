# Name:        (TooeleCo's script to compare their data with what they sent us last time)
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
#env.workspace = r"D:\UTRANS\Updates\SummitCenterlines_16_02_17.gdb" ### change database name ###

#strTimeNow = time.strftime("%c")

# Set local variables
updateFeatures = r"L:\agrc\data\county_obtained\Tooele\TooeleCo_20260514.gdb\TCRoads" ### THIS WOULD BE THE NEWEST DATA
baseFeatures = r"L:\agrc\data\county_obtained\Tooele\TooeleCo_20251117.gdb\TCRoads" ### THIS IS THE DATA THEY SENT US LAST TIME

dirname = os.path.dirname(arcpy.Describe(updateFeatures).catalogPath)
desc = arcpy.Describe(dirname)
if hasattr(desc, "datasetType") and desc.datasetType=='FeatureDataset':
    dirname = os.path.dirname(dirname)

dfcOutput = dirname + "\\DFC_TooeleToTooele"

print ("begin converting nulls to emtpy")
# convert nulls to empty in both the update fc and basefeatures fc
list = [updateFeatures, baseFeatures]
for item in list:
    rows = arcpy.UpdateCursor (item)
    for row in rows:
        if row.FROMADDR_L == None or row.FROMADDR_L is None:
            row.FROMADDR_L = 0
        if row.TOADDR_L == None or row.TOADDR_L is None:
            row.TOADDR_L = 0
        if row.FROMADDR_R == None or row.FROMADDR_R is None:
            row.FROMADDR_R = 0
        if row.TOADDR_R == None or row.TOADDR_R is None:
            row.TOADDR_R = 0
        if row.FULLNAME == ' ' or row.FULLNAME == None or row.FULLNAME is None:
            row.FULLNAME = ""
        else:
            row.FULLNAME = row.FULLNAME.upper().strip()
        if row.PREDIR == None or row.PREDIR is None:
            row.PREDIR = ""
        if row.A1_NAME == ' ' or row.A1_NAME == None or row.A1_NAME is None:
            row.A1_NAME = ""
        else:
            row.A1_NAME = row.A1_NAME.upper().strip()
        if row.A2_NAME == ' ' or row.A2_NAME == None or row.A2_NAME is None:
            row.A2_NAME = ""
        else:
            row.A2_NAME = row.A2_NAME.upper().strip()
        if row.AN_NAME == None or row.AN_NAME is None:
            row.AN_NAME = ""
        if row.STATUS == ' ' or row.STATUS == None or row.STATUS is None:
            row.STATUS = ""
        rows.updateRow(row)
del row
del rows

print ("begin dfc")
#search_distance = "300 Feet" # 300 feet is about 90 meters \ 40 meters = 131.234 feet
search_distance = "200 Feet" # The distance used to search for match candidates. A distance must be specified and it must be greater than zero. You can choose a preferred unit; the default is the feature unit.
#match values
match_fields = "FULLNAME FULLNAME"
statsTable = arcpy.Describe(updateFeatures).catalogPath + "\\new_roads_stats_tooele"
#change_tolerance = "300 Feet"
change_tolerance = "40" # The Change Tolerance serves as the width of a buffer zone around the update features or the base features.  It's the distance used to determine if there is a spatial change. All matched update features and base features are checked against this tolerance. If any portions of update or base features fall outside the zone around the matched feature, it is considered a spatial change.

## compare values
compare_fields = "FROMADDR_L FROMADDR_L; TOADDR_L TOADDR_L; FROMADDR_R FROMADDR_R; TOADDR_R TOADDR_R; FULLNAME FULLNAME; PREDIR PREDIR; A1_NAME A1_NAME; A2_NAME A2_NAME; AN_NAME AN_NAME; STATUS STATUS"
#compare_fields = "FromLeft FromLeft; ToLeft ToLeft; FromRight FromRight; ToRight ToRight; SP_Street SP_Street; SP_Alias_1 SP_Alias_1; SP_Alias_2 SP_Alias_2"
#compare_fields = "FromLeft FromLeft; ToLeft ToLeft; FromRight FromRight; ToRight ToRight; SP_Street SP_Street; SP_Alias_1 SP_Alias_1; SP_Alias_2 SP_Alias_2; CONSTRUCTI CONSTRUCTI"

arcpy.AddMessage("Begining detect feature change process for TooeleCo at: " + time.strftime("%c"))
#print "begining detect feature change process..."
# Perform spatial change detection
arcpy.DetectFeatureChanges_management(updateFeatures, baseFeatures, dfcOutput, search_distance, match_fields, statsTable, change_tolerance, compare_fields)
print ("finished detect feature change process!")

print ("begin creating seperate feature class named RoadsCenterlines_Recents")
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
expression = r"DFC_TooeleToTooele.CHANGE_TYPE <> 'NC'"
layerName = "roads_lyr"
arcpy.SelectLayerByAttribute_management(layerName, "NEW_SELECTION", expression)

# Copy the layer to a new permanent feature class
outFeature = dirname + "\\RoadCenterline_Recents"
arcpy.CopyFeatures_management(layerName, outFeature)

arcpy.AddMessage("Finished detect feature change process at: " + time.strftime("%c"))
print ("done at: ") + time.strftime("%c")