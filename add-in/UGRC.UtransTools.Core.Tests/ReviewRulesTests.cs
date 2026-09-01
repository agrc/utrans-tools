using Xunit;
using UGRC.UtransTools.Core;

namespace UGRC.UtransTools.Core.Tests;

public sealed class ReviewRulesTests
{
    [Fact]
    public void Creates_status_only_save_for_unlinked_record_with_ignore_status()
    {
        var plan = ReviewRules.CreateSavePlan(
            ChangeStatus.Ignore,
            hasLinkedUtransRoad: false,
            new Dictionary<string, object?> { ["NAME"] = "County Road" }
        );

        Assert.False(plan.WritesUtransRoad);
        Assert.Empty(plan.UtransRoadValues);
        Assert.Equal(ChangeStatus.Ignore, plan.ChangeStatus);
    }

    [Fact]
    public void Creates_road_save_for_linked_record_with_completed_status()
    {
        var plan = ReviewRules.CreateSavePlan(
            ChangeStatus.Completed,
            hasLinkedUtransRoad: true,
            new Dictionary<string, object?> { ["NAME"] = "UTRANS Road" }
        );

        Assert.True(plan.WritesUtransRoad);
        Assert.Equal("UTRANS Road", plan.UtransRoadValues["NAME"]);
        Assert.Equal(ChangeStatus.Completed, plan.ChangeStatus);
    }

    [Fact]
    public void Creates_status_only_save_for_linked_record_with_revisit_status()
    {
        var plan = ReviewRules.CreateSavePlan(
            ChangeStatus.Revisit,
            hasLinkedUtransRoad: true,
            new Dictionary<string, object?> { ["NAME"] = "UTRANS Road" }
        );

        Assert.False(plan.WritesUtransRoad);
        Assert.Empty(plan.UtransRoadValues);
        Assert.Equal(ChangeStatus.Revisit, plan.ChangeStatus);
    }

    [Fact]
    public void Rejects_completed_save_for_unlinked_record()
    {
        var exception = Assert.Throws<InvalidOperationException>(() =>
            ReviewRules.CreateSavePlan(
                ChangeStatus.Completed,
                hasLinkedUtransRoad: false,
                new Dictionary<string, object?>()
            )
        );

        Assert.Equal("Click Add New to create the target UTRANS road before saving.", exception.Message);
    }

    [Fact]
    public void Builds_road_payload_with_street_type_for_named_road()
    {
        var payload = ReviewRules.BuildRoadPayload(
            new Dictionary<string, object?>
            {
                ["NAME"] = "Main",
                ["POSTTYPE"] = "St",
                ["POSTDIR"] = "E",
            },
            new RoadReviewValues("11", "0", "0", "25", "Active")
        );

        Assert.Equal("Main St", payload["FULLNAME"]);
        Assert.Equal("11", payload["CARTOCODE"]);
        Assert.Equal("0", payload["ONEWAY"]);
        Assert.Equal("0", payload["VERT_LEVEL"]);
        Assert.Equal("25", payload["SPEED_LMT"]);
        Assert.Equal("Active", payload["STATUS"]);
    }

    [Fact]
    public void Allows_new_road_creation_only_for_unlinked_new_records()
    {
        var selections = new[]
        {
            new DfcResultReview("N", -1),
            new DfcResultReview("N", -1),
        };

        Assert.True(ReviewRules.CanCreateNewUtransRoads(selections));
        Assert.False(
            ReviewRules.CanCreateNewUtransRoads(
                new[] { new DfcResultReview("M", -1) }
            )
        );
    }

    [Fact]
    public void Builds_bulk_new_road_payload_from_editable_county_values_and_overrides()
    {
        var payload = ReviewRules.BuildNewRoadPayload(
            new Dictionary<string, object?>
            {
                ["NAME"] = "County Road",
                ["CARTOCODE"] = "10",
                ["SYSTEM_FIELD"] = "excluded",
            },
            new[] { "NAME", "CARTOCODE", "ONEWAY", "VERT_LEVEL", "SPEED_LMT", "STATUS" },
            new RoadReviewValues("11", "0", "0", "25", "Active"),
            applyRoadValueOverrides: true
        );

        Assert.Equal("County Road", payload["NAME"]);
        Assert.Equal("11", payload["CARTOCODE"]);
        Assert.Equal("0", payload["ONEWAY"]);
        Assert.Equal("0", payload["VERT_LEVEL"]);
        Assert.Equal("25", payload["SPEED_LMT"]);
        Assert.Equal("Active", payload["STATUS"]);
        Assert.DoesNotContain("SYSTEM_FIELD", payload.Keys);
    }
}