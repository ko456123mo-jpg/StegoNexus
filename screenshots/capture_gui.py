#!/usr/bin/env python3
"""
Capture the StegoNexus Dashboard (all pages) as PNG screenshots.
Run: QT_QPA_PLATFORM=offscreen python screenshots/capture_gui.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication

import stegonexus.gui.widgets as W

W.ok = W.warn = W.fail = lambda *a, **k: None     # silent dialogs in headless mode

from stegonexus.gui.app import MainWindow

OUT = os.path.dirname(os.path.abspath(__file__))
WS = os.path.join(OUT, "_case_ws")
DEMO = os.path.join(os.path.dirname(OUT), "demo_output")


def grab(win, key, name):
    win.goto(key)
    QApplication.processEvents()
    QApplication.processEvents()
    win.resize(1380, 860)
    QApplication.processEvents()
    pix = win.grab()
    path = os.path.join(OUT, name)
    pix.save(path)
    print("saved", name, pix.width(), "x", pix.height())


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(W.DARK)
    win = MainWindow(workspace=WS)
    win.show()

    # full suite on every page
    grab(win, "dashboard", "01_dashboard.png")
    grab(win, "forensics", "02_forensics.png")
    grab(win, "hashing", "03_hashing.png")
    grab(win, "text", "04_text_hiding.png")
    grab(win, "image", "05_image_hiding.png")
    grab(win, "audio", "06_audio_hiding.png")
    grab(win, "video", "07_video_hiding.png")
    grab(win, "network", "08_network_hiding.png")
    grab(win, "malware", "09_malware_lab.png")
    grab(win, "case", "11_case_management.png")
    print("GUI screenshots done.")


if __name__ == "__main__":
    main()
