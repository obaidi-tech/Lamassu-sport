"""Hand-written articles by the site's own writers: content/posts/*.md, published in full under the author's name.

File format (edit it straight in GitHub's web editor):

    ---
    title: عنوان المقال
    author: اسم الكاتب
    date: 2026-11-03 12:00        (optional; defaults to when the file was first published)
    category: opinion             (optional; any category key from config/categories.yaml)
    excerpt: سطر يلخص المقال      (optional; defaults to the opening of the first paragraph)
    draft: true                   (optional; keeps the article off the site)
    ---

    فقرة أولى…

    ## عنوان فرعي (اختياري)

    فقرة ثانية…
"""
import glob
import hashlib
import os
import re
from datetime import datetime
from zoneinfo import ZoneInfo

import yaml

FRONT = re.compile(r"^﻿?---\s*\n(.*?)\n---\s*\n(.*)$", re.S)


def _blocks(text: str) -> list:
    """Paragraphs separated by blank lines; a line starting with '## ' becomes a subheading."""
    out = []
    for chunk in re.split(r"\n\s*\n", text.strip()):
        chunk = " ".join(line.strip() for line in chunk.splitlines() if line.strip())
        if chunk:
            out.append(chunk)
    return out


def load_posts(posts_dir: str, tz: str, site_name: str, log=print) -> list:
    zone = ZoneInfo(tz)
    out = []
    for path in sorted(glob.glob(os.path.join(posts_dir, "*.md"))):
        name = os.path.basename(path)
        if name.lower().startswith(("readme", "_")):
            continue
        with open(path, encoding="utf-8") as f:
            raw = f.read()
        m = FRONT.match(raw)
        if not m:
            log(f"  ⚠ {name}: لا يبدأ بسطر --- ومعلومات المقال، فلم يُنشر")
            continue
        try:
            meta = yaml.safe_load(m.group(1)) or {}
        except yaml.YAMLError as ex:
            log(f"  ⚠ {name}: خطأ في معلومات المقال ({ex.__class__.__name__})، فلم يُنشر")
            continue
        if meta.get("draft") or not meta.get("title"):
            if not meta.get("title"):
                log(f"  ⚠ {name}: لا يوجد عنوان (title)، فلم يُنشر")
            continue
        body = _blocks(m.group(2))
        if not body:
            log(f"  ⚠ {name}: المقال فارغ، فلم يُنشر")
            continue
        when = meta.get("date")
        if isinstance(when, str):
            when = datetime.fromisoformat(when.strip())
        elif not isinstance(when, datetime):
            when = (datetime.combine(when, datetime.min.time().replace(hour=9)) if when
                    else datetime.fromtimestamp(os.path.getmtime(path)))
        if when.tzinfo is None:
            when = when.replace(tzinfo=zone)
        first = next((b for b in body if not b.startswith("## ")), body[0])
        excerpt = str(meta.get("excerpt") or (first[:180].rsplit(" ", 1)[0] + "…" if len(first) > 180 else first))
        out.append({
            "id": "p" + hashlib.sha1(name.encode()).hexdigest()[:9],
            "title": str(meta["title"]).strip(),
            "excerpt": excerpt,
            "body": body,
            "tags": meta.get("tags") or [],
            "category": str(meta.get("category") or "opinion"),
            "sub": "own",
            "score": 0,
            "n_sources": 0,
            "sources": [],
            "author": str(meta.get("author") or site_name),
            "outlet": site_name,
            "original_title": None,
            "lang": "ar",
            "published_at": when.isoformat(),
            "own": True,
            "file": name,
        })
    return out
