# Security Policy

## Supported status

This repository is an experimental, private learning project. It is not approved
for production use or for processing confidential, personal, regulated, or customer
data.

## Reporting a vulnerability

Do not open a public issue containing exploit details, credentials, personal data,
or private logs. While the repository is private, contact the repository owner
directly. Before public release, GitHub private vulnerability reporting must be
enabled and this section updated with the final contact route.

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
