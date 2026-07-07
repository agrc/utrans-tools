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
#env.workspace = r"D:\UTRANS\Updates\BoxElderCenterlines_16_02_17.gdb" ### change database name ###

#strTimeNow = time.strftime("%c")

# Set local variables
updateFeatures = r"L:\agrc\data\county_obtained\BoxElder\BoxElder_20260624.gdb\BECO_RDS" ### THIS WOULD BE THE NEWEST DATA
baseFeatures = r"L:\agrc\data\county_obtained\BoxElder\BoxElder_20260331.gdb\BE_Roads" ### THIS IS THE DATA THEY SENT US LAST TIME

dirname = os.path.dirname(arcpy.Describe(updateFeatures).catalogPath)
desc = arcpy.Describe(dirname)
if hasattr(desc, "datasetType") and desc.datasetType=='FeatureDataset':
    dirname = os.path.dirname(dirname)
print(dirname)

# print ("Directory Name: ") + str(dirname)
# print ("Description: ") + str(desc)

print(f"Directory Name: {dirname}")
print(f"Description: {desc}")

#dfcOutput = "DFC_RESULT"
#dfcResult = arcpy.Describe(updateFeatures).catalogPath + "\\DFC_RESULT"
#dfcOutput = arcpy.Describe(updateFeatures).catalogPath + "\\DFC_RESULT"
dfcOutput = dirname + "\\DFC_BoxEToBoxE"

print ("begin converting nulls to emtpy")
# convert nulls to empty in both the update fc and basefeatures fc
list = [updateFeatures, baseFeatures]
for item in list:
    rows = arcpy.UpdateCursor (item)
    for row in rows:
        if row.L_F_ADD == ' ' or row.L_F_ADD == None or row.L_F_ADD is None:
            row.L_F_ADD = 0
        if row.L_T_ADD == ' ' or row.L_T_ADD == None or row.L_T_ADD is None:
            row.L_T_ADD = 0
        if row.R_F_ADD == ' ' or row.R_F_ADD == None or row.R_F_ADD is None:
            row.R_F_ADD = 0
        if row.R_T_ADD == ' ' or row.R_T_ADD == None or row.R_T_ADD is None:
            row.R_T_ADD = 0
        if row.PRE_DIR == ' ' or row.PRE_DIR == None or row.PRE_DIR is None:
            row.PRE_DIR = ""
        if row.S_NAME == ' ' or row.S_NAME == None or row.S_NAME is None:
            row.S_NAME = ""
        if row.S_TYPE == ' ' or row.S_TYPE == None or row.S_TYPE is None:
            row.S_TYPE = ""
        if row.SUF_DIR == ' ' or row.SUF_DIR == None or row.SUF_DIR is None:
            row.SUF_DIR = ""
        if row.ACS_ALIAS == ' ' or row.ACS_ALIAS == None or row.ACS_ALIAS is None:
            row.ACS_ALIAS = ""
        if row.ACS_NAME == ' ' or row.ACS_NAME == None or row.ACS_NAME is None:
            row.ACS_NAME = ""
        if row.ACS_SUF == ' ' or row.ACS_SUF == None or row.ACS_SUF is None:
            row.ACS_SUF = ""
        if row.ALIAS1 == ' ' or row.ALIAS1 == None or row.ALIAS1 is None:
            row.ALIAS1 = ""
        if row.ALIAS1_TYP == ' ' or row.ALIAS1_TYP == None or row.ALIAS1_TYP is None:
            row.ALIAS1_TYP = ""
        if row.ALIAS2 == ' ' or row.ALIAS2 == None or row.ALIAS2 is None:
            row.ALIAS2 = ""
        if row.ALIAS2_TYP == ' ' or row.ALIAS2_TYP == None or row.ALIAS2_TYP is None:
            row.ALIAS2_TYP = ""

        rows.updateRow(row)
del row
del rows


print ("begin dfc")
#search_distance = "300 Feet" # 300 feet is about 90 meters \ 40 meters = 131.234 feet
search_distance = "200 Feet" # The distance used to search for match candidates. A distance must be specified and it must be greater than zero. You can choose a preferred unit; the default is the feature unit.
#match values
match_fields = "S_NAME S_NAME"
#statsTable = arcpy.Describe(updateFeatures).catalogPath + "\\stats_vecc"
statsTable = dirname + "\\stats_boxe_to_boxe"
# print ("StatsTable: ") + str(statsTable)
# print ("DFC Layer: ") + str(dfcOutput)
print(f"StatsTable: {statsTable}")
print(f"DFC Layer: {dfcOutput}")
#statsTable = None

#change_tolerance = "300 Feet"
change_tolerance = "40" # The Change Tolerance serves as the width of a buffer zone around the update features or the base features.  It's the distance used to determine if there is a spatial change. All matched update features and base features are checked against this tolerance. If any portions of update or base features fall outside the zone around the matched feature, it is considered a spatial change.

## compare values
compare_fields = "L_F_ADD L_F_ADD; L_T_ADD L_T_ADD; R_F_ADD R_F_ADD; R_T_ADD R_T_ADD; PRE_DIR PRE_DIR; S_NAME S_NAME; S_TYPE S_TYPE; SUF_DIR SUF_DIR; ACS_ALIAS ACS_ALIAS; ACS_NAME ACS_NAME; ACS_SUF ACS_SUF; ALIAS1 ALIAS1; ALIAS1_TYP ALIAS1_TYP; ALIAS2 ALIAS2; ALIAS2_TYP ALIAS2_TYP"

arcpy.AddMessage("Begining detect feature change process for BoxElder at: " + time.strftime("%c"))
#print "begining detect feature change process..."
# Perform spatial change detection
print ("reading to just before comand")
arcpy.DetectFeatureChanges_management(updateFeatures, baseFeatures, dfcOutput, search_distance, match_fields, statsTable, change_tolerance, compare_fields)
print ("right after comand")
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
expression = r"DFC_BoxEToBoxE.CHANGE_TYPE <> 'NC'"
layerName = "roads_lyr"
arcpy.SelectLayerByAttribute_management(layerName, "NEW_SELECTION", expression)

# Copy the layer to a new permanent feature class
outFeature = dirname + "\\RoadCenterline_Recents"
arcpy.CopyFeatures_management(layerName, outFeature)

arcpy.AddMessage("Finished detect feature change process at: " + time.strftime("%c"))
print ("done at: ") + time.strftime("%c")
