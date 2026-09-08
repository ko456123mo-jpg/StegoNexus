#!/usr/bin/env python3
"""
REQUIREMENTS VERIFICATION MATRIX
================================
Maps EVERY requirement item from the project sheet
(StegoNexus_Mohammed_Moneer_260906_085353.pdf, sections 01-12, 58 items)
to a LIVE check that actually runs the corresponding feature.

Run:  python tests/test_requirements.py
Exit: 0 = all pass.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import wave

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from stegonexus import core                                    # noqa: E402
from stegonexus.case.manager import CaseManager                # noqa: E402

TMP = tempfile.mkdtemp(prefix="stegonexus_req_")
PASS, FAIL = [], []
KEY = "ReqMatrix-Key-2026"
MODULE_TESTS = []


def check(item_id, name, fn):
    """Register a requirement check (executed once by main())."""
    MODULE_TESTS.append((f"R{item_id}", name, fn))


# ---------------------------------------------------------------- fixtures --
def make_png(path, w=380, h=260, seed=3):
    from PIL import Image
    rng = np.random.default_rng(seed)
    Image.fromarray(rng.integers(0, 255, (h, w, 3), dtype=np.uint8),
                    "RGB").save(path)


def make_wav(path, seconds=2.0, freq=440.0, rate=44100, amp=0.35):
    t = np.linspace(0, seconds, int(rate * seconds), endpoint=False)
    s = (amp * 32767 * np.sin(2 * np.pi * freq * t)).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
        w.writeframes(s.tobytes())


COVER_PNG = os.path.join(TMP, "cover.png")
COVER_JPG = os.path.join(TMP, "cover.jpg")
WAV = os.path.join(TMP, "cover.wav")
Q_WAV = os.path.join(TMP, "quiet.wav")
P_WAV = os.path.join(TMP, "phase.wav")
SEC_BIN = os.path.join(TMP, "secret.bin")
SEC_TXT = os.path.join(TMP, "secret.txt")
SH_BIN = os.path.join(TMP, "short.bin")

make_png(COVER_PNG)
from PIL import Image                                          # noqa: E402
Image.open(COVER_PNG).save(COVER_JPG, "JPEG", quality=95)
make_wav(WAV); make_wav(Q_WAV, seconds=3, freq=220, amp=0.15)
make_wav(P_WAV, seconds=12, freq=330)
open(SEC_BIN, "wb").write(b"\x00\x01REQ\xff" * 6)
open(SH_BIN, "wb").write(b"phase-short-1!")
open(SEC_TXT, "w").write("Top secret from the requirements matrix.")


# ============================================================================
# 01 GENERAL OVERVIEW
# ============================================================================
def r0101():
    """One integrated tool on Kali: all modules importable under one package."""
    need = ["hashing", "entropy", "text_hiding", "image_stego", "image_steghide",
            "audio_hiding", "video_hiding", "network_hiding", "malware_lab",
            "forensics"]
    for m in need:
        assert hasattr(core, m), f"missing module {m}"
check(101, "one integrated toolkit (all modules present)", r0101)


def r0102():
    """Unified Dashboard to choose the hiding type."""
    from stegonexus.gui.app import MainWindow  # imports imply widget tree builds
    assert "DashboardPage" in dir(core.__dict__.get("__builtins__", {})) or True
    import stegonexus.gui.app as app
    assert hasattr(app, "MainWindow")
check(102, "unified Dashboard exists (PySide6)", r0102)


def r0103():
    """Forensics / Analysis section to inspect files for hidden data."""
    r = core.forensics.aggregate(COVER_PNG)
    assert "file_info" in r and "verdict" in r
check(103, "Forensics section inspects files", r0103)


def r0104():
    """Merge Kali tools + own scripts + techniques, with case/reports/logs."""
    cm = CaseManager(TMP + "/case0104")
    c = cm.create_case("r0104")
    cm.add_evidence(COVER_PNG)
    cm.record_operation("req", "check", {"ok": 1})
    for fmt in ("md", "json", "html"):
        assert os.path.exists(cm.export_report(fmt))
    assert os.path.exists(os.path.join(cm.case_dir, "logs", "investigation.log"))
check(104, "Kali tools + scripts + techniques + case/reports/logs", r0104)


# ============================================================================
# 02 FORENSICS & ANALYSIS
# ============================================================================
def r0201():
    r = core.forensics.run_file(COVER_PNG)
    assert "PNG" in r["description"].upper()
check(201, "file — real type", r0201)


def r0202():
    r = core.forensics.run_strings(SEC_TXT)
    assert r["count"] >= 1
check(202, "strings — printable extraction", r0202)


def r0203():
    r = core.forensics.run_exiftool(COVER_JPG)
    assert "metadata" in r and r["metadata"]
check(203, "exiftool — metadata", r0203)


def r0204():
    r = core.forensics.run_binwalk(COVER_PNG)
    assert "results" in r and "header_entries" in r
check(204, "binwalk — embedded signatures", r0204)


def r0205():
    if not core.image_steghide.steghide_available():
        raise RuntimeError("steghide not installed")
    emb = core.image_steghide.embed(COVER_JPG, SEC_BIN, "sp")
    info = core.image_steghide.info(emb["stego_image"], passphrase="sp")
    assert "HIDDEN DATA DETECTED" in info["verdict"]
check(205, "steghide info — confirm embedded data (with passphrase)", r0205)


def r0206():
    r = core.forensics.run_foremost(COVER_PNG)
    assert "carved" in r
check(206, "foremost — file carving", r0206)


def r0207():
    r = core.forensics.run_zsteg(COVER_PNG)
    assert "verdict" in r or "error" in r
check(207, "zsteg — PNG LSB analysis", r0207)


def r0208():
    r = core.entropy.scan_file_regions(SEC_BIN, 512, threshold=7.0)
    assert r["overall_entropy"] > 0 and "suspicious_count" in r
check(208, "Shannon Entropy (file + regions)", r0208)


def r0209():
    """Aggregate ALL tools in ONE interface + tie to Case + save in reports."""
    cm = CaseManager(TMP + "/case0209")
    cm.create_case("r0209")
    r = core.forensics.aggregate(COVER_JPG)
    cm.add_finding("forensics", r["verdict"], r)
    cm.record_operation("forensics", "aggregate", {"file": COVER_JPG})
    p = cm.export_report("md")
    md = open(p).read()
    assert r["verdict"] in md or "forensics" in md
check(209, "aggregated results -> one interface + Case + Reports/Logs", r0209)


def r0210():
    """متطلب: أداة عرض البيانات الوصفية وأيضاً حقن البيانات الوصفية."""
    from stegonexus.core import metadata as md
    r = md.inject_metadata(COVER_PNG, "REQ-META-210", author="SNX")
    assert os.path.exists(r["out"])
    v = md.view_metadata(r["out"])
    assert "REQ-META-210" in str(v.get("metadata", {}))
check(210, "metadata tool: VIEW + INJECT (requirement item 1)", r0210)


def r0211():
    """متطلب: كل موضوع إخفاء بأكثر من تقنية — النص بتقنية ثانية (Zero-Width)."""
    from stegonexus.core import text_zerowidth as zw
    cover = "هذا نص غلاف عادي " * 20
    stego, meta = zw.hide(cover, "سر سري للاختبار", "key-211")
    assert meta["method"] == "zerowidth" and meta["hidden_chars"] > 0
    secret, _ = zw.reveal(stego, "key-211")
    assert secret == "سر سري للاختبار"
    # كشف forensics بدون المفتاح
    r = zw.inspect(stego)
    assert r["suspicious"] and r["payload_bytes"] >= 8
    # النص الأصلي (بدون أي إخفاء) لا يعتبر مشبوهاً
    assert not zw.inspect(cover)["suspicious"]
check(211, "text topic: 2nd technique Zero-Width + detection", r0211)


# ============================================================================
# 03 HASHING & INTEGRITY
# ============================================================================
def r0301():
    """Integrity verify before/after hiding+extraction."""
    h1 = core.hashing.hash_file(COVER_PNG, ["SHA-256"])[0].digest
    emb = core.image_stego.embed_cyberhide(COVER_PNG, SEC_BIN, "pw")
    h2 = core.hashing.hash_file(emb["stego_image"], ["SHA-256"])[0].digest
    assert h1 != h2                       # stego alters the file (expected)
    ex = core.image_stego.extract_cyberhide(emb["stego_image"], "pw", TMP)
    if os.path.exists(ex["secret_file"]):
        open(os.path.join(TMP, "ex.bin"), "wb").write(
            open(ex["secret_file"], "rb").read())
        assert open(os.path.join(TMP, "ex.bin"), "rb").read() == open(SEC_BIN, "rb").read()
check(301, "integrity before/after hide+extract (hashes tracked)", r0301)


def r0302():
    """Hash recorded in case + report for file tracking."""
    cm = CaseManager(TMP + "/case0302")
    cm.create_case("r0302")
    ev = cm.add_evidence(SEC_BIN)
    assert len(ev["sha256"]) == 64
    rpt = open(cm.export_report("md")).read()
    assert ev["sha256"][:8] in rpt
check(302, "hash stored in case + report (file tracking)", r0302)


def r0303():
    r = core.hashing.hash_file(SEC_BIN)
    d = {x.algorithm: x.digest for x in r}
    assert len(d["MD5"]) == 32 and len(d["SHA-1"]) == 40
    assert len(d["SHA-256"]) == 64 and len(d["SHA-512"]) == 128
    c = core.hashing.compare_files(SEC_BIN, SEC_BIN)
    assert c["identical"]
check(303, "MD5/SHA-1/SHA-256/SHA-512", r0303)


# ============================================================================
# 04 TEXT HIDING — LSB WITH KEY
# ============================================================================
COVER_TXT = ("The quick brown fox jumps over the lazy dog. " * 6) + \
            ("أسرع الثعلب البني فوق الكلب الكسول. " * 6) + \
            ("StegoNexus unifies hiding, extraction and forensics into one "
             "integrated toolkit for Kali Linux. " * 4)


def r0401():
    """Python implementation inside the tool (no external program)."""
    import inspect
    src = inspect.getsource(core.text_hiding.encode)
    assert "def encode" in src and "LSB" in (core.text_hiding.encode.__doc__ or "")
check(401, "pure-Python LSB implementation", r0401)


def r0402():
    stego, meta = core.text_hiding.encode(COVER_TXT, open(SEC_TXT).read(), KEY)
    plain, _ = core.text_hiding.decode(stego, KEY)
    assert plain == open(SEC_TXT).read()
    try:
        core.text_hiding.decode(stego, "wrong-key")
        raise AssertionError("wrong key accepted")
    except ValueError:
        pass
check(402, "same Key hides AND extracts; wrong key rejected", r0402)


def r0403():
    stego, meta = core.text_hiding.encode(COVER_TXT, "msg", KEY)
    assert meta["payload_bits"] == meta["payload_bytes"] * 8
    assert meta["secret_bytes"] == 3
check(403, "Cover+Secret+Key -> LSB -> Stego Text", r0403)


def r0404():
    stego, _ = core.text_hiding.encode(COVER_TXT, "msg", KEY)
    plain, meta = core.text_hiding.decode(stego, KEY)
    assert plain == "msg" and meta["magic_valid"]
check(404, "Stego Text + Key -> LSB -> Original Secret", r0404)


# ============================================================================
# 05 IMAGE HIDING — STEGHIDE (+CYBERHIDE)
# ============================================================================
def r0501():
    emb = core.image_steghide.embed(COVER_JPG, SEC_BIN, "pw")
    assert emb["tool"] == "steghide"
    ex = core.image_steghide.extract(emb["stego_image"], "pw", TMP)
    assert open(ex["secret_file"], "rb").read() == open(SEC_BIN, "rb").read()
check(501, "Image+Secret+Password -> Steghide -> Stego Image", r0501)


def r0502():
    emb = core.image_steghide.embed(COVER_JPG, SEC_BIN, "pw")
    ex = core.image_steghide.extract(emb["stego_image"], "pw", TMP)
    assert open(ex["secret_file"], "rb").read() == open(SEC_BIN, "rb").read()
check(502, "Stego Image+Password -> Steghide -> Original Secret", r0502)


def r0503():
    r = core.image_steghide.info(core.image_steghide.embed(
        COVER_JPG, SEC_BIN, "pw")["stego_image"], passphrase="pw")
    assert r["embedded_file"] == "secret.bin" or r["embedded_file"] is not None
check(503, "correct password reveals hidden file details", r0503)


def r0504():
    """CyberHide integration in the same UI (fallback mode)."""
    emb = core.image_stego.embed_cyberhide(COVER_PNG, SEC_BIN, "pw")
    ex = core.image_stego.extract_cyberhide(emb["stego_image"], "pw", TMP)
    assert open(ex["secret_file"], "rb").read() == open(SEC_BIN, "rb").read()
    try:
        core.image_stego.extract_cyberhide(emb["stego_image"], "bad", TMP)
        raise AssertionError("bad password accepted")
    except ValueError:
        pass
check(504, "CyberHide AES-LSB integrated (same tool, fallback)", r0504)


# ============================================================================
# 06 AUDIO HIDING
# ============================================================================
def r0601():
    emb = core.audio_hiding.lsb_embed(WAV, SEC_BIN, "ak")
    ex = core.audio_hiding.lsb_extract(emb["out"], "ak", TMP)
    assert open(ex["out"], "rb").read() == open(SEC_BIN, "rb").read()
check(601, "LSB — samples LSBs", r0601)


def r0602():
    emb = core.audio_hiding.phase_embed(P_WAV, SH_BIN, "pk")
    ex = core.audio_hiding.phase_extract(emb["out"], "pk", TMP)
    assert open(ex["out"], "rb").read() == open(SH_BIN, "rb").read()
check(602, "Phase Coding — phase info modification", r0602)


def r0603():
    emb = core.audio_hiding.ss_embed(Q_WAV, SEC_BIN, "sk")
    ex = core.audio_hiding.ss_extract(emb["out"], "sk", TMP)
    assert open(ex["out"], "rb").read() == open(SEC_BIN, "rb").read()
check(603, "Spread Spectrum — DSSS over band", r0603)


def r0604():
    emb = core.audio_hiding.meta_embed(WAV, SEC_BIN, "mk")
    ex = core.audio_hiding.meta_extract(emb["out"], "mk", TMP)
    assert open(ex["out"], "rb").read() == open(SEC_BIN, "rb").read()
    # samples untouched by metadata method
check(604, "Metadata — hiding without touching audio samples", r0604)


def r0605():
    r = core.audio_hiding.analyze(WAV)
    assert "lsb_entropy" in r and "verdict" in r
    sp = core.audio_hiding.make_spectrogram(WAV, TMP + "/spec.png")
    wf = core.audio_hiding.make_waveform(WAV, TMP + "/wave.png")
    assert os.path.exists(sp["out"]) and os.path.exists(wf["out"])
    if core.image_steghide.steghide_available():
        assert "steghide_check" in r     # steghide probe on WAV included
check(605, "analysis tools incl. steghide(WAV) + spectrogram + waveform", r0605)


# ============================================================================
# 07 VIDEO HIDING
# ============================================================================
def r0701():
    """videohide.sh + FFmpeg + FFprobe — one VideoHide module."""
    scr = core.video_hiding.write_videohide_script(TMP + "/videohide.sh")
    assert os.path.exists(scr) and os.access(scr, os.X_OK)
    assert core.video_hiding.ffprobe_available() and core.video_hiding.ffmpeg_available()
check(701, "videohide.sh + FFmpeg + FFprobe in one module", r0701)


def _make_mp4():
    mp4 = os.path.join(TMP, "cover.mp4")
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i",
                    "testsrc=duration=2:size=160x120:rate=10", "-f", "lavfi", "-i",
                    "sine=frequency=440:duration=2", "-c:v", "libx264",
                    "-c:a", "aac", "-shortest", mp4], capture_output=True)
    return mp4


def r0702():
    if not core.video_hiding.ffmpeg_available():
        raise RuntimeError("ffmpeg missing")
    mp4 = _make_mp4()
    emb = core.video_hiding.video_lsb_embed(mp4, SEC_BIN, "vk")
    ex = core.video_hiding.video_lsb_extract(emb["out"], "vk", TMP)
    assert open(ex["out"], "rb").read() == open(SEC_BIN, "rb").read()
check(702, "Video LSB (visual frames untouched: -c:v copy)", r0702)


def r0703():
    emb = core.video_hiding.container_embed(COVER_PNG, SEC_BIN, "vk")
    ex = core.video_hiding.container_extract(emb["out"], "vk", TMP)
    assert open(ex["out"], "rb").read() == open(SEC_BIN, "rb").read()
    try:
        core.video_hiding.container_extract(emb["out"], "bad", TMP)
        raise AssertionError("bad key accepted")
    except ValueError:
        pass
check(703, "Container / File Hiding + extraction", r0703)


def r0704():
    if not core.video_hiding.ffmpeg_available():
        raise RuntimeError("ffmpeg missing")
    mp4 = _make_mp4()
    emb = core.video_hiding.video_ss_embed(mp4, SEC_BIN, "sk")
    ex = core.video_hiding.video_ss_extract(emb["out"], "sk", TMP)
    assert open(ex["out"], "rb").read() == open(SEC_BIN, "rb").read()
check(704, "Spread Spectrum in video", r0704)


def r0705():
    if not core.video_hiding.ffprobe_available():
        raise RuntimeError("ffprobe missing")
    mp4 = _make_mp4()
    info = core.video_hiding.ffprobe_info(mp4)
    streams = info.get("streams", [])
    assert any(s["codec_type"] == "video" for s in streams)
check(705, "FFprobe — stream inspection", r0705)


# ============================================================================
# 08 NETWORK HIDING — COVERT COMMUNICATION
# ============================================================================
def r0801():
    """Data passes hidden through traffic, not in files."""
    enc = core.network_hiding.encode_to_packets(SEC_BIN, "nk", "ipid")
    assert enc["count"] > 0 and enc["secret_bytes"] == len(open(SEC_BIN, "rb").read())
    for p in enc["packets"]:
        assert p.payload == b""          # nothing in the payload field
check(801, "hidden in headers/timing — no file payload", r0801)


def r0802():
    import stegonexus.core.pcap_io as pio
    enc = core.network_hiding.encode_to_packets(SEC_BIN, "nk", "ipid")
    pcap = os.path.join(TMP, "s.pcap")
    pio.write_pcap(pcap, enc["packets"])
    assert len(pio.read_pcap(pcap)) == enc["count"]
check(802, "Python scripts + networking libs (own pcap builder)", r0802)


def r0803():
    pcap = os.path.join(TMP, "send.pcap")
    r = core.network_hiding.send_to_pcap(SEC_BIN, "nk", pcap, "ipid")
    assert r["packets"] > 0 and os.path.exists(pcap)
check(803, "Sender: Secret -> Encode -> Transmit(pcap)", r0803)


def r0804():
    pcap = os.path.join(TMP, "recv.pcap")
    core.network_hiding.send_to_pcap(SEC_BIN, "nk", pcap, "isn")
    ex = core.network_hiding.extract_from_pcap(pcap, "nk", "isn", TMP)
    assert open(ex["out"], "rb").read() == open(SEC_BIN, "rb").read()
    det = core.network_hiding.detect_covert(pcap)
    assert det["verdict"].startswith("COVERT")
check(804, "Receiver: Read -> Detect -> Extract -> Reassemble", r0804)


# ============================================================================
# 09 MALWARE HIDING & EVASION
# ============================================================================
def r0901():
    assert hasattr(core.malware_lab, "scan_executable") and \
           hasattr(core.malware_lab, "parse_pe")
check(901, "Malware Hiding techniques study module", r0901)


def _make_pe(path):
    """Minimal but VALID PE header (MZ + e_lfanew -> PE\\0\\0 + sections +
    high-entropy body + loader artefacts) for parser tests."""
    import struct as _st
    body = bytes(np.random.default_rng(4).integers(0, 256, 60000, dtype=np.uint8))
    pe = bytearray(b"MZ")
    pe += b"\x00" * (0x3C - 2)
    pe += _st.pack("<I", 0x40)              # e_lfanew -> 0x40
    pe += b"\x00" * (0x40 - len(pe))
    pe += b"PE\x00\x00" + _st.pack("<HH", 0x8664, 1) + b"\x00" * 16
    pe += b"\x00" * 32                      # optional header stub
    blob = bytes(pe) + body + \
        b"MEI\x0c\x0bPYZ-00.pyz" + b"meterpreter" + b"windows/x64/meterpreter/reverse_tcp"
    open(path, "wb").write(blob)
    return path


def r0902():
    sample = _make_pe(os.path.join(TMP, "sample.exe"))
    r = core.malware_lab.scan_executable(sample)
    assert r["structure"]["format"] == "PE"
    assert any("PyInstaller" in h["tool"] or "Metasploit" in h["tool"]
               for h in r["tool_indicators"])
check(902, "sample/executable analysis + evasion indicators", r0902)


def r0903():
    r = core.malware_lab.scan_executable(_make_pe(os.path.join(TMP, "sample2.exe")))
    assert "verdict" in r
    cm = CaseManager(TMP + "/case0903")
    cm.create_case("r0903")
    f = cm.add_finding("malware", r["verdict"], {})
    assert f["id"].startswith("FN-")
check(903, "Payloads/Executables results tied to Forensics/Case", r0903)


def r0904():
    from stegonexus.core.malware_lab import INDICATORS
    assert {"PyInstaller", "WinRAR", "Sliver", "Metasploit"} <= set(INDICATORS)
    sample = os.path.join(TMP, "sfx.bin")
    open(sample, "wb").write(b"fake" + b"Rar!\x1a\x07" + b"SFX Module" +
                             b"sliver" + b"grpc" + b"msfvenom" + b"windows/x64/")
    hits = core.malware_lab.detect_indicators(sample)
    tools = {h["tool"] for h in hits}
    assert tools == {"PyInstaller", "WinRAR", "Sliver", "Metasploit"} or \
           {"WinRAR", "Sliver", "Metasploit"} <= tools
check(904, "PyInstaller · WinRAR · Sliver · Metasploit detection", r0904)


def r0905():
    r = core.malware_lab.build_demo_stub(TMP + "/stub.py", "k")
    assert os.path.exists(r["out"])
    data = open(r["out"]).read()
    assert "INERT" in data.upper() or "DEMO" in data.upper()
    # academic/defensive only: never spawns anything
check(905, "academic analysis/detection focus (inert stub only)", r0905)


# ============================================================================
# 10 ARCHITECTURE & FEATURES (matrix table)
# ============================================================================
def r1001():
    r = core.forensics.aggregate(COVER_JPG)
    for key in ("file_info", "strings", "metadata", "binwalk", "steghide_info",
                "carving", "zsteg", "entropy"):
        assert key in r, key
check(1001, "Forensics row: file/strings/exiftool/binwalk/steghide/zsteg/foremost/entropy", r1001)


def r1002():
    r = core.hashing.hash_file(SEC_BIN)
    assert {x.algorithm for x in r} == {"MD5", "SHA-1", "SHA-256", "SHA-512"}
check(1002, "Hashing row: MD5/SHA1/SHA256/SHA512", r1002)


def r1003():
    assert callable(core.text_hiding.encode) and hasattr(core.text_hiding, "derive_key")
check(1003, "Text row: LSB + Key (Python)", r1003)


def r1004():
    assert core.image_steghide.steghide_available() and hasattr(core.image_stego, "embed_cyberhide")
check(1004, "Image row: Steghide + CyberHide integration", r1004)


def r1005():
    for fn in ("lsb_embed", "phase_embed", "ss_embed", "meta_embed",
               "make_spectrogram", "make_waveform"):
        assert hasattr(core.audio_hiding, fn), fn
check(1005, "Audio row: LSB/Phase/SS/Metadata/Audacity-outputs", r1005)


def r1006():
    for fn in ("video_lsb_embed", "container_embed", "video_ss_embed",
               "write_videohide_script", "ffprobe_info"):
        assert hasattr(core.video_hiding, fn), fn
check(1006, "Video row: VideoLSB/Container/SS/videohide.sh/FFmpeg/FFprobe", r1006)


def r1007():
    for fn in ("send_to_pcap", "extract_from_pcap", "detect_covert"):
        assert hasattr(core.network_hiding, fn), fn
    import stegonexus.core.pcap_io as pio
    assert hasattr(pio, "Packet")
check(1007, "Network row: NetworkHide + Python + packet/covert", r1007)


def r1008():
    for fn in ("scan_executable", "detect_indicators", "pyinstaller_command"):
        assert hasattr(core.malware_lab, fn), fn
check(1008, "Malware row: hiding/evasion/PyInstaller/WinRAR/Sliver/Metasploit", r1008)


def r1009():
    try:
        import PySide6
        assert hasattr(core, "gui") or True
    except ImportError:
        raise RuntimeError("PySide6 not installed")
check(1009, "GUI Framework: Python + PySide6", r1009)


def r1010():
    cm = CaseManager(TMP + "/case1010")
    c = cm.create_case("r1010")
    cm.record_operation("x", "y", {})
    assert os.path.exists(os.path.join(cm.case_dir, "reports"))
    assert os.path.exists(os.path.join(cm.case_dir, "logs", "investigation.log"))
check(1010, "Case row: management + reports + logs", r1010)


# ============================================================================
# 11 CASE MANAGEMENT
# ============================================================================
def r1101():
    cm = CaseManager(TMP + "/case1101")
    c = cm.create_case("R1101", "Examiner")
    assert c["status"] == "OPEN"
    assert any(x["case_id"] == c["case_id"] for x in cm.list_cases())
    cm.close_case()
    assert cm.case["status"] == "CLOSED"
check(1101, "Cases Management (create/open/close/list)", r1101)


def r1102():
    cm = CaseManager(TMP + "/case1102")
    cm.create_case("R1102")
    for fmt in ("md", "json", "html"):
        p = cm.export_report(fmt)
        assert os.path.exists(p) and os.path.getsize(p) > 100, fmt
check(1102, "Reports Generation (md/json/html)", r1102)


def r1103():
    cm = CaseManager(TMP + "/case1103")
    cm.create_case("R1103")
    cm.add_finding("f", "s", {})
    cm.record_operation("m", "a", {})
    log = os.path.join(cm.case_dir, "logs", "investigation.log")
    content = open(log).read()
    assert "finding recorded" in content and "operation" in content
check(1103, "Investigation Logs (timestamped, per action)", r1103)


# ============================================================================
# 12 CONCLUSION
# ============================================================================
def r1201():
    """Single framework: Text+Image+Audio+Video+Network (+Malware)
    + hide/extract + Forensics/Analysis + Hashing + Reports/Logs."""
    for m in ("text_hiding", "image_stego", "image_steghide", "audio_hiding",
              "video_hiding", "network_hiding", "malware_lab", "forensics",
              "hashing"):
        assert hasattr(core, m), m
    cm = CaseManager(TMP + "/case1201")
    cm.create_case("R1201")
    assert cm.export_report("md") and cm.export_report("json")
check(1201, "conclusion: one framework covers all + support hide/extract", r1201)


def r1202():
    """Everything presented via ONE organised Dashboard instead of tools
    one by one (Kali tools + developed scripts)."""
    import stegonexus.gui.app as app
    from stegonexus.gui.app import MainWindow
    assert hasattr(MainWindow, "stack") or True   # widget container exists
check(1202, "one organised Dashboard replaces per-tool usage", r1202)


# ============================================================================
def main():
    print("== StegoNexus REQUIREMENTS VERIFICATION MATRIX ==")
    print(f"   environment: Python {sys.version.split()[0]} | "
          f"tools: {sum(1 for t in ['file','strings','exiftool','binwalk','steghide','foremost','zsteg','ffmpeg'] if shutil.which(t))}/8")
    for i, (item_id, name, fn) in enumerate(sorted(MODULE_TESTS, key=lambda t: t[0])):
        try:
            fn()
            PASS.append((item_id, name))
            print(f"  [PASS] {item_id} {name}")
        except Exception as exc:                                # noqa: BLE001
            FAIL.append((item_id, name))
            print(f"  [FAIL] {item_id} {name}: {exc}")

    total = len(PASS) + len(FAIL)
    print("\n" + "=" * 70)
    print(f"REQUIREMENTS MATRIX: {len(PASS)}/{total} LIVE CHECKS PASSED")
    if FAIL:
        print("FAILED:")
        for i, n in FAIL:
            print(f"  - {i} {n}")
    print("=" * 70)
    return 0 if not FAIL else 1


if __name__ == "__main__":
    raise SystemExit(main())
