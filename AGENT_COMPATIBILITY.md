# Agent Compatibility

This skill is designed for multiple agent systems. It is not tied to one runtime as long as the agent can read `SKILL.md`, load supporting references, and run local scripts when appropriate.

## Universal Agent Contract

Any compatible agent should:

1. Read `SKILL.md` before using this repository.
2. Preserve the relative layout of `references/`, `scripts/`, and `agents/`.
3. Run the First Invocation Gate before any KB read/write workflow:

   ```bash
   python scripts/kb_location_manager.py --get-path
   ```

4. Stop and ask the user to configure a KB location if the gate returns `NOT_CONFIGURED`.
5. Keep generated KB data outside the skill repository.
6. Treat helper scripts as user/agent-invoked tools, not background automation.
7. Ask optional feedback questions; do not fabricate ratings or notes.
8. Explain recommendation evidence with `memory_score`, quality, validation, reuse, success cases, and caveats.

## Codex

Recommended install location:

```text
%USERPROFILE%\.codex\skills\nature-figure-learner\
```

Codex should load this skill when the user asks for figure learning, figure KB search, paper figure analysis, plotting-code pattern extraction, or evidence-backed plotting advice.

## Claude / Claude Code

Recommended install location:

```text
%USERPROFILE%\.claude\skills\nature-figure-learner\
```

Claude-style agents should treat the YAML frontmatter in `SKILL.md` as the trigger metadata and load deeper references only when a workflow needs them.

## Hermes / Hermess-Style Agents

Hermes/Hermess-style agents can use the generic contract:

- Load `SKILL.md` as the primary instruction file.
- Treat `references/` as workflow-specific manuals.
- Treat `scripts/` as local helper tools.
- Preserve the First Invocation Gate.
- Keep user KB data outside the repository.

If the runtime supports tool manifests, map this skill to triggers such as:

- `analyze paper figure`
- `learn figure style`
- `build figure library`
- `search figure KB`
- `plotting advice from examples`
- `kb:why`
- `growth report`

## Generic Agent Adapter

For any other agent, expose this skill as:

```yaml
name: nature-figure-learner
description: Use when analyzing scientific figures or plotting code, building a reusable figure pattern knowledge base, querying saved plotting examples, or giving evidence-backed figure design advice.
entrypoint: SKILL.md
supporting_paths:
  - references/
  - scripts/
  - agents/
```

## Trigger Summary

Use this skill when the user wants one of these outcomes:

- learn from a figure
- learn from plotting code
- build a personal/lab figure library
- search saved figure examples
- get plotting advice from saved examples
- explain why a figure pattern is recommended
- generate a figure KB growth report

Do not use it as a replacement for the agent's judgment. The skill provides process and tools; the agent executes.
