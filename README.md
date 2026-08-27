# utrans-tools

Tools for working with UTRANS data

## Attribute Rule Scripts

The attribute-rule utilities are in [attribute-rules/new_ar.py](attribute-rules/new_ar.py), [attribute-rules/deploy_ar.py](attribute-rules/deploy_ar.py), and [attribute-rules/deploy_all_ar.py](attribute-rules/deploy_all_ar.py).

- [attribute-rules/deploy_ar.py](attribute-rules/deploy_ar.py) is the primary script.
  - Default mode is idempotent deploy: add if missing, alter if mutable changes, recreate when immutable changes require it.
  - Use `--mode add` for strict add-only behavior.
  - Use `--mode alter` to update an existing rule only.
- [attribute-rules/new_ar.py](attribute-rules/new_ar.py) is a compatibility wrapper that forwards to deploy script add mode.
- [attribute-rules/deploy_all_ar.py](attribute-rules/deploy_all_ar.py) recursively deploys every `.arcade` file using idempotent deploy mode. It infers the rule type from the top-level folder (`calculation`, `constraint`, or `validation`) and reads optional `// KEY: value` metadata from each script.

Supported per-script metadata keys are `RULE_NAME`, `FIELD`, `EVENTS`, `IS_EDITABLE`, `ERROR_NUMBER`, `ERROR_MESSAGE`, `DESCRIPTION`, and `SUBTYPE`. Use `FIELD:` with no value for calculation rules that return an `attributes` dictionary for multiple fields.

Examples:

```bash
# deploy mode (default)
python attribute-rules/deploy_ar.py fullname_calculation --in-table "Z:/data/County.gdb/Roads" --field FULLNAME

# add-only compatibility behavior
python attribute-rules/new_ar.py fullname_calculation --in-table "Z:/data/County.gdb/Roads" --field FULLNAME

# alter existing rule only
python attribute-rules/deploy_ar.py fullname_calculation --in-table "Z:/data/County.gdb/Roads" --mode alter --field FULLNAME

# recursively deploy every rule using its script metadata
python attribute-rules/deploy_all_ar.py --in-table "Z:/data/County.gdb/Roads"

# preview all actions without changing the geodatabase
python attribute-rules/deploy_all_ar.py --in-table "Z:/data/County.gdb/Roads" --dry-run
```

### Deploying to an enterprise geodatabase

Attribute rule tools require a file, mobile, or enterprise geodatabase dataset. A feature service URL such as `https://server/server/rest/services/Roads/FeatureServer/0` cannot be used as `--in-table`, and ArcGIS Online hosted feature layers are not a supported target. Deploy to the enterprise geodatabase instead.

The UTRANS enterprise geodatabase is SQL Server on `db.ugrc.utah.gov`. Create a connection file once, then use its `.sde` path in place of a local `.gdb` path.

Option 1 — ArcGIS Pro: use the **New Database Connection** dialog in the Catalog pane (Database Platform `SQL Server`, Instance `db.ugrc.utah.gov`, Authentication Type `Database authentication`, User name `TRANSADMIN`). Then right-click the finished connection and choose **Copy Path** to get the `.sde` location to pass to the script. Connections saved to Catalog favorites live in `%APPDATA%\Esri\ArcGISPro\Favorites`, so you can also browse to the file directly.

Option 2 — Python:

```python
import arcpy

arcpy.management.CreateDatabaseConnection(
    out_folder_path="Z:/connections",
    out_name="roadtest_transadmin.sde",
    database_platform="SQL_SERVER",
    instance="db.ugrc.utah.gov",
    account_authentication="DATABASE_AUTH",
    username="TRANSADMIN",
    save_user_pass="SAVE_USERNAME",
    database="RoadTest",
)
```

Append the dataset name to the connection path and deploy:

```bash
python attribute-rules/deploy_all_ar.py --in-table "Z:/connections/roadtest.sde/TRANSADMIN.Roads_Edit" --dry-run
```

Requirements to be aware of:

- Connect as the dataset owner (`TRANSADMIN`). Attribute rule changes made by any other account fail validation.
- The identity that matters is the database login stored in the `.sde` file, not your Windows account or ArcGIS Pro portal sign-in. Check it with `arcpy.Describe("<connection>.sde").connectionProperties.user`.
- Validation rules require branch versioning on an enterprise geodatabase. Calculation and constraint rules do not.
- Datasets are qualified as `schema.table`. Feature classes inside a feature dataset can also be addressed as `<connection>.sde/TRANSADMIN.Centerlines_Edit/TRANSADMIN.Roads_Edit`.
- Always run `--dry-run` first. It previews each rule action and warns about owner and versioning problems, but because it never calls the geoprocessing tool it cannot catch every server-side rejection.
- Confirm a connection's platform with `arcpy.Describe("<connection>.sde").connectionProperties.dbclient`.
- Keep connection files outside the repository so database credentials are never committed.

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
