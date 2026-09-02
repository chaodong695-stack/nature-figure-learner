# Integration Bridge: `nature-figure-learner` and `nature-figure`

This bridge is optional. The agent may query the learner KB before creating a
figure and may feed a completed figure back after the user agrees. Neither
skill silently monitors the other.

## Ownership Boundary

The LLM owns the scientific claim, hero panel, evidence hierarchy, visual
meaning, and optional `ScientificReview`. Python owns schema validation, path
resolution, DOI/figure duplicate detection, Markdown persistence, derived
index rebuilding, query filtering/ranking, mock data, rendering, and objective
image checks.

Unsupported renderer capability is reported as `unsupported`; it is not a
validation failure. Render errors and objective validation failures remain
separate statuses.

## Before Figure Creation

When the user asks for a reference, a chart type, or an evidence-backed style
recommendation:

1. Run the First Invocation Gate from `SKILL.md`.
2. Translate the request into explicit query options.
3. Run the query through the install-free launcher:

```bash
python scripts/figure_kb.py query \
  --chart-type grouped-bar \
  --tag-all method-comparison \
  --limit 3
```

4. Present the returned matches and warnings. Ask the user whether to adapt a
   selected pattern or create from scratch.
5. Pass selected layout, palette, typography, success cases, failure cases,
   and rationale into the figure contract. Re-evaluate them against the
   current data and scientific claim.

For a known pattern ID, use:

```bash
python scripts/figure_kb.py query --reference-id pattern-003 --limit 3
```

The similarity score is evidence for discussion, not an automatic design
decision.

## During Figure Creation

Use query results to inform layout and color choices, but keep the scientific
interpretation with the LLM. The figure workflow may call objective validation
for supported chart types:

```bash
python scripts/figure_kb.py self-validate \
  --pattern-id pattern-003 \
  --output-dir previews
```

Every launcher command returns one JSON Envelope on stdout. Progress or debug
text belongs on stderr. An `unsupported` Envelope exits with status 0; an
error Envelope exits non-zero.

## After Figure Creation

If the user wants the result learned, run WF1 or WF2 and prepare a new valid
pattern. Save it through Repository-backed CLI commands:

```bash
python scripts/figure_kb.py pattern validate --input pattern.json
python scripts/figure_kb.py pattern save \
  --input pattern.json \
  --narrative narrative.md \
  --duplicate-policy error
```

The Markdown document is authoritative. The Repository atomically derives
`index.json`; do not edit the index directly.

If an existing pattern was actually used, collect optional feedback and apply
it through Repository support while preserving the narrative. Do not invent a
rating or feedback note, and do not block figure delivery on this optional
step.

## Graceful Degradation

- No configured KB: run the gate and ask whether to configure one.
- Missing or empty KB: continue the figure workflow without a reference.
- No query matches: explain that the evidence set is empty and continue.
- Invalid Markdown or index: report warnings; use `index audit`, then rebuild
  only after source documents are corrected.
- Unsupported chart type: continue with the creation workflow and report the
  capability gap without calling it a validation failure.

## Bridge Checklist

- [ ] User requested or accepted KB use
- [ ] First Invocation Gate completed
- [ ] Query performed through `scripts/figure_kb.py`
- [ ] Scientific claim and evidence hierarchy reviewed by the LLM
- [ ] Objective validation status kept distinct from scientific review
- [ ] New or updated patterns saved through the Repository
- [ ] Optional feedback recorded only when supplied by the user
- [ ] User told which pattern informed the figure
