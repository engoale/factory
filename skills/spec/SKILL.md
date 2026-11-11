---
name: spec
description: Turn a feature idea or bug report into an approved GitHub issue that serves as the spec. Interviews the user, drafts the issue, and creates it only after approval.
argument-hint: "[short description of the feature or bug]"
disable-model-invocation: true
allowed-tools: Bash(gh issue create *) Bash(gh label list *)
---

Write a spec for: $ARGUMENTS

The GitHub issue is the spec. Nothing gets built until it is complete and approved.

## Steps

1. **Explore, read-only.** Read only the code needed to ask good questions: the files and interfaces this idea touches. Do not edit anything.
2. **Interview.** Ask with the AskUserQuestion tool, at most 4 questions per round. Skip anything the code already answers. Dig into the hard parts: edge cases, failure modes, trade-offs, what is out of scope. Keep going until every section of the template can be filled without guessing.
3. **Draft.** Fill [issue-template.md](issue-template.md). Show the full draft in the reply.
4. **Approve.** Ask the user to approve or edit. Apply edits and show the new draft. Repeat until approved.
5. **Create.** Only after explicit approval, run `gh issue create --title "<title>" --body-file <tmp file>`. Add an existing label only if one clearly fits (`gh label list`).
6. **Report.** Reply with the issue URL and the next command: `/factory:build <number>`.

## Rules

- Title follows Conventional Commits style: `<type>(<scope>): <description>`.
- Every acceptance criterion must be checkable by running something or observing something. Rewrite vague ones ("works well", "is fast") into measurable ones.
- The end-to-end check is one concrete procedure that proves the whole feature works.
- Do not include implementation details the user did not ask for. The plan comes later.
