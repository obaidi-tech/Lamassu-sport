"""Upcoming events (content/events.yaml): shown on the home page and on events.html; past ones drop out by themselves."""
import os
from datetime import date

import yaml

SPORTS = {   # key: (Arabic label, colour variable from the site's palette)
    "football": ("كرة قدم", "--c-top5"),
    "basketball": ("كرة سلة", "--c-nba"),
    "tennis": ("تنس", "--c-other_sports"),
    "f1": ("فورمولا 1", "--c-awareness"),
    "rally": ("رالي", "--c-opinion"),
    "olympic": ("أولمبياد", "--c-orgs"),
    "para": ("بارالمبياد", "--c-para"),
}


def _d(v):
    if isinstance(v, date):
        return v
    return date.fromisoformat(str(v).strip())


def load_events(path: str, log=print) -> list:
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        raw = (yaml.safe_load(f) or {}).get("events") or []
    out = []
    for e in raw:
        try:
            start = _d(e["start"])
            end = _d(e.get("end") or e["start"])
            if end < start:
                raise ValueError("end before start")
            label, colour = SPORTS.get(str(e.get("sport", "")).strip(), ("رياضة", "--c-world"))
            link = str(e.get("link") or "").strip()
            out.append({"name": str(e["name"]).strip(), "start": start, "end": end, "sport": label, "colour": colour,
                        "place": str(e.get("place") or "").strip(), "note": str(e.get("note") or "").strip(),
                        "link": link if link.startswith("http") else ""})
        except Exception as ex:
            log(f"  ⚠ أحداث قادمة: حدث غير مفهوم ({e.get('name', '?') if isinstance(e, dict) else e}): {ex}")
    return sorted(out, key=lambda e: (e["start"], e["end"]))


def upcoming(events: list, today: date, months: list) -> list:
    """Events not yet over, with their Arabic date range and a countdown label."""
    res = []
    for e in events:
        if e["end"] < today:
            continue
        days = (e["start"] - today).days
        if e["start"] <= today <= e["end"] and e["start"] != e["end"]:
            when = "جارٍ الآن"
        elif days == 0:
            when = "اليوم"
        elif days == 1:
            when = "غداً"
        elif days == 2:
            when = "بعد يومين"
        elif 3 <= days <= 10:
            when = f"بعد {days} أيام"
        else:
            when = f"بعد {days} يوماً"
        res.append(dict(e, when=when, live=when == "جارٍ الآن", dates=date_range(e["start"], e["end"], months),
                        month="جارية الآن" if when == "جارٍ الآن" else f"{months[e['start'].month - 1]} {e['start'].year}"))
    return res


def date_range(a: date, b: date, months: list) -> str:
    m = lambda d: months[d.month - 1]  # noqa: E731
    if a == b:
        return f"{a.day} {m(a)} {a.year}"
    if a.year != b.year:
        return f"من {a.day} {m(a)} {a.year} إلى {b.day} {m(b)} {b.year}"
    if a.month != b.month:
        return f"من {a.day} {m(a)} إلى {b.day} {m(b)} {b.year}"
    return f"من {a.day} إلى {b.day} {m(a)} {a.year}"
