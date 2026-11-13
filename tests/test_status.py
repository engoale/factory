"""The status board's decisions: CI state, comment parsing, next step, merge order."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "skills" / "status" / "scripts" / "status.py"
spec = importlib.util.spec_from_file_location("status", SCRIPT)
status = importlib.util.module_from_spec(spec)
sys.modules["status"] = status  # dataclasses look their module up here
spec.loader.exec_module(status)

HEAD = "abc1234" + "0" * 33


def row(**fields) -> "status.Row":
    defaults = dict(issue=1, branch="feat/1-x", pr=10, draft=True, head=HEAD, ci="green",
                    verified=True, review="APPROVE", review_commit=HEAD)
    defaults.update(fields)
    return status.Row(**defaults)


class CiStateTest(unittest.TestCase):
    def test_states(self) -> None:
        done = {"status": "completed", "conclusion": "success"}
        self.assertEqual(status.ci_state([]), "none")
        self.assertEqual(status.ci_state([dict(done, name="a")]), "green")
        self.assertEqual(status.ci_state([dict(done, name="a"), {"name": "b", "status": "in_progress"}]), "running")
        failing = [dict(done, name="Tests", conclusion="failure"), {"name": "Lint", "status": "in_progress"}]
        self.assertEqual(status.ci_state(failing), "failing: Tests")


class ReadCommentsTest(unittest.TestCase):
    def test_latest_review_wins_and_blocker_only_counts_when_last(self) -> None:
        r = status.Row(issue=1)
        status.read_comments(r, [
            {"body": "**Blocker:** need a decision"},
            {"body": "**Verification:**\n| a | MET |"},
            {"body": "**Review:**\n\n**Verdict:** CHANGES REQUESTED\n**Reviewed commit:** 1111111"},
            {"body": "**Review:**\n\n**Verdict:** APPROVE\n**Reviewed commit:** abc1234"},
            {"body": "Thanks, looks good"},
        ])
        self.assertEqual((r.verified, r.review, r.review_commit, r.blocked), (True, "APPROVE", "abc1234", False))

    def test_blocker_after_plan_blocks(self) -> None:
        r = status.Row(issue=1)
        status.read_comments(r, [{"body": "**Plan:** steps"}, {"body": "**Blocker:** which option?"}])
        self.assertTrue(r.blocked)


class NextStepTest(unittest.TestCase):
    def test_sequence(self) -> None:
        cases = [
            (dict(blocked=True), "answer the Blocker"),
            (dict(branch=None, pr=None), "build"),
            (dict(verified=False), "build (verify)"),
            (dict(review=None), "review"),
            (dict(review_commit="9999999"), "review"),
            (dict(review="CHANGES REQUESTED"), "fix, then review"),
            (dict(review="INCOMPLETE"), "review inputs broken (factory bug)"),
            (dict(pr=None, head=None), "ship"),
            (dict(ci="failing: Tests"), "fix CI"),
            (dict(ci="running"), "wait for CI"),
            (dict(draft=True), "ship (mark ready)"),
            (dict(draft=False), "merge"),
        ]
        for fields, expected in cases:
            with self.subTest(fields=fields):
                self.assertEqual(status.next_step(row(**fields)), expected)


class MergeOrderTest(unittest.TestCase):
    def test_independent_first_then_broadest_in_each_group(self) -> None:
        files = {
            101: {"a.py"},
            102: {"x.py", "y.py", "z.py"},
            103: {"x.py"},
            104: {"y.py", "z.py"},
            105: {"q.py"},
            106: {"q.py", "r.py"},
        }
        self.assertEqual(
            status.merge_order(files),
            [(101, []), (102, [103, 104]), (104, [102]), (103, [102]), (106, [105]), (105, [106])],
        )


class RepoFromRemoteTest(unittest.TestCase):
    def test_formats(self) -> None:
        for url in ["https://github.com/engoale/speak.git", "git@github.com:engoale/speak.git",
                    "https://github.com/engoale/speak", "ssh://git@github.com/engoale/speak.git\n"]:
            with self.subTest(url=url):
                self.assertEqual(status.repo_from_remote(url), "engoale/speak")
        self.assertIsNone(status.repo_from_remote("https://gitlab.com/engoale/speak.git"))


if __name__ == "__main__":
    unittest.main()
