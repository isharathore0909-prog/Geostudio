# -*- coding: utf-8 -*-
"""
GeoStudio - Vector Digitizing, Snapping & Editing Controller Mixin
"""
from PyQt5.QtWidgets import QMessageBox
from qgis.core import QgsMapLayer, QgsProject, QgsFeature, QgsSnappingConfig


class EditingControllerMixin:
    """Handles vector editing, undo/redo, feature geometry mutations, and snapping."""

    def undo_action(self):
        tool = self.map_canvas.canvas.mapTool() if self.map_canvas.canvas else None
        if tool and hasattr(tool, "undo_last_point") and tool.undo_last_point():
            self.geo_status.showMessage("Removed last vertex.", 2000)
            return

        layer = self.layer_panel.get_active_layer()
        if layer and hasattr(layer, "undoStack") and layer.undoStack():
            if layer.undoStack().canUndo():
                layer.undoStack().undo()
                self.map_canvas.refresh_canvas()
                self.geo_status.showMessage(f"Undo edit in '{layer.name()}'.", 2500)
                return

        for l in QgsProject.instance().mapLayers().values():
            if hasattr(l, "isEditable") and l.isEditable() and hasattr(l, "undoStack") and l.undoStack():
                if l.undoStack().canUndo():
                    l.undoStack().undo()
                    self.map_canvas.refresh_canvas()
                    self.geo_status.showMessage(f"Undo edit in '{l.name()}'.", 2500)
                    return

        self.geo_status.showMessage("Nothing to undo.", 2000)

    def redo_action(self):
        tool = self.map_canvas.canvas.mapTool() if self.map_canvas.canvas else None
        if tool and hasattr(tool, "redo_last_point") and tool.redo_last_point():
            self.geo_status.showMessage("Restored last point/vertex (Redo).", 2000)
            return

        layer = self.layer_panel.get_active_layer()
        if layer and hasattr(layer, "undoStack") and layer.undoStack():
            if layer.undoStack().canRedo():
                layer.undoStack().redo()
                self.map_canvas.refresh_canvas()
                self.geo_status.showMessage(f"Redo edit in '{layer.name()}'.", 2500)
                return

        for l in QgsProject.instance().mapLayers().values():
            if hasattr(l, "isEditable") and l.isEditable() and hasattr(l, "undoStack") and l.undoStack():
                if l.undoStack().canRedo():
                    l.undoStack().redo()
                    self.map_canvas.refresh_canvas()
                    self.geo_status.showMessage(f"Redo edit in '{l.name()}'.", 2500)
                    return

        self.geo_status.showMessage("Nothing to redo.", 2000)

    def cut_features(self):
        self.geo_status.showMessage("Cut feature", 2000)

    def copy_features(self):
        self.geo_status.showMessage("Copied features", 2000)

    def paste_features(self):
        self.geo_status.showMessage("Pasted features", 2000)

    def delete_selected(self):
        layer = self.layer_panel.get_active_layer()
        if not layer or layer.type() != QgsMapLayer.VectorLayer:
            self._info("Please select a vector layer first.")
            return
        selected_ids = list(layer.selectedFeatureIds())
        if not selected_ids:
            self.geo_status.showMessage("No features selected to delete.", 2000)
            return
        if not layer.isEditable():
            reply = QMessageBox.question(
                self, "Delete Features",
                f"Layer '{layer.name()}' is not in edit mode.\n"
                f"Start editing and delete {len(selected_ids)} selected feature(s)?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                layer.startEditing()
            else:
                return
        layer.deleteSelectedFeatures()
        self.map_canvas.refresh_canvas()
        self.geo_status.showMessage(f"Deleted {len(selected_ids)} selected feature(s).", 2500)

    def toggle_editing(self):
        layer = self.layer_panel.get_active_layer()
        if not layer or layer.type() != QgsMapLayer.VectorLayer:
            reply = QMessageBox.question(
                self, "Vector Editing",
                "Editing requires a vector layer (points, lines, polygons).\n"
                "The currently active layer is a raster/DEM or none is selected.\n\n"
                "Would you like to create a new editable vector layer to draw on?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self._create_vector_scratch_layer("Polygon")
            return

        if hasattr(layer, "isEditable") and hasattr(layer, "startEditing"):
            if layer.isEditable():
                layer.commitChanges()
                self.map_canvas.refresh_canvas()
                self.geo_status.showMessage(f"Committed changes for '{layer.name()}'.", 2500)
            else:
                layer.startEditing()
                self.map_canvas.refresh_canvas()
                self.geo_status.showMessage(f"Started editing for '{layer.name()}'.", 2500)
        else:
            self._info("Selected layer does not support direct vector editing.")

    def _create_vector_scratch_layer(self, geom_type="Polygon"):
        try:
            from qgis.core import QgsVectorLayer, QgsField
            dest_crs = self.map_canvas.canvas.mapSettings().destinationCrs()
            crs_str = dest_crs.authid() if dest_crs.isValid() else "EPSG:4326"
            layer_name = f"Digitized {geom_type}s"
            layer = QgsVectorLayer(f"{geom_type}?crs={crs_str}", layer_name, "memory")
            if layer.isValid():
                pr = layer.dataProvider()
                pr.addAttributes([QgsField("name")])
                layer.updateFields()
                QgsProject.instance().addMapLayer(layer)
                layer.startEditing()
                self.layer_panel.refresh()
                self.layer_panel.set_active_layer(layer)
                self.map_canvas.refresh_canvas()
                self.geo_status.showMessage(f"Created & started editing vector layer '{layer_name}'.", 3500)
                return layer
        except Exception as e:
            self._err(f"Could not create vector layer: {e}")
        return None

    def set_digitize_tool(self, tool_type: str):
        from tools.interactive_tools import GeoDigitizeTool
        tool = GeoDigitizeTool(self.map_canvas.canvas, self, tool_type=tool_type)
        self.map_canvas.canvas.setMapTool(tool)
        labels = {
            "point": "Add Point: Left-click on map to insert points.",
            "line": "Add Line: Left-click vertices. Right-click to complete line.",
            "polygon": "Add Polygon: Left-click vertices. Right-click to complete polygon.",
            "vertex": "Vertex Tool: Drag vertex to move. Del to delete vertex. Double-click edge to add vertex.",
            "split": "Split Feature: Draw a cut line crossing the feature. Right-click to split.",
            "move": "Move Feature: Click and drag feature to new position.",
            "rotate": "Rotate Feature: Click and drag to rotate feature around its center.",
        }
        msg = labels.get(tool_type, f"Digitizing Tool Active: {tool_type.capitalize()}")
        self.geo_status.showMessage(msg, 5000)

    def split_feature(self):
        self.set_digitize_tool("split")

    def merge_features(self):
        layer = self.layer_panel.get_active_layer()
        if not layer or layer.type() != QgsMapLayer.VectorLayer:
            self._info("Please select a vector layer with selected features to merge.")
            return
        selected = list(layer.selectedFeatures())
        if len(selected) < 2:
            self._info("Please select 2 or more features to merge.")
            return
        try:
            geoms = [f.geometry() for f in selected if f.geometry() and not f.geometry().isEmpty()]
            if not geoms:
                return
            merged_geom = geoms[0]
            for g in geoms[1:]:
                merged_geom = merged_geom.combine(g)

            if not layer.isEditable():
                layer.startEditing()

            first_feat = selected[0]
            new_feat = QgsFeature(layer.fields())
            for i in range(len(layer.fields())):
                new_feat.setAttribute(i, first_feat.attribute(i))
            new_feat.setGeometry(merged_geom)

            layer.addFeature(new_feat)
            layer.deleteSelectedFeatures()
            self.map_canvas.refresh_canvas()
            self.geo_status.showMessage(f"Merged {len(selected)} features into 1 new feature.", 3500)
        except Exception as e:
            self._err(f"Merge features error: {e}")

    def toggle_snapping(self):
        cfg = QgsProject.instance().snappingConfig()
        new_state = not cfg.enabled()
        cfg.setEnabled(new_state)
        QgsProject.instance().setSnappingConfig(cfg)
        st = "Enabled (Snaps to vertices & edges)" if new_state else "Disabled"
        self.geo_status.showMessage(f"Vector Snapping: {st}", 3000)

    def set_snapping_mode(self, mode: str):
        cfg = QgsProject.instance().snappingConfig()
        cfg.setEnabled(True)
        if mode == "vertex":
            cfg.setTypeFlag(QgsSnappingConfig.VertexFlag)
        elif mode == "segment":
            cfg.setTypeFlag(QgsSnappingConfig.SegmentFlag)
        elif mode == "area":
            cfg.setTypeFlag(QgsSnappingConfig.AreaFlag)
        QgsProject.instance().setSnappingConfig(cfg)
        self.geo_status.showMessage(f"Snapping Mode: Snap to {mode.capitalize()}", 3000)
