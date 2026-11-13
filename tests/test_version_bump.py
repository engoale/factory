"""The version-bump check: shipped changes must raise the plugin version."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "check_version_bump.py"
spec = importlib.util.spec_from_file_location("check_version_bump", SCRIPT)
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)


class ProblemTest(unittest.TestCase):
    def test_shipped_change_without_bump_fails(self) -> None:
        message = check.problem(["skills/ship/SKILL.md"], "0.5.1", "0.5.1")
        self.assertIn("skills/ship/SKILL.md", message)
        self.assertIn("not above 0.5.1", message)

    def test_version_going_down_fails(self) -> None:
        self.assertIsNotNone(check.problem(["hooks/guard_git.py"], "0.5.1", "0.5.0"))

    def test_numeric_not_text_comparison(self) -> None:
        self.assertIsNone(check.problem(["agents/reviewer.md"], "0.9.0", "0.10.0"))

    def test_shipped_change_with_bump_passes(self) -> None:
        self.assertIsNone(check.problem(["rules/contract.md", "README.md"], "0.5.1", "0.6.0"))

    def test_docs_and_tests_need_no_bump(self) -> None:
        changed = ["README.md", "tests/test_hooks.py", "Makefile", ".github/workflows/ci.yml", "scripts/x.py"]
        self.assertIsNone(check.problem(changed, "0.5.1", "0.5.1"))


if __name__ == "__main__":
    unittest.main()
