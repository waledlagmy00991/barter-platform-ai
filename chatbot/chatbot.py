# -*- coding: utf-8 -*-
"""
Semantic search + RAG chatbot for the barter platform.

- البحث الدلالي: يفهم المعنى مش الحروف. "محتاج خشب للفرش" يلاقي إعلانات
  خشب الزان والسويد حتى لو الكلمة نفسها مش موجودة.
- RAG: يرجّع أقرب الإعلانات (retrieval) ويجاوب منها ببياناتها الحقيقية -
  مفيش هلوسة، كل رقم في الرد جاي من إعلان مسجل. لو الإعلان المطلوب مش
  موجود، يقترح أقرب بدائل (زي ما الوثيقة طالبة).
- LLM اختياري: لو GEMINI_API_KEY موجود، الرد يتصاغ بيه؛ من غيره بنستخدم
  صياغة جاهزة منظمة (deterministic) فالنظام شغال offline بالكامل.

    from chatbot.chatbot import ask
    ask("عايز ٢٠ طن حديد في العاشر")
"""
import json
import os
import sys
from pathlib import Path

import faiss
import numpy as np

ROOT = Path(__file__).parent
REPO = ROOT.parent
sys.path.insert(0, str(REPO))

_model = None
_index = None
_ads = None


def _load():
    global _model, _index, _ads
    if _model is None:
        from sentence_transformers import SentenceTransformer
        meta = json.load(open(ROOT / "index" / "ads_meta.json",
                              encoding="utf-8"))
        _ads = meta["ads"]
        _model = SentenceTransformer(meta["model"])
        _index = faiss.read_index(str(ROOT / "index" / "ads.faiss"))
    return _model, _index, _ads


def search(query, k=5):
    model, index, ads = _load()
    q = model.encode([query], normalize_embeddings=True)
    scores, ids = index.search(np.asarray(q, dtype="float32"), k)
    out = []
    for s, i in zip(scores[0], ids[0]):
        if i < 0:
            continue
        ad = dict(ads[int(i)])
        ad["score"] = round(float(s), 4)
        out.append(ad)
    return out


def _format_ad(ad):
    return ("إعلان #{id}: {text} — الخامة: {material} ({condition})، "
            "الكمية: {quantity} {unit}، المكان: {location}، "
            "السعر المطلوب: {total_price_egp:,} جنيه "
            "(العادل ~{fair_total_price_egp:,})").format(**ad)


def answer_with_template(query, matches):
    if not matches or matches[0]["score"] < 0.35:
        return ("للأسف مفيش إعلانات قريبة من طلبك على المنصة حاليا. "
                "سجّل طلبك وهننبهك أول ما حاجة مناسبة تنزل.")
    lines = [f"لقيت {len(matches)} إعلان قريب من طلبك:"]
    lines += ["- " + _format_ad(m) for m in matches]
    best = matches[0]
    lines.append(
        f"أقرب واحد ليك: #{best['id']} في {best['location']} "
        f"بسعر {best['total_price_egp']:,} جنيه.")
    return "\n".join(lines)


def answer(query, k=5):
    """Full RAG answer: retrieve -> compose from retrieved facts only."""
    matches = search(query, k=k)
    if os.environ.get("GEMINI_API_KEY"):
        try:
            return _answer_with_gemini(query, matches), matches
        except Exception:
            pass
    return answer_with_template(query, matches), matches


def _answer_with_gemini(query, matches):
    import urllib.request
    key = os.environ["GEMINI_API_KEY"]
    context = "\n".join(_format_ad(m) for m in matches) or "لا توجد إعلانات"
    prompt = (
        "انت مساعد ذكي في منصة مقايضة مواد خام B2B في مصر. "
        "جاوب التاجر بالعامية المصرية بناءً على الإعلانات دي بس، "
        "متحطش أي رقم مش موجود فيها. لو مفيش حاجة مناسبة اقترح أقرب بديل.\n\n"
        f"الإعلانات:\n{context}\n\nطلب التاجر: {query}\nالرد:")
    req = urllib.request.Request(
        "https://generativelanguage.googleapis.com/v1beta/models/"
        "gemini-2.0-flash:generateContent?key=" + key,
        data=json.dumps({"contents": [{"parts": [{"text": prompt}]}]}
                        ).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as f:
        data = json.load(f)
    return data["candidates"][0]["content"]["parts"][0]["text"]


def ask(query, k=5):
    text, _ = answer(query, k=k)
    return text


if __name__ == "__main__":
    print(ask(" ".join(sys.argv[1:]) or "عايز ٢٠ طن حديد في العاشر"))
