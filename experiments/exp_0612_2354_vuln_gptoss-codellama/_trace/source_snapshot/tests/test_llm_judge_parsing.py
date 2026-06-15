import os
import sys
import unittest


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
SRC = os.path.join(ROOT, "src")
sys.path.insert(0, SRC)


from llm_judge import _extract_json_object  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()
