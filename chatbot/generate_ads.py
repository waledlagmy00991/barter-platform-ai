# -*- coding: utf-8 -*-
"""
Build the ads corpus used by the semantic search + RAG chatbot.

Data provenance: the ad records are generated from the same vocabularies
as the NER training data (see ner/generate_data.py) and priced with the
trained pricing model, so the chatbot's data matches what the other
models understand. Fields: id, text, material, quantity, unit, location,
condition, total_price_egp, fair_total_price_egp.

Output: chatbot/data/ads.jsonl
"""
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "ner"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "pricing"))

from generate_data import build_sentence  # noqa: E402  (ner generator)
from integration.pipeline import map_material, parse_quantity  # noqa: E402
from pricing.predict import fair_price  # noqa: E402

random.seed(99)
OUT = Path(__file__).parent / "data"
OUT.mkdir(parents=True, exist_ok=True)


def main(n=600):
    seen, ads = set(), []
    while len(ads) < n:
        text, ents = build_sentence()
        if text in seen:
            continue
        seen.add(text)
        d = {l: text[s:e] for s, e, l in ents}
        mat_raw = d.get("MATERIAL")
        if not mat_raw:
            continue
        material, _ = map_material(mat_raw)
        qty, unit = parse_quantity(d.get("QUANTITY", "")) \
            if d.get("QUANTITY") else (None, None)
        if not material or not qty:
            continue
        condition = "مستعمل" if any(w in text for w in
                                    ("مستعمل", "صدأ", "هالك")) else "جديد"
        loc = d.get("LOCATION", "القاهرة")
        fair_unit = fair_price(material, condition, loc, qty)
        ask_total = round(fair_unit * qty * random.uniform(0.85, 1.25))
        ads.append({
            "id": len(ads) + 1, "text": text, "material": material,
            "material_raw": mat_raw, "quantity": qty, "unit": unit,
            "location": loc, "condition": condition,
            "total_price_egp": ask_total,
            "fair_total_price_egp": round(fair_unit * qty),
        })
    with open(OUT / "ads.jsonl", "w", encoding="utf-8") as f:
        for a in ads:
            f.write(json.dumps(a, ensure_ascii=False) + "\n")
    print("ads:", len(ads))


if __name__ == "__main__":
    main()
