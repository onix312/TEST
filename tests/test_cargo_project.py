"""Do Not Feed the Cargo approved baseline and orchestration-seeding tests."""
import tempfile
import unittest
from pathlib import Path

from office_core import ProjectStore
from cargo_project import (
    BASELINE_MARKER, DOCS, PLAN, activate_next_phase, approved_baseline,
    load_documents, seed_game_project,
)


class CargoProjectTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "unity"
        for name in ("Assets", "Packages", "ProjectSettings"):
            (self.root / name).mkdir(parents=True)
        self.store = ProjectStore(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def test_approved_design_package_has_all_100_unique_decisions(self):
        docs = load_documents()
        self.assertEqual(len(docs), len(DOCS) + 1)
        baseline = approved_baseline(docs)
        self.assertTrue(baseline.startswith(BASELINE_MARKER))
        self.assertIn("GDD-001", baseline)
        self.assertIn("GDD-100", baseline)
        self.assertIn("большая альфа", baseline.lower())

    def test_install_creates_gdd_references_and_task_dag_without_execution(self):
        result = seed_game_project(self.store)
        self.assertEqual(result["created"], len(PLAN))
        self.assertEqual(result["total"], len(PLAN))
        self.assertFalse(result["started"])
        self.assertEqual(len(self.store.tasks), len(PLAN))
        self.assertEqual(result["documents"], len(DOCS) + 1)
        self.assertIn("GDD-099", self.store.gdd())
        self.assertEqual(
            len(list((self.store.folder / "gdd" / "reference").iterdir())),
            len(DOCS) + 1)
        self.assertTrue(all(t["status"] == "queued" for t in self.store.tasks))
        self.assertTrue(all(t["paused"] for t in self.store.tasks))
        self.assertTrue(all(t["route"] == "codex" for t in self.store.tasks))
        self.assertTrue(all(t.get("gdd_refs") for t in self.store.tasks))
        self.assertEqual(list(self.store.eligible()), [])

    def test_idempotent_and_preserves_existing_task_state(self):
        seed_game_project(self.store)
        first = self.store.tasks[0]
        self.store.update(first["id"], status="merged", summary="Human-approved Unity test")
        second = seed_game_project(self.store)
        self.assertEqual(second["created"], 0)
        self.assertEqual(len(self.store.tasks), len(PLAN))
        self.assertEqual(first["status"], "merged")
        self.assertTrue(all(t["paused"] for t in self.store.tasks[1:]))

    def test_unlocks_only_next_milestone(self):
        seed_game_project(self.store)
        first = activate_next_phase(self.store)
        self.assertEqual(first["phase"], "P0")
        self.assertEqual(first["released"], 3)
        self.assertEqual(first["remaining"], 3)
        self.assertEqual([t["seed_key"] for t in self.store.eligible()], ["P0-CORE"])
        again = activate_next_phase(self.store)
        self.assertEqual(again["released"], 0)
        for task in self.store.tasks:
            if task["phase"] == "P0":
                self.store.update(task["id"], status="merged")
        following = activate_next_phase(self.store)
        self.assertEqual(following["phase"], "P1")
        self.assertEqual(following["released"], 3)
        self.assertTrue(all(t["paused"] for t in self.store.tasks if t["phase"] == "P2"))

    def test_release_requires_approved_baseline(self):
        with self.assertRaisesRegex(ValueError, "approved DFTC"):
            activate_next_phase(self.store)

    def test_refuses_to_override_other_approved_gdd(self):
        self.store.approve_gdd("# Another approved user's game")
        before = self.store.gdd()
        with self.assertRaisesRegex(ValueError, "refusing to overwrite"):
            seed_game_project(self.store)
        self.assertEqual(before, self.store.gdd())
        self.assertEqual(self.store.tasks, [])

    def test_refuses_to_replace_changed_reference_file(self):
        seed_game_project(self.store)
        path = self.store.folder / "gdd" / "reference" / DOCS[0]
        path.write_text("changed", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "refusing overwrite"):
            seed_game_project(self.store)
        self.assertEqual(path.read_text(encoding="utf-8"), "changed")

    def test_register_cannot_be_incomplete(self):
        docs = load_documents()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "gdd").mkdir()
            for name in DOCS:
                (root / "gdd" / name).write_text(docs[name], encoding="utf-8")
            (root / "ROADMAP-UNITY-CODEX.md").write_text(docs["ROADMAP-UNITY-CODEX.md"], encoding="utf-8")
            decision_path = root / "gdd" / DOCS[0]
            decision_path.write_text(docs[DOCS[0]].replace("**GDD-099**", "**GDD-998**"), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "GDD-001 through GDD-100"):
                load_documents(root)


if __name__ == "__main__":
    unittest.main()
