using System.Collections.Generic;
using ArcGIS.Core.Geometry;

namespace UGRC.UtransTools.Models;

internal sealed record RoadSnapshot(
    long ObjectId,
    IReadOnlyDictionary<string, object?> Attributes,
    Geometry Shape
)
{
    internal string GetText(string fieldName) =>
        Attributes.TryGetValue(fieldName, out var value) && value is not null
            ? value.ToString() ?? string.Empty
            : string.Empty;
}
