from __future__ import annotations

import hmac
import json
import os
import secrets
from pathlib import Path
from threading import Lock

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from openai import OpenAIError

from .models import BugReport, LedgerEntry, StatusSubmission, VerdictSubmission
from .tracker import load_tracker, tracker_summary, update_issue_status, upsert_issue
from .triage import DEFAULT_MODEL, append_ledger, prepare_report, triage_report

PACKAGE_ROOT = Path(__file__).parent
LEDGER_PATH = Path("artifacts/decision-ledger.jsonl")
TRACKER_PATH = Path("artifacts/tracker.json")
TRACKER_LOCK = Lock()
MAX_REQUEST_BYTES = 64 * 1024
CSRF_COOKIE = "triage_csrf"
ALLOWED_ORIGINS = {
    "http://127.0.0.1:8000",
    "http://localhost:8000",
    "http://testserver",
}


def _require_csrf(request: Request) -> None:
    origin = request.headers.get("origin")
    if origin not in ALLOWED_ORIGINS:
        raise HTTPException(status_code=403, detail="Request origin is not allowed.")
    cookie_token = request.cookies.get(CSRF_COOKIE, "")
    header_token = request.headers.get("x-csrf-token", "")
    if not cookie_token or not hmac.compare_digest(cookie_token, header_token):
        raise HTTPException(status_code=403, detail="CSRF validation failed.")


def create_app() -> FastAPI:
    app = FastAPI(
        title="AI Bug Triage Lab",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.mount("/static", StaticFiles(directory=PACKAGE_ROOT / "static"), name="static")
    templates = Jinja2Templates(directory=PACKAGE_ROOT / "templates")

    @app.middleware("http")
    async def security_middleware(request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > MAX_REQUEST_BYTES:
            return JSONResponse(status_code=413, content={"detail": "Request is too large."})
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; "
            "base-uri 'none'; form-action 'self'"
        )
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/", response_class=HTMLResponse)
    async def home(request: Request):
        csrf_token = secrets.token_urlsafe(32)
        response = templates.TemplateResponse(
            request=request,
            name="index.html",
            context={"csrf_token": csrf_token, "default_model": DEFAULT_MODEL},
        )
        response.set_cookie(
            CSRF_COOKIE,
            csrf_token,
            httponly=True,
            samesite="strict",
            secure=False,
            max_age=3_600,
        )
        return response

    @app.get("/api/health")
    async def health():
        return {
            "status": "ready",
            "api_key_configured": bool(os.getenv("OPENAI_API_KEY")),
            "model": os.getenv("OPENAI_MODEL", DEFAULT_MODEL),
            "github_write_access": False,
        }

    @app.post("/api/validate")
    async def validate_report(report: BugReport, request: Request):
        _require_csrf(request)
        redacted, findings = prepare_report(report)
        return {"valid": True, "redactions": findings, "report": json.loads(redacted)}

    @app.post("/api/triage")
    def run_triage(report: BugReport, request: Request):
        _require_csrf(request)
        if not os.getenv("OPENAI_API_KEY"):
            raise HTTPException(status_code=503, detail="Server API key is not configured.")
        try:
            return triage_report(report)
        except OpenAIError as exc:
            raise HTTPException(
                status_code=502,
                detail="The AI provider could not complete this request.",
            ) from exc

    @app.post("/api/verdict")
    async def save_verdict(submission: VerdictSubmission, request: Request):
        _require_csrf(request)
        if submission.report.id != submission.entry.bug_id:
            raise HTTPException(status_code=422, detail="Report and triage entry IDs do not match.")
        entry: LedgerEntry = submission.entry.model_copy(
            update={
                "human_verdict": submission.verdict,
                "human_notes": submission.notes.strip() or None,
            }
        )
        try:
            with TRACKER_LOCK:
                append_ledger(entry, LEDGER_PATH)
                tracked = upsert_issue(submission.report, entry, TRACKER_PATH)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            raise HTTPException(
                status_code=500,
                detail="The local decision evidence could not be saved.",
            ) from exc
        return {
            "saved": True,
            "run_id": entry.run_id,
            "verdict": entry.human_verdict,
            "tracked_issue": tracked.model_dump(mode="json"),
        }

    @app.get("/api/issues")
    async def list_issues():
        try:
            with TRACKER_LOCK:
                issues = load_tracker(TRACKER_PATH)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            raise HTTPException(
                status_code=500, detail="The local tracker data is invalid."
            ) from exc
        return {
            "issues": [issue.model_dump(mode="json") for issue in issues],
            "summary": tracker_summary(issues),
        }

    @app.patch("/api/issues/{bug_id}")
    async def change_issue_status(
        bug_id: str,
        submission: StatusSubmission,
        request: Request,
    ):
        _require_csrf(request)
        try:
            with TRACKER_LOCK:
                issue = update_issue_status(bug_id, submission.status, TRACKER_PATH)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Tracked issue was not found.") from exc
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            raise HTTPException(
                status_code=500, detail="The local tracker could not be updated."
            ) from exc
        return {"updated": True, "issue": issue.model_dump(mode="json")}

    return app


app = create_app()
