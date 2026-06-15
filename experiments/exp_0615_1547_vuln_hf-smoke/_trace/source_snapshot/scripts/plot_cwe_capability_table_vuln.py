# #!/usr/bin/env python3
# from __future__ import annotations

# import argparse
# import json
# import math
# import os
# import re
# from collections import Counter, defaultdict
# from dataclasses import dataclass
# from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


# _DIFF_ORDER = ["very easy", "easy", "medium", "hard", "very hard"]
# _DIFF_GROUPS: List[Tuple[str, List[str]]] = [
#     ("Very Easy/Easy", ["very easy", "easy"]),
#     ("Medium", ["medium"]),
#     ("Hard/Very Hard", ["hard", "very hard"]),
# ]


# def _norm_ws(s: Any) -> str:
#     return re.sub(r"\s+", " ", str(s or "").strip().lower())


# def _read_jsonl(path: str) -> Iterable[Dict[str, Any]]:
#     with open(path, "r", encoding="utf-8") as f:
#         for line in f:
#             line = line.strip()
#             if not line:
#                 continue
#             try:
#                 obj = json.loads(line)
#             except Exception:
#                 continue
#             if isinstance(obj, dict):
#                 yield obj


# def _difficulty_group(diff: str) -> Optional[str]:
#     d = _norm_ws(diff)
#     for name, diffs in _DIFF_GROUPS:
#         if d in diffs:
#             return name
#     return None


# def _find_phase_dirs(experiment_dir: str) -> Dict[str, str]:
#     root = os.path.abspath(str(experiment_dir))
#     if not os.path.isdir(root):
#         raise SystemExit(f"Not a directory: {root}")

#     out: Dict[str, str] = {}
#     for name in os.listdir(root):
#         p = os.path.join(root, name)
#         if not os.path.isdir(p):
#             continue
#         if name.startswith("PHASE_ONE_"):
#             out["phase1"] = p
#         elif name.startswith("PHASE_TWO_"):
#             out["phase2"] = p
#         elif name == "PHASE_THREE":
#             out["phase3"] = p
#     return out


# def _pipe_split(s: Any) -> List[str]:
#     if s is None:
#         return []
#     if isinstance(s, list):
#         return [str(x).strip() for x in s if str(x).strip()]
#     if not isinstance(s, str):
#         s = str(s)
#     return [x.strip() for x in (s or "").split("|") if x.strip()]


# def _canonical_cwe(cwe: str) -> Optional[str]:
#     text = str(cwe or "").strip().upper()
#     if not text:
#         return None
#     if text.startswith("CWE-"):
#         num = text[4:]
#         if num.isdigit():
#             return f"CWE-{int(num)}"
#     if text.isdigit():
#         return f"CWE-{int(text)}"
#     return text


# def _cwe_sort_key(cwe: str) -> Tuple[int, str]:
#     s = str(cwe or "").upper()
#     if s.startswith("CWE-"):
#         try:
#             return (int(s[4:]), s)
#         except Exception:
#             return (10**9, s)
#     return (10**9, s)


# @dataclass
# class RunRow:
#     model: str
#     phase: int
#     difficulty: str
#     cwes: List[str]
#     success: bool
#     attempts_till_success: int
#     total_issues: Optional[int]


# def _load_phase_runs(*, model: str, phase_dir: str) -> List[RunRow]:
#     path = os.path.join(os.path.abspath(phase_dir), "runs_index.jsonl")
#     if not os.path.exists(path):
#         return []
#     out: List[RunRow] = []
#     for rec in _read_jsonl(path):
#         phase = int(rec.get("phase") or 0)
#         diff = str(rec.get("difficulty") or "").strip() or "unknown"
#         concepts = _pipe_split(rec.get("concepts"))
#         # In vuln mode, concepts == target CWEs. Keep only CWE-like strings.
#         cwes: List[str] = []
#         for c in concepts:
#             cc = _canonical_cwe(c)
#             if cc and cc.upper().startswith("CWE-"):
#                 cwes.append(cc)
#         if not cwes:
#             continue
#         success = bool(rec.get("success"))
#         attempts = int(rec.get("attempts_till_success") or 1)
#         if attempts <= 0:
#             attempts = 1
#         total_issues = rec.get("total_issues")
#         try:
#             total_issues_i = int(total_issues) if total_issues is not None else None
#         except Exception:
#             total_issues_i = None
#         out.append(
#             RunRow(
#                 model=model,
#                 phase=phase,
#                 difficulty=diff,
#                 cwes=sorted(set(cwes), key=_cwe_sort_key),
#                 success=success,
#                 attempts_till_success=attempts,
#                 total_issues=total_issues_i,
#             )
#         )
#     return out


# def _ensure_matplotlib() -> Tuple[Any, Any]:
#     try:
#         import matplotlib
#         import matplotlib.pyplot as plt

#         return matplotlib, plt
#     except Exception as e:
#         raise SystemExit(
#             "matplotlib is required for plotting. "
#             "Run with the project venv, e.g. `./.venv/bin/python ...`. "
#             f"Error: {type(e).__name__}: {e}"
#         )


# def _save_fig(fig: Any, out_base: str) -> None:
#     for ext in ("png", "svg", "pdf"):
#         fig.savefig(
#             f"{out_base}.{ext}",
#             bbox_inches="tight",
#             dpi=300 if ext == "png" else None,
#         )


# def _contrast_text_color(rgb) -> str:
#     # rgb in 0..1
#     try:
#         r, g, b = float(rgb[0]), float(rgb[1]), float(rgb[2])
#     except Exception:
#         return "black"
#     # Relative luminance
#     lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
#     return "black" if lum > 0.55 else "white"


# def _primary_group_for_cwe(rows: Sequence[RunRow], cwe: str) -> Optional[str]:
#     counts = Counter()
#     for r in rows:
#         if cwe not in set(r.cwes):
#             continue
#         grp = _difficulty_group(r.difficulty)
#         if grp:
#             counts[grp] += 1
#     if not counts:
#         return None
#     # tie-break: prefer harder group
#     order = [g for g, _ in _DIFF_GROUPS]
#     return sorted(counts.items(), key=lambda kv: (kv[1], order.index(kv[0]) if kv[0] in order else -1), reverse=True)[0][0]


# def _compute_failure_rate_table(
#     *,
#     rows: Sequence[RunRow],
#     models: Sequence[str],
#     cwes: Sequence[str],
#     difficulty_group: str,
#     mode: str,
#     success_def: str,
# ) -> Tuple[List[List[float]], List[List[str]]]:
#     """
#     mode:
#       - marginal: a run contributes to every CWE in its target set
#       - single_only: keep only runs where len(cwes)==1
#       - exact_single: alias for single_only (kept for clarity)
#     """
#     mode = str(mode or "").strip().lower()
#     if mode in {"exact_single"}:
#         mode = "single_only"
#     if mode not in {"marginal", "single_only"}:
#         raise SystemExit(f"Unknown --mode: {mode}")

#     success_def = str(success_def or "").strip().lower()
#     if success_def not in {"final", "sast_clean", "one_shot"}:
#         raise SystemExit(f"Unknown --success-def: {success_def}")

#     # (model, cwe) -> Counter(runs/succ) for this group
#     cell: Dict[Tuple[str, str], Counter] = defaultdict(Counter)
#     for r in rows:
#         grp = _difficulty_group(r.difficulty)
#         if grp != difficulty_group:
#             continue
#         if mode == "single_only" and len(r.cwes) != 1:
#             continue
#         if success_def == "final":
#             succ = bool(r.success)
#         elif success_def == "sast_clean":
#             # Treat only SAST-clean outcomes as success (requires total_issues field).
#             succ = (r.total_issues == 0)
#         else:  # one_shot
#             # Prism-style capability mapping: only count success if it succeeds on the first attempt.
#             succ = bool(r.success) and int(r.attempts_till_success) == 1
#         for cwe in r.cwes:
#             cell[(r.model, cwe)]["runs"] += 1
#             cell[(r.model, cwe)]["succ"] += 1 if succ else 0

#     mat: List[List[float]] = []
#     txt: List[List[str]] = []
#     for cwe in cwes:
#         row_vals: List[float] = []
#         row_txt: List[str] = []
#         for model in models:
#             c = cell.get((model, cwe))
#             if not c or int(c.get("runs") or 0) <= 0:
#                 row_vals.append(math.nan)
#                 row_txt.append("")
#                 continue
#             runs_n = int(c.get("runs") or 0)
#             succ_n = int(c.get("succ") or 0)
#             fr = float(1.0 - (succ_n / runs_n)) if runs_n > 0 else 1.0
#             row_vals.append(fr)
#             if fr <= 0.0:
#                 row_txt.append("✓")
#             elif fr >= 1.0:
#                 row_txt.append("X")
#             else:
#                 row_txt.append(f"{fr:.2f}")
#         mat.append(row_vals)
#         txt.append(row_txt)
#     return mat, txt


# def _plot_table(
#     *,
#     rows: Sequence[RunRow],
#     models: Sequence[str],
#     cwes: Sequence[str],
#     out_base: str,
#     title: str,
#     mode: str,
#     success_def: str,
# ) -> None:
#     matplotlib, plt = _ensure_matplotlib()

#     # Determine primary group per CWE (across all models)
#     primary_group: Dict[str, Optional[str]] = {cwe: _primary_group_for_cwe(rows, cwe) for cwe in cwes}

#     # Layout: 3 blocks by difficulty group
#     fig, axes = plt.subplots(1, len(_DIFF_GROUPS), figsize=(6.2 * len(_DIFF_GROUPS) + 2.2, 0.42 * len(cwes) + 2.8), sharey=True)
#     if len(_DIFF_GROUPS) == 1:
#         axes = [axes]

#     try:
#         cmap = matplotlib.colormaps.get_cmap("RdYlGn_r").copy()  # type: ignore[attr-defined]
#     except Exception:
#         cmap = matplotlib.cm.get_cmap("RdYlGn_r").copy()
#     try:
#         cmap.set_bad(color="#eeeeee")
#     except Exception:
#         pass

#     for ax, (group_name, _diffs) in zip(axes, _DIFF_GROUPS):
#         mat, txt = _compute_failure_rate_table(
#             rows=rows,
#             models=models,
#             cwes=cwes,
#             difficulty_group=group_name,
#             mode=mode,
#             success_def=success_def,
#         )
#         im = ax.imshow(mat, aspect="auto", cmap=cmap, vmin=0.0, vmax=1.0)
#         ax.set_title(group_name, fontsize=12, fontweight="bold", pad=10)
#         ax.set_xticks(list(range(len(models))))
#         ax.set_xticklabels(models, rotation=0, fontsize=10)

#         if ax == axes[0]:
#             ax.set_yticks(list(range(len(cwes))))
#             ax.set_yticklabels(cwes, fontsize=10)
#             ax.set_ylabel("CWE", fontsize=12, fontweight="bold")
#         else:
#             ax.set_yticks(list(range(len(cwes))))
#             ax.set_yticklabels([])

#         # Grid
#         ax.set_xticks([x - 0.5 for x in range(1, len(models))], minor=True)
#         ax.set_yticks([y - 0.5 for y in range(1, len(cwes))], minor=True)
#         ax.grid(which="minor", color="white", linestyle="-", linewidth=1.5)
#         ax.tick_params(which="minor", bottom=False, left=False)

#         # Annotations
#         for y in range(len(cwes)):
#             cwe = cwes[y]
#             for x in range(len(models)):
#                 s = txt[y][x]
#                 if not s:
#                     continue
#                 if primary_group.get(cwe) == group_name and s:
#                     s = s + "†"
#                 v = mat[y][x]
#                 if isinstance(v, float) and math.isnan(v):
#                     color = "black"
#                 else:
#                     color = _contrast_text_color(cmap(v)[:3])  # type: ignore[index]
#                 ax.text(x, y, s, ha="center", va="center", fontsize=10, fontweight="bold", color=color)

#     fig.suptitle(title, fontsize=14, fontweight="bold", y=1.02)

#     # Colorbar
#     cax = fig.add_axes([0.92, 0.18, 0.015, 0.65])
#     fig.colorbar(im, cax=cax, label="Failure rate (1 - success rate)")
#     fig.subplots_adjust(left=0.22, right=0.90, top=0.86, bottom=0.12, wspace=0.08)

#     fig.text(
#         0.01,
#         0.01,
#         "Legend: ✓ mastered (no failures), X no success, † primary difficulty group (most runs).",
#         ha="left",
#         va="bottom",
#         fontsize=9,
#     )

#     _save_fig(fig, out_base)
#     plt.close(fig)


# def main() -> int:
#     ap = argparse.ArgumentParser(description="Prism-style CWE capability table (vuln mode): failure rate by difficulty group.")
#     ap.add_argument(
#         "--experiments",
#         nargs="+",
#         required=True,
#         help="One or more exp_*_vuln directories. Each is treated as a 'model' column.",
#     )
#     ap.add_argument(
#         "--labels",
#         nargs="*",
#         default=None,
#         help="Optional labels for --experiments (same length). Defaults to folder name.",
#     )
#     ap.add_argument("--phase", default="phase_1", choices=["phase_1", "phase_2", "phase_3", "all"], help="Which phase to use (default: phase_1).")
#     ap.add_argument("--mode", default="marginal", choices=["marginal", "single_only"], help="How to attribute runs to CWEs (default: marginal).")
#     ap.add_argument(
#         "--success-def",
#         default="final",
#         choices=["final", "sast_clean", "one_shot"],
#         help="What counts as 'success' for the rate: final=record.success; sast_clean=total_issues==0; one_shot=success and attempts_till_success==1.",
#     )
#     ap.add_argument("--top-cwes", type=int, default=30, help="Number of CWE rows to show (by support).")
#     ap.add_argument("--min-runs", type=int, default=5, help="Minimum runs required for a CWE to be included.")
#     ap.add_argument("--out-prefix", required=True, help="Output prefix (writes .png/.svg/.pdf).")
#     args = ap.parse_args()

#     exp_paths = [os.path.abspath(p) for p in args.experiments]
#     labels: List[str] = []
#     if args.labels:
#         if len(args.labels) != len(exp_paths):
#             raise SystemExit("--labels must have the same length as --experiments")
#         labels = [str(x) for x in args.labels]
#     else:
#         labels = [os.path.basename(p.rstrip(os.sep)) for p in exp_paths]

#     phase_filter: Optional[int]
#     if args.phase == "phase_1":
#         phase_filter = 1
#     elif args.phase == "phase_2":
#         phase_filter = 2
#     elif args.phase == "phase_3":
#         phase_filter = 3
#     else:
#         phase_filter = None

#     all_rows: List[RunRow] = []
#     for exp, label in zip(exp_paths, labels):
#         phase_dirs = _find_phase_dirs(exp)
#         # Always load all phase dirs that exist; filter by phase field.
#         for key in ("phase1", "phase2", "phase3"):
#             pdir = phase_dirs.get(key)
#             if not pdir:
#                 continue
#             all_rows.extend(_load_phase_runs(model=label, phase_dir=pdir))

#     if phase_filter is not None:
#         all_rows = [r for r in all_rows if int(r.phase) == int(phase_filter)]

#     if args.mode == "single_only":
#         all_rows = [r for r in all_rows if len(r.cwes) == 1]

#     if not all_rows:
#         raise SystemExit("No runs loaded (check --experiments path and that runs_index.jsonl exists).")

#     support = Counter()
#     for r in all_rows:
#         for c in r.cwes:
#             support[c] += 1

#     # filter + top-k
#     cwes = [c for c, n in support.items() if int(n) >= int(args.min_runs)]
#     cwes = sorted(cwes, key=lambda c: (-support[c], _cwe_sort_key(c)))
#     cwes = cwes[: max(1, int(args.top_cwes))]

#     if not cwes:
#         raise SystemExit("No CWEs meet --min-runs (try lowering it).")

#     title = f"CWE Capability Table — Failure rate by difficulty group ({args.phase}, mode={args.mode}, success={args.success_def})"
#     _plot_table(
#         rows=all_rows,
#         models=labels,
#         cwes=cwes,
#         out_base=str(args.out_prefix),
#         title=title,
#         mode=str(args.mode),
#         success_def=str(args.success_def),
#     )

#     print(f"Wrote: {args.out_prefix}.png/.svg/.pdf")
#     return 0


# if __name__ == "__main__":
#     raise SystemExit(main())

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import textwrap
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from scenario_conditions import axis_groups, axis_order, condition_axis_label, normalize_condition
from attack_surface_conditions import normalize_attack_surface, ordered_attack_surfaces

_DIFF_ORDER = list(axis_order())
_DIFF_GROUPS: List[Tuple[str, List[str]]] = list(axis_groups())
_ATTACK_SURFACE_ORDER = list(ordered_attack_surfaces())


def _norm_ws(s: Any) -> str:
    return re.sub(r"\s+", " ", str(s or "").strip().lower())


def _severity_key(label: Any) -> str:
    d = _norm_ws(label)
    if not d:
        return "unknown"
    return normalize_condition(d)


def _attack_surface_key(label: Any) -> str:
    d = _norm_ws(label)
    if not d:
        return "unknown"
    return normalize_attack_surface(d)


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


def _difficulty_group(diff: str) -> Optional[str]:
    group = condition_axis_label(_severity_key(diff))
    return group if group != "Unknown" else None


def _resolve_difficulty(rec: Dict[str, Any]) -> str:
    for key in ("difficulty_normalized", "condition_label", "difficulty"):
        value = rec.get(key)
        difficulty = _severity_key(value)
        if difficulty != "unknown":
            return difficulty
    return "unknown"


def _resolve_attack_surface(rec: Dict[str, Any]) -> str:
    for key in ("attack_surface", "difficulty", "condition_axis"):
        value = rec.get(key)
        surface = _attack_surface_key(value)
        if surface != "unknown":
            return surface
    return "unknown"


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
    return out


def _pipe_split(s: Any) -> List[str]:
    if s is None:
        return []
    if isinstance(s, list):
        return [str(x).strip() for x in s if str(x).strip()]
    if not isinstance(s, str):
        s = str(s)
    return [x.strip() for x in (s or "").split("|") if x.strip()]


def _canonical_cwe(cwe: str) -> Optional[str]:
    text = str(cwe or "").strip().upper()
    if not text:
        return None
    if text.startswith("CWE-"):
        num = text[4:]
        if num.isdigit():
            return f"CWE-{int(num)}"
    if text.isdigit():
        return f"CWE-{int(text)}"
    return text


def _cwe_sort_key(cwe: str) -> Tuple[int, str]:
    s = str(cwe or "").upper()
    if s.startswith("CWE-"):
        try:
            return (int(s[4:]), s)
        except Exception:
            return (10**9, s)
    return (10**9, s)


def _infer_run_id(rec: Dict[str, Any]) -> str:
    """
    Try hard to find a stable identifier for independent repeats (runs).
    Prism Table-2 style averages across independent runs.
    """
    for k in (
        "run_id",
        "trial_id",
        "replicate",
        "repeat",
        "seed",
        "rng_seed",
        "run",
        "fold",
    ):
        v = rec.get(k)
        if v is None:
            continue
        s = str(v).strip()
        if s:
            return s

    # Fallback: parse from common path-like fields if present
    for k in ("output_dir", "log_dir", "save_dir", "path", "file", "fname"):
        v = rec.get(k)
        if not v:
            continue
        s = str(v)
        m = re.search(r"(?:run|seed|trial)[_\-]([0-9]+)", s, flags=re.IGNORECASE)
        if m:
            return m.group(0)

    return "run_0"


@dataclass
class RunRow:
    model: str
    phase: int
    difficulty: str
    attack_surface: str
    cwes: List[str]
    success: bool
    attempts_till_success: int
    total_issues: Optional[int]
    run_id: str


def _load_phase_runs(*, model: str, phase_dir: str) -> List[RunRow]:
    path = os.path.join(os.path.abspath(phase_dir), "runs_index.jsonl")
    if not os.path.exists(path):
        return []
    out: List[RunRow] = []
    for rec in _read_jsonl(path):
        phase = int(rec.get("phase") or 0)
        diff = _resolve_difficulty(rec)
        attack_surface = _resolve_attack_surface(rec)
        concepts = _pipe_split(rec.get("concepts"))

        # In vuln mode, concepts == target CWEs. Keep only CWE-like strings.
        cwes: List[str] = []
        for c in concepts:
            cc = _canonical_cwe(c)
            if cc and cc.upper().startswith("CWE-"):
                cwes.append(cc)
        if not cwes:
            continue

        run_id = _infer_run_id(rec)

        success = bool(rec.get("success"))
        attempts = int(rec.get("attempts_till_success") or 1)
        if attempts <= 0:
            attempts = 1

        total_issues = rec.get("total_issues")
        try:
            total_issues_i = int(total_issues) if total_issues is not None else None
        except Exception:
            total_issues_i = None

        out.append(
            RunRow(
                model=model,
                phase=phase,
                difficulty=diff,
                attack_surface=attack_surface,
                cwes=sorted(set(cwes), key=_cwe_sort_key),
                success=success,
                attempts_till_success=attempts,
                total_issues=total_issues_i,
                run_id=run_id,
            )
        )
    return out


def _ensure_matplotlib() -> Tuple[Any, Any]:
    try:
        import matplotlib
        import matplotlib.pyplot as plt

        return matplotlib, plt
    except Exception as e:
        raise SystemExit(
            "matplotlib is required for plotting. "
            "Run with the project venv, e.g. `./.venv/bin/python ...`. "
            f"Error: {type(e).__name__}: {e}"
        )


def _save_fig(fig: Any, out_base: str) -> None:
    for ext in ("png", "svg", "pdf"):
        fig.savefig(
            f"{out_base}.{ext}",
            bbox_inches="tight",
            dpi=300 if ext == "png" else None,
        )


def _contrast_text_color(rgb) -> str:
    # rgb in 0..1
    try:
        r, g, b = float(rgb[0]), float(rgb[1]), float(rgb[2])
    except Exception:
        return "black"
    # Relative luminance
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return "black" if lum > 0.55 else "white"


def _group_order(group_by: str) -> List[str]:
    if group_by == "attack_surface":
        return list(_ATTACK_SURFACE_ORDER)
    return [g for g, _ in _DIFF_GROUPS]


def _group_label_for_row(row: RunRow, group_by: str) -> Optional[str]:
    if group_by == "attack_surface":
        return row.attack_surface if row.attack_surface != "unknown" else None
    return _difficulty_group(row.difficulty)


def _primary_group_for_cwe(rows: Sequence[RunRow], cwe: str, *, group_by: str) -> Optional[str]:
    counts = Counter()
    for r in rows:
        if cwe not in set(r.cwes):
            continue
        grp = _group_label_for_row(r, group_by)
        if grp:
            counts[grp] += 1
    if not counts:
        return None
    order = _group_order(group_by)
    return sorted(
        counts.items(),
        key=lambda kv: (kv[1], order.index(kv[0]) if kv[0] in order else -1),
        reverse=True,
    )[0][0]


def _compute_failure_rate_table(
    *,
    rows: Sequence[RunRow],
    models: Sequence[str],
    cwes: Sequence[str],
    group_value: str,
    group_by: str,
    mode: str,
    success_def: str,
) -> Tuple[List[List[float]], List[List[str]]]:
    """
    Prism-style:
      - compute failure rate per independent run (e.g., 3 repeats)
      - then average failure rates equally across runs (not weighted by run size)

    mode:
      - marginal: a run contributes to every CWE in its target set
      - single_only: keep only runs where len(cwes)==1

    success_def:
      - final: record.success
      - sast_clean: total_issues == 0
      - one_shot: success and attempts_till_success == 1
    """
    mode = str(mode or "").strip().lower()
    if mode in {"exact_single"}:
        mode = "single_only"
    if mode not in {"marginal", "single_only"}:
        raise SystemExit(f"Unknown --mode: {mode}")

    success_def = str(success_def or "").strip().lower()
    if success_def not in {"final", "sast_clean", "one_shot"}:
        raise SystemExit(f"Unknown --success-def: {success_def}")

    # (model, cwe, run_id) -> Counter(runs/succ) for this group
    by_run: Dict[Tuple[str, str, str], Counter] = defaultdict(Counter)

    for r in rows:
        grp = _group_label_for_row(r, group_by)
        if grp != group_value:
            continue
        if mode == "single_only" and len(r.cwes) != 1:
            continue

        if success_def == "final":
            succ = bool(r.success)
        elif success_def == "sast_clean":
            succ = (r.total_issues == 0)
        else:  # one_shot
            succ = bool(r.success) and int(r.attempts_till_success) == 1

        for cwe in r.cwes:
            key = (r.model, cwe, r.run_id)
            by_run[key]["runs"] += 1
            by_run[key]["succ"] += 1 if succ else 0

    mat: List[List[float]] = []
    txt: List[List[str]] = []

    for cwe in cwes:
        row_vals: List[float] = []
        row_txt: List[str] = []
        for model in models:
            frs: List[float] = []
            for (m, c, run_id), cnt in by_run.items():
                if m != model or c != cwe:
                    continue
                runs_n = int(cnt.get("runs") or 0)
                succ_n = int(cnt.get("succ") or 0)
                if runs_n <= 0:
                    continue
                frs.append(1.0 - (succ_n / runs_n))

            if not frs:
                row_vals.append(math.nan)
                row_txt.append("")
                continue

            fr = float(sum(frs) / len(frs))  # equal-weight mean across runs
            row_vals.append(fr)

            if fr <= 0.0:
                row_txt.append("✓")
            elif fr >= 1.0:
                row_txt.append("X")
            else:
                row_txt.append(f"{fr:.2f}")
        mat.append(row_vals)
        txt.append(row_txt)

    return mat, txt


def _wrap_group_title(value: str) -> str:
    text = str(value or "").strip()
    if len(text) <= 22:
        return text
    return textwrap.fill(text, width=22)


def _plot_table(
    *,
    rows: Sequence[RunRow],
    models: Sequence[str],
    cwes: Sequence[str],
    out_base: str,
    title: str,
    group_by: str,
    mode: str,
    success_def: str,
) -> None:
    matplotlib, plt = _ensure_matplotlib()

    groups = _group_order(group_by)
    primary_group: Dict[str, Optional[str]] = {
        cwe: _primary_group_for_cwe(rows, cwe, group_by=group_by) for cwe in cwes
    }

    row_fontsize = 10 if len(cwes) <= 22 else (9 if len(cwes) <= 32 else 8)
    cell_fontsize = 10 if len(cwes) <= 22 else (9 if len(cwes) <= 32 else 8)

    fig, all_axes = plt.subplots(
        1,
        len(groups) + 1,
        figsize=(4.9 * len(groups) + 3.8, 0.44 * len(cwes) + 3.0),
        sharey=False,
        gridspec_kw={
            "width_ratios": [1.45] + [4.9] * len(groups),
            "wspace": 0.08,
        },
    )
    if len(groups) == 1:
        label_ax = all_axes[0]
        axes = [all_axes[1]]
    else:
        label_ax = all_axes[0]
        axes = list(all_axes[1:])

    fig.patch.set_facecolor("white")
    single_model = len(models) == 1

    try:
        cmap = matplotlib.colormaps.get_cmap("RdYlGn_r").copy()  # type: ignore[attr-defined]
    except Exception:
        cmap = matplotlib.cm.get_cmap("RdYlGn_r").copy()
    try:
        cmap.set_bad(color="#eeeeee")
    except Exception:
        pass

    label_ax.set_xlim(0.0, 1.0)
    label_ax.set_ylim(len(cwes) - 0.5, -0.5)
    label_ax.set_facecolor("#fafafa")
    label_ax.set_xticks([])
    label_ax.set_yticks(list(range(len(cwes))))
    label_ax.set_yticklabels([])
    label_ax.tick_params(left=False, bottom=False)
    for spine in label_ax.spines.values():
        spine.set_visible(False)
    label_ax.set_title("CWE", fontsize=12, fontweight="bold", pad=10)
    for y, cwe in enumerate(cwes):
        label_ax.text(
            0.98,
            y,
            cwe,
            ha="right",
            va="center",
            fontsize=row_fontsize,
            fontweight="bold",
            color="#222222",
        )
    for y in range(1, len(cwes)):
        label_ax.axhline(y - 0.5, color="#e6e6e6", linewidth=1.0, zorder=0)

    im = None
    for ax, group_name in zip(axes, groups):
        mat, txt = _compute_failure_rate_table(
            rows=rows,
            models=models,
            cwes=cwes,
            group_value=group_name,
            group_by=group_by,
            mode=mode,
            success_def=success_def,
        )
        im = ax.imshow(mat, aspect="auto", cmap=cmap, vmin=0.0, vmax=1.0)
        ax.set_title(_wrap_group_title(group_name), fontsize=12, fontweight="bold", pad=10)
        ax.set_xticks(list(range(len(models))))
        if single_model:
            ax.set_xticklabels([])
        else:
            ax.set_xticklabels(models, rotation=0, fontsize=10)
        ax.tick_params(axis="x", length=0, pad=6)
        ax.set_yticks(list(range(len(cwes))))
        ax.set_yticklabels([])
        ax.tick_params(axis="y", length=0)

        ax.set_xticks([x - 0.5 for x in range(1, len(models))], minor=True)
        ax.set_yticks([y - 0.5 for y in range(1, len(cwes))], minor=True)
        ax.grid(which="minor", color="white", linestyle="-", linewidth=1.5)
        ax.tick_params(which="minor", bottom=False, left=False)
        for spine in ax.spines.values():
            spine.set_linewidth(0.8)
            spine.set_color("#444444")

        for y in range(len(cwes)):
            cwe = cwes[y]
            for x in range(len(models)):
                s = txt[y][x]
                if not s:
                    continue
                if primary_group.get(cwe) == group_name and s:
                    s = s + "†"
                v = mat[y][x]
                if isinstance(v, float) and math.isnan(v):
                    color = "black"
                else:
                    color = _contrast_text_color(cmap(v)[:3])  # type: ignore[index]
                ax.text(
                    x,
                    y,
                    s,
                    ha="center",
                    va="center",
                    fontsize=cell_fontsize,
                    fontweight="bold",
                    color=color,
                )

    fig.suptitle(title, fontsize=14, fontweight="bold", y=0.98)
    if single_model:
        fig.supxlabel(models[0], fontsize=11, fontweight="bold", y=0.07)

    if im is not None:
        cax = fig.add_axes([0.93, 0.19, 0.016, 0.62])
        fig.colorbar(im, cax=cax, label="Failure rate (1 - success rate)")

    fig.subplots_adjust(left=0.05, right=0.91, top=0.85, bottom=0.12, wspace=0.08)

    fig.text(
        0.01,
        0.01,
        f"Legend: ✓ mastered (no failures), X no success, † primary {'attack surface' if group_by == 'attack_surface' else 'difficulty group'} (most runs).",
        ha="left",
        va="bottom",
        fontsize=9,
    )

    _save_fig(fig, out_base)
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="CWE capability table (vuln mode): failure rate by attack surface or difficulty."
    )
    ap.add_argument(
        "--experiments",
        nargs="+",
        required=True,
        help="One or more exp_*_vuln directories. Each is treated as a 'model' column.",
    )
    ap.add_argument(
        "--labels",
        nargs="*",
        default=None,
        help="Optional labels for --experiments (same length). Defaults to folder name.",
    )
    ap.add_argument(
        "--phase",
        default="phase_1",
        choices=["phase_1", "phase_2", "phase_3", "all"],
        help="Which phase to use (default: phase_1).",
    )
    ap.add_argument(
        "--mode",
        default="marginal",
        choices=["marginal", "single_only"],
        help="How to attribute runs to CWEs (default: marginal).",
    )
    ap.add_argument(
        "--success-def",
        default="final",
        choices=["final", "sast_clean", "one_shot"],
        help="What counts as 'success' for the rate: final=record.success; sast_clean=total_issues==0; one_shot=success and attempts_till_success==1.",
    )
    ap.add_argument(
        "--group-by",
        default="attack_surface",
        choices=["difficulty", "attack_surface"],
        help="Panel grouping dimension (default: attack_surface).",
    )
    ap.add_argument("--top-cwes", type=int, default=30, help="Number of CWE rows to show (by support).")
    ap.add_argument("--min-runs", type=int, default=5, help="Minimum runs required for a CWE to be included.")
    ap.add_argument("--out-prefix", required=True, help="Output prefix (writes .png/.svg/.pdf).")
    args = ap.parse_args()

    exp_paths = [os.path.abspath(p) for p in args.experiments]
    labels: List[str] = []
    if args.labels:
        if len(args.labels) != len(exp_paths):
            raise SystemExit("--labels must have the same length as --experiments")
        labels = [str(x) for x in args.labels]
    else:
        labels = [os.path.basename(p.rstrip(os.sep)) for p in exp_paths]

    phase_filter: Optional[int]
    if args.phase == "phase_1":
        phase_filter = 1
    elif args.phase == "phase_2":
        phase_filter = 2
    elif args.phase == "phase_3":
        phase_filter = 3
    else:
        phase_filter = None

    all_rows: List[RunRow] = []
    for exp, label in zip(exp_paths, labels):
        phase_dirs = _find_phase_dirs(exp)
        for key in ("phase1", "phase2", "phase3"):
            pdir = phase_dirs.get(key)
            if not pdir:
                continue
            all_rows.extend(_load_phase_runs(model=label, phase_dir=pdir))

    if phase_filter is not None:
        all_rows = [r for r in all_rows if int(r.phase) == int(phase_filter)]

    if args.mode == "single_only":
        all_rows = [r for r in all_rows if len(r.cwes) == 1]

    if not all_rows:
        raise SystemExit("No runs loaded (check --experiments path and that runs_index.jsonl exists).")

    if args.group_by == "attack_surface":
        all_rows = [r for r in all_rows if r.attack_surface != "unknown"]
        if not all_rows:
            raise SystemExit("No runs with attack_surface metadata found for --group-by attack_surface.")

    support = Counter()
    for r in all_rows:
        for c in r.cwes:
            support[c] += 1

    cwes = [c for c, n in support.items() if int(n) >= int(args.min_runs)]
    cwes = sorted(cwes, key=lambda c: (-support[c], _cwe_sort_key(c)))
    cwes = cwes[: max(1, int(args.top_cwes))]

    if not cwes:
        raise SystemExit("No CWEs meet --min-runs (try lowering it).")

    title = (
        f"CWE Capability Table — Failure rate by "
        f"{'attack surface' if args.group_by == 'attack_surface' else 'difficulty'} "
        f"({args.phase}, mode={args.mode}, success={args.success_def})"
    )
    _plot_table(
        rows=all_rows,
        models=labels,
        cwes=cwes,
        out_base=str(args.out_prefix),
        title=title,
        group_by=str(args.group_by),
        mode=str(args.mode),
        success_def=str(args.success_def),
    )

    print(f"Wrote: {args.out_prefix}.png/.svg/.pdf")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
