#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional


def _safe_int(value: object) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except Exception:
        return None


def _read_json(path: str) -> Optional[Dict[str, Any]]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            obj = json.load(f)
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None


def _write_json(path: str, payload: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def _primary_category(success: bool, reason: str) -> str:
    if success:
        return "success"
    if reason == "syntax_error":
        return "syntax_error"
    if reason == "sast_tool_error":
        return "sast_tool_error"
    if reason in {"unresolved_target_findings", "unresolved_off_target_findings"}:
        return "unresolved_sast_findings"
    if reason in {"functionality_low", "functionality_mismatch"}:
        return "functionality_mismatch"
    return "other"


def _to_list(value: str) -> List[str]:
    return [x for x in (value or "").split("|") if x.strip()]


def _load_code(run_dir: str, result: Optional[Dict[str, Any]]) -> str:
    sol_path = os.path.join(run_dir, "solution.py")
    if os.path.exists(sol_path):
        try:
            with open(sol_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            pass
    if isinstance(result, dict):
        return str(result.get("solution_code") or "")
    return ""


def _load_sast(run_dir: str, result: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    path = os.path.join(run_dir, "sast.json")
    scan = _read_json(path)
    if isinstance(scan, dict):
        return scan
    if isinstance(result, dict) and isinstance(result.get("sast"), dict):
        return result.get("sast") or {}
    return {}


def _load_failure_pattern(run_dir: str, result: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    path = os.path.join(run_dir, "failure_pattern.json")
    fp = _read_json(path)
    if isinstance(fp, dict):
        return fp
    if isinstance(result, dict) and isinstance(result.get("failure_pattern"), dict):
        return result.get("failure_pattern") or {}
    return {}


def _load_pattern_analysis(run_dir: str, result: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    path = os.path.join(run_dir, "pattern_analysis.json")
    pa = _read_json(path)
    if isinstance(pa, dict):
        return pa
    if isinstance(result, dict) and isinstance(result.get("pattern_analysis"), dict):
        return result.get("pattern_analysis") or {}
    return {}


def backfill_run(run_dir: str) -> Dict[str, Any]:
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    src = os.path.join(root, "src")
    if src not in sys.path:
        sys.path.insert(0, src)
    from issue_snippets import build_issue_snippets  # local import

    result_path = os.path.join(run_dir, "result.json")
    result = _read_json(result_path)

    code = _load_code(run_dir, result)
    scan = _load_sast(run_dir, result)
    fp = _load_failure_pattern(run_dir, result)
    pa = _load_pattern_analysis(run_dir, result)

    success = bool(result.get("success")) if isinstance(result, dict) else False
    primary_reason = str(fp.get("primary_reason") or "")
    computed_category = _primary_category(success, primary_reason)

    issues = scan.get("issues") if isinstance(scan, dict) else []
    issues = issues if isinstance(issues, list) else []
    issues = [i for i in issues if isinstance(i, dict)]

    evidence = build_issue_snippets(code, issues, radius=2, max_issues=8) if code else []

    issue_snippets_path = os.path.join(run_dir, "issue_snippets.json")
    if code and isinstance(scan, dict):
        payload = {
            "tool": scan.get("tool"),
            "total_issues": scan.get("total_issues"),
            "issue_snippets": evidence,
        }
        _write_json(issue_snippets_path, payload)

    # Merge deterministic fields into pattern_analysis.json for consistency.
    pa_out = dict(pa or {})
    pa_out["success"] = success
    pa_out["primary_category"] = computed_category
    pa_out["primary_reason"] = primary_reason or None
    pa_out["persistent_sast_tests"] = _to_list(str(fp.get("persistent_test_ids") or ""))
    pa_out["resolved_sast_tests"] = _to_list(str(fp.get("resolved_test_ids") or ""))
    pa_out["introduced_sast_tests"] = _to_list(str(fp.get("introduced_test_ids") or ""))
    pa_out["attempts_executed"] = _safe_int(fp.get("attempts_executed"))
    pa_out["fixer_attempts"] = _safe_int(fp.get("fixer_attempts"))
    pa_out["evidence"] = evidence

    # Keep older keys stable if missing.
    pa_out.setdefault("tags", [])
    pa_out.setdefault("suggested_actions", [])
    pa_out.setdefault("confidence", "MEDIUM")
    pa_out.setdefault("summary", "")

    _write_json(os.path.join(run_dir, "pattern_analysis.json"), pa_out)

    # Optionally update result.json to match (best-effort).
    if isinstance(result, dict):
        result["pattern_analysis"] = pa_out
        result["failure_pattern"] = fp
        try:
            _write_json(result_path, result)
        except Exception:
            pass

    return {"run_dir": run_dir, "wrote": ["issue_snippets.json", "pattern_analysis.json"]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--phase-three-dir",
        required=True,
        help="Path to a PHASE_THREE directory (containing runs/...)",
    )
    args = ap.parse_args()

    root = os.path.abspath(str(args.phase_three_dir))
    runs_root = os.path.join(root, "runs")
    if not os.path.isdir(runs_root):
        raise SystemExit(f"Expected runs/ under: {root}")

    updated = 0
    for dirpath, _dirnames, filenames in os.walk(runs_root):
        if "result.json" not in filenames:
            continue
        backfill_run(dirpath)
        updated += 1

    print(f"Backfilled {updated} run directories under {runs_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
