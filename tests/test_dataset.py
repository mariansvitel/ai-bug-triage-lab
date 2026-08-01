import json
from pathlib import Path

DATASET = Path(__file__).parents[1] / "evals" / "synthetic_bug_reports.jsonl"


def load_rows() -> list[dict]:
    return [
        json.loads(line)
        for line in DATASET.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_dataset_has_twenty_unique_synthetic_cases() -> None:
    rows = load_rows()
    assert len(rows) == 20
    assert len({row["id"] for row in rows}) == 20
    assert all(row["synthetic"] is True for row in rows)


def test_dataset_covers_safety_and_quality_cases() -> None:
    rows = load_rows()
    tags = {tag for row in rows for tag in row["tags"]}
    assert {"complete", "incomplete", "duplicate", "security", "prompt-injection"} <= tags
