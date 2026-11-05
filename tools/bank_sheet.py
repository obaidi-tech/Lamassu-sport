"""Contact sheet of the image bank, for the editor's visual check:  python tools/bank_sheet.py
Reads config/image_bank.yaml and the photos already downloaded into content/posts/images/commons/
(GitHub fetches them on its next build), and writes docs/image-bank.jpg with each photo, its id and size."""
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from newsroom.bank import load_bank          # noqa: E402
from newsroom.commons import normalize_title  # noqa: E402

bank = load_bank(os.path.join(ROOT, "config", "image_bank.yaml"))
cache = json.load(open(os.path.join(ROOT, "content", "posts", "images", "commons.json"), encoding="utf-8"))
W, H, COLS, PAD = 420, 236, 4, 10
rows = (len(bank) + COLS - 1) // COLS
sheet = Image.new("RGB", (COLS * (W + PAD) + PAD, rows * (H + 46 + PAD) + PAD), (20, 33, 61))
d = ImageDraw.Draw(sheet)
font = ImageFont.load_default()
missing = []
for i, e in enumerate(bank):
    x, y = PAD + (i % COLS) * (W + PAD), PAD + (i // COLS) * (H + 46 + PAD)
    raw = e["commons"]
    if raw.lower().startswith(("search:", "search-old:")):
        raw = cache.get("_search", {}).get(raw.split(":", 1)[1].strip(), "")
    rec = cache.get(normalize_title(raw)) if raw else None
    path = os.path.join(ROOT, "content", "posts", "images", "commons", rec["local"]) if rec and rec.get("local") else ""
    if path and os.path.exists(path):
        im = Image.open(path).convert("RGB")
        w0, h0 = im.size
        im.thumbnail((W, H))
        sheet.paste(im, (x + (W - im.width) // 2, y + (H - im.height) // 2))
        info = f"{w0}x{h0}  ({w0 / h0:.2f})  {rec.get('license', '')}"
        title = normalize_title(raw)[5:60]
    else:
        missing.append(e["id"])
        d.rectangle((x, y, x + W, y + H), outline=(200, 80, 80), width=2)
        info, title = "not downloaded yet", e["commons"][:60]
    d.text((x, y + H + 4), f"{i + 1}. {e['id']}  {info}", fill=(242, 169, 0), font=font)
    d.text((x, y + H + 22), title, fill=(220, 226, 235), font=font)
out = os.path.join(ROOT, "docs", "image-bank.jpg")
sheet.save(out, "JPEG", quality=80)
print(f"{len(bank) - len(missing)}/{len(bank)} photos → {out}" + (f"  (missing: {', '.join(missing)})" if missing else ""))
