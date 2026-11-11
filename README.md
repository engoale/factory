# factory

A project-agnostic Claude Code plugin that runs a spec, build, verify, ship workflow on any repository, with hooks that enforce the rules prose cannot.

## Workflow

| Command | What it does | Side effects |
|---|---|---|
| `/factory:spec <idea>` | Interviews you and drafts a GitHub issue as the spec | Creates the issue after you approve |
| `/factory:build <issue>` | Branches, plans, implements, verifies every acceptance criterion | Local commits, issue checkboxes and a Verification comment |
| `/factory:check` | Runs the project's contract and reports with evidence | None |
| `/factory:review [issue]` | Independent review by a subagent that never saw the conversation | Review comment on the issue |
| `/factory:ship` | Gates on check, criteria and an approved review of the exact commit, pushes, opens a pull request | Push and PR, never merges |

Order: `spec`, `build`, `review`, `ship`. `check` runs inside `build` and `ship`, and on its own whenever you want.

## Reviewer

`agents/reviewer.md` has only Read, Grep and Glob, so it cannot change anything. It never receives a summary from the session that wrote the code: `skills/review/scripts/collect.py` writes the issue, the diff, the contract, suspicious lines (silenced checks, removed tests) and touched protected paths into `.git/factory/review/`, and the reviewer gets only that path. It checks acceptance criteria against tests, silenced checks, demonstrable bugs, scope, and the contract, and is told that no findings is a valid outcome.

## Hooks

| Hook | When | What it enforces |
|---|---|---|
| `session_start` | Session start, `/clear`, compaction | Loads [rules/contract.md](rules/contract.md) and the project's protected paths into context |
| `protect_paths` | Before Edit, Write, NotebookEdit | Asks before editing a path listed in `.factory.json` |
| `guard_git` | Before Bash | Denies force-pushes and pushes to the default branch |
| `stop_gate` | When Claude finishes | Uncommitted changes must pass `make format` (if present) and `make lint`; gives up after 3 attempts |

`guard_git` is a guardrail against mistakes, not a security boundary.

## Project contract

A project works with this plugin when it has:

- A `Makefile` with `lint` and `ci` targets that exit non-zero on failure (`format` is optional)
- A GitHub remote and the `gh` CLI signed in
- `python3` (3.9+) on the PATH where Claude Code runs

Optional `.factory.json` at the project root:

```json
{
  "protectedPaths": [".env*", "!.env.example", "deploy/", "src/db/schema.py"]
}
```

Patterns follow gitignore rules: `dir/` covers everything below it, a pattern without `/` matches a file name anywhere, `!` un-protects, and the last match wins.

## Develop

```bash
make ci                                  # the factory follows its own contract
claude plugin validate .
cd your-project && claude --plugin-dir ../factory
```

## Roadmap

- Phase 5: marketplace and permanent install
