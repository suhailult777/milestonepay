import pytest

from app import config

KEYS = [
    "MP_MODE", "PAYPAL_CLIENT_ID", "PAYPAL_CLIENT_SECRET", "PAYPAL_WEBHOOK_ID",
    "PAYPAL_MERCHANT_EMAIL", "LLM_PROVIDER", "LLM_BASE_URL", "LLM_MODEL",
    "OPENROUTER_ENV_FILE", "OPENROUTER_MODEL", "OPENROUTER_PRESET",
    "OPENROUTER_FALLBACKS", "OPENROUTER_TIMEOUT", "MP_DB",
]


def clear(monkeypatch):
    for key in KEYS:
        monkeypatch.delenv(key, raising=False)


def test_defaults_are_sample_and_keyless(monkeypatch):
    clear(monkeypatch)
    s = config.load()
    assert s.mode == "sample"
    assert s.llm_provider == "sample"
    assert s.openrouter_env_file.endswith(".env.openrouter")
    assert "milestonepay_secrets" in s.openrouter_env_file
    assert s.paypal_base == "https://api-m.sandbox.paypal.com"


def test_invalid_mode_rejected(monkeypatch):
    clear(monkeypatch)
    monkeypatch.setenv("MP_MODE", "production")
    with pytest.raises(ValueError, match="sample or live"):
        config.load()


def test_invalid_provider_rejected(monkeypatch):
    clear(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "magic")
    with pytest.raises(ValueError, match="LLM_PROVIDER"):
        config.load()


def test_live_mode_requires_paypal_values(monkeypatch):
    clear(monkeypatch)
    monkeypatch.setenv("MP_MODE", "live")
    with pytest.raises(ValueError, match="PAYPAL_CLIENT_ID"):
        config.load()


def test_live_mode_accepts_complete_sandbox_env(monkeypatch):
    clear(monkeypatch)
    for key, value in {
        "MP_MODE": "live",
        "PAYPAL_CLIENT_ID": "id",
        "PAYPAL_CLIENT_SECRET": "secret",
        "PAYPAL_WEBHOOK_ID": "POLL_ONLY_NO_WEBHOOK",
        "PAYPAL_MERCHANT_EMAIL": "merchant@example.com",
        "LLM_PROVIDER": "auto",
    }.items():
        monkeypatch.setenv(key, value)
    s = config.load()
    assert s.mode == "live" and s.llm_provider == "auto"
    assert "sandbox" in s.paypal_base


def test_openrouter_overrides_parse(monkeypatch):
    clear(monkeypatch)
    monkeypatch.setenv("OPENROUTER_ENV_FILE", "/tmp/keyfile")
    monkeypatch.setenv("OPENROUTER_PRESET", "demo")
    monkeypatch.setenv("OPENROUTER_FALLBACKS", "a:free,b:free")
    monkeypatch.setenv("OPENROUTER_TIMEOUT", "12.5")
    s = config.load()
    assert s.openrouter_env_file == "/tmp/keyfile"
    assert s.openrouter_preset == "demo"
    assert s.openrouter_fallbacks == "a:free,b:free"
    assert s.openrouter_timeout == 12.5
