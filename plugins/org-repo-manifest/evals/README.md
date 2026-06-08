# org-repo-manifest evals

Two suites, both run manually in v1. Automation is deferred to a later release.

## Prerequisites — install the plugin first

The `/draft-claude-md` and `/audit-claude-md` commands only exist when the plugin is installed. Before running any eval:

```bash
# 1. Add the marketplace (skip if already added).
claude plugin marketplace add /path/to/avi-claude-forge

# 2. Install the plugin.
claude plugin install org-repo-manifest

# 3. Confirm the commands are visible.
claude /help | grep -E 'draft-claude-md|audit-claude-md'
```

When iterating on plugin source, re-install (or restart Claude Code) so the latest agent/skill/command files are picked up.

## Auditor evals (`claude-md-auditor/`)

Five fixtures, each a minimal repo with a planted defect. The auditor agent is invoked against the fixture; the produced report is checked against `evals.json`.

### Procedure

For each fixture in `claude-md-auditor/fixtures/`:

1. `cd` into the fixture directory (so the auditor sees its CLAUDE.md and stack files).
2. Invoke `/audit-claude-md` in a fresh Claude Code session.
3. Capture the auditor's full report.
4. Open `claude-md-auditor/evals.json` and find the matching fixture entry.
5. Verify each hard assertion:
   - `criterion_max_grade`: the named criterion must be graded at the listed letter or worse.
   - `must_return_replacement_for_sections`: each named section must appear in the suggested replacements block.
   - `currency_finding_must_name_subcause` (when present): the Currency finding must contain the named sub-cause string (`repo drift` or `convention drift`).
6. Log the soft check informationally: does the findings list mention the substring hints? Don't fail the suite on this.

A fixture passes if all hard assertions hold. A suite passes if all 5 fixtures pass.

### Baseline comparison

Before any prompt change to the auditor agent, run all 5 fixtures and record the produced reports under `claude-md-auditor/baselines/<date>/<fixture-id>.md`. After the change, re-run and diff against the baseline. Investigate any regressions.

## Drafter evals (`claude-md-drafting/`)

Three fixtures, one per stack (Node, Spring Boot, React MFE). Each fixture is a minimal repo with a stack manifest and a stub source file, plus an `answers.txt` containing the user inputs to provide during the interactive Q&A.

### Procedure

For each fixture in `claude-md-drafting/fixtures/`:

1. `cd` into the fixture directory.
2. Read `answers.txt` and have it ready to paste into the prompts.
3. Invoke `/draft-claude-md` in a fresh Claude Code session.
4. Answer each prompt with the corresponding section from `answers.txt`.
5. Accept the draft when prompted.
6. Open the produced `CLAUDE.md` and check each hard assertion in `claude-md-drafting/evals.json`:
   - `max_lines`: `wc -l CLAUDE.md` ≤ value.
   - `required_section_headers_exact`: each header must appear verbatim.
   - `commands_section_must_contain`: each string must appear in the Commands section.
   - `conventions_section_non_empty`: the Conventions section has content.
   - `conventions_section_must_reference_at_least_n_canonical_rules`: count how many rules from `templates/conventions.md` are referenced (by rule text or topic).
   - `conventions_must_include_frontend_rule_topics` (react-mfe only): the named topics must appear.
7. Restore the fixture to its pre-run state (`git restore .` or delete the produced CLAUDE.md) before moving on.

A fixture passes if all hard assertions hold. A suite passes if all 3 fixtures pass.

### Why manual

The drafter is interactive (Q&A in main context); automating it requires a CLI driver that can stream answers into Claude Code. The auditor could be automated, but for v1 we keep both suites manual for consistency and to keep the plugin shippable without a runner script.

## Automating later

When a runner script is built (post-Part 1), it should:
- Drive the agent/skill via `claude --print` or a similar headless mode.
- Parse the produced report / CLAUDE.md.
- Check each `hard_assertion` programmatically.
- Emit a pass/fail summary and exit non-zero on any failure.
