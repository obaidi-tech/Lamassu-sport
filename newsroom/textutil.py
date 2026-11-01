"""Text helpers: normalization, tokens, keyword matching, numbers."""
import html
import re

_TASHKEEL = re.compile(r"[ؐ-ًؚ-ٰٟۖ-ۭـ]")
_TAGS = re.compile(r"<[^>]+>")
_PUNCT = re.compile(r"[^\w\s]", re.UNICODE)
_AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")

STOPWORDS = set("""
a an the and or but of to in on at for from by with as is are was were be been has have had
it its this that these those after before over under into about than then their his her they
he she we you i not no yes will would can could should may might new says said say after amid
vs v against during while who what when where how why up down out off more most first last
في من على إلى الى عن مع بعد قبل هذا هذه ذلك التي الذي الذين كان كانت يكون أن ان إن او أو ثم
لم لن قد ما لا كما عند حتى بين خلال ضد وفق عبر حول منذ أمام امام فيه فيها له لها هو هي
""".split())


def clean_html(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", html.unescape(_TAGS.sub(" ", text))).strip()


def normalize(text: str) -> str:
    t = (text or "").lower().translate(_AR_DIGITS)
    t = _TASHKEEL.sub("", t)
    t = re.sub("[أإآ]", "ا", t).replace("ة", "ه").replace("ى", "ي")
    return t


def tokens(text: str) -> set:
    t = _PUNCT.sub(" ", normalize(text))
    out = set()
    for w in t.split():
        if w.startswith("ال") and len(w) > 4:   # strip Arabic definite article
            w = w[2:]
        if len(w) >= 3 and w not in STOPWORDS and not w.isdigit():
            out.add(w)
    return out


_LABEL = re.compile(r"^\s*(report|update|updated|watch|live|video|breaking|exclusive|analysis|"
                    r"عاجل|فيديو|تقرير|بالفيديو)\s*[:|\-–—]\s*", re.I)


def strip_label(title: str) -> str:
    """Drop 'Report:' / 'Watch:' / 'عاجل:' style labels from the start of a headline."""
    return _LABEL.sub("", title or "").strip()


def strip_publisher_suffix(title: str):
    """Google News titles look like 'Headline - Publisher'. Returns (headline, publisher|None)."""
    m = re.match(r"^(.*\S)\s+[-–—]\s+([^-–—]{2,60})$", title or "")
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return (title or "").strip(), None


def _kw_regex(kw: str):
    kw = kw.strip()
    if re.fullmatch(r"[\x00-\x7f]+", kw):
        return re.compile(r"(?<![a-z0-9])" + re.escape(normalize(kw)) + r"(?![a-z0-9])")
    return re.compile(re.escape(normalize(kw)))


_KW_CACHE = {}


def has_keyword(text_norm: str, keywords) -> str | None:
    """Return the first keyword found in already-normalized text, else None."""
    for kw in keywords or []:
        rx = _KW_CACHE.get(kw)
        if rx is None:
            rx = _KW_CACHE[kw] = _kw_regex(kw)
        if rx.search(text_norm):
            return kw
    return None


def numbers(text: str) -> set:
    """Numbers appearing in text (digits normalized), e.g. scores, years, fees."""
    t = (text or "").translate(_AR_DIGITS)
    return {n.replace(",", "") for n in re.findall(r"\d+(?:[.,]\d+)?", t)}
