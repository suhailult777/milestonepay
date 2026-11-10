"""Free-first LLM providers: OpenRouter primary, Ollama fallback.

The OpenRouter key is read at runtime from a file outside the repo. It is never
logged, printed, or stored in Settings; the client keeps it only in memory.
"""
from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Protocol

import httpx

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Free models checked in the DocDesk reference on 4 Nov 2026. The env preset wins.
OPENROUTER_FREE_MODELS = [
    "google/gemma-4-31b-it:free",
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "openrouter/free",
]

DEFAULT_TIMEOUT = 45.0
MAX_FALLBACKS = 3


class LLMError(RuntimeError):
    pass


class LLM(Protocol):
    name: str

    def complete(self, system: str, prompt: str) -> str: ...


def parse_env_file(path: str | os.PathLike[str]) -> dict[str, str]:
    """Read KEY=VALUE lines without logging or returning them to callers that print."""
    p = Path(path)
    if not p.is_file():
        return {}
    out: dict[str, str] = {}
    for raw in p.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        out[key] = value
    return out


def _redact(text: str, *secrets: str) -> str:
    for secret in secrets:
        if secret:
            text = text.replace(secret, "[redacted]")
    return text


class OpenRouterLLM:
    """OpenRouter chat completions with a small model fallback list and 429 retries."""

    name = "openrouter"
    URL = OPENROUTER_URL

    def __init__(
        self,
        api_key: str,
        model: str | None = None,
        fallbacks: list[str] | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        retries: int = 2,
        http: httpx.Client | None = None,
        sleep=time.sleep,
    ):
        if not api_key:
            raise LLMError("OpenRouter API key is missing")
        self.api_key = api_key
        self.model = model or OPENROUTER_FREE_MODELS[0]
        if self.model.startswith("@preset/"):
            self.models = [self.model]
        else:
            fb = OPENROUTER_FREE_MODELS if fallbacks is None else fallbacks
            self.models = ([self.model] + [m for m in fb if m != self.model])[:MAX_FALLBACKS]
        self.timeout = timeout
        self.retries = retries
        self.http = http or httpx.Client(timeout=timeout)
        self.sleep = sleep
        self.last_model: str | None = None

    def __repr__(self) -> str:
        return f"OpenRouterLLM(model={self.model!r}, models={self.models!r})"

    def body(self, system: str, prompt: str, json_mode: bool = True) -> dict:
        b: dict = {
            "model": self.model,
            "temperature": 0.1,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        }
        if not self.model.startswith("@preset/") and len(self.models) > 1:
            b["models"] = self.models
        if json_mode:
            b["response_format"] = {"type": "json_object"}
        return b

    def complete(self, system: str, prompt: str) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com/suhailult777/milestonepay",
            "X-Title": "MilestonePay",
        }
        json_mode = True
        for attempt in range(self.retries + 1):
            try:
                r = self.http.post(self.URL, json=self.body(system, prompt, json_mode=json_mode), headers=headers)
            except httpx.TimeoutException as e:
                raise LLMError("openrouter timed out") from e
            except httpx.HTTPError as e:
                raise LLMError(f"openrouter transport error: {type(e).__name__}") from e
            if r.status_code == 400 and json_mode:
                # Some free models do not accept response_format. Retry once without it.
                json_mode = False
                continue
            if r.status_code == 429 and attempt < self.retries:
                wait = min(float(r.headers.get("retry-after") or 2 ** (attempt + 1)), 10)
                self.sleep(wait)
                continue
            if r.status_code >= 400:
                raise LLMError(f"openrouter {r.status_code}: {_redact(r.text[:200], self.api_key)}")
            try:
                data = r.json()
            except ValueError as e:
                raise LLMError("openrouter returned a non-JSON response") from e
            if data.get("error"):
                raise LLMError(f"openrouter error: {_redact(str(data['error'])[:200], self.api_key)}")
            try:
                text = (data["choices"][0]["message"].get("content") or "").strip()
            except (KeyError, IndexError, TypeError) as e:
                raise LLMError("openrouter returned an unexpected response shape") from e
            if not text:
                raise LLMError("openrouter returned an empty answer")
            self.last_model = data.get("model", self.model)
            return text
        raise LLMError("openrouter rate limited")


class OllamaLLM:
    """Local Ollama chat with JSON output. Free and offline."""

    name = "ollama"

    def __init__(
        self,
        base_url: str,
        model: str,
        timeout: float = 120.0,
        http: httpx.Client | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.http = http or httpx.Client(timeout=timeout)

    def complete(self, system: str, prompt: str) -> str:
        try:
            r = self.http.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "stream": False,
                    "format": "json",
                    "options": {"temperature": 0},
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt},
                    ],
                },
                timeout=self.timeout,
            )
        except httpx.TimeoutException as e:
            raise LLMError("ollama timed out") from e
        except httpx.HTTPError as e:
            raise LLMError(f"ollama transport error: {type(e).__name__}") from e
        if r.status_code >= 400:
            raise LLMError(f"ollama {r.status_code}: {r.text[:200]}")
        try:
            text = (r.json().get("message") or {}).get("content") or ""
        except ValueError as e:
            raise LLMError("ollama returned a non-JSON response") from e
        text = text.strip()
        if not text:
            raise LLMError("ollama returned an empty answer")
        return text


class ChainLLM:
    """Try each provider in order. Errors keep the provider name only."""

    def __init__(self, providers: list[LLM]):
        if not providers:
            raise LLMError("no LLM providers configured")
        self.providers = providers
        self.name = "+".join(p.name for p in providers)
        self.last_used: str | None = None

    def __repr__(self) -> str:
        return f"ChainLLM(providers={[p.name for p in self.providers]!r})"

    def complete(self, system: str, prompt: str) -> str:
        errors: list[str] = []
        for provider in self.providers:
            try:
                out = provider.complete(system, prompt)
                self.last_used = provider.name
                return out
            except Exception as e:  # noqa: BLE001 - fallback is the point
                errors.append(f"{provider.name}: {type(e).__name__}: {str(e)[:200]}")
        raise LLMError("; ".join(errors))


def openrouter_from_file(
    env_file: str,
    *,
    model: str = "",
    preset: str = "",
    fallbacks: str = "",
    timeout: float = DEFAULT_TIMEOUT,
    http: httpx.Client | None = None,
) -> OpenRouterLLM | None:
    """Load the key from the external env file. Never print the returned values."""
    env = parse_env_file(env_file)
    key = env.get("OPENROUTER_API_KEY") or os.getenv("OPENROUTER_API_KEY") or ""
    if not key:
        return None
    model = model or env.get("OPENROUTER_MODEL", "")
    preset = preset or env.get("OPENROUTER_PRESET", "")
    if not model and preset:
        model = preset if preset.startswith("@preset/") else f"@preset/{preset}"
    raw_fallbacks = fallbacks or env.get("OPENROUTER_FALLBACKS", "")
    fallback_list = [m.strip() for m in raw_fallbacks.split(",") if m.strip()] or None
    return OpenRouterLLM(key, model or None, fallback_list, timeout=timeout, http=http)


def build_llm(settings, *, http: httpx.Client | None = None) -> ChainLLM | None:
    """Build the configured chain. Sample mode returns None and stays keyless."""
    if settings.llm_provider == "sample":
        return None
    ollama = OllamaLLM(settings.llm_base_url, settings.llm_model, http=http)
    if settings.llm_provider == "ollama":
        return ChainLLM([ollama])
    openrouter = openrouter_from_file(
        settings.openrouter_env_file,
        model=settings.openrouter_model,
        preset=settings.openrouter_preset,
        fallbacks=settings.openrouter_fallbacks,
        timeout=settings.openrouter_timeout,
        http=http,
    )
    if settings.llm_provider == "openrouter":
        if openrouter is None:
            raise LLMError(
                "OpenRouter key not found. Set OPENROUTER_API_KEY in the external env file,"
                " or use LLM_PROVIDER=auto to fall back to Ollama."
            )
        return ChainLLM([openrouter, ollama])
    # auto: OpenRouter if a key is available, otherwise local Ollama.
    providers: list[LLM] = [p for p in (openrouter, ollama) if p is not None]
    return ChainLLM(providers)
