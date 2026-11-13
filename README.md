# factory

A project-agnostic Claude Code plugin that runs a spec, build, verify, ship workflow on any repository, with hooks that enforce the rules prose cannot.

## Workflow

| Command | What it does | Side effects |
|---|---|---|
| `/factory:spec <idea>` | Interviews you and drafts a GitHub issue as the spec | Creates the issue after you approve |
| `/factory:build <issue>` | Branches, plans, implements, verifies every acceptance criterion | Local commits, issue checkboxes and a Verification comment |
| `/factory:check` | Runs the project's contract and reports with evidence | None |
| `/factory:review [issue]` | Independent review by a subagent that never saw the conversation | Review comment on the issue |
| `/factory:ship` | Gates on check, criteria and an approved review of the exact commit, pushes, opens or updates a draft PR, waits for CI, marks it ready only when green | Push and PR, never merges |

Order: `spec`, `build`, `review`, `ship`. `check` runs inside `build` and `ship`, and on its own whenever you want.

## Reviewer

`agents/reviewer.md` has only Read, Grep and Glob, so it cannot change anything. It never receives a summary from the session that wrote the code: `skills/review/scripts/collect.py` writes the issue, the diff, the contract, suspicious lines (silenced checks, removed tests), touched protected paths, `make lint` and `make ci` output run at the reviewed commit, and the PR's CI results for that commit into `.git/factory/review/`, and the reviewer gets only that path. Criteria that only CI can prove are "pending CI" and never block the review; `ship` keeps the PR a draft until CI is green. It checks acceptance criteria against tests, silenced checks, demonstrable bugs, scope, and the contract, and is told that no findings is a valid outcome.

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

## Install

The repository is its own marketplace (`engoale`), listed in `.claude-plugin/marketplace.json`.

**In one project, for everyone who clones it** (recommended). Commit this as the project's `.claude/settings.json`:

```json
{
  "extraKnownMarketplaces": {
    "engoale": {
      "source": { "source": "github", "repo": "engoale/factory" },
      "autoUpdate": true
    }
  },
  "enabledPlugins": {
    "factory@engoale": true
  }
}
```

Claude Code registers the marketplace once you trust the folder, and installs the plugin at the next session start.

**For yourself, in every project:**

```bash
claude plugin marketplace add engoale/factory
claude plugin install factory@engoale --scope user
```

On Claude Code 2.1.275 or later, `/plugin install factory --marketplace engoale/factory` does both in one step.

Check with `/plugin`: `factory@engoale` is listed and enabled.

## Updates

Installed copies are cached by version. A change reaches users only when `.claude-plugin/plugin.json`'s `version` goes up, which CI enforces on every pull request (`scripts/check_version_bump.py`).

- With `"autoUpdate": true`, Claude Code fetches new versions in the background. Third-party marketplaces have auto-update off by default.
- By hand: `claude plugin marketplace update engoale`, then `claude plugin update factory@engoale`, then `/reload-plugins`.

## Develop

```bash
make ci                                  # the factory follows its own contract
claude plugin validate .
cd your-project && claude --plugin-dir ../factory
```

A `--plugin-dir` copy overrides the installed `factory@engoale` for that session, so you can test changes without uninstalling.

Version numbers: bump the minor version for new behavior and the patch version for fixes. Docs, tests, CI and `scripts/` need no bump.
