"""
Minimal pure-Python PCAP reader/writer (libpcap format) for the
Network Hiding module. No external dependencies: enough to craft, record
and parse Ethernet/IPv4/TCP streams used in covert communication labs.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import List, Optional

MAGIC_NANO = b"\x4d\x3c\xb2\xa1"
MAGIC_MICRO = b"\xd4\xc3\xb2\xa1"


@dataclass
class Packet:
    ts_micros: float
    dst_mac: bytes
    src_mac: bytes
    eth_type: int
    ip_id: int = 0
    ip_src: bytes = b""
    ip_dst: bytes = b""
    proto: int = 6               # 6 = TCP
    tcp_seq: int = 0             # ISN when SYN
    tcp_flags: int = 0x02        # SYN
    ttl: int = 64
    payload: bytes = field(default=b"")

    def to_bytes(self) -> bytes:
        eth = self.dst_mac + self.src_mac + struct.pack(">H", self.eth_type)
        total = 20 + 20 + max(0, len(self.payload) - 32)
        ver_ihl = 0x45
        ip = struct.pack(">BBHHHBBH4s4s", ver_ihl, 0, total, self.ip_id,
                         0x4000, self.ttl, self.proto, 0,
                         self.ip_src, self.ip_dst)
        tcp = struct.pack(">HHIIBBHHH", 12345, 80, self.tcp_seq, 0,
                         0x50, self.tcp_flags, 8192, 0, 0)
        pad = self.payload[:32]
        pad += b"\x00" * (32 - len(pad))
        return eth + ip + tcp + pad


def write_pcap(path: str, packets: List[Packet], nano: bool = False) -> None:
    """Write a little-endian libpcap file (magic bytes d4 c3 b2 a1)."""
    with open(path, "wb") as fh:
        fh.write(struct.pack("<IHHIIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 1))
        frac_scale = 1000 if nano else 1
        for p in packets:
            raw = p.to_bytes()
            sec = int(p.ts_micros // 1_000_000)
            frac = int((p.ts_micros % 1_000_000) * frac_scale)
            fh.write(struct.pack("<IIII", sec, frac, len(raw), len(raw)))
            fh.write(raw)


def read_pcap(path: str) -> List[Packet]:
    packets: List[Packet] = []
    with open(path, "rb") as fh:
        head = fh.read(24)
        if len(head) < 24:
            return packets
        link = struct.unpack("<I", head[20:24])[0]
        if link != 1:                    # only Ethernet (DLT_EN10MB)
            return packets
        while True:
            rec = fh.read(16)
            if len(rec) < 16:
                break
            ts_sec, ts_frac, cap_len, _orig = struct.unpack("<IIII", rec)
            body = fh.read(cap_len)
            if len(body) < 14 + 20:
                continue
            dst = body[0:6]
            src = body[6:12]
            etype = struct.unpack(">H", body[12:14])[0]
            if etype != 0x0800:
                continue
            ip = body[14:]
            ip_hlen = (ip[0] & 0x0F) * 4
            if len(ip) < ip_hlen + 20:
                continue
            ip_id = struct.unpack(">H", ip[4:6])[0]
            ip_src = ip[12:16]
            ip_dst = ip[16:20]
            proto = ip[9]
            ttl = ip[8]
            tcp = ip[ip_hlen:]
            tcp_seq = struct.unpack(">I", tcp[4:8])[0]
            flags = tcp[13]
            packets.append(Packet(ts_micros=ts_sec + ts_frac / 1_000_000,
                                  dst_mac=dst, src_mac=src, eth_type=etype,
                                  ip_id=ip_id, ip_src=ip_src, ip_dst=ip_dst,
                                  proto=proto, tcp_seq=tcp_seq, tcp_flags=flags,
                                  ttl=ttl))
    return packets


__all__ = ["Packet", "write_pcap", "read_pcap"]
