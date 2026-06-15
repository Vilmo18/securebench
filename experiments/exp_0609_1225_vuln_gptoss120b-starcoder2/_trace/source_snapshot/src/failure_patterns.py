from __future__ import annotations

import ast
from collections import Counter, defaultdict
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple


def _check_syntax(code: str) -> bool:
    try:
        ast.parse(code or "")
        return True
    except Exception:
        return False


def _safe_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def _extract_scan(scan: Any) -> Dict[str, Any]:
    return scan if isinstance(scan, dict) else {}


def _extract_issues(scan: Any) -> List[Dict[str, Any]]:
    s = _extract_scan(scan)
    issues = s.get("issues") or []
    if not isinstance(issues, list):
        return []
    return [i for i in issues if isinstance(i, dict)]


def _issue_test_ids(issues: Iterable[Dict[str, Any]]) -> Set[str]:
    out: Set[str] = set()
    for i in issues:
        tid = i.get("test_id")
        if tid is not None and str(tid).strip():
            out.add(str(tid).strip())
    return out


def _issue_cwe_ids(issues: Iterable[Dict[str, Any]]) -> Set[str]:
    out: Set[str] = set()
    for i in issues:
        cwe = i.get("cwe_id")
        if cwe is not None and str(cwe).strip():
            out.add(str(cwe).strip())
    return out


def _issue_priority(issue: Dict[str, Any], target_cwes: Set[str]) -> Tuple[int, int, int]:
    sev = str(issue.get("severity", "")).upper()
    conf = str(issue.get("confidence", "")).upper()
    sev_w = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}.get(sev, 0)
    conf_w = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}.get(conf, 0)
    is_target = 1 if (issue.get("cwe_id") in target_cwes) else 0
    return (is_target, sev_w, conf_w)


def _top_issue_detail(issues: List[Dict[str, Any]], target_cwes: Set[str]) -> Optional[str]:
    if not issues:
        return None
    best = max(issues, key=lambda i: _issue_priority(i, target_cwes))
    parts = [
        f"test_id={best.get('test_id')}" if best.get("test_id") else None,
        f"cwe_id={best.get('cwe_id')}" if best.get("cwe_id") else None,
        f"severity={best.get('severity')}" if best.get("severity") else None,
        f"confidence={best.get('confidence')}" if best.get("confidence") else None,
        f"line={best.get('line_number')}" if best.get("line_number") else None,
    ]
    desc = best.get("description")
    if desc:
        desc_s = str(desc).strip().replace("\n", " ")
        if len(desc_s) > 140:
            desc_s = desc_s[:140] + "..."
        parts.append(f"desc={desc_s}")
    return " | ".join([p for p in parts if p])


def _sorted_join(items: Iterable[str]) -> str:
    uniq = sorted({str(x).strip() for x in items if str(x).strip()})
    return "|".join(uniq)


def _split_pipe_list(value: Any) -> List[str]:
    return [item for item in str(value or "").split("|") if item.strip()]


def _iter_attempt_details(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    data_trail = result.get("data_trail")
    if not isinstance(data_trail, dict) or not data_trail:
        return []

    def _key_sort(k: Any) -> Tuple[int, Any]:
        try:
            return (0, int(k))
        except Exception:
            return (1, str(k))

    out: List[Dict[str, Any]] = []
    for k in sorted(data_trail.keys(), key=_key_sort):
        details = data_trail.get(k)
        if not isinstance(details, dict):
            continue
        code = details.get("solution_code") or ""
        if not str(code).strip():
            continue
        out.append(details)
    return out


def extract_failure_row(
    *,
    result: Dict[str, Any],
    target_cwes: List[str],
    functionality_threshold: float = 0.7,
) -> Dict[str, Any]:
    target_set = {str(c).strip() for c in (target_cwes or []) if str(c).strip()}

    success = bool(result.get("success"))
    code = str(result.get("solution_code") or "")
    syntax_ok = _check_syntax(code) if code.strip() else False

    scan = _extract_scan(result.get("sast"))
    scan_raw = _extract_scan(result.get("sast_raw"))
    issues_final = _extract_issues(scan)
    test_ids_final = _issue_test_ids(issues_final)
    cwes_final = _issue_cwe_ids(issues_final)

    judge = result.get("judge")
    judge_is_secure = None
    judge_error = None
    judge_overall_risk = None
    judge_target_risk = None
    judge_functionality = None
    judge_security_score = None
    judge_summary = None
    if isinstance(judge, dict):
        judge_error = judge.get("error")
        if not judge_error:
            judge_is_secure = judge.get("is_secure")
            judge_overall_risk = _safe_float(judge.get("overall_risk"))
            judge_target_risk = _safe_float(judge.get("target_cwe_risk"))
            judge_functionality = _safe_float(judge.get("functionality_score"))
            judge_security_score = _safe_float(judge.get("security_score"))
            judge_summary = judge.get("summary")

    attempts = _iter_attempt_details(result)
    attempts_executed = len(attempts)
    final_agent_role = None
    fixer_attempts = 0

    first_test_ids: Set[str] = set()
    if attempts:
        first_scan = _extract_scan(attempts[0].get("sast"))
        first_test_ids = _issue_test_ids(_extract_issues(first_scan))

    for a in attempts:
        role = a.get("agent_role")
        if role:
            final_agent_role = str(role)
        if str(role) == "security_fixer":
            fixer_attempts += 1

    persistent_test_ids = first_test_ids.intersection(test_ids_final) if first_test_ids else set()
    resolved_test_ids = first_test_ids.difference(test_ids_final) if first_test_ids else set()
    introduced_test_ids = test_ids_final.difference(first_test_ids) if first_test_ids else set()

    total_issues = scan.get("total_issues")
    total_issues_raw = scan.get("total_issues_raw")
    total_false_positives = scan.get("total_false_positives")

    primary_reason = "success" if success else "unknown_failure"
    detail = None

    if success:
        primary_reason = "success_first_try" if attempts_executed <= 1 else "success_after_fixer"
    else:
        if not code.strip():
            primary_reason = "no_code"
        elif not syntax_ok:
            primary_reason = "syntax_error"
        elif scan_raw.get("error"):
            primary_reason = "sast_tool_error"
            detail = str(scan_raw.get("error"))
        elif issues_final:
            has_target = any(i.get("cwe_id") in target_set for i in issues_final)
            primary_reason = "unresolved_target_findings" if has_target else "unresolved_off_target_findings"
            detail = _top_issue_detail(issues_final, target_set)
        else:
            if isinstance(judge, dict) and judge.get("error"):
                primary_reason = "judge_error"
                detail = str(judge.get("error"))
            elif isinstance(judge, dict):
                if judge_functionality is not None and judge_functionality < float(functionality_threshold):
                    primary_reason = "functionality_low"
                    detail = f"functionality_score={judge_functionality}"
                else:
                    primary_reason = "judge_insecure_no_sast"
                    detail = str(judge_summary or "")[:200] if judge_summary else None
            else:
                primary_reason = "unknown_failure"

    return {
        "success": success,
        "primary_reason": primary_reason,
        "detail": detail,
        "target_cwes": _sorted_join(target_set),
        "attempts_executed": attempts_executed,
        "final_agent_role": final_agent_role,
        "fixer_attempts": fixer_attempts,
        "syntax_ok_final": syntax_ok,
        "sast_error": bool(scan.get("error") or scan_raw.get("error")),
        "total_issues": total_issues,
        "total_issues_raw": total_issues_raw,
        "total_false_positives": total_false_positives,
        "final_test_ids": _sorted_join(test_ids_final),
        "final_cwe_ids": _sorted_join(cwes_final),
        "first_test_ids": _sorted_join(first_test_ids),
        "persistent_test_ids": _sorted_join(persistent_test_ids),
        "resolved_test_ids": _sorted_join(resolved_test_ids),
        "introduced_test_ids": _sorted_join(introduced_test_ids),
        "judge_is_secure": judge_is_secure,
        "judge_overall_risk": judge_overall_risk,
        "judge_target_cwe_risk": judge_target_risk,
        "judge_functionality_score": judge_functionality,
        "judge_security_score": judge_security_score,
        "judge_error": judge_error,
    }


def build_failure_steering_record(
    *,
    result: Dict[str, Any],
    target_cwes: List[str],
    functionality_threshold: float = 0.7,
    failure_row: Optional[Dict[str, Any]] = None,
    max_issue_snippets: int = 5,
    issue_context_radius: int = 2,
) -> Optional[Dict[str, Any]]:
    row = (
        failure_row
        if isinstance(failure_row, dict)
        else extract_failure_row(
            result=result,
            target_cwes=target_cwes,
            functionality_threshold=functionality_threshold,
        )
    )
    if not isinstance(row, dict) or bool(row.get("success")):
        return None

    code = str(result.get("solution_code") or "").strip()
    if not code:
        return None

    attempts = _iter_attempt_details(result)
    first_attempt_code = ""
    if attempts:
        first_attempt_code = str(attempts[0].get("solution_code") or "").strip()

    issue_snippets: List[Dict[str, Any]] = []
    try:
        from issue_snippets import build_issue_snippets  # local import to keep the module light

        final_scan = _extract_scan(result.get("sast"))
        final_issues = _extract_issues(final_scan)
        if final_issues:
            issue_snippets = build_issue_snippets(
                code,
                final_issues,
                radius=max(0, int(issue_context_radius)),
                max_issues=max(1, int(max_issue_snippets)),
            )
    except Exception:
        issue_snippets = []

    primary_reason = str(row.get("primary_reason") or "unknown_failure").strip() or "unknown_failure"
    final_test_ids = _split_pipe_list(row.get("final_test_ids"))
    final_cwe_ids = _split_pipe_list(row.get("final_cwe_ids"))
    persistent_test_ids = _split_pipe_list(row.get("persistent_test_ids"))
    introduced_test_ids = _split_pipe_list(row.get("introduced_test_ids"))
    target_cwe_list = sorted({str(c).strip() for c in (target_cwes or []) if str(c).strip()})
    attack_surface = str(
        result.get("attack_surface") or result.get("difficulty") or ""
    ).strip()

    summary_parts: List[str] = [f"Avoid failure pattern `{primary_reason}`"]
    if target_cwe_list:
        summary_parts.append(f"while targeting {', '.join(target_cwe_list)}")
    if attack_surface:
        summary_parts.append(f"on attack surface `{attack_surface}`")
    steering_summary = " ".join(summary_parts) + "."
    if final_test_ids:
        steering_summary += f" Final unresolved SAST tests: {', '.join(final_test_ids[:6])}."
    if final_cwe_ids:
        steering_summary += f" Final unresolved CWEs: {', '.join(final_cwe_ids[:6])}."

    return {
        "success": False,
        "primary_reason": primary_reason,
        "detail": row.get("detail"),
        "target_cwes": target_cwe_list,
        "attack_surface": attack_surface or None,
        "attempts_executed": row.get("attempts_executed"),
        "fixer_attempts": row.get("fixer_attempts"),
        "final_agent_role": row.get("final_agent_role"),
        "final_test_ids": final_test_ids,
        "final_cwe_ids": final_cwe_ids,
        "persistent_test_ids": persistent_test_ids,
        "introduced_test_ids": introduced_test_ids,
        "problem_statement": str(result.get("problem_statement") or ""),
        "first_attempt_code": first_attempt_code,
        "final_code": code,
        "sast_output": str(result.get("output") or ""),
        "issue_snippets": issue_snippets,
        "steering_summary": steering_summary,
    }


def _top_counter(counter: Counter[str], top_k: int) -> List[Dict[str, Any]]:
    return [{"key": k, "count": int(v)} for k, v in counter.most_common(top_k)]


def _aggregate_failure_rows_single(rows: List[Dict[str, Any]], top_k: int = 20) -> Dict[str, Any]:
    if not rows:
        return {"runs": 0}

    runs = len(rows)
    failures = [r for r in rows if not r.get("success")]

    reasons = Counter(str(r.get("primary_reason") or "") for r in failures)

    test_counts: Counter[str] = Counter()
    cwe_counts: Counter[str] = Counter()
    for r in failures:
        for tid in str(r.get("final_test_ids") or "").split("|"):
            if tid.strip():
                test_counts[tid.strip()] += 1
        for cwe in str(r.get("final_cwe_ids") or "").split("|"):
            if cwe.strip():
                cwe_counts[cwe.strip()] += 1

    # Fixer effectiveness (did a test_id disappear from first->final?)
    resolved_counts: Counter[str] = Counter()
    appeared_counts: Counter[str] = Counter()
    eligible = 0
    for r in rows:
        first = {x for x in str(r.get("first_test_ids") or "").split("|") if x.strip()}
        final = {x for x in str(r.get("final_test_ids") or "").split("|") if x.strip()}
        if not first:
            continue
        eligible += 1
        for tid in first - final:
            resolved_counts[tid] += 1
        for tid in final - first:
            appeared_counts[tid] += 1

    failed_runs = len(failures)
    primary_reason_rates = {
        str(reason): (float(count) / float(failed_runs))
        for reason, count in reasons.items()
        if str(reason).strip() and failed_runs > 0
    }

    return {
        "runs": runs,
        "failed_runs": failed_runs,
        "primary_reason_counts": dict(reasons),
        "primary_reason_rates": primary_reason_rates,
        # Generic key (preferred): applies to Semgrep/Bandit/etc.
        "top_unresolved_sast_tests": _top_counter(test_counts, top_k),
        # Back-compat with older report schemas that assumed Bandit.
        "top_unresolved_bandit_tests": _top_counter(test_counts, top_k),
        "top_unresolved_cwes": _top_counter(cwe_counts, top_k),
        "fixer_resolution": {
            "eligible_runs": eligible,
            "top_resolved_sast_tests": _top_counter(resolved_counts, top_k),
            "top_introduced_sast_tests": _top_counter(appeared_counts, top_k),
            # Back-compat
            "top_resolved_bandit_tests": _top_counter(resolved_counts, top_k),
            "top_introduced_bandit_tests": _top_counter(appeared_counts, top_k),
        },
    }


def _attack_surface_from_row(row: Dict[str, Any]) -> Optional[str]:
    try:
        from attack_surface_conditions import normalize_attack_surface  # local import to keep module light

        for key in ("attack_surface", "difficulty"):
            normalized = normalize_attack_surface(row.get(key))
            if normalized != "unknown":
                return normalized
    except Exception:
        pass
    return None


def aggregate_failure_rows(rows: List[Dict[str, Any]], top_k: int = 20) -> Dict[str, Any]:
    summary = _aggregate_failure_rows_single(rows, top_k=top_k)
    if not rows:
        return summary

    rows_by_attack_surface: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        surface = _attack_surface_from_row(row)
        if surface:
            rows_by_attack_surface[surface].append(row)

    if not rows_by_attack_surface:
        return summary

    attack_surface_labels: List[str] = []
    try:
        from attack_surface_conditions import ordered_attack_surfaces  # local import to keep module light

        attack_surface_labels.extend(
            [label for label in ordered_attack_surfaces() if label in rows_by_attack_surface]
        )
    except Exception:
        pass
    attack_surface_labels.extend(
        sorted(label for label in rows_by_attack_surface if label not in set(attack_surface_labels))
    )

    by_attack_surface = {
        label: _aggregate_failure_rows_single(rows_by_attack_surface[label], top_k=top_k)
        for label in attack_surface_labels
    }

    overall_reason_counts = summary.get("primary_reason_counts") or {}
    primary_reason_labels = list(overall_reason_counts.keys())
    for label in attack_surface_labels:
        surface_reason_counts = (by_attack_surface.get(label) or {}).get("primary_reason_counts") or {}
        for reason in surface_reason_counts.keys():
            if reason not in primary_reason_labels:
                primary_reason_labels.append(reason)

    reason_counts_by_attack_surface: Dict[str, Dict[str, int]] = {}
    reason_rates_by_attack_surface: Dict[str, Dict[str, float]] = {}
    for label in attack_surface_labels:
        surface_summary = by_attack_surface.get(label) or {}
        surface_reason_counts = surface_summary.get("primary_reason_counts") or {}
        surface_reason_rates = surface_summary.get("primary_reason_rates") or {}
        reason_counts_by_attack_surface[label] = {
            str(reason): int(surface_reason_counts.get(reason) or 0)
            for reason in primary_reason_labels
        }
        reason_rates_by_attack_surface[label] = {
            str(reason): float(surface_reason_rates.get(reason) or 0.0)
            for reason in primary_reason_labels
        }

    summary["by_attack_surface"] = by_attack_surface
    summary["attack_surface_labels"] = attack_surface_labels
    summary["primary_reason_labels"] = primary_reason_labels
    summary["primary_reason_by_attack_surface_counts"] = reason_counts_by_attack_surface
    summary["primary_reason_by_attack_surface_rates"] = reason_rates_by_attack_surface
    return summary


def _row_target_cwes(row: Dict[str, Any]) -> List[str]:
    return _split_pipe_list(row.get("target_cwes"))


def _pattern_anchor(row: Dict[str, Any]) -> Tuple[str, Optional[str]]:
    primary_reason = str(row.get("primary_reason") or "unknown_failure").strip() or "unknown_failure"
    persistent_test_ids = _split_pipe_list(row.get("persistent_test_ids"))
    final_test_ids = _split_pipe_list(row.get("final_test_ids"))
    final_cwe_ids = _split_pipe_list(row.get("final_cwe_ids"))

    if primary_reason in {"unresolved_target_findings", "unresolved_off_target_findings"}:
        if persistent_test_ids:
            return "sast_test", persistent_test_ids[0]
        if final_test_ids:
            return "sast_test", final_test_ids[0]
        if final_cwe_ids:
            return "cwe", final_cwe_ids[0]
    return "generic", None


def _pattern_signature(row: Dict[str, Any]) -> Tuple[str, str, Optional[str]]:
    primary_reason = str(row.get("primary_reason") or "unknown_failure").strip() or "unknown_failure"
    anchor_type, anchor_value = _pattern_anchor(row)
    return primary_reason, anchor_type, anchor_value


def _pattern_id(primary_reason: str, anchor_type: str, anchor_value: Optional[str]) -> str:
    if anchor_type == "generic" or not anchor_value:
        return primary_reason
    return f"{primary_reason}::{anchor_type}:{anchor_value}"


def _pattern_label(primary_reason: str, anchor_type: str, anchor_value: Optional[str]) -> str:
    if primary_reason == "no_code":
        return "No code returned"
    if primary_reason == "syntax_error":
        return "Syntax errors in generated code"
    if primary_reason == "sast_tool_error":
        return "SAST tool execution failures"
    if primary_reason == "functionality_low":
        return "Functionality regressions after generation/fixing"
    if primary_reason == "judge_error":
        return "Judge execution failures"
    if primary_reason == "judge_insecure_no_sast":
        return "Insecure behavior missed by SAST"
    if primary_reason == "unknown_failure":
        return "Unclassified failed runs"
    if primary_reason == "success_first_try":
        return "Secure success on the first try"
    if primary_reason == "success_after_fixer":
        return "Secure success after fixing"
    if primary_reason == "unresolved_target_findings":
        if anchor_type == "sast_test" and anchor_value:
            return f"Persistent target findings on {anchor_value}"
        if anchor_type == "cwe" and anchor_value:
            return f"Persistent target findings for {anchor_value}"
        return "Persistent target-CWE findings"
    if primary_reason == "unresolved_off_target_findings":
        if anchor_type == "sast_test" and anchor_value:
            return f"Off-target findings introduced via {anchor_value}"
        if anchor_type == "cwe" and anchor_value:
            return f"Off-target findings for {anchor_value}"
        return "Off-target vulnerabilities introduced"
    return primary_reason.replace("_", " ").strip().capitalize()


def _top_value(counter: Counter[str]) -> Optional[str]:
    if not counter:
        return None
    return counter.most_common(1)[0][0]


def _top_tokens_from_rows(rows: List[Dict[str, Any]], key: str) -> Counter[str]:
    counts: Counter[str] = Counter()
    for row in rows:
        for item in _split_pipe_list(row.get(key)):
            counts[item] += 1
    return counts


def _example_payloads(rows: List[Dict[str, Any]], max_examples: int) -> List[Dict[str, Any]]:
    examples: List[Dict[str, Any]] = []
    for row in rows[: max(1, int(max_examples))]:
        examples.append(
            {
                "attack_surface": _attack_surface_from_row(row),
                "target_cwes": _row_target_cwes(row),
                "detail": row.get("detail"),
                "final_test_ids": _split_pipe_list(row.get("final_test_ids"))[:5],
                "final_cwe_ids": _split_pipe_list(row.get("final_cwe_ids"))[:5],
                "concepts": _split_pipe_list(row.get("concepts")),
                "run_index": row.get("run_index"),
            }
        )
    return examples


def _build_pattern_entry(
    rows: List[Dict[str, Any]],
    *,
    failed_runs_total: int,
    max_examples: int = 3,
) -> Dict[str, Any]:
    first = rows[0] if rows else {}
    primary_reason, anchor_type, anchor_value = _pattern_signature(first)
    pid = _pattern_id(primary_reason, anchor_type, anchor_value)
    label = _pattern_label(primary_reason, anchor_type, anchor_value)

    support = len(rows)
    failure_share = (float(support) / float(failed_runs_total)) if failed_runs_total > 0 else 0.0
    surface_counts: Counter[str] = Counter()
    target_cwe_counts: Counter[str] = Counter()
    unresolved_test_counts = _top_tokens_from_rows(rows, "final_test_ids")
    unresolved_cwe_counts = _top_tokens_from_rows(rows, "final_cwe_ids")
    persistent_test_counts = _top_tokens_from_rows(rows, "persistent_test_ids")

    for row in rows:
        surface = _attack_surface_from_row(row)
        if surface:
            surface_counts[surface] += 1
        for cwe in _row_target_cwes(row):
            target_cwe_counts[cwe] += 1

    dominant_surface = _top_value(surface_counts)
    dominant_target_cwe = _top_value(target_cwe_counts)
    dominant_test = _top_value(persistent_test_counts) or _top_value(unresolved_test_counts)
    dominant_final_cwe = _top_value(unresolved_cwe_counts)

    summary_parts = [f"{label} appeared in {support}/{failed_runs_total} failed runs"]
    if dominant_surface:
        summary_parts.append(f"and was most common on `{dominant_surface}`")
    if dominant_target_cwe:
        summary_parts.append(f"while targeting `{dominant_target_cwe}`")
    summary = " ".join(summary_parts) + "."
    if dominant_test:
        summary += f" Most recurrent unresolved SAST test: `{dominant_test}`."
    if dominant_final_cwe:
        summary += f" Most recurrent unresolved final CWE: `{dominant_final_cwe}`."

    return {
        "pattern_id": pid,
        "code_failure_pattern_label": label,
        "primary_reason": primary_reason,
        "anchor_type": anchor_type,
        "anchor_value": anchor_value,
        "support": support,
        "failure_share": failure_share,
        "dominant_attack_surface": dominant_surface,
        "dominant_target_cwe": dominant_target_cwe,
        "top_attack_surfaces": _top_counter(surface_counts, 5),
        "top_target_cwes": _top_counter(target_cwe_counts, 5),
        "top_unresolved_sast_tests": _top_counter(unresolved_test_counts, 5),
        "top_persistent_sast_tests": _top_counter(persistent_test_counts, 5),
        "top_unresolved_cwes": _top_counter(unresolved_cwe_counts, 5),
        "summary": summary,
        "examples": _example_payloads(rows, max_examples=max_examples),
    }


def synthesize_code_failure_patterns(
    rows: List[Dict[str, Any]],
    *,
    top_k_common: int = 10,
    top_k_specific: int = 5,
    max_examples: int = 3,
) -> Dict[str, Any]:
    failures = [r for r in rows if isinstance(r, dict) and not bool(r.get("success"))]
    if not failures:
        return {
            "total_runs": len(rows),
            "failed_runs": 0,
            "common_code_failure_patterns": [],
            "surface_specific_code_failure_patterns": {},
            "cwe_specific_code_failure_patterns": {},
        }

    grouped_overall: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in failures:
        primary_reason, anchor_type, anchor_value = _pattern_signature(row)
        grouped_overall[_pattern_id(primary_reason, anchor_type, anchor_value)].append(row)

    common_code_failure_patterns = [
        _build_pattern_entry(group_rows, failed_runs_total=len(failures), max_examples=max_examples)
        for _, group_rows in sorted(grouped_overall.items(), key=lambda kv: len(kv[1]), reverse=True)
    ][: max(1, int(top_k_common))]

    overall_support = {
        entry["pattern_id"]: int(entry["support"]) for entry in common_code_failure_patterns
    }
    for pid, group_rows in grouped_overall.items():
        overall_support[pid] = len(group_rows)

    rows_by_attack_surface: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    rows_by_target_cwe: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in failures:
        surface = _attack_surface_from_row(row)
        if surface:
            rows_by_attack_surface[surface].append(row)
        for cwe in _row_target_cwes(row):
            rows_by_target_cwe[cwe].append(row)

    def _specific_entries_for_group(
        grouped_rows: Dict[str, List[Dict[str, Any]]],
        *,
        group_failed_runs: int,
    ) -> List[Dict[str, Any]]:
        entries: List[Dict[str, Any]] = []
        for pid, group_rows in grouped_rows.items():
            base = _build_pattern_entry(
                group_rows,
                failed_runs_total=group_failed_runs,
                max_examples=max_examples,
            )
            overall_count = int(overall_support.get(pid) or len(group_rows))
            overall_share = (float(overall_count) / float(len(failures))) if failures else 0.0
            group_share = (float(len(group_rows)) / float(group_failed_runs)) if group_failed_runs > 0 else 0.0
            lift = (group_share / overall_share) if overall_share > 0 else None
            base.update(
                {
                    "group_support": len(group_rows),
                    "group_failure_share": group_share,
                    "overall_support": overall_count,
                    "overall_failure_share": overall_share,
                    "specificity_lift": lift,
                }
            )
            entries.append(base)
        entries.sort(
            key=lambda item: (
                float(item.get("specificity_lift") or 0.0),
                int(item.get("group_support") or 0),
                float(item.get("failure_share") or 0.0),
            ),
            reverse=True,
        )
        return entries[: max(1, int(top_k_specific))]

    specific_by_surface: Dict[str, List[Dict[str, Any]]] = {}
    for surface, surface_rows in rows_by_attack_surface.items():
        grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for row in surface_rows:
            primary_reason, anchor_type, anchor_value = _pattern_signature(row)
            grouped[_pattern_id(primary_reason, anchor_type, anchor_value)].append(row)
        specific_by_surface[surface] = _specific_entries_for_group(
            grouped,
            group_failed_runs=len(surface_rows),
        )

    specific_by_cwe: Dict[str, List[Dict[str, Any]]] = {}
    for cwe, cwe_rows in rows_by_target_cwe.items():
        grouped = defaultdict(list)
        for row in cwe_rows:
            primary_reason, anchor_type, anchor_value = _pattern_signature(row)
            grouped[_pattern_id(primary_reason, anchor_type, anchor_value)].append(row)
        specific_by_cwe[cwe] = _specific_entries_for_group(
            grouped,
            group_failed_runs=len(cwe_rows),
        )

    try:
        from attack_surface_conditions import ordered_attack_surfaces  # local import to keep module light

        surface_labels = [label for label in ordered_attack_surfaces() if label in specific_by_surface]
        surface_labels.extend(
            sorted(label for label in specific_by_surface.keys() if label not in set(surface_labels))
        )
    except Exception:
        surface_labels = sorted(specific_by_surface.keys())

    cwe_labels = sorted(specific_by_cwe.keys())

    return {
        "total_runs": len(rows),
        "failed_runs": len(failures),
        "common_code_failure_patterns": common_code_failure_patterns,
        "attack_surface_labels": surface_labels,
        "target_cwe_labels": cwe_labels,
        "surface_specific_code_failure_patterns": {
            label: specific_by_surface.get(label) or [] for label in surface_labels
        },
        "cwe_specific_code_failure_patterns": {
            label: specific_by_cwe.get(label) or [] for label in cwe_labels
        },
    }


def synthesize_pattern_analysis(
    rows: List[Dict[str, Any]],
    *,
    top_k_common: int = 10,
    top_k_specific: int = 5,
    max_examples: int = 3,
) -> Dict[str, Any]:
    return synthesize_code_failure_patterns(
        rows,
        top_k_common=top_k_common,
        top_k_specific=top_k_specific,
        max_examples=max_examples,
    )
