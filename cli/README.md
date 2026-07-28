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

```powershell
utrans get-recent-edits --county Carbon --update-features "Z:\Documents\gdb\Carbon20231019.gdb\Roads" --base-features "Z:\Documents\gdb\Carbon20230208.gdb\CC_Roads"
```

Run `utrans get-recent-edits --help` for the complete option reference and supported county profiles.
