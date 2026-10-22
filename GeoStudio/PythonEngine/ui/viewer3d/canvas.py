# -*- coding: utf-8 -*-
"""
GeoStudio - 3D OpenGL Point Cloud Canvas
High-performance OpenGL viewport for orbit, pan, pitch, and zoom point rendering.
"""

import numpy as np
from PyQt5.QtCore import Qt, QPoint, pyqtSignal
from PyQt5.QtWidgets import QOpenGLWidget
from OpenGL.GL import *
from OpenGL.GLU import *


class GLPointCloudCanvas(QOpenGLWidget):
    """High-performance OpenGL 3D Viewport with Orbit, Pan, Pitch, Tilt, and Zoom."""

    camera_changed = pyqtSignal(float, float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.pts_xyz = None
        self.current_colors = None
        self.rgb_colors = None
        self.z_colors = None
        self.class_colors = None
        self.intensity_colors = None

        self.rot_x = 45.0
        self.rot_z = -30.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.zoom_dist = 300.0
        self.z_exaggeration = 1.5
        self.point_size = 4.5
        self.show_grid = True
        self.show_bbox = True
        self.bg_color = (0.0, 0.0, 0.0, 1.0)

        self._last_pos = QPoint()
        self.color_dict = {}

        # Hardware-accelerated GPU VBOs (persistent VRAM buffers)
        self._vbo_pts = None
        self._vbo_col = None
        self._vbo_needs_pts_upload = False
        self._vbo_needs_col_upload = False

    def set_point_data(self, pts_xyz, rgb_colors, z_colors, class_colors, intensity_colors, mode="auto", color_dict=None):
        def _to_f32(arr):
            if arr is None:
                return None
            return np.ascontiguousarray(arr, dtype=np.float32)

        self.pts_xyz = _to_f32(pts_xyz)
        self.rgb_colors = _to_f32(rgb_colors)
        self.z_colors = _to_f32(z_colors)
        self.class_colors = _to_f32(class_colors)
        self.intensity_colors = _to_f32(intensity_colors)
        self.color_dict = {}
        if color_dict:
            for k, v in color_dict.items():
                self.color_dict[k] = _to_f32(v)

        # Ensure base colors are indexed
        if "Elevation" not in self.color_dict and self.z_colors is not None:
            self.color_dict["Elevation"] = self.z_colors
        if "RGB" not in self.color_dict and self.rgb_colors is not None:
            self.color_dict["RGB"] = self.rgb_colors
        if "Classification" not in self.color_dict and self.class_colors is not None:
            self.color_dict["Classification"] = self.class_colors
        if "Intensity" not in self.color_dict and self.intensity_colors is not None:
            self.color_dict["Intensity"] = self.intensity_colors

        if mode == "auto":
            if self.rgb_colors is not None and not np.all(self.rgb_colors == 0):
                self.current_colors = self.rgb_colors
            else:
                self.current_colors = self.z_colors
        elif mode in self.color_dict:
            self.current_colors = self.color_dict[mode]
        elif mode == "rgb" and self.rgb_colors is not None:
            self.current_colors = self.rgb_colors
        elif mode == "class" and self.class_colors is not None:
            self.current_colors = self.class_colors
        elif mode == "intensity" and self.intensity_colors is not None:
            self.current_colors = self.intensity_colors
        else:
            self.current_colors = self.z_colors

        if self.pts_xyz is not None and len(self.pts_xyz) > 0:
            max_extent = float(np.percentile(np.abs(self.pts_xyz), 98))
            self.zoom_dist = max(30.0, max_extent * 2.2)
            self.pan_x = 0.0
            self.pan_y = 0.0

        self._vbo_needs_pts_upload = True
        self._vbo_needs_col_upload = True
        self.update()

    def set_color_mode(self, mode_str: str):
        # Look up directly in color_dict or fallback to standard properties
        if mode_str in self.color_dict:
            self.current_colors = self.color_dict[mode_str]
        elif mode_str in ["RGB", "RGB (True Color)", "Color Lidar by RGB/Elev", "rgb_elev", "RGB / Elevation Hybrid"]:
            if self.rgb_colors is not None and not np.all(self.rgb_colors == 0):
                self.current_colors = self.rgb_colors
            else:
                self.current_colors = self.z_colors
        elif mode_str in ["Elevation", "Elevation (Turbo Ramp)", "elevation"]:
            self.current_colors = self.z_colors
        elif mode_str in ["Classification", "Classification (ASPRS)", "classification"] and self.class_colors is not None:
            self.current_colors = self.class_colors
        elif mode_str in ["Intensity", "Intensity (Laser Return)", "intensity"] and self.intensity_colors is not None:
            self.current_colors = self.intensity_colors
        else:
            self.current_colors = self.z_colors
        self._vbo_needs_col_upload = True
        self.update()

    def set_point_size(self, size: float):
        self.point_size = size
        self.update()

    def set_z_exaggeration(self, exag: float):
        self.z_exaggeration = exag
        self.update()

    def set_background_theme(self, theme: str):
        if theme == "Dark Slate":
            self.bg_color = (0.06, 0.09, 0.16, 1.0)
        elif theme == "Studio Gray":
            self.bg_color = (0.12, 0.15, 0.20, 1.0)
        elif theme == "Sky Blue":
            self.bg_color = (0.53, 0.75, 0.92, 1.0)
        else:
            self.bg_color = (0.97, 0.98, 0.99, 1.0)
        self.update()

    def reset_view(self):
        self.rot_x = 45.0
        self.rot_z = -30.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        if self.pts_xyz is not None and len(self.pts_xyz) > 0:
            max_extent = float(np.max(np.abs(self.pts_xyz)))
            self.zoom_dist = max(50.0, max_extent * 2.2)
        self.update()

    def set_top_view(self):
        self.rot_x = 0.0
        self.rot_z = 0.0
        self.update()

    def set_isometric_view(self):
        self.rot_x = 54.735
        self.rot_z = -45.0
        self.update()

    # ── OpenGL Pipeline ─────────────────────────────────────────
    def initializeGL(self):
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_POINT_SMOOTH)
        glHint(GL_POINT_SMOOTH_HINT, GL_NICEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        try:
            glEnable(GL_MULTISAMPLE)
            glShadeModel(GL_SMOOTH)
        except Exception:
            pass
        glClearColor(*self.bg_color)

    def resizeGL(self, w, h):
        glViewport(0, 0, w, max(1, h))
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45.0, w / max(1.0, float(h)), 1.0, 50000.0)
        glMatrixMode(GL_MODELVIEW)

    def paintGL(self):
        glClearColor(*self.bg_color)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        # Dynamic perspective near/far plane based on current zoom distance (prevents Z-fighting / depth flicker)
        w = max(1, self.width())
        h = max(1, self.height())
        z_near = max(0.5, float(self.zoom_dist * 0.02))
        z_far = max(2000.0, float(self.zoom_dist * 15.0))

        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45.0, w / float(h), z_near, z_far)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

        glTranslatef(self.pan_x, self.pan_y, -self.zoom_dist)
        glRotatef(self.rot_x, 1.0, 0.0, 0.0)
        glRotatef(self.rot_z, 0.0, 0.0, 1.0)

        glPushMatrix()
        glScalef(1.0, 1.0, float(self.z_exaggeration))

        if self.show_grid:
            self._draw_grid()

        if self.pts_xyz is not None and len(self.pts_xyz) > 0:
            glPointSize(float(self.point_size))
            glDisable(GL_BLEND)
            glDisable(GL_POINT_SMOOTH)
            glEnable(GL_DEPTH_TEST)
            glDepthFunc(GL_LEQUAL)

            import ctypes
            self._sync_vbos()

            try:
                if self._vbo_pts is not None:
                    # ── Pure GPU Path: Zero PCIe bus transfer during camera navigation ──
                    glBindBuffer(GL_ARRAY_BUFFER, self._vbo_pts)
                    glEnableClientState(GL_VERTEX_ARRAY)
                    glVertexPointer(3, GL_FLOAT, 0, ctypes.c_void_p(0))

                    if self._vbo_col is not None:
                        glBindBuffer(GL_ARRAY_BUFFER, self._vbo_col)
                        glEnableClientState(GL_COLOR_ARRAY)
                        glColorPointer(3, GL_FLOAT, 0, ctypes.c_void_p(0))
                    else:
                        glDisableClientState(GL_COLOR_ARRAY)
                        glColor3f(0.25, 0.85, 0.45)

                    glDrawArrays(GL_POINTS, 0, len(self.pts_xyz))
                    glBindBuffer(GL_ARRAY_BUFFER, 0)
                else:
                    # ── Fallback Path: Client-side arrays ──
                    glEnableClientState(GL_VERTEX_ARRAY)
                    pts = np.ascontiguousarray(self.pts_xyz, dtype=np.float32)
                    glVertexPointer(3, GL_FLOAT, 0, pts)

                    colors = self.current_colors if (self.current_colors is not None and len(self.current_colors) == len(self.pts_xyz)) else self.z_colors
                    if colors is not None and len(colors) == len(self.pts_xyz):
                        glEnableClientState(GL_COLOR_ARRAY)
                        col = np.ascontiguousarray(colors, dtype=np.float32)
                        glColorPointer(3, GL_FLOAT, 0, col)
                    else:
                        glDisableClientState(GL_COLOR_ARRAY)
                        glColor3f(0.25, 0.85, 0.45)

                    glDrawArrays(GL_POINTS, 0, len(self.pts_xyz))
            except Exception:
                pass
            finally:
                glDisableClientState(GL_COLOR_ARRAY)
                glDisableClientState(GL_VERTEX_ARRAY)
                try:
                    glBindBuffer(GL_ARRAY_BUFFER, 0)
                except Exception:
                    pass

            if self.show_bbox:
                self._draw_bounding_box()

        glPopMatrix()

    def _draw_grid(self):
        if self.pts_xyz is not None and len(self.pts_xyz) > 0:
            min_v = np.min(self.pts_xyz, axis=0)
            max_v = np.max(self.pts_xyz, axis=0)
            max_extent = max(float(max_v[0] - min_v[0]), float(max_v[1] - min_v[1]))
            grid_size = max(50.0, float(max_extent * 0.65))
            z_floor = float(min_v[2])
        else:
            grid_size = 250.0
            z_floor = 0.0

        glLineWidth(1.0)
        glColor4f(0.3, 0.4, 0.5, 0.25)
        step = max(5.0, grid_size / 10.0)

        glBegin(GL_LINES)
        x = -grid_size
        while x <= grid_size:
            glVertex3f(x, -grid_size, z_floor)
            glVertex3f(x, grid_size, z_floor)
            glVertex3f(-grid_size, x, z_floor)
            glVertex3f(grid_size, x, z_floor)
            x += step
        glEnd()

        # Center Origin Coordinate Triad (X=Red, Y=Green, Z=Blue) at geometric center (0, 0, 0)
        axis_len = max(20.0, grid_size * 0.20)
        glLineWidth(2.5)
        glBegin(GL_LINES)
        glColor3f(0.95, 0.2, 0.2); glVertex3f(0, 0, 0); glVertex3f(axis_len, 0, 0)
        glColor3f(0.2, 0.85, 0.2); glVertex3f(0, 0, 0); glVertex3f(0, axis_len, 0)
        glColor3f(0.2, 0.55, 0.95); glVertex3f(0, 0, 0); glVertex3f(0, 0, axis_len)
        glEnd()

    def _draw_bounding_box(self):
        if self.pts_xyz is None or len(self.pts_xyz) == 0:
            return
        min_v = np.min(self.pts_xyz, axis=0)
        max_v = np.max(self.pts_xyz, axis=0)

        glDepthMask(GL_FALSE)
        glColor4f(0.4, 0.6, 0.8, 0.35)
        glLineWidth(1.2)

        x0, y0, z0 = min_v
        x1, y1, z1 = max_v

        glBegin(GL_LINE_LOOP); glVertex3f(x0, y0, z0); glVertex3f(x1, y0, z0); glVertex3f(x1, y1, z0); glVertex3f(x0, y1, z0); glEnd()
        glBegin(GL_LINE_LOOP); glVertex3f(x0, y0, z1); glVertex3f(x1, y0, z1); glVertex3f(x1, y1, z1); glVertex3f(x0, y1, z1); glEnd()
        glBegin(GL_LINES)
        glVertex3f(x0, y0, z0); glVertex3f(x0, y0, z1)
        glVertex3f(x1, y0, z0); glVertex3f(x1, y0, z1)
        glVertex3f(x1, y1, z0); glVertex3f(x1, y1, z1)
        glVertex3f(x0, y1, z0); glVertex3f(x0, y1, z1)
        glEnd()
        glDepthMask(GL_TRUE)

    # ── Interactive Mouse Navigation ────────────────────────────
    def mousePressEvent(self, event):
        self._last_pos = event.pos()

    def mouseMoveEvent(self, event):
        dx = event.x() - self._last_pos.x()
        dy = event.y() - self._last_pos.y()

        if event.buttons() & Qt.LeftButton:
            self.rot_x = max(-89.0, min(89.0, self.rot_x + dy * 0.4))
            self.rot_z += dx * 0.4
            self.update()

        elif (event.buttons() & Qt.MidButton) or ((event.buttons() & Qt.LeftButton) and (event.modifiers() & Qt.ShiftModifier)):
            factor = self.zoom_dist * 0.0015
            self.pan_x += dx * factor
            self.pan_y -= dy * factor
            self.update()

        elif event.buttons() & Qt.RightButton:
            self.zoom_dist = max(5.0, self.zoom_dist - dy * (self.zoom_dist * 0.008))
            self.update()

        self._last_pos = event.pos()

    def wheelEvent(self, event):
        num_degrees = event.angleDelta().y() / 8.0
        num_steps = num_degrees / 15.0
        zoom_factor = 1.15 ** (-num_steps)
        self.zoom_dist = max(2.0, self.zoom_dist * zoom_factor)
        self.update()

    # ── Hardware GPU VBO Management ──────────────────────────────
    def _delete_vbos(self):
        """Releases persistent GPU VRAM buffers to prevent memory leaks."""
        try:
            if self._vbo_pts is not None:
                glDeleteBuffers(1, [self._vbo_pts])
                self._vbo_pts = None
            if self._vbo_col is not None:
                glDeleteBuffers(1, [self._vbo_col])
                self._vbo_col = None
        except Exception:
            pass

    def _sync_vbos(self):
        """Uploads point data to GPU VRAM once on data/color change."""
        if self._vbo_needs_pts_upload and self.pts_xyz is not None and len(self.pts_xyz) > 0:
            try:
                if self._vbo_pts is None:
                    self._vbo_pts = glGenBuffers(1)
                pts = np.ascontiguousarray(self.pts_xyz, dtype=np.float32)
                glBindBuffer(GL_ARRAY_BUFFER, self._vbo_pts)
                glBufferData(GL_ARRAY_BUFFER, pts.nbytes, pts, GL_STATIC_DRAW)
                glBindBuffer(GL_ARRAY_BUFFER, 0)
                self._vbo_needs_pts_upload = False
            except Exception:
                self._vbo_pts = None

        if self._vbo_needs_col_upload:
            colors = self.current_colors if (self.current_colors is not None and len(self.current_colors) == len(self.pts_xyz)) else self.z_colors
            if colors is not None and len(colors) == len(self.pts_xyz):
                try:
                    if self._vbo_col is None:
                        self._vbo_col = glGenBuffers(1)
                    col = np.ascontiguousarray(colors, dtype=np.float32)
                    glBindBuffer(GL_ARRAY_BUFFER, self._vbo_col)
                    glBufferData(GL_ARRAY_BUFFER, col.nbytes, col, GL_STATIC_DRAW)
                    glBindBuffer(GL_ARRAY_BUFFER, 0)
                except Exception:
                    self._vbo_col = None
            elif self._vbo_col is not None:
                try:
                    glDeleteBuffers(1, [self._vbo_col])
                except Exception:
                    pass
                self._vbo_col = None
            self._vbo_needs_col_upload = False

    def closeEvent(self, event):
        self._delete_vbos()
        super().closeEvent(event)
