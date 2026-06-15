from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


def _safe_int(value: object) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except Exception:
        return None


def _issue_sort_key(issue: Dict[str, Any]) -> Tuple[int, int, int]:
    severity_rank = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    confidence_rank = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    sev = severity_rank.get(str(issue.get("severity") or "").upper(), 3)
    conf = confidence_rank.get(str(issue.get("confidence") or "").upper(), 3)
    line = _safe_int(issue.get("line_number"))
    line_i = int(line) if line is not None else 10**9
    return (sev, conf, line_i)


def extract_code_context(
    code: str,
    line_number: Optional[int],
    *,
    radius: int = 2,
) -> Optional[str]:
    if not code or line_number is None:
        return None
    try:
        target = int(line_number)
    except Exception:
        return None
    if target <= 0:
        return None

    lines = (code or "").splitlines()
    if not lines:
        return None

    total = len(lines)
    start = max(1, target - max(0, int(radius)))
    end = min(total, target + max(0, int(radius)))

    out: List[str] = []
    for ln in range(start, end + 1):
        prefix = ">>" if ln == target else "  "
        # Keep exact source line (no stripping) for easy copy/paste.
        out.append(f"{prefix}{ln:4d}: {lines[ln - 1]}")
    return "\n".join(out)


def build_issue_snippets(
    code: str,
    issues: List[Dict[str, Any]],
    *,
    radius: int = 2,
    max_issues: int = 25,
) -> List[Dict[str, Any]]:
    if not code or not issues:
        return []

    items = [i for i in issues if isinstance(i, dict)]
    if not items:
        return []

    try:
        items = sorted(items, key=_issue_sort_key)
    except Exception:
        pass

    max_issues = max(1, int(max_issues))
    out: List[Dict[str, Any]] = []
    for issue in items[:max_issues]:
        line = _safe_int(issue.get("line_number"))
        test_id = issue.get("test_id")
        signature = None
        if test_id is not None and line is not None:
            signature = f"{str(test_id)}:{line}"
        elif test_id is not None:
            signature = str(test_id)

        out.append(
            {
                "signature": signature,
                "tool": issue.get("tool"),
                "test_id": test_id,
                "cwe_id": issue.get("cwe_id"),
                "severity": issue.get("severity"),
                "confidence": issue.get("confidence"),
                "line_number": line,
                "description": issue.get("description"),
                "tool_snippet": issue.get("code"),
                "context": extract_code_context(code, line, radius=radius),
            }
        )
    return out

