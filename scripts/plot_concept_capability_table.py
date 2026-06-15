#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


_CONCEPT_DISPLAY = {
    "algorithms": "Algorithms",
    "conditionals": "Conditionals",
    "data_structures": "Data Struct.",
    "dynamic_programming": "Dyn. Prog.",
    "error_handling": "Error Hand.",
    "functions": "Functions",
    "loops": "Loops",
    "recursion": "Recursion",
    "searching": "Searching",
    "sorting": "Sorting",
}

_DEFAULT_CONCEPT_ORDER = [
    "algorithms",
    "conditionals",
    "data_structures",
    "dynamic_programming",
    "error_handling",
    "functions",
    "loops",
    "recursion",
    "searching",
    "sorting",
]

_MODEL_LABELS = {
    "4o": "4o",
    "4o-mini": "4o-M",
    "llama3.1-405b": "L405",
    "llama3.1-70b": "L70",
    "llama3.1-8b": "L8",
}

_DEFAULT_MODEL_ORDER = ["4o", "4o-mini", "llama3.1-405b", "llama3.1-70b", "llama3.1-8b"]

_DIFF_ORDER = ["very easy", "easy", "medium", "hard", "very hard"]
_DIFF_GROUPS: List[Tuple[str, List[str]]] = [
    ("Very Easy/Easy", ["very easy", "easy"]),
    ("Medium", ["medium"]),
    ("Hard/Very Hard", ["hard", "very hard"]),
]


def _project_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))


def _norm_ws(s: str) -> str:
    return re.sub(r"\s+", " ", str(s or "").strip().lower())


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return float(default)


def _difficulty_group_index(diff: str) -> Optional[int]:
    d = _norm_ws(diff)
    for i, (_name, diffs) in enumerate(_DIFF_GROUPS):
        if d in diffs:
            return i
    return None


def _difficulty_group_name(diff: str) -> Optional[str]:
    idx = _difficulty_group_index(diff)
    return _DIFF_GROUPS[idx][0] if idx is not None else None


def _iter_models_with_metrics(experiments_dir: str, phase: str) -> Iterable[str]:
    exp = os.path.abspath(str(experiments_dir))
    if not os.path.isdir(exp):
        return []
    for name in sorted(os.listdir(exp)):
        p = os.path.join(exp, name, "average_metrics", phase, "concept_metrics.json")
        if os.path.isfile(p):
            yield name


def _read_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        obj = json.load(f)
    return obj if isinstance(obj, dict) else {}


def _load_concept_mastery(experiments_dir: str, model: str, phase: str) -> Dict[str, Dict[str, Dict[str, Any]]]:
    path = os.path.join(os.path.abspath(str(experiments_dir)), str(model), "average_metrics", str(phase), "concept_metrics.json")
    d = _read_json(path)
    cm = d.get("concept_mastery_distribution") if isinstance(d, dict) else None
    return cm if isinstance(cm, dict) else {}


@dataclass
class Cell:
    failure_rate: float  # 0..1 or NaN
    weight: float  # visit weight (0 if inferred)


def _compute_concept_group_cells(
    mastery: Dict[str, Dict[str, Any]],
    *,
    fill_missing: str = "infer",
) -> Tuple[Dict[str, Cell], Optional[str]]:
    """
    Return (by_group, primary_group) for one concept.

    - failure_rate is weighted by visits inside the group when available.
    - primary_group is the group with the most total visits (tie-break: prefer harder group).
    - if fill_missing == "infer": missing groups are inferred as mastered (0.0) for <= max attempted group,
      else beyond capability (1.0).
    - if fill_missing == "blank": missing groups are NaN (plotted grey / empty).
    """
    group_stats: Dict[str, Dict[str, float]] = {g: {"w_sum": 0.0, "w": 0.0, "visits": 0.0} for g, _ in _DIFF_GROUPS}
    attempted_group_idxs: List[int] = []

    for diff, data in (mastery or {}).items():
        g = _difficulty_group_name(diff)
        if not g:
            continue
        idx = _difficulty_group_index(diff)
        if idx is not None:
            attempted_group_idxs.append(idx)

        if not isinstance(data, dict):
            data = {}
        sr = _safe_float(data.get("success_rate"), default=0.0)
        sr = max(0.0, min(1.0, sr))
        fr = 1.0 - sr
        visits = _safe_float(data.get("visits"), default=1.0)
        visits = max(0.0, visits)

        group_stats[g]["w_sum"] += fr * visits
        group_stats[g]["w"] += visits
        group_stats[g]["visits"] += visits

    max_attempted_idx = max(attempted_group_idxs) if attempted_group_idxs else None

    by_group: Dict[str, Cell] = {}
    for i, (g, _diffs) in enumerate(_DIFF_GROUPS):
        w = group_stats[g]["w"]
        if w > 0.0:
            fr = group_stats[g]["w_sum"] / w
            by_group[g] = Cell(failure_rate=float(max(0.0, min(1.0, fr))), weight=float(group_stats[g]["visits"]))
            continue

        if str(fill_missing).strip().lower() == "blank":
            by_group[g] = Cell(failure_rate=math.nan, weight=0.0)
            continue

        if max_attempted_idx is None:
            # Never attempted: treat as beyond capability (conservative).
            by_group[g] = Cell(failure_rate=1.0, weight=0.0)
        else:
            # Infer mastery at/below max attempted group; beyond capability above it.
            by_group[g] = Cell(failure_rate=(0.0 if i <= max_attempted_idx else 1.0), weight=0.0)

    # Primary group = most visits; tie-break: prefer harder group.
    primary = None
    if any(group_stats[g]["visits"] > 0 for g, _ in _DIFF_GROUPS):
        order = [g for g, _ in _DIFF_GROUPS]
        primary = sorted(
            ((g, group_stats[g]["visits"]) for g, _ in _DIFF_GROUPS),
            key=lambda kv: (kv[1], order.index(kv[0])),
            reverse=True,
        )[0][0]

    return by_group, primary


def _build_model_rows(
    mastery_dist: Dict[str, Dict[str, Dict[str, Any]]],
    *,
    fill_missing: str,
) -> List[Dict[str, Any]]:
    concepts = set(mastery_dist.keys())
    # Keep known concept order first, then add any extras at the end.
    ordered = [c for c in _DEFAULT_CONCEPT_ORDER if c in concepts]
    for c in sorted(concepts):
        if c not in ordered:
            ordered.append(c)

    rows: List[Dict[str, Any]] = []
    for concept in ordered:
        by_group, primary = _compute_concept_group_cells(
            mastery_dist.get(concept, {}) or {},
            fill_missing=fill_missing,
        )
        rows.append(
            {
                "concept": concept,
                "primary_group": primary,
                "by_group": {
                    g: {"failure_rate": by_group[g].failure_rate, "visits": by_group[g].weight}
                    for g, _ in _DIFF_GROUPS
                },
            }
        )
    return rows


def _plot_capability_table_multi_model(
    *,
    model_to_rows: Dict[str, List[Dict[str, Any]]],
    out_base: str,
    title: str,
    cmap_name: str = "RdYlGn_r",
) -> None:
    if not model_to_rows:
        return

    try:
        import matplotlib
        import matplotlib.pyplot as plt
    except Exception as e:
        raise SystemExit(f"matplotlib is required for plotting: {type(e).__name__}: {e}")

    group_names = [name for name, _ in _DIFF_GROUPS]
    model_keys = list(model_to_rows.keys())
    model_labels = [_MODEL_LABELS.get(m, m) for m in model_keys]

    # Union concept list across models
    concepts: List[str] = []
    seen = set()
    for rows in model_to_rows.values():
        for r in rows or []:
            c = str(r.get("concept") or "").strip()
            if not c or c in seen:
                continue
            seen.add(c)
            concepts.append(c)

    # Prefer the canonical order.
    concepts = [c for c in _DEFAULT_CONCEPT_ORDER if c in concepts] + sorted([c for c in concepts if c not in _DEFAULT_CONCEPT_ORDER])
    n_rows = len(concepts)
    if n_rows <= 0:
        return

    # Map model -> concept -> row
    model_maps: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for model, rows in model_to_rows.items():
        model_maps[model] = {str(r.get("concept") or "").strip(): r for r in rows or [] if isinstance(r, dict)}

    n_models = len(model_keys)
    n_groups = len(group_names)

    # Matrices per group: concepts x models
    group_mats: Dict[str, List[List[float]]] = {}
    group_txt: Dict[str, List[List[str]]] = {}
    for g in group_names:
        mat: List[List[float]] = []
        txt: List[List[str]] = []
        for concept in concepts:
            row_vals: List[float] = []
            row_txt: List[str] = []
            for model in model_keys:
                row = model_maps.get(model, {}).get(concept, {})
                by_group = row.get("by_group") if isinstance(row, dict) else {}
                by_group = by_group if isinstance(by_group, dict) else {}
                cell = by_group.get(g) if isinstance(by_group.get(g), dict) else {}
                primary = row.get("primary_group") if isinstance(row, dict) else None

                fr = cell.get("failure_rate")
                if fr is None:
                    row_vals.append(math.nan)
                    row_txt.append("")
                    continue

                try:
                    fv = float(fr)
                except Exception:
                    fv = math.nan
                row_vals.append(fv)

                if math.isnan(fv):
                    row_txt.append("")
                    continue

                if fv <= 0.0:
                    s = "✓"
                elif fv >= 1.0:
                    s = "X"
                else:
                    s = f"{fv:.2f}"

                if primary and str(primary) == str(g):
                    s += "†"
                row_txt.append(s)

            mat.append(row_vals)
            txt.append(row_txt)
        group_mats[g] = mat
        group_txt[g] = txt

    fig_w = max(12.5, 1.8 * n_models * n_groups / 2.2 + 5.0)
    fig_h = max(6.0, 0.35 * n_rows + 2.6)
    fig, axes = plt.subplots(1, n_groups, figsize=(fig_w, fig_h), sharey=True)
    if n_groups == 1:
        axes = [axes]

    try:
        cmap = matplotlib.colormaps.get_cmap(cmap_name).copy()  # type: ignore[attr-defined]
    except Exception:
        cmap = matplotlib.cm.get_cmap(cmap_name).copy()
    try:
        cmap.set_bad(color="#eeeeee")
    except Exception:
        pass

    ims = []
    for ax, g in zip(axes, group_names):
        mat = group_mats.get(g) or []
        txt = group_txt.get(g) or []
        im = ax.imshow(mat, aspect="auto", cmap=cmap, vmin=0.0, vmax=1.0)
        ims.append(im)

        ax.set_title(g, pad=8, fontsize=12, fontweight="bold")
        ax.set_xticks(list(range(n_models)))
        ax.set_xticklabels(model_labels)
        ax.xaxis.tick_top()
        ax.tick_params(top=True, bottom=False, labelsize=10)

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
                # Improve readability: pick black/white based on the underlying cell color luminance.
                try:
                    fv = float(mat[y][x])
                except Exception:
                    fv = math.nan
                color = "black"
                if not math.isnan(fv):
                    try:
                        r, g_, b, _a = cmap(float(fv))  # type: ignore[misc]
                        luminance = 0.299 * float(r) + 0.587 * float(g_) + 0.114 * float(b)
                        color = "white" if luminance < 0.55 else "black"
                    except Exception:
                        color = "black"
                ax.text(
                    x,
                    y,
                    s,
                    ha="center",
                    va="center",
                    fontsize=9,
                    fontweight="bold",
                    color=color,
                )

    # y-axis labels on first subplot
    y_labels = [_CONCEPT_DISPLAY.get(c, c) for c in concepts]
    axes[0].set_yticks(list(range(n_rows)))
    axes[0].set_yticklabels(y_labels, fontsize=11)
    axes[0].set_ylabel("Concept", fontsize=12, fontweight="bold")

    # Add a left-side "Concept" header like the paper tables.
    try:
        axes[0].text(
            -0.08,
            1.05,
            "Concept",
            transform=axes[0].transAxes,
            ha="left",
            va="bottom",
            fontsize=12,
            fontweight="bold",
        )
    except Exception:
        pass

    # Add a shared "Model" header above each group panel.
    for ax in axes:
        try:
            ax.text(
                0.5,
                1.10,
                "Model",
                transform=ax.transAxes,
                ha="center",
                va="bottom",
                fontsize=11,
                fontweight="bold",
            )
        except Exception:
            pass

    # Layout: reserve space for the colorbar to the right (avoids overlapping the last panel).
    # Give enough headroom so the suptitle doesn't overlap group titles.
    fig.subplots_adjust(left=0.09, right=0.88, top=0.82, bottom=0.10, wspace=0.06)
    fig.suptitle(title, y=0.96, fontsize=14, fontweight="bold")

    cax = fig.add_axes([0.90, 0.18, 0.015, 0.65])
    fig.colorbar(
        ims[0],
        cax=cax,
        label="Failure rate (1 - success rate)",
    )

    fig.text(
        0.01,
        0.01,
        "Legend: ✓ mastered (no failures), X no success, † primary difficulty group (most visits).",
        ha="left",
        va="bottom",
        fontsize=9,
    )

    # (No tight_layout here: we already positioned axes + colorbar manually.)
    for ext in ("png", "svg", "pdf"):
        fig.savefig(
            f"{out_base}.{ext}",
            bbox_inches="tight",
            dpi=300 if ext == "png" else None,
        )
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser(description="Plot a Prism-style capability table (failure rate) by concept and difficulty.")
    ap.add_argument(
        "--experiments-dir",
        default=os.path.join(_project_root(), "experiments"),
        help="Directory containing per-model experiment folders (default: <project_root>/experiments).",
    )
    ap.add_argument(
        "--phase",
        default="phase_1",
        help="Average-metrics phase folder to use (phase_1|phase_2|whole_tree).",
    )
    ap.add_argument(
        "--models",
        nargs="*",
        default=None,
        help="Model directory names under experiments-dir (default: auto-detect).",
    )
    ap.add_argument(
        "--fill-missing",
        choices=["infer", "blank"],
        default="infer",
        help="How to handle missing difficulty groups for a concept.",
    )
    ap.add_argument(
        "--out-dir",
        default=None,
        help="Output directory (default: <experiments-dir>/comparative_analysis).",
    )
    ap.add_argument(
        "--out-prefix",
        default=None,
        help="Output filename prefix (default: capability_table_<phase>).",
    )
    ap.add_argument(
        "--title",
        default=None,
        help="Custom plot title.",
    )
    args = ap.parse_args()

    experiments_dir = os.path.abspath(str(args.experiments_dir))
    phase = str(args.phase)
    models = args.models if args.models else list(_iter_models_with_metrics(experiments_dir, phase))
    if not models:
        print(f"No models found under {experiments_dir} with average_metrics/{phase}/concept_metrics.json", file=sys.stderr)
        return 2

    # Stable ordering matching the paper table.
    ordered_models = [m for m in _DEFAULT_MODEL_ORDER if m in models] + sorted([m for m in models if m not in _DEFAULT_MODEL_ORDER])

    model_to_rows: Dict[str, List[Dict[str, Any]]] = {}
    for model in ordered_models:
        cm = _load_concept_mastery(experiments_dir, model, phase)
        model_to_rows[model] = _build_model_rows(cm, fill_missing=str(args.fill_missing))

    out_dir = os.path.abspath(str(args.out_dir)) if args.out_dir else os.path.join(experiments_dir, "comparative_analysis")
    os.makedirs(out_dir, exist_ok=True)
    prefix = str(args.out_prefix or f"capability_table_{phase}")
    out_base = os.path.join(out_dir, prefix)

    title = args.title or f"Model Capability Analysis by Concept and Difficulty ({phase})"
    _plot_capability_table_multi_model(model_to_rows=model_to_rows, out_base=out_base, title=title)

    print(f"Wrote: {out_base}.png/.svg/.pdf")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
