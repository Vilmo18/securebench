import os
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
SRC = os.path.join(ROOT, "src")
sys.path.insert(0, SRC)


from sast_analyzer import SemgrepSastAnalyzer  # noqa: E402


def _semgrep_available() -> bool:
    exe_dir = os.path.dirname(sys.executable)
    candidates = [os.path.join(exe_dir, "semgrep")]
    if os.name == "nt":
        candidates = [
            os.path.join(exe_dir, "semgrep.exe"),
            os.path.join(exe_dir, "semgrep.cmd"),
            os.path.join(exe_dir, "semgrep.bat"),
        ]
    semgrep_exe = next((c for c in candidates if os.path.exists(c)), None) or shutil.which("semgrep")
    if not semgrep_exe:
        return False
    try:
        subprocess.run(
            [semgrep_exe, "--version"],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        return True
    except Exception:
        return False


class TestSemgrepSastAnalyzer(unittest.TestCase):
    def test_project_rules_file_detects_os_system(self) -> None:
        if not _semgrep_available():
            self.skipTest("semgrep is not installed")

        rules_path = os.path.join(ROOT, "semgrep_rules.yml")
        self.assertTrue(os.path.exists(rules_path))

        analyzer = SemgrepSastAnalyzer(
            config=rules_path,
            severity_threshold="LOW",
            confidence_threshold="LOW",
            timeout_seconds=30,
        )
        code = "import os\nos.system('id')\n"
        result = analyzer.scan_code(code)
        issues = result.get("issues", [])
        self.assertTrue(any(i.get("test_id") == "prismvul.python.os-system" for i in issues))

    def test_scan_code_detects_os_system(self) -> None:
        if not _semgrep_available():
            self.skipTest("semgrep is not installed")

        rule = """rules:
  - id: test.os-system
    message: "os.system used"
    languages: [python]
    severity: ERROR
    metadata:
      cwe: ["CWE-78"]
      confidence: HIGH
    pattern: os.system(...)
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False, encoding="utf-8") as f:
            f.write(rule)
            rule_path = f.name

        try:
            analyzer = SemgrepSastAnalyzer(
                config=rule_path,
                severity_threshold="LOW",
                confidence_threshold="LOW",
                timeout_seconds=30,
            )
            code = "import os\n\ndef run(cmd):\n    os.system(cmd)\n"
            result = analyzer.scan_code(code)
            self.assertIsInstance(result, dict)
            self.assertEqual(result.get("tool"), "semgrep")
            self.assertGreaterEqual(result.get("total_issues", 0), 1)
            issues = result.get("issues", [])
            self.assertTrue(
                any(str(i.get("test_id") or "").endswith("test.os-system") for i in issues)
            )
            first = next(
                i
                for i in issues
                if str(i.get("test_id") or "").endswith("test.os-system")
            )
            self.assertEqual(first.get("cwe_id"), "CWE-78")
            self.assertEqual(first.get("severity"), "HIGH")
        finally:
            try:
                os.unlink(rule_path)
            except OSError:
                pass

    def test_scan_code_no_issues(self) -> None:
        if not _semgrep_available():
            self.skipTest("semgrep is not installed")

        # Use a rule that doesn't match this code
        rule = """rules:
  - id: test.never-matches
    message: "never"
    languages: [python]
    severity: INFO
    pattern: definitely_not_in_code(...)
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False, encoding="utf-8") as f:
            f.write(rule)
            rule_path = f.name

        try:
            analyzer = SemgrepSastAnalyzer(config=rule_path, timeout_seconds=30)
            code = "def add(a, b):\n    return a + b\n"
            result = analyzer.scan_code(code)
            self.assertIsInstance(result, dict)
            self.assertEqual(result.get("tool"), "semgrep")
            self.assertEqual(result.get("total_issues"), 0)
        finally:
            try:
                os.unlink(rule_path)
            except OSError:
                pass


if __name__ == "__main__":
    unittest.main()
