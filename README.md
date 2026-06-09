# Nature Figure Learner

Nature Figure Learner is an agent skill for building a reusable scientific figure knowledge base. It analyzes paper figures, screenshots, PDF pages, and plotting code, then extracts reusable visual patterns: chart type, layout, palette, typography, statistical annotation style, evidence logic, and reusable plotting guidance.

It is useful in two modes:

1. **Standalone figure library mode**: users who do not have `nature-figure` installed can still build their own plotting library and ask an agent for figure-design advice before drawing.
2. **Bridge mode with nature-figure**: users who also have `nature-figure` can query this knowledge base before figure creation, then feed selected patterns into the figure-making workflow.

Important boundary: this repository provides skill instructions, references, and helper scripts. It does not execute by itself. The agent that loads the skill is responsible for asking questions, running scripts, reading or writing the figure KB, and explaining recommendations.

## What This Skill Helps With

- Analyze published paper figures from PNG, JPG, screenshots, or PDF pages.
- Analyze Python/R plotting code and extract reusable templates.
- Build a personal or lab-level figure pattern library.
- Search your figure KB for layouts, palettes, chart types, and journal-style references.
- Get plotting advice even without `nature-figure`.
- Explain why a pattern is recommended with `memory_score`, validation, reuse, feedback, and caveats.
- Generate growth reports that identify strong patterns, weak chart types, and what to learn next.

## Trigger Mechanism

An agent should load or invoke this skill when the user asks to:

- "analyze this paper figure"
- "learn from this figure"
- "extract the plotting style"
- "build my figure library"
- "create a reusable plotting pattern"
- "find grouped-bar / heatmap / scatter examples in my KB"
- "check my figure library before drawing"
- "give plotting advice from my saved examples"
- "why are you recommending this pattern?"
- "show my figure KB progress"
- "generate a growth report"
- "add this generated figure to the KB"

The skill may also be useful when the user is about to draw a scientific figure and asks for layout, color, typography, panel structure, statistical annotation, or journal-style advice based on previous examples.

Do not invoke this skill for ordinary one-off plotting if the user does not want learning, pattern extraction, KB lookup, or figure-design advice.

## Works Without nature-figure

`nature-figure-learner` does not require `nature-figure`.

Without `nature-figure`, an agent can still:

1. Analyze example figures and plotting code.
2. Store patterns in a figure KB.
3. Search for relevant examples before the user draws a new figure.
4. Recommend palettes, layouts, font sizes, and figure archetypes.
5. Explain strengths and caveats of a candidate pattern.
6. Track progress and learning gaps over time.

In this standalone mode, the agent does not automatically create final publication figures. It provides evidence-backed guidance that the user or another plotting workflow can apply.

## Integration With nature-figure

If `nature-figure` is installed, use an explicit bridge:

1. Query this KB for relevant patterns.
2. Select a pattern or meta-pattern with the user.
3. Pass layout, palette, typography, success cases, failure cases, and rationale into `nature-figure`.
4. After creation, ask whether to add the finished figure or code back to the KB.

Do not claim that `nature-figure` automatically reads this KB unless the installed `nature-figure` skill explicitly says so.

## Agent Compatibility

This skill is designed for Codex, Claude, Hermes/Hermess-style agents, and other agents that can read a `SKILL.md` file plus supporting references and scripts.

Minimum agent requirements:

- Read `SKILL.md` first.
- Preserve relative paths to `references/`, `scripts/`, and `agents/`.
- Run the First Invocation Gate before any KB operation.
- Treat helper scripts as tools the agent may run, not as autonomous background services.
- Ask optional feedback questions instead of assuming feedback.
- Keep user KB data outside the skill repository.

See [AGENT_COMPATIBILITY.md](AGENT_COMPATIBILITY.md) for adapter notes.

## Repository Structure

```text
nature-figure-learner/
├── SKILL.md
├── README.md
├── INSTALL.md
├── PACKAGING.md
├── AGENT_COMPATIBILITY.md
├── CHANGELOG.md
├── CONTRIBUTING.md
├── LICENSE
├── agents/
│   └── openai.yaml
├── references/
│   ├── analysis-framework.md
│   ├── code-analysis-protocol.md
│   ├── growth-report-protocol.md
│   ├── image-analysis-protocol.md
│   ├── integration-bridge.md
│   ├── kb-location-config.md
│   ├── knowledge-base-schema.md
│   └── query-templates.md
└── scripts/
    ├── kb_location_manager.py
    ├── self_evolution_engine.py
    └── test_self_evolution_engine.py
```

## First-Time Setup

Install the directory into the skill location used by your agent. Then run the KB location gate from the skill root:

```bash
python scripts/kb_location_manager.py --get-path
```

If it returns `NOT_CONFIGURED`, initialize a KB path:

```bash
python scripts/kb_location_manager.py --setup
```

The KB should live outside this repository, for example under `~/.codex/figure-kb` or a user-selected data drive path.

## Common Commands

Check KB location:

```bash
python scripts/kb_location_manager.py --get-path
```

Run self-evolution on an existing KB:

```bash
python scripts/self_evolution_engine.py <configured-kb-path>
```

Run verification:

```bash
python -B -m py_compile scripts/kb_location_manager.py scripts/self_evolution_engine.py scripts/test_self_evolution_engine.py
python -B -m unittest scripts/test_self_evolution_engine.py
```

## Query Shortcuts

Common KB query shortcuts include:

- `kb:bar`: find grouped-bar patterns
- `kb:heat`: find heatmap patterns
- `kb:nature`: find Nature-style examples
- `kb:best`: show strongest or most-used patterns
- `kb:weak`: show patterns needing improvement
- `kb:similar <id>`: find related patterns
- `kb:why <id>`: explain why a pattern is recommended or risky

## Public Repository Safety

Do not commit:

- real `figure-kb/` data
- paper PDFs, screenshots, or copyrighted figure images
- private paths, usernames, tokens, or credentials
- generated `__pycache__/` or `*.pyc`
- temporary backup directories

This repository should contain the reusable skill, documentation, and helper scripts only.

## License

MIT. See [LICENSE](LICENSE).
