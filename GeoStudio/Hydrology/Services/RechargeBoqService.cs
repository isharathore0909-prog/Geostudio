using System;
using System.Collections.Generic;
using GeoStudio.Hydrology.Models;

namespace GeoStudio.Hydrology.Services
{
    public class RechargeBoqService
    {
        private static readonly Lazy<RechargeBoqService> _instance = new(() => new RechargeBoqService());
        public static RechargeBoqService Instance => _instance.Value;

        // Rajasthan WRD / WDSC SOR & BSR Standard Benchmark Rates (2023-2024)
        public const double RATE_EARTHWORK = 165.0;      // Raj WRD BSR Item 1.2
        public const double RATE_EXCAVATION = 240.0;     // Raj WRD BSR Item 1.4
        public const double RATE_DRY_STONE = 2800.0;     // Raj WRD BSR Item 4.1
        public const double RATE_RRM_MASONRY = 3400.0;   // Raj WRD BSR Item 4.3 (1:5 Mortar)
        public const double RATE_CC_136 = 4800.0;        // Raj WRD BSR Item 5.2 (M15 Apron)
        public const double RATE_CC_124 = 6200.0;        // Raj WRD BSR Item 6.1 (M20 Crest Cap)
        public const double RATE_FILTER_MEDIA = 1850.0;  // Graded gravel 3-7mm
        public const double RATE_HDPE_LINER = 190.0;     // 500-micron HDPE geomembrane per sqm
        public const double RATE_DRILLING_BORE = 850.0;  // 450mm shaft bore per meter
        public const double RATE_PVC_CASING = 950.0;     // 200mm slotted PVC pipe per meter

        public StructureEstimate CalculateBoq(
            RechargeStructureType type,
            double lengthM,
            double heightM,
            double widthM = 2.0,
            double foundationDepthM = 1.2)
        {
            var est = new StructureEstimate
            {
                Type = type,
                LengthMeters = lengthM,
                HeightMeters = heightM,
                TopWidthMeters = widthM,
                FoundationDepthMeters = foundationDepthM
            };

            switch (type)
            {
                case RechargeStructureType.CheckDam:
                    est.StructureName = "Masonry Check Dam / Anicut";
                    CalculateCheckDamBoq(est);
                    break;
                case RechargeStructureType.PercolationPond:
                    est.StructureName = "Percolation Tank / Talab";
                    CalculatePercolationPondBoq(est);
                    break;
                case RechargeStructureType.FarmPond:
                    est.StructureName = "Farm Pond (Khet Talai) with HDPE Liner";
                    CalculateFarmPondBoq(est);
                    break;
                case RechargeStructureType.RechargeShaft:
                    est.StructureName = "Recharge Shaft with Injection Bore";
                    CalculateRechargeShaftBoq(est);
                    break;
                default:
                    est.StructureName = "Water Conservation Structure";
                    CalculateCheckDamBoq(est);
                    break;
            }

            double subTotal = 0;
            foreach (var item in est.Items) subTotal += item.TotalCostInr;
            est.SubTotalInr = subTotal;

            double contingencies = subTotal * (est.ContingencyPercent / 100.0);
            double supervision = subTotal * (est.SupervisionPercent / 100.0);
            est.TotalEstimatedCostInr = subTotal + contingencies + supervision;

            return est;
        }

        private static void CalculateCheckDamBoq(StructureEstimate est)
        {
            double L = est.LengthMeters;
            double H = est.HeightMeters;
            double Df = est.FoundationDepthMeters;
            double bottomWidth = est.TopWidthMeters + (0.8 * (H + Df));

            // 1. Foundation Excavation
            double excVol = L * bottomWidth * Df * 1.15;
            est.Items.Add(new BoqItemLine { ItemNo = 1, ItemDescription = "Foundation Bed Excavation in Riverbed/Nallah", Quantity = excVol, Unit = "cum", UnitRateInr = RATE_EXCAVATION });

            // 2. RRM Masonry in CM 1:5
            double rrmVol = L * ((est.TopWidthMeters + bottomWidth) / 2.0) * (H + Df);
            est.Items.Add(new BoqItemLine { ItemNo = 2, ItemDescription = "Random Rubble Masonry (RRM) in Cement Mortar 1:5", Quantity = rrmVol, Unit = "cum", UnitRateInr = RATE_RRM_MASONRY });

            // 3. CC 1:2:4 M20 Crest Cap
            double ccVol = L * est.TopWidthMeters * 0.15;
            est.Items.Add(new BoqItemLine { ItemNo = 3, ItemDescription = "Cement Concrete 1:2:4 (M20) Coping/Crest Cap", Quantity = ccVol, Unit = "cum", UnitRateInr = RATE_CC_124 });

            // 4. CC 1:3:6 M15 Downstream Apron
            double apronVol = L * (H * 2.5) * 0.3;
            est.Items.Add(new BoqItemLine { ItemNo = 4, ItemDescription = "Cement Concrete 1:3:6 (M15) Downstream Stilling Apron", Quantity = apronVol, Unit = "cum", UnitRateInr = RATE_CC_136 });

            est.StorageCapacityTcm = (L * H * H * 15.0) / 1000.0;
        }

        private static void CalculatePercolationPondBoq(StructureEstimate est)
        {
            double L = est.LengthMeters; // Top side length
            double H = est.HeightMeters; // Depth of pond
            double pitVol = L * L * H * 0.85; // trapezoidal excavation volume

            est.Items.Add(new BoqItemLine { ItemNo = 1, ItemDescription = "Earthwork Excavation for Pond Basin & Embankment", Quantity = pitVol, Unit = "cum", UnitRateInr = RATE_EARTHWORK });
            est.Items.Add(new BoqItemLine { ItemNo = 2, ItemDescription = "Dry Stone Pitching on Upstream Earthen Slope (1:2)", Quantity = L * H * 0.35, Unit = "cum", UnitRateInr = RATE_DRY_STONE });
            est.Items.Add(new BoqItemLine { ItemNo = 3, ItemDescription = "Graded Gravel Filter Bed on Recharge Trench", Quantity = L * 2.0 * 0.5, Unit = "cum", UnitRateInr = RATE_FILTER_MEDIA });

            est.StorageCapacityTcm = pitVol / 1000.0;
        }

        private static void CalculateFarmPondBoq(StructureEstimate est)
        {
            double L = est.LengthMeters; // e.g. 20m x 20m
            double H = est.HeightMeters; // e.g. 3m depth
            double earthVol = L * L * H * 0.8;
            double surfaceAreaSqm = (L * L) + (4 * L * H * 1.414);

            est.Items.Add(new BoqItemLine { ItemNo = 1, ItemDescription = "Earthwork & Compaction for Khet Talai Basin", Quantity = earthVol, Unit = "cum", UnitRateInr = RATE_EARTHWORK });
            est.Items.Add(new BoqItemLine { ItemNo = 2, ItemDescription = "500-Micron Multi-layer HDPE Geomembrane Liner", Quantity = surfaceAreaSqm * 1.15, Unit = "sqm", UnitRateInr = RATE_HDPE_LINER });
            est.Items.Add(new BoqItemLine { ItemNo = 3, ItemDescription = "Inlet Chute & Silt Trap Masonry Works", Quantity = 6.5, Unit = "cum", UnitRateInr = RATE_RRM_MASONRY });

            est.StorageCapacityTcm = earthVol / 1000.0;
        }

        private static void CalculateRechargeShaftBoq(StructureEstimate est)
        {
            double depthM = est.HeightMeters > 0 ? est.HeightMeters : 25.0; // Typical bore depth

            est.Items.Add(new BoqItemLine { ItemNo = 1, ItemDescription = "450mm Dia Rotary Drilling of Recharge Borehole", Quantity = depthM, Unit = "m", UnitRateInr = RATE_DRILLING_BORE });
            est.Items.Add(new BoqItemLine { ItemNo = 2, ItemDescription = "200mm Dia High-Collapse Slotted PVC Well Casing", Quantity = depthM, Unit = "m", UnitRateInr = RATE_PVC_CASING });
            est.Items.Add(new BoqItemLine { ItemNo = 3, ItemDescription = "Graded Silica Pea Gravel Filter Pack (3-7mm)", Quantity = 8.5, Unit = "cum", UnitRateInr = RATE_FILTER_MEDIA });
            est.Items.Add(new BoqItemLine { ItemNo = 4, ItemDescription = "Surface Desilting Chamber Concrete Structure", Quantity = 4.0, Unit = "cum", UnitRateInr = RATE_CC_124 });

            est.StorageCapacityTcm = 12.0; // Nominal annual intake TCM
        }
    }
}
