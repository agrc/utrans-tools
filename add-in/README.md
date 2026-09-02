# UTRANS Tools ArcGIS Pro Add-In

## Usage

### Map Requirements

Before opening the editor, the active map must contain these layers with these exact names:

- `UTRANS.TRANSADMIN.ROADS_EDIT`
- `COUNTY_STREETS`
- `DFC_RESULT`
- `SGID.LOCATION.AddressSystemQuadrants`
- `SGID.BOUNDARIES.ZipCodes`
- `SGID.BOUNDARIES.Counties`
- `SGID.BOUNDARIES.Municipalities`

Each layer must have an available feature-class data source. The `CARTOCODE`, `ONEWAY`, `VERT_LEVEL`, `SPEED_LMT`, and `STATUS` fields in `UTRANS.TRANSADMIN.ROADS_EDIT` must exist and use coded-value domains. The editor uses those domains for its dropdown values.

### Dropdown Values and Highlights

The five road dropdowns (`CARTOCODE`, `ONEWAY`, `VERT_LEVEL`, `SPEED_LMT`, and `STATUS`) display the descriptions from the coded-value domain, but save the corresponding domain codes. The available choices therefore come from the current `ROADS_EDIT` schema, not from a hard-coded list.

When a DFC record is loaded, the initial selected value for each road dropdown is calculated independently:

1. Use the non-blank value from the matching `COUNTY_STREETS` field.
2. If the county value is blank, use the matching value from the linked `ROADS_EDIT` feature.
3. If both values are blank, use the default: `CARTOCODE` `11`, `ONEWAY` `0`, `VERT_LEVEL` `0`, `SPEED_LMT` `25`, or `STATUS` `Active`.

If the selected source value is not in its coded-value domain, the editor replaces it with that field's default. For a multi-select **Add New** operation, there is no single source road, so the editor starts with the defaults and applies the same dropdown values to every created road. For a single new record, the county-road values are used when available.

A yellow highlighted border around a road dropdown means its current value differs from the value initially loaded into the editor. This can mean that you changed the value, that a value was normalized to its default because it was not a valid domain code, or that a multi-select new-road value was changed from its default. The highlight is a review indicator; it does not by itself mean that the value is invalid or that it has already been saved.

### Adding New Features

Use **Add New** to copy an unlinked new record or records from `DFC_RESULT` into the UTRANS roads layer.

1. In the map, select one or more unlinked records in the `DFC_RESULT` layer. A record is eligible when its change type is `N` and its `BASE_FID` is `-1`.
2. Review or update the road attributes shown in the editor. When multiple records are selected, the values are used for each new road.
3. Click **Add New**.

The form values override the county-road values for `CARTOCODE`, `ONEWAY`, `VERT_LEVEL`, `SPEED_LMT`, and `STATUS`. Review these values before clicking **Add New** because the same editor values are applied to every new road, including when only one feature is selected.

The editor starts these fields with the following defaults when no county-road or UTRANS value is available: `CARTOCODE` `11`, `ONEWAY` `0`, `VERT_LEVEL` `0`, `SPEED_LMT` `25`, and `STATUS` `Active`. If a loaded value is not present in the corresponding coded-value domain, it is replaced with the same default.

The add-in creates a UTRANS road using each selected county-road geometry and attributes, links the `DFC_RESULT` record to the new road, and marks the change status as `COMPLETED`. The map selections are cleared after the operation finishes.

### Reviewing Detected Changes

Select a `DFC_RESULT` feature to choose its Change Status. Use **IGNORE** for a change that should not update UTRANS, such as a driveway, or **REVISIT** to defer review. Click **Save** to store that change status on the selected DFC result.

For an unlinked new record, **Add New** is available only when the record's change type is `N` and `BASE_FID` is `-1`. **Add New** creates the UTRANS road from the county-road geometry, links the DFC record, and sets its status to **COMPLETED**. A **COMPLETED** save for an unlinked record is rejected; click **Add New** first. Choosing **IGNORE** or **REVISIT** saves only the DFC status and does not write a UTRANS road. For a linked record, **COMPLETED** saves the edited UTRANS attributes and DFC status, while **IGNORE** and **REVISIT** save only the DFC status.

### Repairing a DFC Identifier

Use **Update DFC BASE_FID** when a DFC record references the wrong UTRANS segment or after splitting a line. Select exactly one feature in `UTRANS.TRANSADMIN.ROADS_EDIT` before using the button. The repair changes `DFC_RESULT.BASE_FID` to that feature and appends the previous identifier to `DFC_RESULT.PREV__NOTES`.

## Developer Set Up

This project currently targets ArcGIS Pro v3.6. Make sure that your development machine has the same version of ArcGIS Pro installed.

Install [Visual Studio 2022](https://visualstudio.microsoft.com/vs/) selecting the ".NET desktop development" workload. The 2026 version will not work with the 3.6 SDK.

Because the Visual Studio Extension Manager installs the latest version of the ArcGIS Pro SDK, you may need to manually install the 3.6 version of the SDK to match the targeted ArcGIS Pro version for this project. Download the SDK from my.esri.com, extract, and double-click on the two extensions.

Be aware that Visual Studio auto-builds when you change any C# code but you need to manually rebuild if you make any changes to the `Config.daml` file.

### Code Formatting

This project uses **[CSharpier](https://csharpier.com/)** for opinionated, automated C# code formatting.

1. **Restore Repository Tools**  
   Run the following command in `add-in\UGRC.UtransTools` to install the exact version of CSharpier pinned for this project:

   ```bash
   dotnet tool restore
   ```

2. **Configure Visual Studio**
   - Install the **CSharpier** extension (_Extensions > Manage Extensions_).

#### CLI Commands

- **Format all files manually:**

  ```bash
  dotnet csharpier format .
  ```

- **Verify formatting (used in CI):**

  ```bash
  dotnet csharpier check .
  ```

### Release Package

Build the add-in in Release mode from the `add-in` directory:

```powershell
dotnet build .\UGRC.UtransTools\UGRC.UtransTools.csproj --configuration Release
```

Or use Visual Studio to build the project in Release mode.

The build copies `UGRC.UtransTools.esriAddinX` to `L:\agrc\utrans\UtransEditing\Pro Add-ins`.
