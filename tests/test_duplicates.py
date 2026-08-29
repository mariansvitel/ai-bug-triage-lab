from types import SimpleNamespace

import pytest

from ai_bug_triage.duplicates import search_duplicates, shortlist_candidates
from ai_bug_triage.models import (
    BugReport,
    DuplicateMatch,
    DuplicateSearchResult,
    LedgerEntry,
    TrackedIssue,
    TriageResult,
)


def report(bug_id: str, title: str, description: str) -> BugReport:
    return BugReport(
        id=bug_id,
        title=title,
        description=description,
        expected_behavior="The action succeeds.",
        actual_behavior="The action stays blocked.",
    )


def tracked(candidate: BugReport) -> TrackedIssue:
    entry = LedgerEntry(
        run_id=f"run-{candidate.id}",
        created_at="2026-08-29T00:00:00+00:00",
        bug_id=candidate.id,
        input_sha256="c" * 64,
        model="test-model",
        prompt_version="test",
        result=TriageResult(
            summary="Synthetic candidate",
            category="ui",
            severity="minor",
            priority="P2",
            recommended_action="investigate",
            suggested_labels=[],
            missing_information=[],
            follow_up_questions=[],
            duplicate_likelihood=0,
            possible_duplicate_ids=[],
            data_sensitivity="public",
            prompt_injection_detected=False,
            secret_exposure_suspected=False,
            confidence=0.8,
            rationale="Synthetic evidence.",
            human_review_required=True,
        ),
        human_verdict="accepted",
    )
    return TrackedIssue(
        report=candidate,
        entry=entry,
        created_at="2026-08-29T00:00:00+00:00",
        updated_at="2026-08-29T00:00:00+00:00",
    )


class FakeResponses:
    def __init__(self, result: DuplicateSearchResult) -> None:
        self.result = result
        self.kwargs: dict | None = None

    def parse(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(output_parsed=self.result, id="resp-duplicate-test")


class FakeClient:
    def __init__(self, result: DuplicateSearchResult) -> None:
        self.responses = FakeResponses(result)


def duplicate_result(bug_id: str = "BUG-2") -> DuplicateSearchResult:
    return DuplicateSearchResult(
        recommendation="review_possible_duplicate",
        matches=[
            DuplicateMatch(
                bug_id=bug_id,
                likelihood=0.84,
                matching_signals=["same checkout control"],
                differences=["different browser"],
                rationale="Both reports describe the same disabled confirmation action.",
            )
        ],
        confidence=0.78,
        prompt_injection_detected=False,
        secret_exposure_suspected=False,
        human_review_required=True,
    )


def test_shortlist_excludes_query_and_ranks_similar_title_first() -> None:
    query = report("BUG-1", "Checkout button disabled", "Checkout cannot continue")
    same_id = tracked(report("BUG-1", "Checkout button disabled", "Older revision"))
    similar = tracked(report("BUG-2", "Checkout confirmation disabled", "Order cannot continue"))
    unrelated = tracked(report("BUG-3", "Profile avatar blurry", "Image has low resolution"))

    result = shortlist_candidates(query, [unrelated, same_id, similar])

    assert [issue.report.id for issue in result] == ["BUG-2", "BUG-3"]


def test_shortlist_never_exposes_more_than_five_candidates() -> None:
    query = report("BUG-1", "Checkout button disabled", "Checkout cannot continue")
    issues = [
        tracked(
            report(
                f"BUG-{index}",
                f"Checkout confirmation disabled variant {index}",
                "Checkout cannot continue",
            )
        )
        for index in range(2, 10)
    ]

    result = shortlist_candidates(query, issues)

    assert len(result) == 5


def test_search_redacts_minimizes_and_validates_ai_candidates() -> None:
    query = report("BUG-1", "Checkout button disabled", "Contact dev@example.test")
    candidate = tracked(
        report("BUG-2", "Checkout confirmation disabled", "Observed from 192.0.2.4")
    )
    client = FakeClient(duplicate_result())

    entry = search_duplicates(query, [candidate], model="test-model", client=client)

    assert entry.candidate_ids == ["BUG-2"]
    assert entry.result.matches[0].bug_id == "BUG-2"
    assert client.responses.kwargs is not None
    assert client.responses.kwargs["store"] is False
    request_text = str(client.responses.kwargs["input"])
    assert "dev@example.test" not in request_text
    assert "192.0.2.4" not in request_text
    assert "steps_to_reproduce" not in request_text
    assert "human_notes" not in request_text


def test_search_rejects_hallucinated_candidate_id() -> None:
    query = report("BUG-1", "Checkout button disabled", "Checkout cannot continue")
    candidate = tracked(report("BUG-2", "Checkout confirmation disabled", "Order blocked"))

    with pytest.raises(RuntimeError, match="invalid duplicate candidate"):
        search_duplicates(
            query,
            [candidate],
            model="test-model",
            client=FakeClient(duplicate_result("INVENTED-ID")),
        )


def test_empty_tracker_returns_reviewable_local_result_without_api_call() -> None:
    query = report("BUG-1", "Checkout button disabled", "Checkout cannot continue")

    entry = search_duplicates(query, [], model="test-model")

    assert entry.candidate_ids == []
    assert entry.result.recommendation == "no_likely_duplicate"
    assert entry.result.matches == []
    assert entry.result.human_review_required is True
