# -*- coding: utf-8 -*-
"""
GeoStudio - Hydrology: Sink Filling
Barnes Priority-Flood depression filling algorithm for DEMs.
"""

import heapq
from typing import Callable, Optional
import numpy as np


def fill_sinks_array(
    dem: np.ndarray,
    nodata_val: Optional[float] = None,
    progress_cb: Optional[Callable[[float, str], None]] = None,
    is_canceled: Optional[Callable[[], bool]] = None
) -> np.ndarray:
    """
    Fill depressions and sinks in DEM using exact Priority-Flood algorithm.
    Fills sinks to their exact lowest spill point elevation.
    """
    H, W = dem.shape
    filled = np.copy(dem).astype(np.float64)
    visited = np.zeros((H, W), dtype=bool)

    if nodata_val is not None and not np.isnan(nodata_val):
        nodata_mask = (dem == nodata_val) | np.isnan(dem)
    else:
        nodata_mask = np.isnan(dem)

    visited[nodata_mask] = True

    heap = []
    # Seed boundary cells
    for c in range(W):
        if not visited[0, c]:
            visited[0, c] = True
            heap.append((float(filled[0, c]), 0, c))
        if not visited[H - 1, c]:
            visited[H - 1, c] = True
            heap.append((float(filled[H - 1, c]), H - 1, c))

    for r in range(1, H - 1):
        if not visited[r, 0]:
            visited[r, 0] = True
            heap.append((float(filled[r, 0]), r, 0))
        if not visited[r, W - 1]:
            visited[r, W - 1] = True
            heap.append((float(filled[r, W - 1]), r, W - 1))

    heapq.heapify(heap)

    nbrs = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]
    total_valid = int(np.count_nonzero(~nodata_mask))
    processed = len(heap)
    last_pct = 0

    while heap:
        if is_canceled and is_canceled():
            return dem

        z, r, c = heapq.heappop(heap)
        processed += 1

        if progress_cb and total_valid > 0 and (processed % 100000 == 0):
            pct = min(95.0, (processed / total_valid) * 100.0)
            if pct - last_pct >= 5.0:
                last_pct = pct
                progress_cb(pct, f"Depression filling: {pct:.0f}%")

        for dr, dc in nbrs:
            nr, nc = r + dr, c + dc
            if 0 <= nr < H and 0 <= nc < W and not visited[nr, nc]:
                visited[nr, nc] = True
                if filled[nr, nc] < z:
                    filled[nr, nc] = z
                heapq.heappush(heap, (float(filled[nr, nc]), nr, nc))

    res = filled.astype(np.float32)
    if nodata_val is not None:
        res[nodata_mask] = nodata_val
    return res
