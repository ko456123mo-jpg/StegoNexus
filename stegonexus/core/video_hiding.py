"""
Module 07 - Video Hiding
========================
Required: VideoHide module (videohide.sh + FFprobe + FFmpeg),
          Video LSB, Container / File Hiding, Spread Spectrum, Streams.

Architecture mirrors the classic videohide.sh flow:
  1. ffprobe reads the video streams (codec / bitrate / duration).
  2. ffmpeg extracts the audio track to a lossless WAV.
  3. The secret is hidden in the audio (Video LSB or Spread Spectrum)
     using the StegoNexus audio engine.
  4. ffmpeg muxes the stego audio back into the video (new MP4).

When ffmpeg is unavailable, the module can still embed/extract in plain
WAV (fallback) and always supports Container / File Hiding (append with a
keyed, size-tagged container footer) with pure Python.
"""

from __future__ import annotations

import json
import os
import shutil
import struct
import subprocess
import tempfile
from typing import Optional

from stegonexus.core import audio_hiding

from stegonexus.core.text_hiding import derive_key, xor_crypt

CFOOTER = b"SNXV"               # container hiding footer magic
CFOOTER_LEN = 24


# ------------------------------------------------------------------------ #
# Tool detection
# ------------------------------------------------------------------------ #
def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def ffprobe_available() -> bool:
    return shutil.which("ffprobe") is not None


def _run(cmd: list, timeout: int = 600) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


# ------------------------------------------------------------------------ #
# ffprobe: stream information
# ------------------------------------------------------------------------ #
def ffprobe_info(video_path: str) -> dict:
    """Streams / metadata via ffprobe (or a minimal Python MP4 fallback)."""
    if ffprobe_available():
        res = _run(["ffprobe", "-v", "quiet", "-print_format", "json",
                    "-show_format", "-show_streams", video_path])
        if res.returncode == 0:
            data = json.loads(res.stdout)
            streams = [{
                "index": s.get("index"),
                "codec_type": s.get("codec_type"),
                "codec_name": s.get("codec_name"),
                "width": s.get("width"), "height": s.get("height"),
                "bit_rate": s.get("bit_rate"), "duration": s.get("duration"),
                "sample_rate": s.get("sample_rate"),
            } for s in data.get("streams", [])]
            return {"tool": "ffprobe", "ok": True, "streams": streams,
                    "format": data.get("format", {})}
    # ---- pure-python fallback: walk MP4 boxes' names --------------------
    boxes = _walk_boxes(video_path)
    return {"tool": "python-fallback", "ok": True, "boxes": boxes,
            "streams": [{"codec_type": "unknown", "note": "install ffmpeg for deep stream analysis"}],
            "size_bytes": os.path.getsize(video_path)}


def _walk_boxes(path: str, limit: int = 40):
    out = []
    try:
        with open(path, "rb") as fh:
            pos = 0
            fh.seek(0, 2)
            total = fh.tell()
            fh.seek(0)
            while pos + 8 <= total and len(out) < limit:
                fh.seek(pos)
                head = fh.read(8)
                if len(head) < 8:
                    break
                size = struct.unpack(">I", head[:4])[0]
                btype = head[4:8].decode("latin-1")
                if size == 1:
                    size = struct.unpack(">Q", fh.read(8))[0]
                if size == 0:
                    size = total - pos
                out.append({"box": btype, "offset": pos, "size": size})
                if size < 8:
                    break
                pos += size
    except Exception as exc:                                    # pragma: no cover
        out = [{"error": str(exc)}]
    return out


# ------------------------------------------------------------------------ #
# ffmpeg helpers: extract audio to WAV / mux WAV back into the video
# ------------------------------------------------------------------------ #
def extract_audio_track(video_path: str, out_wav: str) -> dict:
    if not ffmpeg_available():
        raise RuntimeError("ffmpeg is not installed (Kali: sudo apt install ffmpeg)")
    res = _run(["ffmpeg", "-y", "-i", video_path, "-vn", "-ac", "1",
                "-ar", "44100", "-acodec", "pcm_s16le", out_wav])
    if res.returncode != 0:
        raise RuntimeError(f"ffmpeg audio extraction failed: {res.stderr.strip()[-400:]}")
    return {"ok": True, "wav": out_wav}


def mux_audio_track(video_path: str, stego_wav: str, out_video: str) -> dict:
    """
    Re-mux with the video stream COPIED and the audio kept as LOSSLESS PCM
    (MKV container). Lossy encoders (AAC) re-quantise the samples and
    destroy LSB-embedded payloads — PCM keeps every bit intact.
    """
    if not ffmpeg_available():
        raise RuntimeError("ffmpeg is not installed (Kali: sudo apt install ffmpeg)")
    res = _run(["ffmpeg", "-y", "-i", video_path, "-i", stego_wav,
                "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                "-c:a", "pcm_s16le", out_video])
    if res.returncode != 0:
        raise RuntimeError(f"ffmpeg muxing failed: {res.stderr.strip()[-400:]}")
    return {"ok": True, "video": out_video}


# ------------------------------------------------------------------------ #
# Video LSB  (secret -> audio track -> LSB -> re-mux)
# ------------------------------------------------------------------------ #
def video_lsb_embed(video_path: str, secret_path: str, key: str,
                    out_path: Optional[str] = None) -> dict:
    if not ffmpeg_available():
        raise RuntimeError("Video LSB needs ffmpeg. Install it (Kali: sudo apt install ffmpeg).")
    with tempfile.TemporaryDirectory() as tmp:
        wav = os.path.join(tmp, "audio.wav")
        extract_audio_track(video_path, wav)
        stego_wav = os.path.join(tmp, "stego.wav")
        res = audio_hiding.lsb_embed(wav, secret_path, key, out_path=stego_wav)
        out = out_path or os.path.join(
            os.path.dirname(os.path.abspath(video_path)),
            os.path.splitext(os.path.basename(video_path))[0] + "_vstego.mkv")
        mux_audio_track(video_path, stego_wav, out)
    return {"method": "Video LSB (audio-track Least Significant Bits)", "ok": True,
            "out": out, **{k: v for k, v in res.items() if k in ("payload_bytes", "secret_bytes")}}


def video_lsb_extract(video_path: str, key: str, out_dir: Optional[str] = None) -> dict:
    if not ffmpeg_available():
        raise RuntimeError("Video LSB needs ffmpeg. Install it (Kali: sudo apt install ffmpeg).")
    with tempfile.TemporaryDirectory() as tmp:
        wav = os.path.join(tmp, "audio.wav")
        extract_audio_track(video_path, wav)
        out = out_dir or os.path.dirname(os.path.abspath(video_path))
        return audio_hiding.lsb_extract(wav, key, out_dir=out)


def video_ss_embed(video_path: str, secret_path: str, key: str,
                   out_path: Optional[str] = None) -> dict:
    """Spread Spectrum hiding in the video's audio track."""
    if not ffmpeg_available():
        raise RuntimeError("Spread Spectrum in video needs ffmpeg.")
    with tempfile.TemporaryDirectory() as tmp:
        wav = os.path.join(tmp, "audio.wav")
        extract_audio_track(video_path, wav)
        stego_wav = os.path.join(tmp, "stego.wav")
        res = audio_hiding.ss_embed(wav, secret_path, key, out_path=stego_wav)
        out = out_path or os.path.join(
            os.path.dirname(os.path.abspath(video_path)),
            os.path.splitext(os.path.basename(video_path))[0] + "_vss.mkv")
        mux_audio_track(video_path, stego_wav, out)
    return {"method": "Video Spread Spectrum (DSSS on audio track)", "ok": True, "out": out}


def video_ss_extract(video_path: str, key: str, out_dir: Optional[str] = None) -> dict:
    if not ffmpeg_available():
        raise RuntimeError("Spread Spectrum in video needs ffmpeg.")
    with tempfile.TemporaryDirectory() as tmp:
        wav = os.path.join(tmp, "audio.wav")
        extract_audio_track(video_path, wav)
        out = out_dir or os.path.dirname(os.path.abspath(video_path))
        return audio_hiding.ss_extract(wav, key, out_dir=out)


# ------------------------------------------------------------------------ #
# Container / File Hiding  (append-after-container with keyed footer)
# ------------------------------------------------------------------------ #
def container_embed(cover_path: str, secret_path: str, key: str,
                    out_path: Optional[str] = None) -> dict:
    """Append an encrypted secret to the container file (mp4/zip/any)."""
    if not key:
        raise ValueError("A key is required")
    secret = open(secret_path, "rb").read()
    ks = derive_key(key, b"StegoNexus-Container", 60_000)
    body = xor_crypt(secret, ks)
    footer = CFOOTER + len(body).to_bytes(4, "big") + ks[:16]
    cover = open(cover_path, "rb").read()
    out = out_path or os.path.join(
        os.path.dirname(os.path.abspath(cover_path)),
        os.path.splitext(os.path.basename(cover_path))[0] + "_container.bin")
    with open(out, "wb") as fh:
        fh.write(cover + body + footer)
    return {"method": "Container / File Hiding (append + keyed footer)", "ok": True,
            "out": out, "secret_bytes": len(secret),
            "footer_offset": len(cover) + len(body)}


def container_extract(container_path: str, key: str,
                      out_dir: Optional[str] = None) -> dict:
    if not key:
        raise ValueError("A key is required")
    ks = derive_key(key, b"StegoNexus-Container", 60_000)
    data = open(container_path, "rb").read()
    idx = data.rfind(CFOOTER)
    if idx < 0 or idx + CFOOTER_LEN > len(data):
        raise ValueError("No StegoNexus container footer found (not a stego container)")
    size = int.from_bytes(data[idx + 4:idx + 8], "big")
    sig = data[idx + 8:idx + 24]
    if sig != ks[:16]:
        raise ValueError("Key mismatch: footer signature does not match the key")
    body = data[idx - size:idx]
    secret = xor_crypt(body, ks)
    out_dir = out_dir or os.path.dirname(os.path.abspath(container_path))
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "extracted_secret.bin")
    open(out, "wb").write(secret)
    return {"method": "Container extraction", "ok": True, "out": out,
            "secret_bytes": len(secret), "footer_offset": idx}


# ------------------------------------------------------------------------ #
# videohide.sh script generation (the course reference script)
# ------------------------------------------------------------------------ #
def write_videohide_script(path: Optional[str] = None) -> str:
    """Materialise the classic videohide.sh workflow as a bash script."""
    script = r"""#!/usr/bin/env bash
# ============================================================
# videohide.sh - Video Hide / Reveal  (StegoNexus VideoHide module)
# Flow: ffprobe -> ffmpeg audio extraction -> audio LSB/SS hiding
#       -> ffmpeg re-mux (streams preserved with -c:v copy)
# Usage:
#   ./videohide.sh hide <cover.mp4> <secret.bin> <key> <out.mp4>
#   ./videohide.sh reveal <stego.mp4> <key> <out.bin>
# ============================================================
set -euo pipefail
CMD="${1:-}"; shift || true

hide() {
  VIDEO="$1"; SECRET="$2"; KEY="$3"; OUT="$4"
  TMP="$(mktemp -d)"
  echo "[*] ffprobe: inspecting streams..."
  ffprobe -v error -show_streams "$VIDEO" || true
  echo "[*] extracting audio track to WAV..."
  ffmpeg -y -i "$VIDEO" -vn -ac 1 -ar 44100 -acodec pcm_s16le "$TMP/a.wav"
  echo "[*] hiding in audio LSB..."
  python3 - "$TMP/a.wav" "$SECRET" "$KEY" "$TMP/s.wav" <<'PY'
import sys
from stegonexus.core import audio_hiding
audio_hiding.lsb_embed(sys.argv[1], sys.argv[2], sys.argv[3], out_path=sys.argv[4])
PY
  echo "[*] re-muxing stego audio into video (PCM keeps the LSB payload intact)"
  ffmpeg -y -i "$VIDEO" -i "$TMP/s.wav" -map 0:v -map 1:a -c:v copy -c:a pcm_s16le "$OUT"
  rm -rf "$TMP"
  echo "[+] stego video written: $OUT"
}

reveal() {
  VIDEO="$1"; KEY="$2"; OUT="$3"
  TMP="$(mktemp -d)"
  echo "[*] extracting audio track..."
  ffmpeg -y -i "$VIDEO" -vn -ac 1 -ar 44100 -acodec pcm_s16le "$TMP/a.wav"
  echo "[*] extracting hidden data..."
  python3 - "$TMP/a.wav" "$KEY" "$OUT" <<'PY'
import sys
from stegonexus.core import audio_hiding
audio_hiding.lsb_extract(sys.argv[1], sys.argv[2], out_dir=__import__('os').path.dirname(sys.argv[3]))
PY
  rm -rf "$TMP"
  echo "[+] recovered file: $OUT"
}

case "$CMD" in
  hide)   hide "$@";;
  reveal) reveal "$@";;
  *) echo "usage: $0 {hide|reveal} ..."; exit 1;;
esac
"""
    out = path or os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../videohide.sh")
    out = os.path.abspath(out)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(script)
    os.chmod(out, 0o755)
    return out


__all__ = ["ffprobe_info", "extract_audio_track", "mux_audio_track",
           "video_lsb_embed", "video_lsb_extract", "video_ss_embed",
           "video_ss_extract", "container_embed", "container_extract",
           "write_videohide_script", "ffmpeg_available", "ffprobe_available"]
