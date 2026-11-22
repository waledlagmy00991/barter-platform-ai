# Vision evaluation policy, 22 November 2026

## Execution paused

There is no approved production promotion gate. All historical vision scores, including .944, .8847 and .8678, are withdrawn as generalization and localization evidence. Independent integrity review has completed and confirmed the blockers; recovery criteria remain unmet. Training, harvesting, dataset rebuilding, cleanup deletion and metric overwrite scripts now fail closed through `vision/integrity_guard.py` and `evaluation/execution_status.json`.

## Preserved legacy selection set

`vision/evaluation/legacy62_v1/` is a quarantined copy of 62 historical selection files and their labels. Its manifest records SHA-256 hashes and available source evidence. Routine cleanup operates elsewhere; this snapshot is never a cleanup input. The files are read-only in the working copy, and the guard checks exact membership, file hashes, labels and deployed-weight hash before any guarded action. Git commit 2bb8b33248fc0241f64e185bc9edf4bb612cfba8 preserves the original audit evidence.

This protects reproducibility, not validity. The original selection set is adaptively reused, has common source pages with training, and overlaps by bytes with retained older training files. Supplier identities and Egyptian-market origin are not established for every file. The set cannot become a new untouched audit set by being repaired or renamed.

## Corrective work

`evaluation/provenance_recovery.json` records original-byte verification for four renamed files. It does not rewrite the historical snapshot. Four plywood records remain unresolved.

`evaluation/quarantine_ledger.json` is a non-destructive index. No originals are moved or deleted. All existing records remain ineligible until origin, group identity, labels, rights and independent review are resolved. Source components merge exact image bytes and normalized source-page identifiers globally across material classes. These are conservative linkages, not verified supplier identities. Shared domains are not automatically merged as suppliers, and different source components are not proof of independent suppliers.

The retained dataset2 evidence is separate from the legacy selection snapshot. Its actual files and checkpoint metadata are preserved at commit 67ce2ecaa606acb56c272bca0cb38befe5f92dfb. It is not a cryptographically bound historical training manifest.

## Future independent audit

The existing `data/audit/` is a candidate intake only. Its origin, labels, supplier independence and non-exposure to training must be reviewed before it can be treated as final audit data. A fixed percentage or an unfamiliar filename does not establish independence.

Release requires independent review, a versioned corrected pool, evidence-backed source/supplier groups and an explicit evaluation design. No new score may silently replace an invalidated baseline. Thursday 26 November is a discussion checkpoint, not closure of the production-readiness work.
