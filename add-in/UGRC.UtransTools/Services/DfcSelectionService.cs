using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Threading.Tasks;
using ArcGIS.Core.Data;
using ArcGIS.Desktop.Framework.Threading.Tasks;
using UGRC.UtransTools.Configuration;
using UGRC.UtransTools.Models;

namespace UGRC.UtransTools.Services;

internal sealed class DfcSelectionService
{
    internal Task<DfcSelectionSnapshot?> LoadSelectedAsync(EditorLayerContext layers)
    {
        return QueuedTask.Run(() =>
        {
            var selectedObjectIds = layers.DfcResults.GetSelection().GetObjectIDs();
            if (selectedObjectIds.Count == 0)
            {
                return null;
            }

            if (selectedObjectIds.Count != 1)
            {
                throw new InvalidOperationException("Select exactly one DFC_RESULT feature.");
            }

            var dfc = ReadFeature(layers.DfcResults.GetFeatureClass(), selectedObjectIds[0]);
            var updateFeatureId = ReadInt64(dfc.Attributes, "UPDATE_FID");
            var baseFeatureId = ReadInt64(dfc.Attributes, "BASE_FID");
            var changeType = dfc.GetText("CHANGE_TYPE");
            var countyRoad = ReadFeature(layers.CountyRoads.GetFeatureClass(), updateFeatureId);
            var utransRoad = baseFeatureId == -1 ? null : ReadFeature(layers.UtransRoads.GetFeatureClass(), baseFeatureId);

            return new DfcSelectionSnapshot(
                dfc.ObjectId,
                updateFeatureId,
                baseFeatureId,
                changeType,
                GetChangeLabel(changeType, baseFeatureId),
                dfc,
                countyRoad,
                utransRoad);
        });
    }

    internal Task<int> GetRemainingCountAsync(EditorLayerContext layers)
    {
        return QueuedTask.Run(() =>
        {
            var featureClass = layers.DfcResults.GetFeatureClass();
            var queryFilter = new QueryFilter();

            if (!string.IsNullOrWhiteSpace(layers.DfcResults.DefinitionQuery))
            {
                queryFilter.WhereClause = layers.DfcResults.DefinitionQuery;
            }

            return (int)featureClass.GetCount(queryFilter);
        });
    }

    private static RoadSnapshot ReadFeature(FeatureClass featureClass, long objectId)
    {
        var objectIdField = featureClass.GetDefinition().GetObjectIDField();
        using var cursor = featureClass.Search(new QueryFilter { WhereClause = $"{objectIdField} = {objectId}" }, false);
        if (!cursor.MoveNext())
        {
            throw new InvalidOperationException($"Feature {objectId} was not found in {featureClass.GetDefinition().GetName()}.");
        }

        using var feature = (Feature)cursor.Current;
        var attributes = new Dictionary<string, object?>(StringComparer.OrdinalIgnoreCase);
        foreach (var field in feature.GetFields())
        {
            attributes[field.Name] = feature[field.Name] is DBNull ? null : feature[field.Name];
        }

        return new RoadSnapshot(feature.GetObjectID(), attributes, feature.GetShape());
    }

    private static long ReadInt64(IReadOnlyDictionary<string, object?> attributes, string fieldName)
    {
        if (!attributes.TryGetValue(fieldName, out var value) || value is null)
        {
            throw new InvalidOperationException($"DFC_RESULT.{fieldName} is empty.");
        }

        return Convert.ToInt64(value, CultureInfo.InvariantCulture);
    }

    internal static string GetChangeLabel(string changeType, long baseFeatureId) => changeType switch
    {
        "N" when baseFeatureId != -1 => "New ( Now in UTRANS - Please Verify Attributes and Click Save )",
        "N" => "New",
        "S" => "Spatial",
        "A" => "Attribute",
        "SA" => "Spatial and Attribute",
        "NC" => "No Change",
        "D" => "Delation",
        _ => "Unknown"
    };
}
