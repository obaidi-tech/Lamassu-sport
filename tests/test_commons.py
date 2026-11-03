"""Commons images: free licence accepted + credited + cached; non-free rejected; offline failure is harmless."""
import io
import os
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from PIL import Image  # noqa: E402

import newsroom.commons as cm  # noqa: E402
from newsroom.posts import load_posts  # noqa: E402

FAKE = {
    "File:Free photo.jpg": {"license": "CC BY-SA 4.0", "artist": "<a href='x'>Jane Doe</a>"},
    "File:Rights reserved.jpg": {"license": "All rights reserved", "artist": "Someone"},
}
calls = []


def fake_fetch(title, width=1600):
    calls.append(title)
    if title not in FAKE:
        raise LookupError("offline")
    f = FAKE[title]
    return {"title": title, "thumb": "https://upload.wikimedia.org/x/1200px-photo.jpg", "page": "https://commons.wikimedia.org/wiki/" + title,
            "mime": "image/jpeg", "artist": cm._strip(f["artist"]), "license": f["license"],
            "license_url": "https://creativecommons.org/licenses/by-sa/4.0", "restrictions": ""}


def fake_download(url):
    b = io.BytesIO(); Image.new("RGB", (40, 20), (20, 80, 160)).save(b, "JPEG"); return b.getvalue()


def post(d, name, commons):
    open(os.path.join(d, name), "w", encoding="utf-8").write(
        f"---\ntitle: خبر {name}\ncategory: top5\ncommons: {commons}\n---\n\nنص الخبر.\n")


def main():
    d = tempfile.mkdtemp()
    post(d, "a.md", "https://commons.wikimedia.org/wiki/File:Free_photo.jpg")
    post(d, "b.md", "File:Rights_reserved.jpg")
    post(d, "c.md", "File:Unreachable.jpg")
    real = cm.CommonsCache.resolve
    cm.CommonsCache.resolve = lambda self, raw, log=print, fetch=None, download=None: real(self, raw, log, fake_fetch, fake_download)
    logs = []
    posts = {p["file"]: p for p in load_posts(d, "Asia/Riyadh", "Lamassu", log=logs.append)}
    n_calls = len(calls)
    again = {p["file"]: p for p in load_posts(d, "Asia/Riyadh", "Lamassu", log=logs.append)}
    checks = {
        "free image used": bool(posts["a.md"]["cover_src"]) and os.path.exists(posts["a.md"]["cover_src"]),
        "credit has artist (HTML stripped)": posts["a.md"]["credit"]["artist"] == "Jane Doe",
        "credit has licence": posts["a.md"]["credit"]["license"] == "CC BY-SA 4.0",
        "non-free image rejected": posts["b.md"]["cover_src"] is None,
        "offline: published without image": posts["c.md"]["cover_src"] is None and posts["c.md"]["title"],
        "cached: free image not fetched again": "File:Free photo.jpg" not in calls[n_calls:] and again["a.md"]["credit"]["artist"] == "Jane Doe",
        "cache file written": os.path.exists(os.path.join(d, "images", "commons.json")),
    }
    for k, v in checks.items():
        print(("PASS" if v else "FAIL"), k)
    shutil.rmtree(d)
    sys.exit(0 if all(checks.values()) else 1)


def test_unsplash():
    d = tempfile.mkdtemp()
    open(os.path.join(d, "u.md"), "w", encoding="utf-8").write(
        "---\ntitle: خبر\ncategory: orgs\nunsplash: https://unsplash.com/photos/a-stadium-6T3liG3AqSs\nphotographer: Yucel M\n---\n\nنص.\n")
    real = cm.RemoteImages.resolve_unsplash
    big = lambda url: (lambda b: (Image.new("RGB", (3000, 2000), (9, 9, 9)).save(b, "JPEG"), b.getvalue())[1])(io.BytesIO())  # noqa: E731
    cm.RemoteImages.resolve_unsplash = lambda self, link, ph, log=print, download=None: real(self, link, ph, log, big)
    p = load_posts(d, "Asia/Riyadh", "Lamassu", log=lambda *a: None)[0]
    ok = {
        "unsplash image saved and resized to 1400": bool(p["cover_src"]) and Image.open(p["cover_src"]).width == 1400,
        "unsplash credit: photographer + licence + source": p["credit"]["artist"] == "Yucel M" and p["credit"]["license"] == "Unsplash License" and p["credit"]["source"] == "Unsplash",
    }
    for k, v in ok.items():
        print(("PASS" if v else "FAIL"), k)
    shutil.rmtree(d)
    return all(ok.values())


if __name__ == "__main__":
    u = test_unsplash()
    try:
        main()
    except SystemExit as e:
        sys.exit(e.code or (0 if u else 1))
