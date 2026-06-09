# Figure KB Location Configuration

## First Invocation Gate

Before any workflow reads or writes the figure KB, resolve the KB path:

```bash
python scripts/kb_location_manager.py --get-path
```

If output is `NOT_CONFIGURED`, the agent must stop the current workflow and prompt the user to choose a storage location. Do not analyze figures, parse plotting code, query the KB, or generate growth reports until the KB path is configured and initialized.

## Path Resolution Order

1. `FIGURE_KB_HOME`, if the environment variable is set.
2. `$CODEX_HOME/figure-kb-config.json`, if `CODEX_HOME` is set and the config exists.
3. `~/.codex/figure-kb-config.json`, if the config exists.
4. Legacy `~/.claude/figure-kb-config.json`, if the config exists.
5. Default `~/.codex/figure-kb`.

Write new configuration to the Codex config path. Read the legacy config only to preserve existing data.

## Setup Prompt

Use this prompt on first invocation:

```text
Figure Knowledge Base Setup

This is your first time using nature-figure-learner.
Choose where to store the figure KB:

[A] ~/.codex/figure-kb
    Keeps Codex agent data together; may use home/system drive space.

[B] Suggested data-drive path
    Uses a larger data drive if available.

[C] Custom absolute path

[D] Ask every time
```

After the user selects a location, initialize:

```bash
python scripts/kb_location_manager.py --setup
```

If the user provides a direct absolute path, use that path during setup.

## KB Directory Shape

```text
<configured-kb-path>/
  index.json
  patterns/
    chart-type/
    color-scheme/
    layout-archetype/
    journal/
  reports/
```

Create `index.json` as an empty JSON array when it does not exist:

```json
[]
```

## Reconfiguration

Users can say:

- "Change my figure KB location"
- "Reconfigure figure KB"

Use:

```bash
python scripts/kb_location_manager.py --status
python scripts/kb_location_manager.py --reconfigure
```

Before moving data, report current path, entry count, disk usage, destination path, and available free space. Ask before destructive or irreversible operations.

## Backward Compatibility

If a legacy `~/.claude/figure-kb-config.json` or KB exists:

1. Read it if valid.
2. Tell the user what was detected.
3. Ask whether to keep using it, migrate it, or choose a new Codex path.
4. Write the final selected path to the Codex config file.

Do not silently abandon an existing KB created by another agent.
