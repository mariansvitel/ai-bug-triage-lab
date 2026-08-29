# Duplicate Radar implementation review

Date: 2026-08-29

Scope: local, human-reviewed AI duplicate search

## Result

Duplicate Radar is ready for pull-request review. It compares the current synthetic
report with a deterministic shortlist from the ignored local tracker. It cannot
read from or write to GitHub.

## Safety boundaries

- The local shortlist excludes the query ID and contains at most five candidates.
- Query and candidate reports pass through fresh local redaction.
- Only ID, title, description, expected behavior, and actual behavior leave the
  local process for the structured comparison request.
- The request uses `store=False`.
- Returned IDs must belong to the exact shortlist; invented or repeated IDs fail
  closed.
- Results are recommendations, are not persisted automatically, and always require
  human review.
- The API key remains server-side in ignored `.env.local`.

## Verification

- `python -m pytest`: 24 offline tests passed.
- `python -m ruff check .`: passed.
- `python -m ruff format --check .`: passed; 26 files formatted.
- `node --check src/ai_bug_triage/static/app.js`: passed.
- `pip check`: no broken requirements.
- `pip-audit`: no known vulnerabilities in auditable PyPI dependencies.
- Secret-shaped scan: only the expected local startup loader references the
  environment variable name; frontend assets contain no key or OpenAI endpoint.
- `.env.local` and `artifacts/` remain ignored and untracked.

## Live synthetic flow

`WEB-DEMO-002` was compared with the existing local `WEB-DEMO-001` report. The
structured result returned the existing ID as a likely duplicate, explained the
shared checkout trigger and blocked confirmation behavior, and identified the
terminology difference. The tracker count and workflow state did not change.

The live check made one OpenAI API request using only synthetic, minimized, redacted
report fields. It made no GitHub request and no external write.
