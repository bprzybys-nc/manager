# Claude Code Agentic Project Cleanup Instruction (Latest, Best Practice)

## Objective

Efficiently **analyze, plan, and remove obsolete, unused, or redundant code, files, dependencies, and configs** from the project, leveraging Claude Code’s latest agentic features for accuracy, safety, and transparency.

## Step-by-Step Agentic Cleanup Workflow

### 1. Explore & Analyze (Scoping Phase)
- Read relevant project files, configs, and manifest files.
- List candidate files, modules, functions, or configs that may be unused or obsolete.
- Identify obvious deprecated code and flag possible legacy features (check for comments, feature flags, or documentation hints).
- Use static analysis to suggest dead code and unused dependencies.
- **Do not change code yet.**

### 2. Plan the Cleanup
- Draft a Markdown plan listing all items recommended for removal, with file paths and reasons (e.g., “not imported anywhere, deprecated, flagged in history”).
- For critical or ambiguous items, query user or maintainers for confirmation.
- Use Markdown checklist or todo format so progress is tracked transparently in the repo.

### 3. Get Confirmation (Optional)
- Share proposal checklist for review; pause to gather approval or feedback on potentially risky removals.
- Adjust plan as needed.

### 4. Execute Removals (Safe Editing Phase)
- Sequentially:
  - Create pre-cleanup commit in case sth went wrong `git add .` followed by `git commit -m "Project precleanup commit"`
  - Remove each obsolete code block, file, config, test, or dependency from codebase as per the plan.
  - Refactor imports, module references, and related configs.
- After each file/group, run project tests and linters to ensure no regressions.
- Mark completed items as “done” in the plan.

### 5. Final Review & Verification
- Run the full/scope test suite, linter, and build checks.
- Confirm all cleanup actions are safe and complete.
- Summarize what was removed and validate the build.

### 6. Document Changes
- Update `docs/progress.md` (or `CHANGELOG.md`) with a summary of removals and rationale.
- Commit changes with a descriptive message, e.g. `chore(cleanup): remove obsolete legacy payment code, unused test configs, and 3 dead utility modules. All tests passing.`

## Claude Code Command Example

Save the below as `.claude/commands/cleanup.md`:

```markdown
# Project Cleanup Agent (Claude Code Latest Workflow)

## Goal
Clean up the codebase by finding and safely removing all unused, obsolete, or redundant code, files, config, dependencies, and documentation.

## Action Plan

1. **Explore**: Read all source, config, and manifest files to build a candidate list of unused and obsolete items.
2. **Plan**: Draft a Markdown checklist of everything recommended for removal with reasons and locations.
3. **Confirm (Optional)**: Pause and share checklist for user review before changes.
4. **Execute**: Sequentially remove, refactor, and verify. Run tests after each batch. Mark completed items in checklist.
5. **Document**: Update docs/progress.md and commit with clear message.

**Safety Guidelines**:
- Never delete files without listing and explaining first.
- Always run tests and linters after changes.
- Double-check with maintainers if unsure about removal candidates.
- Pause for confirmation before risky deletions.

## Checklist Example

- [ ] `src/old_payment.py` — Not referenced, replaced by `payment_v2.py`
- [ ] `tests/test_legacy_api.py` — Covers deleted API
- [ ] `requirements.txt`: Remove `unused-lib`
```

## Best Practices for Accuracy & Efficiency (Claude Code v4+)

- Use `/cleanup file_or_folder` commands for targeted cleaning[1].
- Always start with **read-only exploration and planning**; never let Claude act before clarity.
- Use Markdown checklists in project root or `docs/` for transparency and traceability.
- After each batch of removals, run `/test` or a custom test/lint slash command.
- Use `/clear` between tasks to keep context focused and efficient[2].
- Keep user/maintainer in the loop for all non-trivial or consequential deletions.
- Use hooks or `CLAUDE.md` to remind about project-specific dependencies or gotchas.

## Evaluation

**Accuracy**  
- Traces dependencies/files and documents rationale for each removal—clear audit trail.
- Minimizes risk with multi-phase (explore/plan/execute) structure and mandatory test/verifications.

**Effectiveness**  
- Comprehensive (covers all code, config, dependencies, docs, and test artifacts).
- Makes removals in small, testable steps—prevents accidental breakage[2][3].

**Efficiency**  
- Markdown plans/checklists accelerate review and batch action.
- Uses Claude Code’s fast refactoring, command chaining, and context optimization.
- Supports team collaboration and approval loops.

This template reflects the latest Anthropic and community standards and will keep your cleanup safe, trackable, and highly productive[2][1][4].

[1] https://www.devshorts.in/p/claude-code-the-complete-guide-for
[2] https://www.anthropic.com/engineering/claude-code-best-practices
[3] https://www.datacamp.com/tutorial/claude-code
[4] https://codenotary.com/blog/using-claude-code-and-aider-to-refactor-large-projects-enhancing-maintainability-and-scalability
[5] https://www.siddharthbharath.com/claude-code-the-complete-guide/
[6] https://clune.org/posts/claude-code-manual/
[7] https://www.anthropic.com/claude-explains/improve-code-maintainability-using-claude
[8] https://www.builder.io/blog/claude-code
[9] https://apidog.com/blog/claude-code-beginners-guide-best-practices/
[10] https://www.claudelog.com/faq/
[11] https://docs.anthropic.com/en/docs/claude-code/settings
[12] https://www.reddit.com/r/ClaudeAI/comments/1k5slll/anthropics_guide_to_claude_code_best_practices/
[13] https://docs.anthropic.com/en/docs/claude-code/common-workflows
[14] https://www.reddit.com/r/ClaudeAI/comments/1ljv2kz/tips_for_developing_large_projects_with_claude/
[15] https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/claude-4-best-practices
[16] https://grantslatton.com/claude-code
[17] https://collabnix.com/claude-code-the-complete-developers-guide-to-getting-started-with-anthropics-revolutionary-ai-coding-assistant/
[18] https://natesnewsletter.substack.com/p/the-claude-code-complete-guide-learn
[19] https://www.youtube.com/watch?v=VxMnsSZJqUI
[20] https://news.ycombinator.com/item?id=43735550