from __future__ import annotations

import argparse
import json
from pathlib import Path

from .triage import DEFAULT_MODEL, append_ledger, load_report, prepare_report, triage_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Human-supervised AI bug triage")
    parser.add_argument("report", type=Path, help="Path to one JSON bug report")
    parser.add_argument("--model", help=f"OpenAI model (default: {DEFAULT_MODEL})")
    parser.add_argument("--ledger", type=Path, help="Optional ignored JSONL decision ledger")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and redact input without calling the OpenAI API",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    report = load_report(args.report)

    if args.dry_run:
        redacted, findings = prepare_report(report)
        print(json.dumps({"valid": True, "redactions": findings, "report": json.loads(redacted)}))
        return

    entry = triage_report(report, model=args.model)
    if args.ledger:
        append_ledger(entry, args.ledger)
    print(entry.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
