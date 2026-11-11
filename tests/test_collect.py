"""The review collector's scanner: flags silenced checks and removed tests."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "skills" / "review" / "scripts" / "collect.py"
spec = importlib.util.spec_from_file_location("collect", SCRIPT)
collect = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collect)


def added(path: str, *lines: str, start: int = 10) -> str:
    body = "\n".join(f"+{line}" for line in lines)
    return f"--- a/{path}\n+++ b/{path}\n@@ -9,0 +{start},{len(lines)} @@\n{body}\n"


class ScanTest(unittest.TestCase):
    def test_flags_suppressions_with_location(self) -> None:
        cases = [
            "    _ = x",
            "import os  # noqa: F401",
            "    return 1  # type: ignore[return-value]",
            "@pytest.mark.skip(reason='flaky')",
            "    except Exception:",
            "    except:",
            "    except (Exception, KeyError) as error:",
            "    except ValueError as error: pass",
            "// eslint-disable-next-line",
            "fail_under = 50",
            "  } catch (e) {}",
        ]
        for line in cases:
            with self.subTest(line=line):
                self.assertEqual(collect.scan(added("src/a.py", line)), [f"src/a.py:10: added: {line.strip()}"])

    def test_ignores_ordinary_code(self) -> None:
        diff = added(
            "src/a.py",
            "def add_one(value: int) -> int:",
            "    _, rest = split(value)",
            "    except ValueError as error:",
            "        raise ConfigError(str(error)) from error",
        )
        self.assertEqual(collect.scan(diff), [])

    def test_counts_line_numbers_across_hunks(self) -> None:
        diff = (
            "--- a/src/a.py\n+++ b/src/a.py\n"
            "@@ -1,0 +2,2 @@\n+ok = 1\n+bad = 2  # noqa\n"
            "@@ -20,0 +40 @@\n+    _ = unused\n"
        )
        self.assertEqual(collect.scan(diff), ["src/a.py:3: added: bad = 2  # noqa", "src/a.py:40: added: _ = unused"])

    def test_flags_removed_test_lines_only_in_test_files(self) -> None:
        diff = (
            "--- a/tests/unit/test_a.py\n+++ b/tests/unit/test_a.py\n"
            "@@ -5,2 +4,0 @@\n-def test_rejects_empty():\n-    assert parse('') is None\n"
            "--- a/src/a.py\n+++ b/src/a.py\n@@ -5 +4,0 @@\n-    assert value > 0\n"
        )
        self.assertEqual(
            collect.scan(diff),
            [
                "tests/unit/test_a.py: removed test line: def test_rejects_empty():",
                "tests/unit/test_a.py: removed test line: assert parse('') is None",
            ],
        )

    def test_new_file(self) -> None:
        diff = "--- /dev/null\n+++ b/src/new.py\n@@ -0,0 +1,2 @@\n+x = 1\n+y = 2  # noqa\n"
        self.assertEqual(collect.scan(diff), ["src/new.py:2: added: y = 2  # noqa"])


class ProtectedTest(unittest.TestCase):
    def test_lists_touched_protected_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".factory.json").write_text(json.dumps({"protectedPaths": ["deploy/", "!deploy/README.md"]}))
            files = ["deploy/fly.toml", "deploy/README.md", "src/a.py"]
            self.assertEqual(collect.protected(files, root), ["deploy/fly.toml  (protected by deploy/)"])

    def test_reports_broken_config_instead_of_failing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".factory.json").write_text("{")
            self.assertIn("could not read protected paths", collect.protected(["a"], root)[0])


if __name__ == "__main__":
    unittest.main()
