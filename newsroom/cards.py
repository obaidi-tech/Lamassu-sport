"""Generate a 1200×630 article image (headline card) for every story. No photos, so no licensing risk."""
import os

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = os.path.join(ROOT, "assets", "fonts")

INK = (20, 33, 61)
PAPER = (244, 246, 245)
AMBER = (242, 169, 0)
CAT_COLORS = {
    "top5": (31, 122, 77), "orgs": (47, 90, 168), "nba": (200, 85, 61),
    "other_sports": (122, 79, 160), "world": (15, 139, 141), "opinion": (140, 109, 31),
    "awareness": (162, 59, 114), "flex": (31, 122, 77), "para": (0, 122, 153), "culture": (139, 90, 43),
}
W, H = 1200, 630


def news_label(n: int) -> str:
    """Arabic number agreement for 'news items'."""
    if n == 1:
        return "خبر واحد"
    if n == 2:
        return "خبران"
    if 3 <= n <= 10:
        return f"{n} أخبار"
    return f"{n} خبراً"


def covered_label(n: int) -> str:
    """'Covered by N independent outlets' with Arabic number agreement."""
    if n == 1:
        return "غطّته جهة واحدة"
    if n == 2:
        return "غطّته جهتان"
    if 3 <= n <= 10:
        return f"غطّته {n} جهات"
    return f"غطّته {n} جهة"


def sources_label(n: int) -> str:
    """Arabic number agreement for 'sources'."""
    if n == 1:
        return "مصدر واحد"
    if n == 2:
        return "مصدران"
    if 3 <= n <= 10:
        return f"{n} مصادر"
    return f"{n} مصدراً"


def _font(weight: str, size: int):
    name = {"heavy": "Cairo_800ExtraBold.ttf", "semi": "Cairo_600SemiBold.ttf", "regular": "Cairo_400Regular.ttf",
            "naskh": "NotoNaskhArabic_400Regular.ttf", "naskh-bold": "NotoNaskhArabic_700Bold.ttf"}[weight]
    return ImageFont.truetype(os.path.join(FONTS, name), size, layout_engine=ImageFont.Layout.RAQM)


def _len(font, text):
    return font.getlength(text, direction="rtl", language="ar")


def _wrap(text: str, font, max_w: int) -> list:
    lines, cur = [], ""
    for w in text.split():
        trial = f"{cur} {w}".strip()
        if _len(font, trial) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def _fit_headline(text: str, max_w: int, max_lines: int = 3):
    for size in (72, 66, 60, 54, 48, 44):
        f = _font("heavy", size)
        lines = _wrap(text, f, max_w)
        if len(lines) <= max_lines:
            return f, lines, size
    f = _font("heavy", 44)
    lines = _wrap(text, f, max_w)[:max_lines]
    lines[-1] = lines[-1] + " …"
    return f, lines, 44


def _rtl(draw, right_x, y, text, font, fill):
    draw.text((right_x - _len(font, text), y), text, font=font, fill=fill, direction="rtl", language="ar")


def make_card(path: str, title: str, category: str, cat_name: str, site_name: str,
              date_label: str, n_sources: int):
    accent = CAT_COLORS.get(category, CAT_COLORS["top5"])
    img = Image.new("RGB", (W, H), INK)
    d = ImageDraw.Draw(img)

    # faint arcs: a quiet nod to a stadium bowl, drawn in the accent colour
    for i, r in enumerate(range(260, 900, 90)):
        d.arc((-r // 2 - 200, H - r // 2, r * 1.2 - 200, H + r), 200, 340,
              fill=tuple(int(a * 0.22 + b * 0.78) for a, b in zip(accent, INK)), width=3)

    d.rectangle((W - 18, 0, W, H), fill=accent)                    # category stripe on the reading edge
    pad_r, pad_l = W - 80, 80

    tag_font = _font("semi", 30)
    tw = _len(tag_font, cat_name)
    d.rounded_rectangle((pad_r - tw - 36, 64, pad_r, 114), radius=25, fill=accent)
    _rtl(d, pad_r - 18, 61, cat_name, tag_font, (255, 255, 255))

    f, lines, size = _fit_headline(title, pad_r - pad_l)
    lh = int(size * 1.45)
    y = 150 + max(0, (3 - len(lines)) * lh // 2)
    for line in lines:
        _rtl(d, pad_r, y, line, f, PAPER)
        y += lh

    # footer: wordmark (right), date + coverage meter (left)
    d.line((pad_l, H - 110, pad_r, H - 110), fill=(52, 66, 96), width=2)
    _rtl(d, pad_r, H - 92, site_name, _font("heavy", 40), PAPER)
    small = _font("regular", 26)
    meter_x = pad_l
    bars = 0 if category == "opinion" or n_sources == 0 else min(n_sources, 8)
    for i in range(bars):
        d.rectangle((meter_x + i * 14, H - 62, meter_x + i * 14 + 8, H - 40), fill=AMBER)
    label = sources_label(n_sources)
    if category == "opinion":
        label = "مقال رأي"
    elif n_sources == 0:
        label = ""
    d.text((meter_x + bars * 14 + (14 if bars else 0), H - 72), label, font=small, fill=(200, 208, 220),
           direction="rtl", language="ar")
    d.text((pad_l + 260, H - 72), date_label, font=small, fill=(150, 160, 180), direction="rtl", language="ar")

    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path, "JPEG", quality=85, optimize=True, progressive=True)
    return path


# the Lamassu wing (same four feathers as site_assets/brand/lamassu-mark.svg, in its 64-unit box)
FEATHERS = [
    [(52, 13), (52, 19), (22, 19), ("Q", (13, 19), (10, 11)), ("Q", (20, 13), (52, 13))],
    [(52, 24), (52, 30), (20, 30), ("Q", (12, 30), (9, 23)), ("Q", (18, 24), (52, 24))],
    [(52, 35), (52, 41), (24, 41), ("Q", (16, 41), (14, 35)), ("Q", (22, 35), (52, 35))],
    [(52, 46), (52, 52), (31, 52), ("Q", (24, 52), (22, 46)), ("Q", (29, 46), (52, 46))],
]


def _feather_points(path, x0, y0, scale):
    out, cur = [], None
    for p in path:
        if p[0] == "Q":
            (cx, cy), (ex, ey) = p[1], p[2]
            for i in range(1, 13):
                t = i / 12
                out.append(((1 - t) ** 2 * cur[0] + 2 * (1 - t) * t * cx + t * t * ex,
                            (1 - t) ** 2 * cur[1] + 2 * (1 - t) * t * cy + t * t * ey))
            cur = (ex, ey)
        else:
            out.append(p)
            cur = p
    return [(x0 + (x - 9) * scale, y0 + (y - 11) * scale) for x, y in out]


def _draw_wing(draw, right_x, top_y, scale=4.0):
    """The wing mark, its right edge at right_x."""
    x0 = right_x - (52 - 9) * scale
    for f in FEATHERS:
        draw.polygon(_feather_points(f, x0, top_y, scale), fill=AMBER)


def make_brand_card(path: str, name: str, tagline: str, tagline_en: str = ""):
    """The site's own share image (home page and any page without its own picture)."""
    img = Image.new("RGB", (W, H), INK)
    d = ImageDraw.Draw(img)
    for r in range(180, 1500, 110):                       # stadium-bowl arcs, centred low on the reading edge
        d.ellipse((W - r - 120, H - r // 2 + 40, W + r - 120, H + r * 1.5 + 40),
                  outline=tuple(int(a * 0.18 + b * 0.82) for a, b in zip(AMBER, INK)), width=3)
    d.rectangle((W - 18, 0, W, H), fill=AMBER)
    pad_r = W - 90
    big = ImageFont.truetype(os.path.join(FONTS, "Cairo_800ExtraBold.ttf"), 150)
    nw = big.getlength(name)
    d.text((pad_r - nw, 150), name, font=big, fill=PAPER)
    wing_png = os.path.join(ROOT, "site_assets", "brand", "lamassu-wing.png")
    if os.path.exists(wing_png):                           # the owner's wing (6 Nov 2026), left of the name
        wing = Image.open(wing_png).convert("RGBA").resize((176, 176), Image.LANCZOS)
        img.paste(wing, (int(pad_r - nw - 34 - 176), 170), wing)
    else:
        _draw_wing(d, pad_r - nw - 34, 205)
    y_rule = 360
    d.rectangle((pad_r - nw, y_rule, pad_r, y_rule + 4), fill=AMBER)
    _rtl(d, pad_r, y_rule + 30, tagline, _font("semi", 52), AMBER)
    if tagline_en:
        f = ImageFont.truetype(os.path.join(FONTS, "Cairo_600SemiBold.ttf"), 34)
        d.text((pad_r - f.getlength(tagline_en), y_rule + 120), tagline_en, font=f, fill=(184, 194, 211))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path, "JPEG", quality=88, optimize=True, progressive=True)
    return path


# ── Instagram card (1080×1350, portrait 4:5) ────────────────────────────
# Text only, in the site's colours: no agency or Getty photos, which may not be re-posted outside the site.
IG_W, IG_H = 1080, 1350


def _fit(text: str, weight: str, sizes, max_w: int, max_lines: int):
    for size in sizes:
        f = _font(weight, size)
        lines = _wrap(text, f, max_w)
        if len(lines) <= max_lines:
            return f, lines, size
    size = sizes[-1]
    f = _font(weight, size)
    lines = _wrap(text, f, max_w)[:max_lines]
    lines[-1] = lines[-1].rstrip("،.") + " …"
    return f, lines, size


def make_social_card(path: str, title: str, excerpt: str, category: str, cat_name: str,
                     site_name: str, date_label: str, label: str = "", footer: str = ""):
    accent = CAT_COLORS.get(category, CAT_COLORS["top5"])
    img = Image.new("RGB", (IG_W, IG_H), INK)
    d = ImageDraw.Draw(img)
    for r in range(300, 1700, 120):                       # stadium-bowl arcs, low on the far edge
        d.ellipse((-r + 140, IG_H - r // 2, r + 140, IG_H + r * 1.4),
                  outline=tuple(int(a * 0.16 + b * 0.84) for a, b in zip(accent, INK)), width=3)
    d.rectangle((IG_W - 20, 0, IG_W, IG_H), fill=accent)   # category stripe on the reading edge
    pad_r, pad_l = IG_W - 90, 90
    width = pad_r - pad_l

    # masthead: wing + name (right), date (left)
    name_f = _font("heavy", 46)
    nw = _len(name_f, site_name)
    _rtl(d, pad_r, 62, site_name, name_f, PAPER)
    wing_png = os.path.join(ROOT, "site_assets", "brand", "lamassu-wing.png")
    if os.path.exists(wing_png):
        wing = Image.open(wing_png).convert("RGBA").resize((64, 64), Image.LANCZOS)
        img.paste(wing, (int(pad_r - nw - 18 - 64), 70), wing)
    else:
        _draw_wing(d, pad_r - nw - 18, 78, scale=1.5)
    if date_label:
        small = _font("semi", 28)
        d.text((pad_l, 78), date_label, font=small, fill=(150, 160, 180), direction="rtl", language="ar")
    d.line((pad_l, 150, pad_r, 150), fill=(52, 66, 96), width=2)

    # category pill (+ a label such as «تقارير غير مؤكدة رسمياً»)
    y = 190
    tag_font = _font("semi", 32)
    tw = _len(tag_font, cat_name)
    d.rounded_rectangle((pad_r - tw - 40, y, pad_r, y + 56), radius=28, fill=accent)
    _rtl(d, pad_r - 20, y - 3, cat_name, tag_font, (255, 255, 255))
    if label:
        lw = _len(tag_font, label)
        x_r = pad_r - tw - 40 - 18
        d.rounded_rectangle((x_r - lw - 40, y, x_r, y + 56), radius=28, outline=AMBER, width=3)
        _rtl(d, x_r - 20, y - 3, label, tag_font, AMBER)

    # headline + amber rule + summary, as one block placed a little above the middle of the free space
    if label and title.startswith(label):                 # «من المختبر: …» already shows as the label
        title = title[len(label):].lstrip(" :：،")
    top, bottom = 290, IG_H - 190
    f, lines, size = _fit(title, "heavy", (84, 78, 72, 66, 60, 56, 52), width, 6)
    lh = int(size * 1.42)
    head_h = lh * len(lines)
    elines, ef, elh = [], None, 0
    if excerpt:
        ef, elines, esize = _fit(excerpt, "naskh", (42, 40, 38, 36), width, 6)
        elh = int(esize * 1.7)
        room = bottom - top - head_h - 82
        keep = max(0, room // elh)
        if keep < len(elines):
            elines = elines[:keep]
            if elines:
                elines[-1] = elines[-1].rstrip("،.") + " …"
    block = head_h + (82 + elh * len(elines) if elines else 0)
    y = top + max(0, (bottom - top - block) // 3)
    for line in lines:
        _rtl(d, pad_r, y, line, f, PAPER)
        y += lh
    if elines:
        y += 26
        d.rectangle((pad_r - 140, y, pad_r, y + 6), fill=AMBER)
        y += 56
        for line in elines:
            _rtl(d, pad_r, y, line, ef, (206, 213, 225))
            y += elh

    # footer
    d.line((pad_l, IG_H - 150, pad_r, IG_H - 150), fill=(52, 66, 96), width=2)
    _rtl(d, pad_r, IG_H - 122, footer or "التفاصيل والمصادر: الرابط في الملف الشخصي", _font("semi", 34), AMBER)

    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path, "JPEG", quality=90, optimize=True, progressive=True)
    return path
