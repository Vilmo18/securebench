import os
import sys
import unittest


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
SRC = os.path.join(ROOT, "src")
sys.path.insert(0, SRC)


from sast_analyzer import BanditSastAnalyzer  # noqa: E402
from vulnerability_mcts import VulnerabilityMCTS, _JUDGE_ENABLED, _JUDGE_MODE  # noqa: E402
from vulnerability_environment import _apply_judge_sast_review  # noqa: E402


class TestBanditSastAnalyzer(unittest.TestCase):
    def test_scan_code_no_issues(self) -> None:
        analyzer = BanditSastAnalyzer(severity_threshold="LOW", confidence_threshold="LOW")
        code = "def add(a, b):\n    return a + b\n"
        result = analyzer.scan_code(code)
        self.assertIsInstance(result, dict)
        self.assertEqual(result.get("tool"), "bandit")
        self.assertEqual(result.get("total_issues"), 0)

    def test_scan_code_detects_pickle(self) -> None:
        analyzer = BanditSastAnalyzer(severity_threshold="LOW", confidence_threshold="LOW")
        code = (
            "import pickle\n\n"
            "def loads_user(data: bytes):\n"
            "    return pickle.loads(data)\n"
        )
        result = analyzer.scan_code(code)
        self.assertIsInstance(result, dict)
        self.assertGreaterEqual(result.get("total_issues", 0), 1)
        issues = result.get("issues", [])
        self.assertTrue(any(i.get("cwe_id") == "CWE-502" for i in issues))


class TestVulnerabilityScoring(unittest.TestCase):
    def test_secure_scores_higher_than_insecure(self) -> None:
        scorer = VulnerabilityMCTS(environment=None, tree=None)

        secure = {
            "target_cwes": ["CWE-502"],
            "attempts_till_success": 1,
            "fixed_by_security_fixer": False,
            "sast": {"tool": "bandit", "issues": [], "total_issues": 0},
        }
        insecure = {
            "target_cwes": ["CWE-502"],
            "attempts_till_success": 1,
            "fixed_by_security_fixer": False,
            "sast": {
                "tool": "bandit",
                "issues": [
                    {
                        "cwe_id": "CWE-502",
                        "severity": "HIGH",
                        "confidence": "HIGH",
                    }
                ],
                "total_issues": 1,
            },
        }

        secure_score = scorer.calculate_score(secure, "very easy")
        insecure_score = scorer.calculate_score(insecure, "very easy")
        self.assertGreater(secure_score, insecure_score)

    def test_judge_risk_affects_score_when_enabled(self) -> None:
        if not _JUDGE_ENABLED:
            self.skipTest("LLM judge disabled in configs.yml")

        scorer = VulnerabilityMCTS(environment=None, tree=None)

        base = {
            "target_cwes": ["CWE-502"],
            "attempts_till_success": 1,
            "fixed_by_security_fixer": False,
            "sast": {"tool": "bandit", "issues": [], "total_issues": 0},
        }

        judged_secure = {
            **base,
            "judge": {
                "overall_risk": 0.0,
                "target_cwe_risk": 0.0,
                "security_score": 1.0,
            },
        }
        judged_insecure = {
            **base,
            "judge": {
                "overall_risk": 0.9,
                "target_cwe_risk": 0.9,
                "security_score": 0.1,
            },
        }

        secure_score = scorer.calculate_score(judged_secure, "very easy")
        insecure_score = scorer.calculate_score(judged_insecure, "very easy")
        if str(_JUDGE_MODE) == "review_only":
            # In review-only mode, judge risk is not used as a detector; it should not affect score
            # when SAST is clean (judge only gates functionality via `functionality_score`).
            self.assertAlmostEqual(secure_score, insecure_score, places=6)
        else:
            self.assertGreater(secure_score, insecure_score)

    def test_judge_functionality_affects_score_when_present(self) -> None:
        scorer = VulnerabilityMCTS(environment=None, tree=None)

        base = {
            "target_cwes": ["CWE-502"],
            "attempts_till_success": 1,
            "fixed_by_security_fixer": False,
            "sast": {"tool": "bandit", "issues": [], "total_issues": 0},
        }
        functional = {
            **base,
            "judge": {"functionality_score": 1.0},
        }
        broken = {
            **base,
            "judge": {"functionality_score": 0.0},
        }

        self.assertGreater(
            scorer.calculate_score(functional, "very easy"),
            scorer.calculate_score(broken, "very easy"),
        )


class TestSastReviewFiltering(unittest.TestCase):
    def test_apply_judge_sast_review_filters_false_positives(self) -> None:
        scan_raw = {
            "tool": "bandit",
            "issues": [
                {"test_id": "B301", "line_number": 10, "cwe_id": "CWE-502", "severity": "HIGH", "confidence": "HIGH"},
                {"test_id": "B603", "line_number": 20, "cwe_id": "CWE-78", "severity": "MEDIUM", "confidence": "MEDIUM"},
            ],
            "total_issues": 2,
        }
        judge = {
            "tool": "llm_judge",
            "sast_review": [
                {"test_id": "B301", "line_number": 10, "verdict": "FP", "reason": "benign in context"},
                {"test_id": "B603", "line_number": 20, "verdict": "TP", "reason": "real risk"},
            ],
        }

        scan_eff, raw_total, fp_count = _apply_judge_sast_review(scan_raw, judge)
        self.assertEqual(raw_total, 2)
        self.assertEqual(fp_count, 1)
        self.assertEqual(scan_eff.get("total_issues"), 1)
        self.assertEqual(len(scan_eff.get("issues", [])), 1)
        self.assertEqual(scan_eff["issues"][0].get("test_id"), "B603")
        self.assertEqual(scan_eff["issues"][0].get("judge_verdict"), "TP")
        self.assertTrue(scan_eff.get("false_positives"))
        self.assertEqual(scan_eff["false_positives"][0].get("test_id"), "B301")
        self.assertEqual(scan_eff["false_positives"][0].get("judge_verdict"), "FP")

    def test_apply_judge_sast_review_review_only_keeps_high_risk_fp_as_uncertain(self) -> None:
        scan_raw = {
            "tool": "bandit",
            "issues": [
                {"test_id": "B301", "line_number": 10, "cwe_id": "CWE-502", "severity": "HIGH", "confidence": "HIGH"},
                {"test_id": "B603", "line_number": 20, "cwe_id": "CWE-78", "severity": "MEDIUM", "confidence": "MEDIUM"},
            ],
            "total_issues": 2,
        }
        judge = {
            "tool": "llm_judge",
            "sast_review": [
                {"test_id": "B301", "line_number": 10, "verdict": "FP", "reason": "benign in context"},
                {"test_id": "B603", "line_number": 20, "verdict": "TP", "reason": "real risk"},
            ],
        }

        scan_eff, raw_total, fp_count = _apply_judge_sast_review(scan_raw, judge, judge_mode="review_only")
        self.assertEqual(raw_total, 2)
        self.assertEqual(fp_count, 0)
        self.assertEqual(scan_eff.get("total_issues"), 2)
        self.assertEqual(scan_eff.get("total_fp_overrides"), 1)
        ids = {i.get("test_id"): i for i in scan_eff.get("issues", [])}
        self.assertEqual(ids["B603"].get("judge_verdict"), "TP")
        self.assertEqual(ids["B301"].get("judge_verdict"), "UNCERTAIN")
        self.assertEqual(ids["B301"].get("judge_verdict_original"), "FP")

    def test_apply_judge_sast_review_fallback_by_test_id(self) -> None:
        scan_raw = {
            "tool": "bandit",
            "issues": [
                {"test_id": "B301", "line_number": 10},
                {"test_id": "B301", "line_number": 99},
                {"test_id": "B603", "line_number": 20},
            ],
            "total_issues": 3,
        }
        judge = {
            "tool": "llm_judge",
            "sast_review": [{"test_id": "B301", "verdict": "FP", "reason": "context safe"}],
        }

        scan_eff, raw_total, fp_count = _apply_judge_sast_review(scan_raw, judge)
        self.assertEqual(raw_total, 3)
        self.assertEqual(fp_count, 2)
        remaining = [i.get("test_id") for i in scan_eff.get("issues", [])]
        self.assertEqual(remaining, ["B603"])


if __name__ == "__main__":
    unittest.main()
