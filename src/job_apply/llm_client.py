"""Thin OpenAI SDK wrapper with the model policy baked in.

Per Draven's directive (memory: Model Policy 2026-04-15):
  - default daily driver: gpt-5.2-mini
  - cheap deterministic / extraction: gpt-4.1-mini
  - reserve gpt-5.4 for hard reasoning, opt-in only via tier="deep"

We expose three task tiers:
  - "extract"  -> gpt-4.1-mini    (job_analyzer)
  - "tailor"   -> gpt-5.2-mini    (resume_tailor, email_writer)
  - "deep"     -> gpt-5.4         (--deep retry)

Model names can be overridden via env so the policy can be tuned without code
changes if OpenAI renames a SKU.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Literal

from .config import load_env

Tier = Literal["extract", "tailor", "deep"]

DEFAULT_MODELS: dict[Tier, str] = {
    "extract": "gpt-4.1-mini",
    "tailor": "gpt-5.2-mini",
    "deep": "gpt-5.4",
}

ENV_OVERRIDES: dict[Tier, str] = {
    "extract": "JOB_APPLY_MODEL_EXTRACT",
    "tailor": "JOB_APPLY_MODEL_TAILOR",
    "deep": "JOB_APPLY_MODEL_DEEP",
}


def model_for(tier: Tier) -> str:
    load_env()
    return os.environ.get(ENV_OVERRIDES[tier], DEFAULT_MODELS[tier])


@dataclass
class LLMResponse:
    text: str
    model: str
    raw: Any | None = None

    def as_json(self) -> Any:
        """Best-effort JSON parse. Strips ```json fences if present."""
        s = self.text.strip()
        if s.startswith("```"):
            # strip first fence line and trailing fence
            lines = s.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]
            s = "\n".join(lines)
        return json.loads(s)


class LLMClient:
    def __init__(self) -> None:
        load_env()
        if not os.environ.get("OPENAI_API_KEY"):
            raise RuntimeError(
                "OPENAI_API_KEY not set. Add it to ~/.openclaw/.env or ./.env."
            )
        # Lazy import so tests can stub without openai installed.
        from openai import OpenAI  # type: ignore
        self._client = OpenAI()

    def complete(
        self,
        *,
        tier: Tier,
        system: str,
        user: str,
        json_mode: bool = False,
        temperature: float = 0.4,
    ) -> LLMResponse:
        model = model_for(tier)
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        resp = self._client.chat.completions.create(**kwargs)
        text = resp.choices[0].message.content or ""
        return LLMResponse(text=text, model=model, raw=resp)
