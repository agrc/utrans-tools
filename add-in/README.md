# UTRANS Tools ArcGIS Pro Add-In

## Usage

### Adding New Features

Use **Add New** to copy an unlinked new record or records from `DFC_RESULT` into the UTRANS roads layer.

1. In the map, select one or more unlinked records in the `DFC_RESULT` layer. A record is eligible when its change type is `N` and its `BASE_FID` is `-1`.
2. Review or update the road attributes shown in the editor. When multiple records are selected, the values are used for each new road.
3. Click **Add New**.

When multiple features are selected, the form values override the county-road values for `CARTOCODE`, `ONEWAY`, `VERT_LEVEL`, `SPEED_LMT`, and `STATUS`. Review these values before clicking **Add New** because the same editor values are applied to every new road.

The add-in creates a UTRANS road using each selected county-road geometry and attributes, links the `DFC_RESULT` record to the new road, and marks the change status as `COMPLETED`. The map selections are cleared after the operation finishes.

### Reviewing Detected Changes

Select a `DFC_RESULT` feature to choose its Change Status. Use **IGNORE** for a change that should not update UTRANS, such as a driveway, or **REVISIT** to defer review. Click **Save** to store that change status on the selected DFC result.

For an unlinked new record, **Add New** remains available while Change Status is **COMPLETED**. Choosing **IGNORE** or **REVISIT** replaces it with **Save** so the record can be reviewed without creating a UTRANS road.

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
