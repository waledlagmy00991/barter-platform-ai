# -*- coding: utf-8 -*-
"""
Build the semantic-search index (embeddings + FAISS vector DB).

- Model: sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
  (multilingual, handles Egyptian Arabic).
- Each ad is embedded from a search view: text + structured fields.
- Index: faiss.IndexFlatIP over L2-normalized vectors (cosine similarity).

Output: chatbot/index/ads.faiss + chatbot/index/ads_meta.json
"""
import json
import sys
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).parent
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


def search_view(ad):
    return (f"{ad['text']} | {ad['material']} {ad['quantity']} {ad['unit']} "
            f"{ad['location']} {ad['condition']} "
            f"{ad['total_price_egp']} جنيه")


def main():
    ads = [json.loads(l) for l in
           open(ROOT / "data" / "ads.jsonl", encoding="utf-8")]
    model = SentenceTransformer(MODEL_NAME)
    embs = model.encode([search_view(a) for a in ads],
                        normalize_embeddings=True, show_progress_bar=True)
    embs = np.asarray(embs, dtype="float32")
    index = faiss.IndexFlatIP(embs.shape[1])
    index.add(embs)
    out = ROOT / "index"
    out.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(out / "ads.faiss"))
    with open(out / "ads_meta.json", "w", encoding="utf-8") as f:
        json.dump({"model": MODEL_NAME, "n": len(ads), "ads": ads}, f,
                  ensure_ascii=False)
    print("indexed", len(ads), "ads, dim", embs.shape[1])


if __name__ == "__main__":
    main()
