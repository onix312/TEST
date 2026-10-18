"""Focused tests; intentionally not executed in the current implementation pass."""
import tempfile
import unittest
import zipfile
from pathlib import Path

from office_core import validate_project, prepare, ProjectStore
from agents import codex_args
from safety import checkpoint
from workspaces import provision, compute_changes, inspect_conflicts, integrate


class ProjectTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        (self.root / "Assets").mkdir()
        (self.root / "Packages").mkdir()
        (self.root / "ProjectSettings").mkdir()
        (self.root / "Assets" / "Test.cs").write_text("old", encoding="utf-8")

    def tearDown(self):
        self.temporary.cleanup()

    def test_project_and_gdd(self):
        self.assertEqual(validate_project(str(self.root)), self.root)
        store = ProjectStore(self.root)
        store.approve_gdd("# Approved")
        self.assertIn("Approved", store.gdd())
        first = store.add("Write movement")
        second = store.add("Write interaction", depends=[first["id"]])
        self.assertEqual(second["depends"], [first["id"]])
        self.assertEqual(len(list(store.eligible())), 1)

    def test_checkpoint_contains_original(self):
        with zipfile.ZipFile(checkpoint(self.root)) as archive:
            self.assertEqual(archive.read("Assets/Test.cs"), b"old")

    def test_copy_and_merge(self):
        prepare(self.root)
        workspace = provision(self.root, "a1", "# GDD")
        self.assertEqual((workspace / "Assets" / "Test.cs").read_text(), "old")
        (workspace / "Assets" / "Test.cs").write_text("new", encoding="utf-8")
        changed = compute_changes(self.root, "a1")
        self.assertEqual(len(changed), 1)
        self.assertFalse(inspect_conflicts(self.root, changed))
        backup, conflicts = integrate(self.root, "a1", changed)
        self.assertFalse(conflicts)
        self.assertIsNotNone(backup)
        self.assertEqual((self.root / "Assets" / "Test.cs").read_text(), "new")

    def test_conflicting_changes_do_not_merge(self):
        prepare(self.root)
        workspace = provision(self.root, "a2", "# GDD")
        (workspace / "Assets" / "Test.cs").write_text("agent", encoding="utf-8")
        (self.root / "Assets" / "Test.cs").write_text("human", encoding="utf-8")
        changes = compute_changes(self.root, "a2")
        self.assertTrue(inspect_conflicts(self.root, changes))
        _, conflicts = integrate(self.root, "a2", changes)
        self.assertTrue(conflicts)
        self.assertEqual((self.root / "Assets" / "Test.cs").read_text(), "human")

    def test_codex_no_git(self):
        args = codex_args("codex", self.root, "Write code")
        self.assertIn("--skip-git-repo-check", args)
        self.assertEqual(args[-1], "-")


if __name__ == "__main__":
    unittest.main()
