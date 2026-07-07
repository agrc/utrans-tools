# Name:        (Garfields's script to compare their data with what they sent us last time)
# Description: Perform change detection between newly received road data and
#              existing road data and find the number of new roads and the
#              total length of them.
# Author:      eneemann
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
#env.workspace = r"D:\UTRANS\Updates\GarfieldCenterlines_16_02_17.gdb" ### change database name ###

#strTimeNow = time.strftime("%c")

# start timer and print start time
start_time = time.time()
readable_start = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
print("The script start time is {}".format(readable_start))
today = time.strftime("%Y%m%d")

# Set local variables
updateFeatures = r"L:\agrc\data\county_obtained\Garfield\Garfield20260427.gdb\Garfield_Streets_Roads_UTM" ### THIS WOULD BE THE NEWEST DATA
baseFeatures = r"L:\agrc\data\county_obtained\Garfield\Garfield20250908.gdb\Garfield_Streets_Roads_UTM" ### THIS IS THE DATA THEY SENT US LAST TIME

dirname = os.path.dirname(arcpy.Describe(updateFeatures).catalogPath)
desc = arcpy.Describe(dirname)
if hasattr(desc, "datasetType") and desc.datasetType=='FeatureDataset':
    dirname = os.path.dirname(dirname)

print(f"Directory Name: {dirname}")
print(f"Description: {desc}")
#dfcOutput = "DFC_RESULT"
#dfcResult = arcpy.Describe(updateFeatures).catalogPath + "\\DFC_RESULT"
#dfcOutput = arcpy.Describe(updateFeatures).catalogPath + "\\DFC_RESULT"
dfcOutput = dirname + "\\DFC_GarfieldToGarfield"

# print("begin converting nulls to empty")
# # convert nulls to empty in both the update fc and basefeatures fc
# list = [updateFeatures, baseFeatures]
# for item in list:
#     rows = arcpy.UpdateCursor (item)
#     for row in rows:
#         if row.FROMADDR_L == None or row.FROMADDR_L is None:
#             row.FROMADDR_L = 0
#         if row.TOADDR_L == None or row.TOADDR_L is None:
#             row.TOADDR_L = 0
#         if row.FROMADDR_R == None or row.FROMADDR_R is None:
#             row.FROMADDR_R = 0
#         if row.TOADDR_R == None or row.TOADDR_R is None:
#             row.TOADDR_R = 0

#         if row.NAME in ('', ' ', 'None', 'NULL', None):
#             row.NAME = ""
#         else:
#             row.NAME = ' '.join(row.NAME.split()).upper()

#         if row.PREDIR in ('', ' ', 'None', 'NULL', None):
#             row.PREDIR = ""
#         else:
#             row.PREDIR = row.PREDIR.strip()

#         if row.POSTDIR in ('', ' ', 'None', 'NULL', None):
#             row.POSTDIR = ""
#         else:
#             row.POSTDIR = ""

#         if row.POSTTYPE in ('', ' ', 'None', 'NULL', None):
#             row.POSTTYPE = ""
#         else:
#             row.POSTTYPE = ' '.join(row.POSTTYPE.split()).upper()

#         if row.AN_NAME in ('', ' ', 'None', 'NULL', None):
#             row.AN_NAME = ""
#         else:
#             row.AN_NAME = ' '.join(row.AN_NAME.split()).upper()

#         if row.A1_NAME in ('', ' ', 'None', 'NULL', None):
#             row.A1_NAME = ""
#         else:
#             row.A1_NAME = ' '.join(row.A1_NAME.split()).upper()

#         if row.A2_NAME in ('', ' ', 'None', 'NULL', None):
#             row.A2_NAME = ""
#         else:
#             row.A2_NAME = ' '.join(row.A2_NAME.split()).upper()

#         rows.updateRow(row)
# del row
# del rows


print("begin dfc")
#search_distance = "300 Feet" # 300 feet is about 90 meters \ 40 meters = 131.234 feet
search_distance = "200 Feet" # The distance used to search for match candidates. A distance must be specified and it must be greater than zero. You can choose a preferred unit; the default is the feature unit.
#match values
match_fields = "NAME NAME"
#statsTable = arcpy.Describe(updateFeatures).catalogPath + "\\stats_vecc"
statsTable = dirname + "\\stats_Garfield_to_Garfield"
print(f"StatsTable: {statsTable}")
print(f"DFC Layer: {dfcOutput}")

#statsTable = None

#change_tolerance = "300 Feet"
change_tolerance = "40" # The Change Tolerance serves as the width of a buffer zone around the update features or the base features.  It's the distance used to determine if there is a spatial change. All matched update features and base features are checked against this tolerance. If any portions of update or base features fall outside the zone around the matched feature, it is considered a spatial change.

## compare values
compare_fields = "FROMADDR_L FROMADDR_L; TOADDR_L TOADDR_L; FROMADDR_R FROMADDR_R; TOADDR_R TOADDR_R; NAME NAME; PREDIR PREDIR; POSTDIR POSTDIR; POSTTYPE POSTTYPE; AN_NAME AN_NAME; A1_NAME A1_NAME; A2_NAME A2_NAME"

arcpy.AddMessage("Beginning detect feature change process for Garfield at: " + time.strftime("%c"))
#print "beginning detect feature change process..."
# Perform spatial change detection
arcpy.DetectFeatureChanges_management(updateFeatures, baseFeatures, dfcOutput, search_distance, match_fields, statsTable, change_tolerance, compare_fields)
print("finished detect feature change process!")


print("begin creating separate feature class named RoadsCenterlines_Recents")
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
expression = r"DFC_GarfieldToGarfield.CHANGE_TYPE <> 'NC'"    # for a feature class
# expression = r"DFC_GarfieldToGarfield.CHANGE_TYP <> 'NC'"   # for a shapefile
layerName = "roads_lyr"
arcpy.SelectLayerByAttribute_management(layerName, "NEW_SELECTION", expression)

# Copy the layer to a new permanent feature class
outFeature = dirname + "\\RoadCenterline_Recents"
arcpy.CopyFeatures_management(layerName, outFeature)

arcpy.AddMessage("Finished detect feature change process at: " + time.strftime("%c"))

print("Script shutting down ...")
#: stop timer and print end time
readable_end = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
print("The script end time is {}".format(readable_end))
print("Time elapsed: {:.2f}s".format(time.time() - start_time))
