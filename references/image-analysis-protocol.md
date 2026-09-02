# Image Analysis Protocol (WF1)

Complete step-by-step protocol for analyzing a scientific figure from an image (PNG, screenshot, or PDF page).

**Input**: Image file + optional metadata (DOI, journal, figure number)  
**Output**: Deep analysis report plus a validated KB entry saved through the
Repository CLI. The Markdown entry is authoritative; `index.json` is derived.

---

## Prerequisites

### User Provides
- Image file (PNG, JPG, PDF page, or screenshot)
- **Optional but recommended**:
  - Paper DOI
  - Journal name
  - Figure number
  - Publication year
  - Paper title

### Agent Preparation
1. Ensure `analysis-framework.md` is loaded (for extraction taxonomy)
2. Ensure `knowledge-base-schema.md` is loaded (for output format)
3. Run the First Invocation Gate from `SKILL.md` / `kb-location-config.md`.
4. Resolve `<configured-kb-path>` only after the KB path is configured.
5. Do not hand-edit or precompute IDs from `index.json`; prepare a valid pattern
   and let `pattern save` apply duplicate policy and update the derived index.

---

## Step 1: Initial Observation

**Goal**: Get a high-level understanding of the figure structure.

### 1.1 View the Image
- Open/display the image
- If PDF, extract the relevant page
- Ensure image is clear enough for analysis

### 1.2 Count and Label Panels
- **Panel count**: How many distinct panels?
- **Panel labels**: Are panels labeled (a, b, c) or (A, B, C) or unlabeled?
- **Layout observation**: Grid (rows × cols)? Asymmetric? Overlapping?

### 1.3 Initial Archetype Guess
Based on visual structure, make initial classification:
- **quantitative-grid**: Regular grid of equal-sized quantitative plots
- **schematic-led-composite**: Large schematic/diagram (45-60% height) + smaller plots
- **image-plate-quant**: Dark microscopy/imaging plate + adjacent plots
- **asymmetric-mixed-modality**: Unequal panels, mixed modalities

### 1.4 Identify Apparent Core Claim
From title, caption, or visual hierarchy:
- What is the one-sentence claim this figure defends?
- Format: Must have verb + relationship (e.g., "X improves Y by Z")

---

## Step 2: Per-Panel Deep Analysis

For **each panel** (a, b, c, ...), extract the following:

### 2.1 Chart Type Identification
Use controlled vocabulary (20 types from `analysis-framework.md`):
- Is it `grouped-bar`, `heatmap`, `scatter`, `line-trend`, etc.?
- If multi-panel figure, list chart type for each panel

### 2.2 Color Extraction
- **Sample dominant colors** from the image
- **Estimate hex codes** (use visual inspection or color picker if available)
- **List in dominance order** (most prominent first)
- **Identify semantic roles**:
  - Which color = proposed method?
  - Which color = baseline?
  - Which color = positive/negative variant?

Example:
```
Panel a colors:
  - #484878 (dark blue) → Baseline method A
  - #7884B4 (medium blue) → Baseline method B
  - #E4CCD8 (pink) → Proposed method (ours)
```

### 2.3 Typography Estimation
**Font family** (infer from visual characteristics):
- Grotesque sans-serif (Arial/Helvetica) — even strokes, open apertures
- Serif (Times) — serifs at letter terminals
- Other (condensed, rounded, geometric)

**Size hierarchy** (estimate relative sizes in pt):
- Panel label size (e.g., "a" in bold)
- Axis title size
- Tick label size
- In-panel annotation size
- Legend text size

**Note**: Published figures are often scaled down 2-3×, so a 24pt label in creation may render as 8pt in print. Estimate the **final rendered size**.

### 2.4 Axis and Scale Analysis
- **X-axis**: Categorical? Continuous? Time-based? What does it represent?
- **Y-axis**: What variable? What unit?
- **Scale**: Linear or log? Normalized (0-100%) or absolute?
- **Limits**: Tight to data range (e.g., 80-95) or fixed (0-100)?
- **Transformations**: Z-score? Percent change? Other?

### 2.5 Statistical Annotation Inventory
- **Error bars**: Present? What type (SD, SEM, CI, IQR)?
- **Significance markers**: Asterisks? P-values? Brackets?
- **Sample size**: Shown in legend, caption, or on plot?
- **Test type mentioned**: t-test, ANOVA, Wilcoxon, etc.?

### 2.6 Legend and Label Strategy
- **Legend location**: Dedicated panel? Shared strip? Per-panel? Direct labels? Omitted?
- **Legend content**: Colors + labels? Includes n? Includes error type?
- **Direct labeling**: Are categories labeled directly on the plot?

---

## Step 3: Cross-Panel Synthesis

**Goal**: Understand how panels work together.

### 3.1 Color Consistency Check
- Is the **same condition/method mapped to the same color** across all panels?
- Example: If "Method A" is blue in panel a, is it also blue in panel b?
- **Verdict**: Consistent ✅ / Inconsistent ⚠️

### 3.2 Evidence Hierarchy Assessment
- **Hero panel**: Which panel carries the main claim? (Usually largest, most central, or most complex)
- **Supporting panels**: Which provide validation, mechanism, or context?
- **Control panels**: Which show baselines or robustness checks?

### 3.3 Panel-to-Claim Mapping
For each panel, answer:
- What **unique scientific question** does this panel answer?
- How does it **support the core conclusion**?
- Could this panel be removed without loss of information? (If yes, it's redundant)

### 3.4 Information Architecture Check
Use the **anti-redundancy checklist** from `analysis-framework.md`:
- [ ] Panel b does NOT re-display the same data as panel a in different form
- [ ] Panel c adds a dimension absent from a and b
- [ ] Each panel has distinct axis-label vocabulary

---

## Step 4: Layout Geometry Extraction

### 4.1 Grid Structure
- **Rows × columns**: e.g., 2×3, 1×4, 3×2, asymmetric
- **Spanning**: Does one panel span multiple grid cells?
- **Height ratios**: If multi-row, are rows equal height? Estimate ratio (e.g., `[2, 1]`)
- **Width ratios**: If multi-column, are columns equal width? Estimate ratio

### 4.2 Archetype Finalization
Refine initial guess:
- **quantitative-grid**: Equal-sized panels, all quantitative
- **schematic-led-composite**: Large schematic + small quant panels
- **image-plate-quant**: Dark imaging plate + quant plots
- **asymmetric-mixed-modality**: Unequal panels, mixed modalities

### 4.3 Panel Proportions
- Which panel occupies the most area?
- Aspect ratios: Wide (3:1), square (1:1), tall (1:2)?
- Gutter size: Tight or generous?

### 4.4 Color Strategy Classification
Classify the overall color strategy:
- `nature-nmi-pastel` — Low-saturation unified families
- `nature-imaging` — Grayscale + fluorescent channels on black
- `nature-clinical` — Dark baseline, restrained warm/cool, pale bands
- `nature-genomics` — Grey scaffolds + small highlights
- `categorical-high-contrast` — Saturated distinct hues
- `sequential-single-hue` — Light → dark gradient
- `diverging` — Two-hue diverging (e.g., red-blue)
- `monochrome` — Grayscale
- `other` — Specify in notes

---

## Step 5: Pattern Extraction

**Goal**: Identify which nature-figure pattern this figure uses, or define a new pattern.

### 5.1 Match Against Known Patterns
Check against **nature-figure's 16 common patterns** (from `analysis-framework.md` Section 7.1):

| Pattern # | Name | Key Feature |
|-----------|------|-------------|
| 1 | Ultra-wide multi-metric bar | `figsize=(28-45, 6-12)`, 4+ metrics, dedicated legend |
| 2 | Compact single bar | One metric, `figsize=(9-16, 5-8)` |
| 3 | Horizontal ablation bar | `ax.barh()`, alpha gradient |
| ... | ... | ... |
| 16 | Asymmetric hero layout | One large central panel, small support plots |

**Record**:
- `matched_nature_figure_pattern`: Pattern number (1-16) or `null`
- `novel_pattern`: `true` if no match, `false` otherwise

### 5.2 Novel Pattern Detection
If no match, define a new pattern:
- **Pattern name**: Short descriptive name (e.g., "circular-timeline-with-insets")
- **Key feature**: What makes it structurally distinct?
- **When to use**: Scientific use case
- **Parameterization**: What varies across instances?

### 5.3 Parameterized Layout Template
If enough detail is visible, sketch the layout structure:
```python
# Example for 1×3 grid with legend panel
fig, axes = plt.subplots(1, 4, figsize=(28, 7))
# axes[0-2]: data panels
# axes[3]: legend only
axes[3].legend(..., loc='center')
axes[3].set_axis_off()
```

---

## Step 6: Self-Validation (Learning Loop)

**Goal**: Verify analysis quality by attempting to reproduce the figure.

### 6.1 Generate Mock Data and Preview

Prepare a `MockDataSpec` only for dimensions that are visible in the source.
The deterministic generator owns seed derivation and typed payload shape. Run
the full mock/render/objective-validation path through the CLI:

```bash
python scripts/figure_kb.py self-validate \
  --pattern-id pattern-001 \
  --spec mock-spec.json \
  --output-dir previews
```

The renderer supports grouped/stacked/horizontal bars, line and multi-line,
scatter and bubble, heatmap, violin, and box. Other chart types return
`unsupported` with exit code 0. A renderer error is distinct from an objective
validation failure.

### 6.2 Objective Checks

Python checks schema dimensions, image readability and non-blank pixels,
expected dimensions, panel metadata, layout metadata, palette proximity, and
font fallback. The command returns checks and an objective score in the JSON
Envelope. It does not assign a scientific validation claim.

### 6.3 Scientific Review

The LLM compares the preview with the source and records the scientific
interpretation: whether the claimed relationship is represented, which panel
is the hero panel, the evidence hierarchy, and any limitations. Keep this
`ScientificReview` separate from objective checks; do not synthesize it from
pixel scores.

### 6.4 Decision

Use objective warnings and the LLM's review to decide whether extracted
parameters need manual review. A low objective score, render error, or
unsupported capability must be described separately in the pattern narrative.

---

## Step 7: Comparative Learning (Optional)

**Goal**: Learn by comparing this figure to existing KB entries.

**Trigger**: If this is a newly created figure (not just analyzed from literature), or if user requests comparative analysis.

### 7.1 Query KB for Similar Patterns
Run a read-only query for entries with the same `chart_type`,
`layout_archetype`, and similar tags:

```bash
python scripts/figure_kb.py query --chart-type grouped-bar --limit 3
```

Use the actual chart type and add layout/tag filters as needed. The CLI owns
filtering and ranking; the agent owns the scientific comparison.

### 7.2 Side-by-Side Comparison
For each reference, compare:

**Color comparison**:
- New figure vs. reference: saturation, contrast, semantic consistency
- Which has better color discipline?
- Which is more readable?

**Layout comparison**:
- Panel proportions: Which allocation is clearer?
- Gutter strategy: Tight or generous?
- Legend strategy: Which is more effective?

**Typography comparison**:
- Size hierarchy: Which is more readable?
- Font choice: Which fits the modality better?

### 7.3 Record Insights
Document findings in `comparative_notes`:
```yaml
comparative_notes:
  - date: 2026-06-05
    compared_to: pattern-012
    insights: "New figure uses more restrained saturation (better for dense multi-panel). Reference pattern-012's legend placement (dedicated panel) is superior to inline legends."
    improvements: ["Lower saturation", "Unified color family"]
    regressions: ["Legend too small", "Gutter too tight"]
```

---

## Step 8: KB Entry Creation

**Goal**: Create a permanent record in the knowledge base.

### 8.1 Generate Unique ID
- Use a valid stable slug such as `pattern-001` or `nature-2026-fig3`.
- `pattern save` validates the ID, checks duplicates, and applies the selected
  duplicate policy. Do not derive uniqueness by editing `index.json`.

### 8.2 Construct YAML Frontmatter
Using the schema from `knowledge-base-schema.md`, populate all fields:
```yaml
---
id: pattern-003
source_type: image
source_doi: "10.1038/s41586-026-10408-8"
source_journal: Nature
source_year: 2026
source_figure: "Figure 3"
chart_type: grouped-bar
sub_chart_types: []
layout_archetype: quantitative-grid
panel_count: 3
color_scheme: nature-nmi-pastel
extracted_colors: ["#484878", "#7884B4", "#B4C0E4", "#E4CCD8"]
font_family: Arial
base_font_size_pt: 7
matched_nature_figure_pattern: 1
novel_pattern: false
tags: [method-comparison, ML-benchmark, 6-methods]
quality_rating: null
confidence: high
analysis_date: 2026-06-05
validation_score: 4
application_count: 0
last_applied: null
application_feedback: []
comparative_notes: []
memory_score: null
success_cases: []
failure_cases: []
recommendation_rationale: null
relations:
  similar_to: []
  superseded_by: []
  contraindicated_for: []
scientific_claim: "Proposed method X outperforms baselines Y and Z across 3 benchmarks"
evidence_hierarchy: "hero: panel b (main result), support: panels a/c (ablation and generalization)"
statistical_annotations: "Error bars: SEM, significance: asterisks (* p<0.05)"
grid_structure: "1×3 equal-width panels + 1 legend panel"
---
```

### 8.3 Write Analysis Narrative
In Markdown body, write structured sections:
1. **Overview**: Brief description
2. **Scientific Logic**: Core conclusion, evidence hierarchy, panel questions
3. **Visual Encoding**: Chart types, data mappings
4. **Color System**: Palette, semantic roles, consistency
5. **Typography**: Font, sizes
6. **Layout Geometry**: Grid, archetype, legend
7. **Statistical Annotations**: Error type, significance, sample size
8. **Reusable Pattern**: Matched pattern or novel pattern definition
9. **Validation**: Self-validation results
10. **Application History**: Initially empty
11. **Comparative Learning Insights**: From Step 7 if applicable

### 8.4 Save and Derive the Index

Write the narrative to a temporary agent-owned file, then run:

```bash
python scripts/figure_kb.py pattern save \
  --input pattern.json \
  --narrative narrative.md \
  --duplicate-policy error
```

The Repository chooses the safe chart-type path, validates frontmatter,
preserves the narrative, checks DOI/figure duplicates, and atomically updates
the derived `index.json`. Use `skip`, `overwrite`, or `create-copy` only when
the user explicitly chooses that duplicate policy.

---

## Step 9: Output to User

Present a **structured analysis report** summarizing findings:

### Report Structure
```
═══════════════════════════════════════════════════════════════
Figure Analysis Complete
═══════════════════════════════════════════════════════════════

Source: Nature (2026), Figure 3
DOI: 10.1038/s41586-026-10408-8
Analyzed: 2026-06-05

─────────────────────────────────────────────────────────────
CORE CONCLUSION
─────────────────────────────────────────────────────────────
"Proposed method X outperforms baselines Y and Z across 3 benchmarks"

─────────────────────────────────────────────────────────────
CHART CLASSIFICATION
─────────────────────────────────────────────────────────────
Type: grouped-bar (3 panels)
Layout: quantitative-grid (1×3 + legend)
Matched pattern: nature-figure #1 (ultra-wide multi-metric bar)

─────────────────────────────────────────────────────────────
COLOR SYSTEM
─────────────────────────────────────────────────────────────
Strategy: nature-nmi-pastel (unified families)
Palette:
  • #484878 (dark blue) → Baseline A
  • #7884B4 (medium blue) → Baseline B
  • #E4CCD8 (pink) → Proposed method
Consistency: ✅ Same method → same color across panels

─────────────────────────────────────────────────────────────
TYPOGRAPHY
─────────────────────────────────────────────────────────────
Font: Arial (inferred)
Sizes: Panel labels 8pt, axis titles 6pt, ticks 5pt

─────────────────────────────────────────────────────────────
VALIDATION
─────────────────────────────────────────────────────────────
Self-validation score: 4/5 (Good match)
Confidence: high
Notes: Color extraction accurate; layout structure verified

─────────────────────────────────────────────────────────────
KB ENTRY CREATED
─────────────────────────────────────────────────────────────
ID: pattern-003
File: patterns/chart-type/grouped-bar/pattern-003.md
Tags: method-comparison, ML-benchmark, 6-methods

─────────────────────────────────────────────────────────────
NEXT STEPS
─────────────────────────────────────────────────────────────
→ Use this pattern when creating figures with nature-figure
→ Query: "Search KB for grouped-bar figures"
→ Apply: "Use pattern-003 for my new comparison figure"
═══════════════════════════════════════════════════════════════
```

### Optional Feedback Prompt

After presenting the report, the agent should ask a skippable feedback question. This is agent behavior, not automatic skill behavior.

Use a concise prompt:

```text
Optional: do you want to rate this new pattern now?
- rating 1-5
- one success note
- one caveat/failure note
- or "skip"
```

If the user provides feedback, update the Markdown entry through Repository
support and let the derived index be rebuilt:

```yaml
quality_rating: 4
success_cases:
  - date: 2026-06-05
    note: "Strong color discipline and clear legend structure"
failure_cases:
  - date: 2026-06-05
    note: "May be too dense for six or more panels"
application_feedback:
  - date: 2026-06-05
    rating: 4
    notes: "Strong color discipline; may be too dense for six or more panels"
```

If the user skips, leave `quality_rating`, `success_cases`, and `failure_cases` unchanged. Do not block KB creation or later use.

---

## Error Handling

### Image Not Clear
If image quality is poor:
- Request higher-resolution version
- Proceed with `confidence: low` and document limitations
- Mark for manual review

### Metadata Missing
If DOI/journal not provided:
- Prompt user for metadata
- If unavailable, use generic ID: `pattern-{number}`
- Mark `source_journal: unknown`

### Validation Fails (score < 3)
- Flag entry with `confidence: low`
- Document specific discrepancies in notes
- Still create entry (for learning)
- Suggest manual review

### Duplicate Detection
Run `pattern save` with `--duplicate-policy error` by default. If the Repository
reports a duplicate, ask the user whether to `skip`, `overwrite`, or
`create-copy`; do not resolve the conflict by editing `index.json`.

---

## Checklist

Before marking WF1 complete, ensure:
- [ ] All 7 layers of analysis framework extracted
- [ ] YAML frontmatter complete with all required fields
- [ ] Markdown narrative written with structured sections
- [ ] Self-validation command run (Step 6), if the chart type is supported
- [ ] Scientific claim, hero panel, and evidence hierarchy reviewed by the LLM
- [ ] KB entry saved with `pattern save`
- [ ] Derived index updated by the Repository
- [ ] Structured report presented to user
- [ ] User informed of next steps (query/apply pattern)
