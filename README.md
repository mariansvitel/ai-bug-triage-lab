# AI Bug Triage Lab

A security-first learning project for evaluating human-supervised AI bug triage.

The distinctive feature is an **AI Decision Ledger**: every recommendation can be
compared with a later human verdict. The goal is not to automate authority, but to
measure where AI helps, where it fails, and when it should abstain.

> Status: private research pilot. The AI can suggest; it cannot edit, label, close,
> assign, or publish GitHub issues.

## What the pilot does

Given a bug report, the local web UI or CLI can return a typed recommendation containing:

- summary, category, severity, and priority;
- missing information and follow-up questions;
- suggested labels and next action;
- possible duplicate signals;
- data-sensitivity and prompt-injection signals;
- confidence, rationale, and a mandatory human-review flag.

After a human verdict, the private web interface can place the synthetic report in a
local tracker with `inbox`, `investigating`, `planned`, and `resolved` states. This is
an ignored local learning artifact, not a GitHub issue or external system of record.

## Safety model

- Input is treated as untrusted data, never as instructions.
- Common secrets and personal data are redacted before an API request.
- API responses use a strict Pydantic schema.
- API requests set `store=False`.
- There are no GitHub write tools in the application.
- Generated ledgers and outputs are written under ignored `artifacts/` only when
  explicitly requested.
- Synthetic reports are used until the safety gate is passed.

See [SECURITY.md](SECURITY.md), [the threat model](docs/threat-model.md), and
[the research plan](docs/research-plan.md).

## Local setup

Requirements: Python 3.11 or newer and an OpenAI API key in the process environment.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

The repository includes `.env.example`, but the application does not load or commit
secret files automatically. Keep `OPENAI_API_KEY` in an ignored local environment
file or inject it into the process environment.

Validate a report without calling the API:

```powershell
ai-bug-triage data/sample-report.json --dry-run
```

Run AI triage and append the recommendation to the local decision ledger:

```powershell
ai-bug-triage data/sample-report.json --ledger artifacts/decision-ledger.jsonl
```

The default model is `gpt-5.6-terra`. Override it with `OPENAI_MODEL` or `--model`.

## Local web interface

Start the private local frontend from PowerShell:

```powershell
.\scripts\start-web.ps1
```

Then open [http://127.0.0.1:8000](http://127.0.0.1:8000). The startup script reads
the existing key into the server process from an ignored `.env.local`; the key is
never embedded in HTML or browser JavaScript. The server binds only to localhost.

The interface supports dry-run validation, AI triage, safety flags, confidence,
and a human verdict saved to the ignored local Decision Ledger. Reviewed reports are
also upserted into an ignored local tracker dashboard so AI confidence, human verdict,
and workflow state remain inspectable together.

## Offline verification

```powershell
python -m pytest
python -m ruff check .
```

The test suite never calls the OpenAI API.

## Publication gate

Keep the repository private until all items in [PUBLICATION_CHECKLIST.md](PUBLICATION_CHECKLIST.md)
are complete. A license is intentionally deferred until the owner chooses one.

## Official references

- [OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
- [OpenAI Safety Best Practices](https://developers.openai.com/api/docs/guides/safety-best-practices)
- [OpenAI GPT-5.6 model guidance](https://developers.openai.com/api/docs/guides/latest-model?model=gpt-5.6)
- [GitHub repository security best practices](https://docs.github.com/en/repositories/creating-and-managing-repositories/best-practices-for-repositories)
