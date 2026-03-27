#!/usr/bin/env python3
"""Switch the active development toolchain across Claude Code configuration.

Updates coderules references, CLAUDE.md, and command files (.claude/commands/)
to use the specified language toolchain.

Usage:
    python switch-toolchain.py <toolchain>
    python switch-toolchain.py --list
    python switch-toolchain.py --current
"""

import argparse
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent


@dataclass
class Toolchain:
    name: str
    coderules: str  # filename in docs/coderules/
    claude_doc: str  # filename in docs/claude/
    format_cmd: str  # formatting check command
    build_cmd: str  # build/lint check command
    test_cmd: str  # test command
    workflow_step: str  # step 8 in CLAUDE.md per-issue workflow
    gitignore: str  # filename in gitignores/


TOOLCHAINS: dict[str, Toolchain] = {
    "cs": Toolchain(
        name="C#",
        coderules="coderules-cs.md",
        claude_doc="claude-cs.md",
        format_cmd="dotnet format --verify-no-changes",
        build_cmd="dotnet build -warnaserror",
        test_cmd="dotnet test",
        workflow_step="Run dotnet format && dotnet build -warnaserror",
        gitignore="cs.gitignore",
    ),
    "go": Toolchain(
        name="Go",
        coderules="coderules-go.md",
        claude_doc="claude-go.md",
        format_cmd="gofmt -l .",
        build_cmd="go vet ./... && golangci-lint run",
        test_cmd="go test ./...",
        workflow_step="Run go vet ./... && golangci-lint run",
        gitignore="go.gitignore",
    ),
    "js": Toolchain(
        name="JavaScript",
        coderules="coderules-js.md",
        claude_doc="claude-js.md",
        format_cmd="npx prettier --check .",
        build_cmd="npx eslint .",
        test_cmd="npm test",
        workflow_step="Run npx eslint . && npx prettier --check .",
        gitignore="js.gitignore",
    ),
    "python": Toolchain(
        name="Python",
        coderules="coderules-python.md",
        claude_doc="claude-python.md",
        format_cmd="black --check .",
        build_cmd="ruff check .",
        test_cmd="uv run pytest",
        workflow_step="Run black --check . && ruff check .",
        gitignore="python.gitignore",
    ),
}

# Paths relative to repo root
CODERULES_INDEX = Path("docs/coderules.md")
CLAUDE_MD = Path("CLAUDE.md")
MERGE_CMD = Path(".claude/commands/merge.md")
CREV_CMD = Path(".claude/commands/crev.md")
GITIGNORES_DIR = Path("gitignores")
GITIGNORE = Path(".gitignore")


def update_coderules_index(tc: Toolchain) -> str:
    path = ROOT / CODERULES_INDEX
    path.write_text(f"@coderules/{tc.coderules}\n")
    return f"  {CODERULES_INDEX} -> @coderules/{tc.coderules}"


def update_claude_doc(tc: Toolchain) -> str:
    claude_dir = ROOT / "docs" / "claude"
    claude_dir.mkdir(parents=True, exist_ok=True)
    for old in claude_dir.glob("claude-*.md"):
        old.unlink()
    src = ROOT / "docs" / "coderules" / tc.coderules
    dst = claude_dir / tc.claude_doc
    shutil.copy2(src, dst)
    return f"  docs/claude/{tc.claude_doc} <- docs/coderules/{tc.coderules}"


def update_claude_md(tc: Toolchain) -> str:
    path = ROOT / CLAUDE_MD
    text = path.read_text()

    text = re.sub(
        r"^@docs/claude/claude-\w+\.md$",
        f"@docs/claude/{tc.claude_doc}",
        text,
        flags=re.MULTILINE,
    )

    text = re.sub(
        r"^(8\. )Run .+$",
        rf"\g<1>{tc.workflow_step}",
        text,
        flags=re.MULTILINE,
    )

    path.write_text(text)
    return f"  {CLAUDE_MD} -> @docs/claude/{tc.claude_doc}, step 8: {tc.workflow_step}"


def update_merge_cmd(tc: Toolchain) -> str:
    path = ROOT / MERGE_CMD
    text = path.read_text()

    text = re.sub(
        r"^1\. `.+` passes.*\n2\. `.+` passes.*\n3\. `.+` passes.*$",
        (
            f"1. `{tc.format_cmd}` passes\n"
            f"2. `{tc.build_cmd}` passes\n"
            f"3. `{tc.test_cmd}` passes (full test suite)"
        ),
        text,
        flags=re.MULTILINE,
    )

    text = re.sub(
        r"@docs/coderules/coderules-\w+\.md",
        f"@docs/coderules/{tc.coderules}",
        text,
    )

    path.write_text(text)
    return f"  {MERGE_CMD} -> checks updated, coderules ref -> {tc.coderules}"


def update_crev_cmd(tc: Toolchain) -> str:
    path = ROOT / CREV_CMD
    text = path.read_text()

    col = 45  # alignment column for comments
    lines = [
        f"{tc.test_cmd:<{col}}# Full test suite",
        f"{tc.format_cmd:<{col}}# Formatting",
        f"{tc.build_cmd:<{col}}# Build and lint checks",
    ]
    block = "```bash\n" + "\n".join(lines) + "\n```"

    text = re.sub(r"```bash\n.+?\n```", block, text, flags=re.DOTALL)

    path.write_text(text)
    return f"  {CREV_CMD} -> verification block updated"


def update_gitignore(tc: Toolchain) -> str:
    src = ROOT / GITIGNORES_DIR / tc.gitignore
    dst = ROOT / GITIGNORE
    if not src.exists():
        return f"  {GITIGNORE} -> SKIPPED ({GITIGNORES_DIR / tc.gitignore} not found)"
    shutil.copy2(src, dst)
    return f"  {GITIGNORE} -> {GITIGNORES_DIR / tc.gitignore}"


def detect_current() -> str | None:
    path = ROOT / CODERULES_INDEX
    if not path.exists():
        return None
    m = re.match(r"@coderules/coderules-(\w+)\.md", path.read_text().strip())
    return m.group(1) if m else None


def switch(toolchain_key: str) -> None:
    tc = TOOLCHAINS[toolchain_key]

    current = detect_current()
    if current == toolchain_key:
        print(f"Already set to {tc.name}. No changes made.")
        return

    print(f"Switching toolchain: {current or '(unknown)'} -> {tc.name}\n")

    results = [
        update_coderules_index(tc),
        update_claude_doc(tc),
        update_claude_md(tc),
        update_merge_cmd(tc),
        update_crev_cmd(tc),
        update_gitignore(tc),
    ]

    print("Updated:")
    for r in results:
        print(r)

    warnings = []
    if not (ROOT / "docs" / "coderules" / tc.coderules).exists():
        warnings.append(f"docs/coderules/{tc.coderules} does not exist yet")

    if warnings:
        print("\nWarnings:")
        for w in warnings:
            print(f"  {w}")

    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Switch the active development toolchain.",
    )
    parser.add_argument(
        "toolchain",
        nargs="?",
        choices=sorted(TOOLCHAINS),
        help="toolchain to activate",
    )
    parser.add_argument(
        "--list",
        "-l",
        action="store_true",
        help="list available toolchains",
    )
    parser.add_argument(
        "--current",
        "-c",
        action="store_true",
        help="show the currently active toolchain",
    )

    args = parser.parse_args()

    if args.list:
        current = detect_current()
        for key in sorted(TOOLCHAINS):
            tc = TOOLCHAINS[key]
            marker = " (active)" if key == current else ""
            print(f"  {key:<10} {tc.name}{marker}")
        return

    if args.current:
        current = detect_current()
        if current and current in TOOLCHAINS:
            print(f"{current} ({TOOLCHAINS[current].name})")
        elif current:
            print(f"{current} (not a known toolchain)")
        else:
            print("Could not detect current toolchain")
        return

    if not args.toolchain:
        parser.print_help()
        sys.exit(1)

    switch(args.toolchain)


if __name__ == "__main__":
    main()
