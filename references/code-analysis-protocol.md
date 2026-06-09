# Code Analysis Protocol (WF2)

Complete step-by-step protocol for analyzing scientific figure plotting code (Python matplotlib/seaborn or R ggplot2).

**Input**: Plotting script (.py or .R file) + optional metadata  
**Output**: Technical pattern extraction + parameterized template + KB entry

---

## Prerequisites

### User Provides
- Plotting script file (.py, .R, or code block)
- **Optional**:
  - Description of what the figure shows
  - Associated paper DOI/journal
  - Output figure image (for validation)

### Agent Preparation
1. Load `analysis-framework.md` (extraction taxonomy)
2. Load `knowledge-base-schema.md` (output format)
3. Run the First Invocation Gate from `SKILL.md` / `kb-location-config.md`.
4. Resolve `<configured-kb-path>` only after the KB path is configured.
5. Identify backend: Python (matplotlib/seaborn) or R (ggplot2/patchwork)

---

## Step 1: Backend Detection and Parsing

### 1.1 Identify Backend
**Python indicators**:
```python
import matplotlib
import matplotlib.pyplot as plt
import seaborn as sns
```

**R indicators**:
```r
library(ggplot2)
library(patchwork)
library(ComplexHeatmap)
```

**Record**: `backend: python` or `backend: r`

### 1.2 Parse Imports and Dependencies
List all plotting-related imports/libraries:
- Python: matplotlib, seaborn, pandas, numpy, scipy.stats
- R: ggplot2, patchwork, ComplexHeatmap, ggrepel, cowplot, ggarrange

### 1.3 Identify Script Structure
Locate key sections:
- Configuration (rcParams, theme settings)
- Data loading/preprocessing
- Figure creation (fig, ax = plt.subplots() or ggplot())
- Plotting commands
- Export/save commands

---

## Step 2: Configuration Extraction

### 2.1 Font Configuration (Python)
Extract from rcParams:
```python
plt.rcParams['font.family']          # e.g., 'sans-serif'
plt.rcParams['font.sans-serif']      # e.g., ['Arial', 'Helvetica', ...]
plt.rcParams['font.size']            # Base size
plt.rcParams['svg.fonttype']         # 'none' for editable SVG text
plt.rcParams['pdf.fonttype']         # 42 for editable PDF text
```

**Record**:
- `font_family`: Extracted family
- `base_font_size_pt`: Base size

### 2.2 Font Configuration (R)
Extract from theme:
```r
theme_set(theme_classic(base_size = 7, base_family = "Arial"))
theme(..., text = element_text(family = "Arial", size = 7))
```

**Record**:
- `font_family`: Extracted family
- `base_font_size_pt`: Base size

### 2.3 Color Definitions
**Python**:
```python
PALETTE = {
    'blue_main': '#0F4D92',
    'green_3': '#8BCF8B',
    ...
}
colors = ['#0F4D92', '#8BCF8B', ...]
```

**R**:
```r
palette <- c("#0F4D92", "#8BCF8B", ...)
scale_color_manual(values = palette)
```

**Extract**:
- List of hex codes
- Semantic names (if available)
- Order of usage

### 2.4 Axes and Spines Configuration (Python)
```python
plt.rcParams['axes.spines.right']    # False
plt.rcParams['axes.spines.top']      # False
plt.rcParams['axes.linewidth']       # e.g., 2.0
plt.rcParams['legend.frameon']       # False
```

**R equivalent**:
```r
theme(axis.line = element_line(...),
      panel.border = element_blank(),
      legend.key = element_blank())
```

---

## Step 3: Figure Dimensions and Layout

### 3.1 Figure Size (Python)
```python
fig, ax = plt.subplots(figsize=(12, 8))
fig = plt.figure(figsize=(20, 10))
```
**Extract**: `figsize` tuple (width, height in inches)

### 3.2 Figure Size (R)
```r
ggsave("output.pdf", width = 183, height = 120, units = "mm")
svglite("output.svg", width = 7.2, height = 4.7)  # inches
```
**Extract**: Width and height (convert to consistent unit)

### 3.3 Layout Structure (Python)
**GridSpec**:
```python
gs = gridspec.GridSpec(2, 3, height_ratios=[2, 1], width_ratios=[1, 1, 1])
ax1 = fig.add_subplot(gs[0, :])  # Spans all columns
```
**Extract**:
- Rows × columns
- Height ratios
- Width ratios
- Spanning cells

**subplot_mosaic** (newer API):
```python
fig, axd = plt.subplot_mosaic([['a', 'b'], ['c', 'c']], figsize=(10, 8))
```
**Extract**: Layout pattern

### 3.4 Layout Structure (R)
**patchwork**:
```r
p1 + p2 + p3 + plot_layout(ncol = 3)
(p1 | p2) / p3  # p1 and p2 side-by-side, p3 below spanning
```
**Extract**: Layout operators and structure

**ggarrange**:
```r
ggarrange(p1, p2, p3, ncol = 3, nrow = 1)
```
**Extract**: Rows, columns

---

## Step 4: Chart Type and Data Mapping

### 4.1 Identify Chart Types
For each axes/plot object:

**Python bar chart**:
```python
ax.bar(x, y, color=colors, ...)
ax.barh(y, x, ...)  # horizontal
```
→ Chart type: `grouped-bar` or `horizontal-bar`

**Python line/trend**:
```python
ax.plot(x, y, ...)
ax.fill_between(x, y1, y2, alpha=0.2)
```
→ Chart type: `line-trend` with uncertainty bands

**Python heatmap**:
```python
sns.heatmap(data, cmap='YlOrRd', ...)
ax.imshow(data, cmap='RdBu_r', ...)
```
→ Chart type: `heatmap`

**R bar chart**:
```r
ggplot(data, aes(x = method, y = value, fill = method)) +
  geom_bar(stat = "identity", ...)
```
→ Chart type: `grouped-bar`

**R heatmap**:
```r
geom_tile(aes(x = x, y = y, fill = value))
ComplexHeatmap::Heatmap(mat, ...)
```
→ Chart type: `heatmap`

### 4.2 Extract Data-to-Visual Mapping
For each plot, identify:
- **Position (x, y)**: What variables?
- **Color/Fill**: Mapped to what variable?
- **Size**: If present (e.g., scatter point size)
- **Alpha/Transparency**: Used for layering or encoding?

---

## Step 5: Export Settings

### 5.1 Python Export
```python
fig.savefig('output.svg', bbox_inches='tight')
fig.savefig('output.png', dpi=300, bbox_inches='tight')
fig.savefig('output.pdf', bbox_inches='tight')
```

**Extract**:
- Primary format: SVG, PDF, PNG, TIFF?
- DPI (if raster)
- `bbox_inches='tight'` used?

### 5.2 R Export
```r
svglite::svglite("output.svg", width = 7, height = 5)
print(plot)
dev.off()

cairo_pdf("output.pdf", width = 7, height = 5, family = "Arial")
print(plot)
dev.off()

ragg::agg_tiff("output.tiff", width = 7, height = 5, res = 600)
print(plot)
dev.off()
```

**Extract**:
- Export functions used
- Output formats
- DPI/resolution

---

## Step 6: Helper Functions and Patterns

### 6.1 Identify Custom Helpers
Look for reusable functions:

**Python**:
```python
def make_bar_plot(ax, data, colors, ...):
    # Parameterized bar plot
    ...

def add_significance_brackets(ax, x1, x2, y, pval):
    # Reusable statistical annotation
    ...
```

**R**:
```r
make_bar_plot <- function(data, colors, ...) {
    ggplot(data, aes(...)) + geom_bar(...) + ...
}
```

**Document**:
- Function name
- Parameters
- Purpose
- Reusability potential

### 6.2 Extract Reusable Patterns
Common patterns to look for:

**Pattern: Dedicated legend panel**:
```python
ax_legend = fig.add_subplot(gs[0, 3])
ax_legend.legend(handles, labels, loc='center', frameon=False)
ax_legend.set_axis_off()
```

**Pattern: In-bar value annotations**:
```python
for bar in bars:
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2, height,
            f'{height:.2f}', ha='center', va='bottom')
```

**Pattern: Luminance-based text color**:
```python
def text_color_from_bg(hex_color):
    # Return 'white' or 'black' based on background luminance
    ...
```

---

## Step 7: Statistical and Annotation Layers

### 7.1 Error Bar Detection
**Python**:
```python
ax.bar(..., yerr=std_values, capsize=5)
ax.errorbar(x, y, yerr=err, fmt='o', ...)
```

**R**:
```r
geom_errorbar(aes(ymin = y - se, ymax = y + se), width = 0.2)
```

**Extract**:
- Error type (variable name like `std`, `sem`, `ci_95`)
- Capsize/width
- Color

### 7.2 Significance Annotation
**Python**:
```python
ax.text(x, y, '*', fontsize=16, ha='center')
ax.plot([x1, x2], [y, y], 'k-', lw=1.5)  # bracket
```

**R**:
```r
geom_text(aes(x = x, y = y, label = "*"), size = 5)
geom_segment(aes(x = x1, xend = x2, y = y, yend = y))
```

**Extract**:
- Annotation style (asterisks, p-values, brackets)
- Positioning logic

### 7.3 Sample Size Annotation
Look for `n=...` in labels:
```python
labels = [f'Method A (n=15)', f'Method B (n=20)']
```

---

## Step 8: Parameterized Template Creation

**Goal**: Abstract away data-specific values, keep structural parameters.

### 8.1 Identify Data-Specific Values
Mark for replacement:
- Actual data arrays/dataframes
- Specific method names (unless generic like "Method A", "Method B")
- Hardcoded counts (if not structural)

### 8.2 Keep Structural Parameters
Preserve:
- Figure dimensions
- Grid structure
- Color palette
- Font settings
- Layout ratios

### 8.3 Create Template
**Example (Python grouped-bar)**:
```python
import matplotlib.pyplot as plt
import numpy as np

# ── Configuration ──
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans']
plt.rcParams['svg.fonttype'] = 'none'
plt.rcParams['font.size'] = 12

# ── Data (REPLACE WITH YOUR DATA) ──
methods = ['Method A', 'Method B', 'Method C']  # PLACEHOLDER
values = [85, 88, 92]  # PLACEHOLDER
errors = [2, 1.5, 1]  # PLACEHOLDER

# ── Color Palette ──
colors = ['#484878', '#7884B4', '#E4CCD8']  # From analysis

# ── Figure Creation ──
fig, ax = plt.subplots(figsize=(10, 6))

# ── Plot ──
bars = ax.bar(methods, values, yerr=errors, capsize=5,
              color=colors, edgecolor='black', linewidth=1.5)

# ── Styling ──
ax.spines['right'].set_visible(False)
ax.spines['top'].set_visible(False)
ax.set_ylabel('Accuracy (%)', fontsize=14)
ax.set_ylim([80, 95])  # Tightened to data range

# ── Export ──
fig.tight_layout(pad=2)
fig.savefig('output.svg', bbox_inches='tight')
fig.savefig('output.png', dpi=300, bbox_inches='tight')
plt.close(fig)
```

### 8.4 Document Parameters
List all configurable parameters:
```yaml
configurable_parameters:
  - name: figsize
    default: (10, 6)
    description: Figure dimensions in inches
  - name: colors
    default: ['#484878', '#7884B4', '#E4CCD8']
    description: Bar colors (one per method)
  - name: ylim
    default: [80, 95]
    description: Y-axis limits (tight to data range)
  - name: base_font_size
    default: 12
    description: Base font size in pt
```

---

## Step 9: KB Entry Creation

### 9.1 Generate ID
- Use `code-{backend}-{chart_type}-{number}` format
- Example: `code-python-grouped-bar-001`

### 9.2 Construct YAML Frontmatter
```yaml
---
id: code-python-grouped-bar-001
source_type: code
source_doi: null  # If code is from a paper, add DOI
source_journal: null
source_year: null
chart_type: grouped-bar
layout_archetype: quantitative-grid
panel_count: 1
color_scheme: nature-nmi-pastel
extracted_colors: ['#484878', '#7884B4', '#E4CCD8']
font_family: Arial
base_font_size_pt: 12
matched_nature_figure_pattern: 2
novel_pattern: false
tags: [python, matplotlib, method-comparison, bar-chart]
quality_rating: null
confidence: high
analysis_date: 2026-06-05
validation_score: null  # Code analysis doesn't self-validate
application_count: 0
backend: python
figsize: [10, 6]
export_formats: [svg, png]
dpi: 300
---
```

### 9.3 Write Analysis Narrative
Structure:
1. **Overview**: What this code creates
2. **Backend**: Python matplotlib or R ggplot2
3. **Configuration**: Font, colors, rcParams/theme
4. **Layout**: Figure dimensions, grid structure
5. **Chart Type**: Bar, line, heatmap, etc.
6. **Reusable Pattern**: Matched pattern or novel
7. **Helper Functions**: Document any custom helpers
8. **Parameterized Template**: Full code with PLACEHOLDER markers
9. **Usage Example**: How to adapt this template

### 9.4 Save to File
```
<configured-kb-path>\patterns\chart-type\{chart_type}\{id}.md
```

### 9.5 Update Index
Add to `index.json` with `source_type: code`

---

## Step 10: Output to User

Present a structured report:

```
═══════════════════════════════════════════════════════════════
Code Analysis Complete
═══════════════════════════════════════════════════════════════

Backend: Python (matplotlib)
Chart Type: grouped-bar
Matched Pattern: nature-figure #2 (compact single bar)

─────────────────────────────────────────────────────────────
EXTRACTED CONFIGURATION
─────────────────────────────────────────────────────────────
Font: Arial, 12pt base
Colors: #484878, #7884B4, #E4CCD8 (nature-nmi-pastel)
Figure size: 10 × 6 inches
Export: SVG (primary), PNG (300 dpi)

─────────────────────────────────────────────────────────────
REUSABLE PATTERN
─────────────────────────────────────────────────────────────
• Unified color family (cool blues)
• Tightened Y-axis (80-95, not 0-100)
• Editable SVG text (svg.fonttype='none')
• Right/top spines removed

─────────────────────────────────────────────────────────────
KB ENTRY CREATED
─────────────────────────────────────────────────────────────
ID: code-python-grouped-bar-001
File: patterns/chart-type/grouped-bar/code-python-grouped-bar-001.md
Tags: python, matplotlib, method-comparison

─────────────────────────────────────────────────────────────
PARAMETERIZED TEMPLATE
─────────────────────────────────────────────────────────────
[Full code with PLACEHOLDER markers shown in entry]

Adapt by:
1. Replace PLACEHOLDER data arrays
2. Adjust figsize if needed
3. Modify color palette if different method count
4. Run and export

─────────────────────────────────────────────────────────────
NEXT STEPS
─────────────────────────────────────────────────────────────
→ Query: "Search KB for Python bar chart templates"
→ Apply: "Use code-python-grouped-bar-001 for my new figure"
═══════════════════════════════════════════════════════════════
```

---

## Error Handling

### Incomplete Code
If critical sections are missing (no savefig, no color definitions):
- Document what's present
- Mark `confidence: low`
- Suggest requesting complete script

### Uncommon Backend
If neither matplotlib nor ggplot2:
- Document as `backend: other`
- Extract what's extractable
- Note limitations in analysis

### Data Preprocessing Dominates
If most of the script is data wrangling:
- Focus on plotting commands only
- Skip data processing details
- Extract only plot-relevant configuration

---

## Checklist

Before marking WF2 complete:
- [ ] Backend identified (Python or R)
- [ ] Configuration extracted (font, colors, rcParams/theme)
- [ ] Layout structure documented (figsize, grid)
- [ ] Chart type identified
- [ ] Export settings recorded
- [ ] Parameterized template created with PLACEHOLDER markers
- [ ] All configurable parameters documented
- [ ] KB entry file saved
- [ ] `index.json` updated
- [ ] Structured report presented to user
