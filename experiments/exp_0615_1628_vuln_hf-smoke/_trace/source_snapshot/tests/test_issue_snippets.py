import os
import sys
import unittest


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
SRC = os.path.join(ROOT, "src")
sys.path.insert(0, SRC)


from issue_snippets import build_issue_snippets, extract_code_context  # noqa: E402


class TestIssueSnippets(unittest.TestCase):
    def test_extract_code_context_highlights_line(self) -> None:
        code = "a=1\nb=2\nc=3\n"
        ctx = extract_code_context(code, 2, radius=1)
        self.assertIsInstance(ctx, str)
        self.assertIn(">>   2: b=2", ctx)
        self.assertIn("     1: a=1", ctx)
        self.assertIn("     3: c=3", ctx)

    def test_build_issue_snippets_includes_context(self) -> None:
        code = "import pickle\n\ndef f(data):\n    return pickle.loads(data)\n"
        issues = [
            {
                "tool": "bandit",
                "test_id": "bandit:B301",
                "cwe_id": "CWE-502",
                "severity": "HIGH",
                "confidence": "HIGH",
                "line_number": 4,
                "description": "pickle usage",
                "code": "return pickle.loads(data)",
            }
        ]
        out = build_issue_snippets(code, issues, radius=1, max_issues=5)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["test_id"], "bandit:B301")
        self.assertIn("pickle.loads", out[0]["context"] or "")


if __name__ == "__main__":
    unittest.main()

