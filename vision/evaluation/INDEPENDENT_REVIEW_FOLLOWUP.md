# Independent review follow-up, 22 November 2026

## Decision

Every historical vision score is withdrawn as evidence of generalization or object localization. This is a withdrawal, not a provisional production gate. There is no clean approved training pool and no valid current performance estimate. All vision execution remains fail-closed. The preserved legacy snapshot and deployed weights are unchanged.

Checkpoint metadata establishes dataset2 lineage for the deployed weights. Forty-six of the 62 later selection images match retained dataset2 training image bytes. The retained directory is not itself a signed historical batch manifest, but this caveat does not rescue the evaluation. The selection set also has cross-split source and perceptual duplication, unsupported-origin files, label conflicts and adaptive reuse.

All historical labels are full-image boxes. Their detector mAP values are whole-image classification through a detector interface, not evidence of object localization. A genuine detection task needs object-level boxes and appropriate detection evaluation. A whole-image material-classification task needs reviewed class labels and classification metrics, with explicit rejection/abstention behavior.

## Added confirmed defects

The following pairs show the same underlying photograph despite encoding or crop differences:

- Validation plastic_shredded_eg_5df2bbfb versus training plastic_pet_eg_60702087.
- Validation plastic_jerrican_os001 versus training plastic_jerrican_os007.
- Validation plastic_jerrican_os002 versus training plastic_jerrican_os005.

The paired pixels were inspected and are preserved in `visual_evidence/cross_split_duplicates.png`; exact filenames and hashes are in `review_followup.json`. The first pair also has inconsistent material labels. These records remain quarantined; no relabeling or training was performed.

Recovering the cement filename aliases adds the fifth shared source page, the Almasry Alyoum article ending `/news/details/4416737`, linking cement_bags training a6b617e3 and validation 4b7d281e. Original-byte reconstruction verifies the URL linkage, not label validity, locality, supplier identity or usage rights.

## Visual evidence for renamed files

`visual_evidence/recovered_label_review.png` now records a fresh internal inspection of the four original-byte-linked renamed images. Two show cement bags, one shows bundled ribbed round steel bars, and the image currently labeled steel_sheet shows thick square/rectangular steel stock rather than a thin sheet. Its current label is unsupported and requires taxonomy/subject review, not another silent relabel.

This fresh internal visual record does not retrospectively prove the original changes were independently reviewed and does not certify production labels. No legacy image or label was changed.

## Source-component count reconciliation

Recomputing the same 322 records gives:

| Filename-based source evidence | URL normalization | Components |
|---|---|---:|
| Original exact filename matches only | No | 150 |
| Original exact filename matches only | Yes | 150 |
| Plus four original-byte-verified rename aliases | No | 146 |
| Plus four original-byte-verified rename aliases | Yes | 146 |

The four-component difference is caused by recovered provenance aliases, not URL normalization. Reproducible variant output is in `grouping_reconciliation.json`. These counts merge exact image hashes and source pages only. Confirmed perceptual duplicates remain explicit exclusion constraints; this historical bookkeeping count does not include additional visual-link merges. No component count is proof of supplier identity or independence, and none may be used to authorize a new split.

## Recovery criteria

- Keep the legacy set forensic/regression-only. Repair, renaming or a new random split cannot make it untouched evaluation data.
- Obtain genuinely new Egyptian-market images with evidence of origin and rights that cover the intended use. Do not infer origin or rights from a domain, filename or article location.
- Establish source and supplier groups with evidence before splitting globally across classes. Treat uncertain linkage conservatively.
- Define the actual task before labeling: whole-image material classification, object localization and visual condition recognition are different tasks. New/used/rust requires its own ground truth, not a rollup from material classes.
- Independently review labels, freeze a new audit set before candidate development, define business-relevant acceptance and abstention criteria, and measure only after data and rights criteria are met.
- Do not start expensive training or claim performance merely because local guards, hash checks or regression tests pass.

The Friday discussion remains a checkpoint. Production-readiness ownership continues beyond it.
