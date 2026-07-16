# County Migration Validation Checklist

Use this checklist when porting a county recent-edits script to ArcGIS Pro style.

## Goal

Verify that modern and legacy logic produce the same recents output for the same input geodatabases.

## Default Policy (Current Project)

- Use dual-run validation by default for each county:
  - Run legacy and modern every time on the same input pair.
  - Compare row counts before considering a county complete.
- Reason: if mismatch rate is non-trivial (for example 2 out of 5 counties), it is faster to validate both paths up front than to context-switch later.
- Re-evaluate this policy after each 5-county batch:
  - If mismatches are rare in the most recent batch, switch back to modern-first with legacy fallback.

## 1) Prepare Inputs

- Pick one county and one known input pair:
- Newer feature class path: `<newer gdb>\<roads fc>`
- Older feature class path: `<older gdb>\<roads fc>`
- Confirm both exist in ArcGIS Pro Python:
  - `arcpy.Exists(r"<newer gdb>\\<roads fc>")`
  - `arcpy.Exists(r"<older gdb>\\<roads fc>")`

## 2) Keep Legacy Runner During Validation

- Keep a county-specific legacy script copy from commit `ccd1d9c` while validating.
- Name it clearly, for example:
  - `Get_<County>s_Recent_Edits_legacy_ccd1d9c.py`
- Use Z-drive-style example defaults for `updateFeatures` and `baseFeatures`
  (for example `Z:\Documents\gdb\...`), and do not keep L-drive defaults.

## 3) Set Safe Legacy Output Names

Always use `_legacy` suffixes so test runs do not overwrite active outputs.

- DFC output: `DFC_<County>To<County>_legacy`
- Stats table: `<stats_name>_legacy`
- Recents feature class: `RoadCenterline_Recents_legacy`
- Ensure status prints also reference `RoadCenterline_Recents_legacy` (not `RoadsCenterlines_Recents`).

For reruns, delete existing `_legacy` outputs before writing:

- `arcpy.Delete_management(<output>)` guarded by `arcpy.Exists(<output>)`

## 4) Avoid Hardcoded DFC Name in Where Clause

Do not hardcode `DFC_<County>To<County>.CHANGE_TYPE` in legacy validation scripts.

Use dynamic name resolution:

- `dfc_name = arcpy.Describe(dfcOutput).name`
- `expression = "{0}.CHANGE_TYPE <> 'NC'".format(dfc_name)`

## 5) Legacy Run

- Run legacy script with the exact same input pair used for modern script.
- Keep outputs as `_legacy` names.

## 6) Modern Run

- Run modern script with the same input pair.
- Use non-conflicting output names, for example:
  - `--dfc-output-name DFC_<County>To<County>_modern`
  - `--stats-table-name <stats_name>_modern`
  - `--recents-name RoadCenterline_Recents_modern`

## 7) Compare Results

Minimum check:

- Compare row count of `RoadCenterline_Recents_legacy` vs `RoadCenterline_Recents_modern`.

Interpretation:

- Counts match: migration is validated for that county/input pair.
- Counts differ: investigate field normalization, output naming, and expression qualification first.

## 8) Known Non-Issue Pattern

If legacy and modern both match each other but not a historical expected count, the historical count likely came from a different run context (different input pair, output artifact, or rerun timing).

## 9) Before Commit

- Keep legacy helper files only while actively validating.
- Remove temporary legacy helper files when finished, unless intentionally kept as test fixtures.
- Keep the modern script and compatibility wrapper naming pattern in place.
