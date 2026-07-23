using System.ComponentModel;
using System.Linq;
using System.Runtime.CompilerServices;

namespace UGRC.UtransTools.Models;

public sealed class AttributeReviewField : INotifyPropertyChanged
{
    private string _utransValue;
    private bool _isUsingCountyValue;

    internal AttributeReviewField(
        string fieldName,
        string countyValue,
        string utransValue,
        bool isAddressRange
    )
    {
        FieldName = fieldName;
        CountyValue = countyValue;
        OriginalUtransValue = utransValue;
        _utransValue = utransValue;
        IsAddressRange = isAddressRange;
    }

    public string FieldName { get; }
    public string CountyValue { get; }
    public string OriginalUtransValue { get; }
    public bool IsAddressRange { get; }
    public bool IsDifferent =>
        !string.Equals(CountyValue, OriginalUtransValue, System.StringComparison.OrdinalIgnoreCase);
    public bool IsEdited =>
        !string.Equals(UtransValue, OriginalUtransValue, System.StringComparison.Ordinal);
    public bool IsUsingCountyValue => _isUsingCountyValue;

    public string UtransValue
    {
        get => _utransValue;
        set
        {
            if (IsAddressRange && !IsValidAddressRange(value))
            {
                return;
            }

            if (_utransValue == value)
            {
                return;
            }

            _utransValue = value;
            OnPropertyChanged();
            OnPropertyChanged(nameof(IsEdited));
        }
    }

    internal void ToggleCountyValue()
    {
        UtransValue = IsUsingCountyValue ? OriginalUtransValue : CountyValue;
        _isUsingCountyValue = !IsUsingCountyValue;
        OnPropertyChanged(nameof(IsUsingCountyValue));
    }

    internal void TransferCountyValue()
    {
        UtransValue = CountyValue;
        _isUsingCountyValue = true;
        OnPropertyChanged(nameof(IsUsingCountyValue));
    }

    public event PropertyChangedEventHandler? PropertyChanged;

    private void OnPropertyChanged([CallerMemberName] string? propertyName = null) =>
        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));

    private static bool IsValidAddressRange(string value) =>
        value.All(character => char.IsDigit(character) || character == '.');
}
