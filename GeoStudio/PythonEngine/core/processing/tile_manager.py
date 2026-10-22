# -*- coding: utf-8 -*-
"""
GeoStudio - Raster Tile & Window Streaming Manager
Handles block-by-block window generation, 1-pixel halo overlap handling for 3x3 kernels, and streaming GDAL I/O.
"""

import math
from typing import Generator, Tuple, Dict, Any, Optional
import numpy as np
from osgeo import gdal


class TileWindow:
    """Represents a spatial tile window with optional halo overlap."""
    def __init__(
        self,
        tile_index: int,
        total_tiles: int,
        x_off: int,
        y_off: int,
        x_size: int,
        y_size: int,
        halo: int = 0,
        raster_width: int = 0,
        raster_height: int = 0
    ):
        self.tile_index = tile_index
        self.total_tiles = total_tiles
        self.x_off = x_off
        self.y_off = y_off
        self.x_size = x_size
        self.y_size = y_size
        self.halo = halo

        # Calculate read window (including halo)
        if halo > 0:
            self.read_x_off = max(0, x_off - halo)
            self.read_y_off = max(0, y_off - halo)
            
            # Pad on right and bottom if needed
            read_x_max = min(raster_width, x_off + x_size + halo)
            read_y_max = min(raster_height, y_off + y_size + halo)
            
            self.read_x_size = read_x_max - self.read_x_off
            self.read_y_size = read_y_max - self.read_y_off

            # Slicing offsets to extract original data from halo tile
            self.slice_top = y_off - self.read_y_off
            self.slice_bottom = self.slice_top + y_size
            self.slice_left = x_off - self.read_x_off
            self.slice_right = self.slice_left + x_size
        else:
            self.read_x_off = x_off
            self.read_y_off = y_off
            self.read_x_size = x_size
            self.read_y_size = y_size
            self.slice_top = 0
            self.slice_bottom = y_size
            self.slice_left = 0
            self.slice_right = x_size


class TileManager:
    """Generates streaming tile windows and manages windowed raster processing."""

    @classmethod
    def generate_windows(
        cls,
        raster_width: int,
        raster_height: int,
        tile_width: int,
        tile_height: int,
        halo: int = 0
    ) -> Generator[TileWindow, None, None]:
        """
        Yields TileWindow objects covering the entire raster dimensions.
        """
        x_steps = int(math.ceil(raster_width / tile_width))
        y_steps = int(math.ceil(raster_height / tile_height))
        total_tiles = x_steps * y_steps

        tile_idx = 0
        for y_step in range(y_steps):
            y_off = y_step * tile_height
            y_size = min(tile_height, raster_height - y_off)

            for x_step in range(x_steps):
                x_off = x_step * tile_width
                x_size = min(tile_width, raster_width - x_off)

                yield TileWindow(
                    tile_index=tile_idx,
                    total_tiles=total_tiles,
                    x_off=x_off,
                    y_off=y_off,
                    x_size=x_size,
                    y_size=y_size,
                    halo=halo,
                    raster_width=raster_width,
                    raster_height=raster_height
                )
                tile_idx += 1

    @classmethod
    def read_tile(
        cls,
        dataset: gdal.Dataset,
        band_num: int,
        window: TileWindow
    ) -> np.ndarray:
        """Read tile window from GDAL dataset band, with edge padding if halo extends outside raster."""
        band = dataset.GetRasterBand(band_num)
        data = band.ReadAsArray(
            window.read_x_off,
            window.read_y_off,
            window.read_x_size,
            window.read_y_size
        )

        if data is None:
            return np.zeros((window.y_size, window.y_size), dtype=np.float32)

        # If halo was requested and tile is at global edge, pad with edge values (replicate border)
        if window.halo > 0:
            expected_h = window.y_size + 2 * window.halo
            expected_w = window.x_size + 2 * window.halo

            pad_top = window.halo - window.slice_top
            pad_bottom = expected_h - (pad_top + data.shape[0])
            pad_left = window.halo - window.slice_left
            pad_right = expected_w - (pad_left + data.shape[1])

            if pad_top > 0 or pad_bottom > 0 or pad_left > 0 or pad_right > 0:
                data = np.pad(
                    data,
                    ((max(0, pad_top), max(0, pad_bottom)), (max(0, pad_left), max(0, pad_right))),
                    mode="edge"
                )

        return data

    @classmethod
    def write_tile(
        cls,
        dataset: gdal.Dataset,
        band_num: int,
        window: TileWindow,
        data: np.ndarray
    ):
        """Write processed tile block to GDAL output dataset."""
        band = dataset.GetRasterBand(band_num)
        
        # Ensure output slice matches window x_size, y_size exactly
        if data.shape[0] != window.y_size or data.shape[1] != window.x_size:
            data = data[window.slice_top:window.slice_bottom, window.slice_left:window.slice_right]

        band.WriteArray(data, window.x_off, window.y_off)
