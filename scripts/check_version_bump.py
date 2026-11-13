#!/usr/bin/env python3
"""Fail when shipped plugin files change but plugin.json's version does not grow.

Installed copies are cached by version, so a change shipped under the same
version never reaches anyone who already has the plugin.

Usage: check_version_bump.py <base-ref>
"""

from __future__ import annotations

import json
import subprocess
import sys

MANIFEST = ".claude-plugin/plugin.json"
SHIPPED = (".claude-plugin/", "agents/", "hooks/", "rules/", "skills/")


def parse(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


def problem(changed: list[str], base_version: str, head_version: str) -> str | None:
    shipped = [path for path in changed if path.startswith(SHIPPED)]
    if not shipped:
        return None
    if parse(head_version) <= parse(base_version):
        listed = ", ".join(shipped[:5]) + (" ..." if len(shipped) > 5 else "")
        return (
            f"Shipped files changed ({listed}) but {MANIFEST} version is {head_version}, "
            f"not above {base_version}. Bump it, or installed copies never update."
        )
    return None


def git(*args: str) -> str:
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__.strip().splitlines()[-1], file=sys.stderr)
        return 2
    base = sys.argv[1]
    changed = [p for p in git("diff", "--name-only", f"{base}...HEAD").splitlines() if p]
    base_version = json.loads(git("show", f"{base}:{MANIFEST}"))["version"]
    head_version = json.loads(git("show", f"HEAD:{MANIFEST}"))["version"]
    message = problem(changed, base_version, head_version)
    if message:
        print(message, file=sys.stderr)
        return 1
    print(f"version: {base_version} -> {head_version}, {len(changed)} files changed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
