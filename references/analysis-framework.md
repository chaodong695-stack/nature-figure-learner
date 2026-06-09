# Figure Analysis Framework

This document defines the complete taxonomy of what to extract from any scientific figure, whether from an image (PNG/screenshot/PDF) or from plotting code (Python/R).

The framework is organized into 7 layers, progressing from high-level scientific logic to low-level implementation details.

---

## 1. Scientific Logic Layer

Extract the **why** behind the figure — the claim it defends and how panels contribute to that claim.

### 1.1 Core Conclusion Extraction
- **What to extract**: A single-sentence claim the figure defends
- **Format**: Must contain a verb and a relationship (e.g., "Method X improves Y by restoring Z")
- **Not acceptable**: Generic labels like "Results" or "Comparison"
- **From images**: Infer from title, caption, panel structure, and visual hierarchy
- **From code**: Look for comments, variable names, or surrounding context

### 1.2 Evidence Hierarchy
- **Hero panel**: The panel carrying the main claim (usually largest, most central, or most complex)
- **Supporting panels**: Provide validation, mechanism, or context
- **Control panels**: Baseline comparisons, negative controls, robustness checks
- **Visual cues**: Size, position, color intensity, caption emphasis

### 1.3 Panel-to-Claim Mapping
For each panel, answer:
- **Unique question**: What specific question does this panel answer that no other panel answers?
- **Evidence type**: Discovery / mechanism / validation / comparison / robustness / clinical relevance
- **Contribution**: How does this panel support the core conclusion?

**Anti-redundancy check**: If covering this panel leaves no gap that cannot be recovered from other panels, it may be redundant.

---

## 2. Visual Encoding Layer

Extract **what visual variables encode what data dimensions**.

### 2.1 Chart Type Classification
Use the controlled vocabulary (20 types):

**Quantitative charts**:
- `grouped-bar` — bars side-by-side, comparing methods/conditions
- `stacked-bar` — bars stacked, showing composition
- `horizontal-bar` — horizontal bars, often for ablation studies
- `line-trend` — time series, longitudinal data
- `multi-line` — multiple time series on same axes
- `heatmap` — matrix, often with row/column clustering
- `scatter` — x-y correlation, no size encoding
- `bubble` — scatter with size encoding third variable
- `violin` — distribution with kernel density
- `box` — distribution with quartiles
- `density` — smoothed histogram or ridge plot
- `forest-plot` — effect sizes with confidence intervals

**Specialized charts**:
- `radar-polar` — multi-axis radar or polar histogram
- `fill-between` — stacked area, time-based composition
- `sankey` — flow diagram
- `upset` — set intersection
- `image-plate` — microscopy, western blot, gel
- `schematic` — hand-drawn or Illustrator diagram
- `network` — node-link or adjacency matrix
- `other` — specify in `chart_type_description` field

### 2.2 Data-to-Visual Mapping
For each chart, identify:
- **Position** (x, y): What data dimensions? (e.g., time, condition, performance)
- **Length/Area**: What quantitative variable? (e.g., accuracy, expression level)
- **Color**: Categorical (method), sequential (low→high), or diverging (negative↔positive)?
- **Size**: Does bubble size encode a third variable?
- **Angle**: Used in pie/donut/polar charts
- **Texture/Hatch**: Used for print-safe grayscale encoding

### 2.3 Scale and Transformation
- **Linear** or **log** scale?
- **Normalized** (0-100%) or absolute units?
- **Z-score transformed** (mean-centered, SD-scaled)?
- **Y-axis tightened** to data range (e.g., 80-95) or fixed (0-100)?
- **X-axis**: Continuous, categorical, or time-based?

---

## 3. Color System Extraction

Extract the **palette, strategy, and semantic roles** of color.

### 3.1 Palette Extraction
- **From images**: Sample dominant colors, estimate hex codes (use color picker or visual inspection)
- **From code**: Extract from `PALETTE` dicts, hex arrays, named color vectors
- **Output format**: List of hex codes in order of dominance

Example:
```yaml
extracted_colors: ["#484878", "#7884B4", "#B4C0E4", "#E4CCD8", "#F0C0CC"]
```

### 3.2 Color Strategy Classification
Choose from controlled vocabulary:

- `nature-nmi-pastel` — Low-saturation unified families (baseline cool, hero warm)
- `nature-imaging` — Grayscale + 1-2 fluorescent channels (cyan, magenta) on black
- `nature-clinical` — Dark baseline, restrained warm/cool, pale background bands
- `nature-genomics` — Neutral grey scaffolds + small biologically meaningful highlights
- `nature-material` — Palette derived from physical objects in schematic
- `categorical-high-contrast` — Saturated distinct hues for category separation
- `sequential-single-hue` — Light → dark gradient (e.g., Blues, YlOrRd)
- `diverging` — Two-hue diverging (e.g., RdBu_r for z-scores)
- `monochrome` — Grayscale or single-hue shades
- `other` — specify in `color_strategy_description`

### 3.3 Semantic Color Roles
Map each color to its scientific meaning:
- Which color = **proposed method** / hero series?
- Which color = **baseline** / control / comparison?
- Which color = **positive variant** / improvement?
- Which color = **negative control** / failure mode?
- Are colors **consistent across panels** (same condition = same color)?

### 3.4 Saturation and Luminance Profile
- **High saturation**: Strong category separation (categorical palettes)
- **Low saturation**: Unified visual feel (NMI pastel, clinical)
- **Luminance contrast**: High (text-on-color readable) or low (soft transitions)

---

## 4. Typography Parameter Estimation

Extract **font family, size hierarchy, and weight usage**.

### 4.1 Font Family Inference
**From images** (visual characteristics):
- **Arial / Helvetica** (grotesque sans-serif): Even stroke width, open apertures, neutral
- **Times / serif**: Serifs visible at letter terminals
- **Other sans-serif**: Condensed, rounded, or geometric variations

**From code**:
- Python: `plt.rcParams['font.sans-serif']` or `font.family`
- R: `base_family` in theme, or `family` in `element_text()`

### 4.2 Size Hierarchy (in pt)
Estimate or extract sizes for:
- **Panel label** (a, b, c): Often 8-10 pt bold
- **Axis title**: 6-7 pt in journal-final dense figures, 12-16 pt in slide-sized
- **Tick label**: 5-6 pt in journal-final, 10-12 pt in slide-sized
- **In-panel annotation**: 5-7 pt
- **Legend text**: 5-6 pt
- **Title** (if present): 7-8 pt bold

**Note**: Published figures are often scaled down 2-3× from creation size, so a 24 pt label in code may render as 8 pt in print.

### 4.3 Weight Usage
- **Bold**: Panel labels, titles, emphasis
- **Regular**: Data labels, axis titles, tick labels, legends
- **Italic**: Rare; used for mathematical variables or emphasis

---

## 5. Layout Geometry

Extract **grid structure, archetype, proportions, and legend strategy**.

### 5.1 Grid Structure
- **Rows × columns**: e.g., 2×3 grid
- **Spanning**: Does one panel span multiple grid cells?
- **Height ratios**: Are rows equal height, or is one row taller?
- **Width ratios**: Are columns equal width?

**From images**: Count panels, observe alignment
**From code**:
- Python: `gridspec.GridSpec(rows, cols, height_ratios=[...], width_ratios=[...])`
- R: `patchwork` operators (`/`, `|`), `plot_layout()`

### 5.2 Archetype Classification
Classify into one of the 4 nature-figure archetypes:

| Archetype | Visual Signal |
|-----------|---------------|
| **quantitative-grid** | Equal-sized panels in regular grid, all quantitative |
| **schematic-led-composite** | One large schematic/illustration panel (45-60% height) + smaller quantitative panels below |
| **image-plate-quant** | Dark microscopy/imaging plate + adjacent quantitative plots |
| **asymmetric-mixed-modality** | Unequal panel sizes, one dominant hero panel, mixed modalities (diagram + quant + image) |

### 5.3 Panel Proportions
- **Relative area allocation**: Which panel occupies the most space?
- **Aspect ratio**: Wide (3:1) for time series, square (1:1) for scatter, tall (1:2) for forest plots
- **Gutter size**: Tight (minimal whitespace) or generous?

### 5.4 Legend Placement Strategy
- **Dedicated panel**: Legend gets its own subplot (common in multi-axis figures)
- **Shared strip**: One legend above or below a row of panels
- **Per-panel**: Each panel has its own legend
- **Direct labels**: No legend; categories labeled directly on plot
- **Omitted**: No legend (context in caption or obvious from axes)

---

## 6. Statistical Annotation Layer

Extract **how statistics are communicated visually**.

### 6.1 Error Representation
- **Error bars present?** Yes / No
- **Error type**: SD (standard deviation) / SEM (standard error of mean) / CI (confidence interval) / IQR (interquartile range)
- **How identified**: Legend, caption, or axis label?

### 6.2 Significance Display
- **Asterisks** (`*`, `**`, `***` for p < 0.05, 0.01, 0.001)?
- **Exact p-values** printed on plot?
- **Brackets** connecting compared groups?
- **Color coding** (e.g., red = significant)?

### 6.3 Sample Size Visibility
- **n shown in legend** (e.g., "Control (n=15)")?
- **n in caption only**?
- **n per bar** (annotated on each bar)?
- **Not shown**?

### 6.4 Statistical Test Declaration
- **Test type mentioned**: t-test, ANOVA, Wilcoxon, etc.?
- **Multiple testing correction**: Bonferroni, FDR, etc.?
- **Where declared**: In caption, on plot, or in methods reference?

---

## 7. Reusable Pattern Extraction

Identify which **nature-figure common patterns** this figure employs, or define a new pattern.

### 7.1 Match Against Known Patterns
Check against nature-figure's 16 common patterns:

| Pattern # | Name | Key Feature |
|-----------|------|-------------|
| 1 | Ultra-wide multi-metric bar | `figsize=(28-45, 6-12)`, 4+ metrics, dedicated legend panel |
| 2 | Compact single bar | One metric, `figsize=(9-16, 5-8)` |
| 3 | Horizontal ablation bar | `ax.barh()`, alpha gradient for component contribution |
| 4 | Multi-line trend | Shared x-axis, `fill_between` uncertainty bands |
| 5 | Sequential heatmap | `YlOrRd`, cell annotations, luminance-based text color |
| 6 | Diverging z-score heatmap | `RdBu_r`, `vmin=-2.5, vmax=2.5` |
| 7 | Bubble scatter | x/y + size encoding, quadrant reference lines |
| 8 | Radar polar | `projection='polar'`, custom spokes, per-spoke normalization |
| 9 | 3D sphere | Lambertian shading, not true 3D projection |
| 10 | Fill-between stacked area | Time-based composition, hatch for print |
| 11 | Log-scale bar | `set_yscale('log')`, top space for annotations |
| 12 | Schematic-led composite | Nature 2026 archetype: large schematic + small quant panels |
| 13 | Dark image plate | Black background, grayscale + fluorescent channels |
| 14 | Clinical triptych | 3-row layout: longitudinal top, forest middle, summary bottom |
| 15 | Dense physics grid | Direct region labels, repeated axis ranges, shadow/texture overlays |
| 16 | Asymmetric hero layout | One large central panel, small support plots around it |

### 7.2 Novel Pattern Detection
If no match, document as a **new pattern**:
- **Pattern name**: Short descriptive name
- **Key structural feature**: What makes it distinct?
- **When to use**: Scientific use case
- **Parameterization**: What varies across instances?

### 7.3 Parameterized Template Creation
For code analysis, produce a **parameterized template**:
1. Abstract away data-specific values (replace with `DATA_PLACEHOLDER`)
2. Keep structural parameters (grid, colors, sizes)
3. Document all configurable parameters
4. Provide usage example

---

## Extraction Checklist

When analyzing a figure, ensure you extract:

- [ ] **Scientific logic**: Core conclusion, evidence hierarchy, panel questions
- [ ] **Visual encoding**: Chart types, data mappings, scales
- [ ] **Color system**: Palette (hex codes), strategy, semantic roles, saturation profile
- [ ] **Typography**: Font family, size hierarchy, weight usage
- [ ] **Layout**: Grid structure, archetype, proportions, legend strategy
- [ ] **Statistics**: Error type, significance display, sample size visibility
- [ ] **Pattern match**: Known pattern # or new pattern definition

---

## Output Integration

All extracted information flows into the knowledge base entry YAML frontmatter and Markdown body. See `knowledge-base-schema.md` for the complete entry format.
