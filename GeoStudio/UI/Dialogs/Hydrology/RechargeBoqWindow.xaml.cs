using System;
using System.IO;
using System.Linq;
using System.Text;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using GeoStudio.Hydrology.Models;
using GeoStudio.Hydrology.Services;
using GeoStudio.UI.Services;

namespace GeoStudio.UI.Dialogs.Hydrology
{
    public partial class RechargeBoqWindow : Window
    {
        private StructureEstimate? _lastEstimate;
        private MasterPlanCalculationResult? _lastMacroResult;

        public RechargeBoqWindow()
        {
            InitializeComponent();
            PopulateDistricts();
            RunDefaultEvaluations();
        }

        private void PopulateDistricts()
        {
            var districts = CgwbMasterPlanService.Instance.GetAllDistricts();
            
            ComboSiteDistrict.Items.Clear();
            ComboMacroDistrict.Items.Clear();

            foreach (var d in districts)
            {
                string icon = d.Region == RajasthanRegion.WesternArid ? "🏜️" : "💧";
                string label = $"{icon} {d.DistrictName}";

                ComboSiteDistrict.Items.Add(new ComboBoxItem { Content = label, Tag = d.DistrictName });
                ComboMacroDistrict.Items.Add(new ComboBoxItem { Content = label, Tag = d.DistrictName });
            }

            // Select Bhilwara or first eastern district by default
            int defaultIdx = districts.ToList().FindIndex(x => x.DistrictName.Equals("Bhilwara", StringComparison.OrdinalIgnoreCase));
            if (defaultIdx >= 0)
            {
                ComboSiteDistrict.SelectedIndex = defaultIdx;
                ComboMacroDistrict.SelectedIndex = defaultIdx;
            }
            else if (ComboSiteDistrict.Items.Count > 0)
            {
                ComboSiteDistrict.SelectedIndex = 0;
                ComboMacroDistrict.SelectedIndex = 0;
            }
        }

        private void RunDefaultEvaluations()
        {
            EvaluateCurrentSite();
            ComputeCurrentBoq();
            ComputeCurrentMacro();
        }

        // ==================== TAB 1: SITE-SPECIFIC SITING & BOQ ====================

        private void ComboSiteDistrict_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            if (ComboSiteDistrict.SelectedItem is not ComboBoxItem item || item.Tag is not string distName) return;

            var profile = CgwbMasterPlanService.Instance.GetDistrict(distName);
            if (profile != null && TxtSiteDtw != null && TxtSiteEc != null)
            {
                TxtSiteDtw.Text = profile.DefaultDtwMeters.ToString("F1");
                TxtSiteEc.Text = profile.DefaultEcMicroSiemens.ToString("F0");

                if (profile.Region == RajasthanRegion.WesternArid)
                {
                    ComboSiteLithology.SelectedIndex = 3; // Desert sand
                }
                else
                {
                    ComboSiteLithology.SelectedIndex = 0; // Weathered hard rock
                }
            }
        }

        private void BtnEvaluateSite_Click(object sender, RoutedEventArgs e)
        {
            EvaluateCurrentSite();
        }

        private void EvaluateCurrentSite()
        {
            try
            {
                string distName = (ComboSiteDistrict.SelectedItem as ComboBoxItem)?.Tag as string ?? "Bhilwara";
                int streamOrder = ComboSiteStreamOrder.SelectedIndex + 1;
                double.TryParse(TxtSiteBedWidth.Text, out double bedWidth);
                double.TryParse(TxtSiteSlope.Text, out double slope);
                double.TryParse(TxtSiteCatchmentArea.Text, out double catchmentHa);
                double.TryParse(TxtSiteDtw.Text, out double dtw);
                double.TryParse(TxtSiteEc.Text, out double ec);

                if (bedWidth <= 0) bedWidth = 10.0;
                if (slope <= 0) slope = 2.0;
                if (catchmentHa <= 0) catchmentHa = 50.0;
                if (dtw <= 0) dtw = 10.0;
                if (ec <= 0) ec = 1000.0;

                string lithology = (ComboSiteLithology.SelectedItem as ComboBoxItem)?.Content?.ToString() ?? "Weathered Hard Rock";
                string catchmentType = (ComboSiteCatchmentType.SelectedItem as ComboBoxItem)?.Content?.ToString() ?? "Average";

                var input = new SiteSpecificSitingInput
                {
                    DistrictName = distName,
                    StreamOrder = streamOrder,
                    ChannelBedWidthMeters = bedWidth,
                    SlopePercent = slope,
                    CatchmentAreaHa = catchmentHa,
                    LithologyType = lithology,
                    DepthToWaterMeters = dtw,
                    EcMicroSiemens = ec,
                    CatchmentType = catchmentType.Contains("Good") ? "Good" : (catchmentType.Contains("Bad") ? "Bad" : "Average"),
                    HasClayeyCoverOverAquifer = ChkClayCover?.IsChecked == true,
                    IsSandstoneLimestoneOutcropInWest = ChkOutcropWest?.IsChecked == true
                };

                var res = CgwbMasterPlanService.Instance.EvaluateSiteSpecificSiting(input);

                // Update Siting Verdict Banner
                TxtSitingVerdict.Text = res.Verdict;
                TxtSitingReason.Text = res.RecommendationReason;
                TxtCatchmentYield.Text = $"Est. Catchment Yield: {res.CatchmentYieldTcm:F1} TCM | {res.RecommendedFillings} Fillings";

                if (res.IsEligible)
                {
                    BorderSitingVerdict.Background = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#EFF6FF"));
                    BorderSitingVerdict.BorderBrush = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#BFDBFE"));
                    TxtSitingVerdict.Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#1E40AF"));
                    TxtSitingReason.Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#1E3A8A"));

                    // Sync Structure Combo
                    switch (res.RecommendedStructure)
                    {
                        case RechargeStructureType.CheckDam: ComboStructureType.SelectedIndex = 0; break;
                        case RechargeStructureType.PercolationPond: ComboStructureType.SelectedIndex = 1; break;
                        case RechargeStructureType.FarmPond: ComboStructureType.SelectedIndex = 2; break;
                        case RechargeStructureType.MiniPercolationTank: ComboStructureType.SelectedIndex = 3; break;
                        case RechargeStructureType.Anicut: ComboStructureType.SelectedIndex = 4; break;
                        case RechargeStructureType.RechargeShaft: ComboStructureType.SelectedIndex = 5; break;
                        case RechargeStructureType.Tanka: ComboStructureType.SelectedIndex = 6; break;
                        case RechargeStructureType.MacroStorageTank: ComboStructureType.SelectedIndex = 7; break;
                    }

                    // Populate recommended dimensions
                    TxtLength.Text = res.RecommendedLengthM.ToString("F1");
                    TxtHeight.Text = res.RecommendedHeightM.ToString("F1");
                    TxtWidth.Text = res.RecommendedWidthM.ToString("F1");
                    TxtFoundation.Text = res.RecommendedFoundationDepthM.ToString("F1");

                    if (res.ComputedBoq != null)
                    {
                        _lastEstimate = res.ComputedBoq;
                        DisplayBoqEstimate(_lastEstimate);
                    }
                }
                else
                {
                    BorderSitingVerdict.Background = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#FEF2F2"));
                    BorderSitingVerdict.BorderBrush = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#FECACA"));
                    TxtSitingVerdict.Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#991B1B"));
                    TxtSitingReason.Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#B91C1C"));
                    GridBoq.ItemsSource = null;
                    TxtTotalCost.Text = "Structure Excluded by Screening Gates";
                }
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Siting evaluation error: {ex.Message}", "Siting Advisor Error", MessageBoxButton.OK, MessageBoxImage.Warning);
            }
        }

        private void ComboStructureType_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            if (TxtLength == null || TxtHeight == null || TxtWidth == null || TxtFoundation == null) return;

            switch (ComboStructureType.SelectedIndex)
            {
                case 0: // Check Dam
                    LblLength.Text = "Length / Span (m):"; LblHeight.Text = "Weir Height (m):"; LblWidth.Text = "Top Width (m):"; LblFoundation.Text = "Found. Depth (m):";
                    TxtLength.Text = "25.0"; TxtHeight.Text = "2.5"; TxtWidth.Text = "1.8"; TxtFoundation.Text = "1.2";
                    break;
                case 1: // Percolation Pond
                    LblLength.Text = "Basin Length (m):"; LblHeight.Text = "Water Depth (m):"; LblWidth.Text = "Bund Width (m):"; LblFoundation.Text = "Found. Depth (m):";
                    TxtLength.Text = "50.0"; TxtHeight.Text = "3.0"; TxtWidth.Text = "2.5"; TxtFoundation.Text = "1.0";
                    break;
                case 2: // Farm Pond
                    LblLength.Text = "Side Length (m):"; LblHeight.Text = "Depth (m):"; LblWidth.Text = "Slope (1:x):"; LblFoundation.Text = "Freeboard (m):";
                    TxtLength.Text = "20.0"; TxtHeight.Text = "3.0"; TxtWidth.Text = "1.5"; TxtFoundation.Text = "0.5";
                    break;
                case 3: // Mini Percolation Tank
                    LblLength.Text = "Pit Side (m):"; LblHeight.Text = "Depth (m):"; LblWidth.Text = "Berm Width (m):"; LblFoundation.Text = "Trench Depth (m):";
                    TxtLength.Text = "15.0"; TxtHeight.Text = "2.0"; TxtWidth.Text = "2.0"; TxtFoundation.Text = "0.8";
                    break;
                case 4: // Anicut
                    LblLength.Text = "Spillway Len (m):"; LblHeight.Text = "Weir Height (m):"; LblWidth.Text = "Crest Width (m):"; LblFoundation.Text = "Found. Depth (m):";
                    TxtLength.Text = "35.0"; TxtHeight.Text = "3.2"; TxtWidth.Text = "2.2"; TxtFoundation.Text = "1.5";
                    break;
                case 5: // Recharge Shaft
                    LblLength.Text = "Pit Length (m):"; LblHeight.Text = "Bore Depth (m):"; LblWidth.Text = "Bore Dia (m):"; LblFoundation.Text = "Filter Bed (m):";
                    TxtLength.Text = "3.5"; TxtHeight.Text = "25.0"; TxtWidth.Text = "0.45"; TxtFoundation.Text = "1.5";
                    break;
                case 6: // Tanka
                    LblLength.Text = "Agor Dia (m):"; LblHeight.Text = "Pit Depth (m):"; LblWidth.Text = "Tanka Dia (m):"; LblFoundation.Text = "Slab Thick (m):";
                    TxtLength.Text = "24.0"; TxtHeight.Text = "3.5"; TxtWidth.Text = "4.0"; TxtFoundation.Text = "0.5";
                    break;
                case 7: // Macro Storage Tank
                    LblLength.Text = "Bund Length (m):"; LblHeight.Text = "Bund Height (m):"; LblWidth.Text = "Top Width (m):"; LblFoundation.Text = "Cutoff Depth (m):";
                    TxtLength.Text = "120.0"; TxtHeight.Text = "4.5"; TxtWidth.Text = "3.0"; TxtFoundation.Text = "2.5";
                    break;
            }
            ComputeCurrentBoq();
        }

        private void BtnCompute_Click(object sender, RoutedEventArgs e)
        {
            ComputeCurrentBoq();
        }

        private void ComputeCurrentBoq()
        {
            try
            {
                var type = ComboStructureType.SelectedIndex switch
                {
                    0 => RechargeStructureType.CheckDam,
                    1 => RechargeStructureType.PercolationPond,
                    2 => RechargeStructureType.FarmPond,
                    3 => RechargeStructureType.MiniPercolationTank,
                    4 => RechargeStructureType.Anicut,
                    5 => RechargeStructureType.RechargeShaft,
                    6 => RechargeStructureType.Tanka,
                    7 => RechargeStructureType.MacroStorageTank,
                    _ => RechargeStructureType.CheckDam
                };

                double.TryParse(TxtLength.Text, out double L);
                double.TryParse(TxtHeight.Text, out double H);
                double.TryParse(TxtWidth.Text, out double W);
                double.TryParse(TxtFoundation.Text, out double Df);

                if (L <= 0) L = 20.0;
                if (H <= 0) H = 2.0;

                _lastEstimate = RechargeBoqService.Instance.CalculateBoq(type, L, H, W, Df);
                DisplayBoqEstimate(_lastEstimate);
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Failed to calculate BOQ: {ex.Message}", "Calculation Error", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        private void DisplayBoqEstimate(StructureEstimate est)
        {
            GridBoq.ItemsSource = null;
            GridBoq.ItemsSource = est.Items;

            TxtStorageCapacity.Text = $"Est. Storage Capacity: {est.StorageCapacityTcm:F2} TCM (Thousand m³)";
            TxtTotalCost.Text = $"Total Cost: ₹ {est.TotalEstimatedCostInr:N0}";
        }

        private void BtnExportCsv_Click(object sender, RoutedEventArgs e)
        {
            if (_lastEstimate == null || _lastEstimate.Items.Count == 0) return;

            if (FileDialogHelper.PromptSave("CSV Spreadsheet (*.csv)|*.csv", $"BOQ_Estimate_{_lastEstimate.Type}.csv") is not { } savePath)
                return;

            var sb = new StringBuilder();
            sb.AppendLine("Item_No,Description,Quantity,Unit,Unit_Rate_INR,Amount_INR");
            foreach (var line in _lastEstimate.Items)
            {
                sb.AppendLine($"{line.ItemNo},\"{line.ItemDescription}\",{line.Quantity:F2},{line.Unit},{line.UnitRateInr},{line.TotalCostInr:F2}");
            }
            sb.AppendLine($",\"Sub-Total\",,,,{_lastEstimate.SubTotalInr:F2}");
            sb.AppendLine($",\"Total Estimated Cost (inc. 3% contingency + 2% QC)\",,,,{_lastEstimate.TotalEstimatedCostInr:F2}");

            File.WriteAllText(savePath, sb.ToString(), Encoding.UTF8);
            MessageBox.Show($"BOQ estimate exported to:\n{savePath}", "Export Successful", MessageBoxButton.OK, MessageBoxImage.Information);
        }

        // ==================== TAB 2: CGWB MASTER PLAN ALLOCATOR ====================

        private void ComboMacroDistrict_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            if (ComboMacroDistrict.SelectedItem is not ComboBoxItem item || item.Tag is not string distName) return;

            var profile = CgwbMasterPlanService.Instance.GetDistrict(distName);
            if (profile != null && TxtMacroDtw != null && TxtMacroTrend != null && TxtMacroEc != null && TxtMacroSy != null && TxtMacroSurplus != null)
            {
                TxtMacroDtw.Text = profile.DefaultDtwMeters.ToString("F1");
                TxtMacroTrend.Text = profile.DefaultTrendMPerYear.ToString("F2");
                TxtMacroEc.Text = profile.DefaultEcMicroSiemens.ToString("F0");
                TxtMacroSy.Text = profile.SpecificYieldPercent.ToString("F1");
                TxtMacroSurplus.Text = profile.SurplusRunoffMcm.ToString("F1");

                switch (profile.DefaultStage)
                {
                    case GroundwaterExploitationStage.OverExploited: ComboMacroStage.SelectedIndex = 0; break;
                    case GroundwaterExploitationStage.Critical: ComboMacroStage.SelectedIndex = 1; break;
                    case GroundwaterExploitationStage.SemiCritical: ComboMacroStage.SelectedIndex = 2; break;
                    case GroundwaterExploitationStage.Safe: ComboMacroStage.SelectedIndex = 3; break;
                }
                ComputeCurrentMacro();
            }
        }

        private void BtnComputeMacro_Click(object sender, RoutedEventArgs e)
        {
            ComputeCurrentMacro();
        }

        private void ComputeCurrentMacro()
        {
            try
            {
                string distName = (ComboMacroDistrict.SelectedItem as ComboBoxItem)?.Tag as string ?? "Bhilwara";
                var stage = ComboMacroStage.SelectedIndex switch
                {
                    0 => GroundwaterExploitationStage.OverExploited,
                    1 => GroundwaterExploitationStage.Critical,
                    2 => GroundwaterExploitationStage.SemiCritical,
                    _ => GroundwaterExploitationStage.Safe
                };

                double.TryParse(TxtMacroDtw.Text, out double dtw);
                double.TryParse(TxtMacroTrend.Text, out double trend);
                double.TryParse(TxtMacroEc.Text, out double ec);
                double.TryParse(TxtMacroSy.Text, out double sy);
                double.TryParse(TxtMacroSurplus.Text, out double surplus);

                if (dtw <= 0) dtw = 10.0;
                if (sy <= 0) sy = 2.0;

                _lastMacroResult = CgwbMasterPlanService.Instance.CalculateMasterPlanAllocation(
                    distName, stage, dtw, trend, ec, sy, surplus);

                // Update UI Metrics
                TxtMacroScreeningRemark.Text = _lastMacroResult.ScreeningRemarks;
                TxtMacroScreeningRemark.Foreground = _lastMacroResult.IsScreeningPassed
                    ? new SolidColorBrush((Color)ColorConverter.ConvertFromString("#1E40AF"))
                    : new SolidColorBrush((Color)ColorConverter.ConvertFromString("#DC2626"));

                TxtMacroT.Text = $"{_lastMacroResult.UnsaturatedThicknessMeters:F1} m";
                TxtMacroVu.Text = $"{_lastMacroResult.UnsaturatedVolumeMcm:N0} MCM";
                TxtMacroSpace.Text = $"{_lastMacroResult.SubsurfaceStorageSpaceMcm:N0} MCM";
                TxtMacroWaterReq.Text = $"{_lastMacroResult.GrossWaterRequiredMcm:N0} MCM";
                TxtMacroSurplusVal.Text = $"{_lastMacroResult.SurplusRunoffAvailableMcm:N1} MCM";
                TxtMacroFeasible.Text = $"{_lastMacroResult.FeasibleRechargeMcm:N1} MCM";

                GridMacroQuota.ItemsSource = null;
                GridMacroQuota.ItemsSource = _lastMacroResult.QuotaLines;

                TxtMacroTotalBudget.Text = $"Estimated District Outlay: ₹ {_lastMacroResult.TotalCostCrores:N2} Cr (₹ {_lastMacroResult.TotalCostLakhs:N0} Lakh)";
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Master Plan calculation error: {ex.Message}", "Master Plan Error", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        private void BtnExportMacroCsv_Click(object sender, RoutedEventArgs e)
        {
            if (_lastMacroResult == null || _lastMacroResult.QuotaLines.Count == 0) return;

            if (FileDialogHelper.PromptSave("CSV Spreadsheet (*.csv)|*.csv", $"CGWB_MasterPlan_{_lastMacroResult.DistrictName}.csv") is not { } savePath)
                return;

            var sb = new StringBuilder();
            sb.AppendLine($"District,{_lastMacroResult.DistrictName}");
            sb.AppendLine($"Region,{_lastMacroResult.Region}");
            sb.AppendLine($"Unsaturated_Thickness_m,{_lastMacroResult.UnsaturatedThicknessMeters:F2}");
            sb.AppendLine($"Unsaturated_Volume_MCM,{_lastMacroResult.UnsaturatedVolumeMcm:F2}");
            sb.AppendLine($"Storage_Space_MCM,{_lastMacroResult.SubsurfaceStorageSpaceMcm:F2}");
            sb.AppendLine($"Gross_Water_Required_MCM,{_lastMacroResult.GrossWaterRequiredMcm:F2}");
            sb.AppendLine($"Surplus_Runoff_Available_MCM,{_lastMacroResult.SurplusRunoffAvailableMcm:F2}");
            sb.AppendLine($"Feasible_Recharge_MCM,{_lastMacroResult.FeasibleRechargeMcm:F2}");
            sb.AppendLine();
            sb.AppendLine("Structure_Type,Target_Quota,Unit_Cost_Lakh_INR,Total_Cost_Crore_INR,Applicable_Zone");
            foreach (var q in _lastMacroResult.QuotaLines)
            {
                sb.AppendLine($"\"{q.StructureType}\",{q.Count},{q.UnitCostLakhs:F1},{q.TotalCostCrores:F2},\"{q.ApplicableRegion}\"");
            }
            sb.AppendLine($",,\"Total Project Outlay (Crores)\",{_lastMacroResult.TotalCostCrores:F2},");

            File.WriteAllText(savePath, sb.ToString(), Encoding.UTF8);
            MessageBox.Show($"Master Plan allocation exported to:\n{savePath}", "Export Successful", MessageBoxButton.OK, MessageBoxImage.Information);
        }

        private void BtnClose_Click(object sender, RoutedEventArgs e) => Close();
    }
}
