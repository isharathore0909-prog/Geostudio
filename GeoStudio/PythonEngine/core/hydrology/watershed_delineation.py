# -*- coding: utf-8 -*-
"""
GeoStudio - Hydrology: Watershed & Stream Network Delineation
Strahler stream network extraction and vectorized hydrological catchment delineation.
"""

from collections import deque
from typing import Optional, Dict
import numpy as np
import scipy.ndimage as ndi


def stream_network_array(
    accum: np.ndarray,
    flowdir: np.ndarray,
    threshold: int = 500,
    nodata_mask: Optional[np.ndarray] = None
) -> np.ndarray:
    """
    Extract stream channels and assign hierarchical Strahler stream orders.
    """
    H, W = flowdir.shape
    is_stream = (accum >= threshold) & (flowdir > 0)
    if nodata_mask is not None:
        is_stream &= (~nodata_mask)

    code_to_offset = {
        1: (0, 1), 2: (1, 1), 4: (1, 0), 8: (1, -1),
        16: (0, -1), 32: (-1, -1), 64: (-1, 0), 128: (-1, 1)
    }

    flat_targets = np.full(H * W, -1, dtype=np.int32)
    stream_in_degrees = np.zeros(H * W, dtype=np.int32)

    for code, (dr, dc) in code_to_offset.items():
        mask = (flowdir == code) & is_stream
        if not np.any(mask):
            continue
        rr, cc = np.where(mask)
        tr = rr + dr
        tc = cc + dc
        valid = (tr >= 0) & (tr < H) & (tc >= 0) & (tc < W)

        src_flat = rr[valid] * W + cc[valid]
        dst_flat = tr[valid] * W + tc[valid]
        valid_stream_dst = is_stream.ravel()[dst_flat]

        src_valid = src_flat[valid_stream_dst]
        dst_valid = dst_flat[valid_stream_dst]

        flat_targets[src_valid] = dst_valid
        np.add.at(stream_in_degrees, dst_valid, 1)

    strahler = np.zeros(H * W, dtype=np.int32)
    strahler[is_stream.ravel()] = 1

    stream_heads = np.where(is_stream.ravel() & (stream_in_degrees == 0))[0]
    queue = deque(stream_heads.tolist())
    trib_orders: Dict[int, list] = {}

    while queue:
        curr = queue.popleft()
        target = flat_targets[curr]
        if target >= 0 and is_stream.ravel()[target]:
            current_order = strahler[curr]
            if target not in trib_orders:
                trib_orders[target] = []
            trib_orders[target].append(current_order)

            stream_in_degrees[target] -= 1
            if stream_in_degrees[target] == 0:
                orders = trib_orders.pop(target, [1])
                if len(orders) >= 2:
                    max_o = max(orders)
                    if orders.count(max_o) >= 2:
                        strahler[target] = max_o + 1
                    else:
                        strahler[target] = max_o
                elif len(orders) == 1:
                    strahler[target] = orders[0]
                queue.append(target)

    strahler_grid = strahler.reshape((H, W))

    # Morphologically dilate stream channels so lines are thick and vivid
    if np.any(strahler_grid > 0):
        dilated = ndi.grey_dilation(strahler_grid, size=(3, 3))
        if nodata_mask is not None:
            dilated[nodata_mask] = 0
        return dilated
    return strahler_grid


def delineate_watersheds_array(
    flowdir: np.ndarray,
    accum: np.ndarray,
    flat_targets: np.ndarray,
    threshold: int = 500,
    nodata_mask: Optional[np.ndarray] = None
) -> np.ndarray:
    """
    Delineate complete hydrological catchment basins.
    Each drainage basin is identified by stream reaches / confluence pour points.
    """
    H, W = flowdir.shape
    flat_accum = accum.ravel()
    valid_cells = (flowdir.ravel() > 0)
    if nodata_mask is not None:
        valid_cells &= (~nodata_mask.ravel())

    is_stream = valid_cells & (flat_accum >= threshold) & (flat_targets >= 0)

    stream_in_degrees = np.zeros(H * W, dtype=np.int32)
    for src in np.where(is_stream)[0]:
        dst = flat_targets[src]
        if dst >= 0 and is_stream[dst]:
            stream_in_degrees[dst] += 1

    is_junction = is_stream & (stream_in_degrees >= 2)
    stream_heads = np.where(is_stream & (stream_in_degrees == 0))[0]
    junction_nodes = np.where(is_junction)[0]

    link_ids = np.zeros(H * W, dtype=np.int32)
    current_link_id = 1
    start_nodes = list(stream_heads) + list(junction_nodes)

    for start_node in start_nodes:
        curr = start_node
        if is_junction[curr]:
            curr = flat_targets[curr]
            if curr < 0 or not is_stream[curr] or link_ids[curr] > 0:
                continue
        link_id = current_link_id
        current_link_id += 1
        while curr >= 0 and is_stream[curr] and link_ids[curr] == 0:
            link_ids[curr] = link_id
            if is_junction[curr]:
                break
            curr = flat_targets[curr]

    # Assign remaining stream cells
    unassigned_streams = np.where(is_stream & (link_ids == 0))[0]
    for u in unassigned_streams:
        link_ids[u] = current_link_id
        current_link_id += 1

    # Label all terminal edge outlets (8-connected to group contiguous boundaries)
    terminal_outlets = valid_cells & (flat_targets == -1) & (link_ids == 0)
    labeled_terminals, num_term = ndi.label(terminal_outlets.reshape((H, W)), structure=np.ones((3, 3)))
    for t_idx in range(1, num_term + 1):
        link_ids[labeled_terminals.ravel() == t_idx] = current_link_id
        current_link_id += 1

    # Label any unassigned local sink outlets / pits
    unassigned_pits = valid_cells & (link_ids == 0) & (flat_targets == -1)
    if np.any(unassigned_pits):
        labeled_pits, num_pits = ndi.label(unassigned_pits.reshape((H, W)), structure=np.ones((3, 3)))
        for p_idx in range(1, num_pits + 1):
            link_ids[labeled_pits.ravel() == p_idx] = current_link_id
            current_link_id += 1

    # Vectorized Pointer Jumping (Path Doubling)
    N = H * W
    is_root = (link_ids > 0)
    targets = np.where(is_root, np.arange(N, dtype=np.int32), flat_targets)
    targets = np.where(targets < 0, np.arange(N, dtype=np.int32), targets)

    for _ in range(25):
        prev = targets
        targets = targets[targets]
        if np.array_equal(prev, targets):
            break

    basins = link_ids[targets]

    # Safety fallback for any missed tree roots
    zero_roots = (basins == 0) & valid_cells
    if np.any(zero_roots):
        labeled_zr, num_zr = ndi.label(zero_roots.reshape((H, W)), structure=np.ones((3, 3)))
        for z_idx in range(1, num_zr + 1):
            basins[labeled_zr.ravel() == z_idx] = current_link_id
            current_link_id += 1

    # Sieve / Absorb micro-slivers into dominant adjacent catchment
    min_basin_area = max(100, int(threshold * 0.1))
    unique_b, counts = np.unique(basins[valid_cells], return_counts=True)
    small_basins = unique_b[counts < min_basin_area]
    if len(small_basins) > 0 and len(small_basins) < len(unique_b):
        basins_2d = basins.reshape((H, W))
        is_small = np.isin(basins_2d, small_basins)
        filtered_basins = np.where(is_small, 0, basins_2d)
        indices = ndi.distance_transform_edt(filtered_basins == 0, return_distances=False, return_indices=True)
        filled_basins = filtered_basins[indices[0], indices[1]]
        basins = filled_basins.ravel()

    # Vectorized Compact Remapping to 1..K (NoData = 0)
    valid_b_mask = (basins > 0) & valid_cells
    unique_b, inv = np.unique(basins[valid_b_mask], return_inverse=True)
    compact_basins = np.zeros(N, dtype=np.int32)
    compact_basins[valid_b_mask] = (inv + 1).astype(np.int32)

    if nodata_mask is not None:
        compact_basins[nodata_mask.ravel()] = 0

    return compact_basins.reshape((H, W))
