# -*- coding: utf-8 -*-
"""
GeoStudio - Map Canvas Widget (core of the application).
Maintains synchronization with QgsProject via QgsLayerTreeMapCanvasBridge.
Provides real-time coordinates and elevation sampling.
Features an off-white background (#f8f9fa) and on-canvas elevation legend like Global Mapper.
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor

from core.elevation_styler import ElevationStyler
from ui.canvas.elevation_legend_widget import ElevationLegendWidget
from ui.canvas.map_canvas_navigation import CanvasNavigationManager
from ui.canvas.map_canvas_layers import CanvasLayerCoordinator


class MapCanvasWidget(QWidget):
    """
    Wraps the QGIS QgsMapCanvas inside a QWidget.
    Maintains synchronization with QgsProject via QgsLayerTreeMapCanvasBridge.
    Provides real-time coordinates and elevation sampling.
    """

    coordinate_changed = pyqtSignal(float, float)
    elevation_changed = pyqtSignal(object)  # float or None

    def __init__(self, parent=None):
        super().__init__(parent)
        self.canvas = None
        self.bridge = None
        self.elevation_legend = None
        self.nav_mgr = None
        self._pan_tool = None
        self._zoom_in_tool = None
        self._zoom_out_tool = None
        self._in_layers_added = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        try:
            from qgis.gui import QgsMapCanvas, QgsLayerTreeMapCanvasBridge
            from qgis.core import QgsProject, QgsCoordinateReferenceSystem, QgsMapSettings, QgsSettings
            from PyQt5.QtWidgets import QApplication

            # Global QGIS rendering thread pool and caching configuration
            try:
                qsettings = QgsSettings()
                qsettings.setValue("qgis/parallel_rendering", True)
                qsettings.setValue("qgis/preview_jobs", False)
                qsettings.setValue("qgis/map_update_interval", 50)
                qsettings.setValue("qgis/enable_render_caching", True)
                qsettings.setValue("qgis/max_threads", 8)
            except Exception:
                pass

            self.canvas = QgsMapCanvas(self)
            self.canvas.setCanvasColor(QColor("#ffffff"))
            self.canvas.enableAntiAliasing(False)  # High-speed point sprite rendering
            self.canvas.setWheelFactor(1.15)

            # Hardware-accelerated GPU viewport (OpenGL) for ultra-fast vector/raster compositing
            try:
                from PyQt5.QtWidgets import QOpenGLWidget
                from PyQt5.QtGui import QSurfaceFormat
                gl_fmt = QSurfaceFormat()
                gl_fmt.setRenderableType(QSurfaceFormat.OpenGL)
                gl_fmt.setSwapBehavior(QSurfaceFormat.DoubleBuffer)
                gl_fmt.setSamples(2)
                gl_vp = QOpenGLWidget()
                gl_vp.setFormat(gl_fmt)
                self.canvas.setViewport(gl_vp)
                self._gpu_accelerated = True
            except Exception:
                self._gpu_accelerated = False

            # High-resolution, flicker-free & crisp rendering configuration
            try:
                screen = QApplication.primaryScreen()
                if screen:
                    dpi = screen.logicalDotsPerInch()
                    self.canvas.mapSettings().setOutputDpi(dpi)
                self.canvas.mapSettings().setFlag(QgsMapSettings.Antialiasing, False)
                self.canvas.setParallelRenderingEnabled(True)
                self.canvas.setCachingEnabled(True)
                self.canvas.setPreviewJobsEnabled(False)
                self.canvas.setMapUpdateInterval(50)  # Responsive 50ms progressive refresh
            except Exception:
                pass


            self.canvas.xyCoordinates.connect(self._on_coord_changed)

            proj = QgsProject.instance()
            if not proj.crs().isValid() or not proj.crs().authid():
                default_crs = QgsCoordinateReferenceSystem("EPSG:4326")
                proj.setCrs(default_crs)
                self.canvas.setDestinationCrs(default_crs)
            else:
                self.canvas.setDestinationCrs(proj.crs())

            self.bridge = QgsLayerTreeMapCanvasBridge(proj.layerTreeRoot(), self.canvas)
            layout.addWidget(self.canvas)
            self._setup_tools()

            self.elevation_legend = ElevationLegendWidget(self.canvas)
            self.elevation_legend.move(14, 14)

            self.nav_mgr = CanvasNavigationManager(self.canvas)
            self.canvas.extentsChanged.connect(self.nav_mgr.on_extents_changed)

            proj.layersAdded.connect(self._on_layers_added)
            proj.layersRemoved.connect(self._on_layers_changed)
            proj.crsChanged.connect(self._on_project_crs_changed)


        except ImportError as e:
            lbl = QLabel(f"⚠ QGIS canvas not available: {e}\nRun via GeoStudio.bat to load QGIS engine.")
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("color: #dc2626; font-size: 14px; background: #f8fafc;")
            layout.addWidget(lbl)

        self.setLayout(layout)

    def set_canvas_background(self, color_str: str = "#f8f9fa"):
        if self.canvas:
            self.canvas.setCanvasColor(QColor(color_str))
            self.canvas.refresh()

    def update_elevation_legend(self, layer=None, mode: str = None):
        if not self.elevation_legend:
            return
        if layer:
            self.elevation_legend.update_from_layer(layer, mode=mode)
        else:
            try:
                from qgis.core import QgsProject, QgsMapLayer
                layers = list(QgsProject.instance().mapLayers().values())
                active_l = None
                for l in reversed(layers):
                    if hasattr(QgsMapLayer, "PointCloudLayer") and l.type() == QgsMapLayer.PointCloudLayer:
                        active_l = l
                        break
                    elif ElevationStyler.is_dem_or_elevation(l):
                        active_l = l
                        break
                if active_l:
                    self.elevation_legend.update_from_layer(active_l, mode=mode)
                else:
                    self.elevation_legend.hide()
            except Exception:
                self.elevation_legend.hide()

    def update_lidar_legend(self, layer, mode: str):
        if self.elevation_legend:
            self.elevation_legend.update_for_lidar_mode(layer, mode)

    def toggle_elevation_legend(self):
        if self.elevation_legend:
            self.elevation_legend.setVisible(not self.elevation_legend.isVisible())

    def _setup_tools(self):
        if not self.canvas:
            return
        try:
            from qgis.gui import QgsMapToolPan, QgsMapToolZoom
            self._pan_tool = QgsMapToolPan(self.canvas)
            self._zoom_in_tool = QgsMapToolZoom(self.canvas, False)
            self._zoom_out_tool = QgsMapToolZoom(self.canvas, True)
            self.canvas.setMapTool(self._pan_tool)
        except Exception:
            pass

    def _on_coord_changed(self, point):
        self.coordinate_changed.emit(point.x(), point.y())
        elev = CanvasLayerCoordinator.sample_elevation_at_point(self.canvas, point)
        self.elevation_changed.emit(elev)

    def _sample_elevation_at_point(self, point):
        return CanvasLayerCoordinator.sample_elevation_at_point(self.canvas, point)

    def _on_project_crs_changed(self):
        CanvasLayerCoordinator.sync_project_crs(self.canvas)

    def _on_layers_added(self, layers):
        if self._in_layers_added:
            return
        self._in_layers_added = True
        try:
            CanvasLayerCoordinator.handle_layers_added(
                self.canvas, self.bridge, self.nav_mgr, self.elevation_legend, layers
            )
        finally:
            self._in_layers_added = False
        self.refresh_canvas()

    def _on_layers_changed(self, *args):
        self.update_elevation_legend()
        if self.bridge:
            self.bridge.setCanvasLayers()
        self.refresh_canvas()

    def set_tool(self, tool_name: str):
        if not self.canvas:
            return
        tool_map = {
            "pan":      self._pan_tool,
            "zoom_in":  self._zoom_in_tool,
            "zoom_out": self._zoom_out_tool,
        }
        tool = tool_map.get(tool_name)
        if tool:
            self.canvas.setMapTool(tool)
        elif tool_name == "identify":
            try:
                from qgis.gui import QgsMapToolIdentifyFeature
                t = QgsMapToolIdentifyFeature(self.canvas)
                self.canvas.setMapTool(t)
            except Exception:
                pass

    def add_layer_to_canvas(self, layer):
        if not self.canvas or not layer:
            return
        try:
            from qgis.core import QgsProject
            QgsProject.instance().addMapLayer(layer)
            if self.nav_mgr:
                self.nav_mgr.zoom_to_layer(layer)
        except Exception:
            pass

    def refresh_layers(self):
        if not self.canvas:
            return
        try:
            if self.bridge:
                self.bridge.setCanvasLayers()
            self.canvas.refresh()
        except Exception:
            pass

    def force_refresh_canvas(self):
        if not self.canvas:
            return
        try:
            self.canvas.refresh()
        except Exception:
            pass

    def refresh_canvas(self):
        if self.canvas:
            self.canvas.refresh()

    def zoom_in(self):
        if self.canvas:
            self.canvas.zoomIn()
            self.canvas.refresh()

    def zoom_out(self):
        if self.canvas:
            self.canvas.zoomOut()
            self.canvas.refresh()

    def zoom_full(self):
        if self.canvas:
            self.canvas.zoomToFullExtent()
            self.canvas.refresh()

    def zoom_last(self):
        if self.nav_mgr:
            self.nav_mgr.zoom_last()

    def zoom_next(self):
        if self.nav_mgr:
            self.nav_mgr.zoom_next()

    def zoom_to_layer(self, layer):
        if self.nav_mgr:
            self.nav_mgr.zoom_to_layer(layer)

    def zoom_to_active_layer(self, layer=None):
        if self.nav_mgr:
            self.nav_mgr.zoom_to_active_layer(layer)

    def get_canvas(self):
        return self.canvas

    def get_scale(self):
        return self.canvas.scale() if self.canvas else 1.0

    def get_crs(self):
        if self.canvas:
            crs = self.canvas.mapSettings().destinationCrs()
            if crs.isValid() and crs.authid():
                return crs.authid()
        try:
            from qgis.core import QgsProject
            crs = QgsProject.instance().crs()
            if crs.isValid() and crs.authid():
                return crs.authid()
        except Exception:
            pass
        return "EPSG:4326"

    def wait_for_render_complete(self, callback, timeout_ms: int = 4000):
        """Executes callback when the canvas completes rendering the current view."""
        if not self.canvas:
            callback()
            return

        from PyQt5.QtCore import QTimer
        triggered = [False]

        def _on_done():
            if not triggered[0]:
                triggered[0] = True
                try:
                    self.canvas.mapCanvasRefreshed.disconnect(_on_done)
                except Exception:
                    pass
                callback()

        self.canvas.mapCanvasRefreshed.connect(_on_done)
        QTimer.singleShot(timeout_ms, _on_done)

