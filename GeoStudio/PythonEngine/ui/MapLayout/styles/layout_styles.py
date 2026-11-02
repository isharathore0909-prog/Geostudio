# -*- coding: utf-8 -*-
"""
GeoStudio - MapLayout Styles & Design Tokens
UI stylesheet customizations, colors, fonts, and appearance presets for layout windows.
"""

from core.style import OFFWHITE_STYLESHEET, DARK_STYLESHEET

LAYOUT_OFFWHITE_STYLE = OFFWHITE_STYLESHEET

LAYOUT_DOCK_TITLE_STYLE = (
    "color: #0f172a; padding: 5px; background: #f8fafc; "
    "border: 1px solid #e2e8f0; border-radius: 4px; font-weight: bold;"
)

LAYOUT_TAB_PANE_STYLE = "QTabWidget::pane { border: 1px solid #cbd5e1; background: white; }"

LAYOUT_STATUS_TOOL_STYLE = "color: #0f172a; font-weight: 600; padding: 2px 10px;"
LAYOUT_STATUS_POS_STYLE = "color: #475569; padding: 2px 8px;"

LAYOUT_EXPORT_BTN_STYLE = (
    "background: #0284c7; color: white; font-weight: bold; padding: 7px 16px; border-radius: 4px;"
)

__all__ = [
    "LAYOUT_OFFWHITE_STYLE",
    "LAYOUT_DOCK_TITLE_STYLE",
    "LAYOUT_TAB_PANE_STYLE",
    "LAYOUT_STATUS_TOOL_STYLE",
    "LAYOUT_STATUS_POS_STYLE",
    "LAYOUT_EXPORT_BTN_STYLE",
]
