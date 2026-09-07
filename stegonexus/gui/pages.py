"""StegoNexus Dashboard pages (one per project module)."""

from __future__ import annotations

import json
import os
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QComboBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QPlainTextEdit, QPushButton, QScrollArea, QSpinBox, QSplitter,
    QTabWidget, QTableWidget, QVBoxLayout, QWidget,
)

from stegonexus import core
from stegonexus.gui import widgets as W


class Page(QWidget):
    title = "Page"

    def __init__(self, app):
        super().__init__()
        self.app = app
        self.case = app.case_manager
        self._build()

    def build(self):  # override
        pass

    def _build(self):
        self.build()
        self.setLayout(self._layout)

    def record(self, module: str, action: str, result: dict):
        if self.case.case:
            self.case.record_operation(module, action, result)
        return result

    def finding(self, category, summary, details=None, severity="INFO"):
        if self.case.case:
            self.case.add_finding(category, summary, details, severity)


# ----------------------------------------------------------------------- #
# 01 Dashboard
# ----------------------------------------------------------------------- #
class DashboardPage(Page):
    title = "Dashboard"

    def build(self):
        self._layout = QVBoxLayout(self)
        head = QLabel("StegoNexus — Unified Hiding, Extraction & Forensics Framework")
        head.setStyleSheet("font-size:22px; font-weight:bold; color:#00d98b;")
        sub = QLabel("Dashboard | Forensics & Analysis | Hashing & Integrity | "
                     "Text LSB · Image · Audio · Video · Network Hiding | "
                     "Malware Evasion Lab | Case Management")
        sub.setWordWrap(True)
        self._layout.addWidget(head)
        self._layout.addWidget(sub)

        grid = QHBoxLayout()
        self.tools = QTableWidget()
        W.fill_table(self.tools, [], ["External Tool", "Status", "Fallback"])
        grid.addWidget(self.tools, 1)
        side = QVBoxLayout()
        side.addWidget(W.group("Modules"))
        for name, page in [("Text Hiding (LSB + Key)", "text"),
                           ("Image Hiding (Steghide / CyberHide)", "image"),
                           ("Audio Hiding (LSB/Phase/SS/Metadata)", "audio"),
                           ("Video Hiding (VideoHide)", "video"),
                           ("Network Hiding (Covert)", "network"),
                           ("Forensics & Analysis", "forensics"),
                           ("Hashing & Integrity", "hashing"),
                           ("Malware Lab (Evasion)", "malware"),
                           ("Case Management & Reports", "case")]:
            b = QPushButton(name)
            b.clicked.connect(lambda _=False, p=page: self.app.goto(p))
            side.addWidget(b)
        side.addStretch(1)
        grid.addLayout(side, 1)
        self._layout.addLayout(grid)

    def refresh(self):
        st = core.forensics.tool_status()
        rows = []
        fallbacks = {
            "steghide": "CyberHide AES-LSB (built-in)",
            "zsteg": "built-in LSB analyser",
            "binwalk": "built-in signature scan",
            "foremost": "built-in carver",
            "exiftool": "Pillow metadata",
        }
        for tool, status in st.items():
            rows.append([tool, status, fallbacks.get(tool, "built-in")])
        W.fill_table(self.tools, rows, ["External Tool", "Status", "Fallback"])


# ----------------------------------------------------------------------- #
# 02 Forensics & Analysis
# ----------------------------------------------------------------------- #
class ForensicsPage(Page):
    title = "Forensics & Analysis"

    def build(self):
        self._layout = QVBoxLayout(self)
        box = W.group("Target file (optional Password enables steghide confirmation)")
        lay = QHBoxLayout(box)
        self.file = W.FileRow("Select a file to analyse (any type)")
        self.passwd = W.KeyRow("Password (optional)", echo=True)
        self.win = QSpinBox(); self.win.setValue(1024); self.win.setRange(256, 65536)
        self.win.setSuffix(" B window")
        self.thr = QSpinBox(); self.thr.setValue(75); self.thr.setRange(10, 100)
        self.thr.setSuffix(" entropy x10")
        run = QPushButton("Run Full Analysis"); run.setObjectName("primary")
        run.clicked.connect(self.run)
        save = QPushButton("Save Finding to Case")
        save.clicked.connect(self.save_finding)
        lay.addWidget(self.file, 1)
        lay.addWidget(self.win); lay.addWidget(self.thr)
        lay.addWidget(run); lay.addWidget(save)
        self._layout.addWidget(box)
        self.passwdRow = QWidget()
        pwl = QHBoxLayout(self.passwdRow)
        pwl.setContentsMargins(0, 0, 0, 0)
        pwl.addWidget(self.passwd)
        self._layout.addWidget(self.passwdRow)

        self.tree = QPlainTextEdit()
        self.tree.setReadOnly(True)
        self.tree.setPlaceholderText("Results of: file | strings | exiftool | binwalk | "
                                     "steghide info | foremost | zsteg | Shannon Entropy")
        self._layout.addWidget(self.tree, 1)
        self._last = None

    def run(self):
        p = self.file.path()
        if not p or not os.path.exists(p):
            W.warn("Choose an existing file first.")
            return
        self.tree.setPlainText("Analysing…")
        self.app.process()
        pw = self.passwd.text() or None
        try:
            r = core.forensics.aggregate(p, self.win.value(), self.thr.value() / 10,
                                         steghide_passphrase=pw)
        except Exception as exc:
            W.fail(str(exc)); return
        self._last = r
        lines = [
            f"FILE      : {r['file']}  ({r['size_bytes']} bytes)",
            f"TYPE      : {r['file_info'].get('description')}",
            f"ENTROPY   : overall {r['entropy']['overall_entropy']} bits/byte | "
            f"suspicious regions: {r['entropy']['suspicious_count']}"
            f" (window {self.win.value()})",
            f"STRINGS   : {r['strings'].get('count')} printable strings",
            f"MARKERS   : {json.dumps(r['interesting_strings'], ensure_ascii=False)[:600]}",
            f"METADATA  : {str(r['metadata'].get('metadata'))[:500]}",
            f"BINWALK   : {json.dumps(r['binwalk'].get('results'), ensure_ascii=False)[:500]}",
            f"CARVING   : {json.dumps(r['carving'].get('results'), ensure_ascii=False)[:400]}",
            f"ZSTEG     : {r['zsteg'].get('verdict')}",
            f"STEGHIDE  : {r['steghide_info'].get('verdict')}",
            "",
            "=" * 60,
            "VERDICT   : " + r["verdict"],
            "=" * 60,
        ]
        for note in r.get("notes", []):
            lines.append("NOTE      : " + note)
        if r.get("entropy", {}).get("suspicious_regions"):
            lines.append("Suspicious high-entropy regions:")
            for s in r["entropy"]["suspicious_regions"][:20]:
                lines.append(f"   offset {s['offset']:>9}  H={s['entropy']}")
        if r.get("binwalk", {}).get("results"):
            lines.append("binwalk / signature findings:")
            for f in r["binwalk"]["results"][:20]:
                lines.append(f"   {f}")
        self.tree.setPlainText("\n".join(lines))
        self.record("forensics", "aggregate", {"file": p, "verdict": r["verdict"]})

    def save_finding(self):
        if self._last:
            self.finding("forensics", self._last["verdict"],
                         {"file": self._last["file"],
                          "entropy": self._last["entropy"]["overall_entropy"]},
                         "HIGH" if "SUSPICIOUS" in self._last["verdict"] else "INFO")
            W.ok("Finding saved to the active case.")


# ----------------------------------------------------------------------- #
# 03 Hashing & Integrity
# ----------------------------------------------------------------------- #
class HashingPage(Page):
    title = "Hashing & Integrity"

    def build(self):
        self._layout = QVBoxLayout(self)
        top = QHBoxLayout()
        box = W.group("File hashes (MD5 · SHA-1 · SHA-256 · SHA-512)")
        lay = QHBoxLayout(box)
        self.file = W.FileRow("Select a file")
        b = QPushButton("Hash"); b.setObjectName("primary"); b.clicked.connect(self.run)
        lay.addWidget(self.file, 1); lay.addWidget(b)
        top.addWidget(box, 3)
        box2 = W.group("Integrity compare")
        lay2 = QHBoxLayout(box2)
        self.a = W.FileRow("File A"); self.b = W.FileRow("File B")
        c = QPushButton("Compare"); c.clicked.connect(self.compare)
        lay2.addWidget(self.a); lay2.addWidget(self.b); lay2.addWidget(c)
        top.addWidget(box2, 3)
        self._layout.addLayout(top)
        self.table = QTableWidget()
        self._layout.addWidget(self.table, 1)
        self.cmp = QPlainTextEdit(); self.cmp.setMaximumHeight(120); self.cmp.setReadOnly(True)
        self._layout.addWidget(self.cmp)

    def run(self):
        p = self.file.path()
        if not p or not os.path.exists(p):
            W.warn("Choose a file first."); return
        try:
            res = core.hashing.hash_file(p)
        except Exception as exc:
            W.fail(str(exc)); return
        W.fill_table(self.table,
                     [[r.algorithm, r.digest, r.target] for r in res],
                     ["Algorithm", "Digest", "Target"])
        self.record("hashing", "hash", {"file": p,
                                        "sha256": res[2].digest if len(res) > 2 else ""})

    def compare(self):
        a, b = self.a.path(), self.b.path()
        if not (os.path.exists(a) and os.path.exists(b)):
            W.warn("Choose both files."); return
        try:
            r = core.hashing.compare_files(a, b)
        except Exception as exc:
            W.fail(str(exc)); return
        self.cmp.setPlainText(
            f"decision : {r['decision']}\n"
            f"A digest : {r['file_a']['digest']}\n"
            f"B digest : {r['file_b']['digest']}")
        self.finding("integrity", r["decision"],
                     {"file_a": a, "file_b": b, "algorithm": r["algorithm"]},
                     "INFO" if r["identical"] else "HIGH")


# ----------------------------------------------------------------------- #
# 04 Text Hiding
# ----------------------------------------------------------------------- #
class TextHidingPage(Page):
    title = "Text Hiding (LSB + Key)"

    def build(self):
        self._layout = QVBoxLayout(self)
        tabs = QTabWidget()
        self._layout.addWidget(tabs, 1)

        # hide
        hide = QWidget(); h = QVBoxLayout(hide)
        self.cover = QPlainTextEdit(); self.cover.setPlaceholderText(
            "Cover text (the innocent carrier). Enough length needed: ~8 carriers per byte of secret.")
        self.secret = QPlainTextEdit(); self.secret.setMaximumHeight(110)
        self.secret.setPlaceholderText("Secret message (hidden inside the cover)")
        self.key = W.KeyRow("Key")
        row = QHBoxLayout()
        save_out = QPushButton("Hide → Stego Text"); save_out.setObjectName("primary")
        save_out.clicked.connect(self.do_hide)
        save_file = QPushButton("Hide → save to file...")
        save_file.clicked.connect(self.do_hide_file)
        row.addWidget(save_out); row.addWidget(save_file)
        self.result = QPlainTextEdit(); self.result.setReadOnly(True)
        h.addWidget(QLabel("Cover text:")); h.addWidget(self.cover, 1)
        h.addWidget(QLabel("Secret message:")); h.addWidget(self.secret)
        h.addWidget(self.key); h.addLayout(row)
        h.addWidget(QLabel("Stego text output:")); h.addWidget(self.result, 1)
        tabs.addTab(hide, "Hide")

        # reveal
        reveal = QWidget(); r = QVBoxLayout(reveal)
        self.stego = QPlainTextEdit(); self.stego.setPlaceholderText(
            "Paste the stego text (LSB carriers preserved)")
        self.rkey = W.KeyRow("Key")
        run = QPushButton("Extract Secret"); run.setObjectName("primary")
        run.clicked.connect(self.do_reveal)
        self.msg = QPlainTextEdit(); self.msg.setReadOnly(True)
        r.addWidget(QLabel("Stego text:")); r.addWidget(self.stego, 1)
        r.addWidget(self.rkey); r.addWidget(run)
        r.addWidget(QLabel("Recovered secret message:")); r.addWidget(self.msg, 1)
        tabs.addTab(reveal, "Extract")

    def do_hide(self):
        cover, secret, key = self.cover.toPlainText(), self.secret.toPlainText(), self.key.text()
        try:
            stego, meta = core.text_hiding.encode(cover, secret, key)
        except Exception as exc:
            W.fail(str(exc)); return
        self.result.setPlainText(stego)
        self.record("text-lsb", "hide", meta)
        W.ok(f"Hidden! Secret: {meta['secret_bytes']} B → payload "
             f"{meta['payload_bits']} bits in {meta['cover_chars']} cover chars.")

    def do_hide_file(self):
        from PySide6.QtWidgets import QFileDialog
        cover = self.cover.toPlainText()
        secret = self.secret.toPlainText()
        try:
            stego, meta = core.text_hiding.encode(cover, secret, self.key.text())
        except Exception as exc:
            W.fail(str(exc)); return
        path, _ = QFileDialog.getSaveFileName(self, "Save stego text", "stego_text.txt")
        if path:
            open(path, "w", encoding="utf-8").write(stego)
            self.result.setPlainText(stego)
            self.record("text-lsb", "hide", meta | {"saved": path})
            W.ok("Stego text saved to " + path)

    def do_reveal(self):
        try:
            secret, meta = core.text_hiding.decode(self.stego.toPlainText(), self.rkey.text())
        except Exception as exc:
            W.fail(str(exc)); return
        self.msg.setPlainText(secret)
        self.record("text-lsb", "extract", meta)
        W.ok("Secret recovered:\n\n" + secret)


# ----------------------------------------------------------------------- #
# 05 Image Hiding
# ----------------------------------------------------------------------- #
class ImageHidingPage(Page):
    title = "Image Hiding (Steghide / CyberHide)"

    def build(self):
        self._layout = QVBoxLayout(self)
        tabs = QTabWidget(); self._layout.addWidget(tabs, 1)
        self.result = QPlainTextEdit(); self.result.setReadOnly(True)

        # hide
        hide = QWidget(); h = QVBoxLayout(hide)
        self.cover = W.FileRow("Cover image (JPG for steghide / PNG for CyberHide)")
        self.secret = W.FileRow("Secret file to hide")
        self.passwd = W.KeyRow("Password", echo=True)
        self.out = W.FileRow("Output stego image", mode="save")
        b = QPushButton("Hide"); b.setObjectName("primary"); b.clicked.connect(self.do_hide)
        h.addWidget(self.cover); h.addWidget(self.secret); h.addWidget(self.passwd)
        h.addWidget(self.out); h.addWidget(b); h.addWidget(self.result, 1)
        tabs.addTab(hide, "Hide")

        # extract
        ex = QWidget(); e = QVBoxLayout(ex)
        self.stego = W.FileRow("Stego image")
        self.epass = W.KeyRow("Password", echo=True)
        self.edir = W.FileRow("Output directory", mode="save")
        b2 = QPushButton("Extract"); b2.setObjectName("primary"); b2.clicked.connect(self.do_extract)
        self.res2 = QPlainTextEdit(); self.res2.setReadOnly(True)
        e.addWidget(self.stego); e.addWidget(self.epass); e.addWidget(self.edir)
        e.addWidget(b2); e.addWidget(self.res2, 1)
        tabs.addTab(ex, "Extract")

        # probe / forensics
        pr = QWidget(); p = QVBoxLayout(pr)
        self.probe_in = W.FileRow("Image to inspect for hidden data")
        self.probe_pass = W.KeyRow("Password (optional — confirms steghide/payload)", echo=True)
        b3 = QPushButton("Probe (steghide info / zsteg-style)"); b3.setObjectName("primary")
        b3.clicked.connect(self.do_probe)
        self.res3 = QPlainTextEdit(); self.res3.setReadOnly(True)
        p.addWidget(self.probe_in); p.addWidget(self.probe_pass)
        p.addWidget(b3); p.addWidget(self.res3, 1)
        tabs.addTab(pr, "Probe / Info")

    def do_hide(self):
        cover, secret, pw = self.cover.path(), self.secret.path(), self.passwd.text()
        out = self.out.path() or None
        try:
            r = core.image_steghide.embed(cover, secret, pw, out)
        except Exception as exc:
            try:
                r = core.image_stego.embed_cyberhide(cover, secret, pw, out)
            except Exception as exc2:
                W.fail(str(exc2)); return
        self.result.setPlainText(json.dumps(r, indent=2, ensure_ascii=False))
        self.record("image-hiding", "embed", r)
        W.ok("Stego image created:\n" + str(r.get("stego_image", r.get("out"))))

    def do_extract(self):
        try:
            r = core.image_steghide.extract(self.stego.path(), self.epass.text(),
                                            self.edir.path() or None)
        except Exception:
            try:
                r = core.image_stego.extract_cyberhide(self.stego.path(),
                                                       self.epass.text(),
                                                       self.edir.path() or None)
            except Exception as exc:
                W.fail(str(exc)); return
        self.res2.setPlainText(json.dumps(r, indent=2, ensure_ascii=False))
        self.record("image-hiding", "extract", r)
        W.ok("Secret extracted:\n" + str(r.get("secret_file")))

    def do_probe(self):
        p = self.probe_in.path()
        if not os.path.exists(p):
            W.warn("Choose an image first."); return
        pw = self.probe_pass.text() or None
        results = {}
        try:
            results["steghide"] = core.image_steghide.info(p, passphrase=pw)
        except Exception as exc:
            results["steghide"] = {"error": str(exc)}
        results["cyberhide_lsb"] = core.image_stego.probe_cyberhide(p)
        self.res3.setPlainText(json.dumps(results, indent=2, ensure_ascii=False))
        verdicts = [r.get("verdict", "") for r in results.values()]
        verdict = "; ".join(v for v in verdicts if v)
        self.finding("image-probe", verdict, results)
        self.record("image-hiding", "probe", results)


# ----------------------------------------------------------------------- #
# 06 Audio Hiding
# ----------------------------------------------------------------------- #
class AudioHidingPage(Page):
    title = "Audio Hiding"

    def build(self):
        self._layout = QVBoxLayout(self)
        tabs = QTabWidget(); self._layout.addWidget(tabs, 1)

        hide = QWidget(); h = QVBoxLayout(hide)
        self.method = QComboBox()
        self.method.addItems(["LSB (keyed permutation)", "Phase Coding",
                              "Spread Spectrum", "Metadata (RIFF-INFO)"])
        self.cover = W.FileRow("Cover WAV audio")
        self.secret = W.FileRow("Secret file")
        self.key = W.KeyRow("Key", echo=True)
        b = QPushButton("Hide"); b.setObjectName("primary"); b.clicked.connect(self.do_hide)
        self.res = QPlainTextEdit(); self.res.setReadOnly(True)
        h.addWidget(QLabel("Method:")); h.addWidget(self.method)
        h.addWidget(self.cover); h.addWidget(self.secret); h.addWidget(self.key)
        h.addWidget(b); h.addWidget(self.res, 1)
        tabs.addTab(hide, "Hide")

        ex = QWidget(); e = QVBoxLayout(ex)
        self.estego = W.FileRow("Stego WAV")
        self.emethod = QComboBox()
        self.emethod.addItems(["LSB (keyed permutation)", "Phase Coding",
                               "Spread Spectrum", "Metadata (RIFF-INFO)"])
        self.ekey = W.KeyRow("Key", echo=True)
        b2 = QPushButton("Extract"); b2.setObjectName("primary"); b2.clicked.connect(self.do_extract)
        self.eres = QPlainTextEdit(); self.eres.setReadOnly(True)
        e.addWidget(QLabel("Method:")); e.addWidget(self.emethod)
        e.addWidget(self.estego); e.addWidget(self.ekey); e.addWidget(b2)
        e.addWidget(self.eres, 1)
        tabs.addTab(ex, "Extract")

        an = QWidget(); a = QVBoxLayout(an)
        self.afile = W.FileRow("Audio to analyse")
        b3 = QPushButton("Analyse + Spectrogram"); b3.setObjectName("primary")
        b3.clicked.connect(self.do_analyze)
        self.aout = QPlainTextEdit(); self.aout.setReadOnly(True)
        self.spec = QLabel("(spectrogram PNG will be saved next to the audio file)")
        self.spec.setAlignment(Qt.AlignCenter)
        a.addWidget(self.afile); a.addWidget(b3); a.addWidget(self.aout)
        a.addWidget(self.spec, 1)
        tabs.addTab(an, "Analyse")

    def _method(self, combo, hide_kind=False):
        m = combo.currentIndex()
        return ["lsb", "phase", "ss", "meta"][m]

    def do_hide(self):
        try:
            m = self._method(self.method)
            if m == "lsb":
                r = core.audio_hiding.lsb_embed(self.cover.path(), self.secret.path(),
                                                self.key.text())
            elif m == "phase":
                r = core.audio_hiding.phase_embed(self.cover.path(), self.secret.path(),
                                                  self.key.text())
            elif m == "ss":
                r = core.audio_hiding.ss_embed(self.cover.path(), self.secret.path(),
                                               self.key.text())
            else:
                r = core.audio_hiding.meta_embed(self.cover.path(), self.secret.path(),
                                                 self.key.text())
        except Exception as exc:
            W.fail(str(exc)); return
        self.res.setPlainText(json.dumps(r, indent=2, ensure_ascii=False))
        self.record("audio-hiding", "embed", r)

    def do_extract(self):
        try:
            m = self._method(self.emethod)
            if m == "lsb":
                r = core.audio_hiding.lsb_extract(self.estego.path(), self.ekey.text())
            elif m == "phase":
                r = core.audio_hiding.phase_extract(self.estego.path(), self.ekey.text())
            elif m == "ss":
                r = core.audio_hiding.ss_extract(self.estego.path(), self.ekey.text())
            else:
                r = core.audio_hiding.meta_extract(self.estego.path(), self.ekey.text())
        except Exception as exc:
            W.fail(str(exc)); return
        self.eres.setPlainText(json.dumps(r, indent=2, ensure_ascii=False))
        self.record("audio-hiding", "extract", r)

    def do_analyze(self):
        p = self.afile.path()
        if not os.path.exists(p):
            W.warn("Choose an audio file."); return
        try:
            r = core.audio_hiding.analyze(p)
            d = os.path.dirname(os.path.abspath(p))
            base = os.path.splitext(os.path.basename(p))[0]
            spec = os.path.join(d, base + "_spectrogram.png")
            wave = os.path.join(d, base + "_waveform.png")
            core.audio_hiding.make_spectrogram(p, spec)
            core.audio_hiding.make_waveform(p, wave)
            r["spectrogram"] = spec
        except Exception as exc:
            W.fail(str(exc)); return
        lines = [f"{k:<18}: {v}" for k, v in r.items()]
        self.aout.setPlainText("\n".join(lines))
        if os.path.exists(spec):
            self.spec.setPixmap(QPixmap(spec).scaled(
                640, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.record("audio-analysis", "spectrogram", r)


# ----------------------------------------------------------------------- #
# 07 Video Hiding
# ----------------------------------------------------------------------- #
class VideoHidingPage(Page):
    title = "Video Hiding (VideoHide)"

    def build(self):
        self._layout = QVBoxLayout(self)
        tabs = QTabWidget(); self._layout.addWidget(tabs, 1)

        hide = QWidget(); h = QVBoxLayout(hide)
        self.vmethod = QComboBox()
        self.vmethod.addItems(["Video LSB (audio track, ffmpeg)",
                               "Spread Spectrum (audio track)",
                               "Container / File Hiding (append)"])
        self.cover = W.FileRow("Cover video (mp4)")
        self.secret = W.FileRow("Secret file")
        self.key = W.KeyRow("Key", echo=True)
        b = QPushButton("Hide"); b.setObjectName("primary"); b.clicked.connect(self.do_hide)
        self.res = QPlainTextEdit(); self.res.setReadOnly(True)
        h.addWidget(self.vmethod); h.addWidget(self.cover); h.addWidget(self.secret)
        h.addWidget(self.key); h.addWidget(b); h.addWidget(self.res, 1)
        tabs.addTab(hide, "Hide")

        ex = QWidget(); e = QVBoxLayout(ex)
        self.estego = W.FileRow("Stego video / container")
        self.emethod = QComboBox()
        self.emethod.addItems(["Video LSB (audio track)", "Container / File Hiding"])
        self.ekey = W.KeyRow("Key", echo=True)
        b2 = QPushButton("Extract"); b2.setObjectName("primary"); b2.clicked.connect(self.do_extract)
        self.eres = QPlainTextEdit(); self.eres.setReadOnly(True)
        e.addWidget(self.emethod); e.addWidget(self.estego); e.addWidget(self.ekey)
        e.addWidget(b2); e.addWidget(self.eres, 1)
        tabs.addTab(ex, "Extract")

        info = QWidget(); i = QVBoxLayout(info)
        self.ifile = W.FileRow("Video file")
        b3 = QPushButton("Streams (ffprobe / boxes)"); b3.setObjectName("primary")
        b3.clicked.connect(self.do_info)
        b4 = QPushButton("Write videohide.sh"); b4.clicked.connect(self.do_script)
        self.ires = QPlainTextEdit(); self.ires.setReadOnly(True)
        i.addWidget(self.ifile); i.addWidget(b3); i.addWidget(b4); i.addWidget(self.ires, 1)
        tabs.addTab(info, "Info / Tools")

    def do_hide(self):
        m = self.vmethod.currentIndex()
        try:
            if m == 0:
                r = core.video_hiding.video_lsb_embed(self.cover.path(), self.secret.path(),
                                                      self.key.text())
            elif m == 1:
                r = core.video_hiding.video_ss_embed(self.cover.path(), self.secret.path(),
                                                     self.key.text())
            else:
                r = core.video_hiding.container_embed(self.cover.path(), self.secret.path(),
                                                      self.key.text())
        except Exception as exc:
            W.fail(str(exc)); return
        self.res.setPlainText(json.dumps(r, indent=2, ensure_ascii=False))
        self.record("video-hiding", "embed", r)

    def do_extract(self):
        m = self.emethod.currentIndex()
        try:
            if m == 0:
                r = core.video_hiding.video_lsb_extract(self.estego.path(), self.ekey.text())
            else:
                r = core.video_hiding.container_extract(self.estego.path(), self.ekey.text())
        except Exception as exc:
            W.fail(str(exc)); return
        self.eres.setPlainText(json.dumps(r, indent=2, ensure_ascii=False))
        self.record("video-hiding", "extract", r)

    def do_info(self):
        p = self.ifile.path()
        if not os.path.exists(p):
            W.warn("Choose a video file."); return
        try:
            r = core.video_hiding.ffprobe_info(p)
        except Exception as exc:
            W.fail(str(exc)); return
        self.ires.setPlainText(json.dumps(r, indent=2, ensure_ascii=False, default=str))
        self.record("video-info", "ffprobe", r)

    def do_script(self):
        p = core.video_hiding.write_videohide_script()
        W.ok("videohide.sh written to:\n" + p)


# ----------------------------------------------------------------------- #
# 08 Network Hiding
# ----------------------------------------------------------------------- #
class NetworkHidingPage(Page):
    title = "Network Hiding (Covert)"

    def build(self):
        self._layout = QVBoxLayout(self)
        tabs = QTabWidget(); self._layout.addWidget(tabs, 1)

        send = QWidget(); s = QVBoxLayout(send)
        self.mode = QComboBox()
        self.mode.addItems(["IPv4 Identification (IP ID) LSB",
                            "TCP ISN LSB", "Timing (inter-packet delay)"])
        self.secret = W.FileRow("Secret file")
        self.key = W.KeyRow("Key", echo=True)
        self.src = QLineEdit("10.0.0.1"); self.dst = QLineEdit("10.0.0.2")
        self.out = W.FileRow("Capture output", mode="save")
        b = QPushButton("Encode & Transmit (PCAP)"); b.setObjectName("primary")
        b.clicked.connect(self.do_send)
        self.res = QPlainTextEdit(); self.res.setReadOnly(True)
        s.addWidget(self.mode); s.addWidget(self.secret); s.addWidget(self.key)
        sr = QHBoxLayout(); sr.addWidget(QLabel("src:")); sr.addWidget(self.src)
        sr.addWidget(QLabel("dst:")); sr.addWidget(self.dst)
        s.addLayout(sr); s.addWidget(self.out); s.addWidget(b); s.addWidget(self.res, 1)
        tabs.addTab(send, "Sender (encode → traffic)")

        recv = QWidget(); r = QVBoxLayout(recv)
        self.rmode = QComboBox(); self.rmode.addItems(["IPv4 Identification (IP ID) LSB",
                                                       "TCP ISN LSB",
                                                       "Timing (inter-packet delay)"])
        self.pcap = W.FileRow("Packet capture (pcap)")
        self.rkey = W.KeyRow("Key", echo=True)
        b2 = QPushButton("Receive & Extract"); b2.setObjectName("primary")
        b2.clicked.connect(self.do_recv)
        self.rres = QPlainTextEdit(); self.rres.setReadOnly(True)
        r.addWidget(self.rmode); r.addWidget(self.pcap); r.addWidget(self.rkey)
        r.addWidget(b2); r.addWidget(self.rres, 1)
        tabs.addTab(recv, "Receiver (read → extract)")

        det = QWidget(); d = QVBoxLayout(det)
        self.dpcap = W.FileRow("Capture to inspect")
        b3 = QPushButton("Detect Covert Channel"); b3.setObjectName("primary")
        b3.clicked.connect(self.do_detect)
        self.dres = QPlainTextEdit(); self.dres.setReadOnly(True)
        d.addWidget(self.dpcap); d.addWidget(b3); d.addWidget(self.dres, 1)
        tabs.addTab(det, "Detection")

    def _m(self, combo):
        return ["ipid", "isn", "timing"][combo.currentIndex()]

    def do_send(self):
        out = self.out.path() or os.path.join(os.getcwd(), "covert_stream.pcap")
        try:
            r = core.network_hiding.send_to_pcap(self.secret.path(), self.key.text(),
                                                 out, self._m(self.mode),
                                                 self.src.text(), self.dst.text())
        except Exception as exc:
            W.fail(str(exc)); return
        self.res.setPlainText(json.dumps(r, indent=2, ensure_ascii=False))
        self.record("network-hiding", "send", r)
        W.ok(f"Covert stream saved: {out} ({r['packets']} packets)")

    def do_recv(self):
        try:
            r = core.network_hiding.extract_from_pcap(self.pcap.path(), self.rkey.text(),
                                                      self._m(self.rmode))
        except Exception as exc:
            W.fail(str(exc)); return
        self.rres.setPlainText(json.dumps(r, indent=2, ensure_ascii=False))
        self.record("network-hiding", "receive", r)

    def do_detect(self):
        try:
            r = core.network_hiding.detect_covert(self.dpcap.path())
        except Exception as exc:
            W.fail(str(exc)); return
        self.dres.setPlainText(json.dumps(r, indent=2, ensure_ascii=False))
        self.finding("network-detect", r["verdict"], r,
                     "HIGH" if "DETECTED" in r["verdict"] else "INFO")


# ----------------------------------------------------------------------- #
# 09 Malware Lab
# ----------------------------------------------------------------------- #
class MalwarePage(Page):
    title = "Malware Lab"

    def build(self):
        self._layout = QVBoxLayout(self)
        box = W.group("Payload / Executable analysis (PyInstaller · WinRAR · Sliver · Metasploit)")
        lay = QHBoxLayout(box)
        self.file = W.FileRow("Executable / payload / archive")
        b = QPushButton("Scan"); b.setObjectName("primary"); b.clicked.connect(self.do_scan)
        lay.addWidget(self.file, 1); lay.addWidget(b)
        self._layout.addWidget(box)
        self.res = QPlainTextEdit(); self.res.setReadOnly(True)
        self._layout.addWidget(self.res, 1)
        box2 = W.group("Defence exercise: build inert demo stub (detection training)")
        lay2 = QHBoxLayout(box2)
        self.stubpath = W.FileRow("Stub output", mode="save")
        b2 = QPushButton("Build Demo Stub"); b2.clicked.connect(self.do_stub)
        lay2.addWidget(self.stubpath, 1); lay2.addWidget(b2)
        self._layout.addWidget(box2)

    def do_scan(self):
        p = self.file.path()
        if not os.path.exists(p):
            W.warn("Choose a file first."); return
        try:
            r = core.malware_lab.scan_executable(p)
        except Exception as exc:
            W.fail(str(exc)); return
        lines = ["STRUCTURE :"]
        for s in r["structure"].get("sections", []):
            lines.append(f"   {s.get('name', s.get('index')):<14} "
                         f"entropy={s.get('entropy')} packed={s.get('packed')}")
        lines += [f"OVERLAY   : {r['structure'].get('overlay_bytes', 'n/a')} bytes",
                  "INDICATORS:"]
        if r["tool_indicators"]:
            for hit in r["tool_indicators"]:
                lines.append(f"   [{hit['tool']}] {hit['signature']} @ {hit['offset']}")
        else:
            lines.append("   (no PyInstaller/WinRAR/Sliver/Metasploit artefacts found)")
        lines += ["", "VERDICT   : " + r["verdict"]]
        self.res.setPlainText("\n".join(lines))
        self.finding("malware", r["verdict"], r,
                     "HIGH" if r["tool_indicators"] else "INFO")

    def do_stub(self):
        p = self.stubpath.path() or os.path.join(os.getcwd(), "demo_stub.py")
        try:
            r = core.malware_lab.build_demo_stub(p, "demo-key")
        except Exception as exc:
            W.fail(str(exc)); return
        W.ok("Inert demo stub written (scan it with Forensics to see detection):\n" + p)


# ----------------------------------------------------------------------- #
# 10/11 Case Management
# ----------------------------------------------------------------------- #
class CasePage(Page):
    title = "Case Management & Reports"

    def build(self):
        self._layout = QVBoxLayout(self)
        top = QHBoxLayout()
        b_new = QPushButton("New Case"); b_new.setObjectName("primary")
        b_new.clicked.connect(self.do_new)
        b_open = QPushButton("Open Case"); b_open.clicked.connect(self.do_open)
        b_close = QPushButton("Close Case"); b_close.clicked.connect(self.do_close)
        b_report = QPushButton("Export Report (MD)"); b_report.clicked.connect(self.do_report)
        top.addWidget(b_new); top.addWidget(b_open); top.addWidget(b_close)
        top.addWidget(b_report); top.addStretch(1)
        self._layout.addLayout(top)

        self.list = QListWidget()
        self.list.itemDoubleClicked.connect(lambda _i: self.do_open())
        self._layout.addWidget(self.list)

        self.detail = QPlainTextEdit(); self.detail.setReadOnly(True)
        self._layout.addWidget(self.detail, 1)

    def refresh(self):
        self.list.clear()
        for c in self.case.list_cases():
            self.list.addItem(f"{c['case_id']}  [{c['status']}]  {c['title']}")
        if self.case.case:
            c = self.case.case
            lines = [f"CASE {c['case_id']} — {c['title']} ({c['status']})",
                     f"created: {c['created']}  examiner: {c['examiner'] or '-'}"]
            def show(tag, items):
                out = []
                if items:
                    out.append("")
                    out.append(f"--- {tag} ---")
                    for it in items[:30]:
                        out.append("  " + str(it)[:120])
                return out
            lines += show("Evidence", [f"{e['id']} {e['path']}" for e in c["evidence"]])
            lines += show("Findings", [f"[{f['severity']}] {f['summary']}"
                                       for f in c["findings"]])
            lines += show("Operations", [f"{o['timestamp']} {o['module']} {o['action']}"
                                         for o in c["operations"]])
            lines += show("Log (last 25)", [f"{l['timestamp']} {l['message']}"
                                            for l in c["logs"][-25:]])
            self.detail.setPlainText("\n".join(lines))

    def do_new(self):
        from PySide6.QtWidgets import QInputDialog
        title, ok = QInputDialog.getText(self, "New Case", "Case title:")
        if not ok:
            return
        examiner, ok2 = QInputDialog.getText(self, "New Case", "Examiner name:", text="")
        c = self.case.create_case(title, examiner)
        self.refresh()
        W.ok(f"Case created: {c['case_id']}")

    def do_open(self):
        idx = self.list.currentRow()
        if idx < 0:
            W.warn("Select a case first."); return
        cid = self.list.item(idx).text().split()[0]
        self.case.open_case(cid)
        self.refresh()
        W.ok("Opened " + cid)

    def do_close(self):
        if self.case.case:
            self.case.close_case(); self.refresh(); W.ok("Case closed.")

    def do_report(self):
        if not self.case.case:
            W.warn("No open case."); return
        p = self.case.export_report("md")
        self.case.export_report("json")
        self.case.export_report("html")
        W.ok("Reports exported to:\n" + os.path.dirname(p))
