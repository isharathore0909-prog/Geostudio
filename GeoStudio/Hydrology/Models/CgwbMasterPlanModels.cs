using System;
using System.Collections.Generic;

namespace GeoStudio.Hydrology.Models
{
    public enum RajasthanRegion
    {
        WesternArid,   // 10 Desert Districts: Barmer, Bikaner, Churu, Ganganagar, Hanumangarh, Jaisalmer, Jhunjhunu, Jodhpur, Nagaur, Sikar
        EasternGeneral // 23 Eastern/Southern Districts (Aravalli & Alluvial)
    }

    public enum GroundwaterExploitationStage
    {
        OverExploited,  // > 100% (Top Priority)
        Critical,       // 90 - 100%
        SemiCritical,   // 70 - 90%
        Safe            // < 70% (CAT treatment only)
    }

    public class DistrictMasterPlanProfile
    {
        public string DistrictName { get; set; } = string.Empty;
        public RajasthanRegion Region { get; set; }
        public double AreaSqKm { get; set; }
        public double DefaultDtwMeters { get; set; }
        public double DefaultTrendMPerYear { get; set; }
        public double DefaultEcMicroSiemens { get; set; }
        public double SpecificYieldPercent { get; set; }
        public double SurplusRunoffMcm { get; set; }
        public GroundwaterExploitationStage DefaultStage { get; set; }
    }

    public class MasterPlanCalculationResult
    {
        public string DistrictName { get; set; } = string.Empty;
        public RajasthanRegion Region { get; set; }
        public bool IsScreeningPassed { get; set; }
        public string ScreeningRemarks { get; set; } = string.Empty;

        // Volumetric calculations (CGWB Section 3)
        public double UnsaturatedThicknessMeters { get; set; } // T = DTW - 3m
        public double UnsaturatedVolumeMcm { get; set; }       // Vu = Area * T
        public double SubsurfaceStorageSpaceMcm { get; set; }  // Space = Vu * Sy
        public double GrossWaterRequiredMcm { get; set; }      // Water req = Space / 0.75
        public double SurplusRunoffAvailableMcm { get; set; }
        public double FeasibleRechargeMcm { get; set; }        // min(GrossWaterRequired, SurplusRunoff)

        // Structure allocations
        public int AllocatedCheckDams { get; set; }
        public int AllocatedPercolationTanks { get; set; }
        public int AllocatedMiniPercolationTanks { get; set; }
        public int AllocatedAnicuts { get; set; }
        public int AllocatedFarmPonds { get; set; }
        public int AllocatedRechargeShafts { get; set; }
        public int AllocatedTankas { get; set; }
        public int AllocatedMacroStorageTanks { get; set; }
        public double AllocatedCatAreaHa { get; set; }

        // Costs in Rupees
        public double TotalCostInr { get; set; }
        public double TotalCostCrores => TotalCostInr / 10000000.0;
        public double TotalCostLakhs => TotalCostInr / 100000.0;

        public List<StructureQuotaLine> QuotaLines { get; set; } = new();
    }

    public class StructureQuotaLine
    {
        public string StructureType { get; set; } = string.Empty;
        public int Count { get; set; }
        public double UnitCostLakhs { get; set; }
        public double TotalCostCrores => (Count * UnitCostLakhs) / 100.0;
        public string ApplicableRegion { get; set; } = "All";
    }

    public class SiteSpecificSitingInput
    {
        public string DistrictName { get; set; } = "Bhilwara";
        public int StreamOrder { get; set; } = 2; // Strahler 1 to 4+
        public double ChannelBedWidthMeters { get; set; } = 10.0;
        public double SlopePercent { get; set; } = 2.0;
        public string LithologyType { get; set; } = "Weathered / Fractured Hard Rock";
        public double DepthToWaterMeters { get; set; } = 8.5;
        public double WaterLevelTrendMPerYear { get; set; } = -0.35;
        public double EcMicroSiemens { get; set; } = 1200.0;
        public double CatchmentAreaHa { get; set; } = 65.0;
        public double Rainfall75PercentMm { get; set; } = 620.0;
        public string CatchmentType { get; set; } = "Average"; // Good, Average, Bad
        public bool HasClayeyCoverOverAquifer { get; set; } = false;
        public bool IsSandstoneLimestoneOutcropInWest { get; set; } = false;
    }

    public class SiteSpecificSitingResult
    {
        public bool IsEligible { get; set; }
        public string Verdict { get; set; } = string.Empty;
        public string RecommendationReason { get; set; } = string.Empty;
        public RechargeStructureType RecommendedStructure { get; set; }
        public string StructureDisplayName { get; set; } = string.Empty;

        // Catchment hydrology
        public double CatchmentYieldCubicMeters { get; set; }
        public double CatchmentYieldTcm => CatchmentYieldCubicMeters / 1000.0;
        public int RecommendedFillings { get; set; }

        // Sized dimensions for BOQ
        public double RecommendedLengthM { get; set; }
        public double RecommendedHeightM { get; set; }
        public double RecommendedWidthM { get; set; }
        public double RecommendedFoundationDepthM { get; set; }

        public StructureEstimate? ComputedBoq { get; set; }
    }
}

