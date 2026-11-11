#!/usr/bin/env python3
"""PreToolUse on Bash: deny force-pushes and pushes to the default branch.

This is a guardrail against mistakes, not a security boundary: a command
built to evade it (aliases, scripts, eval) will get through.
"""

from __future__ import annotations

import re
import shlex
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import default_branch, emit, git, project_root, read_input  # noqa: E402

SEGMENT_SPLIT = re.compile(r"&&|\|\||[;|\n]")
OPTIONS_WITH_VALUE = {"-o", "--push-option", "--repo", "--receive-pack", "--exec"}


def push_args(segment: str) -> list[str] | None:
    """Arguments after `git push` when the segment runs git push, else None."""
    try:
        tokens = shlex.split(segment)
    except ValueError:
        tokens = segment.split()
    while tokens and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", tokens[0]):
        tokens = tokens[1:]  # Leading VAR=value assignments.
    if not tokens or not (tokens[0] == "git" or tokens[0].endswith("/git")):
        return None
    i = 1
    while i < len(tokens) and tokens[i].startswith("-"):
        i += 2 if tokens[i] in ("-C", "-c") else 1
    if i < len(tokens) and tokens[i] == "push":
        return tokens[i + 1:]
    return None


def violation(args: list[str], root: Path) -> str | None:
    positional: list[str] = []
    skip = False
    for arg in args:
        if skip:
            skip = False
            continue
        if arg in OPTIONS_WITH_VALUE:
            skip = True
        elif arg.startswith("--force") or arg == "-f" or (re.match(r"^-[a-zA-Z]+$", arg) and "f" in arg):
            return "Force-pushing is not allowed. Push a new commit instead."
        elif arg in ("--all", "--mirror"):
            return f"{arg} would push the default branch. Push the feature branch by name."
        elif not arg.startswith("-"):
            positional.append(arg)

    branch = default_branch(root)
    refspecs = positional[1:]
    if any(ref.startswith("+") for ref in refspecs):
        return "A '+' refspec force-pushes. Push a new commit instead."
    destinations = [ref.split(":")[-1].removeprefix("refs/heads/") for ref in refspecs]
    if not refspecs:
        current = git(root, "branch", "--show-current").stdout.strip()
        destinations = [current]
    if branch in destinations:
        return f"Pushing to the default branch '{branch}' is not allowed. Push a feature branch and open a pull request."
    return None


def main() -> int:
    data = read_input()
    command = (data.get("tool_input") or {}).get("command", "")
    root = project_root(data)
    if "push" not in command or root is None:
        return 0
    for segment in SEGMENT_SPLIT.split(command):
        args = push_args(segment.strip())
        if args is None:
            continue
        reason = violation(args, root)
        if reason:
            emit({
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": reason,
                }
            })
            return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
