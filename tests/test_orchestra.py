"""Scenario coverage for optional ChatGPT + Codex orchestration.

These tests are intentionally included without running during the user-requested
implementation-only pass.
"""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from office_core import ProjectStore
from director import parse_plan
from model_routing import classify, review_verdict
from orchestra import ModelOrchestrator


class OrchestraTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        (root / "Assets").mkdir()
        (root / "Packages").mkdir()
        (root / "ProjectSettings").mkdir()
        (root / "Assets" / "Main.cs").write_text("class Main {}", encoding="utf-8")
        self.store = ProjectStore(root)
        self.store.approve_gdd("# GDD-001\nApproved movement")

    def tearDown(self):
        self.tmp.cleanup()

    def test_auto_model_routing(self):
        self.assertEqual(classify("Предложи 5 названий для монстра")[0], "chatgpt")
        self.assertEqual(classify("Реализуй движение игрока в Unity")[0], "codex")
        self.assertEqual(classify("Измени Assets/Main.cs")[0], "codex")

    def test_api_text_model_creates_report_without_editing_unity(self):
        task = self.store.add("Предложи 5 вариантов диалога", route="chatgpt_fast")
        runner = ModelOrchestrator(self.store, api_key="dummy")
        with patch("orchestra.invoke_model", return_value="Пять вариантов...") as mock_call:
            runner._run_agent(task["id"], None)
        self.assertEqual(task["status"], "merged")
        self.assertTrue(Path(task["report"]).exists())
        self.assertEqual((self.store.root / "Assets" / "Main.cs").read_text(), "class Main {}")
        self.assertEqual(mock_call.call_args.args[0], "gpt-6-luna")

    def test_no_api_key_stages_manual_chatgpt_handoff(self):
        task = self.store.add("Придумай варианты названий", route="chatgpt_fast")
        runner = ModelOrchestrator(self.store, api_key="")
        with patch.dict("os.environ", {"OPENAI_API_KEY": ""}):
            runner._run_agent(task["id"], None)
        self.assertEqual(task["status"], "handoff")
        self.assertIn("APPROVED GDD", runner.handoff_prompt(task["id"]))
        runner.finish_text_task(task["id"], "Короткие названия", model="ChatGPT conversation")
        self.assertEqual(task["status"], "merged")

    def test_text_dependency_unblocks_codex(self):
        parent = self.store.add("Составь список механик", route="chatgpt_fast")
        child = self.store.add("Реализуй список механик", depends=[parent["id"]], route="codex")
        self.assertEqual([x["id"] for x in self.store.eligible()], [parent["id"]])
        manager = ModelOrchestrator(self.store)
        self.store.update(parent["id"], status="handoff")
        manager.finish_text_task(parent["id"], "Утверждённые механики: передвижение")
        self.assertIn(child["id"], [x["id"] for x in self.store.eligible()])

    def test_model_code_review_blocks_automatic_merge(self):
        task = self.store.add("Исправь класс Main", route="codex")
        runner = ModelOrchestrator(self.store, api_key="dummy", review_enabled=True)
        with patch("orchestra.invoke_model", return_value="BLOCK\nMissing error handling"):
            self.assertFalse(runner.review_before_merge(task["id"], []))
        self.assertEqual(task["status"], "ready")
        self.assertIn("BLOCK", task["review"])

    def test_planner_routes_and_rejects_unsafe_model_edit(self):
        result = parse_plan('{"tasks":[{"title":"Придумай 5 названий","depends":[],'
                            '"route":"chatgpt_fast"},{"title":"Измени Assets/Main.cs",'
                            '"depends":[0],"route":"chatgpt_fast"}]}')
        self.assertEqual(result[0][2], "chatgpt_fast")
        self.assertEqual(result[1][2], "codex")

    def test_reviewer_requires_exact_approve(self):
        self.assertTrue(review_verdict("APPROVE\nNo blocker"))
        self.assertFalse(review_verdict("BLOCK\nDo not merge"))
        self.assertFalse(review_verdict("looks good APPROVE"))


if __name__ == "__main__":
    unittest.main()
