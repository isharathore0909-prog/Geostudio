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

        public const double RATE_PLASTER_13 = 185.0;     // 20mm waterproof cement plaster 1:3 per sqm
        public const double RATE_RCC_M25 = 7800.0;       // RCC M25 for cover slabs / beams per cum
        public const double RATE_BRICK_MASONRY = 3200.0; // Class I brick masonry in CM 1:4 per cum

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
                    est.StructureName = "Pacca Masonry Check Dam";
                    CalculateCheckDamBoq(est);
                    break;
                case RechargeStructureType.PercolationPond:
                    est.StructureName = "Percolation Tank / Talab";
                    CalculatePercolationPondBoq(est);
                    break;
                case RechargeStructureType.MiniPercolationTank:
                    est.StructureName = "Mini Percolation Tank / Pit";
                    CalculateMiniPercolationTankBoq(est);
                    break;
                case RechargeStructureType.Anicut:
                    est.StructureName = "Masonry Anicut (Spillway & Apron)";
                    CalculateAnicutBoq(est);
                    break;
                case RechargeStructureType.FarmPond:
                    est.StructureName = "Farm Pond (Khet Talai) with HDPE Liner";
                    CalculateFarmPondBoq(est);
                    break;
                case RechargeStructureType.RechargeShaft:
                    est.StructureName = "Recharge Shaft with Injection Bore";
                    CalculateRechargeShaftBoq(est);
                    break;
                case RechargeStructureType.Tanka:
                    est.StructureName = "Tanka (Covered Rainwater Harvesting Cistern)";
                    CalculateTankaBoq(est);
                    break;
                case RechargeStructureType.MacroStorageTank:
                    est.StructureName = "Macro Storage Reservoir / Bandha";
                    CalculateMacroStorageTankBoq(est);
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

        private static void CalculateMiniPercolationTankBoq(StructureEstimate est)
        {
            double L = est.LengthMeters > 0 ? est.LengthMeters : 15.0; // Pit length/side
            double H = est.HeightMeters > 0 ? est.HeightMeters : 1.8;  // Depth
            double pitVol = L * L * H * 0.75;

            est.Items.Add(new BoqItemLine { ItemNo = 1, ItemDescription = "Excavation in Soft/Medium Rock for Mini Pit", Quantity = pitVol, Unit = "cum", UnitRateInr = RATE_EXCAVATION });
            est.Items.Add(new BoqItemLine { ItemNo = 2, ItemDescription = "Dry Stone Pitching on Side Embankments", Quantity = L * H * 0.25, Unit = "cum", UnitRateInr = RATE_DRY_STONE });
            est.Items.Add(new BoqItemLine { ItemNo = 3, ItemDescription = "Graded Boulder & Gravel Infiltration Filter Bed", Quantity = L * 1.5 * 0.4, Unit = "cum", UnitRateInr = RATE_FILTER_MEDIA });

            est.StorageCapacityTcm = pitVol / 1000.0;
        }

        private static void CalculateAnicutBoq(StructureEstimate est)
        {
            double L = est.LengthMeters > 0 ? est.LengthMeters : 35.0; // Spillway length
            double H = est.HeightMeters > 0 ? est.HeightMeters : 3.0;  // Overflow weir height
            double Df = est.FoundationDepthMeters > 0 ? est.FoundationDepthMeters : 1.5;
            double topW = est.TopWidthMeters > 0 ? est.TopWidthMeters : 2.2;
            double bottomW = topW + (0.9 * (H + Df));

            double excVol = L * bottomW * Df * 1.25;
            est.Items.Add(new BoqItemLine { ItemNo = 1, ItemDescription = "Deep Riverbed Rock Excavation for Spillway & Flanks", Quantity = excVol, Unit = "cum", UnitRateInr = RATE_EXCAVATION });

            double rrmVol = L * ((topW + bottomW) / 2.0) * (H + Df);
            est.Items.Add(new BoqItemLine { ItemNo = 2, ItemDescription = "Random Rubble Masonry (RRM) in Cement Mortar 1:4 with pointing", Quantity = rrmVol, Unit = "cum", UnitRateInr = RATE_RRM_MASONRY });

            double capVol = L * topW * 0.2;
            est.Items.Add(new BoqItemLine { ItemNo = 3, ItemDescription = "RCC M20 Grade Reinforced Crest & Ogee Overflow Cap", Quantity = capVol, Unit = "cum", UnitRateInr = RATE_CC_124 });

            double apronVol = L * (H * 3.5) * 0.4;
            est.Items.Add(new BoqItemLine { ItemNo = 4, ItemDescription = "M15 Grade Cement Concrete Stilling Basin & Cutoff Walls", Quantity = apronVol, Unit = "cum", UnitRateInr = RATE_CC_136 });

            est.Items.Add(new BoqItemLine { ItemNo = 5, ItemDescription = "Side Guide Bunds Earthwork & Heavy Boulder Pitching", Quantity = L * 4.0, Unit = "cum", UnitRateInr = RATE_EARTHWORK });

            est.StorageCapacityTcm = (L * H * H * 25.0) / 1000.0;
        }

        private static void CalculateTankaBoq(StructureEstimate est)
        {
            // Western Rajasthan Tanka: Traditional 30,000 - 50,000 Liter Circular Masonry Cistern with Silt Trap
            double diaM = est.TopWidthMeters > 0 ? est.TopWidthMeters : 4.0;
            double depthM = est.HeightMeters > 0 ? est.HeightMeters : 3.5;
            double radius = diaM / 2.0;

            double excVol = Math.PI * Math.Pow(radius + 0.4, 2) * (depthM + 0.5);
            est.Items.Add(new BoqItemLine { ItemNo = 1, ItemDescription = "Circular Pit Excavation in Hard Murrum / Caliche", Quantity = excVol, Unit = "cum", UnitRateInr = RATE_EXCAVATION });

            double wallVol = Math.PI * diaM * 0.35 * depthM;
            est.Items.Add(new BoqItemLine { ItemNo = 2, ItemDescription = "Class I Masonry Wall in CM 1:4 with Local Stone", Quantity = wallVol, Unit = "cum", UnitRateInr = RATE_RRM_MASONRY });

            double plasterArea = (Math.PI * diaM * depthM) + (Math.PI * Math.Pow(radius, 2));
            est.Items.Add(new BoqItemLine { ItemNo = 3, ItemDescription = "20mm Waterproof Cement Plaster 1:3 with neat cement slurry", Quantity = plasterArea, Unit = "sqm", UnitRateInr = RATE_PLASTER_13 });

            double slabVol = Math.PI * Math.Pow(radius + 0.3, 2) * 0.12;
            est.Items.Add(new BoqItemLine { ItemNo = 4, ItemDescription = "RCC M25 Roof Cover Slab with Manhole & Vent Pipe", Quantity = slabVol, Unit = "cum", UnitRateInr = RATE_RCC_M25 });

            double agorArea = Math.PI * (Math.Pow(12.0, 2) - Math.Pow(radius, 2)); // 24m dia circular catchment
            est.Items.Add(new BoqItemLine { ItemNo = 5, ItemDescription = "Catchment Apron (Agor) Murrum Dressing & Ramming", Quantity = agorArea, Unit = "sqm", UnitRateInr = 45.0 });

            est.StorageCapacityTcm = (Math.PI * Math.Pow(radius, 2) * depthM) / 1000.0; // in TCM
        }

        private static void CalculateMacroStorageTankBoq(StructureEstimate est)
        {
            double L = est.LengthMeters > 0 ? est.LengthMeters : 120.0; // Bund length
            double H = est.HeightMeters > 0 ? est.HeightMeters : 4.5;   // Max bund height
            double topW = est.TopWidthMeters > 0 ? est.TopWidthMeters : 3.0;

            double bundCrossArea = ((topW + (topW + 2 * 2.5 * H)) / 2.0) * H;
            double earthBundVol = bundCrossArea * L;
            est.Items.Add(new BoqItemLine { ItemNo = 1, ItemDescription = "Zoned Earthen Dam Embankment Compaction with Impermeable Core", Quantity = earthBundVol, Unit = "cum", UnitRateInr = RATE_EARTHWORK });

            double cutoffVol = L * 2.0 * 2.5;
            est.Items.Add(new BoqItemLine { ItemNo = 2, ItemDescription = "Impermeable Clay Key Trench (Cut-off Trench) Excavation & Puddling", Quantity = cutoffVol, Unit = "cum", UnitRateInr = RATE_EXCAVATION });

            double pitchingArea = L * Math.Sqrt(Math.Pow(H * 2.5, 2) + Math.Pow(H, 2));
            est.Items.Add(new BoqItemLine { ItemNo = 3, ItemDescription = "Hand-Packed Dry Stone Pitching with Graded Filter Backing on U/S", Quantity = pitchingArea * 0.3, Unit = "cum", UnitRateInr = RATE_DRY_STONE });

            est.Items.Add(new BoqItemLine { ItemNo = 4, ItemDescription = "Masonry Clear Overfall Surplus Escape Waste Weir (20m length)", Quantity = 85.0, Unit = "cum", UnitRateInr = RATE_RRM_MASONRY });
            est.Items.Add(new BoqItemLine { ItemNo = 5, ItemDescription = "RCC Sluice Outlet Regulator with Screw Gear Hoist", Quantity = 1.0, Unit = "job", UnitRateInr = 185000.0 });

            est.StorageCapacityTcm = (L * H * H * 45.0) / 1000.0;
        }
    }
}
