from pathlib import Path

import httpx
import pytest

from ai_bug_triage.models import LedgerEntry, TriageResult
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


async def test_human_verdict_is_written_to_ignored_ledger(
    monkeypatch, tmp_path: Path
) -> None:
    destination = tmp_path / "ledger.jsonl"
    monkeypatch.setattr("ai_bug_triage.web.LEDGER_PATH", destination)
    payload = {"entry": fake_entry().model_dump(mode="json"), "verdict": "edited", "notes": "Human correction"}
    transport = httpx.ASGITransport(app=create_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        headers = await csrf_headers(client)
        response = await client.post("/api/verdict", json=payload, headers=headers)
    assert response.status_code == 200
    saved = destination.read_text(encoding="utf-8")
    assert '"human_verdict":"edited"' in saved
    assert "Human correction" in saved
