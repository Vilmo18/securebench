#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import random
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from scenario_conditions import condition_axis_label, normalize_condition


def _read_jsonl(path: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
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
                out.append(obj)
    return out


def _find_latest_scenario_store(experiments_dir: str) -> Optional[str]:
    best: Optional[Tuple[float, str]] = None
    for dirpath, _dirnames, filenames in os.walk(experiments_dir):
        if "scenario_store.jsonl" not in filenames:
            continue
        path = os.path.join(dirpath, "scenario_store.jsonl")
        try:
            mtime = os.path.getmtime(path)
        except Exception:
            continue
        if best is None or mtime > best[0]:
            best = (mtime, path)
    return best[1] if best else None


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(v)))


def _l2_normalize_rows(x):  # numpy array
    import numpy as np

    norms = np.linalg.norm(x, axis=1, keepdims=True)
    norms[norms == 0.0] = 1.0
    return x / norms


def _build_tfidf_matrix(
    embeddings: List[Dict[str, float]],
    *,
    vocab_size: int = 2048,
    min_df: int = 2,
) -> Tuple["np.ndarray", List[str]]:
    import numpy as np

    n = len(embeddings)
    if n == 0:
        return np.zeros((0, 0), dtype=np.float32), []

    df: Dict[str, int] = defaultdict(int)
    tf_sum: Dict[str, float] = defaultdict(float)
    for emb in embeddings:
        if not isinstance(emb, dict):
            continue
        seen = set()
        for k, v in emb.items():
            if not k:
                continue
            try:
                w = float(v)
            except Exception:
                continue
            if w == 0.0:
                continue
            tf_sum[k] += abs(w)
            if k not in seen:
                seen.add(k)
                df[k] += 1

    # Compute IDF and select a stable, informative vocabulary.
    # Score by total TF-IDF mass across corpus.
    idf: Dict[str, float] = {}
    feat_score: List[Tuple[str, float]] = []
    for feat, dfi in df.items():
        if int(dfi) < int(min_df):
            continue
        # Smooth IDF.
        idf_val = math.log((n + 1.0) / (dfi + 1.0)) + 1.0
        idf[feat] = idf_val
        feat_score.append((feat, float(tf_sum.get(feat, 0.0)) * idf_val))

    feat_score.sort(key=lambda kv: kv[1], reverse=True)
    vocab = [k for k, _ in feat_score[: max(1, int(vocab_size))]]

    idx = {feat: j for j, feat in enumerate(vocab)}
    x = np.zeros((n, len(vocab)), dtype=np.float32)
    for i, emb in enumerate(embeddings):
        if not isinstance(emb, dict):
            continue
        for feat, val in emb.items():
            j = idx.get(feat)
            if j is None:
                continue
            try:
                w = float(val)
            except Exception:
                continue
            if w == 0.0:
                continue
            x[i, j] = float(w) * float(idf.get(feat, 1.0))

    x = _l2_normalize_rows(x)
    return x, vocab


def _pairwise_squared_euclidean(x):  # numpy array [n,d]
    import numpy as np

    if x.size == 0:
        return np.zeros((0, 0), dtype=np.float64)
    sum_x = np.sum(np.square(x), axis=1, keepdims=True)
    d = sum_x + sum_x.T - 2.0 * (x @ x.T)
    d[d < 0.0] = 0.0
    return d.astype(np.float64, copy=False)


def _hbeta(dist_row, beta: float):
    import numpy as np

    p = np.exp(-dist_row * beta)
    p[0] = 0.0  # assume dist_row[0] corresponds to self after we roll; caller controls this
    sum_p = float(np.sum(p))
    if sum_p <= 1e-12:
        sum_p = 1e-12
    p = p / sum_p
    h = math.log(sum_p) + beta * float(np.sum(dist_row * p))
    return float(h), p


def _binary_search_perplexity(dist_i, perplexity: float, *, max_tries: int = 60, tol: float = 1e-5):
    import numpy as np

    # Binary search for beta (1/(2*sigma^2)) such that perplexity matches.
    log_u = math.log(float(perplexity))
    beta_min = -math.inf
    beta_max = math.inf
    beta = 1.0

    # Caller passes dist_i with self at index 0 (so we can zero it in _hbeta).
    for _ in range(max_tries):
        h, this_p = _hbeta(dist_i, beta)
        hdiff = h - log_u
        if abs(hdiff) < tol:
            return this_p
        if hdiff > 0:
            beta_min = beta
            if math.isinf(beta_max):
                beta *= 2.0
            else:
                beta = (beta + beta_max) / 2.0
        else:
            beta_max = beta
            if math.isinf(beta_min):
                beta /= 2.0
            else:
                beta = (beta + beta_min) / 2.0

    # Best-effort final.
    _h, this_p = _hbeta(dist_i, beta)
    return this_p


def _compute_p_matrix(distances, perplexity: float):
    import numpy as np

    n = distances.shape[0]
    p = np.zeros((n, n), dtype=np.float64)
    for i in range(n):
        # Build a row where index 0 is self distance for _hbeta convenience
        dist_i = distances[i].copy()
        # Move self distance to index 0 by swapping.
        if i != 0:
            dist_i[0], dist_i[i] = dist_i[i], dist_i[0]
        this_p = _binary_search_perplexity(dist_i, perplexity)
        # Undo the swap for placement.
        if i != 0:
            this_p[0], this_p[i] = this_p[i], this_p[0]
        p[i, :] = this_p
        p[i, i] = 0.0

    p = (p + p.T) / (2.0 * n)
    p[p < 1e-12] = 1e-12
    return p


def tsne(
    x,  # numpy array [n,d]
    *,
    perplexity: float = 30.0,
    n_iter: int = 900,
    learning_rate: float = 200.0,
    early_exaggeration: float = 12.0,
    random_state: int = 0,
) -> "np.ndarray":
    """
    Minimal t-SNE (vanilla O(N^2)) implementation using only NumPy.
    Works well for small N (few hundred to ~1k points).
    """
    import numpy as np

    n = int(x.shape[0])
    if n == 0:
        return np.zeros((0, 2), dtype=np.float64)
    if n == 1:
        return np.zeros((1, 2), dtype=np.float64)

    # Perplexity constraints (rule of thumb).
    perplexity = float(_clamp(perplexity, 2.0, max(2.0, (n - 1) / 3.0)))
    n_iter = max(250, int(n_iter))

    rng = np.random.default_rng(int(random_state))
    y = rng.normal(loc=0.0, scale=1e-4, size=(n, 2)).astype(np.float64)
    i_y = np.zeros_like(y)
    gains = np.ones_like(y)

    d_high = _pairwise_squared_euclidean(x)
    p = _compute_p_matrix(d_high, perplexity)
    p *= float(early_exaggeration)

    momentum = 0.5
    final_momentum = 0.8
    mom_switch_iter = 250
    exag_stop_iter = 100

    for it in range(1, n_iter + 1):
        d_low = _pairwise_squared_euclidean(y)
        num = 1.0 / (1.0 + d_low)
        np.fill_diagonal(num, 0.0)
        q = num / float(np.sum(num))
        q[q < 1e-12] = 1e-12

        pq = (p - q) * num
        sum_pq = np.sum(pq, axis=1, keepdims=True)
        d_y = 4.0 * (sum_pq * y - (pq @ y))

        # Adaptive gains (common trick for stability).
        gains = (gains + 0.2) * ((d_y > 0.0) != (i_y > 0.0)) + (gains * 0.8) * (
            (d_y > 0.0) == (i_y > 0.0)
        )
        gains[gains < 0.01] = 0.01

        i_y = momentum * i_y - float(learning_rate) * (gains * d_y)
        y = y + i_y
        y = y - np.mean(y, axis=0, keepdims=True)

        if it == exag_stop_iter:
            p = p / float(early_exaggeration)
        if it == mom_switch_iter:
            momentum = final_momentum

    return y


@dataclass
class Point:
    x: float
    y: float
    label: str
    difficulty: str
    phase: str
    bucket: str
    title: str
    hash: str
    concepts: str

def _level_key(value: Any) -> str:
    return normalize_condition(value)


def _stable_color(label: str) -> str:
    if not label or label == "unknown":
        return "#7f8c8d"
    return "#" + hashlib.sha256(label.encode("utf-8", errors="ignore")).hexdigest()[:6]


def _phase_color_map() -> Dict[str, str]:
    return {
        "PHASE_ONE_5": "#3498db",
        "PHASE_TWO_10": "#9b59b6",
        "PHASE_THREE": "#e67e22",
        "unknown": "#7f8c8d",
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Plot t-SNE clusters of generated scenario embeddings (scenario_store.jsonl)."
    )
    ap.add_argument(
        "--scenario-store",
        default=None,
        help="Path to scenario_store.jsonl. If omitted, the latest under experiments/ is used.",
    )
    ap.add_argument(
        "--experiments-dir",
        default=os.path.join(os.getcwd(), "experiments"),
        help="Where to search for scenario_store.jsonl when --scenario-store is omitted.",
    )
    ap.add_argument("--max-samples", type=int, default=500, help="Subsample for speed.")
    ap.add_argument("--vocab-size", type=int, default=2048, help="TF-IDF vocabulary size.")
    ap.add_argument("--min-df", type=int, default=2, help="Min document frequency for vocab.")
    ap.add_argument("--perplexity", type=float, default=30.0)
    ap.add_argument("--n-iter", type=int, default=900)
    ap.add_argument("--learning-rate", type=float, default=200.0)
    ap.add_argument("--early-exaggeration", type=float, default=12.0)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument(
        "--color-by",
        choices=["difficulty", "axis", "phase", "bucket"],
        default="difficulty",
        help="How to color points.",
    )
    ap.add_argument(
        "--out-dir",
        default=None,
        help="Output directory (defaults to the scenario_store.jsonl directory).",
    )
    ap.add_argument("--out-prefix", default="scenario_tsne")
    args = ap.parse_args()

    store = args.scenario_store
    if not store:
        store = _find_latest_scenario_store(os.path.abspath(str(args.experiments_dir)))
    if not store or not os.path.exists(store):
        print("Could not find scenario_store.jsonl. Pass --scenario-store.", file=sys.stderr)
        return 2

    rows = _read_jsonl(store)
    if not rows:
        print(f"No records found in {store}", file=sys.stderr)
        return 2

    # Subsample for speed (stable).
    rng = random.Random(int(args.seed))
    if len(rows) > int(args.max_samples) > 0:
        rows = rng.sample(rows, int(args.max_samples))

    embeddings: List[Dict[str, float]] = []
    meta: List[Dict[str, Any]] = []
    for r in rows:
        emb = r.get("embedding")
        if not isinstance(emb, dict):
            emb = {}
        # Convert values to float (best-effort).
        emb2: Dict[str, float] = {}
        for k, v in emb.items():
            if not k:
                continue
            try:
                emb2[str(k)] = float(v)
            except Exception:
                continue
        embeddings.append(emb2)
        meta.append(r)

    try:
        import numpy as np
        import matplotlib.pyplot as plt
    except Exception as e:
        print(
            "Missing numpy/matplotlib. Run inside your venv (e.g. `.venv/bin/python`) "
            f"or install deps. Error: {e}",
            file=sys.stderr,
        )
        return 2

    x, vocab = _build_tfidf_matrix(
        embeddings, vocab_size=int(args.vocab_size), min_df=int(args.min_df)
    )
    y = tsne(
        x,
        perplexity=float(args.perplexity),
        n_iter=int(args.n_iter),
        learning_rate=float(args.learning_rate),
        early_exaggeration=float(args.early_exaggeration),
        random_state=int(args.seed),
    )

    out_dir = args.out_dir or os.path.dirname(os.path.abspath(store))
    os.makedirs(out_dir, exist_ok=True)
    out_csv = os.path.join(out_dir, f"{args.out_prefix}_points.csv")
    out_png = os.path.join(out_dir, f"{args.out_prefix}_{args.color_by}.png")

    # Build plot labels/colors.
    phase_colors = _phase_color_map()

    labels: List[str] = []
    colors: List[str] = []
    points: List[Point] = []
    for i, r in enumerate(meta):
        m = r.get("meta") if isinstance(r.get("meta"), dict) else {}
        difficulty = _level_key(m.get("difficulty"))
        condition_axis = condition_axis_label(difficulty)
        phase = str(m.get("phase") or "unknown").strip() or "unknown"
        bucket = str(r.get("bucket") or "unknown").strip() or "unknown"
        title = str(r.get("title") or "")
        h = str(r.get("hash") or "")
        concepts = m.get("concepts")
        if isinstance(concepts, list):
            concepts_s = ",".join(str(c) for c in concepts)
        else:
            concepts_s = ""

        if args.color_by == "difficulty":
            label = difficulty
            color = _stable_color(difficulty)
        elif args.color_by == "axis":
            label = condition_axis
            color = _stable_color(condition_axis)
        elif args.color_by == "phase":
            label = phase
            color = phase_colors.get(phase, phase_colors["unknown"])
        else:
            label = bucket
            color = _stable_color(label)

        labels.append(label)
        colors.append(color)
        points.append(
            Point(
                x=float(y[i, 0]),
                y=float(y[i, 1]),
                label=label,
                difficulty=difficulty,
                phase=phase,
                bucket=bucket,
                title=title,
                hash=h,
                concepts=concepts_s,
            )
        )

    # Save points for analysis.
    with open(out_csv, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "x",
                "y",
                "label",
                "difficulty",
                "condition_axis",
                "phase",
                "bucket",
                "hash",
                "title",
                "concepts",
            ]
        )
        for p in points:
            w.writerow(
                [
                    p.x,
                    p.y,
                    p.label,
                    p.difficulty,
                    condition_axis_label(p.difficulty),
                    p.phase,
                    p.bucket,
                    p.hash,
                    p.title,
                    p.concepts,
                ]
            )

    # Plot.
    plt.figure(figsize=(11, 8))
    plt.scatter(y[:, 0], y[:, 1], c=colors, s=35, alpha=0.75, linewidths=0.0)
    plt.title(f"t-SNE of scenario embeddings (n={len(points)}) — color_by={args.color_by}")
    plt.xlabel("t-SNE 1")
    plt.ylabel("t-SNE 2")
    plt.grid(True, alpha=0.2)

    # Legend for small label sets.
    counts = Counter(labels)
    if len(counts) <= 12:
        handles = []
        for lab, _cnt in counts.most_common():
            c = colors[labels.index(lab)]
            handles.append(plt.Line2D([0], [0], marker="o", color="w", label=f"{lab} ({_cnt})", markerfacecolor=c, markersize=8))
        plt.legend(handles=handles, frameon=True, facecolor="white", framealpha=0.9)

    plt.tight_layout()
    plt.savefig(out_png, dpi=200)

    # Save vocab for interpretability.
    with open(os.path.join(out_dir, f"{args.out_prefix}_vocab.json"), "w", encoding="utf-8") as f:
        json.dump({"vocab": vocab}, f, indent=2, ensure_ascii=False)

    print("Wrote:")
    print(f"- points: {out_csv}")
    print(f"- plot:   {out_png}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
