using System;
using System.Collections.Generic;
using System.Linq;
using GeoStudio.Hydrology.Models;

namespace GeoStudio.Hydrology.Services
{
    public class CgwbMasterPlanService
    {
        private static readonly Lazy<CgwbMasterPlanService> _instance = new(() => new CgwbMasterPlanService());
        public static CgwbMasterPlanService Instance => _instance.Value;

        // CGWB Master Plan 2020 Standard Unit Costs in Lakhs INR (Table 8.17.2)
        public const double UNIT_COST_CHECK_DAM_LAKH = 6.0;
        public const double UNIT_COST_RECHARGE_SHAFT_LAKH = 2.0;
        public const double UNIT_COST_FARM_POND_LAKH = 1.5;
        public const double UNIT_COST_PERCOLATION_TANK_LAKH = 3.0;
        public const double UNIT_COST_CAT_PER_HA_LAKH = 1.0;
        public const double UNIT_COST_TANKA_LAKH = 2.0;
        public const double UNIT_COST_ANICUT_LAKH = 15.0;
        public const double UNIT_COST_MACRO_TANK_LAKH = 50.0;
        public const double UNIT_COST_MINI_PERCOLATION_TANK_LAKH = 1.0;

        public static readonly HashSet<string> WesternDistricts = new(StringComparer.OrdinalIgnoreCase)
        {
            "Barmer", "Bikaner", "Churu", "Ganganagar", "Hanumangarh",
            "Jaisalmer", "Jhunjhunu", "Jodhpur", "Nagaur", "Sikar"
        };

        private readonly Dictionary<string, DistrictMasterPlanProfile> _districtProfiles = new(StringComparer.OrdinalIgnoreCase);

        public CgwbMasterPlanService()
        {
            InitializeDistrictProfiles();
        }

        public IReadOnlyList<DistrictMasterPlanProfile> GetAllDistricts() => _districtProfiles.Values.OrderBy(d => d.DistrictName).ToList();

        public DistrictMasterPlanProfile? GetDistrict(string name) =>
            _districtProfiles.TryGetValue(name, out var profile) ? profile : null;

        public MasterPlanCalculationResult CalculateMasterPlanAllocation(
            string districtName,
            GroundwaterExploitationStage stage,
            double dtwMeters,
            double trendMPerYear,
            double ecMicroSiemens,
            double specificYieldPercent,
            double? surplusOverrideMcm = null)
        {
            var profile = GetDistrict(districtName) ?? new DistrictMasterPlanProfile
            {
                DistrictName = districtName,
                Region = WesternDistricts.Contains(districtName) ? RajasthanRegion.WesternArid : RajasthanRegion.EasternGeneral,
                AreaSqKm = 8000.0,
                SurplusRunoffMcm = 100.0
            };

            var res = new MasterPlanCalculationResult
            {
                DistrictName = profile.DistrictName,
                Region = profile.Region
            };

            // 1. SCREENING RULES
            // Gate A: Waterlogging restriction (upper 3m never counted, DTW < 3m rejected)
            if (dtwMeters < 3.0)
            {
                res.IsScreeningPassed = false;
                res.ScreeningRemarks = "Screening Failed: Post-monsoon DTW is < 3.0 m bgl. Artificial recharge prohibited to prevent waterlogging & secondary soil salinity.";
                return res;
            }

            // Gate B: Groundwater quality ceiling (EC < 2,500 µS/cm)
            if (ecMicroSiemens > 2500.0)
            {
                res.IsScreeningPassed = false;
                res.ScreeningRemarks = $"Screening Failed: Groundwater EC ({ecMicroSiemens:F0} µS/cm) exceeds 2,500 µS/cm potable threshold. Recharge not recommended due to salinity hazard.";
                return res;
            }

            // Gate C: Tiered Trend / Depth combination (Composite Matrix)
            bool isDeclineSignificant = trendMPerYear <= -0.20 || trendMPerYear >= 0.20;
            if (dtwMeters < 9.0 && !isDeclineSignificant)
            {
                res.IsScreeningPassed = false;
                res.ScreeningRemarks = "Screening Failed: For moderate DTW (3-9 m bgl), a long-term post-monsoon declining trend >= 0.2 m/yr is required.";
                return res;
            }

            res.IsScreeningPassed = true;

            // 2. QUANTITY FORMULAS (CGWB Chapter 8.17.1 & Chapter 4)
            // T = mean post-monsoon DTW - 3 m
            res.UnsaturatedThicknessMeters = Math.Max(0.0, dtwMeters - 3.0);
            
            // Vu = Area (sq km * 10^6 sqm) * T (m) -> in MCM (10^6 m^3)
            res.UnsaturatedVolumeMcm = profile.AreaSqKm * res.UnsaturatedThicknessMeters;

            // Space = Vu * Sy
            double syFraction = specificYieldPercent / 100.0;
            res.SubsurfaceStorageSpaceMcm = res.UnsaturatedVolumeMcm * syFraction;

            // Gross Water Required = Space / 0.75 (efficiency factor 75%)
            res.GrossWaterRequiredMcm = res.SubsurfaceStorageSpaceMcm / 0.75;

            // Feasible Recharge = min(Gross Water Required, Surplus Runoff Allotted)
            double surplusAvailable = surplusOverrideMcm ?? profile.SurplusRunoffMcm;
            res.SurplusRunoffAvailableMcm = surplusAvailable;
            res.FeasibleRechargeMcm = Math.Min(res.GrossWaterRequiredMcm, surplusAvailable);

            // 3. REGIONAL ALLOCATION RULES (CGWB Section 2)
            if (stage == GroundwaterExploitationStage.Safe)
            {
                // In Safe blocks (< 70%), only Catchment Area Treatment (CAT) is planned
                res.ScreeningRemarks = "Stage is Safe (< 70%): Structure works deferred; Catchment Area Treatment (CAT) conservation only.";
                res.AllocatedCatAreaHa = Math.Round(profile.AreaSqKm * 1.5);
                res.QuotaLines.Add(new StructureQuotaLine
                {
                    StructureType = "Catchment Area Treatment (CAT)",
                    Count = (int)res.AllocatedCatAreaHa,
                    UnitCostLakhs = UNIT_COST_CAT_PER_HA_LAKH,
                    ApplicableRegion = "Catchment Ridges"
                });
                res.TotalCostInr = res.AllocatedCatAreaHa * (UNIT_COST_CAT_PER_HA_LAKH * 100000.0);
                return res;
            }

            if (res.Region == RajasthanRegion.WesternArid)
            {
                // WESTERN DESERT REGION:
                // Spreading recharge structures NOT recommended due to high PET & low rainfall.
                // Recommend Tanka (Rainwater Cistern) + CAT + local Outcrop Ponds.
                res.AllocatedTankas = (int)Math.Max(500, Math.Round(profile.AreaSqKm * 1.5));
                res.AllocatedFarmPonds = (int)Math.Round(res.AllocatedTankas * 0.1);
                res.AllocatedCatAreaHa = Math.Round(profile.AreaSqKm * 0.8);

                res.ScreeningRemarks = "Western Arid Zone: Spreading basins not viable (High PET & deep sand). Allocated Tanka rainwater harvesting & local runoff talabs.";

                res.QuotaLines.Add(new StructureQuotaLine { StructureType = "Tanka (Household Cistern)", Count = res.AllocatedTankas, UnitCostLakhs = UNIT_COST_TANKA_LAKH, ApplicableRegion = "Desert Settlements" });
                if (res.AllocatedFarmPonds > 0)
                    res.QuotaLines.Add(new StructureQuotaLine { StructureType = "Outcrop Talab / Pond", Count = res.AllocatedFarmPonds, UnitCostLakhs = UNIT_COST_FARM_POND_LAKH, ApplicableRegion = "Rocky Outcrops" });
                if (res.AllocatedCatAreaHa > 0)
                    res.QuotaLines.Add(new StructureQuotaLine { StructureType = "Catchment Treatment (ha)", Count = (int)res.AllocatedCatAreaHa, UnitCostLakhs = UNIT_COST_CAT_PER_HA_LAKH, ApplicableRegion = "Ridges" });
            }
            else
            {
                // EASTERN 23 DISTRICTS:
                // Calculated dynamically from feasible recharge volume and the empirical allocation ratio:
                // Check Dam : Percolation Tank : Anicut : Mini Percolation Tank : Macro Storage Tank ≈ 1 : 2 : 0.5 : 4.2 : 0.03
                double effectiveRunoffMcm = res.FeasibleRechargeMcm;
                double checkDamEquiv = effectiveRunoffMcm / 0.20;

                res.AllocatedCheckDams = Math.Max(1, (int)Math.Round(checkDamEquiv * 1.0));
                res.AllocatedPercolationTanks = Math.Max(1, (int)Math.Round(checkDamEquiv * 2.0));
                res.AllocatedMiniPercolationTanks = Math.Max(1, (int)Math.Round(checkDamEquiv * 4.2));
                res.AllocatedAnicuts = Math.Max(1, (int)Math.Round(checkDamEquiv * 0.5));
                res.AllocatedFarmPonds = Math.Max(1, (int)Math.Round(checkDamEquiv * 5.8));
                res.AllocatedRechargeShafts = Math.Max(1, (int)Math.Round(checkDamEquiv * 0.015));
                res.AllocatedMacroStorageTanks = Math.Max(1, (int)Math.Round(checkDamEquiv * 0.03));
                res.AllocatedCatAreaHa = Math.Round(checkDamEquiv * 6.0);

                res.ScreeningRemarks = "Eastern Zone: High potential for drainage stream harvesting, check dams, percolation tanks, and recharge shafts.";

                res.QuotaLines.Add(new StructureQuotaLine { StructureType = "Pacca Check Dam", Count = res.AllocatedCheckDams, UnitCostLakhs = UNIT_COST_CHECK_DAM_LAKH, ApplicableRegion = "2nd-3rd Order Streams" });
                res.QuotaLines.Add(new StructureQuotaLine { StructureType = "Percolation Tank / Talab", Count = res.AllocatedPercolationTanks, UnitCostLakhs = UNIT_COST_PERCOLATION_TANK_LAKH, ApplicableRegion = "Valley Depressions" });
                res.QuotaLines.Add(new StructureQuotaLine { StructureType = "Mini Percolation Tank", Count = res.AllocatedMiniPercolationTanks, UnitCostLakhs = UNIT_COST_MINI_PERCOLATION_TANK_LAKH, ApplicableRegion = "1st-2nd Order Streams" });
                res.QuotaLines.Add(new StructureQuotaLine { StructureType = "Masonry Anicut", Count = res.AllocatedAnicuts, UnitCostLakhs = UNIT_COST_ANICUT_LAKH, ApplicableRegion = "3rd-4th Order Streams" });
                res.QuotaLines.Add(new StructureQuotaLine { StructureType = "Farm Pond (Khet Talai)", Count = res.AllocatedFarmPonds, UnitCostLakhs = UNIT_COST_FARM_POND_LAKH, ApplicableRegion = "Agricultural Plots" });
                res.QuotaLines.Add(new StructureQuotaLine { StructureType = "Recharge Shaft in Tank Bed", Count = res.AllocatedRechargeShafts, UnitCostLakhs = UNIT_COST_RECHARGE_SHAFT_LAKH, ApplicableRegion = "Clayey / Silted Tanks" });
                if (res.AllocatedMacroStorageTanks > 0)
                    res.QuotaLines.Add(new StructureQuotaLine { StructureType = "Macro Storage Tank", Count = res.AllocatedMacroStorageTanks, UnitCostLakhs = UNIT_COST_MACRO_TANK_LAKH, ApplicableRegion = "Major Valley Bottlenecks" });
                if (res.AllocatedCatAreaHa > 0)
                    res.QuotaLines.Add(new StructureQuotaLine { StructureType = "Catchment Treatment (ha)", Count = (int)res.AllocatedCatAreaHa, UnitCostLakhs = UNIT_COST_CAT_PER_HA_LAKH, ApplicableRegion = "Ridge Areas" });
            }

            // Calculate total cost
            double totalCrores = 0;
            foreach (var q in res.QuotaLines)
            {
                totalCrores += q.TotalCostCrores;
            }
            res.TotalCostInr = totalCrores * 10000000.0;

            return res;
        }

        public SiteSpecificSitingResult EvaluateSiteSpecificSiting(SiteSpecificSitingInput input)
        {
            var res = new SiteSpecificSitingResult();
            bool isWest = WesternDistricts.Contains(input.DistrictName);

            // Exclusion 1: Waterlogging check
            if (input.DepthToWaterMeters < 3.0)
            {
                res.IsEligible = false;
                res.Verdict = "REJECTED (Waterlogging Risk)";
                res.RecommendationReason = "Post-monsoon water table is shallower than 3.0 m bgl. Subsurface space is insufficient; adding recharge will cause severe waterlogging and salinization.";
                return res;
            }

            // Exclusion 2: Groundwater salinity ceiling
            if (input.EcMicroSiemens > 2500.0)
            {
                res.IsEligible = false;
                res.Verdict = "REJECTED (High Salinity)";
                res.RecommendationReason = $"Native groundwater EC is {input.EcMicroSiemens:F0} µS/cm (exceeds 2,500 µS/cm threshold). Recharge risks mobilizing saline water and dissolving subterranean halite/gypsum.";
                return res;
            }

            // Hydrology: Catchment Runoff Yield (Strange's / SCS-CN proxy)
            // Yc = 10 * C * P * A (m3)
            double cCoeff = input.CatchmentType switch
            {
                "Good" => 0.22,
                "Bad" => 0.10,
                _ => 0.16 // Average
            };
            res.CatchmentYieldCubicMeters = 10.0 * cCoeff * input.Rainfall75PercentMm * input.CatchmentAreaHa;
            res.IsEligible = true;

            // SITING DECISION TREE
            if (isWest)
            {
                if (input.IsSandstoneLimestoneOutcropInWest)
                {
                    res.Verdict = "RECOMMENDED: Outcrop Talab + Recharge Shaft";
                    res.RecommendedStructure = RechargeStructureType.RechargeShaft;
                    res.StructureDisplayName = "Recharge Shaft with Desilting Chamber";
                    res.RecommendationReason = "Western Arid Zone exception: Hard rock sandstone/limestone outcrop provides localized runoff; injection bore prevents surface evaporation in sand.";
                    res.RecommendedFillings = 2;
                    res.RecommendedLengthM = 4.0;
                    res.RecommendedHeightM = 25.0; // bore depth
                    res.RecommendedWidthM = 0.45;  // bore dia
                    res.RecommendedFoundationDepthM = 1.5;
                }
                else
                {
                    res.Verdict = "RECOMMENDED: Tanka (Rainwater Cistern)";
                    res.RecommendedStructure = RechargeStructureType.Tanka;
                    res.StructureDisplayName = "Traditional Tanka with Agor Catchment";
                    res.RecommendationReason = "Western Arid Zone: Surface spreading basins lose >70% to evaporation. Covered Tanka with circular apron provides high-efficiency domestic storage.";
                    res.RecommendedFillings = 2;
                    res.RecommendedLengthM = 4.0;
                    res.RecommendedHeightM = 3.5;
                    res.RecommendedWidthM = 4.0;
                    res.RecommendedFoundationDepthM = 0.5;
                }
            }
            else
            {
                // Eastern Zone
                if (input.HasClayeyCoverOverAquifer)
                {
                    res.Verdict = "RECOMMENDED: Recharge Shaft in Village Pond / Silt Bed";
                    res.RecommendedStructure = RechargeStructureType.RechargeShaft;
                    res.StructureDisplayName = "Recharge Shaft (Injection Bore Through Clay)";
                    res.RecommendationReason = "Low-permeability clayey/silty upper cover blocks natural infiltration. Rotary drilled shaft penetrates confining layer directly into the aquifer.";
                    res.RecommendedFillings = 3;
                    res.RecommendedLengthM = 3.5;
                    res.RecommendedHeightM = 30.0;
                    res.RecommendedWidthM = 0.45;
                    res.RecommendedFoundationDepthM = 1.5;
                }
                else if (input.StreamOrder == 1 || input.SlopePercent > 3.0 || input.ChannelBedWidthMeters < 5.0)
                {
                    if (input.CatchmentAreaHa < 25.0)
                    {
                        res.Verdict = "RECOMMENDED: Farm Pond (Khet Talai) with Lining";
                        res.RecommendedStructure = RechargeStructureType.FarmPond;
                        res.StructureDisplayName = "Khet Talai with 500-Micron HDPE Liner";
                        res.RecommendationReason = "Upper micro-catchment / overland flow on individual farm holding. Liner prevents seepage loss for critical supplemental crop irrigation.";
                        res.RecommendedFillings = 2;
                        res.RecommendedLengthM = 20.0;
                        res.RecommendedHeightM = 3.0;
                        res.RecommendedWidthM = 1.5;
                        res.RecommendedFoundationDepthM = 0.0;
                    }
                    else
                    {
                        res.Verdict = "RECOMMENDED: Mini Percolation Tank";
                        res.RecommendedStructure = RechargeStructureType.MiniPercolationTank;
                        res.StructureDisplayName = "Mini Percolation Pit in Upper Gully";
                        res.RecommendationReason = "1st order stream / gully with moderate slope (2-5%). Traps runoff near ridge line and recharges upper saprolite aquifer.";
                        res.RecommendedFillings = 3;
                        res.RecommendedLengthM = 15.0;
                        res.RecommendedHeightM = 2.0;
                        res.RecommendedWidthM = 2.0;
                        res.RecommendedFoundationDepthM = 0.8;
                    }
                }
                else if (input.StreamOrder >= 3 && input.ChannelBedWidthMeters >= 18.0 && input.SlopePercent <= 1.5)
                {
                    res.Verdict = "RECOMMENDED: Masonry Anicut (Spillway)";
                    res.RecommendedStructure = RechargeStructureType.Anicut;
                    res.StructureDisplayName = "Masonry Overflow Anicut with Stilling Apron";
                    res.RecommendationReason = "3rd to 4th order wider ephemeral stream (width > 15m, gentle slope). Large catchment runoff supports substantial storage and command area wells.";
                    res.RecommendedFillings = 3;
                    res.RecommendedLengthM = Math.Max(25.0, input.ChannelBedWidthMeters);
                    res.RecommendedHeightM = 3.0;
                    res.RecommendedWidthM = 2.2;
                    res.RecommendedFoundationDepthM = 1.5;
                }
                else if (input.LithologyType.Contains("Weathered") || input.LithologyType.Contains("Alluvium"))
                {
                    if (input.ChannelBedWidthMeters > 12.0 && input.SlopePercent < 2.0)
                    {
                        res.Verdict = "RECOMMENDED: Percolation Tank / Talab";
                        res.RecommendedStructure = RechargeStructureType.PercolationPond;
                        res.StructureDisplayName = "Percolation Tank with Waste Weir";
                        res.RecommendationReason = "2nd-3rd order stream valley in permeable weathered rock/bouldery alluvium. Extensive ponding bed recharges downstream agricultural well clusters.";
                        res.RecommendedFillings = 2;
                        res.RecommendedLengthM = 60.0;
                        res.RecommendedHeightM = 3.0;
                        res.RecommendedWidthM = 2.5;
                        res.RecommendedFoundationDepthM = 1.2;
                    }
                    else
                    {
                        res.Verdict = "RECOMMENDED: Pacca Check Dam (Masonry)";
                        res.RecommendedStructure = RechargeStructureType.CheckDam;
                        res.StructureDisplayName = "Pacca Masonry Check Dam / Nala Bund";
                        res.RecommendationReason = "2nd order nala with firm rocky bed/banks (width 5-15m, slope 1-3%). Small upstream pondage directly feeds phreatic aquifer.";
                        res.RecommendedFillings = 4;
                        res.RecommendedLengthM = Math.Max(15.0, input.ChannelBedWidthMeters);
                        res.RecommendedHeightM = 2.2;
                        res.RecommendedWidthM = 1.8;
                        res.RecommendedFoundationDepthM = 1.2;
                    }
                }
                else
                {
                    res.Verdict = "RECOMMENDED: Pacca Check Dam";
                    res.RecommendedStructure = RechargeStructureType.CheckDam;
                    res.StructureDisplayName = "Standard Masonry Check Dam";
                    res.RecommendationReason = "Well-suited for stream channel gradient and drainage catchment area.";
                    res.RecommendedFillings = 4;
                    res.RecommendedLengthM = 20.0;
                    res.RecommendedHeightM = 2.0;
                    res.RecommendedWidthM = 1.8;
                    res.RecommendedFoundationDepthM = 1.2;
                }
            }

            // Generate BOQ through RechargeBoqService
            res.ComputedBoq = RechargeBoqService.Instance.CalculateBoq(
                res.RecommendedStructure,
                res.RecommendedLengthM,
                res.RecommendedHeightM,
                res.RecommendedWidthM,
                res.RecommendedFoundationDepthM
            );

            return res;
        }

        private void InitializeDistrictProfiles()
        {
            // Western 10 Arid Districts
            AddProfile(new DistrictMasterPlanProfile { DistrictName = "Barmer", Region = RajasthanRegion.WesternArid, AreaSqKm = 28387, DefaultDtwMeters = 24.5, DefaultTrendMPerYear = -0.32, DefaultEcMicroSiemens = 2200, SpecificYieldPercent = 5.0, SurplusRunoffMcm = 5.0, DefaultStage = GroundwaterExploitationStage.OverExploited });
            AddProfile(new DistrictMasterPlanProfile { DistrictName = "Bikaner", Region = RajasthanRegion.WesternArid, AreaSqKm = 30247, DefaultDtwMeters = 42.0, DefaultTrendMPerYear = -0.45, DefaultEcMicroSiemens = 1850, SpecificYieldPercent = 6.0, SurplusRunoffMcm = 8.5, DefaultStage = GroundwaterExploitationStage.OverExploited });
            AddProfile(new DistrictMasterPlanProfile { DistrictName = "Churu", Region = RajasthanRegion.WesternArid, AreaSqKm = 13835, DefaultDtwMeters = 28.0, DefaultTrendMPerYear = -0.38, DefaultEcMicroSiemens = 2100, SpecificYieldPercent = 6.5, SurplusRunoffMcm = 4.2, DefaultStage = GroundwaterExploitationStage.OverExploited });
            AddProfile(new DistrictMasterPlanProfile { DistrictName = "Ganganagar", Region = RajasthanRegion.WesternArid, AreaSqKm = 10978, DefaultDtwMeters = 16.5, DefaultTrendMPerYear = -0.22, DefaultEcMicroSiemens = 1450, SpecificYieldPercent = 10.0, SurplusRunoffMcm = 12.0, DefaultStage = GroundwaterExploitationStage.SemiCritical });
            AddProfile(new DistrictMasterPlanProfile { DistrictName = "Hanumangarh", Region = RajasthanRegion.WesternArid, AreaSqKm = 9656, DefaultDtwMeters = 14.2, DefaultTrendMPerYear = -0.25, DefaultEcMicroSiemens = 1600, SpecificYieldPercent = 9.5, SurplusRunoffMcm = 15.0, DefaultStage = GroundwaterExploitationStage.SemiCritical });
            AddProfile(new DistrictMasterPlanProfile { DistrictName = "Jaisalmer", Region = RajasthanRegion.WesternArid, AreaSqKm = 38401, DefaultDtwMeters = 38.0, DefaultTrendMPerYear = -0.28, DefaultEcMicroSiemens = 2400, SpecificYieldPercent = 4.5, SurplusRunoffMcm = 6.0, DefaultStage = GroundwaterExploitationStage.OverExploited });
            AddProfile(new DistrictMasterPlanProfile { DistrictName = "Jhunjhunu", Region = RajasthanRegion.WesternArid, AreaSqKm = 5928, DefaultDtwMeters = 34.0, DefaultTrendMPerYear = -0.55, DefaultEcMicroSiemens = 1250, SpecificYieldPercent = 5.5, SurplusRunoffMcm = 18.5, DefaultStage = GroundwaterExploitationStage.OverExploited });
            AddProfile(new DistrictMasterPlanProfile { DistrictName = "Jodhpur", Region = RajasthanRegion.WesternArid, AreaSqKm = 22850, DefaultDtwMeters = 31.0, DefaultTrendMPerYear = -0.42, DefaultEcMicroSiemens = 1950, SpecificYieldPercent = 5.0, SurplusRunoffMcm = 24.0, DefaultStage = GroundwaterExploitationStage.OverExploited });
            AddProfile(new DistrictMasterPlanProfile { DistrictName = "Nagaur", Region = RajasthanRegion.WesternArid, AreaSqKm = 17718, DefaultDtwMeters = 26.5, DefaultTrendMPerYear = -0.48, DefaultEcMicroSiemens = 2300, SpecificYieldPercent = 5.0, SurplusRunoffMcm = 19.5, DefaultStage = GroundwaterExploitationStage.OverExploited });
            AddProfile(new DistrictMasterPlanProfile { DistrictName = "Sikar", Region = RajasthanRegion.WesternArid, AreaSqKm = 7732, DefaultDtwMeters = 36.0, DefaultTrendMPerYear = -0.62, DefaultEcMicroSiemens = 1350, SpecificYieldPercent = 5.5, SurplusRunoffMcm = 21.0, DefaultStage = GroundwaterExploitationStage.OverExploited });

            // Eastern 23 Districts
            AddProfile(new DistrictMasterPlanProfile { DistrictName = "Ajmer", Region = RajasthanRegion.EasternGeneral, AreaSqKm = 8481, DefaultDtwMeters = 14.5, DefaultTrendMPerYear = -0.38, DefaultEcMicroSiemens = 1450, SpecificYieldPercent = 2.5, SurplusRunoffMcm = 115.0, DefaultStage = GroundwaterExploitationStage.OverExploited });
            AddProfile(new DistrictMasterPlanProfile { DistrictName = "Alwar", Region = RajasthanRegion.EasternGeneral, AreaSqKm = 8380, DefaultDtwMeters = 22.0, DefaultTrendMPerYear = -0.52, DefaultEcMicroSiemens = 1150, SpecificYieldPercent = 6.0, SurplusRunoffMcm = 165.0, DefaultStage = GroundwaterExploitationStage.OverExploited });
            AddProfile(new DistrictMasterPlanProfile { DistrictName = "Banswara", Region = RajasthanRegion.EasternGeneral, AreaSqKm = 5037, DefaultDtwMeters = 8.2, DefaultTrendMPerYear = -0.28, DefaultEcMicroSiemens = 680, SpecificYieldPercent = 2.0, SurplusRunoffMcm = 420.0, DefaultStage = GroundwaterExploitationStage.SemiCritical });
            AddProfile(new DistrictMasterPlanProfile { DistrictName = "Baran", Region = RajasthanRegion.EasternGeneral, AreaSqKm = 6992, DefaultDtwMeters = 9.5, DefaultTrendMPerYear = -0.24, DefaultEcMicroSiemens = 750, SpecificYieldPercent = 2.5, SurplusRunoffMcm = 380.0, DefaultStage = GroundwaterExploitationStage.SemiCritical });
            AddProfile(new DistrictMasterPlanProfile { DistrictName = "Bharatpur", Region = RajasthanRegion.EasternGeneral, AreaSqKm = 5066, DefaultDtwMeters = 15.0, DefaultTrendMPerYear = -0.35, DefaultEcMicroSiemens = 1950, SpecificYieldPercent = 7.0, SurplusRunoffMcm = 95.0, DefaultStage = GroundwaterExploitationStage.OverExploited });
            AddProfile(new DistrictMasterPlanProfile { DistrictName = "Bhilwara", Region = RajasthanRegion.EasternGeneral, AreaSqKm = 10455, DefaultDtwMeters = 12.0, DefaultTrendMPerYear = -0.42, DefaultEcMicroSiemens = 1250, SpecificYieldPercent = 2.2, SurplusRunoffMcm = 285.0, DefaultStage = GroundwaterExploitationStage.OverExploited });
            AddProfile(new DistrictMasterPlanProfile { DistrictName = "Bundi", Region = RajasthanRegion.EasternGeneral, AreaSqKm = 5550, DefaultDtwMeters = 10.5, DefaultTrendMPerYear = -0.26, DefaultEcMicroSiemens = 820, SpecificYieldPercent = 2.5, SurplusRunoffMcm = 210.0, DefaultStage = GroundwaterExploitationStage.SemiCritical });
            AddProfile(new DistrictMasterPlanProfile { DistrictName = "Chittorgarh", Region = RajasthanRegion.EasternGeneral, AreaSqKm = 7822, DefaultDtwMeters = 11.2, DefaultTrendMPerYear = -0.36, DefaultEcMicroSiemens = 950, SpecificYieldPercent = 2.3, SurplusRunoffMcm = 260.0, DefaultStage = GroundwaterExploitationStage.OverExploited });
            AddProfile(new DistrictMasterPlanProfile { DistrictName = "Dausa", Region = RajasthanRegion.EasternGeneral, AreaSqKm = 3432, DefaultDtwMeters = 24.0, DefaultTrendMPerYear = -0.58, DefaultEcMicroSiemens = 1380, SpecificYieldPercent = 6.0, SurplusRunoffMcm = 7.0, DefaultStage = GroundwaterExploitationStage.OverExploited });
            AddProfile(new DistrictMasterPlanProfile { DistrictName = "Dholpur", Region = RajasthanRegion.EasternGeneral, AreaSqKm = 3034, DefaultDtwMeters = 13.5, DefaultTrendMPerYear = -0.32, DefaultEcMicroSiemens = 1250, SpecificYieldPercent = 6.5, SurplusRunoffMcm = 85.0, DefaultStage = GroundwaterExploitationStage.SemiCritical });
            AddProfile(new DistrictMasterPlanProfile { DistrictName = "Dungarpur", Region = RajasthanRegion.EasternGeneral, AreaSqKm = 3770, DefaultDtwMeters = 8.5, DefaultTrendMPerYear = -0.22, DefaultEcMicroSiemens = 720, SpecificYieldPercent = 2.0, SurplusRunoffMcm = 310.0, DefaultStage = GroundwaterExploitationStage.Safe });
            AddProfile(new DistrictMasterPlanProfile { DistrictName = "Jaipur", Region = RajasthanRegion.EasternGeneral, AreaSqKm = 11143, DefaultDtwMeters = 28.5, DefaultTrendMPerYear = -0.65, DefaultEcMicroSiemens = 1420, SpecificYieldPercent = 6.5, SurplusRunoffMcm = 145.0, DefaultStage = GroundwaterExploitationStage.OverExploited });
            AddProfile(new DistrictMasterPlanProfile { DistrictName = "Jhalawar", Region = RajasthanRegion.EasternGeneral, AreaSqKm = 6219, DefaultDtwMeters = 7.8, DefaultTrendMPerYear = -0.21, DefaultEcMicroSiemens = 650, SpecificYieldPercent = 2.2, SurplusRunoffMcm = 450.0, DefaultStage = GroundwaterExploitationStage.SemiCritical });
            AddProfile(new DistrictMasterPlanProfile { DistrictName = "Karauli", Region = RajasthanRegion.EasternGeneral, AreaSqKm = 5524, DefaultDtwMeters = 16.0, DefaultTrendMPerYear = -0.34, DefaultEcMicroSiemens = 1180, SpecificYieldPercent = 5.0, SurplusRunoffMcm = 120.0, DefaultStage = GroundwaterExploitationStage.Critical });
            AddProfile(new DistrictMasterPlanProfile { DistrictName = "Kota", Region = RajasthanRegion.EasternGeneral, AreaSqKm = 5217, DefaultDtwMeters = 8.5, DefaultTrendMPerYear = -0.22, DefaultEcMicroSiemens = 780, SpecificYieldPercent = 2.5, SurplusRunoffMcm = 320.0, DefaultStage = GroundwaterExploitationStage.Safe });
            AddProfile(new DistrictMasterPlanProfile { DistrictName = "Pali", Region = RajasthanRegion.EasternGeneral, AreaSqKm = 12387, DefaultDtwMeters = 18.0, DefaultTrendMPerYear = -0.42, DefaultEcMicroSiemens = 1850, SpecificYieldPercent = 3.0, SurplusRunoffMcm = 95.0, DefaultStage = GroundwaterExploitationStage.OverExploited });
            AddProfile(new DistrictMasterPlanProfile { DistrictName = "Pratapgarh", Region = RajasthanRegion.EasternGeneral, AreaSqKm = 4117, DefaultDtwMeters = 8.0, DefaultTrendMPerYear = -0.20, DefaultEcMicroSiemens = 680, SpecificYieldPercent = 2.0, SurplusRunoffMcm = 340.0, DefaultStage = GroundwaterExploitationStage.Safe });
            AddProfile(new DistrictMasterPlanProfile { DistrictName = "Rajsamand", Region = RajasthanRegion.EasternGeneral, AreaSqKm = 4768, DefaultDtwMeters = 11.5, DefaultTrendMPerYear = -0.35, DefaultEcMicroSiemens = 1100, SpecificYieldPercent = 2.0, SurplusRunoffMcm = 180.0, DefaultStage = GroundwaterExploitationStage.OverExploited });
            AddProfile(new DistrictMasterPlanProfile { DistrictName = "Sawai Madhopur", Region = RajasthanRegion.EasternGeneral, AreaSqKm = 4498, DefaultDtwMeters = 15.5, DefaultTrendMPerYear = -0.38, DefaultEcMicroSiemens = 1200, SpecificYieldPercent = 5.0, SurplusRunoffMcm = 140.0, DefaultStage = GroundwaterExploitationStage.Critical });
            AddProfile(new DistrictMasterPlanProfile { DistrictName = "Sirohi", Region = RajasthanRegion.EasternGeneral, AreaSqKm = 5136, DefaultDtwMeters = 13.0, DefaultTrendMPerYear = -0.32, DefaultEcMicroSiemens = 1350, SpecificYieldPercent = 2.5, SurplusRunoffMcm = 160.0, DefaultStage = GroundwaterExploitationStage.OverExploited });
            AddProfile(new DistrictMasterPlanProfile { DistrictName = "Tonk", Region = RajasthanRegion.EasternGeneral, AreaSqKm = 7194, DefaultDtwMeters = 14.0, DefaultTrendMPerYear = -0.36, DefaultEcMicroSiemens = 1400, SpecificYieldPercent = 4.5, SurplusRunoffMcm = 135.0, DefaultStage = GroundwaterExploitationStage.OverExploited });
            AddProfile(new DistrictMasterPlanProfile { DistrictName = "Udaipur", Region = RajasthanRegion.EasternGeneral, AreaSqKm = 11724, DefaultDtwMeters = 9.8, DefaultTrendMPerYear = -0.28, DefaultEcMicroSiemens = 880, SpecificYieldPercent = 2.0, SurplusRunoffMcm = 480.0, DefaultStage = GroundwaterExploitationStage.SemiCritical });
        }

        private void AddProfile(DistrictMasterPlanProfile profile)
        {
            _districtProfiles[profile.DistrictName] = profile;
        }
    }
}
