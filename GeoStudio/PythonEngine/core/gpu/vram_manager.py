# -*- coding: utf-8 -*-
"""
GeoStudio - VRAM & Adaptive Tile Budget Manager
Calculates dynamic tile dimensions based on available VRAM and safety margins to prevent OOM errors.
"""

import math
from typing import Tuple
from .cuda_detector import CudaDetector


class VramManager:
    """Manages GPU VRAM allocation budgets and computes optimal tile sizes."""

    DEFAULT_SAFETY_MARGIN = 0.25  # Keep 25% of free VRAM as safety buffer
    MIN_TILE_SIZE = 512           # Minimum block dimension (px)
    MAX_TILE_SIZE = 8192          # Maximum block dimension (px)
    DEFAULT_CPU_TILE_SIZE = 2048  # Default tile size when using CPU

    @classmethod
    def calculate_tile_size(
        cls,
        raster_width: int,
        raster_height: int,
        bytes_per_pixel: int = 4,   # float32 = 4 bytes
        num_input_bands: int = 1,
        num_output_bands: int = 1,
        intermediate_buffers: int = 2,
        use_gpu: bool = True,
        safety_margin: float = DEFAULT_SAFETY_MARGIN
    ) -> Tuple[int, int]:
        """
        Calculate optimal tile width and height that safely fit in available VRAM/RAM.
        
        Formula:
        MemoryPerPixel = (num_input_bands + num_output_bands + intermediate_buffers) * bytes_per_pixel
        TargetMemoryBudget = FreeVRAM * (1 - safety_margin)
        MaxPixelsPerTile = TargetMemoryBudget / MemoryPerPixel
        TileDimension = sqrt(MaxPixelsPerTile), clamped to [MIN_TILE_SIZE, MAX_TILE_SIZE]
        """
        if not use_gpu:
            # CPU fallback bounded tile size
            tile_dim = min(cls.DEFAULT_CPU_TILE_SIZE, max(raster_width, raster_height))
            tile_w = min(tile_dim, raster_width)
            tile_h = min(tile_dim, raster_height)
            return (tile_w, tile_h)

        free_vram = CudaDetector.get_live_free_vram_bytes()
        
        # If no VRAM information is available, use sensible conservative default (2048x2048)
        if free_vram <= 0:
            return (cls.DEFAULT_CPU_TILE_SIZE, cls.DEFAULT_CPU_TILE_SIZE)

        # Apply safety margin
        safe_budget = int(free_vram * (1.0 - max(0.1, min(0.5, safety_margin))))
        
        # Calculate memory footprint per pixel
        total_buffers = num_input_bands + num_output_bands + intermediate_buffers
        bytes_per_pixel_total = total_buffers * bytes_per_pixel

        if bytes_per_pixel_total <= 0:
            bytes_per_pixel_total = 4 * 4  # Default 16 bytes/pixel

        max_pixels = safe_budget // bytes_per_pixel_total
        if max_pixels <= 0:
            return (cls.MIN_TILE_SIZE, cls.MIN_TILE_SIZE)

        optimal_dim = int(math.sqrt(max_pixels))

        # Clamp to power of 2 or multiple of 256 for optimal CUDA warp/block execution
        optimal_dim = max(cls.MIN_TILE_SIZE, min(cls.MAX_TILE_SIZE, optimal_dim))
        optimal_dim = (optimal_dim // 256) * 256
        if optimal_dim < cls.MIN_TILE_SIZE:
            optimal_dim = cls.MIN_TILE_SIZE

        tile_w = min(optimal_dim, raster_width)
        tile_h = min(optimal_dim, raster_height)

        return (tile_w, tile_h)

    @classmethod
    def get_memory_diagnostics(cls) -> str:
        """Returns a formatted diagnostic string of current memory state."""
        info = CudaDetector.get_gpu_info()
        if info["cuda_available"]:
            return (
                f"GPU: {info['device_name']} | "
                f"Total VRAM: {info['total_vram_mb']:.0f} MB | "
                f"Free VRAM: {info['free_vram_mb']:.0f} MB"
            )
        return "Processing Engine: Multi-threaded CPU (NumPy/OpenMP)"
