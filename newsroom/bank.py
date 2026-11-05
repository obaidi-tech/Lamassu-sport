"""The image bank: checked, wide, free photos for the clubs, venues and competitions we write about most.

config/image_bank.yaml lists entries like:
    - id: real-madrid
      match: ["ريال مدريد", "Real Madrid"]       # words that pick this photo (full names, not short forms)
      not: ["ريال مدريد كاستيا"]                  # optional: phrases that must NOT trigger it
      commons: File:...jpg                         # or search:words (the chosen file is then cached)
      alt: ملعب سانتياغو برنابيو

A post without any picture of its own gets the bank photo whose name appears earliest in its title
(then in its excerpt). A post can also ask for one by id:   bank: real-madrid
"""
import os
import re

import yaml


def load_bank(path: str) -> list:
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    out = []
    for e in data.get("entries") or []:
        if e.get("id") and e.get("commons") and e.get("match"):
            out.append({"id": str(e["id"]), "commons": str(e["commons"]), "alt": str(e.get("alt") or ""),
                        "match": [str(m) for m in e["match"]], "not": [str(m) for m in (e.get("not") or [])]})
    return out


def _first_hit(text: str, entry: dict):
    """Position of the earliest trigger word in text, or None. Excluded phrases are blanked out first."""
    t = text or ""
    for bad in entry["not"]:
        t = re.sub(re.escape(bad), " " * len(bad), t, flags=re.I)
    best = None
    for word in entry["match"]:
        # a whole word: not glued to other letters (Arabic prefixes و/ب/ل/ال are allowed in front)
        m = re.search(r"(?<![\w])(?:و|ب|ل|وال|بال|لل)?" + re.escape(word) + r"(?![\w])", t, flags=re.I)
        if m and (best is None or m.start() < best):
            best = m.start()
    return best


def pick(bank: list, title: str, excerpt: str = "", want: str = ""):
    """The bank entry for a post: the one asked for by id, else the earliest name in the title, then the excerpt."""
    if want:
        return next((e for e in bank if e["id"] == want), None)
    for text in (title, excerpt):
        hits = [(p, i, e) for i, e in enumerate(bank) if (p := _first_hit(text, e)) is not None]
        if hits:
            return min(hits, key=lambda h: (h[0], h[1]))[2]
    return None
