"""
StegoNexus Main Window — the unified Dashboard.
Run:  python -m stegonexus.gui            (or)  python run_gui.py
"""

from __future__ import annotations

import os
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QHBoxLayout, QLabel, QListWidget, QMainWindow, QMessageBox,
    QPushButton, QSplitter, QStackedWidget, QStatusBar, QVBoxLayout, QWidget,
)

from stegonexus import __version__, core
from stegonexus.case.manager import CaseManager
from stegonexus.gui import widgets as W
from stegonexus.gui.pages import (
    AudioHidingPage, CasePage, DashboardPage, ForensicsPage, HashingPage,
    ImageHidingPage, MalwarePage, NetworkHidingPage, TextHidingPage,
    VideoHidingPage,
)

WORKSPACE = os.path.join(os.path.expanduser("~"), "StegoNexus_Workspace")


class MainWindow(QMainWindow):
    def __init__(self, workspace: str = WORKSPACE):
        super().__init__()
        self.setWindowTitle(f"StegoNexus {__version__} — Unified Hiding, Extraction & "
                            "Forensics Framework")
        self.resize(1280, 820)
        os.makedirs(workspace, exist_ok=True)
        self.case_manager = CaseManager(workspace)

        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(8, 8, 8, 8)

        # ---- header -------------------------------------------------
        head = QHBoxLayout()
        title = QLabel("StegoNexus Dashboard")
        title.setStyleSheet("font-size:18px; font-weight:bold; color:#00d98b;")
        self.case_label = QLabel("Case: none")
        self.case_label.setStyleSheet("color:#ffd166; font-weight:bold;")
        self.ws_label = QLabel("Workspace: " + workspace)
        self.ws_label.setStyleSheet("color:#9aa4b5;")
        head.addWidget(title)
        head.addSpacing(24)
        head.addWidget(self.case_label)
        head.addStretch(1)
        head.addWidget(self.ws_label)
        root.addLayout(head)

        # ---- split: nav + stack ------------------------------------
        split = QSplitter(Qt.Horizontal)
        self.nav = QListWidget()
        self.nav.setFixedWidth(230)
        NAV = [
            ("Dashboard", "dashboard", DashboardPage),
            ("Forensics & Analysis", "forensics", ForensicsPage),
            ("Hashing & Integrity", "hashing", HashingPage),
            ("Text Hiding — LSB + Key", "text", TextHidingPage),
            ("Image Hiding — Steghide/CyberHide", "image", ImageHidingPage),
            ("Audio Hiding", "audio", AudioHidingPage),
            ("Video Hiding — VideoHide", "video", VideoHidingPage),
            ("Network Hiding — Covert", "network", NetworkHidingPage),
            ("Malware Hiding & Evasion Lab", "malware", MalwarePage),
            ("Case Management & Reports", "case", CasePage),
        ]
        self.stack = QStackedWidget()
        self.pages: dict[str, object] = {}
        for label, key, cls in NAV:
            self.nav.addItem(label)
            page = cls(self)
            self.pages[key] = page
            self.stack.addWidget(page)
        self.nav.currentRowChanged.connect(self._on_nav)
        split.addWidget(self.nav)
        split.addWidget(self.stack)
        split.setSizes([230, 1050])
        root.addWidget(split, 1)
        self.setCentralWidget(central)

        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self._refresh_status()
        self.nav.setCurrentRow(0)

    # ------------------------------------------------------------------ #
    def process(self):
        QApplication.processEvents()

    def goto(self, key: str):
        idx = list(self.pages.keys()).index(key)
        self.nav.setCurrentRow(idx)
        self.stack.setCurrentIndex(idx)
        self._refresh_page(self.pages[key])

    def _on_nav(self, row: int):
        self.stack.setCurrentIndex(row)
        self._refresh_page(list(self.pages.values())[row])

    def _refresh_page(self, page):
        if hasattr(page, "refresh"):
            page.refresh()
        c = self.case_manager.case
        self.case_label.setText(
            f"Case: {c['case_id']} — {c['title']} ({c['status']})" if c
            else "Case: none (create one in Case Management)")

    def _refresh_status(self):
        st = core.forensics.tool_status()
        kalis = {k: v for k, v in st.items() if v == "INSTALLED"}
        self.status.showMessage(
            f"StegoNexus {__version__}  |  external tools on this host: "
            f"{', '.join(kalis) or 'none (built-in fallbacks active)'}  |  "
            f"prepared & developed by Mohammed Moneer Al-absi")


def main() -> int:
    from PySide6.QtGui import QFont
    app = QApplication(sys.argv)
    app.setStyleSheet(W.DARK)
    app.setFont(QFont("DejaVu Sans", 10))
    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
