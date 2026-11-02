# -*- coding: utf-8 -*-
"""
GeoStudio - MapLayout Panels Package
Exposes dockable inspector panels, settings tabs, and guide tables for the layout designer.
"""

from .items_dock import LayoutItemsDock
from .properties_dock import LayoutPropertiesDock
from .settings_tab import LayoutSettingsTab
from .guides_tab import GuidesTab

__all__ = [
    "LayoutItemsDock",
    "LayoutPropertiesDock",
    "LayoutSettingsTab",
    "GuidesTab",
]
