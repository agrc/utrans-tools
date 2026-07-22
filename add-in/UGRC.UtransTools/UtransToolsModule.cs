using ArcGIS.Desktop.Framework;
using ArcGIS.Desktop.Framework.Contracts;

namespace UGRC.UtransTools;

internal sealed class UtransToolsModule : Module
{
    private static UtransToolsModule? _current;

    internal static UtransToolsModule Current =>
        _current ??= (UtransToolsModule)FrameworkApplication.FindModule("UGRC.UtransTools_Module");

    protected override bool CanUnload() => true;
}
