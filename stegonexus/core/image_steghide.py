"""
Module 05a - Image Hiding: Steghide (+ CyberHide-style AES-LSB integration)
==========================================================================
Required (from the project sheet):
  Hiding     : Image + Secret File + Password -> Steghide -> Stego Image
  Extraction : Stego Image + Password -> Steghide -> Original Secret File
  plus CyberHide integration (AES-encrypted LSB hiding in images).

This module wraps `steghide` when it is installed (Kali: apt install
steghide) *and* provides a pure-Python fallback implementing the same
contract (embed/extract/info) so the Dashboard works everywhere.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from typing import Optional, Tuple

from stegonexus.core import image_stego  # pure-Python fallback + CyberHide mode


# ----------------------------------------------------------------------- #
# External tool detection
# ----------------------------------------------------------------------- #
def steghide_available() -> bool:
    return shutil.which("steghide") is not None


def _run(cmd: list, timeout: int = 300) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


# ----------------------------------------------------------------------- #
# Primary API used by the Dashboard
# ----------------------------------------------------------------------- #
def embed(image_path: str, secret_path: str, password: str,
          output_path: Optional[str] = None, tool: str = "auto") -> dict:
    """
    Image + Secret File + Password -> Stego Image.
    tool: 'auto' | 'steghide' | 'cyberhide' (pure-Python AES-LSB fallback).
    """
    if tool not in ("auto", "steghide", "cyberhide"):
        raise ValueError("tool must be 'auto', 'steghide' or 'cyberhide'")
    if tool == "auto":
        tool = "steghide" if steghide_available() else "cyberhide"

    if tool == "steghide":
        return _steghide_embed(image_path, secret_path, password, output_path)
    return image_stego.embed_cyberhide(image_path, secret_path, password, output_path)


def extract(stego_image: str, password: str, output_dir: Optional[str] = None,
            tool: str = "auto") -> dict:
    """Stego Image + Password -> Original Secret File."""
    if tool not in ("auto", "steghide", "cyberhide"):
        raise ValueError("tool must be 'auto', 'steghide' or 'cyberhide'")
    if tool == "auto":
        tool = "steghide" if steghide_available() else "cyberhide"

    if tool == "steghide":
        return _steghide_extract(stego_image, password, output_dir)
    return image_stego.extract_cyberhide(stego_image, password, output_dir)


def info(image_path: str, tool: str = "auto",
         passphrase: Optional[str] = None) -> dict:
    """Inspect an image for embedded data (steghide info or fallback scan)."""
    if tool == "auto":
        tool = "steghide" if steghide_available() else "cyberhide"
    if tool == "steghide":
        return _steghide_info(image_path, passphrase)
    return image_stego.probe_cyberhide(image_path)


# ----------------------------------------------------------------------- #
# Steghide wrappers (Kali)
# ----------------------------------------------------------------------- #
def _steghide_embed(image_path: str, secret_path: str, password: str,
                    output_path: Optional[str]) -> dict:
    if not steghide_available():
        raise RuntimeError("steghide is not installed (sudo apt install steghide)")
    # steghide rewrites the cover file in place -> work on a copy
    out = output_path or os.path.join(
        os.path.dirname(os.path.abspath(image_path)),
        os.path.splitext(os.path.basename(image_path))[0] + "_stego.jpg")
    shutil.copyfile(image_path, out)
    cmd = ["steghide", "embed", "-cf", out, "-ef", secret_path,
           "-p", password, "-f", "-z", "9"]
    res = _run(cmd)
    if res.returncode != 0:
        raise RuntimeError(f"steghide failed: {res.stderr.strip() or res.stdout.strip()}")
    return {"tool": "steghide", "ok": True, "stego_image": out,
            "message": res.stdout.strip() or "embedding complete"}


def _steghide_extract(stego_image: str, password: str,
                      output_dir: Optional[str]) -> dict:
    if not steghide_available():
        raise RuntimeError("steghide is not installed (sudo apt install steghide)")
    out_dir = output_dir or os.path.dirname(os.path.abspath(stego_image))
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, "extracted_secret.bin")
    cmd = ["steghide", "extract", "-sf", stego_image, "-p", password,
           "-xf", out_file, "-f"]
    res = _run(cmd)
    if res.returncode != 0:
        raise RuntimeError(f"steghide failed: {res.stderr.strip() or res.stdout.strip()}")
    return {"tool": "steghide", "ok": True, "secret_file": out_file,
            "exists": os.path.exists(out_file),
            "size": os.path.getsize(out_file) if os.path.exists(out_file) else 0}


def _steghide_info(image_path: str, passphrase: Optional[str] = None) -> dict:
    """
    Forensic `steghide info`:
      * WITH the correct passphrase -> full details of the embedded file
        (name, size, encryption, compression) => confirmed HIDDEN.
      * WITHOUT a passphrase -> steghide cannot reveal whether data exists
        (verified: it requests a passphrase for clean AND stego files, and
        prints the same failure message for both). We report INDETERMINATE
        honestly instead of raising a false positive.
    """
    if not steghide_available():
        raise RuntimeError("steghide is not installed (sudo apt install steghide)")
    cmd = ["steghide", "info", image_path]
    if passphrase:
        cmd += ["-p", passphrase]
    res = _run(cmd)
    text = res.stdout + res.stderr
    parsed = {
        "tool": "steghide",
        "passphrase_provided": bool(passphrase),
        "embedded_file": None,
        "size_bytes": None,
        "encryption": None,
        "verdict": "NO CONFIRMATION - steghide requires the passphrase to "
                   "confirm embedded data (run again with the Password field)",
        "raw": text.strip(),
    }
    if "embedded file" in text:
        m = re.search(r'embedded file "([^"]+)"', text)
        s = re.search(r"size:\s*([\d.]+)\s*(\w+)", text)
        e = re.search(r"encryption:\s*([^\n]+)", text)
        parsed.update({
            "embedded_file": m.group(1) if m else None,
            "size_bytes": s.group(0) if s else None,
            "encryption": e.group(1).strip() if e else None,
            "verdict": "HIDDEN DATA DETECTED - steghide payload present",
        })
    elif passphrase:
        parsed["verdict"] = ("NO EMBEDDED DATA CONFIRMED (clean file, or the "
                             "passphrase is incorrect)")
    return parsed


def status() -> dict:
    """Status used by the Dashboard / case creation."""
    avail = steghide_available()
    return {
        "steghide": "INSTALLED" if avail else "NOT INSTALLED (fallback: CyberHide-style AES-LSB)",
        "fallback_available": True,
        "mode": "steghide" if avail else "cyberhide",
        "detail": build_system_json(),
    }


def build_system_json() -> str:
    """CyberHide-style manifest embedded with the payload (interoperability aid)."""
    return json.dumps({"format": "CybHide-AES-LSB", "version": "1.0", "app": "StegoNexus"},
                      separators=(",", ":"))
