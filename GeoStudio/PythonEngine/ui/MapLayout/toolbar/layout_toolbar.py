# -*- coding: utf-8 -*-
"""
GeoStudio - MapLayout Toolbar Components
Defines layout toolbars, navigation bars, alignment tools, and tool palette builders.
"""

from PyQt5.QtWidgets import QToolBar
from PyQt5.QtCore import Qt, QSize
from resources.icons.icon_provider import get_icon


def create_layout_operations_toolbar(parent, window) -> QToolBar:
    """Builds the main layout operations toolbar (New, Open, Save, Print, Export, Undo/Redo)."""
    tb = QToolBar("Layout Operations", parent)
    tb.setIconSize(QSize(18, 18))

    tb.addAction(get_icon("new_project"), "New Layout", window.new_layout)
    tb.addAction(get_icon("open_project"), "Open Layout", window.open_layout)
    tb.addAction(get_icon("save_project"), "Save", window.save_layout)
    tb.addAction("Save As", window.duplicate_layout)
    tb.addSeparator()
    tb.addAction(get_icon("print_map"), "Print", window.print_layout)
    tb.addAction("Export Layout", window.open_export_dialog)
    tb.addAction("Export PDF", window.export_pdf)
    tb.addAction("Export Image", window.export_image)
    tb.addAction("Export SVG", window.export_svg)
    tb.addSeparator()

    if window.layout and hasattr(window.layout, "undoStack") and window.layout.undoStack():
        stk = window.layout.undoStack().stack() if hasattr(window.layout.undoStack(), "stack") else window.layout.undoStack()
        if hasattr(stk, "undo"):
            tb.addAction("Undo", stk.undo)
            tb.addAction("Redo", stk.redo)
            tb.addSeparator()

    return tb


def create_navigation_alignment_toolbar(parent, window, align_func, distribute_func) -> QToolBar:
    """Builds navigation, zoom, and geometric alignment toolbar."""
    tb = QToolBar("Navigation & Alignment", parent)
    tb.setIconSize(QSize(18, 18))

    tb.addAction(get_icon("zoom_full"), "Zoom to Page", window.zoom_to_page)
    tb.addAction("1:1", window.zoom_1_1)
    tb.addAction(get_icon("zoom_in"), "Zoom In", window.view.zoomIn)
    tb.addAction(get_icon("zoom_out"), "Zoom Out", window.view.zoomOut)
    tb.addAction(get_icon("refresh"), "Refresh", window.refresh_layout)
    tb.addSeparator()

    tb.addAction(get_icon("pan"), "Pan View", window.set_tool_pan)
    tb.addAction(get_icon("select_single"), "Select Item", window.set_tool_select)
    tb.addAction("Move Item Content", window.set_tool_move_content)
    tb.addSeparator()

    tb.addAction("Align Left", lambda: align_func(window.layout, "left"))
    tb.addAction("Align Center", lambda: align_func(window.layout, "center"))
    tb.addAction("Align Right", lambda: align_func(window.layout, "right"))
    tb.addAction("Align Top", lambda: align_func(window.layout, "top"))
    tb.addAction("Align Middle", lambda: align_func(window.layout, "middle"))
    tb.addAction("Align Bottom", lambda: align_func(window.layout, "bottom"))
    tb.addSeparator()

    tb.addAction("Distribute H", lambda: distribute_func(window.layout, "h"))
    tb.addAction("Distribute V", lambda: distribute_func(window.layout, "v"))
    tb.addSeparator()

    tb.addAction("Lock", window.items_dock._toggle_selected_lock)
    tb.addAction("Sync From Canvas", window.sync_extent_from_canvas)
    tb.addAction("Apply Extent to Canvas", window.sync_canvas_from_map)

    return tb


def create_layout_tools_palette(parent, window, add_item_cb, add_node_cb) -> QToolBar:
    """Builds the 14-tool vertical layout tool palette on the left dock."""
    from qgis.core import QgsLayoutItemRegistry, QgsLayoutItemShape

    tb = QToolBar("Layout Tools", parent)
    tb.setOrientation(Qt.Vertical)
    tb.setIconSize(QSize(20, 20))

    tb.addAction(get_icon("select_single"), "Select Item", window.set_tool_select)
    tb.addAction(get_icon("pan"), "Move Item Content", window.set_tool_move_content)
    tb.addSeparator()

    tb.addAction(get_icon("new_project"), "Add Map", lambda: add_item_cb(QgsLayoutItemRegistry.LayoutMap, "map"))
    tb.addAction(get_icon("edit"), "Add Label", lambda: add_item_cb(QgsLayoutItemRegistry.LayoutLabel, "label"))
    tb.addAction(get_icon("layer_properties"), "Add Legend", lambda: add_item_cb(QgsLayoutItemRegistry.LayoutLegend, "legend"))
    tb.addAction(get_icon("measure_dist"), "Add Scale Bar", lambda: add_item_cb(QgsLayoutItemRegistry.LayoutScaleBar, "scalebar"))
    tb.addAction(get_icon("pan"), "Add North Arrow", lambda: add_item_cb(QgsLayoutItemRegistry.LayoutPicture, "north_arrow"))
    tb.addAction(get_icon("save_project"), "Add Image", lambda: add_item_cb(QgsLayoutItemRegistry.LayoutPicture, "image"))
    tb.addAction("Add Table", lambda: add_item_cb(QgsLayoutItemRegistry.LayoutAttributeTable, "table"))
    tb.addSeparator()

    tb.addAction("Add Shape", lambda: add_item_cb(QgsLayoutItemRegistry.LayoutShape, "shape"))
    tb.addAction("Add Line", lambda: add_node_cb(QgsLayoutItemRegistry.LayoutPolyline, "line"))
    tb.addAction("Add Rectangle", lambda: add_item_cb(QgsLayoutItemRegistry.LayoutShape, "rectangle"))
    tb.addAction("Add Ellipse", lambda: add_item_cb(QgsLayoutItemRegistry.LayoutShape, "ellipse"))
    tb.addAction("Add Arrow", lambda: add_node_cb(QgsLayoutItemRegistry.LayoutPolyline, "arrow"))

    return tb


__all__ = [
    "create_layout_operations_toolbar",
    "create_navigation_alignment_toolbar",
    "create_layout_tools_palette",
]
