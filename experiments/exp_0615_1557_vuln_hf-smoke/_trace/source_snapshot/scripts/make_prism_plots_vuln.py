#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import shutil
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from scenario_conditions import axis_groups, axis_order, normalize_condition

_DIFF_ORDER = list(axis_order())
_DIFF_TO_ORD = {d: i for i, d in enumerate(_DIFF_ORDER)}
_DIFF_GROUPS: List[Tuple[str, List[str]]] = list(axis_groups())


def _norm_ws(s: Any) -> str:
    return re.sub(r"\s+", " ", str(s or "").strip().lower())


def _severity_key(label: Any) -> str:
    d = _norm_ws(label)
    if not d:
        return "unknown"
    return normalize_condition(d)


def _project_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))


def _read_jsonl(path: str) -> Iterable[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if isinstance(obj, dict):
                yield obj


def _read_csv(path: str) -> List[Dict[str, Any]]:
    with open(path, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        return [row for row in r if isinstance(row, dict)]


def _safe_int(x: Any, default: int = 0) -> int:
    try:
        return int(x)
    except Exception:
        try:
            return int(float(x))
        except Exception:
            return int(default)


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return float(default)


def _difficulty_group(diff: str) -> Optional[str]:
    d = _severity_key(diff)
    return d if d != "unknown" else None


def _difficulty_ord(diff: str) -> Optional[int]:
    grp = _difficulty_group(diff)
    if grp in _DIFF_TO_ORD:
        return int(_DIFF_TO_ORD[grp])
    return None


def _pipe_split(s: Any) -> List[str]:
    if s is None:
        return []
    if isinstance(s, list):
        return [str(x).strip() for x in s if str(x).strip()]
    if not isinstance(s, str):
        s = str(s)
    return [x.strip() for x in (s or "").split("|") if x.strip()]


def _combo_key(concepts: Sequence[str]) -> str:
    # Stable combination signature.
    items = sorted({str(c).strip() for c in concepts if str(c).strip()})
    return "+".join(items) if items else "UNKNOWN"


def _find_phase_dirs(experiment_dir: str) -> Dict[str, str]:
    root = os.path.abspath(str(experiment_dir))
    if not os.path.isdir(root):
        raise SystemExit(f"Not a directory: {root}")

    out: Dict[str, str] = {}
    for name in os.listdir(root):
        p = os.path.join(root, name)
        if not os.path.isdir(p):
            continue
        if name.startswith("PHASE_ONE_"):
            out["phase1"] = p
        elif name.startswith("PHASE_TWO_"):
            out["phase2"] = p
        elif name == "PHASE_THREE":
            out["phase3"] = p
    if "phase3" not in out:
        raise SystemExit(f"Could not find PHASE_THREE under: {root}")
    return out


@dataclass
class RunIndexRow:
    phase: int
    difficulty: str
    concepts: List[str]
    success: bool


def _load_runs_index(phase_dir: str) -> List[RunIndexRow]:
    path = os.path.join(os.path.abspath(phase_dir), "runs_index.jsonl")
    if not os.path.exists(path):
        return []
    out: List[RunIndexRow] = []
    for rec in _read_jsonl(path):
        try:
            phase = _safe_int(rec.get("phase") or 0, default=0)
            diff = _severity_key(rec.get("difficulty"))
            concepts = rec.get("concepts")
            concepts_list = _pipe_split(concepts)
            success = bool(rec.get("success"))
        except Exception:
            continue
        out.append(RunIndexRow(phase=phase, difficulty=diff, concepts=concepts_list, success=success))
    return out


def _load_tree_growth_points(phase_dir: str) -> List[Dict[str, Any]]:
    """
    Load all tree_*.pkl snapshots in a PHASE_* directory and compute simple growth stats.
    """
    root = os.path.abspath(phase_dir)
    paths = []
    for name in os.listdir(root):
        if not (name.startswith("tree_") and name.endswith(".pkl")):
            continue
        if name.endswith("_phases.pkl"):
            continue
        paths.append(os.path.join(root, name))
    # Prefer numeric order when possible (tree_10.pkl, tree_20.pkl, ...).
    def _snap_key(p: str) -> Tuple[int, str]:
        base = os.path.basename(p)
        m = re.match(r"tree_(\\d+)\\.pkl$", base)
        if m:
            return (int(m.group(1)), base)
        if base == "tree_final.pkl":
            return (10**9, base)
        return (10**8, base)

    paths.sort(key=_snap_key)

    # Ensure node module is importable for pickle loads.
    src = os.path.join(_project_root(), "src")
    if src not in sys.path:
        sys.path.insert(0, src)

    import pickle  # local import (pickle requires src on sys.path)

    points: List[Dict[str, Any]] = []
    for p in paths:
        try:
            with open(p, "rb") as f:
                nodes = pickle.load(f)
        except Exception:
            continue
        nodes_list = nodes if isinstance(nodes, list) else []
        children_counts: List[int] = []
        leaf_nodes = 0
        max_depth = 0
        for n in nodes_list:
            depth = _safe_int(getattr(n, "depth", 0) or 0, default=0)
            if depth > max_depth:
                max_depth = depth
            child_list = getattr(n, "children", None) or []
            if not isinstance(child_list, list):
                child_list = []
            children_counts.append(len(child_list))
            if not child_list:
                leaf_nodes += 1
        edges = sum(children_counts)
        points.append(
            {
                "snapshot": os.path.basename(p).replace(".pkl", ""),
                "nodes_total": len(nodes_list),
                "edges_total": edges,
                "leaf_nodes": leaf_nodes,
                "max_depth": max_depth,
                "avg_branching_factor": (edges / len(nodes_list)) if nodes_list else 0.0,
            }
        )
    return points


def _ensure_matplotlib() -> Tuple[Any, Any]:
    try:
        import matplotlib
        import matplotlib.pyplot as plt

        return matplotlib, plt
    except Exception as e:
        raise SystemExit(
            "matplotlib is required for plotting. "
            "Run with the project venv, e.g. `pack/.venv/bin/python ...`. "
            f"Error: {type(e).__name__}: {e}"
        )


def _save_fig(fig: Any, out_base: str) -> None:
    for ext in ("png", "svg", "pdf"):
        fig.savefig(
            f"{out_base}.{ext}",
            bbox_inches="tight",
            dpi=300 if ext == "png" else None,
        )


def _plot_exploration_timeline(
    *,
    runs: List[RunIndexRow],
    out_base: str,
    title: str,
) -> None:
    matplotlib, plt = _ensure_matplotlib()

    phase_colors = {1: "#1f77b4", 2: "#ff7f0e", 3: "#2ca02c"}
    xs_succ: List[int] = []
    ys_succ: List[float] = []
    cs_succ: List[str] = []
    xs_fail: List[int] = []
    ys_fail: List[float] = []
    cs_fail: List[str] = []

    for i, r in enumerate(runs, start=1):
        ord_ = _difficulty_ord(r.difficulty)
        if ord_ is None:
            continue
        # Small vertical jitter to reduce overplotting.
        y = float(ord_) + (0.08 if r.success else -0.08)
        c = phase_colors.get(int(r.phase) or 0, "#7f7f7f")
        if r.success:
            xs_succ.append(i)
            ys_succ.append(y)
            cs_succ.append(c)
        else:
            xs_fail.append(i)
            ys_fail.append(y)
            cs_fail.append(c)

    fig, ax = plt.subplots(figsize=(14, 4.8))
    ax.scatter(xs_succ, ys_succ, c=cs_succ, s=18, marker="o", alpha=0.55, edgecolors="none", label="Success")
    ax.scatter(xs_fail, ys_fail, c=cs_fail, s=22, marker="x", alpha=0.85, label="Failure")

    ax.set_title(title, fontsize=13, fontweight="bold", pad=10)
    ax.set_xlabel("Run index (chronological, phase1 → phase2 → phase3)")
    ax.set_ylabel("Attack Surface")
    ax.set_yticks(list(range(len(_DIFF_ORDER))))
    ax.set_yticklabels(_DIFF_ORDER)
    ax.grid(True, axis="y", linestyle="--", alpha=0.25)

    # Phase legend
    from matplotlib.lines import Line2D

    handles = [
        Line2D([0], [0], marker="o", color="w", markerfacecolor=phase_colors[1], markersize=8, label="Phase 1"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor=phase_colors[2], markersize=8, label="Phase 2"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor=phase_colors[3], markersize=8, label="Phase 3"),
        Line2D([0], [0], marker="o", color="black", markersize=7, linestyle="None", label="Success"),
        Line2D([0], [0], marker="x", color="black", markersize=7, linestyle="None", label="Failure"),
    ]
    ax.legend(handles=handles, loc="upper right", frameon=True, framealpha=0.95)

    fig.tight_layout()
    _save_fig(fig, out_base)
    plt.close(fig)


def _plot_tree_growth(
    *,
    phase_to_points: Dict[str, List[Dict[str, Any]]],
    out_base: str,
    title: str,
) -> None:
    matplotlib, plt = _ensure_matplotlib()

    fig, axes = plt.subplots(3, 1, figsize=(12.5, 8.2), sharex=False)
    metrics = [
        ("nodes_total", "Nodes"),
        ("max_depth", "Max depth"),
        ("avg_branching_factor", "Avg branching"),
    ]
    phase_label = {"phase1": "Phase 1", "phase2": "Phase 2", "phase3": "Phase 3"}
    phase_color = {"phase1": "#1f77b4", "phase2": "#ff7f0e", "phase3": "#2ca02c"}

    for ax, (key, ylab) in zip(axes, metrics):
        for ph, pts in phase_to_points.items():
            if not pts:
                continue
            xs = list(range(1, len(pts) + 1))
            ys = [_safe_float(p.get(key), default=0.0) for p in pts]
            ax.plot(xs, ys, marker="o", linewidth=2.0, markersize=4.0, color=phase_color.get(ph, "#7f7f7f"), label=phase_label.get(ph, ph))
        ax.set_ylabel(ylab)
        ax.grid(True, linestyle="--", alpha=0.25)
        if key == "avg_branching_factor":
            ax.set_ylim(bottom=0.0)

    axes[0].set_title(title, fontsize=13, fontweight="bold", pad=10)
    axes[-1].set_xlabel("Snapshot index within phase (tree_*.pkl order)")
    axes[0].legend(loc="upper left", frameon=True, framealpha=0.95)

    fig.tight_layout()
    _save_fig(fig, out_base)
    plt.close(fig)


def _plot_frontier_heatmap_top_combos(
    *,
    runs: List[RunIndexRow],
    out_base: str,
    title: str,
    top_n: int = 25,
) -> None:
    matplotlib, plt = _ensure_matplotlib()

    # Aggregate success by (combo, difficulty)
    counts: Dict[Tuple[str, str], Counter] = defaultdict(Counter)
    combo_runs = Counter()
    for r in runs:
        diff = _severity_key(r.difficulty)
        if diff not in _DIFF_TO_ORD:
            continue
        combo = _combo_key(r.concepts)
        combo_runs[combo] += 1
        counts[(combo, diff)]["runs"] += 1
        counts[(combo, diff)]["succ"] += 1 if r.success else 0

    combos = [c for c, _n in combo_runs.most_common(max(1, int(top_n)))]
    diffs = list(_DIFF_ORDER)

    mat: List[List[float]] = []
    txt: List[List[str]] = []
    primary_diff: Dict[str, str] = {}

    # Compute primary attack surface per combo (most runs).
    for combo in combos:
        group_counts = Counter()
        for d in diffs:
            cell = counts.get((combo, d))
            if not cell:
                continue
            group = _difficulty_group(d)
            if group:
                group_counts[group] += int(cell.get("runs") or 0)
        if group_counts:
            # Tie-break: prefer harder group if equal counts.
            order = [g for g, _ in _DIFF_GROUPS]
            primary = sorted(group_counts.items(), key=lambda kv: (kv[1], order.index(kv[0]) if kv[0] in order else -1), reverse=True)[0][0]
            primary_diff[combo] = primary

    for combo in combos:
        row_vals: List[float] = []
        row_txt: List[str] = []
        for d in diffs:
            cell = counts.get((combo, d))
            if not cell or int(cell.get("runs") or 0) <= 0:
                row_vals.append(math.nan)
                row_txt.append("")
                continue
            runs_n = int(cell.get("runs") or 0)
            succ_n = int(cell.get("succ") or 0)
            sr = float(succ_n) / float(runs_n) if runs_n > 0 else 0.0
            fr = float(1.0 - sr)
            row_vals.append(fr)

            if fr <= 0.0:
                s = "✓"
            elif fr >= 1.0:
                s = "X"
            else:
                s = f"{fr:.2f}"

            grp = _difficulty_group(d)
            if grp and primary_diff.get(combo) == grp and s:
                s += "†"
            row_txt.append(s)
        mat.append(row_vals)
        txt.append(row_txt)

    try:
        cmap = matplotlib.colormaps.get_cmap("RdYlGn_r").copy()  # type: ignore[attr-defined]
    except Exception:
        cmap = matplotlib.cm.get_cmap("RdYlGn_r").copy()
    try:
        cmap.set_bad(color="#eeeeee")
    except Exception:
        pass

    fig_w = max(11.5, 1.0 * len(diffs) + 7.0)
    fig_h = max(6.0, 0.33 * len(combos) + 2.6)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    im = ax.imshow(mat, aspect="auto", cmap=cmap, vmin=0.0, vmax=1.0)

    ax.set_title(title, fontsize=13, fontweight="bold", pad=10)
    ax.set_xlabel("Attack Surface")
    ax.set_ylabel("Top concept combinations (by runs)")
    ax.set_xticks(list(range(len(diffs))))
    ax.set_xticklabels(diffs, rotation=0)
    ax.set_yticks(list(range(len(combos))))
    ax.set_yticklabels(combos, fontsize=9)

    # Gridlines
    ax.set_xticks([x - 0.5 for x in range(len(diffs) + 1)], minor=True)
    ax.set_yticks([y - 0.5 for y in range(len(combos) + 1)], minor=True)
    ax.grid(which="minor", color="white", linestyle="-", linewidth=1.0)
    ax.tick_params(which="minor", bottom=False, left=False)

    # Annotations with contrast-aware color.
    for y in range(len(combos)):
        for x in range(len(diffs)):
            s = txt[y][x]
            if not s:
                continue
            try:
                fv = float(mat[y][x])
            except Exception:
                fv = math.nan
            color = "black"
            if not math.isnan(fv):
                try:
                    r, g_, b, _a = cmap(float(fv))
                    lum = 0.299 * float(r) + 0.587 * float(g_) + 0.114 * float(b)
                    color = "white" if lum < 0.55 else "black"
                except Exception:
                    color = "black"
            ax.text(x, y, s, ha="center", va="center", fontsize=9, fontweight="bold", color=color)

    # Colorbar
    cax = fig.add_axes([0.92, 0.18, 0.015, 0.65])
    fig.colorbar(im, cax=cax, label="Failure rate (1 - success rate)")
    fig.subplots_adjust(left=0.18, right=0.90, top=0.88, bottom=0.10)

    fig.text(
        0.01,
        0.01,
        "Legend: ✓ mastered (no failures), X no success, † primary attack surface (most runs).",
        ha="left",
        va="bottom",
        fontsize=9,
    )

    _save_fig(fig, out_base)
    plt.close(fig)


def _plot_failure_reasons_by_difficulty(
    *,
    failure_rows: List[Dict[str, Any]],
    out_base: str,
    title: str,
    top_k: int = 8,
) -> None:
    matplotlib, plt = _ensure_matplotlib()

    # Only failures.
    rows = [r for r in failure_rows if str(r.get("success") or "").strip().lower() in {"false", "0"}]
    if not rows:
        return

    # attack surface -> reason -> count
    counts: Dict[str, Counter] = defaultdict(Counter)
    for r in rows:
        diff = _severity_key(r.get("difficulty"))
        grp = _difficulty_group(diff) or "Unknown"
        reason = str(r.get("primary_reason") or "").strip() or "unknown"
        counts[grp][reason] += 1

    # Keep groups in stable order.
    groups = [g for g, _ in _DIFF_GROUPS] + [g for g in sorted(counts.keys()) if g not in {x for x, _ in _DIFF_GROUPS}]

    # Top reasons overall.
    total = Counter()
    for g in groups:
        total.update(counts.get(g, Counter()))
    top = [r for r, _n in total.most_common(max(1, int(top_k)))]

    # Build stacked bars: top reasons + "other".
    series: Dict[str, List[int]] = {}
    for reason in top:
        series[reason] = [int(counts.get(g, Counter()).get(reason) or 0) for g in groups]
    other = []
    for g in groups:
        c = counts.get(g, Counter())
        other.append(int(sum(v for k, v in c.items() if k not in top)))
    series["other"] = other

    # Colors (categorical)
    palette = [
        "#d62728",
        "#ff7f0e",
        "#bcbd22",
        "#9467bd",
        "#8c564b",
        "#e377c2",
        "#7f7f7f",
        "#17becf",
        "#1f77b4",
    ]

    fig, ax = plt.subplots(figsize=(12.5, 5.2))
    bottom = [0] * len(groups)
    for i, (reason, vals) in enumerate(series.items()):
        ax.bar(groups, vals, bottom=bottom, label=reason, color=palette[i % len(palette)], edgecolor="white", linewidth=0.5)
        bottom = [b + int(v) for b, v in zip(bottom, vals)]

    ax.set_title(title, fontsize=13, fontweight="bold", pad=10)
    ax.set_ylabel("Failure count")
    ax.set_xlabel("Attack Surface")
    ax.grid(True, axis="y", linestyle="--", alpha=0.25)
    ax.legend(loc="upper right", frameon=True, framealpha=0.95, fontsize=9)
    fig.tight_layout()

    _save_fig(fig, out_base)
    plt.close(fig)


def _plot_persistent_tests_by_difficulty(
    *,
    failure_rows: List[Dict[str, Any]],
    out_base: str,
    title: str,
    top_k: int = 15,
) -> None:
    matplotlib, plt = _ensure_matplotlib()

    rows = [r for r in failure_rows if str(r.get("success") or "").strip().lower() in {"false", "0"}]
    if not rows:
        return

    # attack surface -> test_id -> count
    counts: Dict[str, Counter] = defaultdict(Counter)
    total = Counter()
    for r in rows:
        diff = _severity_key(r.get("difficulty"))
        grp = _difficulty_group(diff) or "Unknown"
        tests = str(r.get("persistent_test_ids") or "").strip()
        ids = [t for t in tests.split("|") if t.strip()]
        for tid in ids:
            t = str(tid).strip()
            if not t:
                continue
            counts[grp][t] += 1
            total[t] += 1

    top_tests = [t for t, _n in total.most_common(max(1, int(top_k)))]
    groups = [g for g, _ in _DIFF_GROUPS] + [g for g in sorted(counts.keys()) if g not in {x for x, _ in _DIFF_GROUPS}]

    mat: List[List[float]] = []
    for t in top_tests:
        mat.append([float(counts.get(g, Counter()).get(t) or 0) for g in groups])

    try:
        cmap = matplotlib.colormaps.get_cmap("YlOrRd").copy()  # type: ignore[attr-defined]
    except Exception:
        cmap = matplotlib.cm.get_cmap("YlOrRd").copy()

    fig_h = max(5.0, 0.35 * len(top_tests) + 2.2)
    fig, ax = plt.subplots(figsize=(11.5, fig_h))
    im = ax.imshow(mat, aspect="auto", cmap=cmap)

    ax.set_title(title, fontsize=13, fontweight="bold", pad=10)
    ax.set_xlabel("Attack Surface")
    ax.set_ylabel("Persistent SAST tests (top)")
    ax.set_xticks(list(range(len(groups))))
    ax.set_xticklabels(groups, rotation=0)
    ax.set_yticks(list(range(len(top_tests))))
    ax.set_yticklabels(top_tests, fontsize=9)

    # annotate counts
    for y in range(len(top_tests)):
        for x in range(len(groups)):
            v = mat[y][x]
            if v <= 0:
                continue
            ax.text(x, y, str(int(v)), ha="center", va="center", fontsize=9, fontweight="bold", color="black")

    cax = fig.add_axes([0.92, 0.18, 0.015, 0.65])
    fig.colorbar(im, cax=cax, label="Count")
    fig.subplots_adjust(left=0.25, right=0.90, top=0.88, bottom=0.10)

    _save_fig(fig, out_base)
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate a small Prism-style plot set for vulnerability-mode experiments.")
    ap.add_argument("--experiment-dir", required=True, help="Path to an exp_*_vuln directory containing PHASE_* subfolders.")
    ap.add_argument("--out-dir", default=None, help="Output directory (default: <PHASE_THREE>/analysis/prism_plots).")
    ap.add_argument("--top-combos", type=int, default=25, help="Top combinations to show in the frontier heatmap.")
    ap.add_argument("--top-failure-reasons", type=int, default=8, help="Top failure reasons for the stacked bar plot.")
    ap.add_argument("--top-persistent-tests", type=int, default=15, help="Top persistent SAST tests for the heatmap.")
    ap.add_argument(
        "--curate",
        action="store_true",
        help="Archive the noisy vuln_report plot folder and keep only a small curated set (Prism-style + a few legacy matrices).",
    )
    ap.add_argument(
        "--keep-legacy",
        nargs="*",
        default=[
            "matrix_combo_success_rate_top_cwes",
            "matrix_combo_avg_risk_top_cwes",
            "matrix_combo_visits_top_cwes",
            "matrix_combo_run_count_top_cwes",
        ],
        help="Extra plot basenames to keep from <PHASE_THREE>/analysis/plots (copied into the curated plots folder).",
    )
    args = ap.parse_args()

    phase_dirs = _find_phase_dirs(str(args.experiment_dir))
    phase1 = phase_dirs.get("phase1")
    phase2 = phase_dirs.get("phase2")
    phase3 = phase_dirs["phase3"]

    out_dir = os.path.abspath(str(args.out_dir)) if args.out_dir else os.path.join(phase3, "analysis", "prism_plots")
    os.makedirs(out_dir, exist_ok=True)

    # 1) Exploration timeline (uses runs_index.jsonl in each phase)
    runs: List[RunIndexRow] = []
    if phase1:
        runs.extend(_load_runs_index(phase1))
    if phase2:
        runs.extend(_load_runs_index(phase2))
    runs.extend(_load_runs_index(phase3))

    if runs:
        _plot_exploration_timeline(
            runs=runs,
            out_base=os.path.join(out_dir, "exploration_timeline"),
            title="MCTS exploration over time (difficulty × phase)",
        )
        _plot_frontier_heatmap_top_combos(
            runs=runs,
            out_base=os.path.join(out_dir, "capability_frontier_top_combos"),
            title=f"Capability frontier (top combos) — failure rate by difficulty (n={int(args.top_combos)})",
            top_n=int(args.top_combos),
        )

    # 2) Tree growth across snapshots (one plot with 3 subplots)
    phase_to_points: Dict[str, List[Dict[str, Any]]] = {}
    if phase1:
        phase_to_points["phase1"] = _load_tree_growth_points(phase1)
    if phase2:
        phase_to_points["phase2"] = _load_tree_growth_points(phase2)
    phase_to_points["phase3"] = _load_tree_growth_points(phase3)

    if any(phase_to_points.values()):
        _plot_tree_growth(
            phase_to_points=phase_to_points,
            out_base=os.path.join(out_dir, "tree_growth"),
            title="MCTS tree growth (snapshots): nodes, depth, branching",
        )

    # 3) Root-cause plots from failure_patterns.csv (requires PHASE_THREE analysis outputs)
    fp_csv = os.path.join(phase3, "analysis", "failure_patterns.csv")
    if os.path.exists(fp_csv):
        fp_rows = _read_csv(fp_csv)
        _plot_failure_reasons_by_difficulty(
            failure_rows=fp_rows,
            out_base=os.path.join(out_dir, "failures_by_reason_and_axis"),
            title="Root causes: failure reasons by difficulty",
            top_k=int(args.top_failure_reasons),
        )
        _plot_persistent_tests_by_difficulty(
            failure_rows=fp_rows,
            out_base=os.path.join(out_dir, "persistent_sast_tests_by_axis"),
            title="Root causes: persistent SAST tests by difficulty",
            top_k=int(args.top_persistent_tests),
        )

    if args.curate:
        phase3_analysis = os.path.join(phase3, "analysis")
        legacy_plots_dir = os.path.join(phase3_analysis, "plots")
        prism_plots_dir = out_dir

        curated_plots_dir = legacy_plots_dir
        archive_dir = None
        if os.path.isdir(legacy_plots_dir):
            suffix = time.strftime("%Y%m%d_%H%M%S")
            archive_dir = os.path.join(phase3_analysis, f"plots_full_{suffix}")
            shutil.move(legacy_plots_dir, archive_dir)
        os.makedirs(curated_plots_dir, exist_ok=True)

        def _copy_family(src_dir: str, base: str) -> List[str]:
            copied: List[str] = []
            for ext in ("png", "svg", "pdf"):
                src = os.path.join(src_dir, f"{base}.{ext}")
                if not os.path.exists(src):
                    continue
                dst = os.path.join(curated_plots_dir, f"{base}.{ext}")
                shutil.copy2(src, dst)
                copied.append(os.path.basename(dst))
            return copied

        kept: Dict[str, List[str]] = {"prism": [], "legacy": []}
        missing: Dict[str, List[str]] = {"prism": [], "legacy": []}
        copied_files: List[str] = []

        prism_bases = [
            "exploration_timeline",
            "tree_growth",
            "capability_frontier_top_combos",
            "failures_by_reason_and_axis",
            "persistent_sast_tests_by_axis",
        ]
        for base in prism_bases:
            got = _copy_family(prism_plots_dir, base)
            if got:
                kept["prism"].append(base)
                copied_files.extend(got)
            else:
                missing["prism"].append(base)

        if archive_dir:
            for base in [str(b).strip() for b in (args.keep_legacy or []) if str(b).strip()]:
                got = _copy_family(archive_dir, base)
                if got:
                    kept["legacy"].append(base)
                    copied_files.extend(got)
                else:
                    missing["legacy"].append(base)

        readme_path = os.path.join(curated_plots_dir, "README.md")
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write("# Curated plots (Prism-style)\n\n")
            f.write("This folder is intentionally **small** and paper-ready.\n\n")
            f.write("## Mapping to research questions\n")
            f.write("- Dynamic/adaptive benchmark & MCTS exploration: `exploration_timeline`, `tree_growth`\n")
            f.write("- Capability frontier: `capability_frontier_top_combos`\n")
            f.write("- Root-cause analysis: `failures_by_reason_and_axis`, `persistent_sast_tests_by_axis`\n")
            if kept["legacy"]:
                f.write("- CWE interaction matrices (legacy): " + ", ".join(f"`{b}`" for b in kept["legacy"]) + "\n")
            f.write("\n")
            if archive_dir:
                f.write(f"Full (noisy) plot set archived at: `{archive_dir}`\n")

        manifest = {
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "experiment_dir": os.path.abspath(str(args.experiment_dir)),
            "phase3_dir": phase3,
            "prism_plots_dir": prism_plots_dir,
            "curated_plots_dir": curated_plots_dir,
            "archived_legacy_plots_dir": archive_dir,
            "kept_bases": kept,
            "missing_bases": missing,
            "copied_files": sorted(set(copied_files)),
        }
        with open(os.path.join(curated_plots_dir, "curation_manifest.json"), "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, sort_keys=True)

        print(f"Wrote curated plots to: {curated_plots_dir}")
        if archive_dir:
            print(f"Archived full plots to: {archive_dir}")

    print(f"Wrote Prism-style plots to: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
