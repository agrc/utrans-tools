# Name:        (DaggettCo's script to compare their data with what they sent us last time)
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
updateFeatures = r"K:\AGRC Projects\UtransEditing\Data\Daggett\DaggettCoMay31st2017\DaggettCoMay31st2017.gdb\DaggettRoads" ### THIS WOULD BE THE NEWEST DATA
baseFeatures = r"K:\AGRC Projects\UtransEditing\Data\Daggett\DaggettJuly15th2016.gdb\DaggettRoads" ### THIS IS THE DATA THEY SENT US LAST TIME

dirname = os.path.dirname(arcpy.Describe(updateFeatures).catalogPath)
desc = arcpy.Describe(dirname)
if hasattr(desc, "datasetType") and desc.datasetType=='FeatureDataset':
    dirname = os.path.dirname(dirname)

#dfcOutput = "DFC_RESULT"
#dfcResult = arcpy.Describe(updateFeatures).catalogPath + "\\DFC_RESULT"
#dfcOutput = arcpy.Describe(updateFeatures).catalogPath + "\\DFC_RESULT"
dfcOutput = dirname + "\\DFC_DaggettToDaggett"

print "begin converting nulls to emtpy"
# convert nulls to empty in both the update fc and basefeatures fc
list = [updateFeatures, baseFeatures]
for item in list:
    rows = arcpy.UpdateCursor (item)
    for row in rows:
        if row.PRE_DIR == ' ' or row.PRE_DIR == None or row.PRE_DIR is None:
            row.PRE_DIR = ""
        if row.S_NAME == ' ' or row.S_NAME == None or row.S_NAME is None:
            row.S_NAME = ""
        if row.S_TYPE == ' ' or row.S_TYPE == None or row.S_TYPE is None:
            row.S_TYPE = ""
        if row.ALT_NAME == ' ' or row.ALT_NAME == None or row.ALT_NAME is None:
            row.ALT_NAME = ""
        if row.SUF_DIR == ' ' or row.SUF_DIR == None or row.SUF_DIR is None:
            row.SUF_DIR = ""
        if row.ACS_ALIAS == ' ' or row.ACS_ALIAS == None or row.ACS_ALIAS is None:
            row.ACS_ALIAS = ""

        rows.updateRow(row)
del row
del rows


print "begin dfc"
#search_distance = "300 Feet" # 300 feet is about 90 meters \ 40 meters = 131.234 feet
search_distance = "200 Feet" # The distance used to search for match candidates. A distance must be specified and it must be greater than zero. You can choose a preferred unit; the default is the feature unit.
#match values
match_fields = "S_NAME S_NAME"
statsTable = arcpy.Describe(updateFeatures).catalogPath + "\\new_roads_stats_daggett"
#change_tolerance = "300 Feet"
change_tolerance = "40" # The Change Tolerance serves as the width of a buffer zone around the update features or the base features.  It's the distance used to determine if there is a spatial change. All matched update features and base features are checked against this tolerance. If any portions of update or base features fall outside the zone around the matched feature, it is considered a spatial change.

## compare values
compare_fields = "PRE_DIR PRE_DIR; S_NAME S_NAME; S_TYPE S_TYPE; L_F_ADD L_F_ADD; L_T_ADD L_T_ADD; R_F_ADD R_F_ADD; R_T_ADD R_T_ADD; ACS_ALIAS ACS_ALIAS; SUF_DIR SUF_DIR;"

arcpy.AddMessage("Begining detect feature change process for DaggettCo at: " + time.strftime("%c"))
#print "begining detect feature change process..."
# Perform spatial change detection
arcpy.DetectFeatureChanges_management(updateFeatures, baseFeatures, dfcOutput, search_distance, match_fields, statsTable, change_tolerance, compare_fields)
#print "finished detect feature change process!"
arcpy.AddMessage("Finished detect feature change process at: " + time.strftime("%c"))
print "done at: " + time.strftime("%c")
