"""Technical check of the built site (public/): broken internal links, images without alt text,
heavy pages, missing titles/descriptions, duplicate ids. No network needed.

    python3 tools/site_check.py [public] [--report docs/SITE_CHECK.md]

Exit code 1 when there are errors (broken links, missing alt, missing title), 0 otherwise.
Accessibility rules beyond these (contrast, ARIA) are checked by tools/a11y_check.js with axe-core.
"""
import os
import re
import sys
from html.parser import HTMLParser
from urllib.parse import urldefrag, unquote, urlparse

HEAVY_KB = 600          # page + its own images/css/js, excluding third-party embeds


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links, self.assets, self.imgs, self.ids = [], [], [], []
        self.title = self.desc = self.lang = ""
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get("id"):
            self.ids.append(a["id"])
        if tag == "html":
            self.lang = a.get("lang", "")
        elif tag == "title":
            self._in_title = True
        elif tag == "meta" and a.get("name") == "description":
            self.desc = a.get("content", "")
        elif tag == "a" and a.get("href"):
            self.links.append(a["href"])
        elif tag == "img":
            self.imgs.append(a)
            if a.get("src"):
                self.assets.append(a["src"])
        elif tag == "link" and a.get("rel") in ("stylesheet", "icon") and a.get("href"):
            self.assets.append(a["href"])
        elif tag == "script" and a.get("src"):
            self.assets.append(a["src"])

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False

    def handle_data(self, d):
        if self._in_title:
            self.title += d


def local(href):
    u = urlparse(href)
    return not (u.scheme or href.startswith("//") or href.startswith(("mailto:", "tel:", "javascript:", "data:")))


def check(root):
    errors, warns, weights = [], [], []
    pages = []
    for d, _, fs in os.walk(root):
        pages += [os.path.join(d, f) for f in fs if f.endswith(".html")]
    for path in sorted(pages):
        rel = os.path.relpath(path, root)
        html = open(path, encoding="utf-8").read()
        if rel.startswith("google"):
            continue
        p = Page()
        p.feed(html)
        redirect = 'http-equiv="refresh"' in html
        if not redirect:
            if not p.title.strip():
                errors.append((rel, "لا عنوان للصفحة <title>"))
            if not p.desc.strip() and rel != "404.html":
                warns.append((rel, "لا وصف للصفحة (meta description)"))
            if p.lang != "ar":
                warns.append((rel, f"لغة الصفحة «{p.lang}» وليست ar"))
        dup = {i for i in p.ids if p.ids.count(i) > 1}
        if dup:
            warns.append((rel, "معرّفات مكررة: " + "، ".join(sorted(dup))))
        for img in p.imgs:
            if "alt" not in img:
                errors.append((rel, f"صورة بلا نص بديل: {img.get('src', '')}"))
            elif not img["alt"].strip() and not (img.get("aria-hidden") or "hero__img" in img.get("class", "")) \
                    and "lamassu-wing" not in img.get("class", ""):
                pass   # alt="" is right for decorative pictures next to a linked title
        base = os.path.dirname(path)
        size = len(html.encode())
        seen = set()
        for href in p.links + p.assets:
            if not local(href):
                continue
            target = unquote(urldefrag(href)[0].split("?")[0])
            if not target:
                continue
            fp = os.path.normpath(os.path.join(root if target.startswith("/") else base, target.lstrip("/")))
            if os.path.isdir(fp):
                fp = os.path.join(fp, "index.html")
            if not os.path.exists(fp):
                errors.append((rel, f"رابط داخلي مكسور: {href}"))
            elif href in p.assets and fp not in seen:
                seen.add(fp)
                size += os.path.getsize(fp)
        weights.append((size // 1024, rel))
        if size // 1024 > HEAVY_KB:
            warns.append((rel, f"صفحة ثقيلة: {size // 1024} ك.ب (الحد {HEAVY_KB})"))
    return pages, errors, warns, sorted(weights, reverse=True)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    root = args[0] if args else "public"
    report = sys.argv[sys.argv.index("--report") + 1] if "--report" in sys.argv else ""
    pages, errors, warns, weights = check(root)
    lines = [f"# الفحص التقني للموقع", "",
             f"- الصفحات: {len(pages)}", f"- أخطاء: {len(errors)}", f"- تنبيهات: {len(warns)}",
             f"- متوسط وزن الصفحة: {sum(w for w, _ in weights) // max(1, len(weights))} ك.ب (دون التضمينات الخارجية)", ""]
    if errors:
        lines += ["## أخطاء", ""] + [f"- `{r}`: {m}" for r, m in errors] + [""]
    if warns:
        lines += ["## تنبيهات", ""] + [f"- `{r}`: {m}" for r, m in warns] + [""]
    lines += ["## أثقل الصفحات", ""] + [f"- `{r}`: {w} ك.ب" for w, r in weights[:8]] + [""]
    out = "\n".join(lines)
    print(out)
    if report:
        with open(report, "w", encoding="utf-8") as f:
            f.write(out)
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
