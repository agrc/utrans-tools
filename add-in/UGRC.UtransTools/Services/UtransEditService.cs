using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using ArcGIS.Core.Data;
using ArcGIS.Desktop.Editing;
using ArcGIS.Desktop.Framework.Threading.Tasks;
using ArcGIS.Desktop.Mapping;
using UGRC.UtransTools.Configuration;
using UGRC.UtransTools.Models;

namespace UGRC.UtransTools.Services;

internal sealed class UtransEditService
{
    internal Task CreateNewUtransRoadsAsync(
        EditorLayerContext layers,
        IReadOnlyList<DfcSelectionSnapshot> selections,
        EditorReviewState roadValues
    )
    {
        return QueuedTask.Run(async () =>
        {
            if (
                selections.Count == 0
                || selections.Any(selection => !selection.IsNotYetCopiedNewRecord)
            )
            {
                throw new InvalidOperationException(
                    "All selected DFC records must be unlinked New records to create UTRANS roads."
                );
            }

            var createOperation = new EditOperation
            {
                Name = "Add new UTRANS road",
                SelectModifiedFeatures = false,
            };
            using var utransFeatureClass = layers.UtransRoads.GetFeatureClass();
            var newRoads = selections
                .Select(selection => new
                {
                    Selection = selection,
                    NewRoad = createOperation.Create(
                        layers.UtransRoads,
                        selection.CountyRoad.Shape,
                        GetCountyRoadValues(
                            selection.CountyRoad,
                            utransFeatureClass,
                            roadValues,
                            selections.Count > 1
                        )
                    ),
                })
                .ToList();
            if (!await createOperation.ExecuteAsync())
            {
                throw new InvalidOperationException(
                    createOperation.ErrorMessage ?? "The new UTRANS roads could not be created."
                );
            }

            var linkOperation = new EditOperation
            {
                Name = "Link DFC record to new UTRANS road",
                SelectModifiedFeatures = false,
            };
            foreach (var newRoad in newRoads)
            {
                var values = new Dictionary<string, object?>
                {
                    ["BASE_FID"] = newRoad.NewRoad.ObjectID,
                    [UtransEditorConfiguration.DfcDispositionField] = "COMPLETED",
                };

                linkOperation.Modify(layers.DfcResults, newRoad.Selection.ObjectId, values);
            }
            if (!await linkOperation.ExecuteAsync())
            {
                throw new InvalidOperationException(
                    linkOperation.ErrorMessage ?? "The new UTRANS roads could not be linked to DFC."
                );
            }

            layers.DfcResults.ClearSelection();
            layers.UtransRoads.ClearSelection();
        });
    }

    internal Task RepairDfcIdentifierAsync(EditorLayerContext layers, EditorReviewState state)
    {
        return QueuedTask.Run(async () =>
        {
            var selectedObjectIds = layers.UtransRoads.GetSelection().GetObjectIDs();
            if (selectedObjectIds.Count != 1)
            {
                throw new InvalidOperationException(
                    "Select exactly one feature in the Roads_Edit layer."
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
                    ["BASE_FID"] = selectedObjectIds[0],
                    ["PREV__NOTES"] = string.IsNullOrWhiteSpace(previousNotes)
                        ? state.Selection.BaseFeatureId.ToString(
                            System.Globalization.CultureInfo.InvariantCulture
                        )
                        : $"{previousNotes}; {state.Selection.BaseFeatureId.ToString(System.Globalization.CultureInfo.InvariantCulture)}",
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
                throw new InvalidOperationException(
                    "Click Add New to create the target UTRANS road before saving."
                );
            }

            if (shouldWriteRoad)
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

        foreach (var pair in state.GetEditedValues())
        {
            values[pair.Key] = pair.Value;
        }

        values = new Dictionary<string, object?>(values, StringComparer.OrdinalIgnoreCase)
        {
            ["CARTOCODE"] = state.Cartocode,
            ["ONEWAY"] = state.Oneway,
            ["VERT_LEVEL"] = state.VerticalLevel,
            ["SPEED_LMT"] = state.SpeedLimit,
            ["FULLNAME"] = BuildFullName(values),
        };

        values["STATUS"] = state.Status;

        return values;
    }

    private static Dictionary<string, object?> GetCountyRoadValues(
        RoadSnapshot countyRoad,
        FeatureClass utransFeatureClass,
        EditorReviewState roadValues,
        bool applyRoadValueOverrides
    )
    {
        var values = new Dictionary<string, object?>(StringComparer.OrdinalIgnoreCase);
        foreach (var field in utransFeatureClass.GetDefinition().GetFields())
        {
            if (field.IsEditable && countyRoad.Attributes.TryGetValue(field.Name, out var value))
            {
                values[field.Name] = value;
            }
        }

        if (applyRoadValueOverrides)
        {
            values["CARTOCODE"] = roadValues.Cartocode;
            values["ONEWAY"] = roadValues.Oneway;
            values["VERT_LEVEL"] = roadValues.VerticalLevel;
            values["SPEED_LMT"] = roadValues.SpeedLimit;
            values["STATUS"] = roadValues.Status;
        }

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
