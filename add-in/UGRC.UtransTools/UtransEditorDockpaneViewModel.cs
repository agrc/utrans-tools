using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Diagnostics;
using System.Runtime.CompilerServices;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Input;
using ArcGIS.Desktop.Framework;
using ArcGIS.Desktop.Framework.Contracts;
using ArcGIS.Desktop.Framework.Dialogs;
using ArcGIS.Desktop.Mapping.Events;
using UGRC.UtransTools.Infrastructure;
using UGRC.UtransTools.Models;
using UGRC.UtransTools.Services;

namespace UGRC.UtransTools;

internal sealed class UtransEditorDockpaneViewModel : DockPane, INotifyPropertyChanged
{
    private const string DockPaneId = "UGRC_UtransTools_UtransEditorDockpane";
    private const string DefaultVersionMessage = "not versioned";
    private static readonly EditorReviewState EmptyReviewState = new();
    private readonly LayerValidationService _layerValidationService = new();
    private readonly DfcSelectionService _dfcSelectionService = new();
    private readonly UtransEditService _utransEditService = new();
    private EditorReviewState? _reviewState;
    private int? _remainingDfcRecords;
    private string _changeTypeMessage = "Please select a feature from DFC_RESULT layer";
    private string _statusMessage = "Select one DFC_RESULT feature to load it in the editor";
    private string _utransDatabaseVersion = DefaultVersionMessage;
    private bool _codedValueOptionsLoaded;

    internal UtransEditorDockpaneViewModel()
    {
        SaveCommand = new AsyncRelayCommand(SaveAsync);
        NextCommand = new RelayCommand<object>(_ => StatusMessage = "Select the next DFC_RESULT feature to load it in the editor.");
        UpdateDfcObjectIdCommand = new AsyncRelayCommand(RepairDfcIdentifierAsync);
        TransferAllCommand = new RelayCommand<EditorReviewState>(TransferAllValues);
        ToggleFieldCommand = new RelayCommand<AttributeReviewField>(field => field.ToggleCountyValue());
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
            var layers = await _layerValidationService.GetRequiredLayersAsync();
            await _utransEditService.RepairDfcIdentifierAsync(layers, ReviewState);
            StatusMessage = $"DFC record {ReviewState.Selection.ObjectId} now references UTRANS feature {ReviewState.Selection.UtransRoad?.ObjectId}.";
        }
        catch (Exception exception)
        {
            StatusMessage = exception.Message;
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
        }
    }

    public bool HasReviewState => ReviewState is not null;

    public EditorReviewState AvailableReviewState => ReviewState ?? EmptyReviewState;

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

    public ICommand SaveCommand { get; }
    public ICommand NextCommand { get; }
    public ICommand UpdateDfcObjectIdCommand { get; }
    public ICommand OpenLinkCommand { get; }
    public ICommand TransferAllCommand { get; }
    public ICommand ToggleFieldCommand { get; }
    public IReadOnlyList<CodedValueOption> CartocodeValues { get; private set; } = [];
    public IReadOnlyList<CodedValueOption> OnewayValues { get; private set; } = [];
    public IReadOnlyList<CodedValueOption> VerticalLevelValues { get; private set; } = [];
    public IReadOnlyList<string> SpeedLimitValues { get; } = CreateRange(5, 80, 5);
    public IReadOnlyList<string> DfcStatusValues { get; } = new[] { "COMPLETED", "IGNORE", "REVISIT" };

    internal static void Show()
    {
        FrameworkApplication.DockPaneManager.Find(DockPaneId)?.Activate();
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
            StatusMessage = $"Saved DFC record {ReviewState.Selection.ObjectId}.";
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
            var versionTask = _layerValidationService.GetUtransDatabaseVersionAsync(layers, DefaultVersionMessage);
            await LoadCodedValueOptionsAsync(layers);
            RemainingDfcRecords = await _dfcSelectionService.GetRemainingCountAsync(layers);
            UtransDatabaseVersion = await versionTask;

            var selection = await _dfcSelectionService.LoadSelectedAsync(layers);
            if (selection is null)
            {
                ReviewState = null;
                ChangeTypeMessage = "Please select one feature from DFC_RESULT layer.";
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
            ChangeTypeMessage = exception.Message;
            RemainingDfcRecords = null;
            StatusMessage = exception.Message;
        }
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
        _codedValueOptionsLoaded = true;
        OnPropertyChanged(nameof(CartocodeValues));
        OnPropertyChanged(nameof(OnewayValues));
        OnPropertyChanged(nameof(VerticalLevelValues));
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
