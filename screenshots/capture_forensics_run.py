#!/usr/bin/env python3
"""Capture Forensics page WITH a real analysis result (populated screenshot)."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication

import stegonexus.gui.widgets as W

W.ok = W.warn = W.fail = lambda *a, **k: None

from stegonexus.gui.app import MainWindow

OUT = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(OUT)
DEMO = os.path.join(ROOT, "demo_output")


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(W.DARK)
    win = MainWindow(workspace=os.path.join(OUT, "_case_ws"))
    win.show()
    win.goto("forensics")
    fp = win.pages["forensics"]
    # run a REAL analysis: steghide stego JPEG, with the demo passphrase
    fp.file.set_path(os.path.join(DEMO, "cover_photo_stego.jpg"))
    fp.passwd.edit.setText("StegoNexus-Demo-Key-2026")
    fp.run()
    app.processEvents()
    win.resize(1380, 860)
    app.processEvents()
    pix = win.grab()
    pix.save(os.path.join(OUT, "02_forensics_run.png"))
    print("saved 02_forensics_run.png", pix.width(), pix.height())


if __name__ == "__main__":
    main()
