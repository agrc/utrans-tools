using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using ArcGIS.Core.Data;
using ArcGIS.Desktop.Framework.Threading.Tasks;
using ArcGIS.Desktop.Mapping;

namespace UGRC.UtransTools.Services;

internal sealed class DfcNavigationService
{
    internal Task<long?> SelectNextAndZoomAsync(EditorLayerContext layers)
    {
        return QueuedTask.Run(() =>
        {
            var dfcResults = layers.DfcResults;
            var featureClass = dfcResults.GetFeatureClass();
            var objectIdField = featureClass.GetDefinition().GetObjectIDField();
            var selectedObjectIds = dfcResults.GetSelection().GetObjectIDs();
            var baseWhereClauses = new List<string>();

            if (!string.IsNullOrWhiteSpace(dfcResults.DefinitionQuery))
            {
                baseWhereClauses.Add($"({dfcResults.DefinitionQuery})");
            }

            var whereClauses = new List<string>(baseWhereClauses);
            if (selectedObjectIds.Count == 1)
            {
                whereClauses.Add($"{objectIdField} <> {selectedObjectIds[0]}");
            }

            var queryFilter = new QueryFilter
            {
                WhereClause = string.Join(" AND ", whereClauses),
                PostfixClause = $"ORDER BY {objectIdField}",
            };
            using var cursor = featureClass.Search(queryFilter, false);
            if (!cursor.MoveNext())
            {
                return null;
            }

            using var feature = (Feature)cursor.Current;
            var nextObjectId = feature.GetObjectID();
            dfcResults.Select(
                new QueryFilter { WhereClause = $"{objectIdField} = {nextObjectId}" },
                SelectionCombinationMethod.New
            );

            var mapView =
                MapView.Active
                ?? throw new InvalidOperationException(
                    "Open a map before using the UTRANS editor."
                );
            mapView.ZoomTo(dfcResults, nextObjectId, null, false, 1.5, null);
            return (long?)nextObjectId;
        });
    }
}
