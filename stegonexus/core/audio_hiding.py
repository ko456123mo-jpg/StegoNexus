"""
Module 06 - Audio Hiding
========================
Required techniques: LSB, Phase Coding, Spread Spectrum, Metadata,
plus Audacity-style Spectrogram Frequency Analysis & Waveform export.

All methods operate on 16-bit PCM WAV files (pure Python + numpy), so the
Dashboard can hide/extract without external tools; WAV files produced here
open directly in Audacity for manual frequency analysis.

  * LSB             : keyed-permutation LSB embedding (samples are carriers)
  * Phase Coding    : secret bits are coded into the phase difference of
                      consecutive FFT frames (perceptual robustness)
  * Spread Spectrum : direct-sequence BSSK — each bit is spread over a
                      key-derived PN sequence and embedded with low amplitude
  * Metadata        : secret stored in RIFF INFO comment chunk (ICMT)
  * Analysis        : spectrogram + waveform PNG generation, entropy metrics
"""

from __future__ import annotations

import math
import os
import random as _random
import struct
import wave
from typing import List, Optional, Tuple

import numpy as np

from stegonexus.core.text_hiding import derive_key, xor_crypt

MAGIC = b"SNAU"                 # StegoNexus audio marker
RATE = 44100
FRAME = 1024                    # FFT frame size for phase coding
PN_LEN = 64                     # chips per bit for spread spectrum
ALPHA = 2500                    # embedding amplitude for spread spectrum
NOTE_SS = ("Spread-spectrum needs a quiet cover (low-amplitude signal); "
           "ALPHA must dominate the carrier level for clean correlation.")


# ------------------------------------------------------------------------ #
# WAV IO helpers
# ------------------------------------------------------------------------ #
def load_wav(path: str) -> Tuple[np.ndarray, int, int]:
    """Return (samples int16 mono, sample_rate, bits_per_sample)."""
    with wave.open(path, "rb") as w:
        n = w.getnframes()
        ch = w.getnchannels()
        sw = w.getsampwidth()
        rate = w.getframerate()
        raw = w.readframes(n)
    if ch > 1:
        data = np.frombuffer(raw, dtype="<i2").reshape(-1, ch)
        data = data.mean(axis=1).astype(np.int16)      # downmix to mono
    else:
        data = np.frombuffer(raw, dtype="<i2")
    return data, rate, sw * 8


def save_wav(path: str, samples: np.ndarray, rate: int = RATE) -> None:
    s = np.clip(samples, -32768, 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(s.tobytes())


def _bits(data: bytes) -> List[int]:
    return [(b >> s) & 1 for b in data for s in range(7, -1, -1)]


def _from_bits(bits: List[int]) -> bytes:
    out = bytearray()
    for i in range(0, len(bits) - 7, 8):
        byte = 0
        for b in bits[i:i + 8]:
            byte = (byte << 1) | b
        out.append(byte)
    return bytes(out)


def _perm(n: int, seed: bytes) -> List[int]:
    rng = _random.Random(seed)
    idx = list(range(n))
    for i in range(n - 1, 0, -1):
        j = rng.randint(0, i)
        idx[i], idx[j] = idx[j], idx[i]
    return idx


def _encrypt(secret: bytes, key: str) -> bytes:
    ks = derive_key(key, b"StegoNexus-Audio", 80_000)
    return MAGIC + len(secret).to_bytes(4, "big") + xor_crypt(secret, ks)


def _decrypt(blob: bytes, key: str) -> Optional[bytes]:
    if len(blob) < 8 or blob[:4] != MAGIC:
        return None
    size = int.from_bytes(blob[4:8], "big")
    ks = derive_key(key, b"StegoNexus-Audio", 80_000)
    return xor_crypt(blob[8:], ks)[:size]


# ======================================================================= #
# 1) LSB
# ======================================================================= #
def lsb_embed(wav_path: str, secret_path: str, key: str, out_path: Optional[str] = None) -> dict:
    from numpy import array
    samples, rate, _bps = load_wav(wav_path)
    secret = open(secret_path, "rb").read()
    payload = _encrypt(secret, key)
    bits = _bits(payload)
    if len(bits) > len(samples):
        raise ValueError(f"Audio too short: need {len(bits)} sample LSBs, have {len(samples)}")
    order = _perm(len(samples), derive_key(key, b"StegoNexus-Audio")[:16])
    s = samples.copy()
    for i, pos in enumerate(order[:len(bits)]):
        s[pos] = (s[pos] & ~1) | bits[i]
    out = out_path or os.path.join(os.path.dirname(os.path.abspath(wav_path)),
                                   os.path.splitext(os.path.basename(wav_path))[0] + "_stego.wav")
    save_wav(out, s, rate)
    return {"method": "Audio LSB (keyed permutation)", "ok": True, "out": out,
            "payload_bytes": len(payload), "secret_bytes": len(secret)}


def lsb_extract(wav_path: str, key: str, out_dir: Optional[str] = None) -> dict:
    samples, rate, _ = load_wav(wav_path)
    order = _perm(len(samples), derive_key(key, b"StegoNexus-Audio")[:16])
    bits: List[int] = []
    for i, pos in enumerate(order):
        bits.append(int(samples[pos] & 1))
        if i >= 8 * 8 - 1 and len(bits) % 8 == 0:
            header = _from_bits(bits[:64])
            if len(header) == 8 and header[:4] != MAGIC:
                raise ValueError("No StegoNexus payload (wrong key or not a stego file)")
            if len(header) == 8:
                total = 8 + int.from_bytes(header[4:8], "big")
                if total * 8 > len(samples):
                    total = len(samples) // 8
                if len(bits) >= total * 8:
                    break
    blob = _from_bits(bits)
    secret = _decrypt(blob, key)
    if secret is None:
        raise ValueError("Wrong key or corrupted audio")
    out_dir = out_dir or os.path.dirname(os.path.abspath(wav_path))
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "extracted_secret.bin")
    open(out, "wb").write(secret)
    return {"method": "Audio LSB", "ok": True, "out": out, "secret_bytes": len(secret)}


# ======================================================================= #
# 2) Phase Coding  (bits -> phase difference between consecutive FFT frames)
# ======================================================================= #
def phase_embed(wav_path: str, secret_path: str, key: str, out_path: Optional[str] = None) -> dict:
    samples, rate, _ = load_wav(wav_path)
    secret = open(secret_path, "rb").read()
    payload = _encrypt(secret, key)
    bits = _bits(payload)

    n = len(samples)
    nframes = n // FRAME
    need = (nframes - 1) // 2          # one bit per 2 frames (neighbors pair)
    if len(bits) > need:
        raise ValueError(f"Audio too short for payload: need {len(bits)} bits, audio supports {need} (frame={FRAME})")

    frames = samples[:nframes * FRAME].reshape(nframes, FRAME).astype(np.float64)
    spectra = np.fft.rfft(frames, axis=1)              # (nframes, FRAME/2+1)
    mag = np.abs(spectra)
    phase = np.angle(spectra)
    key_seed = derive_key(key, b"StegoNexus-Phase")[:16]
    rng = _random.Random(key_seed)
    bins = list(range(2, FRAME // 2 - 10))             # skip DC + extremes
    rng.shuffle(bins)

    # encode bit b in frame pair (f0,f1): phase difference ~ +π/2 (1) / -π/2 (0)
    mod = phase.copy()
    count = 0
    for f0 in range(0, nframes - 1, 2):
        if count >= len(bits):
            break
        for b in bins:                                 # carry the same bit in many bins
            delta = math.pi / 2 if bits[count] == 1 else -math.pi / 2
            mod[f0 + 1, b] = phase[f0, b] + delta
        count += 1
    stego_spectra = mag * np.exp(1j * mod)
    stego = np.fft.irfft(stego_spectra, n=FRAME, axis=1).flatten()
    # preserve original length
    stego = stego[:n]
    out = out_path or os.path.join(os.path.dirname(os.path.abspath(wav_path)),
                                   os.path.splitext(os.path.basename(wav_path))[0] + "_phase.wav")
    save_wav(out, stego.astype(np.int16), rate)
    return {"method": "Phase Coding (π/2 phase-difference, multi-bin)", "ok": True, "out": out,
            "payload_bits": len(bits), "frames_used": count}


def phase_extract(wav_path: str, key: str, out_dir: Optional[str] = None) -> dict:
    samples, rate, _ = load_wav(wav_path)
    n = len(samples)
    nframes = n // FRAME
    frames = samples[:nframes * FRAME].reshape(nframes, FRAME).astype(np.float64)
    spectra = np.fft.rfft(frames, axis=1)
    phase = np.angle(spectra)
    key_seed = derive_key(key, b"StegoNexus-Phase")[:16]
    rng = _random.Random(key_seed)
    bins = list(range(2, FRAME // 2 - 10))
    rng.shuffle(bins)

    bits: List[int] = []
    for f0 in range(0, nframes - 1, 2):
        # majority vote across bins: d = embedded ±π/2; sin(d) gives the sign
        votes = 0
        for b in bins:
            d = phase[f0 + 1, b] - phase[f0, b]
            votes += 1 if math.sin(d) > 0 else -1
        bits.append(1 if votes > 0 else 0)
        if len(bits) >= 64 and len(bits) % 8 == 0:
            header = _from_bits(bits[:64])
            if len(header) == 8:
                if header[:4] != MAGIC:
                    # early sanity: if header is full and wrong -> wrong key/file
                    pass
                total = 8 + int.from_bytes(header[4:8], "big")
                if len(bits) >= total * 8:
                    break
    blob = _from_bits(bits)
    secret = _decrypt(blob, key)
    if secret is None:
        raise ValueError(
            "Phase decoding failed: wrong key, or the stego audio was "
            "re-sampled/re-encoded. Note: Phase Coding needs a broadband cover "
            "(music / noise) — pure tones leave most frequency bins empty.")
    out_dir = out_dir or os.path.dirname(os.path.abspath(wav_path))
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "extracted_secret.bin")
    open(out, "wb").write(secret)
    return {"method": "Phase Coding", "ok": True, "out": out, "secret_bytes": len(secret)}


# ======================================================================= #
# 3) Spread Spectrum (direct-sequence BPSK, key-derived PN sequence)
# ======================================================================= #
def _pn(seed: bytes, length: int) -> np.ndarray:
    rng = _random.Random(seed)
    return np.array([1.0 if rng.random() < 0.5 else -1.0 for _ in range(length)])


def ss_embed(wav_path: str, secret_path: str, key: str, out_path: Optional[str] = None,
             amplitude: int = ALPHA) -> dict:
    samples, rate, _ = load_wav(wav_path)
    secret = open(secret_path, "rb").read()
    payload = _encrypt(secret, key)
    bits = _bits(payload)
    need = len(bits) * PN_LEN
    if need > len(samples):
        raise ValueError(f"Audio too short for spread spectrum payload: need {need} samples")
    seed = derive_key(key, b"StegoNexus-SS")[:16]
    pn = _pn(seed, PN_LEN)
    s = samples.astype(np.float64).copy()
    for i, bit in enumerate(bits):
        sign = 1.0 if bit == 1 else -1.0
        chip = i * PN_LEN
        s[chip:chip + PN_LEN] += amplitude * sign * pn
    out = out_path or os.path.join(os.path.dirname(os.path.abspath(wav_path)),
                                   os.path.splitext(os.path.basename(wav_path))[0] + "_ss.wav")
    save_wav(out, s, rate)
    return {"method": "Spread Spectrum (DSSS-BPSK)", "ok": True, "out": out,
            "payload_bits": len(bits), "chips_per_bit": PN_LEN, "amplitude": amplitude}


def ss_extract(wav_path: str, key: str, out_dir: Optional[str] = None) -> dict:
    samples, rate, _ = load_wav(wav_path)
    seed = derive_key(key, b"StegoNexus-SS")[:16]
    pn = _pn(seed, PN_LEN)
    s = samples.astype(np.float64)
    n_chips = len(s) // PN_LEN
    bits: List[int] = []
    for i in range(n_chips):
        block = s[i * PN_LEN:(i + 1) * PN_LEN]
        corr = float(np.dot(block, pn) / PN_LEN)
        bits.append(1 if corr > 0 else 0)
        if len(bits) >= 64 and len(bits) % 8 == 0:
            header = _from_bits(bits[:64])
            if len(header) == 8 and header[:4] == MAGIC:
                total = 8 + int.from_bytes(header[4:8], "big")
                if len(bits) >= total * 8:
                    break
            elif len(header) == 8 and len(bits) > 800:
                break
    blob = _from_bits(bits)
    secret = _decrypt(blob, key)
    if secret is None:
        raise ValueError("Spread-spectrum decoding failed (wrong key / not stego)")
    out_dir = out_dir or os.path.dirname(os.path.abspath(wav_path))
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "extracted_secret.bin")
    open(out, "wb").write(secret)
    return {"method": "Spread Spectrum", "ok": True, "out": out, "secret_bytes": len(secret)}


# ======================================================================= #
# 4) Metadata (RIFF LIST-INFO ICMT comment chunk)
# ======================================================================= #
def _riff_chunks(data: bytes):
    """Yield (id, payload) for RIFF sub-chunks of a WAV file."""
    pos = 12
    while pos + 8 <= len(data):
        cid = data[pos:pos + 4]
        size = struct.unpack("<I", data[pos + 4:pos + 8])[0]
        yield cid, data[pos:pos + 8 + size + (size & 1)]
        pos += 8 + size + (size & 1)


def meta_embed(wav_path: str, secret_path: str, key: str, out_path: Optional[str] = None) -> dict:
    secret = open(secret_path, "rb").read()
    payload = _encrypt(secret, key)                       # MAGIC + size + encrypted
    with open(wav_path, "rb") as fh:
        data = fh.read()
    if data[:4] != b"RIFF":
        raise ValueError("Not a RIFF/WAV file")

    # build a LIST-INFO chunk carrying ICMT (comment) = base64 blob
    import base64
    comment = base64.b64encode(payload).decode("ascii")
    info_body = b"INFO" + b"ICMT" + struct.pack("<I", len(comment) + 1) + \
        comment.encode() + b"\x00"
    info_body += b"\x00" if len(info_body) & 1 else b""
    info = b"LIST" + struct.pack("<I", len(info_body)) + info_body

    # strip any existing LIST chunks, then append the new LIST right after fmt
    out = bytearray(data[:12])          # keep the RIFF/WAVE header!
    pos = 12
    inserted = False
    while pos + 8 <= len(data):
        cid = data[pos:pos + 4]
        size = struct.unpack("<I", data[pos + 4:pos + 8])[0]
        chunk = data[pos:pos + 8 + size + (size & 1)]
        if cid == b"LIST":
            pos += len(chunk)
            continue
        out += chunk
        if cid == b"fmt " and not inserted:
            out += info
            inserted = True
        pos += len(chunk)
    if not inserted:
        out = out[:12] + info + out[12:]
    # fix sizes
    riff_size = len(out) - 8
    out[4:8] = struct.pack("<I", riff_size)
    out_path = out_path or os.path.join(os.path.dirname(os.path.abspath(wav_path)),
                                        os.path.splitext(os.path.basename(wav_path))[0] + "_meta.wav")
    with open(out_path, "wb") as fh:
        fh.write(bytes(out))
    return {"method": "Metadata (RIFF LIST-INFO ICMT)", "ok": True, "out": out_path,
            "comment_bytes": len(comment)}


def meta_extract(wav_path: str, key: str, out_dir: Optional[str] = None) -> dict:
    import base64
    with open(wav_path, "rb") as fh:
        data = fh.read()
    blob = None
    for cid, payload in _riff_chunks(data):
        if cid == b"LIST":
            p = payload[8:]
            if p[:4] == b"INFO":        # skip the LIST form-type
                p = p[4:]
            pos = 0
            while pos + 8 <= len(p):
                sub = p[pos:pos + 4]
                size = struct.unpack("<I", p[pos + 4:pos + 8])[0]
                val = p[pos + 8:pos + 8 + size]
                if sub == b"ICMT":
                    try:
                        blob = base64.b64decode(val.rstrip(b"\x00").decode("ascii"))
                    except Exception:
                        blob = None
                pos += 8 + size + (size & 1)
    if not blob:
        raise ValueError("No ICMT metadata chunk found (not a stego file)")
    secret = _decrypt(blob, key)
    if secret is None:
        raise ValueError("Wrong key or the comment is not a StegoNexus payload")
    out_dir = out_dir or os.path.dirname(os.path.abspath(wav_path))
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "extracted_secret.bin")
    open(out, "wb").write(secret)
    return {"method": "Metadata", "ok": True, "out": out, "secret_bytes": len(secret)}


# ======================================================================= #
# 5) Analysis: spectrogram / waveform PNG (Audacity-style output)
# ======================================================================= #
def _heat_to_rgb(v: np.ndarray) -> np.ndarray:
    """Map normalized values to a jEt-like colormap (pure numpy)."""
    v = np.clip(v, 0, 1)
    r = np.clip(1.5 - np.abs(4 * v - 3), 0, 1)
    g = np.clip(1.5 - np.abs(4 * v - 2), 0, 1)
    b = np.clip(1.5 - np.abs(4 * v - 1), 0, 1)
    return np.stack([r, g, b], axis=-1)


def make_spectrogram(wav_path: str, out_png: str, nfft: int = 512, hop: int = 256,
                     max_freq: Optional[float] = None) -> dict:
    """Generate a spectrogram PNG for frequency-domain inspection (Audacity style)."""
    samples, rate, _ = load_wav(wav_path)
    win = np.hanning(nfft)
    frames = []
    for start in range(0, len(samples) - nfft, hop):
        frame = samples[start:start + nfft].astype(np.float64) * win
        frames.append(np.abs(np.fft.rfft(frame))[:nfft // 2])
    spec = np.array(frames).T                       # (freq, time)
    if max_freq:
        spec = spec[:int(nfft // 2 * max_freq / (rate / 2))]
    spec_db = 20 * np.log10(spec + 1e-12)
    spec_db -= spec_db.min()
    spec_db /= max(spec_db.max(), 1e-9)
    img = (255 * _heat_to_rgb(spec_db.T)).astype(np.uint8)
    from PIL import Image
    im = Image.fromarray(img, "RGB")
    im = im.resize((max(img.shape[1], 320), max(img.shape[0], 240)))
    im.save(out_png)
    return {"out": out_png, "method": "Spectrogram (STFT)", "nfft": nfft,
            "hop": hop, "rate": rate, "audio": wav_path}


def make_waveform(wav_path: str, out_png: str, width: int = 1200, height: int = 300) -> dict:
    """Generate a waveform preview PNG."""
    samples, rate, _ = load_wav(wav_path)
    step = max(1, len(samples) // (width * 8))
    chunk = samples[::step]
    seg = max(1, len(chunk) // width)
    peaks = []
    for i in range(0, len(chunk) - seg, seg):
        c = chunk[i:i + seg]
        peaks.append(float(np.max(np.abs(c))))
    peaks = np.array(peaks)
    peaks = np.clip(peaks / max(float(peaks.max()), 1e-9), 0, 1)
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (width, height), (8, 10, 14))
    d = ImageDraw.Draw(im)
    mid = height / 2
    for x, p in enumerate(peaks):
        h = p * (height / 2 - 4)
        d.line([(x, mid - h), (x, mid + h)], fill=(0, 220, 130))
    im.save(out_png)
    return {"out": out_png, "method": "Waveform", "audio": wav_path, "rate": rate}


def analyze(wav_path: str) -> dict:
    """Quick forensic pass: entropy, metadata, spectral stats, LSB stats.
    LSB verdict uses balance + TRANSITION RATE: natural audio has structured
    LSBs (long runs / alternating patterns); embedded random payloads raise
    the LSB transition rate toward a balanced, non-deterministic mix."""
    samples, rate, _ = load_wav(wav_path)
    bits = [int(s & 1) for s in samples]
    n = len(bits)
    p1 = sum(bits) / n if n else 0.5
    p0 = 1 - p1
    lsb_entropy = 0.0
    if 0 < p1 < 1:
        lsb_entropy = -(p0 * math.log2(p0) + p1 * math.log2(p1))
    transitions = (sum(1 for i in range(n - 1) if bits[i] != bits[i + 1]) / (n - 1)
                   if n > 1 else 0.0)
    # honest grading: 16-bit PCM LSBs are typically noise-like (both clean
    # and stego files show p1~0.5 / transitions~0.5), so statistics alone
    # cannot discriminate; we only claim an anomaly for EXTREME structures.
    info = None
    with open(wav_path, "rb") as fh:
        data = fh.read()
    found = data.find(b"ICMT")
    if found >= 0:
        info = "ICMT comment metadata chunk present"
    # Steghide supports WAV/AU containers -> included among the analysis
    # tools (requirement 06). Honest reporting: steghide only confirms data
    # WITH the passphrase; without it the answer is indeterminate.
    steghide_check = None
    try:
        from stegonexus.core import image_steghide
        if image_steghide.steghide_available():
            res = image_steghide.info(wav_path)
            steghide_check = res["verdict"]
    except Exception:
        steghide_check = None
    if info:
        verdict = "HIDING INDICATOR: ICMT comment metadata chunk present"
    elif steghide_check and "HIDDEN DATA DETECTED" in str(steghide_check):
        verdict = "HIDING INDICATOR: steghide payload in the audio file"
    elif transitions > 0.95:
        verdict = "STRUCTURED TOGGLING LSB STREAM (no embedded-random payload indicated)"
    elif p1 < 0.2 or p1 > 0.8:
        verdict = "SKEWED LSB STREAM (no embedded-random payload indicated)"
    else:
        verdict = ("INDETERMINATE - LSB statistics are noise-like (typical of "
                   "16-bit PCM, with or without payload); no reliable anomaly")
    return {
        "audio": wav_path, "rate": rate, "samples": int(len(samples)),
        "duration_s": round(len(samples) / rate, 2),
        "lsb_entropy": round(lsb_entropy, 4),
        "lsb_balance_p1": round(p1, 4),
        "lsb_transitions": round(transitions, 4),
        "metadata_chunks": info,
        "steghide_check": steghide_check,
        "verdict": verdict,
    }


__all__ = ["lsb_embed", "lsb_extract", "phase_embed", "phase_extract",
           "ss_embed", "ss_extract", "meta_embed", "meta_extract",
           "make_spectrogram", "make_waveform", "analyze",
           "load_wav", "save_wav"]
