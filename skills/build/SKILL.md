---
name: build
description: Implement an approved GitHub issue on its own branch, following plan, build and verify stages, until the project's contract passes. Does not push or open a pull request.
argument-hint: "[issue-number]"
disable-model-invocation: true
allowed-tools: Bash(gh issue view *) Bash(gh repo view *) Bash(gh issue comment *) Bash(gh issue edit *) Bash(git status *) Bash(git fetch *) Bash(git switch *) Bash(git add *) Bash(git commit *) Bash(make lint) Bash(make ci)
---

Implement issue #$0.

## Stage 1: Gate

Run `gh issue view $0` for the spec, then `gh issue view $0 --comments` for its discussion. The second command alone omits the body. If the issue does not exist, stop.

Check the spec has all five parts: problem, goal, acceptance criteria, out of scope, end-to-end check. If any part is missing or vague, stop. List what is missing and suggest `/factory:spec` to fix it. Do not continue.

## Stage 2: Branch

1. Run `git status --short`. If the working tree is not clean, stop and ask the user what to do with the changes.
2. Find the default branch with `gh repo view --json defaultBranchRef -q .defaultBranchRef.name`, then `git fetch origin`.
3. Create the branch from the fresh default branch: `git switch -c <type>/$0-<short-slug> origin/<default>`. Pick `<type>` from Conventional Commits (`feat`, `fix`, `refactor`, ...).

## Stage 3: Plan

1. Read the files and interfaces the change touches. Read, do not edit.
2. Present a numbered checklist: one line per logical component, naming the files each one changes and the test that proves it.
3. Wait for the user to approve the plan. Skip this wait only when the whole diff fits in one sentence.
4. If the approved plan differs from the issue, post a `Decision:` or `Spec Change:` comment on the issue (`gh issue comment $0`) before building.

## Stage 4: Build

For each component in the plan, in order:

1. For a bug fix, write a test that reproduces the bug and run it to see it fail.
2. Implement the component. Touch only what it needs.
3. Run the relevant tests.
4. Commit: `<type>(<scope>): <description>` with `Refs #$0` in the body.

If a decision changes during the build, post an issue comment using the project's issue comment format.

## Stage 5: Verify

1. Run the `/factory:check` skill.
2. If it fails, fix the cause (never silence a check), commit, and run it again.
3. After 3 failed attempts on the same failure, stop. Post a `Blocker:` comment on the issue and report to the user.

## Stage 6: Acceptance criteria

Re-read the issue. For every acceptance criterion, copied word for word from the issue (never merged, split, or reworded), assign one status:

- **MET:** proven by a command you ran in this session, with its output. Name the test or command.
- **NOT MET:** not done, or done only partly.
- **PENDING CI:** can only be proven by CI on the pull request (a CI job passes, an image builds, all checks are green). `/factory:ship` settles it.
- **NEEDS HUMAN:** cannot be proven here or in CI (real API keys, a browser, a device). Say exactly what the human must do.

Rules:

- Reading the code is never evidence. "Verified by code inspection" means NOT MET.
- Coverage of new code counts. If a new file or function has no test exercising it, its criteria are NOT MET.
- Treat the end-to-end check as one more criterion. Run it if you can. Otherwise mark it NEEDS HUMAN.

If anything is NOT MET, go back to Stage 4 for it. Apply the 3-attempt limit from Stage 5.

When done:

1. Tick the box of every MET criterion in the issue body: write the edited body to a temp file, then `gh issue edit $0 --body-file <file>`. Change nothing else in the body.
2. Post one comment on the issue (`gh issue comment $0`) titled `**Verification:**`, holding a table with columns Criterion, Status, Evidence, and the `/factory:check` report.

## Hand-off

Reply with: the branch name, the commit list (`git log --oneline origin/<default>..HEAD`), the verification table, and the next command: `/factory:review`.

Do not push. Do not open a pull request.
