# Installation

Install the complete repository as a skill. Keep the user's figure KB outside
the skill directory.

## Runtime

Python 3.10 or newer is required. The package declares Pydantic 2, PyYAML,
NumPy, Matplotlib, and Pillow in `pyproject.toml`. This repository does not
install dependencies automatically.

## Skill Locations

Codex on Windows:

```text
%USERPROFILE%\.codex\skills\nature-figure-learner\
```

Unix-like agents may use `~/.codex/skills/nature-figure-learner/`. Claude and
other agents should use their documented skill directory. Preserve
`SKILL.md`, `references/`, `scripts/`, `src/`, and `agents/` together.

## KB Setup

From the skill root, run the First Invocation Gate:

```bash
python scripts/kb_location_manager.py --get-path
```

If it returns `NOT_CONFIGURED`, run the setup flow and select a location
outside this repository:

```bash
python scripts/kb_location_manager.py --setup
```

## Direct Use From a Checkout

No package installation is required for the launcher:

```bash
python scripts/figure_kb.py schema export
```

Commands are non-interactive and return a single JSON Envelope on stdout.

## Verification

```bash
python -B -m unittest discover -s tests -t . -v
python -B -m unittest scripts.test_self_evolution_engine -v
python -B -m py_compile scripts/figure_kb.py scripts/kb_location_manager.py scripts/self_evolution_engine.py
```
