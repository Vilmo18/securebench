from __future__ import annotations

import ast
import inspect
import os
import re
from typing import Any, Dict, Optional, Set


# Mapping library for SAST findings -> CWE.
#
# Notes:
# - Prefer tool-native CWE metadata when available (e.g., Bandit's `issue_cwe` field).
# - Use these mappings as a fallback when the tool does not provide a CWE.


_BANDIT_TEST_TO_CWE_FALLBACK: Dict[str, str] = {}

_BANDIT_DYNAMIC_TEST_TO_CWE: Optional[Dict[str, str]] = None


def _extract_cwe_value(node: ast.AST) -> Optional[int]:
    if isinstance(node, ast.Constant) and isinstance(node.value, int):
        return int(node.value)

    parts: list[str] = []
    cur: Optional[ast.AST] = node
    while isinstance(cur, ast.Attribute):
        parts.append(cur.attr)
        cur = cur.value
    if isinstance(cur, ast.Name):
        parts.append(cur.id)
    else:
        return None

    dotted = ".".join(reversed(parts))
    if dotted.startswith("issue.Cwe."):
        const_name = dotted.split(".", 2)[2]
    elif dotted.startswith("Cwe."):
        const_name = dotted.split(".", 1)[1]
    else:
        return None

    try:
        from bandit.core import issue as issue_mod  # type: ignore
    except Exception:
        return None

    try:
        value = getattr(issue_mod.Cwe, const_name)
        return int(value)
    except Exception:
        return None


def _analyze_bandit_module_for_cwes(module: object) -> Dict[str, Set[int]]:
    try:
        src_path = inspect.getsourcefile(module) or inspect.getfile(module)
    except Exception:
        src_path = None
    if not src_path or not os.path.exists(src_path):
        return {}

    try:
        with open(src_path, "r", encoding="utf-8") as f:
            src = f.read()
    except Exception:
        return {}

    try:
        tree = ast.parse(src)
    except SyntaxError:
        return {}

    func_defs = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    direct: Dict[str, Set[int]] = {name: set() for name in func_defs}
    calls: Dict[str, Set[str]] = {name: set() for name in func_defs}

    class _Visitor(ast.NodeVisitor):
        def __init__(self, func_name: str) -> None:
            self.func_name = func_name

        def visit_Call(self, node: ast.Call) -> None:
            if isinstance(node.func, ast.Name):
                calls[self.func_name].add(node.func.id)

            func_name = None
            if isinstance(node.func, ast.Attribute):
                func_name = node.func.attr
            elif isinstance(node.func, ast.Name):
                func_name = node.func.id

            if func_name == "Issue":
                for kw in node.keywords or []:
                    if kw.arg == "cwe":
                        val = _extract_cwe_value(kw.value)
                        if isinstance(val, int) and val > 0:
                            direct[self.func_name].add(val)

            self.generic_visit(node)

    for name, node in func_defs.items():
        _Visitor(name).visit(node)

    closure: Dict[str, Set[int]] = {k: set(v) for k, v in direct.items()}
    changed = True
    while changed:
        changed = False
        for name in func_defs:
            before = set(closure[name])
            for callee in calls[name]:
                if callee in closure:
                    closure[name].update(closure[callee])
            if closure[name] != before:
                changed = True

    return closure


def _build_bandit_test_to_cwe_mapping() -> Dict[str, str]:
    try:
        from bandit.core.extension_loader import MANAGER  # type: ignore
    except Exception:
        return {}

    mapping: Dict[str, str] = {}

    for test_id, info in (getattr(MANAGER, "blacklist_by_id", {}) or {}).items():
        if not isinstance(info, dict):
            continue
        cwe = info.get("cwe")
        if isinstance(cwe, int) and cwe > 0:
            mapping[str(test_id).strip().upper()] = f"CWE-{cwe}"

    module_cache: Dict[str, Dict[str, Set[int]]] = {}
    for test_id, ext in (getattr(MANAGER, "plugins_by_id", {}) or {}).items():
        func = getattr(ext, "plugin", None)
        if not callable(func):
            continue
        module_name = getattr(func, "__module__", None)
        if not module_name:
            continue

        try:
            mod = inspect.getmodule(func)
        except Exception:
            mod = None
        if mod is None:
            continue

        if module_name not in module_cache:
            module_cache[module_name] = _analyze_bandit_module_for_cwes(mod)

        cwes = module_cache[module_name].get(getattr(func, "__name__", ""))
        if not cwes:
            continue

        cwe_val = sorted([int(v) for v in cwes if isinstance(v, int) and v > 0])[0]
        mapping[str(test_id).strip().upper()] = f"CWE-{cwe_val}"

    return mapping


def _get_bandit_test_to_cwe_mapping() -> Dict[str, str]:
    global _BANDIT_DYNAMIC_TEST_TO_CWE
    if _BANDIT_DYNAMIC_TEST_TO_CWE is not None:
        return _BANDIT_DYNAMIC_TEST_TO_CWE
    _BANDIT_DYNAMIC_TEST_TO_CWE = _build_bandit_test_to_cwe_mapping()
    return _BANDIT_DYNAMIC_TEST_TO_CWE


def bandit_test_to_cwe(test_id: str) -> Optional[str]:
    if not test_id:
        return None
    tid = str(test_id).strip().upper()
    dynamic = _get_bandit_test_to_cwe_mapping()
    if dynamic.get(tid):
        return dynamic.get(tid)
    return _BANDIT_TEST_TO_CWE_FALLBACK.get(tid)


_CWE_RE = re.compile(r"\bCWE[-_ ]?(\d{1,6})\b", flags=re.IGNORECASE)


def extract_cwe_id(value: Any) -> Optional[str]:
    """
    Best-effort extraction of a CWE ID from strings/lists/dicts.

    Examples:
      - "CWE-79" -> "CWE-79"
      - "CWE-79: Cross-site Scripting" -> "CWE-79"
      - ["CWE-22", "CWE-78"] -> "CWE-22"
    """
    if value is None:
        return None

    if isinstance(value, str):
        m = _CWE_RE.search(value)
        if not m:
            return None
        try:
            num = int(m.group(1))
        except Exception:
            return None
        if num <= 0:
            return None
        return f"CWE-{num}"

    if isinstance(value, (list, tuple, set)):
        for item in value:
            cwe = extract_cwe_id(item)
            if cwe:
                return cwe
        return None

    if isinstance(value, dict):
        # Common metadata keys first.
        for k in ("cwe", "cwe_id", "cwe-id", "cweID", "cweId"):
            if k in value:
                cwe = extract_cwe_id(value.get(k))
                if cwe:
                    return cwe

        # Fall back to scanning values.
        for v in value.values():
            cwe = extract_cwe_id(v)
            if cwe:
                return cwe
        return None

    return None
