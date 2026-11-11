---
name: check
description: Run the project's contract (make lint, make ci) and report pass or fail with evidence. Use before claiming any work is done.
---

Verify the current state of the project against its contract.

1. Confirm a Makefile exists with `lint` and `ci` targets. If either is missing, stop and say which one.
2. Run `make lint`. Then run `make ci`, even if lint failed.
3. Report in this format:
   - **lint:** PASS or FAIL
   - **ci:** PASS or FAIL
   - **coverage:** the total percentage, if printed
   - **warnings:** the count, if printed
   - **evidence:** the last 15 lines of output from each command, verbatim
4. If anything failed, list each failure with its file and line. Do not fix anything unless asked.

Never report PASS without having run the command in this session.
