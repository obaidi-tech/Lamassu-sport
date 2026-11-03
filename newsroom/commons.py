"""Free-licence images from Wikimedia Commons, with automatic photographer credit.

In a post's header:   commons: File:Some_photo.jpg   (or the full commons.wikimedia.org/wiki/File:... link)

On the first build that can reach the internet (GitHub Actions), the image's licence and author are
read from the official Commons API. Only free licences are accepted. The picture is saved into
content/posts/images/commons/ and the credit into content/posts/images/commons.json, so later builds
work offline and never depend on Wikimedia's servers.
"""
import hashlib
import html
import json
import os
import re
from urllib.parse import unquote

import requests

API = "https://commons.wikimedia.org/w/api.php"
UA = "LamassuSiteBuilder/1.0 (+https://github.com/obaidi-tech/lamassu-sport)"
FREE = re.compile(r"^(cc0|cc[ -]by(-sa)?([ -]\d(\.\d)?)?|public domain|pd\b|pd-|attribution|gfdl|fal\b|free art)", re.I)


def normalize_title(raw: str) -> str:
    t = unquote(str(raw).strip())
    t = re.sub(r"^https?://[^/]*wikimedia\.org/wiki/", "", t)
    t = t.split("?")[0].split("#")[0].replace("_", " ").strip()
    if not re.match(r"^(file|ملف):", t, re.I):
        t = "File:" + t
    return re.sub(r"^(file|ملف):", "File:", t, flags=re.I)


def _strip(s: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", s or ""))).strip()


def fetch_info(title: str, width: int = 1600) -> dict:
    r = requests.get(API, timeout=30, headers={"User-Agent": UA}, params={
        "action": "query", "format": "json", "titles": title, "prop": "imageinfo",
        "iiprop": "url|extmetadata|mime", "iiurlwidth": width})
    r.raise_for_status()
    page = next(iter(r.json().get("query", {}).get("pages", {}).values()), {})
    info = (page.get("imageinfo") or [None])[0]
    if not info:
        raise LookupError("not found on Commons")
    meta = info.get("extmetadata", {})
    val = lambda k: (meta.get(k) or {}).get("value", "")  # noqa: E731
    return {
        "title": title,
        "thumb": info.get("thumburl") or info["url"],
        "page": info.get("descriptionurl", ""),
        "mime": info.get("mime", ""),
        "artist": _strip(val("Artist")) or _strip(val("Credit")) or "Wikimedia Commons",
        "license": _strip(val("LicenseShortName")),
        "license_url": _strip(val("LicenseUrl")),
        "restrictions": _strip(val("Restrictions")),
    }


class CommonsCache:
    def __init__(self, posts_dir: str):
        self.dir = os.path.join(posts_dir, "images", "commons")
        self.path = os.path.join(posts_dir, "images", "commons.json")
        self.data = {}
        if os.path.exists(self.path):
            with open(self.path, encoding="utf-8") as f:
                self.data = json.load(f)
        self.dirty = False

    def resolve(self, raw: str, log=print, fetch=fetch_info, download=None):
        """Return (local_image_path, credit_dict) or (None, None). Never raises."""
        title = normalize_title(raw)
        rec = self.data.get(title)
        if rec and rec.get("local") and os.path.exists(os.path.join(self.dir, rec["local"])):
            return os.path.join(self.dir, rec["local"]), rec
        try:
            info = fetch(title)
        except Exception as ex:
            log(f"  ⚠ صورة {title}: تعذر الوصول إلى Wikimedia ({type(ex).__name__}). نُشر الخبر دون صورة، وتُعاد المحاولة في التشغيل التالي.")
            return None, None
        if not FREE.match(info.get("license", "")):
            log(f"  ⚠ صورة {title}: رخصتها «{info.get('license') or 'غير معروفة'}» ليست حرة، فلم تُستخدم.")
            return None, None
        if not info.get("mime", "image/jpeg").startswith("image/"):
            log(f"  ⚠ صورة {title}: الملف ليس صورة، فلم يُستخدم.")
            return None, None
        ext = os.path.splitext(info["thumb"].split("?")[0])[1].lower() or ".jpg"
        if ext not in (".jpg", ".jpeg", ".png", ".webp"):
            ext = ".jpg"
        local = hashlib.sha1(title.encode()).hexdigest()[:12] + ext
        try:
            os.makedirs(self.dir, exist_ok=True)
            data = (download or _download)(info["thumb"])
            with open(os.path.join(self.dir, local), "wb") as f:
                f.write(data)
        except Exception as ex:
            log(f"  ⚠ صورة {title}: تعذر تنزيلها ({type(ex).__name__}).")
            return None, None
        rec = {k: info[k] for k in ("title", "page", "artist", "license", "license_url")}
        rec["local"] = local
        self.data[title] = rec
        self.dirty = True
        log(f"  ✔ صورة {title}: {rec['artist']} — {rec['license']}")
        return os.path.join(self.dir, local), rec

    def save(self):
        if self.dirty:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=1)


def _download(url: str) -> bytes:
    r = requests.get(url, timeout=60, headers={"User-Agent": UA})
    r.raise_for_status()
    if len(r.content) > 8 * 1024 * 1024:
        raise ValueError("image too large")
    return r.content


# ── Unsplash (free photos under the Unsplash License) ──────────────────────────
UNSPLASH_LICENSE = "https://unsplash.com/license"


def unsplash_download_url(page_or_image: str) -> str:
    """Accept a photo page (unsplash.com/photos/<slug>-<id>) or a direct images.unsplash.com link."""
    u = page_or_image.strip()
    if "images.unsplash.com/" in u:
        base = u.split("?")[0]
        return base + "?fm=jpg&q=80&w=1600&fit=max"
    m = re.search(r"unsplash\.com/photos/(?:[^/?#]*-)?([A-Za-z0-9_-]{11})(?:[/?#]|$)", u)
    if not m:
        raise ValueError("not an Unsplash photo link")
    return f"https://unsplash.com/photos/{m.group(1)}/download?force=true"


class RemoteImages:
    """Downloads a free photo once (on GitHub, where the internet is open), keeps a local copy and its credit."""
    def __init__(self, posts_dir: str):
        self.dir = os.path.join(posts_dir, "images", "remote")
        self.path = os.path.join(posts_dir, "images", "remote.json")
        self.data = json.load(open(self.path, encoding="utf-8")) if os.path.exists(self.path) else {}
        self.dirty = False

    def resolve_unsplash(self, link: str, photographer: str, log=print, download=None):
        key = link.strip()
        rec = self.data.get(key)
        credit = {"artist": photographer or "Unsplash", "license": "Unsplash License",
                  "license_url": UNSPLASH_LICENSE, "page": key if key.startswith("https://unsplash.com/") else "",
                  "source": "Unsplash"}
        if rec and os.path.exists(os.path.join(self.dir, rec["local"])):
            return os.path.join(self.dir, rec["local"]), dict(credit, **{k: rec[k] for k in ("artist",) if rec.get(k)})
        try:
            url = unsplash_download_url(key)
            raw = (download or _download_big)(url)
            from io import BytesIO
            from PIL import Image
            im = Image.open(BytesIO(raw)).convert("RGB")
            if im.width > 1600:
                im = im.resize((1600, round(im.height * 1600 / im.width)), Image.LANCZOS)
            os.makedirs(self.dir, exist_ok=True)
            local = hashlib.sha1(key.encode()).hexdigest()[:12] + ".jpg"
            im.save(os.path.join(self.dir, local), "JPEG", quality=84, optimize=True, progressive=True)
        except Exception as ex:
            log(f"  ⚠ صورة Unsplash {key}: تعذر تنزيلها ({type(ex).__name__}). نُشر الخبر دون صورة، وتُعاد المحاولة في التشغيل التالي.")
            return None, None
        self.data[key] = {"local": local, "artist": credit["artist"]}
        self.dirty = True
        log(f"  ✔ صورة Unsplash: {credit['artist']}")
        return os.path.join(self.dir, local), credit

    def save(self):
        if self.dirty:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=1)


def _download_big(url: str) -> bytes:
    r = requests.get(url, timeout=90, headers={"User-Agent": UA}, allow_redirects=True)
    r.raise_for_status()
    if not r.headers.get("content-type", "").startswith("image/"):
        raise ValueError("not an image")
    if len(r.content) > 30 * 1024 * 1024:
        raise ValueError("image too large")
    return r.content
