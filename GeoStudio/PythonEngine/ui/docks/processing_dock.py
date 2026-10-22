# -*- coding: utf-8 -*-
"""
GeoStudio - Pure QGIS Processing Toolbox Dock Widget
Single hierarchical collapsible tree panel without horizontal tab strips.
"""

from PyQt5.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QTreeWidget, QTreeWidgetItem, QToolButton, QMessageBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor

from core.processing.algorithm_registry import AlgorithmRegistry, AlgorithmDefinition
from app.ui.runners.processing_launcher import launch_algorithm


class ProcessingToolboxTree(QWidget):
    """
    QGIS-Style Hierarchical Processing Tree Widget:
    - Real-time search filter
    - Hierarchical collapsible categories and subcategories
    - Recently used algorithms pinned at top
    - Double-click launches dedicated QGIS Algorithm Dialog
    """

    def __init__(self, map_canvas=None, main_window=None, parent=None):
        super().__init__(parent)
        self.map_canvas = map_canvas
        self.main_window = main_window
        self._recently_used = []
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        # Search & Filter Toolbar
        search_box = QHBoxLayout()
        search_box.setSpacing(4)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("🔎 Search algorithms...")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.setStyleSheet("QLineEdit { background: #ffffff; color: #0f172a; border: 1px solid #cbd5e1; border-radius: 4px; padding: 5px 8px; font-size: 11px; } QLineEdit:focus { border-color: #0f172a; }")
        self.search_edit.textChanged.connect(self._filter_tree)
        search_box.addWidget(self.search_edit)

        btn_expand = QToolButton()
        btn_expand.setText("➕")
        btn_expand.setToolTip("Expand All Categories")
        btn_expand.setStyleSheet("QToolButton { background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 4px; padding: 4px; } QToolButton:hover { background: #e2e8f0; }")
        btn_expand.clicked.connect(self.expand_all)
        search_box.addWidget(btn_expand)

        btn_collapse = QToolButton()
        btn_collapse.setText("➖")
        btn_collapse.setToolTip("Collapse All Categories")
        btn_collapse.setStyleSheet("QToolButton { background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 4px; padding: 4px; } QToolButton:hover { background: #e2e8f0; }")
        btn_collapse.clicked.connect(self.collapse_all)
        search_box.addWidget(btn_collapse)

        layout.addLayout(search_box)

        # QGIS Hierarchical Algorithm Tree
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setAnimated(True)
        self.tree.setIndentation(16)
        self.tree.setStyleSheet("""
            QTreeWidget { background: #ffffff; color: #0f172a; border: 1px solid #e2e8f0; border-radius: 4px; font-size: 11px; outline: none; selection-background-color: #e2e8f0; selection-color: #0f172a; }
            QTreeWidget::branch { background: transparent; }
            QTreeWidget::item { padding: 4px 6px; border-radius: 3px; }
            QTreeWidget::item:selected { background: #e2e8f0; color: #0f172a; font-weight: 600; }
            QTreeWidget::item:hover:!selected { background: #f8fafc; }
        """)
        self.tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.tree)

        all_algos = AlgorithmRegistry.get_all_algorithms()
        self.count_label = QLabel(f"Total: {len(all_algos)} algorithms available")
        self.count_label.setStyleSheet("color: #64748b; font-size: 10px; padding: 2px;")
        layout.addWidget(self.count_label)

        self._populate_tree()

    def _populate_tree(self):
        self.tree.clear()

        self.recent_group = QTreeWidgetItem(self.tree)
        self.recent_group.setText(0, "🕒 Recently Used")
        self.recent_group.setFont(0, QFont("Segoe UI", 9, QFont.Bold))
        self.recent_group.setForeground(0, QColor("#0f172a"))
        self.recent_group.setHidden(len(self._recently_used) == 0)

        for cat in AlgorithmRegistry.HIERARCHY:
            cat_item = QTreeWidgetItem(self.tree)
            total_cat_items = sum(len(sub["items"]) for sub in cat["subcategories"])
            cat_item.setText(0, f"{cat['category']} ({total_cat_items})")
            cat_item.setFont(0, QFont("Segoe UI", 9, QFont.Bold))
            cat_item.setForeground(0, QColor("#0f172a"))

            for sub in cat["subcategories"]:
                sub_item = QTreeWidgetItem(cat_item)
                sub_item.setText(0, f"📁 {sub['name']} ({len(sub['items'])})")
                sub_item.setFont(0, QFont("Segoe UI", 9, QFont.Bold))
                sub_item.setForeground(0, QColor("#0f172a"))

                for algo in sub["items"]:
                    item = QTreeWidgetItem(sub_item)
                    gpu_badge = "⚡ " if algo.supports_gpu else ""
                    item.setText(0, f"⚙  {algo.name} {gpu_badge}")
                    item.setToolTip(0, f"{algo.name}\n\n{algo.description}\nAlgorithm ID: {algo.algo_id}")
                    item.setData(0, Qt.UserRole, algo)

        self.tree.collapseAll()
        if self.tree.topLevelItemCount() > 1:
            self.tree.topLevelItem(1).setExpanded(True)

    def _filter_tree(self, text: str):
        query = text.strip().lower()
        total_visible = 0

        if not query:
            for i in range(self.tree.topLevelItemCount()):
                cat = self.tree.topLevelItem(i)
                cat.setHidden(len(self._recently_used) == 0 if cat == self.recent_group else False)
                for j in range(cat.childCount()):
                    sub = cat.child(j)
                    sub.setHidden(False)
                    for k in range(sub.childCount()):
                        sub.child(k).setHidden(False)
            all_algos = AlgorithmRegistry.get_all_algorithms()
            self.count_label.setText(f"Total: {len(all_algos)} algorithms available")
            return

        for i in range(self.tree.topLevelItemCount()):
            cat = self.tree.topLevelItem(i)
            cat_has_match = False
            for j in range(cat.childCount()):
                sub = cat.child(j)
                sub_has_match = False
                for k in range(sub.childCount()):
                    child = sub.child(k)
                    algo_data = child.data(0, Qt.UserRole)
                    if isinstance(algo_data, AlgorithmDefinition):
                        matches = query in algo_data.name.lower() or query in algo_data.description.lower() or query in algo_data.algo_id.lower()
                    else:
                        matches = query in child.text(0).lower()

                    child.setHidden(not matches)
                    if matches:
                        sub_has_match = True
                        cat_has_match = True
                        total_visible += 1

                sub.setHidden(not sub_has_match)
                if sub_has_match:
                    sub.setExpanded(True)

            cat.setHidden(not cat_has_match)
            if cat_has_match:
                cat.setExpanded(True)

        self.count_label.setText(f"Found: {total_visible} algorithms matching '{text}'")

    def expand_all(self):
        self.tree.expandAll()

    def collapse_all(self):
        self.tree.collapseAll()

    def _on_item_double_clicked(self, item, column):
        algo = item.data(0, Qt.UserRole)
        if not algo or not isinstance(algo, AlgorithmDefinition):
            item.setExpanded(not item.isExpanded())
            return
        self._add_to_recent(algo)
        self.launch_algorithm_dialog(algo)

    def _add_to_recent(self, algo: AlgorithmDefinition):
        self._recently_used = [r for r in self._recently_used if r.algo_id != algo.algo_id]
        self._recently_used.insert(0, algo)
        if len(self._recently_used) > 6:
            self._recently_used.pop()

        self.recent_group.takeChildren()
        self.recent_group.setHidden(False)
        self.recent_group.setText(0, f"🕒 Recently Used ({len(self._recently_used)})")

        for r_algo in self._recently_used:
            item = QTreeWidgetItem(self.recent_group)
            gpu_badge = "⚡ " if r_algo.supports_gpu else ""
            item.setText(0, f"⚙  {r_algo.name} {gpu_badge}")
            item.setToolTip(0, f"{r_algo.name}\n\n{r_algo.description}\nAlgorithm ID: {r_algo.algo_id}")
            item.setData(0, Qt.UserRole, r_algo)

        self.recent_group.setExpanded(True)

    def launch_algorithm_dialog(self, algo: AlgorithmDefinition):
        launch_algorithm(algo, map_canvas=self.map_canvas, main_window=self.main_window, parent=self)


class ProcessingDock(QDockWidget):
    """
    QGIS Processing Toolbox Dock Panel:
    - Pure hierarchical tree without horizontal tab strips
    - Real-time search filter
    - Bounded-RAM streaming and CUDA GPU execution
    """

    def __init__(self, map_canvas, parent=None):
        super().__init__("⚙ Processing Toolbox", parent)
        self.setObjectName("processing_dock")
        self.setMinimumWidth(320)
        self.setMaximumWidth(480)
        self.setAllowedAreas(Qt.RightDockWidgetArea | Qt.LeftDockWidgetArea)

        self.map_canvas = map_canvas
        self.main_window = parent

        self.tree_widget = ProcessingToolboxTree(
            map_canvas=self.map_canvas,
            main_window=self.main_window,
            parent=self
        )
        self.setWidget(self.tree_widget)

    def open_algorithm(self, algo_id_or_name: str):
        """Programmatically open an algorithm dialog by name or algorithm ID."""
        self.show()
        algo = AlgorithmRegistry.find_algorithm(algo_id_or_name)
        if algo:
            self.tree_widget.launch_algorithm_dialog(algo)
        else:
            for a in AlgorithmRegistry.get_all_algorithms():
                if algo_id_or_name.lower() in a.name.lower():
                    self.tree_widget.launch_algorithm_dialog(a)
                    return
            QMessageBox.warning(self, "Algorithm Not Found", f"Could not find algorithm '{algo_id_or_name}'.")

    def open_tab(self, tab_name: str):
        """Backward compatibility for menu actions."""
        self.show()
        tab_map = {
            "spatial": "native:buffer",
            "raster": "native:slope",
            "satellite": "satellite:ndvi",
            "io": "native:import_vector",
            "tools": "native:measure_dist"
        }
        target = tab_map.get(tab_name, "native:slope")
        self.open_algorithm(target)
