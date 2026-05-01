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
            open_mail=args.mail, mode=args.mode,
        )
    except tailor_pipeline.TailorError as e:
        print(f"tailor failed: {e}", file=sys.stderr)
        return 1
    val = packet["validation"]
    blocks = val.get("fabrication_blocks") or []
    warns = val.get("fabrication_warnings") or []
    is_blocked = bool(packet.get("blocked"))
    print(f"packet drafted: outputs/{slug}/  run_id={packet.get('run_id', '?')}")
    if is_blocked:
        print(f"  ⛔ BLOCKED — employer renders and Mail draft suppressed.")
        reasons = packet.get("block_reasons", {})
        for issue in reasons.get("high_qa_issues") or []:
            print(f"    [HIGH/{issue.get('category')}] {issue.get('where', '')}")
            fix = (issue.get("fix_suggestion") or "").strip()
            if fix:
                print(f"      fix: {fix[:200]}")
        for fb in reasons.get("fabrication_blocks") or []:
            print(f"    [FAB/{fb.get('rule')}] {fb.get('detail', '')}")
        print(f"  Internal review files: outputs/{slug}/internal/")
        print(f"  Fix the issues, edit profile if needed, then re-run tailor.")
    else:
        print(f"  employer: outputs/{slug}/employer/  (PDF resume + cover letter)")
        print(f"  internal: outputs/{slug}/internal/  (markdown views, qa_report.md, evidence_map.json, match_report.md)")
    from . import state as _state
    analyzed = _state.load_analyzed(packet["job_id"])
    if analyzed:
        sc = analyzed.get("source_confidence")
        if sc == "low":
            reason = analyzed.get("source_confidence_reason") or ""
            print(f"  ⚠ source confidence: LOW — {reason}")
            print(f"     Consider applying via the company's direct careers page if you can find it.")
        elif sc == "medium":
            reason = analyzed.get("source_confidence_reason") or ""
            print(f"  ℹ source confidence: medium — {reason}")
    if blocks:
        print(f"\n  ⚠ {len(blocks)} fabrication BLOCKS:")
        for b in blocks[:5]:
            print(f"    - [{b['rule']}] {b['detail']}")
        if len(blocks) > 5:
            print(f"    … and {len(blocks) - 5} more (see match_report.md).")
    if warns:
        print(f"  ℹ {len(warns)} fabrication warnings (non-blocking).")
    qa = val.get("qa") or {}
    qa_issues = qa.get("issues") or []
    if qa:
        polish = qa.get("overall_polish", "ready")
        print(f"  QA polish: {polish} ({len(qa_issues)} issue(s) — see internal/qa_report.md)")
    return 2 if is_blocked else 0


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


def _cmd_track_list(args: argparse.Namespace) -> int:
    from . import tracker
    rows = tracker.list_rows(status=args.status if args.status != "all" else None)
    print(tracker.render_table(rows))
    return 0


def _cmd_track_status(args: argparse.Namespace) -> int:
    from . import tracker
    try:
        row = tracker.set_status(
            ident=args.ident, new_status=args.new_status, notes=args.notes or "",
        )
    except tracker.TrackerError as e:
        print(f"track-status failed: {e}", file=sys.stderr)
        return 1
    print(f"{row['slug']} -> {row['status']}  (next_followup: {row.get('next_followup_date') or '—'})")
    return 0


def _cmd_track_followup(args: argparse.Namespace) -> int:
    from . import tracker
    rows = tracker.due_followups()
    if not rows:
        print("(no follow-ups due)")
        return 0
    print(f"{len(rows)} follow-up(s) due:")
    print(tracker.render_table(rows))
    return 0


def _cmd_track_add(args: argparse.Namespace) -> int:
    from . import approval_queue, state, tracker
    try:
        slug, packet = approval_queue._resolve(args.ident)
    except approval_queue.ApprovalError as e:
        print(f"track-add failed: {e}", file=sys.stderr)
        return 1
    analyzed = state.load_analyzed(packet.get("job_id"))
    row = tracker.upsert(packet=packet, analyzed=analyzed, status=args.status)
    print(f"tracked: {row['slug']}  status={row['status']}  applied_date={row['applied_date']}")
    return 0


def _cmd_send_outreach(args: argparse.Namespace) -> int:
    """Open a Mail.app draft addressed to a recruiter or hiring manager,
    using one of the generated outreach variants and ONLY employer/ attachments.

    Blocked packets (HIGH-severity QA issues or fabrication blocks) are refused
    unless --force is passed. DOCX attachments are off by default (employer
    portals usually accept PDF; some explicitly request DOCX — use --include-docx).
    """
    from . import approval_queue, mail_draft, state
    try:
        slug, packet = approval_queue._resolve(args.ident)
    except approval_queue.ApprovalError as e:
        print(f"send-outreach failed: {e}", file=sys.stderr)
        return 1
    if packet.get("blocked") and not args.force:
        reasons = packet.get("block_reasons", {})
        high = reasons.get("high_qa_issues") or []
        fab = reasons.get("fabrication_blocks") or []
        print(
            f"send-outreach refused: packet is BLOCKED "
            f"({len(high)} high QA issue(s), {len(fab)} fabrication block(s)). "
            f"Re-run tailor after fixing, or pass --force to override.",
            file=sys.stderr,
        )
        return 2
    emails = packet.get("emails") or {}
    variant = emails.get(args.variant)
    if not variant:
        print(f"send-outreach: no `{args.variant}` email found in packet (re-run tailor).",
              file=sys.stderr)
        return 1
    subject = variant.get("subject") or ""
    body_paragraphs = variant.get("body_paragraphs") or []
    body_text = "\n\n".join(
        p.get("text", "") for p in body_paragraphs if isinstance(p, dict)
    ).strip()
    if not body_text:
        print("send-outreach: empty body — packet's variant has no paragraphs.",
              file=sys.stderr)
        return 1
    out_dir = state.packet_dir(slug)
    attachments = mail_draft.packet_attachments(
        out_dir, mode="employer", include_docx=args.include_docx,
    )
    if not attachments:
        print(f"send-outreach: no employer-facing attachments found in {out_dir / 'employer'}",
              file=sys.stderr)
        return 1
    run_id = packet.get("run_id", "")
    stamped_subject = mail_draft.stamp_subject(subject, run_id)
    try:
        mail_draft.open_draft(
            to_addr=args.to, subject=stamped_subject, body=body_text,
            attachments=attachments,
        )
    except mail_draft.MailDraftError as e:
        print(f"send-outreach failed: {e}", file=sys.stderr)
        return 1
    print(f"draft opened to {args.to}  variant={args.variant}  attachments={len(attachments)}")
    print(f"  run id: {run_id}")
    print("(NOT sent. Review in Mail and click Send when ready.)")
    return 0


def _cmd_close_drafts(args: argparse.Namespace) -> int:
    """Close any open Mail compose windows whose subject contains the given run id."""
    from . import mail_draft
    closed = mail_draft.close_drafts_with_run_id(args.run_id)
    print(f"closed {closed} draft(s) with run id {args.run_id}")
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
    p_tailor.add_argument("--mail", action="store_true",
                          help="Open a Mail.app draft to your email (from secrets.yaml) with all attachments. macOS only.")
    p_tailor.add_argument("--mode", default="production",
                          choices=["production", "benchmark"],
                          help=("production (default): early-stop on fit<50 (skip), 50-64 "
                                "(lightweight, no PDFs unless --force), 65+ (full pipeline). "
                                "benchmark: run full pipeline regardless of fit."))
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

    p_tl = sub.add_parser("track-list", help="List tracked applications.")
    p_tl.add_argument("--status", default="all",
                      help="all | waiting | interview_pending | interview_completed | rejected | offer | accepted | withdrawn")
    p_tl.set_defaults(func=_cmd_track_list)

    p_ts = sub.add_parser("track-status", help="Update an application's status.")
    p_ts.add_argument("ident", help="Packet slug or 12-char job id.")
    p_ts.add_argument("new_status",
                      choices=["waiting", "interview_pending", "interview_completed",
                               "rejected", "offer", "accepted", "withdrawn"])
    p_ts.add_argument("--notes", default="")
    p_ts.set_defaults(func=_cmd_track_status)

    p_tf = sub.add_parser("track-followup", help="Show applications with follow-ups due today or earlier.")
    p_tf.set_defaults(func=_cmd_track_followup)

    p_ta = sub.add_parser("track-add", help="Manually add an application to the tracker.")
    p_ta.add_argument("ident", help="Packet slug or 12-char job id.")
    p_ta.add_argument("--status", default="waiting")
    p_ta.set_defaults(func=_cmd_track_add)

    p_so = sub.add_parser(
        "send-outreach",
        help="Open Mail.app draft to a recruiter / hiring manager with only employer-facing attachments.",
    )
    p_so.add_argument("ident", help="Packet slug or 12-char job id.")
    p_so.add_argument("--to", required=True, help="Recipient email address.")
    p_so.add_argument(
        "--variant", default="recruiter",
        choices=["recruiter", "hiring_manager"],
        help="Which outreach variant to use as the email body.",
    )
    p_so.add_argument("--include-docx", action="store_true",
                      help="Also attach DOCX (default: PDF only).")
    p_so.add_argument("--force", action="store_true",
                      help="Open the draft even if the packet is BLOCKED by QA / fabrication checks.")
    p_so.set_defaults(func=_cmd_send_outreach)

    p_cd = sub.add_parser(
        "close-drafts",
        help="Close Mail.app compose windows tagged with a given run id (safe; only matches stamped drafts).",
    )
    p_cd.add_argument("run_id")
    p_cd.set_defaults(func=_cmd_close_drafts)

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
