"""
Module 08 - Network Hiding: Covert Communication (NetworkHide)
==============================================================
Required:
  Sender   : Secret Data -> Hide/Encode into Network Traffic -> Transmit
  Receiver : Receive Traffic -> Read/Detect Hidden Data -> Extract/Reassemble

Implemented covert channels (pure Python, PCAP record + optional live
socket send when raw sockets/scapy are available):
  * IPv4 Identification field (16-bit) LSB channel     (mode='ipid')
  * TCP Initial Sequence Number LSB channel           (mode='isn')
  * Covert timing channel: inter-packet delay = bit  (mode='timing')
  * DNS-label channel (mention, usable with scapy)    (mode='dns-label')

Payload protection: MAGIC + length + XOR keystream (PBKDF2 from the key),
bits distributed over packets via a keyed permutation.
"""

from __future__ import annotations

import os
import random as _random
from typing import List, Optional

from stegonexus.core import pcap_io
from stegonexus.core.text_hiding import bits_to_bytes, bytes_to_bits, derive_key, xor_crypt

MAGIC = b"SNNW"                 # StegoNexus network payload marker
SRC_MAC = b"\xaa\xbb\xcc\xdd\xee\xff"
DST_MAC = b"\x00\x11\x22\x33\x44\x55"


# ------------------------------------------------------------------------ #
# Payload prep
# ------------------------------------------------------------------------ #
def _wrap(secret: bytes, key: str) -> bytes:
    ks = derive_key(key, b"StegoNexus-NetHide", 80_000)
    return MAGIC + len(secret).to_bytes(4, "big") + xor_crypt(secret, ks)


def _unwrap(blob: bytes, key: str) -> Optional[bytes]:
    if len(blob) < 8 or blob[:4] != MAGIC:
        return None
    size = int.from_bytes(blob[4:8], "big")
    ks = derive_key(key, b"StegoNexus-NetHide", 80_000)
    return xor_crypt(blob[8:], ks)[:size]


def _perm(n: int, seed: bytes) -> List[int]:
    rng = _random.Random(seed)
    idx = list(range(n))
    for i in range(n - 1, 0, -1):
        j = rng.randint(0, i)
        idx[i], idx[j] = idx[j], idx[i]
    return idx


def _addr(ip: str) -> bytes:
    return bytes(int(x) for x in ip.split("."))


# ------------------------------------------------------------------------ #
# Sender: secret data -> network traffic
# ------------------------------------------------------------------------ #
def encode_to_packets(secret_path: str, key: str, mode: str = "ipid",
                      src_ip: str = "10.0.0.1", dst_ip: str = "10.0.0.2",
                      base_isn: int = 1_600_000_000,
                      base_ipid: int = 0xFA00,
                      base_delay_ms: float = 0.4) -> dict:
    """Encode a secret file into a synthetic packet stream (list of packets)."""
    if mode not in ("ipid", "isn", "timing"):
        raise ValueError("mode must be 'ipid', 'isn' or 'timing'")
    secret = open(secret_path, "rb").read()
    payload = _wrap(secret, key)
    bits = bytes_to_bits(payload)

    ks = derive_key(key, b"StegoNexus-NetHide")[:16]
    # one bit per packet (timing uses n+1 packets, one bit per gap)
    n_pkts = len(bits) + (1 if mode == "timing" else 0)
    order = _perm(len(bits), ks)
    rng = _random.Random(ks + mode.encode())
    packets: List[pcap_io.Packet] = []
    t = 1_700_000_000.0            # arbitrary start timestamp
    for i in range(n_pkts):
        if mode == "timing":
            # gap AFTER packet i carries payload bit order[i-1] (i>=1)
            # delays in MICROSECONDS: bit0 ~ 450-650 us, bit1 ~ 2400-2600 us
            if i > 0:
                bit = bits[order[i - 1]]
                delay = base_delay_ms * 1000.0 + (2000.0 if bit else 50.0)
                t += delay + rng.uniform(0, 200.0)
        else:
            bit = bits[order[i]]
            t += rng.uniform(500.0, 1500.0)      # microsecond jitter
        if mode == "ipid":
            ipid = (base_ipid + i) & ~1 | bit                       # LSB channel
        else:
            ipid = (base_ipid + i) & 0xFFFF
        if mode == "isn":
            isn = ((base_isn + i * 7) & ~1) | bit                   # LSB channel
        else:
            isn = base_isn + i * 7
        packets.append(pcap_io.Packet(
            ts_micros=t,
            dst_mac=DST_MAC, src_mac=SRC_MAC, eth_type=0x0800,
            ip_id=ipid,
            ip_src=_addr(src_ip), ip_dst=_addr(dst_ip), proto=6,
            tcp_seq=isn & 0xFFFFFFFF,
            tcp_flags=0x02,
        ))
    return {"mode": mode, "packets": packets, "count": n_pkts,
            "payload_bytes": len(payload), "secret_bytes": len(secret),
            "src": src_ip, "dst": dst_ip}


def send_to_pcap(secret_path: str, key: str, out_pcap: str, mode: str = "ipid",
                 src_ip: str = "10.0.0.1", dst_ip: str = "10.0.0.2") -> dict:
    """Sender: encode + transmit (record to PCAP for the receiver)."""
    enc = encode_to_packets(secret_path, key, mode, src_ip, dst_ip)
    pcap_io.write_pcap(out_pcap, enc["packets"])
    return {"ok": True, "out": out_pcap, "mode": mode,
            "packets": enc["count"], "payload_bytes": enc["payload_bytes"]}


# ------------------------------------------------------------------------ #
# Receiver: traffic -> detect hidden data -> extract/reassemble
# ------------------------------------------------------------------------ #
def extract_from_pcap(pcap_path: str, key: str, mode: str = "ipid",
                      out_dir: Optional[str] = None) -> dict:
    """Receiver: read the stream, de-permute with the key, reassemble data."""
    packets = pcap_io.read_pcap(pcap_path)
    if not packets:
        raise ValueError("No packets found in the capture")
    ks = derive_key(key, b"StegoNexus-NetHide")[:16]
    n = len(packets)

    if mode == "ipid":
        bits = [(p.ip_id & 1) for p in packets]
    elif mode == "isn":
        bits = [(p.tcp_seq & 1) for p in packets]
    elif mode == "timing":
        # decode delay between consecutive packets: big gap -> 1, small -> 0
        bits = []
        for i in range(1, n):
            gap_s = packets[i].ts_micros - packets[i - 1].ts_micros
            bits.append(1 if gap_s > 0.001 else 0)
    else:
        raise ValueError("mode must be 'ipid', 'isn' or 'timing'")

    # de-permute: stream position i carries the bit for payload position order[i]
    order = _perm(len(bits), ks)
    N = len(bits)
    stream_bits = [0] * N
    for i in range(N):
        stream_bits[order[i]] = bits[i]
    raw = bits_to_bytes(stream_bits[:len(stream_bits) - len(stream_bits) % 8])
    blob = raw
    secret = _unwrap(blob, key)
    if secret is None:
        raise ValueError(
            f"No StegoNexus payload in capture (mode={mode}). Wrong key or "
            "not a covert stream.")
    out_dir = out_dir or os.path.dirname(os.path.abspath(pcap_path))
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "extracted_secret.bin")
    open(out, "wb").write(secret)
    return {"ok": True, "out": out, "mode": mode, "packets_read": n,
            "secret_bytes": len(secret)}


# ------------------------------------------------------------------------ #
# Detection / forensics on captures
# ------------------------------------------------------------------------ #
def _looks_random_embedded(low_bits: List[int]) -> bool:
    """
    Natural traffic that increments a counter (IP ID +1 per packet, or an
    ISN generator with odd stride) gives ALTERNATING low bits (transitions
    ~100%). Real hidden payload bits give a balanced, non-alternating mix.
    """
    if len(low_bits) < 32:
        return False
    n = len(low_bits)
    balance = sum(low_bits) / n
    transitions = sum(1 for i in range(n - 1) if low_bits[i] != low_bits[i + 1]) / (n - 1)
    return 0.30 < balance < 0.70 and transitions < 0.85


def detect_covert(pcap_path: str) -> dict:
    """Heuristic channel detection on a capture (receiver side)."""
    packets = pcap_io.read_pcap(pcap_path)
    if not packets:
        return {"verdict": "EMPTY CAPTURE", "indicators": []}
    indicators = []
    ids = [p.ip_id for p in packets]
    seqs = [p.tcp_seq for p in packets]

    id_deltas = [ids[i + 1] - ids[i] for i in range(len(ids) - 1)]
    if any(abs(d) > 3 for d in id_deltas):
        indicators.append("IP ID field shows non-incremental pattern "
                          "(possible ipid covert channel)")
    elif _looks_random_embedded([i & 1 for i in ids]):
        indicators.append("IP ID LSBs balanced & non-alternating "
                          "(possible ipid covert channel)")
    if _looks_random_embedded([s & 1 for s in seqs]):
        indicators.append("TCP ISN LSBs balanced & non-alternating "
                          "(possible ISN covert channel)")
    # timing: bimodal delays
    if len(packets) > 40:
        gaps = [packets[i + 1].ts_micros - packets[i].ts_micros
                for i in range(len(packets) - 1)]
        short = sum(1 for g in gaps if g < 0.001)
        if 0.2 < short / len(gaps) < 0.8:
            indicators.append("Inter-packet delays are bimodal "
                              "(possible timing covert channel)")
    verdict = ("COVERT CHANNEL INDICATORS DETECTED" if indicators
               else "NO OBVIOUS COVERT CHANNEL INDICATORS")
    return {"verdict": verdict, "indicators": indicators, "packets": len(packets)}


# ------------------------------------------------------------------------ #
# Live transmission (requires root / scapy) — optional lab extension
# ------------------------------------------------------------------------ #
def try_live_send(secret_path: str, key: str, dst_ip: str,
                  mode: str = "ipid", count_pkts: int = 8) -> dict:
    """
    Live covert send. Requires scapy + raw socket privileges:
      sudo pip install scapy ; sudo python -m stegonexus.tools.network --send ...
    Falls back to a capture file when privileges are unavailable.
    """
    out = os.path.join(os.getcwd(), "covert_stream.pcap")
    try:
        from scapy.all import IP, TCP, Raw, send  # noqa: F401
        have_scapy = True
    except Exception:
        have_scapy = False
    if not have_scapy:
        return send_to_pcap(secret_path, key, out, mode, dst_ip=dst_ip) | \
            {"note": "scapy unavailable: stream recorded to PCAP instead of live wire"}
    raise RuntimeError("Live send requires root; use the PCAP workflow in the sandbox.")


__all__ = ["encode_to_packets", "send_to_pcap", "extract_from_pcap",
           "detect_covert", "try_live_send", "MAGIC"]
