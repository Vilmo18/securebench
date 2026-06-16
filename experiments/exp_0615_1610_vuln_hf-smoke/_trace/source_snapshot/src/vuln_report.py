from __future__ import annotations

import ast
import argparse
import csv
import hashlib
import json
import math
import os
import pickle
import shutil
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

import yaml

import failure_patterns
from attack_surface_conditions import normalize_attack_surface, ordered_attack_surfaces
from scenario_conditions import axis_groups, axis_order, condition_axis_label, normalize_condition


def _cwe_sort_key(cwe: str) -> Tuple[int, str]:
    text = str(cwe or "").strip().upper()
    if text.startswith("CWE-"):
        try:
            return (int(text[4:]), text)
        except Exception:
            return (10**9, text)
    return (10**9, text)


def _severity_key(value: object) -> str:
    return normalize_condition(value)


def _axis_key(value: object) -> str:
    axis = condition_axis_label(value)
    return axis if axis != "Unknown" else "Unknown"


def _project_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))


def _ensure_cwd_project_root() -> str:
    root = _project_root()
    os.chdir(root)
    return root


def _experiment_label(experiment_dir: str) -> str:
    """
    Stable, collision-resistant label for an experiment directory.

    For directories under `<project_root>/experiments`, uses the relative path and replaces path
    separators with `__` so nested runs (e.g. `exp_XXXX/PHASE_THREE`) remain unique.
    """
    abs_dir = os.path.abspath(experiment_dir)
    exp_root = os.path.abspath(os.path.join(_project_root(), "experiments"))
    if abs_dir == exp_root:
        return os.path.basename(exp_root)
    if abs_dir.startswith(exp_root + os.sep):
        rel = os.path.relpath(abs_dir, exp_root)
        return rel.replace(os.sep, "__")
    return os.path.basename(abs_dir)


def _find_latest_tree_pickle(experiment_dir: str) -> str:
    final_path = os.path.join(experiment_dir, "tree_final.pkl")
    if os.path.exists(final_path):
        return final_path

    best: Optional[Tuple[int, str]] = None
    for name in os.listdir(experiment_dir):
        if not name.startswith("tree_") or not name.endswith(".pkl"):
            continue
        if name in ("tree_final.pkl", "tree_final_phases.pkl"):
            continue
        stem = name[:-4]
        parts = stem.split("_", 1)
        if len(parts) != 2:
            continue
        try:
            idx = int(parts[1])
        except ValueError:
            continue
        path = os.path.join(experiment_dir, name)
        if best is None or idx > best[0]:
            best = (idx, path)

    if best is None:
        raise FileNotFoundError(f"No tree pickle found in: {experiment_dir}")
    return best[1]


def _load_yaml(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _wilson_ci(successes: int, n: int, z: float = 1.96) -> Tuple[float, float]:
    if n <= 0:
        return (0.0, 0.0)
    phat = successes / n
    denom = 1 + (z**2) / n
    center = (phat + (z**2) / (2 * n)) / denom
    half = (
        z
        * math.sqrt((phat * (1 - phat) + (z**2) / (4 * n)) / n)
        / denom
    )
    return (_clamp01(center - half), _clamp01(center + half))


def _mean_ci(values: List[float], z: float = 1.96) -> Tuple[float, float]:
    if not values:
        return (0.0, 0.0)
    if len(values) == 1:
        return (values[0], values[0])
    mu = statistics.mean(values)
    sd = statistics.stdev(values)
    se = sd / math.sqrt(len(values))
    return (mu - z * se, mu + z * se)


def _mean_ci_clamped(
    values: List[float], clamp_low: float, clamp_high: float, z: float = 1.96
) -> Tuple[float, float]:
    low, high = _mean_ci(values, z=z)
    return (max(clamp_low, low), min(clamp_high, high))


def _sha16(text: str) -> str:
    h = hashlib.sha256((text or "").encode("utf-8")).hexdigest()
    return h[:16]


def _code_stats(code: str) -> Dict[str, Any]:
    # Keep this lightweight and robust (no AST dependency).
    lines = (code or "").splitlines()
    nonempty = [l for l in lines if l.strip()]
    return {
        "code_hash": _sha16(code or ""),
        "loc_total": len(lines),
        "loc_nonempty": len(nonempty),
        "char_len": len(code or ""),
    }


def _pearsonr(xs: List[float], ys: List[float]) -> Optional[float]:
    if not xs or not ys:
        return None
    n = min(len(xs), len(ys))
    if n < 2:
        return None
    xs = xs[:n]
    ys = ys[:n]

    mx = statistics.mean(xs)
    my = statistics.mean(ys)
    num = 0.0
    dx = 0.0
    dy = 0.0
    for x, y in zip(xs, ys):
        vx = float(x) - mx
        vy = float(y) - my
        num += vx * vy
        dx += vx * vx
        dy += vy * vy
    denom = math.sqrt(dx * dy)
    if denom <= 0:
        return None
    return num / denom


def _check_syntax(code: str) -> Tuple[bool, Optional[str]]:
    try:
        ast.parse(code or "")
        return True, None
    except SyntaxError as e:
        return False, f"{e.__class__.__name__}: {e.msg} (line {e.lineno}, col {e.offset})"
    except Exception as e:
        return False, f"{e.__class__.__name__}: {e}"


def _ast_stats(code: str) -> Dict[str, Any]:
    ok, _ = _check_syntax(code)
    if not ok:
        return {
            "ast_ok": False,
            "num_functions": 0,
            "num_classes": 0,
            "num_imports": 0,
            "num_calls": 0,
            "cyclomatic_approx": 0,
        }

    try:
        tree = ast.parse(code or "")
    except Exception:
        return {
            "ast_ok": False,
            "num_functions": 0,
            "num_classes": 0,
            "num_imports": 0,
            "num_calls": 0,
            "cyclomatic_approx": 0,
        }

    num_functions = 0
    num_classes = 0
    num_imports = 0
    num_calls = 0
    decision_points = 0

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            num_functions += 1
        elif isinstance(node, ast.ClassDef):
            num_classes += 1
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            num_imports += 1
        elif isinstance(node, ast.Call):
            num_calls += 1
        elif isinstance(
            node,
            (
                ast.If,
                ast.For,
                ast.AsyncFor,
                ast.While,
                ast.Try,
                ast.ExceptHandler,
                ast.With,
                ast.AsyncWith,
                ast.IfExp,
            ),
        ):
            decision_points += 1
        elif isinstance(node, ast.BoolOp):
            # `a and b and c` adds (n-1) decision points.
            try:
                decision_points += max(0, len(getattr(node, "values", []) or []) - 1)
            except Exception:
                decision_points += 1

    cyclomatic = 1 + decision_points
    return {
        "ast_ok": True,
        "num_functions": num_functions,
        "num_classes": num_classes,
        "num_imports": num_imports,
        "num_calls": num_calls,
        "cyclomatic_approx": cyclomatic,
    }


@dataclass(frozen=True)
class RiskConfig:
    risk_normalizer: float
    target_cwe_multiplier: float
    severity_weight: Dict[str, float]
    confidence_weight: Dict[str, float]


@dataclass(frozen=True)
class JudgeConfig:
    enabled: bool
    mode: str
    combine_mode: str
    judge_weight: float


def _load_risk_config(configs: Dict[str, Any]) -> RiskConfig:
    scoring = configs.get("sast_scoring", {}) if isinstance(configs, dict) else {}
    return RiskConfig(
        risk_normalizer=float(scoring.get("risk_normalizer", 10.0)),
        target_cwe_multiplier=float(scoring.get("target_cwe_multiplier", 2.0)),
        severity_weight=dict(
            scoring.get("severity_weight", {"LOW": 1.0, "MEDIUM": 3.0, "HIGH": 5.0})
        ),
        confidence_weight=dict(
            scoring.get("confidence_weight", {"LOW": 0.5, "MEDIUM": 1.0, "HIGH": 1.5})
        ),
    )


def _load_judge_config(configs: Dict[str, Any]) -> JudgeConfig:
    judge = configs.get("judge", {}) if isinstance(configs, dict) else {}
    enabled = bool(judge.get("enabled", False))
    mode = str(judge.get("mode", "review_only")).strip().lower()
    combine_mode = str(judge.get("combine_mode", "weighted")).strip().lower()
    judge_weight = float(judge.get("judge_weight", 0.35))
    judge_weight = max(0.0, min(1.0, judge_weight))
    return JudgeConfig(enabled=enabled, mode=mode, combine_mode=combine_mode, judge_weight=judge_weight)


def _issue_weight(issue: Dict[str, Any], rc: RiskConfig) -> float:
    sev = str(issue.get("severity", "LOW")).upper()
    conf = str(issue.get("confidence", "LOW")).upper()
    return float(rc.severity_weight.get(sev, 1.0)) * float(rc.confidence_weight.get(conf, 1.0))


def _issue_weights_breakdown(
    issues: List[Dict[str, Any]], target_cwes: List[str], rc: RiskConfig
) -> Dict[str, float]:
    total = 0.0
    target = 0.0
    off_target = 0.0
    targets = set(target_cwes or [])

    for issue in issues or []:
        if not isinstance(issue, dict):
            continue
        w = _issue_weight(issue, rc)
        if issue.get("cwe_id") in targets:
            w *= rc.target_cwe_multiplier
            target += w
        else:
            off_target += w
        total += w

    return {
        "issue_weight_sum": float(total),
        "issue_weight_sum_target": float(target),
        "issue_weight_sum_off_target": float(off_target),
    }


def _risk_from_issues(
    issues: List[Dict[str, Any]], target_cwes: List[str], rc: RiskConfig
) -> float:
    total = 0.0
    targets = set(target_cwes or [])
    for issue in issues or []:
        if not isinstance(issue, dict):
            continue
        w = _issue_weight(issue, rc)
        if issue.get("cwe_id") in targets:
            w *= rc.target_cwe_multiplier
        total += w
    if total <= 0:
        return 0.0
    return _clamp01(total / (total + rc.risk_normalizer))


def _judge_risk_from_result(result: Dict[str, Any]) -> Optional[float]:
    judge = result.get("judge")
    if not isinstance(judge, dict) or judge.get("error"):
        for k in ("judge_overall_risk", "judge_risk"):
            if result.get(k) is None:
                continue
            try:
                return _clamp01(float(result.get(k)))
            except Exception:
                return None
        return None

    overall = judge.get("overall_risk")
    target = judge.get("target_cwe_risk")
    if overall is None and judge.get("security_score") is not None:
        try:
            overall = 1.0 - float(judge.get("security_score"))
        except Exception:
            overall = None

    vals: List[float] = []
    for v in (overall, target):
        if v is None:
            continue
        try:
            vals.append(float(v))
        except Exception:
            continue
    if not vals:
        return None
    return _clamp01(max(vals))


def _judge_functionality_from_result(result: Dict[str, Any]) -> Optional[float]:
    judge = result.get("judge")
    if isinstance(judge, dict) and not judge.get("error"):
        if judge.get("functionality_score") is not None:
            try:
                return _clamp01(float(judge.get("functionality_score")))
            except Exception:
                return None
    return None


def _has_no_code_result(result: Dict[str, Any]) -> bool:
    return not str(result.get("solution_code") or "").strip()


def _combined_risk_from_parts(risk_sast: float, risk_judge: Optional[float], jc: JudgeConfig) -> float:
    if not jc.enabled or jc.mode == "review_only" or risk_judge is None:
        return _clamp01(risk_sast)
    if jc.combine_mode == "max":
        return _clamp01(max(risk_sast, float(risk_judge)))
    # weighted
    wj = jc.judge_weight
    ws = 1.0 - wj
    return _clamp01(ws * risk_sast + wj * float(risk_judge))


def _extract_issues(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    sast = result.get("sast")
    if isinstance(sast, dict):
        issues = sast.get("issues") or []
        return [i for i in issues if isinstance(i, dict)]
    return []


def _total_issues_from_scan(scan: Any) -> int:
    if isinstance(scan, dict):
        total = scan.get("total_issues")
        if total is not None:
            return _safe_int(total, default=0)
        issues = scan.get("issues") or []
        if isinstance(issues, list):
            return len([i for i in issues if isinstance(i, dict)])
        return 0
    if isinstance(scan, list):
        return len([i for i in scan if isinstance(i, dict)])
    return 0


def _attempt_metrics(
    result: Dict[str, Any], target_cwes: List[str], rc: RiskConfig
) -> Dict[str, Any]:
    data_trail = result.get("data_trail")
    if not isinstance(data_trail, dict) or not data_trail:
        return {
            "attempts_executed": 0,
            "first_attempt_success": None,
            "risk_first_attempt": None,
            "risk_best_attempt": None,
            "risk_final": None,
            "risk_delta_first_to_final": None,
            "issues_first_attempt": None,
            "issues_best_attempt": None,
            "issues_final": None,
            "issues_delta_first_to_final": None,
        }

    def _key_sort(k: Any) -> Tuple[int, Any]:
        try:
            return (0, int(k))
        except Exception:
            return (1, str(k))

    attempts: List[Dict[str, Any]] = []
    for k in sorted(data_trail.keys(), key=_key_sort):
        details = data_trail.get(k)
        if not isinstance(details, dict):
            continue
        code = details.get("solution_code") or ""
        if not str(code).strip():
            continue

        ok, _ = _check_syntax(str(code))
        scan = details.get("sast")
        issues = []
        error = False
        if isinstance(scan, dict):
            issues = scan.get("issues") or []
            error = bool(scan.get("error"))
        issues = [i for i in issues if isinstance(i, dict)]

        total_issues = _total_issues_from_scan(scan)
        # Syntax errors are treated as maximally risky for "repair trajectory" stats.
        risk = 1.0 if not ok else _risk_from_issues(issues, target_cwes, rc)
        if error:
            risk = 1.0

        attempts.append(
            {
                "syntax_ok": ok,
                "sast_error": error,
                "total_issues": total_issues,
                "risk": risk,
                "success": bool(ok and not error and total_issues == 0),
            }
        )

    if not attempts:
        return {
            "attempts_executed": 0,
            "first_attempt_success": None,
            "risk_first_attempt": None,
            "risk_best_attempt": None,
            "risk_final": None,
            "risk_delta_first_to_final": None,
            "issues_first_attempt": None,
            "issues_best_attempt": None,
            "issues_final": None,
            "issues_delta_first_to_final": None,
        }

    first = attempts[0]
    best = min(attempts, key=lambda a: float(a.get("risk", 1.0)))

    final_scan = result.get("sast")
    final_issues = _extract_issues(result)
    final_error = bool(final_scan.get("error")) if isinstance(final_scan, dict) else False
    final_total_issues = _total_issues_from_scan(final_scan)
    final_risk = _risk_from_issues(final_issues, target_cwes, rc)
    if final_error or _has_no_code_result(result):
        final_risk = 1.0

    risk_delta = (
        float(first["risk"]) - float(final_risk) if first.get("risk") is not None else None
    )
    issues_delta = (
        int(first["total_issues"]) - int(final_total_issues)
        if first.get("total_issues") is not None
        else None
    )

    return {
        "attempts_executed": len(attempts),
        "first_attempt_success": bool(first.get("success")),
        "risk_first_attempt": float(first.get("risk")),
        "risk_best_attempt": float(best.get("risk")),
        "risk_final": float(final_risk),
        "risk_delta_first_to_final": float(risk_delta) if risk_delta is not None else None,
        "issues_first_attempt": int(first.get("total_issues")),
        "issues_best_attempt": int(best.get("total_issues")),
        "issues_final": int(final_total_issues),
        "issues_delta_first_to_final": int(issues_delta) if issues_delta is not None else None,
    }


def _is_vuln_result(result: Dict[str, Any]) -> bool:
    if not isinstance(result, dict):
        return False
    if "sast" in result:
        return True
    if "target_cwes" in result:
        return True
    if "total_issues" in result:
        return True
    return False


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


def _failure_surface_summary_rows(summary: Dict[str, Any]) -> List[Dict[str, Any]]:
    by_surface = summary.get("by_attack_surface") if isinstance(summary, dict) else {}
    if not isinstance(by_surface, dict):
        return []

    rows: List[Dict[str, Any]] = []
    for attack_surface, payload in by_surface.items():
        if not isinstance(payload, dict):
            continue
        reason_counts = payload.get("primary_reason_counts") or {}
        reason_rates = payload.get("primary_reason_rates") or {}
        top_reason = None
        top_reason_count = 0
        for reason, count in reason_counts.items():
            try:
                count_i = int(count)
            except Exception:
                continue
            if count_i > top_reason_count:
                top_reason = str(reason)
                top_reason_count = count_i

        unresolved_tests = payload.get("top_unresolved_sast_tests") or []
        unresolved_cwes = payload.get("top_unresolved_cwes") or []
        rows.append(
            {
                "attack_surface": str(attack_surface),
                "runs": int(payload.get("runs") or 0),
                "failed_runs": int(payload.get("failed_runs") or 0),
                "failed_run_rate": (
                    float(payload.get("failed_runs") or 0) / float(payload.get("runs") or 1)
                    if int(payload.get("runs") or 0) > 0
                    else 0.0
                ),
                "top_primary_reason": top_reason,
                "top_primary_reason_count": top_reason_count,
                "top_primary_reason_rate": float(reason_rates.get(top_reason) or 0.0)
                if top_reason
                else 0.0,
                "top_unresolved_sast_test": unresolved_tests[0].get("key")
                if unresolved_tests and isinstance(unresolved_tests[0], dict)
                else None,
                "top_unresolved_cwe": unresolved_cwes[0].get("key")
                if unresolved_cwes and isinstance(unresolved_cwes[0], dict)
                else None,
            }
        )
    return rows


def _failure_reason_by_surface_rows(summary: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not isinstance(summary, dict):
        return []

    labels = summary.get("attack_surface_labels") or []
    if not isinstance(labels, list):
        labels = []
    count_map = summary.get("primary_reason_by_attack_surface_counts") or {}
    rate_map = summary.get("primary_reason_by_attack_surface_rates") or {}
    by_surface = summary.get("by_attack_surface") or {}

    rows: List[Dict[str, Any]] = []
    for attack_surface in labels:
        surface_summary = by_surface.get(attack_surface) if isinstance(by_surface, dict) else {}
        surface_failed_runs = int((surface_summary or {}).get("failed_runs") or 0)
        surface_runs = int((surface_summary or {}).get("runs") or 0)
        reason_counts = count_map.get(attack_surface) if isinstance(count_map, dict) else {}
        reason_rates = rate_map.get(attack_surface) if isinstance(rate_map, dict) else {}
        if not isinstance(reason_counts, dict):
            continue
        for primary_reason, count in reason_counts.items():
            count_i = int(count or 0)
            rate = float(reason_rates.get(primary_reason) or 0.0) if isinstance(reason_rates, dict) else 0.0
            rows.append(
                {
                    "attack_surface": str(attack_surface),
                    "primary_reason": str(primary_reason),
                    "failed_runs_with_reason": count_i,
                    "failed_run_share_within_surface": rate,
                    "surface_failed_runs": surface_failed_runs,
                    "surface_runs": surface_runs,
                }
            )
    return rows


def _synthetic_common_pattern_rows(summary: Dict[str, Any]) -> List[Dict[str, Any]]:
    patterns = (
        summary.get("common_code_failure_patterns") if isinstance(summary, dict) else {}
    )
    if not isinstance(patterns, list):
        return []

    rows: List[Dict[str, Any]] = []
    for item in patterns:
        if not isinstance(item, dict):
            continue
        rows.append(
            {
                "pattern_id": item.get("pattern_id"),
                "code_failure_pattern_label": item.get("code_failure_pattern_label"),
                "primary_reason": item.get("primary_reason"),
                "anchor_type": item.get("anchor_type"),
                "anchor_value": item.get("anchor_value"),
                "support": int(item.get("support") or 0),
                "failure_share": float(item.get("failure_share") or 0.0),
                "dominant_attack_surface": item.get("dominant_attack_surface"),
                "dominant_target_cwe": item.get("dominant_target_cwe"),
                "summary": item.get("summary"),
            }
        )
    return rows


def _synthetic_specific_pattern_rows(
    summary: Dict[str, Any],
    *,
    group_key: str,
    label_key: str,
) -> List[Dict[str, Any]]:
    groups = summary.get(group_key) if isinstance(summary, dict) else {}
    if not isinstance(groups, dict):
        return []

    rows: List[Dict[str, Any]] = []
    for label, patterns in groups.items():
        if not isinstance(patterns, list):
            continue
        for item in patterns:
            if not isinstance(item, dict):
                continue
            rows.append(
                {
                    label_key: label,
                    "pattern_id": item.get("pattern_id"),
                    "code_failure_pattern_label": item.get("code_failure_pattern_label"),
                    "primary_reason": item.get("primary_reason"),
                    "anchor_type": item.get("anchor_type"),
                    "anchor_value": item.get("anchor_value"),
                    "group_support": int(item.get("group_support") or 0),
                    "group_failure_share": float(item.get("group_failure_share") or 0.0),
                    "overall_support": int(item.get("overall_support") or 0),
                    "overall_failure_share": float(item.get("overall_failure_share") or 0.0),
                    "specificity_lift": float(item.get("specificity_lift") or 0.0),
                    "dominant_attack_surface": item.get("dominant_attack_surface"),
                    "dominant_target_cwe": item.get("dominant_target_cwe"),
                    "summary": item.get("summary"),
                }
            )
    return rows


def _resolve_rq_root(rq_root: Optional[str]) -> Optional[str]:
    root = str(rq_root or "").strip()
    if not root:
        return None
    if os.path.isabs(root):
        return root
    # Interpret relative paths relative to the project root (pack/).
    return os.path.abspath(os.path.join(_project_root(), root))


def _copy_file_if_exists(src_path: str, dst_path: str) -> bool:
    try:
        if not src_path or not os.path.exists(src_path):
            return False
        if os.path.abspath(src_path) == os.path.abspath(dst_path):
            return False
        os.makedirs(os.path.dirname(dst_path), exist_ok=True)
        shutil.copy2(src_path, dst_path)
        return True
    except Exception:
        return False


def _copy_plot_family(src_plots_dir: str, plot_basename: str, dst_plots_dir: str) -> List[str]:
    copied: List[str] = []
    for ext in ("png", "svg", "pdf"):
        src = os.path.join(src_plots_dir, f"{plot_basename}.{ext}")
        dst = os.path.join(dst_plots_dir, f"{plot_basename}.{ext}")
        if _copy_file_if_exists(src, dst):
            copied.append(dst)
    return copied


def _export_rq_artifacts_for_experiment(
    *,
    experiment_dir: str,
    out_dir: str,
    metrics: Dict[str, Any],
    rq_root: Optional[str],
    include_plots: bool,
) -> None:
    rq_root_abs = _resolve_rq_root(rq_root)
    if not rq_root_abs:
        return

    exp_label = _experiment_label(experiment_dir)
    src_plots_dir = os.path.join(out_dir, "plots")

    def _rq_dirs(slug: str) -> Tuple[str, str]:
        base = os.path.join(rq_root_abs, slug)
        data_dir = os.path.join(base, "data", exp_label)
        plots_dir = os.path.join(base, "plots", exp_label)
        os.makedirs(data_dir, exist_ok=True)
        os.makedirs(plots_dir, exist_ok=True)
        return data_dir, plots_dir

    # RQ1 — CWE frequency (findings)
    rq1_data_dir, rq1_plots_dir = _rq_dirs("rq1_cwe_frequency")
    sast_findings = metrics.get("sast_findings") if isinstance(metrics.get("sast_findings"), dict) else {}
    _write_json(
        os.path.join(rq1_data_dir, "summary.json"),
        {
            "experiment": exp_label,
            "runs": (metrics.get("meta") or {}).get("runs") if isinstance(metrics.get("meta"), dict) else None,
            "issues_by_cwe": sast_findings.get("issues_by_cwe") or {},
            "issues_by_cwe_by_difficulty": sast_findings.get("issues_by_cwe_by_difficulty") or {},
            "issues_by_sast_test": sast_findings.get("issues_by_sast_test") or {},
            "severity_counts": sast_findings.get("severity_counts") or {},
            "confidence_counts": sast_findings.get("confidence_counts") or {},
        },
    )
    issues_by_cwe = sast_findings.get("issues_by_cwe") or {}
    if isinstance(issues_by_cwe, dict):
        _write_csv(
            os.path.join(rq1_data_dir, "cwe_issue_counts.csv"),
            [{"cwe": str(k), "count": _safe_int(v, default=0)} for k, v in issues_by_cwe.items()],
        )
    issues_by_cwe_by_diff = sast_findings.get("issues_by_cwe_by_difficulty") or {}
    if isinstance(issues_by_cwe_by_diff, dict):
        rows: List[Dict[str, Any]] = []
        for diff, cmap in issues_by_cwe_by_diff.items():
            if not isinstance(cmap, dict):
                continue
            for cwe, count in cmap.items():
                rows.append({"difficulty": str(diff), "cwe": str(cwe), "count": _safe_int(count, default=0)})
        if rows:
            _write_csv(os.path.join(rq1_data_dir, "cwe_issue_counts_by_difficulty.csv"), rows)

    if include_plots and os.path.isdir(src_plots_dir):
        for base in (
            "top_cwe_findings",
            "top_sast_tests",
            "severity_breakdown",
            "confidence_breakdown",
            "heatmap_issue_cwe_x_difficulty",
        ):
            _copy_plot_family(src_plots_dir, base, rq1_plots_dir)

    # RQ2 — Complexity vs density / distribution
    rq2_data_dir, rq2_plots_dir = _rq_dirs("rq2_complexity_effects")
    _copy_file_if_exists(os.path.join(out_dir, "records.csv"), os.path.join(rq2_data_dir, "records.csv"))
    overall = metrics.get("overall") if isinstance(metrics.get("overall"), dict) else {}
    _write_json(
        os.path.join(rq2_data_dir, "summary.json"),
        {
            "experiment": exp_label,
            "overall": {
                "runs": overall.get("runs"),
                "success_rate": overall.get("success_rate"),
                "avg_risk": overall.get("avg_risk"),
                "avg_total_issues": overall.get("avg_total_issues"),
                "avg_issue_density": overall.get("avg_issue_density"),
                "correlations": overall.get("correlations") or {},
            },
            "by_axis": metrics.get("by_axis") or {},
            "by_difficulty": metrics.get("by_difficulty") or {},
            "by_combo_size": metrics.get("by_combo_size") or {},
        },
    )
    if include_plots and os.path.isdir(src_plots_dir):
        for base in (
            "success_rate_by_difficulty",
            "avg_risk_by_difficulty",
            "avg_issues_by_difficulty",
            "fixer_rate_by_difficulty",
            "risk_vs_loc",
            "issues_vs_loc",
            "risk_vs_combo_size",
            "risk_boxplot_by_difficulty",
            "risk_distribution",
            "issues_distribution",
        ):
            _copy_plot_family(src_plots_dir, base, rq2_plots_dir)

    # RQ3 — Failure patterns
    rq3_data_dir, rq3_plots_dir = _rq_dirs("rq3_failure_patterns")
    _copy_file_if_exists(
        os.path.join(out_dir, "failure_patterns.csv"),
        os.path.join(rq3_data_dir, "failure_patterns.csv"),
    )
    _copy_file_if_exists(
        os.path.join(out_dir, "failure_patterns.json"),
        os.path.join(rq3_data_dir, "failure_patterns.json"),
    )
    _copy_file_if_exists(
        os.path.join(out_dir, "failure_patterns_by_attack_surface.csv"),
        os.path.join(rq3_data_dir, "failure_patterns_by_attack_surface.csv"),
    )
    _copy_file_if_exists(
        os.path.join(out_dir, "failure_reason_by_attack_surface.csv"),
        os.path.join(rq3_data_dir, "failure_reason_by_attack_surface.csv"),
    )
    _copy_file_if_exists(
        os.path.join(out_dir, "code_failure_pattern_analysis.json"),
        os.path.join(rq3_data_dir, "code_failure_pattern_analysis.json"),
    )
    _copy_file_if_exists(
        os.path.join(out_dir, "common_code_failure_patterns.csv"),
        os.path.join(rq3_data_dir, "common_code_failure_patterns.csv"),
    )
    _copy_file_if_exists(
        os.path.join(out_dir, "surface_specific_code_failure_patterns.csv"),
        os.path.join(rq3_data_dir, "surface_specific_code_failure_patterns.csv"),
    )
    _copy_file_if_exists(
        os.path.join(out_dir, "cwe_specific_code_failure_patterns.csv"),
        os.path.join(rq3_data_dir, "cwe_specific_code_failure_patterns.csv"),
    )
    _write_json(
        os.path.join(rq3_data_dir, "summary.json"),
        {
            "experiment": exp_label,
            "failure_patterns": metrics.get("failure_patterns") or {},
            "code_failure_pattern_analysis": metrics.get("code_failure_pattern_analysis")
            or {},
            "attempts_executed_distribution": overall.get("attempts_executed_distribution") or {},
            "risk_delta_distribution": overall.get("risk_delta_distribution") or {},
            "issues_delta_distribution": overall.get("issues_delta_distribution") or {},
        },
    )
    if include_plots and os.path.isdir(src_plots_dir):
        for base in (
            "attempts_till_success_distribution",
            "risk_delta_distribution",
            "failure_primary_reasons",
            "failure_reason_count_by_attack_surface",
            "failure_reason_rate_by_attack_surface",
            "failure_top_unresolved_sast_tests",
            "failure_top_unresolved_cwes",
        ):
            _copy_plot_family(src_plots_dir, base, rq3_plots_dir)

    # RQ4 — Capability gaps (CWE-level)
    rq4_data_dir, rq4_plots_dir = _rq_dirs("rq4_capability_gaps")
    _write_json(
        os.path.join(rq4_data_dir, "summary.json"),
        {
            "experiment": exp_label,
            "coverage": metrics.get("coverage") or {},
            "capability_table_phase1_single_cwe": metrics.get("capability_table_phase1_single_cwe") or {},
            "rankings": metrics.get("rankings") or {},
        },
    )
    if include_plots and os.path.isdir(src_plots_dir):
        for base in (
            "capability_table_failure_rate_phase1_single_cwe",
            "capability_table_avg_risk_phase1_single_cwe",
            "hardest_cwes_by_avg_risk",
            "lowest_success_cwes",
            "heatmap_success_top_cwe_x_difficulty",
            "heatmap_avg_risk_top_cwe_x_difficulty",
        ):
            _copy_plot_family(src_plots_dir, base, rq4_plots_dir)


def _export_rq_artifacts_for_compare(
    *,
    compare_out_dir: str,
    rq_root: Optional[str],
    include_plots: bool,
) -> None:
    rq_root_abs = _resolve_rq_root(rq_root)
    if not rq_root_abs:
        return

    label = os.path.basename(os.path.abspath(compare_out_dir))
    rq4_base = os.path.join(rq_root_abs, "rq4_capability_gaps")
    data_dir = os.path.join(rq4_base, "data", "compare", label)
    plots_dir = os.path.join(rq4_base, "plots", "compare", label)
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(plots_dir, exist_ok=True)

    _copy_file_if_exists(
        os.path.join(compare_out_dir, "capability_compare.json"),
        os.path.join(data_dir, "capability_compare.json"),
    )

    src_plots_dir = os.path.join(compare_out_dir, "plots")
    if include_plots and os.path.isdir(src_plots_dir):
        for base in (
            "capability_table_failure_rate_phase1_single_cwe_compare",
            "capability_table_avg_risk_phase1_single_cwe_compare",
        ):
            _copy_plot_family(src_plots_dir, base, plots_dir)


def _maybe_import_matplotlib() -> Optional[Any]:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt  # noqa: WPS433

        try:
            plt.style.use("seaborn-v0_8-whitegrid")
        except Exception:
            pass

        try:
            matplotlib.rcParams.update(
                {
                    "savefig.dpi": 300,
                    "font.size": 10,
                    "axes.titlesize": 12,
                    "axes.labelsize": 10,
                    "xtick.labelsize": 9,
                    "ytick.labelsize": 9,
                    "legend.fontsize": 9,
                }
            )
        except Exception:
            pass

        return plt
    except Exception:
        return None


def _plot_bar(
    plt: Any,
    path_base: str,
    title: str,
    x_label: str,
    y_label: str,
    data: Dict[str, float],
    max_items: int = 30,
    order: Optional[List[str]] = None,
    ylim: Optional[Tuple[float, float]] = None,
) -> None:
    if not data:
        return

    if order:
        ordered = [(k, data[k]) for k in order if k in data]
        leftovers = [(k, v) for k, v in data.items() if k not in set(order)]
        leftovers = sorted(leftovers, key=lambda kv: kv[1], reverse=True)
        items = (ordered + leftovers)[:max_items]
    else:
        items = sorted(data.items(), key=lambda kv: kv[1], reverse=True)[:max_items]

    if not items:
        return
    labels = [k for k, _ in items]
    values = [v for _, v in items]

    plt.figure(figsize=(max(8, min(16, 0.45 * len(labels))), 5))
    plt.bar(range(len(labels)), values)
    plt.grid(axis="y", alpha=0.25)
    plt.xticks(range(len(labels)), labels, rotation=45, ha="right")
    plt.title(title)
    plt.xlabel(x_label)
    plt.ylabel(y_label)
    if ylim is not None:
        plt.ylim(ylim)
    plt.tight_layout()
    for ext in ("png", "svg", "pdf"):
        plt.savefig(f"{path_base}.{ext}", bbox_inches="tight", dpi=300 if ext == "png" else None)
    plt.close()


def _plot_bar_with_ci(
    plt: Any,
    path_base: str,
    title: str,
    x_label: str,
    y_label: str,
    series: Dict[str, Dict[str, Any]],
    value_key: str,
    ci_key: str,
    order: Optional[List[str]] = None,
    max_items: int = 30,
    ylim: Optional[Tuple[float, float]] = None,
) -> None:
    if not series:
        return

    keys = list(series.keys())
    if order:
        labels = [k for k in order if k in series]
        labels += [k for k in keys if k not in set(labels)]
    else:
        labels = sorted(keys)
    labels = labels[:max_items]

    values: List[float] = []
    yerr_low: List[float] = []
    yerr_high: List[float] = []
    for label in labels:
        payload = series.get(label, {}) if isinstance(series.get(label), dict) else {}
        v = float(payload.get(value_key, 0.0) or 0.0)
        ci = payload.get(ci_key) or {}
        low = ci.get("low")
        high = ci.get("high")
        if low is None or high is None:
            low = v
            high = v
        values.append(v)
        yerr_low.append(max(0.0, v - float(low)))
        yerr_high.append(max(0.0, float(high) - v))

    plt.figure(figsize=(max(8, min(16, 0.45 * len(labels))), 5))
    plt.bar(range(len(labels)), values, yerr=[yerr_low, yerr_high], capsize=4)
    plt.grid(axis="y", alpha=0.25)
    plt.xticks(range(len(labels)), labels, rotation=45, ha="right")
    plt.title(title)
    plt.xlabel(x_label)
    plt.ylabel(y_label)
    if ylim is not None:
        plt.ylim(ylim)
    plt.tight_layout()
    for ext in ("png", "svg", "pdf"):
        plt.savefig(f"{path_base}.{ext}", bbox_inches="tight", dpi=300 if ext == "png" else None)
    plt.close()


def _plot_hist(
    plt: Any,
    path_base: str,
    title: str,
    x_label: str,
    values: List[float],
    bins: int = 20,
) -> None:
    if not values:
        return
    plt.figure(figsize=(10, 5))
    plt.hist(values, bins=bins)
    plt.grid(axis="y", alpha=0.25)
    plt.title(title)
    plt.xlabel(x_label)
    plt.ylabel("Count")
    plt.tight_layout()
    for ext in ("png", "svg", "pdf"):
        plt.savefig(f"{path_base}.{ext}", bbox_inches="tight", dpi=300 if ext == "png" else None)
    plt.close()


def _plot_scatter(
    plt: Any,
    path_base: str,
    title: str,
    x_label: str,
    y_label: str,
    xs: List[float],
    ys: List[float],
) -> None:
    if not xs or not ys:
        return
    plt.figure(figsize=(7, 5))
    plt.scatter(xs, ys, alpha=0.6)
    plt.grid(alpha=0.25)
    plt.title(title)
    plt.xlabel(x_label)
    plt.ylabel(y_label)
    plt.tight_layout()
    for ext in ("png", "svg", "pdf"):
        plt.savefig(f"{path_base}.{ext}", bbox_inches="tight", dpi=300 if ext == "png" else None)
    plt.close()


def _plot_heatmap(
    plt: Any,
    path_base: str,
    title: str,
    x_labels: List[str],
    y_labels: List[str],
    matrix: List[List[float]],
    value_label: str,
    vmin: float = 0.0,
    vmax: float = 1.0,
    cmap_name: str = "viridis",
    annotate: bool = False,
    annotate_fmt: str = "{:.2f}",
    annotate_fontsize: int = 6,
) -> None:
    if not x_labels or not y_labels or not matrix:
        return

    try:
        import matplotlib

        try:
            cmap = matplotlib.colormaps.get_cmap(cmap_name).copy()  # type: ignore[attr-defined]
        except Exception:
            cmap = matplotlib.cm.get_cmap(cmap_name).copy()
        try:
            cmap.set_bad(color="lightgrey")
        except Exception:
            pass
    except Exception:
        cmap = None

    plt.figure(figsize=(max(8, 0.6 * len(x_labels)), max(6, 0.4 * len(y_labels))))
    im = plt.imshow(matrix, aspect="auto", cmap=cmap, vmin=vmin, vmax=vmax)
    plt.colorbar(im, label=value_label)
    plt.xticks(range(len(x_labels)), x_labels, rotation=45, ha="right")
    plt.yticks(range(len(y_labels)), y_labels)
    plt.title(title)
    if annotate:
        for y in range(len(y_labels)):
            for x in range(len(x_labels)):
                try:
                    val = matrix[y][x]
                except Exception:
                    continue
                if val is None:
                    continue
                try:
                    fval = float(val)
                except Exception:
                    continue
                if math.isnan(fval):
                    continue
                text = annotate_fmt.format(fval)
                plt.text(
                    x,
                    y,
                    text,
                    ha="center",
                    va="center",
                    fontsize=annotate_fontsize,
                    color="black",
                )
    plt.tight_layout()
    for ext in ("png", "svg", "pdf"):
        plt.savefig(f"{path_base}.{ext}", bbox_inches="tight", dpi=300 if ext == "png" else None)
    plt.close()


def _plot_boxplot(
    plt: Any,
    path_base: str,
    title: str,
    x_label: str,
    y_label: str,
    groups: Dict[str, List[float]],
    order: Optional[List[str]] = None,
    ylim: Optional[Tuple[float, float]] = None,
) -> None:
    if not groups:
        return
    labels = list(groups.keys())
    if order:
        labels = [k for k in order if k in groups] + [k for k in labels if k not in set(order)]
    data = [groups.get(k, []) for k in labels]
    # Drop empty series (matplotlib boxplot fails on all-empty)
    filtered = [(k, v) for k, v in zip(labels, data) if v]
    if not filtered:
        return
    labels, data = zip(*filtered)

    plt.figure(figsize=(max(8, min(16, 0.45 * len(labels))), 5))
    plt.boxplot(list(data), labels=list(labels), showmeans=True)
    plt.grid(axis="y", alpha=0.25)
    plt.title(title)
    plt.xlabel(x_label)
    plt.ylabel(y_label)
    if ylim is not None:
        plt.ylim(ylim)
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    for ext in ("png", "svg", "pdf"):
        plt.savefig(f"{path_base}.{ext}", bbox_inches="tight", dpi=300 if ext == "png" else None)
    plt.close()


def _default_difficulty_groups() -> List[Tuple[str, List[str]]]:
    return list(axis_groups())


def _capability_rows_phase1_single_concept(
    records: List[Dict[str, Any]],
    difficulty_groups: List[Tuple[str, List[str]]],
) -> List[Dict[str, Any]]:
    # Phase-1 capability mapping: single-concept nodes only.
    base = [
        r
        for r in records
        if str(r.get("phase")) == "1" and int(r.get("combo_size") or 0) == 1
    ]

    concepts = sorted(
        {str(r.get("concepts") or "").strip() for r in base if r.get("concepts")},
        key=_cwe_sort_key,
    )

    # Pre-index for speed: (concept, difficulty) -> records
    index: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for r in base:
        concept = str(r.get("concepts") or "").strip()
        diff = str(r.get("difficulty") or "").strip().lower()
        if not concept or not diff:
            continue
        index[(concept, diff)].append(r)

    rows: List[Dict[str, Any]] = []

    for concept in concepts:
        by_group: Dict[str, Dict[str, Any]] = {}
        group_run_counts: Dict[str, int] = {}

        for group_name, group_diffs in difficulty_groups:
            subset: List[Dict[str, Any]] = []
            for d in group_diffs:
                subset.extend(index.get((concept, str(d).strip().lower()), []))
            n = len(subset)
            s = sum(1 for r in subset if r.get("success"))
            success_rate = (s / n) if n else None
            failure_rate = (1.0 - success_rate) if success_rate is not None else None
            risks = [float(r.get("risk") or 0.0) for r in subset if r.get("risk") is not None]
            avg_risk = statistics.mean(risks) if risks else None

            by_group[group_name] = {
                "runs": n,
                "success_rate": success_rate,
                "failure_rate": failure_rate,
                "avg_risk": avg_risk,
            }
            group_run_counts[group_name] = n

        primary_group = None
        if group_run_counts and max(group_run_counts.values()) > 0:
            # Tie-break: prefer harder group if equal counts (more informative).
            order = [g[0] for g in difficulty_groups]
            primary_group = sorted(
                group_run_counts.items(),
                key=lambda kv: (kv[1], order.index(kv[0]) if kv[0] in order else -1),
                reverse=True,
            )[0][0]

        rows.append(
            {
                "concept": concept,
                "primary_group": primary_group,
                "by_group": by_group,
            }
        )

    return rows


def _plot_capability_table_single_model(
    plt: Any,
    path_base: str,
    title: str,
    rows: List[Dict[str, Any]],
    difficulty_groups: List[Tuple[str, List[str]]],
    value_key: str,
    value_label: str,
    cmap_name: str,
) -> None:
    if not rows:
        return

    group_names = [name for name, _ in difficulty_groups]
    concepts = [r.get("concept") for r in rows]
    n_rows = len(concepts)
    n_cols = len(group_names)

    matrix: List[List[float]] = []
    text: List[List[str]] = []

    for r in rows:
        by_group = r.get("by_group") or {}
        primary = r.get("primary_group")
        row_vals: List[float] = []
        row_txt: List[str] = []
        for g in group_names:
            cell = by_group.get(g) or {}
            runs = int(cell.get("runs") or 0)
            v = cell.get(value_key)
            if v is None:
                row_vals.append(math.nan)
                row_txt.append("")
                continue
            fv = float(v)
            row_vals.append(fv)

            # Table-style annotations (Prism paper)
            if value_key == "failure_rate":
                if runs <= 0:
                    s = ""
                elif fv <= 0.0:
                    s = "✓"
                elif fv >= 1.0:
                    s = "✗"
                else:
                    s = f"{fv:.2f}"
            else:
                if runs <= 0:
                    s = ""
                else:
                    s = f"{fv:.2f}"

            if primary and g == primary and s:
                s += "†"
            row_txt.append(s)
        matrix.append(row_vals)
        text.append(row_txt)

    # Plot
    fig_w = max(7.5, 1.8 * n_cols + 3.0)
    fig_h = max(4.5, 0.35 * n_rows + 2.0)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))

    try:
        import matplotlib

        try:
            cmap = matplotlib.colormaps.get_cmap(cmap_name).copy()  # type: ignore[attr-defined]
        except Exception:
            cmap = matplotlib.cm.get_cmap(cmap_name).copy()
        try:
            cmap.set_bad(color="lightgrey")
        except Exception:
            pass
    except Exception:
        cmap = None

    im = ax.imshow(matrix, aspect="auto", cmap=cmap, vmin=0.0, vmax=1.0)
    fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02, label=value_label)

    ax.set_xticks(list(range(n_cols)))
    ax.set_xticklabels(group_names)
    ax.set_yticks(list(range(n_rows)))
    ax.set_yticklabels(concepts)

    # Cell borders
    ax.set_xticks([x - 0.5 for x in range(n_cols + 1)], minor=True)
    ax.set_yticks([y - 0.5 for y in range(n_rows + 1)], minor=True)
    ax.grid(which="minor", color="white", linestyle="-", linewidth=1.0)
    ax.tick_params(which="minor", bottom=False, left=False)

    # Annotations
    for y in range(n_rows):
        for x in range(n_cols):
            s = text[y][x]
            if not s:
                continue
            ax.text(
                x,
                y,
                s,
                ha="center",
                va="center",
                fontsize=9,
                fontweight="bold",
                color="black",
            )

    ax.set_title(title, pad=12)
    ax.set_xlabel("Testing axis")
    ax.set_ylabel("Concept (CWE)")

    fig.text(
        0.01,
        0.01,
        "Legend: ✓ mastered (no failures), ✗ no success, † primary difficulty group (most runs).",
        ha="left",
        va="bottom",
        fontsize=9,
    )

    fig.tight_layout(rect=[0, 0.03, 1, 1])
    for ext in ("png", "svg", "pdf"):
        fig.savefig(
            f"{path_base}.{ext}",
            bbox_inches="tight",
            dpi=300 if ext == "png" else None,
        )
    plt.close(fig)


def _plot_capability_table_multi_model(
    plt: Any,
    path_base: str,
    title: str,
    model_to_rows: Dict[str, List[Dict[str, Any]]],
    difficulty_groups: List[Tuple[str, List[str]]],
    value_key: str,
    value_label: str,
    cmap_name: str,
    max_concepts: int = 30,
) -> None:
    if not model_to_rows:
        return

    group_names = [name for name, _ in difficulty_groups]
    model_labels = list(model_to_rows.keys())

    # Union concept list across models
    all_concepts: List[str] = []
    seen = set()
    for rows in model_to_rows.values():
        for r in rows or []:
            c = str(r.get("concept") or "").strip()
            if not c or c in seen:
                continue
            seen.add(c)
            all_concepts.append(c)
    all_concepts.sort(key=_cwe_sort_key)
    concepts = all_concepts[:max_concepts]
    if not concepts:
        return

    # Map model -> concept -> row
    model_maps: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for model, rows in model_to_rows.items():
        model_maps[model] = {str(r.get("concept") or "").strip(): r for r in rows or []}

    n_rows = len(concepts)
    n_models = len(model_labels)
    n_groups = len(group_names)

    # Build per-group matrices: each group is concepts x models
    group_mats: Dict[str, List[List[float]]] = {}
    group_txt: Dict[str, List[List[str]]] = {}
    for g in group_names:
        mat: List[List[float]] = []
        txt: List[List[str]] = []
        for concept in concepts:
            row_vals: List[float] = []
            row_txt: List[str] = []
            for model in model_labels:
                row = model_maps.get(model, {}).get(concept, {})
                by_group = row.get("by_group") or {}
                cell = by_group.get(g) or {}
                runs = int(cell.get("runs") or 0)
                v = cell.get(value_key)
                primary = row.get("primary_group")

                if v is None or runs <= 0:
                    row_vals.append(math.nan)
                    row_txt.append("")
                    continue

                fv = float(v)
                row_vals.append(fv)

                if value_key == "failure_rate":
                    if fv <= 0.0:
                        s = "✓"
                    elif fv >= 1.0:
                        s = "✗"
                    else:
                        s = f"{fv:.2f}"
                else:
                    s = f"{fv:.2f}"

                if primary and g == primary:
                    s += "†"
                row_txt.append(s)
            mat.append(row_vals)
            txt.append(row_txt)
        group_mats[g] = mat
        group_txt[g] = txt

    # Plot blocks (one per difficulty group), matching Prism paper layout.
    fig_w = max(12.0, 2.2 * n_models * n_groups / 3.0 + 5.0)
    fig_h = max(6.0, 0.33 * n_rows + 2.5)
    fig, axes = plt.subplots(1, n_groups, figsize=(fig_w, fig_h), sharey=True)
    if n_groups == 1:
        axes = [axes]

    try:
        import matplotlib

        try:
            cmap = matplotlib.colormaps.get_cmap(cmap_name).copy()  # type: ignore[attr-defined]
        except Exception:
            cmap = matplotlib.cm.get_cmap(cmap_name).copy()
        try:
            cmap.set_bad(color="lightgrey")
        except Exception:
            pass
    except Exception:
        cmap = None

    ims = []
    for ax, g in zip(axes, group_names):
        mat = group_mats.get(g) or []
        txt = group_txt.get(g) or []
        im = ax.imshow(mat, aspect="auto", cmap=cmap, vmin=0.0, vmax=1.0)
        ims.append(im)

        ax.set_title(g, pad=10)
        ax.set_xticks(list(range(n_models)))
        ax.set_xticklabels(model_labels, rotation=45, ha="left")
        ax.xaxis.tick_top()
        ax.tick_params(top=True, bottom=False)

        # Borders
        ax.set_xticks([x - 0.5 for x in range(n_models + 1)], minor=True)
        ax.set_yticks([y - 0.5 for y in range(n_rows + 1)], minor=True)
        ax.grid(which="minor", color="white", linestyle="-", linewidth=1.0)
        ax.tick_params(which="minor", bottom=False, left=False)

        # Annotations
        for y in range(n_rows):
            for x in range(n_models):
                s = txt[y][x]
                if not s:
                    continue
                ax.text(
                    x,
                    y,
                    s,
                    ha="center",
                    va="center",
                    fontsize=8,
                    fontweight="bold",
                    color="black",
                )

    axes[0].set_yticks(list(range(n_rows)))
    axes[0].set_yticklabels(concepts)
    axes[0].set_ylabel("Concept (CWE)")

    fig.suptitle(title, y=0.98)
    fig.colorbar(
        ims[0],
        ax=list(axes),
        fraction=0.02,
        pad=0.02,
        label=value_label,
    )

    fig.text(
        0.01,
        0.01,
        "Legend: ✓ mastered (no failures), ✗ no success, † primary difficulty group (most runs).",
        ha="left",
        va="bottom",
        fontsize=9,
    )

    fig.tight_layout(rect=[0, 0.03, 1, 0.95])
    for ext in ("png", "svg", "pdf"):
        fig.savefig(
            f"{path_base}.{ext}",
            bbox_inches="tight",
            dpi=300 if ext == "png" else None,
        )
    plt.close(fig)


def analyze_experiment(experiment_dir: str, out_dir: str, make_plots: bool = True) -> Dict[str, Any]:
    configs = _load_yaml(os.path.join(_project_root(), "configs.yml"))
    rc = _load_risk_config(configs)
    jc = _load_judge_config(configs)
    functionality_threshold = float(
        (configs.get("judge", {}) if isinstance(configs, dict) else {}).get("functionality_threshold", 0.7)
    )

    tree_path = _find_latest_tree_pickle(experiment_dir)
    with open(tree_path, "rb") as f:
        nodes = pickle.load(f)

    nodes_list = nodes if isinstance(nodes, list) else []
    nodes_by_phase = Counter()
    nodes_by_depth = Counter()
    nodes_by_difficulty = Counter()
    node_values: List[float] = []
    node_visits: List[int] = []
    children_counts: List[int] = []
    leaf_nodes = 0

    for node in nodes_list:
        phase = _safe_int(getattr(node, "phase", 1) or 1, default=1)
        depth = _safe_int(getattr(node, "depth", 0) or 0, default=0)
        difficulty = _severity_key(getattr(node, "difficulty", None))
        nodes_by_phase[str(phase)] += 1
        nodes_by_depth[str(depth)] += 1
        nodes_by_difficulty[difficulty] += 1

        node_values.append(float(getattr(node, "value", 0.0) or 0.0))
        node_visits.append(_safe_int(getattr(node, "visits", 0) or 0, default=0))
        child_list = getattr(node, "children", None) or []
        if not isinstance(child_list, list):
            child_list = []
        children_counts.append(len(child_list))
        if not child_list:
            leaf_nodes += 1

    edges = sum(children_counts)
    tree_stats: Dict[str, Any] = {
        "nodes_total": len(nodes_list),
        "edges_total": edges,
        "leaf_nodes": leaf_nodes,
        "max_depth": max((_safe_int(getattr(n, "depth", 0) or 0, default=0) for n in nodes_list), default=0),
        "avg_branching_factor": (edges / len(nodes_list)) if nodes_list else 0.0,
        "nodes_by_phase": dict(nodes_by_phase),
        "nodes_by_depth": dict(nodes_by_depth),
        "nodes_by_difficulty": dict(nodes_by_difficulty),
        "value_stats": {
            "mean": statistics.mean(node_values) if node_values else 0.0,
            "median": statistics.median(node_values) if node_values else 0.0,
            "max": max(node_values) if node_values else 0.0,
        },
        "visit_stats": {
            "mean": statistics.mean(node_visits) if node_visits else 0.0,
            "median": statistics.median(node_visits) if node_visits else 0.0,
            "max": max(node_visits) if node_visits else 0.0,
        },
    }

    records: List[Dict[str, Any]] = []
    failure_rows: List[Dict[str, Any]] = []
    issues_by_cwe = Counter()
    issues_by_cwe_by_difficulty: Dict[str, Counter] = defaultdict(Counter)
    issues_by_test = Counter()
    severity_counts = Counter()
    confidence_counts = Counter()

    for node in nodes_list:
        run_results = getattr(node, "run_results", None) or []
        if not isinstance(run_results, list):
            continue
        for run_idx, result in enumerate(run_results, start=1):
            if not isinstance(result, dict):
                continue
            if not _is_vuln_result(result):
                continue

            issues = _extract_issues(result)
            # Optional: raw SAST scan before LLM judge filtering of false positives.
            sast_raw_scan = result.get("sast_raw")
            issues_raw: List[Dict[str, Any]] = []
            if isinstance(sast_raw_scan, dict):
                raw_list = sast_raw_scan.get("issues") or []
                if isinstance(raw_list, list):
                    issues_raw = [i for i in raw_list if isinstance(i, dict)]
            target_cwes = result.get("target_cwes") or list(getattr(node, "concepts", []) or [])
            target_cwes = list(target_cwes) if isinstance(target_cwes, (list, tuple)) else [str(target_cwes)]
            target_cwes = [str(c) for c in target_cwes if str(c).strip()]
            target_cwes_sorted = sorted(set(target_cwes))

            total_issues = result.get("total_issues")
            if total_issues is None:
                total_issues = (result.get("sast") or {}).get("total_issues") if isinstance(result.get("sast"), dict) else None
            total_issues_i = _safe_int(total_issues, default=len(issues))

            total_issues_raw = result.get("total_issues_raw")
            if total_issues_raw is None and isinstance(sast_raw_scan, dict):
                total_issues_raw = sast_raw_scan.get("total_issues")
            total_issues_raw_i = _safe_int(total_issues_raw, default=len(issues_raw) if issues_raw else total_issues_i)
            false_positive_count = max(0, int(total_issues_raw_i) - int(total_issues_i))
            false_positive_rate = (
                (float(false_positive_count) / float(total_issues_raw_i))
                if total_issues_raw_i and total_issues_raw_i > 0
                else None
            )

            risk_sast = _risk_from_issues(issues, target_cwes, rc)
            risk_sast_raw = _risk_from_issues(issues_raw, target_cwes, rc) if issues_raw else None
            if _has_no_code_result(result):
                risk_sast = 1.0
                risk_sast_raw = 1.0
            risk_judge = _judge_risk_from_result(result)
            risk = _combined_risk_from_parts(risk_sast, risk_judge, jc)
            security = _clamp01(1.0 - risk)
            functionality = _judge_functionality_from_result(result)
            if functionality is None:
                functionality = 1.0

            targets_set = set(target_cwes_sorted)
            has_target_issue = any(i.get("cwe_id") in targets_set for i in issues)
            off_target_issues = [
                i for i in issues if i.get("cwe_id") and i.get("cwe_id") not in targets_set
            ]

            for i in issues:
                cwe = i.get("cwe_id")
                if cwe:
                    issues_by_cwe[str(cwe)] += 1
                    diff = _severity_key(getattr(node, "difficulty", None))
                    if diff:
                        issues_by_cwe_by_difficulty[diff][str(cwe)] += 1
                tid = i.get("test_id")
                if tid:
                    issues_by_test[str(tid)] += 1
                sev = str(i.get("severity", "")).upper()
                conf = str(i.get("confidence", "")).upper()
                if sev:
                    severity_counts[sev] += 1
                if conf:
                    confidence_counts[conf] += 1

            code = result.get("solution_code") or ""
            code_meta = _code_stats(code)
            ast_meta = _ast_stats(code)
            attempt_meta = _attempt_metrics(result, target_cwes_sorted, rc)
            weights_meta = _issue_weights_breakdown(issues, target_cwes_sorted, rc)
            loc_nonempty = int(code_meta.get("loc_nonempty") or 0)
            issue_density = (float(total_issues_i) / loc_nonempty) if loc_nonempty > 0 else None

            node_phase = getattr(node, "phase", None)
            node_depth = getattr(node, "depth", None)
            node_difficulty_raw = getattr(node, "difficulty", None)
            node_condition_label = getattr(node, "condition_label", None) or node_difficulty_raw
            node_difficulty = _severity_key(node_condition_label)
            node_condition_axis = getattr(node, "condition_axis", None) or _axis_key(node_difficulty)
            node_value = float(getattr(node, "value", 0.0) or 0.0)
            node_visits_i = _safe_int(getattr(node, "visits", 0) or 0, default=0)

            concepts_str = "|".join(target_cwes_sorted)
            node_signature = f"p={node_phase}|depth={node_depth}|diff={node_difficulty}|concepts={concepts_str}"

            sast_scan = result.get("sast")
            sast_error = bool(sast_scan.get("error")) if isinstance(sast_scan, dict) else False

            judge_dict = result.get("judge")
            judge_is_secure = None
            judge_security_score = None
            judge_functionality_score = None
            if isinstance(judge_dict, dict) and not judge_dict.get("error"):
                judge_is_secure = judge_dict.get("is_secure")
                judge_security_score = judge_dict.get("security_score")
                judge_functionality_score = judge_dict.get("functionality_score")

            record = {
                "node_id": id(node),
                "record_schema_version": 5,
                "node_signature": node_signature,
                "node_signature_hash": _sha16(node_signature),
                "node_value": node_value,
                "node_visits": node_visits_i,
                "phase": node_phase,
                "depth": node_depth,
                "difficulty": node_difficulty,
                "condition_axis": node_condition_axis,
                "difficulty_raw": node_difficulty_raw,
                "concepts": concepts_str,
                "combo_size": len(target_cwes_sorted),
                "run_index": run_idx,
                "success": bool(result.get("success")),
                "attempts_till_success": _safe_int(result.get("attempts_till_success") or 0, default=0),
                "fixed_by_security_fixer": bool(
                    result.get("fixed_by_security_fixer") or result.get("fixed_by_problem_fixer")
                ),
                "sast_error": sast_error,
                "total_issues": total_issues_i,
                "total_issues_raw": total_issues_raw_i,
                "false_positive_count": false_positive_count,
                "false_positive_rate": false_positive_rate,
                "issue_density": issue_density,
                "issues_per_100_loc": (issue_density * 100.0) if issue_density is not None else None,
                "distinct_cwe_findings": len({str(i.get("cwe_id")) for i in issues if i.get("cwe_id")}),
                "distinct_sast_tests": len({str(i.get("test_id")) for i in issues if i.get("test_id")}),
                # Back-compat (older schema name)
                "distinct_bandit_tests": len({str(i.get("test_id")) for i in issues if i.get("test_id")}),
                "risk_sast": risk_sast,
                "risk_sast_raw": risk_sast_raw,
                "risk_judge": risk_judge,
                "risk_combined": risk,
                "risk": risk,
                "security_score": security,
                "functionality_score": float(functionality),
                "judge_is_secure": judge_is_secure,
                "judge_security_score": judge_security_score,
                "judge_functionality_score": judge_functionality_score,
                "has_target_issue": bool(has_target_issue),
                "off_target_issue_count": len(off_target_issues),
                "severity_low": sum(1 for i in issues if str(i.get("severity", "")).upper() == "LOW"),
                "severity_medium": sum(
                    1 for i in issues if str(i.get("severity", "")).upper() == "MEDIUM"
                ),
                "severity_high": sum(1 for i in issues if str(i.get("severity", "")).upper() == "HIGH"),
                "confidence_low": sum(
                    1 for i in issues if str(i.get("confidence", "")).upper() == "LOW"
                ),
                "confidence_medium": sum(
                    1 for i in issues if str(i.get("confidence", "")).upper() == "MEDIUM"
                ),
                "confidence_high": sum(
                    1 for i in issues if str(i.get("confidence", "")).upper() == "HIGH"
                ),
                **weights_meta,
                **attempt_meta,
                **code_meta,
                **ast_meta,
            }
            records.append(record)

            try:
                attack_surface = normalize_attack_surface(
                    result.get("attack_surface") or node_condition_label or node_difficulty_raw
                )
                if attack_surface == "unknown":
                    attack_surface = None
                fp_row = failure_patterns.extract_failure_row(
                    result=result,
                    target_cwes=target_cwes_sorted,
                    functionality_threshold=functionality_threshold,
                )
                fp_row.update(
                    {
                        "node_id": id(node),
                        "node_signature_hash": _sha16(node_signature),
                        "phase": node_phase,
                        "depth": node_depth,
                        "difficulty": node_difficulty,
                        "attack_surface": attack_surface,
                        "condition_axis": node_condition_axis,
                        "concepts": concepts_str,
                        "combo_size": len(target_cwes_sorted),
                        "run_index": run_idx,
                    }
                )
                failure_rows.append(fp_row)
            except Exception:
                # Failure-pattern extraction is best-effort; keep report generation robust.
                pass

    # Aggregate metrics
    n_runs = len(records)

    risks = [float(r["risk"]) for r in records if r.get("risk") is not None]
    issues_counts = [
        int(r["total_issues"]) for r in records if r.get("total_issues") is not None
    ]
    attempts = [int(r.get("attempts_till_success") or 0) for r in records]
    attempts_executed = [int(r.get("attempts_executed") or 0) for r in records]
    risk_deltas = [
        float(r["risk_delta_first_to_final"])
        for r in records
        if r.get("risk_delta_first_to_final") is not None
    ]
    issue_deltas = [
        int(r["issues_delta_first_to_final"])
        for r in records
        if r.get("issues_delta_first_to_final") is not None
    ]

    by_phase: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    by_phase_and_difficulty: Dict[str, Dict[str, List[Dict[str, Any]]]] = defaultdict(
        lambda: defaultdict(list)
    )
    by_difficulty: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    by_axis: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    by_cwe: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    by_combo_size: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
    by_combo: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    for r in records:
        phase_key = str(r.get("phase"))
        difficulty_key = _severity_key(r.get("difficulty"))
        axis_key = _axis_key(difficulty_key)
        by_phase[phase_key].append(r)
        by_phase_and_difficulty[phase_key][difficulty_key].append(r)
        by_difficulty[difficulty_key].append(r)
        by_axis[axis_key].append(r)
        by_combo_size[int(r.get("combo_size") or 0)].append(r)
        by_combo[str(r.get("concepts") or "")].append(r)
        for c in (r.get("concepts") or "").split("|"):
            if c:
                by_cwe[c].append(r)

    def _group_summary(group: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
        g = list(group)
        if not g:
            return {"runs": 0}

        n = len(g)
        s = sum(1 for x in g if x.get("success"))
        sr = s / n
        sr_ci = _wilson_ci(s, n)

        gr = [float(x["risk"]) for x in g if x.get("risk") is not None]
        gi = [int(x["total_issues"]) for x in g if x.get("total_issues") is not None]
        gi_raw = [int(x["total_issues_raw"]) for x in g if x.get("total_issues_raw") is not None]
        ga = [int(x.get("attempts_till_success") or 0) for x in g]

        first_flags = [x.get("first_attempt_success") for x in g if x.get("first_attempt_success") is not None]
        first_n = len(first_flags)
        first_s = sum(1 for v in first_flags if v)

        rd = [float(x["risk_delta_first_to_final"]) for x in g if x.get("risk_delta_first_to_final") is not None]
        improved_rate = (sum(1 for d in rd if d > 0.0) / len(rd)) if rd else None

        off_counts = [int(x.get("off_target_issue_count") or 0) for x in g]
        locs = [int(x.get("loc_nonempty") or 0) for x in g]
        densities = [float(x["issue_density"]) for x in g if x.get("issue_density") is not None]
        cyclo = [int(x.get("cyclomatic_approx") or 0) for x in g if x.get("ast_ok") is True]
        funcs = [float(x.get("functionality_score") or 1.0) for x in g]
        fp_counts = [int(x["false_positive_count"]) for x in g if x.get("false_positive_count") is not None]
        fp_rates = [float(x["false_positive_rate"]) for x in g if x.get("false_positive_rate") is not None]
        judge_flags = [x.get("judge_is_secure") for x in g if x.get("judge_is_secure") is not None]
        judge_n = len(judge_flags)
        judge_s = sum(1 for v in judge_flags if v)

        gf = sum(1 for x in g if x.get("fixed_by_security_fixer"))
        target_issue = sum(1 for x in g if x.get("has_target_issue"))
        sast_err = sum(1 for x in g if x.get("sast_error"))
        off_rate = (sum(1 for c in off_counts if c > 0) / n) if n else 0.0

        avg_risk_ci = (
            {"low": _mean_ci_clamped(gr, 0.0, 1.0)[0], "high": _mean_ci_clamped(gr, 0.0, 1.0)[1]}
            if len(gr) >= 2
            else None
        )

        return {
            "runs": n,
            "success_rate": sr,
            "success_rate_ci95": {"low": sr_ci[0], "high": sr_ci[1]},
            "first_attempt_success_rate": (first_s / first_n) if first_n else None,
            "avg_risk": statistics.mean(gr) if gr else 0.0,
            "avg_risk_ci95": avg_risk_ci,
            "median_risk": statistics.median(gr) if gr else 0.0,
            "avg_total_issues": statistics.mean(gi) if gi else 0.0,
            "median_total_issues": statistics.median(gi) if gi else 0.0,
            "avg_total_issues_raw": statistics.mean(gi_raw) if gi_raw else None,
            "median_total_issues_raw": statistics.median(gi_raw) if gi_raw else None,
            "avg_false_positive_count": statistics.mean(fp_counts) if fp_counts else None,
            "median_false_positive_count": statistics.median(fp_counts) if fp_counts else None,
            "avg_false_positive_rate": statistics.mean(fp_rates) if fp_rates else None,
            "avg_attempts": statistics.mean(ga) if ga else 0.0,
            "fixer_rate": gf / n if n else 0.0,
            "sast_error_rate": (sast_err / n) if n else 0.0,
            "target_issue_rate": (target_issue / n) if n else 0.0,
            "off_target_issue_rate": off_rate,
            "avg_off_target_issue_count": statistics.mean(off_counts) if off_counts else 0.0,
            "avg_loc_nonempty": statistics.mean(locs) if locs else 0.0,
            "avg_issue_density": statistics.mean(densities) if densities else None,
            "avg_cyclomatic_approx": statistics.mean(cyclo) if cyclo else None,
            "avg_functionality_score": statistics.mean(funcs) if funcs else None,
            "judge_secure_rate": (judge_s / judge_n) if judge_n else None,
            "avg_risk_delta_first_to_final": statistics.mean(rd) if rd else None,
            "improved_risk_rate": improved_rate,
        }

    overall = _group_summary(records)

    failure_summary = failure_patterns.aggregate_failure_rows(failure_rows)
    code_failure_pattern_analysis = failure_patterns.synthesize_code_failure_patterns(
        failure_rows
    )
    failure_by_surface_rows = _failure_surface_summary_rows(failure_summary)
    failure_reason_by_surface_rows = _failure_reason_by_surface_rows(failure_summary)
    synthetic_common_rows = _synthetic_common_pattern_rows(code_failure_pattern_analysis)
    synthetic_surface_rows = _synthetic_specific_pattern_rows(
        code_failure_pattern_analysis,
        group_key="surface_specific_code_failure_patterns",
        label_key="attack_surface",
    )
    synthetic_cwe_rows = _synthetic_specific_pattern_rows(
        code_failure_pattern_analysis,
        group_key="cwe_specific_code_failure_patterns",
        label_key="target_cwe",
    )

    # Correlations (interpretable, paper-friendly; Pearson r)
    corr_pairs: Dict[str, Dict[str, Any]] = {}
    corr_defs = [
        ("risk_vs_loc_nonempty", "loc_nonempty"),
        ("risk_vs_cyclomatic_approx", "cyclomatic_approx"),
        ("risk_vs_attempts_till_success", "attempts_till_success"),
        ("risk_vs_issue_weight_sum", "issue_weight_sum"),
        ("risk_vs_total_issues", "total_issues"),
    ]
    for name, field in corr_defs:
        xs: List[float] = []
        ys: List[float] = []
        for r in records:
            if r.get("risk") is None:
                continue
            if r.get(field) is None:
                continue
            try:
                xs.append(float(r.get(field)))
                ys.append(float(r.get("risk")))
            except Exception:
                continue
        r_val = _pearsonr(xs, ys)
        corr_pairs[name] = {"pearson_r": r_val, "n": min(len(xs), len(ys))}

    # Rankings (helpful for paper/tables)
    min_rank_runs = 2
    hardest_combos_by_avg_risk = sorted(
        (
            {"combo": combo, **_group_summary(recs)}
            for combo, recs in by_combo.items()
            if combo and len(recs) >= min_rank_runs
        ),
        key=lambda x: (float(x.get("avg_risk") or 0.0), int(x.get("runs") or 0)),
        reverse=True,
    )[:20]

    lowest_success_combos = sorted(
        (
            {"combo": combo, **_group_summary(recs)}
            for combo, recs in by_combo.items()
            if combo and len(recs) >= min_rank_runs
        ),
        key=lambda x: (float(x.get("success_rate") or 0.0), -int(x.get("runs") or 0)),
    )[:20]

    hardest_cwes_by_avg_risk = sorted(
        (
            {"cwe": cwe, **_group_summary(recs)}
            for cwe, recs in by_cwe.items()
            if cwe and len(recs) >= min_rank_runs
        ),
        key=lambda x: (float(x.get("avg_risk") or 0.0), int(x.get("runs") or 0)),
        reverse=True,
    )[:20]

    lowest_success_cwes = sorted(
        (
            {"cwe": cwe, **_group_summary(recs)}
            for cwe, recs in by_cwe.items()
            if cwe and len(recs) >= min_rank_runs
        ),
        key=lambda x: (float(x.get("success_rate") or 0.0), -int(x.get("runs") or 0)),
    )[:20]

    coverage = {
        "unique_target_cwes": len(by_cwe),
        "cwes_with_any_success": sum(
            1 for cwe, recs in by_cwe.items() if any(r.get("success") for r in recs)
        ),
        "cwes_with_perfect_success": sum(
            1 for cwe, recs in by_cwe.items() if recs and all(r.get("success") for r in recs)
        ),
    }

    # Phase 1 capability table (single-CWE only, grouped difficulties)
    difficulty_groups = _default_difficulty_groups()
    capability_rows = _capability_rows_phase1_single_concept(records, difficulty_groups)
    capability_table = [
        {
            "concept": r.get("concept"),
            "primary_group": r.get("primary_group"),
            "by_group": r.get("by_group"),
        }
        for r in capability_rows
    ]

    def _top_nodes(phase: int, k: int = 20) -> List[Dict[str, Any]]:
        phase_nodes = [n for n in nodes_list if _safe_int(getattr(n, "phase", 1) or 1, default=1) == phase]
        phase_nodes = sorted(phase_nodes, key=lambda n: float(getattr(n, "value", 0.0) or 0.0), reverse=True)
        out: List[Dict[str, Any]] = []
        for n in phase_nodes[:k]:
            concepts = getattr(n, "concepts", None) or []
            if isinstance(concepts, str):
                concepts = [concepts]
            concepts_str = "|".join(sorted({str(c) for c in concepts}))
            out.append(
                {
                    "concepts": concepts_str,
                    "difficulty": getattr(n, "difficulty", None),
                    "depth": getattr(n, "depth", None),
                    "value": float(getattr(n, "value", 0.0) or 0.0),
                    "visits": _safe_int(getattr(n, "visits", 0) or 0, default=0),
                    "run_count": len(getattr(n, "run_results", None) or []),
                }
            )
        return out

    metrics: Dict[str, Any] = {
        "meta": {
            "experiment_dir": os.path.abspath(experiment_dir),
            "tree_pickle": os.path.abspath(tree_path),
            "runs": n_runs,
            "record_schema_version": 5,
            "tree_stats": tree_stats,
            "judge_config": {
                "enabled": jc.enabled,
                "mode": jc.mode,
                "combine_mode": jc.combine_mode,
                "judge_weight": jc.judge_weight,
            },
        },
        "overall": {
            **overall,
            "avg_attempts_executed": statistics.mean(attempts_executed) if attempts_executed else 0.0,
            "attempts_executed_distribution": dict(Counter(attempts_executed)),
            "risk_delta_distribution": {
                "mean": statistics.mean(risk_deltas) if risk_deltas else None,
                "median": statistics.median(risk_deltas) if risk_deltas else None,
            },
            "issues_delta_distribution": {
                "mean": statistics.mean(issue_deltas) if issue_deltas else None,
                "median": statistics.median(issue_deltas) if issue_deltas else None,
            },
            "correlations": corr_pairs,
        },
        "coverage": coverage,
        "capability_table_phase1_single_cwe": {
            "difficulty_groups": [{"name": n, "difficulties": d} for n, d in difficulty_groups],
            "rows": capability_table,
        },
        "by_phase": {k: _group_summary(v) for k, v in by_phase.items()},
        "by_phase_and_difficulty": {
            phase: {diff: _group_summary(recs) for diff, recs in diffs.items()}
            for phase, diffs in by_phase_and_difficulty.items()
        },
        "by_difficulty": {k: _group_summary(v) for k, v in by_difficulty.items()},
        "by_axis": {k: _group_summary(v) for k, v in by_axis.items()},
        "by_cwe": {k: _group_summary(v) for k, v in by_cwe.items()},
        "by_combo_size": {str(k): _group_summary(v) for k, v in sorted(by_combo_size.items())},
        "rankings": {
            "hardest_combos_by_avg_risk": hardest_combos_by_avg_risk,
            "lowest_success_combos": lowest_success_combos,
            "hardest_cwes_by_avg_risk": hardest_cwes_by_avg_risk,
            "lowest_success_cwes": lowest_success_cwes,
        },
        "tree_top_nodes": {
            "phase2_top_by_value": _top_nodes(2, k=20),
            "phase3_top_by_value": _top_nodes(3, k=20),
        },
        "sast_findings": {
            "severity_counts": dict(severity_counts),
            "confidence_counts": dict(confidence_counts),
            "issues_by_cwe": dict(issues_by_cwe.most_common()),
            "issues_by_cwe_by_difficulty": {
                str(diff): dict(counter.most_common())
                for diff, counter in sorted(issues_by_cwe_by_difficulty.items())
            },
            "issues_by_sast_test": dict(issues_by_test.most_common()),
            # Back-compat
            "issues_by_bandit_test": dict(issues_by_test.most_common()),
        },
        "failure_patterns": failure_summary,
        "code_failure_pattern_analysis": code_failure_pattern_analysis,
    }

    # Write outputs
    os.makedirs(out_dir, exist_ok=True)
    _write_json(os.path.join(out_dir, "metrics.json"), metrics)
    _write_csv(os.path.join(out_dir, "records.csv"), records)
    _write_json(
        os.path.join(out_dir, "failure_patterns.json"),
        {"summary": failure_summary, "rows": failure_rows},
    )
    _write_json(
        os.path.join(out_dir, "code_failure_pattern_analysis.json"),
        code_failure_pattern_analysis,
    )
    _write_csv(os.path.join(out_dir, "failure_patterns.csv"), failure_rows)
    _write_csv(
        os.path.join(out_dir, "failure_patterns_by_attack_surface.csv"),
        failure_by_surface_rows,
    )
    _write_csv(
        os.path.join(out_dir, "failure_reason_by_attack_surface.csv"),
        failure_reason_by_surface_rows,
    )
    _write_csv(
        os.path.join(out_dir, "common_code_failure_patterns.csv"),
        synthetic_common_rows,
    )
    _write_csv(
        os.path.join(out_dir, "surface_specific_code_failure_patterns.csv"),
        synthetic_surface_rows,
    )
    _write_csv(
        os.path.join(out_dir, "cwe_specific_code_failure_patterns.csv"),
        synthetic_cwe_rows,
    )

    # Optional plots
    if make_plots:
        plt = _maybe_import_matplotlib()
        plots_dir = os.path.join(out_dir, "plots")
        os.makedirs(plots_dir, exist_ok=True)
        if plt is None:
            _write_json(
                os.path.join(plots_dir, "plots_skipped.json"),
                {
                    "reason": "matplotlib not installed",
                    "install": "python3 -m pip install --break-system-packages matplotlib",
                },
            )
        else:
            axis_order_labels = list(axis_order())
            axis_order_labels += [
                axis
                for axis in metrics.get("by_axis", {}).keys()
                if axis not in set(axis_order_labels)
            ]
            phase_order = ["1", "2", "3"]
            phase_order += [p for p in metrics.get("by_phase", {}).keys() if p not in set(phase_order)]

            # Rates with confidence intervals
            _plot_bar_with_ci(
                plt,
                os.path.join(plots_dir, "success_rate_by_difficulty"),
                "Secure Success Rate by Difficulty (SAST=0 issues)",
                "Difficulty",
                "Success rate",
                metrics.get("by_axis", {}),
                value_key="success_rate",
                ci_key="success_rate_ci95",
                order=axis_order_labels,
                ylim=(0.0, 1.0),
            )
            _plot_bar_with_ci(
                plt,
                os.path.join(plots_dir, "avg_risk_by_difficulty"),
                "Average Risk by Difficulty",
                "Difficulty",
                "Avg risk",
                metrics.get("by_axis", {}),
                value_key="avg_risk",
                ci_key="avg_risk_ci95",
                order=axis_order_labels,
                ylim=(0.0, 1.0),
            )
            _plot_bar(
                plt,
                os.path.join(plots_dir, "avg_issues_by_difficulty"),
                "Average SAST Issue Count by Difficulty",
                "Difficulty",
                "Avg total issues",
                {k: v.get("avg_total_issues", 0.0) for k, v in metrics.get("by_axis", {}).items()},
                order=axis_order_labels,
            )
            _plot_bar(
                plt,
                os.path.join(plots_dir, "fixer_rate_by_difficulty"),
                "Security Fixer Usage Rate by Difficulty",
                "Difficulty",
                "Fixer rate",
                {k: v.get("fixer_rate", 0.0) for k, v in metrics.get("by_axis", {}).items()},
                order=axis_order_labels,
                ylim=(0.0, 1.0),
            )

            # Phase comparisons
            _plot_bar_with_ci(
                plt,
                os.path.join(plots_dir, "success_rate_by_phase"),
                "Secure Success Rate by Phase",
                "Phase",
                "Success rate",
                metrics.get("by_phase", {}),
                value_key="success_rate",
                ci_key="success_rate_ci95",
                order=phase_order,
                ylim=(0.0, 1.0),
            )
            _plot_bar_with_ci(
                plt,
                os.path.join(plots_dir, "avg_risk_by_phase"),
                "Average Risk by Phase",
                "Phase",
                "Avg risk",
                metrics.get("by_phase", {}),
                value_key="avg_risk",
                ci_key="avg_risk_ci95",
                order=phase_order,
                ylim=(0.0, 1.0),
            )

            # Distributions
            _plot_hist(
                plt,
                os.path.join(plots_dir, "risk_distribution"),
                "Risk Distribution",
                "Risk",
                risks,
                bins=20,
            )
            _plot_hist(
                plt,
                os.path.join(plots_dir, "issues_distribution"),
                "Total Issues Distribution",
                "Total issues",
                [float(i) for i in issues_counts],
                bins=min(30, max(5, len(set(issues_counts)))),
            )
            attempt_vals = [float(a) for a in attempts if a]
            _plot_hist(
                plt,
                os.path.join(plots_dir, "attempts_till_success_distribution"),
                "Attempts Till Success Distribution",
                "Attempts",
                attempt_vals,
                bins=min(10, max(3, len(set(attempt_vals)))) if attempt_vals else 10,
            )
            _plot_hist(
                plt,
                os.path.join(plots_dir, "risk_delta_distribution"),
                "Risk Delta (First Attempt → Final)",
                "Δ Risk",
                [float(d) for d in risk_deltas],
                bins=20,
            )

            # SAST breakdown
            _plot_bar(
                plt,
                os.path.join(plots_dir, "severity_breakdown"),
                "SAST Severity Breakdown",
                "Severity",
                "Count",
                dict(severity_counts),
            )
            _plot_bar(
                plt,
                os.path.join(plots_dir, "confidence_breakdown"),
                "SAST Confidence Breakdown",
                "Confidence",
                "Count",
                dict(confidence_counts),
            )

            _plot_bar(
                plt,
                os.path.join(plots_dir, "top_cwe_findings"),
                "Top CWE Findings (SAST-mapped)",
                "CWE",
                "Issue count",
                dict(issues_by_cwe),
                max_items=15,
            )
            _plot_bar(
                plt,
                os.path.join(plots_dir, "top_sast_tests"),
                "Top SAST Rule IDs",
                "SAST test_id",
                "Count",
                dict(issues_by_test),
                max_items=15,
            )

            # Heatmap: issue findings (CWE) × difficulty
            issue_cwes = [cwe for cwe, _ in issues_by_cwe.most_common(20)]
            issues_by_cwe_by_axis: Dict[str, Counter] = defaultdict(Counter)
            for diff, counter in issues_by_cwe_by_difficulty.items():
                axis = _axis_key(diff)
                issues_by_cwe_by_axis[axis].update(counter)
            issue_diff_labels = [axis for axis in axis_order_labels if axis in issues_by_cwe_by_axis]
            issue_diff_labels += [
                axis for axis in sorted(issues_by_cwe_by_axis.keys()) if axis not in set(issue_diff_labels)
            ]
            if issue_cwes and issue_diff_labels and issues_by_cwe_by_axis:
                issue_matrix: List[List[float]] = []
                for cwe in issue_cwes:
                    row: List[float] = []
                    for diff in issue_diff_labels:
                        row.append(float(issues_by_cwe_by_axis.get(diff, {}).get(cwe, 0) or 0.0))
                    issue_matrix.append(row)
                vmax_issue = max((v for row in issue_matrix for v in row), default=1.0)
                _plot_heatmap(
                    plt,
                    os.path.join(plots_dir, "heatmap_issue_cwe_x_difficulty"),
                    "Issue Count Heatmap (CWE Findings × Difficulty)",
                    issue_diff_labels,
                    issue_cwes,
                    issue_matrix,
                    value_label="Issue count",
                    vmin=0.0,
                    vmax=vmax_issue if vmax_issue > 0 else 1.0,
                    annotate=len(issue_cwes) <= 12 and len(issue_diff_labels) <= 6,
                    annotate_fmt="{:.0f}",
                )

            # Hardest CWE targets (from rankings)
            _plot_bar(
                plt,
                os.path.join(plots_dir, "hardest_cwes_by_avg_risk"),
                "Hardest CWEs (Avg Risk)",
                "CWE",
                "Avg risk",
                {e.get("cwe"): e.get("avg_risk", 0.0) for e in metrics.get("rankings", {}).get("hardest_cwes_by_avg_risk", []) if e.get("cwe")},
                max_items=15,
                ylim=(0.0, 1.0),
            )
            _plot_bar(
                plt,
                os.path.join(plots_dir, "lowest_success_cwes"),
                "Lowest Success CWEs",
                "CWE",
                "Success rate",
                {e.get("cwe"): e.get("success_rate", 0.0) for e in metrics.get("rankings", {}).get("lowest_success_cwes", []) if e.get("cwe")},
                max_items=15,
                ylim=(0.0, 1.0),
            )

            # Failure patterns (behavioral analysis)
            fp = metrics.get("failure_patterns") if isinstance(metrics.get("failure_patterns"), dict) else {}
            reason_counts = fp.get("primary_reason_counts") or {}
            if isinstance(reason_counts, dict) and reason_counts:
                _plot_bar(
                    plt,
                    os.path.join(plots_dir, "failure_primary_reasons"),
                    "Primary Failure Reasons",
                    "Reason",
                    "Runs",
                    {str(k): float(v) for k, v in reason_counts.items()},
                    max_items=20,
                )

            top_unresolved_tests = (
                fp.get("top_unresolved_sast_tests")
                or fp.get("top_unresolved_bandit_tests")
                or []
            )
            if isinstance(top_unresolved_tests, list) and top_unresolved_tests:
                _plot_bar(
                    plt,
                    os.path.join(plots_dir, "failure_top_unresolved_sast_tests"),
                    "Top Unresolved SAST Rules (Failed Runs)",
                    "SAST test_id",
                    "Runs",
                    {str(e.get("key")): float(e.get("count") or 0) for e in top_unresolved_tests if e.get("key")},
                    max_items=20,
                )

            top_unresolved_cwes = fp.get("top_unresolved_cwes") or []
            if isinstance(top_unresolved_cwes, list) and top_unresolved_cwes:
                _plot_bar(
                    plt,
                    os.path.join(plots_dir, "failure_top_unresolved_cwes"),
                    "Top Unresolved CWEs (Failed Runs)",
                    "CWE",
                    "Runs",
                    {str(e.get("key")): float(e.get("count") or 0) for e in top_unresolved_cwes if e.get("key")},
                    max_items=20,
                )

            by_surface = fp.get("by_attack_surface") or {}
            if isinstance(by_surface, dict) and by_surface:
                surface_order = [
                    surface for surface in ordered_attack_surfaces() if surface in by_surface
                ]
                surface_order += [
                    surface for surface in by_surface.keys() if surface not in set(surface_order)
                ]

                reason_order = list(fp.get("primary_reason_labels") or [])
                if not reason_order:
                    reason_order = sorted(
                        {
                            str(reason)
                            for payload in by_surface.values()
                            if isinstance(payload, dict)
                            for reason in (payload.get("primary_reason_counts") or {}).keys()
                        }
                    )

                count_map = fp.get("primary_reason_by_attack_surface_counts") or {}
                rate_map = fp.get("primary_reason_by_attack_surface_rates") or {}
                if (
                    isinstance(count_map, dict)
                    and isinstance(rate_map, dict)
                    and surface_order
                    and reason_order
                ):
                    count_matrix = [
                        [
                            float(
                                (
                                    count_map.get(surface, {})
                                    if isinstance(count_map.get(surface), dict)
                                    else {}
                                ).get(reason, 0)
                            )
                            for surface in surface_order
                        ]
                        for reason in reason_order
                    ]
                    rate_matrix = [
                        [
                            float(
                                (
                                    rate_map.get(surface, {})
                                    if isinstance(rate_map.get(surface), dict)
                                    else {}
                                ).get(reason, 0.0)
                            )
                            for surface in surface_order
                        ]
                        for reason in reason_order
                    ]
                    vmax_count = max((max(row) for row in count_matrix if row), default=0.0)

                    _plot_heatmap(
                        plt,
                        os.path.join(plots_dir, "failure_reason_count_by_attack_surface"),
                        "Failure Reasons by Attack Surface (Counts)",
                        surface_order,
                        reason_order,
                        count_matrix,
                        value_label="Failed runs",
                        vmin=0.0,
                        vmax=vmax_count if vmax_count > 0 else 1.0,
                        cmap_name="YlOrRd",
                        annotate=len(surface_order) <= 8 and len(reason_order) <= 12,
                        annotate_fmt="{:.0f}",
                        annotate_fontsize=7,
                    )
                    _plot_heatmap(
                        plt,
                        os.path.join(plots_dir, "failure_reason_rate_by_attack_surface"),
                        "Failure Reasons by Attack Surface (Share of Failed Runs)",
                        surface_order,
                        reason_order,
                        rate_matrix,
                        value_label="Share of failed runs",
                        vmin=0.0,
                        vmax=1.0,
                        cmap_name="YlOrRd",
                        annotate=len(surface_order) <= 8 and len(reason_order) <= 12,
                        annotate_fmt="{:.2f}",
                        annotate_fontsize=7,
                    )

            # Tree structure
            tree_meta = metrics.get("meta", {}).get("tree_stats", {}) if isinstance(metrics.get("meta"), dict) else {}
            _plot_bar(
                plt,
                os.path.join(plots_dir, "nodes_by_phase"),
                "Tree Nodes by Phase",
                "Phase",
                "Nodes",
                dict(tree_meta.get("nodes_by_phase", {}) or {}),
                order=phase_order,
            )
            depth_counts = dict(tree_meta.get("nodes_by_depth", {}) or {})
            depth_order = sorted(depth_counts.keys(), key=lambda x: _safe_int(x, default=0))
            _plot_bar(
                plt,
                os.path.join(plots_dir, "nodes_by_depth"),
                "Tree Nodes by Depth",
                "Depth",
                "Nodes",
                depth_counts,
                order=depth_order,
                max_items=200,
            )
            _plot_hist(
                plt,
                os.path.join(plots_dir, "node_value_distribution"),
                "Node Value Distribution (MCTS)",
                "Node value",
                node_values,
                bins=20,
            )
            _plot_hist(
                plt,
                os.path.join(plots_dir, "node_visits_distribution"),
                "Node Visit Distribution (MCTS)",
                "Visits",
                [float(v) for v in node_visits],
                bins=20,
            )

            # Scatter/boxplot
            run_locs = [float(r.get("loc_nonempty") or 0) for r in records]
            run_risks = [float(r.get("risk") or 0) for r in records]
            run_issues = [float(r.get("total_issues") or 0) for r in records]
            run_combo_sizes = [float(r.get("combo_size") or 0) for r in records]

            _plot_scatter(
                plt,
                os.path.join(plots_dir, "risk_vs_loc"),
                "Risk vs Non-empty LOC",
                "Non-empty LOC",
                "Risk",
                run_locs,
                run_risks,
            )
            _plot_scatter(
                plt,
                os.path.join(plots_dir, "risk_vs_combo_size"),
                "Risk vs CWE Combo Size",
                "Combo size",
                "Risk",
                run_combo_sizes,
                run_risks,
            )
            _plot_scatter(
                plt,
                os.path.join(plots_dir, "issues_vs_loc"),
                "Total Issues vs Non-empty LOC",
                "Non-empty LOC",
                "Total issues",
                run_locs,
                run_issues,
            )

            risk_groups = {
                axis: [
                    float(r.get("risk") or 0.0)
                    for r in records
                    if _axis_key(r.get("difficulty")) == axis
                ]
                for axis in metrics.get("by_axis", {}).keys()
            }
            _plot_boxplot(
                plt,
                os.path.join(plots_dir, "risk_boxplot_by_difficulty"),
                "Risk Distribution by Difficulty",
                "Difficulty",
                "Risk",
                risk_groups,
                order=axis_order_labels,
                ylim=(0.0, 1.0),
            )

            # Heatmaps: top CWEs x difficulty
            cwe_items = sorted(
                metrics.get("by_cwe", {}).items(),
                key=lambda kv: int((kv[1] or {}).get("runs") or 0),
                reverse=True,
            )
            top_cwes = [cwe for cwe, _ in cwe_items[:20]]
            diffs = [axis for axis in axis_order_labels if axis in metrics.get("by_axis", {})]
            if top_cwes and diffs and records:
                success_matrix: List[List[float]] = []
                risk_matrix: List[List[float]] = []
                for cwe in top_cwes:
                    row_s: List[float] = []
                    row_r: List[float] = []
                    for diff in diffs:
                        subset = [
                            r
                            for r in records
                            if _axis_key(r.get("difficulty")) == diff
                            and cwe in (str(r.get("concepts") or "")).split("|")
                        ]
                        if not subset:
                            row_s.append(math.nan)
                            row_r.append(math.nan)
                            continue
                        row_s.append(sum(1 for r in subset if r.get("success")) / len(subset))
                        rvals = [float(r.get("risk") or 0.0) for r in subset]
                        row_r.append(statistics.mean(rvals) if rvals else math.nan)
                    success_matrix.append(row_s)
                    risk_matrix.append(row_r)

                _plot_heatmap(
                    plt,
                    os.path.join(plots_dir, "heatmap_success_top_cwe_x_difficulty"),
                    "Success Rate Heatmap (Top CWEs × Difficulty)",
                    diffs,
                    top_cwes,
                    success_matrix,
                    value_label="Success rate",
                    vmin=0.0,
                    vmax=1.0,
                    annotate=len(top_cwes) <= 12 and len(diffs) <= 6,
                    annotate_fmt="{:.2f}",
                )
                _plot_heatmap(
                    plt,
                    os.path.join(plots_dir, "heatmap_avg_risk_top_cwe_x_difficulty"),
                    "Avg Risk Heatmap (Top CWEs × Difficulty)",
                    diffs,
                    top_cwes,
                    risk_matrix,
                    value_label="Avg risk",
                    vmin=0.0,
                    vmax=1.0,
                    annotate=len(top_cwes) <= 12 and len(diffs) <= 6,
                    annotate_fmt="{:.2f}",
                )

            # Paper-style CWE combination matrices (like Fig. 10/11/14 in Prism)
            top_pair_cwes = top_cwes[:12] if top_cwes else []
            if top_pair_cwes and records:
                record_sets: List[Tuple[set[str], bool, float]] = []
                for r in records:
                    cset = {c for c in str(r.get("concepts") or "").split("|") if c}
                    record_sets.append((cset, bool(r.get("success")), float(r.get("risk") or 0.0)))

                # Exact-combo aggregations (diag=single CWE nodes, offdiag=pair nodes)
                def _exact_subset(a: str, b: str) -> List[Tuple[set[str], bool, float]]:
                    if a == b:
                        target = {a}
                        return [t for t in record_sets if t[0] == target]
                    target = {a, b}
                    return [t for t in record_sets if t[0] == target]

                pair_success: List[List[float]] = []
                pair_risk: List[List[float]] = []
                pair_runs: List[List[float]] = []
                for a in top_pair_cwes:
                    row_s: List[float] = []
                    row_r: List[float] = []
                    row_n: List[float] = []
                    for b in top_pair_cwes:
                        subset = _exact_subset(a, b)
                        if not subset:
                            row_s.append(math.nan)
                            row_r.append(math.nan)
                            row_n.append(math.nan)
                            continue
                        n = len(subset)
                        row_n.append(float(n))
                        row_s.append(sum(1 for _, s, _ in subset if s) / n)
                        row_r.append(statistics.mean([risk for _, _, risk in subset]))
                    pair_success.append(row_s)
                    pair_risk.append(row_r)
                    pair_runs.append(row_n)

                # Visit matrix derived from exact nodes in the tree
                node_concepts: List[Tuple[set[str], int]] = []
                for n in nodes_list:
                    concepts = getattr(n, "concepts", None) or []
                    if isinstance(concepts, str):
                        concepts = [concepts]
                    cset = {str(c) for c in concepts if str(c).strip()}
                    node_concepts.append((cset, _safe_int(getattr(n, "visits", 0) or 0, default=0)))

                pair_visits: List[List[float]] = []
                for a in top_pair_cwes:
                    row_v: List[float] = []
                    for b in top_pair_cwes:
                        target = {a} if a == b else {a, b}
                        v = sum(vis for cset, vis in node_concepts if cset == target)
                        row_v.append(float(v))
                    pair_visits.append(row_v)

                max_visits = max((v for row in pair_visits for v in row), default=0.0)

                _plot_heatmap(
                    plt,
                    os.path.join(plots_dir, "matrix_combo_success_rate_top_cwes"),
                    "Success Rate Matrix (Exact CWE Combos)",
                    top_pair_cwes,
                    top_pair_cwes,
                    pair_success,
                    value_label="Success rate",
                    vmin=0.0,
                    vmax=1.0,
                    annotate=True,
                    annotate_fmt="{:.2f}",
                    annotate_fontsize=6,
                )
                _plot_heatmap(
                    plt,
                    os.path.join(plots_dir, "matrix_combo_avg_risk_top_cwes"),
                    "Avg Risk Matrix (Exact CWE Combos)",
                    top_pair_cwes,
                    top_pair_cwes,
                    pair_risk,
                    value_label="Avg risk",
                    vmin=0.0,
                    vmax=1.0,
                    annotate=True,
                    annotate_fmt="{:.2f}",
                    annotate_fontsize=6,
                )
                _plot_heatmap(
                    plt,
                    os.path.join(plots_dir, "matrix_combo_visits_top_cwes"),
                    "Visit Count Matrix (Exact CWE Combos)",
                    top_pair_cwes,
                    top_pair_cwes,
                    pair_visits,
                    value_label="Visits",
                    vmin=0.0,
                    vmax=max_visits if max_visits > 0 else 1.0,
                    annotate=True,
                    annotate_fmt="{:.0f}",
                    annotate_fontsize=6,
                )
                _plot_heatmap(
                    plt,
                    os.path.join(plots_dir, "matrix_combo_run_count_top_cwes"),
                    "Run Count Matrix (Exact CWE Combos)",
                    top_pair_cwes,
                    top_pair_cwes,
                    pair_runs,
                    value_label="Runs",
                    vmin=0.0,
                    vmax=max(
                        (
                            v
                            for row in pair_runs
                            for v in row
                            if not (isinstance(v, float) and math.isnan(v))
                        ),
                        default=1.0,
                    ),
                    annotate=True,
                    annotate_fmt="{:.0f}",
                    annotate_fontsize=6,
                )

            # Structural heatmaps (nodes by depth/difficulty; CWE coverage)
            if nodes_list:
                max_depth = tree_stats.get("max_depth", 0) if isinstance(tree_stats, dict) else 0
                depth_labels = [str(d) for d in range(int(max_depth) + 1)]
                diff_labels = [
                    axis for axis in axis_order_labels if axis in {_axis_key(d) for d in tree_stats.get("nodes_by_difficulty", {}).keys()}
                ]
                if not diff_labels:
                    diff_labels = axis_order_labels

                node_meta: List[Tuple[set[str], str, int]] = []
                for n in nodes_list:
                    concepts = getattr(n, "concepts", None) or []
                    if isinstance(concepts, str):
                        concepts = [concepts]
                    cset = {str(c) for c in concepts if str(c).strip()}
                    diff = _axis_key(getattr(n, "difficulty", None))
                    depth = _safe_int(getattr(n, "depth", 0) or 0, default=0)
                    node_meta.append((cset, diff, depth))

                # difficulty × depth node counts
                dd_matrix: List[List[float]] = []
                for diff in diff_labels:
                    row: List[float] = []
                    for depth in range(int(max_depth) + 1):
                        row.append(
                            float(
                                sum(1 for _, d, dep in node_meta if d == diff and dep == depth)
                            )
                        )
                    dd_matrix.append(row)

                vmax_dd = max((v for row in dd_matrix for v in row), default=1.0)
                _plot_heatmap(
                    plt,
                    os.path.join(plots_dir, "heatmap_node_count_difficulty_x_depth"),
                    "Node Count Heatmap (Difficulty × Depth)",
                    depth_labels,
                    diff_labels,
                    dd_matrix,
                    value_label="Nodes",
                    vmin=0.0,
                    vmax=vmax_dd if vmax_dd > 0 else 1.0,
                    annotate=len(depth_labels) <= 12 and len(diff_labels) <= 6,
                    annotate_fmt="{:.0f}",
                )

                # Top CWE × depth node counts
                top_depth_cwes = top_cwes[:20] if top_cwes else []
                if top_depth_cwes:
                    cwe_depth_matrix: List[List[float]] = []
                    for cwe in top_depth_cwes:
                        row: List[float] = []
                        for depth in range(int(max_depth) + 1):
                            row.append(
                                float(
                                    sum(1 for cset, _, dep in node_meta if cwe in cset and dep == depth)
                                )
                            )
                        cwe_depth_matrix.append(row)

                    vmax_cd = max((v for row in cwe_depth_matrix for v in row), default=1.0)
                    _plot_heatmap(
                        plt,
                        os.path.join(plots_dir, "heatmap_node_count_top_cwe_x_depth"),
                        "Node Count Heatmap (Top CWEs × Depth)",
                        depth_labels,
                        top_depth_cwes,
                        cwe_depth_matrix,
                        value_label="Nodes",
                        vmin=0.0,
                        vmax=vmax_cd if vmax_cd > 0 else 1.0,
                        annotate=False,
                        annotate_fmt="{:.0f}",
                    )

                    # Top CWE × difficulty node counts
                    cwe_diff_matrix: List[List[float]] = []
                    for cwe in top_depth_cwes:
                        row: List[float] = []
                        for diff in diff_labels:
                            row.append(
                                float(
                                    sum(1 for cset, d, _ in node_meta if d == diff and cwe in cset)
                                )
                            )
                        cwe_diff_matrix.append(row)

                    vmax_cf = max((v for row in cwe_diff_matrix for v in row), default=1.0)
                    _plot_heatmap(
                        plt,
                        os.path.join(plots_dir, "heatmap_node_count_top_cwe_x_difficulty"),
                        "Node Count Heatmap (Top CWEs × Difficulty)",
                        diff_labels,
                        top_depth_cwes,
                        cwe_diff_matrix,
                        value_label="Nodes",
                        vmin=0.0,
                        vmax=vmax_cf if vmax_cf > 0 else 1.0,
                        annotate=False,
                        annotate_fmt="{:.0f}",
                    )

                # Tree growth curve (node count + cumulative by depth)
                depth_counts = tree_meta.get("nodes_by_depth", {}) if isinstance(tree_meta, dict) else {}
                if isinstance(depth_counts, dict) and depth_counts:
                    depths_int = sorted([_safe_int(k, default=0) for k in depth_counts.keys()])
                    counts = [float(depth_counts.get(str(d), 0.0) or 0.0) for d in depths_int]
                    cumulative: List[float] = []
                    running = 0.0
                    for c in counts:
                        running += float(c)
                        cumulative.append(running)

                    plt.figure(figsize=(9, 5))
                    plt.plot(depths_int, counts, marker="o", label="Nodes per depth")
                    plt.fill_between(depths_int, cumulative, alpha=0.2, label="Cumulative nodes")
                    plt.title("Tree Growth by Depth")
                    plt.xlabel("Depth")
                    plt.ylabel("Nodes")
                    plt.legend()
                    plt.tight_layout()
                    for ext in ("png", "svg"):
                        plt.savefig(os.path.join(plots_dir, f"tree_growth_by_depth.{ext}"))
                    plt.close()

            # Capability table (Phase 1, single CWE) like Prism paper Table 2
            _plot_capability_table_single_model(
                plt,
                os.path.join(plots_dir, "capability_table_failure_rate_phase1_single_cwe"),
                "Phase 1 Capability Table (Single CWE) — Failure Rate",
                capability_rows,
                difficulty_groups,
                value_key="failure_rate",
                value_label="Failure rate (1 - success_rate)",
                cmap_name="RdYlGn_r",
            )
            _plot_capability_table_single_model(
                plt,
                os.path.join(plots_dir, "capability_table_avg_risk_phase1_single_cwe"),
                "Phase 1 Capability Table (Single CWE) — Avg Risk",
                capability_rows,
                difficulty_groups,
                value_key="avg_risk",
                value_label="Avg risk",
                cmap_name="RdYlGn_r",
            )

    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="Vulnerability-mode metrics + plots generator")
    parser.add_argument("--experiment", type=str, help="Path to a single experiment directory (PHASE_*)")
    parser.add_argument(
        "--experiments-dir",
        type=str,
        help="Directory containing experiment folders (recursively finds PHASE_* subdirectories and analyzes all)",
    )
    parser.add_argument(
        "--compare-experiments",
        nargs="+",
        help="Compare multiple experiments and generate a Table-2 style capability table (each experiment treated as a model).",
    )
    parser.add_argument("--out", type=str, default=None, help="Output directory (default: <experiment>/analysis)")
    parser.add_argument("--no-plots", action="store_true", help="Skip plot generation")
    parser.add_argument(
        "--rq-out-dir",
        type=str,
        default=None,
        help="Also export RQ-specific artifacts here (default: <project_root>/research_questions)",
    )
    parser.add_argument("--no-rq-export", action="store_true", help="Disable RQ-specific export")
    parser.add_argument(
        "--max-concepts",
        type=int,
        default=30,
        help="Maximum number of concepts (rows) in capability tables (default: 30).",
    )
    args = parser.parse_args()

    if not args.experiment and not args.experiments_dir and not args.compare_experiments:
        raise SystemExit("Provide --experiment, --experiments-dir, or --compare-experiments")

    rq_root = None if args.no_rq_export else (args.rq_out_dir or os.path.join(_project_root(), "research_questions"))

    if args.compare_experiments:
        exp_paths = [os.path.abspath(p) for p in args.compare_experiments]
        out = os.path.abspath(args.out) if args.out else os.path.join(os.getcwd(), "vuln_compare")
        os.makedirs(out, exist_ok=True)

        model_to_rows: Dict[str, List[Dict[str, Any]]] = {}
        dg: Optional[List[Tuple[str, List[str]]]] = None

        for exp in exp_paths:
            # Always compute fresh metrics/records (fast, and keeps schema consistent).
            exp_out = os.path.join(exp, "analysis")
            m = analyze_experiment(exp, exp_out, make_plots=False)
            label = os.path.basename(exp)
            try:
                _export_rq_artifacts_for_experiment(
                    experiment_dir=exp,
                    out_dir=exp_out,
                    metrics=m,
                    rq_root=rq_root,
                    include_plots=True,
                )
            except Exception as e:
                print(f"[rq-export] Skipped per-experiment export for {label}: {type(e).__name__}: {e}")

            cap = m.get("capability_table_phase1_single_cwe") or {}
            rows = cap.get("rows") or []
            if isinstance(rows, list):
                model_to_rows[label] = rows

            if dg is None:
                groups = cap.get("difficulty_groups") or []
                parsed: List[Tuple[str, List[str]]] = []
                for g in groups:
                    if not isinstance(g, dict):
                        continue
                    name = str(g.get("name") or "").strip()
                    diffs = g.get("difficulties") or []
                    if not name or not isinstance(diffs, list):
                        continue
                    parsed.append((name, [str(d).strip().lower() for d in diffs if str(d).strip()]))
                dg = parsed or _default_difficulty_groups()

        _write_json(
            os.path.join(out, "capability_compare.json"),
            {
                "difficulty_groups": [{"name": n, "difficulties": d} for n, d in (dg or _default_difficulty_groups())],
                "models": sorted(model_to_rows.keys()),
                "tables": model_to_rows,
            },
        )

        if args.no_plots:
            print(f"Wrote compare JSON: {os.path.join(out, 'capability_compare.json')}")
            try:
                _export_rq_artifacts_for_compare(compare_out_dir=out, rq_root=rq_root, include_plots=True)
            except Exception as e:
                print(f"[rq-export] Skipped compare export: {type(e).__name__}: {e}")
            return

        plt = _maybe_import_matplotlib()
        plots_dir = os.path.join(out, "plots")
        os.makedirs(plots_dir, exist_ok=True)
        if plt is None:
            _write_json(
                os.path.join(plots_dir, "plots_skipped.json"),
                {
                    "reason": "matplotlib not installed",
                    "install": "python3 -m pip install --break-system-packages matplotlib",
                },
            )
        else:
            _plot_capability_table_multi_model(
                plt,
                os.path.join(plots_dir, "capability_table_failure_rate_phase1_single_cwe_compare"),
                "Phase 1 Capability Table (Single CWE) — Failure Rate (Compare)",
                model_to_rows,
                dg or _default_difficulty_groups(),
                value_key="failure_rate",
                value_label="Failure rate (1 - success_rate)",
                cmap_name="RdYlGn_r",
                max_concepts=int(args.max_concepts),
            )
            _plot_capability_table_multi_model(
                plt,
                os.path.join(plots_dir, "capability_table_avg_risk_phase1_single_cwe_compare"),
                "Phase 1 Capability Table (Single CWE) — Avg Risk (Compare)",
                model_to_rows,
                dg or _default_difficulty_groups(),
                value_key="avg_risk",
                value_label="Avg risk",
                cmap_name="RdYlGn_r",
                max_concepts=int(args.max_concepts),
            )

        print(f"Wrote compare JSON: {os.path.join(out, 'capability_compare.json')}")
        print(f"Wrote compare plots: {plots_dir}")
        try:
            _export_rq_artifacts_for_compare(compare_out_dir=out, rq_root=rq_root, include_plots=True)
        except Exception as e:
            print(f"[rq-export] Skipped compare export: {type(e).__name__}: {e}")
        return

    if args.experiment:
        exp = os.path.abspath(args.experiment)
        out = os.path.abspath(args.out) if args.out else os.path.join(exp, "analysis")
        metrics = analyze_experiment(exp, out, make_plots=not args.no_plots)
        try:
            _export_rq_artifacts_for_experiment(
                experiment_dir=exp,
                out_dir=out,
                metrics=metrics,
                rq_root=rq_root,
                include_plots=True,
            )
        except Exception as e:
            print(f"[rq-export] Skipped export for {os.path.basename(exp)}: {type(e).__name__}: {e}")
        print(f"Wrote metrics: {os.path.join(out, 'metrics.json')}")
        print(f"Wrote records: {os.path.join(out, 'records.csv')}")
        if not args.no_plots:
            print(f"Wrote plots: {os.path.join(out, 'plots')}")
        return

    # Bulk mode: analyze all experiment subdirectories
    base = os.path.abspath(args.experiments_dir)
    exp_dirs: List[str] = []
    for root, dirs, _files in os.walk(base):
        for d in dirs:
            if "PHASE_" not in d:
                continue
            exp_dirs.append(os.path.join(root, d))
    exp_dirs = sorted(set(exp_dirs))

    combined_records: List[Dict[str, Any]] = []
    summaries: Dict[str, Any] = {}

    for exp in exp_dirs:
        exp_label = _experiment_label(exp)
        out = os.path.join(exp, "analysis")
        try:
            m = analyze_experiment(exp, out, make_plots=not args.no_plots)
            summaries[exp_label] = m.get("overall", {})
            try:
                _export_rq_artifacts_for_experiment(
                    experiment_dir=exp,
                    out_dir=out,
                    metrics=m,
                    rq_root=rq_root,
                    include_plots=True,
                )
            except Exception as e:
                print(
                    f"[rq-export] Skipped export for {exp_label}: {type(e).__name__}: {e}"
                )

            # Append CSV records into a combined file (re-parse from written CSV to keep memory bounded)
            rec_path = os.path.join(out, "records.csv")
            if os.path.exists(rec_path):
                with open(rec_path, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        row["experiment"] = exp_label
                        combined_records.append(row)
        except FileNotFoundError as e:
            summaries[exp_label] = {"error": str(e)}
            print(f"Skipping {exp_label}: {e}")
        except Exception as e:
            summaries[exp_label] = {"error": f"{type(e).__name__}: {e}"}
            print(f"Skipping {exp_label}: {type(e).__name__}: {e}")

    bulk_out = os.path.abspath(args.out) if args.out else os.path.join(base, "vuln_summary")
    os.makedirs(bulk_out, exist_ok=True)
    _write_json(os.path.join(bulk_out, "summary.json"), summaries)
    _write_csv(os.path.join(bulk_out, "records_all.csv"), combined_records)
    print(f"Wrote summary: {os.path.join(bulk_out, 'summary.json')}")
    print(f"Wrote combined records: {os.path.join(bulk_out, 'records_all.csv')}")


if __name__ == "__main__":
    main()
