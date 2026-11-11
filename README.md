# factory

A project-agnostic Claude Code plugin that runs a spec, build, verify, ship workflow on any repository, with hooks that enforce the rules prose cannot.

## Workflow

| Command | What it does | Side effects |
|---|---|---|
| `/factory:spec <idea>` | Interviews you and drafts a GitHub issue as the spec | Creates the issue after you approve |
| `/factory:build <issue>` | Branches, plans, implements, verifies every acceptance criterion | Local commits, issue checkboxes and a Verification comment |
| `/factory:check` | Runs the project's contract and reports with evidence | None |
| `/factory:ship` | Gates on check and criteria, pushes, opens a pull request | Push and PR, never merges |

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

- Phase 4: fresh-context reviewer subagent
- Phase 5: marketplace and permanent install
