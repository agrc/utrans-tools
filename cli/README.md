# UTRANS Tools

`utrans-tools` provides command-line tools for working with UTRANS data.

## Install for users

```powershell
conda create --name utrans-tools --clone arcgispro-py3
conda activate utrans-tools
pip install ugrc-utrans-tools
```

Show help:

```powershell
utrans --help
```

Upgrade to a new version:

```powershell
pip install --upgrade ugrc-utrans-tools
```

## Install for development

From this directory:

```powershell
conda create --name utrans-tools --clone arcgispro-py3
pip install -e ".[dev]"
```

Upgrade these packages if you have troubles installing the dev version:

```powershell
pip install --upgrade pathspec hatchling
```

## Usage

### Get Recent Edits

```powershell
utrans get-recent-edits --county Carbon --update-features "Z:\Documents\gdb\Carbon20231019.gdb\Roads" --base-features "Z:\Documents\gdb\Carbon20230208.gdb\CC_Roads"
```

The output is written to the geodatabase containing `--update-features`.

Run `utrans get-recent-edits --help` for the complete option reference and supported county profiles.

### ETL

Convert county roads to the UTRANS schema with explicit inputs:

```powershell
utrans etl --county saltlake --source-features "Z:\Documents\gdb\SaltLake.gdb\RoadCenterline_Recents" --utrans-roads "Z:\schemas\UtahRoadsNGSchema.gdb\Roads_Edit" --county-boundaries "Database Connections\internal.sde\SGID.BOUNDARIES.Counties"
```

The output is written to the geodatabase containing `--source-features`. It contains complete road features that intersect the selected county boundary; it does not clip features at the boundary. Run `utrans etl --help` for all options.

### Detect Changes

Process ETL output against a previous UTRANS road feature class:

```powershell
utrans detect-changes --county Carbon --update-features "Z:\Documents\gdb\Carbon.gdb\county_etl" --utrans-features "Z:\Documents\gdb\UTRANS.gdb\Roads"
```

The command writes outputs to the geodatabase containing `--update-features`. It uses the `NAME` matching and comparison fields, adds DFC editor metadata, creates `TEST_DFC_RESULT` with `NC` and `D` changes excluded, and appends the filtered result to the fixed UTRANS DFC.

Run `utrans detect-changes --help` for the remaining options.

### One-use value mapping discovery

The repository includes a one-use ArcPy script for inventorying county values
that may need `value_mappings`. It uses the local manifest at
`cli/scripts/county_datasets.csv`; the manifest contains machine-specific paths
and should not be added to package configuration.

Run this from the `utrans-tools` Conda environment with a UTRANS target feature
class whose fields have the production coded-value domains:

```powershell
python cli/scripts/discover_value_mappings.py discover `
	--target-features "C:\path\to\UTRANS.gdb\Roads"
```

The script reads the manifest and profiles from `cli/scripts/` and
`cli/src/utrans/` automatically. It writes
`value-mapping-inventory.csv`, `value-mapping-summary.csv`, and
`reviewed-value-mappings.csv` to the folder where the command is run. The
inventory contains all distinct observed source values, counts, normalized
values, domain resolutions, and statuses. The review CSV contains only
unresolved, non-empty values and includes an `approved_target_value` column.
Enter a valid UTRANS domain code or description for values that should be
mapped; leave it blank for values that should not be mapped. Apply reviewed
mappings directly to `profiles.json`:

```powershell
python cli/scripts/discover_value_mappings.py apply `
	--target-features "C:\path\to\UTRANS.gdb\Roads"
```

Apply mode reads `value-mapping-inventory.csv` and
`reviewed-value-mappings.csv` from the current folder. It applies all rows
marked `review` only when `approved_target_value` is filled in, and skips
approvals that resolve to the same normalized source value. Existing mappings
are preserved; conflicting mappings stop the operation before the file is
written. `value_mappings` should contain translations only, such as
`LANE` to `LN`; values already accepted by the target domain need no entry.
