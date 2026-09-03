# Agent Compatibility

Any compatible agent must be able to read `SKILL.md`, preserve the relative
`references/` and `scripts/` paths, and invoke local commands when appropriate.

## Universal Contract

1. Read `SKILL.md` before using the skill.
2. Run the First Invocation Gate before KB operations.
3. Keep generated KB data outside the skill repository.
4. Treat scripts as agent-invoked tools, not background services.
5. After a pattern is persisted, offer optional feedback; never fabricate
   ratings or notes.
6. Explain recommendations with quality, objective validation, reuse,
   feedback, memory evidence, and caveats.

## Deterministic CLI

Use `scripts/figure_kb.py` for schema export, validation, save, query, index
maintenance, and self-validation. Each command writes one JSON Envelope to
stdout; progress/debug text is stderr. Unsupported chart capability is not a
validation failure.

## Responsibility Boundary

The LLM supplies scientific claim, hero panel, evidence hierarchy, and
`ScientificReview`. Python supplies schema/path checks, persistence, duplicate
handling, query ranking, mock data, rendering, and objective image checks.

## Installation Paths

Codex commonly uses `%USERPROFILE%\.codex\skills\nature-figure-learner\` on
Windows and `~/.codex/skills/nature-figure-learner/` on Unix-like systems.
Claude and generic agents may use their own skill directories, provided the
complete repository is preserved.
