from __future__ import annotations

import re

REDACTION_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("OPENAI_KEY", re.compile(r"sk-[A-Za-z0-9_-]{16,}")),
    ("EMAIL", re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)),
    ("IPV4", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")),
    (
        "AUTH_HEADER",
        re.compile(r"(?i)(authorization\s*:\s*(?:bearer|basic)\s+)[^\s,;]+"),
    ),
)


def redact_text(value: str) -> tuple[str, list[str]]:
    """Redact common sensitive patterns without retaining matched values."""
    redacted = value
    findings: list[str] = []
    for label, pattern in REDACTION_PATTERNS:
        redacted, count = pattern.subn(f"[REDACTED_{label}]", redacted)
        if count:
            findings.extend([label] * count)
    return redacted, findings
