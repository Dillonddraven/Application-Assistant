from __future__ import annotations

from job_apply.render import _scrub_source_ids


def test_scrubs_parenthetical_source_id():
    s = "Built a tool (dillards_intern.b1) for management."
    assert _scrub_source_ids(s) == "Built a tool for management."


def test_scrubs_dotted_source_id_with_underscores():
    s = "Reference here (experience.dillards_intern.b2)."
    assert _scrub_source_ids(s) == "Reference here."


def test_scrubs_with_inner_whitespace():
    s = "Item ( dillards_intern.b1 ) here."
    assert _scrub_source_ids(s) == "Item here."


def test_does_not_strip_normal_parentheticals():
    s = "Built a tool (Python, OpenPyXL) for management."
    assert _scrub_source_ids(s) == "Built a tool (Python, OpenPyXL) for management."


def test_does_not_strip_year_parentheticals():
    s = "CompTIA Network+ (2024-08)."
    assert _scrub_source_ids(s) == "CompTIA Network+ (2024-08)."


def test_handles_multiple_in_one_string():
    s = "First (foo_bar.b1) and second (baz_qux.b2) refs."
    assert _scrub_source_ids(s) == "First and second refs."


def test_scrubs_single_token_id_when_known(workspace=None):
    from job_apply.render import _scrub_source_ids as scrub
    s = "Built a Centralized Logging Lab (proj_centralized_logging_lab) for the team."
    known = {"proj_centralized_logging_lab"}
    assert scrub(s, known) == "Built a Centralized Logging Lab for the team."


def test_does_not_scrub_unknown_single_token():
    """Without known_ids, single-token parentheticals stay (no false positives)."""
    from job_apply.render import _scrub_source_ids as scrub
    s = "Designed a (secure_workflow) for the client."
    assert scrub(s) == "Designed a (secure_workflow) for the client."


def test_collect_known_ids_from_profile():
    from job_apply.render import collect_known_ids
    profile_data = {
        "experience": [
            {"id": "dillards_intern",
             "bullets": [{"id": "dillards_intern.b1"}, {"id": "dillards_intern.b2"}]}
        ],
        "projects": [
            {"id": "proj_centralized_logging_lab"},
            {"id": "proj_app_finder"},
        ],
        "reusable_answers": {"why_security": "x", "how_coursework_prepared_me": "y"},
    }
    ids = collect_known_ids(profile_data)
    assert "dillards_intern" in ids
    assert "proj_centralized_logging_lab" in ids
    assert "proj_app_finder" in ids
    assert "why_security" in ids
    assert "how_coursework_prepared_me" in ids
    assert "dillards_intern.b1" in ids
    assert "b1" in ids  # tail also added
