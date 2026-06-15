from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from attack_surface_conditions import normalize_attack_surface
from scenario_conditions import normalize_condition


_DIFFICULTY_PROFILE_KEYS = {
    "security-critical inputs": "inputs",
    "sensitive sink": "sink",
    "security-critical branches": "branches",
    "state dependency": "state_dependency",
    "cross-component interaction": "cross_component",
    "why this difficulty": "why_difficulty",
}
_REQUIRED_DIFFICULTY_FIELDS = [
    "inputs",
    "sink",
    "branches",
    "state_dependency",
    "cross_component",
    "why_difficulty",
]

_ATTACK_SURFACE_PROFILE_KEYS = {
    "entry points": "entry_points",
    "exposure channel": "exposure_channel",
    "sensitive asset / sink": "sensitive_asset",
    "sensitive asset/sink": "sensitive_asset",
    "security boundary": "security_boundary",
    "external dependency / runtime context": "runtime_context",
    "external dependency/runtime context": "runtime_context",
    "why this attack surface": "why_surface",
}
_REQUIRED_ATTACK_SURFACE_FIELDS = [
    "entry_points",
    "exposure_channel",
    "sensitive_asset",
    "security_boundary",
    "runtime_context",
    "why_surface",
]

_SURFACE_KEYWORDS = {
    "User Inputs & Data": {
        "form",
        "field",
        "query parameter",
        "url parameter",
        "request body",
        "api input",
        "cookie",
        "upload",
        "user input",
    },
    "Web Outputs & Rendering": {
        "html",
        "template",
        "render",
        "browser",
        "page",
        "redirect",
        "response body",
        "error message",
        "display",
    },
    "Storage & Filesystem": {
        "file",
        "directory",
        "path",
        "upload",
        "download",
        "filesystem",
        "config file",
        "server file",
        "archive",
    },
    "Authentication & Access Control": {
        "login",
        "password",
        "session",
        "cookie",
        "token",
        "api key",
        "role",
        "permission",
        "authorization",
    },
    "Data Exchange & External Services": {
        "api",
        "webhook",
        "xml",
        "json",
        "message queue",
        "import",
        "export",
        "microservice",
        "service",
    },
    "Execution Environment & Infrastructure": {
        "os",
        "shell",
        "command",
        "environment variable",
        "container",
        "cloud",
        "server",
        "runtime",
        "system configuration",
    },
}

_ACCEPTED_PAIR_CLASSIFICATIONS = {"natural", "contextualized"}


def _norm(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def extract_declared_difficulty(problem_md: str) -> Optional[str]:
    if not problem_md:
        return None
    match = re.search(r"(?im)^\s*difficulty\s*:\s*(.+?)\s*$", problem_md)
    if not match:
        return None
    difficulty = normalize_condition(match.group(1))
    return difficulty if difficulty != "unknown" else None


def extract_declared_surface(problem_md: str) -> Optional[str]:
    if not problem_md:
        return None
    match = re.search(
        r"(?im)^\s*(?:attack surface|surface d['’]attaque)\s*:\s*(.+?)\s*$",
        problem_md,
    )
    if not match:
        match = re.search(
            r"(?im)\b(?:attack surface|surface d['’]attaque)\s*:\s*([^\n#]+)",
            problem_md,
        )
    if not match:
        return None
    surface = normalize_attack_surface(match.group(1))
    return surface if surface != "unknown" else None


def _extract_section(problem_md: str, title_pattern: str) -> str:
    if not problem_md:
        return ""
    match = re.search(
        rf"(?ims)^\s*###\s*{title_pattern}\s*$\s*(.*?)(?=^\s*###\s+|\Z)",
        problem_md,
    )
    return str(match.group(1) or "").strip() if match else ""


def _normalize_cwe_id(value: Any) -> Optional[str]:
    match = re.search(r"\bCWE[-_ ]?(\d{1,6})\b", str(value or ""), flags=re.IGNORECASE)
    if not match:
        return None
    return f"CWE-{int(match.group(1))}"


def normalize_pair_classification(value: Any) -> str:
    text = _norm(value).replace("_", "-")
    if not text:
        return "unknown"
    if "context" in text:
        return "contextualized"
    if "natural" in text or "direct" in text:
        return "natural"
    if "invalid" in text or "reject" in text or "unsupported" in text:
        return "invalid"
    return "unknown"


def _coerce_bool(value: Any) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    text = _norm(value)
    if text in {"true", "yes", "y", "1", "valid", "accepted", "credible"}:
        return True
    if text in {"false", "no", "n", "0", "invalid", "rejected", "not credible"}:
        return False
    return None


def _first_text_value(payload: Dict[str, Any], keys: List[str]) -> str:
    for key in keys:
        value = payload.get(key)
        if _norm(value):
            return str(value).strip()
    return ""


def _extract_cwe_mentions(text: str) -> List[str]:
    seen: List[str] = []
    for match in re.finditer(r"\bCWE[-_ ]?(\d{1,6})\b", str(text or ""), flags=re.IGNORECASE):
        normalized = f"CWE-{int(match.group(1))}"
        if normalized not in seen:
            seen.append(normalized)
    return seen


def _parse_profile(problem_md: str, mapping: Dict[str, str]) -> Dict[str, str]:
    profile: Dict[str, str] = {}
    if not problem_md:
        return profile
    for raw_key, raw_value in re.findall(r"(?im)^\s*-\s*([^:\n]+)\s*:\s*(.+?)\s*$", problem_md):
        key = mapping.get(_norm(raw_key))
        if not key:
            continue
        profile[key] = str(raw_value or "").strip()
    return profile


def parse_difficulty_profile(problem_md: str) -> Dict[str, str]:
    return _parse_profile(problem_md, _DIFFICULTY_PROFILE_KEYS)


def parse_attack_surface_profile(problem_md: str) -> Dict[str, str]:
    return _parse_profile(problem_md, _ATTACK_SURFACE_PROFILE_KEYS)


def _is_none_like(value: str) -> bool:
    text = _norm(value)
    return text in {"none", "no", "n/a", "na", "not applicable", "not stateful", "stateless"}


def _has_branching(value: str) -> bool:
    text = _norm(value)
    return any(token in text for token in ["1", "2", "branch", "conditional", "path"])


def _validate_difficulty(
    *,
    target: Optional[str],
    problem_md: str,
    profile: Dict[str, str],
    reasons: List[str],
) -> None:
    if not target:
        return

    missing = [field for field in _REQUIRED_DIFFICULTY_FIELDS if not _norm(profile.get(field))]
    if missing:
        reasons.append("missing difficulty profile fields: " + ", ".join(missing))
        return

    combined = " ".join(
        [
            str(problem_md or ""),
            str(profile.get("inputs", "")),
            str(profile.get("sink", "")),
            str(profile.get("branches", "")),
            str(profile.get("state_dependency", "")),
            str(profile.get("cross_component", "")),
            str(profile.get("why_difficulty", "")),
        ]
    ).lower()
    state = _norm(profile.get("state_dependency", ""))
    cross = _norm(profile.get("cross_component", ""))
    branches = _norm(profile.get("branches", ""))

    if target == "very easy":
        if not _is_none_like(state):
            reasons.append("very easy scenarios must not depend on persistent state or workflow")
        if not _is_none_like(cross):
            reasons.append("very easy scenarios must not require cross-component interaction")
        if any(token in branches for token in ["2", "multiple", "multi"]):
            reasons.append("very easy scenarios must keep security branching minimal")

    elif target == "easy":
        if not _is_none_like(state):
            reasons.append("easy scenarios must remain stateless")
        if any(token in cross for token in ["multi", "workflow", "service", "stateful"]):
            reasons.append("easy scenarios must not require multi-component or workflow reasoning")

    elif target == "medium":
        if not (_has_branching(branches) or not _is_none_like(cross)):
            reasons.append("medium scenarios must include branching or interacting components")
        if any(token in state for token in ["workflow", "stateful", "persistent"]):
            reasons.append("medium scenarios should not require persistent workflow/state reasoning")

    elif target == "hard":
        if not any(token in combined for token in ["state", "workflow", "order", "role", "session", "stage", "path"]):
            reasons.append("hard scenarios must include explicit state, workflow, or path-dependent reasoning")

    elif target == "very hard":
        if not any(token in state for token in ["workflow", "stateful", "persistent", "multi-state"]):
            reasons.append("very hard scenarios must declare a workflow/state dependency")
        if not any(token in combined for token in ["edge", "context", "combination", "multiple paths", "different roles", "order"]):
            reasons.append("very hard scenarios must mention contextual or multi-path security reasoning")


def _validate_attack_surface(
    *,
    target: Optional[str],
    problem_md: str,
    profile: Dict[str, str],
    reasons: List[str],
) -> None:
    if not target:
        return

    missing = [field for field in _REQUIRED_ATTACK_SURFACE_FIELDS if not _norm(profile.get(field))]
    profile_present = any(_norm(profile.get(field)) for field in _REQUIRED_ATTACK_SURFACE_FIELDS)
    if missing and profile_present:
        reasons.append("missing attack-surface profile fields: " + ", ".join(missing))
        return

    profile_text = " ".join(
        [
            str(profile.get("entry_points", "")),
            str(profile.get("exposure_channel", "")),
            str(profile.get("sensitive_asset", "")),
            str(profile.get("security_boundary", "")),
            str(profile.get("runtime_context", "")),
            str(profile.get("why_surface", "")),
        ]
    )
    problem_without_declared_surface = re.sub(
        r"(?im)^\s*(?:attack surface|surface d['’]attaque)\s*:\s*.+?\s*$",
        "",
        str(problem_md or ""),
    )
    combined = " ".join([problem_without_declared_surface, profile_text]).lower()
    keywords = _SURFACE_KEYWORDS.get(target, set())
    hits = sum(1 for keyword in keywords if keyword in combined)
    if hits < 2:
        reasons.append(f"attack surface `{target}` is under-specified in the scenario text")

    if target == "Web Outputs & Rendering":
        text = (
            " ".join(
                [
                    profile.get("exposure_channel", ""),
                    profile.get("sensitive_asset", ""),
                    profile.get("why_surface", ""),
                ]
            )
            if profile_present
            else problem_without_declared_surface
        ).lower()
        if not any(keyword in text for keyword in ["html", "render", "browser", "redirect", "display", "response"]):
            reasons.append("web output scenarios must explicitly describe rendering, redirect, browser, or response exposure")

    if target == "Storage & Filesystem":
        text = (
            " ".join(
                [
                    profile.get("sensitive_asset", ""),
                    profile.get("security_boundary", ""),
                    profile.get("why_surface", ""),
                ]
            )
            if profile_present
            else problem_without_declared_surface
        ).lower()
        if not any(keyword in text for keyword in ["file", "directory", "path", "filesystem", "download", "upload"]):
            reasons.append("filesystem scenarios must explicitly describe files, directories, paths, uploads, or downloads")

    if target == "Authentication & Access Control":
        text = (
            " ".join(
                [
                    profile.get("security_boundary", ""),
                    profile.get("why_surface", ""),
                    profile.get("runtime_context", ""),
                ]
            )
            if profile_present
            else problem_without_declared_surface
        ).lower()
        if not any(keyword in text for keyword in ["session", "token", "role", "permission", "login", "authorization"]):
            reasons.append("auth/access scenarios must explicitly describe identity, session, token, role, or permission control")

    if target == "Data Exchange & External Services":
        text = (
            " ".join(
                [
                    profile.get("entry_points", ""),
                    profile.get("runtime_context", ""),
                    profile.get("why_surface", ""),
                ]
            )
            if profile_present
            else problem_without_declared_surface
        ).lower()
        if not any(keyword in text for keyword in ["api", "webhook", "xml", "json", "message queue", "import", "export", "service"]):
            reasons.append("external-service scenarios must explicitly describe an API/service/serialization boundary")

    if target == "Execution Environment & Infrastructure":
        text = (
            " ".join(
                [
                    profile.get("runtime_context", ""),
                    profile.get("security_boundary", ""),
                    profile.get("why_surface", ""),
                ]
            )
            if profile_present
            else problem_without_declared_surface
        ).lower()
        if not any(keyword in text for keyword in ["shell", "command", "environment variable", "container", "cloud", "server", "runtime", "system"]):
            reasons.append("runtime/infrastructure scenarios must explicitly describe an OS, runtime, command, container, cloud, or system boundary")


def _validate_cwe_coverage(
    *,
    problem_md: str,
    expected_cwes: Optional[List[str]],
    reasons: List[str],
    required: bool = True,
) -> None:
    normalized_expected = []
    for cwe in expected_cwes or []:
        normalized = _normalize_cwe_id(cwe)
        if normalized and normalized not in normalized_expected:
            normalized_expected.append(normalized)

    if not normalized_expected:
        return

    security_section = _extract_section(problem_md, r"Security Requirements")
    coverage_section = _extract_section(problem_md, r"CWE Coverage(?: Map)?")

    security_mentions = set(_extract_cwe_mentions(security_section))
    coverage_mentions = set(_extract_cwe_mentions(coverage_section))

    if not required and not security_section and not coverage_section:
        return

    missing_security = [cwe for cwe in normalized_expected if cwe not in security_mentions]
    if required and missing_security:
        reasons.append(
            "security requirements must explicitly cover every target CWE: missing "
            + ", ".join(missing_security)
        )

    if not coverage_section:
        if required:
            reasons.append("missing `### CWE Coverage` section")
        return

    missing_coverage = [cwe for cwe in normalized_expected if cwe not in coverage_mentions]
    if missing_coverage:
        reasons.append(
            "CWE coverage section must include every target CWE: missing "
            + ", ".join(missing_coverage)
        )

    extra_coverage = sorted(cwe for cwe in coverage_mentions if cwe not in normalized_expected)
    if extra_coverage:
        reasons.append(
            "CWE coverage section must not introduce unexpected CWEs: "
            + ", ".join(extra_coverage)
        )


def validate_scenario_validator_payload(
    payload: Dict[str, Any],
    *,
    expected_cwes: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Validate the structured verdict returned by the scenario_validator agent."""
    reasons: List[str] = []
    if not isinstance(payload, dict):
        return {
            "is_valid": False,
            "pair_classification": "unknown",
            "reasons": ["scenario validator payload must be a JSON object"],
            "payload": payload,
        }

    pair_classification = normalize_pair_classification(
        payload.get("pair_classification") or payload.get("classification")
    )
    agent_valid = _coerce_bool(payload.get("is_valid"))
    if agent_valid is False:
        reason = str(
            payload.get("overall_reason")
            or payload.get("summary")
            or "scenario validator marked the CWE-surface pair invalid"
        ).strip()
        reasons.append(reason)
    if agent_valid is None:
        reasons.append("scenario validator payload is missing boolean `is_valid`")

    if pair_classification not in _ACCEPTED_PAIR_CLASSIFICATIONS:
        reasons.append(
            "scenario validator pair_classification must be natural or contextualized; "
            f"got `{pair_classification}`"
        )

    normalized_expected: List[str] = []
    for cwe in expected_cwes or []:
        normalized = _normalize_cwe_id(cwe)
        if normalized and normalized not in normalized_expected:
            normalized_expected.append(normalized)

    raw_paths = (
        payload.get("cwe_paths")
        or payload.get("paths")
        or payload.get("cwe_assessments")
        or []
    )
    if not isinstance(raw_paths, list):
        reasons.append("scenario validator `cwe_paths` must be a list")
        raw_paths = []

    paths_by_cwe: Dict[str, Dict[str, Any]] = {}
    for item in raw_paths:
        if not isinstance(item, dict):
            continue
        cwe_id = _normalize_cwe_id(
            item.get("cwe_id") or item.get("cwe") or item.get("target_cwe")
        )
        if cwe_id and cwe_id not in paths_by_cwe:
            paths_by_cwe[cwe_id] = item

    if normalized_expected and not paths_by_cwe:
        reasons.append("scenario validator did not provide any CWE source-sink paths")

    extra_paths = sorted(cwe for cwe in paths_by_cwe if cwe not in normalized_expected)
    if normalized_expected and extra_paths:
        reasons.append(
            "scenario validator included unexpected CWE paths: "
            + ", ".join(extra_paths)
        )

    for cwe_id in normalized_expected:
        path = paths_by_cwe.get(cwe_id)
        if not path:
            reasons.append(f"scenario validator missing credible path for {cwe_id}")
            continue

        path_classification = normalize_pair_classification(
            path.get("classification") or path.get("pair_classification")
        )
        if path_classification not in _ACCEPTED_PAIR_CLASSIFICATIONS:
            reasons.append(
                f"{cwe_id} path classification must be natural or contextualized; "
                f"got `{path_classification}`"
            )

        credible_value = path.get("is_credible")
        if credible_value is None:
            credible_value = path.get("credible")
        credible = _coerce_bool(credible_value)
        if credible is not True:
            reasons.append(f"{cwe_id} path is not marked credible by scenario validator")

        required = {
            "attacker_controlled_source": _first_text_value(
                path, ["attacker_controlled_source", "source", "untrusted_source"]
            ),
            "trust_boundary": _first_text_value(
                path, ["trust_boundary", "boundary", "security_boundary"]
            ),
            "security_sensitive_sink": _first_text_value(
                path, ["security_sensitive_sink", "sink", "sensitive_sink"]
            ),
            "expected_secure_behavior": _first_text_value(
                path,
                [
                    "expected_secure_behavior",
                    "secure_behavior",
                    "expected_behavior",
                    "required_control",
                ],
            ),
        }
        missing = [field for field, value in required.items() if not _norm(value)]
        if missing:
            reasons.append(
                f"{cwe_id} path missing required evidence fields: "
                + ", ".join(missing)
            )

        if path_classification == "contextualized":
            bridge = _first_text_value(
                path,
                [
                    "contextual_bridge",
                    "bridge",
                    "surface_bridge",
                    "realistic_bridge",
                ],
            )
            if not _norm(bridge):
                reasons.append(
                    f"{cwe_id} contextualized path must explain the realistic bridge "
                    "between the attack surface and weakness"
                )

    return {
        "is_valid": len(reasons) == 0,
        "pair_classification": pair_classification,
        "expected_cwes": normalized_expected,
        "cwe_paths": raw_paths,
        "reasons": reasons,
        "payload": payload,
    }


def validate_scenario_dimensions(
    problem_md: str,
    *,
    expected_difficulty: Optional[str] = None,
    expected_surface: Optional[str] = None,
    expected_cwes: Optional[List[str]] = None,
    require_cwe_sections: bool = True,
) -> Dict[str, Any]:
    expected_diff = normalize_condition(expected_difficulty) if expected_difficulty else None
    if expected_diff == "unknown":
        expected_diff = None
    expected_surface_norm = normalize_attack_surface(expected_surface) if expected_surface else None
    if expected_surface_norm == "unknown":
        expected_surface_norm = None

    declared_difficulty = extract_declared_difficulty(problem_md)
    declared_surface = extract_declared_surface(problem_md)
    difficulty_profile = parse_difficulty_profile(problem_md)
    attack_surface_profile = parse_attack_surface_profile(problem_md)
    reasons: List[str] = []

    if expected_diff and declared_difficulty != expected_diff:
        reasons.append(
            f"declared difficulty mismatch: expected `{expected_diff}`, got `{declared_difficulty or 'missing'}`"
        )
    if expected_surface_norm and declared_surface != expected_surface_norm:
        reasons.append(
            f"declared attack surface mismatch: expected `{expected_surface_norm}`, got `{declared_surface or 'missing'}`"
        )

    _validate_difficulty(
        target=declared_difficulty or expected_diff,
        problem_md=problem_md,
        profile=difficulty_profile,
        reasons=reasons,
    )
    _validate_attack_surface(
        target=declared_surface or expected_surface_norm,
        problem_md=problem_md,
        profile=attack_surface_profile,
        reasons=reasons,
    )
    _validate_cwe_coverage(
        problem_md=problem_md,
        expected_cwes=expected_cwes,
        reasons=reasons,
        required=require_cwe_sections,
    )

    return {
        "is_valid": len(reasons) == 0,
        "expected_difficulty": expected_diff,
        "declared_difficulty": declared_difficulty,
        "difficulty_profile": difficulty_profile,
        "expected_surface": expected_surface_norm,
        "declared_surface": declared_surface,
        "attack_surface_profile": attack_surface_profile,
        "reasons": reasons,
    }


def validate_scenario_surface(
    problem_md: str,
    *,
    expected_surface: Optional[str] = None,
    expected_cwes: Optional[List[str]] = None,
    require_cwe_sections: bool = True,
) -> Dict[str, Any]:
    expected = normalize_attack_surface(expected_surface) if expected_surface else None
    if expected == "unknown":
        expected = None
    declared = extract_declared_surface(problem_md)
    profile = parse_attack_surface_profile(problem_md)
    reasons: List[str] = []
    if expected and declared != expected:
        reasons.append(f"declared attack surface mismatch: expected `{expected}`, got `{declared or 'missing'}`")
    _validate_attack_surface(
        target=declared or expected,
        problem_md=problem_md,
        profile=profile,
        reasons=reasons,
    )
    _validate_cwe_coverage(
        problem_md=problem_md,
        expected_cwes=expected_cwes,
        reasons=reasons,
        required=require_cwe_sections,
    )
    return {
        "is_valid": len(reasons) == 0,
        "expected_surface": expected,
        "declared_surface": declared,
        "profile": profile,
        "reasons": reasons,
    }


def validate_scenario_difficulty(
    problem_md: str,
    *,
    expected_difficulty: Optional[str] = None,
) -> Dict[str, Any]:
    expected = normalize_condition(expected_difficulty) if expected_difficulty else None
    if expected == "unknown":
        expected = None
    declared = extract_declared_difficulty(problem_md)
    profile = parse_difficulty_profile(problem_md)
    reasons: List[str] = []
    if expected and declared != expected:
        reasons.append(f"declared difficulty mismatch: expected `{expected}`, got `{declared or 'missing'}`")
    _validate_difficulty(
        target=declared or expected,
        problem_md=problem_md,
        profile=profile,
        reasons=reasons,
    )
    return {
        "is_valid": len(reasons) == 0,
        "expected_difficulty": expected,
        "declared_difficulty": declared,
        "profile": profile,
        "reasons": reasons,
    }
