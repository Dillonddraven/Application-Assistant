"""Argparse entry point.

Subcommands are wired up by milestone; M0 ships with --help and stubs that
report which milestone implements them. Each milestone fills its own handlers.
"""
from __future__ import annotations

import argparse
import sys

from . import __version__


def _stub(name: str, milestone: str):
    def handler(args: argparse.Namespace) -> int:
        print(f"`{name}` is implemented in milestone {milestone}; not wired yet.")
        return 2
    return handler


def _cmd_ingest(args: argparse.Namespace) -> int:
    from . import job_ingest
    try:
        result = job_ingest.ingest(args.source, refresh=args.refresh)
    except job_ingest.IngestError as e:
        print(f"ingest failed: {e}", file=sys.stderr)
        return 1
    rec = result.record
    state_word = "cached" if result.cached else "saved"
    src = rec.source_url or rec.source_kind
    print(f"{state_word} job_id={rec.job_id}  source={src}  text={rec.raw_text_path}")
    return 0


def _cmd_analyze(args: argparse.Namespace) -> int:
    from . import job_analyzer
    from .profile_loader import ProfileError
    try:
        results = job_analyzer.analyze_all(only_id=args.id, refresh=args.refresh)
    except ProfileError as e:
        print(f"profile error: {e}", file=sys.stderr)
        return 1
    if not results:
        print("nothing to analyze (everything already analyzed; use --refresh to redo).")
        return 0
    for r in results:
        flag = ""
        if r["industry_filter"] == "avoid":
            flag = "  [FILTER:AVOID]"
        elif r["industry_filter"] == "review":
            flag = "  [FILTER:REVIEW]"
        print(f"analyzed {r['id']}  fit={r['fit_score']:3d}  {r['company']} — {r['title']}{flag}")
    return 0


def _cmd_rank(args: argparse.Namespace) -> int:
    from . import rank as rank_mod
    print(rank_mod.render_table(rank_mod.ranked()))
    return 0


def _cmd_tailor(args: argparse.Namespace) -> int:
    from . import tailor_pipeline
    try:
        packet, slug = tailor_pipeline.run_tailor(
            job_id=args.job_id, force=args.force, deep=args.deep,
        )
    except tailor_pipeline.TailorError as e:
        print(f"tailor failed: {e}", file=sys.stderr)
        return 1
    val = packet["validation"]
    blocks = val.get("fabrication_blocks") or []
    warns = val.get("fabrication_warnings") or []
    print(f"packet drafted: outputs/{slug}/")
    print(f"  resume: outputs/{slug}/tailored_resume.md")
    print(f"  cover:  outputs/{slug}/cover_letter.md")
    print(f"  emails: outreach_recruiter.md, outreach_hiring_manager.md, linkedin_dm.md")
    print(f"  report: outputs/{slug}/match_report.md")
    if blocks:
        print(f"\n  ⚠ {len(blocks)} fabrication BLOCKS — fix before approving:")
        for b in blocks[:5]:
            print(f"    - [{b['rule']}] {b['detail']}")
        if len(blocks) > 5:
            print(f"    … and {len(blocks) - 5} more (see match_report.md).")
    if warns:
        print(f"  ℹ {len(warns)} warnings (non-blocking).")
    return 0 if not blocks else 2


def _cmd_review(args: argparse.Namespace) -> int:
    from . import approval_queue
    try:
        print(approval_queue.review(args.job_id))
    except approval_queue.ApprovalError as e:
        print(f"review failed: {e}", file=sys.stderr)
        return 1
    return 0


def _cmd_approve(args: argparse.Namespace) -> int:
    from . import approval_queue
    try:
        pkt = approval_queue.approve(args.job_id)
    except approval_queue.ApprovalError as e:
        print(f"approve refused: {e}", file=sys.stderr)
        return 2
    print(f"approved: {pkt['slug']}  (status={pkt['status']})  [no message sent — manual upload/send]")
    return 0


def _cmd_skip(args: argparse.Namespace) -> int:
    from . import approval_queue
    try:
        pkt = approval_queue.skip(args.job_id)
    except approval_queue.ApprovalError as e:
        print(f"skip failed: {e}", file=sys.stderr)
        return 1
    print(f"skipped: {pkt['slug']}")
    return 0


def _cmd_queue(args: argparse.Namespace) -> int:
    from . import approval_queue
    rows = approval_queue.queue(args.status)
    print(approval_queue.render_queue_table(rows))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="job-apply",
        description="Local-first job application assistant (approval-gated, no-fabrication).",
    )
    p.add_argument("--version", action="version", version=f"job-apply {__version__}")
    sub = p.add_subparsers(dest="cmd", metavar="<command>")
    sub.required = False

    p_ingest = sub.add_parser("ingest", help="Fetch or load a job posting (URL or file).")
    p_ingest.add_argument("source", help="URL or path to a .txt/.md job posting.")
    p_ingest.add_argument("--refresh", action="store_true", help="Re-fetch even if cached.")
    p_ingest.set_defaults(func=_cmd_ingest)

    p_analyze = sub.add_parser("analyze", help="LLM-extract structured fields + fit score.")
    p_analyze.add_argument("--id", help="Specific job id; default: all unanalyzed.")
    p_analyze.add_argument("--refresh", action="store_true", help="Re-analyze even if cached.")
    p_analyze.set_defaults(func=_cmd_analyze)

    p_rank = sub.add_parser("rank", help="Print ranked table of analyzed jobs.")
    p_rank.set_defaults(func=_cmd_rank)

    p_tailor = sub.add_parser("tailor", help="Generate tailored application packet.")
    p_tailor.add_argument("job_id")
    p_tailor.add_argument("--force", action="store_true", help="Tailor even on FILTER:AVOID jobs.")
    p_tailor.add_argument("--deep", action="store_true", help="Use higher-tier model on tough fits.")
    p_tailor.set_defaults(func=_cmd_tailor)

    p_review = sub.add_parser("review", help="Show packet contents + validation report.")
    p_review.add_argument("job_id", help="Packet slug or 12-char job id.")
    p_review.set_defaults(func=_cmd_review)

    p_approve = sub.add_parser("approve", help="Mark packet approved (no send).")
    p_approve.add_argument("job_id", help="Packet slug or 12-char job id.")
    p_approve.set_defaults(func=_cmd_approve)

    p_skip = sub.add_parser("skip", help="Mark packet skipped.")
    p_skip.add_argument("job_id", help="Packet slug or 12-char job id.")
    p_skip.set_defaults(func=_cmd_skip)

    p_queue = sub.add_parser("queue", help="List packets by status.")
    p_queue.add_argument("--status", choices=["draft", "approved", "skipped", "all"], default="all")
    p_queue.set_defaults(func=_cmd_queue)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.cmd:
        parser.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
