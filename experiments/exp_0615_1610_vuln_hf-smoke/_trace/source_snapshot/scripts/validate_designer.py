#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

import sys


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from attack_surface_conditions import normalize_attack_surface
from scenario_conditions import axis_order, condition_axis_label, condition_order_index, normalize_condition
from scenario_quality import (
    extract_declared_difficulty,
    extract_declared_surface,
    validate_scenario_difficulty,
    validate_scenario_dimensions,
    validate_scenario_surface,
)
_DIFF_ORDER = list(axis_order())
_DIFF_TO_ORD = {d: i for i, d in enumerate(_DIFF_ORDER)}


def _project_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))


def _safe_float(x: Any) -> Optional[float]:
    if x is None:
        return None
    try:
        return float(x)
    except Exception:
        return None


def _safe_int(x: Any) -> Optional[int]:
    if x is None:
        return None
    try:
        return int(float(x))
    except Exception:
        return None


def _read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _iter_jsonl(path: str) -> Iterable[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            if isinstance(rec, dict):
                yield rec


def _severity_key(value: Any) -> Optional[str]:
    raw = normalize_condition(value)
    return raw if raw != "unknown" else None


def _spearman(xs: List[float], ys: List[float]) -> Optional[float]:
    if len(xs) != len(ys) or len(xs) < 3:
        return None

    def _rank(values: List[float]) -> List[float]:
        # Average ranks for ties.
        indexed = sorted(enumerate(values), key=lambda kv: kv[1])
        ranks = [0.0] * len(values)
        i = 0
        while i < len(indexed):
            j = i
            while j < len(indexed) and indexed[j][1] == indexed[i][1]:
                j += 1
            avg = (i + 1 + j) / 2.0
            for k in range(i, j):
                ranks[indexed[k][0]] = avg
            i = j
        return ranks

    rx = _rank(xs)
    ry = _rank(ys)
    mx = statistics.mean(rx)
    my = statistics.mean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    denx = sum((a - mx) ** 2 for a in rx)
    deny = sum((b - my) ** 2 for b in ry)
    den = (denx * deny) ** 0.5
    if den <= 0:
        return None
    return float(num / den)


@dataclass
class DesignerMismatchRow:
    run_dir: str
    meta_difficulty: Optional[str]
    declared_difficulty: Optional[str]
    meta_surface: Optional[str]
    declared_surface: Optional[str]
    concepts: str
    phase: Optional[int]


@dataclass
class DesignerStructureRow:
    run_dir: str
    meta_difficulty: Optional[str]
    declared_difficulty: Optional[str]
    meta_surface: Optional[str]
    declared_surface: Optional[str]
    reasons: List[str]
    concepts: str
    phase: Optional[int]


def validate_problem_designer(
    *,
    experiments_dir: str,
) -> Dict[str, Any]:
    """
    Validates whether the challenge designer follows the requested axis metadata by comparing:
      - meta difficulty / attack_surface (from runs_index.jsonl)
      - declared values inside problem.md (`Difficulty: ...`, `Attack Surface: ...`)

    Outputs aggregated mismatch rates and a few examples.
    """
    mismatches: List[DesignerMismatchRow] = []
    structure_violations: List[DesignerStructureRow] = []
    total = 0
    declared_missing = 0

    for root, _dirs, files in os.walk(experiments_dir):
        if "runs_index.jsonl" not in files:
            continue
        idx_path = os.path.join(root, "runs_index.jsonl")
        for rec in _iter_jsonl(idx_path):
            run_dir = rec.get("run_dir")
            if not isinstance(run_dir, str) or not run_dir:
                continue
            meta_diff_s = _severity_key(rec.get("difficulty"))
            meta_surface_s = normalize_attack_surface(rec.get("attack_surface"))
            if meta_surface_s == "unknown":
                meta_surface_s = None

            problem_path = os.path.join(run_dir, "problem.md")
            if not os.path.exists(problem_path):
                continue

            problem_md = _read_text(problem_path)
            declared_diff = _severity_key(extract_declared_difficulty(problem_md))
            declared_surface = extract_declared_surface(problem_md)
            declared_surface = None if declared_surface in {None, "unknown"} else declared_surface

            total += 1
            if meta_diff_s and meta_surface_s:
                if declared_diff is None or declared_surface is None:
                    declared_missing += 1
            elif meta_diff_s:
                if declared_diff is None:
                    declared_missing += 1
            elif declared_surface is None:
                declared_missing += 1
            validation = (
                validate_scenario_dimensions(
                    problem_md,
                    expected_difficulty=meta_diff_s,
                    expected_surface=meta_surface_s,
                    expected_cwes=rec.get("concepts") or [],
                )
                if meta_diff_s and meta_surface_s
                else validate_scenario_difficulty(
                    problem_md,
                    expected_difficulty=meta_diff_s,
                )
                if meta_diff_s
                else validate_scenario_surface(
                    problem_md,
                    expected_surface=meta_surface_s,
                    expected_cwes=rec.get("concepts") or [],
                )
            )
            if not validation.get("is_valid"):
                structure_violations.append(
                    DesignerStructureRow(
                        run_dir=run_dir,
                        meta_difficulty=meta_diff_s,
                        declared_difficulty=declared_diff,
                        meta_surface=meta_surface_s,
                        declared_surface=declared_surface,
                        reasons=[str(r) for r in (validation.get("reasons") or [])[:5]],
                        concepts=str(rec.get("concepts") or ""),
                        phase=_safe_int(rec.get("phase")),
                    )
                )
            if meta_diff_s:
                if meta_surface_s:
                    if declared_diff is None and declared_surface is None:
                        continue
                elif declared_diff is None:
                    continue
            elif declared_surface is None:
                continue

            if (
                (meta_diff_s and declared_diff and declared_diff != meta_diff_s)
                or (meta_surface_s and declared_surface and declared_surface != meta_surface_s)
            ):
                mismatches.append(
                    DesignerMismatchRow(
                        run_dir=run_dir,
                        meta_difficulty=meta_diff_s,
                        declared_difficulty=declared_diff,
                        meta_surface=meta_surface_s,
                        declared_surface=declared_surface,
                        concepts=str(rec.get("concepts") or ""),
                        phase=_safe_int(rec.get("phase")),
                    )
                )

    mismatch_rate = (len(mismatches) / total) if total else 0.0
    return {
        "runs_with_problem_md": total,
        "declared_dimension_missing": declared_missing,
        "mismatch_count": len(mismatches),
        "mismatch_rate": mismatch_rate,
        "mismatch_examples": [
            {
                "run_dir": m.run_dir,
                "meta_difficulty": m.meta_difficulty,
                "declared_difficulty": m.declared_difficulty,
                "meta_surface": m.meta_surface,
                "declared_surface": m.declared_surface,
                "concepts": m.concepts,
                "phase": m.phase,
            }
            for m in mismatches[:20]
        ],
        "structure_violation_count": len(structure_violations),
        "structure_violation_rate": (len(structure_violations) / total) if total else 0.0,
        "structure_violation_examples": [
            {
                "run_dir": row.run_dir,
                "meta_difficulty": row.meta_difficulty,
                "declared_difficulty": row.declared_difficulty,
                "meta_surface": row.meta_surface,
                "declared_surface": row.declared_surface,
                "reasons": row.reasons,
                "concepts": row.concepts,
                "phase": row.phase,
            }
            for row in structure_violations[:20]
        ],
    }


def analyze_difficulty_value(
    *,
    records_csv: str,
) -> Dict[str, Any]:
    """
    Empirical validation: does difficulty correlate with outcomes?
      - success rate / risk / attempts can differ by difficulty group
    """
    by_diff: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    rows = 0

    with open(records_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            diff = _severity_key(r.get("difficulty"))
            if not diff:
                continue
            axis = condition_axis_label(diff)
            by_diff[axis].append(r)
            rows += 1

    def _mean(vals: List[float]) -> Optional[float]:
        vals = [v for v in vals if v is not None]
        return float(statistics.mean(vals)) if vals else None

    summary: Dict[str, Any] = {}
    xs_ord: List[float] = []
    ys_risk: List[float] = []
    ys_attempts: List[float] = []
    ys_success: List[float] = []

    for diff, items in sorted(by_diff.items(), key=lambda kv: _DIFF_TO_ORD.get(kv[0], 999)):
        success = [1.0 if str(i.get("success")).lower() == "true" else 0.0 for i in items]
        risk = [_safe_float(i.get("risk")) for i in items]
        attempts = [_safe_float(i.get("attempts_till_success")) for i in items]

        summary[diff] = {
            "rows": len(items),
            "success_rate": _mean(success),
            "avg_risk": _mean([v for v in risk if v is not None]),
            "avg_attempts": _mean([v for v in attempts if v is not None]),
        }

        ordv = float(_DIFF_TO_ORD.get(diff, 0))
        for s in success:
            xs_ord.append(ordv)
            ys_success.append(s)
        for v in risk:
            if v is not None:
                xs_ord.append(ordv)
                ys_risk.append(v)
        for a in attempts:
            if a is not None:
                xs_ord.append(ordv)
                ys_attempts.append(a)

    # Spearman computed on per-row pairs; we rebuild aligned arrays per metric.
    def _pairs(metric: str) -> Tuple[List[float], List[float]]:
        xs: List[float] = []
        ys: List[float] = []
        for diff, items in by_diff.items():
            ordv = float(_DIFF_TO_ORD.get(diff, 0))
            for i in items:
                if metric == "risk":
                    v = _safe_float(i.get("risk"))
                elif metric == "attempts":
                    v = _safe_float(i.get("attempts_till_success"))
                else:
                    v = 1.0 if str(i.get("success")).lower() == "true" else 0.0
                if v is None:
                    continue
                xs.append(ordv)
                ys.append(float(v))
        return xs, ys

    x_r, y_r = _pairs("risk")
    x_a, y_a = _pairs("attempts")
    x_s, y_s = _pairs("success")

    corr = {
        "spearman_difficulty_vs_risk": _spearman(x_r, y_r),
        "spearman_difficulty_vs_attempts": _spearman(x_a, y_a),
        "spearman_difficulty_vs_success": _spearman(x_s, y_s),
    }

    return {"rows": rows, "by_surface": summary, "correlations": corr}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--experiments-dir",
        default=os.path.join(_project_root(), "experiments"),
        help="Path to pack/experiments",
    )
    ap.add_argument(
        "--records-csv",
        default=os.path.join(_project_root(), "experiments", "vuln_summary", "records_all.csv"),
        help="Aggregated records CSV",
    )
    ap.add_argument(
        "--out-dir",
        default=os.path.join(_project_root(), "experiments", "vuln_summary"),
        help="Output directory for validation artifacts",
    )
    args = ap.parse_args()

    out_dir = str(args.out_dir)
    os.makedirs(out_dir, exist_ok=True)

    designer = validate_problem_designer(experiments_dir=str(args.experiments_dir))
    difficulty = analyze_difficulty_value(records_csv=str(args.records_csv))

    out = {"designer": designer, "surface_value": difficulty}
    out_path = os.path.join(out_dir, "designer_validation.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)

    # A small CSV of mismatches (if any).
    mism = designer.get("mismatch_examples") or []
    mism_path = os.path.join(out_dir, "designer_mismatch_examples.csv")
    with open(mism_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["run_dir", "meta_surface", "declared_surface", "concepts", "phase"],
        )
        w.writeheader()
        for r in mism:
            if isinstance(r, dict):
                w.writerow({k: r.get(k) for k in w.fieldnames})

    print(f"Wrote: {out_path}")
    print(f"Wrote: {mism_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
