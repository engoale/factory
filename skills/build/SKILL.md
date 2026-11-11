---
name: build
description: Implement an approved GitHub issue on its own branch, following plan, build and verify stages, until the project's contract passes. Does not push or open a pull request.
argument-hint: "[issue-number]"
disable-model-invocation: true
allowed-tools: Bash(gh issue view *) Bash(gh repo view *) Bash(gh issue comment *) Bash(git status *) Bash(git fetch *) Bash(git switch *) Bash(git add *) Bash(git commit *) Bash(make lint) Bash(make ci)
---

Implement issue #$0.

## Stage 1: Gate

Run `gh issue view $0 --comments` and read the full output. If the issue does not exist, stop.

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
4. When it passes, walk through every acceptance criterion and state how it was verified, with evidence.

## Hand-off

Reply with: the branch name, the commit list (`git log --oneline origin/<default>..HEAD`), the `/factory:check` report, the acceptance criteria with their evidence, and the next command: `/factory:ship`.

Do not push. Do not open a pull request.
