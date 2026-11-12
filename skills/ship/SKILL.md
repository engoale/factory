---
name: ship
description: Verify the current branch, push it, and open a pull request that closes its issue, with the contract's evidence in the description. Never merges.
disable-model-invocation: true
allowed-tools: Bash(git status *) Bash(git log *) Bash(git branch *) Bash(git rev-parse *) Bash(gh repo view *) Bash(git push -u origin *) Bash(gh pr create *) Bash(gh pr checks *) Bash(gh issue view *) Bash(make lint) Bash(make ci)
---

Ship the current branch as a pull request.

## Steps

1. **Gate on the branch.** Run `git branch --show-current` and `gh repo view --json defaultBranchRef -q .defaultBranchRef.name`. If the current branch is the default branch, stop. Never push to it.
2. **Gate on the tree.** Run `git status --short`. If there are uncommitted changes, stop and ask the user whether to commit them.
3. **Find the issue.** Read the issue number from the branch name (`<type>/<number>-<slug>`). If there is none, ask the user for it.
4. **Verify.** Run the `/factory:check` skill. If anything is FAIL, stop and show the report. Do not ship a failing branch.
5. **Gate on criteria.** Run `gh issue view <number>` (body with checkboxes) and `gh issue view <number> --comments` (comments). Find the latest `**Verification:**` comment.
   - If there is none, stop and tell the user to run `/factory:build <number>` first.
   - If any criterion is NOT MET, stop and list them.
   - If the issue has more unticked boxes than NEEDS HUMAN rows, stop: something was skipped.
6. **Gate on review.** In the same output, find the latest `**Review:**` comment. Stop and suggest `/factory:review` if there is none, if its verdict is not APPROVE, or if its `Reviewed commit` differs from `git rev-parse HEAD` (the code changed after the review).
7. **Push.** `git push -u origin <branch>`. Never force-push.
8. **Open the pull request** with `gh pr create --base <default> --title "<title>" --body-file <tmp file>`:
   - Title: the main commit's Conventional Commits subject.
   - Body, in this order:
     - `Closes #<number>`
     - **Summary:** 2 to 4 bullets on what changed and why.
     - **Acceptance criteria:** the verification table from the issue comment, unchanged.
     - **Needs human before merge:** a checkbox per NEEDS HUMAN criterion, with what to do. Omit the section if there are none.
     - **Review:** the verdict and reviewed commit, with a link to the review comment.
     - **Evidence:** the `/factory:check` report, verbatim.
     - **Out of scope / follow-ups:** anything deliberately left out.
9. **Wait for CI.** Run `gh pr checks <pr-number> --watch --interval 30` with a 10-minute command timeout. Local checks passing does not prove CI passes: runtimes and dependency versions can differ.
10. **Report.** Reply with the pull request URL and each CI check with its result. If any check failed, say so first, name the failing checks, and state that the PR must not be merged until it is green. If CI is still running after the timeout, say which checks are pending.

## Rules

- Never merge, approve, or enable auto-merge.
- Never edit code in this skill. If something needs fixing, stop and say so.
