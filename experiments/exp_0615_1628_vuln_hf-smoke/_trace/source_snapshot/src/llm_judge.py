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


def _normalize_duplicate_ref(value: Any) -> Optional[str]:
    raw = str(value or "").strip()
    if not raw:
        return None
    if "#" in raw:
        test_id, line_text = raw.rsplit("#", 1)
        line_number = _safe_int(line_text)
        if test_id and line_number is not None:
            return f"{test_id}:{line_number}"
        return test_id or None
    return raw


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
                        "duplicate_of": _normalize_duplicate_ref(item.get("duplicate_of")),
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
        }
