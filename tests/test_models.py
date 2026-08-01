from ai_bug_triage.models import BugReport, Priority, Severity, TriageResult


def test_triage_result_requires_human_review() -> None:
    result = TriageResult(
        summary="Synthetic summary",
        category="ui",
        severity=Severity.minor,
        priority=Priority.p3,
        recommended_action="investigate",
        suggested_labels=["ui"],
        missing_information=[],
        follow_up_questions=[],
        duplicate_likelihood=0,
        possible_duplicate_ids=[],
        data_sensitivity="public",
        prompt_injection_detected=False,
        secret_exposure_suspected=False,
        confidence=0.8,
        rationale="Based only on the synthetic report.",
        human_review_required=True,
    )
    assert result.human_review_required is True


def test_bug_report_rejects_unknown_fields() -> None:
    payload = {"id": "B-1", "title": "x", "description": "y", "unexpected": True}
    try:
        BugReport.model_validate(payload)
    except ValueError:
        return
    raise AssertionError("Unknown fields must be rejected")
