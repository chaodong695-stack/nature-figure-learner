# Growth Report Protocol

This document defines how to generate periodic skill growth reports that quantify whether the user's scientific figure creation ability is improving over time.

---

## Purpose

The knowledge base is not just a static archive—it's a **learning system**. This protocol measures:
- **Breadth**: How many chart types and archetypes are covered?
- **Quality**: Are new figures better than old ones?
- **Memory strength**: Which patterns have the best combined quality, validation, reuse, feedback, and recency?
- **Usage**: Which patterns are actually used vs. dormant?
- **Reflections**: Which style lessons have become reliable enough to guide future figures?
- **Gaps**: What chart types need more examples?

## KB Location Gate

Before generating any growth report, run the First Invocation Gate from `SKILL.md` / `kb-location-config.md`.

If `python scripts/kb_location_manager.py --get-path` returns `NOT_CONFIGURED`, stop and prompt the user to choose a KB storage location. Do not compute or save a report until `<configured-kb-path>` is resolved and initialized.

---

## Report Frequency

| Frequency | When to Generate | Purpose |
|-----------|------------------|---------|
| **Monthly** | 1st of each month | Track short-term trends, identify immediate gaps |
| **Quarterly** | Every 3 months | Assess sustained improvement, long-term patterns |
| **On-Demand** | User requests | "How am I doing?", "Show my progress", "What should I learn next?" |

---

## Report Structure

A growth report contains 7 sections:

1. **Summary Stats**: KB size, coverage, quality trends
2. **Quality Trajectory**: Are figures getting better?
3. **Coverage Analysis**: Chart types, archetypes, journals
4. **Memory Strength**: Best and weakest evidence-backed patterns by `memory_score`
5. **Usage Patterns**: Most-used vs. dormant patterns
6. **Capability Gaps**: Weakest chart types, missing archetypes
7. **Recommendations**: What to learn next

---

## Section 1: Summary Stats

### Metrics to Compute

```python
import json
from pathlib import Path
from datetime import datetime, timedelta

kb_path = Path("<configured-kb-path>")
with open(kb_path / "index.json", encoding="utf-8") as f:
    index = json.load(f)

# Total entries
total_entries = len(index)

# Entries added in last 30 days
today = datetime.now()
thirty_days_ago = today - timedelta(days=30)
recent_entries = [e for e in index 
                  if datetime.fromisoformat(e["analysis_date"]) >= thirty_days_ago]
new_entries_count = len(recent_entries)

# Average quality rating (exclude nulls)
ratings = [e["quality_rating"] for e in index if e.get("quality_rating") is not None]
avg_quality = sum(ratings) / len(ratings) if ratings else None

# Average validation score (exclude nulls)
val_scores = [e["validation_score"] for e in index if e.get("validation_score") is not None]
avg_validation = sum(val_scores) / len(val_scores) if val_scores else None

# Average memory score (exclude missing)
memory_scores = [(e.get("memory_score") or {}).get("total")
                 for e in index
                 if (e.get("memory_score") or {}).get("total") is not None]
avg_memory = sum(memory_scores) / len(memory_scores) if memory_scores else None

# Unique chart types covered
unique_chart_types = len(set(e["chart_type"] for e in index))

# Unique journals covered
unique_journals = len(set(e.get("source_journal", "unknown") for e in index 
                           if e.get("source_journal")))
```

### Output Format

```
═══════════════════════════════════════════════════════════════
Figure KB Growth Report: June 2026
═══════════════════════════════════════════════════════════════

SUMMARY
───────────────────────────────────────────────────────────────
Total KB Entries:        180  (↑ +30 from last month)
Average Quality:         4.1 / 5  (↑ +0.3 from last month)
Average Validation:      4.0 / 5  (↑ +0.2 from last month)
Average Memory Score:    78.2 / 100  (↑ +4.5 from last month)
Chart Types Covered:     15 / 20  (75%)
Journals Covered:        8  (Nature, Science, Cell, NMI, ...)
Entries This Month:      30

Growth Rate:             +20% entries/month (accelerating)
```

---

## Section 2: Quality Trajectory

### Metrics to Compute

Compare quality across time windows:

```python
def get_entries_in_window(index, start_date, end_date):
    return [e for e in index 
            if start_date <= datetime.fromisoformat(e["analysis_date"]) < end_date]

# Define windows: 3 months ago, 2 months ago, 1 month ago, this month
windows = [
    ("3 months ago", today - timedelta(days=90), today - timedelta(days=60)),
    ("2 months ago", today - timedelta(days=60), today - timedelta(days=30)),
    ("1 month ago", today - timedelta(days=30), today),
]

for label, start, end in windows:
    entries = get_entries_in_window(index, start, end)
    if entries:
        ratings = [e["quality_rating"] for e in entries if e.get("quality_rating")]
        avg = sum(ratings) / len(ratings) if ratings else None
        print(f"{label}: {avg:.2f}" if avg else f"{label}: N/A")
```

### Output Format

```
QUALITY TRAJECTORY
───────────────────────────────────────────────────────────────
Average Quality by Month:

  Mar 2026:  3.8 / 5  (15 entries)
  Apr 2026:  4.0 / 5  (22 entries)  ↑ +0.2
  May 2026:  4.1 / 5  (28 entries)  ↑ +0.1
  Jun 2026:  4.3 / 5  (30 entries)  ↑ +0.2

Trend: ✅ Quality improving consistently
       Your figures are getting better month over month.
```

**Interpretation**:
- **Improving** (↑): Quality rising month-over-month
- **Stable** (→): Quality unchanged (±0.1)
- **Declining** (↓): Quality dropping (investigate why)

---

## Section 3: Coverage Analysis

### Metrics to Compute

```python
from collections import Counter

# Chart type distribution
chart_type_counts = Counter(e["chart_type"] for e in index)

# Layout archetype distribution
archetype_counts = Counter(e.get("layout_archetype", "unknown") for e in index)

# Journal distribution
journal_counts = Counter(e.get("source_journal", "unknown") for e in index 
                         if e.get("source_journal"))

# Coverage against total vocabulary
TOTAL_CHART_TYPES = 20  # From analysis-framework.md
covered_types = len(chart_type_counts)
coverage_pct = (covered_types / TOTAL_CHART_TYPES) * 100
```

### Output Format

```
COVERAGE ANALYSIS
───────────────────────────────────────────────────────────────
Chart Types Covered: 15 / 20 (75%)

Top 5 Chart Types (by entry count):
  1. grouped-bar       32 entries  (18%)
  2. heatmap           28 entries  (16%)
  3. line-trend        22 entries  (12%)
  4. scatter           18 entries  (10%)
  5. bubble            15 entries  (8%)

Missing Chart Types (0 entries):
  • radar-polar
  • sankey
  • upset
  • pie-donut
  • network

Layout Archetypes:
  • quantitative-grid:              85 entries  (47%)
  • schematic-led-composite:        45 entries  (25%)
  • asymmetric-mixed-modality:      32 entries  (18%)
  • image-plate-quant:              18 entries  (10%)

Journals:
  • Nature:                         52 entries  (29%)
  • Nature Machine Intelligence:    28 entries  (16%)
  • Science:                        22 entries  (12%)
  • Cell:                           18 entries  (10%)
  • Other:                          60 entries  (33%)

Insight: You have strong coverage of bar charts and heatmaps, but 
         no radar-polar examples yet. Consider analyzing a radar figure.
```

---

## Section 4: Memory Strength

### Metrics to Compute

```python
ranked = sorted(
    [e for e in index if (e.get("memory_score") or {}).get("total") is not None],
    key=lambda e: e["memory_score"]["total"],
    reverse=True
)

top_memory = ranked[:5]
weak_memory = ranked[-5:]
patterns_with_caveats = [e for e in index if e.get("failure_cases")]
style_reflection_count = len(list((kb_path / "reflections").glob("*.md"))) if (kb_path / "reflections").exists() else 0
```

### Output Format

```
MEMORY STRENGTH
───────────────────────────────────────────────────────────────
Top Evidence-Backed Patterns:
  1. pattern-015  memory: 91.2/100
     • Why: high validation; reused successfully; positive feedback
     • Caveats: none

  2. pattern-003  memory: 82.5/100
     • Why: high validation; reused successfully; check legend caveat
     • Caveats: dense-panels, small-text

Patterns Needing Review:
  • pattern-089  memory: 31.0/100
    Reason: low quality, low validation, failure cases present

Style Reflections Available: 6
```

Agent rule: `memory_score` is a ranking aid, not authority. The agent must explain why a pattern fits the current figure before applying it.

---

## Section 5: Usage Patterns

### Metrics to Compute

```python
# Most-used patterns
used_patterns = [e for e in index if e.get("application_count", 0) > 0]
most_used = sorted(used_patterns, key=lambda e: e["application_count"], reverse=True)[:5]

# Dormant patterns (never used)
dormant_patterns = [e for e in index if e.get("application_count", 0) == 0]
dormant_count = len(dormant_patterns)
dormant_pct = (dormant_count / total_entries) * 100 if total_entries > 0 else 0

# Average feedback rating for used patterns
feedback_ratings = []
for e in used_patterns:
    if e.get("application_feedback"):
        ratings = [f["rating"] for f in e["application_feedback"]]
        feedback_ratings.extend(ratings)

avg_feedback = sum(feedback_ratings) / len(feedback_ratings) if feedback_ratings else None
```

### Output Format

```
USAGE PATTERNS
───────────────────────────────────────────────────────────────
Active Patterns:     45 / 180  (25% have been used at least once)
Dormant Patterns:    135 / 180  (75% never used)

Most-Used Patterns (Top 5):
  1. pattern-012  (used 15 times, avg feedback: 4.5/5)
     • schematic-led-composite, Nature 2026
     • Why popular: Versatile layout for mixed-modality figures

  2. pattern-003  (used 12 times, avg feedback: 4.2/5)
     • grouped-bar, Nature 2026
     • Why popular: Clean method comparison template

  3. pattern-015  (used 8 times, avg feedback: 4.8/5)
     • grouped-bar, Nature MI 2025
     • Why popular: NMI pastel palette, highly rated

  4. code-python-grouped-bar-001  (used 7 times, avg feedback: 4.6/5)
     • Python template, easy to adapt

  5. pattern-028  (used 6 times, avg feedback: 4.3/5)
     • heatmap, Nature 2026
     • Why popular: Excellent z-score diverging color map

Average Feedback Rating:  4.4 / 5  (across all applications)

Insight: Your schematic-led patterns (pattern-012) are your most-used.
         25% usage rate is healthy—not every pattern needs to be used frequently.
         Dormant patterns serve as reference library.
```

---

## Section 6: Capability Gaps

### Metrics to Compute

```python
# Weakest chart types (lowest avg quality among entries with ratings)
chart_type_quality = {}
for ct in chart_type_counts.keys():
    entries = [e for e in index if e["chart_type"] == ct and e.get("quality_rating")]
    if entries:
        avg_quality = sum(e["quality_rating"] for e in entries) / len(entries)
        chart_type_quality[ct] = avg_quality

weakest = sorted(chart_type_quality.items(), key=lambda x: x[1])[:3]

# Chart types with < 3 examples (under-represented)
underrep = [(ct, count) for ct, count in chart_type_counts.items() if count < 3]
```

### Output Format

```
CAPABILITY GAPS
───────────────────────────────────────────────────────────────
Weakest Chart Types (lowest avg quality):
  1. forest-plot         avg quality: 3.0 / 5  (2 entries)
  2. violin              avg quality: 3.2 / 5  (3 entries)
  3. bubble              avg quality: 3.5 / 5  (15 entries)

Under-Represented Types (< 3 examples):
  • forest-plot          2 entries
  • violin               3 entries  ← Just crossed threshold
  • density              2 entries
  • fill-between         1 entry
  • image-plate          2 entries

Missing Types (0 entries):
  • radar-polar
  • sankey
  • upset
  • pie-donut
  • network

Archetypes Without High-Quality Examples (quality < 4):
  • asymmetric-mixed-modality:  avg 3.8 / 5

Insight: Your forest-plot examples are weak. Consider analyzing a
         high-quality Nature forest plot to improve this archetype.
```

---

## Section 7: Recommendations

### Logic for Generating Recommendations

```python
recommendations = []

# Rec 1: Missing chart types
if len(missing_types) > 0:
    recommendations.append({
        "priority": "high" if len(missing_types) > 5 else "medium",
        "action": f"Analyze examples of: {', '.join(missing_types[:3])}",
        "why": "Broaden coverage"
    })

# Rec 2: Weak chart types (quality < 3.5)
if len(weakest) > 0 and weakest[0][1] < 3.5:
    recommendations.append({
        "priority": "high",
        "action": f"Improve {weakest[0][0]} by analyzing more high-quality examples",
        "why": f"Current avg quality is only {weakest[0][1]:.1f}/5"
    })

# Rec 3: Most-used patterns with declining feedback
for e in most_used[:3]:
    if len(e.get("application_feedback", [])) >= 3:
        recent_ratings = [f["rating"] for f in e["application_feedback"][-3:]]
        avg_recent = sum(recent_ratings) / len(recent_ratings)
        if avg_recent < e["quality_rating"] - 0.5:
            recommendations.append({
                "priority": "medium",
                "action": f"Review pattern-{e['id']}",
                "why": f"Feedback trending down (recent: {avg_recent:.1f}, historical: {e['quality_rating']:.1f})"
            })

# Rec 4: Under-represented types (< 3 examples)
if len(underrep) > 0:
    recommendations.append({
        "priority": "low",
        "action": f"Add more examples for: {underrep[0][0]}",
        "why": f"Only {underrep[0][1]} examples"
    })

# Rec 5: Learn from success (highest-rated archetype)
best_archetype = max(archetype_counts.items(), key=lambda x: x[1])
recommendations.append({
    "priority": "insight",
    "action": f"Your {best_archetype[0]} figures are consistently strong",
    "why": "Leverage this strength in future work"
})
```

### Output Format

```
RECOMMENDATIONS
───────────────────────────────────────────────────────────────
Based on your KB analysis, here's what to focus on next:

🔴 High Priority:
  1. Improve forest-plot examples
     → Why: Current avg quality is only 3.0/5
     → Action: Analyze a high-quality Nature Immunology or NEJM forest plot

  2. Broaden coverage: Add radar-polar, sankey, upset examples
     → Why: These types are missing from your KB
     → Action: Find papers with these chart types and analyze them

🟡 Medium Priority:
  3. Add more heatmap examples
     → Why: Only 28 examples for such a common type
     → Action: Analyze diverse heatmap styles (sequential, diverging, clustered)

🟢 Low Priority:
  4. Fill out violin and density plot examples
     → Why: Only 2-3 examples each
     → Action: Look for statistical papers with distribution plots

💡 Insight:
  Your schematic-led-composite figures are excellent (avg 4.7/5).
  This is your strongest archetype. Use it for high-stakes papers.

───────────────────────────────────────────────────────────────
NEXT STEPS:
  → Focus on high-priority recommendations this month
  → Revisit this report next month to track progress
  → Run "kb:weak" query to see weak patterns anytime
═══════════════════════════════════════════════════════════════
```

---

## Generation Command

### Trigger Phrases
- "Generate growth report"
- "Show my figure KB progress"
- "How am I doing with figures?"
- "What should I learn next?"
- "KB stats"
- "Figure learning report"

### Execution
```python
def generate_growth_report(report_date=None):
    """
    Generate a comprehensive skill growth report.
    
    Args:
        report_date: datetime object, defaults to today
    
    Returns:
        Formatted report string
    """
    if report_date is None:
        report_date = datetime.now()
    
    # Load index after the First Invocation Gate has resolved <configured-kb-path>.
    kb_path = Path("<configured-kb-path>")
    with open(kb_path / "index.json", encoding="utf-8") as f:
        index = json.load(f)
    
    # Compute all metrics (7 sections)
    summary = compute_summary_stats(index, report_date)
    trajectory = compute_quality_trajectory(index, report_date)
    coverage = compute_coverage_analysis(index)
    memory = compute_memory_strength(index)
    usage = compute_usage_patterns(index)
    gaps = identify_capability_gaps(index)
    recommendations = generate_recommendations(index, gaps, trajectory)
    
    # Format and return
    report = format_report(report_date, summary, trajectory, coverage, 
                          memory, usage, gaps, recommendations)
    return report
```

---

## Comparison to Previous Report

If a previous report exists (saved as `growth-report-YYYY-MM.md`), compute deltas:

```python
def compare_to_previous(current, previous):
    """
    Compute changes since last report.
    
    Returns dict of deltas:
        - total_entries_delta
        - quality_delta
        - coverage_delta
        - etc.
    """
    return {
        "total_entries_delta": current["total_entries"] - previous["total_entries"],
        "quality_delta": current["avg_quality"] - previous["avg_quality"],
        # ...
    }
```

Display deltas with arrows: ↑ +0.3, ↓ -0.1, → no change

---

## Saving Reports

Each generated report is saved to:
```
<configured-kb-path>\reports\growth-report-YYYY-MM.md
```

This creates a **time series of reports** for long-term tracking.

---

## Advanced: Trend Visualization (Optional)

If user wants visual trends, generate simple ASCII charts:

```
Quality Trend (Last 6 Months):
5.0 ┤
4.5 ┤        ●────●────●
4.0 ┤    ●───╯
3.5 ┤●───╯
3.0 ┤
    └─────────────────────
    Jan Feb Mar Apr May Jun
    
Entry Growth:
200 ┤                  ╭──●
150 ┤             ╭────╯
100 ┤        ╭────╯
 50 ┤   ╭────╯
  0 ┤●──╯
    └─────────────────────
    Jan Feb Mar Apr May Jun
```

Use simple libraries like `asciichartpy` if available, or generate manually with box-drawing characters.

---

## Checklist for Report Generation

When generating a growth report:
- [ ] Run First Invocation Gate and resolve `<configured-kb-path>`
- [ ] Load index.json
- [ ] Compute all 7 sections (summary, trajectory, coverage, memory, usage, gaps, recommendations)
- [ ] Compare to previous report if available (compute deltas)
- [ ] Format with clear visual hierarchy (═══, ───, bullets, arrows)
- [ ] Save report to `figure-kb/reports/growth-report-YYYY-MM.md`
- [ ] Present report to user
- [ ] Highlight top 1-2 actionable recommendations
