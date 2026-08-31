# UTRANS Tools

Tools for working with UTRANS data

## Attribute Rule Scripts

These are Arcade scripts for calculation and constraint rules on the UTRANS geodatabase in ArcGIS Pro. See its [README](attribute-rules/README.md) for deployment instructions.

## `Get_Recent_Edits.py` script run example

This is a Python CLI tool for processing county-submitted data prior to ingestion into UTRANS. See its [README](cli/README.md) for installation, usage, and release instructions.

## ArcGIS Pro Add-in

This is an ArcGIS Pro Add-in for working with UTRANS data. See its [README](add-in/README.md) for installation, usage, and release instructions.

## Data Flow

The following diagram shows the flow of data from the county into UTRANS.

```mermaid
flowchart TD
  subgraph CLI
    direction TB
    updateFeatureClass@{ shape: lean-r , label: "Update Feature Class (--update-features)"} --> getRecentEdits["get-recent-edits"]
    countyBaseFeatureClass@{ shape: lean-r , label: "County Base Feature Class (--base-features)"} --> getRecentEdits
    getRecentEdits --> RoadCenterline_Recents@{ shape: lean-r , label: "RoadCenterline_Recents (--source-features)"}

    RoadCenterline_Recents --> etl["etl"]
    utransRoads@{ shape: lean-r , label: "UTRANS Roads Schema (--utrans-roads)"} --> etl
    countyBoundaries@{ shape: lean-r , label: "County Boundaries (--county-boundaries)"} --> etl
    etl --> etlOutput@{ shape: lean-r , label: "county_etl_YYYYMMDD"}

    etlOutput --> detectChanges["detect-changes"]
    utransBaseFeatureClass@{ shape: lean-r , label: "UTRANS Feature Class (--utrans-features)"} --> detectChanges
    detectChanges --> productionDfc@{ shape: lean-r , label: "UTRANS/DFC_RESULT"}
  end
```
