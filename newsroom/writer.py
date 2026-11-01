"""Turn a selected story into an Arabic article with an LLM (Claude API), from source facts only."""
import json
import os
import re

import requests

API_URL = "https://api.anthropic.com/v1/messages"

STYLE = """أنت محرر أخبار رياضية في موقع "{site}". تكتب بالعربية الفصحى الواضحة، بأسلوب خبري محايد.

قواعد ملزمة:
1. اكتب فقط ما ورد في المواد المقدمة. لا تضف أرقاماً أو تواريخ أو أسماء أو تصريحات غير موجودة فيها.
2. لا تنسخ جمل المصادر. أعد الصياغة بالكامل بكلماتك، ولا تقتبس أكثر من جملة قصيرة واحدة بين علامتي تنصيص إن لزم.
3. انسب كل معلومة لمصدرها بصيغة "بحسب وكالة رويترز" أو "أعلن الاتحاد الدولي...".
4. إن كانت المادة شائعة أو غير مؤكدة، فاذكر ذلك صراحة ("لم يصدر تأكيد رسمي").
5. لا تبدِ رأياً ولا تستخدم مبالغات.
6. استخدم هذه الصيغ الثابتة للأسماء: {glossary}
7. العنوان: 6 إلى 12 كلمة، دقيق وغير مضلل.
"""

NEWS_TASK = """اكتب خبراً من المواد التالية (فئة: {category}).
الطول: {length} كلمة تقريباً، في 2 إلى 4 فقرات.

المواد:
{materials}

أعد JSON فقط بهذا الشكل:
{{"title": "...", "excerpt": "جملة واحدة تلخص الخبر", "body": ["فقرة", "فقرة"], "tags": ["وسم", "وسم"],
  "confidence": "high|medium|low", "needs_review": false, "review_reason": ""}}
ضع needs_review=true إن كانت المواد متناقضة أو غير كافية أو حساسة."""

OPINION_TASK = """هذه مقالة رأي. لا تعِد كتابتها، بل اكتب ملخصاً قصيراً (70 إلى 110 كلمات) يعرض فكرتها الرئيسية
بصيغة "يرى الكاتب..." مع نسبتها لكاتبها ومصدرها. لا تنقل جملاً من النص.

الكاتب: {author}
المصدر: {publisher}
العنوان: {title}
المقدمة المتاحة: {summary}

أعد JSON فقط:
{{"title": "عنوان يذكر اسم الكاتب أو فكرته", "excerpt": "...", "body": ["فقرة الملخص"], "tags": [],
  "confidence": "high|medium|low", "needs_review": false, "review_reason": ""}}"""


def _materials(c: dict, limit: int = 6) -> str:
    rows = []
    for i, m in enumerate(c["items"][:limit], 1):
        rows.append(f"[{i}] الناشر: {m['publisher']} ({m['kind']}) | التاريخ: {m['published'][:16]}\n"
                    f"العنوان: {m['title']}\nالملخص: {m['summary'][:700]}")
    return "\n\n".join(rows)


def _parse_json(text: str) -> dict:
    s, e = text.find("{"), text.rfind("}")
    if s < 0 or e < 0:
        raise ValueError("no JSON in model output")
    return json.loads(text[s:e + 1])


def call_claude(system: str, prompt: str, cfg: dict) -> str:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set")
    r = requests.post(API_URL, timeout=90, headers={
        "x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json",
    }, json={
        "model": cfg["model"], "max_tokens": cfg.get("max_tokens", 1400),
        "temperature": cfg.get("temperature", 0.3), "system": system,
        "messages": [{"role": "user", "content": prompt}],
    })
    r.raise_for_status()
    return "".join(b.get("text", "") for b in r.json()["content"] if b.get("type") == "text")


def write_article(c: dict, site: dict, rules: dict, cat_name: str, use_llm: bool = True) -> dict:
    glossary = "، ".join(f"{k} = {v}" for k, v in rules.get("glossary", {}).items())
    system = STYLE.format(site=site["site_name"], glossary=glossary)
    lead = c["lead"]
    if c["category"] == "opinion":
        prompt = OPINION_TASK.format(author=lead.get("author") or "غير مذكور", publisher=lead["publisher"],
                                     title=lead["title"], summary=lead["summary"][:900])
    else:
        length = 220 if len(c["items"]) >= 3 else 150
        prompt = NEWS_TASK.format(category=cat_name, length=length, materials=_materials(c))

    if not use_llm:
        return _stub(c)
    raw = call_claude(system, prompt, site["llm"])
    art = _parse_json(raw)
    art["body"] = [p.strip() for p in art.get("body", []) if p and p.strip()]
    return art


def _stub(c: dict) -> dict:
    """No-LLM mode: an untranslated draft so the whole pipeline can be tested for free."""
    lead = c["lead"]
    return {
        "title": lead["title"],
        "excerpt": lead["summary"][:200],
        "body": [f"[مسودة دون صياغة] {m['publisher']}: {m['title']}. {m['summary'][:300]}" for m in c["items"][:3]],
        "tags": [],
        "confidence": "low",
        "needs_review": True,
        "review_reason": "تشغيل تجريبي دون نموذج لغوي",
        "_stub": True,
    }


def source_text(c: dict) -> str:
    return " ".join(m["title"] + " " + m["summary"] + " " + m["published"][:10] for m in c["items"])


def strip_html(s: str) -> str:
    return re.sub(r"<[^>]+>", "", s or "")
