from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from textwrap import dedent, wrap

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap


ROOT = Path("/home/kira/pack")
OUT = ROOT / "presentation"
PLOTS = OUT / "plots"
DATA = OUT / "data"

RUNS = [
    {
        "model": "CodeLlama 13B",
        "short": "CodeLlama",
        "experiment": "exp_0425_1421_vuln",
        "path": ROOT / "experiments/exp_0425_1421_vuln/PHASE_ONE_5",
        "note": "model label from existing two-model report",
    },
    {
        "model": "GPT-OSS 20B",
        "short": "GPT-OSS",
        "experiment": "exp_0425_2118_vuln",
        "path": ROOT / "experiments/exp_0425_2118_vuln/PHASE_ONE_5",
        "note": "model label from existing two-model report",
    },
    {
        "model": "DeepSeek Coder V2",
        "short": "DeepSeek",
        "experiment": "exp_0427_0010_vuln",
        "path": ROOT / "experiments/exp_0427_0010_vuln/PHASE_ONE_5",
        "note": "model label inferred from current agent_config_vul.yml",
    },
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
    "Authentication & Access Control": "Auth\nAccess",
    "Data Exchange & External Services": "Data\nExchange",
    "Execution Environment & Infrastructure": "Execution\nInfra",
    "Storage & Filesystem": "Storage\nFilesystem",
    "User Inputs & Data": "User\nInputs",
    "Web Outputs & Rendering": "Web\nOutputs",
}

MODEL_COLORS = {
    "CodeLlama 13B": "#2364AA",
    "GPT-OSS 20B": "#2A9D8F",
    "DeepSeek Coder V2": "#E76F51",
}

MODEL_MARKERS = {
    "CodeLlama 13B": "o",
    "GPT-OSS 20B": "s",
    "DeepSeek Coder V2": "^",
}

CWE_LABELS = {
    "CWE-20": "CWE-20 input validation",
    "CWE-22": "CWE-22 path traversal/path injection",
    "CWE-78": "CWE-78 OS command execution/subprocess misuse",
    "CWE-79": "CWE-79 XSS/unsafe output rendering",
    "CWE-89": "CWE-89 SQL injection",
    "CWE-94": "CWE-94 server-side template/code injection",
    "CWE-95": "CWE-95 eval/code injection",
    "CWE-113": "CWE-113 HTTP header/response injection",
    "CWE-117": "CWE-117 log injection",
    "CWE-209": "CWE-209 error-message/stack-trace exposure",
    "CWE-215": "CWE-215 debug-mode exposure",
    "CWE-259": "CWE-259 hard-coded secret",
    "CWE-287": "CWE-287 improper authentication",
    "CWE-312": "CWE-312 clear-text storage of sensitive data",
    "CWE-319": "CWE-319 cleartext transmission/insecure protocol",
    "CWE-327": "CWE-327 broken/risky cryptography",
    "CWE-330": "CWE-330 predictable randomness",
    "CWE-377": "CWE-377 insecure temporary file use",
    "CWE-502": "CWE-502 unsafe deserialization",
    "CWE-532": "CWE-532 clear-text logging of sensitive data",
    "CWE-601": "CWE-601 open redirect",
    "CWE-605": "CWE-605 network exposure/binding to all interfaces",
    "CWE-611": "CWE-611 unsafe XML parsing/XXE risk",
    "CWE-703": "CWE-703 improper error handling",
    "CWE-732": "CWE-732 overly permissive file permissions",
    "CWE-1333": "CWE-1333 regular expression DoS",
}

TEST_TO_VULNERABILITY = {
    "bandit:B101": "CWE-703 improper error handling/assertion use",
    "bandit:B103": "CWE-732 overly permissive file permissions",
    "bandit:B104": "CWE-605 network exposure/binding to all interfaces",
    "bandit:B105": "CWE-259 hard-coded secret",
    "bandit:B106": "CWE-259 hard-coded secret",
    "bandit:B108": "CWE-377 insecure temporary file use",
    "bandit:B110": "CWE-703 improper error handling",
    "bandit:B112": "CWE-703 improper error handling",
    "bandit:B201": "CWE-215 debug-mode exposure",
    "bandit:B301": "CWE-502 unsafe deserialization",
    "bandit:B311": "CWE-330 predictable randomness",
    "bandit:B313": "CWE-611 unsafe XML parsing/XXE risk",
    "bandit:B314": "CWE-611 unsafe XML parsing/XXE risk",
    "bandit:B324": "CWE-327 broken/risky cryptography",
    "bandit:B403": "CWE-502 unsafe deserialization",
    "bandit:B404": "CWE-78 OS command execution/subprocess misuse",
    "bandit:B405": "CWE-611 unsafe XML parsing/XXE risk",
    "bandit:B408": "CWE-611 unsafe XML parsing/XXE risk",
    "bandit:B413": "CWE-611 unsafe XML parsing/XXE risk",
    "bandit:B602": "CWE-78 OS command execution/subprocess misuse",
    "bandit:B603": "CWE-78 OS command execution/subprocess misuse",
    "bandit:B605": "CWE-78 OS command execution/subprocess misuse",
    "bandit:B607": "CWE-78 OS command execution/subprocess misuse",
    "bandit:B608": "CWE-89 SQL injection",
    "bandit:B701": "CWE-79 XSS/unsafe template rendering",
    "codeql:py/bad-tag-filter": "CWE-79 XSS/unsafe HTML sanitization",
    "codeql:py/clear-text-logging-sensitive-data": "CWE-532 clear-text logging of sensitive data",
    "codeql:py/clear-text-storage-sensitive-data": "CWE-312 clear-text storage of sensitive data",
    "codeql:py/command-line-injection": "CWE-78 OS command execution/subprocess misuse",
    "codeql:py/cookie-injection": "CWE-113 HTTP header/cookie injection",
    "codeql:py/flask-debug": "CWE-215 debug-mode exposure",
    "codeql:py/http-response-splitting": "CWE-113 HTTP response splitting",
    "codeql:py/insecure-protocol": "CWE-319 cleartext transmission/insecure protocol",
    "codeql:py/jinja2/autoescape-false": "CWE-79 XSS/unsafe template rendering",
    "codeql:py/log-injection": "CWE-117 log injection",
    "codeql:py/overly-permissive-file": "CWE-732 overly permissive file permissions",
    "codeql:py/path-injection": "CWE-22 path traversal/path injection",
    "codeql:py/polynomial-redos": "CWE-1333 regular expression DoS",
    "codeql:py/reflective-xss": "CWE-79 XSS/unsafe template rendering",
    "codeql:py/sql-injection": "CWE-89 SQL injection",
    "codeql:py/stack-trace-exposure": "CWE-209 error-message/stack-trace exposure",
    "codeql:py/template-injection": "CWE-94 server-side template/code injection",
    "codeql:py/url-redirection": "CWE-601 open redirect",
    "codeql:py/weak-sensitive-data-hashing": "CWE-327 broken/risky cryptography",
    "semgrep:prismvul.python.eval": "CWE-95 eval/code injection",
}


def _float(value: object, default: float = 0.0) -> float:
    try:
        if value in ("", None):
            return default
        return float(value)
    except Exception:
        return default


def _int(value: object, default: int = 0) -> int:
    try:
        if value in ("", None):
            return default
        return int(float(value))
    except Exception:
        return default


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_records(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def split_ids(value: object) -> list[str]:
    return [item for item in str(value or "").split("|") if item]


def pct(value: float) -> float:
    return 100.0 * value


def rate(rows: list[dict], key: str) -> float:
    if not rows:
        return 0.0
    return sum(1 for row in rows if str(row.get(key, "")).lower() == "true") / len(rows)


def numeric_rate(rows: list[dict], key: str) -> float:
    if not rows:
        return 0.0
    return sum(1 for row in rows if _int(row.get(key)) > 0) / len(rows)


def avg_numeric(rows: list[dict], key: str, default: float = 0.0) -> float:
    values = [_float(row.get(key), default=None) for row in rows if row.get(key) not in ("", None)]
    values = [value for value in values if value is not None]
    if not values:
        return default
    return sum(values) / len(values)


def issue_rate(rows: list[dict]) -> float:
    if not rows:
        return 0.0
    return sum(1 for row in rows if _int(row.get("total_issues")) > 0) / len(rows)


def target_issue_rate(rows: list[dict]) -> float:
    if not rows:
        return 0.0
    return sum(1 for row in rows if str(row.get("has_target_issue", "")).lower() == "true") / len(rows)


def row_cwes(row: dict) -> list[str]:
    return re.findall(r"CWE-\d+", str(row.get("concepts") or ""))


def vulnerability_from_test(test_id: str) -> str:
    return TEST_TO_VULNERABILITY.get(test_id, test_id)


def vulnerability_from_cwe(cwe_id: str) -> str:
    return CWE_LABELS.get(cwe_id, cwe_id)


def wrapped_label(label: str, width: int = 31) -> str:
    return "\n".join(wrap(label, width=width, break_long_words=False))


def compact_vulnerability_label(label: str) -> str:
    compact = {
        "CWE-22": "CWE-22\npath traversal",
        "CWE-78": "CWE-78\ncommand exec",
        "CWE-79": "CWE-79\nXSS/rendering",
        "CWE-89": "CWE-89\nSQL injection",
        "CWE-113": "CWE-113\nHTTP splitting",
        "CWE-117": "CWE-117\nlog injection",
        "CWE-209": "CWE-209\nerror exposure",
        "CWE-215": "CWE-215\ndebug exposure",
        "CWE-259": "CWE-259\nhard-coded secret",
        "CWE-327": "CWE-327\nweak crypto",
        "CWE-502": "CWE-502\ndeserialization",
        "CWE-605": "CWE-605\nnetwork exposure",
    }
    for prefix, short_label in compact.items():
        if label.startswith(prefix):
            return short_label
    return "\n".join(wrap(label, width=17, break_long_words=False))


def short_vulnerability_phrase(label: str) -> str:
    phrases = {
        "CWE-22": "path traversal",
        "CWE-78": "command exec",
        "CWE-79": "XSS/rendering",
        "CWE-89": "SQL injection",
        "CWE-113": "HTTP splitting",
        "CWE-117": "log injection",
        "CWE-209": "error exposure",
        "CWE-215": "debug exposure",
        "CWE-259": "hard-coded secret",
        "CWE-327": "weak crypto",
        "CWE-502": "deserialization",
        "CWE-601": "open redirect",
        "CWE-605": "network exposure",
    }
    for prefix, phrase in phrases.items():
        if label.startswith(prefix):
            return f"{prefix} {phrase}"
    return label


def count_failure_column(bundle: dict, column: str, mapper) -> Counter:
    counts: Counter = Counter()
    for row in bundle.get("failure_rows", []):
        counts.update(mapper(item) for item in split_ids(row.get(column)))
    return counts


def top_union(counts_by_model: dict[str, Counter], limit: int = 9) -> list[str]:
    totals: Counter = Counter()
    for counts in counts_by_model.values():
        totals.update(counts)
    return [name for name, _ in totals.most_common(limit)]


def annotate_bar_values(ax, bars, values: list[float], *, suffix: str = "", min_value: float = 0.0) -> None:
    for bar, value in zip(bars, values):
        if value < min_value:
            continue
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 1.2,
            f"{value:.1f}{suffix}",
            ha="center",
            va="bottom",
            fontsize=8,
        )


def model_bundle() -> list[dict]:
    bundles = []
    for run in RUNS:
        analysis = run["path"] / "analysis"
        metrics = load_json(analysis / "metrics.json")
        records = load_records(analysis / "records.csv")
        failure_rows = load_records(analysis / "failure_patterns.csv")
        failures = load_json(analysis / "failure_patterns.json")
        patterns = load_json(analysis / "code_failure_pattern_analysis.json")
        bundles.append(
            {
                **run,
                "metrics": metrics,
                "records": records,
                "failure_rows": failure_rows,
                "failures": failures,
                "patterns": patterns,
            }
        )
    return bundles


def failure_summary(bundle: dict) -> dict:
    failures = bundle.get("failures") or {}
    if "summary" in failures:
        return failures.get("summary") or {}
    return failures or (bundle.get("metrics", {}).get("failure_patterns") or {})


def group_by(records: list[dict], key: str) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in records:
        grouped[str(row.get(key) or "unknown")].append(row)
    return grouped


def overall_rows(bundles: list[dict]) -> list[dict]:
    rows = []
    for bundle in bundles:
        records = bundle["records"]
        overall = (bundle["metrics"].get("overall") or {})
        rows.append(
            {
                "model": bundle["model"],
                "experiment": bundle["experiment"],
                "runs": len(records) or int(overall.get("runs", 0) or 0),
                "first_success": rate(records, "first_attempt_success"),
                "final_success": rate(records, "success"),
                "feedback_gain": rate(records, "success") - rate(records, "first_attempt_success"),
                "issue_rate": issue_rate(records),
                "target_issue_rate": target_issue_rate(records),
                "off_target_issue_rate": numeric_rate(records, "off_target_issue_count"),
                "fixer_rate": rate(records, "fixed_by_security_fixer"),
                "avg_risk": avg_numeric(records, "risk", _float(overall.get("avg_risk"))),
                "avg_attempts": avg_numeric(records, "attempts_executed", _float(overall.get("avg_attempts"))),
            }
        )
    return rows


def set_style() -> None:
    plt.rcParams.update(
        {
            "figure.dpi": 150,
            "savefig.dpi": 240,
            "font.size": 10,
            "axes.titlesize": 15,
            "axes.titleweight": "bold",
            "axes.labelsize": 10,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "legend.fontsize": 9,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.alpha": 0.22,
            "grid.linewidth": 0.7,
        }
    )


def savefig(name: str) -> None:
    for suffix in ("png", "svg", "pdf"):
        plt.savefig(PLOTS / f"{name}.{suffix}", bbox_inches="tight", facecolor="white")
    plt.close()


def plot_model_overview(bundles: list[dict]) -> None:
    rows = overall_rows(bundles)
    metrics = [
        ("first_success", "Zero-shot secure"),
        ("final_success", "One-shot secure"),
        ("feedback_gain", "Repair gain"),
        ("issue_rate", "Residual\nSAST issue"),
    ]
    x = np.arange(len(metrics))
    width = 0.22
    fig, ax = plt.subplots(figsize=(10.8, 5.8))
    for idx, row in enumerate(rows):
        values = [pct(row[key]) for key, _ in metrics]
        pos = x + (idx - 1) * width
        bars = ax.bar(pos, values, width, label=f"{row['model']} (n={row['runs']})", color=MODEL_COLORS[row["model"]])
        annotate_bar_values(ax, bars, values, min_value=0.1)
    ax.set_ylabel("Rate (%)")
    ax.set_ylim(0, 105)
    ax.set_xticks(x)
    ax.set_xticklabels([label for _, label in metrics])
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=3, frameon=False)
    savefig("01_model_overview")


def plot_surface_success_heatmap(bundles: list[dict]) -> None:
    values = []
    labels = []
    for bundle in bundles:
        grouped = group_by(bundle["records"], "condition_axis")
        row = []
        label_row = []
        for surface in SURFACES:
            rows = grouped.get(surface, [])
            row.append(pct(rate(rows, "success")) if rows else np.nan)
            label_row.append(f"{pct(rate(rows, 'success')):.0f}%\nN={len(rows)}" if rows else "-")
        values.append(row)
        labels.append(label_row)

    fig, ax = plt.subplots(figsize=(12.6, 4.7))
    cmap = LinearSegmentedColormap.from_list("success", ["#F4A261", "#F7F7F2", "#2A9D8F"])
    im = ax.imshow(values, cmap=cmap, vmin=0, vmax=100, aspect="auto")
    ax.set_title("One-shot secure success by attack surface")
    ax.set_yticks(np.arange(len(bundles)))
    ax.set_yticklabels([bundle["model"] for bundle in bundles])
    ax.set_xticks(np.arange(len(SURFACES)))
    ax.set_xticklabels([SURFACE_SHORT[s] for s in SURFACES])
    for i in range(len(bundles)):
        for j in range(len(SURFACES)):
            ax.text(j, i, labels[i][j], ha="center", va="center", fontsize=9, color="#1B1B1B")
    cbar = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.02)
    cbar.set_label("One-shot secure success (%)")
    ax.grid(False)
    savefig("02_surface_success_heatmap")


def plot_feedback_gain_by_surface(bundles: list[dict]) -> None:
    x = np.arange(len(SURFACES))
    width = 0.24
    fig, ax = plt.subplots(figsize=(13.4, 5.8))
    all_gains = []
    for idx, bundle in enumerate(bundles):
        grouped = group_by(bundle["records"], "condition_axis")
        gains = []
        for surface in SURFACES:
            rows = grouped.get(surface, [])
            gains.append(pct(rate(rows, "success") - rate(rows, "first_attempt_success")) if rows else 0)
        all_gains.extend(gains)
        bars = ax.bar(x + (idx - 1) * width, gains, width, label=bundle["model"], color=MODEL_COLORS[bundle["model"]])
        for bar, gain in zip(bars, gains):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                gain + 0.8,
                f"+{gain:.1f}",
                ha="center",
                va="bottom",
                fontsize=7.5,
            )
    ax.axhline(0, color="#333333", linewidth=0.9)
    ax.set_title("Correction gain by attack surface")
    ax.set_ylabel("One-shot minus zero-shot success (pp)")
    ax.set_ylim(0, max(all_gains or [0]) + 8)
    ax.set_xticks(x)
    ax.set_xticklabels([SURFACE_SHORT[s] for s in SURFACES])
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=3, frameon=False)
    savefig("03_feedback_gain_by_surface")


def plot_combo_size_degradation(bundles: list[dict]) -> None:
    fig, ax = plt.subplots(figsize=(9.8, 5.8))
    label_offsets = {
        "CodeLlama 13B": (-0.07, -7.0),
        "GPT-OSS 20B": (0.07, 7.0),
        "DeepSeek Coder V2": (0.0, -8.0),
    }
    first_point_offsets = {
        "CodeLlama 13B": (-0.08, 6.0),
        "GPT-OSS 20B": (0.09, -7.0),
    }
    for bundle in bundles:
        grouped = group_by(bundle["records"], "combo_size")
        sizes = sorted([_int(size) for size in grouped if _int(size) > 0])
        success = []
        for size in sizes:
            rows = grouped.get(str(size), [])
            success.append(pct(rate(rows, "success")))
        ax.plot(
            sizes,
            success,
            marker=MODEL_MARKERS[bundle["model"]],
            markersize=7,
            linewidth=2.4,
            label=bundle["model"],
            color=MODEL_COLORS[bundle["model"]],
        )
        for x_val, y_val in zip(sizes, success):
            n = len(grouped.get(str(x_val), []))
            dx, dy = first_point_offsets.get(bundle["model"], label_offsets[bundle["model"]]) if x_val == 1 else label_offsets[bundle["model"]]
            ax.text(
                x_val + dx,
                y_val + dy,
                f"{y_val:.1f}%\nn={n}",
                ha="center",
                va="center",
                fontsize=8,
                color=MODEL_COLORS[bundle["model"]],
                bbox={"boxstyle": "round,pad=0.18", "facecolor": "white", "edgecolor": "none", "alpha": 0.72},
            )
    ax.set_title("One-shot secure success as CWE composition grows")
    ax.set_xlabel("Target CWE combination size")
    ax.set_ylabel("One-shot secure success (%)")
    ax.set_ylim(0, 105)
    ax.set_xlim(0.75, 5.25)
    ax.set_xticks([1, 2, 3, 4, 5])
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=3, frameon=False)
    savefig("04_combo_size_success")


def plot_failure_reason_stacks(bundles: list[dict]) -> None:
    reasons = [
        "unresolved_target_findings",
        "unresolved_off_target_findings",
        "syntax_error",
        "no_code",
    ]
    labels = {
        "unresolved_target_findings": "Target vuln",
        "unresolved_off_target_findings": "Off-target vuln",
        "syntax_error": "Syntax",
        "no_code": "No code",
    }
    colors = {
        "unresolved_target_findings": "#D1495B",
        "unresolved_off_target_findings": "#EDAE49",
        "syntax_error": "#30638E",
        "no_code": "#6D597A",
    }
    fig, ax = plt.subplots(figsize=(10.8, 4.8))
    y = np.arange(len(bundles))
    left = np.zeros(len(bundles))
    for reason in reasons:
        vals = []
        for bundle in bundles:
            fp = failure_summary(bundle)
            counts = fp.get("primary_reason_counts") or {}
            runs = len(bundle["records"]) or fp.get("runs") or 1
            vals.append(pct((counts.get(reason) or 0) / runs))
        bars = ax.barh(y, vals, left=left, color=colors[reason], label=labels[reason])
        for bar, value, offset in zip(bars, vals, left):
            if value >= 6:
                ax.text(
                    offset + value / 2,
                    bar.get_y() + bar.get_height() / 2,
                    f"{value:.1f}%",
                    ha="center",
                    va="center",
                    fontsize=8,
                    color="white",
                    fontweight="bold",
                )
        left += np.array(vals)
    ax.set_yticks(y)
    ax.set_yticklabels([bundle["model"] for bundle in bundles])
    ax.set_xlabel("Share of all runs (%)")
    ax.set_title("Why one-shot runs fail")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=4, frameon=False)
    savefig("05_failure_reason_stacks")


def plot_top_residual_cwes(bundles: list[dict]) -> None:
    fig, axes = plt.subplots(1, len(bundles), figsize=(15.2, 5.6), sharex=False)
    for ax, bundle in zip(axes, bundles):
        fp = failure_summary(bundle)
        items = fp.get("top_unresolved_cwes") or []
        labels = [item["key"] for item in items[:6]][::-1]
        counts = [item["count"] for item in items[:6]][::-1]
        ax.barh(labels, counts, color=MODEL_COLORS[bundle["model"]])
        ax.set_title(bundle["model"])
        ax.set_xlabel("Unresolved count")
        for y, count in enumerate(counts):
            ax.text(count + 0.4, y, str(count), va="center", fontsize=9)
    fig.suptitle("Top unresolved CWE families", y=1.03, fontsize=15)
    savefig("06_top_unresolved_cwes")


def plot_surface_coverage(bundles: list[dict]) -> None:
    x = np.arange(len(SURFACES))
    width = 0.24
    fig, ax = plt.subplots(figsize=(13.4, 5.5))
    for idx, bundle in enumerate(bundles):
        grouped = group_by(bundle["records"], "condition_axis")
        counts = [len(grouped.get(surface, [])) for surface in SURFACES]
        bars = ax.bar(x + (idx - 1) * width, counts, width, label=bundle["model"], color=MODEL_COLORS[bundle["model"]])
        for bar, count in zip(bars, counts):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                count + 1.0,
                str(count),
                ha="center",
                va="bottom",
                fontsize=7.5,
                color=MODEL_COLORS[bundle["model"]],
            )
    ax.set_title("Exploration coverage by attack surface")
    ax.set_ylabel("Number of evaluated runs")
    ax.set_ylim(0, max(len(bundle["records"]) for bundle in bundles) * 0.25)
    ax.set_xticks(x)
    ax.set_xticklabels([SURFACE_SHORT[s] for s in SURFACES])
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=3, frameon=False)
    savefig("07_surface_coverage")


def plot_cwe_success_heatmap(bundles: list[dict]) -> None:
    cwes = sorted(
        {
            cwe
            for bundle in bundles
            for row in bundle["records"]
            for cwe in row_cwes(row)
        },
        key=lambda value: int(value.split("-")[1]) if value.split("-")[1].isdigit() else 99999,
    )
    values = []
    annotations = []
    for bundle in bundles:
        row_values = []
        row_annotations = []
        for cwe in cwes:
            rows = [row for row in bundle["records"] if cwe in row_cwes(row)]
            row_values.append(pct(rate(rows, "success")) if rows else np.nan)
            row_annotations.append(f"{pct(rate(rows, 'success')):.0f}%\nN={len(rows)}" if rows else "-")
        values.append(row_values)
        annotations.append(row_annotations)
    fig, ax = plt.subplots(figsize=(11.5, 4.7))
    cmap = LinearSegmentedColormap.from_list("cwe_success", ["#F4A261", "#F7F7F2", "#2A9D8F"])
    im = ax.imshow(values, cmap=cmap, vmin=0, vmax=100, aspect="auto")
    ax.set_title("One-shot secure success by target CWE membership")
    ax.set_yticks(np.arange(len(bundles)))
    ax.set_yticklabels([bundle["model"] for bundle in bundles])
    ax.set_xticks(np.arange(len(cwes)))
    ax.set_xticklabels(cwes, rotation=0)
    for i in range(len(bundles)):
        for j in range(len(cwes)):
            ax.text(j, i, annotations[i][j], ha="center", va="center", fontsize=8)
    cbar = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.02)
    cbar.set_label("One-shot secure success (%)")
    ax.grid(False)
    savefig("08_cwe_success_heatmap")


def plot_vulnerability_count_heatmap(
    bundles: list[dict],
    counts_by_model: dict[str, Counter],
    families: list[str],
    *,
    title: str,
    cbar_label: str,
    filename: str,
) -> None:
    matrix = np.array(
        [[counts_by_model[bundle["model"]].get(family, 0) for bundle in bundles] for family in families],
        dtype=float,
    )
    fig_height = max(5.4, 0.58 * len(families) + 2.1)
    fig, ax = plt.subplots(figsize=(12.4, fig_height))
    cmap = LinearSegmentedColormap.from_list(
        "vuln_counts",
        ["#FAFAF6", "#DDE8D5", "#9EC5A4", "#4F8A67", "#1F4D36"],
    )
    vmax = max(float(matrix.max()) if matrix.size else 0.0, 1.0)
    im = ax.imshow(matrix, cmap=cmap, vmin=0, vmax=vmax, aspect="auto")

    ax.set_title(title)
    ax.set_xticks(np.arange(len(bundles)))
    ax.set_xticklabels([f"{bundle['short']}\nn={len(bundle['records'])}" for bundle in bundles])
    ax.set_yticks(np.arange(len(families)))
    ax.set_yticklabels([wrapped_label(family) for family in families])

    for row_idx, family in enumerate(families):
        for col_idx, bundle in enumerate(bundles):
            value = counts_by_model[bundle["model"]].get(family, 0)
            text_color = "white" if value >= vmax * 0.55 else "#222222"
            label = str(value) if value else "-"
            ax.text(col_idx, row_idx, label, ha="center", va="center", fontsize=10, fontweight="bold", color=text_color)

    cbar = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.02)
    cbar.set_label(cbar_label)
    ax.grid(False)
    savefig(filename)


def plot_fixer_resolved_vulnerabilities(bundles: list[dict]) -> None:
    counts_by_model = {
        bundle["model"]: count_failure_column(bundle, "resolved_test_ids", vulnerability_from_test)
        for bundle in bundles
    }
    families = top_union(counts_by_model, limit=9)
    plot_vulnerability_count_heatmap(
        bundles,
        counts_by_model,
        families,
        title="What the fixer resolves",
        cbar_label="Resolved vulnerability findings",
        filename="09_fixer_resolved_vulnerabilities",
    )


def plot_persistent_vulnerability_patterns(bundles: list[dict]) -> None:
    counts_by_model = {
        bundle["model"]: count_failure_column(bundle, "persistent_test_ids", vulnerability_from_test)
        for bundle in bundles
    }
    families = top_union(counts_by_model, limit=9)
    plot_vulnerability_count_heatmap(
        bundles,
        counts_by_model,
        families,
        title="Persistent vulnerability patterns after repair",
        cbar_label="Persistent vulnerability findings",
        filename="10_persistent_vulnerability_patterns",
    )


def plot_overall_vulnerability_patterns(bundles: list[dict]) -> None:
    counts_by_model = {
        bundle["model"]: count_failure_column(bundle, "first_test_ids", vulnerability_from_test)
        for bundle in bundles
    }
    families = top_union(counts_by_model, limit=9)
    plot_vulnerability_count_heatmap(
        bundles,
        counts_by_model,
        families,
        title="Overall vulnerability patterns produced initially",
        cbar_label="Initial vulnerability findings",
        filename="11_overall_initial_vulnerability_patterns",
    )


def plot_persistent_patterns_by_attack_surface(bundles: list[dict]) -> None:
    totals = np.zeros((len(SURFACES), len(bundles)), dtype=float)
    labels: list[list[str]] = [["-" for _ in bundles] for _ in SURFACES]

    for col_idx, bundle in enumerate(bundles):
        by_surface: dict[str, Counter] = defaultdict(Counter)
        for row in bundle.get("failure_rows", []):
            surface = str(row.get("attack_surface") or row.get("condition_axis") or "unknown")
            if surface not in SURFACES:
                continue
            by_surface[surface].update(vulnerability_from_cwe(item) for item in split_ids(row.get("final_cwe_ids")))

        for row_idx, surface in enumerate(SURFACES):
            counts = by_surface.get(surface, Counter())
            total = sum(counts.values())
            totals[row_idx, col_idx] = total
            if total:
                top_items = counts.most_common(3)
                label_lines = [f"{short_vulnerability_phrase(family)} ({count})" for family, count in top_items]
                labels[row_idx][col_idx] = "\n".join(label_lines)

    fig, ax = plt.subplots(figsize=(12.4, 6.8))
    cmap = LinearSegmentedColormap.from_list(
        "surface_persistent",
        ["#FAFAF6", "#DDE8D5", "#9EC5A4", "#4F8A67", "#1F4D36"],
    )
    vmax = max(float(totals.max()) if totals.size else 0.0, 1.0)
    im = ax.imshow(totals, cmap=cmap, vmin=0, vmax=vmax, aspect="auto")
    ax.set_title("Residual vulnerability patterns by attack surface")
    ax.set_xticks(np.arange(len(bundles)))
    ax.set_xticklabels([f"{bundle['short']}\nn={len(bundle['records'])}" for bundle in bundles])
    ax.set_yticks(np.arange(len(SURFACES)))
    ax.set_yticklabels([SURFACE_SHORT[surface].replace("\n", " ") for surface in SURFACES])

    for row_idx in range(len(SURFACES)):
        for col_idx in range(len(bundles)):
            value = totals[row_idx, col_idx]
            text_color = "white" if value >= vmax * 0.55 else "#1B1B1B"
            ax.text(col_idx, row_idx, labels[row_idx][col_idx], ha="center", va="center", fontsize=8.8, color=text_color, fontweight="bold")

    cbar = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.02)
    cbar.set_label("Residual vulnerability findings")
    ax.grid(False)
    savefig("12_persistent_patterns_by_attack_surface")


def write_summary_tables(bundles: list[dict]) -> None:
    rows = overall_rows(bundles)
    with (DATA / "overall_summary.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    surface_rows = []
    for bundle in bundles:
        grouped = group_by(bundle["records"], "condition_axis")
        for surface in SURFACES:
            records = grouped.get(surface, [])
            surface_rows.append(
                {
                    "model": bundle["model"],
                    "experiment": bundle["experiment"],
                    "surface": surface,
                    "runs": len(records),
                    "first_success": rate(records, "first_attempt_success"),
                    "final_success": rate(records, "success"),
                    "gain": rate(records, "success") - rate(records, "first_attempt_success"),
                    "issue_rate": issue_rate(records),
                }
            )
    with (DATA / "surface_summary.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(surface_rows[0].keys()))
        writer.writeheader()
        writer.writerows(surface_rows)


def md_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(headers) + " |"]
    lines.append("|" + "|".join(["---"] * len(headers)) + "|")
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def write_report(bundles: list[dict]) -> None:
    rows = overall_rows(bundles)
    overview = md_table(
        ["Model", "Run", "N", "Zero-shot secure", "One-shot secure", "Gain", "Residual SAST issue", "Avg risk"],
        [
            [
                row["model"],
                row["experiment"],
                str(row["runs"]),
                f"{pct(row['first_success']):.1f}%",
                f"{pct(row['final_success']):.1f}%",
                f"{pct(row['final_success'] - row['first_success']):+.1f} pp",
                f"{pct(row['issue_rate']):.1f}%",
                f"{row['avg_risk']:.3f}",
            ]
            for row in rows
        ],
    )

    surface_best_worst = []
    for bundle in bundles:
        grouped = group_by(bundle["records"], "condition_axis")
        surface_rates = [
            (surface, len(grouped.get(surface, [])), rate(grouped.get(surface, []), "success"))
            for surface in SURFACES
        ]
        worst = min(surface_rates, key=lambda item: item[2])
        best = max(surface_rates, key=lambda item: item[2])
        surface_best_worst.append(
            [
                bundle["model"],
                f"{best[0]} ({pct(best[2]):.1f}%, n={best[1]})",
                f"{worst[0]} ({pct(worst[2]):.1f}%, n={worst[1]})",
            ]
        )

    surface_table = md_table(["Model", "Best surface", "Weakest surface"], surface_best_worst)

    pattern_rows = []
    for bundle in bundles:
        fp = failure_summary(bundle)
        cwes = fp.get("top_unresolved_cwes") or []
        pattern_rows.append(
            [
                bundle["model"],
                ", ".join(f"{vulnerability_from_cwe(item['key'])} ({item['count']})" for item in cwes[:3]) or "n/a",
            ]
        )
    pattern_table = md_table(["Model", "Top residual vulnerability families"], pattern_rows)

    report = dedent(
        f"""
        # Presentation Report: Three Phase-1 Secure-Code Agent Runs

        This folder contains presentation-ready plots and a compact report for the latest three model runs selected for comparison:

        - CodeLlama 13B: `/home/kira/pack/experiments/exp_0425_1421_vuln/PHASE_ONE_5`
        - GPT-OSS 20B: `/home/kira/pack/experiments/exp_0425_2118_vuln/PHASE_ONE_5`
        - DeepSeek Coder V2: `/home/kira/pack/experiments/exp_0427_0010_vuln/PHASE_ONE_5`

        The DeepSeek label is inferred from the current `agent_config_vul.yml`; the run artifacts do not store a model name directly. All plotted rates are recomputed from each run's `records.csv` so the tables and figures use the same denominator.

        ## Core Message

        The benchmark should be presented as a dynamic secure-code capability mapper. It does not only produce one score per model. It shows:

        - whether the model can generate secure code,
        - how much feedback improves the one-shot result,
        - where capability breaks by attack surface and CWE composition,
        - which vulnerability families remain recurrent after correction.

        ## Overall Results

        {overview}

        The main reading is that feedback matters for all compared agents, but the gain is not uniform. The report should therefore avoid a single "winner" narrative and instead emphasize different capability profiles.

        ## Surface-Level Capability

        {surface_table}

        Surface-level results are important because they show where secure-code capability is concentrated or fragile. Use the surface heatmap and feedback-gain plot to make this visible.

        ## Recurrent Vulnerability Patterns

        {pattern_table}

        These patterns are the strongest evidence that the benchmark is diagnostic. It reveals not only that a model fails, but what kind of vulnerability it tends to leave behind.

        ## Presentation Figures

        ### 1. Model Overview

        High-level zero-shot, one-shot, repair-gain, and residual issue comparison.

        ![Model overview](plots/01_model_overview.png)

        ### 2. Success By Attack Surface

        One-shot secure success by model and attack surface.

        ![Surface success heatmap](plots/02_surface_success_heatmap.png)

        ### 3. Feedback Gain By Surface

        How much feedback improves each surface.

        ![Feedback gain by surface](plots/03_feedback_gain_by_surface.png)

        ### 4. CWE Composition Effect

        Degradation as CWE combinations become larger.

        ![Combo size success](plots/04_combo_size_success.png)

        ### 5. Failure Reasons

        One-shot failure composition.

        ![Failure reason stacks](plots/05_failure_reason_stacks.png)

        ### 6. Top Unresolved CWEs

        Dominant residual CWE families.

        ![Top unresolved CWEs](plots/06_top_unresolved_cwes.png)

        ### 7. Surface Coverage

        Evaluation budget distribution by surface.

        ![Surface coverage](plots/07_surface_coverage.png)

        ### 8. Success By CWE

        One-shot success by CWE membership.

        ![CWE success heatmap](plots/08_cwe_success_heatmap.png)

        ### 9. What The Fixer Resolves

        Known vulnerability families removed during feedback and repair.

        ![Fixer resolved vulnerabilities](plots/09_fixer_resolved_vulnerabilities.png)

        ### 10. Persistent Vulnerability Patterns

        Vulnerability families that remain present after the fixer loop.

        ![Persistent vulnerability patterns](plots/10_persistent_vulnerability_patterns.png)

        ### 11. Overall Initial Vulnerability Patterns

        Vulnerability families produced by the zero-shot/generated code before repair.

        ![Overall initial vulnerability patterns](plots/11_overall_initial_vulnerability_patterns.png)

        ### 12. Residual Patterns By Attack Surface

        Top residual vulnerability families for each attack surface and model.

        ![Residual patterns by attack surface](plots/12_persistent_patterns_by_attack_surface.png)

        ## How To Present The Engine

        The exploration engine guides evaluation in three steps:

        1. A surface scheduler allocates budget toward difficult, under-covered, or uncertain attack surfaces.
        2. MCTS selects an informative node inside the chosen surface.
        3. Expansion keeps the same surface and adds one under-covered CWE, making the task progressively more compositional.

        The reviewer-facing sentence:

        > The benchmark turns secure-code evaluation into adaptive search: it allocates budget across attack surfaces, explores informative CWE combinations inside each surface, and reports capability maps and residual vulnerability patterns rather than a single aggregate score.

        ## Methodological Caveats

        - The runs have different sample sizes, so rates should be preferred over raw counts.
        - The benchmark is search-conditioned: results reflect the adaptive exploration policy.
        - Static analysis tools define the observed vulnerability signal; manual validation or multiple scanner configurations would further strengthen publication claims.
        - Model labels should be stored in future run metadata to remove ambiguity when comparing archived runs.
        """
    ).strip()
    report = "\n".join(
        line[8:] if line.startswith("        ") else line
        for line in report.splitlines()
    )
    (OUT / "report.md").write_text(report + "\n", encoding="utf-8")


def main() -> None:
    PLOTS.mkdir(parents=True, exist_ok=True)
    DATA.mkdir(parents=True, exist_ok=True)
    set_style()
    bundles = model_bundle()
    write_summary_tables(bundles)
    plot_model_overview(bundles)
    plot_surface_success_heatmap(bundles)
    plot_feedback_gain_by_surface(bundles)
    plot_combo_size_degradation(bundles)
    plot_failure_reason_stacks(bundles)
    plot_top_residual_cwes(bundles)
    plot_surface_coverage(bundles)
    plot_cwe_success_heatmap(bundles)
    plot_fixer_resolved_vulnerabilities(bundles)
    plot_persistent_vulnerability_patterns(bundles)
    plot_overall_vulnerability_patterns(bundles)
    plot_persistent_patterns_by_attack_surface(bundles)
    write_report(bundles)


if __name__ == "__main__":
    main()
