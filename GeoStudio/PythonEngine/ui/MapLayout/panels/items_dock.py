# -*- coding: utf-8 -*-
"""
GeoStudio - MapLayout Items Dock Panel
Manages items in the current layout:
- Item list with icons, visibility toggles, and lock indicators
- Z-order management (Bring Forward, Send Backward)
- Rename, delete, and duplicate items
"""

from PyQt5.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget,
    QTreeWidgetItem, QToolButton, QLabel, QMenu, QInputDialog, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QIcon, QFont, QColor

from resources.icons.icon_provider import get_icon


class LayoutItemsDock(QDockWidget):
    """Dock widget listing all items in the layout with Z-order & lock controls."""

    item_selected = pyqtSignal(object)  # QgsLayoutItem

    def __init__(self, layout_designer, parent=None):
        super().__init__("Items", parent or layout_designer)
        self.designer = layout_designer
        self.setObjectName("layout_items_dock")
        self.setMinimumWidth(220)
        self.setMaximumWidth(380)

        self._build_ui()

    def _build_ui(self):
        container = QWidget(self)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Toolbar for Items
        tb = QHBoxLayout()
        tb.setSpacing(2)

        btn_raise = QToolButton()
        btn_raise.setIcon(get_icon("zoom_next"))
        btn_raise.setToolTip("Raise Item (Bring Forward)")
        btn_raise.clicked.connect(self._raise_item)
        tb.addWidget(btn_raise)

        btn_lower = QToolButton()
        btn_lower.setIcon(get_icon("zoom_last"))
        btn_lower.setToolTip("Lower Item (Send Backward)")
        btn_lower.clicked.connect(self._lower_item)
        tb.addWidget(btn_lower)

        tb.addSpacing(6)

        btn_lock = QToolButton()
        btn_lock.setIcon(get_icon("edit"))
        btn_lock.setToolTip("Lock / Unlock Selected Item")
        btn_lock.clicked.connect(self._toggle_selected_lock)
        tb.addWidget(btn_lock)

        btn_del = QToolButton()
        btn_del.setIcon(get_icon("delete"))
        btn_del.setToolTip("Remove Selected Item")
        btn_del.clicked.connect(self._delete_item)
        tb.addWidget(btn_del)

        tb.addStretch()

        btn_refresh = QToolButton()
        btn_refresh.setIcon(get_icon("refresh"))
        btn_refresh.setToolTip("Refresh Items")
        btn_refresh.clicked.connect(self.refresh_items)
        tb.addWidget(btn_refresh)

        layout.addLayout(tb)

        # Items Tree
        self.tree = QTreeWidget(self)
        self.tree.setHeaderLabels(["Item", "Type", "ID"])
        self.tree.setColumnWidth(0, 140)
        self.tree.setColumnWidth(1, 80)
        self.tree.setAlternatingRowColors(True)
        self.tree.setSelectionMode(QTreeWidget.SingleSelection)
        self.tree.setStyleSheet("""
            QTreeWidget {
                border: 1px solid #cbd5e1;
                border-radius: 4px;
                background: #ffffff;
                font-size: 11px;
            }
            QTreeWidget::item:selected {
                background: #e0f2fe;
                color: #0369a1;
            }
        """)
        self.tree.itemSelectionChanged.connect(self._on_selection_changed)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)
        layout.addWidget(self.tree)

        self.setWidget(container)

    def refresh_items(self):
        """Populates tree widget with current layout items sorted by z-value (top to bottom)."""
        if not self.designer.layout:
            return

        self.tree.blockSignals(True)
        self.tree.clear()

        # Sort by z-value descending so topmost item appears first in tree
        items = list(self.designer.layout.items())
        items.sort(key=lambda it: it.zValue() if hasattr(it, "zValue") else 0, reverse=True)

        for item in items:
            name = item.id() if hasattr(item, "id") and item.id() else (item.displayName() if hasattr(item, "displayName") else type(item).__name__)
            item_type = type(item).__name__.replace("QgsLayoutItem", "")

            tree_item = QTreeWidgetItem([name, item_type, str(round(item.zValue(), 1)) if hasattr(item, "zValue") else ""])
            tree_item.setData(0, Qt.UserRole, item)

            is_locked = item.isLocked() if hasattr(item, "isLocked") else False
            if is_locked:
                tree_item.setForeground(0, QColor("#94a3b8"))
                tree_item.setText(0, f"🔒 {name}")

            self.tree.addTopLevelItem(tree_item)

            if hasattr(item, "isSelected") and item.isSelected():
                tree_item.setSelected(True)

        self.tree.blockSignals(False)

    def _get_selected_item(self):
        sel = self.tree.selectedItems()
        if sel:
            return sel[0].data(0, Qt.UserRole)
        return None

    def _on_selection_changed(self):
        item = self._get_selected_item()
        if item and self.designer.layout:
            self.designer.layout.setSelectedItem(item)
            self.item_selected.emit(item)

    def _raise_item(self):
        item = self._get_selected_item()
        if item and hasattr(item, "zValue"):
            item.setZValue(item.zValue() + 1.0)
            self.designer.view.update()
            self.refresh_items()

    def _lower_item(self):
        item = self._get_selected_item()
        if item and hasattr(item, "zValue"):
            item.setZValue(max(0.0, item.zValue() - 1.0))
            self.designer.view.update()
            self.refresh_items()

    def _toggle_selected_lock(self):
        item = self._get_selected_item()
        if item and hasattr(item, "setLocked"):
            cur = item.isLocked()
            item.setLocked(not cur)
            self.refresh_items()

    def _delete_item(self):
        item = self._get_selected_item()
        if item and self.designer.layout:
            self.designer.layout.removeLayoutItem(item)
            self.refresh_items()

    def _show_context_menu(self, pos):
        item = self._get_selected_item()
        if not item:
            return
        menu = QMenu(self)
        menu.addAction("Rename Item...", lambda: self._rename_item(item))
        menu.addSeparator()
        menu.addAction("Bring to Front", lambda: self._bring_to_front(item))
        menu.addAction("Send to Back", lambda: self._send_to_back(item))
        menu.addSeparator()
        lock_text = "Unlock Item" if (hasattr(item, "isLocked") and item.isLocked()) else "Lock Item"
        menu.addAction(lock_text, self._toggle_selected_lock)
        menu.addSeparator()
        menu.addAction("Delete Item", self._delete_item)
        menu.exec_(self.tree.mapToGlobal(pos))

    def _rename_item(self, item):
        curr_id = item.id() if hasattr(item, "id") else ""
        new_id, ok = QInputDialog.getText(self, "Rename Layout Item", "Item ID:", text=curr_id)
        if ok and new_id.strip() and hasattr(item, "setId"):
            item.setId(new_id.strip())
            self.refresh_items()

    def _bring_to_front(self, item):
        if hasattr(item, "zValue") and self.designer.layout:
            max_z = max([it.zValue() for it in self.designer.layout.items() if hasattr(it, "zValue")] or [0])
            item.setZValue(max_z + 1.0)
            self.designer.view.update()
            self.refresh_items()

    def _send_to_back(self, item):
        if hasattr(item, "zValue") and self.designer.layout:
            min_z = min([it.zValue() for it in self.designer.layout.items() if hasattr(it, "zValue")] or [0])
            item.setZValue(max(0.0, min_z - 1.0))
            self.designer.view.update()
            self.refresh_items()


__all__ = ["LayoutItemsDock"]
