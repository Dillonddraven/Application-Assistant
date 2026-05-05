"""LLM client with multi-provider support.

Two model tiers map to whatever model IDs the configured provider exposes:
  - "extract" -- cheap deterministic JSON extraction (job_analyzer)
  - "tailor"  -- daily driver for resume / email / outreach generation
  - "deep"    -- explicit `--deep` opt-in for tough fits

Provider is selected via the `LLM_PROVIDER` env var:
  - `openai`   (default)        -- uses OPENAI_API_KEY
  - `deepseek`                  -- uses DEEPSEEK_API_KEY, base_url
                                   https://api.deepseek.com/v1
  - `openai-compat`             -- bring your own LLM_BASE_URL +
                                   LLM_API_KEY (LM Studio, vLLM, Ollama
                                   running an OpenAI-compatible
                                   endpoint, etc.)
  - `anthropic`                 -- uses ANTHROPIC_API_KEY (separate SDK)

Per-tier model IDs default to sensible picks for each provider; override
with `JOB_APPLY_MODEL_EXTRACT` / `_TAILOR` / `_DEEP` env vars.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Literal

from .config import load_env

Tier = Literal["extract", "tailor", "deep"]


# --- per-provider defaults ---

PROVIDER_DEFAULTS: dict[str, dict[str, Any]] = {
    "openai": {
        "models": {
            "extract": "gpt-4.1-mini",
            "tailor": "gpt-5-mini",
            "deep": "gpt-5",
        },
        "base_url": None,
        "key_env": "OPENAI_API_KEY",
        "no_temperature_prefixes": ("gpt-5",),
    },
    "deepseek": {
        "models": {
            # DeepSeek public model IDs (chat/reasoner). Update if the user
            # explicitly wants V4 -- DeepSeek's API names tend to be
            # "deepseek-chat" / "deepseek-reasoner" with the latest version
            # served behind that name.
            "extract": "deepseek-chat",
            "tailor": "deepseek-chat",
            "deep": "deepseek-reasoner",
        },
        "base_url": "https://api.deepseek.com/v1",
        "key_env": "DEEPSEEK_API_KEY",
        "no_temperature_prefixes": (),
    },
    "openai-compat": {
        # Bring-your-own-endpoint (Ollama, LM Studio, vLLM, Together, etc.)
        "models": {
            "extract": "auto",
            "tailor": "auto",
            "deep": "auto",
        },
        "base_url": None,   # must be supplied via LLM_BASE_URL
        "key_env": "LLM_API_KEY",
        "no_temperature_prefixes": (),
    },
    "anthropic": {
        "models": {
            "extract": "claude-haiku-4-5",
            "tailor": "claude-sonnet-4-5",
            "deep": "claude-opus-4",
        },
        "base_url": None,
        "key_env": "ANTHROPIC_API_KEY",
        "no_temperature_prefixes": (),
    },
}

ENV_OVERRIDES: dict[Tier, str] = {
    "extract": "JOB_APPLY_MODEL_EXTRACT",
    "tailor": "JOB_APPLY_MODEL_TAILOR",
    "deep": "JOB_APPLY_MODEL_DEEP",
}


def _provider() -> str:
    load_env()
    return (os.environ.get("LLM_PROVIDER") or "openai").lower()


def model_for(tier: Tier) -> str:
    load_env()
    override = os.environ.get(ENV_OVERRIDES[tier])
    if override:
        return override
    prov = _provider()
    return PROVIDER_DEFAULTS.get(prov, PROVIDER_DEFAULTS["openai"])["models"][tier]


@dataclass
class LLMResponse:
    text: str
    model: str
    raw: Any | None = None

    def as_json(self) -> Any:
        """Best-effort JSON parse. Strips ```json fences if present."""
        s = self.text.strip()
        if s.startswith("```"):
            lines = s.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]
            s = "\n".join(lines)
        return json.loads(s)


# --- providers ---


class _OpenAICompatibleClient:
    """Used for `openai`, `deepseek`, and `openai-compat`. They all speak the
    OpenAI chat-completions wire format; only base_url / key / model IDs
    differ."""

    def __init__(self, *, base_url: str | None, api_key: str,
                  no_temperature_prefixes: tuple[str, ...]) -> None:
        from openai import OpenAI  # type: ignore
        kwargs: dict[str, Any] = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self._client = OpenAI(**kwargs)
        self._no_temp = no_temperature_prefixes

    def complete(self, *, model: str, system: str, user: str,
                  json_mode: bool, temperature: float) -> LLMResponse:
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if not any(model.startswith(p) for p in self._no_temp):
            kwargs["temperature"] = temperature
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        resp = self._client.chat.completions.create(**kwargs)
        text = resp.choices[0].message.content or ""
        return LLMResponse(text=text, model=model, raw=resp)


class _AnthropicClient:
    """Anthropic uses a different wire format; we adapt our (system, user,
    json_mode) interface to anthropic.messages.create.

    JSON mode: Anthropic doesn't have response_format, so we append a strict
    instruction to the system prompt asking for raw JSON only. The downstream
    `as_json()` parser already strips fences."""

    def __init__(self, *, api_key: str) -> None:
        from anthropic import Anthropic  # type: ignore
        self._client = Anthropic(api_key=api_key)

    def complete(self, *, model: str, system: str, user: str,
                  json_mode: bool, temperature: float) -> LLMResponse:
        sys_prompt = system
        if json_mode:
            sys_prompt = (
                system
                + "\n\nYou MUST return valid JSON only, no prose, no fences."
            )
        resp = self._client.messages.create(
            model=model, max_tokens=4096, temperature=temperature,
            system=sys_prompt,
            messages=[{"role": "user", "content": user}],
        )
        # Anthropic returns content blocks; concatenate text blocks.
        chunks = [c.text for c in resp.content if getattr(c, "type", "") == "text"]
        text = "".join(chunks)
        return LLMResponse(text=text, model=model, raw=resp)


class LLMClient:
    """Unified interface across providers. Constructed lazily so tests can
    skip provider auth."""

    def __init__(self) -> None:
        load_env()
        prov = _provider()
        defaults = PROVIDER_DEFAULTS.get(prov)
        if not defaults:
            raise RuntimeError(
                f"unknown LLM_PROVIDER {prov!r}; valid: "
                f"{', '.join(PROVIDER_DEFAULTS)}"
            )

        # Resolve base_url
        base_url = (defaults.get("base_url")
                    or os.environ.get("LLM_BASE_URL"))
        if prov == "openai-compat" and not base_url:
            raise RuntimeError(
                "LLM_PROVIDER=openai-compat requires LLM_BASE_URL "
                "(e.g. http://localhost:11434/v1 for Ollama)."
            )

        # Resolve API key
        key_env = defaults["key_env"]
        api_key = os.environ.get(key_env) or os.environ.get("LLM_API_KEY")
        if not api_key:
            raise RuntimeError(
                f"{key_env} not set (and no LLM_API_KEY fallback). "
                f"Add it to ./.env or export it in your shell."
            )

        if prov == "anthropic":
            self._impl = _AnthropicClient(api_key=api_key)
        else:
            self._impl = _OpenAICompatibleClient(
                base_url=base_url, api_key=api_key,
                no_temperature_prefixes=defaults["no_temperature_prefixes"],
            )

    def complete(
        self, *, tier: Tier, system: str, user: str,
        json_mode: bool = False, temperature: float = 0.4,
    ) -> LLMResponse:
        return self._impl.complete(
            model=model_for(tier), system=system, user=user,
            json_mode=json_mode, temperature=temperature,
        )
