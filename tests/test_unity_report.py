"""Unity test-result gate checks without requiring Unity Editor."""
import tempfile
import unittest
from pathlib import Path

from unity_integration import test_report_status


class UnityTestReportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "playmode.xml"

    def tearDown(self):
        self.temp.cleanup()

    def test_valid_result_counts_as_passed(self):
        self.path.write_text(
            '<test-run total="3" passed="2" failed="0" skipped="1" result="Passed"/>',
            encoding="utf-8")
        passed, summary = test_report_status(self.path)
        self.assertTrue(passed)
        self.assertIn("total=3", summary)

    def test_failed_tests_block_success_even_with_unity_exit_zero(self):
        self.path.write_text(
            '<test-run total="3" passed="2" failed="1" skipped="0" result="Failed"/>',
            encoding="utf-8")
        self.assertFalse(test_report_status(self.path)[0])

    def test_missing_xml_cannot_reuse_previous_test_success(self):
        self.assertFalse(test_report_status(self.path)[0])

    def test_zero_tests_cannot_be_called_success(self):
        self.path.write_text(
            '<test-run total="0" passed="0" failed="0" skipped="0" result="Passed"/>',
            encoding="utf-8")
        self.assertFalse(test_report_status(self.path)[0])

    def test_malformed_xml_does_not_count_as_success(self):
        self.path.write_text("<test-run", encoding="utf-8")
        self.assertFalse(test_report_status(self.path)[0])


if __name__ == "__main__":
    unittest.main()
