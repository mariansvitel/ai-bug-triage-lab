from pathlib import Path

import httpx
import pytest

from ai_bug_triage.models import (
    DuplicateMatch,
    DuplicateSearchEntry,
    DuplicateSearchResult,
    LedgerEntry,
    TriageResult,
)
from ai_bug_triage.web import create_app

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


async def csrf_headers(client: httpx.AsyncClient) -> dict[str, str]:
    response = await client.get("/")
    token = client.cookies["triage_csrf"]
    assert token in response.text
    return {"Origin": "http://testserver", "X-CSRF-Token": token}


def report_payload() -> dict:
    return {
        "id": "WEB-TEST-1",
        "title": "Synthetic form issue",
        "description": "Contact dev@example.test from 192.0.2.4",
        "steps_to_reproduce": ["Open form", "Submit"],
        "expected_behavior": "Submission works",
        "actual_behavior": "Submission stays pending",
        "environment": "Synthetic test",
    }


def fake_entry() -> LedgerEntry:
    return LedgerEntry(
        run_id="run-test",
        created_at="2026-08-01T00:00:00+00:00",
        bug_id="WEB-TEST-1",
        input_sha256="a" * 64,
        model="test-model",
        prompt_version="test",
        result=TriageResult(
            summary="Synthetic result",
            category="ui",
            severity="minor",
            priority="P2",
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
            rationale="Synthetic evidence only.",
            human_review_required=True,
        ),
    )


def fake_duplicate_entry() -> DuplicateSearchEntry:
    return DuplicateSearchEntry(
        run_id="duplicate-run-test",
        created_at="2026-08-29T00:00:00+00:00",
        query_bug_id="WEB-TEST-1",
        model="test-model",
        candidate_ids=["WEB-OLD-1"],
        result=DuplicateSearchResult(
            recommendation="review_possible_duplicate",
            matches=[
                DuplicateMatch(
                    bug_id="WEB-OLD-1",
                    likelihood=0.82,
                    matching_signals=["same blocked form"],
                    differences=["different environment"],
                    rationale="Synthetic comparison.",
                )
            ],
            confidence=0.76,
            prompt_injection_detected=False,
            secret_exposure_suspected=False,
            human_review_required=True,
        ),
    )


async def test_home_has_security_headers_and_no_key_value(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "local-test-value")
    transport = httpx.ASGITransport(app=create_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/")
    assert response.status_code == 200
    assert "AI Bug Triage Lab" in response.text
    assert "local-test-value" not in response.text
    assert response.headers["x-frame-options"] == "DENY"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]


async def test_validate_requires_csrf() -> None:
    transport = httpx.ASGITransport(app=create_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/api/validate", json=report_payload())
    assert response.status_code == 403


async def test_validate_redacts_sensitive_values() -> None:
    transport = httpx.ASGITransport(app=create_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        headers = await csrf_headers(client)
        response = await client.post("/api/validate", json=report_payload(), headers=headers)
    assert response.status_code == 200
    text = response.text
    assert "dev@example.test" not in text
    assert "192.0.2.4" not in text
    assert response.json()["redactions"] == ["EMAIL", "IPV4"]


async def test_triage_uses_server_side_key_and_returns_typed_result(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "local-test-value")
    monkeypatch.setattr("ai_bug_triage.web.triage_report", lambda report: fake_entry())
    transport = httpx.ASGITransport(app=create_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        headers = await csrf_headers(client)
        response = await client.post("/api/triage", json=report_payload(), headers=headers)
    assert response.status_code == 200
    assert response.json()["result"]["human_review_required"] is True
    assert "local-test-value" not in response.text


async def test_duplicate_search_is_csrf_protected_and_returns_only_typed_result(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "local-test-value")
    monkeypatch.setattr("ai_bug_triage.web.TRACKER_PATH", tmp_path / "tracker.json")
    monkeypatch.setattr(
        "ai_bug_triage.web.search_duplicates", lambda report, issues: fake_duplicate_entry()
    )
    transport = httpx.ASGITransport(app=create_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        blocked = await client.post("/api/duplicates", json=report_payload())
        headers = await csrf_headers(client)
        response = await client.post("/api/duplicates", json=report_payload(), headers=headers)

    assert blocked.status_code == 403
    assert response.status_code == 200
    assert response.json()["result"]["matches"][0]["bug_id"] == "WEB-OLD-1"
    assert response.json()["result"]["human_review_required"] is True
    assert "local-test-value" not in response.text


async def test_human_verdict_is_written_to_ignored_ledger(monkeypatch, tmp_path: Path) -> None:
    destination = tmp_path / "ledger.jsonl"
    tracker = tmp_path / "tracker.json"
    monkeypatch.setattr("ai_bug_triage.web.LEDGER_PATH", destination)
    monkeypatch.setattr("ai_bug_triage.web.TRACKER_PATH", tracker)
    payload = {
        "report": report_payload(),
        "entry": fake_entry().model_dump(mode="json"),
        "verdict": "edited",
        "notes": "Human correction",
    }
    transport = httpx.ASGITransport(app=create_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        headers = await csrf_headers(client)
        response = await client.post("/api/verdict", json=payload, headers=headers)
        queue = await client.get("/api/issues")
    assert response.status_code == 200
    saved = destination.read_text(encoding="utf-8")
    assert '"human_verdict":"edited"' in saved
    assert "Human correction" in saved
    assert queue.status_code == 200
    assert queue.json()["summary"]["total"] == 1
    assert queue.json()["issues"][0]["status"] == "inbox"


async def test_tracked_issue_status_requires_csrf_and_can_be_updated(
    monkeypatch, tmp_path: Path
) -> None:
    tracker = tmp_path / "tracker.json"
    monkeypatch.setattr("ai_bug_triage.web.LEDGER_PATH", tmp_path / "ledger.jsonl")
    monkeypatch.setattr("ai_bug_triage.web.TRACKER_PATH", tracker)
    payload = {
        "report": report_payload(),
        "entry": fake_entry().model_dump(mode="json"),
        "verdict": "accepted",
        "notes": "Synthetic review",
    }
    transport = httpx.ASGITransport(app=create_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        headers = await csrf_headers(client)
        saved = await client.post("/api/verdict", json=payload, headers=headers)
        blocked = await client.patch("/api/issues/WEB-TEST-1", json={"status": "planned"})
        updated = await client.patch(
            "/api/issues/WEB-TEST-1",
            json={"status": "planned"},
            headers=headers,
        )

    assert saved.status_code == 200
    assert blocked.status_code == 403
    assert updated.status_code == 200
    assert updated.json()["issue"]["status"] == "planned"


async def test_missing_tracked_issue_returns_404(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("ai_bug_triage.web.TRACKER_PATH", tmp_path / "tracker.json")
    transport = httpx.ASGITransport(app=create_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        headers = await csrf_headers(client)
        response = await client.patch(
            "/api/issues/DOES-NOT-EXIST",
            json={"status": "resolved"},
            headers=headers,
        )

    assert response.status_code == 404


async def test_verdict_rejects_mismatched_report_id(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("ai_bug_triage.web.LEDGER_PATH", tmp_path / "ledger.jsonl")
    monkeypatch.setattr("ai_bug_triage.web.TRACKER_PATH", tmp_path / "tracker.json")
    report = report_payload()
    report["id"] = "OTHER-ID"
    payload = {
        "report": report,
        "entry": fake_entry().model_dump(mode="json"),
        "verdict": "rejected",
        "notes": "IDs must match",
    }
    transport = httpx.ASGITransport(app=create_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        headers = await csrf_headers(client)
        response = await client.post("/api/verdict", json=payload, headers=headers)

    assert response.status_code == 422
