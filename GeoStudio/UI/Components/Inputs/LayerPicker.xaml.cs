using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Windows;
using System.Windows.Controls;
using Microsoft.Win32;
using GeoStudio.Models;

namespace GeoStudio.UI.Components
{
    public partial class LayerPicker : UserControl
    {
        public static readonly DependencyProperty LabelProperty =
            DependencyProperty.Register(nameof(Label), typeof(string), typeof(LayerPicker),
                new PropertyMetadata("Select Layer:", (d, e) => ((LayerPicker)d).TxtLabel.Text = (string)e.NewValue));

        public static readonly DependencyProperty ShowBrowseButtonProperty =
            DependencyProperty.Register(nameof(ShowBrowseButton), typeof(bool), typeof(LayerPicker),
                new PropertyMetadata(true, (d, e) => ((LayerPicker)d).BtnBrowse.Visibility = (bool)e.NewValue ? Visibility.Visible : Visibility.Collapsed));

        public static readonly DependencyProperty BrowseTitleProperty =
            DependencyProperty.Register(nameof(BrowseTitle), typeof(string), typeof(LayerPicker),
                new PropertyMetadata("Select Dataset"));

        public static readonly DependencyProperty BrowseFilterProperty =
            DependencyProperty.Register(nameof(BrowseFilter), typeof(string), typeof(LayerPicker),
                new PropertyMetadata("All Supported Files (*.*)|*.*"));

        public static readonly DependencyProperty ExtraActionTextProperty =
            DependencyProperty.Register(nameof(ExtraActionText), typeof(string), typeof(LayerPicker),
                new PropertyMetadata(string.Empty, (d, e) =>
                {
                    var self = (LayerPicker)d;
                    var text = (string)e.NewValue;
                    if (string.IsNullOrEmpty(text))
                    {
                        self.BtnExtra.Visibility = Visibility.Collapsed;
                    }
                    else
                    {
                        self.BtnExtra.Visibility = Visibility.Visible;
                        self.BtnExtra.Content = text;
                    }
                }));

        public static readonly DependencyProperty ExtraActionToolTipProperty =
            DependencyProperty.Register(nameof(ExtraActionToolTip), typeof(string), typeof(LayerPicker),
                new PropertyMetadata(string.Empty, (d, e) => ((LayerPicker)d).BtnExtra.ToolTip = (string)e.NewValue));

        public string Label
        {
            get => (string)GetValue(LabelProperty);
            set => SetValue(LabelProperty, value);
        }

        public bool ShowBrowseButton
        {
            get => (bool)GetValue(ShowBrowseButtonProperty);
            set => SetValue(ShowBrowseButtonProperty, value);
        }

        public string BrowseTitle
        {
            get => (string)GetValue(BrowseTitleProperty);
            set => SetValue(BrowseTitleProperty, value);
        }

        public string BrowseFilter
        {
            get => (string)GetValue(BrowseFilterProperty);
            set => SetValue(BrowseFilterProperty, value);
        }

        public string ExtraActionText
        {
            get => (string)GetValue(ExtraActionTextProperty);
            set => SetValue(ExtraActionTextProperty, value);
        }

        public string ExtraActionToolTip
        {
            get => (string)GetValue(ExtraActionToolTipProperty);
            set => SetValue(ExtraActionToolTipProperty, value);
        }

        public event EventHandler<SelectionChangedEventArgs>? SelectionChanged;
        public event EventHandler<RoutedEventArgs>? ExtraActionClick;

        private string? _customFilePath;

        public LayerPicker()
        {
            InitializeComponent();
        }

        public void Populate(IEnumerable<LayerItem> layers, Func<LayerItem, bool>? filter = null)
        {
            ComboLayers.Items.Clear();
            var filtered = filter != null ? layers.Where(filter) : layers;

            foreach (var l in filtered)
            {
                ComboLayers.Items.Add(new ComboBoxItem
                {
                    Content = l.Name,
                    Tag = l.FilePath
                });
            }

            if (ComboLayers.Items.Count > 0)
                ComboLayers.SelectedIndex = 0;
        }

        public string? SelectedPath
        {
            get
            {
                if (!string.IsNullOrEmpty(_customFilePath))
                    return _customFilePath;

                if (ComboLayers.SelectedItem is ComboBoxItem item && item.Tag is string path)
                    return path;

                return null;
            }
            set
            {
                _customFilePath = value;
                if (!string.IsNullOrEmpty(value))
                {
                    foreach (ComboBoxItem item in ComboLayers.Items)
                    {
                        if (item.Tag is string path && string.Equals(path, value, StringComparison.OrdinalIgnoreCase))
                        {
                            ComboLayers.SelectedItem = item;
                            return;
                        }
                    }
                    AddCustomItem(Path.GetFileName(value), value, select: true);
                }
            }
        }

        public ComboBox ComboBoxControl => ComboLayers;
        public Button ExtraButtonControl => BtnExtra;

        public void AddCustomItem(string label, string path, bool select = true)
        {
            _customFilePath = path;
            var item = new ComboBoxItem
            {
                Content = label,
                Tag = path
            };
            ComboLayers.Items.Insert(0, item);
            if (select)
            {
                ComboLayers.SelectedItem = item;
            }
        }

        public void SetBadge(string text, bool visible = true)
        {
            TxtBadge.Text = text;
            BadgeBorder.Visibility = visible ? Visibility.Visible : Visibility.Collapsed;
        }

        public void ClearBadge()
        {
            BadgeBorder.Visibility = Visibility.Collapsed;
        }

        private void ComboLayers_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            _customFilePath = null;
            SelectionChanged?.Invoke(this, e);
        }

        private void BtnBrowse_Click(object sender, RoutedEventArgs e)
        {
            var dlg = new OpenFileDialog
            {
                Title = BrowseTitle,
                Filter = BrowseFilter
            };

            if (dlg.ShowDialog() == true)
            {
                AddCustomItem($"[File] {Path.GetFileName(dlg.FileName)}", dlg.FileName, select: true);
            }
        }

        private void BtnExtra_Click(object sender, RoutedEventArgs e)
        {
            ExtraActionClick?.Invoke(this, e);
        }
    }
}
