"""
Module 03 - Hashing & Integrity
===============================
Required: MD5, SHA-1, SHA-256, SHA-512.
Provides hash computation for files and buffers, dual-file comparison,
integrity manifests and the report-friendly output used by the Dashboard.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

ALGORITHMS: Dict[str, Callable[[bytes], "hashlib._Hash"]] = {
    "MD5": hashlib.md5,
    "SHA-1": hashlib.sha1,
    "SHA-256": hashlib.sha256,
    "SHA-512": hashlib.sha512,
}

CHUNK = 1024 * 1024  # 1 MiB


@dataclass
class HashResult:
    """Result of hashing one file (or a buffer)."""

    target: str                 # file path or "<buffer>"
    algorithm: str
    digest: str
    size_bytes: int = 0
    elapsed_s: float = 0.0

    def to_dict(self) -> dict:
        return {
            "target": self.target,
            "algorithm": self.algorithm,
            "digest": self.digest,
            "size_bytes": self.size_bytes,
            "elapsed_s": round(self.elapsed_s, 6),
        }

    def __str__(self) -> str:
        return f"{self.algorithm:<7} {self.digest}  {self.target}"


def hash_buffer(data: bytes, algorithms: Optional[List[str]] = None) -> Dict[str, str]:
    """Hash an in-memory buffer with the requested algorithms."""
    names = algorithms or list(ALGORITHMS)
    out: Dict[str, str] = {}
    for name in names:
        if name not in ALGORITHMS:
            raise ValueError(f"Unsupported algorithm: {name}")
        out[name] = ALGORITHMS[name](data).hexdigest()
    return out


def hash_file(path: str, algorithms: Optional[List[str]] = None) -> List[HashResult]:
    """Hash a file with the requested algorithms (streamed, low memory)."""
    names = algorithms or list(ALGORITHMS)
    results: List[HashResult] = []
    size = os.path.getsize(path)
    for name in names:
        if name not in ALGORITHMS:
            raise ValueError(f"Unsupported algorithm: {name}")
        h = ALGORITHMS[name]()
        with open(path, "rb") as f:
            while True:
                block = f.read(CHUNK)
                if not block:
                    break
                h.update(block)
        results.append(HashResult(target=path, algorithm=name, digest=h.hexdigest(), size_bytes=size))
    return results


def compare_files(path_a: str, path_b: str, algorithm: str = "SHA-256") -> dict:
    """Compare two files by digest. Returns decision + both digests."""
    if algorithm not in ALGORITHMS:
        raise ValueError(f"Unsupported algorithm: {algorithm}")
    ha = hash_file(path_a, [algorithm])[0]
    hb = hash_file(path_b, [algorithm])[0]
    return {
        "algorithm": algorithm,
        "file_a": {"path": path_a, "digest": ha.digest},
        "file_b": {"path": path_b, "digest": hb.digest},
        "identical": ha.digest == hb.digest,
        "decision": "IDENTICAL (integrity verified)" if ha.digest == hb.digest else "DIFFERENT (integrity violated)",
    }


def generate_manifest(directory: str, algorithms: List[str] = None, recursive: bool = True) -> Dict:
    """Build an integrity manifest (sorted; JSON-serialisable)."""
    names = algorithms or ["SHA-256"]
    manifest: Dict[str, dict] = {}
    root = os.path.abspath(directory)
    for dirpath, _dirnames, filenames in os.walk(root):
        for fname in sorted(filenames):
            full = os.path.join(dirpath, fname)
            rel = os.path.relpath(full, root)
            try:
                res = hash_file(full, names)
                manifest[rel] = {r.algorithm: r.digest for r in res}
            except OSError:
                continue
    return {
        "root": root,
        "algorithms": names,
        "files": manifest,
        "file_count": len(manifest),
    }


def verify_manifest(manifest_path: str, directory: Optional[str] = None) -> Dict:
    """Verify a saved manifest. Returns per-file status."""
    with open(manifest_path, "r", encoding="utf-8") as fh:
        manifest = json.load(fh)
    root = directory or manifest.get("root")
    status: Dict[str, str] = {}
    for rel, digests in manifest.get("files", {}).items():
        full = os.path.join(root, rel) if root else rel
        if not os.path.exists(full):
            status[rel] = "MISSING"
            continue
        try:
            res = hash_file(full, list(digests.keys()))
        except OSError:
            status[rel] = "ERROR"
            continue
        ok = all(res[i].digest == digests[res[i].algorithm] for i in range(len(res)))
        status[rel] = "OK" if ok else "MODIFIED"
    return {"manifest": manifest_path, "root": root, "status": status,
            "verified": sum(1 for v in status.values() if v == "OK"),
            "modified": sum(1 for v in status.values() if v == "MODIFIED"),
            "missing": sum(1 for v in status.values() if v == "MISSING")}
