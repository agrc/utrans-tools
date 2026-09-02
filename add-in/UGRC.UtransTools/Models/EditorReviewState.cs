using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Linq;
using System.Runtime.CompilerServices;
using UGRC.UtransTools.Configuration;
using UGRC.UtransTools.Core;

namespace UGRC.UtransTools.Models;

internal sealed class EditorReviewState : INotifyPropertyChanged
{
    private readonly string _initialCartocode = string.Empty;
    private readonly string _initialOneway = string.Empty;
    private readonly string _initialVerticalLevel = string.Empty;
    private readonly string _initialSpeedLimit = string.Empty;
    private string _cartocode = string.Empty;
    private string _oneway = string.Empty;
    private string _verticalLevel = string.Empty;
    private string _speedLimit = string.Empty;
    private string _status = string.Empty;
    private string _changeStatus = string.Empty;

    internal EditorReviewState()
    {
        Fields = new ObservableCollection<AttributeReviewField>(
            UtransEditorConfiguration
                .EditableAddressFields.Select(field => CreateEmptyField(field, true))
                .Concat(
                    UtransEditorConfiguration.EditableTextFields.Select(field =>
                        CreateEmptyField(field, false)
                    )
                )
        );
        Cartocode = "11";
        Oneway = "0";
        VerticalLevel = "0";
        SpeedLimit = "25";
        Status = "Active";
        ChangeStatus = "COMPLETED";
        _initialCartocode = Cartocode;
        _initialOneway = Oneway;
        _initialVerticalLevel = VerticalLevel;
        _initialSpeedLimit = SpeedLimit;

        static AttributeReviewField CreateEmptyField(string fieldName, bool isAddressRange) =>
            new(fieldName, string.Empty, string.Empty, isAddressRange);
    }

    internal EditorReviewState(DfcSelectionSnapshot selection)
    {
        Selection = selection;
        var utransRoad = selection.UtransRoad;
        Fields = new ObservableCollection<AttributeReviewField>(
            UtransEditorConfiguration
                .EditableAddressFields.Select(field => CreateField(field, true))
                .Concat(
                    UtransEditorConfiguration.EditableTextFields.Select(field =>
                        CreateField(field, false)
                    )
                )
        );

        Cartocode = ResolveRoadFieldValue("CARTOCODE", "11");
        Oneway = ResolveRoadFieldValue("ONEWAY", "0");
        VerticalLevel = ResolveRoadFieldValue("VERT_LEVEL", "0");
        SpeedLimit = ResolveRoadFieldValue("SPEED_LMT", "25");
        Status = ResolveRoadFieldValue("STATUS", "Active");
        _initialCartocode = Cartocode;
        _initialOneway = Oneway;
        _initialVerticalLevel = VerticalLevel;
        _initialSpeedLimit = SpeedLimit;
        ChangeStatus = string.IsNullOrWhiteSpace(
            selection.DfcResult.GetText(UtransEditorConfiguration.DfcChangeStatusField)
        )
            ? "COMPLETED"
            : selection.DfcResult.GetText(UtransEditorConfiguration.DfcChangeStatusField);
        IsUdotRoad = !string.IsNullOrWhiteSpace(utransRoad?.GetText("DOT_RTNAME"));
        IsAgrcAdjusted =
            utransRoad
                ?.GetText("UTRANS_NOTES")
                .Contains("AGRC ADJUSTED", System.StringComparison.OrdinalIgnoreCase) == true;

        AttributeReviewField CreateField(string fieldName, bool isAddressRange) =>
            new(
                fieldName,
                selection.CountyRoad.GetText(fieldName),
                utransRoad?.GetText(fieldName) ?? string.Empty,
                isAddressRange
            );

        string ResolveRoadFieldValue(string fieldName, string defaultValue) =>
            ReviewRules.ResolveRoadFieldValue(
                selection.CountyRoad.GetText(fieldName),
                utransRoad?.GetText(fieldName),
                defaultValue
            );
    }

    public string Status
    {
        get => _status;
        set
        {
            if (_status == value)
            {
                return;
            }

            _status = value;
            OnPropertyChanged();
        }
    }

    internal DfcSelectionSnapshot? Selection { get; }
    public event PropertyChangedEventHandler? PropertyChanged;
    public string ChangeLabel => Selection?.ChangeLabel ?? string.Empty;
    public long? DfcRecordObjectId => Selection?.ObjectId;
    public long? CountyRecordObjectId => Selection?.CountyRoad.ObjectId;
    public long? UtransRecordObjectId => Selection?.BaseFeatureId;
    public ObservableCollection<AttributeReviewField> Fields { get; }
    public AttributeReviewField this[string fieldName] =>
        Fields.First(field => field.FieldName == fieldName);

    public AttributeReviewField FromaddrL => this["FROMADDR_L"];
    public AttributeReviewField ToaddrL => this["TOADDR_L"];
    public AttributeReviewField FromaddrR => this["FROMADDR_R"];
    public AttributeReviewField ToaddrR => this["TOADDR_R"];
    public AttributeReviewField Predir => this["PREDIR"];
    public AttributeReviewField Name => this["NAME"];
    public AttributeReviewField Posttype => this["POSTTYPE"];
    public AttributeReviewField Postdir => this["POSTDIR"];
    public AttributeReviewField A1Predir => this["A1_PREDIR"];
    public AttributeReviewField A1Name => this["A1_NAME"];
    public AttributeReviewField A1Posttype => this["A1_POSTTYPE"];
    public AttributeReviewField A1Postdir => this["A1_POSTDIR"];
    public AttributeReviewField A2Predir => this["A2_PREDIR"];
    public AttributeReviewField A2Name => this["A2_NAME"];
    public AttributeReviewField A2Posttype => this["A2_POSTTYPE"];
    public AttributeReviewField A2Postdir => this["A2_POSTDIR"];
    public AttributeReviewField AnName => this["AN_NAME"];
    public AttributeReviewField AnPostdir => this["AN_POSTDIR"];

    public string Cartocode
    {
        get => _cartocode;
        set => SetTrackedValue(ref _cartocode, value, nameof(IsCartocodeChanged));
    }

    public string Oneway
    {
        get => _oneway;
        set => SetTrackedValue(ref _oneway, value, nameof(IsOnewayChanged));
    }

    public string VerticalLevel
    {
        get => _verticalLevel;
        set => SetTrackedValue(ref _verticalLevel, value, nameof(IsVerticalLevelChanged));
    }

    public string SpeedLimit
    {
        get => _speedLimit;
        set => SetTrackedValue(ref _speedLimit, value, nameof(IsSpeedLimitChanged));
    }

    public bool IsCartocodeChanged =>
        !string.Equals(Cartocode, _initialCartocode, StringComparison.Ordinal);
    public bool IsOnewayChanged => !string.Equals(Oneway, _initialOneway, StringComparison.Ordinal);
    public bool IsVerticalLevelChanged =>
        !string.Equals(VerticalLevel, _initialVerticalLevel, StringComparison.Ordinal);
    public bool IsSpeedLimitChanged =>
        !string.Equals(SpeedLimit, _initialSpeedLimit, StringComparison.Ordinal);
    public string ChangeStatus
    {
        get => _changeStatus;
        set
        {
            if (_changeStatus == value)
            {
                return;
            }

            _changeStatus = value;
            OnPropertyChanged();
        }
    }
    public bool IsUdotRoad { get; }
    public bool IsAgrcAdjusted { get; }

    internal IReadOnlyDictionary<string, object?> GetEditedValues()
    {
        return ReviewRules.NormalizeEditedRoadValues(
            Fields.ToDictionary(field => field.FieldName, field => field.UtransValue),
            Fields.Where(field => field.IsAddressRange).Select(field => field.FieldName)
        );
    }

    internal void NormalizeCodedValues(
        IEnumerable<CodedValueOption> cartocodeValues,
        IEnumerable<CodedValueOption> onewayValues,
        IEnumerable<CodedValueOption> verticalLevelValues,
        IEnumerable<CodedValueOption> speedLimitValues,
        IEnumerable<CodedValueOption> statusValues
    )
    {
        Cartocode = NormalizeCodedValue(Cartocode, "11", cartocodeValues);
        Oneway = NormalizeCodedValue(Oneway, "0", onewayValues);
        VerticalLevel = NormalizeCodedValue(VerticalLevel, "0", verticalLevelValues);
        SpeedLimit = NormalizeCodedValue(SpeedLimit, "25", speedLimitValues);
        Status = NormalizeCodedValue(Status, "Active", statusValues);
    }

    private static string NormalizeCodedValue(
        string value,
        string defaultValue,
        IEnumerable<CodedValueOption> options
    ) =>
        ReviewRules.NormalizeCodedValue(
            value,
            defaultValue,
            new HashSet<string>(
                options.Select(option => option.Code),
                StringComparer.OrdinalIgnoreCase
            )
        );

    private void SetTrackedValue(
        ref string field,
        string value,
        string changedPropertyName,
        [CallerMemberName] string? propertyName = null
    )
    {
        if (field == value)
        {
            return;
        }

        field = value;
        OnPropertyChanged(propertyName);
        OnPropertyChanged(changedPropertyName);
    }

    private void OnPropertyChanged([CallerMemberName] string? propertyName = null) =>
        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));
}
