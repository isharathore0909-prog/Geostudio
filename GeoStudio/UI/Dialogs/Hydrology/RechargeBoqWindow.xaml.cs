using System;
using System.IO;
using System.Text;
using System.Windows;
using System.Windows.Controls;
using Microsoft.Win32;
using GeoStudio.Hydrology.Models;
using GeoStudio.Hydrology.Services;

namespace GeoStudio.UI.Dialogs.Hydrology
{
    public partial class RechargeBoqWindow : Window
    {
        private StructureEstimate? _lastEstimate;

        public RechargeBoqWindow()
        {
            InitializeComponent();
            ComputeCurrent();
        }

        private void ComboStructureType_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            if (TxtLength == null || TxtHeight == null || TxtWidth == null) return;

            switch (ComboStructureType.SelectedIndex)
            {
                case 0: // Check Dam
                    LblLength.Text = "Length / Span (m):";
                    LblHeight.Text = "Weir Height (m):";
                    LblWidth.Text = "Top Width (m):";
                    TxtLength.Text = "25.0"; TxtHeight.Text = "2.5"; TxtWidth.Text = "1.8";
                    break;
                case 1: // Percolation Pond
                    LblLength.Text = "Basin Length (m):";
                    LblHeight.Text = "Water Depth (m):";
                    LblWidth.Text = "Bund Width (m):";
                    TxtLength.Text = "50.0"; TxtHeight.Text = "3.0"; TxtWidth.Text = "2.5";
                    break;
                case 2: // Farm Pond
                    LblLength.Text = "Side Length (m):";
                    LblHeight.Text = "Depth (m):";
                    LblWidth.Text = "Side Slope (1:x):";
                    TxtLength.Text = "20.0"; TxtHeight.Text = "3.0"; TxtWidth.Text = "1.5";
                    break;
                case 3: // Recharge Shaft
                    LblLength.Text = "Chamber Length (m):";
                    LblHeight.Text = "Bore Depth (m):";
                    LblWidth.Text = "Bore Dia (m):";
                    TxtLength.Text = "3.0"; TxtHeight.Text = "25.0"; TxtWidth.Text = "0.45";
                    break;
            }
            ComputeCurrent();
        }

        private void BtnCompute_Click(object sender, RoutedEventArgs e)
        {
            ComputeCurrent();
        }

        private void ComputeCurrent()
        {
            try
            {
                var type = (RechargeStructureType)ComboStructureType.SelectedIndex;
                double.TryParse(TxtLength.Text, out double L);
                double.TryParse(TxtHeight.Text, out double H);
                double.TryParse(TxtWidth.Text, out double W);
                double.TryParse(TxtFoundation.Text, out double Df);

                if (L <= 0) L = 20.0;
                if (H <= 0) H = 2.0;

                _lastEstimate = RechargeBoqService.Instance.CalculateBoq(type, L, H, W, Df);

                GridBoq.ItemsSource = null;
                GridBoq.ItemsSource = _lastEstimate.Items;

                TxtStorageCapacity.Text = $"Est. Storage Capacity: {_lastEstimate.StorageCapacityTcm:F2} TCM (Thousand m³)";
                TxtTotalCost.Text = $"Total Cost: ₹ {_lastEstimate.TotalEstimatedCostInr:N0}";
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Failed to calculate BOQ: {ex.Message}", "Calculation Error", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        private void BtnExportCsv_Click(object sender, RoutedEventArgs e)
        {
            if (_lastEstimate == null || _lastEstimate.Items.Count == 0) return;

            var sfd = new SaveFileDialog
            {
                Filter = "CSV Spreadsheet (*.csv)|*.csv",
                FileName = $"BOQ_Estimate_{_lastEstimate.Type}.csv"
            };

            if (sfd.ShowDialog() == true)
            {
                var sb = new StringBuilder();
                sb.AppendLine("Item_No,Description,Quantity,Unit,Unit_Rate_INR,Amount_INR");
                foreach (var line in _lastEstimate.Items)
                {
                    sb.AppendLine($"{line.ItemNo},\"{line.ItemDescription}\",{line.Quantity:F2},{line.Unit},{line.UnitRateInr},{line.TotalCostInr:F2}");
                }
                sb.AppendLine($",\"Sub-Total\",,,,{_lastEstimate.SubTotalInr:F2}");
                sb.AppendLine($",\"Total Estimated Cost (inc. 3% contingency + 2% QC)\",,,,{_lastEstimate.TotalEstimatedCostInr:F2}");

                File.WriteAllText(sfd.FileName, sb.ToString(), Encoding.UTF8);
                MessageBox.Show($"BOQ estimate exported to:\n{sfd.FileName}", "Export Successful", MessageBoxButton.OK, MessageBoxImage.Information);
            }
        }

        private void BtnClose_Click(object sender, RoutedEventArgs e) => Close();
    }
}
