using System;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;

namespace GeoStudio.UI.Dialogs.Hydrology
{
    public partial class CropWaterPlannerWindow : Window
    {
        public CropWaterPlannerWindow()
        {
            InitializeComponent();
            Loaded += (s, e) => BtnGeneratePlan_Click(this, new RoutedEventArgs());
        }

        private void BtnGeneratePlan_Click(object sender, RoutedEventArgs e)
        {
            if (!double.TryParse(TxtRainfall.Text, out double rainfall) || rainfall <= 0)
            {
                MessageBox.Show("Please enter a valid positive rainfall value in mm.", "Invalid Input", MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }

            int gwIdx = ComboGwStatus.SelectedIndex; // 0: Safe, 1: Semi-Critical, 2: Critical, 3: Over-Exploited
            int aqIdx = ComboAquifer.SelectedIndex;   // 0: Alluvium, 1: Sandstone/Limestone, 2: Hard Rock, 3: Basalt

            // CGWB Water Availability Index (WAI) Scoring
            double gwScore = gwIdx switch
            {
                3 => 20.0, // Over-Exploited
                2 => 45.0, // Critical
                1 => 70.0, // Semi-Critical
                _ => 100.0 // Safe
            };

            double aqScore = aqIdx switch
            {
                2 => 40.0, // Hard rock
                3 => 45.0, // Basalt
                1 => 60.0, // Sandstone / Limestone
                _ => 100.0 // Alluvium
            };

            double depthScore = (gwIdx >= 2) ? 30.0 : 60.0;
            double rainScore = rainfall < 300 ? 20.0 : (rainfall < 450 ? 40.0 : (rainfall < 600 ? 65.0 : 90.0));

            double wai = (0.40 * gwScore) + (0.25 * depthScore) + (0.20 * rainScore) + (0.15 * aqScore);

            // Hydrological safety caps for water-stressed blocks
            if (gwIdx == 3) wai = Math.Min(38.0, wai); // OE capped strictly to Tier 1
            else if (gwIdx == 2) wai = Math.Min(54.0, wai); // Critical capped to Tier 2

            int tier = (wai < 40.0) ? 1 : ((wai < 55.0) ? 2 : ((wai < 70.0) ? 3 : 4));

            // Calibrated Crop Recommendations & Irrigation Technology
            if (tier == 1)
            {
                TxtKharif.Text = "• Bajra (Pearl Millet), Moth Bean, Cluster Bean (Guar)";
                TxtRabi.Text = "• Isabgol (GI-2), Barley (RD-2035), Low-water Mustard (RH-30)";
                TxtHorticulture.Text = "• Date Palm (Barhee / Khadrawy), Aloe Vera (Barbadensis), Ber (Gola / Seb)";
                TxtVegetables.Text = "• None recommended (Extreme groundwater deficit)";
                TxtIrrigation.Text = "• Pressurized Sprinkler (field crops) + Mandatory Underground PVC Piped Conveyance (eliminate 25-30% conveyance transit loss)";
            }
            else if (tier == 2)
            {
                TxtKharif.Text = "• Moong (Green Gram), Bajra, Cluster Bean (Guar), Groundnut (Sandy loam only)";
                TxtRabi.Text = "• Cumin (GC-4), Mustard (Pusa Bold), Gram (Chickpea), Isabgol";
                TxtHorticulture.Text = "• Pomegranate (Bhagwa), Ber (Umran), Aonla (NA-7), Dragon Fruit";
                TxtVegetables.Text = "• Garlic (Drip + Mulch), Chilli (Drip), Seed Coriander";
                TxtIrrigation.Text = "• Micro-sprinkler for Cumin (canopy dry to prevent Alternaria blight) | Inline Drip for Vegetables | Pressurized Sprinkler for Mustard";
            }
            else if (tier == 3)
            {
                TxtKharif.Text = "• Groundnut, Cotton (Bt), Soybean, Maize, Moong";
                TxtRabi.Text = "• Mustard (High yield), Gram (Chickpea), Wheat (GW-322 / Raj-4037)";
                TxtHorticulture.Text = "• Guava (L-49 / Taiwan Pink), Mandarin Orange (Nagpur Santra), Kagzi Lemon";
                TxtVegetables.Text = "• Tomato (Staked Drip), Rabi Onion, Capsicum, Watermelon";
                TxtIrrigation.Text = "• Precision Drip + Fertigation (Cotton/Veg/Orchards) | Mini-Sprinkler & Border Strip (Wheat/Mustard)";
            }
            else
            {
                TxtKharif.Text = "• Soybean, Maize, Cotton, Groundnut";
                TxtRabi.Text = "• Wheat (GW-322), Mustard (Pusa Jai Kisan), Gram, Green Vegetables";
                TxtHorticulture.Text = "• Kinnow (Abohar), Guava (L-49), Kagzi Lemon, Mango (Amrapali)";
                TxtVegetables.Text = "• High-yielding Tomato, Onion, Capsicum, Cauliflower";
                TxtIrrigation.Text = "• Pressurized Drip & Canal scheduled supply | Underground Piped Distribution";
            }

            ScrollResults?.ScrollToTop();
        }

        private void BtnClose_Click(object sender, RoutedEventArgs e) => Close();
    }
}
