from __future__ import annotations

import concurrent.futures
import json
import os
import subprocess
import sys
import tempfile
import shutil
import urllib.parse
from typing import Any, Dict, List, Optional, Sequence, Union

from loguru import logger

from sast_cwe_mapping import bandit_test_to_cwe, extract_cwe_id


_SEVERITY_LEVELS = ["LOW", "MEDIUM", "HIGH"]
_CONFIDENCE_LEVELS = ["LOW", "MEDIUM", "HIGH"]


def _normalize_level(value: str, allowed: List[str], default: str) -> str:
    if not value:
        return default
    upper = str(value).upper()
    return upper if upper in allowed else default


def _level_at_least(value: str, threshold: str, allowed: List[str]) -> bool:
    try:
        return allowed.index(value) >= allowed.index(threshold)
    except ValueError:
        return False


class BanditSastAnalyzer:
    """
    Run Bandit (Python SAST) and return a normalized issue list with CWE mapping.

    Notes:
    - Uses `python -m bandit` to avoid PATH issues.
    - Bandit returns non-zero when findings exist; that's treated as a successful scan.
    """

    def __init__(
        self,
        severity_threshold: str = "LOW",
        confidence_threshold: str = "LOW",
        timeout_seconds: int = 30,
    ) -> None:
        self.severity_threshold = _normalize_level(
            severity_threshold, _SEVERITY_LEVELS, "LOW"
        )
        self.confidence_threshold = _normalize_level(
            confidence_threshold, _CONFIDENCE_LEVELS, "LOW"
        )
        self.timeout_seconds = int(timeout_seconds)

        self._bandit_cmd = [sys.executable, "-m", "bandit"]
        self._ensure_bandit_available()

    def _ensure_bandit_available(self) -> None:
        try:
            subprocess.run(
                [*self._bandit_cmd, "--version"],
                capture_output=True,
                text=True,
                check=True,
                timeout=self.timeout_seconds,
            )
        except FileNotFoundError as e:
            raise RuntimeError("Python executable not found for Bandit invocation.") from e
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                "Bandit is not installed or failed to run. Install it with: pip install bandit"
            ) from e
        except subprocess.TimeoutExpired as e:
            raise RuntimeError("Bandit version check timed out.") from e

    def scan_code(self, code: str) -> Dict[str, Any]:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as f:
            f.write(code or "")
            tmp_path = f.name

        try:
            return self.scan_file(tmp_path)
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    def scan_file(self, file_path: str) -> Dict[str, Any]:
        if not os.path.exists(file_path):
            return {"tool": "bandit", "issues": [], "total_issues": 0, "error": "File not found"}

        cmd = [
            *self._bandit_cmd,
            "-f",
            "json",
            "-q",
            file_path,
        ]

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            return {
                "tool": "bandit",
                "issues": [],
                "total_issues": 0,
                "error": f"Bandit scan timed out after {self.timeout_seconds}s",
            }
        except Exception as e:
            return {
                "tool": "bandit",
                "issues": [],
                "total_issues": 0,
                "error": f"Bandit scan failed: {e}",
            }

        stdout = (proc.stdout or "").strip()
        if not stdout:
            # When Bandit crashes, stderr usually contains the clue.
            if proc.returncode not in (0, 1):
                return {
                    "tool": "bandit",
                    "issues": [],
                    "total_issues": 0,
                    "error": (proc.stderr or "").strip() or "Bandit returned no output",
                }
            return {"tool": "bandit", "issues": [], "total_issues": 0, "metrics": {}}

        try:
            raw = json.loads(stdout)
        except json.JSONDecodeError:
            return {
                "tool": "bandit",
                "issues": [],
                "total_issues": 0,
                "error": "Failed to parse Bandit JSON output",
                "raw_stdout": stdout[:2000],
                "raw_stderr": (proc.stderr or "")[:2000],
            }

        return self._normalize_output(raw)

    def _normalize_output(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        issues: List[Dict[str, Any]] = []

        for item in raw.get("results", []) or []:
            severity = _normalize_level(item.get("issue_severity"), _SEVERITY_LEVELS, "LOW")
            confidence = _normalize_level(
                item.get("issue_confidence"), _CONFIDENCE_LEVELS, "LOW"
            )

            if not _level_at_least(severity, self.severity_threshold, _SEVERITY_LEVELS):
                continue
            if not _level_at_least(
                confidence, self.confidence_threshold, _CONFIDENCE_LEVELS
            ):
                continue

            cwe_id = self._extract_cwe_id(item)
            issues.append(
                {
                    "tool": "bandit",
                    "test_id": item.get("test_id"),
                    "test_name": item.get("test_name"),
                    "cwe_id": cwe_id,
                    "severity": severity,
                    "confidence": confidence,
                    "line_number": item.get("line_number"),
                    "code": item.get("code"),
                    "description": item.get("issue_text"),
                    "more_info": item.get("more_info"),
                }
            )

        metrics = raw.get("metrics", {}) or {}

        normalized = {
            "tool": "bandit",
            "issues": issues,
            "total_issues": len(issues),
            "metrics": metrics,
            "severity_breakdown": self._breakdown(issues, "severity", _SEVERITY_LEVELS),
            "confidence_breakdown": self._breakdown(
                issues, "confidence", _CONFIDENCE_LEVELS
            ),
        }

        if raw.get("errors"):
            normalized["errors"] = raw.get("errors")
        return normalized

    def _extract_cwe_id(self, item: Dict[str, Any]) -> Optional[str]:
        # Prefer Bandit's built-in CWE mapping when present.
        issue_cwe = item.get("issue_cwe")
        if isinstance(issue_cwe, dict):
            cwe_num = issue_cwe.get("id")
            if isinstance(cwe_num, int) and cwe_num > 0:
                return f"CWE-{cwe_num}"

        test_id = item.get("test_id")
        if not test_id:
            return None
        return bandit_test_to_cwe(str(test_id))

    def _breakdown(
        self, issues: List[Dict[str, Any]], key: str, allowed: List[str]
    ) -> Dict[str, int]:
        breakdown = {level: 0 for level in allowed}
        for issue in issues:
            level = issue.get(key)
            if level in breakdown:
                breakdown[level] += 1
        return breakdown


def _semgrep_severity_to_level(value: str) -> str:
    # Semgrep severities commonly: ERROR|WARNING|INFO (and sometimes CRITICAL).
    v = str(value or "").strip().upper()
    if v in {"ERROR", "CRITICAL", "HIGH"}:
        return "HIGH"
    if v in {"WARNING", "MEDIUM"}:
        return "MEDIUM"
    if v in {"INFO", "LOW"}:
        return "LOW"
    return "LOW"


def _semgrep_confidence_to_level(value: str) -> str:
    # Semgrep rule metadata sometimes includes a confidence/likelihood field.
    v = str(value or "").strip().upper()
    if v in {"HIGH", "VERY_HIGH", "CERTAIN"}:
        return "HIGH"
    if v in {"MEDIUM", "MODERATE"}:
        return "MEDIUM"
    if v in {"LOW", "VERY_LOW"}:
        return "LOW"
    return "MEDIUM"


class SemgrepSastAnalyzer:
    """
    Run Semgrep and return a normalized issue list with (best-effort) CWE mapping.

    Notes:
    - Uses the `semgrep` executable (preferably from the current virtualenv) to avoid PATH issues.
    - For deterministic behavior, provide an explicit `config` (local rules file or registry rulepack).
    """

    def __init__(
        self,
        *,
        config: Union[str, Sequence[str]] = "p/security-audit",
        severity_threshold: str = "LOW",
        confidence_threshold: str = "LOW",
        timeout_seconds: int = 60,
    ) -> None:
        self.config = [str(config)] if isinstance(config, str) else [str(c) for c in (config or [])]
        self.severity_threshold = _normalize_level(severity_threshold, _SEVERITY_LEVELS, "LOW")
        self.confidence_threshold = _normalize_level(confidence_threshold, _CONFIDENCE_LEVELS, "LOW")
        self.timeout_seconds = int(timeout_seconds)

        self._semgrep_cmd = [self._resolve_semgrep_executable()]
        self._ensure_semgrep_available()

    def _resolve_semgrep_executable(self) -> str:
        # Prefer the semgrep executable installed alongside the current interpreter (e.g., venv/bin/semgrep).
        exe_dir = os.path.dirname(sys.executable)
        candidates: List[str] = []
        if os.name == "nt":
            candidates.extend(
                [
                    os.path.join(exe_dir, "semgrep.exe"),
                    os.path.join(exe_dir, "semgrep.cmd"),
                    os.path.join(exe_dir, "semgrep.bat"),
                ]
            )
        else:
            candidates.append(os.path.join(exe_dir, "semgrep"))

        for c in candidates:
            if os.path.exists(c) and os.access(c, os.X_OK):
                return c

        found = shutil.which("semgrep")
        if found:
            return found

        raise RuntimeError(
            "Semgrep executable not found. Install it with: pip install semgrep "
            "(recommended inside a virtual environment)."
        )

    def _ensure_semgrep_available(self) -> None:
        try:
            subprocess.run(
                [*self._semgrep_cmd, "--version"],
                capture_output=True,
                text=True,
                check=True,
                timeout=self.timeout_seconds,
            )
        except FileNotFoundError as e:
            raise RuntimeError("Python executable not found for Semgrep invocation.") from e
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                "Semgrep is not installed or failed to run. Install it with: pip install semgrep"
            ) from e
        except subprocess.TimeoutExpired as e:
            raise RuntimeError("Semgrep version check timed out.") from e

    def scan_code(self, code: str) -> Dict[str, Any]:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as f:
            f.write(code or "")
            tmp_path = f.name

        try:
            return self.scan_file(tmp_path)
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    def scan_file(self, file_path: str) -> Dict[str, Any]:
        if not os.path.exists(file_path):
            return {"tool": "semgrep", "issues": [], "total_issues": 0, "error": "File not found"}

        source_lines: Optional[List[str]] = None
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                source_lines = f.readlines()
        except Exception:
            source_lines = None

        cmd: List[str] = [
            *self._semgrep_cmd,
            "--json",
            "--quiet",
            "--metrics",
            "off",
        ]
        for cfg in self.config:
            if cfg:
                cmd.extend(["--config", cfg])
        cmd.append(file_path)

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            return {
                "tool": "semgrep",
                "issues": [],
                "total_issues": 0,
                "error": f"Semgrep scan timed out after {self.timeout_seconds}s",
            }
        except Exception as e:
            return {
                "tool": "semgrep",
                "issues": [],
                "total_issues": 0,
                "error": f"Semgrep scan failed: {e}",
            }

        stdout = (proc.stdout or "").strip()
        if not stdout:
            # When Semgrep errors, stderr usually contains the clue.
            if proc.returncode not in (0, 1):
                return {
                    "tool": "semgrep",
                    "issues": [],
                    "total_issues": 0,
                    "error": (proc.stderr or "").strip() or "Semgrep returned no output",
                }
            return {"tool": "semgrep", "issues": [], "total_issues": 0, "metrics": {}}

        try:
            raw = json.loads(stdout)
        except json.JSONDecodeError:
            return {
                "tool": "semgrep",
                "issues": [],
                "total_issues": 0,
                "error": "Failed to parse Semgrep JSON output",
                "raw_stdout": stdout[:2000],
                "raw_stderr": (proc.stderr or "")[:2000],
            }

        return self._normalize_output(raw, source_lines=source_lines)

    def _normalize_output(
        self, raw: Dict[str, Any], *, source_lines: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        issues: List[Dict[str, Any]] = []

        def _snippet(start_line: Optional[int], end_line: Optional[int]) -> Optional[str]:
            if not source_lines or start_line is None:
                return None
            try:
                s = max(1, int(start_line))
            except Exception:
                return None
            try:
                e = int(end_line) if end_line is not None else s
            except Exception:
                e = s

            s_idx = max(0, s - 1)
            e_idx = min(len(source_lines), max(s, e))
            if e_idx <= s_idx:
                e_idx = min(len(source_lines), s_idx + 1)

            snippet_text = "".join(source_lines[s_idx:e_idx]).rstrip("\n")
            snippet_text = snippet_text.strip("\n")
            if len(snippet_text) > 800:
                snippet_text = snippet_text[:800] + "\n... (truncated)"
            return snippet_text

        for item in raw.get("results", []) or []:
            if not isinstance(item, dict):
                continue
            check_id = item.get("check_id")
            start = item.get("start") or {}
            end = item.get("end") or {}
            extra = item.get("extra") or {}
            metadata = extra.get("metadata") or {}

            severity = _semgrep_severity_to_level(extra.get("severity") or metadata.get("severity"))
            confidence = _semgrep_confidence_to_level(
                metadata.get("confidence")
                or metadata.get("likelihood")
                or metadata.get("precision")
                or ""
            )

            if not _level_at_least(severity, self.severity_threshold, _SEVERITY_LEVELS):
                continue
            if not _level_at_least(confidence, self.confidence_threshold, _CONFIDENCE_LEVELS):
                continue

            cwe_id = extract_cwe_id(metadata)

            line_number = None
            end_line_number = None
            if isinstance(start, dict):
                line_number = start.get("line")
            if isinstance(end, dict):
                end_line_number = end.get("line")

            code_snippet = extra.get("lines")
            if code_snippet is None:
                code_snippet = extra.get("line")
            # Newer Semgrep versions may redact matched lines unless authenticated ("requires login").
            if isinstance(code_snippet, str) and code_snippet.strip().lower() == "requires login":
                code_snippet = None
            if code_snippet is None:
                code_snippet = _snippet(
                    int(line_number) if line_number is not None else None,
                    int(end_line_number) if end_line_number is not None else None,
                )

            message = extra.get("message") or metadata.get("message") or ""

            more_info = metadata.get("references") or metadata.get("reference") or metadata.get("url")

            issues.append(
                {
                    "tool": "semgrep",
                    "test_id": str(check_id) if check_id is not None else None,
                    "test_name": str(check_id) if check_id is not None else None,
                    "cwe_id": cwe_id,
                    "severity": severity,
                    "confidence": confidence,
                    "line_number": line_number,
                    "code": code_snippet,
                    "description": message,
                    "more_info": more_info,
                }
            )

        normalized: Dict[str, Any] = {
            "tool": "semgrep",
            "issues": issues,
            "total_issues": len(issues),
            "metrics": raw.get("stats", {}) or {},
            "severity_breakdown": self._breakdown(issues, "severity", _SEVERITY_LEVELS),
            "confidence_breakdown": self._breakdown(issues, "confidence", _CONFIDENCE_LEVELS),
        }

        errors = raw.get("errors")
        if errors:
            normalized["errors"] = errors
            try:
                first = errors[0]
                if isinstance(first, dict) and first.get("message"):
                    normalized["error"] = str(first.get("message"))
                else:
                    normalized["error"] = f"Semgrep reported {len(errors)} errors"
            except Exception:
                normalized["error"] = "Semgrep reported errors"

        return normalized

    def _breakdown(
        self, issues: List[Dict[str, Any]], key: str, allowed: List[str]
    ) -> Dict[str, int]:
        breakdown = {level: 0 for level in allowed}
        for issue in issues:
            level = issue.get(key)
            if level in breakdown:
                breakdown[level] += 1
        return breakdown


def _sarif_level_to_severity(value: str) -> str:
    v = str(value or "").strip().lower()
    if v == "error":
        return "HIGH"
    if v == "warning":
        return "MEDIUM"
    if v in {"note", "none"}:
        return "LOW"
    return "LOW"


def _codeql_precision_to_confidence(value: str) -> str:
    v = str(value or "").strip().lower()
    if v in {"high", "very-high", "very_high"}:
        return "HIGH"
    if v in {"medium", "moderate"}:
        return "MEDIUM"
    if v in {"low", "very-low", "very_low"}:
        return "LOW"
    return "MEDIUM"


class CodeQlSastAnalyzer:
    """
    Run CodeQL and return a normalized issue list with CWE mapping (from SARIF tags when available).

    Notes:
    - Requires the `codeql` CLI to be installed (not a pip dependency).
    - Uses SARIF output (`--format=sarifv2.1.0`) and normalizes to the common schema.
    - CodeQL is best at project-level analysis; running it per-attempt is slower than Semgrep/Bandit.
    """

    def __init__(
        self,
        *,
        queries: Union[str, Sequence[str]] = "codeql/python-queries",
        language: str = "python",
        build_mode: Optional[str] = None,
        download_packs: bool = False,
        search_path: Optional[Union[str, Sequence[str]]] = None,
        threads: Optional[int] = None,
        severity_threshold: str = "LOW",
        confidence_threshold: str = "LOW",
        timeout_seconds: int = 180,
        codeql_path: Optional[str] = None,
    ) -> None:
        self._project_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), os.pardir)
        )

        raw_queries = (
            [str(queries)]
            if isinstance(queries, str)
            else [str(q) for q in (queries or [])]
        )
        self.queries = [self._resolve_query_spec(q) for q in raw_queries if q]
        self.language = str(language or "python").strip().lower()
        self.build_mode = (str(build_mode).strip().lower() if build_mode else None) or (
            "none" if self.language == "python" else None
        )
        self.download_packs = bool(download_packs)
        self.search_path = self._normalize_search_path(search_path)
        self.threads = int(threads) if threads is not None else None
        self.severity_threshold = _normalize_level(severity_threshold, _SEVERITY_LEVELS, "LOW")
        self.confidence_threshold = _normalize_level(confidence_threshold, _CONFIDENCE_LEVELS, "LOW")
        self.timeout_seconds = int(timeout_seconds)

        self._codeql_cmd = [self._resolve_codeql_executable(codeql_path)]
        self._ensure_codeql_available()

    def _resolve_query_spec(self, spec: str) -> str:
        raw = str(spec or "").strip()
        if not raw:
            return raw

        # Allow CodeQL's `path:` prefix, but normalize to an absolute path when it exists locally.
        path_part = raw[len("path:") :] if raw.startswith("path:") else raw
        path_part = os.path.expanduser(path_part)

        candidates: List[str] = []
        if os.path.isabs(path_part):
            candidates.append(path_part)
        else:
            candidates.append(os.path.join(self._project_root, path_part))
            candidates.append(os.path.abspath(path_part))

        for c in candidates:
            if c and os.path.exists(c):
                return os.path.abspath(c)

        # Treat as a pack ref (e.g., `codeql/python-queries`) if it doesn't exist locally.
        return raw

    def _normalize_search_path(
        self, search_path: Optional[Union[str, Sequence[str]]]
    ) -> Optional[str]:
        if not search_path:
            return None
        parts = [str(search_path)] if isinstance(search_path, str) else [str(p) for p in search_path]
        resolved: List[str] = []
        for p in parts:
            if not p:
                continue
            p2 = os.path.expanduser(p)
            if not os.path.isabs(p2):
                p2 = os.path.join(self._project_root, p2)
            p2 = os.path.abspath(p2)
            if os.path.exists(p2):
                resolved.append(p2)
        return ":".join(resolved) if resolved else None

    def _resolve_codeql_executable(self, codeql_path: Optional[str]) -> str:
        if codeql_path:
            p = os.path.abspath(os.path.expanduser(str(codeql_path)))
            if os.path.exists(p) and os.access(p, os.X_OK):
                return p

        env = os.getenv("CODEQL_PATH") or os.getenv("CODEQL_CLI") or os.getenv("CODEQL")
        if env:
            p = os.path.abspath(os.path.expanduser(str(env)))
            if os.path.exists(p) and os.access(p, os.X_OK):
                return p

        # Common project-local install location: <project_root>/tools/codeql/codeql
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
        candidates: List[str] = []
        if os.name == "nt":
            candidates.append(os.path.join(project_root, "tools", "codeql", "codeql.exe"))
        else:
            candidates.append(os.path.join(project_root, "tools", "codeql", "codeql"))
        for c in candidates:
            if os.path.exists(c) and os.access(c, os.X_OK):
                return c

        found = shutil.which("codeql")
        if found:
            return found

        raise RuntimeError(
            "CodeQL CLI not found. Install it and ensure `codeql` is on PATH, "
            "or set `sast.codeql.path` in configs.yml / CODEQL_PATH env var."
        )

    def _ensure_codeql_available(self) -> None:
        try:
            subprocess.run(
                [*self._codeql_cmd, "version"],
                capture_output=True,
                text=True,
                check=True,
                timeout=min(self.timeout_seconds, 30),
            )
        except FileNotFoundError as e:
            raise RuntimeError("CodeQL executable not found.") from e
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                "CodeQL failed to run. Ensure the CLI is installed and executable."
            ) from e
        except subprocess.TimeoutExpired as e:
            raise RuntimeError("CodeQL version check timed out.") from e

    def scan_code(self, code: str) -> Dict[str, Any]:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as f:
            f.write(code or "")
            tmp_path = f.name
        try:
            return self.scan_file(tmp_path)
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    def scan_file(self, file_path: str) -> Dict[str, Any]:
        if not os.path.exists(file_path):
            return {"tool": "codeql", "issues": [], "total_issues": 0, "error": "File not found"}

        with tempfile.TemporaryDirectory(prefix="codeql_sast_") as work_dir:
            src_dir = os.path.join(work_dir, "src")
            os.makedirs(src_dir, exist_ok=True)

            # Copy the file into a small source root so CodeQL can build a DB.
            src_name = os.path.basename(file_path) or "main.py"
            if not src_name.endswith(".py"):
                src_name = f"{src_name}.py"
            focus_file = os.path.join(src_dir, src_name)
            try:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    code_text = f.read()
                with open(focus_file, "w", encoding="utf-8") as f:
                    f.write(code_text)
            except Exception as e:
                return {
                    "tool": "codeql",
                    "issues": [],
                    "total_issues": 0,
                    "error": f"Failed to prepare source root: {e}",
                }

            db_dir = os.path.join(work_dir, "db")
            sarif_path = os.path.join(work_dir, "results.sarif")

            # Create CodeQL database (Python doesn't need a build command).
            create_cmd = [
                *self._codeql_cmd,
                "database",
                "create",
                db_dir,
                "--language",
                self.language,
                "--source-root",
                src_dir,
            ]
            if self.build_mode:
                create_cmd.extend(["--build-mode", self.build_mode])
            if self.threads is not None:
                create_cmd.extend(["--threads", str(self.threads)])
            try:
                proc_create = subprocess.run(
                    create_cmd,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_seconds,
                )
            except subprocess.TimeoutExpired:
                return {
                    "tool": "codeql",
                    "issues": [],
                    "total_issues": 0,
                    "error": f"CodeQL database creation timed out after {self.timeout_seconds}s",
                }
            except Exception as e:
                return {
                    "tool": "codeql",
                    "issues": [],
                    "total_issues": 0,
                    "error": f"CodeQL database creation failed: {e}",
                }

            if proc_create.returncode != 0:
                stderr = (proc_create.stderr or "").strip()
                return {
                    "tool": "codeql",
                    "issues": [],
                    "total_issues": 0,
                    "error": stderr or "CodeQL database creation failed",
                }

            analyze_cmd: List[str] = [
                *self._codeql_cmd,
                "database",
                "analyze",
                db_dir,
                *[q for q in self.queries if q],
                *(
                    ["--search-path", self.search_path]
                    if self.search_path
                    else []
                ),
                "--format",
                "sarifv2.1.0",
                "--output",
                sarif_path,
            ]
            if self.threads is not None:
                analyze_cmd.extend(["--threads", str(self.threads)])
            if self.download_packs:
                analyze_cmd.append("--download")

            try:
                proc_analyze = subprocess.run(
                    analyze_cmd,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_seconds,
                )
            except subprocess.TimeoutExpired:
                return {
                    "tool": "codeql",
                    "issues": [],
                    "total_issues": 0,
                    "error": f"CodeQL analyze timed out after {self.timeout_seconds}s",
                }
            except Exception as e:
                return {
                    "tool": "codeql",
                    "issues": [],
                    "total_issues": 0,
                    "error": f"CodeQL analyze failed: {e}",
                }

            # CodeQL may exit non-zero for some conditions; if SARIF exists, try parsing anyway.
            if not os.path.exists(sarif_path):
                stderr = (proc_analyze.stderr or "").strip()
                stdout = (proc_analyze.stdout or "").strip()
                combined = "\n".join([s for s in (stderr, stdout) if s]).strip()

                hint = ""
                lowered = combined.lower()
                if "403 forbidden" in lowered or "could not create access credentials" in lowered:
                    hint = (
                        "CodeQL query pack download failed (GitHub Container Registry auth). "
                        "Either set GITHUB_TOKEN (and enable `download_packs: true`) or "
                        "install the open-source CodeQL query packs locally via "
                        "`bash scripts/install_codeql_queries.sh` and set `search_path`."
                    )
                elif "could not resolve pack" in lowered or "no such pack" in lowered:
                    hint = (
                        "CodeQL query pack not found. Install the open-source CodeQL query packs via "
                        "`bash scripts/install_codeql_queries.sh` and set `search_path`, "
                        "or enable `download_packs: true` with GITHUB_TOKEN."
                    )

                return {
                    "tool": "codeql",
                    "issues": [],
                    "total_issues": 0,
                    "error": (combined or "CodeQL did not produce SARIF output")
                    + (f"\nHint: {hint}" if hint else ""),
                }

            try:
                with open(sarif_path, "r", encoding="utf-8", errors="replace") as f:
                    sarif = json.load(f)
            except Exception as e:
                return {
                    "tool": "codeql",
                    "issues": [],
                    "total_issues": 0,
                    "error": f"Failed to parse CodeQL SARIF: {e}",
                }

            return self._normalize_sarif(sarif, source_root=src_dir)

    def _normalize_sarif(self, sarif: Dict[str, Any], *, source_root: str) -> Dict[str, Any]:
        runs = sarif.get("runs") if isinstance(sarif, dict) else None
        if not isinstance(runs, list) or not runs:
            return {"tool": "codeql", "issues": [], "total_issues": 0, "metrics": {}}

        run = runs[0] if isinstance(runs[0], dict) else {}
        tool = ((run.get("tool") or {}).get("driver") or {}) if isinstance(run.get("tool"), dict) else {}
        rules = tool.get("rules") or []

        rule_by_id: Dict[str, Dict[str, Any]] = {}
        if isinstance(rules, list):
            for r in rules:
                if isinstance(r, dict) and r.get("id"):
                    rule_by_id[str(r.get("id"))] = r

        def _uri_to_path(uri: Optional[str]) -> Optional[str]:
            if not uri:
                return None
            u = str(uri)
            if u.startswith("file://"):
                try:
                    parsed = urllib.parse.urlparse(u)
                    p = urllib.parse.unquote(parsed.path)
                    return p
                except Exception:
                    return None
            # Otherwise treat as relative to the scanned root.
            return os.path.join(source_root, u)

        file_lines_cache: Dict[str, List[str]] = {}

        def _lines_for(path: str) -> List[str]:
            if path in file_lines_cache:
                return file_lines_cache[path]
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    lines = f.readlines()
            except Exception:
                lines = []
            file_lines_cache[path] = lines
            return lines

        def _snippet(path: Optional[str], start_line: Optional[int], end_line: Optional[int]) -> Optional[str]:
            if not path or start_line is None:
                return None
            lines = _lines_for(path)
            if not lines:
                return None
            try:
                s = max(1, int(start_line))
            except Exception:
                return None
            try:
                e = int(end_line) if end_line is not None else s
            except Exception:
                e = s

            s_idx = max(0, s - 1)
            e_idx = min(len(lines), max(s, e))
            if e_idx <= s_idx:
                e_idx = min(len(lines), s_idx + 1)
            snippet_text = "".join(lines[s_idx:e_idx]).rstrip("\n")
            snippet_text = snippet_text.strip("\n")
            if len(snippet_text) > 800:
                snippet_text = snippet_text[:800] + "\n... (truncated)"
            return snippet_text

        issues: List[Dict[str, Any]] = []
        results = run.get("results") or []
        if not isinstance(results, list):
            results = []

        for item in results:
            if not isinstance(item, dict):
                continue
            rule_id = item.get("ruleId") or item.get("rule") or item.get("ruleID")
            rule_id_s = str(rule_id) if rule_id is not None else None
            rule = rule_by_id.get(rule_id_s or "", {}) if rule_id_s else {}

            level = item.get("level")
            default_cfg = rule.get("defaultConfiguration") if isinstance(rule, dict) else None
            if not level and isinstance(default_cfg, dict):
                level = default_cfg.get("level")
            severity = _sarif_level_to_severity(level)

            precision = None
            props = rule.get("properties") if isinstance(rule.get("properties"), dict) else {}
            if isinstance(props, dict):
                precision = props.get("precision") or props.get("problem.severity") or props.get("precisionLevel")
            confidence = _codeql_precision_to_confidence(precision)

            if not _level_at_least(severity, self.severity_threshold, _SEVERITY_LEVELS):
                continue
            if not _level_at_least(confidence, self.confidence_threshold, _CONFIDENCE_LEVELS):
                continue

            tags = None
            if isinstance(props, dict):
                tags = props.get("tags") or props.get("tag")
            cwe_id = extract_cwe_id(tags)

            message = item.get("message") or {}
            if isinstance(message, dict):
                message_text = message.get("text") or message.get("markdown") or ""
            else:
                message_text = str(message or "")

            # Location
            line_number = None
            end_line_number = None
            snippet_path = None
            locations = item.get("locations") or []
            if isinstance(locations, list) and locations:
                loc = locations[0] if isinstance(locations[0], dict) else {}
                phys = loc.get("physicalLocation") or {}
                if isinstance(phys, dict):
                    art = phys.get("artifactLocation") or {}
                    if isinstance(art, dict):
                        snippet_path = _uri_to_path(art.get("uri"))
                    region = phys.get("region") or {}
                    if isinstance(region, dict):
                        line_number = region.get("startLine")
                        end_line_number = region.get("endLine")

            code_snippet = _snippet(
                snippet_path,
                int(line_number) if line_number is not None else None,
                int(end_line_number) if end_line_number is not None else None,
            )

            more_info = rule.get("helpUri") if isinstance(rule, dict) else None
            if not more_info and isinstance(rule, dict):
                help_obj = rule.get("help")
                if isinstance(help_obj, dict):
                    more_info = help_obj.get("text") or help_obj.get("markdown")

            issues.append(
                {
                    "tool": "codeql",
                    "test_id": rule_id_s,
                    "test_name": rule.get("name") or rule_id_s,
                    "cwe_id": cwe_id,
                    "severity": severity,
                    "confidence": confidence,
                    "line_number": line_number,
                    "code": code_snippet,
                    "description": message_text,
                    "more_info": more_info,
                }
            )

        normalized: Dict[str, Any] = {
            "tool": "codeql",
            "issues": issues,
            "total_issues": len(issues),
            "metrics": {},
            "severity_breakdown": self._breakdown(issues, "severity", _SEVERITY_LEVELS),
            "confidence_breakdown": self._breakdown(issues, "confidence", _CONFIDENCE_LEVELS),
        }
        return normalized

    def _breakdown(
        self, issues: List[Dict[str, Any]], key: str, allowed: List[str]
    ) -> Dict[str, int]:
        breakdown = {level: 0 for level in allowed}
        for issue in issues:
            level = issue.get(key)
            if level in breakdown:
                breakdown[level] += 1
        return breakdown


def _issues_breakdown(
    issues: List[Dict[str, Any]], key: str, allowed: List[str]
) -> Dict[str, int]:
    breakdown = {level: 0 for level in allowed}
    for issue in issues:
        level = issue.get(key)
        if level in breakdown:
            breakdown[level] += 1
    return breakdown


class MultiSastAnalyzer:
    """
    Run multiple SAST analyzers in parallel and merge their findings.

    The returned schema matches individual analyzers, with a few additions:
      - tool: "multi"
      - tools: list of tool names
      - scans: per-tool raw scan dicts
      - errors: per-tool error strings (if any)
    """

    def __init__(
        self,
        analyzers: Dict[str, Any],
        *,
        prefix_test_ids: bool = True,
        fail_on_error: bool = True,
        max_workers: Optional[int] = None,
    ) -> None:
        if not isinstance(analyzers, dict) or not analyzers:
            raise ValueError("MultiSastAnalyzer requires a non-empty analyzers dict.")
        self.analyzers: Dict[str, Any] = {str(k).strip().lower(): v for k, v in analyzers.items() if k}
        if not self.analyzers:
            raise ValueError("MultiSastAnalyzer requires at least one analyzer.")

        self.prefix_test_ids = bool(prefix_test_ids)
        self.fail_on_error = bool(fail_on_error)
        self.max_workers = int(max_workers) if max_workers is not None else None

    def scan_code(self, code: str) -> Dict[str, Any]:
        results_by_tool: Dict[str, Dict[str, Any]] = {}

        def _run(tool: str, analyzer: Any) -> Dict[str, Any]:
            try:
                res = analyzer.scan_code(code)
                if not isinstance(res, dict):
                    return {
                        "tool": tool,
                        "issues": [],
                        "total_issues": 0,
                        "error": f"Analyzer returned non-dict result: {type(res).__name__}",
                    }
                out = dict(res)
                out["tool"] = tool
                return out
            except Exception as e:
                return {
                    "tool": tool,
                    "issues": [],
                    "total_issues": 0,
                    "error": f"{type(e).__name__}: {e}",
                }

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.max_workers or min(len(self.analyzers), 8)
        ) as ex:
            futs = {
                ex.submit(_run, tool, analyzer): tool
                for tool, analyzer in self.analyzers.items()
            }
            for fut in concurrent.futures.as_completed(futs):
                tool = futs[fut]
                try:
                    results_by_tool[tool] = fut.result()
                except Exception as e:
                    results_by_tool[tool] = {
                        "tool": tool,
                        "issues": [],
                        "total_issues": 0,
                        "error": f"{type(e).__name__}: {e}",
                    }

        merged_issues: List[Dict[str, Any]] = []
        errors: Dict[str, str] = {}

        for tool, scan in results_by_tool.items():
            if not isinstance(scan, dict):
                continue
            if scan.get("error"):
                errors[tool] = str(scan.get("error"))

            issues = scan.get("issues") or []
            if not isinstance(issues, list):
                issues = []

            for idx, issue in enumerate([i for i in issues if isinstance(i, dict)], start=1):
                merged_issues.append(self._normalize_issue(tool, issue, idx))

        merged_issues, dedup_info = self._deduplicate_issues(merged_issues, code)

        merged = {
            "tool": "multi",
            "tools": sorted(list(self.analyzers.keys())),
            "scans": results_by_tool,
            "issues": merged_issues,
            "total_issues": len(merged_issues),
            "severity_breakdown": _issues_breakdown(merged_issues, "severity", _SEVERITY_LEVELS),
            "confidence_breakdown": _issues_breakdown(
                merged_issues, "confidence", _CONFIDENCE_LEVELS
            ),
        }
        if dedup_info:
            merged["dedup"] = dedup_info
        if errors:
            merged["errors"] = errors
            if self.fail_on_error:
                merged["error"] = "; ".join(
                    [f"{tool}: {msg}" for tool, msg in sorted(errors.items()) if msg]
                )[:4000]

        return merged

    def _normalize_issue(self, tool: str, issue: Dict[str, Any], idx: int) -> Dict[str, Any]:
        out = dict(issue)
        out["tool"] = tool

        raw_test_id = out.get("test_id")
        raw_test_name = out.get("test_name")
        out.setdefault("test_id_raw", raw_test_id)
        out.setdefault("test_name_raw", raw_test_name)

        if self.prefix_test_ids:
            prefix = f"{tool}:"
            base = str(raw_test_id).strip() if raw_test_id is not None else ""
            if not base:
                base = str(raw_test_name).strip() if raw_test_name is not None else ""
            if not base:
                base = f"issue-{idx}"
            if not base.startswith(prefix):
                out["test_id"] = prefix + base

        return out

    def _deduplicate_issues(
        self, issues: List[Dict[str, Any]], code: str
    ) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        De-duplicate alerts that refer to the same underlying vulnerability.

        Motivation: when running multiple tools (Bandit + Semgrep + CodeQL), the same issue may be
        reported multiple times. Counting each tool hit as a separate vulnerability can inflate the
        reward penalty.

        Heuristic: treat issues as duplicates when they share the same (CWE, line_number, source line).
        This is conservative and avoids accidentally merging distinct issues on different lines.
        """
        if not issues:
            return issues, {}

        code_lines = (code or "").splitlines()

        deduped: List[Dict[str, Any]] = []
        by_key: Dict[str, Dict[str, Any]] = {}
        removed = 0

        for issue in issues:
            key = self._dedup_key(issue, code_lines)
            if not key:
                deduped.append(issue)
                continue

            existing = by_key.get(key)
            if existing is None:
                by_key[key] = issue
                deduped.append(issue)
                continue

            removed += 1
            self._merge_duplicate(existing, issue)

        info: Dict[str, Any] = {}
        if removed:
            info["removed_duplicates"] = removed
            info["total_issues_pre_dedup"] = len(issues)
            info["total_issues_post_dedup"] = len(deduped)
        return deduped, info

    def _dedup_key(self, issue: Dict[str, Any], code_lines: List[str]) -> Optional[str]:
        cwe = issue.get("cwe_id")
        if not cwe:
            return None

        line_number = issue.get("line_number")
        try:
            ln = int(line_number) if line_number is not None else None
        except Exception:
            ln = None
        if ln is None or ln <= 0:
            return None

        src_line = ""
        idx = ln - 1
        if 0 <= idx < len(code_lines):
            src_line = code_lines[idx]
        src_line_norm = " ".join(str(src_line or "").strip().split())

        return f"{str(cwe).strip().upper()}:{ln}:{src_line_norm}"

    def _merge_duplicate(self, base: Dict[str, Any], dup: Dict[str, Any]) -> None:
        def _rank(value: object, allowed: List[str]) -> int:
            try:
                return allowed.index(str(value or "").upper())
            except ValueError:
                return -1

        def _max_level(a: object, b: object, allowed: List[str]) -> str:
            return str(a).upper() if _rank(a, allowed) >= _rank(b, allowed) else str(b).upper()

        base["severity"] = _max_level(base.get("severity", "LOW"), dup.get("severity", "LOW"), _SEVERITY_LEVELS)
        base["confidence"] = _max_level(
            base.get("confidence", "LOW"), dup.get("confidence", "LOW"), _CONFIDENCE_LEVELS
        )

        # Keep a minimal trace of which tool hits were merged.
        base_test_id = base.get("test_id")
        dup_test_id = dup.get("test_id")
        base_tool = base.get("tool")
        dup_tool = dup.get("tool")

        test_ids = base.get("dedup_test_ids")
        if not isinstance(test_ids, list):
            test_ids = []
        tools = base.get("dedup_tools")
        if not isinstance(tools, list):
            tools = []

        if base_test_id and str(base_test_id) not in test_ids:
            test_ids.append(str(base_test_id))
        if dup_test_id and str(dup_test_id) not in test_ids:
            test_ids.append(str(dup_test_id))
        if base_tool and str(base_tool) not in tools:
            tools.append(str(base_tool))
        if dup_tool and str(dup_tool) not in tools:
            tools.append(str(dup_tool))

        if test_ids:
            base["dedup_test_ids"] = sorted(set(test_ids))
        if tools:
            base["dedup_tools"] = sorted(set(tools))

        base["dedup_count"] = int(base.get("dedup_count") or 0) + 1
