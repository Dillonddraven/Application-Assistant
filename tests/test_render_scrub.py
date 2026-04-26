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
