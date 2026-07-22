using System;
using System.Windows.Input;

namespace UGRC.UtransTools.Infrastructure;

internal sealed class RelayCommand<T> : ICommand
{
    private readonly Action<T?> _execute;

    internal RelayCommand(Action<T?> execute)
    {
        _execute = execute;
    }

    public event EventHandler? CanExecuteChanged
    {
        add { }
        remove { }
    }

    public bool CanExecute(object? parameter) => parameter is T;

    public void Execute(object? parameter)
    {
        if (parameter is T value)
        {
            _execute(value);
        }
    }
}
