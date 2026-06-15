from __future__ import annotations

import csv
import json
from html import escape
from pathlib import Path


ROOT = Path("/home/kira/pack")
OUT_DIR = ROOT / "research_questions" / "figures" / "phase1_three_agent"

AGENTS = [
    ("CodeLlama 13B", "exp_0425_1421_vuln", "#2a6fbb"),
    ("GPT-OSS 20B", "exp_0425_2118_vuln", "#2f8f5b"),
    ("DeepSeek Coder V2", "exp_0427_0010_vuln", "#b35c1e"),
]

SURFACES = [
    "Authentication & Access Control",
    "Data Exchange & External Services",
    "Execution Environment & Infrastructure",
    "Storage & Filesystem",
    "User Inputs & Data",
    "Web Outputs & Rendering",
]

SURFACE_SHORT = {
    "Authentication & Access Control": "Auth &\nAccess",
    "Data Exchange & External Services": "Data Exchange\n& Services",
    "Execution Environment & Infrastructure": "Execution\nEnvironment",
    "Storage & Filesystem": "Storage &\nFilesystem",
    "User Inputs & Data": "User Inputs\n& Data",
    "Web Outputs & Rendering": "Web Outputs\n& Rendering",
}


def parse_bool(value: str) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def parse_float(value: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def pct(value: float) -> str:
    return f"{100 * value:.1f}%"


def svg_text(x, y, text, size=14, weight="400", fill="#1f2933", anchor="start", extra=""):
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" font-weight="{weight}" '
        f'fill="{fill}" text-anchor="{anchor}" {extra}>{escape(str(text))}</text>'
    )


def svg_multiline(x, y, text, size=12, weight="400", fill="#1f2933", anchor="middle", line_gap=14):
    lines = str(text).split("\n")
    parts = [
        f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" font-weight="{weight}" '
        f'fill="{fill}" text-anchor="{anchor}">'
    ]
    for i, line in enumerate(lines):
        dy = 0 if i == 0 else line_gap
        parts.append(f'<tspan x="{x:.1f}" dy="{dy}">{escape(line)}</tspan>')
    parts.append("</text>")
    return "".join(parts)


def svg_header(width, height, title, subtitle=""):
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        "<style>text{font-family:Arial,DejaVu Sans,sans-serif}.small{font-size:12px}.axis{fill:#475569}.grid{stroke:#d8dee9;stroke-width:1}.frame{stroke:#cbd5e1;stroke-width:1;fill:#ffffff}</style>",
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        svg_text(width / 2, 32, title, size=22, weight="700", fill="#111827", anchor="middle"),
    ] + ([svg_text(width / 2, 56, subtitle, size=13, fill="#52606d", anchor="middle")] if subtitle else [])


def write_svg(path: Path, parts: list[str]) -> None:
    path.write_text("\n".join(parts + ["</svg>\n"]), encoding="utf-8")


def success_color(value: float) -> str:
    # Red -> yellow -> green, tuned for print readability.
    if value < 0.5:
        t = value / 0.5
        r1, g1, b1 = (188, 60, 55)
        r2, g2, b2 = (246, 190, 86)
    else:
        t = (value - 0.5) / 0.5
        r1, g1, b1 = (246, 190, 86)
        r2, g2, b2 = (57, 142, 92)
    r = round(r1 + (r2 - r1) * t)
    g = round(g1 + (g2 - g1) * t)
    b = round(b1 + (b2 - b1) * t)
    return f"#{r:02x}{g:02x}{b:02x}"


def load_rows(exp: str) -> list[dict[str, str]]:
    path = ROOT / "experiments" / exp / "PHASE_ONE_5" / "analysis" / "records.csv"
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def load_failure_summary(exp: str) -> dict:
    path = ROOT / "experiments" / exp / "PHASE_ONE_5" / "analysis" / "failure_patterns.json"
    return json.loads(path.read_text(encoding="utf-8"))["summary"]


def summarize(rows: list[dict[str, str]]) -> dict[str, float]:
    n = len(rows)
    successes = sum(parse_bool(row["success"]) for row in rows)
    first = sum(parse_bool(row["first_attempt_success"]) for row in rows)
    return {
        "runs": n,
        "success_rate": successes / n if n else 0.0,
        "first_attempt_success_rate": first / n if n else 0.0,
        "final_issue_rate": sum(parse_float(row["total_issues"]) > 0 for row in rows) / n if n else 0.0,
        "target_issue_rate": sum(parse_bool(row["has_target_issue"]) for row in rows) / n if n else 0.0,
        "off_target_issue_rate": sum(parse_float(row["off_target_issue_count"]) > 0 for row in rows) / n if n else 0.0,
        "avg_risk": sum(parse_float(row["risk"]) for row in rows) / n if n else 0.0,
        "fixer_rate": sum(parse_bool(row["fixed_by_security_fixer"]) for row in rows) / n if n else 0.0,
        "any_fixer_attempt_rate": sum(parse_float(row["attempts_executed"]) > 1 for row in rows) / n if n else 0.0,
    }


def agent_data():
    data = {}
    for agent, exp, color in AGENTS:
        rows = load_rows(exp)
        data[agent] = {
            "exp": exp,
            "color": color,
            "rows": rows,
            "summary": summarize(rows),
            "failure": load_failure_summary(exp),
        }
    return data


def plot_generation_vs_correction(data: dict) -> None:
    width, height = 980, 500
    margin_l, margin_r = 120, 60
    y0, plot_h = 390, 280
    bar_w = 88
    group_gap = 95
    scale = plot_h
    parts = svg_header(
        width,
        height,
        "Generation vs correction capability",
        "First attempt, fixer gain, and final unresolved failure rate",
    )

    # y-grid
    for tick in [0, 0.25, 0.5, 0.75, 1.0]:
        y = y0 - tick * scale
        parts.append(f'<line class="grid" x1="{margin_l}" y1="{y:.1f}" x2="{width-margin_r}" y2="{y:.1f}"/>')
        parts.append(svg_text(margin_l - 12, y + 4, pct(tick), size=11, fill="#64748b", anchor="end"))

    x = margin_l + 35
    legend_x = width - 330
    legend_y = 82
    legend = [
        ("First-attempt success", "#8fb9e8"),
        ("Added by fixer", "#58b783"),
        ("Final failure", "#d77a61"),
    ]
    for i, (label, color) in enumerate(legend):
        ly = legend_y + i * 22
        parts.append(f'<rect x="{legend_x}" y="{ly - 12}" width="14" height="14" fill="{color}" rx="2"/>')
        parts.append(svg_text(legend_x + 22, ly, label, size=12, fill="#334155"))

    for agent, values in data.items():
        s = values["summary"]
        first = s["first_attempt_success_rate"]
        final = s["success_rate"]
        gain = max(final - first, 0)
        failure = 1 - final
        segments = [
            (first, "#8fb9e8", "first"),
            (gain, "#58b783", "gain"),
            (failure, "#d77a61", "fail"),
        ]
        y = y0
        for val, color, _kind in segments:
            h = val * scale
            y -= h
            parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w}" height="{h:.1f}" fill="{color}" rx="4"/>')
        parts.append(f'<rect x="{x:.1f}" y="{y0-scale:.1f}" width="{bar_w}" height="{scale}" fill="none" stroke="#475569" stroke-width="1"/>')
        parts.append(svg_text(x + bar_w / 2, y0 - final * scale - 8, pct(final), size=13, weight="700", fill="#111827", anchor="middle"))
        parts.append(svg_multiline(x + bar_w / 2, y0 + 28, agent.replace(" ", "\n", 1), size=12, fill="#334155", anchor="middle", line_gap=14))
        parts.append(svg_text(x + bar_w / 2, y0 + 67, f"n={int(s['runs'])}", size=11, fill="#64748b", anchor="middle"))
        x += bar_w + group_gap

    parts.append(svg_text(width / 2, 468, "Benchmark value: separates raw generation skill from repair-driven agent capability.", size=13, weight="700", fill="#111827", anchor="middle"))
    write_svg(OUT_DIR / "fig1_generation_vs_correction.svg", parts)


def plot_surface_heatmap(data: dict) -> None:
    width, height = 1040, 540
    cell_w, cell_h = 210, 52
    left, top = 260, 120
    parts = svg_header(
        width,
        height,
        "Capability profile by attack surface",
        "Final secure success rate; each cell reports success rate and sample size",
    )
    for j, (agent, _exp, _color) in enumerate(AGENTS):
        x = left + j * cell_w + cell_w / 2
        parts.append(svg_multiline(x, top - 38, agent.replace(" ", "\n", 1), size=12, weight="700", fill="#334155", anchor="middle"))
    for i, surface in enumerate(SURFACES):
        y = top + i * cell_h
        parts.append(svg_multiline(left - 18, y + 20, SURFACE_SHORT[surface], size=12, weight="700", fill="#334155", anchor="end", line_gap=13))
        for j, (agent, _exp, _color) in enumerate(AGENTS):
            rows = [row for row in data[agent]["rows"] if row["condition_axis"] == surface]
            s = summarize(rows)
            rate = s["success_rate"] if s else 0.0
            fill = success_color(rate)
            x = left + j * cell_w
            parts.append(f'<rect x="{x}" y="{y}" width="{cell_w-8}" height="{cell_h-8}" fill="{fill}" stroke="#ffffff" stroke-width="2" rx="5"/>')
            text_fill = "#ffffff" if rate < 0.28 or rate > 0.68 else "#111827"
            parts.append(svg_text(x + (cell_w - 8) / 2, y + 21, pct(rate), size=15, weight="700", fill=text_fill, anchor="middle"))
            parts.append(svg_text(x + (cell_w - 8) / 2, y + 39, f"n={int(s['runs'])}", size=11, fill=text_fill, anchor="middle"))
    parts.append(svg_text(width / 2, 500, "Benchmark value: locates where each agent breaks, instead of reporting only one global score.", size=13, weight="700", fill="#111827", anchor="middle"))
    write_svg(OUT_DIR / "fig2_attack_surface_heatmap.svg", parts)


def plot_combo_complexity(data: dict) -> None:
    width, height = 960, 500
    left, right, top, bottom = 90, 70, 80, 390
    plot_w, plot_h = width - left - right, bottom - top
    parts = svg_header(
        width,
        height,
        "Secure success drops as CWE combinations become larger",
        "Final secure success rate by target CWE-combination size",
    )
    for tick in [0, 0.25, 0.5, 0.75, 1.0]:
        y = bottom - tick * plot_h
        parts.append(f'<line class="grid" x1="{left}" y1="{y:.1f}" x2="{width-right}" y2="{y:.1f}"/>')
        parts.append(svg_text(left - 12, y + 4, pct(tick), size=11, fill="#64748b", anchor="end"))
    parts.append(f'<line x1="{left}" y1="{bottom}" x2="{width-right}" y2="{bottom}" stroke="#475569"/>')
    parts.append(f'<line x1="{left}" y1="{top}" x2="{left}" y2="{bottom}" stroke="#475569"/>')

    x_for = {size: left + (int(size) - 1) * (plot_w / 4) for size in ["1", "2", "3", "4", "5"]}
    for size, x in x_for.items():
        parts.append(f'<line class="grid" x1="{x:.1f}" y1="{bottom}" x2="{x:.1f}" y2="{bottom+6}"/>')
        parts.append(svg_text(x, bottom + 24, size, size=12, fill="#334155", anchor="middle"))
    parts.append(svg_text(width / 2, 460, "CWE-combination size", size=13, weight="700", fill="#334155", anchor="middle"))

    for agent, values in data.items():
        color = values["color"]
        points = []
        for size in ["1", "2", "3", "4", "5"]:
            rows = [row for row in values["rows"] if row["combo_size"] == size]
            s = summarize(rows)
            rate = s["success_rate"] if s else 0.0
            x = x_for[size]
            y = bottom - rate * plot_h
            points.append((x, y, rate, int(s["runs"] if s else 0)))
        point_str = " ".join(f"{x:.1f},{y:.1f}" for x, y, _rate, _n in points)
        parts.append(f'<polyline points="{point_str}" fill="none" stroke="{color}" stroke-width="3.5" stroke-linejoin="round"/>')
        for x, y, rate, n in points:
            parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5.5" fill="{color}" stroke="#ffffff" stroke-width="2"/>')
            parts.append(svg_text(x, y - 12, pct(rate), size=10, fill=color, weight="700", anchor="middle"))
        lx = width - right - 210
        ly = top + 10 + list(data.keys()).index(agent) * 24
        parts.append(f'<line x1="{lx}" y1="{ly}" x2="{lx+26}" y2="{ly}" stroke="{color}" stroke-width="3.5"/>')
        parts.append(f'<circle cx="{lx+13}" cy="{ly}" r="4" fill="{color}"/>')
        parts.append(svg_text(lx + 36, ly + 4, agent, size=12, fill="#334155"))

    parts.append(svg_text(width / 2, 486, "Benchmark value: exposes compositional vulnerability difficulty, not only isolated CWE skill.", size=13, weight="700", fill="#111827", anchor="middle"))
    write_svg(OUT_DIR / "fig3_cwe_combo_complexity.svg", parts)


def plot_failure_reasons(data: dict) -> None:
    width, height = 980, 500
    left, top = 130, 105
    bar_w, bar_h = 710, 58
    gap = 50
    colors = {
        "success": "#58b783",
        "unresolved_target_findings": "#c8423f",
        "unresolved_off_target_findings": "#e39b42",
        "syntax_no_code": "#7b6aa8",
    }
    labels = {
        "success": "Success",
        "unresolved_target_findings": "Target finding",
        "unresolved_off_target_findings": "Off-target finding",
        "syntax_no_code": "Syntax/no-code",
    }
    parts = svg_header(
        width,
        height,
        "Final outcome breakdown",
        "Outcome categories as a percentage of all Phase-1 runs",
    )
    legend_x, legend_y = left, 78
    dx = 0
    for key in ["success", "unresolved_target_findings", "unresolved_off_target_findings", "syntax_no_code"]:
        parts.append(f'<rect x="{legend_x+dx}" y="{legend_y-12}" width="14" height="14" fill="{colors[key]}" rx="2"/>')
        parts.append(svg_text(legend_x + dx + 20, legend_y, labels[key], size=12, fill="#334155"))
        dx += 170

    for idx, (agent, values) in enumerate(data.items()):
        y = top + idx * (bar_h + gap)
        runs = int(values["summary"]["runs"])
        failures = values["failure"]["primary_reason_counts"]
        segments = [
            ("success", int(round(values["summary"]["success_rate"] * runs))),
            ("unresolved_target_findings", failures.get("unresolved_target_findings", 0)),
            ("unresolved_off_target_findings", failures.get("unresolved_off_target_findings", 0)),
            ("syntax_no_code", failures.get("syntax_error", 0) + failures.get("no_code", 0)),
        ]
        parts.append(svg_text(left - 18, y + 34, agent, size=13, weight="700", fill="#334155", anchor="end"))
        x = left
        for key, count in segments:
            w = bar_w * count / runs if runs else 0
            parts.append(f'<rect x="{x:.1f}" y="{y}" width="{w:.1f}" height="{bar_h}" fill="{colors[key]}" stroke="#ffffff" stroke-width="1.5"/>')
            if w > 55:
                parts.append(svg_text(x + w / 2, y + 34, pct(count / runs), size=12, weight="700", fill="#ffffff", anchor="middle"))
            x += w
        parts.append(f'<rect x="{left}" y="{y}" width="{bar_w}" height="{bar_h}" fill="none" stroke="#475569" stroke-width="1"/>')
        parts.append(svg_text(left + bar_w + 12, y + 34, f"n={runs}", size=12, fill="#64748b"))

    parts.append(svg_text(width / 2, 460, "Benchmark value: separates intended security failures from off-target and reliability failures.", size=13, weight="700", fill="#111827", anchor="middle"))
    write_svg(OUT_DIR / "fig4_failure_reason_breakdown.svg", parts)


def plot_persistent_cwe_profiles(data: dict) -> None:
    width, height = 980, 560
    cwes = ["CWE-22", "CWE-78", "CWE-502", "CWE-117", "CWE-89", "CWE-209", "CWE-259", "CWE-113"]
    left, top = 160, 105
    cell_w, cell_h = 245, 42
    parts = svg_header(
        width,
        height,
        "Persistent vulnerability profile",
        "Unresolved CWE findings after correction, normalized as findings per 100 runs",
    )
    for j, (agent, _exp, _color) in enumerate(AGENTS):
        parts.append(svg_multiline(left + j * cell_w + cell_w / 2, top - 35, agent.replace(" ", "\n", 1), size=12, weight="700", fill="#334155"))

    # Build normalized values and max.
    matrix = {}
    max_val = 1.0
    for agent, values in data.items():
        runs = values["summary"]["runs"]
        counts = {item["key"]: item["count"] for item in values["failure"]["top_unresolved_cwes"]}
        matrix[agent] = {}
        for cwe in cwes:
            val = counts.get(cwe, 0) / runs * 100
            matrix[agent][cwe] = val
            max_val = max(max_val, val)

    for i, cwe in enumerate(cwes):
        y = top + i * cell_h
        parts.append(svg_text(left - 20, y + 26, cwe, size=13, weight="700", fill="#334155", anchor="end"))
        for j, (agent, _exp, _color) in enumerate(AGENTS):
            val = matrix[agent][cwe]
            intensity = val / max_val if max_val else 0
            # Light slate to deep red.
            r = round(238 + (153 - 238) * intensity)
            g = round(242 + (54 - 242) * intensity)
            b = round(247 + (54 - 247) * intensity)
            fill = f"#{r:02x}{g:02x}{b:02x}"
            x = left + j * cell_w
            parts.append(f'<rect x="{x}" y="{y}" width="{cell_w-8}" height="{cell_h-6}" fill="{fill}" stroke="#ffffff" stroke-width="2" rx="4"/>')
            text_fill = "#ffffff" if intensity > 0.55 else "#111827"
            label = f"{val:.1f}" if val else "-"
            parts.append(svg_text(x + (cell_w - 8) / 2, y + 24, label, size=13, weight="700", fill=text_fill, anchor="middle"))

    parts.append(svg_text(width / 2, 495, "Benchmark value: reveals interpretable security signatures, not just pass/fail rates.", size=13, weight="700", fill="#111827", anchor="middle"))
    parts.append(svg_text(width / 2, 520, "Unit: unresolved CWE findings per 100 runs. A run can contribute more than one finding.", size=11, fill="#64748b", anchor="middle"))
    write_svg(OUT_DIR / "fig5_persistent_cwe_profiles.svg", parts)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    data = agent_data()
    plot_generation_vs_correction(data)
    plot_surface_heatmap(data)
    plot_combo_complexity(data)
    plot_failure_reasons(data)
    plot_persistent_cwe_profiles(data)
    print(f"Wrote SVG figures to {OUT_DIR}")


if __name__ == "__main__":
    main()
