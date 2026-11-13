#!/usr/bin/env python3
"""Collect everything the reviewer sees into files.

The session that wrote the code never summarizes it for the reviewer. This
script decides what the reviewer gets, so the review cannot be framed.

Usage: collect.py <issue-number> [worktree]
Reviews the branch checked out in the worktree (default: the current directory).
Prints the directory it wrote.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PLUGIN_ROOT / "hooks"))
from common import ConfigError, git, load_config, protected_match  # noqa: E402

# Added lines that silence a check instead of fixing the cause. Language-agnostic.
SUPPRESSION = re.compile(
    r"noqa|type:\s*ignore|pyright:\s*ignore|pragma:\s*no cover|"
    r"eslint-disable|@ts-ignore|@ts-expect-error|nolint|#\[allow\(|@SuppressWarnings|"
    r"mark\.(skip|xfail)|\.skip\(|\bxit\(|\.only\(|fail_under|cov-fail-under|--no-verify|"
    r"filterwarnings|^\s*_\s*=\s*[A-Za-z_][A-Za-z0-9_]*\s*$|"
    r"except\s*:|except\s+\(?(Base)?Exception\b[^:]*:\s*$|except\b[^:]*:\s*pass\s*$|"
    r"catch\s*(\([^)]*\))?\s*\{\s*\}"
)
TEST_FILE = re.compile(r"(^|/)(tests?|__tests__|spec)/|(^|/)test_[^/]*$|_test\.[a-z]+$|\.(test|spec)\.[a-z]+$")
TEST_LINE = re.compile(r"\bdef test_|\bassert\b|\bexpect\(|\b(it|test)\(")
HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")


def scan(diff: str) -> list[str]:
    """Suspicious lines in a `git diff -U0`: added suppressions and removed test lines."""
    findings: list[str] = []
    path = ""
    line = 0
    for raw in diff.splitlines():
        if raw.startswith("+++ "):
            path = raw[6:] if raw.startswith("+++ b/") else raw[4:]
            continue
        if raw.startswith("--- "):
            continue
        hunk = HUNK.match(raw)
        if hunk:
            line = int(hunk.group(1))
            continue
        if raw.startswith("+"):
            if SUPPRESSION.search(raw[1:]):
                findings.append(f"{path}:{line}: added: {raw[1:].strip()}")
            line += 1
        elif raw.startswith("-") and TEST_FILE.search(path) and TEST_LINE.search(raw[1:]):
            findings.append(f"{path}: removed test line: {raw[1:].strip()}")
    return findings


def ci_summary(pr: dict | None, head: str) -> str:
    """The pull request's CI results for exactly this commit, or why there are none."""
    if pr is None:
        return "No pull request for this branch yet: CI has not run.\n"
    if pr.get("headRefOid") != head:
        return f"PR #{pr['number']} points at {pr.get('headRefOid')}, not {head}: CI has not run on this commit.\n"
    checks = pr.get("statusCheckRollup") or []
    if not checks:
        return f"PR #{pr['number']}: no CI checks reported for {head}.\n"
    lines = [f"PR #{pr['number']}, commit {head}:"]
    for check in checks:
        name = check.get("name") or check.get("context") or "unnamed"
        result = check.get("conclusion") or check.get("state") or check.get("status") or "unknown"
        lines.append(f"- {name}: {result}")
    return "\n".join(lines) + "\n"


def render_issue(issue: dict) -> str:
    """The issue body and every comment as one markdown document.

    `gh issue view --comments` prints only the comments when not on a terminal,
    which once left the reviewer without the spec. JSON avoids that.
    """
    parts = [f"# #{issue['number']} {issue['title']}", f"State: {issue['state']}", issue["body"] or "(empty body)"]
    for comment in issue.get("comments", []):
        author = (comment.get("author") or {}).get("login", "unknown")
        parts.append(f"## Comment by {author} at {comment['createdAt']}\n\n{comment['body']}")
    return "\n\n".join(parts) + "\n"


def protected(files: list[str], root: Path) -> list[str]:
    try:
        patterns = load_config(root).get("protectedPaths", [])
    except ConfigError as error:
        return [f"(could not read protected paths: {error})"]
    return [f"{f}  (protected by {p})" for f in files if (p := protected_match(f, patterns))]


def run(*args: str) -> str:
    return subprocess.run(args, check=True, capture_output=True, text=True).stdout


def main() -> int:
    if len(sys.argv) not in (2, 3) or not sys.argv[1].isdigit():
        print("usage: collect.py <issue-number> [worktree]", file=sys.stderr)
        return 2
    issue = sys.argv[1]
    if len(sys.argv) == 3:
        os.chdir(sys.argv[2])
    root = Path(run("git", "rev-parse", "--show-toplevel").strip())
    base = run("gh", "repo", "view", "--json", "defaultBranchRef", "-q", ".defaultBranchRef.name").strip()
    run("git", "fetch", "-q", "origin", base)
    merge_base = run("git", "merge-base", f"origin/{base}", "HEAD").strip()

    out = Path(run("git", "rev-parse", "--absolute-git-dir").strip()) / "factory" / "review"
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)

    files = [f for f in git(root, "diff", "--name-only", merge_base, "HEAD").stdout.splitlines() if f]
    suspicious = scan(git(root, "diff", "-U0", merge_base, "HEAD").stdout)
    touched = protected(files, root)

    head = run("git", "rev-parse", "HEAD").strip()
    (out / "head.txt").write_text(head + "\n")
    (out / "root.txt").write_text(f"{root}\n")
    fields = "number,title,state,body,comments"
    (out / "issue.md").write_text(render_issue(json.loads(run("gh", "issue", "view", issue, "--json", fields))))
    (out / "commits.txt").write_text(run("git", "log", "--format=%h %s", f"{merge_base}..HEAD"))
    (out / "stat.txt").write_text(run("git", "diff", "--stat", merge_base, "HEAD"))
    (out / "diff.patch").write_text(run("git", "diff", merge_base, "HEAD"))
    (out / "suppressions.txt").write_text("\n".join(suspicious) + "\n" if suspicious else "none\n")
    (out / "protected.txt").write_text("\n".join(touched) + "\n" if touched else "none\n")
    shutil.copy(PLUGIN_ROOT / "rules" / "contract.md", out / "contract.md")

    # Evidence produced here, at the reviewed commit, so the reviewer never has to
    # trust output pasted by the session that wrote the code.
    runner = PLUGIN_ROOT / "skills" / "check" / "scripts" / "run.sh"
    evidence = [subprocess.run([str(runner), target], cwd=root, capture_output=True, text=True).stdout
                for target in ("lint", "ci")]
    (out / "evidence.txt").write_text(f"Run by collect.py at {head}\n\n" + "\n".join(evidence))

    pr_view = subprocess.run(
        ["gh", "pr", "view", "--json", "number,headRefOid,statusCheckRollup"], cwd=root, capture_output=True, text=True
    )
    pr = json.loads(pr_view.stdout) if pr_view.returncode == 0 else None
    (out / "ci.txt").write_text(ci_summary(pr, head))

    print(out)
    print(f"{len(files)} files changed, {len(suspicious)} suspicious lines, {len(touched)} protected paths touched")
    return 0


if __name__ == "__main__":
    sys.exit(main())
