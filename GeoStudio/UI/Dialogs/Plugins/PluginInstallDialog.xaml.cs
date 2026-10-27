using System.Windows;
using System.Windows.Media;
using GeoStudio.Models;
using GeoStudio.UI.Services;

namespace GeoStudio.UI.Dialogs.Plugins
{
    public partial class PluginInstallDialog : Window
    {
        private readonly PluginManifest _plugin;

        public PluginInstallDialog(PluginManifest plugin)
        {
            InitializeComponent();
            _plugin = plugin;
            UpdateUi();
        }

        private void UpdateUi()
        {
            TxtIcon.Text = _plugin.IconEmoji;
            TxtName.Text = _plugin.Name;
            TxtCategory.Text = $"{_plugin.Category} • v{_plugin.Version}";
            TxtDescription.Text = _plugin.Description;
            TxtSize.Text = $"{_plugin.DownloadSizeMb:F1} MB";
            TxtEngine.Text = _plugin.EngineType;

            if (_plugin.IsInstalled)
            {
                TxtBadge.Text = "INSTALLED & ACTIVE";
                TxtBadge.Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#15803D"));
                BadgeStatus.Background = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#DCFCE7"));
                BtnInstall.Visibility = Visibility.Collapsed;
                BtnUninstall.Visibility = Visibility.Visible;
            }
            else
            {
                TxtBadge.Text = "NOT INSTALLED";
                TxtBadge.Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#475569"));
                BadgeStatus.Background = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#F1F5F9"));
                BtnInstall.Visibility = Visibility.Visible;
                BtnUninstall.Visibility = Visibility.Collapsed;
            }
        }

        private async void BtnInstall_Click(object sender, RoutedEventArgs e)
        {
            BtnInstall.IsEnabled = false;
            BtnInstall.Content = "Installing...";
            try
            {
                await PluginManagerService.Instance.InstallPluginAsync(_plugin);
                UpdateUi();
            }
            finally
            {
                BtnInstall.IsEnabled = true;
                BtnInstall.Content = "📥 Install Plugin";
            }
        }

        private async void BtnUninstall_Click(object sender, RoutedEventArgs e)
        {
            BtnUninstall.IsEnabled = false;
            BtnUninstall.Content = "Uninstalling...";
            try
            {
                await PluginManagerService.Instance.UninstallPluginAsync(_plugin);
                UpdateUi();
            }
            finally
            {
                BtnUninstall.IsEnabled = true;
                BtnUninstall.Content = "🗑️ Uninstall";
            }
        }

        private void BtnOpenAll_Click(object sender, RoutedEventArgs e)
        {
            Close();
            var hub = new PluginManagerWindow { Owner = Application.Current.MainWindow };
            hub.ShowDialog();
        }

        private void BtnClose_Click(object sender, RoutedEventArgs e) => Close();
    }
}
