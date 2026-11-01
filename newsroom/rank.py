"""Importance score: how many distinct, credible publishers cover a story, and how fresh it is."""
from .textutil import has_keyword, normalize


def score_cluster(c: dict, rules: dict, cats_cfg: dict, half_life_h: float = 10.0) -> float:
    kw = rules["kind_weights"]
    by_pub = {}
    for m in c["items"]:
        p = normalize(m["publisher"] or m["source_id"])
        by_pub[p] = max(by_pub.get(p, 0), kw.get(m["kind"], 1.0))
    coverage = sum(by_pub.values())
    newest = min(m["age_h"] for m in c["items"])
    recency = max(0.5 ** (newest / half_life_h), 0.15)
    bonus = cats_cfg.get("category_bonus", {}).get(c["category"], 0)
    official = 1.0 if any(m["kind"] == "official" for m in c["items"]) else 0
    c["publishers"] = sorted({m["publisher"] for m in c["items"] if m["publisher"]})
    c["score"] = round((coverage + official + bonus) * recency, 3)
    return c["score"]


def editorial_flags(c: dict, rules: dict) -> list:
    """Reasons this story must go to human review instead of auto-publishing."""
    text = normalize(" ".join(m["title"] + " " + m["summary"][:300] for m in c["items"][:4]))
    flags = []
    hit = has_keyword(text, rules.get("sensitive_keywords", []))
    if hit:
        flags.append(f"موضوع حساس ({hit})")
    credible = {m["publisher"] for m in c["items"] if m["kind"] in ("official", "agency", "major_media")}
    single = len(c.get("publishers", [])) <= 1
    if not any(m["kind"] == "official" for m in c["items"]):
        rumour = has_keyword(normalize(" ".join(m["title"] for m in c["items"])), rules.get("rumour_keywords", []))
        if rumour and len(credible) < 2:
            flags.append(f"صيغة شائعة دون مصدرين موثوقين ({rumour})")
        elif single and not credible and c["category"] != "opinion":
            flags.append("مصدر واحد غير موثّق")
    return flags
