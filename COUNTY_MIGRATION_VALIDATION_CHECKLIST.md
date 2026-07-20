# County Migration Validation Checklist

Use this checklist when validating county recent-edits processing using the unified `Get_Recent_Edits.py` script.

## Goal

Verify that the unified script produces correct recents output for each county given valid input geodatabases.

## Policy

- Use single-run validation for each county.
- Run the unified script once with known inputs and validate output quality.
- All county-specific legacy scripts have been removed; all processing now routes through `Get_Recent_Edits.py`.

## 1) Prepare Inputs

- Pick one county and one known input pair:
  - Newer feature class path: `<newer gdb>\<roads fc>`
  - Older feature class path: `<older gdb>\<roads fc>`
- Confirm both exist and are accessible:
  - `arcpy.Exists(r"<newer gdb>\<roads fc>")`
  - `arcpy.Exists(r"<older gdb>\<roads fc>")`

## 2) Run Unified Script

Execute `Get_Recent_Edits.py` with the prepared inputs:

```bash
python cli/Get_Recent_Edits.py \
  --county <COUNTY> \
  --update-features "<newer gdb>\<roads fc>" \
  --base-features "<older gdb>\<roads fc>"
```

Example:
```bash
python cli/Get_Recent_Edits.py \
  --county CACHE \
  --update-features "L:\agrc\data\county_obtained\Cache\CacheCo_20260514.gdb\CacheCountyRoads" \
  --base-features "L:\agrc\data\county_obtained\Cache\CacheCo_20260210.gdb\CacheCountyRoads"
```

## 3) Validate Outputs Exist

After the script completes, verify these outputs were created in the newer geodatabase:

- `DFC_<County>To<County>` — Detect Feature Changes output feature class
- `stats_<county>_to_<county>` — Statistics table from DFC
- `RoadCenterline_Recents` — Final recents feature class (only features with changes)

Check for errors or incomplete creation in the script output log.

## 4) Validate Output Row Counts

Query row counts for the recents feature class:

```python
arcpy.GetCount_management("<newer gdb>\RoadCenterline_Recents")
```

Interpretation:

- Row count > 0: Changes were detected and output as expected.
- Row count = 0: No changes detected between inputs (may be correct depending on input pair).
- Script error: Investigate field normalization, schema compatibility, and input paths.

## 5) Spot-Check Output Quality

For a subset of rows in `RoadCenterline_Recents`, verify:

- Geometry is valid (not null, proper coordinates)
- Required fields are populated (GEOCODEST, CHANGE_TYPE, etc.)
- Field values are properly normalized (no leading/trailing spaces, correct null handling)

Use ArcGIS Pro to browse the output or query with arcpy:

```python
with arcpy.da.SearchCursor("<newer gdb>\RoadCenterline_Recents", ["OID@", "GEOCODEST", "CHANGE_TYPE"]) as cursor:
    for row in cursor[:10]:  # First 10 rows
        print(row)
```

## 6) Compare Against Historical Baseline (Optional)

If you have a documented expected row count from a previous production run with the same input pair:

- Compare current row count to historical count.
- Small differences (< 2%) are acceptable; investigate larger divergences.
- If inputs are from a different time period, expected counts may differ; focus on output validity instead.

## 7) Before Commit

- Remove any test output feature classes created during validation (unless keeping as test fixtures).
- Document any deviations or issues discovered during validation.
- Confirm the script runs without errors for at least one representative county per data type (GDB, shapefile inputs).
