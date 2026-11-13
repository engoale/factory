# Development Contract

Universal rules: they apply to any project. Project-specific facts live in the project's `CLAUDE.md`.
The factory plugin loads this file at session start. Keep it free of project names and stack details.

## Behavior

1. **Think:** State assumptions, present options, ask when unclear.
2. **Simplicity:** Minimum code, no speculation, no single-use abstractions.
3. **Surgical:** Touch only what the task needs. Remove only the orphans you created.
4. **Goal-driven:** Define a verifiable success criterion before starting.
5. **Verify, don't guess:** Read the code or run the command instead of assuming.
6. **Plain output:** No sycophantic language, emojis, or em dashes.

## Workflow

Follow these four stages for every task beyond a trivial fix.

### 1. Spec (GitHub issue)

- Write no implementation code until the spec is clear and approved.
- The GitHub issue is the spec. Read the full body before starting.
- A spec is complete when it has: problem, goal, acceptance criteria, what is out of scope, and one end-to-end check that proves the feature works.
- If the issue is unclear or incomplete, ask before proceeding.

### 2. Plan

- Explore in plan mode before editing. Map the files and interfaces the change touches.
- Present a sequential checklist before execution.
- If the plan differs significantly from the issue, post a comment and wait for approval.
- Skip the plan when the diff can be described in one sentence.

### 3. Build

- One issue, one branch, one pull request.
- Branch name: `<type>/<issue-number>-<short-slug>`, for example `fix/142-token-refresh`.
- Never push to the default branch. Never force-push, and never rebase a branch that is already pushed.
- To bring the default branch into a pushed branch, merge it in: `git merge origin/<default>`. With squash merging, those merge commits never reach the default branch.
- Implement one logical component at a time.
- Bug fixes start with a failing test that reproduces the bug, then the fix.
- Commit messages follow Conventional Commits: `<type>(<scope>): <description>`.
- Check off the issue's task boxes as you complete them.

### 4. Verify (definition of done)

- `make lint` and `make ci` pass with zero warnings. These are the project's contract.
- Coverage does not drop below the threshold the project enforces in `make ci`.
- Show evidence: paste the command you ran and its output. Do not assert success.
- A reviewer in a fresh context checks the diff against the issue before merge. The session that wrote the code does not grade it.
- Update the issue: mark the boxes and post a final summary comment if needed.

## Coding standards

### Architecture

- **Separation of concerns:** Keep business logic independent of UI, transport, and persistence.
- **Deterministic state:** Avoid shared mutable state. Prefer pure functions and explicit data flow.
- **Defensive boundaries:** Validate every external input (API payloads, user input, config files) with a schema before processing.

### Style

- **Readability over brevity:** Clear names, shallow nesting, nothing clever.
- **Explicit errors:** Never swallow an error or leave a catch block empty. Propagate typed errors.
- **Comments:** Explain why, not what. Comment only non-obvious optimizations, formulas, and intentional workarounds.

## Constraints

- **No ad-hoc dependencies:** Do not add a third-party package without discussing the trade-offs and getting explicit approval.
- **Breaking changes:** Flag immediately any change that breaks database schemas, local configuration, or downstream APIs.
- **No hardcoded environment:** Never hardcode secrets, local paths, or credentials. Use environment variables or the project's config loader.
- **Protected paths:** Do not edit the paths listed in the project's `.factory.json` without asking first. A hook enforces this for file edits.

## Issue comment policy

Document decisions, findings, and blockers as issue comments during implementation.

```markdown
**[TYPE]:** Brief title

[1-2 sentence context]

**Decision/Finding/Blocker:** [What specifically]
**Rationale:** [Why]
**Impact:** [Consequences, if any]
```

Types:

- `Decision:` A design choice that differs from the original plan.
- `Finding:` A discovery that affects implementation, for example "library doesn't support X".
- `Blocker:` A showstopper that needs user input.
- `Spec Change:` A modification to the original issue specification.

Rules: 3 to 5 sentences. Name specific files and functions. State the next step or impact. No background lectures or apologies.

## Session hygiene

- **Two-strike rule:** If the same correction has been made twice in one session, stop and recommend a fresh session with a better prompt.
- **Learning loop:** When a mistake repeats across sessions, propose a new rule here or, better, a hook that enforces it.

<!-- OPENWIKI:START -->
