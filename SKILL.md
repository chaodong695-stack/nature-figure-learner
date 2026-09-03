---
name: nature-figure-learner
description: >-
  Use when the user wants to analyze figures from academic papers (PNG, screenshots, PDFs), extract reusable patterns from scientific plotting code (Python/R), build or query a searchable figure pattern knowledge base, learn from published figures to improve plotting ability, index a figure collection, show figure KB progress, or generate a growth report.
---
# Nature Figure Learner Skill

The learning/ingestion complement to `nature-figure`. This skill analyzes scientific figures and plotting code, can store reusable patterns in a figure knowledge base (KB) when requested, and lets future figure creation use those patterns as references.

`nature-figure-learner` is standalone. If `nature-figure` is also installed, use an explicit bridge workflow: query this KB before figure creation, then optionally feed successful finished figures back to the KB. Do not claim that `nature-figure` automatically reads this KB unless the active `nature-figure` skill explicitly says so.

---

## Skill vs Agent Boundary

This skill is documentation plus a small, install-free Python package and CLI. It does not execute by itself, monitor the user, pop up feedback forms, update the KB, or call `nature-figure` automatically.

### Trigger Ownership

The skill documents workflow routing rules; the agent selects and executes the
appropriate workflow. The runtime does not infer a workflow from an attachment
alone.

A supplied file is an eligible input, not a trigger. Require explicit user
intent to analyze, learn, import, query, or report before starting a workflow.
When the intent is ambiguous, ask for clarification before running the First
Invocation Gate or performing any KB operation.

## Workflow Routing

Select the workflow from the user's explicit intent and supplied artifact.
Receiving a file alone is not sufficient to trigger WF1 or WF2.

| Workflow | Trigger when | Required input | Default result |
|----------|--------------|----------------|----------------|
| WF1 | The user asks to analyze, learn from, or extract reusable visual patterns from a figure image, screenshot, or PDF page | Image, screenshot, or selected PDF page | Seven-layer visual analysis; save a pattern when learning/import is requested |
| WF2 | The user asks to analyze plotting code, extract figure parameters, or create a reusable plotting template | Python/R code or script | Technical extraction and parameterized template; save a pattern when learning/import is requested |
| WF3 | The user asks to search, filter, compare, recommend, or explain saved KB patterns | Configured KB and query criteria or pattern ID | Read-only query results with ranking evidence |
| WF4 | The user asks for KB progress, statistics, quality trends, coverage, capability gaps, or learning recommendations | Configured KB | Growth report; save it only when explicitly requested |

Do not trigger WF1 or WF2 for an uploaded file when the user has not requested
analysis, learning, or import. Do not trigger WF3 or WF4 for ordinary figure
creation unless the user explicitly requests KB lookup or progress reporting.

If both plotting code and its rendered image are supplied, run WF2 for code
extraction and WF1 for rendered-figure analysis. Keep the two analyses linked by
provenance, but do not silently merge them into one pattern record.

The **agent** is the executor. The agent must read this skill, decide which workflow applies, run scripts, persist KB files only when requested, offer optional feedback for persisted patterns, and explain recommendations. Always phrase automated behavior as "the agent should..." or "run the helper script..." rather than "the skill automatically...".

## Deterministic Tool Boundary

Use `scripts/figure_kb.py` for repeatable operations. The launcher emits one
JSON Envelope on stdout; progress and debug information belong on stderr.

```bash
python scripts/figure_kb.py schema export
python scripts/figure_kb.py pattern validate --input pattern.json
python scripts/figure_kb.py pattern save --input pattern.json --narrative narrative.md
python scripts/figure_kb.py query --chart-type grouped-bar --limit 5
python scripts/figure_kb.py self-validate --pattern-id pattern-001 --output-dir previews
python scripts/figure_kb.py index audit
python scripts/figure_kb.py index rebuild
```

The LLM owns `scientific_claim`, `hero_panel`, `evidence_hierarchy`, and the
optional `ScientificReview`: these require scientific interpretation. Python
owns schema validation, path resolution, DOI deduplication, Markdown
persistence, derived-index rebuilds, deterministic query ranking, synthetic
mock data, rendering adapters, and objective image validation. An unsupported
renderer is a capability result, not a validation failure.

The first renderer set supports `grouped-bar`, `stacked-bar`, `horizontal-bar`,
`line-trend`, `multi-line`, `scatter`, `bubble`, `heatmap`, `violin`, and
`box`. Other schema chart types are valid patterns but return an
`unsupported` capability result until an adapter exists.

Normal workflows run the launcher commands only; they do not run the test
suite. Tests are for development and release verification.

---

## First Invocation Gate

Before WF1, WF2, WF3, WF4, or any KB read/write operation, resolve the KB location.

Run or logically perform this gate:

```bash
python scripts/kb_location_manager.py --get-path
```

If the result is `NOT_CONFIGURED`, stop the requested workflow and have the
agent prompt the user to choose a figure KB storage location. Do not analyze a
figure, parse plotting code, query the KB, or generate a growth report until
the user has selected a location and the KB has been initialized.

Prompt options:

```text
Figure Knowledge Base Setup

This is your first time using nature-figure-learner.
Choose where to store the figure KB:

[A] ~/.codex/figure-kb
    Keeps Codex agent data together; may use home/system drive space.

[B] Suggested data-drive path
    Uses a larger data drive if available.

[C] Custom absolute path

[D] Ask every time
```

After the user chooses, initialize the KB:

```bash
python scripts/kb_location_manager.py --setup
```

If the user gave the path directly, use that path in the setup flow. If an existing legacy `~/.claude/figure-kb-config.json` exists, read it for compatibility but write new configuration to the Codex config path.

---

## Core Workflows

| Workflow                    | Trigger                             | Reference File                                                         |
| --------------------------- | ----------------------------------- | ---------------------------------------------------------------------- |
| WF1: Analyze figure image   | Explicit request to analyze/learn from a PNG, screenshot, or PDF | [references/WF1-image.md](references/WF1-image.md)        |
| WF2: Analyze plotting code  | Explicit request to analyze/extract from Python or R code        | [references/WF2-code.md](references/WF2-code.md)          |
| WF3: Query knowledge base   | Explicit request to search/filter/recommend KB patterns          | [references/WF3-query.md](references/WF3-query.md)        |
| WF4: Generate growth report | Explicit request for KB progress/statistics/recommendations     | [references/WF4-growth-report.md](references/WF4-growth-report.md) |

Every workflow must pass the First Invocation Gate first.

## Batch Processing

A batch task is not a new scientific workflow. It repeats WF1 independently for
each supported image/PDF input and repeats WF2 independently for each supported
Python/R input. A batch analysis without an import/persistence request validates
each candidate but keeps the records transient.

When the user provides a directory, file list, glob, or explicitly requests
batch import:

- Expand inputs and process them in deterministic path-sorted order.
- Image files and selected PDF pages repeat WF1 one item at a time.
- Python/R files repeat WF2 one item at a time.
- Keep per-item status, output ID, warnings, retry count, duplicate result, and
  failure reason.
- One failed or duplicate item must not roll back successful items.
- Do not perform cross-file scientific synthesis unless the user explicitly asks
  for it after individual analyses finish.
- For batch import or persistence, save every item through `pattern save`; never
  batch-edit `index.json`. For analysis-only batches, do not save items.

Retry only transient failures, such as a retryable CLI error, temporary I/O
failure, or active KB lock. Use a bounded policy: at most two retries after the
initial attempt. Do not automatically retry schema errors, unsupported formats,
or duplicate conflicts. Preserve the first and final error so the batch can
resume without reprocessing successful items.

For deduplication, first normalize duplicate input paths. For KB records, use
Repository duplicate detection:

1. Normalize DOI values by removing `doi:`/resolver prefixes and lowercasing.
2. Compare `(normalized source_doi, normalized source_figure)` only when both
   fields are present.
3. Treat an existing pattern ID as an ID conflict.
4. If DOI or figure metadata is missing, do not claim provenance deduplication;
   report the limitation.
5. Use `error` by default. Ask before choosing `skip`, `overwrite`, or
   `create-copy`; `create-copy` requires a new unique pattern ID.
6. In batch mode, record a duplicate item and continue with the remaining items.

---

## Knowledge Base Location

Path resolution order:

1. `FIGURE_KB_HOME`, if set.
2. Saved config at `$CODEX_HOME/figure-kb-config.json` or `~/.codex/figure-kb-config.json`.
3. Legacy saved config at `~/.claude/figure-kb-config.json`.
4. The setup prompt suggests `~/.codex/figure-kb`; it is not an automatic
   fallback. Until setup or an explicit environment/configuration is present,
   the manager returns `NOT_CONFIGURED`.

New configuration should be written to the Codex config path. The legacy `.claude` path is read only for compatibility.

The KB contains:

- `index.json`: derived index for fast queries (Markdown is authoritative)
- `patterns/chart-type/`: authoritative Markdown files organized by chart type;
  color scheme, layout archetype, and journal are query/index fields, not
  duplicate storage trees
- `meta-patterns/`: generalized templates synthesized from mature pattern clusters
- `reflections/`: style reflections generated from repeated success/failure evidence
- `reports/`: growth reports
- one pattern `.md` file per analyzed figure or code pattern

See [references/kb-location-config.md](references/kb-location-config.md) for the location protocol.

---

## Analysis Depth

When analyzing a figure or plotting code, extract seven layers:

1. Scientific logic: core conclusion, evidence hierarchy, panel questions
2. Visual encoding: chart types, data-to-visual mappings, scale transformations
3. Color system: palette, strategy, semantic roles
4. Typography: font family inference, size hierarchy, weight usage
5. Layout geometry: grid structure, archetype, panel proportions
6. Statistical annotations: error types, significance display, sample size visibility
7. Reusable pattern: match a known pattern or define a new one

Use [references/analysis-framework.md](references/analysis-framework.md) for the full extraction taxonomy.

---

## Integration With nature-figure

`nature-figure` does not automatically read this KB unless its own workflow or the user explicitly asks it to do so.

When using both skills together:

- Before figure creation: query this KB for relevant patterns.
- During color/layout selection: use proven palettes and layouts from KB entries.
- After creation: ask whether to analyze the finished figure and add it to the KB.

Use [references/integration-bridge.md](references/integration-bridge.md) for bridge details.

---

## Quick Reference Table

| File                                                                   | Open When                                                              |
| ---------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| [references/kb-location-config.md](references/kb-location-config.md)    | First invocation setup, path selection, migration, disk-space handling |
| [references/analysis-framework.md](references/analysis-framework.md)    | Need the complete seven-layer extraction taxonomy                      |
| [references/schema-notes.md](references/schema-notes.md)       | Need KB format, YAML schema, index structure, controlled vocabularies  |
| [references/WF1-image.md](references/WF1-image.md)        | Analyzing a published figure image or PDF page                         |
| [references/WF2-code.md](references/WF2-code.md)          | Analyzing Python matplotlib or R ggplot2 plotting code                 |
| [references/WF3-query.md](references/WF3-query.md)                | Searching the KB for relevant patterns                                 |
| [references/integration-bridge.md](references/integration-bridge.md)    | Bridging learner KB with nature-figure creation                        |
| [references/WF4-growth-report.md](references/WF4-growth-report.md) | Generating progress and quality reports                                |

---

## Scripts

Reusable tools live in `scripts/`:

```bash
python scripts/kb_location_manager.py --get-path
python scripts/kb_location_manager.py --setup
python scripts/kb_location_manager.py --status
python scripts/kb_location_manager.py --reconfigure
python scripts/figure_kb.py query --chart-type grouped-bar --limit 5
python scripts/figure_kb.py pattern validate --input pattern.json
python scripts/figure_kb.py pattern save --input pattern.json --narrative narrative.md
python scripts/figure_kb.py self-validate --pattern-id pattern-001 --output-dir previews
python scripts/self_evolution_engine.py <configured-kb-path>
```

Do not store generated KB data inside the skill folder. The KB location is user configuration, not part of the skill package.

---

## Learning Loop

1. Self-validation: after a requested save, attempt to reproduce extracted parameters and record the CLI `objective_score` (0-100). An interpreted `validation_score` (1-5) is optional and must remain separate.
2. Immediate optional feedback: after a requested pattern is persisted, the agent asks whether to record a user rating, success note, failure/caveat note, or skip.
3. Application feedback: record user feedback when a KB pattern is used.
4. Memory scoring: use `memory_score` to rank patterns by quality, validation, reuse, feedback, and recency.
5. Comparative learning: compare new figures against similar KB patterns.
6. Style reflection: when enough related patterns exist, synthesize what works and what to watch out for.
7. Capability measurement: growth reports summarize coverage, quality, usage, gaps, and recommended next learning targets.

### Stage 1 Optimizations

- After WF1/WF2 persists a requested pattern, the agent should offer a skippable feedback prompt.
- Each entry should support `memory_score`, `success_cases`, `failure_cases`, and `recommendation_rationale`.
- Query ranking is implemented by the CLI; do not recreate sorting logic in a workflow note or ad-hoc script.
- Growth reports should include "what to learn next" recommendations.

### Stage 2 Optimizations

- Mature clusters should produce `meta-patterns/` entries.
- Mature clusters should produce `reflections/` entries that summarize style lessons.
- Related patterns should track `similar_to`, `superseded_by`, and `contraindicated_for` relationships.
- `kb:why <id>` should explain why an agent recommends or avoids a pattern.

---

## Query Shortcuts

| Shorthand           | Expands to                                                           |
| ------------------- | -------------------------------------------------------------------- |
| `kb:bar`          | Find grouped-bar patterns                                            |
| `kb:heat`         | Find heatmap patterns                                                |
| `kb:nature`       | Find Nature journal patterns                                         |
| `kb:best`         | Show most-used or highest-rated patterns                             |
| `kb:weak`         | Show weakest patterns for improvement                                |
| `kb:python`       | Find patterns with Python code                                       |
| `kb:r`            | Find patterns with R code                                            |
| `kb:similar <id>` | Find patterns similar to an existing entry                           |
| `kb:why <id>`     | Explain why a pattern is recommended, including evidence and caveats |

---

## Error Handling

### KB Not Configured

If `scripts/kb_location_manager.py --get-path` returns `NOT_CONFIGURED`, stop and prompt the user to choose a storage location. This is mandatory on first invocation.

### KB Directory Missing

If a path is configured but `<configured-kb-path>/index.json` is missing, use the CLI's `index rebuild` command after the Markdown directory is initialized. The index is derived and must not be hand-edited.

### No Query Matches

If a query returns no results, suggest broader criteria or analyzing new figures to add examples. Do not error out.

### Duplicate Entry

Before creating an entry, run `pattern validate` and then `pattern save` with
its duplicate policy (`error`, `skip`, `overwrite`, or `create-copy`). The
Repository checks the same `source_doi` plus `source_figure` without requiring
an agent-maintained index.

---

## When Not To Use

- User only wants to create a figure without learning or querying references; use `nature-figure` directly.
- Interactive plotting dashboards such as Plotly, Altair, or Bokeh.
- Illustrator/Figma-first workflows.
