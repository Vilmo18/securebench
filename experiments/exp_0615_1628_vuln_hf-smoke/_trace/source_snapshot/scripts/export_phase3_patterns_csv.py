#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


def _project_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))


def _ensure_src_on_path() -> None:
    root = _project_root()
    src = os.path.join(root, "src")
    if src not in sys.path:
        sys.path.insert(0, src)


_ensure_src_on_path()

from scenario_conditions import (
    axis_order,
    condition_axis_label,
    condition_axis_order_index,
    condition_order_index,
    normalize_condition,
)

_DIFF_ORDER = list(axis_order()) + ["Legacy Levels", "Unknown"]


def _write_json(path: str, payload: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def _write_csv(path: str, rows: List[Dict[str, Any]]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not rows:
        with open(path, "w", encoding="utf-8") as f:
            f.write("")
        return
    fieldnames = sorted({k for r in rows for k in r.keys()})
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


def _pipe_join(items: Any) -> str:
    if items is None:
        return ""
    if isinstance(items, str):
        return items.strip()
    if isinstance(items, (list, tuple, set)):
        out: List[str] = []
        for it in items:
            s = str(it or "").strip()
            if s:
                out.append(s)
        return "|".join(out)
    return str(items).strip()


def _norm_diff(diff: Any) -> str:
    return normalize_condition(diff)


def _safe_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except Exception:
        try:
            return int(float(value))
        except Exception:
            return None


def _top_k_from_counts(counts: Dict[str, Any], *, k: int = 5) -> List[Tuple[str, int]]:
    items: List[Tuple[str, int]] = []
    for key, val in (counts or {}).items():
        ks = str(key or "").strip()
        if not ks:
            continue
        iv = _safe_int(val) or 0
        items.append((ks, int(iv)))
    items.sort(key=lambda kv: kv[1], reverse=True)
    return items[: max(0, int(k))]


def export_phase3_patterns_csv(
    *,
    phase_three_dir: str,
    out_dir: Optional[str] = None,
    max_examples_per_pattern: int = 3,
    max_evidence_per_example: int = 2,
) -> Dict[str, str]:
    _ensure_src_on_path()
    from phase3_patterns import build_phase3_pattern_report  # local import

    phase_three_dir = os.path.abspath(str(phase_three_dir))
    runs_root = os.path.join(phase_three_dir, "runs")
    if not os.path.isdir(runs_root):
        raise SystemExit(f"Expected runs/ under: {phase_three_dir}")

    report = build_phase3_pattern_report(
        phase_three_dir,
        max_examples_per_pattern=max_examples_per_pattern,
        max_evidence_per_example=max_evidence_per_example,
    )

    # Write Prism-style JSON artifacts at the PHASE_THREE root for easy triage.
    out_pattern_summary = os.path.join(phase_three_dir, "pattern_summary.json")
    out_detailed = os.path.join(phase_three_dir, "detailed_report.json")
    _write_json(out_pattern_summary, report.get("pattern_summary") or {})
    _write_json(out_detailed, report)

    analysis_dir = os.path.abspath(out_dir) if out_dir else os.path.join(phase_three_dir, "analysis", "phase3_patterns")
    os.makedirs(analysis_dir, exist_ok=True)

    runs: List[Dict[str, Any]] = report.get("runs") if isinstance(report.get("runs"), list) else []
    patterns: List[Dict[str, Any]] = report.get("patterns") if isinstance(report.get("patterns"), list) else []

    run_rows: List[Dict[str, Any]] = []
    run_pattern_rows: List[Dict[str, Any]] = []
    run_evidence_rows: List[Dict[str, Any]] = []

    tag_counts_by_diff: Dict[Tuple[str, str], int] = defaultdict(int)
    persistent_counts_by_diff: Dict[Tuple[str, str], int] = defaultdict(int)
    category_counts_by_diff: Dict[Tuple[str, str], int] = defaultdict(int)
    reason_counts_by_diff: Dict[Tuple[str, str], int] = defaultdict(int)

    for r in runs:
        if not isinstance(r, dict):
            continue
        diff = _norm_diff(r.get("difficulty"))
        condition_axis = condition_axis_label(diff)
        run_path = str(r.get("run_path") or "")
        node_id = r.get("node_id")
        concepts = r.get("concepts")
        tags = r.get("tags") if isinstance(r.get("tags"), list) else []
        persistent = r.get("persistent_sast_tests") if isinstance(r.get("persistent_sast_tests"), list) else []
        primary_category = str(r.get("primary_category") or "")
        primary_reason = str(r.get("primary_reason") or "")

        patterns_for_run = r.get("patterns") if isinstance(r.get("patterns"), list) else []
        pattern_ids = sorted(
            {str(p.get("pattern_id") or "").strip() for p in patterns_for_run if isinstance(p, dict) and str(p.get("pattern_id") or "").strip()}
        )
        cwe_ids = sorted(
            {str(p.get("cwe_id") or "").strip() for p in patterns_for_run if isinstance(p, dict) and str(p.get("cwe_id") or "").strip()}
        )

        run_rows.append(
            {
                "run_path": run_path,
                "node_id": node_id,
                "difficulty": diff,
                "condition_axis": condition_axis,
                "concepts": _pipe_join(concepts),
                "success": bool(r.get("success")),
                "attempts_till_success": r.get("attempts_till_success"),
                "total_issues": r.get("total_issues"),
                "primary_category": primary_category,
                "primary_reason": primary_reason,
                "tags": _pipe_join(tags),
                "persistent_sast_tests": _pipe_join(persistent),
                "pattern_count": len(pattern_ids),
                "pattern_ids": _pipe_join(pattern_ids),
                "cwe_ids": _pipe_join(cwe_ids),
            }
        )

        for t in tags:
            ts = str(t or "").strip()
            if ts:
                tag_counts_by_diff[(diff, ts)] += 1
        for t in persistent:
            ts = str(t or "").strip()
            if ts:
                persistent_counts_by_diff[(diff, ts)] += 1
        if primary_category.strip():
            category_counts_by_diff[(diff, primary_category.strip())] += 1
        if primary_reason.strip():
            reason_counts_by_diff[(diff, primary_reason.strip())] += 1

        for p in patterns_for_run:
            if not isinstance(p, dict):
                continue
            run_pattern_rows.append(
                {
                    "run_path": run_path,
                    "node_id": node_id,
                    "difficulty": diff,
                    "condition_axis": condition_axis,
                    "concepts": _pipe_join(concepts),
                    "success": bool(r.get("success")),
                    "primary_category": primary_category,
                    "primary_reason": primary_reason,
                    "pattern_id": p.get("pattern_id"),
                    "cwe_id": p.get("cwe_id"),
                    "code_hash": p.get("code_hash"),
                    "code_signatures": _pipe_join(p.get("code_signatures")),
                    "sast_tests": _pipe_join(p.get("sast_tests")),
                    "evidence_count": len(p.get("evidence")) if isinstance(p.get("evidence"), list) else 0,
                }
            )

            evidence_list = p.get("evidence") if isinstance(p.get("evidence"), list) else []
            for ev in evidence_list:
                if not isinstance(ev, dict):
                    continue
                run_evidence_rows.append(
                    {
                        "run_path": run_path,
                        "node_id": node_id,
                        "difficulty": diff,
                        "condition_axis": condition_axis,
                        "pattern_id": p.get("pattern_id"),
                        "cwe_id": p.get("cwe_id"),
                        "tool": ev.get("tool"),
                        "test_id": ev.get("test_id"),
                        "severity": ev.get("severity"),
                        "confidence": ev.get("confidence"),
                        "line_number": ev.get("line_number"),
                        "signature": ev.get("signature"),
                        "description": ev.get("description"),
                        "context": ev.get("context"),
                    }
                )

    pattern_rows: List[Dict[str, Any]] = []
    example_rows: List[Dict[str, Any]] = []
    for p in patterns:
        if not isinstance(p, dict):
            continue
        diff_counts = p.get("difficulties") if isinstance(p.get("difficulties"), dict) else {}
        sast_counts = p.get("sast_tests") if isinstance(p.get("sast_tests"), dict) else {}
        top_tests = _top_k_from_counts(sast_counts, k=5)
        row: Dict[str, Any] = {
            "pattern_id": p.get("pattern_id"),
            "cwe_id": p.get("cwe_id"),
            "frequency": p.get("frequency"),
            "code_signatures": _pipe_join(p.get("code_signatures")),
            "top_sast_tests": _pipe_join([t for t, _c in top_tests]),
            "top_sast_test": top_tests[0][0] if top_tests else "",
            "top_sast_test_count": top_tests[0][1] if top_tests else 0,
            "difficulties_json": json.dumps(diff_counts, ensure_ascii=False),
            "sast_tests_json": json.dumps(sast_counts, ensure_ascii=False),
        }
        diff_counts_by_axis: Dict[str, int] = defaultdict(int)
        for diff_key, count in diff_counts.items():
            diff_counts_by_axis[condition_axis_label(diff_key)] += int(_safe_int(count) or 0)
        for axis in _DIFF_ORDER:
            row[f"axis_{axis.replace(' ', '_').replace('/', '_')}"] = int(
                diff_counts_by_axis.get(axis) or 0
            )
        pattern_rows.append(row)

        examples = p.get("examples") if isinstance(p.get("examples"), list) else []
        for ex in examples:
            if not isinstance(ex, dict):
                continue
            evs = ex.get("evidence") if isinstance(ex.get("evidence"), list) else []
            ex_diff = _norm_diff(ex.get("difficulty"))
            example_rows.append(
                {
                    "pattern_id": p.get("pattern_id"),
                    "cwe_id": p.get("cwe_id"),
                    "run_path": ex.get("run_path"),
                    "node_id": ex.get("node_id"),
                    "difficulty": ex_diff,
                    "condition_axis": condition_axis_label(ex_diff),
                    "concepts": _pipe_join(ex.get("concepts")),
                    "success": bool(ex.get("success")),
                    "primary_reason": ex.get("primary_reason"),
                    "evidence_test_ids": _pipe_join([e.get("test_id") for e in evs if isinstance(e, dict)]),
                    "evidence_signatures": _pipe_join([e.get("signature") for e in evs if isinstance(e, dict)]),
                    "evidence_line_numbers": _pipe_join([e.get("line_number") for e in evs if isinstance(e, dict)]),
                }
            )

    def _counts_to_rows(counts: Dict[Tuple[str, str], int], *, col: str) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for (diff, key), cnt in counts.items():
            out.append(
                {
                    "difficulty": diff,
                    "condition_axis": condition_axis_label(diff),
                    col: key,
                    "count": int(cnt),
                }
            )
        out.sort(
            key=lambda r: (
                condition_axis_order_index(r.get("difficulty")),
                condition_order_index(r.get("difficulty")),
                -int(r.get("count") or 0),
                str(r.get(col) or ""),
            )
        )
        return out

    paths = {
        "pattern_summary_json": out_pattern_summary,
        "detailed_report_json": out_detailed,
        "runs_csv": os.path.join(analysis_dir, "runs.csv"),
        "run_patterns_csv": os.path.join(analysis_dir, "run_patterns.csv"),
        "run_evidence_csv": os.path.join(analysis_dir, "run_evidence.csv"),
        "patterns_csv": os.path.join(analysis_dir, "patterns.csv"),
        "pattern_examples_csv": os.path.join(analysis_dir, "pattern_examples.csv"),
        "tags_by_difficulty_csv": os.path.join(analysis_dir, "tags_by_difficulty.csv"),
        "persistent_tests_by_difficulty_csv": os.path.join(analysis_dir, "persistent_tests_by_difficulty.csv"),
        "categories_by_difficulty_csv": os.path.join(analysis_dir, "categories_by_difficulty.csv"),
        "reasons_by_difficulty_csv": os.path.join(analysis_dir, "reasons_by_difficulty.csv"),
    }

    _write_csv(paths["runs_csv"], run_rows)
    _write_csv(paths["run_patterns_csv"], run_pattern_rows)
    _write_csv(paths["run_evidence_csv"], run_evidence_rows)
    _write_csv(paths["patterns_csv"], pattern_rows)
    _write_csv(paths["pattern_examples_csv"], example_rows)
    _write_csv(paths["tags_by_difficulty_csv"], _counts_to_rows(tag_counts_by_diff, col="tag"))
    _write_csv(
        paths["persistent_tests_by_difficulty_csv"],
        _counts_to_rows(persistent_counts_by_diff, col="test_id"),
    )
    _write_csv(paths["categories_by_difficulty_csv"], _counts_to_rows(category_counts_by_diff, col="primary_category"))
    _write_csv(paths["reasons_by_difficulty_csv"], _counts_to_rows(reason_counts_by_diff, col="primary_reason"))

    return paths


def main() -> int:
    ap = argparse.ArgumentParser(description="Aggregate PHASE_THREE pattern analysis into JSON + CSV reports.")
    ap.add_argument(
        "--phase-three-dir",
        required=True,
        help="Path to a PHASE_THREE directory (containing runs/...)",
    )
    ap.add_argument(
        "--out-dir",
        default=None,
        help="Output directory for CSVs (default: <PHASE_THREE>/analysis/phase3_patterns/)",
    )
    ap.add_argument("--max-examples-per-pattern", type=int, default=3)
    ap.add_argument("--max-evidence-per-example", type=int, default=2)
    args = ap.parse_args()

    paths = export_phase3_patterns_csv(
        phase_three_dir=str(args.phase_three_dir),
        out_dir=str(args.out_dir) if args.out_dir else None,
        max_examples_per_pattern=int(args.max_examples_per_pattern),
        max_evidence_per_example=int(args.max_evidence_per_example),
    )
    print("Wrote:")
    for k, v in paths.items():
        print(f"- {k}: {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
