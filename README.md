# factory

A project-agnostic Claude Code plugin that runs a spec, build, verify, ship workflow on any repository.

## Workflow

| Command | What it does | Side effects |
|---|---|---|
| `/factory:spec <idea>` | Interviews you and drafts a GitHub issue as the spec | Creates the issue after you approve |
| `/factory:build <issue>` | Branches, plans, implements, and verifies the issue | Local commits only |
| `/factory:check` | Runs the project's contract and reports with evidence | None |
| `/factory:ship` | Verifies, pushes, and opens a pull request | Push and PR, never merges |

## Project contract

A project works with this plugin when it has:

- A `Makefile` with `lint` and `ci` targets that exit non-zero on failure
- A GitHub remote and the `gh` CLI signed in

## Try it

```bash
claude plugin validate ./factory
cd your-project && claude --plugin-dir ../factory
```

## Roadmap

- Phase 3: hooks (format on edit, contract before stop, protected paths, inject `AGENTS.md`)
- Phase 4: fresh-context reviewer subagent
- Phase 5: marketplace and permanent install
