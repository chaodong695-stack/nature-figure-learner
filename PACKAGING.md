# Packaging and Public Release

Ship the complete skill repository, including `SKILL.md`, `references/`,
`scripts/`, `src/`, `tests/`, `agents/`, and the package metadata. The install-free
launcher is `scripts/figure_kb.py`.

## Runtime Contract

`pyproject.toml` declares Python 3.10+ and the runtime dependencies: Pydantic,
PyYAML, NumPy, Matplotlib, and Pillow. The launcher can be used from a source
checkout when those dependencies are already available.

All CLI commands return the same JSON Envelope. Supported renderer types return
`success`; unsupported types return `unsupported` with exit code 0; operational
errors return a structured error and a non-zero exit code.

## Exclude From Releases

Do not include real `figure-kb/` data, paper PDFs, screenshots, private images,
user paths, credentials, tokens, backups, `__pycache__/`, or `*.pyc` files.
Generated fixtures must remain test-only.

## Pre-Release Checks

Run from the repository root:

```bash
python -B -m unittest discover -s tests -t . -v
python -B -m unittest scripts.test_self_evolution_engine -v
python -B -m py_compile scripts/figure_kb.py scripts/kb_location_manager.py scripts/self_evolution_engine.py
git diff --check
```

Review `git status --short --untracked-files=all` and the archive file list
before publishing. Keep the configured KB outside the repository.
