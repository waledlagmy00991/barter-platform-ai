# Legacy vision integrity audit, 22 November 2026

Status: WITHDRAWN AS PERFORMANCE EVIDENCE. Independent vision integrity review has completed. All historical vision scores are withdrawn as evidence of generalization or localization, not merely provisional. Training, harvesting and promotion remain blocked pending genuine data recovery. The deployed weights and legacy snapshot are preserved. See `INDEPENDENT_REVIEW_FOLLOWUP.md` and `independent_review_technical.json`. NER, pricing, RAG and backend quality were outside that independent review.

## Reproducible snapshot

`legacy62_v1/` preserves the existing 62 validation images and labels without correction. Its manifest records SHA-256 hashes, exact label text, available source rows and the deployed-weight hash. Supplier identity is explicitly unverified. This is a quarantined historical selection set, not a clean independent audit set. `integrity_audit.json` records the 260 training examples and their hashes as well. Run `python vision/audit_integrity.py` from the repository root to verify snapshot and weight hashes and regenerate the inventory without evaluating weights.

## Exact 60-to-62 transition

Comparing unique `(class, filename)` pairs in `split_v1.json` at cdd8e0c (also unchanged at f055f40 and 8fbc1ff) with ddba5ab:

- Added `brick_white/brick_white_eg_48bae6ff.jpg`.
- Added `copper_scrap/copper_scrap_eg_e1eaa795.jpg`.
- Relabeled `aluminum_shavings_eg_db1a10e3.jpg` from copper_scrap to copper_red, retaining validation membership.
- No other unique validation member changed. In particular, no brick_red image was removed in this transition.

The previous explanation of brick_red erosion from ten to five confused duplicated manifest entries with unique files and is withdrawn. At cdd8e0c the manifest listed 107 entries but contained only 60 unique examples. At ddba5ab it listed 62 entries, all unique. The counting fix alone does not explain the increase in unique examples; the two additions do. Earlier changes from the 55-image set are enumerated in the JSON history.

## Confirmed failures

- Four identical source-page identifiers occur in both train and validation. The split was assigned within classes, not globally, and later class changes and harvesting did not preserve source-level separation.
- Ten source domains occur on both sides. A domain is not a supplier identity. This is a review signal, not proof that all photos from the domain share a supplier.
- Eight active filenames have no exact provenance filename match. Four have possible same-suffix records under previous class prefixes, which must be verified by file/history evidence before being treated as recovered provenance.
- Six byte-identical training-image pairs have conflicting wood_swed/wood_zan labels.
- There is no byte-identical image across the current training and validation inventories. That check does not rule out near duplicates, common suppliers or model-training contamination.
- Active Commons images include sources explicitly naming non-Egyptian locations. The Egyptian-only claim is withdrawn. Source-page presence and a filename ending in `_eg_` do not establish Egyptian-market relevance or commercial reuse rights.
- The selection set has already been inspected and used across multiple candidates. Repairing its bookkeeping cannot make it an untouched final test.

## Metric status

The historical 0.944, 0.8847 and 0.8678 mAP@50 figures are provisional internal full-image-box results on changing, compromised selection sets. None is a stable production promotion gate. The deployed file remains unchanged. Historical JSON entries are retained as evidence, not endorsements. The train7 candidate was not promoted.

## Continuation

Preserve this snapshot separately from remediation. Resolve ambiguous provenance, quarantine unsupported-origin files and conflicting labels, establish source/supplier group identities with evidence, and create a versioned global split only after independent review. Do not certify the corrected data as production-valid based on an internal check alone. Thursday 26 November is a discussion checkpoint, not the end of the production-readiness assignment. Real remaining blockers must be reported and continuation retained.
