# Local API safety status

This is a development service, not a production deployment. Vision training and harvesting remain paused. No model weights were changed by the API safety work.

## Run and endpoints

Run from the repository root:

```bash
uvicorn integration.api:app --host 127.0.0.1 --port 8000
```

- `GET /health`: process liveness only. `production_ready` is false.
- `GET /ready`: HTTP 503 with current release blockers.
- `POST /analyze`: text and optional positive finite numeric asking price. Request body limit 65,536 bytes, text limit 10,000 characters, no unknown fields. At most two concurrent inference calls; excess receives HTTP 429 with Retry-After. Invalid input receives HTTP 422 without echoing the raw text or non-finite values.

This service has no approved production authentication, tenant isolation, reverse-proxy configuration, durable queue, monitoring, privacy retention policy or deployment review. Keep it bound to localhost. The request caps are local safeguards, not a completed denial-of-service defense or performance qualification.

## Price contract changes

`pricing.evaluate_ask` now requires explicit `quantity_unit` for a verdict. The input condition is not replaced with new. An unknown condition, unsupported material/condition pair, ambiguous material assumption or unsupported/missing quantity unit returns null `verdict`, `is_fair`, ratio and fair-price fields. An optional `reference_new_unit_price_egp` is explicitly a new-only reference per `reference_price_unit`, not an inferred price for unknown condition or bag weight.

Only the published material units are used. Kilograms can be converted to tonnes explicitly. Bag weight, linear-to-cubic dimensions and other unprovided conversions are not guessed. Responses include original and normalized quantities and units. Prices remain unvalidated development estimates, not executable quotes or independently validated judgments.

```python
from pricing.predict import evaluate_ask
result = evaluate_ask(
    material='حديد تسليح', condition='جديد', location=None,
    quantity=10, quantity_unit='طن', asking_total_price=400000,
)
```

Earlier pricing tests used ads with no condition while asserting a verdict. Those fixtures now explicitly state new; separate regression tests require null verdicts when condition is absent. This is an intentional contract correction, not an improvement in measured model accuracy.

## Vision behavior

While integrity review is open, `verify_image` returns blocked status, null match and no confidence, without reading the image or loading the model. It does not emit an automatic acceptance/rejection decision. Visual new/used/rust recognition remains unsupported. The text-only public request does not accept local file paths or remote image URLs.

## What the tests establish

The local regression suite checks request limits, chunked body limits, NaN/infinity handling, readiness, quantity-unit guards, condition guards, bounded concurrency, safe errors and preserved vision pause. It does not establish production security, model accuracy, supplier independence or readiness. See `safety_results.json` for the recorded local test run.
