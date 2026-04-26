"""Test scaffolding: redirect ROOT-derived paths into a per-test tmp dir.

Modules in src/job_apply/ derive paths from config.ROOT at import time. We
monkeypatch the path constants in config + state + profile_loader so each test
runs against an isolated workspace with no chance of touching real profile/
or jobs/ data.
"""
from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Return an isolated workspace dir; rebind module-level paths to live inside it."""
    from job_apply import config as cfg
    from job_apply import state as st
    from job_apply import profile_loader as pl

    profile_dir = tmp_path / "profile"
    samples_dir = profile_dir / "samples"
    jobs_dir = tmp_path / "jobs"
    raw = jobs_dir / "raw_posts"
    analyzed = jobs_dir / "analyzed"
    outputs = tmp_path / "outputs"
    for d in (profile_dir, samples_dir, raw, analyzed, outputs):
        d.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(cfg, "ROOT", tmp_path)
    monkeypatch.setattr(cfg, "PROFILE_DIR", profile_dir)
    monkeypatch.setattr(cfg, "PROFILE_PATH", profile_dir / "master_profile.yaml")
    monkeypatch.setattr(cfg, "SECRETS_PATH", profile_dir / "secrets.yaml")
    monkeypatch.setattr(cfg, "SAMPLE_PROFILE_PATH", samples_dir / "master_profile.example.yaml")
    monkeypatch.setattr(cfg, "SAMPLE_SECRETS_PATH", samples_dir / "secrets.example.yaml")
    monkeypatch.setattr(cfg, "JOBS_DIR", jobs_dir)
    monkeypatch.setattr(cfg, "RAW_POSTS_DIR", raw)
    monkeypatch.setattr(cfg, "ANALYZED_DIR", analyzed)
    monkeypatch.setattr(cfg, "INPUT_URLS_FILE", jobs_dir / "input_urls.txt")
    monkeypatch.setattr(cfg, "OUTPUTS_DIR", outputs)

    # Modules captured the constants at import time; rebind in those too.
    monkeypatch.setattr(st, "RAW_POSTS_DIR", raw)
    monkeypatch.setattr(st, "ANALYZED_DIR", analyzed)
    monkeypatch.setattr(st, "OUTPUTS_DIR", outputs)
    monkeypatch.setattr(pl, "PROFILE_PATH", profile_dir / "master_profile.yaml")
    monkeypatch.setattr(pl, "SECRETS_PATH", profile_dir / "secrets.yaml")

    return tmp_path
