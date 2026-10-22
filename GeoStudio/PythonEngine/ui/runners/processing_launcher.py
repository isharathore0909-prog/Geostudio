# -*- coding: utf-8 -*-
"""
GeoStudio - Processing Algorithm Launcher
Routes algorithm dialog openings, special direct tool handling, and main window tool actions.
"""

from PyQt5.QtWidgets import QMessageBox
from core.processing.algorithm_registry import AlgorithmDefinition
from ui.dialogs.algorithm_dialog import QgisAlgorithmDialog


def launch_algorithm(algo: AlgorithmDefinition, map_canvas=None, main_window=None, parent=None):
    """Open universal QGIS algorithm parameter dialog or execute direct GUI tools."""
    if algo.dialog_type == "open_attribute_table":
        if main_window:
            main_window.open_attribute_table()
        return
    elif algo.dialog_type == "dem_dialog":
        if main_window:
            main_window.open_dem_elevation_dialog()
        return
    elif algo.dialog_type == "terrain_profile" or algo.algo_id == "terrain:elevation_profile":
        if main_window:
            main_window.open_elevation_profile()
        return
    elif algo.dialog_type in ("terrain_cutfill", "terrain:cut_fill") or algo.algo_id == "terrain:cut_fill":
        if main_window:
            main_window.open_cut_fill()
        return
    elif algo.dialog_type in ("terrain_volumetrics", "terrain:volumetric_analysis") or algo.algo_id == "terrain:volumetric_analysis":
        if main_window:
            main_window.open_volumetric_analysis()
        return
    elif algo.dialog_type in ("io_import_vector", "io_import_raster", "io_import_csv"):
        if main_window:
            if algo.dialog_type == "io_import_vector":
                main_window.add_vector()
            elif algo.dialog_type == "io_import_raster":
                main_window.add_raster()
            elif algo.dialog_type == "io_import_csv":
                main_window.add_csv()
        return
    elif algo.dialog_type == "tools_measure":
        QMessageBox.information(parent, "Measure Tool", "Click points on the Map Canvas to measure distance and polygon area.")
        return
    elif algo.dialog_type == "tools_coord":
        QMessageBox.information(parent, "Coordinate Capture", "Click anywhere on the map canvas to view coordinates and CRS info.")
        return

    dlg = QgisAlgorithmDialog(algo, map_canvas=map_canvas, main_window=main_window, parent=parent or main_window)
    dlg.exec_()
