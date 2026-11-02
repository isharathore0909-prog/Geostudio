# -*- coding: utf-8 -*-
"""
GeoStudio - App Package Shim & Namespace Bridge
================================================
Provides standard 'app.*' namespace mapping to PythonEngine's modules,
ensuring full backward compatibility for all modules, dialogs, and tests.
"""
import sys
import os

_engine_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _engine_root not in sys.path:
    sys.path.insert(0, _engine_root)

import ui
import core
import modules
import resources

# Expose subpackages under app
sys.modules.setdefault("app", sys.modules[__name__])
sys.modules.setdefault("app.ui", ui)
sys.modules.setdefault("app.core", core)
sys.modules.setdefault("app.modules", modules)
sys.modules.setdefault("app.resources", resources)

try:
    import tools
    sys.modules.setdefault("app.tools", tools)
except ImportError:
    pass

# Direct MapLayout aliases
from ui import MapLayout
sys.modules.setdefault("app.MapLayout", MapLayout)
sys.modules.setdefault("app.ui.MapLayout", MapLayout)

