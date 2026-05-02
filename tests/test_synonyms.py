"""Tests for the synonym-aware skill matcher."""
from __future__ import annotations

from pathlib import Path

import yaml

from job_apply.synonyms import (
    cluster_for_term, expand_with_synonyms, load_clusters,
    matches_with_synonyms,
)


SAMPLE_CLUSTERS = [
    ["SIEM", "Graylog", "OpenSearch", "Splunk", "Microsoft Sentinel"],
    ["log monitoring", "rsyslog", "NXLog", "fluentd"],
    ["phishing analysis", "phishing recognition", "phishing lab",
     "Security+ labs", "suspicious email review"],
    ["vulnerability management", "Nessus", "Qualys", "Tenable"],
]


def test_direct_substring_match():
    assert matches_with_synonyms("Python", ["Python", "Linux"], SAMPLE_CLUSTERS)


def test_jd_siem_matches_profile_graylog():
    """The Soro motivation: JD says 'SIEM', profile says 'Graylog'."""
    assert matches_with_synonyms("SIEM", ["Graylog logging lab"], SAMPLE_CLUSTERS)


def test_jd_log_monitoring_matches_profile_rsyslog():
    assert matches_with_synonyms(
        "log monitoring", ["rsyslog/NXLog forwarding"], SAMPLE_CLUSTERS,
    )


def test_jd_phishing_matches_profile_phishing_lab():
    """The new phishing evidence test."""
    assert matches_with_synonyms(
        "phishing analysis",
        ["Phishing recognition (lab)", "Suspicious email review (lab)"],
        SAMPLE_CLUSTERS,
    )


def test_unrelated_terms_dont_match_via_clusters():
    assert not matches_with_synonyms(
        "Kubernetes operator", ["Python", "Linux"], SAMPLE_CLUSTERS,
    )


def test_empty_profile_skills_returns_false():
    assert not matches_with_synonyms("SIEM", [], SAMPLE_CLUSTERS)


def test_empty_needed_returns_false():
    assert not matches_with_synonyms("", ["SIEM", "Python"], SAMPLE_CLUSTERS)


def test_expand_includes_cluster_members():
    """If a profile skill is in a cluster, all members are also in expanded set."""
    expanded = expand_with_synonyms(["Graylog"], SAMPLE_CLUSTERS)
    for term in ["siem", "graylog", "opensearch", "splunk", "microsoft sentinel"]:
        assert term in expanded, f"missing {term!r} in expansion"


def test_expand_skips_clusters_with_no_overlap():
    expanded = expand_with_synonyms(["Python"], SAMPLE_CLUSTERS)
    # Python isn't in any of these sample clusters, so expansion equals the input
    assert expanded == {"python"}


def test_cluster_for_term_returns_cluster():
    assert "siem" in cluster_for_term("Graylog", SAMPLE_CLUSTERS)
    assert "phishing analysis" in cluster_for_term("Security+ labs", SAMPLE_CLUSTERS)


def test_cluster_for_term_returns_empty_for_unknown():
    assert cluster_for_term("totally unrelated string", SAMPLE_CLUSTERS) == []


def test_load_clusters_skips_malformed_entries(tmp_path: Path):
    f = tmp_path / "synonyms.yaml"
    f.write_text(yaml.safe_dump({
        "clusters": [
            ["SIEM", "Graylog", "Splunk"],   # OK
            ["only one term"],                # too small, skip
            "not a list",                     # invalid, skip
            [],                               # empty, skip
        ]
    }))
    clusters = load_clusters(f)
    assert len(clusters) == 1
    assert "siem" in clusters[0]
    assert "graylog" in clusters[0]


def test_load_clusters_missing_file_returns_empty(tmp_path: Path):
    assert load_clusters(tmp_path / "nonexistent.yaml") == []


def test_match_is_case_insensitive():
    assert matches_with_synonyms("siem", ["GRAYLOG LAB"], SAMPLE_CLUSTERS)
    assert matches_with_synonyms("SIEM", ["graylog lab"], SAMPLE_CLUSTERS)
