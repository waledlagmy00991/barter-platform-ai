# -*- coding: utf-8 -*-
"""
Train the SpaCy NER model on Egyptian-dialect trader ads.

- Base: spacy.blank("ar") (Arabic tokenizer) + a `ner` component.
- Labels: MATERIAL, QUANTITY, LOCATION.
- Training: minibatched with dropout, dev-set evaluation each epoch,
  best model kept (model-best style).
- Output: ner/model/ (loadable with spacy.load) and
  ner/results/metrics.json with real precision/recall/F1 per split.

Run:  python train.py [--epochs 30] [--dropout 0.2]
"""
import argparse
import json
import random
import warnings
from pathlib import Path

import spacy
from spacy.scorer import Scorer
from spacy.tokens import DocBin
from spacy.training import Example
from spacy.util import minibatch, compounding

ROOT = Path(__file__).parent
LABELS = ["MATERIAL", "QUANTITY", "LOCATION"]


def load_jsonl(path):
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def rows_to_examples(nlp, rows, scorer_examples=False):
    examples = []
    for r in rows:
        doc = nlp.make_doc(r["text"])
        ents = [(s, e, l) for s, e, l in r["entities"]]
        spans = [doc.char_span(s, e, label=l) for s, e, l in ents]
        doc.ents = [sp for sp in spans if sp is not None]
        examples.append(Example(doc, doc))
    return examples


def score(nlp, rows):
    scorer = Scorer(nlp)
    examples = []
    for r in rows:
        pred = nlp(r["text"])
        ref = nlp.make_doc(r["text"])
        spans = [ref.char_span(s, e, label=l) for s, e, l in r["entities"]]
        ref.ents = [sp for sp in spans if sp is not None]
        examples.append(Example(pred, ref))
    return scorer.score(examples)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=30)
    ap.add_argument("--dropout", type=float, default=0.2)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--init-from", type=str, default=None,
                    help="warm start from a saved model dir")
    args = ap.parse_args()

    random.seed(42)
    train_rows = load_jsonl(ROOT / "data" / "train.jsonl")
    dev_rows = load_jsonl(ROOT / "data" / "dev.jsonl")
    test_rows = load_jsonl(ROOT / "data" / "test.jsonl")

    if args.init_from:
        nlp = spacy.load(args.init_from)
        ner = nlp.get_pipe("ner")
    else:
        nlp = spacy.blank("ar")
        ner = nlp.add_pipe("ner")
        for label in LABELS:
            ner.add_label(label)

    train_examples = rows_to_examples(nlp, train_rows)

    model_dir = ROOT / "model"
    best_f = -1.0
    if args.init_from:
        best_f = score(nlp, dev_rows)["ents_f"]
    best_state = None
    history = []
    if args.init_from:
        optimizer = nlp.resume_training()
    else:
        optimizer = nlp.initialize(lambda: train_examples)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for epoch in range(args.epochs):
            random.shuffle(train_examples)
            losses = {}
            batches = minibatch(train_examples,
                                size=compounding(4.0, args.batch, 1.001))
            for batch in batches:
                nlp.update(batch, sgd=optimizer, drop=args.dropout,
                           losses=losses)
            dev_scores = score(nlp, dev_rows)
            f = dev_scores["ents_f"]
            history.append({"epoch": epoch + 1,
                            "train_loss": losses.get("ner", 0.0),
                            "dev_ents_f": f,
                            "dev_ents_p": dev_scores["ents_p"],
                            "dev_ents_r": dev_scores["ents_r"]})
            print(f"epoch {epoch+1:02d} loss={losses.get('ner',0):.3f} "
                  f"dev F={f:.4f}")
            if f > best_f:
                best_f = f
                best_state = nlp.to_bytes()
                # checkpoint the best model to disk after every epoch
                if model_dir.exists():
                    import shutil
                    shutil.rmtree(model_dir)
                nlp.to_disk(model_dir)

    if best_state is not None:
        nlp.from_bytes(best_state)
        if model_dir.exists():
            import shutil
            shutil.rmtree(model_dir)
        nlp.to_disk(model_dir)
    else:
        nlp = spacy.load(model_dir)

    # Final evaluation with the saved best model
    best_nlp = spacy.load(model_dir)
    results = {"labels": LABELS,
               "n_train": len(train_rows), "n_dev": len(dev_rows),
               "n_test": len(test_rows),
               "epochs": args.epochs, "dropout": args.dropout,
               "history": history, "splits": {}}
    for name, rows in [("dev", dev_rows), ("test", test_rows)]:
        s = score(best_nlp, rows)
        per = {l: {"p": v["p"], "r": v["r"], "f": v["f"]}
               for l, v in s["ents_per_type"].items()}
        results["splits"][name] = {
            "ents_p": s["ents_p"], "ents_r": s["ents_r"],
            "ents_f": s["ents_f"], "per_type": per}
    def _py(o):
        try:
            import numpy as np
            if isinstance(o, np.generic):
                return o.item()
        except Exception:
            pass
        return o
    out = ROOT / "results" / "metrics.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=_py)
    print("TEST  P={:.4f} R={:.4f} F={:.4f}".format(
        results["splits"]["test"]["ents_p"],
        results["splits"]["test"]["ents_r"],
        results["splits"]["test"]["ents_f"]))
    print("per-type test:", json.dumps(
        results["splits"]["test"]["per_type"], ensure_ascii=False))


if __name__ == "__main__":
    main()
