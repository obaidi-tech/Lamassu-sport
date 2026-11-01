"""Small JSON state: what was published (to avoid repeats) and today's counts per category."""
import json
import os
from datetime import datetime, timedelta, timezone

from .cluster import similar


class State:
    def __init__(self, path: str):
        self.path = path
        self.data = {"published": [], "daily": {}}
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                self.data = json.load(f)

    def day(self, day_key: str) -> dict:
        return self.data["daily"].setdefault(day_key, {"total": 0, "cats": {}, "subs": {}})

    def already_published(self, toks: set) -> bool:
        return any(similar(toks, set(p["tokens"])) for p in self.data["published"])

    def record(self, day_key: str, cluster: dict, post_ref=None):
        d = self.day(day_key)
        d["total"] += 1
        d["cats"][cluster["category"]] = d["cats"].get(cluster["category"], 0) + 1
        sk = f'{cluster["category"]}:{cluster["sub"]}'
        d["subs"][sk] = d["subs"].get(sk, 0) + 1
        self.data["published"].append({
            "tokens": sorted(cluster["lead"]["_tokens"]),
            "title": cluster["lead"]["title"],
            "at": datetime.now(timezone.utc).isoformat(),
            "category": cluster["category"],
            "post": post_ref,
        })

    def prune(self, keep_days: int = 4):
        cutoff = datetime.now(timezone.utc) - timedelta(days=keep_days)
        self.data["published"] = [p for p in self.data["published"]
                                  if datetime.fromisoformat(p["at"]) >= cutoff]
        for k in sorted(self.data["daily"])[:-keep_days]:
            del self.data["daily"][k]

    def save(self):
        self.prune()
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=1)
