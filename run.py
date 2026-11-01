#!/usr/bin/env python3
"""تشغيل غرفة الأخبار الآلية.

أمثلة:
  python run.py --dry-run --no-llm          # تجربة مجانية: جمع واختيار دون صياغة أو نشر
  python run.py --dry-run                   # جمع + صياغة بالذكاء الاصطناعي، دون نشر (تقرير HTML فقط)
  python run.py --publish                   # التشغيل الفعلي: يرسل إلى ووردبريس حسب publish_mode
  python run.py --dry-run --all-day         # اختيار حصة اليوم كاملة (حتى 50) في تشغيل واحد
  python run.py --build-only                # تطبيق قرارات المحرر في content/pending وإعادة بناء الموقع فقط
"""
import argparse
import os
import sys

from datetime import datetime, timezone

from newsroom.pipeline import build_site, load, run
from newsroom.store import Store


def load_env(path=".env"):
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"'))


def main():
    ap = argparse.ArgumentParser(description="Sports newsroom automation")
    ap.add_argument("--publish", action="store_true", help="send to WordPress")
    ap.add_argument("--dry-run", action="store_true", help="never publish (default)")
    ap.add_argument("--no-llm", action="store_true", help="skip AI writing (free test)")
    ap.add_argument("--all-day", action="store_true", help="select the whole daily quota now")
    ap.add_argument("--sources", default=None, help="alternative sources yaml")
    ap.add_argument("--config", default="config")
    ap.add_argument("--out", default="out")
    ap.add_argument("--state", default="state/state.json")
    ap.add_argument("--content", default="content", help="published articles + review queue")
    ap.add_argument("--site-dir", default="public", help="where the website is built")
    ap.add_argument("--banner", default="", help="notice shown at the top of every page")
    ap.add_argument("--build-only", action="store_true", help="apply editor decisions and rebuild the site")
    a = ap.parse_args()
    load_env()
    if a.build_only:
        site = load(a.config)[0]
        Store(a.content).process_pending(datetime.now(timezone.utc),
                                         datetime.now(timezone.utc).astimezone(__import__("zoneinfo").ZoneInfo(site["timezone"])).strftime("%Y-%m-%d"))
        build_site(a.config, a.content, a.site_dir, banner=a.banner)
        return
    if a.publish and a.dry_run:
        sys.exit("اختر --publish أو --dry-run، لا كليهما")
    res = run(cfg_dir=a.config, sources_file=a.sources, out_dir=a.out, state_path=a.state,
              use_llm=not a.no_llm, publish=a.publish, all_day=a.all_day,
              content_dir=a.content, site_dir=a.site_dir, banner=a.banner)
    review = sum(1 for c in res["chosen"] if c.get("problems"))
    print(f"\nالمختار: {len(res['chosen'])} | يحتاج مراجعة: {review} | أُرسل: {len(res['posted'])}")
    bad = [r for r in res["report"] if r[1] != "ok"]
    if bad:
        print(f"تنبيه: {len(bad)} مصدراً لم يعمل — شغّل check_feeds.py")


if __name__ == "__main__":
    main()
