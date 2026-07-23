using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Threading.Tasks;
using ArcGIS.Core.Data;
using ArcGIS.Desktop.Framework.Threading.Tasks;
using ArcGIS.Desktop.Mapping;
using UGRC.UtransTools.Configuration;
using UGRC.UtransTools.Models;

namespace UGRC.UtransTools.Services;

internal sealed class LayerValidationService
{
    internal Task<EditorLayerContext> GetRequiredLayersAsync()
    {
        return QueuedTask.Run(() =>
        {
            var map =
                MapView.Active?.Map
                ?? throw new InvalidOperationException(
                    "Open a map before using the UTRANS editor."
                );
            var layers = map.GetLayersAsFlattenedList().OfType<FeatureLayer>().ToList();
            var missingAliases = new List<string>();

            FeatureLayer GetLayer(string name)
            {
                var layer = layers.FirstOrDefault(candidate =>
                    string.Equals(candidate.Name, name, StringComparison.OrdinalIgnoreCase)
                    || string.Equals(
                        candidate.GetFeatureClass().GetDefinition().GetAliasName(),
                        name,
                        StringComparison.OrdinalIgnoreCase
                    )
                );

                if (layer is null)
                {
                    missingAliases.Add(name);
                }

                return layer!;
            }

            var utransRoads = GetLayer(UtransEditorConfiguration.UtransRoadsAlias);
            var countyRoads = GetLayer(UtransEditorConfiguration.CountyRoadsAlias);
            var dfcResults = GetLayer(UtransEditorConfiguration.DfcResultAlias);
            var addressSystems = GetLayer(UtransEditorConfiguration.AddressSystemAlias);
            var zipCodes = GetLayer(UtransEditorConfiguration.ZipCodesAlias);
            var counties = GetLayer(UtransEditorConfiguration.CountiesAlias);
            var municipalities = GetLayer(UtransEditorConfiguration.MunicipalitiesAlias);

            if (missingAliases.Count > 0)
            {
                throw new InvalidOperationException(
                    $"The active map is missing required layers: {string.Join(", ", missingAliases)}."
                );
            }

            return new EditorLayerContext(
                utransRoads,
                countyRoads,
                dfcResults,
                addressSystems,
                zipCodes,
                counties,
                municipalities
            );
        });
    }

    internal Task<
        IReadOnlyDictionary<string, IReadOnlyList<CodedValueOption>>
    > GetCodedValueOptionsAsync(EditorLayerContext layers)
    {
        return QueuedTask.Run(() =>
        {
            var fields = layers.UtransRoads.GetFeatureClass().GetDefinition().GetFields();
            var options = new Dictionary<string, IReadOnlyList<CodedValueOption>>(
                StringComparer.OrdinalIgnoreCase
            );

            foreach (var fieldName in new[] { "CARTOCODE", "ONEWAY", "VERT_LEVEL" })
            {
                var field =
                    fields.FirstOrDefault(candidate =>
                        string.Equals(candidate.Name, fieldName, StringComparison.OrdinalIgnoreCase)
                    )
                    ?? throw new InvalidOperationException(
                        $"{UtransEditorConfiguration.UtransRoadsAlias}.{fieldName} was not found."
                    );
                using var domain = field.GetDomain();
                if (domain is not CodedValueDomain codedValueDomain)
                {
                    throw new InvalidOperationException(
                        $"{UtransEditorConfiguration.UtransRoadsAlias}.{fieldName} must use a coded-value domain."
                    );
                }

                options[fieldName] = codedValueDomain
                    .GetCodedValuePairs()
                    .Select(pair => new CodedValueOption(
                        Convert.ToString(pair.Key, CultureInfo.InvariantCulture) ?? string.Empty,
                        pair.Value
                    ))
                    .ToList();
            }

            return (IReadOnlyDictionary<string, IReadOnlyList<CodedValueOption>>)options;
        });
    }

    internal Task<string> GetUtransDatabaseVersionAsync(
        EditorLayerContext layers,
        string fallbackVersion
    )
    {
        return QueuedTask.Run(() =>
        {
            try
            {
                using var geodatabase = (Geodatabase)
                    layers.UtransRoads.GetFeatureClass().GetDatastore();
                using var versionManager = geodatabase.GetVersionManager();
                using var version = versionManager.GetCurrentVersion();
                var versionName = version.GetName();
                return string.IsNullOrWhiteSpace(versionName) ? fallbackVersion : versionName;
            }
            catch
            {
                return fallbackVersion;
            }
        });
    }
}
