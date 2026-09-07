#!/usr/bin/env python3
"""
Capture CLI (terminal) screenshots: runs real StegoNexus commands inside a
terminal emulator (pyte) and renders them as dark-theme PNGs.
Run: python screenshots/capture_cli.py
"""
from __future__ import annotations

import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

OUT = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(OUT)
DEMO = os.path.join(ROOT, "demo_output")

WIDTH, HEIGHT = 130, 42
BG = "#0d1117"
FG = "#d8dee9"
ACCENT = "#00d98b"
CYAN = "#56b6c2"
YELLOW = "#ffd166"
RED = "#ff6b6b"

try:
    import pyte
except ImportError:                                        # pragma: no cover
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "pyte"])
    import pyte

from PIL import Image, ImageDraw, ImageFont


def render(lines, path, title="steghide@kali: ~/StegoNexus"):
    """Render pseudo-terminal lines to a PNG."""
    if isinstance(lines, str):
        lines = lines.splitlines()
    cell_w, cell_h = 8, 15
    pad = 14
    img_w = min(WIDTH, max(len(l) + 2 for l in lines)) * cell_w + pad * 2
    img_h = (len(lines) + 4) * cell_h + pad * 2
    im = Image.new("RGB", (int(img_w), int(img_h)), BG)
    d = ImageDraw.Draw(im)
    try:
        f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
                               11)
    except Exception:
        f = ImageFont.load_default()

    # window header
    d.rectangle([0, 0, int(img_w), 24], fill="#161b22")
    for i, c in enumerate(["#ff5f56", "#ffbd2e", "#27c93f"]):
        d.ellipse([10 + i * 16, 8, 10 + i * 16 + 8, 16], fill=c)
    d.text((int(img_w) - len(title) * cell_w - 12, 6), title, fill="#8b949e", font=f)
    y = 24 + pad
    for ln in lines:
        x = pad
        color = FG
        if ln.startswith("$ "):
            d.text((x, y), "$", fill=ACCENT, font=f)
            d.text((x + 9, y), ln[2:], fill=FG, font=f)
        elif ln.startswith("[+]") or ln.startswith("OK") or ln.startswith("PASS"):
            d.text((x, y), ln, fill=ACCENT, font=f)
        elif ln.startswith("  [PASS]"):
            d.text((x, y), ln, fill=ACCENT, font=f)
        elif ln.startswith("  [FAIL]"):
            d.text((x, y), ln, fill=RED, font=f)
        elif ln.startswith("== ") or ln.startswith("###"):
            d.text((x, y), ln, fill=CYAN, font=f)
        elif ln.startswith("[!]") or ln.startswith("WARN"):
            d.text((x, y), ln, fill=YELLOW, font=f)
        elif ln.startswith("SUSPICIOUS") or ln.startswith("HIDDEN") or \
                ln.startswith("COVERT") or ln.startswith("VERY"):
            d.text((x, y), ln, fill=YELLOW, font=f)
        elif ln.startswith("VERDICT") or ln.startswith("dec"):
            d.text((x, y), ln, fill=RED, font=f)
        else:
            d.text((x, y), ln, fill=color, font=f)
        y += cell_h
    im.save(path)
    print("saved", os.path.basename(path), im.size)


def run(cmd, cwd=ROOT, timeout=300):
    """Run a command, capture combined output as terminal lines."""
    p = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True,
                       text=True, timeout=timeout)
    out = (p.stdout or "") + (p.stderr or "")
    return ["$ " + cmd] + out.rstrip("\n").splitlines()


def banner(text):
    return ["", "== " + text + " ==", ""]


def main():
    lines: list[str] = []

    # ---- 01: tool detection -------------------------------------------
    lines += banner("01 · Kali tool detection (auto-detect)")
    lines += run("python run_cli.py --version")
    lines += run("python -c \""
                 "import sys; sys.path.insert(0,'.');"
                 "from stegonexus.core import forensics as f;"
                 "s=f.tool_status();"
                 "print('  '+', '.join(f'{k}={v}' for k,v in s.items()))\"")
    render(lines, os.path.join(OUT, "cli_01_toolchain.png"))

    # ---- 02: hashing ----------------------------------------------------
    lines = banner("02 · Hashing & Integrity  (MD5 · SHA-1 · SHA-256 · SHA-512)")
    lines += run("python run_cli.py hash demo_output/cover_photo.png "
                 "-a MD5 SHA-1 SHA-256 SHA-512")
    render(lines, os.path.join(OUT, "cli_02_hashing.png"))

    # ---- 03: text hiding --------------------------------------------------
    import shutil as _sh
    src_txt = os.path.join(DEMO, "cover_text.txt")
    if not os.path.exists(src_txt):
        with open(src_txt, "w") as fh:
            fh.write(("StegoNexus unifies the hiding techniques of the term "
                      "into one integrated tool running on Kali Linux. "
                      "This innocent paragraph is only a cover carrier. " * 3))
    lines = banner("03 · Text Hiding — LSB with Key (hide → reveal)")
    lines += run("python run_cli.py text hide demo_output/cover_text.txt "
                 "--message demo_output/secret_document.txt "
                 "--key 'StegoNexus-Demo-Key-2026' "
                 "--output demo_output/stego_text_out.txt")
    lines += run("python run_cli.py text reveal demo_output/stego_text_out.txt "
                 "--key 'StegoNexus-Demo-Key-2026'")
    render(lines, os.path.join(OUT, "cli_03_text_lsb.png"))

    # ---- 04: image hiding (steghide REAL) ---------------------------------
    lines = banner("04 · Image Hiding — steghide (real, Kali tool)")
    lines += run("python run_cli.py image-info demo_output/cover_photo_stego.jpg "
                 "--password 'StegoNexus-Demo-Key-2026'")
    lines += run("python run_cli.py image-unhide demo_output/cover_photo_stego.jpg "
                 "--password 'StegoNexus-Demo-Key-2026' --output-dir demo_output")
    render(lines, os.path.join(OUT, "cli_04_image_steghide.png"))

    # ---- 05: audio hiding --------------------------------------------------
    lines = banner("05 · Audio Hiding — LSB / Phase / Spread Spectrum / Metadata")
    lines += run("python run_cli.py audio lsb demo_output/cover_quiet.wav "
                 "demo_output/secret_payload.bin --key 'ak'")
    lines += run("python run_cli.py audio phase demo_output/cover_phase.wav "
                 "demo_output/phase_secret.bin --key 'pk'")
    lines += run("python run_cli.py audio ss demo_output/cover_quiet.wav "
                 "demo_output/secret_payload.bin --key 'sk'")
    lines += run("python run_cli.py audio meta demo_output/cover_song.wav "
                 "demo_output/secret_payload.bin --key 'mk'")
    lines += run("python run_cli.py audio-analyze demo_output/cover_song_meta.wav")
    render(lines, os.path.join(OUT, "cli_05_audio.png"))

    # ---- 06: video ----------------------------------------------------------
    lines = banner("06 · Video Hiding — ffprobe streams + VideoHide (real ffmpeg)")
    lines += run("python run_cli.py video-info demo_output/cover_video.mp4")
    lines += run("python run_cli.py video demo_output/cover_video.mp4 "
                 "demo_output/secret_payload.bin --key 'vk'")
    lines += run("python run_cli.py video-unhide demo_output/cover_video_vstego.mkv "
                 "--key 'vk' --output-dir demo_output")
    render(lines, os.path.join(OUT, "cli_06_video.png"))

    # ---- 07: network --------------------------------------------------------
    lines = banner("07 · Network Hiding — covert channels (IP-ID · ISN · timing)")
    lines += run("python run_cli.py network demo_output/secret_payload.bin "
                 "--key 'nk' --mode ipid --output demo_output/covert_ipid.pcap")
    lines += run("python run_cli.py network-detect demo_output/covert_ipid.pcap")
    lines += run("python run_cli.py network-unhide demo_output/covert_ipid.pcap "
                 "--key 'nk' --mode ipid --output-dir demo_output")
    render(lines, os.path.join(OUT, "cli_07_network.png"))

    # ---- 08: malware lab -----------------------------------------------------
    lines = banner("08 · Malware Hiding & Evasion Lab (defensive scan)")
    lines += run("python run_cli.py malware demo_output/sample_payload.exe")
    render(lines, os.path.join(OUT, "cli_08_malware.png"))

    # ---- 09: forensics pipeline ----------------------------------------------
    lines = banner("09 · Forensics & Analysis — aggregated tools (one report)")
    lines += run("python run_cli.py forensics demo_output/cover_photo_stego.jpg "
                 "--password 'StegoNexus-Demo-Key-2026'")
    render(lines, os.path.join(OUT, "cli_09_forensics.png"))

    # ---- 10: case + reports ----------------------------------------------------
    import glob
    case_dirs = sorted(glob.glob(os.path.join(DEMO, "cases", "CASE-*")))
    case_id = os.path.basename(case_dirs[-1]) if case_dirs else "CASE-DEMO"
    lines = banner("10 · Case Management — Reports & Logs")
    lines += run(f"python run_cli.py case list --workspace demo_output")
    lines += run(f"python run_cli.py case export --case-id {case_id} "
                 f"--format md --workspace demo_output")
    lines += run(f"ls -la demo_output/cases/{case_id}/reports "
                 f"demo_output/cases/{case_id}/logs")
    lines += run(f"tail -6 demo_output/cases/{case_id}/logs/investigation.log")
    render(lines, os.path.join(OUT, "cli_10_case.png"))

    # ---- 11: tests -------------------------------------------------------------
    lines = banner("11 · Verification — 22/22 integration tests")
    lines += run("python tests/test_integration.py 2>&1 | tail -26")
    render(lines, os.path.join(OUT, "cli_11_tests.png"))

    print("CLI screenshots done.")


if __name__ == "__main__":
    main()
