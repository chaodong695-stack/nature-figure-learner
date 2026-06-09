# Query Templates (WF3)

Pre-built query patterns for searching the figure knowledge base. Use these templates when the user wants to find relevant patterns before creating a new figure, or when nature-figure needs to reference existing patterns.

---

## Query Execution Flow

All queries follow this structure:

1. **First Invocation Gate**: Run the gate from `SKILL.md` / `kb-location-config.md`; if it returns `NOT_CONFIGURED`, prompt for a KB location before querying.
2. **Load index**: Read `<configured-kb-path>\index.json`
3. **Filter**: Apply criteria to the index array
4. **Rank**: Prefer `memory_score.total` when present; fall back to quality, validation, usage, or relevance.
5. **Present**: Show top 3-5 matches with summaries
6. **Deep dive** (optional): Load full .md file for selected entry

Use this default ranking helper unless a query explicitly needs a different order:

```python
def ranking_score(entry):
    return (
        (entry.get("memory_score") or {}).get("total", 0),
        entry.get("quality_rating") or 0,
        entry.get("validation_score") or 0,
        entry.get("application_count") or 0,
    )
```

---

## Q1: Find Patterns by Chart Type

**Trigger**: User says "find grouped-bar figures" or "search for heatmaps in my library"

### Query Logic
```python
import json
from pathlib import Path

kb_path = Path("<configured-kb-path>")
with open(kb_path / "index.json", encoding="utf-8") as f:
    index = json.load(f)

target_chart_type = "grouped-bar"  # or "heatmap", "scatter", etc.
matches = [e for e in index if e["chart_type"] == target_chart_type]

# Sort by memory score, then quality/validation/usage fallbacks
matches_sorted = sorted(matches, key=ranking_score, reverse=True)

# Present top 5
top_matches = matches_sorted[:5]
```

### Output Format
```
Found 12 grouped-bar patterns in KB. Top 5:

1. pattern-003 (Nature 2026, memory: 82.5/100, quality: 4/5)
   • 3-panel method comparison with unified color family
   • Tags: method-comparison, ML-benchmark, 6-methods
   • Why: high validation; reused successfully; check legend caveat
   • Used 0 times

2. code-python-grouped-bar-001 (memory: 70.0/100, quality: N/A, from code analysis)
   • Python matplotlib template with NMI pastel palette
   • Tags: python, matplotlib, method-comparison
   • Used 0 times

3. pattern-015 (Nature Machine Intelligence 2025, quality: 5/5)
   • Multi-metric bar with dedicated legend panel
   • Tags: ablation-study, model-variants
   • Used 8 times (avg feedback: 4.7)

[...]

To view details: "Show me pattern-003" or "Load pattern-015"
```

---

## Q2: Find Patterns by Journal and Year

**Trigger**: "Show me Nature figures from 2026" or "What patterns exist from Science?"

### Query Logic
```python
target_journal = "Nature"
target_year = 2026

matches = [e for e in index 
           if e.get("source_journal") == target_journal 
           and e.get("source_year") == target_year]

# Sort by analysis date (newest first)
matches_sorted = sorted(matches, key=lambda e: e["analysis_date"], reverse=True)
```

### Output Format
```
Found 18 patterns from Nature (2026). Recent additions:

1. pattern-003 (Figure 3, analyzed 2026-06-05)
   • grouped-bar, quantitative-grid
   • Quality: 4/5, Tags: method-comparison, ML-benchmark

2. pattern-007 (Figure 2, analyzed 2026-06-04)
   • heatmap, schematic-led-composite
   • Quality: 5/5, Tags: genomics, expression-matrix

[...]
```

---

## Q3: Find Patterns by Layout Archetype

**Trigger**: "Find schematic-led figures" or "Show asymmetric layouts"

### Query Logic
```python
target_archetype = "schematic-led-composite"
# Options: quantitative-grid, schematic-led-composite, image-plate-quant, asymmetric-mixed-modality

matches = [e for e in index if e.get("layout_archetype") == target_archetype]

# Sort by quality
matches_sorted = sorted(matches, key=lambda e: e.get("quality_rating", 0), reverse=True)
```

### Output Format
```
Found 6 schematic-led-composite patterns:

1. pattern-012 (Nature 2026, quality: 5/5)
   • Large schematic (60% height) + 3 small quant panels
   • Matched nature-figure pattern #12
   • Used 15 times (most popular in this archetype)

2. pattern-007 (Nature 2026, quality: 5/5)
   • Material design schematic + rheology + release kinetics
   • Tags: biomaterials, composite-figure

[...]
```

---

## Q4: Find Patterns by Color Scheme

**Trigger**: "Find figures using NMI pastel palette" or "Show me imaging figures with dark backgrounds"

### Query Logic
```python
target_color_scheme = "nature-nmi-pastel"
# Options: nature-nmi-pastel, nature-imaging, nature-clinical, nature-genomics,
#          categorical-high-contrast, sequential-single-hue, diverging, monochrome

matches = [e for e in index if e.get("color_scheme") == target_color_scheme]
matches_sorted = sorted(matches, key=lambda e: e.get("quality_rating", 0), reverse=True)
```

### Output Format
```
Found 9 patterns using nature-nmi-pastel color scheme:

1. pattern-003 (quality: 4/5)
   • Cool baseline family + warm hero family
   • Extracted colors: #484878, #7884B4, #E4CCD8
   • Consistency: ✅ Same method → same color across panels

2. pattern-015 (quality: 5/5)
   • Low saturation unified palette
   • Extracted colors: #484878, #B4C0E4, #F0C0CC
   • Used 8 times with positive feedback

[...]
```

---

## Q5: Multi-Criteria Search

**Trigger**: "I need a grouped-bar figure with NMI palette for Nature" or "Find Python heatmaps with high quality"

### Query Logic
```python
criteria = {
    "chart_type": "grouped-bar",
    "color_scheme": "nature-nmi-pastel",
    "source_journal": "Nature",
    # Optional: quality threshold
    "min_quality": 4
}

matches = [e for e in index 
           if e.get("chart_type") == criteria["chart_type"]
           and e.get("color_scheme") == criteria["color_scheme"]
           and e.get("source_journal") == criteria["source_journal"]
           and e.get("quality_rating", 0) >= criteria.get("min_quality", 0)]

# Sort by quality, then by usage
matches_sorted = sorted(matches, 
                       key=lambda e: (e.get("quality_rating", 0), 
                                     e.get("application_count", 0)), 
                       reverse=True)
```

### Output Format
```
Found 3 patterns matching all criteria:
  • Chart type: grouped-bar
  • Color scheme: nature-nmi-pastel
  • Journal: Nature
  • Quality ≥ 4

Top matches:

1. pattern-003 (quality: 4/5, used 0 times)
   • 3-panel method comparison
   • Tags: method-comparison, ML-benchmark, 6-methods

2. pattern-028 (quality: 5/5, used 3 times)
   • Multi-metric comparison with ablation
   • Tags: ablation-study, benchmark

[...]
```

---

## Q6: Find Similar Patterns to an Existing Entry

**Trigger**: "Find patterns similar to pattern-003" or "What else is like this figure?"

### Query Logic
```python
reference_id = "pattern-003"

# Load reference entry from index
ref = next((e for e in index if e["id"] == reference_id), None)
if not ref:
    print(f"Entry {reference_id} not found")
else:
    # Match on chart_type + layout_archetype + overlapping tags
    matches = [e for e in index 
               if e["id"] != reference_id  # Exclude self
               and e.get("chart_type") == ref.get("chart_type")
               and e.get("layout_archetype") == ref.get("layout_archetype")]
    
    # Rank by tag overlap
    ref_tags = set(ref.get("tags", []))
    for e in matches:
        e_tags = set(e.get("tags", []))
        e["_similarity"] = len(ref_tags & e_tags) / len(ref_tags | e_tags)
    
    matches_sorted = sorted(matches, key=lambda e: e["_similarity"], reverse=True)
```

### Output Format
```
Patterns similar to pattern-003 (grouped-bar, quantitative-grid):

1. pattern-015 (similarity: 0.67, quality: 5/5)
   • Same chart type, same layout
   • Shared tags: method-comparison, ML-benchmark
   • Different: Uses 6 methods vs. 3

2. code-python-grouped-bar-001 (similarity: 0.50, quality: N/A)
   • Python implementation of similar pattern
   • Shared tags: method-comparison
   • Reusable template available

[...]
```

---

## Q7: Find Patterns by Tags

**Trigger**: "Find figures tagged with 'ablation-study'" or "Show me ML benchmarks"

### Query Logic
```python
target_tags = {"ML-benchmark", "method-comparison"}  # Can be single tag or multiple

# Exact match (entry has ALL target tags)
matches_exact = [e for e in index 
                 if target_tags.issubset(set(e.get("tags", [])))]

# Partial match (entry has ANY target tag)
matches_partial = [e for e in index 
                   if any(tag in e.get("tags", []) for tag in target_tags)]

# Usually present exact matches first, then partial
matches = matches_exact + [e for e in matches_partial if e not in matches_exact]
matches_sorted = sorted(matches, key=lambda e: e.get("quality_rating", 0), reverse=True)
```

### Output Format
```
Found 7 patterns with tags ["ML-benchmark", "method-comparison"]:

Exact matches (both tags):
1. pattern-003 (quality: 4/5)
2. pattern-015 (quality: 5/5)

Partial matches (one tag):
3. pattern-021 (has "ML-benchmark", quality: 3/5)
4. pattern-009 (has "method-comparison", quality: 4/5)

[...]
```

---

## Q8: Find Most-Used Patterns

**Trigger**: "What are my most-used patterns?" or "Show popular patterns"

### Query Logic
```python
# Filter out unused patterns
used_patterns = [e for e in index if e.get("application_count", 0) > 0]

# Sort by usage count
matches_sorted = sorted(used_patterns, key=lambda e: e["application_count"], reverse=True)
```

### Output Format
```
Your most-used patterns:

1. pattern-012 (used 15 times, avg feedback: 4.5/5)
   • schematic-led-composite, Nature 2026
   • Why popular: Versatile layout for mixed-modality figures

2. pattern-003 (used 8 times, avg feedback: 4.2/5)
   • grouped-bar, Nature 2026
   • Why popular: Clean method comparison template

3. code-python-grouped-bar-001 (used 5 times, avg feedback: 4.8/5)
   • Python template, easy to adapt

[...]

Insight: Your schematic-led figures get the highest ratings (avg 4.7).
```

---

## Q9: Find Weakest Patterns (For Improvement)

**Trigger**: "What patterns have low ratings?" or "Show me patterns that need improvement"

### Query Logic
```python
# Filter patterns with quality_rating < 3
weak_patterns = [e for e in index 
                 if e.get("quality_rating") is not None 
                 and e.get("quality_rating") < 3]

# Sort by rating (lowest first)
matches_sorted = sorted(weak_patterns, key=lambda e: e.get("quality_rating", 0))
```

### Output Format
```
Found 3 patterns with quality < 3:

1. pattern-089 (quality: 2.1/5, used 1 time)
   • radar-polar, Nature 2025
   • Issue: Poor normalization strategy, overlapping labels
   • Action: Re-analyze or replace with better radar example

2. pattern-045 (quality: 2.8/5, used 0 times)
   • forest-plot, Science 2025
   • Issue: Confidence intervals hard to read
   • Action: Study more forest plots to improve pattern

[...]

Recommendation: Analyze more radar-polar figures to strengthen that archetype.
```

---

## Q10: Find Patterns by Validation Score

**Trigger**: "Show me patterns with high self-validation scores" or "Which analyses are most reliable?"

### Query Logic
```python
# Filter by validation_score >= 4
reliable_patterns = [e for e in index 
                     if e.get("validation_score") is not None 
                     and e.get("validation_score") >= 4]

matches_sorted = sorted(reliable_patterns, key=lambda e: e.get("validation_score", 0), reverse=True)
```

### Output Format
```
Found 8 patterns with validation score ≥ 4:

1. pattern-015 (validation: 5/5, quality: 5/5)
   • Self-validation: Excellent match in reproduction test
   • High confidence in extracted parameters

2. pattern-003 (validation: 4/5, quality: 4/5)
   • Self-validation: Good match, minor font size discrepancy

[...]

These patterns have been verified by reproduction tests.
Use them with confidence.
```

---

## Q11: Explain Why a Pattern Is Recommended

**Trigger**: `kb:why <id>`, "Why are you recommending pattern-003?", or "Should I avoid this pattern?"

### Query Logic
```python
target_id = "pattern-003"
entry = next((e for e in index if e.get("id") == target_id), None)

if entry is None:
    print(f"Entry {target_id} not found")
else:
    score = entry.get("memory_score") or {}
    relations = entry.get("relations") or {}
    rationale = {
        "memory_score": score.get("total"),
        "quality_rating": entry.get("quality_rating"),
        "validation_score": entry.get("validation_score"),
        "application_count": entry.get("application_count", 0),
        "success_cases": entry.get("success_cases", []),
        "failure_cases": entry.get("failure_cases", []),
        "similar_to": relations.get("similar_to", []),
        "superseded_by": relations.get("superseded_by", []),
        "contraindicated_for": relations.get("contraindicated_for", []),
        "recommendation_rationale": entry.get("recommendation_rationale"),
    }
```

### Output Format
```
Why pattern-003?

Recommendation evidence:
  • Memory score: 82.5/100
  • Quality: 4/5
  • Validation: 4/5
  • Used: 3 times
  • Rationale: high validation; reused successfully; check legend caveat

Works well when:
  • Strong color discipline and compact legend

Check before reuse:
  • Legend may be too small in dense panels
  • Contraindicated for: dense-panels, small-text

Related patterns:
  • Similar: pattern-015, pattern-022
  • Superseded by: none

Agent note:
This is evidence for recommendation, not automatic authority. The agent must still
adapt it to the current figure claim, data shape, journal target, and user preference.
```

---

## Integration with nature-figure

When nature-figure is creating a figure, it can query the KB at strategic points:

### Before Figure Contract
```
User: "Create a figure comparing 6 methods"
Agent: Let me check the KB for relevant patterns...
[Runs Q5: multi-criteria search with chart_type=grouped-bar, tags=method-comparison]
Agent: I found 3 similar figures in your KB. Pattern-003 (Nature 2026) 
       uses a 3-panel layout with unified color family. Want to adapt it?
```

### During Archetype Selection
```
Agent: For this data, I recommend a quantitative-grid layout.
[Runs Q3: find patterns by layout_archetype]
Agent: You have 12 quantitative-grid examples in your KB, 
       mostly from Nature and NMI. The most-used is pattern-012.
```

### During Color Selection
```
Agent: I'll use a nature-nmi-pastel palette.
[Runs Q4: find patterns by color_scheme]
Agent: Extracting color codes from pattern-015 (your highest-rated NMI pastel example):
       #484878, #7884B4, #B4C0E4, #E4CCD8
```

---

## Query Shortcuts

Define these as shorthand commands:

| Shorthand | Expands to |
|-----------|------------|
| `kb:bar` | Q1 with chart_type=grouped-bar |
| `kb:heat` | Q1 with chart_type=heatmap |
| `kb:nature` | Q2 with source_journal=Nature |
| `kb:best` | Q8 (most-used patterns) |
| `kb:weak` | Q9 (weakest patterns, for improvement) |
| `kb:python` | Filter by tags=["python"] |
| `kb:r` | Filter by tags=["r"] |
| `kb:similar <id>` | Q6 with specified pattern ID |
| `kb:why <id>` | Q11 recommendation explanation for a selected pattern |

---

## Error Handling

### No Matches Found
```
No patterns found matching your criteria.

Suggestions:
→ Broaden search (remove one filter)
→ Analyze a new figure to add to KB
→ Check spelling of chart type / color scheme
```

### Index File Missing
```
KB index not found at <configured-kb-path>\index.json

Action required:
→ Initialize KB: Create directory and empty index.json
→ Or rebuild index: python rebuild_index.py
```

### Corrupted Entry
If a pattern file referenced in index.json doesn't exist:
```
Warning: pattern-042 listed in index but file not found.
Skipping this entry. Run rebuild_index.py to fix.
```

---

## Performance Notes

- **Index query time**: O(n) linear scan, acceptable for n < 1000
- **Loading full entry**: Only load .md file when user selects a specific pattern
- **Caching**: Keep index.json in memory during a query session (don't reload for every query)
- **Upgrade path**: If KB exceeds 1000 entries, migrate to SQLite for O(log n) indexed queries

---

## Checklist for Query Execution

When user requests a query:
- [ ] Run First Invocation Gate and resolve `<configured-kb-path>`
- [ ] Identify query type (Q1-Q10)
- [ ] Load index.json
- [ ] Apply filters
- [ ] Sort results by appropriate key (quality, usage, similarity)
- [ ] Present top 3-5 matches with summaries
- [ ] Offer to load full entry on user request
- [ ] Suggest related queries if no matches found
