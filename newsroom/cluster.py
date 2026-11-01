"""Group items that report the same story (same language) into clusters."""
from .textutil import tokens


def similar(a: set, b: set, min_shared: int = 3, overlap: float = 0.5, jaccard: float = 0.4) -> bool:
    if not a or not b:
        return False
    shared = len(a & b)
    if shared >= min_shared and shared / min(len(a), len(b)) >= overlap:
        return True
    return shared / len(a | b) >= jaccard and shared >= 2


def cluster_items(items: list) -> list:
    """Greedy single-pass clustering. Returns list of clusters (dicts)."""
    clusters = []
    for it in sorted(items, key=lambda x: x["age_h"]):  # newest first
        tk = tokens(it["title"])
        it["_tokens"] = tk
        target = None
        for c in clusters:
            if c["lang"] != it["lang"]:
                continue
            if any(similar(tk, m["_tokens"]) for m in c["items"]):
                target = c
                break
        if target is None:
            target = {"lang": it["lang"], "items": []}
            clusters.append(target)
        target["items"].append(it)
    for i, c in enumerate(clusters):
        c["id"] = f"c{i:04d}"
        c["tokens"] = set().union(*(m["_tokens"] for m in c["items"]))
        # lead item: most authoritative, then newest
        order = {"official": 0, "agency": 1, "major_media": 2, "media": 3, "opinion": 4, "aggregator": 5}
        c["items"].sort(key=lambda m: (order.get(m["kind"], 9), m["age_h"]))
        c["lead"] = c["items"][0]
    return clusters
