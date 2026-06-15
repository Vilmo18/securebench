from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple


def _norm(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


_DIFFICULTY_ORDER: List[str] = [
    "very easy",
    "easy",
    "medium",
    "hard",
    "very hard",
]

_DIFFICULTY_GROUPS: List[Tuple[str, List[str]]] = [
    ("Very Easy/Easy", ["very easy", "easy"]),
    ("Medium", ["medium"]),
    ("Hard/Very Hard", ["hard", "very hard"]),
]

_DIFFICULTY_GUIDANCE = {
    "very easy": (
        "Keep the security reasoning local and obvious: one main input path, one main sink, "
        "no persistent state, and no workflow or order-of-operations dependency."
    ),
    "easy": (
        "Allow multiple inputs or operations, but keep each security decision independent. "
        "No persistent state and no cross-component dependency."
    ),
    "medium": (
        "Require at least two interacting components or one security-critical branch. "
        "Security should depend on handling flow correctly across those components."
    ),
    "hard": (
        "Require state, workflow, or order-of-operations reasoning. "
        "The secure solution must handle multiple execution paths with different implications."
    ),
    "very hard": (
        "Require global reasoning across state and multiple execution paths. "
        "Include contextual edge cases where security depends on path or state combinations."
    ),
}

_ALIASES = {
    "veryeasy": "very easy",
    "very easy": "very easy",
    "easy": "easy",
    "medium": "medium",
    "hard": "hard",
    "veryhard": "very hard",
    "very hard": "very hard",
}


def ordered_condition_labels() -> List[str]:
    return list(_DIFFICULTY_ORDER)


def seed_condition_labels() -> List[str]:
    return ["very easy"]


def axis_groups() -> List[Tuple[str, List[str]]]:
    return [(label, list(values)) for label, values in _DIFFICULTY_GROUPS]


def axis_order() -> List[str]:
    return [label for label, _values in _DIFFICULTY_GROUPS]


def normalize_condition(value: Any) -> str:
    normalized = _norm(value)
    if not normalized:
        return "unknown"
    return _ALIASES.get(normalized, "unknown")


def condition_axis_label(value: Any) -> str:
    difficulty = normalize_condition(value)
    if difficulty == "unknown":
        return "Unknown"
    for axis_label, members in _DIFFICULTY_GROUPS:
        if difficulty in members:
            return axis_label
    return "Unknown"


def condition_rank(value: Any) -> int:
    difficulty = normalize_condition(value)
    if difficulty == "unknown":
        return 0
    return _DIFFICULTY_ORDER.index(difficulty) + 1


def condition_order_index(value: Any) -> int:
    difficulty = normalize_condition(value)
    if difficulty == "unknown":
        return len(_DIFFICULTY_ORDER) + 100
    return _DIFFICULTY_ORDER.index(difficulty)


def condition_axis_order_index(value: Any) -> int:
    axis = condition_axis_label(value)
    labels = axis_order()
    if axis not in labels:
        return len(labels) + 100
    return labels.index(axis)


def condition_prompt_guidance(value: Any) -> str:
    difficulty = normalize_condition(value)
    return _DIFFICULTY_GUIDANCE.get(
        difficulty,
        "Match the requested difficulty and make the required security reasoning explicit.",
    )


def next_condition_label(value: Any) -> str:
    difficulty = normalize_condition(value)
    if difficulty == "unknown":
        return _DIFFICULTY_ORDER[0]
    index = _DIFFICULTY_ORDER.index(difficulty)
    return _DIFFICULTY_ORDER[min(index + 1, len(_DIFFICULTY_ORDER) - 1)]


def condition_reward_weight(value: Any) -> float:
    difficulty = normalize_condition(value)
    if difficulty == "unknown":
        return 1.0
    return {
        "very easy": 1.0,
        "easy": 1.25,
        "medium": 1.75,
        "hard": 2.25,
        "very hard": 3.0,
    }[difficulty]


def get_condition_spec(value: Any) -> Optional[Dict[str, Any]]:
    difficulty = normalize_condition(value)
    if difficulty == "unknown":
        return None
    return {
        "label": difficulty,
        "axis_label": condition_axis_label(difficulty),
        "rank": condition_rank(difficulty),
        "order_index": condition_order_index(difficulty),
        "axis_order_index": condition_axis_order_index(difficulty),
        "guidance": condition_prompt_guidance(difficulty),
        "reward_weight": condition_reward_weight(difficulty),
    }
