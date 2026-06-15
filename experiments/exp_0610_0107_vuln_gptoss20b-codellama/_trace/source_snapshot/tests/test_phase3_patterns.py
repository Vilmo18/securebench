import json
import os
import sys
import tempfile
import unittest


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
SRC = os.path.join(ROOT, "src")
sys.path.insert(0, SRC)


from phase3_patterns import build_phase3_pattern_report, write_phase3_reports  # noqa: E402


class TestPhase3Patterns(unittest.TestCase):
    def test_build_phase3_pattern_report_minimal(self) -> None:
        with tempfile.TemporaryDirectory(prefix="phase3_") as tmp:
            phase_three = os.path.join(tmp, "PHASE_THREE")
            run_dir = os.path.join(phase_three, "runs", "node_1", "run_0001")
            os.makedirs(run_dir, exist_ok=True)

            meta = {
                "node_id": 1,
                "phase": 3,
                "difficulty": "hard",
                "concepts": ["CWE-502"],
                "success": False,
                "attempts_till_success": 3,
                "total_issues": 2,
            }
            with open(os.path.join(run_dir, "meta.json"), "w", encoding="utf-8") as f:
                json.dump(meta, f)

            code = "import pickle\n\ndef f(data):\n    return pickle.loads(data)\n"
            result = {"solution_code": code, "success": False, "attempts_till_success": 3}
            with open(os.path.join(run_dir, "result.json"), "w", encoding="utf-8") as f:
                json.dump(result, f)

            pa = {
                "primary_category": "unresolved_sast_findings",
                "primary_reason": "unresolved_target_findings",
                "tags": ["insecure_deserialization"],
                "persistent_sast_tests": ["bandit:B301"],
                "evidence": [
                    {
                        "signature": "bandit:B301:4",
                        "tool": "bandit",
                        "test_id": "bandit:B301",
                        "cwe_id": "CWE-502",
                        "severity": "HIGH",
                        "confidence": "HIGH",
                        "line_number": 4,
                        "description": "pickle.loads on untrusted input",
                        "context": "     3: def f(data):\n>>   4:     return pickle.loads(data)\n",
                    },
                    {
                        "signature": "bandit:B301:4",
                        "tool": "bandit",
                        "test_id": "bandit:B301",
                        "cwe_id": "CWE-502",
                        "severity": "HIGH",
                        "confidence": "HIGH",
                        "line_number": 4,
                        "description": "duplicate evidence should not increase frequency",
                        "context": "     3: def f(data):\n>>   4:     return pickle.loads(data)\n",
                    },
                ],
            }
            with open(os.path.join(run_dir, "pattern_analysis.json"), "w", encoding="utf-8") as f:
                json.dump(pa, f)

            report = build_phase3_pattern_report(phase_three)
            summary = report["pattern_summary"]
            self.assertEqual(summary["total_patterns"], 1)
            self.assertEqual(summary["unique_cwes"], 1)
            self.assertEqual(summary["patterns_by_cwe"].get("CWE-502"), 1)
            self.assertEqual(summary["runs_with_any_pattern"], 1)

            patterns = report["patterns"]
            self.assertEqual(len(patterns), 1)
            self.assertEqual(patterns[0]["cwe_id"], "CWE-502")
            self.assertEqual(patterns[0]["frequency"], 1)

            out = write_phase3_reports(phase_three)
            self.assertTrue(os.path.exists(out["pattern_summary"]))
            self.assertTrue(os.path.exists(out["detailed_report"]))


if __name__ == "__main__":
    unittest.main()

