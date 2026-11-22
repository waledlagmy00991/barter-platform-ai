# Private Telegram ad-proposal simulation

This is a private test, not a production release. Vision is excluded. All separate data-rights, vision-integrity and production-validation gates remain in force.

## Current flow

1. The numeric owner paired through a one-time Telegram link is the only allowed tester. Groups, other accounts and mismatched senders are ignored before audio retrieval or inference.
2. Text is processed by the owner's supplied Arabic spaCy 3.8 NER plus entity ruler. Quantity and unit are separate spans in this model. The adapter joins only adjacent spans and uses conservative material, condition and unit checks. Previously extracted source spans can be retained while an answer is appended; a sole missing-location answer is treated as the owner's stated location. These are parsing rules, not independent verification.
3. Voice up to 90 seconds/5 MB is downloaded from Telegram and transcribed with Groq Whisper Large v3. The transcript is shown for confirmation before an ad proposal or price estimate. Audio is not written to application storage.
4. Missing/ambiguous details and multiple lots cause a question, not a price guess. Unsupported material/condition/unit combinations abstain. Bag and board masses are never assumed.
5. Groq `openai/gpt-oss-120b` drafts an Arabic title and description and assesses internal consistency. Inputs are treated as ad data, with no tools or authority to publish. Source-quote evidence, numeric checks, unsupported-claim checks and material/condition/location checks gate the draft. These checks reduce errors; they do not prove truth. A rejected or unavailable LLM response is not silently replaced by a fake LLM template.
6. The existing pricing estimator produces a feature-only development reference without requiring or inventing an asking price. It uses material, grade/brand, condition and month. Location and dimensions are NOT model features; quantity only scales the total. An exact known grade/brand in the owner's text is used when found. Otherwise a condition-compatible default is disclosed explicitly, not asserted as a property of the lot. Predictions far outside that grade's saved source range abstain.
7. Every result is a draft for review. No ad is published, no seller contacted, no order recorded and no money spent.

The pricing table contains saved, sourced published Egyptian prices, not a live feed or validated transaction prices. No simulated pricing rows are added by this adapter. A model reference is not proof that a transaction price is fair. NER quality and pricing accuracy on independent Egyptian transactions remain unvalidated.

## Search, kept separate

`/search` retains the multilingual MiniLM/FAISS retrieval and deterministic response formatting. The 600-row corpus is synthetic demo material, not merchant inventory. Results require matching material, stated condition and location; quantities may differ. This is not chatbot fine-tuning.

The hosted search backend uses the pinned upstream Apache-2.0 ONNX quantized encoder plus SentencePiece to fit a free CPU instance. It is not bit-identical to the original PyTorch/tokenizer implementation. Fixed-query compatibility results are developmental checks, not unseen accuracy. The original default backend outside the deployment remains available.

## Commands and examples

- `/start`, `/help`, `/about`: scope, privacy route and limits.
- `عندي ٣٠ طن حديد تسليح جديد في القاهرة`: draft plus a labeled model reference, without asking price.
- `عندي ٥٠ كيلو نحاس خردة في المنصورة`: copper is preserved, never mapped to iron scrap; kg-to-tonne conversion is explicit in the pricing path.
- `عندي ٥٠ شيكارة اسمنت جديد في القاهرة`: draft may be possible, but price abstains without a supported quantity unit. Bag mass is not inferred.
- `عندي ٥ طن حديد تسليح مستعمل في القاهرة`: price abstains because the saved data does not support that condition.
- `/reset`: new request. `/price` is an alias for the current feature-based proposal flow, not the legacy asking-price conversation.

Do not send personal documents or unrelated private information to the test bot.

## NER provenance

The owner supplied a 3,565,079-byte ZIP through his authenticated conversation on November 22, 2026. Transport filename used a `.bin` suffix. SHA-256: `cab21357f01b2747b9a9759b9f478eaf6771730ec863e4bbe5aeb2506634ce62`.

Its 13 entries were checked before loading. Windows path separators were normalized, and absolute/traversal paths and oversized entries rejected. The archive contains a standard Arabic spaCy 3.8 pipeline with entity ruler and NER, no Python files or custom executable components. It emits ten NER labels including MATERIAL, QUANTITY, UNIT, CONDITION, LOCATION and SPECIFICATION. No training-data provenance, independent test set or performance claim was supplied. No accuracy metric is inferred from smoke tests.

## Private access and secrets

The webhook checks Telegram's secret-token header and the numeric private-chat owner allowlist. API docs are disabled. `/internal/check` requires the same secret, sends no Telegram messages and is explicitly a programmatic test path, not evidence of a live Telegram conversation. JSON inputs and audio are bounded; requests are serialized. The app does not log raw ad contents or token-bearing URLs. Responses use Telegram protected-content mode.

Secrets are host environment values, never committed. Required configuration:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_OWNER_ID`
- `GROQ_API_KEY`
- `BARTER_EMBEDDING_BACKEND=onnx`
- `OMP_NUM_THREADS=1`
- `OPENBLAS_NUM_THREADS=1`
- `TOKENIZERS_PARALLELISM=false`

`BARTER_NER_PATH` defaults in this server to `ner/user_model`. The general integration pipeline keeps its original default unless configured.

An optional `TELEGRAM_WEBHOOK_SECRET` can be configured. Otherwise the app derives a separate fixed-length header secret using SHA-256 over a purpose-tagged bot token. The setup program must derive the same value without printing it. A compromised bot token requires revocation and reconfiguration.

Conversation and the last 512 accepted update IDs exist only in memory. Restarts erase them. Same-process duplicate retries after successful delivery are ignored. Telegram delivery is not transactional with application state, so a network/process failure can cause a lost or duplicate response. This is unsuitable for commitments or orders.

## Free-service and privacy limits

Render was configured as Free, with no card/payment, paid disk, worker or database. It sleeps after 15 idle minutes, and the next request can wait about a minute or more. Free limits are shared with the account's other services. No artificial keep-alive traffic is set up.

Groq's actual account plan was checked as Free ($0). No billing upgrade or card was enabled. Free quotas can stop or rate-limit the bot. The dedicated test key expires December 22, 2026. Inference APIs ZDR was enabled and rechecked before ad/voice inference. Other organization-wide storage features were not disabled. Provider processing and operational metadata still exist; ZDR is not a claim that no system ever handles the content.

The source repository and deployment repository stay private. The deployment copy contains necessary text/model demo files, not the vision dataset or research photos. The web app exposes no source-file route.

## Build and run

```
pip install -r telegram_demo/requirements.txt
python telegram_demo/fetch_encoder.py
uvicorn telegram_demo.server:app --host 0.0.0.0 --port "$PORT" --workers 1 --no-access-log
```

Encoder downloads are hash-checked at revision `e8f8c211226b894fcb81acc59f3b34ba3efd5f42`. No training runs during build.

## Verification boundaries

`tests/test_telegram_demo.py` preserves legacy behavior with the original NER and checks shared server protection. `tests/test_telegram_proposals.py` checks the supplied NER's adjacent quantity/unit handling, feature-only references, copper-scrap mapping, grade selection, missing inputs, unsupported units/conditions, multiple lots, transcript confirmation and mismatched draft rejection. Authorization tests reject unrelated identities/groups before download or provider calls. Passing them is not evidence of live Telegram input or broad model accuracy. Separate deployment evidence must distinguish real Telegram updates, live provider calls and synthetic/mocked fixtures.

Official references:
- https://core.telegram.org/bots/api/
- https://render.com/docs/free
- https://console.groq.com/docs/your-data
- https://console.groq.com/docs/speech-to-text
- https://console.groq.com/docs/rate-limits
- https://console.groq.com/settings/billing/plans
- https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
