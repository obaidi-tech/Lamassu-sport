#!/usr/bin/env python3
"""افحص كل مصدر في config/sources.yaml واطبع: يعمل / لا يعمل، وعدد الأخبار، وأحدث عنوان.
شغّله مرة بعد التركيب، وكلما أضفت مصدراً."""
from datetime import datetime, timezone

import yaml

from newsroom.fetch import fetch_source, source_url


def main(path="config/sources.yaml"):
    with open(path, encoding="utf-8") as f:
        sources = yaml.safe_load(f)["sources"]
    with open("config/rules.yaml", encoding="utf-8") as f:
        rules = yaml.safe_load(f)
    now, ok, bad = datetime.now(timezone.utc), 0, []
    for s in sources:
        try:
            items = fetch_source(s, rules, now, max_age_h=72)
            status = "✔" if items else "⚠ فارغ"
            ok += bool(items)
            sample = items[0]["title"][:70] if items else ""
            print(f"{status:<7} {s['id']:<22} {len(items):>4}  {sample}")
            if not items:
                bad.append(s["id"])
        except Exception as ex:
            print(f"✘       {s['id']:<22}       {type(ex).__name__}: {str(ex)[:60]}")
            print(f"        {source_url(s)}")
            bad.append(s["id"])
    print(f"\n{ok}/{len(sources)} مصدراً يعمل.")
    if bad:
        print("عطّل هذه في sources.yaml بإضافة enabled: false أو صحّح روابطها:\n  " + ", ".join(bad))


if __name__ == "__main__":
    main()
