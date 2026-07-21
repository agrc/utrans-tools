# utrans-tools

Tools for working with UTRANS data

## `Get_Recent_Edits.py` script run example

```bash
# example 1
python Get_Recent_Edits.py --county Carbon --update-features "Z:\Documents\gdb\Carbon20231019.gdb\Roads" --base-features "Z:\Documents\gdb\Carbon20230208.gdb\CC_Roads" --dfc-output-name DFC_CarbonToCarbon_test5 --stats-table-name stats_carbon_to_carbon_test5 --recents-name RoadCenterline_Recents_test5

# example 2

python cli/Get_Recent_Edits.py --county Davis --update-features "Z:\Documents\gdb\DavisCounty_20260626.gdb\DavisRoads" --base-features "Z:\Documents\gdb\DavisCounty_20260514.gdb\DavisRoads" --dfc-output-name DFC_test721 --stats-table-name stats_test721 --recents-name RoadCenterline_Recents_test721
```
