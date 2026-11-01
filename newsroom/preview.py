"""Write an RTL HTML report of a run: what was chosen, why, and what needs review."""
import html
from collections import Counter

CSS = """
:root{--bg:#f6f5f1;--card:#fff;--ink:#1d1d1b;--mute:#6b6a64;--line:#e4e2da;--acc:#0b6e4f;--warn:#b54708;--warnbg:#fff4e5}
@media (prefers-color-scheme:dark){:root{--bg:#141413;--card:#1e1e1c;--ink:#ecebe6;--mute:#a3a29b;--line:#33332f;--acc:#4cc38a;--warn:#f5a35b;--warnbg:#2b2015}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.7 "Noto Naskh Arabic","Segoe UI",Tahoma,sans-serif}
main{max-width:980px;margin:0 auto;padding:24px 16px 64px}
h1{font-size:26px;margin:0 0 4px}.sub{color:var(--mute);margin:0 0 20px}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin-bottom:24px}
.stat{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 14px}
.stat b{display:block;font-size:22px}.stat span{color:var(--mute);font-size:13px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px 18px;margin-bottom:12px}
.meta{display:flex;flex-wrap:wrap;gap:8px;font-size:13px;color:var(--mute);margin-bottom:6px}
.pill{border:1px solid var(--line);border-radius:999px;padding:1px 10px}
.pill.cat{border-color:var(--acc);color:var(--acc)}
h2{font-size:19px;margin:4px 0 8px}
.orig{font-size:13px;color:var(--mute);direction:ltr;text-align:left}
.review{background:var(--warnbg);color:var(--warn);border-radius:8px;padding:6px 10px;font-size:14px;margin:8px 0}
.body p{margin:6px 0}
details{font-size:13px;color:var(--mute)}a{color:var(--acc)}
"""


def write_preview(path: str, chosen: list, cats_cfg: dict, meta: dict):
    cats = cats_cfg["categories"]
    by_cat = Counter(c["category"] for c in chosen)
    review = sum(1 for c in chosen if c.get("problems"))
    stats = [("أخبار مختارة", len(chosen)), ("تحتاج مراجعة", review),
             ("عناصر مجمّعة", meta["items"]), ("قصص مستقلة", meta["clusters"])]
    stats += [(cats[k]["name_ar"], v) for k, v in by_cat.most_common()]

    rows = []
    for i, c in enumerate(chosen, 1):
        art = c.get("article", {})
        prob = "".join(f'<div class="review">⚠ {html.escape(p)}</div>' for p in c.get("problems", []))
        body = "".join(f"<p>{html.escape(p)}</p>" for p in art.get("body", []))
        srcs = "".join(f'<li><a href="{html.escape(m["link"])}">{html.escape(m["publisher"])}</a> — '
                       f'{html.escape(m["title"])}</li>' for m in c["items"][:8])
        rows.append(f"""
<div class="card">
 <div class="meta"><span>#{i}</span><span class="pill cat">{html.escape(cats[c['category']]['name_ar'])}</span>
  <span class="pill">{html.escape(str(c['sub']))}</span><span class="pill">الأهمية {c['score']}</span>
  <span class="pill">{len(c['publishers'])} ناشر</span>{'<span class="pill">حصة مرنة</span>' if c.get('slot') == 'flex' else ''}</div>
 <h2>{html.escape(art.get('title', c['lead']['title']))}</h2>
 <div class="orig">{html.escape(c['lead']['title'])}</div>
 {prob}
 <div class="body">{body}</div>
 <details><summary>المصادر ({len(c['items'])})</summary><ul>{srcs}</ul></details>
</div>""")

    doc = f"""<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>تقرير التشغيل</title><style>{CSS}</style></head>
<body><main><h1>{html.escape(meta['site'])} — تقرير التشغيل</h1>
<p class="sub">{html.escape(meta['when'])} · وضع النشر: {html.escape(meta['mode'])}{' · ' + html.escape(meta['note']) if meta.get('note') else ''}</p>
<div class="stats">{''.join(f'<div class="stat"><b>{v}</b><span>{html.escape(k)}</span></div>' for k, v in stats)}</div>
{''.join(rows)}
</main></body></html>"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(doc)
