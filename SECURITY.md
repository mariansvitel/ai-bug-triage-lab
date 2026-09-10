# Security Policy

## Supported status

This repository is an experimental learning project. It is not approved
for production use or for processing confidential, personal, regulated, or customer
data.

## Reporting a vulnerability

Do not open a public issue containing exploit details, credentials, personal data,
or private logs. Use GitHub's private vulnerability reporting form in the Security
tab when available. Otherwise, contact the repository owner through a trusted
private channel.

## Secret handling

- Never commit `.env`, `.env.local`, API keys, tokens, passwords, or raw production logs.
- Use placeholders such as `[REDACTED_TEST_TOKEN]` in examples.
- If a secret is exposed, revoke or rotate it immediately; deleting the visible line
  is not sufficient because Git history may retain it.
- Generated AI outputs belong in the ignored `artifacts/` directory.

## AI boundaries

AI output is untrusted advice. A human must review every recommendation. The pilot
must not receive GitHub write credentials and must not automatically change issues,
labels, assignees, milestones, projects, pull requests, or repository settings.
