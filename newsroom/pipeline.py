"""End-to-end run: collect → cluster → classify → rank → select → write → verify → publish."""
import json
import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import yaml

from .classify import classify
from .cluster import cluster_items
from .dedupe import dedupe
from .fetch import collect
from .preview import write_preview
from .events import load_events
from .posts import load_hero, load_posts
from .rank import editorial_flags, score_cluster
from .select import run_fraction, select, targets
from .site import Builder
from .state import State
from .store import Store, article_record
from .verify import check_article
from .writer import write_article


def load(cfg_dir: str, sources_file: str | None = None):
    def y(name):
        with open(os.path.join(cfg_dir, name), encoding="utf-8") as f:
            return yaml.safe_load(f)
    site, cats, rules = y("site.yaml"), y("categories.yaml"), y("rules.yaml")
    with open(sources_file or os.path.join(cfg_dir, "sources.yaml"), encoding="utf-8") as f:
        sources = yaml.safe_load(f)["sources"]
    return site, cats, rules, sources


def build_site(cfg_dir="config", content_dir="content", site_dir="public", banner="", extra=None, log=print):
    """(Re)build the static site from content/. `extra` = unsaved records to include (preview)."""
    site, cats, _, _ = load(cfg_dir)
    store = Store(content_dir)
    posts = load_posts(os.path.join(content_dir, "posts"), site["timezone"], site["site_name"], log=log)
    posts = [p for p in posts if p["category"] in cats["categories"]]
    articles = sorted(store.all_articles() + posts + (extra or []), key=lambda a: a["published_at"], reverse=True)
    hero = load_hero(os.path.join(content_dir, "posts"), site.get("hero"), log=log)
    events = load_events(os.path.join(content_dir, "events.yaml"), log=log)
    section_heroes = {}
    for cat, cfg in (site.get("section_heroes") or {}).items():
        imgs = load_hero(os.path.join(content_dir, "posts"), (cfg or {}).get("images"), log=log)
        if imgs:
            section_heroes[cat] = {"images": imgs, "sub": str((cfg or {}).get("sub") or "")}
    res = Builder(site, cats, site_dir).build(articles, banner=banner, hero=hero, events=events,
                                              section_heroes=section_heroes)
    log(f"✔ الموقع: {res['articles']} مادة (منها {len(posts)} مقالاً خاصاً) في {res['days']} يوماً → {site_dir}/index.html")
    return res


def run(cfg_dir="config", sources_file=None, out_dir="out", state_path="state/state.json",
        use_llm=True, publish=False, all_day=False, now=None, log=print,
        content_dir="content", site_dir="public", banner="", build=True):
    site, cats, rules, sources = load(cfg_dir, sources_file)
    now = now or datetime.now(timezone.utc)
    local = now.astimezone(ZoneInfo(site["timezone"]))
    day_key = local.strftime("%Y-%m-%d")
    state = State(state_path)
    used = state.day(day_key)
    static = site.get("output", "static") == "static"
    store = Store(content_dir)
    if static and publish:
        store.process_pending(now, day_key, log=log)

    log(f"▶ جمع الأخبار من {len(sources)} مصدراً …")
    items, report = collect(sources, rules, site["max_age_hours"], now=now, log=log)
    clusters = cluster_items(items)
    for c in clusters:
        c["category"], c["sub"] = classify(c, cats)
        score_cluster(c, rules, cats)
        c["flags"] = editorial_flags(c, rules)
    fresh = [c for c in clusters if not state.already_published(c["lead"]["_tokens"])]
    log(f"▶ {len(items)} عنصراً → {len(clusters)} قصة ({len(clusters) - len(fresh)} سبق نشرها)")

    fraction = 1.0 if all_day else run_fraction(site["run_hours"], local.hour)
    run_total, cat_targets = targets(cats, site["daily_total"], used, fraction)
    if site.get("max_per_run") and not all_day:
        run_total = min(run_total, int(site["max_per_run"]))
    # monthly API budget: stop writing (nothing is published as a raw draft) once the cap is reached
    from . import writer as _w
    month = local.strftime("%Y-%m")
    spend = state.data.setdefault("spend", {})
    budget = float(site["llm"].get("monthly_budget_usd") or 0)
    _w.SPENT.update(usd=0.0, calls=0)
    _w.BUDGET["left"] = (budget - spend.get(month, 0.0)) if budget else None
    if use_llm and budget and spend.get(month, 0.0) >= budget:
        log(f"⚠ بلغ إنفاق {month} الحد الشهري ({budget}$): لا كتابة ولا نشر آلي حتى بداية الشهر القادم")
        run_total = 0
    chosen = select(fresh, cats, run_total, cat_targets, used)
    chosen = dedupe(chosen, fresh, site, use_llm, log=log)
    log(f"▶ هذا التشغيل: {len(chosen)} من {run_total} مستهدفاً (منشور اليوم حتى الآن: {used['total']})")

    for c in chosen:
        cat_name = cats["categories"][c["category"]]["name_ar"]
        try:
            c["article"] = write_article(c, site, rules, cat_name, use_llm=use_llm)
            c["problems"] = c["flags"] + check_article(c["article"], c, rules)
        except Exception as ex:
            c["article"] = write_article(c, site, rules, cat_name, use_llm=False)
            c["problems"] = c["flags"] + [f"تعذرت الصياغة: {type(ex).__name__}: {str(ex)[:100]}"]

    posted, records = [], []
    if static:
        for c in chosen:
            rec = article_record(c, now)
            records.append((c, rec))
            c["live"] = site["publish_mode"] == "auto" and not c["problems"]
        if publish:
            for c, rec in records:
                if c["live"]:
                    store.publish(rec, day_key)
                    posted.append(rec["id"])
                else:
                    store.hold(rec)
                state.record(day_key, c, rec["id"])
            spend[month] = round(spend.get(month, 0.0) + _w.SPENT["usd"], 4)
            state.save()
            log(f"▶ تكلفة هذا التشغيل ≈ {_w.SPENT['usd']:.4f}$ ({_w.SPENT['calls']} طلباً)، وإنفاق {month} ≈ {spend[month]:.2f}$ من {budget or '—'}$")
            held = sum(1 for c, _ in records if not c["live"])
            log(f"▶ نُشر {len(posted)} خبراً، و{held} في قائمة المراجعة (content/pending)")
        if build:
            extra = [] if publish else [r for c, r in records if c["live"]]
            build_site(cfg_dir, content_dir, site_dir, banner=banner or ("" if publish else "معاينة: لم يُنشر شيء بعد"),
                       extra=extra, log=log)
    elif publish:
        from .publisher import WordPress, build_payload, slot_times
        wp = WordPress()
        ok = [c for c in chosen if not c["problems"]]
        times = iter(slot_times(len(ok), site["spacing_minutes"], now))
        for c in chosen:
            cat_name = cats["categories"][c["category"]]["name_ar"]
            slot = next(times) if not c["problems"] else None
            try:
                ref = wp.create_post(build_payload(c["article"], c, cat_name, site["publish_mode"], slot, wp))
                c["post"] = ref
                state.record(day_key, c, ref)
                posted.append(ref)
            except Exception as ex:
                c["problems"].append(f"فشل الإرسال إلى ووردبريس: {str(ex)[:120]}")
        state.save()

    os.makedirs(out_dir, exist_ok=True)
    stamp = local.strftime("%Y-%m-%d_%H%M%S")
    json_path = os.path.join(out_dir, f"run_{stamp}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "when": local.isoformat(), "feeds": report, "items": len(items), "clusters": len(clusters),
            "selected": [{k: v for k, v in c.items() if k not in ("items", "tokens", "lead")} |
                         {"lead_title": c["lead"]["title"], "sources": [
                             {"publisher": m["publisher"], "title": m["title"], "link": m["link"]} for m in c["items"]]}
                         for c in chosen],
        }, f, ensure_ascii=False, indent=1, default=list)
    html_path = os.path.join(out_dir, f"run_{stamp}.html")
    write_preview(html_path, chosen, cats, {
        "site": site["site_name"], "when": local.strftime("%Y-%m-%d %H:%M"), "mode": site["publish_mode"],
        "items": len(items), "clusters": len(clusters),
        "note": "" if use_llm else "دون نموذج لغوي (مسودات خام)",
    })
    log(f"✔ التقرير: {html_path}")
    return {"chosen": chosen, "clusters": clusters, "items": items, "report": report,
            "json": json_path, "html": html_path, "posted": posted, "targets": cat_targets, "run_total": run_total}
