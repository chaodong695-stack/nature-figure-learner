# Contributing

Contributions are welcome. This repository is a reusable agent skill, so changes should improve clarity, portability, and safe execution across agents.

## Ground Rules

- Do not commit real user KB data.
- Do not commit paper PDFs, screenshots, copyrighted figures, private datasets, credentials, tokens, or personal paths.
- Keep KB data outside the skill repository.
- Keep `SKILL.md` trigger-focused and avoid implying the skill executes by itself.
- Preserve the distinction between a skill and an agent: the agent reads instructions, runs scripts, asks questions, and writes KB updates.

## Before Submitting Changes

Run:

```bash
python -B -m py_compile scripts/kb_location_manager.py scripts/self_evolution_engine.py scripts/test_self_evolution_engine.py
python -B -m unittest scripts/test_self_evolution_engine.py
```

Check for private paths:

```bash
rg "C:\\Users\\|/Users/|figure-kb/index.json|token|secret|api_key" .
```

Review files staged for commit:

```bash
git status
git diff --cached
```

## Documentation Style

- Use plain, direct instructions.
- Prefer cross-links to long duplicated explanations.
- Mark optional feedback as optional.
- State trigger phrases clearly.
- Keep examples generic and free of private source material.

## Public Repository Checklist

- [ ] `README.md` explains standalone and bridge use.
- [ ] `INSTALL.md` is up to date.
- [ ] `PACKAGING.md` excludes generated/private files.
- [ ] Tests pass.
- [ ] No real KB data is staged.
- [ ] No private assets are staged.
