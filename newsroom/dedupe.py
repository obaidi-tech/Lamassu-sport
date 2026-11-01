"""Catch the same story selected twice under different wording or language (e.g. Arabic + English)."""
import json

from .writer import call_claude

PROMPT = """هذه قائمة عناوين أخبار رياضية مرقمة، بعضها بالعربية وبعضها بالإنجليزية.
حدّد المجموعات التي تتناول الحدث نفسه تماماً (نفس المباراة أو نفس القرار أو نفس الانتقال).
لا تجمع خبرين مختلفين لمجرد أنهما عن الفريق نفسه.

{rows}

أعد JSON فقط: {{"duplicates": [[رقم, رقم], ...]}} — قائمة فارغة إن لم يوجد تكرار."""


def _drop_and_backfill(chosen: list, reserve: list, groups: list, pool: list) -> list:
    drop = set()
    for g in groups:
        members = [pool[i] for i in g if 0 <= i < len(pool)]
        if len(members) < 2:
            continue
        members.sort(key=lambda c: -c["score"])
        for m in members[1:]:
            drop.add(m["id"])
    kept = [c for c in chosen if c["id"] not in drop]
    spare = [c for c in reserve if c["id"] not in drop]
    for c in [c for c in chosen if c["id"] in drop]:
        same = next((r for r in spare if r["category"] == c["category"]), None) or (spare[0] if spare else None)
        if same:
            spare.remove(same)
            same["slot"] = c.get("slot", "flex")
            kept.append(same)
    return sorted(kept, key=lambda c: -c["score"]), len(drop)


def dedupe(chosen: list, all_clusters: list, site: dict, use_llm: bool, log=print) -> list:
    reserve = [c for c in sorted(all_clusters, key=lambda c: -c["score"])
               if c not in chosen and c["category"] != "opinion" and not c.get("flags")][:20]
    if use_llm:
        pool = chosen + reserve
        rows = "\n".join(f"{i}. [{c['lang']}] {c['lead']['title']}" for i, c in enumerate(pool))
        try:
            raw = call_claude("أنت محرر يكشف الأخبار المكررة.", PROMPT.format(rows=rows), site["llm"])
            groups = json.loads(raw[raw.find("{"): raw.rfind("}") + 1]).get("duplicates", [])
            chosen, n = _drop_and_backfill(chosen, reserve, groups, pool)
            if n:
                log(f"▶ أُزيل {n} خبراً مكرراً واستُبدل")
            return chosen
        except Exception as ex:
            log(f"  (تعذر فحص التكرار بالنموذج: {type(ex).__name__}) — يُستخدم الفحص البسيط")
    # heuristic fallback: same category + same specific sub, different languages → flag for a human
    for i, a in enumerate(chosen):
        for b in chosen[i + 1:]:
            if (a["lang"] != b["lang"] and a["category"] == b["category"] and a["sub"] == b["sub"]
                    and a["sub"] not in ("general", "other", "all")):
                low = a if a["score"] < b["score"] else b
                high = b if low is a else a
                low.setdefault("flags", []).append(f"احتمال تكرار مع: {high['lead']['title'][:60]}")
    return chosen
