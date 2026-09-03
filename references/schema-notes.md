# FigurePattern Schema Notes

## Authority

The executable schema is the `FigurePattern` model in
`src/nature_figure_learner/models.py`.

Use the CLI to inspect the current machine-readable schema:

```bash
python scripts/figure_kb.py schema export
```

The JSON Schema is returned in the JSON Envelope at `data.schema`.

[`schemas/pattern.schema.json`](../schemas/pattern.schema.json) is a checked-in
schema snapshot for external tooling. It must be kept synchronized with the
`FigurePattern` model. It is not a second, independently maintained contract.

Validate candidate records through the CLI:

```bash
python scripts/figure_kb.py pattern validate --input pattern.json
```

Do not validate or repair records by editing `index.json`.

## Runtime Required Fields

The following fields are required by `FigurePattern`:

```text
id
source_type
chart_type
layout_archetype
panel_count
color_scheme
analysis_date
```

The following fields are optional and may be null or omitted:

```text
source_doi
source_journal
source_year
source_figure
source_paper_title
source_url
chart_type_description
color_strategy_description
font_family
base_font_size_pt
matched_nature_figure_pattern
novel_pattern_name
quality_rating
validation_score
last_applied
memory_score
recommendation_rationale
scientific_claim
evidence_hierarchy
hero_panel
statistical_annotations
grid_structure
backend
figsize
dpi
```

Defaults include:

```text
schema_version: "1.0"
novel_pattern: false
confidence: "medium"
application_count: 0
sub_chart_types: []
tags: []
extracted_colors: []
application_feedback: []
comparative_notes: []
success_cases: []
failure_cases: []
relations: empty PatternRelations
export_formats: []
extensions: {}
```

## Controlled Vocabularies

`chart_type` has 20 concrete chart types plus the `other` escape hatch:

```text
grouped-bar
stacked-bar
horizontal-bar
line-trend
multi-line
heatmap
scatter
bubble
radar-polar
forest-plot
violin
box
density
pie-donut
fill-between
sankey
upset
image-plate
schematic
network
other
```

`sub_chart_types` uses the same vocabulary. `line` is not a valid value; use
`line-trend` or `multi-line`.

`layout_archetype` values:

```text
quantitative-grid
schematic-led-composite
image-plate-quant
asymmetric-mixed-modality
```

`color_scheme` values:

```text
nature-nmi-pastel
nature-imaging
nature-clinical
nature-genomics
nature-material
categorical-high-contrast
sequential-single-hue
diverging
monochrome
other
```

## Cross-Field Rules

- `chart_type: other` requires `chart_type_description`.
- `color_scheme: other` requires `color_strategy_description`.
- `novel_pattern: true` requires `novel_pattern_name`.
- `quality_rating` is a user or agent rating from 1 to 5 and may be null.
- `validation_score` is an interpreted 1-5 rating and may be null.
- Objective self-validation returns `objective_score` from 0 to 100. It must not
  be silently copied into `validation_score`.
- `source_doi` is normalized before duplicate detection.
- `memory_score`, when present, must include `total`, all score components, and
  the formula string.

## Minimal Valid Record

```yaml
---
id: pattern-001
source_type: image
chart_type: grouped-bar
layout_archetype: quantitative-grid
panel_count: 1
color_scheme: nature-nmi-pastel
analysis_date: 2026-09-03
quality_rating: null
validation_score: null
memory_score: null
---
```

## Persistence

Markdown pattern files are authoritative. The Repository writes the Markdown
file and derives `index.json` atomically.

Use:

```bash
python scripts/figure_kb.py pattern save \
  --input pattern.json \
  --narrative narrative.md \
  --duplicate-policy error
```

Use `skip`, `overwrite`, or `create-copy` only after the user chooses that
duplicate policy.
