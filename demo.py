#!/usr/bin/env python3
"""
StegoNexus live demo — executes every module and materialises the outputs
in ./demo_output/: stego images, stego audio + spectrogram/waveform PNGs,
a covert PCAP, a stego MKV, and a complete Case with reports & logs.
Run:  python demo.py
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from stegonexus import core
from stegonexus.case.manager import CaseManager

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "demo_output")
KEY = "StegoNexus-Demo-Key-2026"


def wav(path, seconds=3.0, freq=440.0, rate=44100, amp=0.3, quiet=False):
    import wave
    t = np.linspace(0, seconds, int(rate * seconds), endpoint=False)
    s = (amp * 32767 * np.sin(2 * np.pi * freq * t)).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
        w.writeframes(s.tobytes())


def png(path, w=520, h=360, seed=21):
    """Photo-like cover: the AI art image when available (realistic entropy),
    else a smooth gradient. Keeps forensic flags meaningful."""
    from PIL import Image
    art = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "screenshots", "cover_art.png")
    if os.path.exists(art):
        im = Image.open(art).convert("RGB")
        cx, cy = im.size[0] // 2, im.size[1] // 2
        im = im.crop((max(0, cx - w // 2), max(0, cy - h // 2),
                      min(im.size[0], cx + w // 2), min(im.size[1], cy + h // 2)))
        im = im.resize((w, h), Image.LANCZOS)
        im.save(path)
        return
    x = np.linspace(0, 2 * np.pi, w)
    y = np.linspace(0, 2 * np.pi, h)
    X, Y = np.meshgrid(x, y)
    r = 118 + 70 * np.sin(X + seed / 7.0) + 40 * np.sin(2 * X + Y)
    g = 118 + 70 * np.cos(Y + seed / 5.0) + 40 * np.cos(X + 2 * Y)
    b = 118 + 70 * np.sin((X + Y) / 1.6 + seed / 3.0) + 30 * np.cos(X - Y)
    arr = np.clip(np.stack([r, g, b], axis=-1), 0, 255).astype(np.uint8)
    Image.fromarray(arr, "RGB").save(path)


def main():
    shutil.rmtree(OUT, ignore_errors=True)
    os.makedirs(OUT)
    print("StegoNexus DEMO ->", OUT)

    # content -----------------------------------------------------------------
    secret_txt = os.path.join(OUT, "secret_document.txt")
    secret_bin = os.path.join(OUT, "secret_payload.bin")
    open(secret_txt, "w").write(
        "TOP SECRET — StegoNexus demo message\n"
        "The rendezvous point is 15.9430°N, 48.7890°E. Code name: HIDDEN-FALCON.")
    open(secret_bin, "wb").write(b"\x00\x01\x02SNX-PAYLOAD\xfe\xff" * 6)

    cover_png = os.path.join(OUT, "cover_photo.png")
    cover_jpg = os.path.join(OUT, "cover_photo.jpg")
    cover_wav = os.path.join(OUT, "cover_song.wav")
    quiet_wav = os.path.join(OUT, "cover_quiet.wav")
    png(cover_png)
    from PIL import Image
    Image.open(cover_png).save(cover_jpg, "JPEG", quality=95)
    wav(cover_wav)
    wav(quiet_wav, seconds=4.0, freq=220.0, amp=0.15)

    # 03 hashing --------------------------------------------------------------
    print("\n[03] Hashing & Integrity")
    for r in core.hashing.hash_file(cover_png):
        print(f"    {r.algorithm:<7} {r.digest[:40]}...")

    # 04 text -----------------------------------------------------------------
    print("\n[04] Text LSB with Key")
    cover_text = (
        "StegoNexus unifies the hiding techniques of the term into one tool. "
        "This innocent paragraph is only a cover carrier for the LSB experiment. "
        "Every character of this text carries one bit of the hidden message, "
        "spread through a keyed permutation so that without the key nothing "
        "can be reassembled. The key also derives the keystream that encrypts "
        "the secret before it ever touches the cover text. " * 4)
    stego_text, meta = core.text_hiding.encode(cover_text, open(secret_txt).read(), KEY)
    open(os.path.join(OUT, "stego_text.txt"), "w").write(stego_text)
    back, _ = core.text_hiding.decode(stego_text, KEY)
    print(f"    payload bits {meta['payload_bits']} | recovered OK: {back == open(secret_txt).read()}")

    # 05 image ----------------------------------------------------------------
    print("\n[05] Image Hiding")
    if core.image_steghide.steghide_available():
        r = core.image_steghide.embed(cover_jpg, secret_bin, KEY)
        info = core.image_steghide.info(r["stego_image"], passphrase=KEY)
        print(f"    steghide: {os.path.basename(r['stego_image'])} -> {info['verdict']} "
              f"(file: {info['embedded_file']})")
        core.image_steghide.extract(r["stego_image"], KEY, OUT)
        # honest probe without the password (steghide cannot confirm w/o it)
        nopw = core.image_steghide.info(r["stego_image"])
        print(f"    steghide probe w/o password (honest): {nopw['verdict'][:80]}...")
    else:
        print("    steghide missing -> CyberHide fallback")
    r = core.image_stego.embed_cyberhide(cover_png, secret_bin, KEY)
    cyber_img = r["stego_image"]
    print(f"    cyberhide: {os.path.basename(r['stego_image'])} "
          f"(fill {r['embed_ratio_pct']}%)")
    x = core.image_stego.extract_cyberhide(r["stego_image"], KEY, OUT)
    print(f"    extracted {x['secret_bytes']} B, match: "
          f"{open(x['secret_file'], 'rb').read() == open(secret_bin, 'rb').read()}")
    probe = core.image_stego.probe_cyberhide(r["stego_image"])
    print("    probe:", probe["verdict"])

    # 06 audio ----------------------------------------------------------------
    print("\n[06] Audio Hiding")
    # phase coding capacity is frame-pair based -> use a short secret
    phase_secret = os.path.join(OUT, "phase_secret.bin")
    open(phase_secret, "wb").write(b"PHASE-CODING-SECRET-1!")
    for method, fn, ext in [("lsb", core.audio_hiding.lsb_embed, "_lsb.wav"),
                            ("phase", core.audio_hiding.phase_embed, "_phase.wav")]:
        if method == "phase":
            src = os.path.join(OUT, "cover_phase.wav")
            wav(src, seconds=12.0, freq=330.0)
            use_secret = phase_secret
        else:
            src = quiet_wav
            use_secret = secret_bin
        r = fn(src, use_secret, KEY)
        rx = (core.audio_hiding.lsb_extract if method == "lsb"
              else core.audio_hiding.phase_extract)(r["out"], KEY, OUT)
        ok = open(rx["out"], "rb").read() == open(use_secret, "rb").read()
        print(f"    {method:<6} -> {os.path.basename(r['out'])}  round-trip: {ok}")
    r = core.audio_hiding.ss_embed(quiet_wav, secret_bin, KEY)
    rx = core.audio_hiding.ss_extract(r["out"], KEY, OUT)
    print(f"    ss     -> {os.path.basename(r['out'])}  round-trip: "
          f"{open(rx['out'], 'rb').read() == open(secret_bin, 'rb').read()}")
    r = core.audio_hiding.meta_embed(cover_wav, secret_bin, KEY)
    rx = core.audio_hiding.meta_extract(r["out"], KEY, OUT)
    print(f"    meta   -> {os.path.basename(r['out'])}  round-trip: "
          f"{open(rx['out'], 'rb').read() == open(secret_bin, 'rb').read()}")
    spec = os.path.join(OUT, "spectrogram.png"); wavepng = os.path.join(OUT, "waveform.png")
    core.audio_hiding.make_spectrogram(cover_wav, spec)
    core.audio_hiding.make_waveform(cover_wav, wavepng)
    print(f"    analysis: {os.path.basename(spec)}, {os.path.basename(wavepng)}")
    print("    audio stats:", core.audio_hiding.analyze(cover_wav)["verdict"])

    # 07 video ----------------------------------------------------------------
    print("\n[07] Video Hiding")
    mp4 = os.path.join(OUT, "cover_video.mp4")
    if core.video_hiding.ffmpeg_available():
        subprocess.run(
            ["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=duration=3:size=320x240:rate=15",
             "-f", "lavfi", "-i", "sine=frequency=440:duration=3",
             "-c:v", "libx264", "-c:a", "aac", "-shortest", mp4],
            capture_output=True)
        info = core.video_hiding.ffprobe_info(mp4)
        print("    streams:", [(s["codec_type"], s["codec_name"]) for s in info["streams"]])
        r = core.video_hiding.video_lsb_embed(mp4, secret_bin, KEY)
        rx = core.video_hiding.video_lsb_extract(r["out"], KEY, OUT)
        print(f"    video LSB -> {os.path.basename(r['out'])}  round-trip: "
              f"{open(rx['out'], 'rb').read() == open(secret_bin, 'rb').read()}")
    else:
        print("    ffmpeg missing -> container hiding only")
    r = core.video_hiding.container_embed(cover_png, secret_bin, KEY)
    rx = core.video_hiding.container_extract(r["out"], KEY, OUT)
    print(f"    container -> {os.path.basename(r['out'])}  round-trip: "
          f"{open(rx['out'], 'rb').read() == open(secret_bin, 'rb').read()}")
    script = core.video_hiding.write_videohide_script(os.path.join(OUT, "videohide.sh"))
    print(f"    videohide.sh -> {os.path.basename(script)}")

    # 08 network --------------------------------------------------------------
    print("\n[08] Network Hiding (covert channels)")
    for mode in ("ipid", "isn", "timing"):
        pcap = os.path.join(OUT, f"covert_{mode}.pcap")
        core.network_hiding.send_to_pcap(secret_bin, KEY, pcap, mode)
        rx = core.network_hiding.extract_from_pcap(pcap, KEY, mode, OUT)
        print(f"    {mode:<6} -> {os.path.basename(pcap)} ({rx['packets_read']} pkts) "
              f"round-trip: {open(rx['out'], 'rb').read() == open(secret_bin, 'rb').read()}")
    det = core.network_hiding.detect_covert(os.path.join(OUT, "covert_ipid.pcap"))
    print("    detect:", det["verdict"])

    # 09 malware lab ----------------------------------------------------------
    print("\n[09] Malware Hiding & Evasion Lab")
    stub = core.malware_lab.build_demo_stub(os.path.join(OUT, "demo_stub.py"), KEY)
    print(f"    inert stub -> {os.path.basename(stub['out'])}")
    # synthetic packed binary carrying the classic loader artefacts
    import struct as _st
    sample = os.path.join(OUT, "sample_payload.exe")
    rng = np.random.default_rng(7)
    random_body = bytes(rng.integers(0, 256, 60000, dtype=np.uint8))  # high entropy
    pe = bytearray(b"MZ")
    pe += b"\x00" * (0x3C - 2)
    pe += _st.pack("<I", 64)                 # e_lfanew -> PE header
    pe += b"\x00" * (64 - len(pe))
    pe += b"PE\x00\x00" + _st.pack("<HH", 0x8664, 0) + b"\x00" * 16
    blob = bytes(pe) + random_body + \
        b"MEI\x0c\x0bPYZ-00.pyz" + b"meterpreter" + b"windows/x64/meterpreter/reverse_tcp"
    open(sample, "wb").write(blob)
    scan = core.malware_lab.scan_executable(sample)
    print("    payload sample verdict:", scan["verdict"])
    print("    pyinstaller command:", core.malware_lab.pyinstaller_command("payload.py"))

    # 02 forensics ------------------------------------------------------------
    print("\n[02] Forensics & Analysis")
    agg = core.forensics.aggregate(cyber_img)
    print(f"    type: {agg['file_info']['description']}")
    print(f"    entropy: {agg['entropy']['overall_entropy']} | "
          f"zsteg: {agg['zsteg']['verdict']}")
    print(f"    verdict: {agg['verdict']}")

    # 10/11 case + reports ----------------------------------------------------
    print("\n[10/11] Case Management, Reports & Logs")
    cm = CaseManager(OUT)
    case = cm.create_case("Demo case — full pipeline", "Mohammed Moneer Al-absi",
                          "All hiding techniques + forensics in one case")
    cm.add_evidence(secret_bin, "secret", "the payload")
    cm.add_evidence(cyber_img, "stego-artifact", "stego image")
    cm.add_finding("stego", "secret hidden in image (CyberHide AES-LSB)", "verified")
    cm.add_finding("forensics", agg["verdict"], {"file": agg["file"],
                                                 "entropy": agg["entropy"]["overall_entropy"]},
                   "HIGH")
    cm.record_operation("demo", "run-all-modules", {"modules": 12})
    for fmt in ("md", "json", "html"):
        p = cm.export_report(fmt)
        print(f"    report: {os.path.relpath(p, OUT)}")
    cm.close_case()
    print(f"\nCase dir: {os.path.relpath(cm.case_dir, OUT)}")
    print("DEMO COMPLETE ✅ ->", OUT)


if __name__ == "__main__":
    main()
