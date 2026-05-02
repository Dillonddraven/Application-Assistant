"""Synonym-aware skill matcher. User-editable cluster file at
`profile/skill_synonyms.yaml`. Each cluster is a list of equivalent terms;
the matcher considers a JD-required skill matched if any cluster member
matches a profile skill (or vice versa) by case-insensitive substring.

Falls back to plain substring matching when no cluster file is present.
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

import yaml

from .config import PROFILE_DIR

_DEFAULT_PATH = PROFILE_DIR / "skill_synonyms.yaml"


def load_clusters(path: Path | None = None) -> list[list[str]]:
    p = path or _DEFAULT_PATH
    if not p.exists():
        return []
    raw = yaml.safe_load(p.read_text()) or {}
    clusters = raw.get("clusters") or []
    out: list[list[str]] = []
    for cluster in clusters:
        if not isinstance(cluster, list):
            continue
        terms = [str(t).lower().strip() for t in cluster if isinstance(t, str)]
        terms = [t for t in terms if t]
        if len(terms) >= 2:
            out.append(terms)
    return out


def _term_matches_term(a: str, b: str) -> bool:
    """Case-insensitive substring match either direction."""
    a, b = a.lower(), b.lower()
    return a in b or b in a


def _term_matches_cluster(term: str, cluster: list[str]) -> bool:
    return any(_term_matches_term(term, c) for c in cluster)


def _normalize_clusters(clusters: list[list[str]]) -> list[list[str]]:
    """Lowercase + strip every cluster term so comparisons and outputs are
    consistent regardless of how the caller wrote the clusters."""
    out: list[list[str]] = []
    for c in clusters:
        if not isinstance(c, list):
            continue
        terms = [str(t).lower().strip() for t in c if isinstance(t, str)]
        terms = [t for t in terms if t]
        if terms:
            out.append(terms)
    return out


def expand_with_synonyms(
    profile_skills: Iterable[str], clusters: list[list[str]] | None = None,
) -> set[str]:
    """For each profile skill that hits any cluster, also include every other
    term in that cluster. Returns the expanded lowercased set."""
    if clusters is None:
        clusters = load_clusters()
    clusters = _normalize_clusters(clusters)
    base = {s.lower() for s in profile_skills if s}
    expanded = set(base)
    for cluster in clusters:
        if any(_term_matches_cluster(s, cluster) for s in base):
            expanded.update(cluster)
    return expanded


def matches_with_synonyms(
    needed: str, profile_skills: Iterable[str],
    clusters: list[list[str]] | None = None,
) -> bool:
    """True iff `needed` matches any profile skill, including via synonym clusters.

    Match logic:
      1. Direct substring (case-insensitive) against profile skills.
      2. If `needed` falls in a cluster AND any profile skill falls in the
         same cluster, that's a match too.
    """
    if clusters is None:
        clusters = load_clusters()
    clusters = _normalize_clusters(clusters)
    needed_lc = needed.lower().strip()
    if not needed_lc:
        return False

    profile_lc = [s.lower() for s in profile_skills if s]
    # Direct substring path (preserves old behavior).
    for ps in profile_lc:
        if needed_lc in ps or ps in needed_lc:
            return True

    # Synonym path: needed and at least one profile skill must share a cluster.
    for cluster in clusters:
        if not _term_matches_cluster(needed_lc, cluster):
            continue
        for ps in profile_lc:
            if _term_matches_cluster(ps, cluster):
                return True
    return False


def cluster_for_term(term: str, clusters: list[list[str]] | None = None) -> list[str]:
    """Return the cluster a term belongs to, or [] if it doesn't belong to one.
    Useful for explainability — the scorecard can say WHY a synonym matched."""
    if clusters is None:
        clusters = load_clusters()
    clusters = _normalize_clusters(clusters)
    for cluster in clusters:
        if _term_matches_cluster(term, cluster):
            return list(cluster)
    return []
