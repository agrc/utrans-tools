# utrans-tools

Tools for working with UTRANS data

## Attribute Rule Scripts

The attribute-rule utilities are in [attribute-rules/new_ar.py](attribute-rules/new_ar.py) and [attribute-rules/deploy_ar.py](attribute-rules/deploy_ar.py).

- [attribute-rules/deploy_ar.py](attribute-rules/deploy_ar.py) is the primary script.
  - Default mode is idempotent deploy: add if missing, alter if mutable changes, recreate when immutable changes require it.
  - Use `--mode add` for strict add-only behavior.
  - Use `--mode alter` to update an existing rule only.
- [attribute-rules/new_ar.py](attribute-rules/new_ar.py) is a compatibility wrapper that forwards to deploy script add mode.

Examples:

```bash
# deploy mode (default)
python attribute-rules/deploy_ar.py fullname_calculation --in-table "Z:/data/County.gdb/Roads" --field FULLNAME

# add-only compatibility behavior
python attribute-rules/new_ar.py fullname_calculation --in-table "Z:/data/County.gdb/Roads" --field FULLNAME

# alter existing rule only
python attribute-rules/deploy_ar.py fullname_calculation --in-table "Z:/data/County.gdb/Roads" --mode alter --field FULLNAME
```

## `Get_Recent_Edits.py` script run example

`--county` must be an exact, case-sensitive key from the active profiles file.

- By default, the active file is `cli/profiles.json`.
- Use `--profiles <path-to-json>` to supply a custom profiles file.
- The `--county` value must exist as a top-level key in that active file.

```bash
# example 1
python cli/Get_Recent_Edits.py --county carbon --update-features "Z:\Documents\gdb\Carbon20231019.gdb\Roads" --base-features "Z:\Documents\gdb\Carbon20230208.gdb\CC_Roads" --dfc-output-name DFC_CarbonToCarbon_test5 --stats-table-name stats_carbon_to_carbon_test5 --recents-name RoadCenterline_Recents_test5

# example 2

python cli/Get_Recent_Edits.py --county davis --update-features "Z:\Documents\gdb\DavisCounty_20260626.gdb\DavisRoads" --base-features "Z:\Documents\gdb\DavisCounty_20260514.gdb\DavisRoads" --dfc-output-name DFC_test721 --stats-table-name stats_test721 --recents-name RoadCenterline_Recents_test721

# example 3 (custom profiles file)
python cli/Get_Recent_Edits.py --profiles "Z:\Documents\county_profiles_custom.json" --county davis --update-features "Z:\Documents\gdb\DavisCounty_20260626.gdb\DavisRoads" --base-features "Z:\Documents\gdb\DavisCounty_20260514.gdb\DavisRoads"
```
