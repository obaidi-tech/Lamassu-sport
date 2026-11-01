"""Send articles to WordPress through its built-in REST API (Application Passwords)."""
import html
import os
from datetime import datetime, timedelta, timezone

import requests


class WordPress:
    def __init__(self):
        self.base = os.environ["WP_URL"].rstrip("/") + "/wp-json/wp/v2"
        self.auth = (os.environ["WP_USER"], os.environ["WP_APP_PASSWORD"])
        self._cats, self._tags = {}, {}

    def _get_or_create(self, kind: str, name: str, cache: dict) -> int:
        if name in cache:
            return cache[name]
        r = requests.get(f"{self.base}/{kind}", params={"search": name, "per_page": 20},
                         auth=self.auth, timeout=30)
        r.raise_for_status()
        for t in r.json():
            if html.unescape(t["name"]) == name:
                cache[name] = t["id"]
                return t["id"]
        r = requests.post(f"{self.base}/{kind}", json={"name": name}, auth=self.auth, timeout=30)
        r.raise_for_status()
        cache[name] = r.json()["id"]
        return cache[name]

    def create_post(self, payload: dict) -> dict:
        r = requests.post(f"{self.base}/posts", json=payload, auth=self.auth, timeout=60)
        r.raise_for_status()
        j = r.json()
        return {"id": j["id"], "link": j.get("link"), "status": j.get("status")}

    def category_id(self, name):
        return self._get_or_create("categories", name, self._cats)

    def tag_id(self, name):
        return self._get_or_create("tags", name, self._tags)


def render_html(art: dict, c: dict) -> str:
    parts = [f"<p>{html.escape(p)}</p>" for p in art["body"]]
    lead = c["lead"]
    if c["category"] == "opinion":
        parts.append(f'<p><strong>الكاتب:</strong> {html.escape(lead.get("author") or "غير مذكور")} — '
                     f'<strong>المصدر:</strong> {html.escape(lead["publisher"])} — '
                     f'<a href="{html.escape(lead["link"])}" rel="nofollow noopener" target="_blank">اقرأ المقال الأصلي</a></p>')
    else:
        seen, links = set(), []
        for m in c["items"]:
            if m["publisher"] in seen or not m["link"]:
                continue
            seen.add(m["publisher"])
            links.append(f'<li><a href="{html.escape(m["link"])}" rel="nofollow noopener" '
                         f'target="_blank">{html.escape(m["publisher"])}</a></li>')
            if len(links) == 5:
                break
        parts.append("<h4>المصادر</h4><ul>" + "".join(links) + "</ul>")
    return "\n".join(parts)


def build_payload(art: dict, c: dict, cat_name: str, mode: str, slot_time, wp=None) -> dict:
    review = bool(c.get("problems"))
    if mode == "auto" and not review:
        status = "future"
    elif mode == "auto" and review:
        status = "pending"
    else:
        status = "draft"
    payload = {
        "title": art["title"],
        "content": render_html(art, c),
        "excerpt": art.get("excerpt", ""),
        "status": status,
    }
    if status == "future":
        payload["date_gmt"] = slot_time.strftime("%Y-%m-%dT%H:%M:%S")
    if wp:
        payload["categories"] = [wp.category_id(cat_name)]
        payload["tags"] = [wp.tag_id(t) for t in (art.get("tags") or [])[:5] if t]
    return payload


def slot_times(n: int, spacing_min: int, start=None):
    start = (start or datetime.now(timezone.utc)) + timedelta(minutes=5)
    return [start + timedelta(minutes=i * spacing_min) for i in range(n)]
