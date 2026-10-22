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

