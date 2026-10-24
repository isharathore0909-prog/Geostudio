using System;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;

namespace GeoStudio.UI.Components
{
    public partial class ToolActionBar : UserControl
    {
        public static readonly DependencyProperty ActionTextProperty =
            DependencyProperty.Register(nameof(ActionText), typeof(string), typeof(ToolActionBar),
                new PropertyMetadata("Run", (d, e) => ((ToolActionBar)d).BtnRun.Content = (string)e.NewValue));

        public static readonly DependencyProperty CancelTextProperty =
            DependencyProperty.Register(nameof(CancelText), typeof(string), typeof(ToolActionBar),
                new PropertyMetadata("Cancel", (d, e) => ((ToolActionBar)d).BtnCancel.Content = (string)e.NewValue));

        public static readonly DependencyProperty ActionBackgroundProperty =
            DependencyProperty.Register(nameof(ActionBackground), typeof(Brush), typeof(ToolActionBar),
                new PropertyMetadata(null, (d, e) =>
                {
                    if (e.NewValue is Brush brush)
                    {
                        var self = (ToolActionBar)d;
                        self.BtnRun.Background = brush;
                        self.ProgressBar.Foreground = brush;
                    }
                }));

        public string ActionText
        {
            get => (string)GetValue(ActionTextProperty);
            set => SetValue(ActionTextProperty, value);
        }

        public string CancelText
        {
            get => (string)GetValue(CancelTextProperty);
            set => SetValue(CancelTextProperty, value);
        }

        public Brush ActionBackground
        {
            get => (Brush)GetValue(ActionBackgroundProperty);
            set => SetValue(ActionBackgroundProperty, value);
        }

        public string StatusText
        {
            get => TxtStatus.Text;
            set => TxtStatus.Text = value;
        }

        public double Progress
        {
            get => ProgressBar.Value;
            set => ProgressBar.Value = value;
        }

        public bool IsBusy
        {
            get => ProgressBar.Visibility == Visibility.Visible;
            set
            {
                ProgressBar.Visibility = value ? Visibility.Visible : Visibility.Collapsed;
                BtnRun.IsEnabled = !value;
            }
        }

        public event EventHandler<RoutedEventArgs>? RunClick;
        public event EventHandler<RoutedEventArgs>? CancelClick;

        public ToolActionBar()
        {
            InitializeComponent();
        }

        private void BtnRun_Click(object sender, RoutedEventArgs e)
        {
            RunClick?.Invoke(this, e);
        }

        private void BtnCancel_Click(object sender, RoutedEventArgs e)
        {
            CancelClick?.Invoke(this, e);
        }
    }
}
