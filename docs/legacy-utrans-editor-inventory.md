# Legacy UTRANS Editor Inventory

## Scope

This document inventories the observable behavior in the ArcMap WinForms `frmUtransEditor` and its Google Sheets helper. It describes required behavior for an ArcGIS Pro replacement; it does not prescribe a direct ArcObjects-to-Pro port.

## Purpose

The form supports a UGRC editor reviewing county road-submission changes represented by `DFC_RESULT`. For the selected change, it compares county-source and UTRANS attributes, lets the editor choose accepted values, writes the accepted UTRANS attributes and derived spatial attributes, and records the disposition in `DFC_RESULT`.

## Required map data

The form discovers map layers by feature-class alias and closes if any are missing.

- `UTRANS.TRANSADMIN.ROADS_EDIT` � editable target road layer.
- `COUNTY_STREETS` � source submission road layer.
- `DFC_RESULT` � difference/change record layer.
- `SGID.LOCATION.AddressSystemQuadrants` � address-system and quadrant lookup.
- `SGID.BOUNDARIES.ZipCodes` � ZIP and post-community lookup.
- `SGID.BOUNDARIES.Counties` � county FIPS lookup.
- `SGID.BOUNDARIES.Municipalities` � incorporated-municipality lookup and notification city lookup.

The editor also reads the active version name when the editing workspace is a remote/versioned geodatabase. This is informational only.

### Explicit exclusion

Do not migrate the legacy `SGID.BOUNDARIES.MetroTownships` lookup or any functionality that derives `UNINCCOM_L` or `UNINCCOM_R`. That table no longer exists.

## Selection contract

The primary workflow is driven by exactly one selected `DFC_RESULT` feature.

1. Read `UPDATE_FID`, `BASE_FID`, `CHANGE_TYPE`, and `OBJECTID` from the selected DFC record.
2. Use `UPDATE_FID` to load the matching county road by `OBJECTID`.
3. Use `BASE_FID` to load the matching UTRANS road by `OBJECTID`.
4. Populate side-by-side county and UTRANS values.

If zero or multiple DFC records are selected, the form clears data and asks the user to select one DFC record.

### Change labels

- `N`: New. If `BASE_FID` is `-1`, the segment has not yet been copied into UTRANS. Otherwise it is new and awaits attribute verification.
- `S`: Spatial.
- `A`: Attribute.
- `SA`: Spatial and attribute.
- `NC`: No change.
- `D`: Deletion. The UI label contains the legacy spelling `Delation`.
- Other values: Unknown.

## Attribute review experience

The form displays county-source and UTRANS values for these address and naming components:

- `FROMADDR_L`, `TOADDR_L`, `FROMADDR_R`, `TOADDR_R`
- `PREDIR`, `NAME`, `POSTTYPE`, `POSTDIR`
- `AN_NAME`, `AN_POSTDIR`
- `A1_PREDIR`, `A1_NAME`, `A1_POSTTYPE`, `A1_POSTDIR`
- `A2_PREDIR`, `A2_NAME`, `A2_POSTTYPE`, `A2_POSTDIR`

Differences are highlighted in yellow. Edits to a UTRANS-side value bold its field label. Empty UTRANS address ranges are saved as numeric zeroes.

The editor can:

- Edit UTRANS-side values manually.
- Double-click an individual field label to toggle the county value into the UTRANS value, then restore the original UTRANS value on the next double-click.
- Use `Transfer all values` to copy all listed county values into the UTRANS edit buffer.
- Enter only numeric characters and `.` in address-range fields.
- Select values for `CARTOCODE`, `ONEWAY`, `VERT_LEVEL`, and `SPEED_LMT`; edits are visually marked.

Initial defaults after selection are cartocode index 10, vertical level index 0, and one-way index 0 when those values are otherwise absent.

### Special visual indicators

- A UTRANS feature with a non-empty `DOT_RTNAME` is labeled as a UDOT street in red.
- A UTRANS feature whose `UTRANS_NOTES` contains `AGRC ADJUSTED` is also labeled prominently.
- A not-yet-copied new record (`CHANGE_TYPE = N`, `BASE_FID = -1`) uses gray UTRANS inputs, disables field labels, and exposes the copy-new-segment workflow.

## Save and disposition behavior

Before an accepted UTRANS save, the editor warns�but permits continuation�when `CARTOCODE`, `VERT_LEVEL`, or `ONEWAY` is unselected.

The disposition control has the following implemented behaviors:

- `COMPLETED`: save UTRANS attributes and set `DFC_RESULT.CURRENT_NOTES` to `COMPLETED`.
- `IGNORE`: do not modify UTRANS; set `DFC_RESULT.CURRENT_NOTES` to `IGNORE`.
- `REVISIT`: do not modify UTRANS; set `DFC_RESULT.CURRENT_NOTES` to `REVISIT`.

After a successful save, the legacy form clears selection, selects the updated UTRANS feature, refreshes the map, refreshes the remaining DFC count using the DFC layer definition query, and reloads the editor state.

## UTRANS write behavior

For an existing UTRANS road, the form writes the editable address/name/alias components and the four coded attributes. It also:

- Removes apostrophes from the street-name value before storing it.
- Calculates `FULLNAME` as `NAME + POSTDIR` when `NAME` is numeric; otherwise it calculates `NAME + POSTTYPE`.
- Maps cartocode from the zero-based UI selection to values 1 through 18.
- Maps one-way and vertical level from their zero-based UI selections.
- Writes selected speed-limit text, or null when unselected.

Each legacy operation is committed through ArcMap edit operations. The Pro replacement must perform the entire accepted-road update and DFC disposition through well-scoped `EditOperation` instances with undo support.

## Derived spatial attributes

On an accepted UTRANS save, the legacy form derives attributes from the target road geometry.

1. Calculate the line midpoint.
2. Create points 15 map units to the left and right of the midpoint. All supported maps use `EPSG:26912`, so the legacy offset has a fixed projected-meter context and requires no cross-spatial-reference handling.
3. Intersect each point with the reference layers.

For each side, write:

- ZIP layer: `ZIPCODE_L`/`ZIPCODE_R` from `ZIP5`; post community from `NAME`.
  - Write the left and right post-community values to `POSTCOMM_L` and `POSTCOMM_R`, respectively. The legacy right-side write to `POSTCOMM_L` is a confirmed defect and must be corrected.
- Municipality layer: `INCMUNI_L`/`INCMUNI_R` from `NAME`, or blank when absent.
- Address-system layer: `ADDRSYS_L`/`ADDRSYS_R` from title-cased `GRID_NAME`, and `QUADRANT_L`/`QUADRANT_R` from uppercase `QUADRANT`, or blanks when absent.
- County layer: `COUNTY_L`/`COUNTY_R` from `FIPS_STR`, or blank when absent.
- Ownership: if `DOT_RTNAME` starts with `0`, write `UDOT`; otherwise prefer `MU <municipality name>`, then a hard-coded FIPS-to-`CO <county name>` mapping, otherwise blank.

A missing ZIP or county produces a warning but does not stop the save. A missing municipality or address-system feature silently produces blank derived values.

## New-segment workflow

A new DFC record with `BASE_FID = -1` may be copied from `COUNTY_STREETS` into the UTRANS layer.

1. Copy the existing explicit list of common road fields and the geometry from the county feature.
2. Find the new UTRANS feature by matching address ranges and road-name components.
3. If exactly one match is found, update `DFC_RESULT.BASE_FID` with its object ID.
4. If none or multiple matches are found, warn the editor.
5. Select the new UTRANS feature and reload the form.

The matching strategy is not reliable for duplicate road attributes. A Pro replacement should obtain the new feature's object ID directly from the create operation rather than re-querying by attributes.

## Navigation and repair actions

- **Next:** select the next visible DFC feature whose `OBJECTID` is greater than the current selection, zoom to it, and reload. With no selection, select the first visible DFC feature.
- **Repair DFC identifier:** when exactly one DFC feature and one UTRANS feature are selected, set `DFC_RESULT.BASE_FID` to the selected UTRANS object ID and preserve the prior `BASE_FID` in `PREV__NOTES`.

## Explicitly excluded integration

Do not migrate the Google spreadsheet notification workflow, including spreadsheet logging, OAuth authorization, user access-code prompts, notification-note capture, or the legacy Google API helper. This functionality is no longer used.

Do not migrate the legacy vertex display workflow. It will not be implemented as an editor feature or a Pro selection/symbology workflow at this time.

## Migration boundaries

Do not port these implementation patterns:

- ArcObjects COM cursors, application globals, and event subscriptions.
- WinForms controls as the source of business state.
- Hard-coded aliases, field names, FIPS mappings, URLs, or credentials scattered through UI code.
- Re-querying newly-created features by non-unique attribute combinations.

Implement the replacement as a Pro dockpane with a view model and services for layer validation, DFC selection/loading, attribute comparison, spatial derivation, road updates, DFC disposition, and navigation. Map and geodatabase work must run through `QueuedTask.Run`; writes must use `EditOperation`.

## ArcGIS Pro implementation constraints

Follow the repository add-in instructions for all implementation work under `add-in`:

- Use C# and current ArcGIS Pro SDK patterns from authoritative SDK documentation and samples.
- Implement editor UI as WPF with MVVM; the dockpane view must not contain business or geodatabase logic.
- Use `ArcGIS.Desktop.Framework.Dialogs.MessageBox` for messages and `OpenItemDialog` for ArcGIS Pro item selection.
- Use the ArcGIS Pro add-in DAML schema when changing `config.daml`.
- Use `CIMSymbol.MakeSymbolReference()` when a symbol reference is required.
- Keep all map and geodatabase access on the Map Control Thread through `QueuedTask.Run`.
- Use `EditOperation` for every persisted edit so the user receives Pro-native undo/redo behavior.
