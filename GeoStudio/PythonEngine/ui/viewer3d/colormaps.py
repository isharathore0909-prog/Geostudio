# -*- coding: utf-8 -*-
"""
GeoStudio - 3D Viewer Colormaps Engine
Analytical & classified 3D color ramps for NumPy arrays in the OpenGL/3D viewport.
"""

import numpy as np


def apply_turbo_colormap(norm_vals: np.ndarray) -> np.ndarray:
    """High-contrast analytical Turbo colormap for 3D elevation."""
    x = np.clip(norm_vals, 0.0, 1.0)
    r = np.clip(0.1357 + x * (4.6153 + x * (-42.6603 + x * (132.131 + x * (-152.9423 + x * 59.2863)))), 0.0, 1.0)
    g = np.clip(0.0914 + x * (2.1941 + x * (4.8429 + x * (-14.1850 + x * (4.2773 + x * 2.8295)))), 0.0, 1.0)
    b = np.clip(0.1067 + x * (12.5841 + x * (-86.8524 + x * (230.3101 + x * (-267.9254 + x * 113.8821)))), 0.0, 1.0)
    return np.column_stack((r, g, b)).astype(np.float32)


def apply_viridis_colormap(norm_vals: np.ndarray) -> np.ndarray:
    """Perceptually uniform Viridis colormap."""
    x = np.clip(norm_vals, 0.0, 1.0)
    r = np.clip(0.267 + 2.0 * (x - 0.5) ** 2, 0.0, 1.0)
    g = np.clip(x * 0.9 + 0.1, 0.0, 1.0)
    b = np.clip(0.33 + 0.67 * (1.0 - x), 0.0, 1.0)
    return np.column_stack((r, g, b)).astype(np.float32)


def apply_spectral_colormap(norm_vals: np.ndarray) -> np.ndarray:
    """Spectral diverging colormap."""
    x = np.clip(norm_vals, 0.0, 1.0)
    r = np.clip(1.5 - np.abs(4.0 * x - 3.0), 0.0, 1.0)
    g = np.clip(1.5 - np.abs(4.0 * x - 2.0), 0.0, 1.0)
    b = np.clip(1.5 - np.abs(4.0 * x - 1.0), 0.0, 1.0)
    return np.column_stack((r, g, b)).astype(np.float32)


def apply_plasma_colormap(norm_vals: np.ndarray) -> np.ndarray:
    """Plasma perceptually uniform colormap."""
    x = np.clip(norm_vals, 0.0, 1.0)
    r = np.clip(0.05 + 0.9 * x, 0.0, 1.0)
    g = np.clip(0.1 + 0.8 * (x ** 1.5), 0.0, 1.0)
    b = np.clip(0.5 + 0.5 * (1.0 - x), 0.0, 1.0)
    return np.column_stack((r, g, b)).astype(np.float32)


def apply_rdylgn_colormap(norm_vals: np.ndarray) -> np.ndarray:
    """Red-Yellow-Green diverging colormap."""
    x = np.clip(norm_vals, 0.0, 1.0)
    r = np.clip(np.where(x < 0.5, 1.0, 2.0 * (1.0 - x)), 0.0, 1.0)
    g = np.clip(np.where(x < 0.5, 2.0 * x, 1.0), 0.0, 1.0)
    b = np.zeros_like(x)
    return np.column_stack((r, g, b)).astype(np.float32)


def apply_blues_colormap(norm_vals: np.ndarray) -> np.ndarray:
    """Single hue Blues colormap."""
    x = np.clip(norm_vals, 0.0, 1.0)
    r = np.clip(0.95 - 0.9 * x, 0.0, 1.0)
    g = np.clip(0.95 - 0.6 * x, 0.0, 1.0)
    b = np.clip(1.0 - 0.2 * (1.0 - x), 0.0, 1.0)
    return np.column_stack((r, g, b)).astype(np.float32)


def apply_ylorrd_colormap(norm_vals: np.ndarray) -> np.ndarray:
    """Yellow-Orange-Red sequential colormap."""
    x = np.clip(norm_vals, 0.0, 1.0)
    r = np.ones_like(x)
    g = np.clip(1.0 - 0.9 * x, 0.0, 1.0)
    b = np.clip(0.7 * (1.0 - x) ** 2, 0.0, 1.0)
    return np.column_stack((r, g, b)).astype(np.float32)


def apply_categorical_colormap(values: np.ndarray) -> np.ndarray:
    """Applies a distinct qualitative palette for integer categorical labels."""
    vals = values.astype(np.int64)
    r = ((vals * 73 + 12) % 256) / 255.0
    g = ((vals * 151 + 65) % 256) / 255.0
    b = ((vals * 227 + 130) % 256) / 255.0
    return np.column_stack((r, g, b)).astype(np.float32)


def apply_return_number_colormap(ret_num: np.ndarray) -> np.ndarray:
    """Return number coloring: 1st=Emerald, 2nd=Blue, 3rd=Amber, 4th=Red, 5+=Purple."""
    r_map = {
        1: (0.06, 0.72, 0.50),   # First Return
        2: (0.23, 0.51, 0.96),   # Second Return
        3: (0.96, 0.62, 0.04),   # Third Return
        4: (0.93, 0.27, 0.27),   # Fourth Return
        5: (0.54, 0.36, 0.96),   # 5+
    }
    cols = np.zeros((len(ret_num), 3), dtype=np.float32)
    cols[:] = (0.54, 0.36, 0.96)
    for rn, c in r_map.items():
        if rn < 5:
            cols[ret_num == rn] = c
        else:
            cols[ret_num >= 5] = c
    return cols


def apply_las_classification(classes: np.ndarray) -> np.ndarray:
    """Applies ASPRS standard classification colors to 3D points."""
    c_map = {
        0: (0.58, 0.64, 0.72),   # 0: Never Classified (Slate)
        1: (0.79, 0.83, 0.88),   # 1: Unassigned
        2: (0.83, 0.64, 0.45),   # 2: Ground (Tan/Brown)
        3: (0.52, 0.94, 0.67),   # 3: Low Veg
        4: (0.13, 0.77, 0.36),   # 4: Med Veg
        5: (0.08, 0.50, 0.24),   # 5: High Veg / Canopy
        6: (0.93, 0.27, 0.27),   # 6: Building / Roof
        7: (0.39, 0.45, 0.54),   # 7: Low Point / Noise
        8: (0.96, 0.62, 0.04),   # 8: Model Keypoint
        9: (0.01, 0.52, 0.78),   # 9: Water
        10: (0.92, 0.28, 0.60),  # 10: Rail
        11: (0.20, 0.25, 0.33),  # 11: Road Surface
        12: (0.66, 0.33, 0.97),  # 12: Overlap Reserved
        13: (0.92, 0.70, 0.03),  # 13: Wire - Guard
        14: (0.97, 0.45, 0.09),  # 14: Wire - Conductor
        15: (0.52, 0.80, 0.09),  # 15: Transmission Tower
        17: (0.47, 0.44, 0.42),  # 17: Bridge Deck
        18: (0.02, 0.71, 0.83),  # 18: High Noise
    }
    cols = np.zeros((len(classes), 3), dtype=np.float32)
    cols[:] = (0.79, 0.83, 0.88)
    for c_id, c in c_map.items():
        cols[classes == c_id] = c
    return cols
