# -*- coding: utf-8 -*-
"""
GeoStudio - Road & Transportation LiDAR Data Models
Typed structures for road stationing, geometry, hazards, and processing context.
"""

from dataclasses import dataclass, field, asdict
from typing import Callable, Optional, List, Dict, Any
import numpy as np


import time


class ProcessingContext:
    """Manages progress reporting, UI event loop pumping, and logging callbacks during execution."""

    def __init__(
        self,
        progress_callback: Optional[Callable[[float, str], None]] = None,
        log_callback: Optional[Callable[[str], None]] = None
    ):
        self._progress = progress_callback
        self._log = log_callback
        self._last_event_time = 0.0

    def progress(self, pct: float, msg: str):
        if self._progress:
            self._progress(pct, msg)
        self.process_events()

    def log(self, msg: str):
        if self._log:
            self._log(msg)
        self.process_events()

    def process_events(self, force: bool = False):
        """Pumps the Qt application event loop so the UI remains fluid and responsive."""
        now = time.time()
        if force or (now - self._last_event_time > 0.08):
            self._last_event_time = now
            try:
                from PyQt5.QtWidgets import QApplication
                app = QApplication.instance()
                if app:
                    app.processEvents()
            except Exception:
                pass


@dataclass
class StationMarker:
    """3D equidistant station chainage marker along road alignment."""
    station: str
    chainage_m: float
    x: float
    y: float
    z: float
    grade_pct: float
    width_m: float


@dataclass
class CorridorGeometryResult:
    """Extracted 3D geometric alignment layers and metrics."""
    centerline_points: np.ndarray
    curb_left_points: np.ndarray
    curb_right_points: np.ndarray
    station_markers: List[StationMarker]
    total_length_m: float
    average_width_m: float
    max_grade_pct: float


@dataclass
class CorridorHazard:
    """Flagged road corridor hazard (steep grade, low vehicle clearance, pothole depression)."""
    hazard_type: str
    severity: str
    chainage_m: float
    x: float
    y: float
    z: float
    metric_val: float
    description: str
