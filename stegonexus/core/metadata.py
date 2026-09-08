"""
Metadata Tool — View & Inject (متطلب: أداة عرض البيانات الوصفية وأيضاً حقنها)
=============================================================================
* View  : exiftool (Kali) or Pillow fallback — all metadata of a file.
* Inject: write Comment/Artist metadata INTO files:
    - exiftool (Kali): writes without touching the original (-o out)
    - Pillow fallback: PNG tEXt chunk (Comment/Author) or JPEG COM segment
  Audio metadata injection (RIFF LIST-INFO ICMT) lives in audio_hiding
  (meta_embed/meta_extract) — this module covers images/binary containers.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from typing import Optional


def exiftool_available() -> bool:
    return shutil.which("exiftool") is not None


def view_metadata(path: str) -> dict:
    """View ALL metadata of a file (exiftool first, Pillow fallback)."""
    from stegonexus.core import forensics
    return forensics.run_exiftool(path)


def _run(cmd: list, timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def inject_metadata(path: str, comment: str, out_path: Optional[str] = None,
                    author: Optional[str] = None, tool: str = "auto") -> dict:
    """
    Inject metadata (Comment + optional Author) into an image/container.
      path     : the original file (never modified)
      comment  : the data to inject (required)
      out_path : output file (default: <name>_meta.ext next to the original)
      author   : optional Artist field
      tool     : 'auto' | 'exiftool' | 'pillow'
    """
    if not comment.strip():
        raise ValueError("The metadata (comment) to inject must not be empty")
    if tool not in ("auto", "exiftool", "pillow"):
        raise ValueError("tool must be 'auto', 'exiftool' or 'pillow'")
    if tool == "auto":
        tool = "exiftool" if exiftool_available() else "pillow"

    ext = os.path.splitext(path)[1] or ".bin"
    stem = os.path.splitext(os.path.basename(path))[0]
    out = out_path or os.path.join(
        os.path.dirname(os.path.abspath(path)), stem + "_meta" + ext)
    if not out_path and os.path.exists(out):   # auto-pick a free name
        i = 1
        while os.path.exists(out):
            out = os.path.join(os.path.dirname(os.path.abspath(path)),
                               f"{stem}_meta{i}{ext}")
            i += 1

    if tool == "exiftool":
        cmd = ["exiftool", f"-Comment={comment}"]
        if author:
            cmd.append(f"-Artist={author}")
        cmd += ["-o", out, path]
        res = _run(cmd)
        if res.returncode != 0:
            raise RuntimeError(f"exiftool failed: {res.stderr.strip()[:300]}")
        method = "exiftool (IFD/tEXt metadata write)"
    else:
        from PIL import Image, PngImagePlugin
        img = Image.open(path)
        if img.format == "PNG":
            meta = PngImagePlugin.PngInfo()
            meta.add_text("Comment", comment)
            if author:
                meta.add_text("Author", author)
            img.convert("RGB").save(out, "PNG", pnginfo=meta)
            method = "Pillow (PNG tEXt chunks)"
        elif img.format == "JPEG":
            img.convert("RGB").save(out, "JPEG", quality=95,
                                    comment=comment.encode("utf-8")[:65000])
            method = "Pillow (JPEG COM segment)"
        else:
            raise ValueError("Pillow fallback supports PNG/JPEG (use exiftool "
                             "for other formats)")

    v = view_metadata(out)
    meta = v.get("metadata", {})
    text = str(meta)
    if isinstance(meta, dict):
        keys = ("Comment", "comment", "Author", "Artist", "ICMT", "Description")
        lines = [f"{k}: {meta[k]}" for k in keys
                 if k in meta and str(meta[k]).strip()]
        preview = "\n".join(lines) if lines else text[:500]
    else:
        preview = text[:500]
    return {
        "ok": True, "tool": tool, "method": method, "out": out,
        "comment": comment, "author": author or "",
        "verified": comment[:40] in text or comment in text,
        "view_preview": preview,
    }


def extract_metadata_text(path: str) -> str:
    """Convenience: return the Comment/Description metadata found (if any)."""
    try:
        m = view_metadata(path).get("metadata", {}) or {}
    except Exception:
        return ""
    if isinstance(m, str):
        return m[:500]
    for key in ("Comment", "comment", "Description", "description", "ICMT"):
        val = m.get(key)
        if isinstance(val, str) and val.strip():
            return val
    return ""


__all__ = ["view_metadata", "inject_metadata", "extract_metadata_text",
           "exiftool_available"]
