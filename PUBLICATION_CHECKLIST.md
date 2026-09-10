# Publication Safety Gate

The repository may become public only after every required item is complete.

- [x] All test data is synthetic or explicitly approved for publication.
- [x] Git history contains no credentials, personal data, or confidential logs.
- [x] The current OpenAI key has never been committed.
- [ ] GitHub secret scanning and push protection are enabled where available.
- [ ] Dependabot alerts and dependency review are enabled.
- [ ] Code scanning is enabled and high-severity findings are resolved.
- [x] Prompt-injection and sensitive-data tests pass.
- [x] Tracker and Decision Ledger artifacts are ignored, synthetic, and absent from history.
- [x] AI limitations, model choice, expected cost, and human oversight are documented.
- [ ] A spending limit and usage alerts are configured in the OpenAI project.
- [x] `SECURITY.md` has a valid private reporting route.
- [ ] A license has been deliberately selected.
- [ ] The repository owner performs a final Safety Gate review.
