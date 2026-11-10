"""Mocked provider tests. No network, no real key, no secret printing."""
import json
from types import SimpleNamespace

import httpx
import pytest

from app.extraction import EXTRACTION_SYSTEM, SAMPLE_CONTRACT, extract_with_llm, parse_plan
from app.llm import (
    ChainLLM,
    LLMError,
    OllamaLLM,
    OpenRouterLLM,
    build_llm,
    openrouter_from_file,
    parse_env_file,
)

FAKE_KEY = "sk-test-not-a-real-key"


def settings(**over):
    base = dict(
        llm_provider="auto",
        llm_base_url="http://127.0.0.1:11434",
        llm_model="qwen2.5:3b-instruct",
        openrouter_env_file="C:/does/not/exist/.env.openrouter",
        openrouter_model="",
        openrouter_preset="",
        openrouter_fallbacks="",
        openrouter_timeout=45.0,
    )
    base.update(over)
    return SimpleNamespace(**base)


def openrouter_ok(content='{"client_name":"X"}'):
    def handler(req):
        return httpx.Response(200, json={
            "model": "test/model",
            "choices": [{"message": {"content": content}}],
        })
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_parse_env_file(tmp_path):
    p = tmp_path / ".env.openrouter"
    p.write_text(
        "# comment\nOPENROUTER_API_KEY=sk-test-not-a-real-key\n"
        "OPENROUTER_PRESET='demo preset'\n"
        "export OPENROUTER_FALLBACKS=a:free,b:free\n",
        encoding="utf-8",
    )
    env = parse_env_file(p)
    assert env["OPENROUTER_API_KEY"] == FAKE_KEY
    assert env["OPENROUTER_PRESET"] == "demo preset"
    assert env["OPENROUTER_FALLBACKS"] == "a:free,b:free"


def test_openrouter_from_file_missing_key(tmp_path):
    p = tmp_path / ".env.openrouter"
    p.write_text("OPENROUTER_PRESET=demo\n", encoding="utf-8")
    assert openrouter_from_file(str(p)) is None


def test_openrouter_request_shape_and_repr():
    seen = []

    def handler(req):
        seen.append(req)
        return httpx.Response(200, json={
            "model": "test/model",
            "choices": [{"message": {"content": "hello"}}],
        })
    llm = OpenRouterLLM(FAKE_KEY, "test/model", ["fallback:free"], http=httpx.Client(transport=httpx.MockTransport(handler)))
    assert llm.complete("system", "prompt") == "hello"
    assert seen[0].headers["Authorization"] == f"Bearer {FAKE_KEY}"
    body = json.loads(seen[0].content)
    assert body["messages"][0] == {"role": "system", "content": "system"}
    assert body["models"] == ["test/model", "fallback:free"]
    assert body["response_format"] == {"type": "json_object"}
    assert FAKE_KEY not in repr(llm)


def test_openrouter_preset_has_no_models_list():
    seen = []

    def handler(req):
        seen.append(req)
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})
    llm = OpenRouterLLM(FAKE_KEY, "@preset/demo", http=httpx.Client(transport=httpx.MockTransport(handler)))
    llm.complete("s", "p")
    body = json.loads(seen[0].content)
    assert body["model"] == "@preset/demo"
    assert "models" not in body


def test_openrouter_429_retries_then_succeeds():
    calls = {"n": 0}
    sleeps = []

    def handler(req):
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(429, headers={"retry-after": "0"})
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})
    llm = OpenRouterLLM(FAKE_KEY, http=httpx.Client(transport=httpx.MockTransport(handler)),
                        sleep=lambda s: sleeps.append(s))
    assert llm.complete("s", "p") == "ok"
    assert calls["n"] == 2 and sleeps == [0.0]


def test_openrouter_400_retries_without_json_mode():
    seen = []

    def handler(req):
        seen.append(json.loads(req.content))
        if len(seen) == 1:
            return httpx.Response(400, json={"error": "response_format unsupported"})
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})
    llm = OpenRouterLLM(FAKE_KEY, http=httpx.Client(transport=httpx.MockTransport(handler)))
    assert llm.complete("s", "p") == "ok"
    assert "response_format" in seen[0] and "response_format" not in seen[1]


def test_openrouter_error_redacts_key():
    def handler(req):
        return httpx.Response(401, text=f"bad key {FAKE_KEY}")
    llm = OpenRouterLLM(FAKE_KEY, http=httpx.Client(transport=httpx.MockTransport(handler)))
    with pytest.raises(LLMError) as e:
        llm.complete("s", "p")
    assert FAKE_KEY not in str(e.value)
    assert "[redacted]" in str(e.value)


def test_ollama_request_shape():
    seen = []

    def handler(req):
        seen.append(req)
        assert req.url.path == "/api/chat"
        return httpx.Response(200, json={"message": {"content": "ollama-ok"}})
    llm = OllamaLLM("http://127.0.0.1:11434", "qwen2.5:3b-instruct",
                    http=httpx.Client(transport=httpx.MockTransport(handler)))
    assert llm.complete("system", "prompt") == "ollama-ok"
    body = json.loads(seen[0].content)
    assert body["format"] == "json" and body["stream"] is False
    assert body["options"]["temperature"] == 0
    assert body["messages"][0]["role"] == "system"


def test_chain_falls_back_and_records_provider():
    def handler(req):
        if "openrouter.ai" in str(req.url):
            return httpx.Response(503, text="upstream down")
        return httpx.Response(200, json={"message": {"content": "local-ok"}})
    http = httpx.Client(transport=httpx.MockTransport(handler))
    chain = ChainLLM([
        OpenRouterLLM(FAKE_KEY, http=http),
        OllamaLLM("http://127.0.0.1:11434", "qwen2.5:3b-instruct", http=http),
    ])
    assert chain.complete("s", "p") == "local-ok"
    assert chain.last_used == "ollama"


def test_chain_reports_both_providers_without_key():
    def handler(req):
        return httpx.Response(500, text="down")
    http = httpx.Client(transport=httpx.MockTransport(handler))
    chain = ChainLLM([
        OpenRouterLLM(FAKE_KEY, http=http),
        OllamaLLM("http://127.0.0.1:11434", "qwen2.5:3b-instruct", http=http),
    ])
    with pytest.raises(LLMError) as e:
        chain.complete("s", "p")
    msg = str(e.value)
    assert "openrouter" in msg and "ollama" in msg and FAKE_KEY not in msg


def test_build_llm_sample_stays_keyless(tmp_path):
    assert build_llm(settings(llm_provider="sample", openrouter_env_file=str(tmp_path / "missing"))) is None


def test_build_llm_openrouter_without_key_raises(tmp_path):
    with pytest.raises(LLMError, match="OpenRouter key not found"):
        build_llm(settings(llm_provider="openrouter", openrouter_env_file=str(tmp_path / "missing")))


def test_build_llm_auto_uses_openrouter_then_ollama(tmp_path):
    p = tmp_path / ".env.openrouter"
    p.write_text(f"OPENROUTER_API_KEY={FAKE_KEY}\nOPENROUTER_PRESET=demo\n", encoding="utf-8")
    chain = build_llm(settings(llm_provider="auto", openrouter_env_file=str(p)))
    assert [x.name for x in chain.providers] == ["openrouter", "ollama"]


def test_build_llm_auto_without_key_uses_ollama_only(tmp_path):
    chain = build_llm(settings(llm_provider="auto", openrouter_env_file=str(tmp_path / "missing")))
    assert [x.name for x in chain.providers] == ["ollama"]


def test_build_llm_ollama_only():
    chain = build_llm(settings(llm_provider="ollama"))
    assert [x.name for x in chain.providers] == ["ollama"]


class FakeLLM:
    name = "fake"

    def __init__(self, answers):
        self.answers = list(answers)

    def complete(self, system, prompt):
        assert system == EXTRACTION_SYSTEM
        return self.answers.pop(0)


def test_extract_with_llm_valid_json():
    raw = json.dumps({
        "client_name": "Acme", "client_email": "a@example.com", "total": "400.00", "currency": "USD",
        "milestones": [{"title": "Work", "amount": "400.00", "currency": "USD", "due_date": "2026-12-01",
                        "evidence": "Work, USD 400, due 2026-12-01."}],
        "ambiguities": [],
    })
    plan = extract_with_llm(FakeLLM([raw]), SAMPLE_CONTRACT)
    assert plan.total == "400.00"


def test_extract_with_llm_repairs_once():
    good = json.dumps({
        "client_name": "Acme", "client_email": "a@example.com", "total": "400.00", "currency": "USD",
        "milestones": [{"title": "Work", "amount": "400.00", "currency": "USD", "due_date": "2026-12-01",
                        "evidence": "Work, USD 400, due 2026-12-01."}],
        "ambiguities": [],
    })
    plan = extract_with_llm(FakeLLM(["not json", good]), SAMPLE_CONTRACT)
    assert plan.total == "400.00"


def test_extract_with_llm_fails_after_two_bad_answers():
    with pytest.raises(ValueError, match="twice"):
        extract_with_llm(FakeLLM(["not json", "still not json"]), SAMPLE_CONTRACT)


def test_parse_plan_rejects_non_object():
    with pytest.raises(ValueError, match="not an object"):
        parse_plan("[1, 2]")


def test_parse_plan_strips_markdown_fence():
    raw = "```json\n" + json.dumps({
        "client_name": "Acme", "client_email": "a@example.com", "total": "400.00", "currency": "USD",
        "milestones": [{"title": "Work", "amount": "400.00", "currency": "USD", "due_date": "2026-12-01",
                        "evidence": "Work, USD 400, due 2026-12-01."}],
        "ambiguities": [],
    }) + "\n```"
    assert parse_plan(raw).total == "400.00"
