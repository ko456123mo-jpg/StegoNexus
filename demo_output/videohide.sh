#!/usr/bin/env bash
# ============================================================
# videohide.sh - Video Hide / Reveal  (StegoNexus VideoHide module)
# Flow: ffprobe -> ffmpeg audio extraction -> audio LSB/SS hiding
#       -> ffmpeg re-mux (streams preserved with -c:v copy)
# Usage:
#   ./videohide.sh hide <cover.mp4> <secret.bin> <key> <out.mp4>
#   ./videohide.sh reveal <stego.mp4> <key> <out.bin>
# ============================================================
set -euo pipefail
CMD="${1:-}"; shift || true

hide() {
  VIDEO="$1"; SECRET="$2"; KEY="$3"; OUT="$4"
  TMP="$(mktemp -d)"
  echo "[*] ffprobe: inspecting streams..."
  ffprobe -v error -show_streams "$VIDEO" || true
  echo "[*] extracting audio track to WAV..."
  ffmpeg -y -i "$VIDEO" -vn -ac 1 -ar 44100 -acodec pcm_s16le "$TMP/a.wav"
  echo "[*] hiding in audio LSB..."
  python3 - "$TMP/a.wav" "$SECRET" "$KEY" "$TMP/s.wav" <<'PY'
import sys
from stegonexus.core import audio_hiding
audio_hiding.lsb_embed(sys.argv[1], sys.argv[2], sys.argv[3], out_path=sys.argv[4])
PY
  echo "[*] re-muxing stego audio into video (PCM keeps the LSB payload intact)"
  ffmpeg -y -i "$VIDEO" -i "$TMP/s.wav" -map 0:v -map 1:a -c:v copy -c:a pcm_s16le "$OUT"
  rm -rf "$TMP"
  echo "[+] stego video written: $OUT"
}

reveal() {
  VIDEO="$1"; KEY="$2"; OUT="$3"
  TMP="$(mktemp -d)"
  echo "[*] extracting audio track..."
  ffmpeg -y -i "$VIDEO" -vn -ac 1 -ar 44100 -acodec pcm_s16le "$TMP/a.wav"
  echo "[*] extracting hidden data..."
  python3 - "$TMP/a.wav" "$KEY" "$OUT" <<'PY'
import sys
from stegonexus.core import audio_hiding
audio_hiding.lsb_extract(sys.argv[1], sys.argv[2], out_dir=__import__('os').path.dirname(sys.argv[3]))
PY
  rm -rf "$TMP"
  echo "[+] recovered file: $OUT"
}

case "$CMD" in
  hide)   hide "$@";;
  reveal) reveal "$@";;
  *) echo "usage: $0 {hide|reveal} ..."; exit 1;;
esac
