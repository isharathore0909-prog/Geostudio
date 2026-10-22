# -*- coding: utf-8 -*-
"""
GeoStudio / GeoAnalytica - Satellite & Hyperspectral Imagery Module
NDVI, EVI, SAVI, NDWI, NDBI, Band Math, Spectral Profiles,
False Color Composites, PCA, Hyperspectral band selection.
"""

from qgis.PyQt.QtWidgets import QWidget, QVBoxLayout, QMessageBox, QTabWidget, QListWidgetItem
from qgis.core import QgsProject, QgsMapLayer, QgsRasterBandStats
from core.style import MODULE_STYLE
from .satellite_indices import run_raster_calculation, apply_false_color_composite, run_pca as execute_pca
from .satellite_ui import build_indices_tab, build_bandmath_tab, build_composite_tab, build_hyperspectral_tab

STYLE = MODULE_STYLE


class SatelliteHyperspectralWidget(QWidget):
    """
    Satellite & Hyperspectral Analysis:
    - Spectral indices (NDVI, EVI, SAVI, NDWI, NDBI, NBR, NDSI)
    - Custom band math (raster calculator)
    - False color composite rendering
    - Spectral profile extraction & PCA
    """

    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.setStyleSheet(STYLE)
        self._init_ui()
        self._refresh_layers()
        QgsProject.instance().layersAdded.connect(self._refresh_layers)
        QgsProject.instance().layersRemoved.connect(self._refresh_layers)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        inner_tabs = QTabWidget()
        inner_tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #e2e8f0; background: #ffffff; border-radius: 4px; top: -1px; }
            QTabWidget::tab-bar { left: 6px; }
            QTabBar::tab { background: #f8fafc; color: #64748b; padding: 6px 14px; font-size: 11px; font-weight: 500; border: 1px solid #e2e8f0; border-top-left-radius: 4px; border-top-right-radius: 4px; margin-right: 4px; margin-top: 2px; }
            QTabBar::tab:selected { background: #ffffff; color: #0f172a; font-weight: bold; border-bottom: 1px solid #ffffff; margin-top: 0px; }
            QTabBar::tab:hover:!selected { background: #f1f5f9; color: #1e293b; }
        """)

        inner_tabs.addTab(build_indices_tab(self), "📊 Indices")
        inner_tabs.addTab(build_bandmath_tab(self), "∑ Band Math")
        inner_tabs.addTab(build_composite_tab(self), "🎨 Composite")
        inner_tabs.addTab(build_hyperspectral_tab(self), "🌈 Hyperspectral")

        layout.addWidget(inner_tabs)
        self.setLayout(layout)

    def _refresh_layers(self):
        rasters = [l for l in QgsProject.instance().mapLayers().values() if l.type() == QgsMapLayer.RasterLayer]
        for combo in (self.idx_raster_combo, self.bm_raster_combo, self.comp_raster_combo, self.hyp_raster_combo):
            current = combo.currentText()
            combo.clear()
            combo.addItem("-- None --", None)
            for l in rasters:
                combo.addItem(l.name(), l.id())
            idx = combo.findText(current)
            if idx >= 0:
                combo.setCurrentIndex(idx)

    def _update_index_bands(self):
        layer = self._get_raster(self.idx_raster_combo)
        if layer:
            n = layer.bandCount()
            for spin in (self.idx_nir_band, self.idx_red_band, self.idx_green_band, self.idx_swir1_band, self.idx_swir2_band):
                spin.setMaximum(n)

    def _get_raster(self, combo):
        layer_id = combo.currentData()
        return QgsProject.instance().mapLayer(layer_id) if layer_id else None

    def _load_band_list(self):
        layer = self._get_raster(self.hyp_raster_combo)
        if not layer:
            return
        self.band_list.clear()
        for b in range(1, layer.bandCount() + 1):
            stats = layer.dataProvider().bandStatistics(b, QgsRasterBandStats.Min | QgsRasterBandStats.Max | QgsRasterBandStats.Mean)
            item = QListWidgetItem(f"Band {b:3d}: {layer.bandName(b):<25} Min={stats.minimumValue:.3f} Max={stats.maximumValue:.3f} Mean={stats.mean:.3f}")
            self.band_list.addItem(item)

    def _raster_calc(self, formula, layer, output_name):
        res, err = run_raster_calculation(formula, layer, output_name)
        if err:
            QMessageBox.critical(self, "Raster Calc Error", err)
        elif self.iface:
            self.iface.messageBar().pushSuccess("GeoAnalytica", f"{output_name} computed!")
        return res

    def run_ndvi(self):
        layer = self._get_raster(self.idx_raster_combo)
        if not layer: return
        n, r, name = self.idx_nir_band.value(), self.idx_red_band.value(), layer.name()
        self.idx_progress.setValue(30)
        self._raster_calc(f'("{name}@{n}" - "{name}@{r}") / ("{name}@{n}" + "{name}@{r}")', layer, f"{name}_NDVI")
        self.idx_progress.setValue(100); self.idx_progress.setFormat("✓ NDVI done")

    def run_evi(self):
        layer = self._get_raster(self.idx_raster_combo)
        if not layer: return
        n, r, b, name = self.idx_nir_band.value(), self.idx_red_band.value(), 1, layer.name()
        self._raster_calc(f'2.5 * ("{name}@{n}" - "{name}@{r}") / ("{name}@{n}" + 6 * "{name}@{r}" - 7.5 * "{name}@{b}" + 1)', layer, f"{name}_EVI")

    def run_savi(self):
        layer = self._get_raster(self.idx_raster_combo)
        if not layer: return
        n, r, L, name = self.idx_nir_band.value(), self.idx_red_band.value(), self.savi_l.value(), layer.name()
        self._raster_calc(f'(("{name}@{n}" - "{name}@{r}") / ("{name}@{n}" + "{name}@{r}" + {L})) * (1 + {L})', layer, f"{name}_SAVI")

    def run_ndwi(self):
        layer = self._get_raster(self.idx_raster_combo)
        if not layer: return
        n, g, name = self.idx_nir_band.value(), self.idx_green_band.value(), layer.name()
        self._raster_calc(f'("{name}@{g}" - "{name}@{n}") / ("{name}@{g}" + "{name}@{n}")', layer, f"{name}_NDWI")

    def run_ndbi(self):
        layer = self._get_raster(self.idx_raster_combo)
        if not layer: return
        s1, n, name = self.idx_swir1_band.value(), self.idx_nir_band.value(), layer.name()
        self._raster_calc(f'("{name}@{s1}" - "{name}@{n}") / ("{name}@{s1}" + "{name}@{n}")', layer, f"{name}_NDBI")

    def run_nbr(self):
        layer = self._get_raster(self.idx_raster_combo)
        if not layer: return
        n, s2, name = self.idx_nir_band.value(), self.idx_swir2_band.value(), layer.name()
        self._raster_calc(f'("{name}@{n}" - "{name}@{s2}") / ("{name}@{n}" + "{name}@{s2}")', layer, f"{name}_NBR")

    def run_ndsi(self):
        layer = self._get_raster(self.idx_raster_combo)
        if not layer: return
        g, s1, name = self.idx_green_band.value(), self.idx_swir1_band.value(), layer.name()
        self._raster_calc(f'("{name}@{g}" - "{name}@{s1}") / ("{name}@{g}" + "{name}@{s1}")', layer, f"{name}_NDSI")

    def run_band_math(self):
        layer = self._get_raster(self.bm_raster_combo)
        formula = self.formula_edit.toPlainText().strip()
        name = self.bm_output_name.text().strip() or "band_math_result"
        if not layer or not formula:
            QMessageBox.warning(self, "Invalid Input", "Please provide a reference layer and formula.")
            return
        result = self._raster_calc(formula, layer, name)
        self.bm_log.append(f"{'✓ Success' if result else '✗ Failed'}: {name}\nFormula: {formula}\n")

    def _apply_preset(self, r, g, b):
        self.comp_r.setValue(r)
        self.comp_g.setValue(g)
        self.comp_b.setValue(b)

    def apply_composite(self):
        layer = self._get_raster(self.comp_raster_combo)
        ok, msg = apply_false_color_composite(layer, self.comp_r.value(), self.comp_g.value(), self.comp_b.value())
        if not ok:
            QMessageBox.warning(self, "Composite Error", msg)
        else:
            if self.iface:
                self.iface.mapCanvas().refresh()
                self.iface.messageBar().pushSuccess("GeoAnalytica", msg)

    def run_pca(self):
        layer = self._get_raster(self.hyp_raster_combo)
        res, msg = execute_pca(layer)
        self.hyp_log.append(msg + "\n")
        if res and self.iface:
            self.iface.messageBar().pushSuccess("GeoAnalytica", "PCA completed!")

    def show_mnf_info(self):
        QMessageBox.information(self, "MNF Transform", "Minimum Noise Fraction (MNF) transform requires Orfeo Toolbox (OTB) plugin.\n\nInstall OTB from https://www.orfeo-toolbox.org/.")

    def extract_spectral_profile(self):
        layer = self._get_raster(self.hyp_raster_combo)
        if not layer:
            QMessageBox.warning(self, "No Raster", "Select a hyperspectral raster."); return
        self.hyp_log.append("ℹ Use QGIS 'Identify Features' tool (Ctrl+Shift+I) on raster layer to inspect spectral response.\n")
        if self.iface and hasattr(self.iface, "actionIdentify"):
            self.iface.actionIdentify().trigger()

    def show_all_band_stats(self):
        layer = self._get_raster(self.hyp_raster_combo)
        if not layer:
            QMessageBox.warning(self, "No Raster", "Select a hyperspectral raster."); return
        self.hyp_log.clear()
        self.hyp_log.append(f"Band statistics for: {layer.name()}\n{'='*60}\n")
        for b in range(1, layer.bandCount() + 1):
            stats = layer.dataProvider().bandStatistics(b)
            self.hyp_log.append(f"Band {b:3d} | {layer.bandName(b):<20} | Min={stats.minimumValue:10.4f} Max={stats.maximumValue:10.4f} Mean={stats.mean:10.4f} Std={stats.stdDev:8.4f}\n")
        self.hyp_log.append(f"\nTotal bands: {layer.bandCount()}\n")
