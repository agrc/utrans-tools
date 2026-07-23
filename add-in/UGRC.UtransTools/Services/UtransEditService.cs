using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using ArcGIS.Desktop.Editing;
using ArcGIS.Desktop.Framework.Threading.Tasks;
using UGRC.UtransTools.Configuration;
using UGRC.UtransTools.Models;

namespace UGRC.UtransTools.Services;

internal sealed class UtransEditService
{
    internal Task RepairDfcIdentifierAsync(EditorLayerContext layers, EditorReviewState state)
    {
        return QueuedTask.Run(async () =>
        {
            if (state.Selection.UtransRoad is null)
            {
                throw new InvalidOperationException(
                    "A UTRANS road must be loaded before repairing DFC_RESULT.BASE_FID."
                );
            }

            var previousNotes = state.Selection.DfcResult.GetText("PREV__NOTES");
            var operation = new EditOperation
            {
                Name = "Repair DFC_RESULT UTRANS identifier",
                SelectModifiedFeatures = false,
            };
            operation.Modify(
                layers.DfcResults,
                state.Selection.ObjectId,
                new Dictionary<string, object?>
                {
                    ["BASE_FID"] = state.Selection.UtransRoad.ObjectId,
                    ["PREV__NOTES"] = string.IsNullOrWhiteSpace(previousNotes)
                        ? state.Selection.BaseFeatureId.ToString(
                            System.Globalization.CultureInfo.InvariantCulture
                        )
                        : $"{previousNotes}; {state.Selection.BaseFeatureId}",
                }
            );

            if (!await operation.ExecuteAsync())
            {
                throw new InvalidOperationException(
                    operation.ErrorMessage ?? "The DFC identifier repair failed."
                );
            }
        });
    }

    internal Task SaveAsync(EditorLayerContext layers, EditorReviewState state)
    {
        return QueuedTask.Run(async () =>
        {
            var values = GetEditedValues(state);
            var operation = new EditOperation
            {
                Name = "Save UTRANS editor changes",
                SelectModifiedFeatures = false,
            };

            var shouldWriteRoad = string.Equals(
                state.DfcStatus,
                "COMPLETED",
                System.StringComparison.OrdinalIgnoreCase
            );

            if (shouldWriteRoad && state.Selection.UtransRoad is null)
            {
                var newObjectId = operation.Create(
                    layers.UtransRoads,
                    state.Selection.CountyRoad.Shape,
                    values
                );
                operation.Modify(
                    layers.DfcResults,
                    state.Selection.ObjectId,
                    new Dictionary<string, object?>
                    {
                        ["BASE_FID"] = newObjectId,
                        [UtransEditorConfiguration.DfcDispositionField] = state.DfcStatus,
                    }
                );
            }
            else if (shouldWriteRoad)
            {
                operation.Modify(layers.UtransRoads, state.Selection.BaseFeatureId, values);
                operation.Modify(
                    layers.DfcResults,
                    state.Selection.ObjectId,
                    new Dictionary<string, object?>
                    {
                        [UtransEditorConfiguration.DfcDispositionField] = state.DfcStatus,
                    }
                );
            }
            else
            {
                operation.Modify(
                    layers.DfcResults,
                    state.Selection.ObjectId,
                    new Dictionary<string, object?>
                    {
                        [UtransEditorConfiguration.DfcDispositionField] = state.DfcStatus,
                    }
                );
            }

            if (!await operation.ExecuteAsync())
            {
                throw new InvalidOperationException(
                    operation.ErrorMessage ?? "The UTRANS edit operation failed."
                );
            }
        });
    }

    private static Dictionary<string, object?> GetEditedValues(EditorReviewState state)
    {
        var values = new Dictionary<string, object?>(StringComparer.OrdinalIgnoreCase);

        if (state.Selection.UtransRoad is null)
        {
            foreach (var fieldName in UtransEditorConfiguration.CommonRoadFields)
            {
                if (state.Selection.CountyRoad.Attributes.TryGetValue(fieldName, out var value))
                {
                    values[fieldName] = value;
                }
            }
        }

        foreach (var pair in state.GetEditedValues())
        {
            values[pair.Key] = pair.Value;
        }

        values = new Dictionary<string, object?>(values, StringComparer.OrdinalIgnoreCase)
        {
            ["CARTOCODE"] = state.Cartocode,
            ["ONEWAY"] = state.Oneway,
            ["VERT_LEVEL"] = state.VerticalLevel,
            ["SPEED_LMT"] = string.IsNullOrWhiteSpace(state.SpeedLimit) ? null : state.SpeedLimit,
            ["FULLNAME"] = BuildFullName(values),
        };

        return values;
    }

    private static string BuildFullName(IReadOnlyDictionary<string, object?> values)
    {
        var name = GetText(values, "NAME");
        var suffix = name.All(char.IsDigit)
            ? GetText(values, "POSTDIR")
            : GetText(values, "POSTTYPE");
        return string.IsNullOrWhiteSpace(suffix) ? name : $"{name} {suffix}".Trim();
    }

    private static string GetText(IReadOnlyDictionary<string, object?> values, string fieldName) =>
        values.TryGetValue(fieldName, out var value)
            ? value?.ToString()?.Replace("'", string.Empty, System.StringComparison.Ordinal)
                ?? string.Empty
            : string.Empty;
}
