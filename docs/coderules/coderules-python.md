# Code Rules and Processes for this project

**KEY RULES**:

- NEVER CLAIM THAT SOMETHING IS COMPLETE IF THERE ARE REGRESSIONS. RUN THE FULL TEST SUITE BEFORE AND AFTER EACH WORK UNIT.
- NEVER USE `--no-verify` WITH GIT!
- **ALL CODE MUST PASS `black --check .` AND `ruff check .`** before committing

## Project Management

- Use `uv` for dependency management and running tools
- `uv run pytest` to run tests, `uv run black .` to format, `uv run ruff check .` to lint
- Keep `pyproject.toml` as the single source of truth for project metadata, dependencies, and tool configuration
- Pin direct dependencies in `pyproject.toml`; let `uv.lock` handle transitive resolution

## Test Locations

- **CRITICAL**: Tests MUST be placed in a `tests/` directory at the project root
- Use pytest as the test framework; do not mix with unittest unless wrapping legacy code
- Test files must be named `test_*.py` or `*_test.py`
- Integration tests go in `tests/integration/`
- Fixtures belong in `conftest.py` files at the appropriate scope

## Developing in Python

- Never do "fallback" programming in terms of requirements: if you expect a dependency, fail immediately if it's not present
- Target Python 3.12+ (use latest stable)
- Backwards compatibility is NOT a goal, neither in terms of Python versions, nor in terms of this project's code itself
- Use type hints on all function signatures; use `from __future__ import annotations` for modern syntax
- Use dataclasses or attrs for structured data; avoid plain dicts for domain objects
- Prefer `pathlib.Path` over `os.path`
- Use f-strings over `format()` or `%`-formatting

## Code Quality

- **CRITICAL**: Run `black --check .` before committing; all code must be formatted
- **CRITICAL**: Run `ruff check .` before committing; treat all warnings as errors
- Configure both black and ruff in `pyproject.toml`
- Use `ALL` caps for module-level constants
- Avoid mutable default arguments
- Prefer explicit imports over wildcard `from module import *`
- Use `collections.abc` for abstract types in annotations, not `typing` equivalents (e.g., `Sequence` not `typing.Sequence`)

## Error Handling

- Use exceptions for exceptional circumstances, not flow control
- Raise specific exception types, not bare `Exception`
- Include meaningful messages with context in exceptions
- Use custom exception classes for domain-specific errors
- Never catch and swallow exceptions silently; log or reraise
- Prefer `raise ... from err` to preserve exception chains

## Debugging

- **CRITICAL**: Always identify root causes of failures. Do NOT treat the symptoms of failures.
- Use `print()` or `logging.debug()` for quick debugging, but remove before committing
- Use the `logging` module for permanent logging needs; configure via `logging.basicConfig` or a dict config
- Use `breakpoint()` or IDE debugger for complex issues

## Process

- Don't back files up by copying! We use git for versioning.
- For each new development stage, create a new git branch first.
- We practice TDD:
  - Write tests first that demonstrate the desired behaviour
  - Pause for human review of the tests
  - Progress the implementation until the tests succeed.
  - NEVER tweak a test to "fit" the behaviour, unless the test is demonstrably broken.
  - Once a test set has been reviewed and approved, that's a contract: do NOT skip or change without re-approval. All approved tests MUST pass before PR.
  - Before opening a PR, you MUST ensure that the full test suite is green.
  - Review any `@pytest.mark.skip` tests and ensure they are documented.
  - Fix any linter warnings.
- Maintain progress in docs/TODO-X.md files
- Don't use /tmp and other locations outside the current repository: use the tmp/ directory in the repository dir instead, provided for this purpose
- If you create temporary scripts for debugging, remove them after use, and ensure not committed to git

## GitHub Workflow

- **NEVER EVER CHANGE THE DEFAULT BRANCH ON GIT OR GITHUB!**
- When creating PRs or commits, **DO NOT** mention Claude, Anthropic, or AI assistance in the message

**Note**: Don't bulk-add changes to git! Add modifications, additions and deletions individually, based on the knowledge of what you have actually done. That makes it easier for the human to follow, too. Doing it this way reduces the chance that unintended changes makes it into git.

Follow this process for each GitHub issue:

1. **Pick an issue** - Note its ID number
2. **Create branch** - Name format: `{ID}-{slug-derived-from-issue-title}`
   - Example: `9-parser-grammar-basic-terms`
3. **Write tests FIRST** - STOP after writing tests for human review
4. **Commit approved tests** - Only after review approval
5. **Implement until tests pass** - Make the tests green
6. **Run complete test suite** - No regressions tolerated!
7. **Create PR** - Make an orderly PR, squashing commits if necessary.
8. **Verify CI** - Ensure all CI tests pass fully
9. **Await PR review** - Wait for human review
10. **Merge** - After approval, merge PR and verify that tests complete in CI
11. **Maintain issues** Maintain issues by checking boxes where relevant after every commit. If all boxes are ticked, close the issues.
12. **Maintain epics** Update the Epic issue where relevant by ticking any boxes as issues are closed. If all sub-issues are closed, also close the epic.

In any git and GitHub messaging (commit messages, PR messages, issues, comments etc), we maintain a terse, professional tone:

1. **Never make unproven claims**: don't make claims about the validity, effectiveness or awesomeness of your changes in a commit or other message. By definition, that is determined by the CI results, which you can't see yet. Explain what was done, and why. Be modest and factual.
2. **Never use emoji symbols**: we're not 14-year-olds on Instagram here. No green ticks, no red crosses, no smileys, no symbols.
3. **Don't use bold text**: don't embellish or add emphasis with bold or italic text.
4. **Brevity**: issues and commit messages are written for co-workers. Respect their time. Obviously, be complete, but express yourself in a professional, concise tone.
5. **UK English**: we use UK English spelling throughout.
