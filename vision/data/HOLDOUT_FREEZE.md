# Frozen holdout (corrected, 2026-11-22)

data/yolo3/val (60 images, built from data/split_v1.json after the
2026-11-22 data-quality corrections) is FROZEN as the promotion gate.

Baseline: deployed v4 weights score mAP@50 = 0.8847 (P 0.831, R 0.813).
A candidate is promoted only if it beats 0.8847 on this exact set via val2.py/valc.py.

Rules:
- No repeated candidate selection against this set (evaluate each candidate once).
- New harvested images go to the train side only.
- Any future correction to this set must be logged in results/metrics.json
  with reason, and the baseline re-measured and disclosed.
