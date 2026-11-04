"""Hand-written articles by the site's own writers: content/posts/*.md, published in full under the author's name.

File format (edit it straight in GitHub's web editor):

    ---
    title: عنوان المقال
    author: اسم الكاتب
    date: 2026-11-03 12:00        (optional; defaults to when the file was first published)
    category: opinion             (optional; any category key from config/categories.yaml)
    excerpt: سطر يلخص المقال      (optional; defaults to the opening of the first paragraph)
    image: images/cover.jpg       (optional; a picture inside content/posts/, shown on the page and when shared)
    commons: File:Photo.jpg       (optional; a free-licence picture from Wikimedia Commons, credited automatically)
    unsplash: https://unsplash.com/photos/...   + photographer: Name   (optional; a free Unsplash photo)
    updated: 2026-11-03 18:40     (optional) when the story was last changed …
    update_note: سبب التحديث       … and why — shown at the end of the story
    sources:                      (optional, for news) one line per source: "الاسم | الرابط"
      - الاتحاد الآسيوي | https://www.the-afc.com/...
    featured: true                (optional, for news) put it in the lead spot on the home page
    draft: true                   (optional; keeps the article off the site)
    outlet: جريدة فوز              (optional, opinion only) the piece first appeared elsewhere: we publish
    original_url: https://...      our own summary under the writer's name, with a link to the original
    original_title: العنوان الأصلي
    contributor: true              (optional) a volunteer contribution («شارك معنا»), with:
    author_bio: سطر تعريفي          the writer's/photographer's one-line bio
    author_link: https://...       (optional) their public page
    roundup: true                  (optional, opinion only) a digest of pieces from other outlets ("أبرز ما كُتب"):
                                   by-line "إعداد: Lamassu", each original listed under "المقالات الأصلية".
    image_crop: 0 0 21.5 0         (optional) trim the cover: percent from top, right, bottom, left
                                   (e.g. to remove a watermark; allowed by CC BY / CC BY-SA, noted under the photo)
    label: تقرير مرجعي              (optional) a small tag shown with the title, e.g. أرشيف / تقرير مرجعي / ملف
    related:                       (optional) other posts on the same event, by file name; the link shows on both pages
      - 2026-11-04-best-reads-01.md
    Inside the text, [نص](https://...) becomes a link and **نص** becomes bold.
    A picture inside the text, on its own line:  ![التعليق](commons:File:اسم_الملف.jpg)
    (or ![التعليق](commons:search:كلمات البحث) to take the first matching free picture on Commons).
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

from .commons import CommonsCache, RemoteImages

FRONT = re.compile(r"^﻿?---\s*\n(.*?)\n---\s*\n(.*)$", re.S)


def _blocks(text: str) -> list:
    """Paragraphs separated by blank lines. '## ' / '### ' lines become subheadings;
    lines starting with '- ' become a bullet list (consecutive list lines merge into one list);
    lines starting with '|' become a table (first row = headings; a |---| row is ignored)."""
    out = []
    for chunk in re.split(r"\n\s*\n", text.strip()):
        lines = [line.strip() for line in chunk.splitlines() if line.strip()]
        if not lines:
            continue
        if all(l.startswith("|") for l in lines):           # a table: | col | col | rows
            out.append("\n".join(lines))
            continue
        if all(l.startswith("- ") for l in lines):
            if out and out[-1].startswith("- "):
                out[-1] += "\n" + "\n".join(lines)
            else:
                out.append("\n".join(lines))
        elif lines[0].startswith("#"):
            out.append(lines[0])
            if len(lines) > 1:
                out.append(" ".join(lines[1:]))
        else:
            out.append(" ".join(lines))
    return out


def _lenient_meta(text: str) -> dict:
    """Fallback when the header isn't strict YAML (e.g. a title with ':' or starting with quotes):
    'key: value' per line, the value is everything after the first ': '; '  - item' lines form a list."""
    meta, last = {}, None
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        stripped = line.strip()
        if stripped.startswith("- ") and last:
            if not isinstance(meta.get(last), list):
                meta[last] = []
            meta[last].append(stripped[2:].strip())
            continue
        key, sep, val = line.partition(":")
        if not sep or not re.fullmatch(r"[A-Za-z_]+", key.strip()):
            continue
        last, val = key.strip(), val.strip()
        if val.lower() in ("true", "false"):
            meta[last] = val.lower() == "true"
        elif val:
            meta[last] = val
    return meta


def _sources(raw) -> list:
    """Each source: "الاسم | الرابط" or "الاسم | الرابط | ملاحظة". With no link, a short reason is shown instead
    (the given note, or a default)."""
    out = []
    for item in raw or []:
        note = ""
        if isinstance(item, dict):
            name, link = item.get("name") or item.get("publisher"), item.get("link") or item.get("url")
            note = str(item.get("note") or "")
        else:
            name, _, rest = str(item).partition("|")
            link, _, note = rest.partition("|")
        name, link, note = (name or "").strip(), (link or "").strip(), note.strip()
        if not name:
            continue
        link = link if link.startswith("http") else ""
        if not link and not note:
            note = ("لم تُحدَّد الوكالة في المادة الأصلية" if re.search(r"وكالات|agencies", name, re.I)
                    else "لم نعثر على رابط المادة الأصلية")
        out.append({"publisher": name, "title": "", "link": link, "kind": "manual", "note": note})
    return out


def load_posts(posts_dir: str, tz: str, site_name: str, log=print, commons=None) -> list:
    zone = ZoneInfo(tz)
    out = []
    cache = commons or CommonsCache(posts_dir)
    remote = RemoteImages(posts_dir)
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
            if not isinstance(meta, dict):
                raise yaml.YAMLError("header is not a mapping")
        except yaml.YAMLError:
            meta = _lenient_meta(m.group(1))
        if meta.get("draft") or not meta.get("title"):
            if not meta.get("title"):
                log(f"  ⚠ {name}: لا يوجد عنوان (title)، فلم يُنشر")
            continue
        body = _blocks(m.group(2))
        figures = []
        for i, b in enumerate(body):                     # ![تعليق](commons:File:… ) or ![تعليق](commons:search:كلمات)
            fm = re.fullmatch(r"!\[([^\]]*)\]\(commons:([^)]+)\)", b.strip())
            if not fm:
                continue
            path, cr = cache.resolve(fm.group(2).strip(), log=log)
            if path:
                figures.append({"src": path, "credit": cr, "caption": fm.group(1).strip()})
                body[i] = f"!fig:{len(figures) - 1}"
            else:
                body[i] = ""
        body = [b for b in body if b]
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
        first = next((b for b in body if not b.startswith(("#", "- ", "|", "!fig:"))), body[0])
        cover = None
        if meta.get("image"):
            cover = os.path.normpath(os.path.join(posts_dir, str(meta["image"])))
            if not cover.startswith(os.path.normpath(posts_dir)) or not os.path.isfile(cover):
                log(f"  ⚠ {name}: الصورة {meta['image']} غير موجودة، فنُشر المقال دونها")
                cover = None
        credit = None
        if not cover and meta.get("unsplash"):
            cover, credit = remote.resolve_unsplash(str(meta["unsplash"]), str(meta.get("photographer") or ""), log=log,
                                                    image_url=str(meta.get("unsplash_image") or ""))
        if not cover and meta.get("commons"):
            cover, credit = cache.resolve(str(meta["commons"]), log=log)
        elif cover and meta.get("image_credit"):
            credit = {"artist": str(meta["image_credit"]), "license": "", "page": "", "license_url": ""}
        updates = []
        raw_upd = meta.get("updates") or []
        if meta.get("updated"):
            raw_upd = [f"{meta['updated']} | {meta.get('update_note') or 'تحديث'}"] + list(raw_upd)
        for u in raw_upd:
            d, _, note = str(u).partition("|")
            try:
                at = datetime.fromisoformat(d.strip())
            except ValueError:
                log(f"  ⚠ {name}: تاريخ تحديث غير مفهوم «{d.strip()}»، استخدم الصيغة 2026-11-03 18:40")
                continue
            if at.tzinfo is None:
                at = at.replace(tzinfo=zone)
            updates.append({"at": at.isoformat(), "note": note.strip() or "تحديث"})
        updates.sort(key=lambda u: u["at"], reverse=True)
        category = str(meta.get("category") or "opinion")
        srcs = _sources(meta.get("sources"))
        is_news = category != "opinion"
        # an opinion piece first published elsewhere: shown as our summary, under its writer's name, linked to the original
        outlet = str(meta.get("outlet") or "").strip()
        external = (not is_news) and bool(outlet) and outlet != site_name
        if external:
            link = str(meta.get("original_url") or "").strip()
            srcs = [{"publisher": outlet, "title": "", "link": link if link.startswith("http") else "", "kind": "manual"}]
        excerpt = str(meta.get("excerpt") or (first[:180].rsplit(" ", 1)[0] + "…" if len(first) > 180 else first))
        out.append({
            "id": "p" + hashlib.sha1(name.encode()).hexdigest()[:9],
            "title": str(meta["title"]).strip(),
            "excerpt": excerpt,
            "body": body,
            "tags": meta.get("tags") or [],
            "category": category,
            "sub": "own",
            "score": (20 if meta.get("featured") else 3 + 2 * len(srcs)) if is_news else 0,
            "n_sources": 0 if (external or meta.get("roundup")) else len(srcs),
            "sources": srcs,
            "author": str(meta.get("author") or ("" if is_news else site_name)),
            "outlet": outlet if external else site_name,
            "original_title": str(meta.get("original_title") or meta["title"]).strip() if external else None,
            "lang": "ar",
            "published_at": when.isoformat(),
            "own": not external,
            "file": name,
            "cover_src": cover,
            "credit": credit,
            "cover_alt": str(meta.get("image_alt") or ""),
            "updates": updates,
            "figures": figures,
            "label": str(meta.get("label") or "").strip(),
            "crop": [float(x) for x in str(meta.get("image_crop") or "").replace(",", " ").split()][:4],
            "related_files": [str(x).strip() for x in (meta.get("related") or []) if str(x).strip()]
                             if isinstance(meta.get("related"), list) else
                             [x.strip() for x in str(meta.get("related") or "").split(",") if x.strip()],
            "roundup": bool(meta.get("roundup")) and not is_news,
            "contributor": bool(meta.get("contributor")),
            "author_bio": str(meta.get("author_bio") or "").strip(),
            "author_link": (lambda u: u if u.startswith("https://") else "")(str(meta.get("author_link") or "").strip()),
            "updated_at": updates[0]["at"] if updates else None,
        })
    cache.save()
    remote.save()
    return out


def load_hero(posts_dir: str, entries, log=print) -> list:
    """Free photos for the moving banner on the home page (config/site.yaml → hero).
    Each entry: unsplash (photo page) + unsplash_image (direct link) + photographer, or commons: File:…; and alt.
    Downloaded once on GitHub and kept in content/posts/images/remote/, like story photos."""
    remote, commons = RemoteImages(posts_dir), CommonsCache(posts_dir)
    out = []
    for e in entries or []:
        if not isinstance(e, dict):
            continue
        if e.get("commons"):                     # free-licence check and credit come from Wikimedia itself
            path, credit = commons.resolve(str(e["commons"]), log=log)
            if credit:
                credit = dict(credit, source="Wikimedia Commons")
        elif e.get("unsplash"):
            path, credit = remote.resolve_unsplash(str(e["unsplash"]), str(e.get("photographer") or ""), log=log,
                                                   image_url=str(e.get("unsplash_image") or ""))
        else:
            continue
        if path:
            out.append({"src": path, "credit": credit, "alt": str(e.get("alt") or "")})
    remote.save()
    commons.save()
    return out
