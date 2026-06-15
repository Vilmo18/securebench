from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, Normalize
from matplotlib.patches import Rectangle


ROOT = Path("/home/kira/pack")
OUT_DIR = ROOT / "research_questions" / "figures"
SVG_OUT_PATH = OUT_DIR / "three_model_cwe_surface_failure_rate.svg"
PNG_OUT_PATH = OUT_DIR / "three_model_cwe_surface_failure_rate.png"

RUNS = {
    "CL": ROOT / "experiments" / "exp_0412_0914_vuln" / "PHASE_ONE_5" / "analysis" / "records.csv",
    "QW": ROOT / "experiments" / "exp_0412_1505_vuln" / "PHASE_ONE_5" / "analysis" / "records.csv",
    "GR": ROOT / "experiments" / "exp_0412_1918_vuln" / "PHASE_ONE_5" / "analysis" / "records.csv",
}

SURFACES = [
    "User Inputs & Data",
    "Web Outputs & Rendering",
    "Storage & Filesystem",
    "Authentication & Access Control",
    "Data Exchange & External Services",
    "Execution Environment & Infrastructure",
]

SURFACE_LABELS = {
    "User Inputs & Data": "User Inputs & Data",
    "Web Outputs & Rendering": "Web Outputs &\nRendering",
    "Storage & Filesystem": "Storage & Filesystem",
    "Authentication & Access Control": "Authentication &\nAccess Control",
    "Data Exchange & External Services": "Data Exchange &\nExternal Services",
    "Execution Environment & Infrastructure": "Execution Environment &\nInfrastructure",
}

CWES = ["CWE-20", "CWE-22", "CWE-78", "CWE-79", "CWE-89", "CWE-287", "CWE-502"]

MODELS = ["CL", "QW", "GR"]
MODEL_LABELS = {"CL": "CL", "QW": "QW", "GR": "GR"}


def parse_bool(value: str) -> bool:
    return str(value).strip().lower() == "true"


def load_stats():
    stats = {
        model: defaultdict(lambda: defaultdict(lambda: {"n": 0, "success": 0}))
        for model in RUNS
    }
    for model, path in RUNS.items():
        with path.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                cwes = [part.strip() for part in row["concepts"].split("|") if part.strip()]
                surface = row["condition_axis"]
                if surface not in SURFACES:
                    continue
                success = 1 if parse_bool(row["success"]) else 0
                for cwe in cwes:
                    if cwe not in CWES:
                        continue
                    stats[model][cwe][surface]["n"] += 1
                    stats[model][cwe][surface]["success"] += success
    return stats


def build_plot(stats) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    cmap = LinearSegmentedColormap.from_list(
        "failure_scale",
        ["#0b783b", "#fff8b5", "#bd1026"],
    )
    norm = Normalize(vmin=0.0, vmax=1.0)

    cell_w = 1.0
    cell_h = 1.0
    group_gap = 0.28
    left_margin = 1.6
    top_margin = 1.9
    subheader_h = 0.55
    group_header_h = 0.9

    total_width = left_margin
    for i, _surface in enumerate(SURFACES):
        total_width += len(MODELS) * cell_w
        if i < len(SURFACES) - 1:
            total_width += group_gap
    total_height = top_margin + group_header_h + subheader_h + len(CWES) * cell_h + 0.9

    fig, ax = plt.subplots(figsize=(22, 8.6), dpi=220)
    ax.set_xlim(0, total_width + 1.2)
    ax.set_ylim(total_height, 0)
    ax.axis("off")

    fig.text(
        0.5,
        0.965,
        "CWE Capability Table — Final failure rate by attack surface",
        ha="center",
        va="top",
        fontsize=18,
        fontweight="bold",
    )
    fig.text(
        0.5,
        0.935,
        "Phase 1, inclusive contains-CWE aggregation across CodeLlama, Qwen, and Granite3.3",
        ha="center",
        va="top",
        fontsize=11,
        color="#555555",
    )

    ax.text(
        left_margin / 2,
        top_margin + 0.22,
        "CWE",
        ha="center",
        va="center",
        fontsize=11,
        fontweight="bold",
    )

    x = left_margin
    for surface in SURFACES:
        ax.add_patch(
            Rectangle(
                (x, top_margin),
                len(MODELS) * cell_w,
                group_header_h,
                facecolor="white",
                edgecolor="#777777",
                linewidth=0.8,
            )
        )
        ax.text(
            x + 1.5 * cell_w,
            top_margin + 0.35,
            SURFACE_LABELS[surface],
            ha="center",
            va="center",
            fontsize=10,
            fontweight="bold",
            linespacing=1.0,
        )
        for i, model in enumerate(MODELS):
            cell_x = x + i * cell_w
            ax.add_patch(
                Rectangle(
                    (cell_x, top_margin + group_header_h),
                    cell_w,
                    subheader_h,
                    facecolor="#f4f4f4",
                    edgecolor="#999999",
                    linewidth=0.8,
                )
            )
            ax.text(
                cell_x + cell_w / 2,
                top_margin + group_header_h + subheader_h / 2,
                MODEL_LABELS[model],
                ha="center",
                va="center",
                fontsize=9,
                fontweight="bold",
                color="#333333",
            )
        x += len(MODELS) * cell_w + group_gap

    row_y0 = top_margin + group_header_h + subheader_h
    for row_idx, cwe in enumerate(CWES):
        y = row_y0 + row_idx * cell_h
        row_fill = "#f3f3f3" if row_idx % 2 == 0 else "#ececec"
        ax.add_patch(
            Rectangle(
                (0, y),
                left_margin,
                cell_h,
                facecolor=row_fill,
                edgecolor="#dddddd",
                linewidth=0.8,
            )
        )
        ax.text(
            left_margin / 2,
            y + cell_h / 2,
            cwe,
            ha="center",
            va="center",
            fontsize=10,
            fontweight="bold",
        )

        x = left_margin
        for surface in SURFACES:
            for model in MODELS:
                bucket = stats[model][cwe][surface]
                n = int(bucket["n"])
                if n == 0:
                    face = "#e6e6e6"
                    main_text = "-"
                    sub_text = ""
                    text_color = "#777777"
                else:
                    success = bucket["success"] / n
                    failure = 1.0 - success
                    face = cmap(norm(failure))
                    main_text = f"{failure:.2f}"
                    sub_text = f"n={n}"
                    text_color = "#ffffff" if failure <= 0.18 or failure >= 0.82 else "#111111"
                ax.add_patch(
                    Rectangle(
                        (x, y),
                        cell_w,
                        cell_h,
                        facecolor=face,
                        edgecolor="white",
                        linewidth=0.9,
                    )
                )
                ax.text(
                    x + cell_w / 2,
                    y + 0.43,
                    main_text,
                    ha="center",
                    va="center",
                    fontsize=10,
                    fontweight="bold",
                    color=text_color,
                )
                if sub_text:
                    ax.text(
                        x + cell_w / 2,
                        y + 0.72,
                        sub_text,
                        ha="center",
                        va="center",
                        fontsize=7.5,
                        color=text_color,
                    )
                x += cell_w
            x += group_gap

    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax, fraction=0.03, pad=0.012, shrink=0.82)
    cbar.ax.tick_params(labelsize=9)
    cbar.set_label("Failure rate (1 - final secure success)", fontsize=10)

    fig.text(
        0.5,
        0.035,
        "Each cell aggregates all Phase-1 runs whose concept set contains the row CWE on the given attack surface.",
        ha="center",
        va="bottom",
        fontsize=10,
        color="#555555",
    )

    fig.savefig(PNG_OUT_PATH, dpi=320, bbox_inches="tight", pad_inches=0.2)
    fig.savefig(SVG_OUT_PATH, bbox_inches="tight", pad_inches=0.2)
    plt.close(fig)


def main() -> None:
    stats = load_stats()
    build_plot(stats)
    print(PNG_OUT_PATH)
    print(SVG_OUT_PATH)


if __name__ == "__main__":
    main()
