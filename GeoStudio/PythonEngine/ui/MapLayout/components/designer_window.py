# -*- coding: utf-8 -*-
"""
GeoStudio - MapLayout Designer Workstation Window
Professional cartographic design window providing:
- Full interactive QgsLayoutView canvas with pan, zoom, selection, and drag-to-draw tools
- Complete GIS layout designer workflow:
    * Top Menus: Layout, Edit, View, Items, Add Item, Atlas, Settings, Help
    * Top Toolbars: Project/Layout, Navigation, Alignment, Distribution
    * Left Vertical Toolbar: 14 creation and manipulation tools (Select, Move Item, Add Map,
      Add Label, Add Legend, Add Scale Bar, Add North Arrow, Add Image, Add Table,
      Add Shape, Add Line, Add Rectangle, Add Ellipse, Add Arrow)
    * Center Page Canvas with status bar (x, y coordinates in mm, page, zoom %)
    * Upper Right Dock: [Items] [Undo History]
    * Lower Right Dock: [Layout] [Item Properties] [Guides]
- Export connected seamlessly to PrintExportDialog and LayoutExportDialog (PDF, PNG, JPG, TIFF, SVG)
- System Printing & Print Preview
- Canvas-to-Layout and Layout-to-Canvas Extent Synchronization
"""

import os
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QAction,
    QToolBar, QMessageBox, QFileDialog, QApplication, QDockWidget,
    QTabWidget, QUndoView, QLabel, QStatusBar, QHeaderView, QAbstractItemView
)
from PyQt5.QtCore import Qt, QSize, QPointF
from PyQt5.QtGui import QIcon, QFont, QColor, QPolygonF, QPainter
from PyQt5.QtPrintSupport import QPrinter, QPrintPreviewDialog

from qgis.core import (
    QgsProject, QgsPrintLayout, QgsLayoutItem, QgsLayoutItemPage, QgsLayoutItemMap, QgsLayoutItemLabel,
    QgsLayoutItemLegend, QgsLayoutItemScaleBar, QgsLayoutItemPicture,
    QgsLayoutItemShape, QgsLayoutItemPolyline, QgsLayoutItemPolygon,
    QgsLayoutItemHtml, QgsLayoutItemAttributeTable, QgsLayoutSize,
    QgsLayoutPoint, QgsUnitTypes, QgsLayoutMeasurement, QgsLayoutGuide,
    QgsLayoutItemRegistry, QgsApplication
)
from qgis.gui import (
    QgsLayoutView, QgsLayoutViewToolPan, QgsLayoutViewToolZoom,
    QgsLayoutViewToolSelect, QgsLayoutViewToolMoveItemContent,
    QgsLayoutViewToolAddItem, QgsLayoutViewToolAddNodeItem
)

from resources.icons.icon_provider import get_icon
from core.style import OFFWHITE_STYLESHEET
from ..config.presets import PAGE_PRESETS
from ..core.actions import align_items, distribute_items
from .settings_tab import LayoutSettingsTab
from .guides_tab import GuidesTab
from .items_dock import LayoutItemsDock
from .properties_dock import LayoutPropertiesDock
from .export_dialog import LayoutExportDialog
from .print_export_dialog import PrintExportDialog


class GeoStudioLayoutDesignerWindow(QMainWindow):
    """
    Dedicated Professional Layout Designer workstation for GeoStudio.
    """

    def __init__(self, layout=None, main_window=None, parent=None):
        if layout is not None and not hasattr(layout, "initializeDefaults") and main_window is None:
            main_window = layout
            layout = None

        super().__init__(parent or main_window)
        if layout is None:
            from qgis.core import QgsProject, QgsPrintLayout
            prj = QgsProject.instance()
            layout = QgsPrintLayout(prj)
            layout.initializeDefaults()
            layout.setName("Map Layout 1")
            try:
                prj.layoutManager().addLayout(layout)
            except Exception:
                pass
        self.layout = layout
        self.mw = main_window

        self._pending_tool_type = None
        self._keep_warm = False

        layout_name = layout.name() if layout else "Layout Designer"
        self.setWindowTitle(f"GeoStudio Layout Designer — {layout_name}")
        self.setMinimumSize(1200, 800)
        self.resize(1500, 920)
        self.setStyleSheet(OFFWHITE_STYLESHEET)

        # Modal window flags to ensure proper z-index and focus above main map
        self.setWindowModality(Qt.ApplicationModal)

        self._build_ui()
        self._build_menus()
        self._build_toolbars()
        self._build_status_bar()
        self._connect_signals()

        self.zoom_to_page()

    def _build_ui(self):
        # 1. Central Canvas View
        self.view = QgsLayoutView(self)
        if self.layout:
            self.view.setCurrentLayout(self.layout)
        try:
            self.view.setRenderHint(QPainter.Antialiasing, True)
            self.view.setRenderHint(QPainter.SmoothPixmapTransform, True)
            self.view.setRenderHint(QPainter.TextAntialiasing, True)
        except Exception:
            pass
        self.setCentralWidget(self.view)

        # Interactive Tools
        self.tool_select = QgsLayoutViewToolSelect(self.view)
        if self.layout and hasattr(self.tool_select, "setLayout"):
            try:
                self.tool_select.setLayout(self.layout)
            except Exception as e:
                print(f"[Warning] Failed to set layout on tool_select: {e}")

        # Keep tool_select synchronized whenever layout changes to ensure mouse handles are valid
        try:
            self.view.layoutSet.connect(self._on_layout_set)
        except Exception:
            pass

        self.tool_pan = QgsLayoutViewToolPan(self.view)
        self.tool_zoom = QgsLayoutViewToolZoom(self.view)
        self.tool_move_content = QgsLayoutViewToolMoveItemContent(self.view)
        self.tool_add_item = QgsLayoutViewToolAddItem(self.view)
        self.tool_add_node = QgsLayoutViewToolAddNodeItem(self.view)

        # Connect tool callbacks
        self.tool_add_item.createdItem.connect(self._on_item_created_interactive)
        self.tool_add_node.createdItem.connect(self._on_item_created_interactive)

        # Default tool is select
        self.view.setTool(self.tool_select)

        # Track mouse moves for mm coordinates in status bar
        self.view.cursorPosChanged.connect(self._on_view_mouse_moved)

        # 2. Upper Right Dock: [Items] [Undo History]
        self.upper_dock = QDockWidget("Items & History", self)
        self.upper_dock.setObjectName("layout_upper_dock")
        self.upper_dock.setMinimumWidth(280)
        self.upper_dock.setMaximumWidth(450)

        self.tab_upper = QTabWidget(self.upper_dock)
        self.tab_upper.setStyleSheet("QTabWidget::pane { border: 1px solid #cbd5e1; background: white; }")

        # Items panel widget
        self.items_dock_widget = LayoutItemsDock(self, self)
        self.items_dock = self.items_dock_widget
        self.tab_upper.addTab(self.items_dock_widget.widget(), "Items")

        # Undo History View
        if self.layout and hasattr(self.layout, "undoStack") and self.layout.undoStack():
            stk = self.layout.undoStack().stack() if hasattr(self.layout.undoStack(), "stack") else self.layout.undoStack()
            self.undo_view = QUndoView(stk)
            self.undo_view.setEmptyLabel("No actions")
            self.undo_view.setStyleSheet("background: white; border: none; font-size: 11px;")
            self.tab_upper.addTab(self.undo_view, "Undo History")

        self.upper_dock.setWidget(self.tab_upper)
        self.addDockWidget(Qt.RightDockWidgetArea, self.upper_dock)

        # 3. Lower Right Dock: [Layout] [Item Properties] [Guides]
        self.lower_dock = QDockWidget("Properties & Settings", self)
        self.lower_dock.setObjectName("layout_lower_dock")
        self.lower_dock.setMinimumWidth(280)
        self.lower_dock.setMaximumWidth(450)

        self.tab_lower = QTabWidget(self.lower_dock)
        self.tab_lower.setStyleSheet("QTabWidget::pane { border: 1px solid #cbd5e1; background: white; }")

        # Layout Settings Tab
        self.tab_layout_settings = LayoutSettingsTab(self)
        self.tab_lower.addTab(self.tab_layout_settings, "Layout")

        # Properties Inspector Widget
        self.props_dock_widget = LayoutPropertiesDock(self, self)
        self.props_dock = self.props_dock_widget
        self.tab_lower.addTab(self.props_dock_widget.widget(), "Item Properties")

        # Guides Tab
        self.tab_guides = GuidesTab(self)
        self.tab_lower.addTab(self.tab_guides, "Guides")

        self.lower_dock.setWidget(self.tab_lower)
        self.addDockWidget(Qt.RightDockWidgetArea, self.lower_dock)

        # Allocate optimal vertical proportion for right dock panels:
        # upper dock (Items list) gets ~180px, lower dock (Properties & Settings) gets ~550px
        try:
            self.resizeDocks([self.upper_dock, self.lower_dock], [180, 550], Qt.Vertical)
        except Exception:
            pass

        # Default tabs selection
        self.tab_upper.setCurrentIndex(0)
        self.tab_lower.setCurrentIndex(1)  # Default to Item Properties

        # Initial items population
        self.items_dock.refresh_items()
        self.tab_layout_settings.refresh_maps()

    def _build_status_bar(self):
        sb = self.statusBar()
        self.lbl_status_tool = QLabel("Tool: Select")
        self.lbl_status_tool.setStyleSheet("color: #0f172a; font-weight: 600; padding: 2px 10px;")
        sb.addWidget(self.lbl_status_tool)

        self.lbl_status_pos = QLabel("x: 0.0 mm  y: 0.0 mm")
        self.lbl_status_pos.setStyleSheet("color: #475569; padding: 2px 8px;")
        sb.addPermanentWidget(self.lbl_status_pos)

        self.lbl_status_page = QLabel("page: 1")
        self.lbl_status_page.setStyleSheet("color: #475569; padding: 2px 8px;")
        sb.addPermanentWidget(self.lbl_status_page)

        self.lbl_status_zoom = QLabel("100.0%")
        self.lbl_status_zoom.setStyleSheet("color: #475569; padding: 2px 8px;")
        sb.addPermanentWidget(self.lbl_status_zoom)

    def _on_view_mouse_moved(self, point_snapped):
        if point_snapped:
            x_val = round(point_snapped.x(), 1)
            y_val = round(point_snapped.y(), 1)
            self.lbl_status_pos.setText(f"x: {x_val} mm  y: {y_val} mm")

    def _on_layout_set(self, layout):
        """Keep tool_select synchronized whenever the view's layout changes."""
        if hasattr(self, "tool_select") and self.tool_select and layout:
            try:
                self.tool_select.setLayout(layout)
            except Exception:
                pass
        if layout:
            try:
                layout.itemAdded.connect(self._on_layout_item_added)
            except Exception:
                pass

    def showEvent(self, event):
        super().showEvent(event)
        try:
            self.resizeDocks([self.upper_dock, self.lower_dock], [180, 550], Qt.Vertical)
        except Exception:
            pass

    def closeEvent(self, event):
        """Safely deactivate interactive tools and terminate cleanly when window is closed."""
        try:
            if hasattr(self, "tool_select") and self.tool_select:
                self.tool_select.deactivate()
        except Exception:
            pass

        event.accept()
        try:
            app = QApplication.instance()
            if app:
                app.quit()
        except Exception:
            pass

    def load_layer(self, file_path: str):
        """Loads or updates layer into layout project dynamically and brings window to front instantly."""
        if not file_path or not os.path.exists(file_path):
            self.setWindowState(self.windowState() & ~Qt.WindowMinimized | Qt.WindowActive)
            self.show()
            self.raise_()
            self.activateWindow()
            return

        try:
            from qgis.core import QgsProject, QgsRasterLayer, QgsVectorLayer
            prj = self.layout.project() if (self.layout and hasattr(self.layout, "project") and self.layout.project()) else QgsProject.instance()

            existing_layer = None
            for lyr in prj.mapLayers().values():
                if lyr.source() == file_path:
                    existing_layer = lyr
                    break

            if not existing_layer:
                base_name = os.path.splitext(os.path.basename(file_path))[0]
                ext = os.path.splitext(file_path)[1].lower()
                new_lyr = None
                if ext in (".tif", ".tiff", ".img", ".asc", ".vrt"):
                    new_lyr = QgsRasterLayer(file_path, base_name)
                elif ext in (".shp", ".geojson", ".gpkg", ".kml"):
                    new_lyr = QgsVectorLayer(file_path, base_name, "ogr")

                if new_lyr and new_lyr.isValid():
                    prj.addMapLayer(new_lyr)
                    if new_lyr.crs().isValid():
                        prj.setCrs(new_lyr.crs())

            # Update existing map items in layout if present
            if self.layout:
                for item in self.layout.items():
                    if isinstance(item, QgsLayoutItemMap):
                        self._configure_map_item_settings(item)
                        item.refresh()
                self.items_dock.refresh_items()
                self.tab_layout_settings.refresh_maps()

        except Exception as e:
            print(f"[MapLayout] Error synchronizing layer '{file_path}': {e}")

        self.setWindowState(self.windowState() & ~Qt.WindowMinimized | Qt.WindowActive)
        self.show()
        self.raise_()
        self.activateWindow()

    def _connect_signals(self):
        self.items_dock.item_selected.connect(self._on_item_selected)
        if self.layout:
            self.layout.selectedItemChanged.connect(self._on_item_selected)
            try:
                self.layout.itemAdded.connect(self._on_layout_item_added)
            except Exception:
                pass

    def _on_item_selected(self, item):
        self.props_dock.set_item(item)
        if item:
            self.tab_lower.setCurrentIndex(1)  # switch to Item Properties tab

    # ── Interactive Tool Activation ──────────────────────────────
    def _activate_add_item_tool(self, metadata_id: int, tool_type: str):
        self._pending_tool_type = tool_type
        self.tool_add_item.setItemMetadataId(metadata_id)
        self.view.setTool(self.tool_add_item)
        name_map = {
            "map": "Add Map (drag rectangle on page)",
            "label": "Add Label (drag rectangle on page)",
            "legend": "Add Legend (drag rectangle on page)",
            "scalebar": "Add Scale Bar (drag rectangle on page)",
            "north_arrow": "Add North Arrow (drag rectangle on page)",
            "image": "Add Image (drag rectangle on page)",
            "table": "Add Table (drag rectangle on page)",
            "shape": "Add Shape (drag rectangle on page)",
            "rectangle": "Add Rectangle (drag rectangle on page)",
            "ellipse": "Add Ellipse (drag rectangle on page)"
        }
        self.lbl_status_tool.setText(f"Tool: {name_map.get(tool_type, 'Add Item')}")

    def _activate_add_node_tool(self, metadata_id: int, tool_type: str):
        self._pending_tool_type = tool_type
        self.tool_add_node.setItemMetadataId(metadata_id)
        self.view.setTool(self.tool_add_node)
        self.lbl_status_tool.setText(f"Tool: Add {tool_type.capitalize()} (click points, right-click to finish)")

    def _calculate_nice_segment_size(self, val: float) -> float:
        if val <= 0:
            return 50.0
        import math
        exponent = math.floor(math.log10(val))
        fraction = val / (10 ** exponent)
        if fraction < 1.5:
            nice = 1.0
        elif fraction < 3.5:
            nice = 2.0
        elif fraction < 7.5:
            nice = 5.0
        else:
            nice = 10.0
        return round(float(nice * (10 ** exponent)), 2)

    def _configure_scalebar_item(self, item: QgsLayoutItemScaleBar):
        """Ensures scale bar is linked to map, has realistic metric units, and renders clearly."""
        if not item or not isinstance(item, QgsLayoutItemScaleBar):
            return

        if not item.id():
            item.setId("Scale Bar")

        main_map = self.get_main_map_item()
        if main_map:
            item.setLinkedMap(main_map)

        item.setStyle("Single Box")
        item.setNumberOfSegmentsLeft(0)

        # Let PyQGIS try default calculation first if map has valid extent
        if main_map and hasattr(main_map, "extent") and not main_map.extent().isEmpty():
            if hasattr(item, "guessUnits"):
                try:
                    item.guessUnits()
                except Exception:
                    pass
            try:
                item.applyDefaultSize()
            except Exception:
                pass

        # Robust calculation if unitsPerSegment is still 0 or invalid
        if item.unitsPerSegment() <= 0:
            item.setUnits(QgsUnitTypes.DistanceMeters)
            item.setUnitLabel("m")
            if main_map and hasattr(main_map, "extent") and not main_map.extent().isEmpty():
                ground_w = main_map.extent().width()
                seg = self._calculate_nice_segment_size(ground_w / 4.0)
                item.setUnitsPerSegment(seg)
            else:
                item.setUnitsPerSegment(50.0)

        if item.numberOfSegments() < 2:
            item.setNumberOfSegments(2)

        # Style & geometry: ensure scalebar is at least 45mm x 14mm so it is never squished/clipped
        item.setBackgroundEnabled(True)
        item.setBackgroundColor(QColor(255, 255, 255, 220))
        item.resizeToMinimumWidth()

        rect = item.rect()
        if rect.width() < 40 or rect.height() < 12:
            item.attemptResize(QgsLayoutSize(max(rect.width(), 48.0), max(rect.height(), 14.0), QgsUnitTypes.LayoutMillimeters))

        item.update()
        if hasattr(self, "view") and self.view:
            self.view.update()

    def _link_unlinked_items_to_map(self, map_item: QgsLayoutItemMap):
        """Automatically links existing scalebars, north arrows, and legends to the map."""
        if not self.layout or not map_item:
            return
        for it in self.layout.items():
            if isinstance(it, QgsLayoutItemScaleBar):
                if not it.linkedMap() or it.unitsPerSegment() <= 0:
                    self._configure_scalebar_item(it)
            elif isinstance(it, QgsLayoutItemPicture):
                if hasattr(it, "linkedMap") and not it.linkedMap():
                    it.setLinkedMap(map_item)
            elif isinstance(it, QgsLayoutItemLegend):
                if hasattr(it, "linkedMap") and not it.linkedMap():
                    it.setLinkedMap(map_item)

    def _on_layout_item_added(self, item):
        """Called automatically by PyQGIS layout.itemAdded signal whenever an item is added."""
        try:
            if not item or not isinstance(item, QgsLayoutItem):
                return
            if getattr(item, "_gs_configured", False):
                return
            item._gs_configured = True

            if isinstance(item, QgsLayoutItemScaleBar):
                self._configure_scalebar_item(item)
            elif isinstance(item, QgsLayoutItemMap):
                self._configure_map_item_settings(item)
        except Exception as e:
            print(f"[MapLayout] Error configuring added item: {e}")

    def _on_item_created_interactive(self, item=None, *args):
        """Called automatically by PyQGIS QgsLayoutViewToolAddItem when rectangle is drawn."""
        if not self.layout:
            return

        if item is None:
            selected = self.layout.selectedLayoutItems()
            if selected:
                item = selected[0]
            else:
                layout_items = [i for i in self.layout.items() if isinstance(i, QgsLayoutItem) and not isinstance(i, QgsLayoutItemPage)]
                if layout_items:
                    item = layout_items[0]

        if not item or not isinstance(item, QgsLayoutItem):
            return

        tt = self._pending_tool_type or ""

        if isinstance(item, QgsLayoutItemMap):
            map_count = len([i for i in self.layout.items() if isinstance(i, QgsLayoutItemMap)])
            item.setId(f"Map {map_count}")
            item.setFrameEnabled(True)
            item.setBackgroundColor(QColor("#ffffff"))
            self._configure_map_item_settings(item)

        elif isinstance(item, QgsLayoutItemScaleBar):
            self._configure_scalebar_item(item)

        elif isinstance(item, QgsLayoutItemLabel):
            label_count = len([i for i in self.layout.items() if isinstance(i, QgsLayoutItemLabel)])
            item.setId(f"Title {label_count}")
            item.setText("Map Title")
            f = item.font()
            f.setFamily("Segoe UI")
            f.setPointSize(16)
            f.setBold(True)
            item.setFont(f)

        elif isinstance(item, QgsLayoutItemLegend):
            item.setId("Legend")
            item.setTitle("Legend")
            item.setLinkedMap(self.get_main_map_item())
            item.setFrameEnabled(True)
            item.setBackgroundColor(QColor(255, 255, 255, 230))

        elif isinstance(item, QgsLayoutItemPicture):
            if tt == "north_arrow":
                item.setId("North Arrow")
                item.setLinkedMap(self.get_main_map_item())
                svg_path = self._find_north_arrow_svg()
                if svg_path:
                    item.setPicturePath(svg_path)
                item.setBackgroundEnabled(True)
                item.setBackgroundColor(QColor(255, 255, 255, 200))
            else:
                item.setId("Logo / Image")
                path, _ = QFileDialog.getOpenFileName(self, "Choose Image", "", "Images (*.png *.jpg *.jpeg *.svg *.webp)")
                if path:
                    item.setPicturePath(path)

        elif isinstance(item, QgsLayoutItemShape):
            shape_count = len([i for i in self.layout.items() if isinstance(i, QgsLayoutItemShape)])
            if tt == "ellipse":
                item.setId(f"Ellipse {shape_count}")
                item.setShapeType(QgsLayoutItemShape.Ellipse)
            else:
                item.setId(f"Rectangle {shape_count}")
                item.setShapeType(QgsLayoutItemShape.Rectangle)
            item.setFrameEnabled(True)

        elif isinstance(item, QgsLayoutItemPolyline):
            if tt == "arrow":
                item.setId("Arrow")
                item.setEndMarker(QgsLayoutItemPolyline.ArrowHead)
            else:
                item.setId("Line")

        elif isinstance(item, QgsLayoutItemAttributeTable):
            item.setId("Attribute Table")
            main_canvas = getattr(self.mw, "map_canvas", None)
            if main_canvas and main_canvas.canvas and main_canvas.canvas.layers():
                item.setVectorLayer(main_canvas.canvas.layers()[0])

        # Reset tool to select
        self.view.setTool(self.tool_select)
        self.lbl_status_tool.setText("Tool: Select")
        self._pending_tool_type = None

        self.layout.setSelectedItem(item)
        self.items_dock.refresh_items()
        self.tab_layout_settings.refresh_maps()
        self.props_dock.set_item(item)

    def _find_north_arrow_svg(self) -> str:
        """Find default QGIS north arrow SVG path."""
        for p in QgsApplication.svgPaths():
            candidate = os.path.join(p, "arrows", "NorthArrow_02.svg")
            if os.path.exists(candidate):
                return candidate
            candidate1 = os.path.join(p, "arrows", "NorthArrow_01.svg")
            if os.path.exists(candidate1):
                return candidate1
        return ""

    # ── Menus Construction ──────────────────────────────────────
    def _build_menus(self):
        mb = self.menuBar()
        mb.clear()

        # 1. Layout
        m_layout = mb.addMenu("&Layout")
        m_layout.addAction(get_icon("new_project"), "New Layout...", self.new_layout, "Ctrl+N")
        m_layout.addAction(get_icon("open_project"), "Open Layout...", self.open_layout, "Ctrl+O")
        m_layout.addAction(get_icon("save_project"), "Save Layout", self.save_layout, "Ctrl+S")
        m_layout.addAction("Save As...", self.duplicate_layout)
        m_layout.addSeparator()
        m_layout.addAction(get_icon("print_map"), "Print...", self.print_layout, "Ctrl+P")
        m_layout.addAction("Export Layout (GeoStudio)...", self.open_export_dialog, "Ctrl+E")
        m_layout.addAction("Export as PDF...", self.export_pdf, "Ctrl+Shift+P")
        m_layout.addAction("Export as Image...", self.export_image)
        m_layout.addAction("Export as SVG...", self.export_svg)
        m_layout.addSeparator()
        m_layout.addAction("Page Setup / Properties...", self.show_page_properties)
        m_layout.addAction("Close Designer", self.close, "Ctrl+W")

        # 2. Edit
        m_edit = mb.addMenu("&Edit")
        if self.layout and hasattr(self.layout, "undoStack") and self.layout.undoStack():
            stk = self.layout.undoStack().stack() if hasattr(self.layout.undoStack(), "stack") else self.layout.undoStack()
            if hasattr(stk, "createUndoAction"):
                m_edit.addAction(stk.createUndoAction(self, "Undo"))
                m_edit.addAction(stk.createRedoAction(self, "Redo"))
                m_edit.addSeparator()
        m_edit.addAction(get_icon("delete"), "Delete Selected", self.delete_selected, "Delete")
        m_edit.addAction("Select All", self.select_all, "Ctrl+A")
        m_edit.addAction("Clear Selection", self.deselect_all, "Ctrl+Shift+A")

        # 3. View
        m_view = mb.addMenu("&View")
        m_view.addAction(get_icon("zoom_in"), "Zoom In", self.view.zoomIn, "Ctrl++")
        m_view.addAction(get_icon("zoom_out"), "Zoom Out", self.view.zoomOut, "Ctrl+-")
        m_view.addAction(get_icon("zoom_full"), "Zoom to Page", self.zoom_to_page, "Ctrl+0")
        m_view.addAction("Zoom 1:1", self.zoom_1_1, "Ctrl+1")
        m_view.addSeparator()
        m_view.addAction("Toggle Grid", self.toggle_grid)
        m_view.addAction("Toggle Snapping", self.toggle_snapping)
        m_view.addSeparator()
        m_view.addAction(get_icon("refresh"), "Refresh Layout", self.refresh_layout, "F5")

        # 4. Items
        m_items = mb.addMenu("&Items")
        m_items.addAction("Raise (Bring Forward)", self.items_dock._raise_item)
        m_items.addAction("Lower (Send Backward)", self.items_dock._lower_item)
        m_items.addAction("Lock / Unlock Selected", self.items_dock._toggle_selected_lock)
        m_items.addSeparator()
        m_items.addAction("Align Left", lambda: align_items(self.layout, "left"))
        m_items.addAction("Align Center", lambda: align_items(self.layout, "center"))
        m_items.addAction("Align Right", lambda: align_items(self.layout, "right"))
        m_items.addAction("Align Top", lambda: align_items(self.layout, "top"))
        m_items.addAction("Align Middle", lambda: align_items(self.layout, "middle"))
        m_items.addAction("Align Bottom", lambda: align_items(self.layout, "bottom"))
        m_items.addSeparator()
        m_items.addAction("Distribute Horizontally", lambda: distribute_items(self.layout, "h"))
        m_items.addAction("Distribute Vertically", lambda: distribute_items(self.layout, "v"))

        # 5. Add Item
        m_add = mb.addMenu("&Add Item")
        m_add.addAction(get_icon("new_project"), "Add Map", self.add_map_item)
        m_add.addAction(get_icon("edit"), "Add Label / Title", self.add_label_item)
        m_add.addAction(get_icon("layer_properties"), "Add Legend", self.add_legend_item)
        m_add.addAction(get_icon("measure_dist"), "Add Scale Bar", self.add_scalebar_item)
        m_add.addAction(get_icon("pan"), "Add North Arrow", self.add_north_arrow_item)
        m_add.addAction(get_icon("save_project"), "Add Image / Logo", self.add_image_item)
        m_add.addAction("Add Table", self.add_table_item)
        m_add.addAction("Add Shape (Rectangle)", self.add_shape_item)
        m_add.addAction("Add Ellipse", self.add_ellipse_item)
        m_add.addAction("Add Line", self.add_line_item)
        m_add.addAction("Add Arrow", self.add_arrow_item)

        # 6. Atlas
        m_atlas = mb.addMenu("&Atlas")
        m_atlas.addAction("Generate Map Series / Atlas...", self.open_atlas_dialog)

        # 7. Settings
        m_settings = mb.addMenu("&Settings")
        m_settings.addAction("Page Setup...", self.show_page_properties)

        # 8. Help
        m_help = mb.addMenu("&Help")
        m_help.addAction("Layout Guide & Documentation", self.show_help)

    # ── Toolbars Construction ──────────────────────────────────
    def _build_toolbars(self):
        # ── Top Row 1: Project / Layout / Export Toolbar ─────────
        tb_layout = QToolBar("Layout Operations", self)
        tb_layout.setIconSize(QSize(18, 18))
        self.addToolBar(Qt.TopToolBarArea, tb_layout)

        tb_layout.addAction(get_icon("new_project"), "New Layout", self.new_layout)
        tb_layout.addAction(get_icon("open_project"), "Open Layout", self.open_layout)
        tb_layout.addAction(get_icon("save_project"), "Save", self.save_layout)
        tb_layout.addAction("Save As", self.duplicate_layout)
        tb_layout.addSeparator()
        tb_layout.addAction(get_icon("print_map"), "Print", self.print_layout)
        tb_layout.addAction("Export Layout", self.open_export_dialog)
        tb_layout.addAction("Export PDF", self.export_pdf)
        tb_layout.addAction("Export Image", self.export_image)
        tb_layout.addAction("Export SVG", self.export_svg)
        tb_layout.addSeparator()

        if self.layout and hasattr(self.layout, "undoStack") and self.layout.undoStack():
            stk = self.layout.undoStack().stack() if hasattr(self.layout.undoStack(), "stack") else self.layout.undoStack()
            if hasattr(stk, "undo"):
                tb_layout.addAction("Undo", stk.undo)
                tb_layout.addAction("Redo", stk.redo)
                tb_layout.addSeparator()

        # ── Top Row 2: Navigation & Alignment Toolbar ────────────
        self.addToolBarBreak(Qt.TopToolBarArea)
        tb_nav_align = QToolBar("Navigation & Alignment", self)
        tb_nav_align.setIconSize(QSize(18, 18))
        self.addToolBar(Qt.TopToolBarArea, tb_nav_align)

        tb_nav_align.addAction(get_icon("zoom_full"), "Zoom to Page", self.zoom_to_page)
        tb_nav_align.addAction("1:1", self.zoom_1_1)
        tb_nav_align.addAction(get_icon("zoom_in"), "Zoom In", self.view.zoomIn)
        tb_nav_align.addAction(get_icon("zoom_out"), "Zoom Out", self.view.zoomOut)
        tb_nav_align.addAction(get_icon("refresh"), "Refresh", self.refresh_layout)
        tb_nav_align.addSeparator()

        tb_nav_align.addAction(get_icon("pan"), "Pan View", self.set_tool_pan)
        tb_nav_align.addAction(get_icon("select_single"), "Select Item", self.set_tool_select)
        tb_nav_align.addAction("Move Item Content", self.set_tool_move_content)
        tb_nav_align.addSeparator()

        tb_nav_align.addAction("Align Left", lambda: align_items(self.layout, "left"))
        tb_nav_align.addAction("Align Center", lambda: align_items(self.layout, "center"))
        tb_nav_align.addAction("Align Right", lambda: align_items(self.layout, "right"))
        tb_nav_align.addAction("Align Top", lambda: align_items(self.layout, "top"))
        tb_nav_align.addAction("Align Middle", lambda: align_items(self.layout, "middle"))
        tb_nav_align.addAction("Align Bottom", lambda: align_items(self.layout, "bottom"))
        tb_nav_align.addSeparator()

        tb_nav_align.addAction("Distribute H", lambda: distribute_items(self.layout, "h"))
        tb_nav_align.addAction("Distribute V", lambda: distribute_items(self.layout, "v"))
        tb_nav_align.addSeparator()

        tb_nav_align.addAction("Lock", self.items_dock._toggle_selected_lock)
        tb_nav_align.addAction("Sync From Canvas", self.sync_extent_from_canvas)
        tb_nav_align.addAction("Apply Extent to Canvas", self.sync_canvas_from_map)

        # ── Left Vertical Toolbar: Layout Creation Tools (14 Tools) ──
        tb_left = QToolBar("Layout Tools", self)
        tb_left.setOrientation(Qt.Vertical)
        tb_left.setIconSize(QSize(20, 20))
        self.addToolBar(Qt.LeftToolBarArea, tb_left)

        tb_left.addAction(get_icon("select_single"), "Select Item", self.set_tool_select)
        tb_left.addAction(get_icon("pan"), "Move Item Content", self.set_tool_move_content)
        tb_left.addSeparator()

        tb_left.addAction(get_icon("new_project"), "Add Map", lambda: self._activate_add_item_tool(QgsLayoutItemRegistry.LayoutMap, "map"))
        tb_left.addAction(get_icon("edit"), "Add Label", lambda: self._activate_add_item_tool(QgsLayoutItemRegistry.LayoutLabel, "label"))
        tb_left.addAction(get_icon("layer_properties"), "Add Legend", lambda: self._activate_add_item_tool(QgsLayoutItemRegistry.LayoutLegend, "legend"))
        tb_left.addAction(get_icon("measure_dist"), "Add Scale Bar", lambda: self._activate_add_item_tool(QgsLayoutItemRegistry.LayoutScaleBar, "scalebar"))
        tb_left.addAction(get_icon("pan"), "Add North Arrow", lambda: self._activate_add_item_tool(QgsLayoutItemRegistry.LayoutPicture, "north_arrow"))
        tb_left.addAction(get_icon("save_project"), "Add Image", lambda: self._activate_add_item_tool(QgsLayoutItemRegistry.LayoutPicture, "image"))
        tb_left.addAction("Add Table", lambda: self._activate_add_item_tool(QgsLayoutItemRegistry.LayoutAttributeTable, "table"))
        tb_left.addSeparator()

        tb_left.addAction("Add Shape", lambda: self._activate_add_item_tool(QgsLayoutItemRegistry.LayoutShape, "shape"))
        tb_left.addAction("Add Line", lambda: self._activate_add_node_tool(QgsLayoutItemRegistry.LayoutPolyline, "line"))
        tb_left.addAction("Add Rectangle", lambda: self._activate_add_item_tool(QgsLayoutItemRegistry.LayoutShape, "rectangle"))
        tb_left.addAction("Add Ellipse", lambda: self._activate_add_item_tool(QgsLayoutItemRegistry.LayoutShape, "ellipse"))
        tb_left.addAction("Add Arrow", lambda: self._activate_add_node_tool(QgsLayoutItemRegistry.LayoutPolyline, "arrow"))

    # ── Tool Mode Switchers ─────────────────────────────────────
    def set_tool_select(self):
        self.view.setTool(self.tool_select)
        self.lbl_status_tool.setText("Tool: Select")

    def set_tool_pan(self):
        self.view.setTool(self.tool_pan)
        self.lbl_status_tool.setText("Tool: Pan View")

    def set_tool_move_content(self):
        self.view.setTool(self.tool_move_content)
        self.lbl_status_tool.setText("Tool: Move Item Content (Pan inside map frame)")

    # ── Direct Placement Methods (fallback / program placement) ─
    def _configure_map_item_settings(self, item: QgsLayoutItemMap):
        """Configures CRS, layers, smooth raster resampling, and geographic extent so the map renders crisply immediately."""
        try:
            from qgis.core import QgsRectangle, QgsCoordinateReferenceSystem, QgsCoordinateTransform
        except (ImportError, AttributeError):
            return
        prj = self.layout.project() if (self.layout and hasattr(self.layout, "project") and self.layout.project()) else QgsProject.instance()
        main_canvas = getattr(self.mw, "map_canvas", None)

        # Antialiasing and high-fidelity rendering on layout context
        if self.layout and hasattr(self.layout, "renderContext"):
            try:
                from qgis.core import QgsLayoutRenderContext
                rc = self.layout.renderContext()
                rc.setFlag(QgsLayoutRenderContext.FlagAntialiasing, True)
                rc.setFlag(QgsLayoutRenderContext.FlagUseAdvancedEffects, True)
                rc.setFlag(QgsLayoutRenderContext.FlagLosslessImageRendering, True)
            except Exception:
                pass

        # Native QGIS map item caching: must be NoCache so Qt never restricts rendering to item-coordinate pixmaps
        try:
            item.setCacheMode(QgsLayoutItemMap.NoCache)
        except Exception:
            pass

        # Ensure rasters use smooth Bilinear resampling for both zoom-in and zoom-out (eliminates jagged pixel noise)
        def _optimize_rasters(layer_list):
            try:
                from qgis.core import QgsRasterLayer, QgsRasterResampleFilter, QgsBilinearRasterResampler
                for lyr in layer_list:
                    if isinstance(lyr, QgsRasterLayer) and lyr.isValid():
                        pipe = lyr.pipe()
                        if pipe:
                            rf = pipe.resampleFilter()
                            if not rf:
                                rf = QgsRasterResampleFilter()
                                pipe.set(rf)
                            rf.setZoomedInResampler(QgsBilinearRasterResampler())
                            rf.setZoomedOutResampler(QgsBilinearRasterResampler())
                            rf.setMaxOversampling(2.0)
            except Exception:
                pass

        if main_canvas and getattr(main_canvas, "canvas", None) and not main_canvas.canvas.extent().isEmpty():
            canvas_layers = main_canvas.canvas.layers()
            _optimize_rasters(canvas_layers)
            item.setCrs(main_canvas.canvas.mapSettings().destinationCrs())
            item.setLayers(canvas_layers)
            item.setExtent(main_canvas.canvas.extent())
            self._link_unlinked_items_to_map(item)
            return

        valid_layers = [l for l in prj.mapLayers().values() if l.isValid()]
        _optimize_rasters(valid_layers)

        # Determine appropriate map CRS: if layer is geographic, use metric projection (EPSG:3857) to prevent aspect stretching
        crs = None
        if valid_layers and valid_layers[0].crs().isValid():
            layer_crs = valid_layers[0].crs()
            if layer_crs.isGeographic():
                crs = QgsCoordinateReferenceSystem("EPSG:3857")
            else:
                crs = layer_crs
            prj.setCrs(crs)
        elif prj.crs().isValid() and not prj.crs().isGeographic():
            crs = prj.crs()
        else:
            crs = QgsCoordinateReferenceSystem("EPSG:3857")
            prj.setCrs(crs)

        item.setCrs(crs)

        if valid_layers:
            item.setLayers(valid_layers)
            comb_ext = QgsRectangle()
            comb_ext.setNull()
            for lyr in valid_layers:
                lext = lyr.extent()
                if not lext.isNull() and not lext.isEmpty():
                    if lyr.crs().isValid() and lyr.crs() != crs:
                        try:
                            tr = QgsCoordinateTransform(lyr.crs(), crs, prj)
                            lext = tr.transformBoundingBox(lext)
                        except Exception:
                            pass
                    if comb_ext.isNull():
                        comb_ext = QgsRectangle(lext)
                    else:
                        comb_ext.combineExtentWith(lext)

            if not comb_ext.isNull() and not comb_ext.isEmpty():
                comb_ext.scale(1.05)
                item.zoomToExtent(comb_ext)
            else:
                default_ext = QgsRectangle(-180.0, -90.0, 180.0, 90.0) if crs.isGeographic() else QgsRectangle(-20037508.34, -20037508.34, 20037508.34, 20037508.34)
                item.zoomToExtent(default_ext)
        else:
            item.setLayers([])
            default_ext = QgsRectangle(-180.0, -90.0, 180.0, 90.0) if crs.isGeographic() else QgsRectangle(-20037508.34, -20037508.34, 20037508.34, 20037508.34)
            item.zoomToExtent(default_ext)

        self._link_unlinked_items_to_map(item)

    def add_map_item(self):
        page = self.layout.pageCollection().pages()[0]
        pw = page.pageSize().width()
        ph = page.pageSize().height()

        item = QgsLayoutItemMap(self.layout)
        item.setId(f"Map {len([i for i in self.layout.items() if isinstance(i, QgsLayoutItemMap)]) + 1}")
        item.attemptResize(QgsLayoutSize(pw * 0.7, ph * 0.7, QgsUnitTypes.LayoutMillimeters))
        item.attemptMove(QgsLayoutPoint(pw * 0.05, ph * 0.1, QgsUnitTypes.LayoutMillimeters))
        item.setFrameEnabled(True)
        item.setBackgroundColor(QColor("#ffffff"))

        self._configure_map_item_settings(item)

        self.layout.addLayoutItem(item)
        self.layout.setSelectedItem(item)
        self.items_dock.refresh_items()
        self.tab_layout_settings.refresh_maps()

    def add_3d_map_item(self):
        self.add_map_item()

    def add_label_item(self):
        item = QgsLayoutItemLabel(self.layout)
        item.setId(f"Title {len([i for i in self.layout.items() if isinstance(i, QgsLayoutItemLabel)]) + 1}")
        item.setText("Map Title")
        item.attemptResize(QgsLayoutSize(100, 15, QgsUnitTypes.LayoutMillimeters))
        item.attemptMove(QgsLayoutPoint(20, 10, QgsUnitTypes.LayoutMillimeters))
        self.layout.addLayoutItem(item)
        self.layout.setSelectedItem(item)
        self.items_dock.refresh_items()

    def add_legend_item(self):
        item = QgsLayoutItemLegend(self.layout)
        item.setId("Legend")
        item.setTitle("Legend")
        item.setLinkedMap(self.get_main_map_item())
        item.attemptResize(QgsLayoutSize(50, 70, QgsUnitTypes.LayoutMillimeters))
        item.attemptMove(QgsLayoutPoint(150, 30, QgsUnitTypes.LayoutMillimeters))
        item.setFrameEnabled(True)
        item.setBackgroundColor(QColor(255, 255, 255, 230))
        self.layout.addLayoutItem(item)
        self.layout.setSelectedItem(item)
        self.items_dock.refresh_items()

    def add_scalebar_item(self):
        item = QgsLayoutItemScaleBar(self.layout)
        item.setId("Scale Bar")

        page = self.layout.pageCollection().pages()[0] if self.layout else None
        ph = page.pageSize().height() if page else 210
        item.attemptResize(QgsLayoutSize(50, 14, QgsUnitTypes.LayoutMillimeters))
        item.attemptMove(QgsLayoutPoint(25, ph - 30, QgsUnitTypes.LayoutMillimeters))

        self.layout.addLayoutItem(item)
        self._configure_scalebar_item(item)
        self.layout.setSelectedItem(item)
        self.items_dock.refresh_items()

    def add_north_arrow_item(self):
        item = QgsLayoutItemPicture(self.layout)
        item.setId("North Arrow")
        item.setLinkedMap(self.get_main_map_item())
        svg = self._find_north_arrow_svg()
        if svg:
            item.setPicturePath(svg)
        item.attemptResize(QgsLayoutSize(15, 18, QgsUnitTypes.LayoutMillimeters))
        item.attemptMove(QgsLayoutPoint(180, 20, QgsUnitTypes.LayoutMillimeters))
        item.setBackgroundEnabled(True)
        item.setBackgroundColor(QColor(255, 255, 255, 200))
        self.layout.addLayoutItem(item)
        self.layout.setSelectedItem(item)
        self.items_dock.refresh_items()

    def add_image_item(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choose Logo or Image", "", "Images (*.png *.jpg *.jpeg *.svg *.webp)")
        if path:
            item = QgsLayoutItemPicture(self.layout)
            item.setId("Logo")
            item.setPicturePath(path)
            item.attemptResize(QgsLayoutSize(30, 30, QgsUnitTypes.LayoutMillimeters))
            item.attemptMove(QgsLayoutPoint(20, 20, QgsUnitTypes.LayoutMillimeters))
            self.layout.addLayoutItem(item)
            self.layout.setSelectedItem(item)
            self.items_dock.refresh_items()

    def add_shape_item(self):
        item = QgsLayoutItemShape(self.layout)
        item.setId(f"Rectangle {len([i for i in self.layout.items() if isinstance(i, QgsLayoutItemShape)]) + 1}")
        item.setShapeType(QgsLayoutItemShape.Rectangle)
        item.attemptResize(QgsLayoutSize(50, 30, QgsUnitTypes.LayoutMillimeters))
        item.attemptMove(QgsLayoutPoint(40, 40, QgsUnitTypes.LayoutMillimeters))
        item.setFrameEnabled(True)
        self.layout.addLayoutItem(item)
        self.layout.setSelectedItem(item)
        self.items_dock.refresh_items()

    def add_ellipse_item(self):
        item = QgsLayoutItemShape(self.layout)
        item.setId(f"Ellipse {len([i for i in self.layout.items() if isinstance(i, QgsLayoutItemShape)]) + 1}")
        item.setShapeType(QgsLayoutItemShape.Ellipse)
        item.attemptResize(QgsLayoutSize(40, 40, QgsUnitTypes.LayoutMillimeters))
        item.attemptMove(QgsLayoutPoint(50, 50, QgsUnitTypes.LayoutMillimeters))
        item.setFrameEnabled(True)
        self.layout.addLayoutItem(item)
        self.layout.setSelectedItem(item)
        self.items_dock.refresh_items()

    def add_line_item(self):
        poly = QPolygonF([QPointF(20, 20), QPointF(80, 20)])
        item = QgsLayoutItemPolyline(poly, self.layout)
        item.setId("Line")
        self.layout.addLayoutItem(item)
        self.layout.setSelectedItem(item)
        self.items_dock.refresh_items()

    def add_arrow_item(self):
        poly = QPolygonF([QPointF(20, 20), QPointF(80, 20)])
        item = QgsLayoutItemPolyline(poly, self.layout)
        item.setId("Arrow")
        item.setEndMarker(QgsLayoutItemPolyline.ArrowHead)
        self.layout.addLayoutItem(item)
        self.layout.setSelectedItem(item)
        self.items_dock.refresh_items()

    def add_polygon_item(self):
        poly = QPolygonF([QPointF(30, 30), QPointF(70, 30), QPointF(50, 60)])
        item = QgsLayoutItemPolygon(poly, self.layout)
        item.setId("Polygon")
        self.layout.addLayoutItem(item)
        self.layout.setSelectedItem(item)
        self.items_dock.refresh_items()

    def add_html_item(self):
        item = QgsLayoutItemHtml(self.layout)
        item.setId("HTML Block")
        item.setContentMode(QgsLayoutItemHtml.ManualHtml)
        item.setHtml("<h3>GeoStudio Report</h3><p>Analysis summary.</p>")
        item.attemptResize(QgsLayoutSize(80, 40, QgsUnitTypes.LayoutMillimeters))
        item.attemptMove(QgsLayoutPoint(30, 30, QgsUnitTypes.LayoutMillimeters))
        self.layout.addLayoutItem(item)
        self.layout.setSelectedItem(item)
        self.items_dock.refresh_items()

    def add_table_item(self):
        try:
            item = QgsLayoutItemAttributeTable(self.layout)
            item.setId("Attribute Table")
            main_canvas = getattr(self.mw, "map_canvas", None)
            if main_canvas and main_canvas.canvas and main_canvas.canvas.layers():
                item.setVectorLayer(main_canvas.canvas.layers()[0])
            item.attemptResize(QgsLayoutSize(100, 60, QgsUnitTypes.LayoutMillimeters))
            item.attemptMove(QgsLayoutPoint(30, 40, QgsUnitTypes.LayoutMillimeters))
            self.layout.addLayoutItem(item)
            self.layout.setSelectedItem(item)
            self.items_dock.refresh_items()
        except Exception:
            self.add_label_item()

    def get_main_map_item(self):
        for item in self.layout.items():
            if isinstance(item, QgsLayoutItemMap):
                return item
        return None

    # ── Map Extent Synchronization ──────────────────────────────
    def sync_extent_from_canvas(self):
        map_item = self.get_main_map_item()
        main_canvas = getattr(self.mw, "map_canvas", None)
        if map_item and main_canvas and main_canvas.canvas:
            map_item.setExtent(main_canvas.canvas.extent())
            map_item.setScale(main_canvas.canvas.scale())
            self.props_dock.set_item(map_item)
            QMessageBox.information(self, "Synchronized", "Layout map extent updated from map canvas.")

    def sync_canvas_from_map(self):
        map_item = self.get_main_map_item()
        main_canvas = getattr(self.mw, "map_canvas", None)
        if map_item and main_canvas and main_canvas.canvas:
            main_canvas.canvas.setExtent(map_item.extent())
            main_canvas.canvas.refresh()
            QMessageBox.information(self, "Synchronized", "Main map canvas extent updated from layout map.")

    # ── View Controls ───────────────────────────────────────────
    def zoom_to_page(self):
        if not self.layout:
            return
        pages = self.layout.pageCollection().pages()
        if pages:
            self.view.fitInView(pages[0].rect(), Qt.KeepAspectRatio)

    def zoom_1_1(self):
        self.view.resetTransform()

    def toggle_grid(self):
        self.tab_layout_settings.chk_show_grid.toggle()

    def toggle_snapping(self):
        self.tab_layout_settings.chk_snap_grid.toggle()

    def refresh_layout(self):
        self.layout.refresh()
        self.items_dock.refresh_items()
        self.tab_layout_settings.refresh_maps()

    def delete_selected(self):
        for it in self.layout.selectedLayoutItems():
            self.layout.removeLayoutItem(it)
        self.items_dock.refresh_items()

    def select_all(self):
        self.layout.selectAll()

    def deselect_all(self):
        self.layout.deselectAll()

    # ── File I/O & Export ───────────────────────────────────────
    def new_layout(self):
        from .manager_dialog import LayoutManagerDialog
        dlg = LayoutManagerDialog(self.mw, self)
        dlg.exec_()

    def open_layout(self):
        self.new_layout()

    def save_layout(self):
        if self.mw and hasattr(self.mw, "save_project"):
            self.mw.save_project()
        QMessageBox.information(self, "Layout Saved", f"Layout '{self.layout.name()}' saved in project.")

    def duplicate_layout(self):
        mgr = QgsProject.instance().layoutManager()
        new_name = f"{self.layout.name()} (Copy)"
        clone = mgr.duplicateLayout(self.layout, new_name)
        if clone:
            QMessageBox.information(self, "Duplicated", f"Layout duplicated as '{new_name}'.")

    def show_page_properties(self):
        pages = self.layout.pageCollection().pages()
        if pages:
            self.props_dock.set_item(pages[0])
            self.tab_lower.setCurrentIndex(1)

    def open_export_dialog(self):
        """Opens GeoStudio's PrintExportDialog connected to this layout."""
        try:
            dlg = PrintExportDialog(self.mw, self, layout=self.layout)
            dlg.exec_()
        except Exception:
            # Fallback to LayoutExportDialog
            self.export_pdf()

    def export_pdf(self):
        self.open_export_dialog()

    def export_image(self):
        self.open_export_dialog()

    def export_svg(self):
        self.open_export_dialog()

    def print_layout(self):
        printer = QPrinter(QPrinter.HighResolution)
        dlg = QPrintPreviewDialog(printer, self)
        dlg.paintRequested.connect(lambda p: self._render_print_preview(p, printer))
        dlg.exec_()

    def _render_print_preview(self, printer, qprinter):
        from qgis.core import QgsLayoutExporter
        exporter = QgsLayoutExporter(self.layout)
        exporter.renderPage(printer, 0)

    def open_atlas_dialog(self):
        QMessageBox.information(
            self, "Map Series / Atlas",
            f"Atlas series generator ready.\nConfigure coverage layers under Project Layers."
        )

    def show_help(self):
        QMessageBox.information(
            self, "GeoStudio Layout Designer Guide",
            "<b>GeoStudio Layout Designer</b><br><br>"
            "• Use the <b>Left Toolbar</b> to add map frames, labels, legends, scale bars, north arrows, images, and shapes.<br>"
            "• Use the <b>Items Tab</b> (top right) to reorder, lock, and toggle element visibility.<br>"
            "• Use the <b>Item Properties Tab</b> (bottom right) to customize fonts, scale, extent synchronization, and appearance.<br>"
            "• Export to high-resolution PDF, PNG, JPG, TIFF, or SVG via the <b>Layout</b> menu."
        )


__all__ = [
    "GeoStudioLayoutDesignerWindow",
    "LayoutSettingsTab",
    "GuidesTab",
    "PAGE_PRESETS",
]
