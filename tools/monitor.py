"""Lamassu news-monitoring log (سجل الرصد الموحد): one record for every item the monitoring turns up,
whether or not it is published. For the editorial team only; it is not part of the website.

The log lives in content/monitor/YYYY-MM.yaml. Each item gets one of four states (owner's decision, 9 Nov 2026):

  جديد         new event not covered before            → its own story, after checking the source and the archive
  تطور جوهري   major development of a covered story   → its own story, linked to the earlier one (follows)
  تحديث        extra detail, the meaning is unchanged  → added to the existing story or its internal updates log
  مكرر         same event, another source or echo      → dropped from the publishing list

The rule: new information is not a major development just because it is new; what counts is how much it
changes the understanding of the event. A major development needs a «yes» to at least one of the first three
questions of the test; the fourth on its own («an important addition») makes it an update, not a new story.
The test only helps: the final call on every major development is a human editor's (approved_by).

    python3 tools/monitor.py check "عنوان الخبر" ["سطر التلخيص"] [--story STORY_ID]
        archive search before deciding: every post of the story id (all dates), similar posts in the last
        7 days, and similar posts in the whole archive. Similarity uses names, tags and wording together,
        not the headline alone. Then prints the four-question test.
    python3 tools/monitor.py story STORY_ID      the story's path: every post and log entry, oldest first
    python3 tools/monitor.py validate            checks the log and the story_id / follows fields in posts
    python3 tools/monitor.py report [YYYY-MM]    counts by state

Entry fields (content/monitor/YYYY-MM.yaml):
  - id: M-2026-11-09-01            date: 2026-11-09 10:34
    title: ...                     source: رويترز | https://...
    status: جديد | تطور جوهري | تحديث | مكرر
    story_id: f1-2026-brazil       follows: 2026-11-07-x.md   (the earlier post; for مكرر: the post it repeats;
                                                               for تحديث: the post that receives the update)
    test: [نتيجة, قرار, حقيقة, إضافة]     the test questions answered «yes»
    verified: true                 archive_checked: true
    approved_by: محمد العبيدي       (required for تطور جوهري)
    post: 2026-11-08-y.md          the story published from this entry (جديد / تطور جوهري)
    note: ...
"""
import glob
import os
import re
import sys
from datetime import datetime, timedelta

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from newsroom.posts import load_posts          # noqa: E402
from newsroom import tags as _tags              # noqa: E402

STATES = {"جديد": "new", "تطور جوهري": "major_development", "تحديث": "update", "مكرر": "duplicate",
          "new": "new", "major_development": "major_development", "update": "update", "duplicate": "duplicate"}
AR = {"new": "جديد", "major_development": "تطور جوهري", "update": "تحديث", "duplicate": "مكرر"}
TEST = [("نتيجة", "هل تغيرت نتيجة الحدث أو حالته الرسمية؟"),
        ("قرار", "هل صدر قرار أو حُسم سؤال كان مفتوحاً؟"),
        ("حقيقة", "هل ظهرت حقيقة موثقة تغيّر فهم القصة؟"),
        ("إضافة", "هل توجد إضافة مهمة لم تُذكر في الخبر السابق؟")]
MAJOR_KEYS = {"نتيجة", "قرار", "حقيقة"}
STOP = set("""في من على إلى الى عن مع بعد قبل أمام امام بين حتى منذ خلال دون عبر ضد هذا هذه ذلك التي الذي الذين
كان كانت يكون تكون أن ان إن لا لم لن ما قد ثم أو او بل كل أي اي يوم اليوم الأحد الاثنين السبت الجمعة الخميس الأربعاء
الثلاثاء أول اول ثاني الثاني الأولى الاولى فوز يفوز تفوز فاز خسارة يخسر نتيجة لقب بطولة مباراة الموسم المركز نقاط نقطة
هدف هدفا هدفاً أهداف للمرة مرة جديد جديدة لاماسو""".split())


def _norm(w: str) -> str:
    w = re.sub(r"[ً-ْـ]", "", w)
    w = w.translate(str.maketrans("أإآىة", "ااايه"))
    for p in ("وبال", "وال", "بال", "فال", "كال", "لل", "ال"):
        if w.startswith(p) and len(w) - len(p) >= 3:
            w = w[len(p):]
            break
    return w


def _words(text: str) -> set:
    return {n for w in re.findall(r"[\w؀-ۿ]+", text or "")
            if len(w) >= 3 and w not in STOP and not w.isdigit() and len(n := _norm(w)) >= 3 and n not in STOP}


def _grams(text: str) -> set:
    t = re.sub(r"\s+", " ", " ".join(_norm(w) for w in (text or "").split()))
    return {t[i:i + 3] for i in range(len(t) - 2)}


def _jac(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a and b else 0.0


def _posts():
    import yaml as _y
    site = _y.safe_load(open(os.path.join(ROOT, "config", "site.yaml"), encoding="utf-8"))
    posts = load_posts(os.path.join(ROOT, "content", "posts"), site["timezone"], site["site_name"],
                       log=lambda *a, **k: None)
    _tags.assign(posts, _tags.load_tags(os.path.join(ROOT, "config", "tags.yaml")), log=lambda *a, **k: None)
    return posts


def _first_para(p) -> str:
    for b in p.get("body") or []:
        if isinstance(b, str) and not b.startswith(("!fig", "<", "|", "#", "-")):
            return re.sub(r"<[^>]+>", "", b)[:400]
    return ""


def _all_tags(text: str) -> set:
    return {t["slug"] for t in _tags.load_tags(os.path.join(ROOT, "config", "tags.yaml")) if t["re"].search(text)}


def _load_log():
    rows = []
    for f in sorted(glob.glob(os.path.join(ROOT, "content", "monitor", "*.yaml"))):
        try:
            data = yaml.safe_load(open(f, encoding="utf-8")) or {}
        except yaml.YAMLError as err:
            mark = getattr(err, "problem_mark", None)
            print(f"✗ {os.path.basename(f)}: خطأ في الصياغة" + (f" في السطر {mark.line + 1}" if mark else "")
                  + " (غالباً نقطتان «: » داخل نص غير محاط بعلامتي تنصيص)")
            continue
        for e in data.get("entries") or []:
            e["_file"] = os.path.basename(f)
            rows.append(e)
    return rows


def check(title: str, excerpt: str = "", story: str = ""):
    posts = _posts()
    text = f"{title} {excerpt}"
    w, g, tg = _words(text), _grams(text), _all_tags(text)
    now = datetime.now().astimezone()
    scored = []
    for p in posts:
        ptext = f"{p['title']} {p.get('excerpt', '')}"
        pw = _words(ptext) | _words(_first_para(p))
        ptags = {t["slug"] for t in p.get("tags") or []} | _all_tags(ptext)
        score = 0.5 * _jac(w, pw) + 0.3 * _jac(tg, ptags) + 0.2 * _jac(g, _grams(ptext))
        shared = sorted(w & pw)
        if shared or (tg & ptags and _jac(g, _grams(ptext)) > 0.25):   # a shared tag alone is not similarity
            scored.append((score, p, shared))
    scored.sort(key=lambda x: -x[0])

    def show(rows):
        for s, p, shared in rows:
            sid = f"  [قصة: {p['story_id']}]" if p.get("story_id") else ""
            print(f"  {s:.2f}  {p['published_at'][:16].replace('T', ' ')}  {p['title'][:80]}{sid}\n"
                  f"        {p['file']}   مشترك: {'، '.join(shared[:8]) or '—'}")

    if story:
        same = sorted((p for p in posts if p.get("story_id") == story), key=lambda p: p["published_at"])
        print(f"\n■ أخبار القصة «{story}» (كل التواريخ): {len(same)}")
        for p in same:
            print(f"  {p['published_at'][:16].replace('T', ' ')}  {p['title'][:80]}\n        {p['file']}")
    week = [r for r in scored if r[0] >= 0.12 and datetime.fromisoformat(r[1]["published_at"]) >= now - timedelta(days=7)]
    print(f"\n■ مشابه في آخر 7 أيام: {len(week[:8])}")
    show(week[:8])
    older = [r for r in scored if r[0] >= 0.2 and r not in week]
    print(f"\n■ مشابه في الأرشيف كله (أقدم من 7 أيام): {len(older[:8])}")
    show(older[:8])
    stories = sorted({r[1]["story_id"] for r in scored[:10] if r[0] >= 0.12 and r[1].get("story_id")})
    if stories:
        print(f"\n■ قصص قائمة قد يتبعها الخبر: {'، '.join(stories)}   (python3 tools/monitor.py story <id>)")
    print("\n■ اختبار التطور الجوهري (مساعد، والقرار للمحرر):")
    for k, q in TEST:
        print(f"  [ ] {q}   ← {k}")
    print("  نعم لواحد من الثلاثة الأولى على الأقل ← تطور جوهري (خبر مستقل + follows + story_id + approved_by)\n"
          "  نعم للرابع وحده ← تحديث للخبر القائم، لا خبر جديد\n"
          "  الحدث نفسه دون جديد ← مكرر\n"
          "  الدرجات أعلاه مؤشر تشابه لا حكم: قد يتناول خبران الحدث نفسه بعنوانين مختلفين، فاقرأ المرشحين.")


def story(sid: str):
    posts = [p for p in _posts() if p.get("story_id") == sid]
    log = [e for e in _load_log() if str(e.get("story_id") or "") == sid]
    rows = [(p["published_at"][:16].replace("T", " "), "منشور", p["title"], p["file"]) for p in posts]
    rows += [(str(e.get("date"))[:16], AR.get(STATES.get(str(e.get("status")), ""), "؟"), str(e.get("title")),
              str(e.get("id"))) for e in log]
    print(f"مسار القصة «{sid}»:")
    for d, kind, t, ref in sorted(rows):
        print(f"  {d}  [{kind}]  {t[:80]}   ({ref})")


def validate() -> int:
    posts = _posts()
    files = {p["file"]: p for p in posts}
    errs, warns = [], []
    for p in posts:
        f = p.get("follows")
        if f:
            if f not in files:
                errs.append(f"{p['file']}: follows يشير إلى ملف غير موجود «{f}»")
            elif not p.get("story_id"):
                errs.append(f"{p['file']}: فيه follows دون story_id")
            elif files[f].get("story_id") != p["story_id"]:
                errs.append(f"{p['file']}: story_id «{p['story_id']}» يخالف قصة الخبر السابق «{files[f].get('story_id') or '—'}»")
            elif files[f]["published_at"] >= p["published_at"]:
                errs.append(f"{p['file']}: يتبع خبراً لاحقاً له «{f}»")
    ids = set()
    for e in _load_log():
        eid, where = str(e.get("id") or ""), f"{e['_file']} {e.get('id') or '(بلا id)'}"
        if not eid:
            errs.append(f"{where}: لا يوجد id")
        elif eid in ids:
            errs.append(f"{where}: id مكرر")
        ids.add(eid)
        st = STATES.get(str(e.get("status") or "").strip())
        if not st:
            errs.append(f"{where}: حالة غير معروفة «{e.get('status')}» (جديد / تطور جوهري / تحديث / مكرر)")
            continue
        test = {str(x).strip() for x in (e.get("test") or [])}
        for key in ("follows", "post"):
            v = str(e.get(key) or "").strip()
            if v and v not in files:
                errs.append(f"{where}: {key} يشير إلى ملف غير موجود «{v}»")
        if st == "major_development":
            for need in ("follows", "story_id", "approved_by"):
                if not e.get(need):
                    errs.append(f"{where}: التطور الجوهري يحتاج {need}")
            if not (test & MAJOR_KEYS):
                errs.append(f"{where}: لا «نعم» لأي من الأسئلة الثلاثة الأولى، فهو تحديث لا تطور جوهري")
        if st in ("update", "duplicate") and not e.get("follows"):
            errs.append(f"{where}: {AR[st]} يحتاج follows (الخبر القائم)")
        if st in ("new", "major_development") and e.get("post"):
            if not (e.get("verified") and e.get("archive_checked")):
                errs.append(f"{where}: نُشر دون verified و archive_checked")
            p = files.get(str(e["post"]))
            if p and st == "major_development" and p.get("follows") != e.get("follows"):
                warns.append(f"{where}: follows في الخبر المنشور يختلف عن السجل")
            if p and e.get("story_id") and p.get("story_id") != e.get("story_id"):
                warns.append(f"{where}: story_id في الخبر المنشور يختلف عن السجل")
    for m in errs:
        print("✗", m)
    for m in warns:
        print("⚠", m)
    print(f"أخطاء: {len(errs)}   تنبيهات: {len(warns)}")
    return 1 if errs else 0


def report(month: str = ""):
    log = [e for e in _load_log() if not month or str(e.get("date", "")).startswith(month)]
    counts = {}
    for e in log:
        k = AR.get(STATES.get(str(e.get("status")), ""), "غير معروف")
        counts[k] = counts.get(k, 0) + 1
    print(f"سجل الرصد {month or '(كل الأشهر)'}: {len(log)} مادة")
    for k in ("جديد", "تطور جوهري", "تحديث", "مكرر", "غير معروف"):
        if counts.get(k):
            print(f"  {k}: {counts[k]}")


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a or a[0] not in ("check", "story", "validate", "report"):
        print(__doc__)
        sys.exit(0)
    if a[0] == "check":
        sid = ""
        if "--story" in a:
            i = a.index("--story")
            sid = a[i + 1] if i + 1 < len(a) else ""
            a = a[:i] + a[i + 2:]
        check(a[1] if len(a) > 1 else "", a[2] if len(a) > 2 else "", sid)
    elif a[0] == "story":
        story(a[1] if len(a) > 1 else "")
    elif a[0] == "validate":
        sys.exit(validate())
    else:
        report(a[1] if len(a) > 1 else "")
