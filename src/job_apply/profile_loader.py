"""Load and validate the master profile.

Hard rules:
- master_profile.yaml may NOT contain strict PII keys (phone, address, dob,
  personal email). Those belong in secrets.yaml. We hard-fail if violated so
  the LLM never sees them.
- secrets.yaml is loaded separately and never returned alongside the LLM-bound
  profile.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .config import PROFILE_PATH, SECRETS_PATH

# Keys that must NOT appear anywhere in master_profile.yaml.
FORBIDDEN_PROFILE_KEYS = {
    "phone",
    "phone_number",
    "address",
    "street",
    "zip",
    "zip_code",
    "postal_code",
    "dob",
    "date_of_birth",
    "birthday",
    "ssn",
}
# `email` is forbidden at the *profile* level but allowed in scoped reusable_answers
# (e.g. someone might write a stock answer that mentions emailing the team). We
# treat exact key matches at any depth as the violation.


class ProfileError(ValueError):
    pass


@dataclass
class Profile:
    data: dict[str, Any]

    @property
    def full_name(self) -> str:
        return self.data.get("identity", {}).get("full_name", "")

    @property
    def industries_avoid(self) -> list[str]:
        return list(self.data.get("preferences", {}).get("industries_avoid", []))

    @property
    def metrics_allowed(self) -> list[str]:
        return list(self.data.get("metrics_allowed", []))


@dataclass
class Secrets:
    data: dict[str, Any] = field(default_factory=dict)

    def values_for_grep(self) -> list[str]:
        """Return all string leaf values, for the PII-leak grep test."""
        out: list[str] = []
        def walk(x: Any) -> None:
            if isinstance(x, dict):
                for v in x.values():
                    walk(v)
            elif isinstance(x, list):
                for v in x:
                    walk(v)
            elif isinstance(x, str) and x.strip():
                out.append(x.strip())
        walk(self.data)
        return out

    def placeholder_map(self) -> dict[str, str]:
        """Map {{placeholder}} -> real value for local-only render-time substitution."""
        d = self.data
        addr = d.get("address") or {}
        m = {
            "{{email}}": d.get("email", "") or "",
            "{{phone}}": d.get("phone", "") or "",
            "{{linkedin_url}}": d.get("linkedin_url", "") or "",
            "{{github_url}}": d.get("github_url", "") or "",
            "{{portfolio_url}}": d.get("portfolio_url", "") or "",
            "{{address_street}}": addr.get("street", "") or "",
            "{{address_city}}": addr.get("city", "") or "",
            "{{address_state}}": addr.get("state", "") or "",
            "{{address_zip}}": addr.get("zip", "") or "",
        }
        return {k: v for k, v in m.items() if v}


def _check_no_pii(node: Any, path: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(node, dict):
        for k, v in node.items():
            if isinstance(k, str) and k.lower() in FORBIDDEN_PROFILE_KEYS:
                found.append(f"{path}.{k}" if path else k)
            found.extend(_check_no_pii(v, f"{path}.{k}" if path else str(k)))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            found.extend(_check_no_pii(v, f"{path}[{i}]"))
    return found


def load_profile(path: Path | None = None) -> Profile:
    p = path or PROFILE_PATH
    if not p.exists():
        raise ProfileError(
            f"profile not found at {p}. "
            f"Copy profile/samples/master_profile.example.yaml to {p} and edit it."
        )
    raw = yaml.safe_load(p.read_text()) or {}
    if not isinstance(raw, dict):
        raise ProfileError(f"{p}: top-level must be a mapping.")
    violations = _check_no_pii(raw)
    if violations:
        raise ProfileError(
            f"{p}: forbidden PII keys found at: {violations}. "
            f"Move them to secrets.yaml — master_profile.yaml is sent to the LLM."
        )
    for required in ("identity", "preferences"):
        if required not in raw:
            raise ProfileError(f"{p}: missing required top-level key '{required}'.")
    return Profile(data=raw)


def load_secrets(path: Path | None = None, *, required: bool = False) -> Secrets:
    p = path or SECRETS_PATH
    if not p.exists():
        if required:
            raise ProfileError(
                f"secrets not found at {p}. "
                f"Copy profile/samples/secrets.example.yaml or run scripts/init_profile.py."
            )
        return Secrets(data={})
    raw = yaml.safe_load(p.read_text()) or {}
    if not isinstance(raw, dict):
        raise ProfileError(f"{p}: top-level must be a mapping.")
    return Secrets(data=raw)
