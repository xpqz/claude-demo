# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

@docs/claude/claude-js.md

## Workflow: Mandatory Review Stops

**CRITICAL**: Do NOT proceed without explicit human approval at these checkpoints:

1. **After writing tests** - STOP and present tests for review before implementing
2. **After implementation** - STOP and present work for review before moving to next issue
3. **After completing an epic** - STOP and summarise before starting the next epic

### Per-Issue Workflow

```
1. Create branch: {issue-id}-{slug-from-title}
2. Write tests defining expected behaviour
3. Create/update docs/prs/{issue-id}.md with test details
4. STOP → Present tests for review → Wait for approval
5. Commit approved tests
6. Implement until tests pass
7. Run full test suite (no regressions)
8. Run npx eslint . && npx prettier --check .
9. Update docs/prs/{issue-id}.md with implementation details
10. STOP → Present implementation for review → Wait for approval
11. Commit implementation
12. Close issue
```

Note: Always create/update the PR doc in docs/prs/{issue-id}.md when stopping for ANY review.

### PR Descriptions

For each issue, create `docs/prs/{issue-id}.md` containing:

- Issue reference and branch name
- Summary of changes
- File locations with descriptions
- Test locations and what they verify
- Design decisions with rationale
- Commit hashes

Never rush through multiple issues without stopping for review.

## Git Hooks

**NEVER use `--no-verify` when committing or pushing** unless the user has given
explicit approval for that specific commit. Pre-commit hooks exist to catch
regressions. If a hook fails, fix the underlying issue rather than bypassing
the check.

## Code Intelligence

Prefer LSP over Grep/Glob/Read for code navigation:
- `goToDefinition` / `goToImplementation` to jump to source
- `findReferences` to see all usages across the codebase
- `workspaceSymbol` to find where something is defined
- `documentSymbol` to list all symbols in a file
- `hover` for type info without reading the file
- `incomingCalls` / `outgoingCalls` for call hierarchy

Before renaming or changing a function signature, use
`findReferences` to find all call sites first.

Use Grep/Glob only for text/pattern searches (comments,
strings, config values) where LSP doesn't help.

After writing or editing code, check LSP diagnostics before
moving on. Fix any type errors or missing imports immediately.