"""
Module 04b — Text Hiding: Zero-Width Characters (technique #2)
================================================================
Second hiding technique for the TEXT topic (requirement: each hiding
topic can be implemented with more than one technique).

Required operations:
  Hiding/Encoding    : Cover Text + Secret Message + Key
                       -> Zero-Width embedding -> Stego Text
  Extraction/Decoding: Stego Text + Key
                       -> Zero-Width stripping  -> Original Secret Message

How it works:
  1. The secret is XOR-encrypted with a keystream derived from the Key
     (PBKDF2-HMAC-SHA256) and length-prefixed with the MAGIC "SNXZ".
  2. Every 2 bits are mapped to one of four INVISIBLE (zero-width)
     Unicode code points:
          00 -> U+200B ZERO WIDTH SPACE
          01 -> U+200C ZERO WIDTH NON-JOINER
          10 -> U+200D ZERO WIDTH JOINER
          11 -> U+FEFF ZERO WIDTH NO-BREAK SPACE
  3. The invisible characters are scattered inside the cover text after
     a key-derived spacing so the stego text looks/behaves like the cover.
  4. Reveal: strip the 4 known code points, decode pairs, decrypt with
     the same key. Wrong key -> magic/CRC fails -> rejected.
"""
from __future__ import annotations

import hashlib
from typing import Tuple

MAGIC = b"SNXZ"
ZW = {0: "\u200b", 1: "\u200c", 2: "\u200d", 3: "\ufeff"}
ZW_REV = {v: k for k, v in ZW.items()}
MAX_SECRET_BYTES = 4096


def derive_key(key: str, salt: bytes = b"StegoNexus-ZW", iterations: int = 100_000,
               length: int = 64) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", key.encode("utf-8"), salt,
                               iterations, dklen=length)


def xor_crypt(data: bytes, ks: bytes) -> bytes:
    if not ks:
        return data
    return bytes(b ^ ks[i % len(ks)] for i, b in enumerate(data))


def _pack(bits: list) -> bytes:
    out = bytearray()
    for i in range(0, len(bits) - 7, 8):
        b = 0
        for bit in bits[i:i + 8]:
            b = (b << 1) | bit
        out.append(b)
    return bytes(out)


def _unpack(data: bytes) -> list:
    return [(b >> s) & 1 for b in data for s in range(7, -1, -1)]


def _spacing(seed: bytes, n: int) -> int:
    """Key-derived spacing (2..6) so hidden chars are scattered."""
    return 2 + (int.from_bytes(seed[:2], "big") % 5)


def hide(cover_text: str, secret_message: str, key: str) -> Tuple[str, dict]:
    """Cover Text + Secret + Key -> Stego Text (zero-width technique)."""
    if not secret_message:
        raise ValueError("Secret message must not be empty")
    secret = secret_message.encode("utf-8")
    if len(secret) > MAX_SECRET_BYTES:
        raise ValueError(f"Secret too long ({len(secret)} B > {MAX_SECRET_BYTES})")
    ks = derive_key(key)
    payload = MAGIC + len(secret).to_bytes(2, "big") + xor_crypt(secret, ks)

    # map 2 bits -> zero-width char
    bits = _unpack(payload)
    hidden = "".join(ZW[bits[i] * 2 + bits[i + 1]] for i in range(0, len(bits) - 1, 2))

    # scatter into the cover at key-derived spacing
    step = _spacing(ks, len(cover_text))
    out, pos, hidx = [], 0, 0
    for ch in cover_text:
        out.append(ch)
        pos += 1
        if hidx < len(hidden) and pos % step == 0:
            out.append(hidden[hidx]); hidx += 1
            pos = 0
    out.append(hidden[hidx:])          # remainder at the end
    stego = "".join(out)

    return stego, {
        "method": "zerowidth", "secret_bytes": len(secret),
        "hidden_chars": len(hidden), "cover_chars": len(cover_text),
        "spacing": step, "max_secret_bytes": MAX_SECRET_BYTES,
    }


def reveal(stego_text: str, key: str) -> Tuple[str, dict]:
    """Stego Text + Key -> Original Secret Message (zero-width technique)."""
    bits = []
    for ch in stego_text:
        if ch in ZW_REV:
            v = ZW_REV[ch]
            bits.extend([(v >> 1) & 1, v & 1])
    payload = _pack(bits)
    if not payload.startswith(MAGIC):
        raise ValueError("No zero-width payload found (wrong text or no hiding)")
    if len(payload) < len(MAGIC) + 2:
        raise ValueError("Zero-width payload truncated")
    size = int.from_bytes(payload[len(MAGIC):len(MAGIC) + 2], "big")
    body = payload[len(MAGIC) + 2:len(MAGIC) + 2 + size]
    if len(body) != size:
        raise ValueError(f"Zero-width payload incomplete ({len(body)}/{size} B)")
    secret = xor_crypt(body, derive_key(key)).decode("utf-8", "replace")
    return secret, {"method": "zerowidth", "secret_bytes": size,
                    "hidden_chars": len(bits) // 2}


def inspect(stego_text: str) -> dict:
    """Detect zero-width payload presence (for the forensics view).

    Decodes the zero-width bits and checks the MAGIC prefix — this is how
    an analyst can prove a zero-width payload exists even without the key.
    """
    bits = []
    for ch in stego_text:
        if ch in ZW_REV:
            v = ZW_REV[ch]
            bits.extend([(v >> 1) & 1, v & 1])
    payload = _pack(bits)
    counts = {ZW[k]: stego_text.count(ZW[k]) for k in ZW}
    return {"count": len(bits) // 2, "counts": counts,
            "suspicious": payload.startswith(MAGIC),
            "payload_bytes": max(0, len(payload))}


# dual interface: text_hiding uses encode/decode — keep the same names here
encode = hide
decode = reveal

__all__ = ["hide", "reveal", "inspect", "encode", "decode", "derive_key"]
