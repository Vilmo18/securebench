from __future__ import annotations

import hashlib
import re
from typing import Any, Dict, List, Optional, Tuple


def _norm(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


_ATTACK_SURFACES: List[str] = [
    "User Inputs & Data",
    "Web Outputs & Rendering",
    "Storage & Filesystem",
    "Authentication & Access Control",
    "Data Exchange & External Services",
    "Execution Environment & Infrastructure",
]

_GUIDANCE = {
    "User Inputs & Data": (
        "Center the scenario on attacker-controlled input such as forms, query parameters, API payloads, "
        "cookies, or file uploads. The main security boundary must be input ingestion and validation."
    ),
    "Web Outputs & Rendering": (
        "Center the scenario on what is rendered or returned to a browser or web client: dynamic HTML, "
        "redirects, user-visible error messages, or reflected/stored display paths."
    ),
    "Storage & Filesystem": (
        "Center the scenario on server-side files, directories, uploads, downloads, or configuration files. "
        "The main security boundary must be storage path control or filesystem access."
    ),
    "Authentication & Access Control": (
        "Center the scenario on login, sessions, passwords, tokens, API keys, roles, or authorization checks. "
        "The main security boundary must be identity or permission enforcement."
    ),
    "Data Exchange & External Services": (
        "Center the scenario on APIs, webhooks, XML/JSON handling, import/export, message queues, or service-to-service "
        "data exchange. The main security boundary must be a service or serialization boundary."
    ),
    "Execution Environment & Infrastructure": (
        "Center the scenario on operating-system commands, runtime environment, containers, cloud configuration, "
        "environment variables, or system configuration boundaries."
    ),
}

_ALIASES = {
    "entrees & donnees utilisateur": "User Inputs & Data",
    "entrees et donnees utilisateur": "User Inputs & Data",
    "entrées & données utilisateur": "User Inputs & Data",
    "entrées et données utilisateur": "User Inputs & Data",
    "user inputs & data": "User Inputs & Data",
    "user input & data": "User Inputs & Data",
    "sorties web & affichage": "Web Outputs & Rendering",
    "sorties web et affichage": "Web Outputs & Rendering",
    "web outputs & rendering": "Web Outputs & Rendering",
    "web output & rendering": "Web Outputs & Rendering",
    "stockage & systeme de fichiers": "Storage & Filesystem",
    "stockage et systeme de fichiers": "Storage & Filesystem",
    "stockage & système de fichiers": "Storage & Filesystem",
    "stockage et système de fichiers": "Storage & Filesystem",
    "storage & filesystem": "Storage & Filesystem",
    "authentification & controle d’accès": "Authentication & Access Control",
    "authentification & controle d'acces": "Authentication & Access Control",
    "authentification et controle d'acces": "Authentication & Access Control",
    "authentification & contrôle d’accès": "Authentication & Access Control",
    "authentification & contrôle d'acces": "Authentication & Access Control",
    "authentication & access control": "Authentication & Access Control",
    "echanges de donnees & services externes": "Data Exchange & External Services",
    "echanges de donnees et services externes": "Data Exchange & External Services",
    "échanges de données & services externes": "Data Exchange & External Services",
    "échanges de données et services externes": "Data Exchange & External Services",
    "data exchange & external services": "Data Exchange & External Services",
    "environnement d’execution & infrastructure": "Execution Environment & Infrastructure",
    "environnement d'execution & infrastructure": "Execution Environment & Infrastructure",
    "environnement d’exécution & infrastructure": "Execution Environment & Infrastructure",
    "environnement d'exécution & infrastructure": "Execution Environment & Infrastructure",
    "execution environment & infrastructure": "Execution Environment & Infrastructure",
}
_ALIASES.update({_norm(label): label for label in _ATTACK_SURFACES})


def ordered_attack_surfaces() -> List[str]:
    return list(_ATTACK_SURFACES)


def seed_attack_surfaces(available_surfaces: Optional[List[str]] = None) -> List[str]:
    surfaces = [
        normalize_attack_surface(label)
        for label in (available_surfaces or _ATTACK_SURFACES)
    ]
    surfaces = [label for label in surfaces if label != "unknown"]
    if not surfaces:
        return [_ATTACK_SURFACES[0]]
    return [surfaces[0]]


def attack_surface_axis_groups() -> List[Tuple[str, List[str]]]:
    return [(label, [label]) for label in _ATTACK_SURFACES]


def attack_surface_axis_order() -> List[str]:
    return list(_ATTACK_SURFACES)


def normalize_attack_surface(value: Any) -> str:
    normalized = _norm(value)
    if not normalized:
        return "unknown"
    return _ALIASES.get(normalized, "unknown")


def attack_surface_rank(value: Any) -> int:
    surface = normalize_attack_surface(value)
    if surface == "unknown":
        return 0
    return _ATTACK_SURFACES.index(surface) + 1


def next_attack_surface_label(value: Any) -> str:
    surface = normalize_attack_surface(value)
    if surface == "unknown":
        return _ATTACK_SURFACES[0]
    index = _ATTACK_SURFACES.index(surface)
    return _ATTACK_SURFACES[min(index + 1, len(_ATTACK_SURFACES) - 1)]


def attack_surface_reward_weight(value: Any) -> float:
    surface = normalize_attack_surface(value)
    if surface == "unknown":
        return 1.0
    weights = {
        "User Inputs & Data": 1.0,
        "Web Outputs & Rendering": 1.4,
        "Storage & Filesystem": 1.8,
        "Authentication & Access Control": 2.2,
        "Data Exchange & External Services": 2.6,
        "Execution Environment & Infrastructure": 3.0,
    }
    return float(weights.get(surface, 1.0))


def attack_surface_prompt_guidance(value: Any) -> str:
    surface = normalize_attack_surface(value)
    return _GUIDANCE.get(
        surface,
        "Match the requested attack surface and make the main exposure point explicit.",
    )


def get_attack_surface_spec(value: Any) -> Optional[Dict[str, Any]]:
    surface = normalize_attack_surface(value)
    if surface == "unknown":
        return None
    return {
        "label": surface,
        "rank": attack_surface_rank(surface),
        "guidance": attack_surface_prompt_guidance(surface),
    }


def select_attack_surface(
    concepts: Any,
    difficulty: Any,
    available_surfaces: Optional[List[str]] = None,
    preferred: Any = None,
) -> Optional[str]:
    preferred_surface = normalize_attack_surface(preferred)
    if preferred_surface != "unknown":
        return preferred_surface

    surfaces = [
        normalize_attack_surface(label)
        for label in (available_surfaces or ordered_attack_surfaces())
    ]
    surfaces = [label for label in surfaces if label != "unknown"]
    if not surfaces:
        return None

    if isinstance(concepts, (list, tuple, set)):
        concept_parts = sorted({str(c).strip() for c in concepts if str(c).strip()})
    else:
        concept_text = str(concepts or "").strip()
        concept_parts = [concept_text] if concept_text else []

    seed = f"{str(difficulty or '').strip().lower()}|{'|'.join(concept_parts)}"
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()
    index = int(digest[:8], 16) % len(surfaces)
    return surfaces[index]
