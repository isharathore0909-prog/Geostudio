# -*- coding: utf-8 -*-
"""
GeoStudio - Hydrology: Flow Routing
D8 Flow Direction with Garbrecht & Martz Flat Resolution and Kahn's Topological Flow Accumulation.
"""

from collections import deque
from typing import Optional, Tuple
import numpy as np
import scipy.ndimage as ndi


def flow_direction_array(
    dem: np.ndarray,
    cellsize_x: float = 1.0,
    cellsize_y: float = 1.0,
    nodata_val: Optional[float] = None
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Calculate D8 steepest slope flow direction with Garbrecht & Martz flat resolution.
    Prevents horizontal striping and parallel scanlines across flat surfaces and filled depressions.
    """
    H, W = dem.shape
    if nodata_val is not None and not np.isnan(nodata_val):
        nodata_mask = (dem == nodata_val) | np.isnan(dem)
    else:
        nodata_mask = np.isnan(dem)

    diag_dist = float(np.sqrt(cellsize_x ** 2 + cellsize_y ** 2))

    # (dr, dc, code, distance, opp_code)
    directions = [
        (0, 1, 1, cellsize_x, 16),        # East
        (1, 1, 2, diag_dist, 32),         # South-East
        (1, 0, 4, cellsize_y, 64),        # South
        (1, -1, 8, diag_dist, 128),       # South-West
        (0, -1, 16, cellsize_x, 1),       # West
        (-1, -1, 32, diag_dist, 2),       # North-West
        (-1, 0, 64, cellsize_y, 4),       # North
        (-1, 1, 128, diag_dist, 8),       # North-East
    ]

    valid_center = ~nodata_mask
    clean_dem = np.where(valid_center, dem, 0.0)
    flowdir = np.zeros((H, W), dtype=np.uint8)
    max_slope = np.zeros((H, W), dtype=np.float32)

    for dr, dc, code, dist, _ in directions:
        nbr_z = np.zeros_like(dem)
        nbr_valid = np.zeros((H, W), dtype=bool)

        r_slice = slice(max(0, -dr), H - max(0, dr))
        c_slice = slice(max(0, -dc), W - max(0, dc))
        nbr_r_slice = slice(max(0, dr), H + min(0, dr))
        nbr_c_slice = slice(max(0, dc), W + min(0, dc))

        nbr_z[r_slice, c_slice] = dem[nbr_r_slice, nbr_c_slice]
        nbr_valid[r_slice, c_slice] = valid_center[nbr_r_slice, nbr_c_slice]

        valid_pair = valid_center & nbr_valid
        drop = np.where(valid_pair, (clean_dem - nbr_z) / dist, 0.0)
        better = valid_pair & (drop > max_slope) & (drop > 1e-6)
        flowdir[better] = code
        max_slope[better] = drop[better]

    flowdir[nodata_mask] = 0

    # Vectorized Garbrecht & Martz flat area resolution
    flat_cells = (flowdir == 0) & (~nodata_mask)
    if np.any(flat_cells):
        dist = ndi.distance_transform_edt(flat_cells)
        flat_flowdir = np.zeros((H, W), dtype=np.uint8)
        min_dist = np.copy(dist)

        for dr, dc, code, _, _ in directions:
            r_slice = slice(max(0, -dr), H - max(0, dr))
            c_slice = slice(max(0, -dc), W - max(0, dc))
            nbr_r_slice = slice(max(0, dr), H + min(0, dr))
            nbr_c_slice = slice(max(0, dc), W + min(0, dc))

            nbr_dist = np.full((H, W), np.inf, dtype=np.float32)
            nbr_dist[r_slice, c_slice] = dist[nbr_r_slice, nbr_c_slice]

            better = flat_cells & (nbr_dist < min_dist)
            flat_flowdir[better] = code
            min_dist[better] = nbr_dist[better]

        resolved = flat_cells & (flat_flowdir > 0)
        flowdir[resolved] = flat_flowdir[resolved]

    return flowdir, nodata_mask


def flow_accumulation_array(
    flowdir: np.ndarray,
    nodata_mask: Optional[np.ndarray] = None
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Calculate total upslope contributing area (cell count) via topological sorting.
    """
    H, W = flowdir.shape
    code_to_offset = {
        1: (0, 1), 2: (1, 1), 4: (1, 0), 8: (1, -1),
        16: (0, -1), 32: (-1, -1), 64: (-1, 0), 128: (-1, 1)
    }

    flat_targets = np.full(H * W, -1, dtype=np.int32)
    in_degrees = np.zeros(H * W, dtype=np.int32)

    for code, (dr, dc) in code_to_offset.items():
        mask = (flowdir == code)
        if not np.any(mask):
            continue
        rr, cc = np.where(mask)
        tr = rr + dr
        tc = cc + dc
        valid = (tr >= 0) & (tr < H) & (tc >= 0) & (tc < W)

        src_flat = rr[valid] * W + cc[valid]
        dst_flat = tr[valid] * W + tc[valid]

        flat_targets[src_flat] = dst_flat
        np.add.at(in_degrees, dst_flat, 1)

    accum = np.ones(H * W, dtype=np.float32)
    if nodata_mask is not None:
        accum[nodata_mask.ravel()] = 0
        in_degrees[nodata_mask.ravel()] = -1

    # Kahn's topological sort
    ridge_cells = np.where((in_degrees == 0) & (accum > 0))[0]
    queue = deque(ridge_cells.tolist())

    while queue:
        curr = queue.popleft()
        target = flat_targets[curr]
        if target >= 0:
            accum[target] += accum[curr]
            in_degrees[target] -= 1
            if in_degrees[target] == 0:
                queue.append(target)

    return accum.reshape((H, W)), flat_targets
