# UTRANS Tools

`utrans-tools` provides command-line tools for working with UTRANS data.

## Install for users

```powershell
conda create --name utrans-tools --clone arcgispro-py3
pip install ugrc-utrans-tools
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

Run `utrans get-recent-edits --help` for the complete option reference and supported county profiles.

### ETL

Convert county roads to the UTRANS schema with explicit inputs:

```powershell
utrans etl --county saltlake --source-features "Z:\Documents\gdb\SaltLake.gdb\RoadCenterline_Recents" --utrans-roads "Z:\schemas\UtahRoadsNGSchema.gdb\Roads_Edit" --output-workspace "Z:\Documents\gdb\output.gdb" --county-boundaries "Database Connections\internal.sde\SGID.BOUNDARIES.Counties"
```

The output contains complete road features that intersect the selected county boundary; it does not clip features at the boundary. Run `utrans etl --help` for all options.
