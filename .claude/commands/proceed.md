# /proceed - Pick up and implement the next issue

Work through the next logical GitHub issue using red/green TDD with adversarial review gates.

## Process

### 1. Identify the next issue

Use `gh` to list open issues. Find the epic issue and determine which sub-issue should be worked next based on:
- Dependency order (earlier phases before later ones)
- Which issues are already closed
- Which issues are currently in progress

Note the issue ID and title. Read the issue body in full.

### 2. Gather context

Read all referenced documents:
- The epic issue
- Any design or architecture documents referenced in the issue (e.g. docs/plans/*.md)
- Any review documents that informed the current design (docs/reviews/*.md)

Use a sub-agent to analyse the current state of the codebase:
- What already exists?
- What is the starting point for this issue?
- Are there any existing patterns to follow?

### 3. Create branch

Ensure you are on `main` and up to date. Create and switch to a new branch:

```
{issue-id}-{slug-from-issue-title}
```

For example, issue #2 titled "Phase 1: Project scaffolding and test runner" becomes branch `2-project-scaffolding-and-test-runner`.

### 4. Write tests (red phase)

Write tests that demonstrate the behaviour defined by the issue. Follow these rules:

- Tests go in `tests/Unit/` or `tests/Integration/` as appropriate
- Test functions are niladic tradfns: `r←Test_Name dummy` returning 1 (pass) or 0 (fail)
- Test names begin with `Test_`
- Follow patterns established in the Stark test infrastructure (see Stark/Tests/)
- Cover happy paths, edge cases, and error conditions as specified in the issue
- Where possible, validate APL-level test assertions by running them against Dyalog using `dyalogscript`

Confirm the tests fail (red). This is critical: tests that pass before implementation are suspect.

Commit the tests to the branch.

### 5. Adversarial test review

Launch a sub-agent to review the tests. The review must focus on:

1. Do the tests adequately demonstrate the desired behaviour described in the issue?
2. Do the tests fully define edge cases and error behaviour?
3. Are there any missing test cases that the issue or design documents call for?
4. Are the test assertions correct and meaningful?
5. Do the tests follow established patterns?

The sub-agent should write its findings. Address ALL findings, including minor ones. If tests are modified, re-validate that they still fail (red phase must hold). Commit any test changes.

### 6. Implement (green phase)

Implement the feature until all tests pass:

- Follow the implementation guidance in the issue and referenced design documents
- Follow code patterns established in the codebase
- Run the full test suite to confirm no regressions
- Use `dyalogscript` to validate APL code works correctly

Write a detailed PR description to `docs/prs/{ID}.md` containing:
- Issue reference and branch name
- Summary of changes
- File locations with descriptions
- Test locations and what they verify
- Design decisions with rationale
- Commit hashes

Commit the implementation to the branch.

### 7. Adversarial implementation review

Launch a sub-agent to review the implementation. Direct it to read `docs/prs/{ID}.md` and the GitHub issue #{ID}. The review must cover:

1. **Specification conformance**: validate that the implementation conforms to the issue and any referenced design or architecture documentation.

2. **Reward hacking**: examine any test set changes to ensure that no agreed tests have been unduly modified or disabled.

3. **Code organisation and housekeeping**:
   - Is the implementation structured logically, optimising for understandability and maintainability?
   - Are the modifications in the right place?
   - Are files suitably single-concern where that makes sense?
   - Are any files growing too large?

4. **Documentation drift**:
   - Do issues and docs/prs/{ID}.md correctly describe what was implemented?
   - Are commit messages terse but complete, suitable for a professional reader and clean of emojis, bold text, AI mentions, invalidated claims, hyperbole and em-dashes?

5. **Verdict**: must be either "Request changes: ... {list}" or "Approve".

### 8. Address review findings

If the verdict is "Request changes":
- Address every finding
- Re-run the full test suite
- Update docs/prs/{ID}.md if needed
- Commit changes
- Repeat steps 7-8 until verdict is "Approve"

### 9. Final summary

Once approved:
- Ensure all changes are committed to the branch
- Report to the user:
  - What was implemented (brief summary)
  - Reference to `docs/prs/{ID}.md` for full details
  - Link to the GitHub issue
  - Request user review before merge
