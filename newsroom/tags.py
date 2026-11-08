"""Tags: a short, editor-controlled list of teams, competitions and recurring names (config/tags.yaml).

Rules (owner's decision, 8 Nov 2026):
  - only tags in the approved list exist; anything else is ignored
  - a story gets its tags automatically from its headline and summary (not the body), or by hand with
        tags: [ريال مدريد, الدوري الإسباني]
    in the post header (hand-picked tags come first); «أبرز ما كُتب» issues are not tagged automatically
  - phrases listed under a tag's exclude: in config/tags.yaml never count for that tag
  - at most MAX_PER_ARTICLE tags per story
  - a tag page (tag/<slug>.html) is published only once MIN_FOR_PAGE stories carry it; below that the tag
    is not shown anywhere, so the site never has thin, near-empty tag pages
  - hashtags are never written into the story text
"""
import os
import re

import yaml

MAX_PER_ARTICLE = 3
MIN_FOR_PAGE = 3
_PREFIX = r"(?:[وفبكل]|وب|ول|فب|فل)?"


def _pattern(term: str) -> str:
    t = re.escape(term)
    alts = [_PREFIX + t]
    if term.startswith("ال"):                       # ل + الدوري → للدوري
        alts.append(r"(?:و|ف)?لل" + re.escape(term[2:]))
    return r"(?<![\w])(?:" + "|".join(alts) + r")(?![\w])"


def load_tags(path: str) -> list:
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    out = []
    for t in data.get("tags") or []:
        name, slug = str(t.get("name") or "").strip(), str(t.get("slug") or "").strip()
        if not name or not re.fullmatch(r"[a-z0-9-]+", slug):
            continue
        terms = [name] + [str(x).strip() for x in (t.get("match") or []) if str(x).strip()]
        excl = [str(x).strip() for x in (t.get("exclude") or []) if str(x).strip()]
        out.append({"name": name, "slug": slug,
                    "re": re.compile("|".join(_pattern(x) for x in terms)),
                    "ex": re.compile("|".join(re.escape(x) for x in excl)) if excl else None})
    return out


def assign(articles: list, tags: list, log=print) -> dict:
    """Sets a['tags'] = [{'name','slug'}] (only tags that have a page) and returns {slug: [articles]}."""
    by_name = {t["name"]: t for t in tags}
    picked = {}
    for a in articles:
        chosen = []
        for n in a.get("manual_tags") or []:
            t = by_name.get(str(n).strip())
            if t is None:
                log(f"  ⚠ وسم غير معتمد «{n}» في «{a['title'][:40]}»: أضفه إلى config/tags.yaml أو احذفه")
            elif t not in chosen:
                chosen.append(t)
        if not a.get("roundup"):
            text = f"{a.get('title', '')} {a.get('excerpt', '')}"
            for t in tags:
                hay = t["ex"].sub(" ", text) if t["ex"] else text     # «كأس العالم للأندية» is not «كأس العالم»
                if t not in chosen and t["re"].search(hay):
                    chosen.append(t)
        picked[a["id"]] = chosen[:MAX_PER_ARTICLE]
    pages = {}
    for a in articles:
        for t in picked[a["id"]]:
            pages.setdefault(t["slug"], []).append(a)
    pages = {s: items for s, items in pages.items() if len(items) >= MIN_FOR_PAGE}
    for a in articles:
        a["tags"] = [{"name": t["name"], "slug": t["slug"]} for t in picked[a["id"]] if t["slug"] in pages]
    return pages
