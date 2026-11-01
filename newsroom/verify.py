"""Post-writing checks: every number in the article must exist in the sources; basic quality gates."""
from datetime import datetime

from .textutil import has_keyword, normalize, numbers
from .writer import source_text


def check_article(art: dict, c: dict, rules: dict) -> list:
    problems = []
    text = " ".join([art.get("title", ""), art.get("excerpt", "")] + art.get("body", []))
    if art.get("_stub"):
        return [art.get("review_reason", "مسودة")]

    allowed = numbers(source_text(c))
    allowed |= numbers(" ".join(rules.get("glossary", {}).keys()))   # e.g. "Formula 1"
    y = datetime.now().year
    allowed |= {str(y - 1), str(y), str(y + 1)}
    invented = sorted(numbers(text) - allowed)
    if invented:
        problems.append("أرقام غير موجودة في المصادر: " + "، ".join(invented[:6]))

    words = len(" ".join(art.get("body", [])).split())
    if words < 40:
        problems.append(f"النص قصير جداً ({words} كلمة)")
    if not art.get("title") or len(art["title"].split()) > 18:
        problems.append("العنوان مفقود أو طويل")
    if art.get("needs_review"):
        problems.append("النموذج طلب المراجعة: " + (art.get("review_reason") or "دون سبب"))
    if art.get("confidence") == "low":
        problems.append("ثقة منخفضة")
    hit = has_keyword(normalize(text), rules.get("sensitive_keywords", []))
    if hit:
        problems.append(f"النص يتناول موضوعاً حساساً ({hit})")
    return problems
