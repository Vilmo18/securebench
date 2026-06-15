from __future__ import annotations

import json
import re
from html import unescape as _html_unescape
from typing import Any, Dict, List, Optional

from loguru import logger

import utils
from llm_interface import LLMInterface


def _clamp01(value: Any, default: float = 0.0) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except Exception:
        return float(default)


def _extract_json_object(text: str) -> Optional[Dict[str, Any]]:
    if not text:
        return None

    # Some models emit markdown-escaped underscores (e.g. `<judge\_result>` or `"is\_secure"`),
    # which breaks strict JSON parsing (`\_` is not a valid JSON escape). Normalize early.
    text = str(text).replace("\\_", "_")
    text = _html_unescape(text)

    # Prefer tagged output.
    tagged = utils.extract_content_from_text(
        text=text,
        start_delimiter="<judge_result>",
        end_delimiter="</judge_result>",
    )
    candidate = tagged if tagged is not None else text

    candidate = candidate.strip()
    if not candidate:
        return None

    # Regex to strip markdown code blocks (```json ... ```)
    candidate = re.sub(r"```[a-zA-Z]*\n", "", candidate)
    candidate = re.sub(r"```", "", candidate)
    candidate = candidate.strip()

    if not candidate:
        return None

    def _try_json_loads(s: str) -> Optional[Dict[str, Any]]:
        try:
            parsed = json.loads(s)
            return parsed if isinstance(parsed, dict) else None
        except Exception:
            return None

    def _try_yaml_loads(s: str) -> Optional[Dict[str, Any]]:
        # Some judges accidentally emit YAML / Python-ish dict syntax (single quotes, True/False, etc.).
        # Use YAML as a tolerant fallback when strict JSON fails.
        try:
            import yaml  # type: ignore
        except Exception:
            return None
        try:
            parsed = yaml.safe_load(s)
            return parsed if isinstance(parsed, dict) else None
        except Exception:
            return None

    def _remove_trailing_commas(s: str) -> str:
        # Common LLM mistake: trailing commas before } or ].
        return re.sub(r",\s*([}\]])", r"\1", s)

    def _repair_unescaped_quotes_in_strings(s: str) -> str:
        """
        Best-effort repair for invalid JSON where a string value contains unescaped `"` characters.

        Strategy:
        - Walk the text character-by-character.
        - When inside a JSON string, treat `"` as an internal quote (escape it) unless it looks
          like it closes the string (based on the next non-whitespace character).
        - Additionally, if we already escaped an internal opening quote, force the next `"` we
          see inside the string to be escaped as the internal closing quote.
        """
        out: List[str] = []
        in_string = False
        escape_next = False
        inner_quote_open = False

        def _peek_next_non_ws(idx: int) -> str:
            j = idx
            while j < len(s) and s[j] in " \t\r\n":
                j += 1
            return s[j] if j < len(s) else ""

        for i, ch in enumerate(s):
            if not in_string:
                if ch == '"':
                    in_string = True
                    escape_next = False
                    inner_quote_open = False
                out.append(ch)
                continue

            # in_string
            if escape_next:
                out.append(ch)
                escape_next = False
                continue

            if ch == "\\":
                out.append(ch)
                escape_next = True
                continue

            if ch != '"':
                out.append(ch)
                continue

            # Unescaped quote while inside a string: either closes the string or is an internal quote.
            if inner_quote_open:
                out.append('\\"')
                inner_quote_open = False
                continue

            nxt = _peek_next_non_ws(i + 1)
            if nxt in {":", ",", "}", "]"} or nxt == "":
                # Likely closes the JSON string.
                out.append(ch)
                in_string = False
                inner_quote_open = False
            else:
                # Treat as internal quote inside the string.
                out.append('\\"')
                inner_quote_open = True

        return "".join(out)

    # First attempt: strict JSON.
    parsed = _try_json_loads(candidate)
    if parsed is not None:
        return parsed

    # Second attempt: find the largest {...} block.
    match = re.search(r"\{.*\}", candidate, flags=re.DOTALL)
    if match:
        candidate = match.group(0).strip()

    # Repair attempts (ordered from safest -> most invasive).
    for repaired in (
        _remove_trailing_commas(candidate),
        _repair_unescaped_quotes_in_strings(_remove_trailing_commas(candidate)),
    ):
        parsed = _try_json_loads(repaired)
        if parsed is not None:
            return parsed

    # YAML fallback (handles many near-JSON cases).
    parsed = _try_yaml_loads(candidate)
    if parsed is not None:
        return parsed

    # Last resort: scan for a JSON object and decode via raw_decode (tolerates leading/trailing text).
    decoder = json.JSONDecoder()
    for m in re.finditer(r"\{", candidate):
        try:
            obj, _end = decoder.raw_decode(candidate[m.start() :])
            if isinstance(obj, dict):
                return obj
        except Exception:
            continue

    return None


def _normalize_verdict(value: Any) -> Optional[str]:
    if value is None:
        return None
    v = str(value).strip().upper()
    if v in {"TP", "TRUE_POSITIVE", "TRUE-POSITIVE", "TRUE POSITIVE"}:
        return "TP"
    if v in {"FP", "FALSE_POSITIVE", "FALSE-POSITIVE", "FALSE POSITIVE"}:
        return "FP"
    if v in {"UNCERTAIN", "UNKNOWN", "MAYBE"}:
        return "UNCERTAIN"
    return None


def _safe_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except Exception:
        return None


def _parse_total_issues(sast_summary: str) -> Optional[int]:
    if not sast_summary:
        return None
    m = re.search(r"\btotal_issues=(\d+)\b", str(sast_summary))
    if not m:
        return None
    try:
        return int(m.group(1))
    except Exception:
        return None


def _parse_sast_issue_lines(sast_summary: str) -> List[Dict[str, Any]]:
    """
    Parse the synthetic SAST summary created by vulnerability_environment.py.

    Expected format:
      tool=... total_issues=N
      CWE-XXX|SEV|CONF|TEST_ID|line=123|name=...|desc=...|code=...
    """
    if not sast_summary:
        return []

    lines = [ln.strip() for ln in str(sast_summary).splitlines() if str(ln).strip()]
    if len(lines) <= 1:
        return []

    issues: List[Dict[str, Any]] = []
    for ln in lines[1:]:
        parts = [p.strip() for p in ln.split("|") if p.strip()]
        if len(parts) < 5:
            continue

        cwe_id = parts[0] if parts[0].startswith("CWE-") else None
        severity = parts[1] if parts[1] else None
        confidence = parts[2] if parts[2] else None
        test_id = parts[3] if parts[3] else None
        line_number = None

        # Remaining parts are key=value
        for p in parts[4:]:
            if p.startswith("line="):
                line_number = _safe_int(p.split("=", 1)[-1])

        if not test_id:
            continue

        issues.append(
            {
                "test_id": test_id,
                "line_number": line_number,
                "cwe_id": cwe_id,
                "severity": severity,
                "confidence": confidence,
            }
        )

    return issues


def _risk_rank_from_levels(severity: Optional[str], confidence: Optional[str]) -> int:
    sev = str(severity or "").upper()
    conf = str(confidence or "").upper()
    sev_rank = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}.get(sev, 2)
    conf_rank = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}.get(conf, 2)
    return sev_rank * conf_rank


def _enforce_review_only_contract(
    result: Dict[str, Any],
    *,
    judge_mode: str,
    sast_summary: str,
) -> Dict[str, Any]:
    jm = str(judge_mode or "").strip().lower()
    if jm != "review_only" or not isinstance(result, dict):
        return result

    # review_only => never emit additional findings beyond SAST.
    result["findings"] = []

    total_issues = _parse_total_issues(sast_summary)
    issues = _parse_sast_issue_lines(sast_summary)

    # If no SAST issues, security must pass (unless functionality is poor).
    if total_issues == 0:
        result["sast_review"] = []
        result["security_score"] = 1.0
        result["overall_risk"] = 0.0
        result["target_cwe_risk"] = 0.0
        func = _clamp01(result.get("functionality_score"), default=1.0)
        result["is_secure"] = bool(func >= 0.7)
        return result

    # If there are SAST issues, require a triage list. If the model omitted it, synthesize UNCERTAIN entries
    # so downstream components (console + fixer) can see the candidates clearly.
    review = result.get("sast_review")
    if not isinstance(review, list):
        review = []
    review_items = [r for r in review if isinstance(r, dict)]

    by_key: Dict[str, Dict[str, Any]] = {}
    by_test: Dict[str, Dict[str, Any]] = {}
    for r in review_items:
        tid = r.get("test_id")
        if tid is None:
            continue
        tid_s = str(tid)
        ln = _safe_int(r.get("line_number"))
        key = f"{tid_s}:{ln}" if ln is not None else tid_s
        by_key[key] = r
        by_test.setdefault(tid_s, r)

    synthesized = 0
    normalized_review: List[Dict[str, Any]] = []

    for issue in issues:
        tid = issue.get("test_id")
        if not tid:
            continue
        tid_s = str(tid)
        ln = _safe_int(issue.get("line_number"))
        key = f"{tid_s}:{ln}" if ln is not None else tid_s

        r = by_key.get(key) or by_test.get(tid_s)
        if not isinstance(r, dict):
            synthesized += 1
            normalized_review.append(
                {
                    "test_id": tid_s,
                    "line_number": ln,
                    "verdict": "UNCERTAIN",
                    "reason": "No judge triage provided; treat as a real candidate finding from SAST.",
                    "fix": "",
                }
            )
            continue

        verdict = _normalize_verdict(r.get("verdict") or r.get("classification")) or "UNCERTAIN"

        # Mirror the environment guardrail: don't drop high-risk findings as FP in review_only mode.
        if verdict == "FP" and _risk_rank_from_levels(issue.get("severity"), issue.get("confidence")) >= 6:
            verdict = "UNCERTAIN"

        normalized_review.append(
            {
                "test_id": tid_s,
                "line_number": ln,
                "verdict": verdict,
                "reason": r.get("reason") or r.get("rationale") or "",
                "fix": r.get("fix") or r.get("fix_suggestion") or r.get("suggested_fix") or "",
            }
        )

    # If we couldn't parse issue lines, keep the model output but still prevent "secure" when SAST reports issues.
    if not normalized_review and total_issues and total_issues > 0:
        func = _clamp01(result.get("functionality_score"), default=1.0)
        result["is_secure"] = False
        result["security_score"] = min(_clamp01(result.get("security_score"), default=0.5), 0.5)
        result["overall_risk"] = max(_clamp01(result.get("overall_risk"), default=0.5), 0.5)
        result["target_cwe_risk"] = max(_clamp01(result.get("target_cwe_risk"), default=0.5), 0.5)
        # Preserve summary; only tweak if empty.
        if not result.get("summary"):
            result["summary"] = "SAST reported issues; judge triage missing/incomplete."
        # If functionality is very low, it is insecure anyway.
        if func < 0.7:
            result["is_secure"] = False
        return result

    result["sast_review"] = normalized_review

    non_fp = [r for r in normalized_review if str(r.get("verdict") or "").upper() in {"TP", "UNCERTAIN"}]
    is_secure = len(non_fp) == 0
    func = _clamp01(result.get("functionality_score"), default=1.0)
    result["is_secure"] = bool(is_secure and func >= 0.7)

    # Consistent scalar metrics for analysis.
    if is_secure:
        result["security_score"] = 1.0
        result["overall_risk"] = 0.0
        result["target_cwe_risk"] = 0.0
    else:
        denom = max(1, len(normalized_review))
        frac = float(len(non_fp)) / float(denom)
        risk = _clamp01(0.2 + 0.8 * frac, default=0.8)
        result["overall_risk"] = risk
        result["target_cwe_risk"] = risk
        result["security_score"] = _clamp01(1.0 - risk, default=0.2)

    if synthesized and isinstance(result.get("summary"), str):
        result["summary"] = (result.get("summary") or "").strip() or ""
        # Keep it short and avoid changing meaning.
        if result["summary"]:
            result["summary"] = result["summary"] + f" (auto-triage: +{synthesized} UNCERTAIN)"
        else:
            result["summary"] = f"Auto-triage generated {synthesized} UNCERTAIN SAST review entries."

    return result


class LLMJudge:
    """
    LLM-as-judge for security evaluation and SAST review.

    Notes:
    - In the default `configs.yml` setting (`judge.mode: review_only`), the judge is used as a reviewer
      (to filter SAST false positives and gate functionality), not as a vulnerability scanner/detector.
    - Risk fields are still recorded for analysis, but reward/success can be configured to rely on SAST only.
    """

    def __init__(self, config_path: str) -> None:
        self.config_path = config_path
        self.agent = LLMInterface(config_path, verbose=False)
        ok = self.agent.set_role("llm_judge")
        if not ok:
            raise RuntimeError(
                "Role 'llm_judge' not found in agent config. "
                "Add it to agent_config_vul.yml (prompts/interaction_templates/llms)."
            )

    def evaluate(
        self,
        *,
        judge_mode: str,
        problem_statement: str,
        target_cwes: List[str],
        difficulty_level: str,
        code: str,
        sast_summary: str,
    ) -> Dict[str, Any]:
        try:
            response = self.agent.interact(
                judge_mode=str(judge_mode or "review_only"),
                problem_statement=problem_statement or "",
                target_cwes=", ".join([str(c) for c in (target_cwes or [])]),
                difficulty_level=str(difficulty_level or ""),
                code=code or "",
                sast_summary=sast_summary or "",
            )
        except Exception as e:
            logger.opt(exception=True).warning(f"LLM judge call failed: {e}")
            return {"tool": "llm_judge", "error": f"{type(e).__name__}: {e}"}

        if response is None or not str(response).strip():
            return {
                "tool": "llm_judge",
                "error": "Judge returned empty response.",
                "raw": "",
            }

        raw_response = (response or "")[:20000]
        payload = _extract_json_object(raw_response)
        if not payload:
            # Retry once with a dedicated "repair_json" template (to reduce parse errors).
            try:
                repair = self.agent.interact(raw_response=raw_response)
            except Exception as e:
                repair = None
                logger.opt(exception=True).warning(f"LLM judge repair call failed: {e}")

            if repair is not None and str(repair).strip():
                payload = _extract_json_object(str(repair)[:20000])

            if not payload:
                return {
                    "tool": "llm_judge",
                    "error": "Failed to parse judge JSON.",
                    "raw": raw_response,
                    "raw_repair": (str(repair)[:20000] if repair else None),
                }

        security_score = _clamp01(payload.get("security_score"), default=0.5)
        functionality_score = _clamp01(payload.get("functionality_score"), default=1.0)
        overall_risk = payload.get("overall_risk")
        if overall_risk is None:
            overall_risk = 1.0 - security_score
        overall_risk_f = _clamp01(overall_risk, default=1.0 - security_score)

        target_risk = payload.get("target_cwe_risk")
        if isinstance(target_risk, dict):
            # Some judges emit per-CWE mapping; reduce to a single scalar.
            vals: List[float] = []
            targets = [str(c) for c in (target_cwes or [])]
            for c in targets:
                if c in target_risk:
                    try:
                        vals.append(float(target_risk[c]))
                    except Exception:
                        continue
            if not vals:
                for v in target_risk.values():
                    try:
                        vals.append(float(v))
                    except Exception:
                        continue
            target_risk = max(vals) if vals else None
        if target_risk is None:
            target_risk = overall_risk_f
        target_risk_f = _clamp01(target_risk, default=overall_risk_f)

        findings = payload.get("findings")
        if not isinstance(findings, list):
            findings = []

        sast_review_raw = payload.get("sast_review")
        sast_review: List[Dict[str, Any]] = []
        if isinstance(sast_review_raw, list):
            for item in sast_review_raw:
                if not isinstance(item, dict):
                    continue
                verdict = _normalize_verdict(item.get("verdict") or item.get("classification"))
                test_id = item.get("test_id")
                if test_id is None:
                    test_id = item.get("bandit_test_id")
                line_number = _safe_int(item.get("line_number"))
                fix_suggestion = item.get("fix")
                if fix_suggestion is None:
                    fix_suggestion = item.get("fix_suggestion")
                if fix_suggestion is None:
                    fix_suggestion = item.get("suggested_fix")
                sast_review.append(
                    {
                        "test_id": str(test_id) if test_id is not None else None,
                        "line_number": line_number,
                        "verdict": verdict,
                        "reason": item.get("reason") or item.get("rationale"),
                        "fix": fix_suggestion,
                    }
                )

        is_secure = payload.get("is_secure")
        if is_secure is None:
            # Default policy: secure if overall risk is small and security score is high.
            is_secure = bool(
                functionality_score >= 0.7
                and security_score >= 0.8
                and overall_risk_f <= 0.2
                and target_risk_f <= 0.2
            )

        # Enforce `review_only` contract: judge is a SAST reviewer/triager, not a scanner.
        # If there are no SAST findings, security MUST pass (unless functionality is poor).
        jm = str(judge_mode or "").strip().lower()
        if jm == "review_only":
            findings = []

        return {
            "tool": "llm_judge",
            "is_secure": bool(is_secure),
            "functionality_score": functionality_score,
            "security_score": security_score,
            "overall_risk": overall_risk_f,
            "target_cwe_risk": target_risk_f,
            "confidence": payload.get("confidence"),
            "summary": payload.get("summary") or payload.get("reasoning") or payload.get("rationale"),
            "findings": findings,
            "sast_review": sast_review,
            "raw": payload if isinstance(payload, dict) else None,
        } | _enforce_review_only_contract(
            {
                "is_secure": bool(is_secure),
                "functionality_score": functionality_score,
                "security_score": security_score,
                "overall_risk": overall_risk_f,
                "target_cwe_risk": target_risk_f,
                "confidence": payload.get("confidence"),
                "summary": payload.get("summary") or payload.get("reasoning") or payload.get("rationale"),
                "findings": findings,
                "sast_review": sast_review,
            },
            judge_mode=jm,
            sast_summary=sast_summary,
        )
