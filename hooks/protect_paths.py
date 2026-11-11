#!/usr/bin/env python3
"""PreToolUse on file edits: ask before touching a path listed in .factory.json."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ConfigError, emit, load_config, project_root, protected_match, read_input  # noqa: E402


def main() -> int:
    data = read_input()
    tool_input = data.get("tool_input") or {}
    file_path = tool_input.get("file_path") or tool_input.get("notebook_path")
    root = project_root(data)
    if not file_path or root is None:
        return 0

    try:
        patterns = load_config(root).get("protectedPaths", [])
    except ConfigError as error:
        # Exit 1 is a non-blocking notice: a broken config must not freeze all edits.
        print(f"factory: {error}", file=sys.stderr)
        return 1

    target = Path(file_path.replace("\\", "/"))
    if not target.is_absolute():
        target = Path(data.get("cwd") or root) / target
    try:
        relative = target.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return 0  # Outside the project: not ours to protect.

    pattern = protected_match(relative, patterns)
    if pattern is None:
        return 0
    emit({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": f"{relative} is protected by {pattern!r} in .factory.json. Confirm this edit.",
        }
    })
    return 0


if __name__ == "__main__":
    sys.exit(main())
