using System.Collections.Generic;

namespace GeoStudio.Raster.Services
{
    public class SpectralModeInfo
    {
        public string Mode { get; set; } = "NDVI";
        public string Formula { get; set; } = string.Empty;
        public string Description { get; set; } = string.Empty;
        public string ColorHex { get; set; } = "#059669";
        public bool NeedsNir { get; set; }
        public bool NeedsRed { get; set; }
        public bool NeedsGreen { get; set; }
        public bool NeedsBlue { get; set; }
        public bool NeedsSwir1 { get; set; }
        public bool NeedsSwir2 { get; set; }
    }

    public static class SpectralIndexDefinitions
    {
        public static readonly Dictionary<string, SpectralModeInfo> Modes = new()
        {
            ["NDVI"] = new SpectralModeInfo
            {
                Mode = "NDVI",
                Formula = "(NIR - Red) / (NIR + Red)",
                Description = "Normalized Difference Vegetation Index: Evaluates photosynthetic canopy density, vegetation greenness, and crop vigor (-1.0 to +1.0).",
                ColorHex = "#059669",
                NeedsNir = true, NeedsRed = true
            },
            ["NDWI"] = new SpectralModeInfo
            {
                Mode = "NDWI",
                Formula = "(Green - NIR) / (Green + NIR)",
                Description = "Normalized Difference Water Index (McFeeters): Delineates open water bodies, rivers, reservoirs, and surface moisture levels (-1.0 to +1.0).",
                ColorHex = "#0284C7",
                NeedsNir = true, NeedsGreen = true
            },
            ["EVI"] = new SpectralModeInfo
            {
                Mode = "EVI",
                Formula = "2.5 * (NIR - Red) / (NIR + 6*Red - 7.5*Blue + 1)",
                Description = "Enhanced Vegetation Index: Atmospheric- and soil-corrected vegetation index ideal for high-biomass regions and dense forest canopies.",
                ColorHex = "#16A34A",
                NeedsNir = true, NeedsRed = true, NeedsBlue = true
            },
            ["NDBI"] = new SpectralModeInfo
            {
                Mode = "NDBI",
                Formula = "(SWIR1 - NIR) / (SWIR1 + NIR)",
                Description = "Normalized Difference Built-up Index: Identifies urban structures, residential areas, asphalt highways, and impervious surfaces (-1.0 to +1.0).",
                ColorHex = "#E11D48",
                NeedsNir = true, NeedsSwir1 = true
            },
            ["NBR"] = new SpectralModeInfo
            {
                Mode = "NBR",
                Formula = "(NIR - SWIR2) / (NIR + SWIR2)",
                Description = "Normalized Burn Ratio: Highlights burned fire scars and estimates burn severity across forest and shrub ecosystems (-1.0 to +1.0).",
                ColorHex = "#D97706",
                NeedsNir = true, NeedsSwir2 = true
            },
            ["FALSE_COLOR"] = new SpectralModeInfo
            {
                Mode = "FALSE_COLOR",
                Formula = "R = NIR, G = Red, B = Green (Standard Color Infrared)",
                Description = "Infrared Color Composite: Maps NIR to Red channel so dense chlorophyll vegetation appears vivid crimson red, water deep dark, and urban gray-cyan.",
                ColorHex = "#9333EA",
                NeedsNir = true, NeedsRed = true, NeedsGreen = true
            }
        };

        public static (string nir, string red, string green, string blue, string swir1, string swir2) GetPresetBands(string preset) => preset switch
        {
            "sentinel2" => ("8", "4", "3", "2", "11", "12"),
            "landsat8" => ("5", "4", "3", "2", "6", "7"),
            "landsat7" => ("4", "3", "2", "1", "5", "7"),
            "planetscope" => ("4", "1", "2", "3", "4", "4"),
            _ => ("8", "4", "3", "2", "11", "12")
        };

        public static string DetectSensorPreset(string filePath, int bandCount)
        {
            if (string.IsNullOrEmpty(filePath)) return "sentinel2";
            string name = System.IO.Path.GetFileName(filePath).ToUpperInvariant();

            if (name.Contains("LC08") || name.Contains("LC09") || name.Contains("LO08") || name.Contains("LO09") ||
                name.Contains("LC8") || name.Contains("LC9") || name.Contains("LANDSAT_8") || name.Contains("LANDSAT_9") ||
                name.Contains("LANDSAT8") || name.Contains("LANDSAT9"))
            {
                return "landsat8";
            }
            if (name.Contains("LE07") || name.Contains("LT05") || name.Contains("LT04") ||
                name.Contains("LANDSAT_7") || name.Contains("LANDSAT_5") || name.Contains("LANDSAT_4") ||
                name.Contains("LANDSAT7") || name.Contains("LANDSAT5"))
            {
                return "landsat7";
            }
            if (name.Contains("S2A") || name.Contains("S2B") || name.Contains("SENTINEL") || name.Contains("MSIL2A") || name.Contains("MSIL1C"))
            {
                return "sentinel2";
            }
            if (bandCount == 4)
            {
                return "planetscope";
            }
            return "sentinel2";
        }

        public static string? FindSiblingBandFile(string baseFile, params string[] candidates)
        {
            try
            {
                if (string.IsNullOrEmpty(baseFile) || !System.IO.File.Exists(baseFile)) return null;
                string dir = System.IO.Path.GetDirectoryName(baseFile) ?? string.Empty;
                string filename = System.IO.Path.GetFileName(baseFile);
                if (string.IsNullOrEmpty(dir) || !System.IO.Directory.Exists(dir)) return null;

                var match = System.Text.RegularExpressions.Regex.Match(filename, @"(_(?:SR_|ST_|QA_)?B\d+)", System.Text.RegularExpressions.RegexOptions.IgnoreCase);
                if (!match.Success)
                    match = System.Text.RegularExpressions.Regex.Match(filename, @"(_B\d+)", System.Text.RegularExpressions.RegexOptions.IgnoreCase);

                foreach (var cand in candidates)
                {
                    if (match.Success)
                    {
                        string candName = filename.Substring(0, match.Index) + "_" + cand + filename.Substring(match.Index + match.Length);
                        string candPath = System.IO.Path.Combine(dir, candName);
                        if (System.IO.File.Exists(candPath)) return candPath;

                        string candNameSr = filename.Substring(0, match.Index).Replace("_ST_", "_SR_") + "_" + cand + filename.Substring(match.Index + match.Length);
                        string candPathSr = System.IO.Path.Combine(dir, candNameSr);
                        if (System.IO.File.Exists(candPathSr)) return candPathSr;

                        string candNameClean = filename.Substring(0, match.Index).Replace("_ST_", "_").Replace("_SR_", "_") + cand + filename.Substring(match.Index + match.Length);
                        string candPathClean = System.IO.Path.Combine(dir, candNameClean);
                        if (System.IO.File.Exists(candPathClean)) return candPathClean;
                    }

                    foreach (var f in System.IO.Directory.GetFiles(dir, $"*_{cand}.*"))
                    {
                        if (f.EndsWith(".tif", System.StringComparison.OrdinalIgnoreCase) ||
                            f.EndsWith(".tiff", System.StringComparison.OrdinalIgnoreCase) ||
                            f.EndsWith(".jp2", System.StringComparison.OrdinalIgnoreCase))
                            return f;
                    }
                }
            }
            catch { }
            return null;
        }

        public static object BuildBandMap(
            int nir, int red, int green, int blue, int swir1, int swir2,
            string rasterPath)
        {
            string? nirFile = FindSiblingBandFile(rasterPath, $"B{nir}", $"B0{nir}", $"{nir}");
            string? redFile = FindSiblingBandFile(rasterPath, $"B{red}", $"B0{red}", $"{red}");
            string? greenFile = FindSiblingBandFile(rasterPath, $"B{green}", $"B0{green}", $"{green}");
            string? blueFile = FindSiblingBandFile(rasterPath, $"B{blue}", $"B0{blue}", $"{blue}");
            string? swir1File = FindSiblingBandFile(rasterPath, $"B{swir1}", $"B0{swir1}", $"{swir1}");
            string? swir2File = FindSiblingBandFile(rasterPath, $"B{swir2}", $"B0{swir2}", $"{swir2}");

            return new
            {
                nir = Math.Max(1, nir),
                red = Math.Max(1, red),
                green = Math.Max(1, green),
                blue = Math.Max(1, blue),
                swir1 = Math.Max(1, swir1),
                swir2 = Math.Max(1, swir2),
                nir_file = nirFile,
                red_file = redFile,
                green_file = greenFile,
                blue_file = blueFile,
                swir1_file = swir1File,
                swir2_file = swir2File,
                r_composite = Math.Max(1, nir),
                g_composite = Math.Max(1, red),
                b_composite = Math.Max(1, green)
            };
        }
    }
}
