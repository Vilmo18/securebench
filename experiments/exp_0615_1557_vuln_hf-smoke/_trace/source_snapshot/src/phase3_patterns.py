from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import warnings
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


def _sha16(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8", errors="ignore")).hexdigest()[:16]


def _read_json(path: str) -> Optional[Dict[str, Any]]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            obj = json.load(f)
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None


def _read_text(path: str) -> Optional[str]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return None


def _safe_int(value: object) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except Exception:
        return None


def _dedup_preserve_order(items: Sequence[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for it in items:
        s = str(it or "").strip()
        if not s or s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out


def _extract_ast_features(code: str) -> Dict[str, Any]:
    try:
        with warnings.catch_warnings():
            # LLM-generated code sometimes contains regex strings like "\w" without raw-strings.
            # Those can emit SyntaxWarning ("invalid escape sequence") during parsing.
            warnings.simplefilter("ignore", SyntaxWarning)
            tree = ast.parse(code or "")
    except Exception:
        return {"error": "parse_error", "functions_called": [], "modules_imported": []}

    functions_called: List[str] = []
    modules_imported: List[str] = []
    control_structures: List[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                functions_called.append(func.id)
            elif isinstance(func, ast.Attribute):
                functions_called.append(func.attr)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name:
                    modules_imported.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                modules_imported.append(node.module)
        elif isinstance(node, (ast.If, ast.For, ast.While, ast.Try, ast.With)):
            control_structures.append(type(node).__name__)

    # Remove duplicates while keeping some stability.
    functions_called_u = sorted(set(functions_called))
    modules_imported_u = sorted(set(modules_imported))
    control_structures_u = sorted(set(control_structures))

    return {
        "functions_called": functions_called_u,
        "modules_imported": modules_imported_u,
        "control_structures": control_structures_u,
        "complexity": len(control_structures_u) + len(functions_called_u),
    }


_SIGNATURE_PATTERNS: Dict[str, str] = {
    "eval_exec": r"\b(eval|exec)\s*\(",
    "pickle_load": r"\bpickle\.loads?\s*\(",
    "yaml_unsafe_load": r"\byaml\.load\s*\(",
    "subprocess_shell": r"\bsubprocess\.[^(]*\([^)]*shell\s*=\s*True",
    "os_system": r"\bos\.system\s*\(",
    "tarfile_extractall": r"\btarfile\.[^(]*\([^)]*\)\.extractall\s*\(",
    "zipfile_extractall": r"\bzipfile\.[^(]*\([^)]*\)\.extractall\s*\(",
    "etree_fromstring": r"\bET\.fromstring\s*\(",
    "lxml_fromstring": r"\betree\.fromstring\s*\(",
    "jinja2_autoescape_off": r"\b(autoescape\s*=\s*False|Environment\\([^)]*autoescape\\s*=\\s*False)",
    "sql_string_format": r"(SELECT|INSERT|UPDATE|DELETE)[^\\n]{0,200}\\.(format|%|\\+)",
    "requests_no_timeout": r"\brequests\.(get|post|put|delete|patch)\s*\([^)]*\\)(?![^\\n]{0,120}timeout\\s*=)",
}


def _extract_code_signatures(code: str) -> List[str]:
    text = code or ""
    out: List[str] = []
    for name, pattern in _SIGNATURE_PATTERNS.items():
        try:
            if re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE):
                out.append(name)
        except re.error:
            continue
    return sorted(set(out))


def _generate_pattern_id(cwe_id: str, ast_features: Dict[str, Any], signatures: List[str]) -> str:
    key_funcs = sorted(ast_features.get("functions_called") or [])[:3]
    key_sigs = sorted(signatures or [])[:3]
    parts = [str(cwe_id or "CWE-UNKNOWN").strip().upper()] + key_funcs + key_sigs
    return _sha16("_".join([p for p in parts if p]))


def _iter_run_dirs(phase_three_dir: str) -> Iterable[str]:
    runs_root = os.path.join(os.path.abspath(phase_three_dir), "runs")
    if not os.path.isdir(runs_root):
        return []
    for dirpath, _dirnames, filenames in os.walk(runs_root):
        if "result.json" in filenames:
            yield dirpath


def _run_relpath(phase_three_dir: str, run_dir: str) -> str:
    try:
        return os.path.relpath(run_dir, os.path.abspath(phase_three_dir))
    except Exception:
        return run_dir


def _evidence_list(run_dir: str, result: Dict[str, Any]) -> List[Dict[str, Any]]:
    pa = _read_json(os.path.join(run_dir, "pattern_analysis.json"))
    if not isinstance(pa, dict):
        pa = result.get("pattern_analysis") if isinstance(result.get("pattern_analysis"), dict) else {}
    evidence = pa.get("evidence") if isinstance(pa, dict) else None
    if isinstance(evidence, list):
        ev = [i for i in evidence if isinstance(i, dict)]
        if ev:
            return ev

    snips = _read_json(os.path.join(run_dir, "issue_snippets.json")) or {}
    evidence2 = snips.get("issue_snippets")
    if isinstance(evidence2, list):
        return [i for i in evidence2 if isinstance(i, dict)]
    return []


@dataclass
class Phase3Pattern:
    pattern_id: str
    cwe_id: str
    code_signatures: List[str]
    frequency: int
    difficulties: Dict[str, int]
    sast_tests: Dict[str, int]
    examples: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "cwe_id": self.cwe_id,
            "code_signatures": self.code_signatures,
            "frequency": self.frequency,
            "difficulties": self.difficulties,
            "sast_tests": self.sast_tests,
            "examples": self.examples,
        }


def build_phase3_pattern_report(
    phase_three_dir: str,
    *,
    max_examples_per_pattern: int = 3,
    max_evidence_per_example: int = 2,
) -> Dict[str, Any]:
    phase_three_dir = os.path.abspath(str(phase_three_dir))
    generated_at = datetime.now().isoformat(timespec="seconds")

    patterns: Dict[str, Phase3Pattern] = {}
    pattern_seen_runs: Dict[str, set[str]] = defaultdict(set)
    runs_out: List[Dict[str, Any]] = []
    runs_by_primary_category: Dict[str, int] = defaultdict(int)
    runs_by_primary_reason: Dict[str, int] = defaultdict(int)
    persistent_sast_test_counts: Dict[str, int] = defaultdict(int)
    tag_counts: Dict[str, int] = defaultdict(int)

    for run_dir in sorted(list(_iter_run_dirs(phase_three_dir))):
        meta = _read_json(os.path.join(run_dir, "meta.json")) or {}
        result = _read_json(os.path.join(run_dir, "result.json")) or {}
        pa = _read_json(os.path.join(run_dir, "pattern_analysis.json")) or {}
        fp = _read_json(os.path.join(run_dir, "failure_pattern.json")) or {}

        code = _read_text(os.path.join(run_dir, "solution.py"))
        if code is None:
            code = str(result.get("solution_code") or "")

        evidence = _evidence_list(run_dir, result)

        ast_features = _extract_ast_features(code or "")
        code_signatures = _extract_code_signatures(code or "")
        code_hash = _sha16(code or "")

        difficulty = str(meta.get("difficulty") or "").strip() or "unknown"
        concepts = meta.get("concepts")
        if not isinstance(concepts, list):
            concepts = result.get("target_cwes") if isinstance(result.get("target_cwes"), list) else []

        run_path = _run_relpath(phase_three_dir, run_dir)

        run_primary_category = None
        run_primary_reason = None
        run_tags: List[str] = []
        run_persistent: List[str] = []
        if isinstance(pa, dict):
            run_primary_category = pa.get("primary_category")
            run_primary_reason = pa.get("primary_reason")
            tags = pa.get("tags")
            if isinstance(tags, list):
                run_tags = [str(t) for t in tags if str(t).strip()][:12]
            pers = pa.get("persistent_sast_tests")
            if isinstance(pers, list):
                run_persistent = [str(x) for x in pers if str(x).strip()]

        patterns_for_run: List[Dict[str, Any]] = []
        issues_by_cwe: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for issue in evidence:
            cwe = issue.get("cwe_id") or "CWE-UNKNOWN"
            issues_by_cwe[str(cwe).strip().upper()].append(issue)

        for cwe_id, issues in sorted(issues_by_cwe.items()):
            pattern_id = _generate_pattern_id(cwe_id, ast_features, code_signatures)
            patterns_for_run.append(
                {
                    "pattern_id": pattern_id,
                    "cwe_id": cwe_id,
                    "code_hash": code_hash,
                    "code_signatures": code_signatures,
                    "ast_features": ast_features,
                    "sast_tests": _dedup_preserve_order(
                        [str(i.get("test_id") or "") for i in issues if str(i.get("test_id") or "").strip()]
                    ),
                    "evidence": [
                        {
                            "signature": i.get("signature"),
                            "tool": i.get("tool"),
                            "test_id": i.get("test_id"),
                            "severity": i.get("severity"),
                            "confidence": i.get("confidence"),
                            "line_number": i.get("line_number"),
                            "description": i.get("description"),
                            "context": i.get("context"),
                        }
                        for i in issues[: max(1, int(max_evidence_per_example))]
                    ],
                }
            )

            pat = patterns.get(pattern_id)
            if pat is None:
                pat = Phase3Pattern(
                    pattern_id=pattern_id,
                    cwe_id=cwe_id,
                    code_signatures=code_signatures,
                    frequency=0,
                    difficulties={},
                    sast_tests={},
                    examples=[],
                )
                patterns[pattern_id] = pat

            # Count each pattern at most once per run (avoid overweighting repeated lines in one file).
            if run_path not in pattern_seen_runs[pattern_id]:
                pattern_seen_runs[pattern_id].add(run_path)
                pat.frequency += 1
                pat.difficulties[difficulty] = int(pat.difficulties.get(difficulty) or 0) + 1

            for issue in issues:
                tid = issue.get("test_id")
                if not tid:
                    continue
                t = str(tid).strip()
                if not t:
                    continue
                pat.sast_tests[t] = int(pat.sast_tests.get(t) or 0) + 1

            if len(pat.examples) < int(max_examples_per_pattern):
                pat.examples.append(
                    {
                        "run_path": run_path,
                        "node_id": meta.get("node_id"),
                        "difficulty": difficulty,
                        "concepts": concepts,
                        "success": meta.get("success"),
                        "primary_reason": (fp.get("primary_reason") if isinstance(fp, dict) else None)
                        or run_primary_reason,
                        "evidence": [
                            {
                                "signature": i.get("signature"),
                                "test_id": i.get("test_id"),
                                "cwe_id": i.get("cwe_id"),
                                "line_number": i.get("line_number"),
                                "context": i.get("context"),
                            }
                            for i in issues[: max(1, int(max_evidence_per_example))]
                        ],
                    }
                )

        runs_out.append(
            {
                "run_path": run_path,
                "node_id": meta.get("node_id"),
                "difficulty": difficulty,
                "concepts": concepts,
                "success": bool(meta.get("success")),
                "attempts_till_success": _safe_int(meta.get("attempts_till_success"))
                or _safe_int(result.get("attempts_till_success")),
                "total_issues": _safe_int(meta.get("total_issues")),
                "primary_category": run_primary_category,
                "primary_reason": (fp.get("primary_reason") if isinstance(fp, dict) else None)
                or run_primary_reason,
                "tags": run_tags,
                "persistent_sast_tests": run_persistent,
                "patterns": patterns_for_run,
            }
        )

        cat = str(run_primary_category or "unknown").strip() or "unknown"
        runs_by_primary_category[cat] += 1
        reason = (
            (fp.get("primary_reason") if isinstance(fp, dict) else None) or run_primary_reason
        )
        reason_s = str(reason or "unknown").strip() or "unknown"
        runs_by_primary_reason[reason_s] += 1
        for t in run_persistent:
            persistent_sast_test_counts[str(t)] += 1
        for t in run_tags:
            tag_counts[str(t)] += 1

    # Build Prism-style pattern_summary.json (keeps the same keys for easy comparison).
    patterns_by_cwe: Dict[str, int] = defaultdict(int)
    patterns_by_difficulty: Dict[str, int] = defaultdict(int)
    for pat in patterns.values():
        patterns_by_cwe[pat.cwe_id] += 1
        for diff in pat.difficulties:
            patterns_by_difficulty[diff] += 1

    most_common = sorted(((p.pattern_id, p.frequency) for p in patterns.values()), key=lambda x: x[1], reverse=True)
    avg_freq = (sum(p.frequency for p in patterns.values()) / len(patterns)) if patterns else 0.0

    pattern_summary = {
        "total_patterns": len(patterns),
        "unique_cwes": len({p.cwe_id for p in patterns.values()}),
        "patterns_by_cwe": dict(sorted(patterns_by_cwe.items())),
        "patterns_by_difficulty": dict(sorted(patterns_by_difficulty.items())),
        "most_common_patterns": most_common[:10],
        "avg_frequency": avg_freq,
        # Extended keys (non-Prism) for easier triage.
        "total_runs": len(runs_out),
        "runs_with_any_pattern": sum(1 for r in runs_out if r.get("patterns")),
        "runs_by_primary_category": dict(
            sorted(runs_by_primary_category.items(), key=lambda x: x[1], reverse=True)
        ),
        "runs_by_primary_reason": dict(
            sorted(runs_by_primary_reason.items(), key=lambda x: x[1], reverse=True)
        ),
        "top_persistent_sast_tests": sorted(
            persistent_sast_test_counts.items(), key=lambda x: x[1], reverse=True
        )[:20],
        "top_tags": sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:20],
    }

    patterns_out = sorted((p.to_dict() for p in patterns.values()), key=lambda d: int(d.get("frequency") or 0), reverse=True)

    return {
        "phase_three_dir": phase_three_dir,
        "generated_at": generated_at,
        "pattern_summary": pattern_summary,
        "patterns": patterns_out,
        "runs": runs_out,
    }


def write_phase3_reports(phase_three_dir: str) -> Dict[str, str]:
    report = build_phase3_pattern_report(phase_three_dir)
    out_summary = os.path.join(os.path.abspath(phase_three_dir), "pattern_summary.json")
    out_detail = os.path.join(os.path.abspath(phase_three_dir), "detailed_report.json")

    with open(out_summary, "w", encoding="utf-8") as f:
        json.dump(report.get("pattern_summary") or {}, f, indent=2, ensure_ascii=False)
    with open(out_detail, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    return {"pattern_summary": out_summary, "detailed_report": out_detail}
