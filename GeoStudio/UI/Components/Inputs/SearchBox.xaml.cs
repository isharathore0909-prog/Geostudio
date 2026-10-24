using System;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;

namespace GeoStudio.UI.Components
{
    public partial class SearchBox : UserControl
    {
        public static readonly DependencyProperty ExtraButtonTextProperty =
            DependencyProperty.Register(nameof(ExtraButtonText), typeof(string), typeof(SearchBox),
                new PropertyMetadata(string.Empty, (d, e) =>
                {
                    var self = (SearchBox)d;
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

        public string ExtraButtonText
        {
            get => (string)GetValue(ExtraButtonTextProperty);
            set => SetValue(ExtraButtonTextProperty, value);
        }

        public string Text
        {
            get => InputBox.Text;
            set => InputBox.Text = value;
        }

        public event EventHandler<TextChangedEventArgs>? TextChanged;
        public event KeyEventHandler? SearchKeyDown;
        public event EventHandler<RoutedEventArgs>? ExtraButtonClick;

        public SearchBox()
        {
            InitializeComponent();
        }

        public void FocusInput()
        {
            InputBox.Focus();
        }

        private void InputBox_TextChanged(object sender, TextChangedEventArgs e)
        {
            BtnClear.Visibility = string.IsNullOrEmpty(InputBox.Text) ? Visibility.Collapsed : Visibility.Visible;
            TextChanged?.Invoke(this, e);
        }

        private void InputBox_KeyDown(object sender, KeyEventArgs e)
        {
            SearchKeyDown?.Invoke(this, e);
        }

        private void BtnClear_Click(object sender, RoutedEventArgs e)
        {
            InputBox.Text = string.Empty;
            InputBox.Focus();
        }

        private void BtnExtra_Click(object sender, RoutedEventArgs e)
        {
            ExtraButtonClick?.Invoke(this, e);
        }
    }
}
