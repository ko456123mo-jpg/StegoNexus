"""
Module 02 - Forensics & Analysis
================================================
Required tools: file, strings, exiftool, binwalk, steghide info, foremost,
zsteg, Shannon Entropy.
Expected result: aggregate all tool results in ONE interface, tie them to
the Case file, and allow saving into Reports / Logs.

Design:
  * Each external tool is wrapped and detected at runtime (Kali first).
  * A pure-Python fallback engine delivers the same checks when a tool is
    missing (magic sniffing, string extraction, EXIF via Pillow, signature
    scan/carving, PNG LSB statistics, entropy analysis).
  * aggregate() merges everything into one structured report that the
    Dashboard shows and the CaseManager persists (Reports/ + Logs/).
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from typing import Dict, List, Optional

from stegonexus.core import entropy

# ------------------------------------------------------------------------ #
# Tool detection / generic runner
# ------------------------------------------------------------------------ #
TOOLS = ["steghide", "exiftool", "binwalk", "foremost", "zsteg", "exiftool2"]


def tool_status() -> Dict[str, str]:
    return {t: ("INSTALLED" if shutil.which(t) else "missing") for t in
            ["file", "strings", "exiftool", "binwalk", "steghide", "foremost", "zsteg"]}


def _try_run(cmd: list, timeout: int = 300) -> Optional[str]:
    try:
        res = subprocess.run(cmd, capture_output=True, text=True,
                             timeout=timeout, errors="replace")
        out = (res.stdout or "") + (res.stderr or "")
        return out.strip() or None
    except Exception:
        return None


# ------------------------------------------------------------------------ #
# file: magic detection (external or built-in)
# ------------------------------------------------------------------------ #
MAGIC_MAP = [
    (b"\x89PNG\r\n\x1a\n", "PNG image"),
    (b"\xff\xd8\xff", "JPEG image"),
    (b"GIF87a", "GIF87a image"), (b"GIF89a", "GIF89a image"),
    (b"BM", "Windows bitmap (BMP)"),
    (b"%PDF", "PDF document"),
    (b"PK\x03\x04", "ZIP archive (also DOCX/XLSX/PPTX/JAR)"),
    (b"Rar!\x1a\x07", "RAR archive"),
    (b"\x7fELF", "ELF executable"),
    (b"MZ", "PE executable (Windows)"),
    (b"RIFF", "RIFF container (WAV/AVI)"),
    (b"OggS", "Ogg container"),
    (b"ID3", "MP3 audio (ID3 tag)"),
    (b"\x1f\x8b", "gzip compressed stream"),
    (b"BZh", "bzip2 compressed stream"),
    (b"\xfd7zXZ\x00", "xz compressed stream"),
    (b"wOFF", "WOFF font"), (b"\x00\x01\x00\x00", "TrueType font"),
    (b"SQLite format 3\x00", "SQLite database"),
    (b"\x7b\x5c\x72\x74\x66", "RTF document"),
    (b"{\\rtf", "RTF document"),
]


def file_magic(path: str) -> dict:
    """Determine the real file type from its header (magic bytes)."""
    with open(path, "rb") as fh:
        head = fh.read(512)
    for sig, desc in MAGIC_MAP:
        if head.startswith(sig):
            return {"tool": "file", "description": desc, "signature": sig.decode("latin-1")}
    # text heuristic
    if head[:1000].decode("utf-8", errors="ignore").isprintable():
        return {"tool": "file", "description": "ASCII/UTF-8 text"}
    return {"tool": "file", "description": "unknown binary data"}


def run_file(path: str) -> dict:
    if shutil.which("file"):
        out = _try_run(["file", "-b", path])
        if out:
            return {"tool": "file", "description": out}
    return file_magic(path)


# ------------------------------------------------------------------------ #
# strings: printable strings (external or built-in)
# ------------------------------------------------------------------------ #
PRINTABLE = re.compile(rb"[\x20-\x7e]{5,}")
UNICODE = re.compile(rb"(?:[\x20-\x7e]\x00){5,}")


def run_strings(path: str, min_len: int = 6, limit: int = 200) -> dict:
    if shutil.which("strings"):
        out = _try_run(["strings", "-n", str(min_len), path])
        if out is not None:
            lines = out.splitlines()
            return {"tool": "strings", "count": len(lines), "sample": lines[:limit]}
    data = open(path, "rb").read()
    found = [m.group().decode("latin-1") for m in PRINTABLE.finditer(data)]
    found += [m.group().decode("utf-16-le", errors="ignore")
              for m in UNICODE.finditer(data)]
    return {"tool": "strings (py)", "count": len(found), "sample": found[:limit]}


def find_interesting_strings(path: str) -> Dict[str, List[str]]:
    """Keyword triage used by the aggregated report."""
    data = open(path, "rb").read()
    keywords = {
        "stego_markers": [b"steghide", b"SNXI", b"SNAU", b"SNXV", b"SNNW", b"SNX1",
                          b"encrypted", b"hidden", b"secret"],
        "web": [b"http://", b"https://", b"GET /", b"User-Agent"],
        "scripting": [b"eval(", b"exec(", b"base64", b"subprocess", b"powershell"],
        "archives": [b"PK\x03\x04", b"Rar!", b"7z\xbc\xaf"],
    }
    out: Dict[str, List[str]] = {}
    for group, sigs in keywords.items():
        hits = []
        for sig in sigs:
            idx = data.find(sig)
            if idx >= 0:
                hits.append(f"{sig.decode('latin-1')} @ {idx}")
        if hits:
            out[group] = hits[:10]
    return out


# ------------------------------------------------------------------------ #
# exiftool: metadata (external or Pillow built-in)
# ------------------------------------------------------------------------ #
def run_exiftool(path: str) -> dict:
    if shutil.which("exiftool"):
        out = _try_run(["exiftool", "-j", path])
        if out:
            import json as _json
            try:
                arr = _json.loads(out)
                if arr:
                    return {"tool": "exiftool", "metadata": arr[0]}
            except Exception:
                return {"tool": "exiftool", "metadata": {"raw": out[:2000]}}
    try:
        from PIL import Image
        img = Image.open(path)
        return {"tool": "exiftool (py)", "metadata": {
            "format": img.format, "size": img.size, "mode": img.mode,
            "info_keys": list(dict(img.info).keys())[:10],
            "comment": str(img.info.get("comment", ""))[:300]}}
    except Exception:
        return {"tool": "exiftool", "metadata": {"note": "no metadata extractor available"}}


# ------------------------------------------------------------------------ #
# binwalk: embedded-signature scan (external or built-in)
# ------------------------------------------------------------------------ #
def run_binwalk(path: str) -> dict:
    # signatures that belong to the file's OWN compressed structure
    # (e.g. the zlib IDAT stream inside a PNG) are NOT embedded files
    BENIGN = re.compile(r"^Zlib compressed data|^PNG image|^JPEG image data|"
                        r"^gzip compressed data|^TIFF image|^ICO$", re.I)
    if shutil.which("binwalk"):
        out = _try_run(["binwalk", path])
        if out:
            findings = []
            for line in out.splitlines():
                m = re.match(r"^\s*(\d+)\s+0x([0-9A-Fa-f]+)\s+(.+)$", line)
                if m:
                    findings.append({"offset": int(m.group(1)),
                                     "hex": "0x" + m.group(2),
                                     "description": m.group(3).strip()})
            header_entries = [f for f in findings if f["offset"] == 0]
            findings = [f for f in findings if f["offset"] != 0
                        and not BENIGN.search(f["description"])]
            return {"tool": "binwalk", "results": findings,
                    "header_entries": header_entries,
                    "embedded_signatures": len(findings), "raw": out}
    # built-in signature scan across the whole file
    data = open(path, "rb").read()
    findings = []
    for sig, desc in MAGIC_MAP:
        start = 0
        while True:
            idx = data.find(sig, start)
            if idx < 0:
                break
            if idx != 0:                       # ignore the file's own header
                findings.append({"offset": idx, "type": desc,
                                 "signature": sig.decode("latin-1"),
                                 "description": desc})
            start = idx + 1
    return {"tool": "binwalk (py)", "results": findings,
            "embedded_signatures": len(findings)}


# ------------------------------------------------------------------------ #
# foremost: file carving (external or built-in signature carve)
# ------------------------------------------------------------------------ #
CARVABLE = [(b"\x89PNG\r\n\x1a\n", b"\x00\x00\x00\x00IEND", "PNG"),
            (b"\xff\xd8\xff", b"\xff\xd9", "JPEG"),
            (b"PK\x03\x04", b"\x50\x4b\x05\x06", "ZIP"),
            (b"ID3", b"\xff\xfb", "MP3")]


def run_foremost(path: str, out_dir: Optional[str] = None) -> dict:
    if shutil.which("foremost"):
        wd = out_dir or os.path.join(os.path.dirname(os.path.abspath(path)),
                                     "foremost_output")
        os.makedirs(wd, exist_ok=True)
        res = _try_run(["foremost", "-o", wd, "-t", "all", path])
        carved = 0
        if res:
            m = re.search(r"FILES?:\s+(\d+)", res or "")
            if m:
                carved = int(m.group(1))
        return {"tool": "foremost", "output_dir": wd, "carved": carved,
                "raw": (res or "")[-500:]}
    # built-in carver (offset 0 = the file itself, not an embedded carve)
    data = open(path, "rb").read()
    found = []
    for start_sig, end_sig, name in CARVABLE:
        s = data.find(start_sig)
        while s >= 0:
            if s != 0:
                e = data.find(end_sig, s + len(start_sig))
                if e >= 0:
                    found.append({"type": name, "offset": s,
                                  "size": e - s + len(end_sig)})
            s = data.find(start_sig, s + 1)
    return {"tool": "foremost (py)", "carved": len(found), "results": found}


# ------------------------------------------------------------------------ #
# zsteg: PNG LSB analysis (external or built-in)
# ------------------------------------------------------------------------ #
def run_zsteg(path: str) -> dict:
    if shutil.which("zsteg"):
        out = _try_run(["zsteg", path])
        if out is not None:
            lines = [l for l in out.splitlines() if l.strip()]
            # STRONG zsteg signals only: real payload descriptors
            # ("<wbStego size=…>", archive/image signatures) — the common
            # "file: OpenPGP" hits also appear on clean images, so they are
            # treated as weak evidence and do NOT raise the verdict.
            strong = re.compile(
                r"size=|wbStego|stego|\.zip|\.rar|\.png|\.jpe?g|gzip|zlib|"
                r"bzip2|7z|pdf file|\.pdf|\.gif|\.exe|Mz\b|PK\b", re.I)
            suspicious = []
            for l in lines:
                if ".." in l:
                    content = l.split("..", 1)[1].strip()
                    if content.startswith("<") or strong.search(content):
                        suspicious.append(l.strip()[:120])
            return {"tool": "zsteg", "results": lines[:80],
                    "suspicious_plane_hits": suspicious[:20],
                    "verdict": ("POSSIBLE EMBEDDED DATA - zsteg flagged "
                                "LSB planes with file/stego signatures"
                                if suspicious else
                                "no LSB stego signature reported by zsteg")}
    try:
        from PIL import Image
        img = Image.open(path).convert("RGB")
        data = list(img.getdata())
        bits = []
        for px in data:
            bits.extend([px[0] & 1, px[1] & 1, px[2] & 1])
        n = len(bits)
        ones = sum(bits)
        p1 = ones / n if n else 0.5
        import math
        e = 0.0
        if 0 < p1 < 1:
            e = -(p1 * math.log2(p1) + (1 - p1) * math.log2(1 - p1))
        from stegonexus.core.image_stego import MAGIC
        raw = bytes((sum(bits[i + j] << (7 - j) for j in range(8))
                     for i in range(0, len(bits) - 7, 8)))
        off = raw.find(MAGIC)
        return {"tool": "zsteg (py)", "lsb_entropy": round(e, 4),
                "lsb_bit_balance_p1": round(p1, 4),
                "magic_offset": off,
                "verdict": "HIDDEN MARKER FOUND in LSB plane"
                           if off >= 0 else "no obvious LSB marker"}
    except Exception as exc:
        return {"tool": "zsteg", "error": str(exc)}


# ------------------------------------------------------------------------ #
# steghide info (module 05 already wraps it; re-export for aggregation)
# ------------------------------------------------------------------------ #
def run_steghide_info(path: str, passphrase: Optional[str] = None) -> dict:
    from stegonexus.core import image_steghide
    try:
        return image_steghide.info(path, passphrase=passphrase)
    except Exception as exc:
        return {"tool": "steghide info", "error": str(exc)}


def run_cyberhide_probe(path: str) -> dict:
    """Search for the CyberHide LSB marker / LSB anomalies on images."""
    from stegonexus.core import image_stego
    try:
        res = image_stego.probe_cyberhide(path)
        return {"tool": "cyberhide probe", **res}
    except Exception as exc:
        return {"tool": "cyberhide probe", "error": str(exc),
                "verdict": "not an image"}


# ------------------------------------------------------------------------ #
# Aggregate everything into one interface
# ------------------------------------------------------------------------ #
def aggregate(path: str, entropy_window: int = 1024, entropy_threshold: float = 7.5,
              steghide_passphrase: Optional[str] = None) -> dict:
    """Run the full forensics pipeline on one file -> single structured result."""
    report: Dict[str, object] = {
        "file": os.path.abspath(path),
        "size_bytes": os.path.getsize(path),
        "tools_available": tool_status(),
    }
    report["file_info"] = run_file(path)
    report["strings"] = run_strings(path)
    report["interesting_strings"] = find_interesting_strings(path)
    report["metadata"] = run_exiftool(path)
    report["binwalk"] = run_binwalk(path)
    report["carving"] = run_foremost(path)
    report["zsteg"] = run_zsteg(path)
    report["steghide_info"] = run_steghide_info(path, steghide_passphrase)
    report["cyberhide_probe"] = run_cyberhide_probe(path)
    report["entropy"] = entropy.scan_file_regions(path, entropy_window,
                                                  threshold=entropy_threshold)
    report["verdict"], report["notes"] = _verdict(report)
    return report


# containers that are compressed BY DESIGN: high entropy is expected there
# and must not be treated as a hiding indicator
COMPRESSED_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".zip", ".rar",
                  ".7z", ".gz", ".xz", ".bz2", ".mp3", ".mp4", ".mkv",
                  ".avi", ".pdf", ".docx", ".xlsx", ".pptx", ".jar"}


def _is_compressed_container(path: str) -> bool:
    ext = os.path.splitext(path)[1].lower()
    if ext in COMPRESSED_EXT:
        return True
    with open(path, "rb") as fh:
        head = fh.read(16)
    return head.startswith((b"\x89PNG", b"\xff\xd8\xff", b"PK\x03\x04",
                            b"\x1f\x8b", b"Rar!", b"%PDF"))


def _verdict(r: dict):
    """Returns (verdict, notes). Notes are explanatory, not evidence."""
    parts, notes = [], []
    bw = r.get("binwalk", {}).get("results", []) or []
    if any(isinstance(f, dict) and f.get("offset", 0) > 0 for f in bw):
        parts.append("embedded signatures (binwalk)")
    if r.get("carving", {}).get("carved"):
        parts.append("carvable embedded signatures")
    z = r.get("zsteg", {}).get("verdict", "") or ""
    if "POSSIBLE" in z or "HIDDEN" in z:
        parts.append("zsteg LSB-plane hits")
    if "HIDDEN DATA DETECTED" in r.get("steghide_info", {}).get("verdict", ""):
        parts.append("steghide payload")
    probe = r.get("cyberhide_probe", {}) or {}
    if probe.get("indicators") or probe.get("magic_occurrences"):
        parts.append("LSB marker/entropy indicators (cyberhide probe)")
    if r.get("entropy", {}).get("suspicious_count"):
        if _is_compressed_container(r["file"]):
            notes.append("Shannon entropy is high because the container itself "
                         "is compressed (PNG/JPEG/…): not counted as evidence")
        else:
            parts.append("high-entropy regions")
    if r.get("metadata", {}).get("comment"):
        parts.append("comment metadata present")
    if not parts:
        return "NO STRONG HIDING INDICATORS", notes
    return "SUSPICIOUS: " + ", ".join(parts), notes


__all__ = ["aggregate", "tool_status", "run_file", "run_strings",
           "run_exiftool", "run_binwalk", "run_foremost", "run_zsteg",
           "run_steghide_info"]
