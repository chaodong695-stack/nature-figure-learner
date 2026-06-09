---
name: nature-figure-learner
description: >-
  Use when the user wants to analyze figures from academic papers (PNG, screenshots, PDFs), extract reusable patterns from scientific plotting code (Python/R), build or query a searchable figure pattern knowledge base, learn from published figures to improve plotting ability, index a figure collection, show figure KB progress, or generate a growth report.
---

# Nature Figure Learner Skill

The learning/ingestion complement to `nature-figure`. This skill analyzes scientific figures and plotting code, stores reusable patterns in a figure knowledge base (KB), and lets future figure creation use those patterns as references.

`nature-figure-learner` is standalone. If `nature-figure` is also installed, use an explicit bridge workflow: query this KB before figure creation, then optionally feed successful finished figures back to the KB. Do not claim that `nature-figure` automatically reads this KB unless the active `nature-figure` skill explicitly says so.

---

## Skill vs Agent Boundary

This skill is documentation plus helper scripts. It does not execute by itself, monitor the user, pop up feedback forms, update the KB, or call `nature-figure` automatically.

The **agent** is the executor. The agent must read this skill, decide which workflow applies, ask the user for optional feedback, run scripts, write KB files, and explain recommendations. Always phrase automated behavior as "the agent should..." or "run the helper script..." rather than "the skill automatically...".

---

## First Invocation Gate

Before WF1, WF2, WF3, WF4, or any KB read/write operation, resolve the KB location.

Run or logically perform this gate:

```bash
python scripts/kb_location_manager.py --get-path
```

If the result is `NOT_CONFIGURED`, stop the requested workflow and automatically prompt the user to choose a figure KB storage location. Do not analyze a figure, parse plotting code, query the KB, or generate a growth report until the user has selected a location and the KB has been initialized.

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

| Workflow | Trigger | Reference File |
|----------|---------|----------------|
| WF1: Analyze figure image | User provides PNG/screenshot/PDF | [references/image-analysis-protocol.md](references/image-analysis-protocol.md) |
| WF2: Analyze plotting code | User provides Python/R script | [references/code-analysis-protocol.md](references/code-analysis-protocol.md) |
| WF3: Query knowledge base | "Search KB for grouped-bar figures" | [references/query-templates.md](references/query-templates.md) |
| WF4: Generate growth report | "Show my figure KB progress" | [references/growth-report-protocol.md](references/growth-report-protocol.md) |

Every workflow must pass the First Invocation Gate first.

---

## Knowledge Base Location

Path resolution order:

1. `FIGURE_KB_HOME`, if set.
2. Saved config at `$CODEX_HOME/figure-kb-config.json` or `~/.codex/figure-kb-config.json`.
3. Legacy saved config at `~/.claude/figure-kb-config.json`.
4. Default path `~/.codex/figure-kb`.

New configuration should be written to the Codex config path. The legacy `.claude` path is read only for compatibility.

The KB contains:

- `index.json`: primary index for fast queries
- `patterns/`: organized by chart type, color scheme, layout archetype, and journal
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

| File | Open When |
|------|-----------|
| [references/kb-location-config.md](references/kb-location-config.md) | First invocation setup, path selection, migration, disk-space handling |
| [references/analysis-framework.md](references/analysis-framework.md) | Need the complete seven-layer extraction taxonomy |
| [references/knowledge-base-schema.md](references/knowledge-base-schema.md) | Need KB format, YAML schema, index structure, controlled vocabularies |
| [references/image-analysis-protocol.md](references/image-analysis-protocol.md) | Analyzing a published figure image or PDF page |
| [references/code-analysis-protocol.md](references/code-analysis-protocol.md) | Analyzing Python matplotlib or R ggplot2 plotting code |
| [references/query-templates.md](references/query-templates.md) | Searching the KB for relevant patterns |
| [references/integration-bridge.md](references/integration-bridge.md) | Bridging learner KB with nature-figure creation |
| [references/growth-report-protocol.md](references/growth-report-protocol.md) | Generating progress and quality reports |

---

## Scripts

Reusable tools live in `scripts/`:

```bash
python scripts/kb_location_manager.py --get-path
python scripts/kb_location_manager.py --setup
python scripts/kb_location_manager.py --status
python scripts/kb_location_manager.py --reconfigure
python scripts/self_evolution_engine.py <configured-kb-path>
```

Do not store generated KB data inside the skill folder. The KB location is user configuration, not part of the skill package.

---

## Learning Loop

1. Self-validation: attempt to reproduce or validate extracted parameters and assign `validation_score`.
2. Immediate optional feedback: after a new pattern is added, the agent asks whether to record a user rating, success note, failure/caveat note, or skip.
3. Application feedback: record user feedback when a KB pattern is used.
4. Memory scoring: use `memory_score` to rank patterns by quality, validation, reuse, feedback, and recency.
5. Comparative learning: compare new figures against similar KB patterns.
6. Style reflection: when enough related patterns exist, synthesize what works and what to watch out for.
7. Capability measurement: growth reports summarize coverage, quality, usage, gaps, and recommended next learning targets.

### Stage 1 Optimizations

- After WF1/WF2 creates a pattern, the agent should offer a skippable feedback prompt.
- Each entry should support `memory_score`, `success_cases`, `failure_cases`, and `recommendation_rationale`.
- Query ranking should prefer `memory_score.total` when present, then fall back to quality, validation, and usage.
- Growth reports should include "what to learn next" recommendations.

### Stage 2 Optimizations

- Mature clusters should produce `meta-patterns/` entries.
- Mature clusters should produce `reflections/` entries that summarize style lessons.
- Related patterns should track `similar_to`, `superseded_by`, and `contraindicated_for` relationships.
- `kb:why <id>` should explain why an agent recommends or avoids a pattern.

---

## Query Shortcuts

| Shorthand | Expands to |
|-----------|------------|
| `kb:bar` | Find grouped-bar patterns |
| `kb:heat` | Find heatmap patterns |
| `kb:nature` | Find Nature journal patterns |
| `kb:best` | Show most-used or highest-rated patterns |
| `kb:weak` | Show weakest patterns for improvement |
| `kb:python` | Find patterns with Python code |
| `kb:r` | Find patterns with R code |
| `kb:similar <id>` | Find patterns similar to an existing entry |
| `kb:why <id>` | Explain why a pattern is recommended, including evidence and caveats |

---

## Error Handling

### KB Not Configured

If `scripts/kb_location_manager.py --get-path` returns `NOT_CONFIGURED`, stop and prompt the user to choose a storage location. This is mandatory on first invocation.

### KB Directory Missing

If a path is configured but `<configured-kb-path>/index.json` is missing, initialize the KB directory structure and create `index.json` with `[]` before continuing.

### No Query Matches

If a query returns no results, suggest broader criteria or analyzing new figures to add examples. Do not error out.

### Duplicate Entry

Before creating an entry, check `index.json` for the same `source_doi` plus `source_figure`. Ask whether to skip, overwrite, or create a duplicate.

---

## When Not To Use

- User only wants to create a figure without learning or querying references; use `nature-figure` directly.
- Interactive plotting dashboards such as Plotly, Altair, or Bokeh.
- 3D visualization, GIS, or non-scientific plots.
- Illustrator/Figma-first workflows.
