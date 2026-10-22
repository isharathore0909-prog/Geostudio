# -*- coding: utf-8 -*-
"""
GeoStudio - Processing Memory & Budget Manager
Configurable RAM/VRAM thresholds, process limits, and safety margins.
"""

import os
from typing import Dict, Any


class MemoryManager:
    """Manages configurable memory budgets for raster & vector processing."""

    # Defaults (can be configured via Processing Settings)
    DEFAULT_MAX_RAM_PERCENT = 0.70    # Max 70% of total physical RAM
    DEFAULT_MAX_VRAM_PERCENT = 0.75   # Max 75% of available VRAM
    DEFAULT_SAFETY_MARGIN_MB = 256    # Reserve at least 256MB for OS/App

    _config: Dict[str, Any] = {
        "max_ram_mb": 4096,           # 4GB RAM default cap per processing task
        "max_vram_mb": 4096,          # 4GB VRAM default cap
        "enable_gpu": True,
        "default_engine": "auto",     # "auto", "cuda", "cpu"
    }

    @classmethod
    def get_config(cls) -> Dict[str, Any]:
        return cls._config

    @classmethod
    def set_config(cls, key: str, value: Any):
        cls._config[key] = value

    @classmethod
    def get_max_tile_memory_bytes(cls, use_gpu: bool = True) -> int:
        """Returns the maximum allowed memory in bytes for a single tile buffer."""
        if use_gpu and cls._config.get("enable_gpu", True):
            from core.gpu.cuda_detector import CudaDetector
            free_vram = CudaDetector.get_live_free_vram_bytes()
            if free_vram > 0:
                return int(free_vram * cls.DEFAULT_MAX_VRAM_PERCENT)
        
        # CPU RAM Budget
        max_ram_mb = cls._config.get("max_ram_mb", 4096)
        return int(max_ram_mb * 1024 * 1024 * cls.DEFAULT_MAX_RAM_PERCENT)
