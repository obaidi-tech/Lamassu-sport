"""«مباريات مباشرة»: a few matches the editor picks, shown live through Sofascore's free official widget.

content/live.yaml:
    matches:
      - sofascore: <the embed code from the match page, or just its number>
        title: نوتنغهام فورست - مانشستر سيتي      # optional, for the credit link and screen readers
        until: 2026-11-10                         # shown until the end of this day (Riyadh), then hidden
        when: 2026-11-08 18:30                    # optional: kick-off, Riyadh time, shown on the card

Only Sofascore's own widget address is ever put on the page: the match number is pulled out of whatever
was pasted, and nothing else from it is kept.
"""
import os
import re
from datetime import date, datetime

import yaml


def _match_id(raw) -> str:
    s = str(raw or "").strip()
    m = re.search(r"liveResult\?id=(\d{5,12})", s) or re.search(r"#id:(\d{5,12})", s) or re.fullmatch(r"(\d{5,12})", s)
    return m.group(1) if m else ""


def load_live(path: str, today: date) -> list:
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    out = []
    for m in data.get("matches") or []:
        mid = _match_id(m.get("sofascore"))
        until = m.get("until")
        if isinstance(until, str):
            try:
                until = date.fromisoformat(until)
            except ValueError:
                until = None
        if not mid or not isinstance(until, date) or until < today:
            continue
        lang = m.get("lang") if m.get("lang") in ("ar", "en") else "en"
        when = str(m.get("when") or "").strip()          # optional kick-off, Riyadh time: 2026-11-08 18:30
        try:
            when = datetime.strptime(when, "%Y-%m-%d %H:%M") if when else None
        except ValueError:
            when = None
        out.append({"id": mid, "title": str(m.get("title") or ""), "until": until, "when": when,
                    "src": f"https://widgets.sofascore.com/{lang}/embed/liveResult?id={mid}&widgetTheme=light",
                    "page": f"https://www.sofascore.com/event/{mid}"})
    return out[:4]
