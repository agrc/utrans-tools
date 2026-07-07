# Summit_QueryOutCountysRecentEditsNewFC.py
# Created on: 5/26/2016
# Author: gbunce

# NOTE
### three ### pound signs indicates that the user needs to change a variable before running this code

# Import system modules
import arcpy
from arcpy import env

import time
from datetime import date
#get the date
today = date.today()
strDate = str(today.month).zfill(2) + str(today.day).zfill(2) +  str(today.year)


in_features = r"D:\UTRANS\Updates\SummitCenterlines_16_02_17.gdb\SummitUTDM_05262016" ### change fc name ###
out_path = r"D:\UTRANS\Updates\SummitCenterlines_16_02_17.gdb" ### change database name ###
expresstion = "MODIFYDATE >= date '2015-2-17'" ### change date ###
out_name = "SummitUTDM_RecentEditsDefQuery_" + strDate

print "begin feature class to feature class with defintion query"
# Feature Class to Feature Class
arcpy.FeatureClassToFeatureClass_conversion (in_features, out_path, out_name, expresstion)

# add alias name to the feature class for use in the ArcMap Utrans Editor
newFC = "D:\\UTRANS\\Updates\\SummitCenterlines_16_02_17.gdb\\SummitUTDM_RecentEditsDefQuery_" + strDate ### change database name ###
arcpy.AlterAliasName(newFC, "COUNTY_STREETS")