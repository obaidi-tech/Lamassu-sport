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
    "awareness": (162, 59, 114), "flex": (31, 122, 77),
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
    name = {"heavy": "Cairo_800ExtraBold.ttf", "semi": "Cairo_600SemiBold.ttf", "regular": "Cairo_400Regular.ttf"}[weight]
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
