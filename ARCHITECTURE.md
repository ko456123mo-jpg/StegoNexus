# StegoNexus — Architecture

Unified Hiding, Extraction & Forensics Framework · Kali Linux
Author: Mohammed Moneer Al-absi

## 1. Design goals

1. One Dashboard for **all** term techniques (Text/Image/Audio/Video/Network/Malware
   hiding + Hashing + Forensics).
2. Every result is **tied to a Case** and can be **saved into Reports / Logs**.
3. **Kali-first**: use the real external tools when installed
   (`steghide`, `exiftool`, `binwalk`, `foremost`, `zsteg`, `file`, `strings`,
   `ffmpeg`, `ffprobe`); **built-in Python fallbacks** guarantee the tool always
   works, even on a bare box.

## 2. Layers

```
┌──────────────────────────────────────────────────────────────┐
│  PRESENTATION                                                  │
│   GUI  (PySide6 Dashboard, stegonexus/gui)                    │
│   CLI  (argparse, stegonexus/cli.py)                          │
├──────────────────────────────────────────────────────────────┤
│  CASE LAYER  (stegonexus/case/manager.py)                     │
│   cases/<CASE-ID>/case.json + reports/ (md|json|html)         │
│   + logs/investigation.log ; every op is recorded             │
├──────────────────────────────────────────────────────────────┤
│  CORE MODULES  (stegonexus/core, one per sheet section)       │
│   hashing   entropy   text_hiding   image_stego               │
│   image_steghide   audio_hiding   pcap_io   network_hiding    │
│   video_hiding   malware_lab   forensics                      │
├──────────────────────────────────────────────────────────────┤
│  EXTERNAL TOOLS  (optional, auto-detected)                    │
│   steghide · exiftool · binwalk · foremost · zsteg ·          │
│   file · strings · ffmpeg · ffprobe                           │
└──────────────────────────────────────────────────────────────┘
```

## 3. Common payload pattern (hiding modules)

```
MAGIC(4B) | LENGTH(4B) | CIPHERTEXT(secret XOR keystream)
```
* keystream = PBKDF2-HMAC-SHA256(key, module-salt, iters) — the **Key**
  (or Password) is mandatory in every hiding module.
* bits are spread over carriers through a **keyed permutation**
  (Fisher–Yates seeded by derived key): wrong key ⇒ pseudo-random bit order ⇒
  no recovery. Extras: AES-256-CBC+HMAC for images (CyberHide mode),
  key-signed footer for containers, HMAC failure = wrong password detection.

## 4. Module data-flows (sections 04–08)

| Section | Hiding | Extraction | Carrier |
|---------|--------|-----------|---------|
| 04 Text | Cover+Secret+Key → LSB of Unicode code-points → Stego Text | Stego+Key → LSB decode → Secret | characters |
| 05 Image | Image+Secret+Password → steghide (JPEG) **or** AES-LSB (PNG) → Stego Image | Stego+Password → Original Secret File | RGB channel LSBs |
| 06 Audio | LSB / Phase(±π/2 between FFT frames) / SS(BPSK chips) / Metadata(ICMT) | matching reverse | PCM samples / FFT phases / RIFF INFO |
| 07 Video | ffprobe → ffmpeg audio→WAV → audio engine → **PCM re-mux (MKV)**; or container append | reverse | audio track LSBs / appended container |
| 08 Network | Secret→bits→packets (IP-ID LSB / ISN LSB / delays) → PCAP | parse PCAP → keyed de-permutation → reassemble | IPv4 ID, TCP ISN, inter-arrival timing |

## 5. Forensics pipeline (section 02)

`forensics.aggregate(file)` runs: `file` (+magic fallback) → `strings`
(+keyword triage) → `exiftool` (+Pillow) → `binwalk` (+signature scan) →
`steghide info` (+dummy-passphrase probe) → `foremost` (+signature carving) →
`zsteg` (+LSB stats) → **Shannon entropy** (file + sliding-window regions) →
one merged `verdict` → `case.add_finding()`.
Entropy: H = −Σ pᵢ·log₂ pᵢ (bits/byte); regions ≥7.5 bits/byte are flagged.

## 6. Detections implemented

* **Steghide**: `steghide info` with a dummy passphrase — the
  *"could not extract any data with that passphrase!"* answer proves a
  passphrase-protected payload exists (no TTY needed, never hangs).
* **Network**: IP-ID deltas >3, balanced non-alternating LSB streams,
  bimodal inter-packet delays.
* **Malware**: PE/ELF section entropy >7.0, overlay/appended data,
  PyInstaller (`MEI\014\013`, `PYZ-00.pyz`), WinRAR (`Rar!`), Sliver,
  Metasploit (`meterpreter`, `msfvenom`) byte artefacts.
* **Audio**: LSB entropy ≈1.0, ICMT metadata, spectrogram/waveform export.

## 7. Known limitations (documented in the code)

* Text LSB survives **transport as-is** only — HTML/XML/line-wrap re-encoding
  destroys the bit alignment (academic method, stated in the sheet).
* Lossy codecs (AAC, H.264) destroy LSB payloads → VideoHide re-muxes audio as
  **PCM in MKV**; append-style container hiding works on any file.
* Spread-Spectrum works best on quiet covers (documented constraint).

## 8. Testing

`tests/test_integration.py` — 20 end-to-end checks: hashing algorithms, text
hide/reveal (+wrong key), image AES-LSB round trip + probe, 4 audio methods +
spectrogram/waveform, video container + videohide.sh + stream info,
network ipid/isn/timing + detection, malware stub + scan, forensics aggregate,
case persistence + reports + logs.
