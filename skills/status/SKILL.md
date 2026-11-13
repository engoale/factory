---
name: status
description: Show where each factory issue stands (PR, draft, CI, verification, review, next step) and the order to merge open PRs in. Read-only. Use whenever asked what is in progress, what to merge next, or how a batch is going.
argument-hint: "[issue ...]"
allowed-tools: Bash(${CLAUDE_SKILL_DIR}/scripts/status.py *) Bash(${CLAUDE_SKILL_DIR}/scripts/status.py)
---

Run `${CLAUDE_SKILL_DIR}/scripts/status.py $ARGUMENTS` with a 5-minute command timeout and reply with its output unchanged.

With no arguments it covers every open pull request whose branch is `<type>/<number>-<slug>`.

Then add at most three lines: the issues waiting on the user (a Blocker to answer, a PR to merge), in that order. Do not run any other command and do not act on the next steps.
