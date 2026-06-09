# Knowledge Base Schema

This document defines the complete format, indexing scheme, and maintenance protocols for the figure knowledge base (KB).

---

## Location and Directory Structure

### Primary Location
```
<configured-kb-path>/
```

**Rationale**:
- Outside skill folder: survives skill updates/deletion
- Defaults to Codex user data (`~/.codex/figure-kb`) unless the user chooses another location
- Reads legacy `~/.claude/figure-kb-config.json` only for backward compatibility
- Persists across all projects and sessions

See `kb-location-config.md` for the First Invocation Gate and path resolution order.

### Directory Organization

```
figure-kb/
├── index.json                    # Primary index (flat JSON array for fast queries)
├── rebuild_index.py              # Script to rebuild index from all .md files
├── patterns/
│   ├── chart-type/               # Organized by chart type
│   │   ├── grouped-bar/
│   │   │   ├── pattern-001.md
│   │   │   └── pattern-002.md
│   │   ├── heatmap/
│   │   ├── line-trend/
│   │   ├── scatter/
│   │   ├── bubble/
│   │   ├── radar-polar/
│   │   ├── forest-plot/
│   │   ├── image-plate/
│   │   └── ...                   # ~20 chart types total
│   ├── color-scheme/             # Organized by color strategy
│   │   ├── nature-nmi-pastel/
│   │   ├── nature-imaging/
│   │   ├── nature-clinical/
│   │   ├── nature-genomics/
│   │   ├── categorical-high-contrast/
│   │   └── ...
│   ├── layout-archetype/         # Organized by layout archetype
│   │   ├── quantitative-grid/
│   │   ├── schematic-led-composite/
│   │   ├── image-plate-quant/
│   │   └── asymmetric-mixed-modality/
│   └── journal/                  # Organized by source journal
│       ├── nature-2026/
│       ├── nature-machine-intelligence/
│       ├── science/
│       ├── cell/
│       └── ...
├── meta-patterns/                # Generalized templates from mature clusters
├── reflections/                  # Style lessons synthesized from repeated evidence
└── cache/                        # Optional cache for derived data
    └── extracted-palettes.json   # Quick hex palette lookup
```

**File placement**: Each analyzed pattern is saved as one `.md` file in the most relevant subdirectory (e.g., `patterns/chart-type/grouped-bar/pattern-003.md`). Cross-category links are handled via `index.json`.

---

## Entry Format

Each KB entry is a **Markdown file with YAML frontmatter**.

### Complete YAML Frontmatter Schema

```yaml
---
# ── Identity ──────────────────────────────────────────────────────────
id: pattern-001                    # Unique slug (auto-generated or manual)
source_type: image                 # "image" | "code" | "manual"

# ── Source Provenance ─────────────────────────────────────────────────
source_doi: "10.1038/s41586-026-xxxxx"  # DOI if from published paper
source_journal: Nature             # Journal name
source_year: 2026                  # Publication year
source_figure: "Figure 3"          # Figure number or label
source_paper_title: "..."          # Optional: paper title
source_url: "https://..."          # Optional: direct figure URL

# ── Chart Classification ──────────────────────────────────────────────
chart_type: grouped-bar            # From controlled vocabulary (20 types)
sub_chart_types: [scatter, line]  # If multi-panel with different types
layout_archetype: quantitative-grid # From 4 archetypes
panel_count: 3                     # Number of panels

# ── Visual Design ─────────────────────────────────────────────────────
color_scheme: nature-nmi-pastel    # From controlled vocabulary
extracted_colors: ["#484878", "#7884B4", "#B4C0E4"]  # Hex codes in dominance order
color_strategy_description: "Cool baseline family + warm hero family"
font_family: Arial                 # Arial | Helvetica | serif | other
base_font_size_pt: 7               # Base font size in points

# ── Pattern Matching ──────────────────────────────────────────────────
matched_nature_figure_pattern: 1   # Pattern # from nature-figure (1-16) or null
novel_pattern: false               # true if this is a new pattern not in nature-figure
novel_pattern_name: null           # If novel_pattern=true, give it a name

# ── Metadata ──────────────────────────────────────────────────────────
tags: [method-comparison, ML-benchmark, 6-methods]  # Free-form tags
quality_rating: 4                  # 1-5 scale (user or system assigned)
confidence: high                   # high | medium | low (for extracted parameters)
analysis_date: 2026-06-05          # YYYY-MM-DD

# ── Learning Loop Fields ──────────────────────────────────────────────
validation_score: 4                # 1-5: self-validation quality (Step 6 of WF1)
application_count: 0               # How many times this pattern was used
last_applied: null                 # YYYY-MM-DD or null
application_feedback: []           # List of {date, rating, notes} dicts
comparative_notes: []              # List of comparative learning insights
memory_score:                      # Composite retrieval score; agent/script generated
  total: 82.5
  components:
    quality: 24.0
    validation: 20.0
    reuse: 8.5
    feedback: 20.0
    recency: 10.0
  formula: quality30+validation25+reuse15+feedback20+recency10
success_cases: []                  # Positive user/application notes extracted by agent
failure_cases: []                  # Caveats, regressions, and avoid/recheck notes
recommendation_rationale: "High validation; reused successfully; check legend caveat"
relations:
  similar_to: []                    # Similar patterns for comparison or fallback
  superseded_by: []                 # Better patterns in same family, if any
  contraindicated_for: []           # Known bad-fit contexts, e.g. dense-panels

# ── Advanced ──────────────────────────────────────────────────────────
scientific_claim: "Method X improves Y by mechanism Z"  # Core conclusion
evidence_hierarchy: "hero: panel b, support: panel a/c"
statistical_annotations: "Error bars: SEM, significance: asterisks"
grid_structure: "2x2 with panel a spanning cols 1-2"
---

# Analysis Narrative

## Overview
Brief description of the figure and its role in the paper.

## Scientific Logic
- **Core conclusion**: [One-sentence claim]
- **Evidence hierarchy**: [Hero panel and supporting panels]
- **Panel questions**:
  - Panel a: [What unique question does it answer?]
  - Panel b: [...]

## Visual Encoding
- **Chart types**: Panel a = grouped-bar, Panel b = scatter
- **Data mappings**: x=method, y=accuracy, color=method family

## Color System
- **Palette**: Cool baseline (#484878, #7884B4) + warm hero (#E4CCD8, #F0C0CC)
- **Semantic roles**: Blue shades = baselines, pink shades = proposed variants
- **Consistency**: Same method → same color across all panels

## Typography
- **Font**: Arial (inferred from clean sans-serif appearance)
- **Sizes**: Panel labels 8pt bold, axis titles 6pt, tick labels 5pt

## Layout Geometry
- **Grid**: 1 row × 3 columns, equal width
- **Archetype**: quantitative-grid
- **Legend**: Dedicated panel (rightmost)

## Statistical Annotations
- **Error bars**: SEM (standard error of mean)
- **Significance**: Asterisks (* p<0.05, ** p<0.01)
- **Sample size**: Shown in legend as "(n=15)"

## Reusable Pattern
Matches **nature-figure pattern #1** (ultra-wide multi-metric bar).

### Key Parameters
- `figsize=(32, 7)`
- 3 metric panels + 1 legend panel
- Unified color family across all panels
- Dedicated legend panel with `ax.set_axis_off()`

### Code Sketch (Python)
\```python
fig, axes = plt.subplots(1, 4, figsize=(32, 7))
# Panel a: metric 1
# Panel b: metric 2
# Panel c: metric 3
# Panel d: legend only
axes[3].legend(..., loc='center')
axes[3].set_axis_off()
\```

## Validation
- **Self-validation score**: 4/5
- **Notes**: Color extraction accurate; font size estimated (original figure likely created at 2× scale)

## Application History
- **Used 0 times** (newly added to KB)
- **Last applied**: Never
- **Feedback**: None yet

## Comparative Learning Insights
None yet (will accumulate as this pattern is used and compared to new figures).
```

---

## Controlled Vocabularies

### Chart Types (20 types)
```
grouped-bar, stacked-bar, horizontal-bar, line-trend, multi-line, heatmap,
scatter, bubble, radar-polar, forest-plot, violin, box, density, pie-donut,
fill-between, sankey, upset, image-plate, schematic, network, other
```

If `chart_type: other`, must provide `chart_type_description` field.

### Color Schemes (10+ types)
```
nature-nmi-pastel, nature-imaging, nature-clinical, nature-genomics,
nature-material, categorical-high-contrast, sequential-single-hue,
diverging, monochrome, other
```

### Layout Archetypes (4 types)
```
quantitative-grid, schematic-led-composite, image-plate-quant,
asymmetric-mixed-modality
```

### Font Families
```
Arial, Helvetica, Times, serif, sans-serif, other
```

---

## index.json Format

The index is a **flat JSON array** of entry summaries for fast querying.

### Structure
```json
[
  {
    "id": "pattern-001",
    "file": "patterns/chart-type/grouped-bar/pattern-001.md",
    "source_type": "image",
    "source_journal": "Nature",
    "source_year": 2026,
    "chart_type": "grouped-bar",
    "color_scheme": "nature-nmi-pastel",
    "layout_archetype": "quantitative-grid",
    "tags": ["method-comparison", "ML-benchmark", "6-methods"],
    "quality_rating": 4,
  "validation_score": 4,
  "application_count": 0,
  "memory_score": {"total": 82.5},
  "matched_nature_figure_pattern": 1,
  "analysis_date": "2026-06-05"
  },
  {
    "id": "pattern-002",
    "file": "patterns/chart-type/heatmap/pattern-002.md",
    "...": "..."
  }
]
```

### Update Protocol
- **Add entry**: Create `.md` file → append to `index.json`
- **Remove entry**: Delete `.md` file → remove from `index.json`
- **Modify entry**: Edit `.md` file → update corresponding object in `index.json`

### Rebuild Command
If `index.json` becomes out of sync or corrupted:
```bash
python <configured-kb-path>\rebuild_index.py
```
This scans all `.md` files in `patterns/`, parses YAML frontmatter, and regenerates `index.json`.

---

## Query Operations

### Q1: Find by Chart Type
```python
import json
from pathlib import Path

kb_path = Path("<configured-kb-path>")
with open(kb_path / "index.json", encoding="utf-8") as f:
    index = json.load(f)

matches = [e for e in index if e["chart_type"] == "grouped-bar"]
```

### Q2: Find by Journal and Year
```python
matches = [e for e in index 
           if e["source_journal"] == "Nature" and e["source_year"] == 2026]
```

### Q3: Find by Multiple Criteria
```python
matches = [e for e in index 
           if e["chart_type"] == "grouped-bar" 
           and e["color_scheme"] == "nature-nmi-pastel"
           and e["quality_rating"] >= 4]
```

### Q4: Find by Tags
```python
target_tags = {"ML-benchmark", "method-comparison"}
matches = [e for e in index if target_tags.issubset(set(e["tags"]))]
```

### Q5: Sort by Memory Score, Quality, or Usage
```python
def ranking_score(entry):
    return (
        (entry.get("memory_score") or {}).get("total", 0),
        entry.get("quality_rating") or 0,
        entry.get("validation_score") or 0,
        entry.get("application_count") or 0,
    )

# Best evidence-backed patterns
top_ranked = sorted(index, key=ranking_score, reverse=True)[:5]

# Most-used patterns
most_used = sorted(index, key=lambda e: e["application_count"], reverse=True)[:5]
```

---

## Maintenance Protocols

### Protocol 1: Add New Entry
1. Analyze figure via WF1 or WF2
2. Generate unique `id` (e.g., `pattern-{next_number}` or `{journal}-{year}-fig{n}`)
3. Create `.md` file in appropriate subdirectory
4. Append entry summary to `index.json`
5. Optionally update `cache/extracted-palettes.json` if color scheme is new

### Protocol 2: Remove Entry
1. Delete `.md` file
2. Remove corresponding object from `index.json`
3. Recompute any cached aggregates if necessary

### Protocol 3: Update Entry
1. Edit `.md` file (modify YAML frontmatter or Markdown body)
2. Update corresponding fields in `index.json`
3. Set `analysis_date` to current date if substantive change

### Protocol 4: Rebuild Index
Run when:
- `index.json` is corrupted or lost
- Manually added/removed files without updating index
- After batch import of many figures

Command:
```bash
python rebuild_index.py
```

### Protocol 5: Deduplication Check
Before adding a new entry, check for near-duplicates:
1. Query `index.json` for entries with same `source_doi` + `source_figure`
2. If match found, decide:
   - **Same figure, different analysis**: Keep both, cross-reference in notes
   - **Same figure, redundant**: Skip or merge
3. If no DOI but visual similarity suspected, query by `chart_type` + `color_scheme` + `tags`

### Protocol 6: Quality Audit
Periodically review entries with:
- `validation_score < 3` → Re-analyze or flag for manual review
- `confidence: low` → Attempt to verify extracted parameters
- `quality_rating < 3` and `application_count > 5` → Pattern is frequently used but low-rated; investigate why

---

## Scaling Considerations

| KB Size | index.json Size | Query Performance | Recommendation |
|---------|----------------|-------------------|----------------|
| 0-100 | ~10 KB | Instant | Current design perfect |
| 100-500 | ~50 KB | <1 ms | Current design perfect |
| 500-1000 | ~100 KB | Few ms | Current design acceptable |
| 1000-5000 | ~500 KB | 10-50 ms | Consider SQLite upgrade |
| 5000+ | ~2.5 MB+ | 100+ ms | **Upgrade to SQLite** |

### SQLite Upgrade Path (Future)
When KB exceeds ~1000 entries, add `figure-kb/index.sqlite`:
- Markdown files remain the source of truth
- SQLite provides indexed queries and full-text search
- `rebuild_index.py` generates both `index.json` (for compatibility) and `index.sqlite`

Schema:
```sql
CREATE TABLE patterns (
    id TEXT PRIMARY KEY,
    file TEXT,
    source_type TEXT,
    source_journal TEXT,
    chart_type TEXT,
    color_scheme TEXT,
    layout_archetype TEXT,
    quality_rating INTEGER,
    validation_score INTEGER,
    application_count INTEGER,
    tags TEXT,  -- JSON array
    analysis_date TEXT
);
CREATE INDEX idx_chart_type ON patterns(chart_type);
CREATE INDEX idx_journal ON patterns(source_journal);
CREATE INDEX idx_quality ON patterns(quality_rating);
```

---

## Skill Growth Tracking

### Additional Fields for Learning Loop

Each entry tracks:
- `validation_score`: 1-5 scale, from self-validation (WF1 Step 6)
- `application_count`: How many times this pattern was applied via nature-figure
- `last_applied`: Date of last application
- `application_feedback`: Array of feedback objects:
  ```json
  [
    {"date": "2026-06-10", "rating": 4, "notes": "Good color scheme, but legend too small"},
    {"date": "2026-06-15", "rating": 5, "notes": "Perfect for this use case"}
  ]
  ```
- `comparative_notes`: Array of comparative learning insights (from WF1 Step 7)
- `memory_score`: Composite retrieval score. Agents should treat this as a ranking signal, not a guarantee of correctness.
- `success_cases`: Positive reuse notes or user comments that explain when the pattern works.
- `failure_cases`: Negative reuse notes, caveats, or manual review warnings.
- `relations`: `similar_to`, `superseded_by`, and `contraindicated_for` links inferred by the agent or `self_evolution_engine.py`.
- `recommendation_rationale`: Short human-readable reason for recommending or avoiding the entry.

### Agent Execution Rule

The schema defines what can be stored. It does not update itself. The agent must decide when to ask for feedback, when to run `scripts/self_evolution_engine.py`, and whether to accept or skip any generated memory updates.

### Monthly Growth Report
Run `generate_growth_report()` to produce:

```
Figure KB Growth Report: 2026-06
════════════════════════════════════════════════════════

Total Entries:        180  (↑ +30 from last month)
Average Quality:      4.1  (↑ +0.3 from last month)
Average Validation:   4.0  (↑ +0.2 from last month)

Coverage by Chart Type:
  grouped-bar:        25 entries
  heatmap:            18 entries
  scatter:            15 entries
  line-trend:         12 entries
  ...

Most Used Patterns (Top 5):
  1. pattern-012  (used 15 times, avg rating 4.5)
  2. pattern-003  (used 12 times, avg rating 4.2)
  ...

Weakest Patterns (Bottom 5):
  1. pattern-089  (radar-polar, avg rating 2.1)
  2. pattern-045  (forest-plot, avg rating 3.0)
  ...

Recommended Next Steps:
  → Analyze more radar-polar figures to improve that archetype
  → Review pattern-089's low rating; consider re-analysis
  → Your schematic-led-composite figures have consistently high ratings (4.7 avg)
```

---

## Example Entry (Complete)

See `patterns/chart-type/grouped-bar/pattern-001.md` in the KB for a complete example entry.
