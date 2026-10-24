using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;

namespace GeoStudio.UI.Components
{
    public partial class DialogHeader : UserControl
    {
        public static readonly DependencyProperty TitleProperty =
            DependencyProperty.Register(nameof(Title), typeof(string), typeof(DialogHeader),
                new PropertyMetadata("Tool Title", (d, e) => ((DialogHeader)d).TxtTitle.Text = (string)e.NewValue));

        public static readonly DependencyProperty DescriptionProperty =
            DependencyProperty.Register(nameof(Description), typeof(string), typeof(DialogHeader),
                new PropertyMetadata("Tool description", (d, e) => ((DialogHeader)d).TxtDescription.Text = (string)e.NewValue));

        public static readonly DependencyProperty IconProperty =
            DependencyProperty.Register(nameof(Icon), typeof(string), typeof(DialogHeader),
                new PropertyMetadata("⚙", (d, e) => ((DialogHeader)d).TxtIcon.Text = (string)e.NewValue));

        public static readonly DependencyProperty IconBrushProperty =
            DependencyProperty.Register(nameof(IconBrush), typeof(Brush), typeof(DialogHeader),
                new PropertyMetadata(new SolidColorBrush(Color.FromRgb(37, 99, 235)), (d, e) => ((DialogHeader)d).TxtIcon.Foreground = (Brush)e.NewValue));

        public static readonly DependencyProperty IconBgProperty =
            DependencyProperty.Register(nameof(IconBg), typeof(Brush), typeof(DialogHeader),
                new PropertyMetadata(new SolidColorBrush(Color.FromRgb(239, 246, 255)), (d, e) => ((DialogHeader)d).BorderIcon.Background = (Brush)e.NewValue));

        public static readonly DependencyProperty BadgeTextProperty =
            DependencyProperty.Register(nameof(BadgeText), typeof(string), typeof(DialogHeader),
                new PropertyMetadata(string.Empty, (d, e) =>
                {
                    var self = (DialogHeader)d;
                    var val = (string)e.NewValue;
                    if (string.IsNullOrWhiteSpace(val))
                    {
                        self.BadgeContainer.Visibility = Visibility.Collapsed;
                    }
                    else
                    {
                        self.BadgeContainer.Visibility = Visibility.Visible;
                        self.TxtBadge.Text = val;
                    }
                }));

        public string Title
        {
            get => (string)GetValue(TitleProperty);
            set => SetValue(TitleProperty, value);
        }

        public string Description
        {
            get => (string)GetValue(DescriptionProperty);
            set => SetValue(DescriptionProperty, value);
        }

        public string Icon
        {
            get => (string)GetValue(IconProperty);
            set => SetValue(IconProperty, value);
        }

        public Brush IconBrush
        {
            get => (Brush)GetValue(IconBrushProperty);
            set => SetValue(IconBrushProperty, value);
        }

        public Brush IconBg
        {
            get => (Brush)GetValue(IconBgProperty);
            set => SetValue(IconBgProperty, value);
        }

        public string BadgeText
        {
            get => (string)GetValue(BadgeTextProperty);
            set => SetValue(BadgeTextProperty, value);
        }

        public DialogHeader()
        {
            InitializeComponent();
        }
    }
}
