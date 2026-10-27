using System;
using System.Windows;
using System.Windows.Controls;

namespace GeoStudio.UI.Dialogs.Hydrology
{
    public partial class CropWaterPlannerWindow : Window
    {
        public CropWaterPlannerWindow()
        {
            InitializeComponent();
        }

        private void BtnGeneratePlan_Click(object sender, RoutedEventArgs e)
        {
            if (!double.TryParse(TxtRainfall.Text, out double rainfall))
            {
                MessageBox.Show("Please enter a valid rainfall value in mm.", "Invalid Input", MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }

            bool isLowWater = rainfall < 450 || ComboGwStatus.SelectedIndex >= 2;

            if (isLowWater)
            {
                TxtKharif.Text = "• Bajra (Pearl Millet), Moong (Green Gram), Moth Bean, Cluster Bean (Guar)";
                TxtRabi.Text = "• Mustard (Pusa Bold / RH-30), Gram (Chickpea), Barley";
                TxtHorticulture.Text = "• Pomegranate (Bhagwa), Ber (Gola/Seb), Date Palm, Aonla (NA-7)";
                TxtVegetables.Text = "• Garlic (Drip), Chilli (Mulched), Coriander (Seed)";
            }
            else
            {
                TxtKharif.Text = "• Soybean, Maize, Groundnut, Cotton, Moong";
                TxtRabi.Text = "• Wheat (GW-322), Mustard, Chickpea, Green Vegetables";
                TxtHorticulture.Text = "• Guava (Taiwan Pink), Orange / Kinnow, Lemon (Kagzi), Papaya";
                TxtVegetables.Text = "• Tomato (Protected trellis), Onion, Capsicum, Watermelon";
            }
        }

        private void BtnClose_Click(object sender, RoutedEventArgs e) => Close();
    }
}
