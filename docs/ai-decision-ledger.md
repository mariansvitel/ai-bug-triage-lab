# AI Decision Ledger

The ledger is the project's originality mechanism and learning evidence. Each run
stores safe metadata, the typed recommendation, and a later human verdict.

Required fields include a random run ID, timestamp, bug ID, hash of the redacted
input, model, prompt version, result, and optional human verdict. The original raw
report and API key are never stored in the ledger.

The local ledger belongs under `artifacts/decision-ledger.jsonl` and is ignored by
Git. Curated, anonymized aggregate results may be published later as a separate,
reviewed artifact.
