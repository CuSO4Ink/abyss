from __future__ import annotations

from pathlib import Path

from .audit import append_event
from .utils import list_records, read_record, repo_root, write_record

REVIEWS_DIR = repo_root() / "process" / "reviews"
ACTIONS_DIR = repo_root() / "process" / "actions"


def pending_reviews() -> list[tuple[Path, dict]]:
    items = []
    for path in list_records(REVIEWS_DIR, "rev"):
        record = read_record(path)
        if record.get("status") == "pending":
            items.append((path, record))
    return items


def set_review_status(review_path: Path, status: str) -> dict:
    review = read_record(review_path)
    if review.get("status") != "pending":
        raise SystemExit(f"Review is not pending: {review.get('id')}")
    if status not in {"approved", "rejected"}:
        raise SystemExit(f"Unsupported review status: {status}")

    review["status"] = status
    write_record(review_path, review)

    action_id = review.get("action_id")
    if action_id:
        action_path = ACTIONS_DIR / f"{action_id}.yaml"
        if action_path.exists():
            action = read_record(action_path)
            action["status"] = "approved" if status == "approved" else "rejected"
            write_record(action_path, action)

    append_event(f"review.{status}", f"Review {status}", {"review_id": review.get("id"), "action_id": action_id})
    return review
