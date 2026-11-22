# Production recovery plan, 22 November 2026

The project is not production-ready. The independent review covered vision integrity only, not the other models or overall backend. Local safety regressions are not model-quality certification. Friday's discussion is a checkpoint, not closure of the production request.

## Surviving capabilities

- Local SpaCy extraction of material, quantity and location. Existing F1 is an internal generated-sentence result. Real-ad generalization is not established.
- Local published-price-model inference within explicit material/condition/unit combinations. Unknown or unsupported input withholds a verdict; references are labeled. Real transaction accuracy and condition-sensitive pricing are not established.
- Local text-analysis FastAPI with bounded requests and concurrency, safe error behavior, liveness and a failing production-readiness endpoint. This is not an approved public deployment.
- Local semantic retrieval and deterministic formatting over 600 explicitly synthetic, non-actionable examples. This is not merchant inventory, a quoting system, request registration or notification delivery.
- Preserved vision weights and evidence, but no operational image verification or valid performance estimate. All historical vision scores are withdrawn as generalization/localization evidence.

## Completed safety changes

Unknown condition is no longer assumed new. Unsupported condition/material combinations, ambiguous generic material and unknown units abstain. Quantity-to-price multiplication checks the actual published unit; bag masses and dimensional conversions are not guessed. Explicit kg-to-tonne conversion carries the normalized quantity. Negated/conflicting condition keywords abstain conservatively.

The public development request cannot supply arbitrary file paths or image URLs. Vision inference is blocked while recovery criteria are unmet. JSON body size, text size, finite positive prices and concurrent inference are bounded. Readiness remains false.

Every demo record and result is explicitly synthetic and non-actionable, generated-price fields are renamed, and answers do not imply a real offer or a registered alert. Automatic external LLM calls and unsupported synthetic generation are disabled. No new ads/prices or embeddings were generated during labeling of the historical demo corpus.

## Dependency 1: new vision data, rights and task definition

There is no approved training pool. Do not repair the adaptively reused legacy selection set and call it unseen evaluation. Recovery needs genuinely new Egyptian-market data with evidence of origin and permitted use, plus source/supplier grouping before global splitting. Ambiguous records remain in quarantine.

Define separate tasks and ground truth: whole-image material classification, object localization and visual new/used/rust recognition. Full-image boxes do not establish localization. Material classes do not validate condition. Label review, abstention behavior and business-relevant acceptance criteria must be set before training and evaluation. A proposed number of images is a collection estimate, never a guarantee of production readiness.

The data intake record should cover file/hash, source, verified group linkage and its evidence, Egyptian-market relevance and its evidence, rights holder/permitted use and evidence, task-specific labels and review status, collection date, and immutable split membership. Independent review is required before release. Model software and pretrained-weight terms also need review for the intended deployment.

## Dependency 2: real evaluation inputs and inventory

NER and text-condition extraction need independently collected, authorized, labeled real ads and a predeclared evaluation plan. Pricing needs reviewed units/grades/conditions and genuinely supported same-material condition comparisons; no new synthetic pricing rows may fill missing market evidence. The published-price dataset is not a database of executable dealer offers.

RAG needs a real authorized inventory feed, per-ad source/owner and permitted uses, verified price/unit/condition fields, freshness and availability handling, and independent retrieval/answer evaluation. Registration and notification services must be built before any promise to perform them. The existing synthetic corpus must not be promoted to real inventory by relabeling it.

## Dependency 3: deployment and operations decisions

Before any public staging or production release: decide the intended audience and launch scope, authentication and tenant boundaries, storage/retention and consent, request/response contract, failure handling, monitoring, rollback and incident ownership. Review dependencies and reproducible packaging. Obtain approval for hosting, paid services, any external deployment and the related data flows before acting.

Any narrower launch scope must be chosen by the user, not silently inferred from whichever features currently work. No such scope reduction or deployment approval has been assumed.

## Continuation

Training and harvesting stay paused. Preserve original evidence and weights. Continue only when genuinely new authorized data/evidence or an owner decision changes a dependency. No polling or repeated unchanged readiness checks are needed. The production outcome remains open beyond the discussion checkpoint.
