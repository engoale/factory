#!/usr/bin/env python3
"""SessionStart: load the factory contract and this project's settings into context.

Plugins cannot ship an always-loaded instruction file, so this hook is what
makes the contract apply in every project.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ConfigError, load_config, make_targets, project_root, read_input  # noqa: E402

CONTRACT = Path(__file__).resolve().parent.parent / "rules" / "contract.md"


def main() -> int:
    data = read_input()
    parts = ["<factory-contract>", CONTRACT.read_text().strip(), "</factory-contract>"]

    root = project_root(data)
    if root is not None:
        try:
            patterns = load_config(root).get("protectedPaths", [])
        except ConfigError as error:
            parts.append(f"Factory warning: {error}. Protected paths are not enforced until it is fixed.")
            patterns = []
        if patterns:
            parts.append("Protected paths in this project (ask before editing): " + ", ".join(patterns))
        missing = {"lint", "ci"} - make_targets(root)
        if missing:
            parts.append(
                "Factory warning: the Makefile lacks targets "
                + ", ".join(sorted(missing))
                + ". /factory:check and the stop gate cannot verify this project."
            )

    print("\n\n".join(parts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
