---
description: Audit the current repo's CLAUDE.md against the org rubric. Dispatches the claude-md-auditor agent (read-only), renders per-criterion A-F grades and findings, and walks through suggested section replacements one at a time. Audit itself never writes files; only user-accepted replacements touch CLAUDE.md.
---

Audit the CLAUDE.md at the current repo's root.

The two reference files below are inlined into THIS command's body via `@${CLAUDE_PLUGIN_ROOT}/...`. They will land in the **main** conversation. The auditor agent runs in **isolated context** and will not see this conversation — so Step 2 below explicitly pastes both blocks into the agent's prompt parameter. Do not assume the agent inherits them; it doesn't.

## Rubric (inlined here; will be pasted into agent prompt)

@${CLAUDE_PLUGIN_ROOT}/rubrics/claude-md.md

## Canonical conventions reference (inlined here; will be pasted into agent prompt)

@${CLAUDE_PLUGIN_ROOT}/templates/conventions.md

## Steps

1. **Verify CLAUDE.md exists.** If not, tell the user and suggest `/draft-claude-md` to bootstrap one. Stop.

2. **Dispatch the auditor with the references pasted into its prompt.** Use the Agent tool with `subagent_type: "claude-md-auditor"`. Construct the `prompt` parameter by concatenating, in this order:
   - A one-line task statement: `Audit the CLAUDE.md at <absolute-repo-path>.`
   - The literal heading `## Rubric` on its own line, then the full verbatim text of the rubric section inlined above (everything between the `## Rubric (...)` heading and the `## Canonical conventions reference (...)` heading in this command body).
   - The literal heading `## Canonical conventions` on its own line, then the full verbatim text of the conventions section inlined above.

   The agent runs in isolated context. If you do not paste this text into its prompt, the agent has no rubric and no conventions baseline. Referencing "above" does not work across the Agent boundary — the agent does not see this conversation.

3. **Render the report.** Show the agent's full report to the user verbatim — grades table, summary metric, N/A list, findings, suggested replacements.

4. **Walk through replacements one at a time.** For each suggested replacement returned by the agent:
   - Show the section name and the proposed new text.
   - Ask via AskUserQuestion (2 options: "Apply" / "Skip").
   - On Apply: replace the section in CLAUDE.md between its `## SectionName` header and the next `## ` header. Preserve content outside the section. If the headers cannot be located (e.g., the section is missing entirely), surface the failure, print the suggested text, and instruct the user to apply manually.
   - On Skip: continue to the next replacement.

5. **Summarize.** After the walk, report which sections were updated and which were skipped.

## Constraints

- The audit step itself is read-only. The auditor agent has only Read, Glob, Grep.
- Replacements are full-section. Do not attempt line-diff application.
- Convention-drift findings are advisory. Do not pressure the user to accept them — they're expected to include false positives by construction.
- If the auditor times out or errors, surface the error to the user with the exact failure message. Do not silently retry.
- Do not summarize, paraphrase, or truncate the rubric/conventions when constructing the agent prompt — paste them verbatim.
