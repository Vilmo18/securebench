#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
import time
from collections import Counter
from typing import Any, Dict, List, Optional, Sequence, Tuple

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from scenario_conditions import condition_axis_label, normalize_condition
from scenario_dedup import semantic_embedding


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


def _read_cache_jsonl(path: str) -> Dict[str, List[float]]:
    if not path or not os.path.exists(path):
        return {}
    out: Dict[str, List[float]] = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                if not isinstance(rec, dict):
                    continue
                h = str(rec.get("hash") or "").strip()
                emb = rec.get("embedding")
                if not h or not isinstance(emb, list):
                    continue
                try:
                    out[h] = [float(x) for x in emb]
                except Exception:
                    continue
    except Exception:
        return out
    return out


def _append_cache(path: str, h: str, model: str, embedding: Sequence[float]) -> None:
    if not path:
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    rec = {
        "hash": h,
        "model": model,
        "created_at": time.time(),
        "embedding": list(embedding),
    }
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _l2_normalize_rows(x):  # numpy array
    import numpy as np

    norms = np.linalg.norm(x, axis=1, keepdims=True)
    norms[norms == 0.0] = 1.0
    return x / norms


def _pca_reduce(x, n_components: int):  # numpy array
    import numpy as np

    n_components = int(n_components)
    if n_components <= 0:
        return x
    if x.size == 0:
        return x
    if n_components >= int(x.shape[1]):
        return x

    x0 = x - np.mean(x, axis=0, keepdims=True)
    # SVD on (n x d) with n << d is usually OK for a few hundred points.
    _u, _s, vt = np.linalg.svd(x0, full_matrices=False)
    comps = vt[:n_components, :]
    return x0 @ comps.T


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
    p[0] = 0.0
    sum_p = float(np.sum(p))
    if sum_p <= 1e-12:
        sum_p = 1e-12
    p = p / sum_p
    h = float(np.log(sum_p) + beta * float(np.sum(dist_row * p)))
    return h, p


def _binary_search_perplexity(dist_i, perplexity: float, *, max_tries: int = 60, tol: float = 1e-5):
    log_u = float(perplexity)
    log_u = float(__import__("math").log(log_u))
    beta_min = -float("inf")
    beta_max = float("inf")
    beta = 1.0

    for _ in range(max_tries):
        h, this_p = _hbeta(dist_i, beta)
        hdiff = h - log_u
        if abs(hdiff) < tol:
            return this_p
        if hdiff > 0:
            beta_min = beta
            if beta_max == float("inf"):
                beta *= 2.0
            else:
                beta = (beta + beta_max) / 2.0
        else:
            beta_max = beta
            if beta_min == -float("inf"):
                beta /= 2.0
            else:
                beta = (beta + beta_min) / 2.0

    _h, this_p = _hbeta(dist_i, beta)
    return this_p


def _compute_p_matrix(distances, perplexity: float):
    import numpy as np

    n = int(distances.shape[0])
    p = np.zeros((n, n), dtype=np.float64)
    for i in range(n):
        dist_i = distances[i].copy()
        if i != 0:
            dist_i[0], dist_i[i] = dist_i[i], dist_i[0]
        this_p = _binary_search_perplexity(dist_i, perplexity)
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
    import numpy as np

    n = int(x.shape[0])
    if n == 0:
        return np.zeros((0, 2), dtype=np.float64)
    if n == 1:
        return np.zeros((1, 2), dtype=np.float64)

    # Keep perplexity in a safe range.
    perplexity = float(max(2.0, min(float(perplexity), max(2.0, (n - 1) / 3.0))))
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


def _default_huggingface_base_url() -> Optional[str]:
    return os.getenv("HUGGINGFACE_EMBEDDINGS_BASE_URL")


def _preprocess_prompt_text(
    text: str,
    *,
    strip_difficulty_line: bool = False,
    strip_title_line: bool = False,
) -> str:
    """
    Preprocess scenario text before embedding.

    Note: if you want to probe whether embeddings *semantically* separate difficulty levels, you
    should strip the explicit difficulty line to avoid label leakage.
    """
    s = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
    lines = s.splitlines()
    out: list[str] = []
    for line in lines:
        t = line.strip()
        if strip_difficulty_line and t.lower().startswith(
            ("attack surface:", "attack surface group:", "difficulty:", "difficulty group:", "level:", "testing condition:", "condition axis:")
        ):
            continue
        if strip_title_line and t.startswith("## "):
            continue
        out.append(line)
    return "\n".join(out).strip()


def _stable_color(label: str) -> str:
    return "#" + hashlib.sha256(label.encode("utf-8", errors="ignore")).hexdigest()[:6]


def _level_key(value: Any) -> str:
    return normalize_condition(value)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Compute LLM embeddings for generated scenarios, then run t-SNE and plot clusters."
    )
    ap.add_argument("--scenario-store", required=True, help="Path to scenario_store.jsonl")
    ap.add_argument(
        "--text-field",
        choices=["problem_statement", "normalized"],
        default="problem_statement",
        help="Which field to embed.",
    )
    ap.add_argument(
        "--embedding-model",
        default="BAAI/bge-small-en-v1.5",
        help="Hugging Face feature-extraction model name.",
    )
    ap.add_argument(
        "--base-url",
        default=_default_huggingface_base_url(),
        help="Optional dedicated Hugging Face Inference Endpoint URL.",
    )
    ap.add_argument(
        "--api-key",
        default=os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACEHUB_API_TOKEN"),
        help="Hugging Face token (default: $HF_TOKEN).",
    )
    ap.add_argument("--timeout", type=int, default=120)
    ap.add_argument("--batch-size", type=int, default=8)
    ap.add_argument("--max-chars", type=int, default=6000)
    ap.add_argument("--max-samples", type=int, default=400)
    ap.add_argument(
        "--strip-difficulty-line",
        action="store_true",
        help="Remove the explicit testing-condition/axis line before embedding (avoids label leakage).",
    )
    ap.add_argument(
        "--strip-title-line",
        action="store_true",
        help="Remove the leading markdown title line starting with '## ' before embedding.",
    )
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--pca-dim", type=int, default=0, help="Optional PCA dim before t-SNE (0 disables).")
    ap.add_argument("--perplexity", type=float, default=30.0)
    ap.add_argument("--n-iter", type=int, default=900)
    ap.add_argument("--learning-rate", type=float, default=200.0)
    ap.add_argument("--early-exaggeration", type=float, default=12.0)
    ap.add_argument(
        "--color-by",
        choices=["difficulty", "axis", "phase", "bucket", "concepts"],
        default="difficulty",
    )
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--out-prefix", default="scenario_tsne_llm")
    ap.add_argument("--cache", default=None, help="Embeddings cache JSONL path.")
    args = ap.parse_args()

    store_path = os.path.abspath(str(args.scenario_store))
    rows = _read_jsonl(store_path)
    if not rows:
        print(f"No records found in {store_path}", file=sys.stderr)
        return 2

    # Subsample deterministically for speed (keep most recent first).
    if int(args.max_samples) > 0 and len(rows) > int(args.max_samples):
        rows = rows[-int(args.max_samples) :]

    out_dir = args.out_dir or os.path.dirname(store_path)
    os.makedirs(out_dir, exist_ok=True)

    cache_path = args.cache
    if not cache_path:
        safe_model = "".join([c if c.isalnum() or c in "-_." else "_" for c in str(args.embedding_model)])
        cache_path = os.path.join(out_dir, f"{args.out_prefix}_emb_cache_{safe_model}.jsonl")

    cache = _read_cache_jsonl(cache_path)

    # Build embedding requests (hash + text).
    items: List[Tuple[str, str, Dict[str, Any]]] = []
    for r in rows:
        h = str(r.get("hash") or "").strip()
        if not h:
            continue
        text = r.get(args.text_field)
        if not isinstance(text, str) or not text.strip():
            continue
        text = _preprocess_prompt_text(
            text,
            strip_difficulty_line=bool(args.strip_difficulty_line),
            strip_title_line=bool(args.strip_title_line),
        )
        if not text:
            continue
        if int(args.max_chars) > 0 and len(text) > int(args.max_chars):
            text = text[: int(args.max_chars)]
        items.append((h, text, r))

    if not items:
        print("No embeddable items found (missing hash/text).", file=sys.stderr)
        return 2

    # Fetch embeddings.
    pending: List[Tuple[str, str, Dict[str, Any]]] = [it for it in items if it[0] not in cache]
    if pending:
        print(f"Embedding {len(pending)}/{len(items)} new scenarios (cache hit {len(items) - len(pending)}).")
    else:
        print(f"All {len(items)} embeddings loaded from cache.")

    for i in range(0, len(pending), max(1, int(args.batch_size))):
        batch = pending[i : i + max(1, int(args.batch_size))]
        for h, text_value, _row in batch:
            emb, _norm = semantic_embedding(
                text_value,
                base_url=args.base_url,
                model=str(args.embedding_model),
                api_key=args.api_key,
                timeout_seconds=int(args.timeout),
                max_chars=int(args.max_chars),
            )
            if not emb:
                raise SystemExit(f"No embedding returned for scenario {h}.")
            cache[h] = emb
            _append_cache(cache_path, h, str(args.embedding_model), emb)

    # Build matrix in consistent item order.
    hashes: List[str] = []
    metas: List[Dict[str, Any]] = []
    vecs: List[List[float]] = []
    for h, _t, r in items:
        emb = cache.get(h)
        if not emb:
            continue
        hashes.append(h)
        metas.append(r)
        vecs.append(emb)

    if not vecs:
        print("No embeddings available after caching step.", file=sys.stderr)
        return 2

    try:
        import numpy as np
        import matplotlib.pyplot as plt
    except Exception as e:
        print(
            "Missing numpy/matplotlib. Run inside your venv (e.g. `.venv/bin/python`). "
            f"Error: {e}",
            file=sys.stderr,
        )
        return 2

    x = np.array(vecs, dtype=np.float32)
    x = _l2_normalize_rows(x)
    if int(args.pca_dim) > 0:
        x = _pca_reduce(x, int(args.pca_dim)).astype(np.float32, copy=False)
        x = _l2_normalize_rows(x)

    y = tsne(
        x,
        perplexity=float(args.perplexity),
        n_iter=int(args.n_iter),
        learning_rate=float(args.learning_rate),
        early_exaggeration=float(args.early_exaggeration),
        random_state=int(args.seed),
    )

    # Labels/colors.
    labels: List[str] = []
    colors: List[str] = []
    phases: List[str] = []
    difficulties: List[str] = []
    axes: List[str] = []
    buckets: List[str] = []
    concepts_list: List[str] = []
    titles: List[str] = []

    for r in metas:
        m = r.get("meta") if isinstance(r.get("meta"), dict) else {}
        difficulty = _level_key(m.get("difficulty"))
        condition_axis = condition_axis_label(difficulty)
        phase = str(m.get("phase") or "unknown").strip() or "unknown"
        bucket = str(r.get("bucket") or "unknown").strip() or "unknown"
        title = str(r.get("title") or "")
        concepts = m.get("concepts")
        concepts_s = ",".join(str(c) for c in concepts) if isinstance(concepts, list) else ""

        if args.color_by == "difficulty":
            label = difficulty
            color = _stable_color(difficulty if difficulty != "unknown" else "unknown")
        elif args.color_by == "axis":
            label = condition_axis
            color = _stable_color(condition_axis if condition_axis != "Unknown" else "unknown")
        elif args.color_by == "phase":
            label = phase
            color = _stable_color(phase)
        elif args.color_by == "concepts":
            label = concepts_s or "unknown"
            color = _stable_color(label)
        else:
            label = bucket
            color = _stable_color(bucket)

        labels.append(label)
        colors.append(color)
        phases.append(phase)
        difficulties.append(difficulty)
        axes.append(condition_axis)
        buckets.append(bucket)
        concepts_list.append(concepts_s)
        titles.append(title)

    out_csv = os.path.join(out_dir, f"{args.out_prefix}_points.csv")
    out_png = os.path.join(out_dir, f"{args.out_prefix}_{args.color_by}.png")

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
                "embedding_model",
                "text_field",
            ]
        )
        for i, h in enumerate(hashes):
            w.writerow(
                [
                    float(y[i, 0]),
                    float(y[i, 1]),
                    labels[i],
                    difficulties[i],
                    axes[i],
                    phases[i],
                    buckets[i],
                    h,
                    titles[i],
                    concepts_list[i],
                    str(args.embedding_model),
                    str(args.text_field),
                ]
            )

    plt.figure(figsize=(11, 8))
    plt.scatter(y[:, 0], y[:, 1], c=colors, s=35, alpha=0.75, linewidths=0.0)
    plt.title(
        f"t-SNE of LLM embeddings (n={len(hashes)}) — model={args.embedding_model} field={args.text_field} color_by={args.color_by}"
    )
    plt.xlabel("t-SNE 1")
    plt.ylabel("t-SNE 2")
    plt.grid(True, alpha=0.2)

    counts = Counter(labels)
    if len(counts) <= 12:
        handles = []
        for lab, cnt in counts.most_common():
            c = colors[labels.index(lab)]
            handles.append(
                plt.Line2D(
                    [0],
                    [0],
                    marker="o",
                    color="w",
                    label=f"{lab} ({cnt})",
                    markerfacecolor=c,
                    markersize=8,
                )
            )
        plt.legend(handles=handles, frameon=True, facecolor="white", framealpha=0.9)

    plt.tight_layout()
    plt.savefig(out_png, dpi=200)

    print("Wrote:")
    print(f"- cache:  {cache_path}")
    print(f"- points: {out_csv}")
    print(f"- plot:   {out_png}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
