"""«لاماسو | الفرص والتطوير الرياضي»: load content/opportunities.yaml and sort each opportunity into
open / soon (opens later) / recurring (via national bodies, or next round not announced) / closed (archive).
The status is worked out at build time, so a closed opportunity moves to the archive on its own."""
import os
from datetime import date, datetime

import yaml

FIELDS = {
    "academic": "التعليم الأكاديمي والمنح",
    "science": "علوم الرياضة والأداء",
    "coaching": "التدريب والتأهيل الفني",
    "management": "الإدارة والحوكمة",
    "media": "الإعلام والاتصال الرياضي",
    "tech": "التكنولوجيا والابتكار",
    "development": "التنمية والمبادرات الإنسانية",
    "career": "التطوير المهني والفرص العملية",
}
SUPPORT = {
    "full": "منحة كاملة",
    "partial": "تمويل جزئي",
    "free": "تدريب مجاني",
    "paid": "برنامج مدفوع",
    "project": "دعم مشروع",
    "nomination": "عبر ترشيح الجهات الوطنية",
}
SOON_DAYS = 14


def _d(v):
    if not v:
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    return date.fromisoformat(str(v).strip())


def load(path: str, today: date) -> dict:
    out = {"open": [], "soon": [], "recurring": [], "closed": [], "fields": FIELDS, "support": SUPPORT}
    if not os.path.exists(path):
        return out
    data = yaml.safe_load(open(path, encoding="utf-8")) or {}
    for o in data.get("opportunities") or []:
        if not o.get("link", "").startswith("https://") or o.get("field") not in FIELDS \
                or o.get("support") not in SUPPORT:
            continue        # a broken entry is left out rather than shown wrong
        o = dict(o)
        o["field_ar"], o["support_ar"] = FIELDS[o["field"]], SUPPORT[o["support"]]
        opens, deadline = _d(o.get("opens")), _d(o.get("deadline"))
        o["opens"], o["deadline"], o["verified"] = opens, deadline, _d(o.get("verified"))
        if deadline and deadline < today:
            o["status"] = "closed"
        elif opens and opens > today:
            o["status"] = "soon"
            o["days_to_open"] = (opens - today).days
        elif deadline:
            o["status"] = "open"
            o["days_left"] = (deadline - today).days
            o["closing"] = o["days_left"] <= SOON_DAYS
        else:
            o["status"] = "recurring"
        out[o["status"]].append(o)
    far = date(9999, 1, 1)
    out["open"].sort(key=lambda o: o["deadline"])
    out["soon"].sort(key=lambda o: o["opens"])
    out["closed"].sort(key=lambda o: o["deadline"] or far, reverse=True)
    out["count"] = len(out["open"]) + len(out["soon"]) + len(out["recurring"])
    return out
