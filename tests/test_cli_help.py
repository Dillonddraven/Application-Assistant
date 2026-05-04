"""M0 smoke test: --help works and lists the expected subcommands."""
from __future__ import annotations

import subprocess
import sys


def test_help_lists_subcommands():
    r = subprocess.run(
        [sys.executable, "-m", "job_apply.cli", "--help"],
        capture_output=True,
        text=True,
        check=True,
    )
    out = r.stdout
    for cmd in ("ingest", "analyze", "rank", "tailor", "review", "approve", "skip", "queue"):
        assert cmd in out, f"missing subcommand in --help: {cmd}"


def test_help_lists_v1_usage_subcommands():
    """V1 usage upgrade added: set-status, pack, pack-company, finder-approve, email."""
    r = subprocess.run(
        [sys.executable, "-m", "job_apply.cli", "--help"],
        capture_output=True, text=True, check=True,
    )
    for cmd in ("set-status", "pack", "pack-company", "finder-approve", "email"):
        assert cmd in r.stdout, f"missing v1-usage subcommand in --help: {cmd}"


def test_no_args_prints_help():
    r = subprocess.run(
        [sys.executable, "-m", "job_apply.cli"],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0
    assert "ingest" in r.stdout
