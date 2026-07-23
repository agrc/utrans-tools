# UTRANS Tools ArcGIS Pro Add-In

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
  dotnet csharpier .
  ```

- **Verify formatting (used in CI):**

  ```bash
  dotnet csharpier --check .
  ```
