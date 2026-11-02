# -*- coding: utf-8 -*-
"""
GeoStudio - MapLayout Dedicated Module
======================================
The complete self-contained Map Layout module providing professional GIS cartographic
composition, high-resolution multi-format printing and export, template management,
measurement, alignment, coordinate overlays, toolbar management, and utilities.

Consolidated Structure:
- components: Workstation window, docks, tabs, dialogs
- panels: Dock panels (LayoutItemsDock, LayoutPropertiesDock, LayoutSettingsTab, GuidesTab)
- dialogs: Modal dialogs (LayoutManagerDialog, LayoutExportDialog, PrintExportDialog)
- toolbar: Toolbars and palette builders (operations, navigation, alignment, 14-tool palette)
- services: Business logic (template_service, export_service, overlay_service, action_service)
- utils: Measurement, pixel calculation, unit conversions, and memory protection
- types: Type hints, data classes, and enumerations (ExportFormat, ToolType, AlignmentType, etc.)
- constants: Paper presets, dimension matrices, and DPI options
- styles: Layout-specific offwhite stylesheets and UI component styles
- templates: Cartographic template definitions and preset resource packages
- tests: Comprehensive unit test suite
"""

# ── 1. UI Components & Window ──────────────────────────────────────
from .components.designer_window import GeoStudioLayoutDesignerWindow
from .components.properties_dock import LayoutPropertiesDock
from .components.items_dock import LayoutItemsDock
from .components.settings_tab import LayoutSettingsTab
from .components.guides_tab import GuidesTab
from .components.manager_dialog import LayoutManagerDialog
from .components.export_dialog import LayoutExportDialog
from .components.print_export_dialog import PrintExportDialog

# ── 2. Services & Core Logic ───────────────────────────────────────
from .services.template_service import create_layout_from_template
from .services.export_service import (
    export_layout_to_image,
    export_layout_to_pdf,
    export_layout_to_svg,
)
from .services.overlay_service import (
    draw_title_overlay,
    draw_north_arrow_overlay,
    draw_scalebar_overlay,
)
from .services.action_service import (
    align_items,
    distribute_items,
    get_first_map_item,
)

# ── 3. Toolbars & Palettes ─────────────────────────────────────────
from .toolbar.layout_toolbar import (
    create_layout_operations_toolbar,
    create_navigation_alignment_toolbar,
    create_layout_tools_palette,
)

# ── 4. Constants & Presets ─────────────────────────────────────────
from .constants.presets import (
    PAGE_PRESETS,
    PAGE_SIZES,
    DPI_PRESETS,
)

# ── 5. Styles ──────────────────────────────────────────────────────
from .styles.layout_styles import (
    LAYOUT_OFFWHITE_STYLE,
    LAYOUT_DOCK_TITLE_STYLE,
    LAYOUT_TAB_PANE_STYLE,
    LAYOUT_STATUS_TOOL_STYLE,
    LAYOUT_STATUS_POS_STYLE,
    LAYOUT_EXPORT_BTN_STYLE,
)

# ── 6. Utilities ───────────────────────────────────────────────────
from .utils.layout_utils import (
    mm_to_inches,
    inches_to_mm,
    mm_to_pixels,
    pixels_to_mm,
    calculate_page_dimensions,
    estimate_image_memory_mb,
    is_memory_critical,
    get_layout_item_by_id,
)

# ── 7. Types & Enums ───────────────────────────────────────────────
from .types.layout_types import (
    ExportFormat,
    AlignmentType,
    DistributionAxis,
    PageOrientation,
    ToolType,
    PageDimensionTuple,
)

__all__ = [
    # UI Windows & Components
    "GeoStudioLayoutDesignerWindow",
    "LayoutPropertiesDock",
    "LayoutItemsDock",
    "LayoutSettingsTab",
    "GuidesTab",
    "LayoutManagerDialog",
    "LayoutExportDialog",
    "PrintExportDialog",
    # Services & Core Logic
    "create_layout_from_template",
    "export_layout_to_image",
    "export_layout_to_pdf",
    "export_layout_to_svg",
    "draw_title_overlay",
    "draw_north_arrow_overlay",
    "draw_scalebar_overlay",
    "align_items",
    "distribute_items",
    "get_first_map_item",
    # Toolbar Builders
    "create_layout_operations_toolbar",
    "create_navigation_alignment_toolbar",
    "create_layout_tools_palette",
    # Constants & Presets
    "PAGE_PRESETS",
    "PAGE_SIZES",
    "DPI_PRESETS",
    # Styles
    "LAYOUT_OFFWHITE_STYLE",
    "LAYOUT_DOCK_TITLE_STYLE",
    "LAYOUT_TAB_PANE_STYLE",
    "LAYOUT_STATUS_TOOL_STYLE",
    "LAYOUT_STATUS_POS_STYLE",
    "LAYOUT_EXPORT_BTN_STYLE",
    # Utilities
    "mm_to_inches",
    "inches_to_mm",
    "mm_to_pixels",
    "pixels_to_mm",
    "calculate_page_dimensions",
    "estimate_image_memory_mb",
    "is_memory_critical",
    "get_layout_item_by_id",
    # Types
    "ExportFormat",
    "AlignmentType",
    "DistributionAxis",
    "PageOrientation",
    "ToolType",
    "PageDimensionTuple",
]
