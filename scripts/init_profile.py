#!/usr/bin/env python3
"""Interactive helper to create profile/secrets.yaml from the sample.

Career facts (master_profile.yaml) you should edit by hand — the structure
matters. This script just collects strict PII into secrets.yaml so you don't
have to hand-type YAML for it.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_PROFILE = ROOT / "profile" / "samples" / "master_profile.example.yaml"
SAMPLE_SECRETS = ROOT / "profile" / "samples" / "secrets.example.yaml"
OUT_PROFILE = ROOT / "profile" / "master_profile.yaml"
OUT_SECRETS = ROOT / "profile" / "secrets.yaml"


def prompt(label: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default else ""
    val = input(f"{label}{suffix}: ").strip()
    return val or (default or "")


def main() -> int:
    if not OUT_PROFILE.exists():
        shutil.copy(SAMPLE_PROFILE, OUT_PROFILE)
        print(f"copied {SAMPLE_PROFILE.name} -> {OUT_PROFILE}")
        print("edit it by hand: it has placeholders for school name, dates, real bullets.")
    else:
        print(f"{OUT_PROFILE} already exists, leaving alone.")

    if OUT_SECRETS.exists():
        ans = input(f"{OUT_SECRETS} exists. Overwrite? [y/N] ").strip().lower()
        if ans != "y":
            print("keeping existing secrets.yaml.")
            return 0

    print("\nEnter your contact info (stays local, never sent to LLM):")
    secrets = {
        "email": prompt("Email"),
        "phone": prompt("Phone"),
        "address": {
            "street": prompt("Street"),
            "city": prompt("City"),
            "state": prompt("State (2-letter)"),
            "zip": prompt("ZIP"),
        },
        "linkedin_url": prompt("LinkedIn URL", default=""),
        "github_url": prompt("GitHub URL", default=""),
        "portfolio_url": prompt("Portfolio URL", default="") or None,
        "birthday": None,
    }
    OUT_SECRETS.write_text(yaml.safe_dump(secrets, sort_keys=False))
    OUT_SECRETS.chmod(0o600)
    print(f"\nwrote {OUT_SECRETS} (mode 0600).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
