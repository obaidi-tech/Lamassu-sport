"""Checks for the smarter Commons search and the image bank:  python tests/test_bank.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from newsroom.bank import load_bank, pick       # noqa: E402
from newsroom.commons import pick_best          # noqa: E402

fails = 0


def check(name, cond):
    global fails
    print(("PASS  " if cond else "FAIL  ") + name)
    fails += 0 if cond else 1


C = lambda t, w, h, lic="CC BY-SA 4.0", d="", r=1: {"title": t, "width": w, "height": h, "license": lic, "date": d, "rank": r}  # noqa: E731
cands = [C("File:Team 1910.jpg", 2000, 1300, "Public domain", r=1), C("File:Portrait.jpg", 1400, 2100, r=2),
         C("File:Small.jpg", 800, 450, r=3), C("File:Getty.jpg", 3000, 1690, "All rights reserved", r=4),
         C("File:Match 2024.jpg", 2400, 1350, d="2024-05-01", r=5)]
check("search skips old, portrait, small and non-free photos", pick_best(cands) == "File:Match 2024.jpg")
check("search returns nothing when only portraits exist", pick_best([C("File:P.jpg", 1400, 2100)]) == "")
check("search-old accepts a historic photo", pick_best([C("File:Team 1910.jpg", 2000, 1100, "Public domain")], old_ok=True) == "File:Team 1910.jpg")

bank = load_bank(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "image_bank.yaml"))
check("bank loads", len(bank) >= 20)
cases = {"كري يقود ووريورز لعودة": "warriors", "وفاز مانشستر سيتي على لايبزيغ": "man-city",
         "كومو يكتب التاريخ.. وفوز أرسنال": "como", "بالهلال يحتفل": "al-hilal",
         "أوكلاهوما سيتي ثاندر يفوز": None, "نيوكاسل يونايتد يتعادل": None, "الاتحاد الدولي يقرر": None,
         "الهلال الأحمر يشارك": None, "إنتر ميامي يتعاقد": None, "الاتحاد السعودي لكرة القدم يعلن": None}
for t, want in cases.items():
    e = pick(bank, t)
    check(f"bank: «{t}» → {want}", (e and e["id"]) == want)
check("bank by id", (pick(bank, "أي عنوان", want="nba") or {}).get("id") == "nba")
ids = [e["id"] for e in bank]
check("bank ids are unique", len(ids) == len(set(ids)))
from newsroom.posts import _getty  # noqa: E402
code = ("<a id='Ab3dEf_9xQrStUvW' class='gie-single' href='http://www.gettyimages.com/detail/2201234567'>Embed from Getty Images</a>"
        "<script>gie(function(){gie.widgets.load({id:'Ab3dEf_9xQrStUvW',sig:'kq1Zx0Yw9Vt8Us7Tr6Qp5On4Ml3Kj2Ih1Gf0Ed9Cb8A=',"
        "w:'594px',h:'396px',items:'2201234567',caption: true ,tld:'com',is360: false })});</script>")
g = _getty(code)
check("getty: official embed code is read", g.get("item") == "2201234567" and g.get("w") == 594)
check("getty: anything else is refused", _getty("<script>alert(1)</script>") == {} and _getty("id:'x\"><b>',sig:'y',items:'1'") == {})
from newsroom.posts import _lenient_meta  # noqa: E402
m = _lenient_meta("title: عنوان: مع نقطتين\ngetty: |\n  " + code + "\nrelated:\n  - a.md")
check("getty: works even when the header has a ':' in a value", _getty(m.get("getty")).get("item") == "2201234567" and m.get("related") == ["a.md"])
from datetime import date  # noqa: E402
from newsroom.live import _match_id  # noqa: E402
check("live: match number read from Sofascore's embed code", _match_id('<iframe src="https://widgets.sofascore.com/en/embed/liveResult?id=16363919&widgetTheme=light">') == "16363919")
check("live: anything else is refused", _match_id("<script>alert(1)</script>") == "" and _match_id("javascript:1") == "")
from newsroom import srckind  # noqa: E402
from newsroom.posts import _sources  # noqa: E402
check("source type: agency by name, not «قناة»", srckind.classify("رويترز") == "agency" and srckind.classify("قناة العربية") == "media")
check("source type: club site is official", srckind.classify("ليفربول", "https://www.liverpoolfc.com/news/x") == "official")
check("source type: 'via' is a relay", srckind.classify("ذا أتلتيك (عبر ياهو سبورتس)", "https://sports.yahoo.com/a") == "relay")
check("source type: Wikipedia is a reference", srckind.classify("ويكيبيديا", "https://en.wikipedia.org/wiki/X") == "reference")
s1 = _sources(["موقع ما | https://example.com/x | ناقل"])[0]
check("source type: manual override wins and is not shown as a note", s1["kind"] == "relay" and s1["note"] == "")
print(f"\n{fails} failed" if fails else "\nall passed")
sys.exit(1 if fails else 0)
