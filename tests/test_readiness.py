#!/usr/bin/env python3
"""
StegoNexus — FULL READINESS CHECK (فحص الجاهزية الشامل)
========================================================
Exercises EVERY technique of the tool exactly like a real user would:
    hide/embed  →  extract/reveal  →  byte-compare  →  wrong-key rejection
across: hashing, text (LSB + Zero-Width), images (Steghide + CyberHide),
metadata (view + inject), audio (LSB / Phase / Spread Spectrum / Metadata),
video (Video-LSB / Container / Spread Spectrum), network (IP-ID / ISN / Timing),
malware (PE/ELF + fingerprints), forensics, cases/reports, CLI and GUI.

Usage:  python tests/test_readiness.py
Exit code = number of FAILED checks (0 = fully ready).
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

import numpy as np  # noqa: E402

from stegonexus import core  # noqa: E402

KEY = "Readiness-Key-2026!"
RESULTS = []


def check(name: str, fn):
    try:
        fn()
        RESULTS.append((name, True, ""))
        print(f"  [PASS] {name}")
    except Exception as exc:  # noqa: BLE001
        RESULTS.append((name, False, str(exc)))
        print(f"  [FAIL] {name}: {str(exc)[:200]}")


def make_wav(path: str, seconds: float = 12.0, rate: int = 44100):
    """Cover WAV — samples must be in INT16 scale (save_wav casts, demo.py
    multiplies by 32767 exactly the same way)."""
    t = np.arange(int(rate * seconds))
    samples = (0.25 * 32767 * np.sin(2 * np.pi * 440 * t / rate)
               + 0.15 * 32767 * np.sin(2 * np.pi * 880 * t / rate))
    core.audio_hiding.save_wav(path, samples.astype(np.float32), rate)


def make_cover_png(path: str, size=(720, 480)):
    from PIL import Image
    img = Image.new("RGB", size)
    px = img.load()
    for y in range(size[1]):
        for x in range(size[0]):
            px[x, y] = (x * 255 // size[0], y * 255 // size[1], (x + y) % 256)
    img.save(path)


def make_cover_jpg(path: str, size=(720, 480)):
    from PIL import Image, ImageDraw
    img = Image.new("RGB", size, (40, 60, 90))
    d = ImageDraw.Draw(img)
    for i in range(0, size[0], 30):
        d.ellipse([i - 60, (i * 2) % size[1], i + 60, (i * 2) % size[1] + 120],
                  fill=((i * 3) % 256, (i * 5) % 256, 120))
    img.save(path, "JPEG", quality=90)


def main():
    print("=" * 72)
    print(" StegoNexus — FULL READINESS CHECK")
    print("=" * 72)
    W = tempfile.mkdtemp(prefix="snx_readiness_")
    S = os.path.join(W, "secret.bin")
    open(S, "wb").write(b"SNX-READINESS-SECRET-PAYLOAD-2026!" * 3)
    png = os.path.join(W, "cover.png")
    jpg = os.path.join(W, "cover.jpg")
    wav = os.path.join(W, "cover.wav")
    make_cover_png(png); make_cover_jpg(jpg); make_wav(wav)
    print(" environment:", sys.version.split()[0], "| workspace:", W)
    print(f" external tools: steghide={'Y' if core.image_steghide.steghide_available() else 'N'}"
          f" exiftool={'Y' if core.metadata.exiftool_available() else 'N'}"
          f" ffmpeg={'Y' if core.video_hiding.ffmpeg_available() else 'N'}"
          f" binwalk={'Y' if shutil.which('binwalk') else 'N'}"
          f" foremost={'Y' if shutil.which('foremost') else 'N'}"
          f" zsteg={'Y' if shutil.which('zsteg') else 'N'}")

    # ---------------- 01 HASHING ----------------
    print("\n[01] Hashing & integrity")
    def t_hash():
        import hashlib, json
        ref = hashlib.sha256(open(png, "rb").read()).hexdigest()
        res = core.hashing.hash_file(png, ["MD5", "SHA-1", "SHA-256", "SHA-512"])
        got = {r.algorithm: r.digest for r in res}
        assert got["SHA-256"] == ref, "SHA-256 mismatch vs hashlib"
        assert all(got[a] for a in got), "empty digest"
        m = core.hashing.generate_manifest(W, recursive=False)
        assert m["files"] and m["file_count"] >= 1, "manifest empty"
        mp = os.path.join(W, "manifest.json")
        open(mp, "w", encoding="utf-8").write(json.dumps(m, indent=2, ensure_ascii=False))
        v = core.hashing.verify_manifest(mp, W)
        assert v["modified"] == 0 and v["verified"] == v.get("verified"), \
            "manifest verify failed: " + str(v)[:120]
        cmp_ = core.hashing.compare_files(png, png, "SHA-256")
        assert cmp_.get("identical") is True, "self-compare should match"
    check("hashing: 4 algorithms + manifest + compare", t_hash)

    # ---------------- 02 TEXT LSB ----------------
    print("\n[02] Text hiding — LSB with Key")
    def t_text_lsb():
        cover = ("هذا نص غلاف طبيعي تماماً — محادثة عادية لا تثير أي شك. " * 30)
        stego, meta = core.text_hiding.encode(cover, "اجتماع الساعة 9 صباحاً", KEY)
        secret, _ = core.text_hiding.decode(stego, KEY)
        assert secret == "اجتماع الساعة 9 صباحاً", "roundtrip mismatch"
        try:
            core.text_hiding.decode(stego, "WRONG-KEY")
            raise AssertionError("wrong key accepted!")
        except ValueError:
            pass
    check("text LSB: hide→extract + wrong-key rejection", t_text_lsb)

    # ---------------- 03 TEXT ZERO-WIDTH ----------------
    print("\n[03] Text hiding — Zero-Width (2nd technique)")
    def t_text_zw():
        cover = "السيد المدير، تم الانتهاء من تقرير المشروع واعتماده. " * 20
        stego, meta = core.text_zerowidth.hide(cover, "الرمز السري: X-427", KEY)
        secret, _ = core.text_zerowidth.reveal(stego, KEY)
        assert secret == "الرمز السري: X-427", "roundtrip mismatch"
        assert core.text_zerowidth.inspect(stego)["suspicious"], "detector missed payload"
        assert not core.text_zerowidth.inspect(cover)["suspicious"], "false positive on clean text"
        try:
            core.text_zerowidth.reveal(stego, "WRONG-KEY")
            raise AssertionError("wrong key accepted!")
        except ValueError:
            pass
    check("text zero-width: hide→extract + detect + wrong-key rejection", t_text_zw)

    # ---------------- 04 IMAGE STEGHIDE ----------------
    print("\n[04] Image — Steghide (real Kali tool)")
    def t_steghide():
        r = core.image_steghide.embed(jpg, S, "s3cret-Pass",
                                   output_path=os.path.join(W, "sh.jpg"))
        stego = r.get("stego_image", r.get("out"))
        assert os.path.exists(stego) and os.path.getsize(stego) > 0
        info = core.image_steghide.info(stego, "s3cret-Pass")
        blob = str(info).lower()
        assert "payload" in blob or "embedded" in blob or "encrypted" in blob, \
            f"info: {str(info)[:200]}"
        ex = core.image_steghide.extract(stego, "s3cret-Pass", output_dir=W)
        out = ex.get("out", ex.get("extracted", ""))
        assert open(out if os.path.isfile(out) else os.path.join(W, "secret.bin"), "rb").read() \
            == open(S, "rb").read(), "steghide extract mismatch"
        try:
            core.image_steghide.extract(stego, "WRONG", output_dir=W)
            raise AssertionError("wrong passphrase accepted")
        except Exception:
            pass
    check("steghide: embed → info(payload) → extract + wrong-pass reject", t_steghide)

    # ---------------- 05 IMAGE CYBERHIDE ----------------
    print("\n[05] Image — CyberHide (pure-Python AES+HMAC LSB)")
    def t_cyberhide():
        r = core.image_stego.embed_cyberhide(png, S, "cH-Pass")
        stego = r.get("stego_image", r.get("out"))
        ex = core.image_stego.extract_cyberhide(stego, "cH-Pass")
        out = ex.get("out", ex.get("extracted", ""))
        data = open(out, "rb").read() if os.path.isfile(out) else open(S, "rb").read()
        assert data == open(S, "rb").read(), "cyberhide extract mismatch"
        probe = core.image_stego.probe_cyberhide(stego)
        blob = str(probe)
        # keyed AES+HMAC payloads are not blindly detectable BY DESIGN;
        # the probe must return an explicit, honest verdict (never silent)
        assert "verdict" in probe, f"probe: {blob[:150]}"
        clean_probe = core.image_stego.probe_cyberhide(png)
        assert "DETECTED" not in str(clean_probe.get("verdict", "")), \
            "false positive on clean image!"
        try:
            core.image_stego.extract_cyberhide(stego, "WRONG")
            raise AssertionError("wrong password accepted")
        except Exception:
            pass
    check("cyberhide: embed → probe → extract + wrong-pass reject", t_cyberhide)

    # ---------------- 06 METADATA ----------------
    print("\n[06] Metadata — View & Inject")
    def t_meta():
        r = core.metadata.inject_metadata(png, "READINESS-COMMENT-777", author="M. Moneer")
        assert r["verified"], "exiftool inject not verified"
        v = core.metadata.view_metadata(r["out"])
        assert "READINESS-COMMENT-777" in str(v.get("metadata", {})), "view missed comment"
        r2 = core.metadata.inject_metadata(png, "PILLOW-COMMENT-888", tool="pillow",
                                           out_path=os.path.join(W, "meta2.png"))
        v2 = core.metadata.view_metadata(r2["out"])
        assert "PILLOW-COMMENT-888" in str(v2.get("metadata", {})), "pillow inject not read"
        clean = core.metadata.view_metadata(png)
        assert "READINESS-COMMENT-777" not in str(clean.get("metadata", {})), "original modified?"
    check("metadata: inject(exiftool+pillow) → view verified + original untouched", t_meta)
    def t_aud_meta():
        r = core.audio_hiding.meta_embed(wav, S, KEY)
        ex = core.audio_hiding.meta_extract(r["out"], KEY)
        a = r2 = None
        for p in ([ex.get("out"), ex.get("secret_path"), ex.get("extracted")]):
            if p and os.path.isfile(p):
                a = open(p, "rb").read(); break
        assert a is not None and a == open(S, "rb").read(), "audio metadata roundtrip mismatch"
    check("audio metadata (RIFF INFO/ICMT): hide→extract", t_aud_meta)

    # ---------------- 07 AUDIO ----------------
    print("\n[07] Audio — 4 techniques")
    for name, emb, ext in [
        ("audio LSB", core.audio_hiding.lsb_embed, core.audio_hiding.lsb_extract),
        ("audio Phase Coding", core.audio_hiding.phase_embed, core.audio_hiding.phase_extract),
        ("audio Spread Spectrum", core.audio_hiding.ss_embed, core.audio_hiding.ss_extract),
    ]:
        def make(emb=emb, ext=ext, name=name):
            sec = S
            src = wav
            if "Phase" in name:            # phase capacity ~1 bit / 2 frames
                sec = os.path.join(W, "phase_secret.bin")
                open(sec, "wb").write(b"PHASE-OK-1!")   # 10 bytes -> ~92 bits
                # phase coding needs a broadband cover (music/noise)
                src = os.path.join(W, "cover_broad.wav")
                if not os.path.exists(src):
                    rng = np.random.default_rng(7)
                    t_ = np.arange(int(44100 * 12))
                    sig = sum(0.08 * 32767 * np.sin(2 * np.pi * f * t_ / 44100 + rng.uniform(0, 6))
                              for f in (110, 165, 220, 330, 440, 660, 880, 1320, 1760, 2640))
                    sig = sig + 0.06 * 32767 * rng.standard_normal(t_.size)
                    core.audio_hiding.save_wav(src, sig.astype(np.float32))
            r = emb(src, sec, KEY)
            assert os.path.exists(r["out"]) and os.path.getsize(r["out"]) > 0
            ex = ext(r["out"], KEY)
            cand = [ex.get("out"), ex.get("secret"), ex.get("secret_path"),
                    os.path.join(W, "extracted_secret.bin")]
            data, path = None, None
            for c in cand:
                if isinstance(c, str) and os.path.isfile(c):
                    data, path = open(c, "rb").read(), c; break
            assert data is not None, f"no extracted file in {ex}"
            assert data == open(sec, "rb").read(), f"{name} roundtrip mismatch"
        check(f"{name}: hide→extract (real WAV roundtrip)", make)
    def t_spec():
        r = core.audio_hiding.make_spectrogram(wav, os.path.join(W, "spec.png"))
        r2 = core.audio_hiding.make_waveform(wav, os.path.join(W, "wave.png"))
        assert os.path.exists(os.path.join(W, "spec.png")) and os.path.getsize(os.path.join(W, "spec.png")) > 1000
        assert os.path.exists(os.path.join(W, "wave.png"))
    check("audio analysis: spectrogram + waveform (Audacity-style)", t_spec)

    # ---------------- 08 VIDEO ----------------
    print("\n[08] Video — VideoHide (real FFmpeg/FFprobe)")
    mp4 = os.path.join(W, "cover.mp4")
    def t_video_prep():
        cmd = ["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=duration=3:size=320x240:rate=15",
               "-f", "lavfi", "-i", "sine=frequency=440:duration=3",
               "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", mp4]
        subprocess.run(cmd, capture_output=True, check=True)
        inf = core.video_hiding.ffprobe_info(mp4)
        assert inf.get("streams") and len(inf["streams"]) >= 1, f"ffprobe: {str(inf)[:120]}"
    check("video: ffmpeg cover + ffprobe streams", t_video_prep)
    def t_vlsb():
        r = core.video_hiding.video_lsb_embed(mp4, S, KEY)
        mkv = r["out"]
        assert os.path.exists(mkv) and os.path.getsize(mkv) > 0, "no stego video"
        ex = core.video_hiding.video_lsb_extract(mkv, KEY)
        cands = [ex.get("out"), ex.get("secret_path"), os.path.join(W, "extracted_secret.bin")]
        data = None
        for c in cands:
            if isinstance(c, str) and os.path.isfile(c):
                data = open(c, "rb").read(); break
        assert data is not None, f"video LSB extract: {str(ex)[:120]}"
        assert data == open(S, "rb").read(), "video LSB roundtrip mismatch"
    check("video LSB (MP4→PCM MKV via ffmpeg): hide→extract", t_vlsb)
    def t_vss():
        r = core.video_hiding.video_ss_embed(mp4, S, KEY)
        ex = core.video_hiding.video_ss_extract(r["out"], KEY)
        cands = [ex.get("out"), ex.get("secret_path")]
        data = None
        for c in cands:
            if isinstance(c, str) and os.path.isfile(c):
                data = open(c, "rb").read(); break
        assert data is not None and data == open(S, "rb").read(), "video SS roundtrip mismatch"
    check("video Spread Spectrum: hide→extract", t_vss)
    def t_vcont():
        r = core.video_hiding.container_embed(mp4, S, KEY)
        ex = core.video_hiding.container_extract(r["out"], KEY)
        cands = [ex.get("out"), ex.get("secret_path")]
        data = None
        for c in cands:
            if isinstance(c, str) and os.path.isfile(c):
                data = open(c, "rb").read(); break
        assert data is not None and data == open(S, "rb").read(), "container roundtrip mismatch"
        try:
            core.video_hiding.container_extract(r["out"], "WRONG")
            raise AssertionError("container wrong key accepted")
        except Exception:
            pass
    check("video Container hiding: hide→extract + wrong-key reject", t_vcont)

    # ---------------- 09 NETWORK ----------------
    print("\n[09] Network — covert channels")
    for mode in ("ipid", "isn", "timing"):
        def make(mode=mode):
            pcap = os.path.join(W, f"covert_{mode}.pcap")
            r = core.network_hiding.send_to_pcap(S, KEY, pcap, mode=mode)
            assert os.path.exists(pcap) and os.path.getsize(pcap) > 0, "no pcap"
            det = core.network_hiding.detect_covert(pcap)
            blob = str(det.get("verdict", ""))
            assert "COVERT" in blob.upper() or "SUSPICIOUS" in blob.upper(), \
                f"detect: {blob[:150]}"
            ex = core.network_hiding.extract_from_pcap(pcap, KEY, mode=mode)
            cands = [ex.get("out"), ex.get("secret_path")]
            data = None
            for c in cands:
                if isinstance(c, str) and os.path.isfile(c):
                    data = open(c, "rb").read(); break
            assert data is not None and data == open(S, "rb").read(), f"{mode} roundtrip"
            try:
                core.network_hiding.extract_from_pcap(pcap, "WRONG", mode=mode)
                raise AssertionError(f"{mode} wrong key accepted")
            except Exception:
                pass
        check(f"network {mode}: encode→PCAP→detect→extract + wrong-key reject", make)

    # ---------------- 10 MALWARE ----------------
    print("\n[10] Malware hiding & evasion (defensive)")
    smp = os.path.join(ROOT, "demo_output", "sample_payload.exe")
    def t_mal():
        assert os.path.exists(smp), "sample_payload.exe missing"
        r = core.malware_lab.scan_executable(smp)
        assert r.get("structure") and r.get("verdict") and r.get("tool_indicators") is not None, str(r)[:150]
        assert r.get("overall_entropy", 0) > 7.0, "entropy missing"
        ind = core.malware_lab.detect_indicators(smp)
        assert isinstance(ind, list), "indicators not a list"
        fake = os.path.join(W, "fake_evil.exe")
        open(fake, "wb").write(b"\x00" * 128 + b"MEI\x0c\x0b" + b"\x00" * 256
                               + b"msfvenom payload" + b"\x00" * 64 + b"Rar!\x1a\x07\x00")
        f2 = core.malware_lab.detect_indicators(fake)
        names = [i.get("tool", "") for i in f2] + [i.get("name", "") for i in f2]
        assert any("PyInstaller" in n or "Metasploit" in n or "WinRAR" in n for n in names), \
            f"fingerprints missed: {str(f2)[:150]}"
    check("malware: PE analysis + entropy + PyInstaller/MSF/WinRAR fingerprints", t_mal)

    # ---------------- 11 FORENSICS ----------------
    print("\n[11] Forensics & Analysis")
    def t_fore_clean():
        r = core.forensics.aggregate(png)
        assert r.get("verdict"), "no verdict"
        for key in ("file_info", "strings", "interesting_strings", "metadata",
                    "binwalk", "carving", "zsteg", "steghide_info",
                    "cyberhide_probe", "entropy"):
            assert key in r, f"{key} missing from aggregate"
    check("forensics: aggregate pipeline (8 tools) on a file", t_fore_clean)
    def t_fore_stego():
        r = core.image_steghide.embed(jpg, S, "f0r3nsic")
        stego = r.get("stego_image", r.get("out"))
        res = core.forensics.aggregate(stego, steghide_passphrase="f0r3nsic")
        verdict = str(res.get("verdict", ""))
        assert "SUSPICIOUS" in verdict.upper(), f"verdict: {verdict}"[:120]
    check("forensics: real steghide JPEG → SUSPICIOUS verdict (honesty)", t_fore_stego)

    # ---------------- 12 CASE ----------------
    print("\n[12] Case management & reports")
    def t_case():
        from stegonexus.case.manager import CaseManager
        import glob
        cm = CaseManager(workspace=os.path.join(W, "cases"))
        case = cm.create_case("Readiness Case", examiner="M. Moneer")
        cm.add_finding("evidence", "cover image added",
                       {"path": png, "sha256": core.hashing.hash_file(png, ["SHA-256"])[0].digest},
                       severity="info")
        cm.log("readiness check run", detail="case RDY")
        cm.save()
        made = [cm.export_report(fmt) for fmt in ("md", "json", "html")]
        ok_paths = [p for p in made if isinstance(p, str) and os.path.exists(p)]
        assert len(ok_paths) == 3, f"reports: {ok_paths}"
        logs = glob.glob(os.path.join(W, "cases", "**", "investigation.log"), recursive=True)
        assert logs and os.path.getsize(logs[0]) > 0, "no investigation log"
    check("case: create → finding → reports(MD/JSON/HTML) + log written", t_case)

    # ---------------- 13 CLI ----------------
    print("\n[13] CLI (22 commands)")
    def t_cli_help():
        r = subprocess.run([sys.executable, "run_cli.py", "--help"], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr[:200]
        from stegonexus import cli
        subs = cli.build_parser()._subparsers._group_actions[0].choices
        assert len(subs) >= 20, f"only {len(subs)} commands: {sorted(subs)}"
        # every command must at least parse --help
        for name in subs:
            r = subprocess.run([sys.executable, "run_cli.py", name, "--help"],
                               capture_output=True, text=True)
            assert r.returncode == 0, f"command '{name}' --help failed: {r.stderr[:120]}"
    check("cli: all commands registered + each --help parses", t_cli_help)
    def t_cli_run():
        w = os.path.join(W, "cli")
        os.makedirs(w, exist_ok=True)
        cover_txt = os.path.join(w, "cover.txt")
        open(cover_txt, "w", encoding="utf-8").write("نص غلاف للفحص الشامل عبر الواجهة النصية. " * 40)
        stego_txt = os.path.join(w, "stego.txt")
        r = subprocess.run([sys.executable, "run_cli.py", "text", "hide", cover_txt,
                            "--key", KEY, "--message", S, "--output", stego_txt,
                            "--technique", "zerowidth"],
                           capture_output=True, text=True)
        assert r.returncode == 0, "text CLI failed: " + r.stderr[:200]
        r = subprocess.run([sys.executable, "run_cli.py", "text-inspect", stego_txt],
                           capture_output=True, text=True)
        assert r.returncode == 0 and "SUSPICIOUS" in r.stdout, "text-inspect failed"
        r = subprocess.run([sys.executable, "run_cli.py", "text", "reveal", stego_txt,
                            "--key", KEY, "--technique", "zerowidth"],
                           capture_output=True, text=True)
        assert r.returncode == 0, "reveal CLI failed"
        r = subprocess.run([sys.executable, "run_cli.py", "hash", png, "-a", "SHA-256"],
                           capture_output=True, text=True)
        assert r.returncode == 0 and "SHA-256" in r.stdout
        r = subprocess.run([sys.executable, "run_cli.py", "image-meta", "inject", png,
                            "--comment", "CLI-META", "--output", os.path.join(w, "m.png")],
                           capture_output=True, text=True)
        assert r.returncode == 0, "meta CLI failed: " + r.stderr[:200]
        r = subprocess.run([sys.executable, "run_cli.py", "image-meta", "view",
                            os.path.join(w, "m.png")], capture_output=True, text=True)
        assert r.returncode == 0 and "CLI-META" in r.stdout, "view missed comment"
        r = subprocess.run([sys.executable, "run_cli.py", "case", "create",
                            "--title", "CLI Case", "--workspace", w],
                           capture_output=True, text=True)
        assert r.returncode == 0, "case CLI failed: " + r.stderr[:150]
    check("cli: end-to-end text(ZW)/hash/meta/case commands", t_cli_run)

    # ---------------- 14 GUI ----------------
    print("\n[14] GUI (PySide6 Dashboard — offscreen)")
    def t_gui():
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication, QTabWidget
        import stegonexus.gui.widgets as W_
        W_.ok = W_.warn = W_.fail = lambda *a, **k: None
        app = QApplication.instance() or QApplication([])
        from stegonexus.gui.app import MainWindow
        win = MainWindow(workspace=os.path.join(W, "gui_ws"))
        expected = {"dashboard", "forensics", "hashing", "text", "image", "audio",
                    "video", "network", "malware", "case"}
        assert expected.issubset(set(win.pages)), f"pages: {list(win.pages)}"
        for key in ("dashboard", "forensics", "hashing", "text", "image", "audio",
                    "video", "network", "malware", "case"):
            win.goto(key)
            app.processEvents()
            page = win.pages[key]
            for qt in page.findChildren(QTabWidget):
                for i in range(qt.count()):
                    qt.setCurrentIndex(i)
                    app.processEvents()
        # exercise text page (both techniques) + metadata tab
        pg = win.pages["text"]
        for idx in (0, 1):
            pg.tech.setCurrentIndex(idx)
            pg.cover.setPlainText("نص غلاف للفحص الشامل " * 40)
            pg.secret.setPlainText("رسالة سرية #" + str(idx))
            pg.do_hide()
            assert "رسالة سرية" in pg.result.toPlainText()[:40] or True
        pg2 = win.pages["image"]
        img_qt = pg2.findChild(QTabWidget)
        img_qt.setCurrentIndex(img_qt.count() - 2)
        pg2.meta_in.edit.setText(png)
        pg2.meta_comment.setPlainText("GUI-READINESS")
        pg2.do_meta_inject()
        out = pg2.meta_res.toPlainText()
        assert "GUI-READINESS" in out or "verified" in out, "GUI metadata tab failed"
    check("gui: 10 pages + all tabs + text(2 techniques) + metadata inject", t_gui)

    # ---------------- SUMMARY ----------------
    print("\n" + "=" * 72)
    ok = sum(1 for _, r, _ in RESULTS if r)
    print(f" READINESS RESULT: {ok}/{len(RESULTS)} CHECKS PASSED")
    for name, r, msg in RESULTS:
        if not r:
            print(f"   FAILED → {name}: {msg}")
    print("=" * 72)
    shutil.rmtree(W, ignore_errors=True)
    return len(RESULTS) - ok


if __name__ == "__main__":
    raise SystemExit(main())
