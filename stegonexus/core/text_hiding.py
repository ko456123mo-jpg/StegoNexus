"""
Module 04 - Text Hiding: LSB with Key (Python implementation)
=============================================================
Required operations:
  Hiding/Encoding    : Cover Text + Secret Message + Key
                       -> LSB Encoding -> Stego Text
  Extraction/Decoding: Stego Text + Key
                       -> LSB Decoding -> Original Secret Message

Design (classic text-LSB, key-controlled):
  1. The secret message is XOR-encrypted with a keystream derived from the
     Key (PBKDF2-HMAC-SHA256) and length-prefixed with a format MAGIC.
  2. Bits are hidden in the Least Significant Bit of eligible Unicode
     code-points of the cover text (shift=0), or in the second-to-last bit
     (shift=1, survives ASCII-only printers).
  3. The Key also drives a deterministic permutation (Fisher-Yates seeded
     from the derived key) of the carrier positions: without the key the
     LSB stream is a pseudo-random sequence and cannot be reassembled.

Security note: teaching implementation of the classic Text-LSB method.
"""

from __future__ import annotations

import hashlib
import random as _random
from typing import List, Tuple

MAX_SECRET_BYTES = 4096
MAGIC = b"SNX1"                       # StegoNexus v1 text stego marker
_SURROGATE_LO, _SURROGATE_HI = 0xD800, 0xDFFF


# ----------------------------------------------------------------------- #
# Key derivation + stream cipher
# ----------------------------------------------------------------------- #
def derive_key(key: str, salt: bytes = b"StegoNexus-TextLSB", iterations: int = 100_000,
               length: int = 64) -> bytes:
    """PBKDF2-HMAC-SHA256 keystream derived from the user's Key."""
    return hashlib.pbkdf2_hmac("sha256", key.encode("utf-8"), salt, iterations, dklen=length)


def xor_crypt(data: bytes, keystream: bytes) -> bytes:
    """XOR a buffer with the (repeating) keystream."""
    if not keystream:
        return data
    return bytes(b ^ keystream[i % len(keystream)] for i, b in enumerate(data))


# ----------------------------------------------------------------------- #
# Bit helpers
# ----------------------------------------------------------------------- #
def bytes_to_bits(data: bytes) -> List[int]:
    return [(b >> shift) & 1 for b in data for shift in range(7, -1, -1)]


def bits_to_bytes(bits: List[int]) -> bytes:
    out = bytearray()
    for i in range(0, len(bits) - 7, 8):
        byte = 0
        for b in bits[i:i + 8]:
            byte = (byte << 1) | b
        out.append(byte)
    return bytes(out)


# ----------------------------------------------------------------------- #
# Carrier eligibility (must be identical in encode and decode)
# ----------------------------------------------------------------------- #
def _carrier_indices(text: str, shift: int) -> List[int]:
    """
    Character positions that are safe to touch:
      - code point >= 0x20 (printable / no C0 controls)
      - not DEL (0x7F)
      - not a UTF-16 surrogate
      - flipping the bit at `shift` keeps the code point inside a printable
        band (>= 0x20).
    """
    idx: List[int] = []
    for i, ch in enumerate(text):
        code = ord(ch)
        if code < 0x20 or code == 0x7F:
            continue
        if _SURROGATE_LO <= code <= _SURROGATE_HI:
            continue
        flipped = (code & ~(1 << shift)) | ((code >> shift) & 1 ^ 1) << shift
        # ensure resulting plane does not fall below the printable band
        if flipped < 0x20 and flipped != code:
            continue
        idx.append(i)
    return idx


def _permutation_indices(n: int, seed: bytes) -> List[int]:
    """Deterministic permutation of n carrier positions (seeded by the key)."""
    rng = _random.Random(seed)
    idx = list(range(n))
    for i in range(n - 1, 0, -1):
        j = rng.randint(0, i)
        idx[i], idx[j] = idx[j], idx[i]
    return idx


# ----------------------------------------------------------------------- #
# Encoding / decoding
# ----------------------------------------------------------------------- #
def encode(cover_text: str, secret_message: str, key: str,
           shift: int = 0) -> Tuple[str, dict]:
    """Cover Text + Secret Message + Key -> LSB Encoding -> Stego Text."""
    if not cover_text:
        raise ValueError("Cover text must not be empty")
    secret = secret_message.encode("utf-8")
    if len(secret) > MAX_SECRET_BYTES:
        raise ValueError(f"Secret message too large (max {MAX_SECRET_BYTES} bytes)")
    if not key:
        raise ValueError("A Key is required (hiding without a key is not permitted)")

    ks = derive_key(key)
    payload = MAGIC + len(secret).to_bytes(4, "big") + xor_crypt(secret, ks)
    bits = bytes_to_bits(payload)

    carriers = _carrier_indices(cover_text, shift)
    if len(carriers) < len(bits):
        raise ValueError(
            f"Cover text too short: need {len(bits)} bits, cover provides "
            f"{len(carriers)} usable characters")
    order = _permutation_indices(len(carriers), ks[:16])

    chars = list(cover_text)
    for bit_pos, carrier_pos in enumerate(order[:len(bits)]):
        pos = carriers[carrier_pos]
        code = ord(chars[pos])
        chars[pos] = chr((code & ~(1 << shift)) | (bits[bit_pos] << shift))

    meta = {
        "method": "Text LSB (LSB of Unicode code points) + keyed permutation",
        "key_derivation": "PBKDF2-HMAC-SHA256 (100000 iters, 64-byte keystream)",
        "cipher": "XOR keystream, then LSB embedding",
        "payload_bits": len(bits),
        "payload_bytes": len(payload),
        "secret_bytes": len(secret),
        "cover_chars": len(cover_text),
        "used_carriers": len(carriers),
        "shift": shift,
    }
    return "".join(chars), meta


def decode(stego_text: str, key: str, shift: int = 0) -> Tuple[str, dict]:
    """Stego Text + Key -> LSB Decoding -> Original Secret Message."""
    if not key:
        raise ValueError("A Key is required to extract the hidden message")
    if not stego_text:
        raise ValueError("Stego text must not be empty")

    ks = derive_key(key)
    carriers = _carrier_indices(stego_text, shift)
    order = _permutation_indices(len(carriers), ks[:16])

    # phase 1: read magic + 4-byte length (64 bits) using the keyed order
    first_bits: List[int] = []
    for carrier_pos in order:
        if len(first_bits) >= 64:
            break
        pos = carriers[carrier_pos]
        first_bits.append((ord(stego_text[pos]) >> shift) & 1)
    header = bits_to_bytes(first_bits)
    if len(header) < 8 or header[:4] != MAGIC:
        raise ValueError(
            "No StegoNexus payload found. Wrong Key, wrong text, or the "
            "text was re-encoded (line breaks / HTML) after hiding.")
    total = 8 + int.from_bytes(header[4:8], "big")

    # phase 2: read the remaining (total*8 - 64) bits
    rest_bits: List[int] = []
    for carrier_pos in order[64:]:
        if len(rest_bits) >= total * 8 - 64:
            break
        pos = carriers[carrier_pos]
        rest_bits.append((ord(stego_text[pos]) >> shift) & 1)

    raw = bits_to_bytes(first_bits + rest_bits)
    secret = xor_crypt(raw[8:total], ks)
    meta = {
        "method": "Text LSB extraction (keyed permutation)",
        "recovered_bytes": len(secret),
        "magic_valid": True,
    }
    return secret.decode("utf-8", errors="replace"), meta


def encode_to_text(cover_text: str, secret_message: str, key: str) -> str:
    stego, _ = encode(cover_text, secret_message, key)
    return stego


def decode_from_text(stego_text: str, key: str) -> str:
    plain, _ = decode(stego_text, key)
    return plain


__all__ = ["encode", "decode", "encode_to_text", "decode_from_text",
           "derive_key", "xor_crypt", "bytes_to_bits", "bits_to_bytes",
           "MAX_SECRET_BYTES", "MAGIC"]
