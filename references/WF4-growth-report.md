# Growth Report Protocol

This protocol describes the semantic report an agent should prepare when the
user asks about figure-KB progress. It defines what to report; deterministic
storage, schema validation, and query behavior remain in the Python package.

## Gate and Ownership

Run the First Invocation Gate in `SKILL.md` before reading the KB. If the
location is not configured, stop and ask the user to configure it. Markdown
pattern files are authoritative and `index.json` is a derived read model.

Python owns schema validation, persistence, index rebuilding, filtering, and
stable ordering. The LLM owns interpretation: whether a pattern supports the
current scientific claim, which evidence is strongest, and what to learn next.

## Report Sections

Every report may contain these seven sections:

1. Summary statistics: total patterns, recent additions, rated-pattern means,
   validation means, and covered chart types/journals.
2. Quality trajectory: quality by comparable time windows, with improving,
   stable, or declining interpretation.
3. Coverage: chart types, layout archetypes, journals, and under-represented
   or missing categories.
4. Memory strength: strongest and weakest `memory_score` entries, rationale,
   success cases, failure cases, and available reflections.
5. Usage: active versus dormant patterns, most-used entries, and feedback
   coverage.
6. Capability gaps: missing or weak chart types and archetypes.
7. Recommendations: a short, evidence-backed list of what to analyze next.

The report must distinguish missing data from a low score. A missing
`quality_rating`, `validation_score`, or `memory_score` is reported as
unavailable, not as zero.

## Deterministic Inputs

For a reproducible report, obtain current entries through the CLI query path:

```bash
python scripts/figure_kb.py query --limit 100
python scripts/figure_kb.py query --min-quality 1 --limit 100
python scripts/figure_kb.py query --min-validation 1 --limit 100
```

Use `index audit` to inspect invalid Markdown and `index rebuild` only after
the source documents are valid:

```bash
python scripts/figure_kb.py index audit
python scripts/figure_kb.py index rebuild
```

Do not recreate filter, sort, or Top-N code in a report note. The query result
already records warnings, truncation, and the deterministic ordering used.

## Interpretation Guidance

- Compare time windows with the same missing-value policy.
- Treat `memory_score` as retrieval evidence, never as scientific authority.
- Explain recommendations using quality, objective validation, reuse,
  feedback, success cases, failure cases, and relations.
- Keep unsupported renderer capability separate from render errors and
  objective validation failures.
- A small or empty KB is a valid state; recommend a focused next analysis
  instead of inventing trends.

## Report Output

Use a compact human-readable report with the report date, counts, means,
coverage, and a short recommendations section. Keep the source of each metric
traceable to the returned query data. If a report is saved, place it under the
configured KB's `reports/` directory, outside this repository.

## Optional Feedback

After presenting a report, the agent may ask whether the user wants to rate a
recent pattern or add a success/caveat note. Feedback is optional and must be
written through Repository support; never edit `index.json` directly.

## Checklist

- [ ] First Invocation Gate completed
- [ ] Current entries obtained through `scripts/figure_kb.py query`
- [ ] Missing, unsupported, and failed states kept distinct
- [ ] Seven report sections considered
- [ ] Recommendations tied to evidence and scientific context
- [ ] Any saved report kept outside the skill repository
