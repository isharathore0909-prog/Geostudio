using System.Configuration;
using System.Data;
using System.IO;
using System.Windows;

namespace GeoStudio;

/// <summary>
/// Interaction logic for App.xaml
/// </summary>
public partial class App : Application
{
    protected override void OnStartup(StartupEventArgs e)
    {
        DispatcherUnhandledException += (s, args) =>
        {
            System.Diagnostics.Debug.WriteLine($"[UNHANDLED UI EXCEPTION] {args.Exception}");
            MessageBox.Show($"An unexpected error occurred:\n{args.Exception.Message}", "GeoStudio", MessageBoxButton.OK, MessageBoxImage.Warning);
            args.Handled = true;
        };

        AppDomain.CurrentDomain.UnhandledException += (s, args) =>
        {
            if (args.ExceptionObject is Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[FATAL DOMAIN EXCEPTION] {ex}");
                MessageBox.Show($"Application error:\n{ex.Message}", "GeoStudio Error", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        };

        Environment.SetEnvironmentVariable("WEBVIEW2_DEFAULT_BACKGROUND_COLOR", "0xFFFFFFFF");
        if (e.Args.Length > 1 && e.Args[0] == "--test-preview")
        {
            try
            {
                var meta = Raster.GdalRasterService.InspectAndGeneratePreview(e.Args[1]);
                long sz = File.Exists(meta.PreviewImagePath) ? new FileInfo(meta.PreviewImagePath).Length : 0;
                Console.WriteLine($"TEST_RESULT|IsElevation={meta.IsElevation}|Min={meta.MinElevation}|Max={meta.MaxElevation}|PreviewPath={meta.PreviewImagePath}|FileSize={sz}");
            }
            catch (Exception ex)
            {
                Console.WriteLine($"TEST_ERR: {ex.Message}\n{ex.StackTrace}");
            }
            Shutdown();
            return;
        }
        base.OnStartup(e);
    }
}

