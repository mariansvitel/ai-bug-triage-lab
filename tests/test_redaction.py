from ai_bug_triage.redaction import redact_text


def test_redacts_email_and_ip_without_returning_values() -> None:
    original = "Contact dev@example.test from 192.0.2.44"
    redacted, findings = redact_text(original)
    assert "dev@example.test" not in redacted
    assert "192.0.2.44" not in redacted
    assert findings == ["EMAIL", "IPV4"]


def test_redacts_authorization_header() -> None:
    redacted, findings = redact_text("Authorization: Bearer synthetic-value")
    assert "synthetic-value" not in redacted
    assert findings == ["AUTH_HEADER"]
