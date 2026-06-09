# Installation

This repository is an agent skill. Install the whole directory, not just `SKILL.md`, because the skill depends on `references/`, `scripts/`, and `agents/`.

## Codex

Recommended location on Windows:

```text
%USERPROFILE%\.codex\skills\nature-figure-learner\
```

Recommended location on Unix-like systems:

```text
~/.codex/skills/nature-figure-learner/
```

## Claude / Claude Code

Recommended location on Windows:

```text
%USERPROFILE%\.claude\skills\nature-figure-learner\
```

Recommended location on Unix-like systems:

```text
~/.claude/skills/nature-figure-learner/
```

## Hermes / Hermess / Generic Agents

For other agents, install the full repository wherever that agent expects reusable skills or tool instructions. The agent must be able to read:

```text
SKILL.md
references/
scripts/
agents/
```

See [AGENT_COMPATIBILITY.md](AGENT_COMPATIBILITY.md) for adapter guidance.

## First Invocation Gate

Before any workflow that reads or writes the figure KB, the agent must resolve the KB location:

```bash
python scripts/kb_location_manager.py --get-path
```

If the command returns `NOT_CONFIGURED`, run setup:

```bash
python scripts/kb_location_manager.py --setup
```

The KB should be stored outside the skill repository. Good locations include:

```text
~/.codex/figure-kb
<data-drive>/figure-kb
<custom-absolute-path>/figure-kb
```

Do not store real KB data in this repository.

## Verify Installation

From the skill root:

```bash
python -B scripts/kb_location_manager.py --get-path
python -B -m py_compile scripts/kb_location_manager.py scripts/self_evolution_engine.py scripts/test_self_evolution_engine.py
python -B -m unittest scripts/test_self_evolution_engine.py
```

The first command should print a configured path or `NOT_CONFIGURED`. The compile and unittest commands should succeed.

## Relationship to nature-figure

This skill works without `nature-figure`.

If `nature-figure` is also installed, use an explicit bridge: query this KB first, then pass the selected pattern's layout, colors, typography, success cases, and caveats into the figure creation workflow.

Do not assume automatic integration unless the active `nature-figure` skill explicitly documents it.
