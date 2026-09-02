# Query Templates (WF3)

This reference describes the meaning of common searches. The executable query
implementation lives in `src/nature_figure_learner/query.py`; use the launcher
instead of writing a second filter or ranking implementation.

## Before Querying

1. Run the First Invocation Gate in `SKILL.md`.
2. If the gate returns `NOT_CONFIGURED`, ask the user to choose and initialize a KB.
3. Run a launcher command. The command returns one JSON Envelope on stdout.
4. Treat `warnings` as diagnostic context. An empty result is a successful query.

The Markdown files are the durable source of truth. `index.json` is a derived
read model; users and agents should not edit it directly. `index audit` and
`index rebuild` are the only maintenance commands needed for the derived index.

## CLI Mapping

The common command shape is:

```bash
python scripts/figure_kb.py query --chart-type grouped-bar --limit 5
```

Add `--kb-path <configured-kb-path>` when the location is not supplied by
`FIGURE_KB_HOME` or the location manager. Repeated filters such as
`--chart-type`, `--journal`, and `--tag-all` are allowed.

| User intent | CLI options |
| --- | --- |
| Chart type | `--chart-type grouped-bar` |
| Source type | `--source-type image` or `code` |
| Journal | `--journal Nature` |
| Publication window | `--year-from 2020 --year-to 2026` |
| Layout | `--layout-archetype quantitative-grid` |
| Palette | `--color-scheme nature-nmi-pastel` |
| All required tags | `--tag-all method-comparison` (repeat as needed) |
| Any matching tag | `--tag-any python` (repeat as needed) |
| Quality threshold | `--min-quality 4` |
| Validation threshold | `--min-validation 4` |
| Memory threshold | `--min-memory-score 70` |
| Usage threshold | `--min-application-count 1` |
| Similarity to an entry | `--reference-id pattern-003` |
| Result count | `--limit 5` |
| Explicit ordering | `--sort-by quality`, `validation`, `application_count`, or `default` |

The default ordering is deterministic and implemented by Python: memory total,
quality, validation, application count, then entry ID. Similarity uses the
fixed chart/layout/color/tag weighting in the query module. Do not reproduce
these formulas in this document or in an agent-generated script.

## Common Searches

### Q1: Chart Type

Trigger: "find grouped-bar figures" or "search for heatmaps".

```bash
python scripts/figure_kb.py query --chart-type grouped-bar --limit 5
python scripts/figure_kb.py query --chart-type heatmap --limit 5
```

Interpret each match using its chart type, layout, palette, quality,
validation, memory score, usage count, and caveats. The agent may load the
selected Markdown narrative for a deeper explanation.

### Q2: Journal and Year

```bash
python scripts/figure_kb.py query --journal Nature --year-from 2024 --year-to 2026
```

Journal matching is case-insensitive. Preserve the stored display spelling in
the response.

### Q3: Layout and Palette

```bash
python scripts/figure_kb.py query \
  --layout-archetype quantitative-grid \
  --color-scheme nature-nmi-pastel \
  --min-quality 4
```

Use this when the user has already chosen a visual archetype and wants proven
style evidence.

### Q4: Multi-Criteria Search

```bash
python scripts/figure_kb.py query \
  --chart-type grouped-bar \
  --journal Nature \
  --tag-all method-comparison \
  --min-quality 4 \
  --limit 5
```

Start with the narrowest useful criteria. If no matches are returned, remove
one constraint and explain the change.

### Q5: Similar Pattern

```bash
python scripts/figure_kb.py query --reference-id pattern-003 --limit 3
```

The agent compares the returned entries with the reference's scientific claim,
hero panel, evidence hierarchy, layout, palette, typography, and caveats. A
similarity score is evidence for review, not an automatic recommendation.

### Q6: Tags and Agent Shortcuts

```bash
python scripts/figure_kb.py query --tag-all ML-benchmark --tag-all method-comparison
python scripts/figure_kb.py query --chart-type grouped-bar --limit 5
python scripts/figure_kb.py query --reference-id pattern-003 --limit 3
```

The skill-level aliases `kb:bar`, `kb:heat`, `kb:nature`, `kb:best`, `kb:weak`,
`kb:python`, `kb:r`, `kb:similar <id>`, and `kb:why <id>` should be translated
by the agent into the explicit CLI options shown above. The CLI's optional
`--shortcut` flag is retained for compatibility; it does not replace explicit
filters or add a second query implementation.

## Interpreting Results

For each selected pattern, report:

- why it matches the requested chart, layout, source, or tags;
- quality, objective validation, memory score, and application evidence;
- `success_cases`, `failure_cases`, and `recommendation_rationale` when present;
- any warning about a fallback scan or invalid files.

The LLM owns the scientific interpretation: the claim being made, which panel
is the hero panel, the evidence hierarchy, and the optional `ScientificReview`.
Python owns filtering, deterministic ranking, similarity, and data integrity.

## Empty, Unsupported, and Broken Data

- No matches: return a successful empty result and suggest one broader query.
- Missing or corrupt `index.json`: the query implementation may scan Markdown
  read-only and returns a structured warning. It must not rewrite the index.
- Invalid Markdown: skip the invalid file with a warning; use `index audit` to
  inspect it and `index rebuild` after it is corrected.
- An unsupported chart type is a capability result, not a query failure.

## Maintenance Commands

```bash
python scripts/figure_kb.py index audit
python scripts/figure_kb.py index rebuild
```

These commands operate on the configured KB and emit the same JSON Envelope.
Do not append to, sort, or repair `index.json` in an ad-hoc Python snippet.

## Checklist

- [ ] First Invocation Gate completed
- [ ] Query expressed with `scripts/figure_kb.py query`
- [ ] Filters and limit reflect the user's request
- [ ] Empty results handled as success
- [ ] Warnings and unsupported capability distinguished from errors
- [ ] Scientific recommendation explained by the LLM
