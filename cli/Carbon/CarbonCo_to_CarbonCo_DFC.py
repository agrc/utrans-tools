# Name:        (CarbonCo's script to compare their data with what they sent us last time)
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
updateFeatures = r"\\<share>\\AGRC\\agrc\data\\county_obtained\\Carbon\\CC_Roads_010720.gdb\\CC_Roads" ### THIS WOULD BE THE NEWEST DATA
baseFeatures = r"\\<share>\\AGRC\\agrc\data\\county_obtained\\Carbon\\CC_Roads_010720.gdb\\CC_March2019_LastUpdate" ### THIS IS THE DATA THEY SENT US LAST TIME

dirname = os.path.dirname(arcpy.Describe(updateFeatures).catalogPath)
desc = arcpy.Describe(dirname)
if hasattr(desc, "datasetType") and desc.datasetType=='FeatureDataset':
    dirname = os.path.dirname(dirname)

#dfcOutput = "DFC_RESULT"
#dfcResult = arcpy.Describe(updateFeatures).catalogPath + "\\DFC_RESULT"
#dfcOutput = arcpy.Describe(updateFeatures).catalogPath + "\\DFC_RESULT"
dfcOutput = dirname + "\\DFC_CarbonToCarbon"

print "begin converting nulls to emtpy"
# convert nulls to empty in both the update fc and basefeatures fc
# list = [updateFeatures, baseFeatures]
# for item in list:
#     rows = arcpy.UpdateCursor (item)
# #: the old fields (REMOVE THESE):
#     for row in rows:
#         if row.ALT_NAME == ' ' or row.ALT_NAME == None or row.ALT_NAME is None:
#             row.ALT_NAME = ""
#         if row.PRE_DIR == ' ' or row.PRE_DIR == None or row.PRE_DIR is None:
#             row.PRE_DIR = ""
#         if row.S_NAME == ' ' or row.S_NAME == None or row.S_NAME is None:
#             row.S_NAME = ""
#         if row.S_TYPE == ' ' or row.S_TYPE == None or row.S_TYPE is None:
#             row.S_TYPE = ""
#         if row.SUF_DIR == ' ' or row.SUF_DIR == None or row.SUF_DIR is None:
#             row.SUF_DIR = ""
#         if row.ACS_ALIAS == ' ' or row.ACS_ALIAS == None or row.ACS_ALIAS is None:
#             row.ACS_ALIAS = ""
#         if row.ALIAS1 == ' ' or row.ALIAS1 == None or row.ALIAS1 is None:
#             row.ALIAS1 = ""
#         if row.ALIAS1_TYP == ' ' or row.ALIAS1_TYP == None or row.ALIAS1_TYP is None:
#             row.ALIAS1_TYP = ""
#         if row.ALIAS2 == ' ' or row.ALIAS2 == None or row.ALIAS2 is None:
#             row.ALIAS2 = ""
#         if row.ALIAS2_TYP == ' ' or row.ALIAS2_TYP == None or row.ALIAS2_TYP is None:
#             row.ALIAS2_TYP = ""
#         if row.L_F_ADD == ' ' or row.L_F_ADD == None or row.L_F_ADD is None:
#             row.L_F_ADD = 0
#         if row.L_T_ADD == ' ' or row.L_T_ADD == None or row.L_T_ADD is None:
#             row.L_T_ADD = 0
#         if row.R_T_ADD == ' ' or row.R_T_ADD == None or row.R_T_ADD is None:
#             row.R_T_ADD = 0
#         if row.R_F_ADD == ' ' or row.R_F_ADD == None or row.R_F_ADD is None:
#             row.R_F_ADD = 0
# #: new fields (KEEP THIS)
#         if row.PREDIR == ' ' or row.PREDIR == None or row.PREDIR is None:
#             row.PREDIR = ""
#         if row.NAME == ' ' or row.NAME == None or row.NAME is None:
#             row.NAME = ""
#         if row.POSTTYPE == ' ' or row.POSTTYPE == None or row.POSTTYPE is None:
#             row.POSTTYPE = ""
#         if row.POSTDIR == ' ' or row.POSTDIR == None or row.POSTDIR is None:
#             row.POSTDIR = ""
#         if row.AN_NAME == ' ' or row.AN_NAME == None or row.AN_NAME is None:
#             row.AN_NAME = ""
#         if row.AN_POSTDIR == ' ' or row.AN_POSTDIR == None or row.AN_POSTDIR is None:
#             row.AN_POSTDIR = ""
#         if row.A1_PREDIR == ' ' or row.A1_PREDIR == None or row.A1_PREDIR is None:
#             row.A1_PREDIR = ""
#         if row.A1_NAME == ' ' or row.A1_NAME == None or row.A1_NAME is None:
#             row.A1_NAME = ""
#         if row.A1_POSTTYPE == ' ' or row.A1_POSTTYPE == None or row.A1_POSTTYPE is None:
#             row.A1_POSTTYPE = ""
#         if row.A1_POSTDIR == ' ' or row.A1_POSTDIR == None or row.A1_POSTDIR is None:
#             row.A1_POSTDIR = ""
#         if row.A2_PREDIR == ' ' or row.A2_PREDIR == None or row.A2_PREDIR is None:
#             row.A2_PREDIR = 0
#         if row.A2_NAME == ' ' or row.A2_NAME == None or row.A2_NAME is None:
#             row.A2_NAME = 0
#         if row.A2_POSTTYPE == ' ' or row.A2_POSTTYPE == None or row.A2_POSTTYPE is None:
#             row.A2_POSTTYPE = 0
#         if row.A2_POSTDIR == ' ' or row.A2_POSTDIR == None or row.A2_POSTDIR is None:
#             row.A2_POSTDIR = 0
#         if row.FROMADDR_L == ' ' or row.FROMADDR_L == None or row.FROMADDR_L is None:
#             row.FROMADDR_L = 0
#         if row.TOADDR_L == ' ' or row.TOADDR_L == None or row.TOADDR_L is None:
#             row.TOADDR_L = 0
#         if row.FROMADDR_R == ' ' or row.FROMADDR_R == None or row.FROMADDR_R is None:
#             row.FROMADDR_R = 0
#         if row.TOADDR_R == ' ' or row.TOADDR_R == None or row.TOADDR_R is None:
#             row.TOADDR_R = 0
#         rows.updateRow(row)
# del row
# del rows


#: null the fields in the old data model:
rows = arcpy.UpdateCursor (baseFeatures)
for row in rows:
    if row.ALT_NAME == ' ' or row.ALT_NAME == None or row.ALT_NAME is None:
        row.ALT_NAME = ""
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
    if row.ALIAS1 == ' ' or row.ALIAS1 == None or row.ALIAS1 is None:
        row.ALIAS1 = ""
    if row.ALIAS1_TYP == ' ' or row.ALIAS1_TYP == None or row.ALIAS1_TYP is None:
        row.ALIAS1_TYP = ""
    if row.ALIAS2 == ' ' or row.ALIAS2 == None or row.ALIAS2 is None:
        row.ALIAS2 = ""
    if row.ALIAS2_TYP == ' ' or row.ALIAS2_TYP == None or row.ALIAS2_TYP is None:
        row.ALIAS2_TYP = ""
    if row.L_F_ADD == ' ' or row.L_F_ADD == None or row.L_F_ADD is None:
        row.L_F_ADD = 0
    if row.L_T_ADD == ' ' or row.L_T_ADD == None or row.L_T_ADD is None:
        row.L_T_ADD = 0
    if row.R_T_ADD == ' ' or row.R_T_ADD == None or row.R_T_ADD is None:
        row.R_T_ADD = 0
    if row.R_F_ADD == ' ' or row.R_F_ADD == None or row.R_F_ADD is None:
        row.R_F_ADD = 0
del row
del rows


#: null the fields in the new data model:
rows = arcpy.UpdateCursor (updateFeatures)
for row in rows:
    if row.PREDIR == ' ' or row.PREDIR == None or row.PREDIR is None:
        row.PREDIR = ""
    if row.NAME == ' ' or row.NAME == None or row.NAME is None:
        row.NAME = ""
    if row.POSTTYPE == ' ' or row.POSTTYPE == None or row.POSTTYPE is None:
        row.POSTTYPE = ""
    if row.POSTDIR == ' ' or row.POSTDIR == None or row.POSTDIR is None:
        row.POSTDIR = ""
    if row.AN_NAME == ' ' or row.AN_NAME == None or row.AN_NAME is None:
        row.AN_NAME = ""
    if row.AN_POSTDIR == ' ' or row.AN_POSTDIR == None or row.AN_POSTDIR is None:
        row.AN_POSTDIR = ""
    if row.A1_PREDIR == ' ' or row.A1_PREDIR == None or row.A1_PREDIR is None:
        row.A1_PREDIR = ""
    if row.A1_NAME == ' ' or row.A1_NAME == None or row.A1_NAME is None:
        row.A1_NAME = ""
    if row.A1_POSTTYPE == ' ' or row.A1_POSTTYPE == None or row.A1_POSTTYPE is None:
        row.A1_POSTTYPE = ""
    if row.A1_POSTDIR == ' ' or row.A1_POSTDIR == None or row.A1_POSTDIR is None:
        row.A1_POSTDIR = ""
    if row.A2_PREDIR == ' ' or row.A2_PREDIR == None or row.A2_PREDIR is None:
        row.A2_PREDIR = 0
    if row.A2_NAME == ' ' or row.A2_NAME == None or row.A2_NAME is None:
        row.A2_NAME = 0
    if row.A2_POSTTYPE == ' ' or row.A2_POSTTYPE == None or row.A2_POSTTYPE is None:
        row.A2_POSTTYPE = 0
    if row.A2_POSTDIR == ' ' or row.A2_POSTDIR == None or row.A2_POSTDIR is None:
        row.A2_POSTDIR = 0
    if row.FROMADDR_L == ' ' or row.FROMADDR_L == None or row.FROMADDR_L is None:
        row.FROMADDR_L = 0
    if row.TOADDR_L == ' ' or row.TOADDR_L == None or row.TOADDR_L is None:
        row.TOADDR_L = 0
    if row.FROMADDR_R == ' ' or row.FROMADDR_R == None or row.FROMADDR_R is None:
        row.FROMADDR_R = 0
    if row.TOADDR_R == ' ' or row.TOADDR_R == None or row.TOADDR_R is None:
        row.TOADDR_R = 0
    rows.updateRow(row)
del row
del rows


print "begin dfc"
#search_distance = "300 Feet" # 300 feet is about 90 meters \ 40 meters = 131.234 feet
search_distance = "200 Feet" # The distance used to search for match candidates. A distance must be specified and it must be greater than zero. You can choose a preferred unit; the default is the feature unit.
#match values
match_fields = "NAME S_NAME"
statsTable = arcpy.Describe(updateFeatures).catalogPath + "\\new_roads_stats_carbon"
#change_tolerance = "300 Feet"
change_tolerance = "40" # The Change Tolerance serves as the width of a buffer zone around the update features or the base features.  It's the distance used to determine if there is a spatial change. All matched update features and base features are checked against this tolerance. If any portions of update or base features fall outside the zone around the matched feature, it is considered a spatial change.

## compare values
#OLD SCHEMA: compare_fields = "ALT_NAME ALT_NAME; PRE_DIR PRE_DIR; S_NAME S_NAME; S_TYPE S_TYPE; SUF_DIR SUF_DIR; ACS_ALIAS ACS_ALIAS; ALIAS1 ALIAS1; ALIAS1_TYP ALIAS1_TYP; ALIAS2 ALIAS2; ALIAS2_TYP ALIAS2_TYP; L_F_ADD L_F_ADD; L_T_ADD L_T_ADD; R_T_ADD R_T_ADD; R_F_ADD R_F_ADD"
#MIXED SCHEMAS: compare_fields = "PREDIR PRE_DIR; NAME S_NAME; POSTTYPE S_TYPE; POSTDIR SUF_DIR; A1_NAME ALIAS1; A1_POSTTYPE ALIAS1_TYP; A2_NAME ALIAS2; A2_POSTTYPE ALIAS2_TYP"
compare_fields = "PREDIR PRE_DIR; NAME S_NAME; POSTTYPE S_TYPE; POSTDIR SUF_DIR"

arcpy.AddMessage("Begining detect feature change process for CarbonCo at: " + time.strftime("%c"))
#print "begining detect feature change process..."
# Perform spatial change detection
arcpy.DetectFeatureChanges_management(updateFeatures, baseFeatures, dfcOutput, search_distance, match_fields, statsTable, change_tolerance, compare_fields)
print "finished detect feature change process!"


print "begin creating seperate feature class named RoadsCenterlines_Recents"
# join the dfc output to the newest county data to see what changes have been made
arcpy.env.qualifiedFieldNames = False

# Set local variables
joinField_roads = "OBJECTID"
joinField_dfc = "UPDATE_FID"

# Make a layer from the feature class
arcpy.MakeFeatureLayer_management(updateFeatures,"roads_lyr")

# Make a layer from the feature class
arcpy.MakeFeatureLayer_management(dfcOutput,"dfc_lyr")

# Join the feature layer to a table
arcpy.AddJoin_management("roads_lyr", joinField_roads, "dfc_lyr", joinField_dfc)

# Select desired features from veg_layer
expression = r"DFC_CarbonToCarbon.CHANGE_TYPE <> 'NC'"
layerName = "roads_lyr"
arcpy.SelectLayerByAttribute_management(layerName, "NEW_SELECTION", expression)

# Copy the layer to a new permanent feature class
outFeature = dirname + "\\Roads_Recents"
arcpy.CopyFeatures_management(layerName, outFeature)

arcpy.AddMessage("Finished detect feature change process at: " + time.strftime("%c"))
print "done at: " + time.strftime("%c")
