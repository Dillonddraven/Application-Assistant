from __future__ import annotations

from pathlib import Path

from job_apply import state as st


def test_job_id_url_canonicalization(workspace: Path):
    a = st.job_id_for("https://x.com/job", is_url=True)
    b = st.job_id_for("HTTPS://X.COM/JOB", is_url=True)
    c = st.job_id_for("  https://x.com/job  ", is_url=True)
    assert a == b == c
    assert len(a) == 12


def test_job_id_text_canonicalization(workspace: Path):
    a = st.job_id_for("Senior  Analyst\n\nrole", is_url=False)
    b = st.job_id_for("Senior Analyst role", is_url=False)
    assert a == b


def test_save_and_load_ingest_roundtrip(workspace: Path):
    rec = st.save_ingest(
        job_id="abc123def456",
        text="hello posting",
        source_url="https://x.com/job",
        source_kind="url",
    )
    assert rec.text == "hello posting"
    loaded = st.load_ingest("abc123def456")
    assert loaded is not None
    assert loaded.source_url == "https://x.com/job"
    assert loaded.source_kind == "url"
    assert loaded.text == "hello posting"


def test_list_ingests(workspace: Path):
    st.save_ingest(job_id="aaaaaaaaaaaa", text="t1", source_url="u1", source_kind="url")
    st.save_ingest(job_id="bbbbbbbbbbbb", text="t2", source_url="u2", source_kind="url")
    all_ = st.list_ingests()
    assert {r.job_id for r in all_} == {"aaaaaaaaaaaa", "bbbbbbbbbbbb"}


def test_analyzed_roundtrip(workspace: Path):
    st.save_analyzed("xxxxxxxxxxxx", {"id": "xxxxxxxxxxxx", "company": "Acme"})
    got = st.load_analyzed("xxxxxxxxxxxx")
    assert got and got["company"] == "Acme"


def test_packet_paths_and_slug(workspace: Path):
    s = st.packet_slug("Acme Corp", "Senior Security Analyst")
    assert s == "acme-corp_senior-security-analyst"
    st.save_packet(s, {"slug": s, "job_id": "abc", "status": "draft"})
    pkt = st.load_packet(s)
    assert pkt and pkt["status"] == "draft"
    assert st.find_slug_by_job_id("abc") == s


def test_atomic_writes_no_temp_left(workspace: Path):
    st.save_ingest(job_id="cccccccccccc", text="t", source_url=None, source_kind="stdin")
    leftovers = list((workspace / "jobs" / "raw_posts").glob("*.tmp"))
    assert leftovers == []
