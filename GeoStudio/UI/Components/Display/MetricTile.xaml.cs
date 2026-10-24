using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;

namespace GeoStudio.UI.Components
{
    public partial class MetricTile : UserControl
    {
        public static readonly DependencyProperty LabelProperty =
            DependencyProperty.Register(nameof(Label), typeof(string), typeof(MetricTile),
                new PropertyMetadata("LABEL", (d, e) => ((MetricTile)d).TxtLabel.Text = (string)e.NewValue));

        public static readonly DependencyProperty ValueProperty =
            DependencyProperty.Register(nameof(Value), typeof(string), typeof(MetricTile),
                new PropertyMetadata("--", (d, e) => ((MetricTile)d).TxtValue.Text = (string)e.NewValue));

        public static readonly DependencyProperty SubtextProperty =
            DependencyProperty.Register(nameof(Subtext), typeof(string), typeof(MetricTile),
                new PropertyMetadata(string.Empty, (d, e) =>
                {
                    var self = (MetricTile)d;
                    var text = (string)e.NewValue;
                    self.TxtSubtext.Text = text;
                    self.TxtSubtext.Visibility = string.IsNullOrWhiteSpace(text) ? Visibility.Collapsed : Visibility.Visible;
                }));

        public static readonly DependencyProperty LabelBrushProperty =
            DependencyProperty.Register(nameof(LabelBrush), typeof(Brush), typeof(MetricTile),
                new PropertyMetadata(null, (d, e) =>
                {
                    if (e.NewValue is Brush b) ((MetricTile)d).TxtLabel.Foreground = b;
                }));

        public static readonly DependencyProperty ValueBrushProperty =
            DependencyProperty.Register(nameof(ValueBrush), typeof(Brush), typeof(MetricTile),
                new PropertyMetadata(null, (d, e) =>
                {
                    if (e.NewValue is Brush b) ((MetricTile)d).TxtValue.Foreground = b;
                }));

        public static readonly DependencyProperty TileBackgroundProperty =
            DependencyProperty.Register(nameof(TileBackground), typeof(Brush), typeof(MetricTile),
                new PropertyMetadata(null, (d, e) =>
                {
                    if (e.NewValue is Brush b) ((MetricTile)d).BorderContainer.Background = b;
                }));

        public static readonly DependencyProperty TileBorderBrushProperty =
            DependencyProperty.Register(nameof(TileBorderBrush), typeof(Brush), typeof(MetricTile),
                new PropertyMetadata(null, (d, e) =>
                {
                    if (e.NewValue is Brush b) ((MetricTile)d).BorderContainer.BorderBrush = b;
                }));

        public string Label
        {
            get => (string)GetValue(LabelProperty);
            set => SetValue(LabelProperty, value);
        }

        public string Value
        {
            get => (string)GetValue(ValueProperty);
            set => SetValue(ValueProperty, value);
        }

        public string Text
        {
            get => Value;
            set => Value = value;
        }

        public string Subtext
        {
            get => (string)GetValue(SubtextProperty);
            set => SetValue(SubtextProperty, value);
        }

        public Brush LabelBrush
        {
            get => (Brush)GetValue(LabelBrushProperty);
            set => SetValue(LabelBrushProperty, value);
        }

        public Brush ValueBrush
        {
            get => (Brush)GetValue(ValueBrushProperty);
            set => SetValue(ValueBrushProperty, value);
        }

        public Brush TileBackground
        {
            get => (Brush)GetValue(TileBackgroundProperty);
            set => SetValue(TileBackgroundProperty, value);
        }

        public Brush TileBorderBrush
        {
            get => (Brush)GetValue(TileBorderBrushProperty);
            set => SetValue(TileBorderBrushProperty, value);
        }

        public MetricTile()
        {
            InitializeComponent();
        }
    }
}
