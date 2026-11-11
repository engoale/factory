---
name: ship
description: Verify the current branch, push it, and open a pull request that closes its issue, with the contract's evidence in the description. Never merges.
disable-model-invocation: true
allowed-tools: Bash(git status *) Bash(git log *) Bash(git branch *) Bash(git symbolic-ref *) Bash(git push -u origin *) Bash(gh pr create *) Bash(gh issue view *) Bash(make lint) Bash(make ci)
---

Ship the current branch as a pull request.

## Context

- Branch: !`git branch --show-current`
- Default branch: !`git symbolic-ref --short refs/remotes/origin/HEAD || true`
- Uncommitted changes: !`git status --short`

## Steps

1. **Gate on the branch.** If the current branch is the default branch, stop. Never push to it.
2. **Gate on the tree.** If there are uncommitted changes, stop and ask the user whether to commit them.
3. **Find the issue.** Read the issue number from the branch name (`<type>/<number>-<slug>`). If there is none, ask the user for it.
4. **Verify.** Run the `/factory:check` skill. If anything is FAIL, stop and show the report. Do not ship a failing branch.
5. **Push.** `git push -u origin <branch>`. Never force-push.
6. **Open the pull request** with `gh pr create --base <default> --title "<title>" --body-file <tmp file>`:
   - Title: the main commit's Conventional Commits subject.
   - Body, in this order:
     - `Closes #<number>`
     - **Summary:** 2 to 4 bullets on what changed and why.
     - **Acceptance criteria:** each criterion from the issue with how it was verified.
     - **Evidence:** the `/factory:check` report, verbatim.
     - **Out of scope / follow-ups:** anything deliberately left out.
7. **Report.** Reply with the pull request URL.

## Rules

- Never merge, approve, or enable auto-merge.
- Never edit code in this skill. If something needs fixing, stop and say so.
