"""One guarded live OpenRouter free-model smoke test.

Rules from MP-Q11:
- at most 3 live calls total
- sample contract only
- explicit model id ending in ":free"
- small max_tokens
- stop if the returned model is not :free or if any credit use appears
- never print the key

Run from the backend directory:
    python evals/openrouter_smoke.py
"""
from __future__ import annotations

import json
import sys
import argparse
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.extraction import (  # noqa: E402
    EXTRACTION_SYSTEM, SAMPLE_CONTRACT, build_extraction_prompt, parse_plan, validate_plan,
)
from app.llm import parse_env_file  # noqa: E402

URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_FREE = "google/gemma-4-31b-it:free"
FALLBACK_FREE = ["google/gemma-4-26b-a4b-it:free", "nvidia/nemotron-3-ultra-550b-a55b:free"]
MAX_CALLS = 3
MAX_TOKENS = 900
ENV_FILE = Path.home() / "milestonepay_secrets" / ".env.openrouter"


def model_candidates(env: dict[str, str], chosen: str = "") -> list[str]:
    if chosen:
        return [chosen]
    raw = env.get("OPENROUTER_FALLBACKS", "")
    models = [m.strip() for m in raw.split(",") if m.strip().endswith(":free")]
    configured = env.get("OPENROUTER_MODEL", "").strip()
    if configured.endswith(":free") and configured not in models:
        models.insert(0, configured)
    for model in [DEFAULT_FREE, *FALLBACK_FREE]:
        if model not in models:
            models.append(model)
    return [m for m in models if m.endswith(":free")][:MAX_CALLS]


def call_once(api_key: str, model: str) -> dict:
    body = {
        "model": model,
        "temperature": 0.1,
        "max_tokens": MAX_TOKENS,
        "messages": [
            {"role": "system", "content": EXTRACTION_SYSTEM},
            {"role": "user", "content": build_extraction_prompt(SAMPLE_CONTRACT)},
        ],
    }
    started = time.time()
    with httpx.Client(timeout=60) as client:
        r = client.post(URL, json=body, headers={
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://github.com/suhailult777/milestonepay",
            "X-Title": "MilestonePay free smoke",
        })
    latency = round(time.time() - started, 2)
    credits = r.headers.get("x-credits-charged")
    if credits is not None:
        try:
            if float(credits) > 0:
                return {"status": "blocked_credit_use", "model_requested": model,
                        "latency_seconds": latency, "credits_charged": credits}
        except ValueError:
            return {"status": "blocked_credit_header", "model_requested": model,
                    "latency_seconds": latency}
    if r.status_code == 429:
        return {"status": "rate_limited", "model_requested": model, "latency_seconds": latency}
    if r.status_code >= 400:
        return {"status": "http_error", "model_requested": model, "http_status": r.status_code,
                "latency_seconds": latency}
    try:
        data = r.json()
    except ValueError:
        return {"status": "bad_response_json", "model_requested": model, "latency_seconds": latency}
    returned = data.get("model") or ""
    usage = data.get("usage") or {}
    cost = usage.get("cost")
    if cost is not None:
        try:
            if float(cost) > 0:
                return {"status": "blocked_credit_use", "model_requested": model,
                        "model_returned": returned, "latency_seconds": latency,
                        "usage_cost": cost}
        except (TypeError, ValueError):
            return {"status": "blocked_cost_unreadable", "model_requested": model,
                    "model_returned": returned, "latency_seconds": latency}
    if not str(returned).endswith(":free"):
        return {"status": "blocked_non_free_model", "model_requested": model,
                "model_returned": returned, "latency_seconds": latency}
    try:
        content = data["choices"][0]["message"]["content"] or ""
        plan = parse_plan(content)
        errors = validate_plan(plan, SAMPLE_CONTRACT)
    except Exception as e:  # noqa: BLE001 - the artifact should record the class, not the raw body
        return {"status": "invalid_plan", "model_requested": model, "model_returned": returned,
                "latency_seconds": latency, "error_type": type(e).__name__,
                "usage": {"prompt_tokens": usage.get("prompt_tokens"),
                          "completion_tokens": usage.get("completion_tokens"),
                          "cost": cost}}
    return {
        "status": "passed",
        "model_requested": model,
        "model_returned": returned,
        "latency_seconds": latency,
        "json_parsed": True,
        "blocking_errors": errors,
        "milestones": len(plan.milestones),
        "usage": {
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
            "cost": cost,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="", help="explicit model id ending in :free")
    parser.add_argument("--prior-calls", type=int, default=0, help="live calls already used in earlier attempts")
    args = parser.parse_args()
    env = parse_env_file(ENV_FILE)
    key = env.get("OPENROUTER_API_KEY", "")
    if not key:
        print("smoke=failed reason=no_key")
        return 1
    candidates = model_candidates(env, args.model)
    remaining = max(0, MAX_CALLS - args.prior_calls)
    candidates = candidates[:remaining]
    if not candidates:
        print("smoke=blocked reason=call_budget_exhausted")
        return 1
    attempts: list[dict] = []
    result: dict = {}
    used = 0
    for model in candidates:
        if not model.endswith(":free"):
            result = {"status": "blocked_non_free_request", "model_requested": model}
            attempts.append(result)
            break
        used += 1
        print(f"smoke_call={args.prior_calls + used} model={model}")
        result = call_once(key, model)
        attempts.append(result)
        if result.get("status") == "passed":
            break
        if result.get("status", "").startswith("blocked_"):
            break
    artifact = {
        "date_ist": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "scope": "Live OpenRouter free-model smoke, bundled sample contract only, no real client data",
        "max_calls_allowed": MAX_CALLS,
        "prior_live_calls": args.prior_calls,
        "calls_used_this_run": used,
        "calls_used_total": args.prior_calls + used,
        "model_candidates": candidates,
        "attempts": attempts,
        "result": result,
        "notes": "No key, headers, or raw model output are stored. Free models only; stop on any credit sign.",
    }
    out = Path(__file__).with_name("openrouter_smoke_20261110.json")
    out.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    print(f"smoke_status={result.get('status')} calls_used_total={args.prior_calls + used} artifact={out.name}")
    return 0 if result.get("status") == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
