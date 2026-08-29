from __future__ import annotations

import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from pydantic import TypeAdapter

from .models import BugReport, IssueStatus, LedgerEntry, TrackedIssue

_TRACKED_ISSUES = TypeAdapter(list[TrackedIssue])


def load_tracker(source: Path) -> list[TrackedIssue]:
    if not source.exists():
        return []
    payload = json.loads(source.read_text(encoding="utf-8"))
    return _TRACKED_ISSUES.validate_python(payload)


def upsert_issue(
    report: BugReport,
    entry: LedgerEntry,
    destination: Path,
) -> TrackedIssue:
    if report.id != entry.bug_id:
        raise ValueError("The report ID does not match the triage entry.")

    issues = load_tracker(destination)
    existing = next((issue for issue in issues if issue.report.id == report.id), None)
    now = datetime.now(UTC).isoformat()
    tracked = TrackedIssue(
        report=report,
        entry=entry,
        status=existing.status if existing else IssueStatus.inbox,
        created_at=existing.created_at if existing else now,
        updated_at=now,
    )
    updated = [issue for issue in issues if issue.report.id != report.id]
    updated.append(tracked)
    updated.sort(key=lambda issue: issue.updated_at, reverse=True)
    _atomic_write(updated, destination)
    return tracked


def update_issue_status(
    bug_id: str,
    status: IssueStatus,
    destination: Path,
) -> TrackedIssue:
    issues = load_tracker(destination)
    position = next(
        (index for index, issue in enumerate(issues) if issue.report.id == bug_id), None
    )
    if position is None:
        raise KeyError(bug_id)

    current = issues[position]
    updated = current.model_copy(
        update={"status": status, "updated_at": datetime.now(UTC).isoformat()}
    )
    issues[position] = updated
    issues.sort(key=lambda issue: issue.updated_at, reverse=True)
    _atomic_write(issues, destination)
    return updated


def tracker_summary(issues: list[TrackedIssue]) -> dict[str, object]:
    statuses = Counter(issue.status.value for issue in issues)
    verdicts = Counter(issue.entry.human_verdict or "pending" for issue in issues)
    reviewed = [issue.entry.result.confidence for issue in issues]
    return {
        "total": len(issues),
        "statuses": {status.value: statuses[status.value] for status in IssueStatus},
        "verdicts": dict(sorted(verdicts.items())),
        "average_confidence": round(sum(reviewed) / len(reviewed), 3) if reviewed else 0,
    }


def _atomic_write(issues: list[TrackedIssue], destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.{uuid4().hex}.tmp")
    try:
        payload = [issue.model_dump(mode="json") for issue in issues]
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
