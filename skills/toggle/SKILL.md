---
name: toggle
description: Turn plainly on or off, or show whether it is enabled. Argument is one of on, off, status; with no argument it flips the current state.
argument-hint: [on | off | status]
disable-model-invocation: true
allowed-tools: Bash(node *)
---

Result of the plainly toggle:

!`node "${CLAUDE_PLUGIN_ROOT}/scripts/toggle.mjs" $ARGUMENTS`

Relay the line above to the user verbatim. Do nothing else.
