"""End-to-end test on offline fixtures, with a mocked AI writer and a mock WordPress server.
Run:  python tests/make_fixtures.py && python tests/test_pipeline.py"""
import json
import os
import re
import shutil
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

import yaml  # noqa: E402

import newsroom.dedupe as dd  # noqa: E402
import newsroom.writer as wr  # noqa: E402
from newsroom.pipeline import run  # noqa: E402

# ── mock AI (Arabic text for the fictional test headlines) ──────────────────
sys.path.insert(0, os.path.join(ROOT, "tests"))
from demo_writer import fake_claude  # noqa: E402

wr.call_claude = fake_claude
dd.call_claude = fake_claude

# ── mock WordPress ───────────────────────────────────────────────────────
POSTS, TERMS = [], {}


class WP(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, obj, code=200):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        self._send([])

    def do_POST(self):
        data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if self.path.endswith("/posts"):
            POSTS.append(data)
            self._send({"id": len(POSTS), "link": f"http://wp.test/?p={len(POSTS)}", "status": data["status"]}, 201)
        else:
            TERMS[data["name"]] = len(TERMS) + 1
            self._send({"id": TERMS[data["name"]], "name": data["name"]}, 201)


def main():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), WP)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    os.environ.update(WP_URL=f"http://127.0.0.1:{srv.server_port}", WP_USER="t", WP_APP_PASSWORD="t")

    tmp = tempfile.mkdtemp()
    cfg = os.path.join(tmp, "config")
    shutil.copytree("config", cfg)
    site = yaml.safe_load(open(os.path.join(cfg, "site.yaml"), encoding="utf-8"))
    site["publish_mode"] = "auto"
    site["output"] = "wordpress"
    yaml.safe_dump(site, open(os.path.join(cfg, "site.yaml"), "w", encoding="utf-8"), allow_unicode=True)
    state = os.path.join(tmp, "state.json")
    quiet = lambda *a: None  # noqa: E731

    r = run(cfg_dir=cfg, sources_file="tests/fixtures/sources_test.yaml", out_dir=os.path.join(tmp, "out"),
            state_path=state, use_llm=True, publish=True, all_day=True, log=quiet)
    ch = r["chosen"]
    titles = [c["lead"]["title"] for c in ch]
    by = lambda cat: sum(1 for c in ch if c["category"] == cat)  # noqa: E731
    checks = {
        "between 10 and 20 selected": 10 <= len(ch) <= 20,
        "opinion quota = 2": by("opinion") == 2,
        "nba within quota (2)": 1 <= by("nba") <= 2,
        "awareness within quota (1)": by("awareness") <= 1,
        "one piece per columnist": len({c["sub"] for c in ch if c["category"] == "opinion"}) == 2,
        "labels stripped": not any(re.match(r"(Report|Update|Watch):", t) for t in titles),
        "Al-Hilal not duplicated": sum(("Al-Hilal" in t or "الهلال" in t) for t in titles) <= 1,
        "single-source rumour excluded": not any("reportedly" in t for t in titles),
        "old item ignored": not any("Old story" in t for t in titles),
        "death story sent to review": all(c["problems"] for c in ch if "dies" in c["lead"]["title"]),
        "invented number caught": any("4" in p for c in ch if "Liverpool" in c["lead"]["title"] for p in c["problems"]),
        "every selected story sent": len(POSTS) == len(ch),
        "reviewed items are 'pending'": all(p["status"] == "pending" for p, c in zip(POSTS, ch) if c["problems"]),
        "most items auto-scheduled": sum(p["status"] == "future" for p in POSTS) >= len(POSTS) - 5,
        "clean items are scheduled": all(p["status"] == "future" and p.get("date_gmt") for p, c in zip(POSTS, ch) if not c["problems"]),
        "every post has category + sources": all(p["categories"] and ("المصادر" in p["content"] or "الكاتب" in p["content"]) for p in POSTS),
        "opinion posts credit author + link": all("Test Columnist" in p["content"] and "href" in p["content"]
                                                  for p, c in zip(POSTS, ch) if c["category"] == "opinion"),
    }
    r2 = run(cfg_dir=cfg, sources_file="tests/fixtures/sources_test.yaml", out_dir=os.path.join(tmp, "out"),
             state_path=state, use_llm=True, publish=True, all_day=True, log=quiet)
    checks["daily ceiling of 20 never exceeded"] = len(POSTS) <= 20
    checks["nothing republished on re-run"] = not ({c["lead"]["title"] for c in r2["chosen"]} & set(titles))

    # quiet day: keep only weak (1–2 publisher) stories → far fewer than 50, no filler
    weak = [c for c in r["clusters"] if len(c["publishers"]) <= 2]
    from newsroom.select import select, targets
    cats = yaml.safe_load(open(os.path.join(cfg, "categories.yaml"), encoding="utf-8"))
    tot, tg = targets(cats, 20, {"total": 0, "cats": {}, "subs": {}}, 1.0)
    quiet_day = select(weak, cats, tot, tg, {"total": 0, "cats": {}, "subs": {}})
    checks[f"quiet day publishes fewer ({len(quiet_day)} of {len(weak)} weak stories)"] = len(quiet_day) < 10
    checks["quiet day: nothing below its category floor"] = all(
        c["score"] >= cats["categories"][c["category"]]["min_score"] for c in quiet_day)

    # ── static website mode ──────────────────────────────────────────────
    site["output"] = "static"
    yaml.safe_dump(site, open(os.path.join(cfg, "site.yaml"), "w", encoding="utf-8"), allow_unicode=True)
    content, public = os.path.join(tmp, "content"), os.path.join(tmp, "public")
    r3 = run(cfg_dir=cfg, sources_file="tests/fixtures/sources_test.yaml", out_dir=os.path.join(tmp, "out"),
             state_path=os.path.join(tmp, "state2.json"), use_llm=True, publish=True, all_day=True, log=quiet,
             content_dir=content, site_dir=public)
    from newsroom.pipeline import build_site
    from newsroom.store import Store
    from datetime import datetime, timezone
    st = Store(content)
    live, pend = st.all_articles(), st.pending()
    pages = os.listdir(os.path.join(public, "article"))
    home = open(os.path.join(public, "index.html"), encoding="utf-8").read()
    checks["static: clean stories live, flagged ones queued"] = (
        len(live) == sum(1 for c in r3["chosen"] if not c["problems"]) and len(pend) == sum(1 for c in r3["chosen"] if c["problems"]))
    checks["static: one page + image per live story"] = (
        len(pages) == len(live) and all(os.path.exists(os.path.join(public, "img", f"{a['id']}.jpg")) for a in live))
    checks["static: flagged stories NOT on the site"] = all(p["title"] not in home for p in pend) and \
        not any(f"{p['id']}.html" in pages for p in pend)
    checks["static: home, categories, archive, feed, sitemap"] = all(os.path.exists(os.path.join(public, f)) for f in
        ["index.html", "category/top5.html", "category/opinion.html", "archive.html", "about.html", "feed.xml", "sitemap.xml"])
    checks["static: Arabic text rendered on home"] = live[0]["title"] in home or any(a["title"] in home for a in live[:5])
    # editor approves one queued story and rejects the rest
    for i, p in enumerate(pend):
        path = os.path.join(content, "pending", f"{p['id']}.json")
        rec = json.load(open(path, encoding="utf-8"))
        rec["decision"] = "publish" if i == 0 else "reject"
        json.dump(rec, open(path, "w", encoding="utf-8"), ensure_ascii=False)
    now = datetime.now(timezone.utc)
    st.process_pending(now, now.strftime("%Y-%m-%d"), log=quiet)
    build_site(cfg, content, public, log=quiet)
    checks["static: approved story goes live, rejected removed"] = (
        len(st.all_articles()) == len(live) + 1 and not st.pending()
        and os.path.exists(os.path.join(public, "article", f"{pend[0]['id']}.html")))

    w = max(len(k) for k in checks)
    for k, v in checks.items():
        print(f"{'PASS' if v else 'FAIL'}  {k:<{w}}")
    review = sum(1 for c in ch if c["problems"])
    print(f"\n{len(ch)} selected, {review} to review, {len(POSTS)} posts. Report: {r['html']}")
    srv.shutdown()
    sys.exit(0 if all(checks.values()) else 1)


if __name__ == "__main__":
    main()
