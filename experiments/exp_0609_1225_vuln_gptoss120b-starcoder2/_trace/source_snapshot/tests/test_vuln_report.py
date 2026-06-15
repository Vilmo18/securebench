import os
import pickle
import sys
import tempfile
import unittest


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
SRC = os.path.join(ROOT, "src")
sys.path.insert(0, SRC)


from node import ChallengeNode  # noqa: E402
from vuln_report import analyze_experiment  # noqa: E402


class TestVulnReportFailurePatterns(unittest.TestCase):
    def test_analyze_experiment_adds_failure_breakdown_by_attack_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vuln_report_exp_") as exp_dir:
            out_dir = os.path.join(exp_dir, "report")

            node = ChallengeNode(
                difficulty="User Inputs & Data",
                concepts=["CWE-502"],
                challenge_description="",
                condition_axis="attack_surface",
                condition_label="User Inputs & Data",
                condition_rank=1,
                log_creation=False,
            )
            node.run_results = [
                {
                    "target_cwes": ["CWE-502"],
                    "attack_surface": "User Inputs & Data",
                    "success": False,
                    "attempts_till_success": 1,
                    "solution_code": "def broken(:\n    pass\n",
                    "sast": {"tool": "bandit", "issues": [], "total_issues": 0},
                    "total_issues": 0,
                }
            ]

            with open(os.path.join(exp_dir, "tree_final.pkl"), "wb") as f:
                pickle.dump([node], f)

            metrics = analyze_experiment(exp_dir, out_dir, make_plots=False)

            failure_patterns = metrics.get("failure_patterns") or {}
            by_surface = failure_patterns.get("by_attack_surface") or {}
            self.assertIn("User Inputs & Data", by_surface)
            self.assertEqual(
                by_surface["User Inputs & Data"]["primary_reason_counts"]["syntax_error"],
                1,
            )
            self.assertTrue(
                os.path.exists(os.path.join(out_dir, "failure_patterns_by_attack_surface.csv"))
            )
            self.assertTrue(
                os.path.exists(os.path.join(out_dir, "failure_reason_by_attack_surface.csv"))
            )
            self.assertTrue(
                os.path.exists(os.path.join(out_dir, "code_failure_pattern_analysis.json"))
            )
            self.assertTrue(
                os.path.exists(
                    os.path.join(out_dir, "surface_specific_code_failure_patterns.csv")
                )
            )
            synthetic = metrics.get("code_failure_pattern_analysis") or {}
            self.assertIn("common_code_failure_patterns", synthetic)
            self.assertIn("surface_specific_code_failure_patterns", synthetic)


if __name__ == "__main__":
    unittest.main()
