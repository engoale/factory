"""Run each hook as Claude Code does: JSON on stdin, decision on stdout, exit code."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HOOKS = Path(__file__).resolve().parent.parent / "hooks"
sys.path.insert(0, str(HOOKS))
from common import protected_match  # noqa: E402


def sh(cwd: Path, *args: str) -> None:
    subprocess.run(args, cwd=cwd, check=True, capture_output=True)


def run_hook(name: str, payload: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(HOOKS / name)], input=json.dumps(payload), capture_output=True, text=True
    )


class RepoTestCase(unittest.TestCase):
    """A fresh git repository on branch main with one commit."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name).resolve()
        sh(self.root, "git", "init", "-q", "-b", "main")
        sh(self.root, "git", "config", "user.email", "test@example.com")
        sh(self.root, "git", "config", "user.name", "test")
        (self.root / "README.md").write_text("x\n")
        sh(self.root, "git", "add", ".")
        sh(self.root, "git", "commit", "-q", "-m", "init")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def write(self, relative: str, content: str) -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)


class ProtectedMatchTest(unittest.TestCase):
    patterns = [".env*", "!.env.example", "deploy/", "src/db/schema.py", "*.pem"]

    def test_matches(self) -> None:
        cases = {
            ".env": ".env*",
            ".env.local": ".env*",
            "deploy/fly.toml": "deploy/",
            "deploy/a/b.yml": "deploy/",
            "src/db/schema.py": "src/db/schema.py",
            "certs/key.pem": "*.pem",
        }
        for path, pattern in cases.items():
            with self.subTest(path=path):
                self.assertEqual(protected_match(path, self.patterns), pattern)

    def test_does_not_match(self) -> None:
        for path in [".env.example", "deployer.py", "src/db/other.py", "README.md"]:
            with self.subTest(path=path):
                self.assertIsNone(protected_match(path, self.patterns))


class ProtectPathsTest(RepoTestCase):
    def edit(self, relative: str) -> subprocess.CompletedProcess:
        return run_hook("protect_paths.py", {
            "cwd": str(self.root), "tool_name": "Edit",
            "tool_input": {"file_path": str(self.root / relative)},
        })

    def test_asks_for_protected_path(self) -> None:
        self.write(".factory.json", json.dumps({"protectedPaths": ["deploy/"]}))
        result = self.edit("deploy/app.yml")
        self.assertEqual(result.returncode, 0)
        decision = json.loads(result.stdout)["hookSpecificOutput"]
        self.assertEqual(decision["permissionDecision"], "ask")
        self.assertIn("deploy/app.yml", decision["permissionDecisionReason"])

    def test_silent_for_other_paths(self) -> None:
        self.write(".factory.json", json.dumps({"protectedPaths": ["deploy/"]}))
        result = self.edit("src/app.py")
        self.assertEqual((result.returncode, result.stdout), (0, ""))

    def test_silent_without_config(self) -> None:
        self.assertEqual(self.edit("deploy/app.yml").stdout, "")

    def test_silent_outside_project(self) -> None:
        self.write(".factory.json", json.dumps({"protectedPaths": ["*"]}))
        result = run_hook("protect_paths.py", {
            "cwd": str(self.root), "tool_name": "Write", "tool_input": {"file_path": "/tmp/elsewhere.txt"},
        })
        self.assertEqual(result.stdout, "")

    def test_invalid_config_is_a_notice_not_a_block(self) -> None:
        self.write(".factory.json", "{not json")
        result = self.edit("deploy/app.yml")
        self.assertEqual(result.returncode, 1)
        self.assertIn("not valid JSON", result.stderr)

    def test_unknown_key_is_rejected(self) -> None:
        self.write(".factory.json", json.dumps({"protectedPath": ["deploy/"]}))
        self.assertIn("unknown keys", self.edit("deploy/app.yml").stderr)


class GuardGitTest(RepoTestCase):
    def bash(self, command: str) -> str | None:
        result = run_hook("guard_git.py", {
            "cwd": str(self.root), "tool_name": "Bash", "tool_input": {"command": command},
        })
        self.assertEqual(result.returncode, 0, result.stderr)
        if not result.stdout:
            return None
        return json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"]

    def test_denies(self) -> None:
        sh(self.root, "git", "switch", "-q", "-c", "feat/1-x")
        for command in [
            "git push --force",
            "git push -f origin feat/1-x",
            "git push -uf origin feat/1-x",
            "git push --force-with-lease",
            "git push origin +feat/1-x",
            "git push origin main",
            "git push origin feat/1-x:main",
            "git push origin HEAD:refs/heads/main",
            "git push --all",
            "make lint && git push origin main",
            "GIT_TRACE=1 git -C . push origin main",
        ]:
            with self.subTest(command=command):
                self.assertEqual(self.bash(command), "deny")

    def test_denies_bare_push_on_default_branch(self) -> None:
        self.assertEqual(self.bash("git push"), "deny")

    def test_allows(self) -> None:
        sh(self.root, "git", "switch", "-q", "-c", "feat/1-x")
        for command in [
            "git push",
            "git push -u origin feat/1-x",
            "git push -o ci.skip origin feat/1-x",
            "git status",
            "echo git push --force",
            "gh pr create --title push",
        ]:
            with self.subTest(command=command):
                self.assertIsNone(self.bash(command))


class StopGateTest(RepoTestCase):
    def makefile(self, lint_exit: int) -> None:
        self.write("Makefile", f"lint:\n\t@echo lint-ran >> .lint-log; echo 'E1 bad thing'; exit {lint_exit}\n")
        (self.root / ".gitignore").write_text(".lint-log\n")
        sh(self.root, "git", "add", ".")
        sh(self.root, "git", "commit", "-q", "-m", "makefile")

    def stop(self, active: bool = False, mode: str = "default") -> subprocess.CompletedProcess:
        return run_hook("stop_gate.py", {
            "cwd": str(self.root), "hook_event_name": "Stop",
            "stop_hook_active": active, "permission_mode": mode,
        })

    def lint_runs(self) -> int:
        log = self.root / ".lint-log"
        return len(log.read_text().splitlines()) if log.exists() else 0

    def test_skips_clean_tree(self) -> None:
        self.makefile(lint_exit=1)
        self.assertEqual(self.stop().returncode, 0)
        self.assertEqual(self.lint_runs(), 0)

    def test_skips_without_lint_target(self) -> None:
        self.write("new.py", "x = 1\n")
        self.assertEqual(self.stop().returncode, 0)

    def test_skips_in_plan_mode(self) -> None:
        self.makefile(lint_exit=1)
        self.write("new.py", "x = 1\n")
        self.assertEqual(self.stop(mode="plan").returncode, 0)

    def test_passes_and_caches(self) -> None:
        self.makefile(lint_exit=0)
        self.write("new.py", "x = 1\n")
        self.assertEqual(self.stop().returncode, 0)
        self.assertEqual(self.stop().returncode, 0)
        self.assertEqual(self.lint_runs(), 1)
        self.write("new.py", "x = 2\n")
        self.assertEqual(self.stop().returncode, 0)
        self.assertEqual(self.lint_runs(), 2)

    def test_blocks_on_failure_with_output(self) -> None:
        self.makefile(lint_exit=1)
        self.write("new.py", "x = 1\n")
        result = self.stop()
        self.assertEqual(result.returncode, 2)
        self.assertIn("attempt 1/3", result.stderr)
        self.assertIn("E1 bad thing", result.stderr)

    def test_gives_up_after_three_blocks(self) -> None:
        self.makefile(lint_exit=1)
        self.write("new.py", "x = 1\n")
        codes = [self.stop().returncode] + [self.stop(active=True).returncode for _ in range(3)]
        self.assertEqual(codes, [2, 2, 2, 0])
        self.assertEqual(self.stop().returncode, 2)  # A fresh stop starts a new count.


class SessionStartTest(RepoTestCase):
    def test_injects_contract_and_settings(self) -> None:
        self.write(".factory.json", json.dumps({"protectedPaths": ["deploy/", ".env*"]}))
        result = run_hook("session_start.py", {"cwd": str(self.root), "source": "startup"})
        self.assertEqual(result.returncode, 0)
        self.assertIn("<factory-contract>", result.stdout)
        self.assertIn("## Workflow", result.stdout)
        self.assertIn("deploy/, .env*", result.stdout)
        self.assertIn("lacks targets ci, lint", result.stdout)
        self.assertLess(len(result.stdout), 10_000)

    def test_reports_broken_config(self) -> None:
        self.write(".factory.json", "[]")
        result = run_hook("session_start.py", {"cwd": str(self.root)})
        self.assertIn("must be a JSON object", result.stdout)


if __name__ == "__main__":
    unittest.main()
