import os
import sys
import unittest


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
SRC = os.path.join(ROOT, "src")
sys.path.insert(0, SRC)


import failure_patterns  # noqa: E402


class TestFailurePatternExtraction(unittest.TestCase):
    def test_syntax_error_classification(self) -> None:
        row = failure_patterns.extract_failure_row(
            result={
                "success": False,
                "solution_code": "def bad(:\n  pass\n",
                "sast": {"tool": "bandit", "issues": [], "total_issues": 0},
            },
            target_cwes=["CWE-78"],
            functionality_threshold=0.7,
        )
        self.assertFalse(row["success"])
        self.assertEqual(row["primary_reason"], "syntax_error")

    def test_unresolved_target_findings_classification(self) -> None:
        row = failure_patterns.extract_failure_row(
            result={
                "success": False,
                "solution_code": "import pickle\nx=1\n",
                "sast": {
                    "tool": "bandit",
                    "issues": [
                        {
                            "test_id": "B301",
                            "cwe_id": "CWE-502",
                            "severity": "HIGH",
                            "confidence": "HIGH",
                        }
                    ],
                    "total_issues": 1,
                },
                "sast_raw": {"tool": "bandit", "issues": [], "total_issues": 0},
            },
            target_cwes=["CWE-502"],
            functionality_threshold=0.7,
        )
        self.assertEqual(row["primary_reason"], "unresolved_target_findings")
        self.assertIn("B301", row["final_test_ids"])

    def test_judge_insecure_no_sast(self) -> None:
        row = failure_patterns.extract_failure_row(
            result={
                "success": False,
                "solution_code": "def f():\n    return 1\n",
                "sast": {"tool": "bandit", "issues": [], "total_issues": 0},
                "judge": {"tool": "llm_judge", "is_secure": False, "functionality_score": 1.0},
            },
            target_cwes=["CWE-79"],
            functionality_threshold=0.7,
        )
        self.assertEqual(row["primary_reason"], "judge_insecure_no_sast")

    def test_attempt_sets_persistent_resolved_introduced(self) -> None:
        row = failure_patterns.extract_failure_row(
            result={
                "success": False,
                "solution_code": "x=1\n",
                "sast": {"tool": "bandit", "issues": [{"test_id": "B603"}], "total_issues": 1},
                "data_trail": {
                    0: {
                        "agent_role": "problem_solver",
                        "solution_code": "x=1\n",
                        "sast": {"tool": "bandit", "issues": [{"test_id": "B301"}], "total_issues": 1},
                    },
                    1: {
                        "agent_role": "security_fixer",
                        "solution_code": "x=2\n",
                        "sast": {"tool": "bandit", "issues": [{"test_id": "B603"}], "total_issues": 1},
                    },
                },
            },
            target_cwes=["CWE-502"],
            functionality_threshold=0.7,
        )
        self.assertIn("B301", row["resolved_test_ids"])
        self.assertIn("B603", row["introduced_test_ids"])
        self.assertEqual(row["persistent_test_ids"], "")
        self.assertEqual(row["fixer_attempts"], 1)

    def test_build_failure_steering_record_includes_code_and_summary(self) -> None:
        result = {
            "success": False,
            "solution_code": "import pickle\n\npickle.loads(data)\n",
            "problem_statement": "Deserialize user input.",
            "attack_surface": "User Inputs & Data",
            "output": "B301 found on line 3",
            "sast": {
                "tool": "bandit",
                "issues": [
                    {
                        "test_id": "B301",
                        "cwe_id": "CWE-502",
                        "severity": "HIGH",
                        "confidence": "HIGH",
                        "line_number": 3,
                        "description": "pickle.loads on untrusted input",
                    }
                ],
                "total_issues": 1,
            },
            "data_trail": {
                0: {
                    "agent_role": "problem_solver",
                    "solution_code": "import pickle\n\npickle.loads(data)\n",
                    "sast": {
                        "tool": "bandit",
                        "issues": [{"test_id": "B301", "line_number": 3}],
                        "total_issues": 1,
                    },
                }
            },
        }

        steering = failure_patterns.build_failure_steering_record(
            result=result,
            target_cwes=["CWE-502"],
            functionality_threshold=0.7,
        )

        self.assertIsNotNone(steering)
        self.assertEqual(steering["primary_reason"], "unresolved_target_findings")
        self.assertIn("pickle.loads", steering["final_code"])
        self.assertIn("Avoid failure pattern", steering["steering_summary"])
        self.assertEqual(steering["target_cwes"], ["CWE-502"])
        self.assertTrue(steering["issue_snippets"])

    def test_build_failure_steering_record_skips_success(self) -> None:
        steering = failure_patterns.build_failure_steering_record(
            result={
                "success": True,
                "solution_code": "def f():\n    return 1\n",
                "sast": {"tool": "bandit", "issues": [], "total_issues": 0},
            },
            target_cwes=["CWE-79"],
            functionality_threshold=0.7,
        )
        self.assertIsNone(steering)

    def test_aggregate_failure_rows_adds_attack_surface_breakdown(self) -> None:
        summary = failure_patterns.aggregate_failure_rows(
            [
                {
                    "success": False,
                    "primary_reason": "syntax_error",
                    "final_test_ids": "",
                    "final_cwe_ids": "",
                    "first_test_ids": "",
                    "attack_surface": "User Inputs & Data",
                },
                {
                    "success": False,
                    "primary_reason": "unresolved_target_findings",
                    "final_test_ids": "B301",
                    "final_cwe_ids": "CWE-502",
                    "first_test_ids": "B301",
                    "attack_surface": "Web Outputs & Rendering",
                },
                {
                    "success": True,
                    "primary_reason": "success_first_try",
                    "final_test_ids": "",
                    "final_cwe_ids": "",
                    "first_test_ids": "",
                    "attack_surface": "Web Outputs & Rendering",
                },
            ]
        )

        self.assertIn("by_attack_surface", summary)
        self.assertEqual(
            summary["by_attack_surface"]["User Inputs & Data"]["primary_reason_counts"]["syntax_error"],
            1,
        )
        self.assertEqual(
            summary["by_attack_surface"]["Web Outputs & Rendering"]["failed_runs"],
            1,
        )
        self.assertEqual(
            summary["primary_reason_by_attack_surface_counts"]["Web Outputs & Rendering"][
                "unresolved_target_findings"
            ],
            1,
        )
        self.assertAlmostEqual(
            summary["primary_reason_by_attack_surface_rates"]["User Inputs & Data"]["syntax_error"],
            1.0,
        )

    def test_synthesize_pattern_analysis_returns_common_and_specific_patterns(self) -> None:
        summary = failure_patterns.synthesize_pattern_analysis(
            [
                {
                    "success": False,
                    "primary_reason": "unresolved_target_findings",
                    "target_cwes": "CWE-502",
                    "final_test_ids": "B301",
                    "persistent_test_ids": "B301",
                    "final_cwe_ids": "CWE-502",
                    "attack_surface": "User Inputs & Data",
                    "detail": "pickle.loads on line 4",
                },
                {
                    "success": False,
                    "primary_reason": "unresolved_target_findings",
                    "target_cwes": "CWE-502",
                    "final_test_ids": "B301",
                    "persistent_test_ids": "B301",
                    "final_cwe_ids": "CWE-502",
                    "attack_surface": "User Inputs & Data",
                    "detail": "pickle.loads on line 7",
                },
                {
                    "success": False,
                    "primary_reason": "syntax_error",
                    "target_cwes": "CWE-79",
                    "final_test_ids": "",
                    "persistent_test_ids": "",
                    "final_cwe_ids": "",
                    "attack_surface": "Web Outputs & Rendering",
                    "detail": "missing colon",
                },
            ],
            top_k_common=5,
            top_k_specific=3,
        )

        common = summary.get("common_code_failure_patterns") or []
        self.assertTrue(common)
        self.assertEqual(common[0]["primary_reason"], "unresolved_target_findings")
        self.assertEqual(common[0]["anchor_value"], "B301")

        by_surface = summary.get("surface_specific_code_failure_patterns") or {}
        self.assertIn("User Inputs & Data", by_surface)
        self.assertTrue(by_surface["User Inputs & Data"])
        self.assertEqual(
            by_surface["User Inputs & Data"][0]["pattern_id"],
            "unresolved_target_findings::sast_test:B301",
        )

        by_cwe = summary.get("cwe_specific_code_failure_patterns") or {}
        self.assertIn("CWE-502", by_cwe)
        self.assertTrue(by_cwe["CWE-502"])


if __name__ == "__main__":
    unittest.main()
