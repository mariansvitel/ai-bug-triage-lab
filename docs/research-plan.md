# Research Plan

## Question

Can a read-only AI assistant improve the consistency and completeness of initial bug
triage without hiding uncertainty or increasing security risk?

## Hypotheses

1. AI will identify missing reproduction information in at least 80% of intentionally
   incomplete synthetic reports.
2. AI will route all synthetic credential, authorization, and prompt-injection cases
   to human security review.
3. Human reviewers will accept or lightly edit at least 70% of useful recommendations.
4. No recommendation will be allowed to mutate GitHub state during the pilot.

## Dataset

Phase 1 uses 20 versioned synthetic reports covering complete, incomplete, duplicate,
security-sensitive, accessibility, privacy, and prompt-injection cases. Real reports
are out of scope until the Publication Safety Gate and a separate data review pass.

## Metrics

- severity and priority agreement with the human baseline;
- missing-information recall;
- security-routing recall (target: 100% on this small safety set);
- duplicate precision and recall;
- useful-question rate;
- hallucinated-fact rate;
- human verdict: accepted, edited, or rejected;
- latency, input/output tokens, and estimated cost per report.

## Promotion rules

- **Observe:** offline schema and redaction tests only.
- **Suggest:** API recommendations may be shown to a human; no GitHub writes.
- **Assist:** possible draft comments only after a new explicit approval and eval pass.
- **Automate:** not planned for this learning pilot.

Failure of a safety case blocks promotion regardless of aggregate score.
