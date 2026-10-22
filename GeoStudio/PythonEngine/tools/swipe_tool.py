# -*- coding: utf-8 -*-
"""
GeoStudio - Swipe Tool
Interactive map canvas tool that lets the user compare two layers side-by-side
using an interactive vertical divider, horizontal divider, or circular spyglass.

Three modes (matching ArcGIS Web AppBuilder & ArcGIS Pro):
  - vertical   : drag left ↔ right to peel back Layer A over Layer B
  - horizontal : drag up   ↕ down to peel back Layer A over Layer B
  - spyglass   : circular porthole that follows the mouse to look through Layer B into Layer A

Implementation strategy:
-----------------------
SwipeOverlay renders Layer A and Layer B via QgsMapSettings and QgsMapRendererSequentialJob
for the exact current canvas extent and resolution.
In paintEvent, QPainter clip regions (setClipRect / setClipPath) composite Layer A and
Layer B at 60+ FPS without re-rendering during dragging or mouse movement.
"""

from PyQt5.QtWidgets import QWidget, QSizePolicy
from PyQt5.QtCore import Qt, QPoint, QRect, QPointF, pyqtSignal, QTimer, QSize
from PyQt5.QtGui import (
    QPainter, QPen, QColor, QPainterPath, QCursor, QPixmap, QBrush, QFont
)


# ---------------------------------------------------------------------------
# Visual styling constants
# ---------------------------------------------------------------------------
HANDLE_SIZE   = 36          # px - draggable handle circle diameter
BAR_WIDTH     = 2           # px - divider line thickness
SPYGLASS_R    = 120         # px - spyglass radius
BAR_COLOR     = QColor("#ffffff")
SHADOW_COLOR  = QColor(0, 0, 0, 90)
HANDLE_COLOR  = QColor("#2563eb")
HANDLE_BORDER = QColor("#ffffff")


class SwipeOverlay(QWidget):
    """
    Transparent hardware-blitted overlay widget drawn on top of QgsMapCanvas.
    Renders Layer A and Layer B with real-time clipped compositing.

    Signals
    -------
    position_changed(float)
        Emits the divider position as a fraction [0..1] whenever the user drags it.
    """

    position_changed = pyqtSignal(float)

    def __init__(self, canvas, layer_a=None, layer_b=None, mode: str = "vertical", parent=None):
        """
        Parameters
        ----------
        canvas  : QgsMapCanvas
        layer_a : QgsMapLayer - primary swipe layer (left / top / inside spyglass)
        layer_b : QgsMapLayer - comparison layer (right / bottom / outside spyglass)
        mode    : "vertical" | "horizontal" | "spyglass"
        """
        super().__init__(parent or (canvas.parent() if canvas else None) or canvas)
        self.canvas  = canvas
        self.layer_a = layer_a
        self.layer_b = layer_b
        self.mode    = mode            # "vertical" | "horizontal" | "spyglass"
        self._frac   = 0.5             # divider position [0..1]
        self._mouse  = QPoint(200, 200) # current mouse pos for spyglass
        self._drag   = False           # dragging divider state
        self.spyglass_radius = SPYGLASS_R

        self._pixmap_a = None
        self._pixmap_b = None
        self._render_pending = False

        # Set up overlay attributes
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setWindowFlags(Qt.SubWindow)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMouseTracking(True)

        self._sync_geometry()
        self._update_cursor()

        # Connect to canvas view changes
        if self.canvas:
            try:
                self.canvas.extentsChanged.connect(self._schedule_render)
                self.canvas.layersChanged.connect(self._schedule_render)
            except Exception:
                pass

        # Initial render of both layers
        self._render_layers()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_mode(self, mode: str):
        """Switch between 'vertical', 'horizontal', 'spyglass'."""
        self.mode = mode
        self._update_cursor()
        self.update()

    def set_layers(self, layer_a, layer_b=None):
        """Set which two layers are being compared."""
        self.layer_a = layer_a
        self.layer_b = layer_b
        self._render_layers()

    def set_layer(self, layer_a):
        """Backward compatibility: set primary layer."""
        self.set_layers(layer_a, self.layer_b)

    def set_fraction(self, frac: float):
        """Programmatically move divider (0.0 = left/top, 1.0 = right/bottom)."""
        self._frac = max(0.01, min(0.99, frac))
        self.update()

    def set_spyglass_radius(self, r: int):
        """Set the radius in pixels for the circular spyglass."""
        self.spyglass_radius = max(40, min(400, r))
        self.update()

    def deactivate(self):
        """Disconnect canvas signals, release pixmaps, and hide overlay."""
        if self.canvas:
            try:
                self.canvas.extentsChanged.disconnect(self._schedule_render)
            except Exception:
                pass
            try:
                self.canvas.layersChanged.disconnect(self._schedule_render)
            except Exception:
                pass
        self._pixmap_a = None
        self._pixmap_b = None
        self.hide()

    # ------------------------------------------------------------------
    # Layer Rendering (Pre-compositing)
    # ------------------------------------------------------------------

    def _schedule_render(self):
        """Debounce render during rapid panning or zooming."""
        if not self.isVisible() or not self.canvas:
            return
        if self._render_pending:
            return
        self._render_pending = True
        QTimer.singleShot(40, self._do_scheduled_render)

    def _do_scheduled_render(self):
        self._render_pending = False
        self._render_layers()

    def _render_layers(self):
        """Render high-resolution pixmaps for Layer A and Layer B matching canvas."""
        if not self.canvas:
            return

        w, h = self.width(), self.height()
        if w <= 10 or h <= 10:
            geo = self.canvas.geometry()
            w, h = geo.width(), geo.height()
        if w <= 10 or h <= 10:
            return

        out_size = QSize(w, h)
        extent   = self.canvas.extent()
        crs      = self.canvas.mapSettings().destinationCrs()
        dpi      = self.canvas.mapSettings().outputDpi()
        bg       = self.canvas.canvasColor()

        try:
            from qgis.core import QgsMapSettings, QgsMapRendererSequentialJob

            # 1. Render Layer A (Primary top layer)
            if self.layer_a and self.layer_a.isValid():
                ms_a = QgsMapSettings()
                ms_a.setOutputSize(out_size)
                ms_a.setOutputDpi(dpi)
                ms_a.setExtent(extent)
                ms_a.setDestinationCrs(crs)
                ms_a.setLayers([self.layer_a])
                ms_a.setBackgroundColor(bg)
                job_a = QgsMapRendererSequentialJob(ms_a)
                job_a.start()
                job_a.waitForFinished()
                self._pixmap_a = QPixmap.fromImage(job_a.renderedImage())
            else:
                self._pixmap_a = None

            # 2. Render Layer B (Comparison layer)
            layers_b = []
            if self.layer_b and self.layer_b.isValid():
                layers_b = [self.layer_b]
            else:
                # Fallback to all other visible layers currently in canvas
                for l in self.canvas.layers():
                    if l != self.layer_a and l.isValid():
                        layers_b.append(l)

            if layers_b:
                ms_b = QgsMapSettings()
                ms_b.setOutputSize(out_size)
                ms_b.setOutputDpi(dpi)
                ms_b.setExtent(extent)
                ms_b.setDestinationCrs(crs)
                ms_b.setLayers(layers_b)
                ms_b.setBackgroundColor(bg)
                job_b = QgsMapRendererSequentialJob(ms_b)
                job_b.start()
                job_b.waitForFinished()
                self._pixmap_b = QPixmap.fromImage(job_b.renderedImage())
            else:
                self._pixmap_b = None

        except Exception as e:
            print(f"[SwipeOverlay] Error rendering layer pixmaps: {e}")

        self.update()

    # ------------------------------------------------------------------
    # Geometry sync & resizing
    # ------------------------------------------------------------------

    def _sync_geometry(self):
        """Fit overlay exactly over canvas."""
        if self.canvas:
            geo = self.canvas.geometry()
            self.setGeometry(0, 0, geo.width(), geo.height())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._sync_geometry()
        self._schedule_render()

    # ------------------------------------------------------------------
    # Mouse & Keyboard Interaction
    # ------------------------------------------------------------------

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag = True
            self._update_from_event(event)

    def mouseMoveEvent(self, event):
        self._mouse = event.pos()
        if self._drag or self.mode == "spyglass":
            self._update_from_event(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag = False

    def wheelEvent(self, event):
        """Forward mouse wheel scroll to canvas for zooming."""
        if self.canvas:
            self.canvas.wheelEvent(event)

    def _update_from_event(self, event):
        pos = event.pos()
        w, h = self.width(), self.height()
        if w == 0 or h == 0:
            return
        if self.mode == "vertical":
            self._frac = max(0.01, min(0.99, pos.x() / w))
        elif self.mode == "horizontal":
            self._frac = max(0.01, min(0.99, pos.y() / h))
        elif self.mode == "spyglass":
            self._mouse = pos

        self.position_changed.emit(self._frac)
        self.update()

    # ------------------------------------------------------------------
    # Painting
    # ------------------------------------------------------------------

    def paintEvent(self, event):
        if not self.isVisible():
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        w, h = self.width(), self.height()

        if self.mode == "vertical":
            self._paint_vertical(painter, w, h)
        elif self.mode == "horizontal":
            self._paint_horizontal(painter, w, h)
        elif self.mode == "spyglass":
            self._paint_spyglass(painter, w, h)

        painter.end()

    def _paint_vertical(self, painter, w, h):
        x = int(self._frac * w)

        # 1. Left side [0 .. x]: Layer A
        if self._pixmap_a:
            painter.save()
            painter.setClipRect(0, 0, x, h)
            painter.drawPixmap(0, 0, self._pixmap_a)
            painter.restore()

        # 2. Right side [x .. w]: Layer B
        if self._pixmap_b:
            painter.save()
            painter.setClipRect(x, 0, w - x, h)
            painter.drawPixmap(0, 0, self._pixmap_b)
            painter.restore()

        # 3. Divider shadow & line
        pen_shadow = QPen(SHADOW_COLOR, BAR_WIDTH + 2)
        painter.setPen(pen_shadow)
        painter.drawLine(x + 1, 0, x + 1, h)

        pen = QPen(BAR_COLOR, BAR_WIDTH)
        painter.setPen(pen)
        painter.drawLine(x, 0, x, h)

        # 4. Handle knob in center
        self._paint_handle(painter, QPointF(x, h / 2))

        # 5. Descriptive layer labels at bottom
        name_a = self.layer_a.name() if self.layer_a else "Layer A"
        name_b = self.layer_b.name() if self.layer_b else "Layer B"
        self._paint_label(painter, QRect(max(10, x - 170), h - 34, 160, 24), f"◀  {name_a}", Qt.AlignRight)
        self._paint_label(painter, QRect(min(w - 170, x + 10), h - 34, 160, 24), f"{name_b}  ▶", Qt.AlignLeft)

    def _paint_horizontal(self, painter, w, h):
        y = int(self._frac * h)

        # 1. Top side [0 .. y]: Layer A
        if self._pixmap_a:
            painter.save()
            painter.setClipRect(0, 0, w, y)
            painter.drawPixmap(0, 0, self._pixmap_a)
            painter.restore()

        # 2. Bottom side [y .. h]: Layer B
        if self._pixmap_b:
            painter.save()
            painter.setClipRect(0, y, w, h - y)
            painter.drawPixmap(0, 0, self._pixmap_b)
            painter.restore()

        # 3. Divider shadow & line
        pen_shadow = QPen(SHADOW_COLOR, BAR_WIDTH + 2)
        painter.setPen(pen_shadow)
        painter.drawLine(0, y + 1, w, y + 1)

        pen = QPen(BAR_COLOR, BAR_WIDTH)
        painter.setPen(pen)
        painter.drawLine(0, y, w, y)

        # 4. Handle knob in center
        self._paint_handle(painter, QPointF(w / 2, y))

        # 5. Descriptive layer labels
        name_a = self.layer_a.name() if self.layer_a else "Layer A"
        name_b = self.layer_b.name() if self.layer_b else "Layer B"
        self._paint_label(painter, QRect(w - 170, max(10, y - 30), 160, 24), f"▲  {name_a}", Qt.AlignRight)
        self._paint_label(painter, QRect(w - 170, min(h - 34, y + 6), 160, 24), f"▼  {name_b}", Qt.AlignRight)

    def _paint_spyglass(self, painter, w, h):
        cx, cy = self._mouse.x(), self._mouse.y()
        r = self.spyglass_radius

        # 1. Base map outside lens is Layer B
        if self._pixmap_b:
            painter.drawPixmap(0, 0, self._pixmap_b)

        # 2. Inside circular lens is Layer A
        if self._pixmap_a:
            painter.save()
            circle_path = QPainterPath()
            circle_path.addEllipse(QPointF(cx, cy), r, r)
            painter.setClipPath(circle_path)
            painter.drawPixmap(0, 0, self._pixmap_a)
            painter.restore()

        # 3. Lens ring shadow
        pen_shadow = QPen(SHADOW_COLOR, 5)
        painter.setPen(pen_shadow)
        painter.drawEllipse(QPointF(cx + 1, cy + 1), r, r)

        # 4. Lens ring outer border
        pen = QPen(BAR_COLOR, 3)
        painter.setPen(pen)
        painter.drawEllipse(QPointF(cx, cy), r, r)

        # 5. Cross-hairs
        pen_cross = QPen(QColor(255, 255, 255, 180), 1.2)
        painter.setPen(pen_cross)
        painter.drawLine(int(cx - r), int(cy), int(cx + r), int(cy))
        painter.drawLine(int(cx), int(cy - r), int(cx), int(cy + r))

        # 6. Floating label indicating what layer is being inspected
        name_a = self.layer_a.name() if self.layer_a else "Layer A"
        lbl_rect = QRect(int(cx - 80), int(cy + r + 6), 160, 22)
        if lbl_rect.bottom() > h - 5:
            lbl_rect.moveBottom(int(cy - r - 6))
        self._paint_label(painter, lbl_rect, f"🔍  {name_a}", Qt.AlignCenter)

    def _paint_handle(self, painter, center: QPointF):
        """Draw round drag handle knob with arrow glyph."""
        r = HANDLE_SIZE / 2
        # Shadow
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(SHADOW_COLOR))
        painter.drawEllipse(center + QPointF(1, 1), r, r)

        # Outer border
        painter.setBrush(QBrush(HANDLE_COLOR))
        painter.setPen(QPen(HANDLE_BORDER, 2))
        painter.drawEllipse(center, r, r)

        # Glyph
        painter.setPen(QPen(QColor("#ffffff"), 1.5))
        rect = QRect(int(center.x() - r), int(center.y() - r), HANDLE_SIZE, HANDLE_SIZE)
        f = QFont()
        f.setPointSize(11)
        f.setBold(True)
        painter.setFont(f)
        glyph = "⇔" if self.mode == "vertical" else "⇕"
        painter.drawText(rect, Qt.AlignCenter, glyph)

    def _paint_label(self, painter, rect: QRect, text: str, align):
        """Draw semi-transparent badge with layer name."""
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(15, 23, 42, 190)))
        painter.drawRoundedRect(rect, 4, 4)

        painter.setPen(QColor("#ffffff"))
        f = QFont()
        f.setPointSize(8)
        f.setBold(True)
        painter.setFont(f)
        painter.drawText(rect.adjusted(6, 0, -6, 0), align | Qt.AlignVCenter, text)

    def _update_cursor(self):
        if self.mode == "spyglass":
            self.setCursor(Qt.CrossCursor)
        elif self.mode == "vertical":
            self.setCursor(Qt.SplitHCursor)
        else:
            self.setCursor(Qt.SplitVCursor)
