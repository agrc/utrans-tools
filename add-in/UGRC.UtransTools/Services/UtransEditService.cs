using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using ArcGIS.Core.Data;
using ArcGIS.Desktop.Editing;
using ArcGIS.Desktop.Framework.Threading.Tasks;
using ArcGIS.Desktop.Mapping;
using UGRC.UtransTools.Configuration;
using UGRC.UtransTools.Core;
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
                !ReviewRules.CanCreateNewUtransRoads(selections.Select(ToDfcResultReview).ToArray())
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
                    [UtransEditorConfiguration.DfcChangeStatusField] = "COMPLETED",
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
            var values = GetRoadPayload(state);
            var operation = new EditOperation
            {
                Name = "Save UTRANS editor changes",
                SelectModifiedFeatures = false,
            };

            var plan = ReviewRules.CreateSavePlan(
                ParseChangeStatus(state.ChangeStatus),
                state.Selection.UtransRoad is not null,
                values
            );

            if (plan.WritesUtransRoad)
            {
                operation.Modify(
                    layers.UtransRoads,
                    state.Selection.BaseFeatureId,
                    new Dictionary<string, object?>(
                        plan.UtransRoadValues,
                        StringComparer.OrdinalIgnoreCase
                    )
                );
            }
            operation.Modify(
                layers.DfcResults,
                state.Selection.ObjectId,
                new Dictionary<string, object?>
                {
                    [UtransEditorConfiguration.DfcChangeStatusField] = plan
                        .ChangeStatus.ToString()
                        .ToUpperInvariant(),
                }
            );

            if (!await operation.ExecuteAsync())
            {
                throw new InvalidOperationException(
                    operation.ErrorMessage ?? "The UTRANS edit operation failed."
                );
            }
        });
    }

    private static IReadOnlyDictionary<string, object?> GetRoadPayload(EditorReviewState state) =>
        ReviewRules.BuildRoadPayload(state.GetEditedValues(), ToRoadReviewValues(state));

    private static Dictionary<string, object?> GetCountyRoadValues(
        RoadSnapshot countyRoad,
        FeatureClass utransFeatureClass,
        EditorReviewState roadValues,
        bool applyRoadValueOverrides
    )
    {
        var editableFieldNames = utransFeatureClass
            .GetDefinition()
            .GetFields()
            .Where(field => field.IsEditable)
            .Select(field => field.Name);
        return new Dictionary<string, object?>(
            ReviewRules.BuildNewRoadPayload(
                countyRoad.Attributes,
                editableFieldNames,
                ToRoadReviewValues(roadValues),
                applyRoadValueOverrides
            ),
            StringComparer.OrdinalIgnoreCase
        );
    }

    private static DfcResultReview ToDfcResultReview(DfcSelectionSnapshot selection) =>
        new(selection.ChangeType, selection.BaseFeatureId);

    private static RoadReviewValues ToRoadReviewValues(EditorReviewState state) =>
        new(state.Cartocode, state.Oneway, state.VerticalLevel, state.SpeedLimit, state.Status);

    private static ChangeStatus ParseChangeStatus(string changeStatus) =>
        Enum.TryParse<ChangeStatus>(changeStatus, ignoreCase: true, out var parsedStatus)
            ? parsedStatus
            : throw new InvalidOperationException($"Unsupported change status: {changeStatus}");
}
