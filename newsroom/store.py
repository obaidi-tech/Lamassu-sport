"""Git-as-CMS: published articles and the review queue are plain JSON files in content/.

content/articles/YYYY-MM-DD/<id>.json   → live on the site
content/pending/<id>.json               → waiting for an editor. Set "decision" to "publish" or "reject".
"""
import glob
import hashlib
import json
import os
from datetime import datetime, timedelta, timezone


def article_record(c: dict, now: datetime) -> dict:
    art, lead = c["article"], c["lead"]
    seen, sources = set(), []
    for m in c["items"]:
        if m["publisher"] in seen:
            continue
        seen.add(m["publisher"])
        sources.append({"publisher": m["publisher"], "title": m["title"], "link": m["link"], "kind": m["kind"]})
    return {
        "id": hashlib.sha1((lead["link"] or lead["title"]).encode()).hexdigest()[:10],
        "title": art["title"],
        "excerpt": art.get("excerpt", ""),
        "body": art.get("body", []),
        "tags": art.get("tags", []),
        "category": c["category"],
        "sub": c["sub"],
        "score": c["score"],
        "n_sources": len(c.get("publishers") or seen),
        "sources": sources[:8],
        "author": lead.get("author") if c["category"] == "opinion" else None,
        "outlet": lead["publisher"] if c["category"] == "opinion" else None,
        "original_title": lead["title"],
        "lang": c["lang"],
        "published_at": now.isoformat(),
        "problems": c.get("problems", []),
        "draft_only": bool(art.get("_stub")),
    }


class Store:
    def __init__(self, root="content"):
        self.root = root
        self.articles_dir = os.path.join(root, "articles")
        self.pending_dir = os.path.join(root, "pending")

    def _write(self, path, rec):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(rec, f, ensure_ascii=False, indent=1)

    def publish(self, rec: dict, local_day: str):
        rec = dict(rec, problems=[])
        self._write(os.path.join(self.articles_dir, local_day, f"{rec['id']}.json"), rec)

    def hold(self, rec: dict):
        rec = dict(rec, decision="")
        self._write(os.path.join(self.pending_dir, f"{rec['id']}.json"), rec)

    def process_pending(self, now: datetime, local_day: str, expire_days: int = 3, log=print) -> dict:
        """Apply editor decisions. 'publish' → live now; 'reject' → removed; untouched for 3 days → expires."""
        done = {"published": 0, "rejected": 0, "expired": 0, "waiting": 0}
        for path in sorted(glob.glob(os.path.join(self.pending_dir, "*.json"))):
            with open(path, encoding="utf-8") as f:
                rec = json.load(f)
            decision = (rec.get("decision") or "").strip().lower()
            age = now - datetime.fromisoformat(rec["published_at"])
            if decision in ("publish", "نشر"):
                rec.pop("decision", None)
                rec["published_at"] = now.isoformat()
                self.publish(rec, local_day)
                os.remove(path)
                done["published"] += 1
            elif decision in ("reject", "رفض") or age > timedelta(days=expire_days):
                os.remove(path)
                done["rejected" if decision else "expired"] += 1
            else:
                done["waiting"] += 1
        if any(done[k] for k in ("published", "rejected", "expired")):
            log(f"▶ قائمة المراجعة: نُشر {done['published']}، رُفض {done['rejected']}، انتهت مهلة {done['expired']}")
        return done

    def all_articles(self) -> list:
        out = []
        for path in glob.glob(os.path.join(self.articles_dir, "*", "*.json")):
            with open(path, encoding="utf-8") as f:
                out.append(json.load(f))
        return sorted(out, key=lambda a: a["published_at"], reverse=True)

    def pending(self) -> list:
        out = []
        for path in glob.glob(os.path.join(self.pending_dir, "*.json")):
            with open(path, encoding="utf-8") as f:
                out.append(json.load(f))
        return sorted(out, key=lambda a: -a["score"])
