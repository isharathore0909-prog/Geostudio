# -*- coding: utf-8 -*-
"""
GeoStudio - CUDA & Hardware Acceleration Detector
Detects NVIDIA CUDA GPUs, VRAM availability, driver versions, and compute frameworks (CuPy, PyTorch, Numba).
"""

import sys
import shutil
import subprocess
from typing import Dict, Any, Optional


class CudaDetector:
    """Detects and queries CUDA devices and system memory capabilities."""

    _cached_info: Optional[Dict[str, Any]] = None

    @classmethod
    def get_gpu_info(cls, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Query available CUDA devices, VRAM statistics, and active backends.
        Returns a structured dictionary with device capabilities.
        """
        if cls._cached_info is not None and not force_refresh:
            return cls._cached_info

        info: Dict[str, Any] = {
            "cuda_available": False,
            "device_count": 0,
            "device_name": "CPU Only",
            "compute_capability": None,
            "total_vram_bytes": 0,
            "free_vram_bytes": 0,
            "total_vram_mb": 0.0,
            "free_vram_mb": 0.0,
            "driver_version": "N/A",
            "backend": "numpy",  # "cupy", "torch", "numba", or "numpy"
            "description": "CPU multi-threaded execution",
        }

        # 1. Try PyTorch CUDA if available
        try:
            import torch
            if torch.cuda.is_available():
                dev_idx = 0
                props = torch.cuda.get_device_properties(dev_idx)
                free_bytes, total_bytes = torch.cuda.mem_get_info(dev_idx)
                
                info["cuda_available"] = True
                info["device_count"] = torch.cuda.device_count()
                info["device_name"] = props.name
                info["compute_capability"] = f"{props.major}.{props.minor}"
                info["total_vram_bytes"] = total_bytes
                info["free_vram_bytes"] = free_bytes
                info["total_vram_mb"] = round(total_bytes / (1024 * 1024), 1)
                info["free_vram_mb"] = round(free_bytes / (1024 * 1024), 1)
                info["backend"] = "torch"
                info["description"] = f"{props.name} ({info['free_vram_mb']} MB free)"
                cls._cached_info = info
                return info
        except Exception:
            pass

        # 2. Try CuPy if available
        try:
            import cupy as cp
            dev = cp.cuda.Device(0)
            free_bytes, total_bytes = dev.mem_info
            
            info["cuda_available"] = True
            info["device_count"] = cp.cuda.runtime.getDeviceCount()
            info["device_name"] = cp.cuda.runtime.getDeviceProperties(0).get("name", b"CUDA Device").decode("utf-8")
            info["total_vram_bytes"] = total_bytes
            info["free_vram_bytes"] = free_bytes
            info["total_vram_mb"] = round(total_bytes / (1024 * 1024), 1)
            info["free_vram_mb"] = round(free_bytes / (1024 * 1024), 1)
            info["backend"] = "cupy"
            info["description"] = f"{info['device_name']} ({info['free_vram_mb']} MB free)"
            cls._cached_info = info
            return info
        except Exception:
            pass

        # 3. Fallback: Query nvidia-smi if installed on Windows/Linux
        if shutil.which("nvidia-smi"):
            try:
                cmd = ["nvidia-smi", "--query-gpu=name,memory.total,memory.free,driver_version", "--format=csv,noheader,nounits"]
                out = subprocess.check_output(cmd, encoding="utf-8", timeout=2).strip().splitlines()
                if out:
                    parts = [p.strip() for p in out[0].split(",")]
                    if len(parts) >= 4:
                        name, total_mb, free_mb, driver = parts[0], float(parts[1]), float(parts[2]), parts[3]
                        info["cuda_available"] = True
                        info["device_count"] = len(out)
                        info["device_name"] = name
                        info["total_vram_mb"] = total_mb
                        info["free_vram_mb"] = free_mb
                        info["total_vram_bytes"] = int(total_mb * 1024 * 1024)
                        info["free_vram_bytes"] = int(free_mb * 1024 * 1024)
                        info["driver_version"] = driver
                        info["backend"] = "nvidia-smi"
                        info["description"] = f"{name} ({free_mb:.0f} MB free)"
            except Exception:
                pass

        cls._cached_info = info
        return info

    @classmethod
    def is_cuda_available(cls) -> bool:
        """Returns True if a compatible CUDA GPU is available."""
        return cls.get_gpu_info().get("cuda_available", False)

    @classmethod
    def get_device_name(cls) -> str:
        """Returns the primary GPU device name."""
        return cls.get_gpu_info().get("device_name", "CPU Only")

    @classmethod
    def get_device_count(cls) -> int:
        """Returns the number of detected GPU devices."""
        return cls.get_gpu_info().get("device_count", 0)

    @classmethod
    def get_total_vram_mb(cls) -> float:
        """Returns total VRAM in megabytes."""
        return cls.get_gpu_info().get("total_vram_mb", 0.0)

    @classmethod
    def get_free_vram_mb(cls) -> float:
        """Returns free VRAM in megabytes."""
        return cls.get_gpu_info().get("free_vram_mb", 0.0)

    @classmethod
    def get_live_free_vram_bytes(cls) -> int:
        """Query currently available free VRAM bytes dynamically."""
        try:
            import torch
            if torch.cuda.is_available():
                free_bytes, _ = torch.cuda.mem_get_info(0)
                return free_bytes
        except Exception:
            pass

        try:
            import cupy as cp
            free_bytes, _ = cp.cuda.Device(0).mem_info
            return free_bytes
        except Exception:
            pass

        info = cls.get_gpu_info()
        return info.get("free_vram_bytes", 0)


class HardwareInfo:
    """Dataclass holding structured hardware info."""
    def __init__(self, is_cuda_available: bool, device_name: str, vram_total_gb: float, vram_free_gb: float):
        self.is_cuda_available = is_cuda_available
        self.device_name = device_name
        self.vram_total_gb = vram_total_gb
        self.vram_free_gb = vram_free_gb


def get_cuda_hardware_info() -> HardwareInfo:
    """Helper function to get hardware acceleration status."""
    info = CudaDetector.get_gpu_info()
    return HardwareInfo(
        is_cuda_available=info.get("cuda_available", False),
        device_name=info.get("device_name", "CPU Only"),
        vram_total_gb=info.get("total_vram_mb", 0.0) / 1024.0,
        vram_free_gb=info.get("free_vram_mb", 0.0) / 1024.0
    )
