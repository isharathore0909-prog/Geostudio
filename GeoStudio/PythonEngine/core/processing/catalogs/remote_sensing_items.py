# -*- coding: utf-8 -*-
"""
GeoStudio - Remote Sensing Algorithm Definitions
Lists algorithm entries for Landsat, Spectral Indices, Radiometry, and Hyperspectral.
"""

from ..algorithm_definition import AlgorithmDefinition

LANDSAT_ITEMS = [
    AlgorithmDefinition(
        "Landsat Metadata & Auto-Calibration (MTL.txt)",
        "landsat:mtl_ingest",
        "Landsat & Remote Sensing",
        "Landsat Workflows",
        "Parses MTL.txt metadata and performs automated DN to TOA Radiance & Reflectance conversion with sun angle correction.",
        "landsat_mtl",
        supports_gpu=True,
    ),
    AlgorithmDefinition(
        "Land Surface Temperature (LST)",
        "landsat:lst",
        "Landsat & Remote Sensing",
        "Landsat Workflows",
        "Computes Brightness Temperature & LST in Celsius/Kelvin from Landsat thermal bands (B10/B11 or B6) with FVC emissivity correction.",
        "landsat_lst",
        supports_gpu=True,
    ),
    AlgorithmDefinition(
        "Landsat 7 SLC-Off Gap Fill",
        "landsat:slc_off",
        "Landsat & Remote Sensing",
        "Landsat Workflows",
        "Recovers scan line corrector (SLC-off) data gaps using local focal histogram matching.",
        "landsat_generic",
        supports_gpu=True,
    ),
    AlgorithmDefinition(
        "Landsat QA Pixel Cloud & Shadow Mask",
        "landsat:cloud_mask",
        "Landsat & Remote Sensing",
        "Landsat Workflows",
        "Decodes QA_PIXEL bitmask to generate transparent masks for clouds, shadows, cirrus, snow, and water.",
        "landsat_generic",
        supports_gpu=True,
    ),
    AlgorithmDefinition(
        "Landsat RGB Composite Presets",
        "landsat:composites",
        "Landsat & Remote Sensing",
        "Landsat Workflows",
        "One-click presets for Natural Color (4-3-2), Color Infrared (5-4-3), Agriculture (6-5-2), and Geology (7-6-4).",
        "sat_composite",
        supports_gpu=True,
    ),
]

SPECTRAL_INDICES_ITEMS = [
    AlgorithmDefinition(
        "NDVI (Vegetation Index)",
        "satellite:ndvi",
        "Landsat & Remote Sensing",
        "Spectral Indices Studio",
        "Normalized Difference Vegetation Index: (NIR - Red) / (NIR + Red)",
        "spectral_index",
        supports_gpu=True,
    ),
    AlgorithmDefinition(
        "NDWI / MNDWI (Water Index)",
        "satellite:ndwi",
        "Landsat & Remote Sensing",
        "Spectral Indices Studio",
        "Normalized Difference Water Index: (Green - NIR) / (Green + NIR) and Modified NDWI.",
        "spectral_index",
        supports_gpu=True,
    ),
    AlgorithmDefinition(
        "EVI / SAVI (Soil Adjusted)",
        "satellite:evi_savi",
        "Landsat & Remote Sensing",
        "Spectral Indices Studio",
        "Enhanced Vegetation Index and Soil-Adjusted Vegetation Index with L factor.",
        "spectral_index",
        supports_gpu=True,
    ),
    AlgorithmDefinition(
        "NDBI (Built-Up Index)",
        "satellite:ndbi",
        "Landsat & Remote Sensing",
        "Spectral Indices Studio",
        "Normalized Difference Built-up Index: (SWIR1 - NIR) / (SWIR1 + NIR)",
        "spectral_index",
        supports_gpu=True,
    ),
    AlgorithmDefinition(
        "NBR / dNBR (Burn Ratio)",
        "satellite:nbr",
        "Landsat & Remote Sensing",
        "Spectral Indices Studio",
        "Normalized Burn Ratio: (NIR - SWIR2) / (NIR + SWIR2) for wildfire scar mapping.",
        "spectral_index",
        supports_gpu=True,
    ),
    AlgorithmDefinition(
        "NDSI (Snow Index)",
        "satellite:ndsi",
        "Landsat & Remote Sensing",
        "Spectral Indices Studio",
        "Normalized Difference Snow Index: (Green - SWIR1) / (Green + SWIR1)",
        "spectral_index",
        supports_gpu=True,
    ),
]

ENHANCEMENT_ITEMS = [
    AlgorithmDefinition(
        "Pansharpening (Brovey & IHS)",
        "raster:pansharpen",
        "Landsat & Remote Sensing",
        "Image Enhancement & Radiometry",
        "Fuses high-res panchromatic band with multispectral bands to sharpen spatial resolution.",
        "raster_pansharpen",
        supports_gpu=True,
    ),
    AlgorithmDefinition(
        "Dark Object Subtraction (DOS1)",
        "raster:dos1",
        "Landsat & Remote Sensing",
        "Image Enhancement & Radiometry",
        "Image-based atmospheric haze correction via dark pixel histogram minimum subtraction.",
        "raster_generic",
        supports_gpu=True,
    ),
    AlgorithmDefinition(
        "Contrast Stretching (2%-98% Cut)",
        "raster:contrast_stretch",
        "Landsat & Remote Sensing",
        "Image Enhancement & Radiometry",
        "Dynamic histogram stretch to remove atmospheric haze and enhance dynamic range.",
        "raster_generic",
        supports_gpu=True,
    ),
]

HYPERSPECTRAL_ITEMS = [
    AlgorithmDefinition(
        "Principal Component Analysis (PCA)",
        "raster:pca",
        "Landsat & Remote Sensing",
        "Hyperspectral & Dimensionality",
        "Uncorrelated orthogonal spectral component transformation for multi-band dimensionality reduction.",
        "raster_pca",
        supports_gpu=True,
    ),
    AlgorithmDefinition(
        "Spectral Angle Mapper (SAM)",
        "raster:sam",
        "Landsat & Remote Sensing",
        "Hyperspectral & Dimensionality",
        "Supervised spectral classification comparing n-dimensional angle against endmember signatures.",
        "raster_sam",
        supports_gpu=True,
    ),
    AlgorithmDefinition(
        "Tasseled Cap Transformation (K-T)",
        "raster:tasseled_cap",
        "Landsat & Remote Sensing",
        "Hyperspectral & Dimensionality",
        "Derives Brightness, Greenness, and Wetness orthogonal components for sensor calibration.",
        "raster_generic",
        supports_gpu=True,
    ),
]
