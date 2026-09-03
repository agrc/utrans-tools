using UGRC.UtransTools.Core;
using Xunit;

namespace UGRC.UtransTools.Core.Tests;

public sealed class ReviewRulesTests
{
    [Theory]
    [InlineData("123", true)]
    [InlineData("123.5", true)]
    [InlineData("12A", false)]
    [InlineData("12-14", false)]
    public void Validates_Address_Range_Values(string value, bool isValid)
    {
        Assert.Equal(isValid, ReviewRules.IsValidAddressRange(value));
    }

    [Fact]
    public void Normalizes_Edited_Road_Values_For_Saving()
    {
        var values = ReviewRules.NormalizeEditedRoadValues(
            new Dictionary<string, string> { ["NAME"] = " O'Brien ", ["L_F_ADD"] = " " },
            new[] { "L_F_ADD" }
        );

        Assert.Equal("OBrien", values["NAME"]);
        Assert.Equal(0d, values["L_F_ADD"]);
    }

    [Fact]
    public void Creates_Status_Only_Save_For_Unlinked_Record_With_Ignore_Status()
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
    public void Creates_Status_Only_Save_For_Unlinked_Record_With_Revisit_Status()
    {
        var plan = ReviewRules.CreateSavePlan(
            ChangeStatus.Revisit,
            hasLinkedUtransRoad: false,
            new Dictionary<string, object?> { ["NAME"] = "County Road" }
        );

        Assert.False(plan.WritesUtransRoad);
        Assert.Empty(plan.UtransRoadValues);
        Assert.Equal(ChangeStatus.Revisit, plan.ChangeStatus);
    }

    [Fact]
    public void Creates_Road_Save_For_Linked_Record_With_Completed_Status()
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
    public void Creates_Status_Only_Save_For_Linked_Record_With_Revisit_Status()
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
    public void Creates_Status_Only_Save_For_Linked_Record_With_Ignore_Status()
    {
        var plan = ReviewRules.CreateSavePlan(
            ChangeStatus.Ignore,
            hasLinkedUtransRoad: true,
            new Dictionary<string, object?> { ["NAME"] = "UTRANS Road" }
        );

        Assert.False(plan.WritesUtransRoad);
        Assert.Empty(plan.UtransRoadValues);
        Assert.Equal(ChangeStatus.Ignore, plan.ChangeStatus);
    }

    [Fact]
    public void Rejects_Completed_Save_For_Unlinked_Record()
    {
        var exception = Assert.Throws<InvalidOperationException>(() =>
            ReviewRules.CreateSavePlan(
                ChangeStatus.Completed,
                hasLinkedUtransRoad: false,
                new Dictionary<string, object?>()
            )
        );

        Assert.Equal(
            "Click Add New to create the target UTRANS road before saving.",
            exception.Message
        );
    }

    [Fact]
    public void Builds_Road_Payload()
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

        Assert.Equal("11", payload["CARTOCODE"]);
        Assert.Equal("0", payload["ONEWAY"]);
        Assert.Equal("0", payload["VERT_LEVEL"]);
        Assert.Equal("25", payload["SPEED_LMT"]);
        Assert.Equal("Active", payload["STATUS"]);
    }

    [Fact]
    public void Allows_New_Road_Creation_Only_For_Unlinked_New_Records()
    {
        var selections = new[] { new DfcResultReview("N", -1), new DfcResultReview("N", -1) };

        Assert.True(ReviewRules.CanCreateNewUtransRoads(selections));
        Assert.False(ReviewRules.CanCreateNewUtransRoads(new[] { new DfcResultReview("M", -1) }));
        Assert.False(ReviewRules.CanCreateNewUtransRoads(new[] { new DfcResultReview("N", 42) }));
        Assert.False(ReviewRules.CanCreateNewUtransRoads([]));
    }

    [Theory]
    [InlineData("11", "9", "11")]
    [InlineData("0", "1", "0")]
    [InlineData("0", "2", "0")]
    [InlineData("25", "15", "25")]
    [InlineData("Active", "Retired", "Active")]
    public void Prefers_Primary_Road_Values_Over_Fallback_Values(
        string primaryValue,
        string fallbackValue,
        string defaultValue
    )
    {
        var result = ReviewRules.ResolveRoadFieldValue(primaryValue, fallbackValue, defaultValue);

        Assert.Equal(primaryValue, result);
    }

    [Theory]
    [InlineData("", "15", "25", "15")]
    [InlineData(" ", "", "25", "25")]
    [InlineData("", null, "Active", "Active")]
    public void Falls_Back_When_County_Road_Value_Is_Blank(
        string countyValue,
        string? utransValue,
        string defaultValue,
        string expectedValue
    )
    {
        var result = ReviewRules.ResolveRoadFieldValue(countyValue, utransValue, defaultValue);

        Assert.Equal(expectedValue, result);
    }

    [Theory]
    [InlineData("25", "25")]
    [InlineData("0", "25")]
    [InlineData("Unknown", "25")]
    public void Normalizes_Coded_Values_To_Allowed_Values(string value, string expectedValue)
    {
        var result = ReviewRules.NormalizeCodedValue(
            value,
            "25",
            new HashSet<string>(new[] { "5", "25", "80" }, StringComparer.OrdinalIgnoreCase)
        );

        Assert.Equal(expectedValue, result);
    }

    [Fact]
    public void Transfers_Editable_County_Values_Without_Road_Overrides()
    {
        var payload = ReviewRules.BuildNewRoadPayload(
            new Dictionary<string, object?>
            {
                ["NAME"] = "County Road",
                ["CARTOCODE"] = "10",
                ["SYSTEM_FIELD"] = "excluded",
            },
            new[] { "NAME", "CARTOCODE", "ONEWAY" },
            new RoadReviewValues("11", "0", "0", "25", "Active"),
            applyRoadValueOverrides: false
        );

        Assert.Equal("County Road", payload["NAME"]);
        Assert.Equal("10", payload["CARTOCODE"]);
        Assert.DoesNotContain("ONEWAY", payload.Keys);
        Assert.DoesNotContain("SYSTEM_FIELD", payload.Keys);
    }

    [Fact]
    public void Builds_Bulk_New_Road_Payload_From_Editable_County_Values_And_Overrides()
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
