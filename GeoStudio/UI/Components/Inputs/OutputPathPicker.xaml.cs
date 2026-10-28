using System;
using System.IO;
using System.Windows;
using System.Windows.Controls;
using GeoStudio.UI.Services;

namespace GeoStudio.UI.Components
{
    public partial class OutputPathPicker : UserControl
    {
        public static readonly DependencyProperty LabelProperty =
            DependencyProperty.Register(nameof(Label), typeof(string), typeof(OutputPathPicker),
                new PropertyMetadata("Output Path:", (d, e) => ((OutputPathPicker)d).TxtLabel.Text = (string)e.NewValue));

        public static readonly DependencyProperty HelperTextProperty =
            DependencyProperty.Register(nameof(HelperText), typeof(string), typeof(OutputPathPicker),
                new PropertyMetadata(string.Empty, (d, e) =>
                {
                    var self = (OutputPathPicker)d;
                    var text = (string)e.NewValue;
                    self.TxtHelper.Text = text;
                    self.TxtHelper.Visibility = string.IsNullOrWhiteSpace(text) ? Visibility.Collapsed : Visibility.Visible;
                }));

        public static readonly DependencyProperty DialogTitleProperty =
            DependencyProperty.Register(nameof(DialogTitle), typeof(string), typeof(OutputPathPicker),
                new PropertyMetadata("Save Output File"));

        public static readonly DependencyProperty FileFilterProperty =
            DependencyProperty.Register(nameof(FileFilter), typeof(string), typeof(OutputPathPicker),
                new PropertyMetadata("GeoTIFF (*.tif)|*.tif|All Files (*.*)|*.*"));

        public static readonly DependencyProperty DefaultExtensionProperty =
            DependencyProperty.Register(nameof(DefaultExtension), typeof(string), typeof(OutputPathPicker),
                new PropertyMetadata(".tif"));

        public string Label
        {
            get => (string)GetValue(LabelProperty);
            set => SetValue(LabelProperty, value);
        }

        public string HelperText
        {
            get => (string)GetValue(HelperTextProperty);
            set => SetValue(HelperTextProperty, value);
        }

        public string DialogTitle
        {
            get => (string)GetValue(DialogTitleProperty);
            set => SetValue(DialogTitleProperty, value);
        }

        public string FileFilter
        {
            get => (string)GetValue(FileFilterProperty);
            set => SetValue(FileFilterProperty, value);
        }

        public string DefaultExtension
        {
            get => (string)GetValue(DefaultExtensionProperty);
            set => SetValue(DefaultExtensionProperty, value);
        }

        public string PathText
        {
            get => TxtPath.Text.Trim();
            set => TxtPath.Text = value;
        }

        public event EventHandler<TextChangedEventArgs>? PathChanged;

        public OutputPathPicker()
        {
            InitializeComponent();
        }

        public void SetAutoPath(string? inputPath, string suffix = "_output.tif")
        {
            if (string.IsNullOrWhiteSpace(inputPath)) return;

            try
            {
                string dir = Path.GetDirectoryName(inputPath) ?? AppDomain.CurrentDomain.BaseDirectory;
                string baseName = Path.GetFileNameWithoutExtension(inputPath);
                PathText = Path.Combine(dir, $"{baseName}{suffix}");
            }
            catch
            {
                // Fallback
            }
        }

        private void TxtPath_TextChanged(object sender, TextChangedEventArgs e)
        {
            PathChanged?.Invoke(this, e);
        }

        private void BtnBrowse_Click(object sender, RoutedEventArgs e)
        {
            string defaultName = !string.IsNullOrEmpty(PathText) ? Path.GetFileName(PathText) : $"output{DefaultExtension}";
            if (FileDialogHelper.PromptSave(FileFilter, defaultName, DialogTitle) is { } path)
            {
                PathText = path;
            }
        }
    }
}
