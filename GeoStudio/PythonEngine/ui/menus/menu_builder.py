# -*- coding: utf-8 -*-
"""
GeoStudio - Menu Bar Builder
Constructs the complete 14-category Desktop GIS menu bar with clean typography and icons.
"""

from PyQt5.QtWidgets import QAction, QMenuBar, QMenu
from PyQt5.QtGui import QKeySequence

from resources.icons.icon_provider import get_icon


def _act(parent, text, slot, shortcut=None, tip=None, icon_key=None):
    """Helper to create a configured QAction with optional vector icon."""
    if icon_key:
        a = QAction(get_icon(icon_key), text, parent)
    else:
        a = QAction(text, parent)
    a.triggered.connect(slot)
    if shortcut:
        a.setShortcut(QKeySequence(shortcut))
    if tip:
        a.setToolTip(tip)
        a.setStatusTip(tip)
    return a


def build_main_menus(mw):
    """
    Builds the complete desktop GIS menu hierarchy for GeoStudio:
    File | Edit | View | Layer | Settings | Plugins | Vector | Raster | Satellite | Terrain | LiDAR | Processing | 3D | Help
    """
    mb = mw.menuBar()

    # ── 1. File / Project ─────────────────────────────────────
    m_file = mb.addMenu("&File")
    m_file.addAction(_act(mw, "New Project", mw.new_project, "Ctrl+N", icon_key="new_project"))
    m_file.addAction(_act(mw, "Open Project...", mw.open_project, "Ctrl+O", icon_key="open_project"))
    m_file.addSeparator()
    m_file.addAction(_act(mw, "Save Project", mw.save_project, "Ctrl+S", icon_key="save_project"))
    m_file.addAction(_act(mw, "Save Project As...", mw.save_project_as, "Ctrl+Shift+S", icon_key="save_project_as"))
    m_file.addSeparator()
    m_file.addAction(_act(mw, "Project Properties...", mw.project_properties))
    m_file.addSeparator()
    m_file.addAction(_act(mw, "Print / Export Map Layout...", mw.print_map, "Ctrl+P", icon_key="print_map"))
    m_file.addSeparator()
    m_file.addAction(_act(mw, "Exit", mw.close, "Ctrl+Q"))

    # ── 2. Edit ───────────────────────────────────────────────
    m_edit = mb.addMenu("&Edit")
    m_edit.addAction(_act(mw, "Undo", mw.undo_action, "Ctrl+Z", icon_key="zoom_last"))
    m_edit.addAction(_act(mw, "Redo", mw.redo_action, "Ctrl+Y", icon_key="zoom_next"))
    m_edit.addSeparator()
    m_edit.addAction(_act(mw, "Cut Features", mw.cut_features, "Ctrl+X", icon_key="clip"))
    m_edit.addAction(_act(mw, "Copy Features", mw.copy_features, "Ctrl+C"))
    m_edit.addAction(_act(mw, "Paste Features", mw.paste_features, "Ctrl+V"))
    m_edit.addAction(_act(mw, "Delete Selected", mw.delete_selected, "Delete", icon_key="delete"))
    m_edit.addSeparator()
    m_edit.addAction(_act(mw, "Toggle Editing", mw.toggle_editing, "Ctrl+E", icon_key="toggle_edit"))

    # ── 3. View ───────────────────────────────────────────────
    m_view = mb.addMenu("&View")
    m_view.addAction(_act(mw, "Zoom In", mw.zoom_in, "Ctrl++", icon_key="zoom_in"))
    m_view.addAction(_act(mw, "Zoom Out", mw.zoom_out, "Ctrl+-", icon_key="zoom_out"))
    m_view.addAction(_act(mw, "Zoom Full Extent", mw.zoom_full, "Ctrl+Shift+F", icon_key="zoom_full"))
    m_view.addAction(_act(mw, "Zoom Last", mw.zoom_last, "Ctrl+[", icon_key="zoom_last"))
    m_view.addAction(_act(mw, "Zoom Next", mw.zoom_next, "Ctrl+]", icon_key="zoom_next"))
    m_view.addSeparator()
    m_view.addAction(_act(mw, "Refresh Map Canvas", mw.refresh_canvas, "F5", icon_key="refresh"))
    m_view.addSeparator()
    m_view.addAction(_act(mw, "Layer Swipe Compare...", mw.open_swipe_compare, "Ctrl+Shift+W", icon_key="swipe"))
    m_view.addSeparator()
    mw._view_menu = m_view

    # ── 4. Layer ──────────────────────────────────────────────
    m_layer = mb.addMenu("&Layer")
    m_layer.addAction(_act(mw, "Add Vector Layer...", mw.add_vector, "Ctrl+Shift+V", icon_key="add_vector"))
    m_layer.addAction(_act(mw, "Add Raster Layer...", mw.add_raster, "Ctrl+Shift+R", icon_key="add_raster"))
    m_layer.addAction(_act(mw, "Add Delimited Text (CSV)...", mw.add_csv, icon_key="add_csv"))
    m_layer.addSeparator()
    m_layer.addAction(_act(mw, "Remove Selected Layer", mw.remove_layer, "Ctrl+D", icon_key="delete"))
    m_layer.addSeparator()
    m_layer.addAction(_act(mw, "Layer Properties...", mw.layer_properties, "F3", icon_key="identify"))

    # ── 5. Settings ───────────────────────────────────────────
    m_settings = mb.addMenu("&Settings")
    theme_menu = m_settings.addMenu("UI Theme")
    theme_menu.addAction(_act(mw, "Off-White Light Theme (Default)", lambda: mw.set_theme("offwhite")))
    theme_menu.addAction(_act(mw, "Dark GIS Theme", lambda: mw.set_theme("dark")))
    m_settings.addSeparator()
    m_settings.addAction(_act(mw, "Processing Settings & GPU Budget...", mw.open_processing_settings))
    m_settings.addAction(_act(mw, "Map CRS...", mw.set_project_crs))

    # ── 6. Plugins ────────────────────────────────────────────
    m_plugins = mb.addMenu("&Plugins")
    m_plugins.addAction(_act(mw, "Manage and Install Plugins...", mw.open_plugin_manager))
    m_plugins.addAction(_act(mw, "Python Console", mw.toggle_python_console, "Ctrl+Alt+P"))

    # ── 7. Vector ─────────────────────────────────────────────
    m_vector = mb.addMenu("&Vector")
    m_vector_geom = m_vector.addMenu("Geometry Tools")
    m_vector_geom.addAction(_act(mw, "Centroids", mw.run_centroids))
    m_vector_geom.addAction(_act(mw, "Convex Hull", mw.run_convex_hull))
    m_vector_geom.addAction(_act(mw, "Voronoi Polygons", mw.run_voronoi))
    m_vector_geom.addAction(_act(mw, "Buffer", mw.open_buffer_dialog))
    m_vector_geom.addAction(_act(mw, "Dissolve", mw.open_dissolve_dialog))

    m_vector_overlay = m_vector.addMenu("Overlay Tools")
    m_vector_overlay.addAction(_act(mw, "Clip", mw.open_clip_dialog, icon_key="clip"))
    m_vector_overlay.addAction(_act(mw, "Intersection", mw.open_intersect_dialog))
    m_vector_overlay.addAction(_act(mw, "Union", mw.open_union_dialog))
    m_vector_overlay.addAction(_act(mw, "Difference", mw.open_diff_dialog))

    m_vector.addSeparator()
    m_vector.addAction(_act(mw, "Open Attribute Table", mw.open_attribute_table, "F6"))
    m_vector.addAction(_act(mw, "Merge Vector Layers...", mw.run_merge, icon_key="merge"))
    m_vector.addSeparator()
    m_vector.addAction(_act(mw, "Transpose / Pivot Fields...", mw.open_transpose_fields_dialog, icon_key="transpose"))

    # ── 8. Raster ─────────────────────────────────────────────
    m_raster = mb.addMenu("&Raster")
    m_raster_terrain = m_raster.addMenu("Terrain Analysis")
    m_raster_terrain.addAction(_act(mw, "Calculate Slope...", mw.open_slope_dialog, icon_key="slope"))
    m_raster_terrain.addAction(_act(mw, "Calculate Aspect...", mw.open_aspect_dialog, icon_key="aspect"))
    m_raster_terrain.addAction(_act(mw, "3D Hillshade Relief...", mw.open_hillshade_dialog, icon_key="hillshade"))
    m_raster_terrain.addAction(_act(mw, "Roughness (TRI)...", mw.open_tri_dialog))
    m_raster_terrain.addAction(_act(mw, "Topographic Wetness Index (TWI)...", mw.open_twi_dialog, icon_key="watershed"))
    m_raster_terrain.addAction(_act(mw, "Generate Contours...", mw.open_contour_dialog))

    m_raster_hydro = m_raster.addMenu("Hydrology")
    m_raster_hydro.addAction(_act(mw, "Fill Sinks", mw.open_hydro_fillsinks))
    m_raster_hydro.addAction(_act(mw, "Flow Direction (D8)", mw.open_hydro_flowdir))
    m_raster_hydro.addAction(_act(mw, "Flow Accumulation", mw.open_hydro_flowaccum))
    m_raster_hydro.addAction(_act(mw, "Watershed Delineation", mw.open_hydro_watershed, icon_key="watershed"))

    m_raster.addSeparator()
    m_raster.addAction(_act(mw, "Raster Calculator...", mw.open_band_math_dialog))
    m_raster.addAction(_act(mw, "Raster Statistics...", mw.raster_stats))
    m_raster.addAction(_act(mw, "Crop / Clip Raster by Polygon Mask...", mw.open_crop_raster_dialog, icon_key="clip"))
    m_raster.addAction(_act(mw, "Reproject / Warp Raster...", mw.raster_reproject))
    m_raster.addSeparator()
    m_raster_blend = m_raster.addMenu("🎨 Layer Blend Mode")
    from core.elevation_styler import ElevationStyler
    BLEND_CATEGORIES = [
        ("Darken Group",  ["Normal", "Multiply", "Darken", "Color Burn"]),
        ("Lighten Group", ["Screen", "Lighten", "Color Dodge", "Linear Dodge"]),
        ("Contrast",      ["Overlay", "Hard Light", "Soft Light"]),
        ("Comparative",   ["Difference", "Exclusion"]),
    ]
    for cat_label, modes in BLEND_CATEGORIES:
        cat_hdr = m_raster_blend.addAction(f"— {cat_label} —")
        cat_hdr.setEnabled(False)
        for bmode in modes:
            m_raster_blend.addAction(
                _act(mw, bmode,
                     lambda checked=False, m=bmode: mw.apply_layer_blend_mode(m))
            )
        m_raster_blend.addSeparator()

    # ── 9. Satellite ──────────────────────────────────────────
    m_sat = mb.addMenu("&Satellite")
    m_sat_indices = m_sat.addMenu("Spectral Indices")
    m_sat_indices.addAction(_act(mw, "NDVI (Vegetation Index)", lambda: mw.open_spectral_index("satellite:ndvi")))
    m_sat_indices.addAction(_act(mw, "EVI (Enhanced Vegetation)", lambda: mw.open_spectral_index("satellite:evi")))
    m_sat_indices.addAction(_act(mw, "NDWI (Water Index)", lambda: mw.open_spectral_index("satellite:ndwi")))
    m_sat_indices.addAction(_act(mw, "NDBI (Built-up Index)", lambda: mw.open_spectral_index("satellite:ndbi")))
    m_sat_indices.addAction(_act(mw, "NBR (Burn Ratio)", lambda: mw.open_spectral_index("satellite:nbr")))
    m_sat_indices.addAction(_act(mw, "NDSI (Snow Index)", lambda: mw.open_spectral_index("satellite:ndsi")))

    m_sat_bands = m_sat.addMenu("Band Operations & Hyperspectral")
    m_sat_bands.addAction(_act(mw, "False Color RGB Composite...", mw.open_composite_dialog))
    m_sat_bands.addAction(_act(mw, "Band Stack Cube...", mw.open_band_stack_dialog))
    m_sat_bands.addAction(_act(mw, "Principal Component Analysis (PCA)...", mw.open_pca_dialog))
    m_sat_bands.addAction(_act(mw, "Spectral Angle Mapper (SAM)...", mw.open_sam_dialog))

    # ── 10. Terrain ───────────────────────────────────────────
    m_terrain = mb.addMenu("&Terrain")
    m_terrain.addAction(_act(mw, "Elevation Symbology & 3D Relief...", mw.open_dem_elevation_dialog, "Ctrl+Shift+E", icon_key="elevation"))
    m_terrain.addAction(_act(mw, "Calculate Slope...", mw.open_slope_dialog, icon_key="slope"))
    m_terrain.addAction(_act(mw, "Calculate Aspect...", mw.open_aspect_dialog, icon_key="aspect"))
    m_terrain.addAction(_act(mw, "3D Hillshade Relief...", mw.open_hillshade_dialog, icon_key="hillshade"))
    m_terrain.addSeparator()
    m_terrain.addAction(_act(mw, "Elevation Profile Tool", mw.open_elevation_profile, icon_key="profile"))
    m_terrain.addAction(_act(mw, "Viewshed Analysis...", mw.open_viewshed, icon_key="viewshed"))
    m_terrain.addAction(_act(mw, "Volumetric Analysis & Stage-Storage...", mw.open_volumetric_analysis, icon_key="profile"))
    m_terrain.addAction(_act(mw, "Cut & Fill Volume...", mw.open_cut_fill, icon_key="cut_fill"))
    m_terrain.addAction(_act(mw, "Watershed Basin Analysis...", mw.open_hydro_watershed, icon_key="watershed"))

    # ── 11. LiDAR ─────────────────────────────────────────────
    m_lidar = mb.addMenu("&LiDAR")
    m_lidar.addAction(_act(mw, "Load LAS / LAZ Point Cloud...", mw.load_las_file, icon_key="load_las"))
    m_lidar.addSeparator()
    m_lidar.addAction(_act(mw, "Classify Ground Points...", lambda: mw.processing_dock.open_algorithm("lidar:classify_ground"), icon_key="classify_ground"))
    m_lidar.addAction(_act(mw, "Classify Buildings...", lambda: mw.processing_dock.open_algorithm("lidar:classify_buildings"), icon_key="classify_buildings"))
    m_lidar.addAction(_act(mw, "Extract Building Planar Roofs...", lambda: mw.processing_dock.open_algorithm("lidar:extract_roofs")))
    m_lidar.addAction(_act(mw, "Classify Vegetation...", lambda: mw.processing_dock.open_algorithm("lidar:classify_veg"), icon_key="classify_veg"))
    m_lidar.addSeparator()
    m_lidar.addAction(_act(mw, "Classify Powerlines & Towers...", lambda: mw.processing_dock.open_algorithm("lidar:classify_powerlines")))
    m_lidar.addAction(_act(mw, "Vegetation Clearance & Danger Trees...", lambda: mw.processing_dock.open_algorithm("lidar:vegetation_clearance")))
    m_lidar.addSeparator()
    m_lidar.addAction(_act(mw, "Classify Road Surface (ASPRS 11)...", lambda: mw.processing_dock.open_algorithm("lidar:classify_roads")))
    m_lidar.addAction(_act(mw, "Extract Road Centerlines & Curbs...", lambda: mw.processing_dock.open_algorithm("lidar:road_centerline")))
    m_lidar.addAction(_act(mw, "Road Grade & Clearance Analysis...", lambda: mw.processing_dock.open_algorithm("lidar:road_condition")))
    m_lidar.addSeparator()
    m_lidar.addAction(_act(mw, "Density Thinning...", lambda: mw.processing_dock.open_algorithm("lidar:thinning"), icon_key="thin"))
    m_lidar.addAction(_act(mw, "Clip Point Cloud to Polygon...", lambda: mw.processing_dock.open_algorithm("lidar:clip"), icon_key="clip"))
    m_lidar.addSeparator()
    m_lidar.addAction(_act(mw, "Generate Bare-Earth DTM (TIN/IDW)...", lambda: mw.processing_dock.open_algorithm("lidar:generate_dtm")))
    m_lidar.addAction(_act(mw, "Canopy Height Model (CHM)...", lambda: mw.processing_dock.open_algorithm("lidar:chm")))
    m_lidar.addAction(_act(mw, "AGB & Carbon Stock Estimation...", lambda: mw.processing_dock.open_algorithm("forestry:carbon_stock")))
    m_lidar.addAction(_act(mw, "Point Cloud 3D Viewer...", mw.open_3d_viewer, icon_key="view_3d"))

    # ── 12. Processing ────────────────────────────────────────
    m_proc = mb.addMenu("&Processing")
    m_proc.addAction(_act(mw, "Processing Toolbox", mw.toggle_processing_dock, "Ctrl+Alt+T"))
    m_proc.addAction(_act(mw, "Recently Used Algorithms...", mw.show_recently_used))
    m_proc.addSeparator()
    m_proc.addAction(_act(mw, "GPU Acceleration Status & VRAM...", mw.open_gpu_status))

    # ── 13. 3D ────────────────────────────────────────────────
    m_3d = mb.addMenu("&3D")
    m_3d.addAction(_act(mw, "Open 3D Map Canvas...", mw.open_3d_viewer, icon_key="view_3d"))
    m_3d.addAction(_act(mw, "3D Elevation Mesh Draping...", mw.open_dem_elevation_dialog, icon_key="elevation"))

    # ── 14. Help ──────────────────────────────────────────────
    m_help = mb.addMenu("&Help")
    m_help.addAction(_act(mw, "Documentation", mw.open_docs))
    m_help.addAction(_act(mw, "About GeoStudio", mw.about))
