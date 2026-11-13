#!/usr/bin/env python3
"""Status board for factory work: one row per issue, then a merge order.

Usage: status.py [issue ...]
With no issues, covers every open pull request whose branch is <type>/<number>-<slug>.
Uses the GitHub REST API only. Changes nothing.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import dataclass, field

BRANCH = re.compile(r"^[a-z]+/(\d+)-")
VERDICT = re.compile(r"\*\*Verdict:\*\*\s*(APPROVE|CHANGES REQUESTED|INCOMPLETE)")
REVIEWED = re.compile(r"\*\*Reviewed commit:\*\*\s*`?([0-9a-f]{7,40})")
FACTORY_COMMENT = re.compile(r"^\*\*(Blocker|Verification|Review):\*\*")


@dataclass
class Row:
    issue: int
    title: str = ""
    branch: str | None = None
    pr: int | None = None
    draft: bool = False
    head: str | None = None
    ci: str = "none"
    verified: bool = False
    review: str | None = None
    review_commit: str | None = None
    blocked: bool = False
    files: set[str] = field(default_factory=set)


def repo_from_remote(url: str) -> str | None:
    """owner/name from an https or ssh GitHub remote URL."""
    match = re.search(r"github\.com[:/]([^/]+/[^/]+?)(?:\.git)?/?$", url.strip())
    return match.group(1) if match else None


def gh(path: str) -> object:
    result = subprocess.run(["gh", "api", path], check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def ci_state(check_runs: list[dict]) -> str:
    if not check_runs:
        return "none"
    failed = sorted(r["name"] for r in check_runs if r.get("conclusion") in ("failure", "timed_out", "cancelled", "action_required"))
    if failed:
        return "failing: " + ", ".join(failed)
    if any(r.get("status") != "completed" for r in check_runs):
        return "running"
    return "green"


def read_comments(row: Row, comments: list[dict]) -> None:
    """Fill verification, review and blocker state from the issue's comments, oldest first."""
    last_kind = None
    for comment in comments:
        body = comment.get("body") or ""
        match = FACTORY_COMMENT.match(body.lstrip())
        if not match:
            continue
        last_kind = match.group(1)
        if last_kind == "Verification":
            row.verified = True
        elif last_kind == "Review":
            verdict, commit = VERDICT.search(body), REVIEWED.search(body)
            row.review = verdict.group(1) if verdict else "unreadable"
            row.review_commit = commit.group(1) if commit else None
    row.blocked = last_kind == "Blocker"


def next_step(row: Row) -> str:
    if row.blocked:
        return "answer the Blocker"
    if row.branch is None:
        return "build"
    if not row.verified:
        return "build (verify)"
    reviewed_head = bool(row.head and row.review_commit and row.head.startswith(row.review_commit))
    if row.review is None or (row.pr is not None and not reviewed_head):
        return "review"
    if row.review == "CHANGES REQUESTED":
        return "fix, then review"
    if row.review != "APPROVE":
        return "review inputs broken (factory bug)"
    if row.pr is None:
        return "ship"
    if row.ci.startswith("failing"):
        return "fix CI"
    if row.ci in ("running", "none"):
        return "wait for CI"
    if row.draft:
        return "ship (mark ready)"
    return "merge"


def merge_order(files: dict[int, set[str]]) -> list[tuple[int, list[int]]]:
    """Independent PRs first, then each group of PRs sharing files, broadest change first."""
    prs = sorted(files)
    overlaps = {p: sorted(q for q in prs if q != p and files[p] & files[q]) for p in prs}
    independent = [(p, []) for p in prs if not overlaps[p]]
    groups: list[list[int]] = []
    seen: set[int] = set()
    for p in prs:
        if p in seen or not overlaps[p]:
            continue
        group, stack = [], [p]
        while stack:
            q = stack.pop()
            if q in seen:
                continue
            seen.add(q)
            group.append(q)
            stack.extend(overlaps[q])
        # Most shared files first, then the largest change: the others adapt to it once.
        groups.append(sorted(group, key=lambda q: (-len(files[q] & set().union(*(files[o] for o in overlaps[q]))), -len(files[q]), q)))
    return independent + [(p, overlaps[p]) for group in groups for p in group]


def collect(repo: str, issues: list[int]) -> list[Row]:
    open_prs = gh(f"repos/{repo}/pulls?state=open&per_page=100")
    by_issue = {}
    for pr in open_prs:
        match = BRANCH.match(pr["head"]["ref"])
        if match:
            by_issue.setdefault(int(match.group(1)), pr)
    if not issues:
        issues = sorted(by_issue)
    branches = [b["name"] for b in gh(f"repos/{repo}/branches?per_page=100")]

    rows = []
    for number in issues:
        row = Row(issue=number, title=gh(f"repos/{repo}/issues/{number}")["title"])
        pr = by_issue.get(number)
        if pr:
            row.branch, row.pr, row.draft, row.head = pr["head"]["ref"], pr["number"], pr["draft"], pr["head"]["sha"]
            row.ci = ci_state(gh(f"repos/{repo}/commits/{row.head}/check-runs?per_page=100")["check_runs"])
            row.files = {f["filename"] for f in gh(f"repos/{repo}/pulls/{row.pr}/files?per_page=100")}
        else:
            row.branch = next((b for b in branches if BRANCH.match(b) and BRANCH.match(b).group(1) == str(number)), None)
        read_comments(row, gh(f"repos/{repo}/issues/{number}/comments?per_page=100"))
        rows.append(row)
    return rows


def render(rows: list[Row]) -> str:
    lines = [
        "| Issue | PR | Draft | CI | Verified | Review | Next step |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        review = r.review or "-"
        if r.review and r.head and r.review_commit and not r.head.startswith(r.review_commit):
            review += " (older commit)"
        lines.append(
            f"| #{r.issue} {r.title[:50]} | {f'#{r.pr}' if r.pr else '-'} | {'yes' if r.draft else 'no' if r.pr else '-'} "
            f"| {r.ci if r.pr else '-'} | {'yes' if r.verified else 'no'} | {review} | {next_step(r)} |"
        )
    files = {r.pr: r.files for r in rows if r.pr}
    if files:
        lines += ["", "Merge order (merge the default branch into each later PR and re-review after every merge):", ""]
        for i, (pr, overlaps) in enumerate(merge_order(files), 1):
            note = f"shares files with {', '.join(f'#{o}' for o in overlaps)}" if overlaps else "independent"
            lines.append(f"{i}. #{pr} ({note})")
    return "\n".join(lines)


def main() -> int:
    try:
        issues = [int(arg.lstrip("#")) for arg in sys.argv[1:]]
    except ValueError:
        print(__doc__.strip().splitlines()[2], file=sys.stderr)
        return 2
    remote = subprocess.run(["git", "remote", "get-url", "origin"], check=True, capture_output=True, text=True).stdout
    repo = repo_from_remote(remote)
    if repo is None:
        print(f"origin is not a GitHub repository: {remote.strip()}", file=sys.stderr)
        return 2
    print(render(collect(repo, issues)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
