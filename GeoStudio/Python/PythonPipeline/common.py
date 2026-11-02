# -*- coding: utf-8 -*-
"""
GeoStudio Python Pipeline - Shared Utilities & Environment Bootstrap
Configures PROJ/GDAL paths, imports system paths, and standardizes IPC progress/result reporting.
"""

import os
import sys
import json

# Configure PROJ & GDAL data paths to ensure stable coordinate transforms
qgis_share_proj = r"C:\Program Files\QGIS 3.40.14\share\proj"
if os.path.exists(qgis_share_proj):
    os.environ["PROJ_LIB"] = qgis_share_proj
    os.environ["PROJ_DATA"] = qgis_share_proj

qgis_share_gdal = r"C:\Program Files\QGIS 3.40.14\share\gdal"
if os.path.exists(qgis_share_gdal):
    os.environ["GDAL_DATA"] = qgis_share_gdal

# Priority 1: Use the local PythonEngine in the current project
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
_search = CURRENT_DIR
PYTHON_ENGINE_DIR = None
for _ in range(6):
    _cand = os.path.join(_search, "PythonEngine")
    if os.path.isdir(_cand) and os.path.isfile(os.path.join(_cand, "main.py")):
        PYTHON_ENGINE_DIR = _cand
        break
    _search = os.path.dirname(_search)

if not PYTHON_ENGINE_DIR or not os.path.exists(PYTHON_ENGINE_DIR):
    PYTHON_ENGINE_DIR = r"D:\GEO MAP\GeoStudio\PythonEngine"

if os.path.exists(PYTHON_ENGINE_DIR) and PYTHON_ENGINE_DIR not in sys.path:
    sys.path.insert(0, PYTHON_ENGINE_DIR)

# QGIS plugins path for processing & vector/raster tools
qgis_plugins = r"C:\Program Files\QGIS 3.40.14\apps\qgis-ltr\python\plugins"
if os.path.exists(qgis_plugins) and qgis_plugins not in sys.path:
    sys.path.insert(1, qgis_plugins)

# Priority 2: Duplicacy fallback
APP_DIR = r"D:\DUPLICACY\GeoStudio\app"
if os.path.exists(APP_DIR) and APP_DIR not in sys.path:
    sys.path.insert(2, APP_DIR)


def report_progress(percent: int, message: str = ""):
    """Emits IPC progress indicator to host .NET process."""
    print(f"PROGRESS:{percent}:{message}", flush=True)


def report_result(success: bool, data: dict, error_msg: str = ""):
    """Emits serialized JSON result payload to host .NET process."""
    payload = {"status": "ok" if success else "error", "data": data, "error": error_msg}
    print("RESULT:" + json.dumps(payload), flush=True)
