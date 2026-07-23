namespace UGRC.UtransTools.Models;

internal sealed record DfcSelectionSnapshot(
    long ObjectId,
    long UpdateFeatureId,
    long BaseFeatureId,
    string ChangeType,
    string ChangeLabel,
    RoadSnapshot DfcResult,
    RoadSnapshot CountyRoad,
    RoadSnapshot? UtransRoad
)
{
    internal bool IsNotYetCopiedNewRecord => ChangeType == "N" && BaseFeatureId == -1;
}
