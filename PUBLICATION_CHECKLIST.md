# Publication Safety Gate

The repository may become public only after every required item is complete.

- [ ] All test data is synthetic or explicitly approved for publication.
- [ ] Git history contains no credentials, personal data, or confidential logs.
- [ ] The current OpenAI key has never been committed.
- [ ] GitHub secret scanning and push protection are enabled where available.
- [ ] Dependabot alerts and dependency review are enabled.
- [ ] Code scanning is enabled and high-severity findings are resolved.
- [ ] Prompt-injection and sensitive-data tests pass.
- [ ] Tracker and Decision Ledger artifacts are ignored, synthetic, and absent from history.
- [ ] AI limitations, model choice, expected cost, and human oversight are documented.
- [ ] A spending limit and usage alerts are configured in the OpenAI project.
- [ ] `SECURITY.md` has a valid private reporting route.
- [ ] A license has been deliberately selected.
- [ ] The repository owner performs a final Safety Gate review.
