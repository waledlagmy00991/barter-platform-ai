# Holdout policy (corrected, 2026-11-22)

## Promotion gate (in use)
data/yolo3/val (60 images, from data/split_v1.json after the 2026-11-22
data-quality corrections). Baseline: deployed v4 weights mAP@50 = 0.8678 (re-measured 2026-11-22 after val erosion from duplicate cleanup was logged; see results/metrics.json v7_holdout_rebased).
Each candidate is evaluated on it once; a candidate is promoted only if it
beats 0.8678. Note: even one-evaluation-per-candidate adaptively reuses this
set across candidates, so it is NOT sufficient for a production claim.

## Final audit set (untouched)
data/audit/ is reserved for a genuinely untouched final audit:
- New harvests for weak classes route ~20% of kept images (whole supplier
  groups, never split) into data/audit/<class>/ instead of raw2.
- Audit images are never trained on, never used for candidate selection,
  and evaluated exactly once, at the production-readiness audit.
- build_dataset3.py only globs data/raw2, so audit images are excluded
  by construction.

## Rules
- New harvested training images go to the train side of split_v1.json only.
- Any correction to the promotion set must be logged in results/metrics.json
  with reason, and the baseline re-measured and disclosed.
