"""
Module 05b - Image Hiding: CyberHide-style AES-LSB (pure Python)
================================================================
Implements the same contract as the Steghide module (embed / extract /
info) in pure Python, so StegoNexus keeps working even when `steghide`
is not installed on the host (it is the Kali fallback module).

Method (CyberHide-style):
  * Secret file is encrypted with AES-256-CBC (PyCryptodome) using a key
    derived from the password (PBKDF2-HMAC-SHA256, 100k iterations).
  * A small authenticated header (MAGIC + IV + length + HMAC) is added.
  * Bits of the payload are *permuted* by a keyed PRNG (seeded from the
    derived key) and hidden in the Least Significant Bits of the RGB(A)
    channels of a lossless image (PNG / BMP / TIFF).

  Hiding    : Image + Secret File + Password -> Stego Image (PNG)
  Extraction: Stego Image + Password -> Original Secret File
  Forensics : probe() detects the SnexyMagIC marker without the password.
"""

from __future__ import annotations

import hashlib
import hmac
import io
import os
import random as _random
from typing import List, Optional, Tuple

from PIL import Image

try:  # AES hardware/software encryption
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad, unpad
    _HAVE_CRYPTO = True
except Exception:  # pragma: no cover - fallback path
    _HAVE_CRYPTO = False

from stegonexus.core.text_hiding import xor_crypt  # fallback cipher when no pycryptodome

MAGIC = b"SNXI"                 # StegoNexus CyberHide-style marker
VERSION = 1
MAX_CHANNELS_PER_PIXEL = 4


# ------------------------------------------------------------------------ #
# Key / cipher helpers
# ------------------------------------------------------------------------ #
def derive_key(password: str, salt: bytes = b"StegoNexus-CyberHide",
               iterations: int = 100_000) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt,
                               iterations, dklen=32)


def _build_payload(secret: bytes, password: str) -> bytes:
    """Encrypt + authenticate a secret file into the stego payload."""
    if _HAVE_CRYPTO:
        key = derive_key(password)
        iv = os.urandom(16)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        ct = cipher.encrypt(pad(secret, AES.block_size))
        mac = hmac.new(key, iv + ct, hashlib.sha256).digest()[:16]
        total = 4 + 1 + 16 + 4 + 16 + len(ct)     # full payload length
        payload = MAGIC + bytes([VERSION]) + iv + total.to_bytes(4, "big") + mac + ct
        return payload
    # reduced-security fallback (XOR keystream) - still key-protected
    ks = derive_key(password, b"StegoNexus-CyberHide-XOR", 50_000)
    body = xor_crypt(secret, ks)
    total = 4 + 1 + 16 + 4 + len(body)            # full payload length
    return MAGIC + bytes([VERSION | 0x80]) + b"\x00" * 16 + total.to_bytes(4, "big") + body


def _parse_payload(blob: bytes, password: str) -> Optional[bytes]:
    """Reverse of _build_payload; returns the original secret or None."""
    if len(blob) < 4 + 1 + 16 + 4 + 16 or blob[:4] != MAGIC:
        return None
    ver = blob[4]
    total = int.from_bytes(blob[21:25], "big")
    if total > len(blob):
        total = len(blob)
    if ver & 0x80 or not _HAVE_CRYPTO:
        ks = derive_key(password, b"StegoNexus-CyberHide-XOR", 50_000)
        body = blob[25:total]
        return xor_crypt(body, ks)
    mac = blob[25:41]
    iv = blob[5:21]
    ct = blob[41:total]
    if len(ct) % AES.block_size:
        return None
    key = derive_key(password)
    if not hmac.compare_digest(mac, hmac.new(key, iv + ct, hashlib.sha256).digest()[:16]):
        raise ValueError("HMAC verification failed -> WRONG PASSWORD or corrupted image")
    plain = unpad(AES.new(key, AES.MODE_CBC, iv).decrypt(ct), AES.block_size)
    return plain


# ------------------------------------------------------------------------ #
# Bit plumbing (keyed permutation of channel positions)
# ------------------------------------------------------------------------ #
def _channel_bit_stream(pixels: List[Tuple[int, ...]], nbits: int, seed: bytes) -> List[int]:
    """Extract `nbits` LSBs from pixel channels in keyed-permutation order."""
    channels: List[int] = []
    for px in pixels:
        channels.extend(list(px[:MAX_CHANNELS_PER_PIXEL]))
    # keyed permutation of channel slots
    rng = _random.Random(seed)
    order = list(range(len(channels)))
    for i in range(len(order) - 1, 0, -1):
        j = rng.randint(0, i)
        order[i], order[j] = order[j], order[i]
    return [channels[k] & 1 for k in order[:nbits]]


def _set_channel_bits(pixels: List[Tuple[int, ...]], bits: List[int], seed: bytes) -> List[Tuple[int, ...]]:
    """Set LSBs of pixel channels in the same keyed-permutation order."""
    flat: List[int] = []
    for px in pixels:
        flat.extend(list(px[:MAX_CHANNELS_PER_PIXEL]))
    rng = _random.Random(seed)
    order = list(range(len(flat)))
    for i in range(len(order) - 1, 0, -1):
        j = rng.randint(0, i)
        order[i], order[j] = order[j], order[i]
    for bit_pos, chan_pos in enumerate(order[:len(bits)]):
        flat[chan_pos] = (flat[chan_pos] & ~1) | bits[bit_pos]
    # reassemble pixels
    nch = len(pixels[0]) if pixels else 3
    out: List[Tuple[int, ...]] = []
    for i in range(0, len(flat), nch):
        out.append(tuple(flat[i:i + nch]))
    return out


def _bytes_to_bits(data: bytes) -> List[int]:
    return [(b >> s) & 1 for b in data for s in range(7, -1, -1)]


def _bits_to_bytes(bits: List[int]) -> bytes:
    out = bytearray()
    for i in range(0, len(bits) - 7, 8):
        byte = 0
        for b in bits[i:i + 8]:
            byte = (byte << 1) | b
        out.append(byte)
    return bytes(out)


# ------------------------------------------------------------------------ #
# Public API
# ------------------------------------------------------------------------ #
def embed_cyberhide(image_path: str, secret_path: str, password: str,
                    output_path: Optional[str] = None) -> dict:
    """Image + Secret File + Password -> Stego Image (lossless PNG)."""
    if not password:
        raise ValueError("A password is required")
    if not os.path.exists(image_path):
        raise FileNotFoundError(image_path)
    if not os.path.exists(secret_path):
        raise FileNotFoundError(secret_path)

    secret = open(secret_path, "rb").read()
    payload = _build_payload(secret, password)
    bits = _bytes_to_bits(payload)

    img = Image.open(image_path).convert("RGB")
    w, h = img.size
    pixels = list(img.getdata())
    capacity = len(pixels) * 3
    if len(bits) > capacity:
        raise ValueError(
            f"Secret too large: need {len(bits)} bits, image capacity "
            f"{capacity} bits (RGB LSB). Use a bigger image.")

    key = derive_key(password)
    stego_pixels = _set_channel_bits(pixels, bits, key[:16])
    stego_img = Image.new("RGB", (w, h))
    stego_img.putdata(stego_pixels)

    out = output_path or os.path.join(
        os.path.dirname(os.path.abspath(image_path)),
        os.path.splitext(os.path.basename(image_path))[0] + "_stego.png")
    stego_img.save(out, "PNG")

    return {
        "tool": "cyberhide", "ok": True,
        "cipher": "AES-256-CBC + HMAC-SHA256" if _HAVE_CRYPTO else "XOR keystream (fallback)",
        "stego_image": out,
        "image_size": f"{w}x{h}",
        "capacity_bits": capacity,
        "payload_bits": len(bits),
        "payload_bytes": len(payload),
        "secret_bytes": len(secret),
        "embed_ratio_pct": round(100.0 * len(bits) / capacity, 2),
    }


def extract_cyberhide(stego_image: str, password: str,
                      output_dir: Optional[str] = None) -> dict:
    """Stego Image + Password -> Original Secret File."""
    if not password:
        raise ValueError("A password is required")
    img = Image.open(stego_image).convert("RGB")
    pixels = list(img.getdata())
    key = derive_key(password)

    # read enough bits to parse the header (magic+ver+iv+len = 25 bytes)
    header_bits = _channel_bit_stream(pixels, 25 * 8, key[:16])
    header = _bits_to_bytes(header_bits)
    if header[:4] != MAGIC:
        raise ValueError("No CyberHide payload found. Wrong password or image not stego.")
    total = int.from_bytes(header[21:25], "big")
    cap = len(pixels) * 3 // 8
    if total > cap:
        raise ValueError("Corrupted header: declared payload exceeds image capacity.")
    all_bits = _channel_bit_stream(pixels, total * 8, key[:16])
    blob = _bits_to_bytes(all_bits)
    secret = _parse_payload(blob, password)
    if secret is None:
        raise ValueError("Could not parse payload (wrong password / corrupted image)")

    out_dir = output_dir or os.path.dirname(os.path.abspath(stego_image))
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "extracted_secret.bin")
    with open(out, "wb") as fh:
        fh.write(secret)
    return {"tool": "cyberhide", "ok": True, "secret_file": out,
            "secret_bytes": len(secret), "exists": True}


def probe_cyberhide(stego_image: str) -> dict:
    """Forensic probe: detect hidden data WITHOUT the password."""
    img = Image.open(stego_image).convert("RGB")
    pixels = list(img.getdata())

    # 1) keyed stream would need the key; for detection we scan the *raw*
    #    (unpermuted) LSB stream for the magic pattern as a heuristic, and
    #    measure LSB statistics.
    flat: List[int] = []
    for px in pixels:
        flat.extend(px[:3])
    raw_bits = [c & 1 for c in flat]

    # heuristic A: magic appears in raw LSBs
    raw_bytes = _bits_to_bytes(raw_bits)
    found = raw_bytes.find(MAGIC)
    nested = raw_bytes.count(MAGIC)

    # heuristic B: LSB entropy (NOTE ONLY — natural photos have noise-like
    # LSBs with entropy ~1.0, so it must never raise the verdict)
    n = len(raw_bits)
    ones = sum(raw_bits)
    p1 = ones / n if n else 0.0
    p0 = 1.0 - p1
    import math
    lsb_entropy = 0.0
    if p1 > 0 and p0 > 0:
        lsb_entropy = -(p0 * math.log2(p0) + p1 * math.log2(p1))

    # heuristic C: trailing data after IEND for PNG (real evidence of append)
    trailing = 0
    raw = open(stego_image, "rb").read()
    idx = raw.rfind(b"IEND")
    if idx >= 0:
        trailing = len(raw) - idx - 8

    strong = []
    if found >= 0:
        strong.append("MAGIC MARKER FOUND in raw LSB stream (probable hidden payload)")
    if trailing > 64:
        strong.append(f"{trailing} trailing bytes after IEND chunk (appended data)")
    notes = []
    if lsb_entropy > 0.985:
        notes.append(f"note: LSB entropy {lsb_entropy:.4f} is high, but natural "
                     "photos are usually noise-like there (not evidence)")

    return {
        "tool": "cyberhide", "ok": True,
        "image": stego_image,
        "raw_lsb_magic_offset": found,
        "magic_occurrences": nested,
        "lsb_entropy": round(lsb_entropy, 4),
        "trailing_bytes": trailing,
        "indicators": strong,
        "notes": notes,
        "verdict": ("HIDDEN DATA INDICATORS DETECTED" if strong
                    else "NO CONFIRMED INDICATORS (keyed LSB payloads are hidden "
                         "behind the permutation; detection needs the key)"),
    }


def capacity(image_path: str) -> dict:
    """Max payload capacity (bytes) for a cover image."""
    img = Image.open(image_path)
    w, h = img.size
    bits = w * h * 3
    return {"image": image_path, "size": f"{w}x{h}",
            "capacity_bytes": bits // 8, "capacity_bits": bits,
            "format": img.format}


__all__ = ["embed_cyberhide", "extract_cyberhide", "probe_cyberhide",
           "capacity", "derive_key", "MAGIC"]
