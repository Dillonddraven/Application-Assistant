"""Tests for the multi-provider LLM client (no live network).

We don't actually call any LLM provider; we verify provider selection,
default model resolution, and env-override behavior by patching the
underlying OpenAI / Anthropic SDKs."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from job_apply import llm_client


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch):
    """Each test starts with NO LLM-related env vars set."""
    for k in (
        "LLM_PROVIDER", "LLM_BASE_URL", "LLM_API_KEY",
        "OPENAI_API_KEY", "DEEPSEEK_API_KEY", "ANTHROPIC_API_KEY",
        "JOB_APPLY_MODEL_EXTRACT",
        "JOB_APPLY_MODEL_TAILOR",
        "JOB_APPLY_MODEL_DEEP",
    ):
        monkeypatch.delenv(k, raising=False)
    # Reset the load_env idempotent flag so nothing leaks between tests
    import job_apply.config as cfg
    cfg._loaded = True   # already loaded once by import; tests below set env directly
    yield


# --- model_for ---

def test_model_for_openai_defaults(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    assert llm_client.model_for("extract") == "gpt-4.1-mini"
    assert llm_client.model_for("tailor") == "gpt-5-mini"
    assert llm_client.model_for("deep") == "gpt-5"


def test_model_for_deepseek_defaults(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    assert llm_client.model_for("extract") == "deepseek-chat"
    assert llm_client.model_for("tailor") == "deepseek-chat"
    assert llm_client.model_for("deep") == "deepseek-reasoner"


def test_model_for_anthropic_defaults(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    assert llm_client.model_for("tailor") == "claude-sonnet-4-5"
    assert llm_client.model_for("deep") == "claude-opus-4"


def test_model_for_env_override_wins(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("JOB_APPLY_MODEL_TAILOR", "gpt-5-fancy-test")
    assert llm_client.model_for("tailor") == "gpt-5-fancy-test"


def test_model_for_unknown_provider_falls_back_to_openai(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "totally-bogus")
    # No exception in model_for itself; it just falls through to openai defaults
    assert llm_client.model_for("extract") == "gpt-4.1-mini"


# --- provider construction ---

def test_openai_provider_uses_openai_api_key(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-1")
    fake_openai = MagicMock()
    with patch.dict("sys.modules", {"openai": MagicMock(OpenAI=fake_openai)}):
        llm_client.LLMClient()
    fake_openai.assert_called_once_with(api_key="sk-test-1")


def test_deepseek_provider_sets_base_url(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-deepseek-1")
    fake_openai = MagicMock()
    with patch.dict("sys.modules", {"openai": MagicMock(OpenAI=fake_openai)}):
        llm_client.LLMClient()
    fake_openai.assert_called_once_with(
        api_key="sk-deepseek-1",
        base_url="https://api.deepseek.com/v1",
    )


def test_openai_compat_requires_base_url(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai-compat")
    monkeypatch.setenv("LLM_API_KEY", "x")
    with pytest.raises(RuntimeError, match="LLM_BASE_URL"):
        llm_client.LLMClient()


def test_openai_compat_with_base_url(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai-compat")
    monkeypatch.setenv("LLM_BASE_URL", "http://localhost:11434/v1")
    monkeypatch.setenv("LLM_API_KEY", "ollama")
    fake_openai = MagicMock()
    with patch.dict("sys.modules", {"openai": MagicMock(OpenAI=fake_openai)}):
        llm_client.LLMClient()
    fake_openai.assert_called_once_with(
        api_key="ollama", base_url="http://localhost:11434/v1",
    )


def test_anthropic_provider_uses_anthropic_sdk(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-1")
    fake_anthropic = MagicMock()
    with patch.dict("sys.modules",
                     {"anthropic": MagicMock(Anthropic=fake_anthropic)}):
        llm_client.LLMClient()
    fake_anthropic.assert_called_once_with(api_key="sk-ant-1")


def test_missing_api_key_raises(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    # No OPENAI_API_KEY, no LLM_API_KEY
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY not set"):
        llm_client.LLMClient()


def test_unknown_provider_raises(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "fictional-provider")
    monkeypatch.setenv("OPENAI_API_KEY", "x")  # so we don't fail on missing key
    with pytest.raises(RuntimeError, match="unknown LLM_PROVIDER"):
        llm_client.LLMClient()


# --- complete (end-to-end with mocked SDK) ---

def test_complete_openai_omits_temperature_for_gpt5(monkeypatch):
    """gpt-5 family rejects custom temperature; client must not send it."""
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    fake_resp = MagicMock()
    fake_resp.choices = [MagicMock(message=MagicMock(content='{"ok": true}'))]
    fake_create = MagicMock(return_value=fake_resp)
    fake_client_instance = MagicMock()
    fake_client_instance.chat.completions.create = fake_create
    fake_openai = MagicMock(return_value=fake_client_instance)
    with patch.dict("sys.modules", {"openai": MagicMock(OpenAI=fake_openai)}):
        c = llm_client.LLMClient()
        c.complete(tier="tailor", system="s", user="u", temperature=0.5)
    kwargs = fake_create.call_args.kwargs
    assert kwargs["model"] == "gpt-5-mini"
    assert "temperature" not in kwargs


def test_complete_deepseek_passes_temperature(monkeypatch):
    """DeepSeek accepts temperature; client should pass it through."""
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    fake_resp = MagicMock()
    fake_resp.choices = [MagicMock(message=MagicMock(content="ok"))]
    fake_create = MagicMock(return_value=fake_resp)
    fake_client_instance = MagicMock()
    fake_client_instance.chat.completions.create = fake_create
    fake_openai = MagicMock(return_value=fake_client_instance)
    with patch.dict("sys.modules", {"openai": MagicMock(OpenAI=fake_openai)}):
        c = llm_client.LLMClient()
        c.complete(tier="tailor", system="s", user="u", temperature=0.5)
    kwargs = fake_create.call_args.kwargs
    assert kwargs["temperature"] == 0.5
    assert kwargs["model"] == "deepseek-chat"


def test_complete_json_mode_added_for_openai(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    fake_resp = MagicMock()
    fake_resp.choices = [MagicMock(message=MagicMock(content='{"ok": true}'))]
    fake_create = MagicMock(return_value=fake_resp)
    fake_client_instance = MagicMock()
    fake_client_instance.chat.completions.create = fake_create
    fake_openai = MagicMock(return_value=fake_client_instance)
    with patch.dict("sys.modules", {"openai": MagicMock(OpenAI=fake_openai)}):
        c = llm_client.LLMClient()
        c.complete(tier="extract", system="s", user="u", json_mode=True)
    kwargs = fake_create.call_args.kwargs
    assert kwargs["response_format"] == {"type": "json_object"}


def test_anthropic_json_mode_appends_system_instruction(monkeypatch):
    """Anthropic doesn't support response_format; we adapt by appending a
    JSON-only instruction to the system prompt."""
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant")
    fake_resp = MagicMock()
    fake_resp.content = [MagicMock(type="text", text='{"ok":true}')]
    fake_create = MagicMock(return_value=fake_resp)
    fake_client_instance = MagicMock()
    fake_client_instance.messages.create = fake_create
    fake_anthropic = MagicMock(return_value=fake_client_instance)
    with patch.dict("sys.modules",
                     {"anthropic": MagicMock(Anthropic=fake_anthropic)}):
        c = llm_client.LLMClient()
        out = c.complete(tier="tailor", system="be helpful",
                          user="u", json_mode=True)
    kwargs = fake_create.call_args.kwargs
    assert "JSON" in kwargs["system"]
    assert out.text == '{"ok":true}'
