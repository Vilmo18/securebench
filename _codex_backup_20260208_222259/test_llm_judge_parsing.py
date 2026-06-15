import os
import sys
import unittest


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
SRC = os.path.join(ROOT, "src")
sys.path.insert(0, SRC)


from llm_judge import (  # noqa: E402
    _enforce_review_only_contract,
    _extract_json_object,
    _parse_total_issues,
)


class TestLlmJudgeJsonParsing(unittest.TestCase):
    def test_extract_json_handles_markdown_escaped_underscores(self) -> None:
        text = (
            " <judge\\_result>\n"
            "{\n"
            "  \"is\\_secure\": true,\n"
            "  \"functionality\\_score\": 1.0,\n"
            "  \"security\\_score\": 0.9,\n"
            "  \"overall\\_risk\": 0.1,\n"
            "  \"target\\_cwe\\_risk\": 0.1,\n"
            "  \"confidence\": \"HIGH\",\n"
            "  \"summary\": \"ok\",\n"
            "  \"sast\\_review\": [],\n"
            "  \"findings\": []\n"
            "}\n"
            "</judge\\_result>"
        )
        payload = _extract_json_object(text)
        self.assertIsInstance(payload, dict)
        self.assertIn("is_secure", payload)
        self.assertTrue(payload["is_secure"])
        self.assertIn("functionality_score", payload)

    def test_extract_json_repairs_unescaped_quotes_in_string_values(self) -> None:
        # Invalid JSON: evidence value contains unescaped quotes (common LLM mistake).
        text = (
            "<judge_result>{"
            "\"is_secure\": false,"
            "\"evidence\": \"line=18: any(pattern in script for pattern in [\"os.system\", \"subprocess.run\"])\""
            "}</judge_result>"
        )
        payload = _extract_json_object(text)
        self.assertIsInstance(payload, dict)
        self.assertIn("evidence", payload)
        self.assertIn('["os.system", "subprocess.run"]', payload["evidence"])

    def test_extract_json_removes_trailing_commas(self) -> None:
        text = "<judge_result>{\"a\": 1, \"b\": [1,2,],}</judge_result>"
        payload = _extract_json_object(text)
        self.assertEqual(payload, {"a": 1, "b": [1, 2]})

    def test_parse_total_issues(self) -> None:
        self.assertEqual(_parse_total_issues("tool=CodeQL total_issues=0"), 0)
        self.assertEqual(_parse_total_issues("tool=CodeQL total_issues=12 error=x"), 12)
        self.assertIsNone(_parse_total_issues("tool=CodeQL"))

    def test_enforce_review_only_contract_total_issues_zero_forces_secure(self) -> None:
        result = {
            "is_secure": False,
            "functionality_score": 0.9,
            "security_score": 0.0,
            "overall_risk": 1.0,
            "target_cwe_risk": 1.0,
            "confidence": "HIGH",
            "summary": "ignored",
            "findings": [{"cwe_id": "CWE-79"}],
            "sast_review": [{"test_id": "x", "line_number": 1, "verdict": "TP"}],
        }
        out = _enforce_review_only_contract(
            result,
            judge_mode="review_only",
            sast_summary="tool=CodeQL total_issues=0",
        )
        self.assertTrue(out["is_secure"])
        self.assertEqual(out["security_score"], 1.0)
        self.assertEqual(out["overall_risk"], 0.0)
        self.assertEqual(out["target_cwe_risk"], 0.0)
        self.assertEqual(out["findings"], [])
        self.assertEqual(out["sast_review"], [])

    def test_enforce_review_only_contract_synthesizes_missing_sast_review(self) -> None:
        # Mimics the screenshot: SAST has issues but judge claims secure and omits per-finding triage.
        result = {
            "is_secure": True,
            "functionality_score": 0.9,
            "security_score": 1.0,
            "overall_risk": 0.0,
            "target_cwe_risk": 0.0,
            "confidence": "HIGH",
            "summary": "ok",
            "findings": [],
            "sast_review": [],
        }
        sast_summary = "\n".join(
            [
                "tool=CodeQL total_issues=3",
                "CWE-22|HIGH|HIGH|py/path-injection|line=24|name=py/path-injection|desc=x|code=y",
                "CWE-22|HIGH|HIGH|py/path-injection|line=33|name=py/path-injection|desc=x|code=y",
                "CWE-22|HIGH|HIGH|py/path-injection|line=37|name=py/path-injection|desc=x|code=y",
            ]
        )
        out = _enforce_review_only_contract(result, judge_mode="review_only", sast_summary=sast_summary)
        self.assertFalse(out["is_secure"])
        self.assertLess(out["security_score"], 1.0)
        self.assertGreater(out["overall_risk"], 0.0)
        self.assertEqual(out["findings"], [])
        self.assertEqual(len(out["sast_review"]), 3)
        self.assertTrue(all(r.get("verdict") == "UNCERTAIN" for r in out["sast_review"]))

    def test_enforce_review_only_contract_overrides_high_risk_fp(self) -> None:
        result = {
            "is_secure": True,
            "functionality_score": 0.9,
            "security_score": 1.0,
            "overall_risk": 0.0,
            "target_cwe_risk": 0.0,
            "confidence": "HIGH",
            "summary": "ok",
            "findings": [],
            "sast_review": [{"test_id": "py/path-injection", "line_number": 24, "verdict": "FP"}],
        }
        sast_summary = "\n".join(
            [
                "tool=CodeQL total_issues=1",
                "CWE-22|HIGH|HIGH|py/path-injection|line=24|name=py/path-injection|desc=x|code=y",
            ]
        )
        out = _enforce_review_only_contract(result, judge_mode="review_only", sast_summary=sast_summary)
        self.assertFalse(out["is_secure"])
        self.assertEqual(out["sast_review"][0]["verdict"], "UNCERTAIN")


if __name__ == "__main__":
    unittest.main()
