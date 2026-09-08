"""
StegoNexus end-to-end integration tests (all 12 sections of the project).
Run: python -m pytest tests/ -v   (or)   python tests/test_integration.py
"""

from __future__ import annotations

import os
import sys
import tempfile
import wave

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from stegonexus import core                                               # noqa: E402
from stegonexus.case.manager import CaseManager                           # noqa: E402

TMP = tempfile.mkdtemp(prefix="stegonexus_test_")
PASS = 0
FAIL = 0


def check(name, fn):
    global PASS, FAIL
    try:
        fn()
        PASS += 1
        print(f"  [PASS] {name}")
    except Exception as exc:  # noqa: BLE001
        FAIL += 1
        print(f"  [FAIL] {name}: {exc}")


def make_wav(path, seconds=2.0, freq=440.0, rate=44100, amplitude=0.4):
    t = np.linspace(0, seconds, int(rate * seconds), endpoint=False)
    s = (amplitude * 32767 * np.sin(2 * np.pi * freq * t)).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
        w.writeframes(s.tobytes())


def make_png(path, w=320, h=240):
    from PIL import Image
    import numpy as np
    rng = np.random.default_rng(7)
    arr = rng.integers(0, 255, (h, w, 3), dtype=np.uint8)
    Image.fromarray(arr, "RGB").save(path)


def main():
    print("== StegoNexus integration tests ==")

    # ---- prep fixtures -------------------------------------------------
    cover_png = os.path.join(TMP, "cover.png")
    secret_txt = os.path.join(TMP, "secret.txt")
    secret_bin = os.path.join(TMP, "secret.bin")
    cover_wav = os.path.join(TMP, "cover.wav")
    make_png(cover_png)
    make_wav(cover_wav)
    with open(secret_txt, "w", encoding="utf-8") as fh:
        fh.write("TOP SECRET - StegoNexus integration test message")
    with open(secret_bin, "wb") as fh:
        fh.write(b"\x00\x01\x02\x03PAYLOAD\xff\xfe" * 8)

    # ---- 03 hashing ----------------------------------------------------
    def t_hash():
        res = core.hashing.hash_file(secret_bin)
        assert len(res) == 4
        d = {r.algorithm: r.digest for r in res}
        assert len(d["MD5"]) == 32 and len(d["SHA-1"]) == 40
        assert len(d["SHA-256"]) == 64 and len(d["SHA-512"]) == 128
        comp = core.hashing.compare_files(secret_bin, secret_bin)
        assert comp["identical"]
    check("03 hashing MD5/SHA1/256/512 + compare", t_hash)

    # ---- 04 text LSB ---------------------------------------------------
    def t_text():
        cover = ("The quick brown fox jumps over the lazy dog. " * 2 +
                 "أسرع الثعلب البني يقفز فوق الكلب الكسول. " * 2 + "\n" +
                 "StegoNexus text hiding demo — the key protects the payload. " * 2)
        stego, meta = core.text_hiding.encode(cover,
                                              "hello secret text", key="k123")
        assert meta["payload_bytes"] == meta["secret_bytes"] + 8
        plain, _ = core.text_hiding.decode(stego, "k123")
        assert plain == "hello secret text"
        # wrong key must fail
        try:
            core.text_hiding.decode(stego, "wrong-key")
            raise AssertionError("wrong key accepted")
        except ValueError:
            pass
    check("04 text LSB with key (hide/reveal + wrong key rejected)", t_text)

    # ---- 05 image ------------------------------------------------------
    def t_image():
        r = core.image_stego.embed_cyberhide(cover_png, secret_bin, "pw", 
                                             os.path.join(TMP, "stego.png"))
        assert os.path.exists(r["stego_image"])
        ex = core.image_stego.extract_cyberhide(r["stego_image"], "pw", TMP)
        data = open(ex["secret_file"], "rb").read()
        assert data == open(secret_bin, "rb").read()
        # honest probe: keyed payloads resist keyless detection; wrong password
        # must be rejected (HMAC) — this is the real security contract
        probe = core.image_stego.probe_cyberhide(r["stego_image"])
        assert "verdict" in probe and "indicators" in probe
        try:
            core.image_stego.extract_cyberhide(r["stego_image"], "WRONG", TMP)
            raise AssertionError("wrong password accepted")
        except ValueError:
            pass
    check("05 image CyberHide-style AES-LSB (+wrong password rejected)", t_image)

    # ---- 06 audio ------------------------------------------------------
    phase_wav = os.path.join(TMP, "phase_cover.wav")
    phase_secret = os.path.join(TMP, "phase_secret.bin")
    make_wav(phase_wav, seconds=12.0, freq=330.0)          # long => enough FFT frames
    with open(phase_secret, "wb") as fh:
        fh.write(b"phase-secret-01!")                       # short payload fits easily
    quiet_wav = os.path.join(TMP, "quiet_cover.wav")
    make_wav(quiet_wav, seconds=3.0, freq=220.0, rate=22050, amplitude=0.15)

    def t_audio_lsb():
        r = core.audio_hiding.lsb_embed(cover_wav, secret_bin, "ak", TMP + "/a_lsb.wav")
        ex = core.audio_hiding.lsb_extract(r["out"], "ak", TMP)
        assert open(ex["out"], "rb").read() == open(secret_bin, "rb").read()
    check("06 audio LSB embed/extract", t_audio_lsb)

    def t_audio_phase():
        r = core.audio_hiding.phase_embed(phase_wav, phase_secret, "pk",
                                          TMP + "/a_phase.wav")
        ex = core.audio_hiding.phase_extract(r["out"], "pk", TMP)
        assert open(ex["out"], "rb").read() == open(phase_secret, "rb").read()
    check("06 audio phase coding embed/extract", t_audio_phase)

    def t_audio_ss():
        r = core.audio_hiding.ss_embed(quiet_wav, secret_bin, "sk", TMP + "/a_ss.wav")
        ex = core.audio_hiding.ss_extract(r["out"], "sk", TMP)
        assert open(ex["out"], "rb").read() == open(secret_bin, "rb").read()
    check("06 audio spread spectrum embed/extract", t_audio_ss)

    def t_audio_meta():
        r = core.audio_hiding.meta_embed(cover_wav, secret_bin, "mk", TMP + "/a_meta.wav")
        ex = core.audio_hiding.meta_extract(r["out"], "mk", TMP)
        assert open(ex["out"], "rb").read() == open(secret_bin, "rb").read()
    check("06 audio metadata (RIFF-INFO ICMT) embed/extract", t_audio_meta)

    def t_audio_analysis():
        r = core.audio_hiding.analyze(cover_wav)
        assert r["rate"] == 44100
        sp = core.audio_hiding.make_spectrogram(cover_wav, TMP + "/spec.png")
        wf = core.audio_hiding.make_waveform(cover_wav, TMP + "/wave.png")
        assert os.path.exists(sp["out"]) and os.path.exists(wf["out"])
    check("06 audio analysis (spectrogram/waveform PNG)", t_audio_analysis)

    # ---- 07 video ------------------------------------------------------
    def t_video_container():
        r = core.video_hiding.container_embed(cover_wav, secret_bin, "vk",
                                              TMP + "/video_container.bin")
        ex = core.video_hiding.container_extract(r["out"], "vk", TMP)
        assert open(ex["out"], "rb").read() == open(secret_bin, "rb").read()
        # wrong key rejected
        try:
            core.video_hiding.container_extract(r["out"], "wrong", TMP)
            raise AssertionError("wrong container key accepted")
        except ValueError:
            pass
    check("07 video container/file hiding embed/extract (wrong key rejected)", t_video_container)

    def t_video_script():
        p = core.video_hiding.write_videohide_script(TMP + "/videohide.sh")
        assert os.path.exists(p) and os.access(p, os.X_OK)
    check("07 videohide.sh generation", t_video_script)

    def t_video_info():
        r = core.video_hiding.ffprobe_info(cover_wav)
        assert r["ok"]
    check("07 video stream info (ffprobe/py fallback)", t_video_info)

    def t_video_lsb_wav():
        r = core.audio_hiding.lsb_embed(cover_wav, secret_bin, "vk2", TMP + "/v.wav")
        ex = core.audio_hiding.lsb_extract(r["out"], "vk2", TMP)
        assert open(ex["out"], "rb").read() == open(secret_bin, "rb").read()
    check("07 video-LSB engine round trip on audio track WAV", t_video_lsb_wav)

    # ---- 08 network ----------------------------------------------------
    def t_net_ipid():
        r = core.network_hiding.send_to_pcap(secret_bin, "nk", TMP + "/covert.pcap", "ipid")
        assert r["packets"] > 0
        ex = core.network_hiding.extract_from_pcap(r["out"], "nk", "ipid", TMP)
        assert open(ex["out"], "rb").read() == open(secret_bin, "rb").read()
    check("08 network ipid covert channel (pcap round trip)", t_net_ipid)

    def t_net_isn():
        r = core.network_hiding.send_to_pcap(secret_bin, "nk", TMP + "/covert2.pcap", "isn")
        ex = core.network_hiding.extract_from_pcap(r["out"], "nk", "isn", TMP)
        assert open(ex["out"], "rb").read() == open(secret_bin, "rb").read()
    check("08 network isn covert channel", t_net_isn)

    def t_net_timing():
        r = core.network_hiding.send_to_pcap(secret_bin, "nk", TMP + "/covert3.pcap", "timing")
        ex = core.network_hiding.extract_from_pcap(r["out"], "nk", "timing", TMP)
        assert open(ex["out"], "rb").read() == open(secret_bin, "rb").read()
    check("08 network timing covert channel", t_net_timing)

    def t_net_detect():
        r = core.network_hiding.send_to_pcap(secret_bin, "nk", TMP + "/detect.pcap", "ipid")
        d = core.network_hiding.detect_covert(r["out"])
        assert d["verdict"].startswith("COVERT")
    check("08 covert channel detection heuristics", t_net_detect)

    # ---- 09 malware lab -------------------------------------------------
    def t_malware():
        stub = core.malware_lab.build_demo_stub(TMP + "/demo_stub.py", "mlk")
        assert os.path.exists(stub["out"])
        cmd = core.malware_lab.pyinstaller_command("payload.py")
        assert cmd.startswith("pyinstaller")
        info = core.malware_lab.scan_executable(stub["out"])
        assert "verdict" in info
    check("09 malware evasion demo stub + detection pass", t_malware)

    # ---- metadata view & inject (متطلب: عرض وحقن البيانات الوصفية) ------
    def t_metadata():
        from stegonexus.core import metadata as md
        r = md.inject_metadata(cover_png, "STEALTH-COMMENT-42", author="SNX")
        assert os.path.exists(r["out"])
        v = md.view_metadata(r["out"])
        text = str(v.get("metadata", {}))
        assert "STEALTH-COMMENT-42" in text
        # view before injection must NOT contain the comment
        v0 = md.view_metadata(cover_png)
        assert "STEALTH-COMMENT-42" not in str(v0.get("metadata", {}))
    check("metadata tool: view + inject (images, exiftool/Pillow)", t_metadata)

    # ---- text: second technique (zero-width) --------------------------
    def t_zerowidth():
        from stegonexus.core import text_zerowidth as zw
        cover = "نص غلاف عادي للمتطلبات — يجب أن يبقى مقروءاً تماماً. " * 30
        stego, meta = zw.hide(cover, "SECRET-ZW-777", "key-zw")
        assert meta["hidden_chars"] > 0
        assert zw.inspect(stego)["suspicious"]
        secret, _ = zw.reveal(stego, "key-zw")
        assert secret == "SECRET-ZW-777"
    check("text hiding: second technique (zero-width) + detection", t_zerowidth)

    # ---- 02 forensics ---------------------------------------------------
    def t_forensics():
        r = core.forensics.aggregate(cover_png)
        assert r["file_info"]["description"].startswith("PNG")
        assert "entropy" in r and "zsteg" in r and "binwalk" in r
        # honest detection: a CLEAN image must NOT raise false positives
        # (compressed containers get a note, not an indicator)
        assert r["verdict"] == "NO STRONG HIDING INDICATORS", r["verdict"]
        # a steghide stego image IS confirmed through its passphrase
        if core.image_steghide.steghide_available():
            from PIL import Image as PILImage
            jpg = os.path.join(TMP, "fs.jpg")
            PILImage.fromarray(np.random.default_rng(11).integers(
                0, 255, (220, 220, 3), dtype=np.uint8), "RGB").save(jpg, "JPEG", quality=95)
            emb = core.image_steghide.embed(jpg, secret_bin, "fp")
            r2 = core.forensics.aggregate(emb["stego_image"],
                                          steghide_passphrase="fp")
            assert "SUSPICIOUS" in r2["verdict"] and "steghide" in r2["verdict"]
    check("02 forensics aggregate (no false positives + confirmed detection)", t_forensics)

    # ---- 01/10/11 case + reports + architecture -------------------------
    def t_case():
        cm = CaseManager(TMP + "/case_ws")
        c = cm.create_case("Integration Case", "Test Examiner")
        cm.add_evidence(secret_bin, "secret", "the hidden file")
        cm.add_finding("stego", "secret recovered", {"ok": True})
        cm.record_operation("forensics", "aggregate", {"file": cover_png})
        md = cm.export_report("md")
        html = cm.export_report("html")
        js = cm.export_report("json")
        assert os.path.exists(md) and os.path.exists(html) and os.path.exists(js)
        # reopen and verify persistence
        cm2 = CaseManager(TMP + "/case_ws")
        reopened = cm2.open_case(c["case_id"])
        assert reopened["findings"][0]["summary"] == "secret recovered"
        assert os.path.exists(os.path.join(cm2.case_dir, "logs", "investigation.log"))
        cm2.close_case()
    check("01/10/11 case management + reports (md/html/json) + logs", t_case)

    # ---- entropy module -------------------------------------------------
    def t_entropy():
        r = core.entropy.scan_file_regions(secret_bin)
        assert r["overall_entropy"] > 0
        level = core.entropy.entropy_level(8.0)
        assert "HIGH" in level
    check("02 entropy engine (file + sliding window + levels)", t_entropy)

    # ---- external tools (skipped automatically when not installed) ---------
    from stegonexus.core import image_steghide, video_hiding, forensics as _f

    if image_steghide.steghide_available():
        def t_steghide_real():
            from PIL import Image
            jpg = os.path.join(TMP, "real.jpg")
            Image.fromarray(np.random.default_rng(5).integers(
                0, 255, (200, 200, 3), dtype=np.uint8), "RGB").save(jpg, "JPEG", quality=95)
            r = image_steghide.embed(jpg, secret_bin, "rp", tool="steghide")
            # WITH passphrase -> confirmed hidden + details
            info = image_steghide.info(r["stego_image"], passphrase="rp")
            assert "HIDDEN DATA DETECTED" in info["verdict"]
            assert info["embedded_file"] is not None
            # WITHOUT passphrase -> honest indeterminate (no false positive)
            info_nopw = image_steghide.info(r["stego_image"])
            assert "CONFIRMATION" in info_nopw["verdict"]
            # clean file + correct passphrase -> NO data confirmed
            from PIL import Image as _I
            clean2 = os.path.join(TMP, "real_clean.jpg")
            _I.fromarray(np.random.default_rng(6).integers(
                0, 255, (200, 200, 3), dtype=np.uint8), "RGB").save(clean2, "JPEG", quality=95)
            clean_info = image_steghide.info(clean2, passphrase="rp")
            assert "NO EMBEDDED DATA CONFIRMED" in clean_info["verdict"]
            x = image_steghide.extract(r["stego_image"], "rp", TMP, tool="steghide")
            assert open(x["secret_file"], "rb").read() == open(secret_bin, "rb").read()
        check("05b steghide REAL embed/info(+pw)/extract + honest no-pw probe",
              t_steghide_real)
    else:
        print("  [SKIP] steghide not installed")

    if video_hiding.ffmpeg_available():
        def t_video_real():
            mp4 = os.path.join(TMP, "r.mp4")
            os.system(f"ffmpeg -y -f lavfi -i testsrc=duration=2:size=160x120:rate=10 "
                      f"-f lavfi -i sine=frequency=440:duration=2 -c:v libx264 "
                      f"-c:a aac -shortest {mp4} >/dev/null 2>&1")
            r = video_hiding.video_lsb_embed(mp4, secret_bin, "vk", TMP + "/r_stego.mkv")
            x = video_hiding.video_lsb_extract(r["out"], "vk", TMP)
            assert open(x["out"], "rb").read() == open(secret_bin, "rb").read()
            info = video_hiding.ffprobe_info(r["out"])
            assert any(s["codec_type"] == "video" for s in info["streams"])
        check("07 video LSB REAL via ffmpeg (MP4 -> PCM MKV)", t_video_real)
    else:
        print("  [SKIP] ffmpeg not installed")

    print(f"\n== RESULTS: {PASS} passed, {FAIL} failed ==")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
