# Integration Bridge: nature-figure-learner ↔ nature-figure

This document defines the explicit bridge between nature-figure-learner (the learning skill) and nature-figure (the creation skill). The bridge is optional and must be requested by the user or clearly invoked by the active workflow; do not describe it as automatic unless nature-figure itself is configured to query this KB.

Important boundary: skills do not execute. The agent executes this bridge by reading the KB, asking optional questions, running helper scripts, and writing updates. Never imply that `nature-figure-learner` silently monitors or updates `nature-figure`.

---

## Overview

```
┌─────────────────────────────────────────────────────────────┐
│  nature-figure-learner (Learning Side)                      │
│    • Analyze published figures → Extract patterns → Build KB│
│    • Analyze plotting code → Extract templates → Build KB   │
└──────────────────────┬──────────────────────────────────────┘
                       │ (feeds)
                       ↓
            ┌──────────────────────┐
            │   Knowledge Base     │
            │  (figure-kb/)        │
            └──────────┬───────────┘
                       │ (queries)
                       ↓
┌─────────────────────────────────────────────────────────────┐
│  nature-figure (Creation Side)                               │
│    • Optionally query KB for relevant patterns                │
│    • Apply pattern to new figure                             │
│    • Collect user feedback → Update KB                       │
└──────────────────────────────────────────────────────────────┘
```

---

## Integration Point 1: Pre-Creation Pattern Lookup

**When**: Before nature-figure starts the figure contract (Step 1 of nature-figure workflow)

**Trigger**: User mentions a reference, chart type, or asks for recommendations

### Example Scenarios

**Scenario A: User mentions a reference**
```
User: "Create a figure like Figure 3 from that Nature paper on X"
nature-figure agent:
  1. Detect reference mention
  2. Query KB: "Search for Nature figures with chart_type similar to description"
  3. Present matches: "I found 3 similar figures in your KB: ..."
  4. Ask: "Would you like to adapt one of these patterns?"
```

**Scenario B: User describes a chart type**
```
User: "I need a grouped-bar chart comparing 6 methods"
nature-figure agent:
  1. Identify chart_type = grouped-bar
  2. Query KB: "Find grouped-bar patterns with method-comparison tag"
  3. Present top 3 matches ranked by memory_score, then quality/validation/usage fallback
  4. Ask: "Pattern-003 (Nature 2026, quality 4/5) has a similar structure. Use as starting point?"
```

**Scenario C: Agent recommends proactively**
```
User: "Create a figure for my benchmark results"
nature-figure agent:
  1. Infer chart_type likely grouped-bar or heatmap
  2. Query KB: "Find method-comparison patterns"
  3. Say: "I can create this figure. Your KB has 5 method-comparison examples. 
          Pattern-015 is your most-used (8 times, avg rating 4.5/5). Want to use that style?"
```

### Implementation Protocol

**Step 1**: Detect trigger
- User says: "like", "similar to", "reference", "example", "pattern"
- User describes chart type: "bar chart", "heatmap", "scatter plot"
- Task implies common archetype: "benchmark" → grouped-bar

**Step 2**: Formulate query
Before reading the KB, run the First Invocation Gate from `kb-location-config.md`. If no KB path is configured, ask whether the user wants to configure one now; otherwise proceed without a KB reference.

Use query templates from `query-templates.md`:
- Q1 if user specifies chart type
- Q5 if multi-criteria (chart type + journal + color scheme)
- Q6 if user provides a specific pattern ID

**Step 3**: Present results
Format:
```
I found {n} patterns in your KB matching your description:

Top 3:
1. {id} ({source_journal} {source_year}, quality: {rating}/5)
   • {brief_description}
   • Used {application_count} times (avg feedback: {avg_feedback})
   
2. ...

Would you like to:
  [A] Adapt one of these patterns
  [B] View a specific pattern in detail
  [C] Create from scratch
```

**Step 4**: On user selection
- If [A]: Load selected pattern's full .md file
- Extract key parameters: colors, layout, figsize, font settings, success_cases, failure_cases, and recommendation_rationale
- Proceed with figure contract using these as defaults
- If [C]: Proceed without KB reference (but still recordable later)

---

## Integration Point 2: Archetype Selection Guidance

**When**: During nature-figure's figure contract, Step 3 (archetype selection)

**Purpose**: Help user choose between the 4 archetypes by showing real examples from KB

### Implementation Protocol

```
nature-figure agent: "Now let's classify your figure archetype..."

[Query KB]
For each of the 4 archetypes, query: 
  "How many patterns with layout_archetype = X?"

Present:
"Your KB contains:
  • quantitative-grid: 12 examples (avg quality: 4.2)
  • schematic-led-composite: 6 examples (avg quality: 4.7) ← Highest rated
  • image-plate-quant: 3 examples (avg quality: 4.0)
  • asymmetric-mixed-modality: 4 examples (avg quality: 3.8)

Based on your description (method comparison), I recommend quantitative-grid.
Your highest-rated examples use schematic-led-composite, but that's typically 
for mechanism figures with diagrams."
```

This helps the user make an informed choice backed by their own accumulated knowledge.

---

## Integration Point 3: Color Palette Seeding

**When**: During nature-figure's figure contract, when choosing a color palette

**Purpose**: Reuse proven palettes from KB instead of generic defaults

### Implementation Protocol

```
nature-figure agent: "Let's choose a color palette..."

[Query KB for palette]
Query: "Find patterns with:
  • chart_type = {user's chart type}
  • source_journal = {target journal if specified}
  • color_scheme = nature-nmi-pastel (or user's preference)
  • quality_rating >= 4
Sort by application_count (most-used first)"

Extract `extracted_colors` from top match.

Present:
"I'll use colors from pattern-015 (your most-used Nature figure):
  • #484878 (dark blue) — Baseline
  • #7884B4 (medium blue) — Baseline variant
  • #E4CCD8 (pink) — Proposed method

This palette has been used successfully in 8 of your figures with avg rating 4.5/5."
```

**Fallback**: If no KB match, use nature-figure's default `PALETTE` or `PALETTE_NMI_PASTEL`.

---

## Integration Point 4: Post-Creation Feedback Loop

**When**: After nature-figure completes figure creation and export

**Purpose**: Collect user feedback to improve KB quality ratings

### Implementation Protocol

**Step 1**: Record pattern usage
After figure creation, if a KB pattern was used:
```python
# Update the pattern entry
pattern_entry["application_count"] += 1
pattern_entry["last_applied"] = "2026-06-05"  # Today's date
```

**Step 2**: Request feedback
Present to user:
```
Figure created and exported successfully!

You used pattern-015 (Nature 2026 grouped-bar) as reference.

Quick feedback (optional):
  Rate this figure: [1] [2] [3] [4] [5]
  Any issues or improvements? [text input or skip]

[Skip] [Submit]
```

If the user skips feedback, do not block delivery. The agent may still increment `application_count` only when the pattern was actually used, and should keep `failure_cases`/`success_cases` unchanged unless the user provides evidence.

**Step 3**: Update KB entry
```python
feedback_entry = {
    "date": "2026-06-05",
    "rating": 4,  # User's rating
    "notes": "Good color scheme, but legend text was too small"
}

pattern_entry["application_feedback"].append(feedback_entry)

# Recompute quality_rating as weighted average
ratings = [f["rating"] for f in pattern_entry["application_feedback"]]
pattern_entry["quality_rating"] = sum(ratings) / len(ratings)
```

**Step 4**: Save updates
- Write updated entry to .md file
- Update index.json

**Step 5**: Thank user and close loop
```
Thanks for the feedback! Pattern-015's rating updated to 4.3/5.
Your feedback helps improve the KB.
```

---

## Integration Point 5: Post-Creation Comparative Learning

**When**: After figure creation, if user wants to learn from what they just created

**Purpose**: Analyze the new figure, compare to KB references, extract insights

### Implementation Protocol

**Trigger**: User says "analyze this figure I just created" or "add to KB"

**Step 1**: Treat new figure as analysis input
- If user has the output image: Run WF1 (image-analysis-protocol.md)
- If user has the code: Run WF2 (code-analysis-protocol.md)

**Step 2**: Comparative learning
Execute `image-analysis-protocol.md` Step 7:
- Query KB for 3 similar patterns (same chart_type + layout_archetype)
- Compare: color, layout, typography
- Record insights in `comparative_notes`

**Step 3**: Add to KB
Create new entry with:
- All extracted parameters
- Comparative notes from Step 2
- Initial quality_rating = null (will be updated as it gets used)

**Step 4**: Close the loop
```
Your figure has been analyzed and added to KB as pattern-042.

Insights from comparison:
  • Your color saturation is lower than pattern-015 → Better for dense panels ✓
  • Your legend placement (dedicated panel) matches your highest-rated examples ✓
  • Your font size (7pt) is smaller than average (9pt) → Consider increasing

Next time you create a similar figure, I can reference pattern-042.
```

---

## Integration Point 6: nature-figure SKILL.md Modification

To enable discovery of the KB, add the following to `nature-figure/SKILL.md`:

### Modification A: "When to load this skill" section

Add a bullet point:
```markdown
## When to load this skill

- Python or R figures for papers, slides, or reports...
- Requests involving grouped bars, trend lines, heatmaps...
- **Before creating a figure, consider querying the figure KB (nature-figure-learner) to find relevant proven patterns**
- ...
```

### Modification B: "Related files" table

Add a row at the end:
```markdown
| File | Open when |
|------|-----------|
| ... | ... |
| **[nature-figure-learner: references/integration-bridge.md](../nature-figure-learner/references/integration-bridge.md)** | Need to search the figure KB for relevant patterns before creating, or want to add created figure to KB for future reference |
| **[nature-figure-learner: references/query-templates.md](../nature-figure-learner/references/query-templates.md)** | Need specific query examples for finding patterns by chart type, journal, color scheme, or tags |
```

**Important**: These are **optional references**, not required dependencies. nature-figure works standalone. The KB is an enhancement layer.

---

## Integration Point 7: Skill Discovery

How does nature-figure agent know to query the KB?

### Scenario A: User explicitly mentions KB
```
User: "Create a bar chart. Check my figure library for examples."
→ nature-figure agent sees "figure library" → loads integration-bridge.md → queries KB
```

### Scenario B: Agent detects reference request
```
User: "Create a figure like the one in that Nature paper"
→ nature-figure agent sees "like" + "Nature paper" → considers KB query as option
→ Runs the First Invocation Gate, then reads <configured-kb-path>\index.json if configured
→ If exists and non-empty: queries KB
→ If doesn't exist or empty: proceeds without KB
```

### Scenario C: Proactive suggestion (only if KB is substantial)
```
User: "Create a grouped-bar figure"
→ nature-figure agent: internally checks KB entry count
→ If KB has >= 10 entries: "I can check your KB for grouped-bar examples. Want me to?"
→ If KB has < 10 entries: proceeds directly (no interruption)
```

---

## Data Flow Diagram

```
┌────────────────────────────────────────────────────────────┐
│  LEARNING PHASE (nature-figure-learner)                    │
│                                                             │
│  Analyze figure image or code                              │
│         ↓                                                   │
│  Extract 7 layers (scientific logic, visual encoding, ...) │
│         ↓                                                   │
│  Self-validation (reproduce figure)                        │
│         ↓                                                   │
│  Create KB entry (YAML + Markdown)                         │
│         ↓                                                   │
│  Update index.json                                         │
└────────────────────┬───────────────────────────────────────┘
                     │
                     │ (persistent storage)
                     ↓
         ┌───────────────────────┐
         │   figure-kb/          │
         │   - index.json        │
         │   - patterns/*.md     │
         └───────────┬───────────┘
                     │
                     │ (query)
                     ↓
┌────────────────────────────────────────────────────────────┐
│  CREATION PHASE (nature-figure)                            │
│                                                             │
│  User: "Create figure"                                     │
│         ↓                                                   │
│  Query KB for relevant patterns (optional)                 │
│         ↓                                                   │
│  Present matches, let user choose                          │
│         ↓                                                   │
│  Extract parameters from chosen pattern                    │
│         ↓                                                   │
│  Apply to new figure (colors, layout, fonts)               │
│         ↓                                                   │
│  Create figure, export                                     │
│         ↓                                                   │
│  Request feedback, update KB entry                         │
│         ↓                                                   │
│  [Optional] Analyze new figure, add to KB                  │
└────────────────────────────────────────────────────────────┘
                     │
                     │ (feedback loop)
                     ↓
         (Back to figure-kb/ — quality_rating updated)
```

---

## Error Handling

### KB Not Found
```
nature-figure agent attempts to query KB
→ <configured-kb-path>\index.json not found
→ Agent: "No figure KB found. Proceeding without pattern reference.
         (You can build a KB with nature-figure-learner skill)"
→ Continues with default nature-figure workflow
```

### KB Empty
```
index.json exists but is empty: []
→ Agent: "Your KB is empty. Proceeding without pattern reference."
→ Continues with default workflow
```

### Pattern File Missing
```
index.json references pattern-042.md but file doesn't exist
→ Agent: "Warning: pattern-042 listed but file not found. Skipping."
→ Present other matches
```

### No Matches Found
```
User: "Create a radar chart"
KB query returns 0 matches
→ Agent: "No radar chart patterns in your KB yet.
         After creating this figure, you can analyze it with nature-figure-learner 
         to add it as the first radar example."
→ Continues with default workflow
```

---

## Best Practices for Integration

### 1. Don't Interrupt Flow
- Only query KB if user mentions it OR task clearly benefits
- If KB query returns 0 matches, proceed silently (don't force feedback)
- Never require KB — it's an enhancement, not a dependency

### 2. Keep Feedback Optional
- Post-creation feedback should be skippable
- Don't block export on feedback collection
- Allow "Skip" option

### 3. Respect User's Choice
- If user says "create from scratch", don't force KB patterns
- If user says "use pattern X", don't suggest alternatives

### 4. Graceful Degradation
- If KB is unavailable, nature-figure works standalone
- If KB query fails, fall back to defaults
- Never error out due to KB issues

### 5. Transparency
- When using a KB pattern, tell the user: "Using pattern-015 as reference"
- When updating KB, confirm: "Pattern-015 rating updated"
- When adding to KB, announce: "Added as pattern-042"

---

## Testing the Integration

### Test 1: KB Query Before Creation
```
Setup: Add 3 grouped-bar patterns to KB
Test: Ask nature-figure to create a grouped-bar figure
Expected: Agent queries KB, presents 3 matches, asks for selection
```

### Test 2: Feedback Loop
```
Setup: Create figure using pattern-015
Test: Provide rating of 5/5
Expected: pattern-015's quality_rating increases, application_count increments
```

### Test 3: Comparative Learning
```
Setup: Create figure, then ask to analyze it
Test: "Analyze the figure I just created"
Expected: WF1 runs, comparative notes generated, new pattern added to KB
```

### Test 4: Graceful Degradation
```
Setup: Delete figure-kb/ directory
Test: Ask nature-figure to create a figure
Expected: Agent proceeds without KB, no errors
```

---

## Checklist for Successful Integration

- [ ] nature-figure can query KB via query-templates.md
- [ ] KB patterns inform color/layout choices
- [ ] Post-creation feedback updates KB entries
- [ ] Newly created figures can be added to KB
- [ ] Graceful fallback when KB unavailable
- [ ] User informed when KB is used or updated
- [ ] integration-bridge.md cross-referenced in both skills
- [ ] No hard dependency (both skills work standalone)
