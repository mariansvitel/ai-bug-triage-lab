import json
from pathlib import Path

import pytest

from ai_bug_triage.models import BugReport, IssueStatus, LedgerEntry, TriageResult
from ai_bug_triage.tracker import load_tracker, tracker_summary, update_issue_status, upsert_issue


def report() -> BugReport:
    return BugReport(id="TRACK-1", title="Synthetic tracker issue", description="Local only")


def entry() -> LedgerEntry:
    return LedgerEntry(
        run_id="tracker-run",
        created_at="2026-08-29T00:00:00+00:00",
        bug_id="TRACK-1",
        input_sha256="b" * 64,
        model="test-model",
        prompt_version="test",
        result=TriageResult(
            summary="Synthetic recommendation",
            category="ui",
            severity="minor",
            priority="P3",
            recommended_action="investigate",
            suggested_labels=["ui"],
            missing_information=[],
            follow_up_questions=[],
            duplicate_likelihood=0,
            possible_duplicate_ids=[],
            data_sensitivity="public",
            prompt_injection_detected=False,
            secret_exposure_suspected=False,
            confidence=0.75,
            rationale="Synthetic evidence.",
            human_review_required=True,
        ),
        human_verdict="accepted",
    )


def test_tracker_upserts_and_preserves_workflow_state(tmp_path: Path) -> None:
    destination = tmp_path / "tracker.json"
    first = upsert_issue(report(), entry(), destination)
    planned = update_issue_status("TRACK-1", IssueStatus.planned, destination)
    refreshed = upsert_issue(report(), entry(), destination)

    assert first.status == "inbox"
    assert planned.status == "planned"
    assert refreshed.status == "planned"
    assert len(load_tracker(destination)) == 1


def test_tracker_summary_is_human_evidence_aware(tmp_path: Path) -> None:
    destination = tmp_path / "tracker.json"
    upsert_issue(report(), entry(), destination)

    summary = tracker_summary(load_tracker(destination))

    assert summary["total"] == 1
    assert summary["statuses"]["inbox"] == 1
    assert summary["verdicts"] == {"accepted": 1}
    assert summary["average_confidence"] == 0.75


def test_tracker_rejects_mismatched_entry(tmp_path: Path) -> None:
    mismatched = entry().model_copy(update={"bug_id": "OTHER"})

    with pytest.raises(ValueError, match="does not match"):
        upsert_issue(report(), mismatched, tmp_path / "tracker.json")


def test_tracker_reports_missing_and_malformed_storage(tmp_path: Path) -> None:
    destination = tmp_path / "tracker.json"
    destination.write_text(json.dumps({"not": "a list"}), encoding="utf-8")

    with pytest.raises(ValueError):
        load_tracker(destination)
    with pytest.raises(KeyError):
        update_issue_status("MISSING", IssueStatus.resolved, tmp_path / "empty.json")
