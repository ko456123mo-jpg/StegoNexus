"""
StegoNexus Command-Line Interface (mirrors the Dashboard operations).
Runs on Kali Linux and anywhere Python 3.9+ is available.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Optional

from stegonexus import core
from stegonexus.case.manager import CaseManager
from stegonexus import __version__


# ----------------------------------------------------------------------- #
# helpers
# ----------------------------------------------------------------------- #
def _p(msg: str = "") -> None:
    print(msg)


def _table(rows: list, headers: list) -> None:
    widths = [max(len(str(h)), *(len(str(r[i])) for r in rows)) if rows else len(str(h))
              for i, h in enumerate(headers)]
    fmt = "  ".join("{:<%d}" % w for w in widths)
    _p(fmt.format(*headers))
    _p("-" * (sum(widths) + 2 * (len(headers) - 1)))
    for r in rows:
        _p(fmt.format(*map(str, r)))


def from_filemgr(case: Optional[CaseManager], module: str, action: str,
                 result: dict) -> None:
    if case:
        case.record_operation(module, action, result)


# ----------------------------------------------------------------------- #
# commands
# ----------------------------------------------------------------------- #
def cmd_hash(args) -> None:
    rows = []
    for path in args.files:
        res = core.hashing.hash_file(path, args.algorithms)
        for r in res:
            rows.append([r.algorithm, r.digest, r.target])
    _table(rows, ["ALGORITHM", "DIGEST", "TARGET"])


def cmd_hash_compare(args) -> None:
    r = core.hashing.compare_files(args.a, args.b, args.algorithm)
    _p(r["decision"])
    _p(f"  {args.a}  {r['file_a']['digest']}")
    _p(f"  {args.b}  {r['file_b']['digest']}")


def cmd_entropy(args) -> None:
    r = core.entropy.scan_file_regions(args.file, args.window, threshold=args.threshold)
    _p(f"file            : {r['file']}")
    _p(f"size            : {r['size_bytes']} bytes")
    _p(f"overall entropy : {r['overall_entropy']} bits/byte "
       f"({core.entropy.entropy_level(r['overall_entropy'])})")
    _p(f"suspicious high-entropy regions (>= {args.threshold}): {r['suspicious_count']}")
    for s in r["suspicious_regions"][:10]:
        _p(f"   @ {s['offset']:>10} : {s['entropy']}")
    _p("VERDICT: " + r["verdict"])


def cmd_text(args) -> None:
    tech = getattr(args, "technique", "lsb")
    mod = core.text_zerowidth if tech == "zerowidth" else core.text_hiding
    if args.action == "hide":
        with open(args.cover, "r", encoding="utf-8") as fh:
            cover = fh.read()
        with open(args.message, "r", encoding="utf-8") as fh:
            secret = fh.read()
        stego, meta = mod.encode(cover, secret, args.key)
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(stego)
        _p(f"[+] Stego text written: {args.output}")
        _p(f"    technique: {tech} | payload bits: {meta.get('payload_bits', meta.get('hidden_chars'))} | "
           f"secret bytes: {meta['secret_bytes']} | "
           f"cover chars: {meta['cover_chars']}")
    else:
        with open(args.cover, "r", encoding="utf-8") as fh:
            text = fh.read()
        secret, meta = mod.decode(text, args.key)
        _p("[+] Recovered message:")
        _p(secret)
        _p(f"    technique: {tech} | recovered bytes: "
           f"{meta.get('recovered_bytes', meta.get('secret_bytes'))}")


def cmd_text_inspect(args) -> None:
    from stegonexus.core import text_zerowidth as zw
    with open(args.file, "r", encoding="utf-8") as fh:
        text = fh.read()
    r = zw.inspect(text)
    _p(f"zero-width characters found : {r['count']}")
    _p(f"breakdown                   : { {repr(k): v for k, v in r['counts'].items()} }")
    _p(f"payload bytes (bit-decoded): {r['payload_bytes']}")
    _p("VERDICT: " + ("SUSPICIOUS - zero-width payload detected"
                      if r["suspicious"] else "no zero-width payload"))


def cmd_image(args) -> None:
    # steghide first when supported by the cover (JPEG/BMP; requirement:
    # Image Module على Steghide), CyberHide-style AES-LSB fallback for PNG
    # — same auto mode as the GUI.
    try:
        res = core.image_steghide.embed(args.cover, args.secret, args.password,
                                        args.output)
        tool = res.get("tool", "steghide")
    except Exception as steghide_exc:
        res = core.image_stego.embed_cyberhide(args.cover, args.secret,
                                               args.password, args.output)
        tool = res.get("tool", "cyberhide")
        _p(f"[!] steghide not usable ({steghide_exc}) -> CyberHide fallback")
    _p(f"[+] Stego image: {res.get('stego_image', res.get('out'))} (tool: {tool})")
    return res


def cmd_image_unhide(args) -> None:
    try:
        res = core.image_steghide.extract(args.stego, args.password,
                                          args.output_dir)
    except Exception:
        res = core.image_stego.extract_cyberhide(args.stego, args.password,
                                                 args.output_dir)
    size = res.get("secret_bytes", res.get("size", "?"))
    _p(f"[+] Secret file: {res['secret_file']} ({size} bytes)")


def cmd_image_info(args) -> None:
    try:
        res = core.image_steghide.info(args.file, passphrase=args.password or None)
    except Exception as exc:
        res = core.image_stego.probe_cyberhide(args.file)
        res["fallback_note"] = str(exc)
    for k, v in res.items():
        if k != "raw":
            _p(f"{k:<16}: {v}")
    if res.get("raw"):
        _p("--- steghide output ---")
        _p(res["raw"][:800])


def cmd_audio(args) -> None:
    if args.method == "lsb":
        r = core.audio_hiding.lsb_embed(args.cover, args.secret, args.key, args.output)
    elif args.method == "phase":
        r = core.audio_hiding.phase_embed(args.cover, args.secret, args.key, args.output)
    elif args.method == "ss":
        r = core.audio_hiding.ss_embed(args.cover, args.secret, args.key, args.output)
    elif args.method == "meta":
        r = core.audio_hiding.meta_embed(args.cover, args.secret, args.key, args.output)
    else:
        raise SystemExit(f"unknown method {args.method}")
    _p(f"[+] {r['method']} -> {r['out']}")
    return r


def cmd_audio_unhide(args) -> None:
    if args.method == "lsb":
        r = core.audio_hiding.lsb_extract(args.stego, args.key, args.output_dir)
    elif args.method == "phase":
        r = core.audio_hiding.phase_extract(args.stego, args.key, args.output_dir)
    elif args.method == "ss":
        r = core.audio_hiding.ss_extract(args.stego, args.key, args.output_dir)
    elif args.method == "meta":
        r = core.audio_hiding.meta_extract(args.stego, args.key, args.output_dir)
    else:
        raise SystemExit(f"unknown method {args.method}")
    _p(f"[+] {r['out']} ({r['secret_bytes']} bytes)")


def cmd_audio_analyze(args) -> None:
    r = core.audio_hiding.analyze(args.file)
    for k, v in r.items():
        _p(f"{k:<16}: {v}")
    return r


def cmd_video(args) -> None:
    r = core.video_hiding.video_lsb_embed(args.cover, args.secret, args.key, args.output)
    _p(f"[+] {r['method']} -> {r['out']}")


def cmd_video_unhide(args) -> None:
    r = core.video_hiding.video_lsb_extract(args.stego, args.key, args.output_dir)
    _p(f"[+] {r['out']} ({r['secret_bytes']} bytes)")


def cmd_video_info(args) -> None:
    r = core.video_hiding.ffprobe_info(args.file)
    _p("streams:")
    for s in r.get("streams", []):
        _p("  " + json.dumps(s, default=str))
    if r.get("boxes"):
        _p("container boxes:")
        for b in r["boxes"][:20]:
            _p(f"  {b['box']:<8} offset={b['offset']} size={b['size']}")


def cmd_network(args) -> None:
    r = core.network_hiding.send_to_pcap(args.secret, args.key, args.output,
                                         args.mode, args.src, args.dst)
    _p(f"[+] covert stream: {r['out']} ({r['packets']} packets, "
       f"mode={r['mode']})")


def cmd_network_unhide(args) -> None:
    r = core.network_hiding.extract_from_pcap(args.pcap, args.key,
                                              args.mode, args.output_dir)
    _p(f"[+] reassembled: {r['out']} ({r['secret_bytes']} bytes)")


def cmd_network_detect(args) -> None:
    r = core.network_hiding.detect_covert(args.pcap)
    _p("VERDICT: " + r["verdict"])
    for i in r["indicators"]:
        _p("  * " + i)


def cmd_malware(args) -> None:
    r = core.malware_lab.scan_executable(args.file)
    _p(f"file        : {r['file']}")
    _p(f"entropy     : {r['overall_entropy']:.4f} (max section {r['max_section_entropy']:.4f})")
    _p("sections:")
    for s in r["structure"].get("sections", []):
        _p(f"  {s.get('name', s.get('index')):<16} entropy={s.get('entropy')} "
           f"packed={s.get('packed')}")
    _p("tool indicators:")
    for h in r["tool_indicators"]:
        _p(f"  [{h['tool']}] {h['signature']} @ {h['offset']}")
    _p("VERDICT: " + r["verdict"])


def cmd_forensics(args) -> None:
    r = core.forensics.aggregate(args.file, steghide_passphrase=args.password or None)
    _p(f"=== StegoNexus Forensics Report ===")
    _p(f"file    : {r['file']}  ({r['size_bytes']} bytes)")
    _p(f"type    : {r['file_info'].get('description')}")
    _p(f"entropy : {r['entropy']['overall_entropy']} "
       f"(suspicious regions: {r['entropy']['suspicious_count']})")
    _p(f"strings : {r['strings'].get('count')} found")
    _p(f"markers : {json.dumps(r['interesting_strings'], ensure_ascii=False)[:400]}")
    _p(f"metadata: {str(r['metadata'].get('metadata'))[:300]}")
    _p(f"binwalk : {json.dumps(r['binwalk'].get('results'))[:400]}")
    _p(f"carve   : {json.dumps(r['carving'].get('results'))[:300]}")
    _p(f"zsteg   : {r['zsteg'].get('verdict')}")
    _p(f"steghide: {r['steghide_info'].get('verdict')}")
    for note in r.get("notes", []):
        _p("NOTE    : " + note)
    _p("VERDICT : " + r["verdict"])
    return r


def cmd_image_meta(args) -> None:
    from stegonexus.core import metadata as md
    if args.meta_action == "view":
        r = md.view_metadata(args.file)
        meta = r.get("metadata", {})
        if isinstance(meta, dict):
            for k, v in meta.items():
                _p(f"{k:<20}: {v}")
        else:
            _p(str(meta)[:2000])
        _p(f"[tool: {r.get('tool')}]")
    else:
        if not args.comment:
            raise SystemExit("--comment is required for inject")
        r = md.inject_metadata(args.file, args.comment,
                               out_path=args.output, author=args.author or None)
        _p(f"[+] Metadata injected ({r['method']}) -> {r['out']}")
        _p(f"    verified: {r['verified']}")


def cmd_videohide_script(args) -> None:
    path = core.video_hiding.write_videohide_script(args.output)
    _p(f"[+] videohide.sh written: {path}")


def cmd_case(args) -> None:
    cm = CaseManager(args.workspace)
    if args.action == "create":
        c = cm.create_case(args.title, args.examiner, args.notes)
        _p(f"[+] case {c['case_id']} created: {c['title']}")
    elif args.action == "list":
        for c in cm.list_cases():
            _p(f"  {c['case_id']}  {c['status']:<6} {c['title']}")
    elif args.action == "export":
        c = cm.open_case(args.case_id)
        p = cm.export_report(args.format)
        _p(f"[+] report: {p}")
    else:
        raise SystemExit("unknown case action")


# ----------------------------------------------------------------------- #
# argparse wiring
# ----------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="stegonexus",
        description="StegoNexus - Unified Hiding, Extraction & Forensics Framework "
                    "(© Mohammed Moneer Al-absi)")
    p.add_argument("--version", action="version", version=f"StegoNexus {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    # hashing
    s = sub.add_parser("hash", help="MD5/SHA-1/SHA-256/SHA-512")
    s.add_argument("files", nargs="+")
    s.add_argument("-a", "--algorithms", nargs="+",
                   default=["MD5", "SHA-1", "SHA-256", "SHA-512"])
    s.set_defaults(fn=cmd_hash)

    s = sub.add_parser("compare", help="integrity compare of two files")
    s.add_argument("a"); s.add_argument("b")
    s.add_argument("--algorithm", default="SHA-256")
    s.set_defaults(fn=cmd_hash_compare)

    # entropy
    s = sub.add_parser("entropy", help="Shannon entropy analysis")
    s.add_argument("file")
    s.add_argument("--window", type=int, default=1024)
    s.add_argument("--threshold", type=float, default=7.5)
    s.set_defaults(fn=cmd_entropy)

    # text (2 techniques: LSB and Zero-Width)
    s = sub.add_parser("text", help="Text hiding with key (LSB / Zero-Width)")
    s.add_argument("action", choices=["hide", "reveal"])
    s.add_argument("cover"); s.add_argument("--key", required=True)
    s.add_argument("--message"); s.add_argument("--output", default="stego_text.txt")
    s.add_argument("--technique", choices=["lsb", "zerowidth"], default="lsb")
    s.set_defaults(fn=cmd_text)

    s = sub.add_parser("text-inspect",
                       help="detect zero-width (invisible) payloads in text")
    s.add_argument("file")
    s.set_defaults(fn=cmd_text_inspect)

    # image
    s = sub.add_parser("image", help="Image hiding (CyberHide-style AES-LSB)")
    s.add_argument("cover"); s.add_argument("secret")
    s.add_argument("--password", required=True); s.add_argument("--output")
    s.set_defaults(fn=cmd_image)

    s = sub.add_parser("image-unhide", help="extract secret from stego image")
    s.add_argument("stego"); s.add_argument("--password", required=True)
    s.add_argument("--output-dir")
    s.set_defaults(fn=cmd_image_unhide)

    s = sub.add_parser("image-info", help="probe image for hidden data")
    s.add_argument("file")
    s.add_argument("--password", help="steghide passphrase (confirms embedded data)")
    s.set_defaults(fn=cmd_image_info)

    s = sub.add_parser("image-meta", help="view or inject metadata (exiftool / Pillow)")
    s.add_argument("meta_action", choices=["view", "inject"])
    s.add_argument("file")
    s.add_argument("--comment", default="", help="metadata to inject (inject)")
    s.add_argument("--author", default="")
    s.add_argument("--output", help="output file (inject)")
    s.set_defaults(fn=cmd_image_meta)

    # audio
    s = sub.add_parser("audio", help="audio hiding (lsb|phase|ss|meta)")
    s.add_argument("method", choices=["lsb", "phase", "ss", "meta"])
    s.add_argument("cover"); s.add_argument("secret")
    s.add_argument("--key", required=True); s.add_argument("--output")
    s.set_defaults(fn=cmd_audio)

    s = sub.add_parser("audio-unhide", help="audio extraction")
    s.add_argument("method", choices=["lsb", "phase", "ss", "meta"])
    s.add_argument("stego"); s.add_argument("--key", required=True)
    s.add_argument("--output-dir")
    s.set_defaults(fn=cmd_audio_unhide)

    s = sub.add_parser("audio-analyze", help="audio forensic analysis")
    s.add_argument("file")
    s.set_defaults(fn=cmd_audio_analyze)

    s = sub.add_parser("spectrogram", help="generate spectrogram PNG")
    s.add_argument("file"); s.add_argument("--output", default="spectrogram.png")
    s.set_defaults(fn=lambda a: (_p("[+] " + core.audio_hiding.make_spectrogram(
        a.file, a.output)["out"])))

    # video
    s = sub.add_parser("video", help="video hiding (audio-track LSB)")
    s.add_argument("cover"); s.add_argument("secret")
    s.add_argument("--key", required=True); s.add_argument("--output")
    s.set_defaults(fn=cmd_video)

    s = sub.add_parser("video-unhide", help="video extraction")
    s.add_argument("stego"); s.add_argument("--key", required=True)
    s.add_argument("--output-dir")
    s.set_defaults(fn=cmd_video_unhide)

    s = sub.add_parser("video-info", help="ffprobe streams / container boxes")
    s.add_argument("file")
    s.set_defaults(fn=cmd_video_info)

    s = sub.add_parser("videohide-script", help="generate videohide.sh")
    s.add_argument("--output", default="videohide.sh")
    s.set_defaults(fn=cmd_videohide_script)

    # network
    s = sub.add_parser("network", help="encode secret into packet stream")
    s.add_argument("secret"); s.add_argument("--key", required=True)
    s.add_argument("--mode", default="ipid", choices=["ipid", "isn", "timing"])
    s.add_argument("--output", default="covert_stream.pcap")
    s.add_argument("--src", default="10.0.0.1"); s.add_argument("--dst", default="10.0.0.2")
    s.set_defaults(fn=cmd_network)

    s = sub.add_parser("network-unhide", help="extract from packet capture")
    s.add_argument("pcap"); s.add_argument("--key", required=True)
    s.add_argument("--mode", default="ipid", choices=["ipid", "isn", "timing"])
    s.add_argument("--output-dir")
    s.set_defaults(fn=cmd_network_unhide)

    s = sub.add_parser("network-detect", help="covert channel detection heuristics")
    s.add_argument("pcap")
    s.set_defaults(fn=cmd_network_detect)

    # malware lab
    s = sub.add_parser("malware", help="PE/ELF evasion & packer analysis")
    s.add_argument("file")
    s.set_defaults(fn=cmd_malware)

    s = sub.add_parser("demo-stub", help="build inert evasion demo stub (defence exercise)")
    s.add_argument("--key", default="demo-key"); s.add_argument("--output", default="demo_stub.py")
    s.set_defaults(fn=lambda a: _p("[+] " + core.malware_lab.build_demo_stub(
        a.output, a.key)["out"]))

    # forensics
    s = sub.add_parser("forensics", help="full forensic pipeline on one file")
    s.add_argument("file")
    s.add_argument("--password", help="optional steghide passphrase for confirmation")
    s.set_defaults(fn=cmd_forensics)

    # case
    s = sub.add_parser("case", help="case management & reports")
    s.add_argument("action", choices=["create", "list", "export"])
    s.add_argument("--title", default=""); s.add_argument("--examiner", default="")
    s.add_argument("--notes", default=""); s.add_argument("--case-id")
    s.add_argument("--format", default="md")
    s.add_argument("--workspace", default=os.path.join(os.getcwd(), "workspace"))
    s.set_defaults(fn=cmd_case)

    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        args.fn(args)
    except Exception as exc:                    # noqa: BLE001
        print(f"[!] error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
