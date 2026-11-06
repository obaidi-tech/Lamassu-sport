"""Source type for hand-written posts: shown under each story so the reader can tell an original
source from an agency, a newspaper, a site that only relays someone else's report, or a reference work.

Types (the label shown is in LABELS):
  official   الجهة صاحبة الشأن: نادٍ، اتحاد، رابطة، لجنة، أو حساب رسمي
  agency     وكالة أنباء
  media      صحيفة أو موقع أو قناة
  relay      ناقل: موقع أعاد نشر خبر جهة أخرى (مثل «ذا أتلتيك عبر ياهو»)
  reference  مرجع: موسوعة أو قاعدة بيانات أو متحف

The type is guessed from the link's domain and the name; a manual override wins:
  - ذا أتلتيك | https://... | ناقل        (the third field is one of the Arabic labels or a key above)
"""
import re
from urllib.parse import urlparse

LABELS = {"official": "جهة رسمية", "agency": "وكالة أنباء", "media": "صحيفة أو موقع",
          "relay": "ناقل", "reference": "مرجع"}
_OVERRIDE = {"رسمي": "official", "رسمية": "official", "جهة رسمية": "official", "أصلي": "official",
             "وكالة": "agency", "وكالة أنباء": "agency",
             "صحيفة": "media", "صحفي": "media", "موقع": "media", "صحيفة أو موقع": "media", "قناة": "media",
             "ناقل": "relay", "مرجع": "reference", **{k: k for k in LABELS}}

_OFFICIAL_DOMAINS = (
    "uefa.com", "fifa.com", "the-afc.com", "cafonline.com", "concacaf.com", "conmebol.com",
    "olympics.com", "paralympic.org", "nba.com", "wnba.com", "nfl.com", "mlb.com", "nhl.com",
    "premierleague.com", "laliga.com", "legaseriea.it", "bundesliga.com", "ligue1.com", "spl.com.sa",
    "worldathletics.org", "fiba.basketball", "wada-ama.org", "tas-cas.org", "itftennis.com", "atptour.com",
    "wtatennis.com", "formula1.com", "fia.com", "uci.org", "fivb.com", "worldaquatics.com", "ihf.info",
    "thefa.com", "saff.com.sa", "qfa.qa", "uaefa.ae", "jfa.jp", "europa.eu",
    "realmadrid.com", "fcbarcelona.com", "liverpoolfc.com", "manutd.com", "mancity.com", "arsenal.com",
    "chelseafc.com", "tottenhamhotspur.com", "fcbayern.com", "bvb.de", "juventus.com", "acmilan.com",
    "inter.it", "psg.fr", "atleticodemadrid.com", "fenerbahce.org", "galatasaray.org", "alhilal.com",
    "alnassr.sa", "alittihad.club", "alahli.com",
)
_AGENCY_DOMAINS = ("reuters.com", "apnews.com", "afp.com", "dpa.com", "efe.com", "ansa.it", "aa.com.tr",
                   "spa.gov.sa", "wam.ae", "qna.org.qa", "kuna.net.kw", "bna.bh", "omannews.gov.om",
                   "petra.gov.jo", "mena.org.eg", "xinhuanet.com", "kyodonews.net", "pa.media")
_AGENCY_NAMES = ("رويترز", "reuters", "فرانس برس", "فرانس پرس", "afp", "أسوشيتد", "associated press",
                 "الأناضول", "anadolu", "د ب أ", "dpa", "إفي", "efe", "أنسا", "ansa", "واس", "وام", "قنا", "كونا")
_RELAY_DOMAINS = ("sports.yahoo.com", "news.yahoo.com", "msn.com", "news.google.com", "flipboard.com")
_REFERENCE_DOMAINS = ("wikipedia.org", "wikimedia.org", "britannica.com", "topendsports.com",
                      "transfermarkt", "worldfootball.net", "rsssf.org", "artuk.org", "museum",
                      "artsandculture.google.com", "footballheritage")


def _host(link: str) -> str:
    try:
        return (urlparse(link).hostname or "").lower()
    except ValueError:
        return ""


def override(note: str):
    """A note that is exactly a type label → that type, else None."""
    return _OVERRIDE.get((note or "").strip().lower()) or _OVERRIDE.get((note or "").strip())


def classify(name: str, link: str = "") -> str:
    n, h = (name or "").lower(), _host(link)
    on = lambda doms: any(h == d or h.endswith("." + d) or d in h for d in doms)  # noqa: E731
    if "(عبر" in n or " عبر " in n or on(_RELAY_DOMAINS):
        return "relay"
    if on(_REFERENCE_DOMAINS) or re.search(r"ويكيبيديا|wikipedia|موسوعة|متحف|museum", n):
        return "reference"
    if on(_AGENCY_DOMAINS) or any(re.search(r"(?<![\w])" + re.escape(a) + r"(?![\w])", n) for a in _AGENCY_NAMES):
        return "agency"
    if on(_OFFICIAL_DOMAINS) or "رسمي" in n or "official" in n:
        return "official"
    if h.endswith(".gov") or ".gov." in h:
        return "official"
    return "media"
