"""
Shannon Entropy — Forensics indicator (part of modules 02 / 10)
==============================================================
Shannon Entropy H = -Σ p_i · log2(p_i)  (bits per byte, max 8.0).

High entropy (≈ 7.0–8.0) inside a file — or in a single section / region —
is a classic indicator of compressed data (packers), encrypted blobs,
or embedded hidden payloads. Used by:
  * forensics.EntropyAnalysis  (file-level + sliding-window scans)
  * malware_lab                (PE section entropy)
  * audio_hiding               (optional sanity metric)
"""

from __future__ import annotations

import math
from collections import Counter
from typing import Dict, List, Optional, Tuple

MAX_ENTROPY = 8.0


def entropy_of_bytes(data: bytes) -> float:
    """Shannon entropy (bits/byte) of an in-memory buffer."""
    if not data:
        return 0.0
    counts = Counter(data)
    n = len(data)
    return -sum((c / n) * math.log2(c / n) for c in counts.values())


def entropy_of_file(path: str, chunk: int = 4 * 1024 * 1024) -> float:
    """Entropy of a whole file, streamed in chunks (approximate)."""
    total = 0.0
    size = 0
    counts = Counter()
    with open(path, "rb") as fh:
        while True:
            block = fh.read(chunk)
            if not block:
                break
            counts.update(block)
            size += len(block)
    if size == 0:
        return 0.0
    return -sum((c / size) * math.log2(c / size) for c in counts.values())


def sliding_window_entropy(data: bytes, window: int = 1024, step: Optional[int] = None) -> List[Tuple[int, float]]:
    """Sliding-window entropy scan. Returns [(offset, entropy), ...]."""
    step = step or (window // 2)
    out: List[Tuple[int, float]] = []
    for off in range(0, len(data) - window + 1, step):
        out.append((off, entropy_of_bytes(data[off:off + window])))
    # tail window
    if len(data) > window and (len(data) - window) % step:
        out.append((len(data) - window, entropy_of_bytes(data[-window:])))
    return out


def scan_file_regions(path: str, window: int = 1024, step: Optional[int] = None,
                      threshold: float = 7.5) -> dict:
    """Scan a file with a sliding window and flag suspicious high-entropy regions."""
    with open(path, "rb") as fh:
        data = fh.read()
    points = sliding_window_entropy(data, window, step)
    flagged = [{"offset": off, "entropy": round(e, 4)} for off, e in points if e >= threshold]
    if not points:
        avg = 0.0
    else:
        avg = sum(e for _o, e in points) / len(points)
    return {
        "file": path,
        "size_bytes": len(data),
        "window": window,
        "overall_entropy": round(entropy_of_bytes(data) if data else 0.0, 4),
        "average_window_entropy": round(avg, 4),
        "suspicious_regions": flagged[:50],
        "suspicious_count": len(flagged),
        "verdict": ("SUSPICIOUS - high entropy regions may hide compressed/encrypted data"
                    if flagged else "NO HIGH-ENTROPY ANOMALY DETECTED"),
    }


def entropy_level(entropy: float) -> str:
    """Human-readable categorisation."""
    if entropy >= 7.5:
        return "VERY HIGH (likely encrypted/compressed/packed)"
    if entropy >= 6.8:
        return "HIGH (possible obfuscated payload)"
    if entropy >= 5.0:
        return "MEDIUM"
    return "LOW (structured / plaintext)"


__all__ = ["entropy_of_bytes", "entropy_of_file", "sliding_window_entropy",
           "scan_file_regions", "entropy_level", "MAX_ENTROPY"]
