"""job_finder: poll curated company ATS boards, dedupe, score, queue.

Public APIs:
- `run(profile, secrets)`: poll all configured sources, dedupe, score, persist
  the review queue. Returns the queue rows.
- `review(...)`: list current queue, optionally filtered.
- `approve(slug)`: promote a queued posting to the standard ingest+analyze flow.
- `ignore(slug)`: mark a queued posting as not-interested.
"""
from .queue import load_queue, save_queue, FinderQueueRow
from .runner import run_finder
