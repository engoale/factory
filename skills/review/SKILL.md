---
name: review
description: Independent review of the current branch against its issue by a reviewer subagent that never saw this conversation. Posts the verdict on the issue. Run after /factory:build and before /factory:ship.
argument-hint: "[issue-number]"
disable-model-invocation: true
allowed-tools: Bash(${CLAUDE_SKILL_DIR}/scripts/collect.py *) Bash(git status *) Bash(git branch *) Bash(gh issue comment *)
---

Get an independent review of the current branch.

## Steps

1. **Find the issue.** Use `$ARGUMENTS` if given. Otherwise read the number from the branch name (`git branch --show-current`, format `<type>/<number>-<slug>`). If neither works, ask.
2. **Gate on the tree.** Run `git status --short`. If there are uncommitted changes, stop: the review covers committed code only.
3. **Collect.** Run `${CLAUDE_SKILL_DIR}/scripts/collect.py <number>` with a 10-minute command timeout: it runs `make lint` and `make ci` itself. It prints a directory and a one-line summary.
4. **Review.** Invoke the `factory:reviewer` subagent and wait for its result. Its task is exactly this sentence and nothing else:

   `Review the change prepared in <directory>.`

   Do not add a summary, context, your opinion, or anything from this conversation. The reviewer's independence is the point of this skill.
5. **Post.** Write `**Review:**` followed by a blank line and the reviewer's output, unchanged, to a temp file. Run `gh issue comment <number> --body-file <file>`.
6. **Report.** Reply with the reviewer's output unchanged, then the next step:
   - **APPROVE:** `/factory:ship`
   - **CHANGES REQUESTED:** fix each BLOCKING finding and unmet criterion, commit, then run `/factory:review` again.
   - **INCOMPLETE:** the review inputs are broken. Show what is missing; this is a factory bug, not a problem with the branch.

## Rules

- Never edit code in this skill.
- Never filter, soften, or argue with the reviewer's output before posting it. If you believe a finding is wrong, say so to the user after posting, with evidence. The user decides.
