using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Linq;
using System.Runtime.CompilerServices;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Input;
using ArcGIS.Desktop.Framework;
using ArcGIS.Desktop.Framework.Contracts;
using ArcGIS.Desktop.Mapping.Events;
using UGRC.UtransTools.Infrastructure;
using UGRC.UtransTools.Models;
using UGRC.UtransTools.Services;

namespace UGRC.UtransTools;

internal sealed class UtransEditorDockpaneViewModel : DockPane, INotifyPropertyChanged
{
    private const string DockPaneId = "UGRC_UtransTools_UtransEditorDockpane";
    private const string DefaultVersionMessage = "not versioned";
    private const string SelectDfcFeatureMessage =
        "Please select one or more features from the DFC_RESULT layer.";
    private static readonly EditorReviewState EmptyReviewState = new();
    private readonly LayerValidationService _layerValidationService = new();
    private readonly DfcSelectionService _dfcSelectionService = new();
    private readonly DfcNavigationService _dfcNavigationService = new();
    private readonly UtransEditService _utransEditService = new();
    private EditorReviewState? _reviewState;
    private int? _remainingDfcRecords;
    private string _changeTypeMessage = SelectDfcFeatureMessage;
    private string _statusMessage = "Select one DFC_RESULT feature to load it in the editor";
    private string _updateDfcObjectIdErrorMessage = string.Empty;
    private string _utransDatabaseVersion = DefaultVersionMessage;
    private IReadOnlyList<DfcSelectionSnapshot> _selectedNewRecords = [];
    private EditorReviewState? _newRoadValueState;
    private string _selectedDfcObjectIds = string.Empty;
    private bool _codedValueOptionsLoaded;

    internal UtransEditorDockpaneViewModel()
    {
        AddNewCommand = new AsyncRelayCommand(AddNewAsync);
        SaveCommand = new AsyncRelayCommand(SaveAsync);
        NextCommand = new AsyncRelayCommand(SelectNextDfcAsync);
        UpdateDfcObjectIdCommand = new AsyncRelayCommand(RepairDfcIdentifierAsync);
        TransferAllCommand = new RelayCommand<EditorReviewState>(TransferAllValues);
        ToggleFieldCommand = new RelayCommand<AttributeReviewField>(field =>
            field.ToggleCountyValue()
        );
        MapSelectionChangedEvent.Subscribe(OnMapSelectionChanged, false);
        ActiveMapViewChangedEvent.Subscribe(OnActiveMapViewChanged, false);
        QueueSelectionLoad();
    }

    private async Task RepairDfcIdentifierAsync()
    {
        if (ReviewState is null)
        {
            return;
        }

        try
        {
            UpdateDfcObjectIdErrorMessage = string.Empty;
            var layers = await _layerValidationService.GetRequiredLayersAsync();
            await _utransEditService.RepairDfcIdentifierAsync(layers, ReviewState);
            var updatedSelection = await _dfcSelectionService.LoadSelectedAsync(layers);
            if (updatedSelection is null)
            {
                throw new InvalidOperationException(
                    "Select one DFC_RESULT feature to refresh the target road segment."
                );
            }

            ReviewState = new EditorReviewState(updatedSelection);
            ChangeTypeMessage = updatedSelection.ChangeLabel;
            StatusMessage =
                $"DFC record {ReviewState.Selection.ObjectId} now references the selected Roads_Edit feature.";
        }
        catch (Exception exception)
        {
            StatusMessage = exception.Message;
            UpdateDfcObjectIdErrorMessage = exception.Message;
        }
    }

    public event PropertyChangedEventHandler? PropertyChanged;

    public EditorReviewState? ReviewState
    {
        get => _reviewState;
        private set
        {
            if (_reviewState == value)
            {
                return;
            }

            _reviewState = value;
            OnPropertyChanged();
            OnPropertyChanged(nameof(HasReviewState));
            OnPropertyChanged(nameof(AvailableReviewState));
            OnPropertyChanged(nameof(CanAddNew));
            OnPropertyChanged(nameof(CanEditRoadValues));
            OnPropertyChanged(nameof(RoadValueState));
            OnPropertyChanged(nameof(DisplayDfcStatus));
        }
    }

    public bool HasReviewState => ReviewState?.Selection?.UtransRoad is not null;

    public bool CanAddNew =>
        _selectedNewRecords.Count > 0 || ReviewState?.Selection?.IsNotYetCopiedNewRecord == true;

    public bool CanEditRoadValues => HasReviewState || CanAddNew;

    public bool HasMultipleNewRecords => _selectedNewRecords.Count > 1;

    public string DisplayDfcStatus =>
        HasMultipleNewRecords ? "COMPLETED" : ReviewState?.DfcStatus ?? string.Empty;

    public EditorReviewState AvailableReviewState => ReviewState ?? EmptyReviewState;
    public EditorReviewState RoadValueState =>
        _newRoadValueState ?? ReviewState ?? EmptyReviewState;

    public string ChangeTypeMessage
    {
        get => _changeTypeMessage;
        private set
        {
            if (_changeTypeMessage == value)
            {
                return;
            }

            _changeTypeMessage = value;
            OnPropertyChanged();
        }
    }

    public string SelectedDfcObjectIds
    {
        get => _selectedDfcObjectIds;
        private set
        {
            if (_selectedDfcObjectIds == value)
            {
                return;
            }

            _selectedDfcObjectIds = value;
            OnPropertyChanged();
        }
    }

    public int? RemainingDfcRecords
    {
        get => _remainingDfcRecords;
        private set
        {
            if (_remainingDfcRecords == value)
            {
                return;
            }

            _remainingDfcRecords = value;
            OnPropertyChanged();
        }
    }

    public string UtransDatabaseVersion
    {
        get => _utransDatabaseVersion;
        private set
        {
            if (_utransDatabaseVersion == value)
            {
                return;
            }

            _utransDatabaseVersion = value;
            OnPropertyChanged();
        }
    }

    public string StatusMessage
    {
        get => _statusMessage;
        private set
        {
            if (_statusMessage == value)
            {
                return;
            }

            _statusMessage = value;
            OnPropertyChanged();
        }
    }

    public string UpdateDfcObjectIdErrorMessage
    {
        get => _updateDfcObjectIdErrorMessage;
        private set
        {
            if (_updateDfcObjectIdErrorMessage == value)
            {
                return;
            }

            _updateDfcObjectIdErrorMessage = value;
            OnPropertyChanged();
        }
    }

    public ICommand AddNewCommand { get; }
    public ICommand SaveCommand { get; }
    public ICommand NextCommand { get; }
    public ICommand UpdateDfcObjectIdCommand { get; }
    public ICommand OpenLinkCommand { get; }
    public ICommand TransferAllCommand { get; }
    public ICommand ToggleFieldCommand { get; }
    public IReadOnlyList<CodedValueOption> CartocodeValues { get; private set; } = [];
    public IReadOnlyList<CodedValueOption> OnewayValues { get; private set; } = [];
    public IReadOnlyList<CodedValueOption> VerticalLevelValues { get; private set; } = [];
    public IReadOnlyList<CodedValueOption> StatusValues { get; private set; } = [];
    public IReadOnlyList<string> SpeedLimitValues { get; } = CreateRange(5, 80, 5);
    public IReadOnlyList<string> DfcStatusValues { get; } =
        new[] { "COMPLETED", "IGNORE", "REVISIT" };

    internal static void Show()
    {
        FrameworkApplication.DockPaneManager.Find(DockPaneId)?.Activate();
    }

    private async Task AddNewAsync()
    {
        if (_selectedNewRecords.Count == 0 && ReviewState is null)
        {
            return;
        }

        try
        {
            var layers = await _layerValidationService.GetRequiredLayersAsync();
            var selections =
                _selectedNewRecords.Count > 0 ? _selectedNewRecords
                : ReviewState?.Selection is { IsNotYetCopiedNewRecord: true } selection
                    ? [selection]
                : [];
            await _utransEditService.CreateNewUtransRoadsAsync(layers, selections, RoadValueState);
            ReviewState = null;
            SetSelectedNewRecords([]);
            RemainingDfcRecords = await _dfcSelectionService.GetRemainingCountAsync(layers);
            ChangeTypeMessage = SelectDfcFeatureMessage;
            StatusMessage =
                $"Created {selections.Count} UTRANS road(s) for DFC record(s) {string.Join(", ", selections.Select(selection => selection.ObjectId))}.";
        }
        catch (Exception exception)
        {
            StatusMessage = exception.Message;
        }
    }

    private async Task SaveAsync()
    {
        if (ReviewState is null)
        {
            return;
        }

        try
        {
            var layers = await _layerValidationService.GetRequiredLayersAsync();
            await _utransEditService.SaveAsync(layers, ReviewState);
            var savedObjectId = ReviewState.Selection.ObjectId;
            ReviewState = null;
            ChangeTypeMessage = SelectDfcFeatureMessage;
            StatusMessage = $"Saved DFC record {savedObjectId}.";
        }
        catch (Exception exception)
        {
            StatusMessage = exception.Message;
        }
    }

    private async Task SelectNextDfcAsync()
    {
        try
        {
            var layers = await _layerValidationService.GetRequiredLayersAsync();
            var nextObjectId = await _dfcNavigationService.SelectNextAndZoomAsync(layers);
            if (nextObjectId is null)
            {
                StatusMessage = "There are no more DFC_RESULT features to review.";
                return;
            }

            await LoadSelectedDfcAsync();
        }
        catch (Exception exception)
        {
            StatusMessage = exception.Message;
        }
    }

    private static void TransferAllValues(EditorReviewState? state)
    {
        if (state is null)
        {
            return;
        }

        foreach (var field in state.Fields)
        {
            field.TransferCountyValue();
        }
    }

    private void OnMapSelectionChanged(MapSelectionChangedEventArgs args)
    {
        QueueSelectionLoad();
    }

    private void OnActiveMapViewChanged(ActiveMapViewChangedEventArgs args)
    {
        if (args.IncomingView is not null)
        {
            _codedValueOptionsLoaded = false;
            QueueSelectionLoad();
        }
    }

    private void QueueSelectionLoad()
    {
        _ = Application.Current.Dispatcher.InvokeAsync(() => _ = LoadSelectedDfcAsync());
    }

    private async Task LoadSelectedDfcAsync()
    {
        try
        {
            var layers = await _layerValidationService.GetRequiredLayersAsync();
            var versionTask = _layerValidationService.GetUtransDatabaseVersionAsync(
                layers,
                DefaultVersionMessage
            );
            await LoadCodedValueOptionsAsync(layers);
            RemainingDfcRecords = await _dfcSelectionService.GetRemainingCountAsync(layers);
            UtransDatabaseVersion = await versionTask;

            var selectedNewRecords = await _dfcSelectionService.LoadSelectedNewRecordsAsync(layers);
            if (selectedNewRecords.Count > 0)
            {
                ReviewState = null;
                SetSelectedNewRecords(selectedNewRecords);
                ChangeTypeMessage = "New";
                StatusMessage =
                    $"Selected new DFC records {SelectedDfcObjectIds}. Click Add New to create UTRANS roads.";
                return;
            }

            SetSelectedNewRecords([]);

            var selection = await _dfcSelectionService.LoadSelectedAsync(layers);
            if (selection is null)
            {
                ReviewState = null;
                ChangeTypeMessage = SelectDfcFeatureMessage;
                StatusMessage = "No DFC_RESULT feature is currently selected.";
                return;
            }

            ReviewState = new EditorReviewState(selection);
            ChangeTypeMessage = selection.ChangeLabel;
            StatusMessage = $"{selection.ChangeLabel} DFC record {selection.ObjectId} loaded.";
        }
        catch (Exception exception)
        {
            ReviewState = null;
            SetSelectedNewRecords([]);
            ChangeTypeMessage = exception.Message;
            RemainingDfcRecords = null;
            StatusMessage = exception.Message;
        }
    }

    private void SetSelectedNewRecords(IReadOnlyList<DfcSelectionSnapshot> selections)
    {
        _selectedNewRecords = selections;
        _newRoadValueState = selections.Count switch
        {
            0 => null,
            1 => new EditorReviewState(selections[0]),
            _ => new EditorReviewState(),
        };
        SelectedDfcObjectIds = string.Join(
            ", ",
            selections.Select(selection => selection.ObjectId)
        );
        OnPropertyChanged(nameof(CanAddNew));
        OnPropertyChanged(nameof(CanEditRoadValues));
        OnPropertyChanged(nameof(HasMultipleNewRecords));
        OnPropertyChanged(nameof(DisplayDfcStatus));
        OnPropertyChanged(nameof(RoadValueState));
    }

    private async Task LoadCodedValueOptionsAsync(EditorLayerContext layers)
    {
        if (_codedValueOptionsLoaded)
        {
            return;
        }

        var options = await _layerValidationService.GetCodedValueOptionsAsync(layers);
        CartocodeValues = options["CARTOCODE"];
        OnewayValues = options["ONEWAY"];
        VerticalLevelValues = options["VERT_LEVEL"];
        StatusValues = options["STATUS"];
        _codedValueOptionsLoaded = true;
        OnPropertyChanged(nameof(CartocodeValues));
        OnPropertyChanged(nameof(OnewayValues));
        OnPropertyChanged(nameof(VerticalLevelValues));
        OnPropertyChanged(nameof(StatusValues));
    }

    private static IReadOnlyList<string> CreateRange(int start, int end)
    {
        var values = new List<string>();
        for (var value = start; value <= end; value++)
        {
            values.Add(value.ToString());
        }

        return values;
    }

    private void OnPropertyChanged([CallerMemberName] string? propertyName = null) =>
        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));

    private static IReadOnlyList<string> CreateRange(int start, int end, int increment)
    {
        var values = new List<string>();
        for (var value = start; value <= end; value += increment)
        {
            values.Add(value.ToString());
        }

        return values;
    }

    public EditorReviewState EffectiveReviewState => ReviewState ?? EmptyReviewState;
}

internal sealed class UtransEditorDockpaneButton : Button
{
    protected override void OnClick() => UtransEditorDockpaneViewModel.Show();
}
