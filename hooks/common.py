"""Shared helpers for the factory hooks. Standard library only, Python 3.9+."""

from __future__ import annotations

import fnmatch
import json
import os
import re
import subprocess
import sys
from pathlib import Path

CONFIG_FILE = ".factory.json"
CONFIG_KEYS = {"protectedPaths"}


class ConfigError(Exception):
    """The project's .factory.json is missing required structure."""


def read_input() -> dict:
    raw = sys.stdin.read()
    return json.loads(raw) if raw.strip() else {}


def git(root: Path | str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)


def project_root(data: dict) -> Path | None:
    """Git top-level of the hook's working directory, or None outside a repository.

    Uses the input's cwd rather than CLAUDE_PROJECT_DIR, because the latter does
    not follow Claude into a worktree.
    """
    cwd = data.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    result = git(cwd, "rev-parse", "--show-toplevel")
    return Path(result.stdout.strip()) if result.returncode == 0 else None


def load_config(root: Path) -> dict:
    path = root / CONFIG_FILE
    if not path.is_file():
        return {}
    try:
        config = json.loads(path.read_text())
    except json.JSONDecodeError as error:
        raise ConfigError(f"{CONFIG_FILE} is not valid JSON: {error}") from error
    if not isinstance(config, dict):
        raise ConfigError(f"{CONFIG_FILE} must be a JSON object")
    unknown = set(config) - CONFIG_KEYS
    if unknown:
        raise ConfigError(f"{CONFIG_FILE} has unknown keys: {sorted(unknown)}")
    patterns = config.get("protectedPaths", [])
    if not isinstance(patterns, list) or not all(isinstance(p, str) and p for p in patterns):
        raise ConfigError(f"{CONFIG_FILE}: protectedPaths must be a list of non-empty strings")
    return config


def make_targets(root: Path) -> set[str]:
    makefile = root / "Makefile"
    if not makefile.is_file():
        return set()
    target = re.compile(r"^([A-Za-z0-9_.-]+)\s*:(?!=)")
    return {m.group(1) for line in makefile.read_text().splitlines() if (m := target.match(line))}


def default_branch(root: Path) -> str:
    """Default branch from local refs only, so hooks stay fast and work offline."""
    result = git(root, "symbolic-ref", "--short", "refs/remotes/origin/HEAD")
    if result.returncode == 0:
        return result.stdout.strip().removeprefix("origin/")
    for candidate in ("main", "master"):
        if git(root, "rev-parse", "--verify", "--quiet", f"refs/heads/{candidate}").returncode == 0:
            return candidate
    return "main"


def protected_match(relative_path: str, patterns: list[str]) -> str | None:
    """Return the pattern that protects the path, or None.

    gitignore-like rules: the last matching pattern wins, and "!pattern"
    un-protects. "dir/" protects everything under dir. A pattern without "/"
    also matches the file name in any directory.
    """
    matched: str | None = None
    name = relative_path.rsplit("/", 1)[-1]
    for raw in patterns:
        negate = raw.startswith("!")
        pattern = raw[1:] if negate else raw
        if pattern.endswith("/"):
            hit = relative_path.startswith(pattern)
        elif "/" in pattern:
            hit = fnmatch.fnmatchcase(relative_path, pattern)
        else:
            hit = fnmatch.fnmatchcase(relative_path, pattern) or fnmatch.fnmatchcase(name, pattern)
        if hit:
            matched = None if negate else raw
    return matched


def emit(payload: dict) -> None:
    print(json.dumps(payload))
