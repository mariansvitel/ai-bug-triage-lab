from __future__ import annotations

import hmac
import json
import os
import secrets
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from openai import OpenAIError

from .models import BugReport, LedgerEntry, VerdictSubmission
from .triage import DEFAULT_MODEL, append_ledger, prepare_report, triage_report

PACKAGE_ROOT = Path(__file__).parent
LEDGER_PATH = Path("artifacts/decision-ledger.jsonl")
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
        entry: LedgerEntry = submission.entry.model_copy(
            update={
                "human_verdict": submission.verdict,
                "human_notes": submission.notes.strip() or None,
            }
        )
        append_ledger(entry, LEDGER_PATH)
        return {"saved": True, "run_id": entry.run_id, "verdict": entry.human_verdict}

    return app


app = create_app()
