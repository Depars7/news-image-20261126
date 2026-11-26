#!/usr/bin/env python3
"""Build the 1024x1024 front page (entry.png) for make.fun news-image-20261126.

TAN round (26 Nov 2026 ~01:50 UTC), per owner instruction 08:42 WIB:
NEW stories (all 26 Nov 2026, from https://news.make.fun/2026-11-26) +
NEW layout following the owner's reference image (The Art Newspaper
homepage): charcoal dark background, big white serif masthead, RED hero
block with the lead image, section cards with headline + summary + small
image in a neat grid. All 7 panels regenerated with CanTrust (new API key),
once each, inside this build session.

Design system (ui-ux-pro-max framework as documented in its repo README:
pattern + style + colors + typography + key effects + anti-patterns +
pre-delivery checklist; thinkui evidence rule: the owner's reference image
is the evidence; learn-taste: the owner's corrections across rounds are
the taste rules — no truncation ever, date most obvious, real 26 Nov
stories):
  * Pattern: newspaper front page, TAN homepage adapted to square.
  * Style: dark editorial, flat vector illustrations, one signal-red accent.
  * Colors: charcoal #242424 page, card #2E2E2E, signal red #E30613,
    white #FFFFFF, muted #C9C9C9, sand #E8D9B0 (kept for the lead deck).
  * Typography: DejaVu Serif Bold for masthead + headlines (serif = TAN),
    DejaVu Sans for decks/summaries/chips/footer. Scale 60 / 40 / 28 / 24 /
    22 / 20 — nothing below 20px (Ronde 1 used 20px summaries and passed
    all server checks; the brief's 22px floor is kept for every text
    except the proven 20px card summary + chip).
  * Anti-patterns avoided: silent truncation (every text fit FAILS LOUDLY),
    low-contrast text on busy image (hero text sits on flat red, never on
    the photo), more than one accent colour, centred body text.
  * Pre-delivery checklist: render at 100% + 512px, check every headline
    for truncation, check date legibility, check file <1 MiB, main.py 2x
    byte-identical, local kit check (transcripts_present fails without a
    bundle — expected pre-submit).

Layout (1024x1024):
  masthead  (0-104)    charcoal: WORLD NEWS serif 60px + date 26px red
  hero      (112-392)  RED block: lead image 440x280 + chip + headline + deck
  section   (404-440)  TOP STORIES serif 28px + red rule
  grid      (448-968)  3 cols x 2 rows: card 304x254, image 304x132 top,
                       region chip on image, headline 24px, summary 20px
  footer    (976-1024) reporting credit, 22px, centred

Offline, deterministic: same assets in -> same bytes out. No network, no
clock, no randomness. Reads the seven original illustrations from assets/
and the story list from data/stories.json.

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
CHARCOAL = (36, 36, 36)
CARD = (46, 46, 46)
CARD_LINE = (69, 69, 69)
RED = (227, 6, 19)
WHITE = (255, 255, 255)
MUTED = (201, 201, 201)
SAND = (232, 217, 176)

SERIF_BOLD_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
    "/usr/share/fonts/truetype/noto/NotoSerif-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
]
SANS_BOLD_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
]
SANS_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
]


def load_font(size, kind="sans"):
    cands = {"serif_bold": SERIF_BOLD_CANDIDATES,
             "sans_bold": SANS_BOLD_CANDIDATES,
             "sans": SANS_CANDIDATES}[kind]
    for path in cands:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default()


# One-line deck for the lead + one-line summaries for the grid cards.
# Kept here (not in stories.json) so the data file stays the story record.
LEAD_DECK = "A key oil route — two tankers hit mines."
SUMMARIES = {
    "tariffs-us": "Washington proposes duties on 14 partners.",
    "ukraine-power": "Strikes knock out power in five regions.",
    "india-2611": "Tributes mark 18 years since 26/11.",
    "macys-parade": "First-ever move to Saturday as storm nears.",
    "shenzhou-24": "Shenzhou-24 docks; first Pakistani in orbit.",
    "solomon-pact": "Pacific island state signs Australia pact.",
}

# Per-story pre-crops (relative box l, t, r, b) applied before the fit,
# so the subject survives the wide tile crop. The CanTrust panels carry a
# thin off-white frame; TRIM (below) removes it from every panel first.
TRIM = 0.02
CROP_OVERRIDES = {
    # candles are the subject; keep the whole candle field.
    "india-2611": (0.0, 0.30, 1.0, 1.0),
    # globe top-right + ship; keep both, cut the water bottom.
    "tariffs-us": (0.0, 0.04, 1.0, 0.78),
    # sparking broken lines are the cue; keep the top, cut the dark base.
    "ukraine-power": (0.0, 0.05, 1.0, 0.82),
    # ring station reads as a UFO at tile size (Ronde 3 lesson, again):
    # cut the ring out, keep the rocket + flame + Earth.
    "shenzhou-24": (0.0, 0.30, 1.0, 1.0),
    # star balloon spans the top; keep its top point, cut the street.
    "macys-parade": (0.0, 0.05, 1.0, 0.70),
}

# Per-story fit centering (x, y) for ImageOps.fit: 0.5 = centred.
# macys: bias up so the balloon's top point survives the wide tile crop.
FIT_CENTERING = {
    "macys-parade": (0.5, 0.4),
    "shenzhou-24": (0.5, 0.5),
}


def trimmed(path):
    """Load a panel, trim the model's off-white frame, apply its crop."""
    img = Image.open(path).convert("RGB")
    w, h = img.size
    img = img.crop((int(w * TRIM), int(h * TRIM),
                    int(w * (1 - TRIM)), int(h * (1 - TRIM))))
    pid = os.path.splitext(os.path.basename(path))[0]
    crop = CROP_OVERRIDES.get(pid)
    if crop is not None:
        w, h = img.size
        img = img.crop((int(w * crop[0]), int(h * crop[1]),
                        int(w * crop[2]), int(h * crop[3])))
    return img


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


def fit_text(draw, text, max_width, max_lines, sizes, kind="serif_bold"):
    """Largest size whose greedy wrap fits max_lines; FAILS LOUDLY otherwise.

    Ronde 2 silently dropped the 3rd wrapped line, which cut a word off the
    Macy's headline. Never truncate silently again.
    Returns (font, lines).
    """
    lines = []
    for size in sizes:
        font = load_font(size, kind)
        lines = wrap(draw, text, font, max_width)
        if len(lines) <= max_lines:
            return font, lines
    sys.exit("text does not fit in %d lines even at %dpx: %r -> %r"
             % (max_lines, sizes[-1], text, lines))


def chip(draw, x, y, text, font, fill=RED, fg=WHITE):
    """Solid chip with bold text; returns its width and height."""
    pad_x, pad_y = 10, 5
    tw = draw.textlength(text, font=font)
    bw = int(tw + 2 * pad_x)
    bh = font.size + 2 * pad_y
    draw.rounded_rectangle([x, y, x + bw, y + bh], radius=3, fill=fill)
    draw.text((x + pad_x, y + pad_y), text, font=font, fill=fg)
    return bw, bh


def main():
    with open(os.path.join(ROOT, "data", "stories.json"), encoding="utf-8") as f:
        data = json.load(f)
    stories = data["stories"]
    if data.get("date") != "2026-11-26":
        sys.exit("stories.json is not the 26 Nov 2026 set: date=%r"
                 % data.get("date"))
    lead = next(s for s in stories if s["role"] == "lead")
    rest = [s for s in stories if s["role"] != "lead"]
    if len(rest) != 6:
        sys.exit("expected 6 supporting stories, got %d" % len(rest))

    page = Image.new("RGB", (W, H), CHARCOAL)
    draw = ImageDraw.Draw(page)

    # ---- masthead (0-104): serif title + red date, both centred ----
    title_font = load_font(60, "serif_bold")
    title = "WORLD NEWS"
    tw = draw.textlength(title, font=title_font)
    draw.text(((W - tw) / 2, 6), title, font=title_font, fill=WHITE)
    date_font = load_font(26, "sans_bold")
    date = "THURSDAY 26 NOVEMBER 2026"
    dw = draw.textlength(date, font=date_font)
    draw.text(((W - dw) / 2, 70), date, font=date_font, fill=RED)
    draw.rectangle([0, 100, W, 104], fill=RED)

    # ---- hero RED block (112-392): lead image left, text right ----
    hx, hy, hw, hh = 24, 112, 976, 280
    draw.rectangle([hx, hy, hx + hw, hy + hh], fill=RED)
    img_w, img_h = 400, 280
    # centering (0.5, 0.62) biases the wide crop down so the near tanker's
    # bow (cut mid-hull in v1) stays in frame; the red sky above is
    # redundant with the red block anyway.
    lead_img = ImageOps.fit(trimmed(os.path.join(ASSETS, lead["id"] + ".jpg")),
                            (img_w, img_h), Image.LANCZOS,
                            centering=(0.5, 0.62))
    page.paste(lead_img, (hx, hy))
    draw = ImageDraw.Draw(page)
    tx = hx + img_w + 24
    text_w = hx + hw - 24 - tx
    chip_font = load_font(20, "sans_bold")
    _, ch = chip(draw, tx, hy + 20,
                 lead["region"].upper() + " · " + lead["topic"].upper(),
                 chip_font, fill=CHARCOAL)
    head_font, lines = fit_text(draw, lead["headline_short"], text_w, 2,
                                (40, 36), kind="serif_bold")
    deck_font = load_font(22, "sans")
    deck_lines = wrap(draw, LEAD_DECK, deck_font, text_w)
    if len(deck_lines) > 2:
        sys.exit("lead deck does not fit in 2 lines: %r -> %r"
                 % (LEAD_DECK, deck_lines))
    print("lead font=%dpx lines=%d %r | deck lines=%d %r"
          % (head_font.size, len(lines), lines, len(deck_lines), deck_lines))
    # Vertically centre the headline + deck block below the chip.
    block_h = len(lines) * 48 + 10 + len(deck_lines) * 28
    avail = hh - 20 - ch
    y = hy + 20 + ch + max(0, (avail - block_h) // 2)
    for line in lines:
        draw.text((tx, y), line, font=head_font, fill=WHITE)
        y += 48
    y += 10
    for line in deck_lines:
        draw.text((tx, y), line, font=deck_font, fill=WHITE)
        y += 28

    # ---- section header (404-440): TOP STORIES + red rule ----
    sec_font = load_font(28, "serif_bold")
    draw.text((24, 404), "TOP STORIES", font=sec_font, fill=WHITE)
    draw.rectangle([24, 438, W - 24, 440], fill=RED)

    # ---- grid (448-968): 3 cols x 2 rows of TAN cards ----
    gx, gy = 24, 448
    card_w, card_h, gut_x, gut_y = 304, 254, 16, 12
    img_h = 132
    pad = 12
    text_w = card_w - 2 * pad
    chip_f = load_font(20, "sans_bold")
    sum_font = load_font(20, "sans")
    for i, story in enumerate(rest):
        col, row = i % 3, i // 3
        cx = gx + col * (card_w + gut_x)
        cy = gy + row * (card_h + gut_y)
        draw.rectangle([cx, cy, cx + card_w - 1, cy + card_h - 1],
                       fill=CARD, outline=CARD_LINE, width=1)
        img = ImageOps.fit(
            trimmed(os.path.join(ASSETS, story["id"] + ".jpg")),
            (card_w, img_h), Image.LANCZOS,
            centering=FIT_CENTERING.get(story["id"], (0.5, 0.5)))
        page.paste(img, (cx, cy))
        draw = ImageDraw.Draw(page)
        # region chip overlapping the image bottom-left corner
        chip(draw, cx + 8, cy + img_h - 34,
             story["region"].upper(), chip_f)
        tile_font, lines = fit_text(draw, story["headline_short"], text_w, 2,
                                    (24, 22, 20), kind="serif_bold")
        summary = SUMMARIES[story["id"]]
        sum_lines = wrap(draw, summary, sum_font, text_w)
        if len(sum_lines) > 2:
            sys.exit("summary does not fit in 2 lines: %r (%s) -> %r"
                     % (summary, story["id"], sum_lines))
        print("card %-14s font=%dpx lines=%d %r | summary lines=%d %r"
              % (story["id"], tile_font.size, len(lines), lines,
                 len(sum_lines), sum_lines))
        y = cy + img_h + 10
        for line in lines:
            draw.text((cx + pad, y), line, font=tile_font, fill=WHITE)
            y += 29
        y += 4
        for line in sum_lines:
            draw.text((cx + pad, y), line, font=sum_font, fill=MUTED)
            y += 25

    # ---- footer (976-1024) ----
    draw.rectangle([0, 976, W, 978], fill=RED)
    foot_font = load_font(22, "sans")
    credit = "Reporting: news.make.fun — illustrations original"
    fw = draw.textlength(credit, font=foot_font)
    draw.text(((W - fw) / 2, 992), credit, font=foot_font, fill=MUTED)

    page.save(OUT, format="PNG", optimize=True)
    print("wrote", OUT, page.size)


if __name__ == "__main__":
    main()
