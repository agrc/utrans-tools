using System.Collections.Generic;

namespace UGRC.UtransTools.Configuration;

internal static class UtransEditorConfiguration
{
    internal const string UtransRoadsAlias = "UTRANS.TRANSADMIN.ROADS_EDIT";
    internal const string CountyRoadsAlias = "COUNTY_STREETS";
    internal const string DfcResultAlias = "DFC_RESULT";
    internal const string AddressSystemAlias = "SGID.LOCATION.AddressSystemQuadrants";
    internal const string ZipCodesAlias = "SGID.BOUNDARIES.ZipCodes";
    internal const string CountiesAlias = "SGID.BOUNDARIES.Counties";
    internal const string MunicipalitiesAlias = "SGID.BOUNDARIES.Municipalities";
    internal const string DfcDispositionField = "CURRENT_NOTES";
    internal const string AttributeReferenceUrl = "https://docs.google.com/document/d/1h7FTFUEXWobA8fvctgxKLaxr6LslnwVPnGVgPlrHnz0/edit";
    internal const string DfcDefinitionQueryUrl = "https://www.google.com/search?q=DFC_RESULT+definition+query";

    internal static readonly string[] EditableTextFields =
    {
        "PREDIR", "NAME", "POSTTYPE", "POSTDIR",
        "AN_NAME", "AN_POSTDIR",
        "A1_PREDIR", "A1_NAME", "A1_POSTTYPE", "A1_POSTDIR",
        "A2_PREDIR", "A2_NAME", "A2_POSTTYPE", "A2_POSTDIR"
    };

    internal static readonly string[] EditableAddressFields =
    {
        "FROMADDR_L", "TOADDR_L", "FROMADDR_R", "TOADDR_R"
    };

    internal static readonly string[] CommonRoadFields =
    {
        "FROMADDR_L", "TOADDR_L", "FROMADDR_R", "TOADDR_R",
        "PREDIR", "NAME", "POSTTYPE", "POSTDIR", "AN_NAME", "AN_POSTDIR",
        "A1_PREDIR", "A1_NAME", "A1_POSTTYPE", "A1_POSTDIR",
        "A2_PREDIR", "A2_NAME", "A2_POSTTYPE", "A2_POSTDIR",
        "CARTOCODE", "ONEWAY", "VERT_LEVEL", "SPEED_LMT"
    };

    internal static readonly IReadOnlyDictionary<string, string> CountyOwnershipNames =
        new Dictionary<string, string>
        {
            ["001"] = "Beaver",
            ["003"] = "Box Elder",
            ["005"] = "Cache",
            ["007"] = "Carbon",
            ["009"] = "Daggett",
            ["011"] = "Davis",
            ["013"] = "Duchesne",
            ["015"] = "Emery",
            ["017"] = "Garfield",
            ["019"] = "Grand",
            ["021"] = "Iron",
            ["023"] = "Juab",
            ["025"] = "Kane",
            ["027"] = "Millard",
            ["029"] = "Morgan",
            ["031"] = "Piute",
            ["033"] = "Rich",
            ["035"] = "Salt Lake",
            ["037"] = "San Juan",
            ["039"] = "Sanpete",
            ["041"] = "Sevier",
            ["043"] = "Summit",
            ["045"] = "Tooele",
            ["047"] = "Uintah",
            ["049"] = "Utah",
            ["051"] = "Wasatch",
            ["053"] = "Washington",
            ["055"] = "Wayne",
            ["057"] = "Weber"
        };
}
