# Threat Model

## Assets

- OpenAI API key and usage budget;
- repository and issue confidentiality;
- personal data and credentials inside logs;
- integrity of triage decisions;
- human control over GitHub state.

## Trust boundaries

Bug report text, links, attachments, model output, and copied logs are untrusted.
The local operator and reviewed source code are trusted only within the private pilot.

## Main threats and controls

| Threat | Control |
| --- | --- |
| API key committed to Git | `.env*` ignored; only `.env.example` allowed |
| Prompt injection in an issue | Data delimiters, explicit instruction hierarchy, adversarial evals |
| Personal data sent to the API | Local redaction and synthetic-only Phase 1 data |
| Hallucinated severity or duplicate | Strict schema, confidence, evidence-based rationale, human verdict |
| Unauthorized GitHub mutation | No GitHub token or write tool in the application |
| Unbounded spend | One-report CLI, explicit execution, configurable model, platform budget controls |
| Sensitive output committed | Generated output defaults to ignored `artifacts/` |
| Dependency compromise | Minimal dependencies, Dependabot, offline CI tests |

## Non-goals

The pilot does not prove production security, detect every secret type, replace a
security review, execute issue attachments, browse issue links, or automatically
change GitHub content.
