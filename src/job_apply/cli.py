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
    p_analyze.set_defaults(func=_stub("analyze", "M2"))

    p_rank = sub.add_parser("rank", help="Print ranked table of analyzed jobs.")
    p_rank.set_defaults(func=_stub("rank", "M2"))

    p_tailor = sub.add_parser("tailor", help="Generate tailored application packet.")
    p_tailor.add_argument("job_id")
    p_tailor.add_argument("--force", action="store_true", help="Tailor even on FILTER:AVOID jobs.")
    p_tailor.add_argument("--deep", action="store_true", help="Use higher-tier model on tough fits.")
    p_tailor.set_defaults(func=_stub("tailor", "M3"))

    p_review = sub.add_parser("review", help="Show packet contents + validation report.")
    p_review.add_argument("job_id")
    p_review.set_defaults(func=_stub("review", "M4"))

    p_approve = sub.add_parser("approve", help="Mark packet approved (no send).")
    p_approve.add_argument("job_id")
    p_approve.set_defaults(func=_stub("approve", "M4"))

    p_skip = sub.add_parser("skip", help="Mark packet skipped.")
    p_skip.add_argument("job_id")
    p_skip.set_defaults(func=_stub("skip", "M4"))

    p_queue = sub.add_parser("queue", help="List packets by status.")
    p_queue.add_argument("--status", choices=["draft", "approved", "skipped", "all"], default="all")
    p_queue.set_defaults(func=_stub("queue", "M4"))

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
