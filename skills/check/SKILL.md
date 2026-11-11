---
name: check
description: Run the project's contract (make lint, make ci) and report pass or fail with verbatim evidence. Use before claiming any work is done, and whenever asked whether the project passes.
allowed-tools: Bash(${CLAUDE_SKILL_DIR}/scripts/run.sh *)
---

Verify the current state of the project against its contract. This skill only reports. It never edits files.

## Steps

1. Confirm a Makefile exists with `lint` and `ci` targets. If either is missing, stop and say which one.
2. Run `${CLAUDE_SKILL_DIR}/scripts/run.sh lint`.
3. Run `${CLAUDE_SKILL_DIR}/scripts/run.sh ci`, even if lint failed.
4. Reply with the output of both runs, each in its own fenced code block, copied exactly. The script already extracts status, coverage, warnings, and the last 15 lines.
5. If anything failed, read the full log the script names and add a **Failures** list: one line per failure with file, line, and error message.

## Rules

- The script output is the report. Do not retype, reorder, or summarize it.
- Never report PASS for a command you did not run in this invocation.
- Do not fix anything, even trivially. Do not add conclusions or claims about earlier work.
