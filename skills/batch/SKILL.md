---
name: batch
description: Run build, review and ship for several issues in parallel, each in its own worktree, stopping each issue at its first failed gate. Ends with the status board and a merge order. Never merges.
argument-hint: "<issue> [issue ...]"
disable-model-invocation: true
allowed-tools: Bash(git *) Bash(gh pr *) Bash(gh issue *) Bash(${CLAUDE_SKILL_DIR}/../review/scripts/collect.py *) Bash(${CLAUDE_SKILL_DIR}/../check/scripts/run.sh *) Bash(${CLAUDE_SKILL_DIR}/../status/scripts/status.py *)
---

Run the factory pipeline for issues: $ARGUMENTS

Each issue goes **build → review → ship**. An issue stops at its first failed gate; the others continue. Every stage follows its own skill file, so the rules live in one place:

- Build procedure: `${CLAUDE_SKILL_DIR}/../build/SKILL.md` (run by the `factory:builder` agent)
- Review procedure: `${CLAUDE_SKILL_DIR}/../review/SKILL.md`
- Ship procedure: `${CLAUDE_SKILL_DIR}/../ship/SKILL.md`

Read the review and ship files before stage 2. You run those stages yourself, following their steps with the adjustments below, because agents cannot start other agents.

## Stage 0: Preflight

1. Parse the issue numbers. More than 5: stop and ask which 5 to run. Batches beyond that produce more reviews and merges than one person can follow.
2. Run `git status --short` and `git branch --show-current`. The main checkout must be clean and on the default branch, so every issue branch is free to be checked out in a worktree. Otherwise stop and say why.

## Stage 1: Build

Start one `factory:builder` agent per issue, **with worktree isolation**, at most 3 running at a time. Start the next when one finishes. Each task is exactly:

`Build issue #<number>. Procedure: <absolute path of build/SKILL.md>. You are unattended.`

Record each final reply: Outcome, Branch, Worktree, Head, Reason, Notes. Only VERIFIED issues continue.

## Stage 2: Review

For each VERIFIED issue, following the review procedure with these adjustments:

1. Collect with `${CLAUDE_SKILL_DIR}/../review/scripts/collect.py <number> <worktree>` and a 10-minute command timeout. At most 3 collections at a time: each runs `make ci`.
2. Start the `factory:reviewer` agent with exactly `Review the change prepared in <directory>.` Reviewers can run in parallel.
3. Post each verdict with `**Review:**` as the review procedure says, unchanged.

Only APPROVE continues. CHANGES REQUESTED and INCOMPLETE stop that issue.

## Stage 3: Ship

For each approved issue, follow the ship procedure from step 5 (criteria gate) with these adjustments:

- Run git commands as `git -C <worktree> ...` and pass `--head <branch>` (or the PR number) to `gh pr` commands, since the branch is not checked out in the main checkout.
- Step 4 (verify) is already satisfied when the review's `Reviewed commit` equals the worktree's HEAD: its `evidence.txt` ran `make lint` and `make ci` on that commit. Otherwise stop that issue.
- Create or update every draft PR first, then wait for CI on each with `gh pr checks <pr> --watch --interval 30` and a 10-minute command timeout. The runs happen in parallel on GitHub, so later waits return quickly.
- Settle each PR as the ship procedure's step 10 says. Only a fully green PR with an APPROVE on its head becomes ready.

## Stage 4: Report

1. Run `${CLAUDE_SKILL_DIR}/../status/scripts/status.py <all issue numbers>` and show its output unchanged.
2. Below it, list every issue that stopped, Blockers first: issue, stage, one-line reason, and the comment to read.
3. End with the cleanup command for finished worktrees: `git worktree list`, then `git worktree remove <path>` once a PR is merged.

## Rules

- Never merge, approve, enable auto-merge, rebase, or force-push.
- Never review an issue whose build did not end VERIFIED, and never ship one whose review is not APPROVE on its current head.
- Never edit code yourself in this skill. Fixes go through `/factory:build`, or a new batch.
- Never summarize a stage for the reviewer. Its task is the one sentence above.
