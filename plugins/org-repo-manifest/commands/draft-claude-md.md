---
description: Draft a new CLAUDE.md for the current repo, interactively. Detects build stack, auto-fills the Commands section, then conversationally prompts for Purpose, Features, Architecture, Gotchas, and Conventions selection. Writes CLAUDE.md at the repo root on accept.
---

I'm invoking the `claude-md-drafting` skill to draft a CLAUDE.md for the current working directory.

## Canonical conventions reference (embedded for the skill)

@${CLAUDE_PLUGIN_ROOT}/templates/conventions.md

## CLAUDE.md skeleton template (embedded for the skill)

@${CLAUDE_PLUGIN_ROOT}/templates/CLAUDE.md.template

## What happens next

The `claude-md-drafting` skill will:
1. Detect the build stack (Node, JVM, Python, etc.) by Globbing for manifest files.
2. Auto-fill the Commands section from those build files.
3. Prompt conversationally for Purpose, Features, Architecture, Gotchas.
4. Present the canonical conventions list (embedded above) and ask which apply.
5. Substitute the chosen content into the skeleton template (embedded above) and show a preview.
6. On accept, write CLAUDE.md at the repo root.

If the repo already has a CLAUDE.md, confirm with me before overwriting. To audit an existing CLAUDE.md without rewriting it, use `/audit-claude-md` instead.
