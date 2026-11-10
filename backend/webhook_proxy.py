"""Webhook-only reverse proxy for a temporary public tunnel.

Exposes exactly POST /api/webhooks/paypal -> 127.0.0.1:8011. Everything else 404.
- 64 KB cap enforced on streamed bytes (not just Content-Length)
- max 4 concurrent, max 30 requests/minute, 10 s upstream timeout
- forwards only Content-Type and PayPal-* headers (no cookies, no auth, no X-MP-Token)
- logs only method, path, status, size; never bodies or headers
"""
import asyncio, os, time
import httpx
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route

UPSTREAM = os.getenv("WH_UPSTREAM", "http://127.0.0.1:8011/api/webhooks/paypal")
MAX = 64 * 1024
sem = asyncio.Semaphore(4)
hits: list[float] = []
client = httpx.AsyncClient(timeout=10)


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


async def webhook(req: Request):
    now = time.time()
    hits[:] = [t for t in hits if now - t < 60]
    if len(hits) >= 30:
        return PlainTextResponse("rate limited", 429)
    hits.append(now)
    if sem.locked():
        return PlainTextResponse("busy", 503)
    async with sem:
        body = bytearray()
        async for chunk in req.stream():
            body += chunk
            if len(body) > MAX:
                log("POST webhook 413")
                return PlainTextResponse("too large", 413)
        fwd = {k: v for k, v in req.headers.items() if k.lower().startswith("paypal-") or k.lower() == "content-type"}
        try:
            r = await client.post(UPSTREAM, content=bytes(body), headers=fwd)
        except httpx.HTTPError:
            log("POST webhook 502")
            return PlainTextResponse("upstream error", 502)
        log("POST webhook", r.status_code, len(body))
        return PlainTextResponse("ok" if r.status_code < 300 else "rejected", 200 if r.status_code < 300 else 400)


async def notfound(req: Request):
    return PlainTextResponse("not found", 404)


app = Starlette(routes=[Route("/api/webhooks/paypal", webhook, methods=["POST"]),
                        Route("/{p:path}", notfound, methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])])
