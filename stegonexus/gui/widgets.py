"""Reusable Qt widgets for the StegoNexus Dashboard."""

from __future__ import annotations

import os
from typing import Callable, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPlainTextEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

DARK = """
QWidget { background: #0f1117; color: #e6e6e6; font-size: 13px; }
QGroupBox { border: 1px solid #2a2f3a; border-radius: 8px; margin-top: 10px;
            font-weight: bold; color: #00d98b; }
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }
QPushButton { background: #1c2430; border: 1px solid #2a2f3a; border-radius: 6px;
              padding: 7px 14px; font-weight: bold; }
QPushButton:hover { background: #243040; border-color: #00d98b; }
QPushButton#primary { background: #00d98b; color: #08130d; }
QPushButton#primary:hover { background: #12f0a0; }
QLineEdit, QPlainTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background: #141925; border: 1px solid #2a2f3a; border-radius: 6px; padding: 6px; }
QTableWidget { background: #141925; gridline-color: #2a2f3a;
               selection-background-color: #00d98b; selection-color: #08130d; }
QHeaderView::section { background: #1c2430; padding: 6px; border: none; }
QStatusBar { background: #0b0d12; color: #9aa4b5; }
QSplitter::handle { background: #2a2f3a; }
QTabBar::tab { background: #141925; padding: 8px 16px; border-top-left-radius: 6px;
               border-top-right-radius: 6px; }
QTabBar::tab:selected { background: #00d98b; color: #08130d; }
QListWidget { background: #141925; }
QListWidget::item { padding: 10px 14px; border-radius: 6px; }
QListWidget::item:selected { background: #00d98b; color: #08130d; }
QListWidget::item:hover { background: #243040; }
QScrollArea { border: none; }
"""


class FileRow(QWidget):
    """Label + line edit + browse button."""

    def __init__(self, title: str, mode: str = "open", parent=None):
        super().__init__(parent)
        self.mode = mode
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.edit = QLineEdit()
        self.edit.setPlaceholderText(title)
        btn = QPushButton("Browse…")
        btn.clicked.connect(self._browse)
        lay.addWidget(self.edit, 1)
        lay.addWidget(btn)

    def _browse(self):
        if self.mode == "save":
            path, _ = QFileDialog.getSaveFileName(self, "Save as")
        else:
            path, _ = QFileDialog.getOpenFileName(self, "Open file")
        if path:
            self.edit.setText(path)

    def path(self) -> str:
        return self.edit.text().strip()

    def set_path(self, p: str) -> None:
        self.edit.setText(p)


class KeyRow(QWidget):
    def __init__(self, title: str = "Key / Password", echo=False, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lab = QLabel(title + ":")
        self.edit = QLineEdit()
        self.edit.setEchoMode(QLineEdit.Password if echo else QLineEdit.Normal)
        lay.addWidget(lab)
        lay.addWidget(self.edit, 1)

    def text(self) -> str:
        return self.edit.text()


def group(title: str) -> QGroupBox:
    return QGroupBox(title)


def form(parent: QWidget) -> QFormLayout:
    f = QFormLayout(parent)
    f.setContentsMargins(12, 12, 12, 12)
    return f


def buttons(*specs) -> list:
    """specs: (text, callback, style or None)"""
    out = []
    for text, cb, style in specs:
        b = QPushButton(text)
        if style:
            b.setObjectName(style)
        b.clicked.connect(cb)
        out.append(b)
    return out


def ok(msg: str, title: str = "StegoNexus") -> None:
    QMessageBox.information(None, title, msg)


def warn(msg: str, title: str = "StegoNexus") -> None:
    QMessageBox.warning(None, title, msg)


def fail(msg: str) -> None:
    QMessageBox.critical(None, "StegoNexus - Error", msg)


def fill_table(table: QTableWidget, rows: list, headers: list) -> None:
    table.clear()
    table.setColumnCount(len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.setRowCount(len(rows))
    for r, row in enumerate(rows):
        for c, val in enumerate(row):
            item = QTableWidgetItem(str(val))
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            table.setItem(r, c, item)
    table.resizeColumnsToContents()
