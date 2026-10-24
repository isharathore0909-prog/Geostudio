using System;

namespace GeoStudio.Raster
{
    public static partial class ElevationShadedRelief
    {
        // Exact Global Mapper Pro Atlas Shader stops: Blue -> Cyan -> Green -> Yellow -> Orange -> Red
        public static readonly (float frac, byte r, byte g, byte b)[] AtlasStops = new[]
        {
            (0.00f, (byte)0,   (byte)0,   (byte)255), // Min Elevation - Deep Blue
            (0.08f, (byte)0,   (byte)212, (byte)255), // Low Water - Cyan
            (0.18f, (byte)0,   (byte)184, (byte)40),  // Lowlands - Fresh Green
            (0.45f, (byte)15,  (byte)166, (byte)25),  // Dominant Plains - Lush Green
            (0.70f, (byte)96,  (byte)200, (byte)0),   // Upper Plains - Chartreuse
            (0.82f, (byte)255, (byte)214, (byte)0),   // Highland / Slope - Yellow
            (0.92f, (byte)255, (byte)102, (byte)0),   // Elevated Features - Orange
            (1.00f, (byte)204, (byte)0,   (byte)0)    // Highest Peaks - Vivid Red
        };

        // Global Mapper Terrain Shader (Earth Tones)
        public static readonly (float frac, byte r, byte g, byte b)[] TerrainStops = new[]
        {
            (0.00f, (byte)25,  (byte)104, (byte)40),
            (0.15f, (byte)63,  (byte)162, (byte)53),
            (0.30f, (byte)140, (byte)198, (byte)69),
            (0.48f, (byte)229, (byte)223, (byte)99),
            (0.65f, (byte)221, (byte)162, (byte)70),
            (0.78f, (byte)180, (byte)90,  (byte)36),
            (0.88f, (byte)125, (byte)63,  (byte)31),
            (0.96f, (byte)150, (byte)144, (byte)140),
            (1.00f, (byte)255, (byte)255, (byte)255)
        };

        // Scientific Viridis
        public static readonly (float frac, byte r, byte g, byte b)[] ViridisStops = new[]
        {
            (0.00f, (byte)68,  (byte)1,   (byte)84),
            (0.25f, (byte)59,  (byte)82,  (byte)139),
            (0.50f, (byte)33,  (byte)145, (byte)140),
            (0.75f, (byte)94,  (byte)201, (byte)98),
            (1.00f, (byte)253, (byte)231, (byte)37)
        };

        // Scientific Magma
        public static readonly (float frac, byte r, byte g, byte b)[] MagmaStops = new[]
        {
            (0.00f, (byte)0,   (byte)0,   (byte)4),
            (0.25f, (byte)81,  (byte)18,  (byte)124),
            (0.50f, (byte)183, (byte)55,  (byte)121),
            (0.75f, (byte)252, (byte)137, (byte)97),
            (1.00f, (byte)252, (byte)253, (byte)191)
        };

        // Slope gradient stops: 0° (flat green) to 45°+ (extreme cliff red)
        public static readonly (float frac, byte r, byte g, byte b)[] SlopeStops = new[]
        {
            (0.00f, (byte)34,  (byte)197, (byte)94),  // Flat: 0° (#22c55e)
            (0.15f, (byte)132, (byte)204, (byte)22),  // Gentle: 5°-10° (#84cc16)
            (0.35f, (byte)234, (byte)179, (byte)8),   // Moderate: 15°-20° (#eab308)
            (0.60f, (byte)249, (byte)115, (byte)22),  // Steep: 25°-35° (#f97316)
            (1.00f, (byte)239, (byte)68,  (byte)68)   // Extreme: 45°+ (#ef4444)
        };

        // Aspect compass direction stops: 0° to 360°
        public static readonly (float frac, byte r, byte g, byte b)[] AspectStops = new[]
        {
            (0.0000f, (byte)227, (byte)26,  (byte)28),  // North (0°)
            (0.0625f, (byte)255, (byte)127, (byte)0),   // North-East (22.5°)
            (0.1875f, (byte)255, (byte)255, (byte)51),  // East (67.5°)
            (0.3125f, (byte)77,  (byte)175, (byte)74),  // South-East (112.5°)
            (0.4375f, (byte)55,  (byte)126, (byte)184), // South (157.5°)
            (0.5625f, (byte)152, (byte)78,  (byte)163), // South-West (202.5°)
            (0.6875f, (byte)247, (byte)129, (byte)191), // West (247.5°)
            (0.8125f, (byte)166, (byte)86,  (byte)40),  // North-West (292.5°)
            (0.9375f, (byte)227, (byte)26,  (byte)28),  // North (337.5°)
            (1.0000f, (byte)227, (byte)26,  (byte)28)   // North (360°)
        };

        // Topographic Wetness Index stops: Dry Ridge (Buff/Tan) to Saturated Riverbed (Deep Blue)
        public static readonly (float frac, byte r, byte g, byte b)[] TwiStops = new[]
        {
            (0.00f, (byte)245, (byte)235, (byte)200), // Very dry ridge (Tan)
            (0.20f, (byte)210, (byte)225, (byte)170), // Dry slope (Pale green)
            (0.40f, (byte)120, (byte)198, (byte)121), // Moderate moisture (Green)
            (0.65f, (byte)65,  (byte)182, (byte)196), // Wet (Cyan)
            (0.85f, (byte)34,  (byte)94,  (byte)168), // High wetness (Blue)
            (1.00f, (byte)8,   (byte)29,  (byte)88)   // Drainage / River (Deep Blue)
        };

        // Surface Curvature stops: Convex / Ridge (Red) -> Planar (Light Gray) -> Concave / Valley (Blue)
        public static readonly (float frac, byte r, byte g, byte b)[] CurvatureStops = new[]
        {
            (0.00f, (byte)215, (byte)48,  (byte)39),  // Convex / Ridge (Red)
            (0.25f, (byte)252, (byte)141, (byte)89),  // Moderately convex (Orange)
            (0.50f, (byte)240, (byte)240, (byte)240), // Planar / Flat (Light Gray)
            (0.75f, (byte)145, (byte)191, (byte)219), // Moderately concave (Cyan/Blue)
            (1.00f, (byte)69,  (byte)117, (byte)180)  // Concave / Valley (Deep Blue)
        };

        private static void InterpolateColor((float frac, byte r, byte g, byte b)[] stops, float normVal, out byte outR, out byte outG, out byte outB)
        {
            outR = 255; outG = 255; outB = 255;
            for (int s = 0; s < stops.Length - 1; s++)
            {
                var s0 = stops[s];
                var s1 = stops[s + 1];
                if (normVal >= s0.frac && (normVal <= s1.frac || s == stops.Length - 2))
                {
                    float t = (normVal - s0.frac) / (s1.frac - s0.frac + 1e-6f);
                    t = Math.Clamp(t, 0.0f, 1.0f);
                    outR = (byte)(s0.r + t * (s1.r - s0.r));
                    outG = (byte)(s0.g + t * (s1.g - s0.g));
                    outB = (byte)(s0.b + t * (s1.b - s0.b));
                    return;
                }
            }
        }
    }
}
