using System.Collections.ObjectModel;

namespace UGRC.UtransTools.Core;

public enum ChangeStatus
{
    Completed,
    Ignore,
    Revisit,
}

public sealed record SavePlan(
    ChangeStatus ChangeStatus,
    bool WritesUtransRoad,
    IReadOnlyDictionary<string, object?> UtransRoadValues
);

public sealed record RoadReviewValues(
    string Cartocode,
    string Oneway,
    string VerticalLevel,
    string SpeedLimit,
    string Status
);

public sealed record DfcResultReview(string ChangeType, long BaseFeatureId)
{
    public bool IsUnlinkedNewRecord => ChangeType == "N" && BaseFeatureId == -1;
}

public static class ReviewRules
{
    public static bool CanCreateNewUtransRoads(
        IReadOnlyCollection<DfcResultReview> selections
    ) => selections.Count > 0 && selections.All(selection => selection.IsUnlinkedNewRecord);

    public static IReadOnlyDictionary<string, object?> BuildNewRoadPayload(
        IReadOnlyDictionary<string, object?> countyRoadValues,
        IEnumerable<string> editableFieldNames,
        RoadReviewValues reviewValues,
        bool applyRoadValueOverrides
    )
    {
        var values = new Dictionary<string, object?>(StringComparer.OrdinalIgnoreCase);
        foreach (var fieldName in editableFieldNames)
        {
            if (countyRoadValues.TryGetValue(fieldName, out var value))
            {
                values[fieldName] = value;
            }
        }

        if (applyRoadValueOverrides)
        {
            values["CARTOCODE"] = reviewValues.Cartocode;
            values["ONEWAY"] = reviewValues.Oneway;
            values["VERT_LEVEL"] = reviewValues.VerticalLevel;
            values["SPEED_LMT"] = reviewValues.SpeedLimit;
            values["STATUS"] = reviewValues.Status;
        }

        return new ReadOnlyDictionary<string, object?>(values);
    }

    public static IReadOnlyDictionary<string, object?> BuildRoadPayload(
        IReadOnlyDictionary<string, object?> editedValues,
        RoadReviewValues reviewValues
    )
    {
        var values = new Dictionary<string, object?>(editedValues, StringComparer.OrdinalIgnoreCase)
        {
            ["CARTOCODE"] = reviewValues.Cartocode,
            ["ONEWAY"] = reviewValues.Oneway,
            ["VERT_LEVEL"] = reviewValues.VerticalLevel,
            ["SPEED_LMT"] = reviewValues.SpeedLimit,
            ["STATUS"] = reviewValues.Status,
        };
        values["FULLNAME"] = BuildFullName(values);

        return new ReadOnlyDictionary<string, object?>(values);
    }

    public static SavePlan CreateSavePlan(
        ChangeStatus changeStatus,
        bool hasLinkedUtransRoad,
        IReadOnlyDictionary<string, object?> editedRoadValues
    )
    {
        var writesUtransRoad = changeStatus == ChangeStatus.Completed;
        if (writesUtransRoad && !hasLinkedUtransRoad)
        {
            throw new InvalidOperationException(
                "Click Add New to create the target UTRANS road before saving."
            );
        }

        return new SavePlan(
            changeStatus,
            writesUtransRoad,
            writesUtransRoad
                ? new ReadOnlyDictionary<string, object?>(
                    new Dictionary<string, object?>(editedRoadValues, StringComparer.OrdinalIgnoreCase)
                )
                : new ReadOnlyDictionary<string, object?>(new Dictionary<string, object?>())
        );
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
            ? value?.ToString()?.Replace("'", string.Empty, StringComparison.Ordinal) ?? string.Empty
            : string.Empty;
}