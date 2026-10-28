using System.Windows;

namespace GeoStudio.UI.Services;

/// <summary>
/// Helper to reduce repetitive window management and lifecycle boilerplate across dialogs.
/// </summary>
public static class WindowHelper
{
    /// <summary>
    /// Restores the main window from minimized state and focuses it when a tool or dialog completes.
    /// </summary>
    public static void RestoreAndFocusMainWindow(Window? currentWindow = null)
    {
        var main = currentWindow?.Owner as MainWindow ?? Application.Current.MainWindow as MainWindow;
        if (main != null)
        {
            if (main.WindowState == WindowState.Minimized)
                main.WindowState = WindowState.Normal;
            main.Activate();
            main.Focus();
        }
    }
}
