# Progress

## 10 Nov 2026 (laptop, OpenBot takeover)

- Repo extracted locally, `.git` intact, head `98ffa3b`.
- Python 3.12.6 venv, backend deps installed, Node 26.13.0, npm 11.6.2, Ollama 0.40.15.
- **64 pytest tests pass** (1.62 s on laptop; one Starlette/httpx deprecation warning). Added 20 amount-format cases, 7 date cases, range/limit evidence checks, and two prompt-injection tests.
- Web production build passes.
- UI polish: page title `MilestonePay`, persistent "No real funds" badge, explicit `LOCKED` milestone badges, blocked-plan panel, evidence quotes, readable action results, extraction progress text. Added `?project=<id>` resume support.
- Sample-mode UI flow clicked end to end in a real browser: extract -> approve -> draft -> send -> simulate payment -> milestone 1 `PAID` -> milestone 2 unlocked -> milestone 3 still locked. Verified 10 Nov 14:19 IST.
- Local `.env` built from the supplied sandbox credentials, git-ignored. Live mode runs with `MP_MODE=live` and `LLM_PROVIDER=ollama`.
- Ollama `qwen2.5:3b-instruct` pulled (1.9 GB). Real UI extraction took about 10 s and passed validation.
- **Live sandbox UI flow verified on 10 Nov:** approve -> draft real invoice `INV2-49NL-8AUM-4U23-WUYL` -> send with no emails -> US sandbox buyer paid USD 400.00 with fake funds -> fresh `GET` returned `PAID` with merchant/currency/amount/paid_full all true -> milestone 2 unlocked and drafted only (`INV2-8VKB-NZRP-SFZX-ZPNS`, `DRAFTED`, not sent) -> milestone 3 stayed `LOCKED`. Evidence: `backend/evals/laptop_sandbox_payment_20261110.json` (no emails or secrets).
- Not yet verified on the laptop: signed webhook, refund against real sandbox.

## 8 Nov 2026 (development box, historical)

Local only. Not pushed, no tunnel, no live PayPal call yet.

## Done
- Backend: evidence-checked AI extraction (quote verbatim, amount and date must appear in quote, USD, sum, future dates)
- Payment safety: atomic NONE->IN_FLIGHT claim; definite 4xx releases claim; timeout/5xx/crash -> RECONCILIATION_REQUIRED, automatic retry blocked; human reconcile searches PayPal by unique invoice number (search-invoices)
- Webhooks: official verify endpoint (webhook_event sent as JSON object built from the received bytes), event-id dedupe, crashed-in-processing events re-run, fresh GET reconcile (status, merchant, currency, exact amount)
- Refund/cancel after PAID puts later milestones on hold; send blocked while held
- Local token (X-MP-Token) on all state-changing routes; servers bound to 127.0.0.1. Real auth + CSRF needed before any tunnel/public exposure.
- Real local AI: Ollama 0.40.15, Qwen2.5-3B-Instruct Q4_K_M GGUF from huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF (sha256 prefix 626b4a6678b86442), CPU only
- Eval on 3 synthetic contracts (backend/evals): 2 valid plans with verbatim evidence; 1 sum-mismatch trap correctly blocked; ambiguities surfaced. Latency 12.5-28.8 s per contract on CPU.
- 32 pytest tests passed at the time (PayPal failures are mocked/simulated); 64 pass now, see 10 Nov section; web build passes

## Not done
- Live PayPal sandbox (needs credentials), visual QA, demo video, overdue reminder drafting, public repo, submission
- search-invoices filter and invoice webhook resource shape need live verification

## Real PayPal sandbox evidence (8 Nov 2026 IST) - see backend/evals/sandbox_smoke_artifact.json
- 18:42 create + exact invoice_number search + send (no emails) to US sandbox buyer: INV2-5B6P-CMK9-FU6Z-7E82
- Buyer checkout done once in browser (sandbox funds)
- 18:47 fresh GET: PAID, paid 1.00 USD, due 0.00, merchant/buyer match, payment_id 5PX244119T794353V
- 18:47 app reconcile logic on real invoice (isolated fixture, not UI flow): PAID, all checks true
- 18:47 forged webhook to local live-mode server: 400 (verify errors now fail closed)
- IN-addressed invoice is blocked by PayPal (INR_FOREIGN_CURRENCY_BLOCKED); use non-India buyers
Open: UI approve-create-send against live sandbox, visual QA, valid signed webhook (needs approved public endpoint + auth/CSRF), refund/concurrency only mocked

## Webhook endpoint attempt + HTTP integration (8 Nov 2026 IST)
- 18:52 webhook-only proxy (backend/webhook_proxy.py, 127.0.0.1:8020) tested locally: all other paths/methods 404, 70 KB chunked body 413, unsigned 400, 31st request/min 429. Concurrency cap (4) not load-tested.
- 18:52-18:54 cloudflared 2026.10.7 quick tunnel: QUIC timed out; http2 got TLS EOF to Cloudflare edge (box network). No connection registered; public URL returned 530. Stopped tunnel and proxy. No webhook registered with PayPal.
- 18:54 PayPal event catalog (GET /v1/notifications/webhooks-event-types) confirms INVOICING.INVOICE.PAID / REFUNDED / CANCELLED exist. 0 webhooks registered on the app.
- 18:54 isolated sandbox instance (8011, /tmp/mp_sandbox_ui.sqlite3) over HTTP API with local token, not the UI: real Qwen extraction 16.7 s valid; approve; milestone 2 draft refused (409); milestone 1 invoice INV2-TGZH-57DY-C4DA-5HBF created and sent (no emails), status SENT.
- 19:01 IST fresh GET INV2-TGZH-57DY-C4DA-5HBF (MP-d3f24545a903-1): PAID via PAYPAL method, 1.00 USD paid, 0.00 due, merchant/buyer match, payment_id 4N502163BR404925D
- 19:01 app API refresh on isolated 8011 project d3f24545a903: milestone_paid (all checks true); milestone 2 then drafted only: INV2-ESYF-VJUY-BC75-FYGP (DRAFT, not sent, not paid)
- Real backend/API flow verified end to end with polling. NOT verified: UI clicks/visual (browser cannot reach box localhost), signed webhook (tunnel blocked), refund/concurrency (mocked only)
