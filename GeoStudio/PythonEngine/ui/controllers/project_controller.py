# -*- coding: utf-8 -*-
"""
GeoStudio - Project & App Lifecycle Controller Mixin
"""
import os
from PyQt5.QtWidgets import QFileDialog, QMessageBox


class ProjectControllerMixin:
    """Handles project lifecycle, file I/O, layouts, themes, and about dialogs."""

    def new_project(self):
        try:
            from qgis.core import QgsProject
            QgsProject.instance().clear()
            self.layer_panel.refresh()
            self.map_canvas.refresh_canvas()
            self.setWindowTitle(f"{self.APP_NAME} — New Project")
        except Exception as e:
            self._info(f"New project: {e}")

    def open_project(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Project", "", "QGIS Projects (*.qgs *.qgz);;All Files (*)"
        )
        if path:
            import time
            fname = os.path.basename(path)
            sz_str = ""
            try:
                sz = os.path.getsize(path)
                if sz >= 1024 * 1024:
                    sz_str = f"{sz / (1024 * 1024):.1f} MB"
                elif sz >= 1024:
                    sz_str = f"{sz / 1024:.1f} KB"
            except Exception:
                pass

            t0 = time.perf_counter()
            if hasattr(self, "geo_status") and hasattr(self.geo_status, "start_file_loading"):
                self.geo_status.start_file_loading(fname, sz_str, "Reading project layers & state...")

            try:
                from qgis.core import QgsProject
                if hasattr(self, "geo_status") and hasattr(self.geo_status, "update_file_loading"):
                    self.geo_status.update_file_loading(50, "Restoring map canvas layers...")

                QgsProject.instance().read(path)
                self.layer_panel.refresh()
                self.map_canvas.refresh_canvas()
                self.setWindowTitle(f"{self.APP_NAME} — {fname}")

                t_elapsed = time.perf_counter() - t0
                if hasattr(self, "geo_status") and hasattr(self.geo_status, "finish_file_loading"):
                    self.geo_status.finish_file_loading(fname, t_elapsed, sz_str, "Project")
            except Exception as e:
                t_elapsed = time.perf_counter() - t0
                if hasattr(self, "geo_status") and hasattr(self.geo_status, "fail_file_loading"):
                    self.geo_status.fail_file_loading(fname, t_elapsed, str(e))
                self._err(f"Could not open project: {e}")


    def save_project(self):
        try:
            from qgis.core import QgsProject
            path = QgsProject.instance().fileName()
            if path:
                QgsProject.instance().write(path)
                self.statusBar().showMessage("Project saved.", 3000)
            else:
                self.save_project_as()
        except Exception as e:
            self._err(str(e))

    def save_project_as(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Project As", "",
            "QGIS Project (*.qgs);;QGIS Compressed (*.qgz)"
        )
        if path:
            try:
                from qgis.core import QgsProject
                QgsProject.instance().write(path)
                self.setWindowTitle(f"{self.APP_NAME} — {os.path.basename(path)}")
            except Exception as e:
                self._err(str(e))

    def project_properties(self):
        self._info("Project Properties dialog.")

    def print_map(self):
        from ui.dialogs.print_export_dialog import PrintExportDialog
        dlg = PrintExportDialog(self)
        dlg.exec_()

    def set_theme(self, theme_name: str = "offwhite"):
        from core.style import OFFWHITE_STYLESHEET, DARK_STYLESHEET
        if theme_name == "offwhite":
            self.setStyleSheet(OFFWHITE_STYLESHEET)
            if self.map_canvas:
                self.map_canvas.set_canvas_background("#f8f9fa")
            self.geo_status.showMessage("Off-White Light Theme applied", 3000)
        else:
            self.setStyleSheet(DARK_STYLESHEET)
            if self.map_canvas:
                self.map_canvas.set_canvas_background("#1e272c")
            self.geo_status.showMessage("Dark GIS Theme applied", 3000)

    def set_project_crs(self):
        self._info("CRS selector.")

    def open_docs(self):
        import webbrowser
        webbrowser.open("https://docs.qgis.org/3.34/en/docs/pyqgis_developer_cookbook/")

    def about(self):
        QMessageBox.about(
            self, f"About {self.APP_NAME}",
            f"<h2>🌍 {self.APP_NAME} v{self.VERSION}</h2>"
            f"<p>A standalone GIS application powered by QGIS & GPU-accelerated computing.</p>"
            f"<p>Built with PyQGIS, PyQt5, GDAL, NumPy, CuPy.</p>"
        )

    def _info(self, msg):
        QMessageBox.information(self, self.APP_NAME, msg)

    def _err(self, msg):
        QMessageBox.critical(self, self.APP_NAME, msg)

    def closeEvent(self, event):
        reply = QMessageBox.question(
            self, "Exit GeoStudio", "Exit GeoStudio?", QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()
