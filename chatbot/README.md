# RAG status: synthetic demo only

The existing corpus has 600 generated examples and generated prices. It is not verified merchant inventory. The numeric prices and ad text were preserved for historical demo continuity, not validated or corrected into real offers.

## Explicit artifacts and response contract

- `data/synthetic_demo_ads.jsonl`
- `index/synthetic_demo_ads_meta.json`
- `index/synthetic_demo_ads.faiss`

Every record is marked `synthetic: true`, `inventory_verified: false`, `is_actionable: false` and with synthetic price origin. Price keys are `synthetic_demo_asking_total_egp` and `synthetic_demo_model_reference_total_egp`. There is no ordinary price or fair-price field implying a genuine offer. The migration ledger records prior/current hashes and confirms unchanged FAISS bytes and numeric values.

Search returns demo markers on every result, including a display notice. The answer template says the data and prices are generated, not actual sale offers. Scores are similarity/ranking signals, not calibrated probabilities or a relevance guarantee. A source-label migration does not improve retrieval quality or validate the old generated prices.

## Surviving local capability

`search(query, k)` performs local embedding retrieval and keyword/location reranking over the demo corpus. `ask(query)` formats the retrieved examples. Queries are capped at 10,000 characters and k at 1 to 20. Loading checks corpus/index hashes, row consistency, index count and embedding dimension. The embedding model must already be cached locally; there is no runtime download or external generation fallback.

An environment API key does not trigger a paid external model call. Synthetic corpus regeneration is disabled, because the old generator assumed condition and price units and could produce unsupported prices. No new synthetic ads or prices were created during this safety remediation.

## Unsupported production features

There is no real inventory feed, verified seller availability, transaction quote, durable request registration or notification delivery. The answer does not claim that a request or alert was created. There is no production chat API endpoint or independently measured real-ad relevance benchmark.

Production work needs authorized real listings with per-ad source, owner and permitted uses; real units/conditions/grades; verified prices and availability freshness; a reviewed ingestion/update policy; independent relevance and answer evaluation; and any requested registration/notification service built and approved. No new recipient, merchant contact, external deployment or paid service is authorized by these local code changes.
