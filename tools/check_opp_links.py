"""Check every link in content/opportunities.yaml (run monthly by .github/workflows/opportunities-links.yml).
Prints a Markdown report and exits 1 when a link is broken (404/410, DNS or connection failure).
403/429 are reported as "could not check" (many sites refuse automated requests) but do not fail."""
import sys

import requests
import yaml

BROKEN = {404, 410}
data = yaml.safe_load(open("content/opportunities.yaml", encoding="utf-8")) or {}
broken, unsure = [], []
for o in data.get("opportunities") or []:
    url = o.get("link", "")
    try:
        r = requests.get(url, timeout=25, allow_redirects=True,
                         headers={"User-Agent": "Mozilla/5.0 (compatible; Lamassu link check)"})
        if r.status_code in BROKEN:
            broken.append((o["id"], url, str(r.status_code)))
        elif r.status_code >= 400:
            unsure.append((o["id"], url, str(r.status_code)))
    except requests.RequestException as e:
        broken.append((o["id"], url, type(e).__name__))
lines = ["## فحص روابط «الفرص والتطوير الرياضي»", ""]
lines += [f"- ❌ `{i}` — {u} ({c})" for i, u, c in broken] or ["- لا روابط معطلة."]
if unsure:
    lines += ["", "تعذّر الفحص الآلي (قد يرفض الموقع الطلبات الآلية، يُراجع يدوياً):"]
    lines += [f"- ⚠️ `{i}` — {u} ({c})" for i, u, c in unsure]
print("\n".join(lines))
sys.exit(1 if broken else 0)
