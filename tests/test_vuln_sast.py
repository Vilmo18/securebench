import os
import sys
import unittest
import warnings

def _silence_known_third_party_deprecations() -> None:
    warnings.filterwarnings(
        "ignore",
        message=r"The verify_requirements argument is now a no-op.*",
        category=DeprecationWarning,
        module=r"stevedore\.extension",
    )
    warnings.filterwarnings(
        "ignore",
        message=r"ast\.Str is deprecated.*",
        category=DeprecationWarning,
        module=r"bandit\.core\.utils",
    )


# Apply once for non-unittest runners; unittest's own warning filter may override
# this during execution, so we re-apply again in `setUpModule`.
_silence_known_third_party_deprecations()


def setUpModule() -> None:
    _silence_known_third_party_deprecations()


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
SRC = os.path.join(ROOT, "src")
sys.path.insert(0, SRC)


from sast_analyzer import BanditSastAnalyzer, MultiSastAnalyzer  # noqa: E402
from sast_cwe_mapping import bandit_test_to_cwe  # noqa: E402
from vulnerability_mcts import VulnerabilityMCTS, _JUDGE_ENABLED, _JUDGE_MODE  # noqa: E402
from vulnerability_environment import (  # noqa: E402
    VulnerabilityChallengeEnvironment,
    _apply_judge_sast_review,
    _format_judge_for_feedback,
    _format_sast_output_impl,
    _normalize_review_only_judge_output,
)


class _RoleAgent:
    def __init__(self, configured: bool) -> None:
        self.configured = configured

    def set_role(self, _role: str) -> bool:
        return self.configured


class TestRequiredAgentConfiguration(unittest.TestCase):
    def test_rejects_unconfigured_required_agent(self) -> None:
        environment = VulnerabilityChallengeEnvironment.__new__(
            VulnerabilityChallengeEnvironment
        )
        environment.agents = {
            "challenge_designer": _RoleAgent(False),
            "problem_solver": _RoleAgent(True),
        }

        with self.assertRaisesRegex(RuntimeError, "challenge_designer"):
            environment._configure_required_agents(environment.agents.keys())

    def test_accepts_configured_required_agents(self) -> None:
        environment = VulnerabilityChallengeEnvironment.__new__(
            VulnerabilityChallengeEnvironment
        )
        environment.agents = {
            "challenge_designer": _RoleAgent(True),
            "problem_solver": _RoleAgent(True),
        }

        environment._configure_required_agents(environment.agents.keys())


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

    def test_bandit_test_to_cwe_covers_all_bandit_tests(self) -> None:
        from bandit.core.extension_loader import MANAGER  # type: ignore

        ids = set((MANAGER.blacklist_by_id or {}).keys()) | set((MANAGER.plugins_by_id or {}).keys())
        missing = [tid for tid in sorted(ids) if not bandit_test_to_cwe(tid)]
        self.assertEqual(missing, [])


class _DummySastAnalyzer:
    def __init__(self, tool: str, result: dict) -> None:
        self._tool = tool
        self._result = dict(result)

    def scan_code(self, _code: str) -> dict:
        out = dict(self._result)
        out.setdefault("tool", self._tool)
        return out


class TestMultiSastAnalyzer(unittest.TestCase):
    def test_merges_and_prefixes_test_ids(self) -> None:
        bandit = _DummySastAnalyzer(
            "bandit",
            {
                "issues": [
                    {
                        "test_id": "B301",
                        "line_number": 10,
                        "cwe_id": "CWE-502",
                        "severity": "HIGH",
                        "confidence": "HIGH",
                    }
                ],
                "total_issues": 1,
            },
        )
        semgrep = _DummySastAnalyzer(
            "semgrep",
            {
                "issues": [
                    {
                        "test_id": "test.os-system",
                        "line_number": 3,
                        "cwe_id": "CWE-78",
                        "severity": "HIGH",
                        "confidence": "HIGH",
                    }
                ],
                "total_issues": 1,
            },
        )

        multi = MultiSastAnalyzer({"bandit": bandit, "semgrep": semgrep}, prefix_test_ids=True)
        result = multi.scan_code("print('hi')\n")

        self.assertEqual(result.get("tool"), "multi")
        self.assertEqual(set(result.get("tools") or []), {"bandit", "semgrep"})
        self.assertEqual(result.get("total_issues"), 2)

        ids = {i.get("test_id") for i in (result.get("issues") or [])}
        self.assertIn("bandit:B301", ids)
        self.assertIn("semgrep:test.os-system", ids)

        bandit_issue = next(i for i in result.get("issues") if i.get("test_id") == "bandit:B301")
        self.assertEqual(bandit_issue.get("test_id_raw"), "B301")

    def test_deduplicates_same_cwe_same_line_across_tools(self) -> None:
        bandit = _DummySastAnalyzer(
            "bandit",
            {
                "issues": [
                    {
                        "test_id": "B301",
                        "line_number": 2,
                        "cwe_id": "CWE-502",
                        "severity": "LOW",
                        "confidence": "LOW",
                    }
                ],
                "total_issues": 1,
            },
        )
        semgrep = _DummySastAnalyzer(
            "semgrep",
            {
                "issues": [
                    {
                        "test_id": "rule.unsafe-deserialize",
                        "line_number": 2,
                        "cwe_id": "CWE-502",
                        "severity": "HIGH",
                        "confidence": "HIGH",
                    }
                ],
                "total_issues": 1,
            },
        )

        multi = MultiSastAnalyzer({"bandit": bandit, "semgrep": semgrep}, prefix_test_ids=True)
        result = multi.scan_code("import pickle\npickle.loads(data)\n")

        self.assertEqual(result.get("tool"), "multi")
        self.assertEqual(result.get("total_issues"), 1)
        self.assertEqual((result.get("dedup") or {}).get("removed_duplicates"), 1)

        issues = result.get("issues") or []
        self.assertEqual(len(issues), 1)
        issue = issues[0]
        self.assertEqual(issue.get("cwe_id"), "CWE-502")
        # Worst-case severity/confidence should win when merging duplicates.
        self.assertEqual(issue.get("severity"), "HIGH")
        self.assertEqual(issue.get("confidence"), "HIGH")
        # Both tool hits should be tracked for debugging.
        self.assertIn("bandit:B301", issue.get("dedup_test_ids") or [])
        self.assertIn("semgrep:rule.unsafe-deserialize", issue.get("dedup_test_ids") or [])
        self.assertEqual(set(issue.get("dedup_tools") or []), {"bandit", "semgrep"})

    def test_propagates_tool_errors(self) -> None:
        ok = _DummySastAnalyzer("bandit", {"issues": [], "total_issues": 0})
        bad = _DummySastAnalyzer(
            "semgrep",
            {"issues": [], "total_issues": 0, "error": "semgrep failed"},
        )

        multi = MultiSastAnalyzer({"bandit": ok, "semgrep": bad}, fail_on_error=True)
        result = multi.scan_code("print('hi')\n")

        self.assertTrue(result.get("errors"))
        self.assertIn("semgrep", result.get("errors"))
        self.assertTrue(result.get("error"))


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

        secure_score = scorer.calculate_score(secure, "basic")
        insecure_score = scorer.calculate_score(insecure, "basic")
        self.assertGreater(secure_score, insecure_score)

    def test_judge_risk_does_not_affect_score_when_sast_clean(self) -> None:
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

        secure_score = scorer.calculate_score(judged_secure, "basic")
        insecure_score = scorer.calculate_score(judged_insecure, "basic")
        # Phase 1 reward is derived from SAST outcomes only; judge scoring must not change it.
        self.assertAlmostEqual(secure_score, insecure_score, places=6)

    def test_judge_functionality_does_not_affect_score_when_sast_clean(self) -> None:
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

            # Phase 1 reward does not use LLM-judge scoring.
        self.assertAlmostEqual(
            scorer.calculate_score(functional, "basic"),
            scorer.calculate_score(broken, "basic"),
            places=6,
        )

    def test_no_code_is_penalized_without_fake_attempt_penalty(self) -> None:
        scorer = VulnerabilityMCTS(environment=None, tree=None)

        no_code = {
            "target_cwes": ["CWE-502"],
            "attempts_till_success": 0,
            "fixed_by_security_fixer": False,
            "solution_code": "",
            "sast": {"tool": "bandit", "issues": [], "total_issues": 0},
        }
        insecure = {
            "target_cwes": ["CWE-502"],
            "attempts_till_success": 1,
            "fixed_by_security_fixer": False,
            "solution_code": "import pickle\npickle.loads(data)\n",
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

        no_code_score = scorer.calculate_score(no_code, "basic")
        insecure_score = scorer.calculate_score(insecure, "basic")
        self.assertLess(no_code_score, 0.5)
        self.assertLess(no_code_score, insecure_score)


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

    def test_apply_judge_sast_review_with_tool_prefixed_ids(self) -> None:
        scan_raw = {
            "tool": "multi",
            "issues": [
                {"test_id": "bandit:B301", "line_number": 10},
                {"test_id": "semgrep:test.os-system", "line_number": 20},
            ],
            "total_issues": 2,
        }
        judge = {
            "tool": "llm_judge",
            "sast_review": [
                {"test_id": "bandit:B301", "line_number": 10, "verdict": "FP"},
                {"test_id": "semgrep:test.os-system", "line_number": 20, "verdict": "TP"},
            ],
        }

        scan_eff, raw_total, fp_count = _apply_judge_sast_review(scan_raw, judge)
        self.assertEqual(raw_total, 2)
        self.assertEqual(fp_count, 1)
        remaining = [i.get("test_id") for i in scan_eff.get("issues", [])]
        self.assertEqual(remaining, ["semgrep:test.os-system"])

    def test_apply_judge_sast_review_removes_duplicate_true_positives(self) -> None:
        scan_raw = {
            "tool": "multi",
            "issues": [
                {
                    "test_id": "codeql:py/flask-debug",
                    "line_number": 41,
                    "cwe_id": "CWE-215",
                    "severity": "HIGH",
                    "confidence": "HIGH",
                },
                {
                    "test_id": "bandit:B201",
                    "line_number": 41,
                    "cwe_id": "CWE-94",
                    "severity": "HIGH",
                    "confidence": "MEDIUM",
                },
            ],
            "total_issues": 2,
        }
        judge = {
            "tool": "llm_judge",
            "sast_review": [
                {
                    "test_id": "codeql:py/flask-debug",
                    "line_number": 41,
                    "verdict": "TP",
                    "reason": "debug mode exposed",
                },
                {
                    "test_id": "bandit:B201",
                    "line_number": 41,
                    "verdict": "TP",
                    "reason": "same debug mode exposure",
                    "duplicate_of": "codeql:py/flask-debug#41",
                },
            ],
        }

        scan_eff, raw_total, fp_count = _apply_judge_sast_review(scan_raw, judge)
        self.assertEqual(raw_total, 2)
        self.assertEqual(fp_count, 0)
        self.assertEqual(scan_eff.get("total_issues"), 1)
        self.assertEqual(scan_eff.get("total_duplicates_removed"), 1)
        self.assertEqual(len(scan_eff.get("duplicate_findings", [])), 1)
        kept = (scan_eff.get("issues") or [])[0]
        self.assertEqual(kept.get("test_id"), "codeql:py/flask-debug")
        self.assertIn("bandit:B201", kept.get("dedup_test_ids") or [])
        self.assertIn("CWE-94", kept.get("dedup_cwe_ids") or [])

    def test_apply_judge_sast_review_auto_collapses_same_sink_duplicates(self) -> None:
        scan_raw = {
            "tool": "multi",
            "issues": [
                {
                    "tool": "codeql",
                    "test_id": "codeql:py/flask-debug",
                    "test_name": "py/flask-debug",
                    "line_number": 63,
                    "cwe_id": "CWE-215",
                    "severity": "HIGH",
                    "confidence": "HIGH",
                    "description": (
                        "A Flask app appears to be run in debug mode. "
                        "This may allow an attacker to run arbitrary code through the debugger."
                    ),
                    "code": "app.run(debug=True, port=5000)",
                },
                {
                    "tool": "bandit",
                    "test_id": "bandit:B201",
                    "test_name": "flask_debug_true",
                    "line_number": 63,
                    "cwe_id": "CWE-94",
                    "severity": "HIGH",
                    "confidence": "MEDIUM",
                    "description": (
                        "A Flask app appears to be run with debug=True, which exposes the "
                        "Werkzeug debugger and allows the execution of arbitrary code."
                    ),
                    "code": "62 if __name__ == '__main__':\n63     app.run(debug=True, port=5000)",
                },
            ],
            "total_issues": 2,
        }
        judge = {
            "tool": "llm_judge",
            "sast_review": [
                {
                    "test_id": "codeql:py/flask-debug",
                    "line_number": 63,
                    "verdict": "TP",
                    "reason": "The app is running in debug mode and exposes the Werkzeug debugger.",
                },
                {
                    "test_id": "bandit:B201",
                    "line_number": 63,
                    "verdict": "TP",
                    "reason": "The app is run with debug=True and exposes the same debugger entry point.",
                },
            ],
        }

        scan_eff, raw_total, fp_count = _apply_judge_sast_review(
            scan_raw,
            judge,
            judge_mode="review_only",
        )
        self.assertEqual(raw_total, 2)
        self.assertEqual(fp_count, 0)
        self.assertEqual(scan_eff.get("total_issues"), 1)
        self.assertEqual(scan_eff.get("total_duplicates_removed"), 1)
        self.assertEqual(len(scan_eff.get("duplicate_findings", [])), 1)
        kept = (scan_eff.get("issues") or [])[0]
        self.assertIn("codeql:py/flask-debug", kept.get("dedup_test_ids") or [])
        self.assertIn("bandit:B201", kept.get("dedup_test_ids") or [])
        self.assertIn("CWE-215", kept.get("dedup_cwe_ids") or [])
        self.assertIn("CWE-94", kept.get("dedup_cwe_ids") or [])

    def test_apply_judge_sast_review_keeps_distinct_same_line_findings(self) -> None:
        scan_raw = {
            "tool": "multi",
            "issues": [
                {
                    "tool": "codeql",
                    "test_id": "codeql:py/url-redirection",
                    "test_name": "py/url-redirection",
                    "line_number": 18,
                    "cwe_id": "CWE-601",
                    "severity": "HIGH",
                    "confidence": "HIGH",
                    "description": "Unvalidated data is used in a redirect target.",
                    "code": "return redirect(target)",
                },
                {
                    "tool": "semgrep",
                    "test_id": "semgrep:rendered-user-input",
                    "test_name": "rendered-user-input",
                    "line_number": 18,
                    "cwe_id": "CWE-79",
                    "severity": "HIGH",
                    "confidence": "HIGH",
                    "description": "User-controlled HTML is rendered without escaping.",
                    "code": "return redirect(target)",
                },
            ],
            "total_issues": 2,
        }
        judge = {
            "tool": "llm_judge",
            "sast_review": [
                {
                    "test_id": "codeql:py/url-redirection",
                    "line_number": 18,
                    "verdict": "TP",
                    "reason": "The redirect target is attacker controlled.",
                },
                {
                    "test_id": "semgrep:rendered-user-input",
                    "line_number": 18,
                    "verdict": "TP",
                    "reason": "The rendered output is not escaped.",
                },
            ],
        }

        scan_eff, raw_total, fp_count = _apply_judge_sast_review(
            scan_raw,
            judge,
            judge_mode="review_only",
        )
        self.assertEqual(raw_total, 2)
        self.assertEqual(fp_count, 0)
        self.assertEqual(scan_eff.get("total_issues"), 2)
        self.assertEqual(scan_eff.get("total_duplicates_removed"), 0)

    def test_normalize_review_only_judge_output_collapses_duplicate_reviews(self) -> None:
        scan_raw = {
            "tool": "multi",
            "issues": [
                {"test_id": "codeql:py/flask-debug", "line_number": 41},
                {"test_id": "bandit:B201", "line_number": 41},
            ],
            "total_issues": 2,
        }
        judge = {
            "tool": "llm_judge",
            "sast_review": [
                {
                    "test_id": "codeql:py/flask-debug",
                    "line_number": 41,
                    "verdict": "TP",
                    "reason": "debug mode exposed",
                },
                {
                    "test_id": "bandit:B201",
                    "line_number": 41,
                    "verdict": "TP",
                    "reason": "same issue",
                    "duplicate_of": "codeql:py/flask-debug#41",
                },
            ],
        }

        normalized = _normalize_review_only_judge_output(
            judge,
            scan_raw,
            sast_success=False,
            raw_total_issues=2,
            effective_total_issues=1,
            false_positive_count=0,
            duplicate_count=1,
            fp_override_count=0,
        )
        self.assertIsNotNone(normalized)
        self.assertEqual(len(normalized.get("sast_review") or []), 1)
        self.assertIn("duplicates=1", str(normalized.get("summary") or ""))

    def test_normalize_review_only_judge_output_auto_collapses_heuristic_duplicates(self) -> None:
        scan_raw = {
            "tool": "multi",
            "issues": [
                {
                    "tool": "codeql",
                    "test_id": "codeql:py/flask-debug",
                    "test_name": "py/flask-debug",
                    "line_number": 63,
                    "cwe_id": "CWE-215",
                    "severity": "HIGH",
                    "confidence": "HIGH",
                    "description": "A Flask app appears to be run in debug mode.",
                    "code": "app.run(debug=True, port=5000)",
                },
                {
                    "tool": "bandit",
                    "test_id": "bandit:B201",
                    "test_name": "flask_debug_true",
                    "line_number": 63,
                    "cwe_id": "CWE-94",
                    "severity": "HIGH",
                    "confidence": "MEDIUM",
                    "description": "A Flask app appears to be run with debug=True.",
                    "code": "62 if __name__ == '__main__':\n63     app.run(debug=True, port=5000)",
                },
            ],
            "total_issues": 2,
        }
        judge = {
            "tool": "llm_judge",
            "sast_review": [
                {
                    "test_id": "codeql:py/flask-debug",
                    "line_number": 63,
                    "verdict": "TP",
                    "reason": "The Flask debugger is exposed.",
                },
                {
                    "test_id": "bandit:B201",
                    "line_number": 63,
                    "verdict": "TP",
                    "reason": "The same Flask debug entry point is exposed.",
                },
            ],
        }

        normalized = _normalize_review_only_judge_output(
            judge,
            scan_raw,
            sast_success=False,
            raw_total_issues=2,
            effective_total_issues=1,
            false_positive_count=0,
            duplicate_count=1,
            fp_override_count=0,
        )
        self.assertIsNotNone(normalized)
        self.assertEqual(len(normalized.get("sast_review") or []), 1)
        self.assertIn("duplicates=1", str(normalized.get("summary") or ""))

    def test_fixer_sast_feedback_hides_judge_reason_and_fix(self) -> None:
        scan_effective = {
            "issues": [
                {
                    "test_id": "bandit:B602",
                    "test_name": "subprocess_popen_with_shell_equals_true",
                    "line_number": 12,
                    "cwe_id": "CWE-78",
                    "severity": "HIGH",
                    "confidence": "HIGH",
                    "description": "subprocess call with shell=True",
                    "code": "subprocess.run(cmd, shell=True)",
                    "judge_verdict": "TP",
                    "judge_reason": "This explanation should not be fed to the fixer.",
                    "judge_fix": "This fix hint should not be fed to the fixer.",
                }
            ],
            "total_issues": 1,
        }

        feedback = _format_sast_output_impl(
            scan_effective,
            include_false_positives=False,
            include_judge_details=False,
        )

        self.assertIn("[TP] CWE-78", feedback)
        self.assertIn("subprocess.run(cmd, shell=True)", feedback)
        self.assertNotIn("judge:", feedback)
        self.assertNotIn("fix:", feedback)
        self.assertNotIn("This explanation should not be fed", feedback)
        self.assertNotIn("This fix hint should not be fed", feedback)

    def test_fixer_judge_feedback_is_labels_only(self) -> None:
        scan_raw = {
            "issues": [
                {
                    "test_id": "bandit:B602",
                    "line_number": 12,
                    "cwe_id": "CWE-78",
                    "severity": "HIGH",
                    "confidence": "HIGH",
                    "code": "subprocess.run(cmd, shell=True)",
                },
                {
                    "test_id": "bandit:B606",
                    "line_number": 18,
                    "cwe_id": "CWE-78",
                    "severity": "LOW",
                    "confidence": "HIGH",
                    "code": "os.execvp('zip', args)",
                },
            ]
        }
        judge = {
            "sast_review": [
                {
                    "test_id": "bandit:B602",
                    "line_number": 12,
                    "verdict": "TP",
                    "reason": "This TP reason should be hidden from the fixer.",
                },
                {
                    "test_id": "bandit:B606",
                    "line_number": 18,
                    "verdict": "FP",
                    "reason": "This FP reason should also be hidden from the fixer.",
                },
            ]
        }

        feedback = _format_judge_for_feedback(
            judge,
            judge_mode="review_only",
            scan_raw=scan_raw,
            for_fixer=True,
        )

        self.assertIn("bandit:B602", feedback)
        self.assertIn("verdict=TP", feedback)
        self.assertNotIn("bandit:B606", feedback)
        self.assertNotIn("reason:", feedback)
        self.assertNotIn("This TP reason", feedback)
        self.assertNotIn("This FP reason", feedback)


if __name__ == "__main__":
    unittest.main()
