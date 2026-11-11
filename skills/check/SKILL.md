---
name: check
description: Run the project's contract (make lint, make ci) and report pass or fail with verbatim evidence. Use before claiming any work is done, and whenever asked whether the project passes.
allowed-tools: Bash(make lint) Bash(make ci)
---

Verify the current state of the project against its contract. This skill only reports. It never edits files.

## Steps

1. Confirm a Makefile exists with `lint` and `ci` targets. If either is missing, stop and say which one.
2. Run `make lint`. Then run `make ci`, even if lint failed.
3. Report using exactly the format below, and nothing else.

## Report format

```
lint:     PASS | FAIL
ci:       PASS | FAIL
coverage: <total %> | not printed
warnings: <count>   | not printed
```

Then two fenced code blocks, one per command, each holding the last 15 lines of its output copied verbatim. Do not summarize, reorder, or reword the output.

If anything failed, add a **Failures** list: one line per failure with file, line, and the error message.

## Rules

- Never report PASS for a command you did not run in this invocation.
- Do not fix anything, even trivially. Do not add conclusions, explanations, or claims about earlier work.
- A command that cannot start (missing tool, environment error) is FAIL. Quote the error.
