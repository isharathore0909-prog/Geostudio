using System.Collections.Generic;

namespace GeoStudio.Hydrology.Models
{
    public enum RechargeStructureType
    {
        CheckDam,           // Masonry Anicut / Check Dam
        PercolationPond,    // Percolation Pond / Talab
        FarmPond,           // Khet Talai with HDPE Lining
        SubsurfaceDyke,     // Sub-surface Barrier
        RechargeShaft,      // Filtered Recharge Borehole Shaft
        ContourBund         // Field Contour Bunding
    }

    public class SorRateItem
    {
        public string ItemCode { get; set; } = string.Empty;
        public string Description { get; set; } = string.Empty;
        public string Unit { get; set; } = "cum";
        public double RateInr { get; set; }
        public string Source { get; set; } = "Rajasthan WRD BSR 2023-24";
    }

    public class BoqItemLine
    {
        public int ItemNo { get; set; }
        public string ItemDescription { get; set; } = string.Empty;
        public double Quantity { get; set; }
        public string Unit { get; set; } = "cum";
        public double UnitRateInr { get; set; }
        public double TotalCostInr => Quantity * UnitRateInr;
    }

    public class StructureEstimate
    {
        public RechargeStructureType Type { get; set; }
        public string StructureName { get; set; } = string.Empty;
        public double LengthMeters { get; set; }
        public double HeightMeters { get; set; }
        public double TopWidthMeters { get; set; }
        public double FoundationDepthMeters { get; set; }
        public double StorageCapacityTcm { get; set; } // Thousand Cubic Meters
        public List<BoqItemLine> Items { get; set; } = new List<BoqItemLine>();
        public double ContingencyPercent { get; set; } = 3.0; // 3% contingency
        public double SupervisionPercent { get; set; } = 2.0; // 2% quality control
        
        public double SubTotalInr { get; set; }
        public double TotalEstimatedCostInr { get; set; }
    }

    public class CropWaterRequirement
    {
        public string CropName { get; set; } = string.Empty;
        public string Season { get; set; } = "Kharif"; // Kharif, Rabi, Zaid
        public double WaterRequirementMm { get; set; }
        public double CultivationCostPerHa { get; set; }
        public double ExpectedNetProfitPerHa { get; set; }
        public string IrrigationMethod { get; set; } = "Drip / Micro-irrigation";
    }
}
