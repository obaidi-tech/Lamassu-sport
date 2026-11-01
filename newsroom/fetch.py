"""Collect items from free RSS feeds and Google News queries."""
import calendar
import hashlib
import os
import time
from datetime import datetime, timezone
from urllib.parse import quote_plus

import feedparser
import requests

from .textutil import clean_html, normalize, strip_label, strip_publisher_suffix

UA = "Mozilla/5.0 (compatible; SportsNewsroomBot/0.1; +https://example.com/bot)"


def gnews_url(query: str, lang: str = "en") -> str:
    q = quote_plus(f"{query} when:1d")
    if lang == "ar":
        return f"https://news.google.com/rss/search?q={q}&hl=ar&gl=SA&ceid=SA:ar"
    return f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"


def source_url(src: dict) -> str:
    return src.get("url") or gnews_url(src["gnews"], src.get("lang", "en"))


def _read(url: str, timeout: int = 15):
    if url.startswith("file://") or os.path.exists(url):
        path = url[7:] if url.startswith("file://") else url
        with open(path, "rb") as f:
            return f.read()
    r = requests.get(url, headers={"User-Agent": UA}, timeout=timeout)
    r.raise_for_status()
    return r.content


def classify_publisher(name: str, default_kind: str, rules: dict) -> str:
    if default_kind == "official" or not name:
        return default_kind
    n = normalize(name)
    pw = rules.get("publisher_weights", {})
    if any(normalize(a) in n for a in pw.get("agency", [])):
        return "agency"
    if any(normalize(m) in n for m in pw.get("major_media", [])):
        return "major_media"
    return default_kind


def _entry_time(e):
    for key in ("published_parsed", "updated_parsed"):
        tp = e.get(key)
        if tp:
            return datetime.fromtimestamp(calendar.timegm(tp), tz=timezone.utc)
    return None


def fetch_source(src: dict, rules: dict, now: datetime, max_age_h: float):
    url = source_url(src)
    feed = feedparser.parse(_read(url))
    items = []
    for e in feed.entries:
        raw_title = clean_html(e.get("title", ""))
        title, suffix_pub = strip_publisher_suffix(raw_title) if "gnews" in src else (raw_title, None)
        title = strip_label(title)
        publisher = None
        if e.get("source") and e.source.get("title"):
            publisher = e.source.get("title")
        publisher = publisher or suffix_pub or src["name"]
        published = _entry_time(e) or now
        age_h = (now - published).total_seconds() / 3600
        if age_h > max_age_h or not title:
            continue
        link = e.get("link", "")
        items.append({
            "id": hashlib.sha1((link or title).encode()).hexdigest()[:16],
            "title": title,
            "summary": clean_html(e.get("summary", ""))[:1200],
            "link": link,
            "publisher": publisher,
            "kind": classify_publisher(publisher, src["kind"], rules),
            "source_id": src["id"],
            "forced_category": src.get("category"),
            "lang": src.get("lang", "en"),
            "author": clean_html(e.get("author", "")) or None,
            "tags": [t.get("term", "") for t in e.get("tags", [])][:8],
            "published": published.isoformat(),
            "age_h": round(max(age_h, 0), 2),
        })
    return items


def collect(sources: list, rules: dict, max_age_h: float, now=None, log=print):
    now = now or datetime.now(timezone.utc)
    all_items, seen, report = [], set(), []
    for src in sources:
        if src.get("enabled", True) is False:
            continue
        t0 = time.time()
        try:
            items = fetch_source(src, rules, now, max_age_h)
            report.append((src["id"], "ok", len(items)))
        except Exception as ex:  # one bad feed must never stop the run
            report.append((src["id"], f"error: {type(ex).__name__}: {str(ex)[:80]}", 0))
            continue
        for it in items:
            if it["id"] in seen:
                continue
            seen.add(it["id"])
            all_items.append(it)
        log(f"  {src['id']:<22} {len(items):>4} items  ({time.time()-t0:.1f}s)")
    return all_items, report
