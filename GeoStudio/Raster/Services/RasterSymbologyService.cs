using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using OSGeo.GDAL;

namespace GeoStudio.Raster.Services
{
    public class RasterClassItem
    {
        public int Value { get; set; }
        public string Label { get; set; } = string.Empty;
        public string ColorHex { get; set; } = "#000000";
        public byte R { get; set; }
        public byte G { get; set; }
        public byte B { get; set; }
        public byte A { get; set; } = 255;
        public bool IsVisible { get; set; } = true;
    }

    public static class RasterSymbologyService
    {
        public static readonly Dictionary<string, uint[]> LayerCustomLuts = new();

        public static readonly Dictionary<int, (string Name, string Hex)> Lulc22Taxonomy = new()
        {
            { 0,   ("Outside AOI", "#00000000") },
            { 10,  ("Tree Cover", "#228B22") },
            { 11,  ("Dense Forest", "#006400") },
            { 12,  ("Sparse Forest / Plantation", "#90EE90") },
            { 13,  ("Degraded Forest", "#808000") },
            { 20,  ("Shrubland", "#BDB76B") },
            { 30,  ("Grassland", "#ADFF2F") },
            { 40,  ("Cropland", "#FFA500") },
            { 41,  ("Irrigated Cropland", "#FFD700") },
            { 42,  ("Fallow / Rainfed Cropland", "#D2B48C") },
            { 50,  ("Built-up / Urban", "#FF4500") },
            { 60,  ("Bare / Sparse Veg", "#C0C0C0") },
            { 61,  ("Rocky / Barren", "#696969") },
            { 62,  ("Sandy / Alluvial", "#F5DEB3") },
            { 70,  ("Snow / Ice", "#FFFFFF") },
            { 80,  ("Water", "#0040FF") },
            { 81,  ("Permanent Water", "#0000CD") },
            { 82,  ("Seasonal Water", "#4682B4") },
            { 90,  ("Wetland", "#00CED1") },
            { 91,  ("Flooded Vegetation", "#008080") },
            { 92,  ("Mudflat / Bare Wetland", "#A0522D") },
            { 95,  ("Mangroves", "#006666") },
            { 100, ("Moss / Lichen", "#98FF98") }
        };

        public static List<RasterClassItem> GetLulc22Preset()
        {
            var list = new List<RasterClassItem>();
            foreach (var kvp in Lulc22Taxonomy)
            {
                var (r, g, b, a) = ParseHexToRgba(kvp.Value.Hex);
                list.Add(new RasterClassItem
                {
                    Value = kvp.Key,
                    Label = kvp.Value.Name,
                    ColorHex = kvp.Value.Hex,
                    R = r, G = g, B = b, A = a,
                    IsVisible = kvp.Key != 0
                });
            }
            return list;
        }

        public static List<RasterClassItem> GetDynamicWorldPreset()
        {
            var dw = new (int Val, string Name, string Hex)[]
            {
                (0, "Water", "#419BDF"),
                (1, "Trees", "#397D49"),
                (2, "Grass", "#88B053"),
                (3, "Flooded Vegetation", "#7A87C6"),
                (4, "Crops", "#E49635"),
                (5, "Shrub & Scrub", "#DFC35A"),
                (6, "Built Area", "#C4281B"),
                (7, "Bare Ground", "#A59B8F"),
                (8, "Snow & Ice", "#B39FE1")
            };

            return dw.Select(d =>
            {
                var (r, g, b, a) = ParseHexToRgba(d.Hex);
                return new RasterClassItem { Value = d.Val, Label = d.Name, ColorHex = d.Hex, R = r, G = g, B = b, A = a };
            }).ToList();
        }

        public static (byte R, byte G, byte B, byte A) ParseHexToRgba(string hex)
        {
            if (string.IsNullOrWhiteSpace(hex)) return (0, 0, 0, 255);
            string h = hex.Trim().TrimStart('#');
            if (h.Length == 8)
            {
                byte a = byte.Parse(h.Substring(0, 2), NumberStyles.HexNumber);
                byte r = byte.Parse(h.Substring(2, 2), NumberStyles.HexNumber);
                byte g = byte.Parse(h.Substring(4, 2), NumberStyles.HexNumber);
                byte b = byte.Parse(h.Substring(6, 2), NumberStyles.HexNumber);
                return (r, g, b, a);
            }
            if (h.Length == 6)
            {
                byte r = byte.Parse(h.Substring(0, 2), NumberStyles.HexNumber);
                byte g = byte.Parse(h.Substring(2, 2), NumberStyles.HexNumber);
                byte b = byte.Parse(h.Substring(4, 2), NumberStyles.HexNumber);
                return (r, g, b, 255);
            }
            return (0, 0, 0, 255);
        }

        public static List<RasterClassItem> ExtractOrScanClasses(string filePath)
        {
            var classes = new List<RasterClassItem>();
            if (!File.Exists(filePath)) return classes;

            GdalCacheManager.Initialize();
            using var ds = Gdal.Open(filePath, Access.GA_ReadOnly);
            if (ds == null || ds.RasterCount < 1) return classes;

            var b1 = ds.GetRasterBand(1);
            ColorTable? ct = null;
            try { ct = b1.GetRasterColorTable(); } catch { }

            if (ct != null && ct.GetCount() > 0)
            {
                int cnt = ct.GetCount();
                HashSet<byte>? presentVals = null;
                if (cnt > 32)
                {
                    try
                    {
                        int sW = Math.Min(512, ds.RasterXSize);
                        int sH = Math.Min(512, ds.RasterYSize);
                        byte[] sBuf = new byte[sW * sH];
                        b1.ReadRaster(0, 0, ds.RasterXSize, ds.RasterYSize, sBuf, sW, sH, 0, 0);
                        presentVals = new HashSet<byte>(sBuf);
                    }
                    catch { }
                }

                for (int i = 0; i < cnt; i++)
                {
                    ColorEntry entry = ct.GetColorEntry(i);
                    byte r = (byte)Math.Clamp((int)entry.c1, 0, 255);
                    byte g = (byte)Math.Clamp((int)entry.c2, 0, 255);
                    byte b = (byte)Math.Clamp((int)entry.c3, 0, 255);
                    byte a = (byte)Math.Clamp((int)entry.c4, 0, 255);

                    if (presentVals != null && !presentVals.Contains((byte)i) && !Lulc22Taxonomy.ContainsKey(i) && (a == 0 || (r == 0 && g == 0 && b == 0)))
                    {
                        continue;
                    }

                    if (i == 0) a = 0; // Class 0 outside AOI transparent

                    // Check if matches standard LULC name
                    string label = Lulc22Taxonomy.TryGetValue(i, out var tax) ? tax.Name : $"Class {i}";
                    string hex = a == 0 ? "#00000000" : $"#{r:X2}{g:X2}{b:X2}";

                    classes.Add(new RasterClassItem
                    {
                        Value = i,
                        Label = label,
                        ColorHex = hex,
                        R = r, G = g, B = b, A = a,
                        IsVisible = a != 0
                    });
                }
                if (classes.Count > 0) return classes;
            }

            // Fallback: scan unique integer values from small sample window
            int sampleW = Math.Min(512, ds.RasterXSize);
            int sampleH = Math.Min(512, ds.RasterYSize);
            byte[] buf = new byte[sampleW * sampleH];
            b1.ReadRaster(0, 0, ds.RasterXSize, ds.RasterYSize, buf, sampleW, sampleH, 0, 0);

            var uniqueVals = buf.Distinct().OrderBy(v => v).ToList();
            bool isLulcMatched = uniqueVals.Any(v => v is 11 or 12 or 13 or 41 or 42 or 60 or 61 or 62 or 81 or 82);

            foreach (var val in uniqueVals)
            {
                if (val == 0)
                {
                    classes.Add(new RasterClassItem { Value = 0, Label = "Outside AOI / NoData", ColorHex = "#00000000", R = 0, G = 0, B = 0, A = 0, IsVisible = false });
                    continue;
                }

                if (isLulcMatched && Lulc22Taxonomy.TryGetValue(val, out var tax))
                {
                    var (r, g, b, a) = ParseHexToRgba(tax.Hex);
                    classes.Add(new RasterClassItem { Value = val, Label = tax.Name, ColorHex = tax.Hex, R = r, G = g, B = b, A = a });
                }
                else
                {
                    // Generate visually distinct categorical color
                    double hue = (val * 137.508) % 360.0; // golden ratio distribution
                    var (r, g, b) = HslToRgb(hue / 360.0, 0.75, 0.50);
                    string hex = $"#{r:X2}{g:X2}{b:X2}";
                    classes.Add(new RasterClassItem { Value = val, Label = $"Class {val}", ColorHex = hex, R = r, G = g, B = b, A = 255 });
                }
            }

            return classes;
        }

        public static (byte R, byte G, byte B) HslToRgb(double h, double s, double l)
        {
            double r, g, b;
            if (s == 0) r = g = b = l;
            else
            {
                double q = l < 0.5 ? l * (1 + s) : l + s - l * s;
                double p = 2 * l - q;
                r = HueToRgb(p, q, h + 1.0 / 3);
                g = HueToRgb(p, q, h);
                b = HueToRgb(p, q, h - 1.0 / 3);
            }
            return ((byte)(r * 255), (byte)(g * 255), (byte)(b * 255));
        }

        private static double HueToRgb(double p, double q, double t)
        {
            if (t < 0) t += 1;
            if (t > 1) t -= 1;
            if (t < 1.0 / 6) return p + (q - p) * 6 * t;
            if (t < 1.0 / 2) return q;
            if (t < 2.0 / 3) return p + (q - p) * (2.0 / 3 - t) * 6;
            return p;
        }
    }
}
