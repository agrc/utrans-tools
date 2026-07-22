---
applyTo: "add-in/**"
description: Custom instructions obtained from https://github.com/Esri/arcgis-pro-sdk-community-samples/blob/master/.github/copilot-instructions.md
---

# Copilot Custom Instructions for ArcGIS Pro SDK Add-in Development

I am developing ArcGIS Pro Add-ins using the ArcGIS Pro SDK.

- Use the authoritative ArcGIS Pro SDK API documentation as the primary reference: https://pro.arcgis.com/en/pro-app/latest/sdk/api-reference and https://github.com/Esri/arcgis-pro-sdk/tree/master/References/ArcGIS%20Pro%20API
- When providing code examples, follow the patterns and best practices from the official ArcGIS Pro SDK documentation and samples.
- Prefer C# for all code snippets and explanations.
- Reference and leverage the code snippets available at: https://github.com/Esri/arcgis-pro-sdk-snippets and at: https://github.com/Esri/arcgis-pro-sdk
- Assume the development environment is Visual Studio 2022 or later.
- Use a tab size as defined in the Visual Studio settings (usually 2 spaces).
- To open ArcGIS Pro items, use the OpenItemDialog rather than the standard OpenFileDialog.
- To display a message box, use the ArcGIS.Desktop.Framework.Dialogs.MessageBox class.
- Use modern .NET and ArcGIS Pro SDK conventions.
- Use the https://github.com/Esri/arcgis-pro-sdk/blob/master/References/ArcGIS.Desktop.Framework.xsd xml schema when making changes to any config.daml desktop add-in markup language file.
- For UI development, use the MVVM (Model-View-ViewModel) programming pattern as recommended by the ArcGIS Pro SDK.
- When possible, provide concise explanations and relevant links to documentation.
- If a task involves UI, follow the ArcGIS Pro Add-in UI guidelines.
- CIMSymbol has an extension method called MakeSymbolReference. Use MakeSymbolReference to convert any CIMSymbol to a CIMSymbolReference.

Always ensure that code suggestions are compatible with the latest supported version of ArcGIS Pro SDK.

# Migration instructions

This project is being migrated from an old ArcMap Add-in to a new ArcGIS Pro Add-in. The old add-in codebase is available as a sibling to this repository named: "utrans-editor-tools". Please refer to this project when migrating functionality.

When migrating code, follow these guidelines:

- Identify the core functionality in the ArcMap add-in that needs to be migrated.
- For each piece of functionality, find the equivalent API in the ArcGIS Pro SDK.

# Validation

After you have made changes to the add-in, validate your changes by:

- Building the add-in in Visual Studio to ensure there are no compilation errors.
