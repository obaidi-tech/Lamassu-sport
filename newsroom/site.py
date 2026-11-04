"""Build the static website from content/ — no server, no database, free hosting (GitHub Pages)."""
import json
import os
import shutil
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup

from .events import upcoming
from .cards import covered_label, make_brand_card, make_card, news_label, sources_label

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DAYS = ["الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"]
MONTHS = {
    "gulf": ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو", "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"],
    "levant": ["كانون الثاني", "شباط", "آذار", "نيسان", "أيار", "حزيران", "تموز", "آب", "أيلول",
               "تشرين الأول", "تشرين الثاني", "كانون الأول"],
}
DISPLAY_ORDER = ["top5", "orgs", "world", "other_sports", "nba", "para", "awareness"]
CARD_DAYS = 30            # newer articles get their own card image; older ones share a category image


def _table(block: str) -> Markup:
    """'| a | b |' lines → an accessible HTML table; first row is the heading, '|---|' rows are skipped.
    Columns whose cells are numbers are aligned for easy comparison."""
    import re
    rows = []
    for line in block.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
            continue
        rows.append(cells)
    if not rows:
        return Markup("")
    head, body = rows[0], rows[1:]
    num = lambda c: bool(re.fullmatch(r"[\d٠-٩.,+\-–% ]+", c))  # noqa: E731
    th = "".join(f'<th scope="col">{_inline_links(c)}</th>' for c in head)
    trs = []
    for r in body:
        tds = "".join(f'<td{" class=num" if num(c) else ""}>{_inline_links(c)}</td>' for c in r)
        trs.append(f"<tr>{tds}</tr>")
    return Markup(f'<div class="table-wrap" tabindex="0"><table><thead><tr>{th}</tr></thead>'
                  f'<tbody>{"".join(trs)}</tbody></table></div>')


def _domain(url: str) -> str:
    """https://sports.yahoo.com/x/y → sports.yahoo.com  (shown under a source name instead of the long address)"""
    from urllib.parse import urlparse
    host = urlparse(str(url or "")).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def _inline_links(text: str) -> Markup:
    """Escape a paragraph, then turn **bold** into bold and [label](https://…) into an outbound link."""
    import re
    from markupsafe import escape as esc
    out = str(esc(text))
    out = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", out)
    return Markup(re.sub(r"\[([^\]]+)\]\((https?://[^\s)]+)\)",
                         lambda m: f'<a href="{m.group(2)}" rel="nofollow noopener" target="_blank">{m.group(1)}</a>', out))


def load_links(path: str) -> dict:
    """config/links.yaml → groups of competitions, each with (label, url) pairs. Missing file = no page content."""
    import yaml
    from urllib.parse import urlparse
    if not os.path.exists(path):
        return {"groups": [], "home": []}
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    groups, home = [], []
    for g in data.get("groups") or []:
        items = []
        for it in g.get("items") or []:
            parsed = []
            for raw in it.get("links") or []:
                label, _, url = str(raw).partition("|")
                label, url = label.strip(), url.strip()
                if label and url.startswith("https://"):
                    parsed.append((label, url))
            if not parsed:
                continue
            item = {"name": it["name"], "parsed": parsed,
                    "domain": urlparse(parsed[0][1]).netloc.replace("www.", "")}
            items.append(item)
            if it.get("home"):
                home.append(item)
        if items:
            groups.append({"title": g.get("title", ""), "comps": items})
    return {"groups": groups, "home": home}


class Builder:
    def __init__(self, site: dict, cats_cfg: dict, out_dir: str):
        self.site, self.cats = dict(site), cats_cfg["categories"]
        email = str(self.site.get("contact_email") or "")
        self.site["email"] = email if "@" in email and "example." not in email else ""
        li = str(self.site.get("linkedin_url") or "")
        self.site["linkedin"] = li if li.startswith("https://") and "linkedin.com/" in li else ""
        form = str(self.site.get("contribute_form_url") or "").strip()
        ok_form = form.startswith("https://") and any(h in form for h in ("docs.google.com/forms", "forms.gle/"))
        self.site["contribute"] = form if ok_form else ""
        self.out = out_dir
        self.tz = ZoneInfo(site["timezone"])
        self.months = MONTHS.get(site.get("month_names", "gulf"), MONTHS["gulf"])
        self.env = Environment(loader=FileSystemLoader(os.path.join(ROOT, "templates")),
                               autoescape=select_autoescape(["html", "xml"]), trim_blocks=True, lstrip_blocks=True)
        self.env.filters["day"] = self.day_label
        self.env.filters["time"] = lambda iso: self.local(iso).strftime("%H:%M")
        self.env.filters["ago"] = self.ago
        self.env.filters["sources"] = sources_label
        self.env.filters["news"] = news_label
        self.env.filters["covered"] = covered_label
        # JSON for <script> blocks: marked safe so quotes aren't HTML-escaped; "</" broken up so it can't close the tag
        self.env.filters["links"] = _inline_links
        self.env.filters["domain"] = _domain
        self.env.filters["table"] = _table
        self.env.filters["tojson_ar"] = lambda o: Markup(json.dumps(o, ensure_ascii=False).replace("</", "<\\/"))
        self.now = datetime.now(timezone.utc)
        self.links = load_links(os.path.join(ROOT, "config", "links.yaml"))
        self.nav = DISPLAY_ORDER + ["opinion"]

    # ── helpers ────────────────────────────────────────────────────────
    def local(self, iso):
        return datetime.fromisoformat(iso).astimezone(self.tz)

    def day_label(self, iso_or_dt):
        d = self.local(iso_or_dt) if isinstance(iso_or_dt, str) else iso_or_dt
        return f"{DAYS[d.weekday()]} {d.day} {self.months[d.month - 1]} {d.year}"

    def ago(self, iso):
        mins = int((self.now - datetime.fromisoformat(iso)).total_seconds() // 60)
        if mins < 60:
            return "قبل دقائق" if mins < 10 else f"قبل {mins} دقيقة"
        if mins < 24 * 60:
            h = mins // 60
            return "قبل ساعة" if h == 1 else ("قبل ساعتين" if h == 2 else f"قبل {h} ساعات" if h <= 10 else f"قبل {h} ساعة")
        return self.day_label(iso)

    def _render(self, tpl, path, depth, **ctx):
        full = os.path.join(self.out, path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        root = "../" * depth
        if path == "404.html":      # GitHub shows this page at any address, so its links must be absolute
            root = str(self.site.get("site_url") or "").rstrip("/") + "/"
        html = self.env.get_template(tpl).render(site=self.site, links=self.links, cats=self.cats, nav=self.nav,
                                                 has_reads=getattr(self, "has_reads", False),
                                                 has_events=getattr(self, "has_events", False),
                                                 root=root, path=path, now=self.now, **ctx)
        with open(full, "w", encoding="utf-8") as f:
            f.write(html)

    def _images(self, articles):
        try:
            self._make_images(articles)
        except Exception as ex:  # images are a nice-to-have; never block publishing
            print(f"  ⚠ تعذر توليد الصور ({type(ex).__name__}: {ex}). يُنشر الموقع دون صور مشاركة.")
            for a in articles:
                a.setdefault("image", f"img/default-{a['category']}.jpg")

    def _make_images(self, articles):
        img_dir = os.path.join(self.out, "img")
        make_brand_card(os.path.join(img_dir, "og-default.jpg"), self.site["site_name"],
                        self.site["tagline"], self.site.get("tagline_en", ""))
        for cat, c in self.cats.items():
            path = os.path.join(img_dir, f"default-{cat}.jpg")
            if not os.path.exists(path):
                make_card(path, self.site["tagline"], cat, c["name_ar"], self.site["site_name"], "", 0)
        cutoff = self.now - timedelta(days=CARD_DAYS)
        for a in articles:
            if a.get("cover_src"):                       # hand-written post with its own image
                ext = os.path.splitext(a["cover_src"])[1].lower()
                rel = f"img/{a['id']}{ext}"
                os.makedirs(img_dir, exist_ok=True)
                shutil.copyfile(a["cover_src"], os.path.join(self.out, rel))
                a["image"] = a["cover"] = rel
                try:
                    from PIL import Image
                    with Image.open(a["cover_src"]) as im:
                        a["cover_w"], a["cover_h"] = im.size
                except Exception:
                    pass
            elif datetime.fromisoformat(a["published_at"]) >= cutoff:
                rel = f"img/{a['id']}.jpg"
                if not os.path.exists(os.path.join(self.out, rel)):
                    make_card(os.path.join(self.out, rel), a["title"], a["category"],
                              self.cats[a["category"]]["name_ar"], self.site["site_name"],
                              self.day_label(a["published_at"]), a["n_sources"])
                a["image"] = rel
            else:
                a["image"] = f"img/default-{a['category']}.jpg"

    # ── build ──────────────────────────────────────────────────────────
    def _hero(self, hero, prefix="hero"):
        """Banner photos, made light: cropped to the banner's shape and saved in two sizes (phone ~760px,
        desktop ~1400px). The file name carries a fingerprint of the photo, so a browser never shows an
        old picture after a photo is changed."""
        import hashlib
        out = []
        os.makedirs(os.path.join(self.out, "img"), exist_ok=True)
        for i, h in enumerate(hero or []):
            try:
                from PIL import Image
                with open(h["src"], "rb") as f:
                    tag = hashlib.sha1(f.read()).hexdigest()[:8]
                with Image.open(h["src"]) as im:
                    im = im.convert("RGB")
                    ratio = 2.4                                    # wide banner shape
                    w, ht = im.size
                    if w / ht < ratio:                              # too tall: keep the upper-middle band
                        nh = round(w / ratio)
                        top = max(0, min(ht - nh, round((ht - nh) * 0.4)))
                        im = im.crop((0, top, w, top + nh))
                    files = {}
                    for size in (1400, 760):
                        rel = f"img/{prefix}-{tag}-{size}.jpg"
                        small = im if im.width <= size else im.resize((size, round(im.height * size / im.width)), Image.LANCZOS)
                        small.save(os.path.join(self.out, rel), "JPEG", quality=72, optimize=True, progressive=True)
                        files[size] = (rel, small.size)
                big, big_size = files[1400]
                out.append({"src": big, "w": big_size[0], "h": big_size[1], "src_small": files[760][0],
                            "credit": h["credit"], "alt": h["alt"]})
            except Exception as ex:
                print(f"  ⚠ صورة الترويسة {prefix} {i + 1}: {type(ex).__name__}")
        return out

    def build(self, articles: list, pending_count: int = 0, banner: str = "", hero=None, events=None, section_heroes=None):
        os.makedirs(self.out, exist_ok=True)
        shutil.copytree(os.path.join(ROOT, "site_assets"), os.path.join(self.out, "assets"), dirs_exist_ok=True)
        if os.path.isdir(os.path.join(ROOT, "site_root")):      # files that must sit at the site root (e.g. Google verification)
            shutil.copytree(os.path.join(ROOT, "site_root"), self.out, dirs_exist_ok=True)
        self._images(articles)
        common = {"banner": banner}
        present = {a["category"] for a in articles}
        self.nav = [c for c in DISPLAY_ORDER + ["opinion"] if c in present]   # empty sections stay hidden until their first story
        self.has_reads = any(a.get("roundup") for a in articles)
        coming = upcoming(events or [], self.now.astimezone(self.tz).date(), self.months)
        self.has_events = bool(coming)
        by_file = {a["file"]: a for a in articles if a.get("file")}
        for a in articles:
            a["linked"] = []
        for a in articles:                      # "related:" links an article and a news story both ways
            for f in a.get("related_files", []):
                b = by_file.get(f) or by_file.get(f + ".md")
                if not b or b is a:
                    print(f"  ⚠ {a.get('file')}: الملف المرتبط «{f}» غير موجود")
                    continue
                if b not in a["linked"]:
                    a["linked"].append(b)
                if a not in b["linked"]:
                    b["linked"].append(a)

        news = [a for a in articles if a["category"] != "opinion"]
        recent = [a for a in news if self.now - datetime.fromisoformat(a["published_at"]) < timedelta(hours=30)]
        ranked = sorted(recent or news[:30], key=lambda a: -a["score"])
        lead, runners = (ranked[0] if ranked else None), ranked[1:5]
        used = {a["id"] for a in ranked[:5]}
        own = [a for a in articles if a.get("own") and a["category"] == "opinion"]
        if lead is None and own:          # no news yet: our own newest article takes the lead spot
            lead = own[0]
            used.add(lead["id"])
        sections = []
        for cat in DISPLAY_ORDER:
            items = [a for a in news if a["category"] == cat and a["id"] not in used][:5]
            if items:
                sections.append((cat, items))
        today_key = self.now.astimezone(self.tz).date()
        today = [a for a in news if self.local(a["published_at"]).date() == today_key]
        self._render("index.html", "index.html", 0, lead=lead, runners=runners, sections=sections,
                     opinions=[a for a in self._opinion_band(articles) if a["id"] not in used],
                     today_count=len(today), today_sources=sum(a["n_sources"] for a in today),
                     edition_day=self.day_label(self.now), hero=self._hero(hero), coming=coming[:6], **common)

        for a in articles:
            same = [b for b in articles if b["category"] == a["category"] and b["id"] != a["id"]][:4]
            others = [b for b in articles if b["category"] != a["category"] and b["id"] != a["id"]]
            related = (same + others)[:4]
            related_title = "من القسم نفسه" if related and len(same) == len(related) else "اقرأ أيضاً"
            self._render("article.html", f"article/{a['id']}.html", 1, a=a, related=related, related_title=related_title, **common)

        for cat in DISPLAY_ORDER + ["opinion"]:
            items = [a for a in articles if a["category"] == cat][:80]
            sh = (section_heroes or {}).get(cat)
            imgs = self._hero(sh["images"], prefix=f"hero-{cat}") if sh else []
            self._render("list.html", f"category/{cat}.html", 1, title=self.cats[cat]["name_ar"],
                         items=items, cat=cat, section_hero={"images": imgs, "sub": sh.get("sub", "")} if imgs else None,
                         **common)

        by_day = {}
        for a in articles:
            by_day.setdefault(self.local(a["published_at"]).strftime("%Y-%m-%d"), []).append(a)
        for day, items in by_day.items():
            items.sort(key=lambda a: -a["score"])
            self._render("list.html", f"day/{day}.html", 1, title=f"عدد {self.day_label(items[0]['published_at'])}",
                         items=items, cat=None, **common)
        self._render("archive.html", "archive.html", 0, days=[(d, self.day_label(v[0]["published_at"]), len(v))
                                                               for d, v in sorted(by_day.items(), reverse=True)], **common)
        self._render("about.html", "about.html", 0, **common)
        self._render("contact.html", "contact.html", 0, **common)
        contributions = [a for a in articles if a.get("contributor")]
        if self.site["contribute"]:          # the page goes live once the Google Form link is set
            self._render("contribute.html", "contribute.html", 0, contributions=contributions, **common)
        self._render("schedules.html", "schedules.html", 0, **common)

        # latest news: chronological, grouped by day (most recent 120 items)
        latest, groups = articles[:120], []
        for a in latest:
            label = self.day_label(a["published_at"])
            if not groups or groups[-1][0] != label:
                groups.append((label, []))
            groups[-1][1].append(a)
        self._render("latest.html", "latest.html", 0, days=groups, more=len(articles) > len(latest), **common)

        # site search: a small JSON index read by search.html in the browser (no external service)
        idx = []
        for a in articles:
            body = " ".join(p.lstrip("#- ").replace("\n- ", " ").replace("|", " ") for p in a.get("body", []))
            idx.append({"t": a["title"], "e": a.get("excerpt", ""), "u": f"article/{a['id']}.html", "c": a["category"],
                        "d": a["published_at"], "dl": self.day_label(a["published_at"]), "b": body,
                        "s": " ".join(filter(None, [a.get("author") or ""]
                                             + [x.get("publisher", "") for x in a.get("sources", [])]
                                             + [_domain(x.get("link")) for x in a.get("sources", [])]))})
        with open(os.path.join(self.out, "search-index.json"), "w", encoding="utf-8") as f:
            json.dump(idx, f, ensure_ascii=False, separators=(",", ":"))
        self._render("search.html", "search.html", 0, cat_names={k: v["name_ar"] for k, v in self.cats.items()}, **common)
        if coming:
            months = []
            for e in coming:
                if not months or months[-1][0] != e["month"]:
                    months.append((e["month"], []))
                months[-1][1].append(e)
            self._render("events.html", "events.html", 0, months=months, coming=coming, **common)
        reads = [a for a in articles if a.get("roundup")]
        if reads:
            self._render("reads.html", "reads.html", 0, items=reads, **common)
        self._render("404.html", "404.html", 0, latest=[a for a in articles if a["category"] != "opinion"][:5], **common)
        self._feeds(articles)
        return {"articles": len(articles), "days": len(by_day), "out": self.out}

    @staticmethod
    def _opinion_band(articles):
        """Home-page opinion band: the newest piece by our own writers first, then the latest others."""
        ops = [a for a in articles if a["category"] == "opinion"]          # already newest-first
        own = [a for a in ops if a.get("own")][:1]
        return (own + [a for a in ops if a not in own])[:3]

    def _feeds(self, articles):
        base = self.site["site_url"].rstrip("/")
        items = []
        for a in articles[:50]:
            link = f"{base}/article/{a['id']}.html"
            items.append(f"<item><title>{escape(a['title'])}</title><link>{link}</link><guid>{link}</guid>"
                         f"<pubDate>{format_datetime(datetime.fromisoformat(a['published_at']))}</pubDate>"
                         f"<category>{escape(self.cats[a['category']]['name_ar'])}</category>"
                         f"<description>{escape(a['excerpt'])}</description></item>")
        rss = (f'<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel>'
               f"<title>{escape(self.site['site_name'])}</title><link>{base}/</link>"
               f"<description>{escape(self.site['tagline'])}</description><language>ar</language>"
               + "".join(items) + "</channel></rss>")
        newest = articles[0]["published_at"][:10] if articles else self.now.date().isoformat()
        reads = [a for a in articles if a.get("roundup")]
        urls = [(f"{base}/", newest), (f"{base}/latest.html", newest)] + ([(f"{base}/contribute.html", None)] if self.site.get("contribute") else []) + ([(f"{base}/events.html", None)] if getattr(self, "has_events", False) else []) + ([(f"{base}/reads.html", reads[0]["published_at"][:10])] if reads else []) + [ (f"{base}/schedules.html", newest), (f"{base}/archive.html", newest),
                (f"{base}/about.html", None), (f"{base}/contact.html", None)]
        for c in DISPLAY_ORDER + ["opinion"]:                      # only sections that have content
            items = [a for a in articles if a["category"] == c]
            if items:
                urls.append((f"{base}/category/{c}.html", items[0]["published_at"][:10]))
        urls += [(f"{base}/article/{a['id']}.html", a["published_at"][:10]) for a in articles]
        sitemap = ('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                   + "".join(f"<url><loc>{u}</loc>{f'<lastmod>{d}</lastmod>' if d else ''}</url>\n" for u, d in urls)
                   + "</urlset>\n")
        for name, body in [("feed.xml", rss), ("sitemap.xml", sitemap),
                           ("robots.txt", f"User-agent: *\nAllow: /\nSitemap: {base}/sitemap.xml\n"),
                           (".nojekyll", "")]:
            with open(os.path.join(self.out, name), "w", encoding="utf-8") as f:
                f.write(body)
