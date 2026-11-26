#!/usr/bin/env python3
"""Build the 1024x1024 front page (entry.png) for make.fun news-image-20261126.

Offline, deterministic: same assets in -> same bytes out. No network, no
clock, no randomness. Reads the seven original illustrations from assets/
and the story list from data/stories.json, then composites:

  masthead  (0-96)     navy band: WORLD NEWS + THURSDAY 26 NOVEMBER 2026
  lead      (108-532)  full-width panel + dark gradient strip + headline
  grid      (544-968)  2 columns x 3 rows: square illustration + chip + headline
  footer    (968-1024) reporting credit line

Run from the repo root:  python3 build/build_image.py
"""

import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ASSETS = os.path.join(ROOT, "assets")
OUT = os.path.join(ROOT, "entry.png")

W, H = 1024, 1024
NAVY = (16, 30, 51)
RED = (214, 40, 40)
SAND = (242, 193, 78)
SAND_BG = (245, 239, 227)
WHITE = (255, 255, 255)

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]


def load_font(size):
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default()


def wrap(draw, text, font, max_width):
    """Greedy word wrap; returns a list of lines that fit max_width."""
    words = text.split()
    lines, cur = [], ""
    for word in words:
        trial = (cur + " " + word).strip()
        if draw.textlength(trial, font=font) <= max_width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def chip(draw, x, y, text, font):
    """Red chip with white bold text; returns its width."""
    pad_x, pad_y = 10, 5
    tw = draw.textlength(text, font=font)
    bw = int(tw + 2 * pad_x)
    bh = font.size + 2 * pad_y
    draw.rounded_rectangle([x, y, x + bw, y + bh], radius=4, fill=RED)
    draw.text((x + pad_x, y + pad_y), text, font=font, fill=WHITE)
    return bw, bh


def vertical_gradient(size, max_alpha=217):
    """1-column alpha ramp (transparent at top, dark at bottom), resized."""
    w, h = size
    ramp = Image.new("L", (1, h))
    for yy in range(h):
        ramp.putpixel((0, yy), int(max_alpha * (yy / max(h - 1, 1)) ** 1.1))
    return ramp.resize((w, h))


def main():
    with open(os.path.join(ROOT, "data", "stories.json"), encoding="utf-8") as f:
        data = json.load(f)
    stories = data["stories"]
    lead = next(s for s in stories if s["role"] == "lead")
    rest = [s for s in stories if s["role"] != "lead"]
    if len(rest) != 6:
        sys.exit("expected 6 supporting stories, got %d" % len(rest))

    page = Image.new("RGB", (W, H), WHITE)
    draw = ImageDraw.Draw(page)

    # ---- masthead ----
    draw.rectangle([0, 0, W, 96], fill=NAVY)
    draw.rectangle([0, 96, W, 102], fill=RED)
    draw.text((24, 8), "WORLD NEWS", font=load_font(42), fill=WHITE)
    draw.text((24, 54), "THURSDAY 26 NOVEMBER 2026",
              font=load_font(32), fill=SAND)

    # ---- lead panel ----
    lx, ly, lw, lh = 24, 108, 976, 424
    lead_img = Image.open(os.path.join(ASSETS, lead["id"] + ".jpg")).convert("RGB")
    lead_img = ImageOps.fit(lead_img, (lw, lh), Image.LANCZOS)
    lead_img = lead_img.convert("RGBA")
    strip_h = 224
    black = Image.new("RGBA", (lw, strip_h), (0, 0, 0, 255))
    lead_img.paste(black, (0, lh - strip_h), vertical_gradient((lw, strip_h), max_alpha=238))
    page.paste(lead_img.convert("RGB"), (lx, ly))
    draw = ImageDraw.Draw(page)
    chip(draw, lx + 16, ly + 16, lead["region"].upper() + " · " +
         lead["topic"].upper(), load_font(24))
    head_font = load_font(52)
    lines = wrap(draw, lead["headline_short"], head_font, lw - 32)
    y = ly + lh - 16 - len(lines) * 60
    for line in lines:
        draw.text((lx + 16, y), line, font=head_font, fill=WHITE)
        y += 60

    # ---- grid: 2 cols x 3 rows ----
    gx, gy = 24, 544
    tile_w, tile_h, gutter = 480, 133, 12
    img_s = 133
    tile_font = load_font(26)
    chip_font = load_font(22)
    for i, story in enumerate(rest):
        col, row = i % 2, i // 2
        tx = gx + col * (tile_w + gutter)
        ty = gy + row * (tile_h + gutter)
        img = Image.open(os.path.join(ASSETS, story["id"] + ".jpg")).convert("RGB")
        img = ImageOps.fit(img, (img_s, img_s), Image.LANCZOS)
        page.paste(img, (tx, ty))
        # thin sand frame around the illustration
        draw.rectangle([tx, ty, tx + img_s - 1, ty + img_s - 1],
                       outline=SAND, width=2)
        text_x = tx + img_s + 12
        text_w = tile_w - img_s - 12
        _, ch = chip(draw, text_x, ty + 4,
                     story["region"].upper(), chip_font)
        lines = wrap(draw, story["headline_short"], tile_font, text_w)
        lines = lines[:3]
        block_h = len(lines) * 31
        y = ty + ch + 4 + max(0, (tile_h - ch - 4 - block_h) // 2)
        for line in lines:
            draw.text((text_x, y), line, font=tile_font, fill=NAVY)
            y += 31

    # ---- footer ----
    draw.rectangle([0, 968, W, H], fill=SAND_BG)
    draw.rectangle([0, 968, W, 970], fill=NAVY)
    foot_font = load_font(22)
    credit = "Reporting: AP News — illustrations original"
    fw = draw.textlength(credit, font=foot_font)
    draw.text(((W - fw) / 2, 986), credit, font=foot_font, fill=NAVY)

    page.save(OUT, format="PNG", optimize=True)
    print("wrote", OUT, page.size)


if __name__ == "__main__":
    main()
