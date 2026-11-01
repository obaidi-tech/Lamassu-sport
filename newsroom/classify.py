"""Assign each cluster a category (quota bucket) and a sub-key (league / sport / country / org)."""
from .textutil import has_keyword, normalize

PRIORITY = ["opinion", "nba", "orgs", "top5", "other_sports", "awareness", "world"]


def _match_group(text_norm: str, groups: dict):
    for sub, kws in groups.items():
        if sub == "_":
            if has_keyword(text_norm, kws):
                return "all"
            continue
        if has_keyword(text_norm, kws):
            return sub
    return None


def classify(cluster: dict, cats_cfg: dict) -> tuple:
    kw = cats_cfg["keywords"]
    titles = normalize(" ".join(m["title"] for m in cluster["items"]))
    full = titles + " " + normalize(" ".join(m["summary"][:400] for m in cluster["items"][:3]))
    full += " " + normalize(" ".join(" ".join(m.get("tags") or []) for m in cluster["items"][:3]))

    forced = [m["forced_category"] for m in cluster["items"] if m.get("forced_category")]
    if forced:
        cat = min(forced, key=lambda c: PRIORITY.index(c) if c in PRIORITY else 99)
        if cat == "opinion":
            lead = next(m for m in cluster["items"] if m.get("forced_category") == "opinion")
            return "opinion", (lead.get("author") or lead["publisher"])
        sub = None
        if cat in kw:
            sub = _match_group(titles, kw[cat]) or _match_group(full, kw[cat])
        return cat, sub or "other"

    for text in (titles, full):
        for cat in ["nba", "orgs", "top5", "other_sports", "awareness"]:
            sub = _match_group(text, kw.get(cat, {}))
            if sub:
                return cat, sub
        sub = _match_group(text, {k: v for k, v in kw.get("world", {}).items() if v})
        if sub:
            return "world", sub
    if has_keyword(full, cats_cfg.get("football_markers", [])):
        return "world", "general"
    return "world", "general"
