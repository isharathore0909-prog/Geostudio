using System.Windows;
using System.Windows.Controls;
using GeoStudio.Models;
using GeoStudio.UI.Services;

namespace GeoStudio.UI.Components
{
    public partial class PluginCardControl : UserControl
    {
        public PluginCardControl()
        {
            InitializeComponent();
        }

        private async void BtnAction_Click(object sender, RoutedEventArgs e)
        {
            if (DataContext is PluginManifest plugin)
            {
                BtnAction.IsEnabled = false;
                try
                {
                    await PluginManagerService.Instance.TogglePluginAsync(plugin);
                }
                finally
                {
                    BtnAction.IsEnabled = true;
                }
            }
        }
    }
}
