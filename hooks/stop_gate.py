#!/usr/bin/env python3
"""Stop: uncommitted changes must pass `make lint` before Claude finishes.

Runs `make format` first when the target exists. Skips when the tree is
clean, in plan mode, or when the exact same changes already passed. After
3 blocked attempts in a row it lets Claude stop and tells the user, so a
problem Claude cannot fix never traps the session.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import emit, git, make_targets, project_root, read_input  # noqa: E402

MAX_BLOCKS = 3
LINT_TIMEOUT_SECONDS = 540  # Below the hook's 600s timeout, so we report instead of being killed.
TAIL_LINES = 30


def fingerprint(root: Path) -> str | None:
    """Hash of HEAD plus every uncommitted change, or None when the tree is clean."""
    status = git(root, "status", "--porcelain=v1", "-uall").stdout
    if not status.strip():
        return None
    digest = hashlib.sha256()
    digest.update(git(root, "rev-parse", "HEAD").stdout.encode())
    digest.update(git(root, "diff", "HEAD", "--binary").stdout.encode())
    untracked = git(root, "ls-files", "--others", "--exclude-standard").stdout.split("\n")
    for path in filter(None, untracked):
        digest.update(path.encode())
        file = root / path
        if file.is_file():
            digest.update(file.read_bytes())
    return digest.hexdigest()


def state_path(root: Path) -> Path:
    git_dir = Path(git(root, "rev-parse", "--absolute-git-dir").stdout.strip())
    return git_dir / "factory" / "stop-gate.json"


def load_state(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state))


def run(root: Path, target: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["make", target], cwd=root, capture_output=True, text=True, timeout=LINT_TIMEOUT_SECONDS
    )


def main() -> int:
    data = read_input()
    root = project_root(data)
    if root is None or data.get("permission_mode") == "plan":
        return 0
    targets = make_targets(root)
    if "lint" not in targets:
        return 0
    before = fingerprint(root)
    if before is None:
        return 0

    path = state_path(root)
    state = load_state(path)
    if before == state.get("passed"):
        return 0

    try:
        if "format" in targets:
            run(root, "format")
        lint = run(root, "lint")
    except subprocess.TimeoutExpired:
        print(f"factory: make lint took over {LINT_TIMEOUT_SECONDS}s; stop gate skipped.", file=sys.stderr)
        return 1

    if lint.returncode == 0:
        save_state(path, {"passed": fingerprint(root), "blocks": 0})
        return 0

    blocks = state.get("blocks", 0) + 1 if data.get("stop_hook_active") else 1
    if blocks > MAX_BLOCKS:
        save_state(path, {"blocks": 0})
        emit({"systemMessage": f"factory: make lint still fails after {MAX_BLOCKS} attempts. Stopping so you can decide."})
        return 0

    save_state(path, {"blocks": blocks})
    output = (lint.stdout + lint.stderr).strip().splitlines()[-TAIL_LINES:]
    print(
        f"make lint fails on the uncommitted changes (attempt {blocks}/{MAX_BLOCKS}). "
        "Fix the cause, do not silence the check. Last lines:\n" + "\n".join(output),
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
