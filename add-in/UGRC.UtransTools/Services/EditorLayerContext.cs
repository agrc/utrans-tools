using ArcGIS.Desktop.Mapping;

namespace UGRC.UtransTools.Services;

internal sealed record EditorLayerContext(
    FeatureLayer UtransRoads,
    FeatureLayer CountyRoads,
    FeatureLayer DfcResults,
    FeatureLayer AddressSystems,
    FeatureLayer ZipCodes,
    FeatureLayer Counties,
    FeatureLayer Municipalities
);
