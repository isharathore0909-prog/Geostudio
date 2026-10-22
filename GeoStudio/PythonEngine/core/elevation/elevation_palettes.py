# -*- coding: utf-8 -*-
"""
GeoStudio - Elevation & DEM Color Palette Presets
Exact Global Mapper Atlas, ArcGIS, and USGS Color Ramps.
"""

ELEVATION_PRESETS = {
    "GLOBAL_MAPPER_ATLAS": {
        "name": "🏔 Global Mapper Atlas (Blue -> Cyan -> Green -> Yellow -> Red)",
        "description": "Exact Global Mapper Pro Atlas Shader: Blue valleys, Cyan water channels, Green dominant plains, Yellow uplands, Orange structures, and Red highest peaks.",
        "stops": [
            (0.00, "#0000ff", "Min Elevation"),
            (0.08, "#00d4ff", "Low Water"),
            (0.18, "#00b828", "Lowlands"),
            (0.45, "#0fa619", "Dominant Plains"),
            (0.70, "#60c800", "Upper Plains"),
            (0.82, "#ffd600", "Highland / Slope"),
            (0.92, "#ff6600", "Elevated Features"),
            (1.00, "#cc0000", "Max Elevation"),
        ]
    },
    "GLOBAL_MAPPER_TERRAIN": {
        "name": "🌿 Global Mapper Terrain (Earth Tones)",
        "description": "Lush forest lowlands, golden plains, terracotta mountains, and snowy peaks.",
        "stops": [
            (0.00, "#196828", "Lowlands"),
            (0.15, "#3fa235", "Valleys"),
            (0.30, "#8cc645", "Plains"),
            (0.48, "#e5df63", "Plateaus"),
            (0.65, "#dda246", "Foothills"),
            (0.78, "#b45a24", "Highlands"),
            (0.88, "#7d3f1f", "Mountains"),
            (0.96, "#96908c", "Rock"),
            (1.00, "#ffffff", "Snow"),
        ]
    },
    "ARCGIS_ELEVATION": {
        "name": "🌍 ArcGIS Elevation #1 (Earth Tones)",
        "description": "Standard ArcGIS terrain styling: rich green, chartreuse, warm yellow, ochre, sienna, and alpine summit tones.",
        "stops": [
            (0.00, "#267300", "Low"),
            (0.18, "#70a800", "Low-Mid"),
            (0.38, "#ffff73", "Mid"),
            (0.58, "#ffaa00", "Mid-High"),
            (0.78, "#a80000", "High"),
            (0.92, "#730000", "Very High"),
            (1.00, "#e6e6e6", "Summit"),
        ]
    },
    "SRTM_TOPO": {
        "name": "🗺 SRTM / USGS Topographic",
        "description": "Standard USGS Topographic relief colors suitable for worldwide DEMs and regional elevation mapping.",
        "stops": [
            (0.00, "#38a800", "0 m"),
            (0.20, "#70a800", "Valley"),
            (0.40, "#ffff00", "Plains"),
            (0.65, "#ff7f00", "Hills"),
            (0.85, "#7f3f00", "Highlands"),
            (1.00, "#ffffff", "Snow"),
        ]
    },
    "VIRIDIS": {
        "name": "🔮 Viridis (Perceptually Uniform)",
        "description": "High scientific clarity, colorblind-friendly continuous colormap from deep purple to teal and bright yellow.",
        "stops": [
            (0.00, "#440154", "Min"),
            (0.25, "#3b528b", "Low"),
            (0.50, "#21918c", "Mid"),
            (0.75, "#5ec962", "High"),
            (1.00, "#fde725", "Max"),
        ]
    },
    "TURBO": {
        "name": "🌈 Turbo (Vibrant High-Contrast)",
        "description": "Google Turbo colormap with exceptional dynamic range and feature separation across complex terrain.",
        "stops": [
            (0.00, "#30123b", "Min"),
            (0.20, "#4686fa", "Low"),
            (0.40, "#1ae4b6", "Mid-Low"),
            (0.60, "#a2fc3c", "Mid-High"),
            (0.80, "#fbb41a", "High"),
            (1.00, "#7a0403", "Max"),
        ]
    },
    "BATHO_TOPO": {
        "name": "🌊 Bathymetry + Topography (ETOPO)",
        "description": "Optimized for coastal and combined sea-land elevation models: deep marine blues to shoreline green and mountain brown.",
        "stops": [
            (0.00, "#081d58", "Deep Sea"),
            (0.25, "#41b6c4", "Shallow Sea"),
            (0.45, "#c7e9b4", "Coastline"),
            (0.60, "#238443", "Lowland"),
            (0.75, "#fe9929", "Upland"),
            (0.90, "#8c2d04", "Mountain"),
            (1.00, "#ffffff", "Glacier"),
        ]
    },
    "TERRAIN_MODERN": {
        "name": "🌿 Modern Emerald & Terracotta",
        "description": "Sleek modern cartographic palette with soft deep green valleys, sand plateaus, terracotta ridges, and silver peaks.",
        "stops": [
            (0.00, "#134e4a", "Deep Valley"),
            (0.25, "#10b981", "Lush Plain"),
            (0.50, "#f59e0b", "Warm Highland"),
            (0.75, "#b45309", "Ridge"),
            (1.00, "#f3f4f6", "Peak"),
        ]
    },
}
