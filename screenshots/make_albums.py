#!/usr/bin/env python3
"""Build combined album sheets (grids) from the captured screenshots."""
from __future__ import annotations

import os

from PIL import Image, ImageDraw, ImageFont

OUT = os.path.dirname(os.path.abspath(__file__))


def font(size):
    try:
        return ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)
    except Exception:
        return ImageFont.load_default()


def grid(names, out, cols=3, cell_w=640, cell_h=400, pad=10, title=""):
    tiles = []
    for name in names:
        p = os.path.join(OUT, name)
        if os.path.exists(p):
            tiles.append((name, Image.open(p)))
    rows = (len(tiles) + cols - 1) // cols
    w = cols * cell_w + (cols + 1) * pad
    h = rows * (cell_h + 26) + (rows + 1) * pad + (34 if title else 0)
    canvas = Image.new("RGB", (w, h), (10, 13, 18))
    d = ImageDraw.Draw(canvas)
    y = pad
    if title:
        d.text((pad, 8), title, fill=(0, 217, 139), font=font(20))
        y = 42
    for i, (name, img) in enumerate(tiles):
        r, c = divmod(i, cols)
        x = pad + c * (cell_w + pad)
        yy = y + r * (cell_h + 26)
        img.thumbnail((cell_w, cell_h), Image.LANCZOS)
        canvas.paste(img, (x + (cell_w - img.width) // 2,
                           yy + (cell_h - img.height) // 2))
        d.text((x, yy + cell_h + 4), name.replace(".png", ""),
               fill=(150, 164, 181), font=font(13))
    canvas.save(out)
    print("saved", os.path.basename(out), canvas.size)


def main():
    gui = [f"0{i}_" for i in range(1, 10)] or []
    gui_names = ["01_dashboard.png", "02_forensics_run.png", "03_hashing.png",
                 "04_text_hiding.png", "05_image_hiding.png", "06_audio_hiding.png",
                 "07_video_hiding.png", "08_network_hiding.png", "09_malware_lab.png",
                 "11_case_management.png"]
    grid(gui_names, os.path.join(OUT, "GUISheet_dashboard.png"),
         cols=3, cell_w=660, cell_h=420,
         title="StegoNexus Dashboard — GUI (PySide6) · Kali toolchain 7/7")

    cli_names = ["cli_01_toolchain.png", "cli_02_hashing.png", "cli_03_text_lsb.png",
                 "cli_04_image_steghide.png", "cli_05_audio.png", "cli_06_video.png",
                 "cli_07_network.png", "cli_08_malware.png", "cli_09_forensics.png",
                 "cli_10_case.png", "cli_11_tests.png"]
    grid(cli_names, os.path.join(OUT, "CLISheet_terminal.png"),
         cols=3, cell_w=660, cell_h=420,
         title="StegoNexus CLI — real commands on Kali-style terminal")


if __name__ == "__main__":
    main()
