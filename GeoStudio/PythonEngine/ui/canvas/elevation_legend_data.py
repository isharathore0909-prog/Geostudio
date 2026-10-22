# -*- coding: utf-8 -*-
"""
GeoStudio - Legend Data & Layer Configuration Helper
Provides color ramp stoppoints and configures legend parameters for LiDAR & raster DEM layers.
"""

from core.elevation_styler import ElevationStyler
from core.lidar.lidar_styler import LidarStyler

RAMP_STOPS = {
    "Turbo": [
        (0.00, "#30123b"), (0.15, "#4662d8"), (0.30, "#28bbec"),
        (0.45, "#40e0d0"), (0.60, "#a2fc3c"), (0.75, "#febc2b"),
        (0.90, "#f86214"), (1.00, "#7a0403")
    ],
    "Viridis": [
        (0.00, "#440154"), (0.25, "#3b528b"), (0.50, "#21918c"),
        (0.75, "#5ec962"), (1.00, "#fde725")
    ],
    "Magma": [
        (0.00, "#000004"), (0.25, "#51127c"), (0.50, "#b73779"),
        (0.75, "#fc8961"), (1.00, "#fcfdbf")
    ],
    "Spectral": [
        (0.00, "#9e0142"), (0.20, "#d53e4f"), (0.40, "#fee08b"),
        (0.60, "#e6f598"), (0.80, "#66c2a5"), (1.00, "#5e4fa2")
    ],
    "Plasma": [
        (0.00, "#0d0887"), (0.25, "#6a00a8"), (0.50, "#b12a90"),
        (0.75, "#e16462"), (1.00, "#fca636")
    ],
    "RdYlGn": [
        (0.00, "#d73027"), (0.25, "#fdae61"), (0.50, "#ffffbf"),
        (0.75, "#a6d96a"), (1.00, "#1a9850")
    ],
    "Blues": [
        (0.00, "#f7fbff"), (0.30, "#9ecae1"), (0.60, "#4292c6"),
        (0.85, "#08519c"), (1.00, "#08306b")
    ],
    "Greys": [
        (0.00, "#111827"), (0.25, "#334155"), (0.50, "#64748b"),
        (0.75, "#cbd5e1"), (1.00, "#f8fafc")
    ],
    "YlOrRd": [
        (0.00, "#ffffb2"), (0.30, "#fecc5c"), (0.60, "#fd8d3c"),
        (0.85, "#f03b20"), (1.00, "#bd0026")
    ]
}


def configure_lidar_legend(widget, layer, mode: str = None) -> bool:
    """Configures the legend widget for point cloud layers. Returns True if active."""
    widget.layer_name = layer.name()

    renderer = getattr(layer, "renderer", lambda: None)()
    r_name = renderer.__class__.__name__ if renderer else ""

    if "Rgb" in r_name or hasattr(renderer, "redAttribute"):
        return False

    attrs = [a.lower() for a in LidarStyler.get_attribute_names(layer)]
    has_rgb_data = "red" in attrs and "green" in attrs and "blue" in attrs

    if mode is None or mode == "auto":
        if has_rgb_data:
            return False
        if "Classified" in r_name:
            attr = getattr(renderer, "attribute", lambda: "")()
            mode = "return_num" if "return" in attr.lower() else "classification"
        elif "Ramp" in r_name:
            attr = getattr(renderer, "attribute", lambda: "")().lower()
            if "intensity" in attr: mode = "intensity"
            elif "hag" in attr or "height" in attr: mode = "hag"
            elif "scan" in attr or "angle" in attr: mode = "scan_angle"
            elif "source" in attr: mode = "point_source_id"
            elif "density" in attr: mode = "point_density"
            elif "delta" in attr: mode = "return_delta"
            elif "ndvi" in attr: mode = "ndvi"
            elif "ndwi" in attr: mode = "ndwi"
            else: mode = "elevation"
        else:
            mode = "elevation"

    mode = mode.lower()
    widget.mode = mode

    if mode in ["rgb", "true_color", "true color", "rgb (true color)"]:
        return False
    if mode == "rgb_elev" and has_rgb_data:
        return False

    if mode in ["elevation", "rgb_elev"]:
        z_attr = LidarStyler._find_attr(layer, ["Z", "Elevation", "Height"])
        z_min, z_max = LidarStyler._get_attribute_range(layer, z_attr, 0.0, 100.0)
        widget.legend_type = "gradient"
        widget.title = "Elevation (Z)"
        widget.min_val = float(z_min)
        widget.max_val = float(z_max)
        widget.unit_str = "m"
        widget.ramp_name = "Turbo"
        widget.setFixedSize(126, 260)

    elif mode == "intensity":
        int_attr = LidarStyler._find_attr(layer, ["Intensity", "intensity", "reflectance", "LaserIntensity"], fallback="Intensity")
        i_min, i_max = LidarStyler._get_attribute_range(layer, int_attr, 0.0, 65535.0)
        widget.legend_type = "gradient"
        widget.title = "Laser Intensity"
        widget.min_val = float(i_min)
        widget.max_val = float(i_max)
        widget.unit_str = ""
        widget.ramp_name = "Greys"
        widget.setFixedSize(126, 260)

    elif mode == "classification":
        widget.legend_type = "discrete"
        widget.title = "LAS Classification"
        widget.categories = [
            ("#d4a373", "2: Ground"), ("#86efac", "3: Low Veg"),
            ("#22c55e", "4: Med Veg"), ("#15803d", "5: High Veg"),
            ("#ef4444", "6: Building"), ("#0284c7", "9: Water"),
            ("#334155", "11: Road Surface"), ("#64748b", "7: Low Noise"),
        ]
        widget.setFixedSize(148, 220)

    elif mode == "return_num":
        widget.legend_type = "discrete"
        widget.title = "Return Number"
        widget.categories = [
            ("#10b981", "1: 1st (Canopy/Roof)"), ("#3b82f6", "2: Second Return"),
            ("#f59e0b", "3: Third Return"), ("#ef4444", "4: Fourth Return"),
            ("#8b5cf6", "5+: Last (Ground)"),
        ]
        widget.setFixedSize(156, 170)

    elif mode == "hag":
        hag_attr = LidarStyler._find_attr(layer, ["HeightAboveGround", "HAG", "hag", "NormalizedZ", "Z"])
        h_min, h_max = LidarStyler._get_attribute_range(layer, hag_attr, 0.0, 35.0)
        widget.legend_type = "gradient"
        widget.title = "Height Above Grnd"
        widget.min_val = max(0.0, float(h_min))
        widget.max_val = max(5.0, float(h_max))
        widget.unit_str = "m"
        widget.ramp_name = "Viridis"
        widget.setFixedSize(132, 260)

    elif mode == "scan_angle":
        sa_attr = LidarStyler._find_attr(layer, ["ScanAngleRank", "ScanAngle", "scan_angle", "Angle"])
        s_min, s_max = LidarStyler._get_attribute_range(layer, sa_attr, -35.0, 35.0)
        widget.legend_type = "gradient"
        widget.title = "Scan Angle"
        widget.min_val = float(s_min)
        widget.max_val = float(s_max)
        widget.unit_str = "°"
        widget.ramp_name = "Spectral"
        widget.setFixedSize(126, 260)

    elif mode == "point_source_id":
        widget.legend_type = "gradient"
        widget.title = "Point Source ID"
        widget.min_val = 1.0
        widget.max_val = 10.0
        widget.unit_str = "ID"
        widget.ramp_name = "Turbo"
        widget.setFixedSize(126, 260)

    elif mode == "source_layer":
        widget.legend_type = "gradient"
        widget.title = "Source File / Layer"
        widget.min_val = 0.0
        widget.max_val = 10.0
        widget.unit_str = "Tile"
        widget.ramp_name = "Turbo"
        widget.setFixedSize(126, 260)

    elif mode == "segment":
        widget.legend_type = "gradient"
        widget.title = "Segment / Cluster"
        widget.min_val = 0.0
        widget.max_val = 100.0
        widget.unit_str = "#"
        widget.ramp_name = "Turbo"
        widget.setFixedSize(126, 260)

    elif mode == "point_index":
        widget.legend_type = "gradient"
        widget.title = "Point Index"
        widget.min_val = 0.0
        widget.max_val = 100000.0
        widget.unit_str = "pts"
        widget.ramp_name = "Plasma"
        widget.setFixedSize(130, 260)

    elif mode == "cir":
        widget.legend_type = "discrete"
        widget.title = "Color Infrared (CIR)"
        widget.categories = [
            ("#ef4444", "NIR: Veg Biomass"),
            ("#22c55e", "Red: Healthy Soil"),
            ("#3b82f6", "Green: Moisture/Water"),
        ]
        widget.setFixedSize(160, 125)

    elif mode == "ndvi":
        widget.legend_type = "gradient"
        widget.title = "NDVI (Vegetation)"
        widget.min_val = -0.2
        widget.max_val = 1.0
        widget.unit_str = ""
        widget.ramp_name = "RdYlGn"
        widget.setFixedSize(126, 260)

    elif mode == "ndwi":
        widget.legend_type = "gradient"
        widget.title = "NDWI (Water Index)"
        widget.min_val = -0.5
        widget.max_val = 0.5
        widget.unit_str = ""
        widget.ramp_name = "Blues"
        widget.setFixedSize(126, 260)

    elif mode == "point_density":
        widget.legend_type = "gradient"
        widget.title = "Point Density"
        widget.min_val = 1.0
        widget.max_val = 50.0
        widget.unit_str = "p/m²"
        widget.ramp_name = "Plasma"
        widget.setFixedSize(130, 260)

    elif mode == "withheld":
        widget.legend_type = "discrete"
        widget.title = "Withheld Flag"
        widget.categories = [
            ("#10b981", "0: Valid (Not Withheld)"),
            ("#ef4444", "1: Flagged Outlier / Noise"),
        ]
        widget.setFixedSize(165, 105)

    elif mode == "keypoint":
        widget.legend_type = "discrete"
        widget.title = "Key Point Flag"
        widget.categories = [
            ("#64748b", "0: Normal Point"),
            ("#f59e0b", "1: Model Key Point"),
        ]
        widget.setFixedSize(155, 105)

    elif mode == "overlap":
        widget.legend_type = "discrete"
        widget.title = "Overlap Flag"
        widget.categories = [
            ("#64748b", "0: Primary Swath"),
            ("#06b6d4", "1: Swath Overlap"),
        ]
        widget.setFixedSize(155, 105)

    elif mode == "return_delta":
        widget.legend_type = "gradient"
        widget.title = "Return Delta (ΔZ)"
        widget.min_val = 0.0
        widget.max_val = 30.0
        widget.unit_str = "m"
        widget.ramp_name = "YlOrRd"
        widget.setFixedSize(130, 260)

    return True


def configure_raster_legend(widget, layer) -> bool:
    """Configures the legend widget for raster DEM layers. Returns True if active."""
    if not layer or not layer.isValid() or not ElevationStyler.is_dem_or_elevation(layer):
        return False

    stats = ElevationStyler.get_valid_elevation_stats(layer, 1)
    if not stats:
        return False

    widget.layer_name = layer.name()
    widget.legend_type = "gradient"
    widget.title = "Raster Elevation"
    widget.min_val = float(stats["min"])
    widget.max_val = float(stats["max"])
    widget.unit_str = "m"
    widget.ramp_name = "Turbo"
    widget.setFixedSize(126, 260)
    return True
