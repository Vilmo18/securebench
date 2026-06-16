#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import os
import random
import sys
from collections import Counter
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from scenario_conditions import (
    axis_order,
    condition_axis_label,
    condition_order_index,
    normalize_condition,
)


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


def _read_emb_cache(path: str) -> Dict[str, List[float]]:
    out: Dict[str, List[float]] = {}
    for rec in _read_jsonl(path):
        h = str(rec.get("hash") or "").strip()
        emb = rec.get("embedding")
        if not h or not isinstance(emb, list):
            continue
        try:
            out[h] = [float(x) for x in emb]
        except Exception:
            continue
    return out


def _find_latest_cache(dir_path: str) -> Optional[str]:
    best: Optional[Tuple[float, str]] = None
    try:
        for name in os.listdir(dir_path):
            if "emb_cache" not in name or not name.endswith(".jsonl"):
                continue
            path = os.path.join(dir_path, name)
            try:
                mtime = os.path.getmtime(path)
            except Exception:
                continue
            if best is None or mtime > best[0]:
                best = (mtime, path)
    except Exception:
        return None
    return best[1] if best else None


def _condition_from_record(rec: Dict[str, Any]) -> Optional[str]:
    meta = rec.get("meta")
    if isinstance(meta, dict):
        d = meta.get("difficulty")
        if isinstance(d, str) and d.strip():
            return normalize_condition(d)
    return None


def _axis_from_record(rec: Dict[str, Any]) -> Optional[str]:
    condition = _condition_from_record(rec)
    if not condition:
        return None
    axis = condition_axis_label(condition)
    return axis if axis != "Unknown" else None


def _l2_normalize_rows(x):  # numpy array
    import numpy as np

    norms = np.linalg.norm(x, axis=1, keepdims=True)
    norms[norms == 0.0] = 1.0
    return x / norms


def _standardize_fit(x):  # numpy array
    import numpy as np

    mean = np.mean(x, axis=0, keepdims=True)
    std = np.std(x, axis=0, keepdims=True)
    std[std == 0.0] = 1.0
    return mean, std


def _standardize_apply(x, mean, std):  # numpy array
    return (x - mean) / std


def _stratified_kfold_indices(
    labels: Sequence[int],
    *,
    k_folds: int = 5,
    seed: int = 0,
) -> List[List[int]]:
    """
    Returns list of folds; each fold is a list of indices.
    """
    k_folds = max(2, int(k_folds))
    by_class: Dict[int, List[int]] = {}
    for i, y in enumerate(labels):
        by_class.setdefault(int(y), []).append(i)

    rng = random.Random(int(seed))
    folds: List[List[int]] = [[] for _ in range(k_folds)]
    for _cls, idxs in sorted(by_class.items(), key=lambda kv: kv[0]):
        rng.shuffle(idxs)
        for j, idx in enumerate(idxs):
            folds[j % k_folds].append(idx)

    for f in folds:
        f.sort()
    return folds


def _confusion_matrix(y_true: Sequence[int], y_pred: Sequence[int], num_classes: int) -> List[List[int]]:
    m = [[0 for _ in range(num_classes)] for _ in range(num_classes)]
    for t, p in zip(y_true, y_pred):
        ti = int(t)
        pi = int(p)
        if 0 <= ti < num_classes and 0 <= pi < num_classes:
            m[ti][pi] += 1
    return m


def _per_class_prf(cm: List[List[int]]) -> Dict[int, Dict[str, float]]:
    k = len(cm)
    out: Dict[int, Dict[str, float]] = {}
    for c in range(k):
        tp = cm[c][c]
        fp = sum(cm[r][c] for r in range(k) if r != c)
        fn = sum(cm[c][r] for r in range(k) if r != c)
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
        support = sum(cm[c])
        out[c] = {
            "precision": float(precision),
            "recall": float(recall),
            "f1": float(f1),
            "support": float(support),
        }
    return out


def _macro_avg(per_class: Dict[int, Dict[str, float]], key: str) -> float:
    if not per_class:
        return 0.0
    vals = [float(v.get(key) or 0.0) for v in per_class.values()]
    return float(sum(vals) / len(vals)) if vals else 0.0


def _accuracy(cm: List[List[int]]) -> float:
    total = sum(sum(r) for r in cm)
    if total <= 0:
        return 0.0
    correct = sum(cm[i][i] for i in range(len(cm)))
    return float(correct / total)


def _knn_predict(
    x_train,  # numpy array
    y_train: Sequence[int],
    x_test,  # numpy array
    *,
    k: int = 5,
    metric: str = "cosine",
) -> List[int]:
    import numpy as np

    k = max(1, int(k))
    y_train_i = [int(y) for y in y_train]
    num_classes = len(set(y_train_i))

    if metric == "cosine":
        # Assume L2-normalized rows.
        sims = x_test @ x_train.T  # [nt, ntr]
        # Higher is better → convert to "distance" by negating for argpartition.
        order = np.argpartition(-sims, kth=min(k - 1, sims.shape[1] - 1), axis=1)[:, :k]
        preds: List[int] = []
        for i in range(order.shape[0]):
            neigh = order[i]
            votes: Dict[int, List[float]] = {}
            for j in neigh:
                cls = y_train_i[int(j)]
                votes.setdefault(cls, []).append(float(sims[i, int(j)]))
            # majority vote; tie-break by mean similarity
            best_cls = None
            best = (-10**9, -10**9.0)  # (count, mean_sim)
            for cls, ss in votes.items():
                count = len(ss)
                mean_sim = float(sum(ss) / count) if count else -1e9
                cand = (count, mean_sim)
                if cand > best:
                    best = cand
                    best_cls = cls
            preds.append(int(best_cls) if best_cls is not None else 0)
        return preds

    # L2 metric.
    preds2: List[int] = []
    for i in range(x_test.shape[0]):
        d = np.sum((x_train - x_test[i : i + 1, :]) ** 2, axis=1)
        nn = np.argpartition(d, kth=min(k - 1, d.shape[0] - 1))[:k]
        votes: Dict[int, List[float]] = {}
        for j in nn:
            cls = y_train_i[int(j)]
            votes.setdefault(cls, []).append(float(d[int(j)]))
        # majority vote; tie-break by mean *smallest* distance
        best_cls = None
        best = (-10**9, 10**9.0)  # (count, mean_dist)
        for cls, ds in votes.items():
            count = len(ds)
            mean_dist = float(sum(ds) / count) if count else 1e9
            cand = (count, -mean_dist)
            if cand > (best[0], -best[1]):
                best = (count, mean_dist)
                best_cls = cls
        preds2.append(int(best_cls) if best_cls is not None else 0)
    return preds2


def _softmax(logits):  # numpy array
    import numpy as np

    z = logits - np.max(logits, axis=1, keepdims=True)
    e = np.exp(z)
    s = np.sum(e, axis=1, keepdims=True)
    s[s == 0.0] = 1.0
    return e / s


def _linear_probe_fit(
    x_train,  # numpy array [n,d]
    y_train: Sequence[int],
    *,
    num_classes: int,
    lr: float = 0.2,
    epochs: int = 600,
    l2: float = 1e-2,
    seed: int = 0,
):
    """
    Multiclass logistic regression (softmax) with batch GD.
    """
    import numpy as np

    rng = np.random.default_rng(int(seed))

    n, d = x_train.shape
    y = np.array([int(v) for v in y_train], dtype=np.int64)

    # Add bias.
    xb = np.concatenate([x_train, np.ones((n, 1), dtype=x_train.dtype)], axis=1)
    w = rng.normal(loc=0.0, scale=0.01, size=(d + 1, int(num_classes))).astype(np.float64)

    y_onehot = np.zeros((n, int(num_classes)), dtype=np.float64)
    y_onehot[np.arange(n), y] = 1.0

    lr = float(lr)
    l2 = float(l2)
    epochs = max(50, int(epochs))

    for _ in range(epochs):
        logits = xb @ w
        p = _softmax(logits)
        grad = (xb.T @ (p - y_onehot)) / float(n)
        grad += l2 * w
        w -= lr * grad

    return w


def _linear_probe_predict(x_test, w):  # numpy array, weights
    import numpy as np

    n = x_test.shape[0]
    xb = np.concatenate([x_test, np.ones((n, 1), dtype=x_test.dtype)], axis=1)
    logits = xb @ w
    return [int(i) for i in np.argmax(logits, axis=1).tolist()]


@dataclass
class FoldMetrics:
    accuracy: float
    macro_f1: float


def _mean_std(values: Sequence[float]) -> Dict[str, float]:
    if not values:
        return {"mean": 0.0, "std": 0.0}
    m = float(sum(values) / len(values))
    v = float(sum((x - m) ** 2 for x in values) / max(1, (len(values) - 1))) if len(values) > 1 else 0.0
    return {"mean": m, "std": float(math.sqrt(v))}


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Probe whether scenario attack surfaces or exact attack-surface labels are encoded in embeddings."
    )
    ap.add_argument("--scenario-store", required=True, help="Path to scenario_store.jsonl")
    ap.add_argument(
        "--embedding-cache",
        default=None,
        help="Path to *_emb_cache_*.jsonl from plot_scenario_tsne_llm_repr.py (dense LLM embeddings). "
        "If omitted, picks the newest cache in the same directory as scenario_store.",
    )
    ap.add_argument("--method", choices=["knn", "linear"], default="linear")
    ap.add_argument("--k", type=int, default=7, help="k for kNN (when --method knn)")
    ap.add_argument("--metric", choices=["cosine", "l2"], default="cosine")
    ap.add_argument("--k-folds", type=int, default=5)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument(
        "--normalize",
        choices=["l2", "standardize", "none"],
        default="l2",
        help="How to normalize embeddings per fold.",
    )
    ap.add_argument("--lr", type=float, default=0.2, help="Learning rate for linear probe")
    ap.add_argument("--epochs", type=int, default=600, help="Epochs for linear probe")
    ap.add_argument("--l2", type=float, default=1e-2, help="L2 weight decay for linear probe")
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--out-prefix", default="difficulty_probe")
    ap.add_argument(
        "--target",
        choices=["axis", "condition"],
        default="axis",
        help="Predict attack surface (default) or exact axis label.",
    )
    args = ap.parse_args()

    store_path = os.path.abspath(str(args.scenario_store))
    if not os.path.exists(store_path):
        print(f"scenario_store not found: {store_path}", file=sys.stderr)
        return 2

    rows = _read_jsonl(store_path)
    if not rows:
        print(f"No records found in {store_path}", file=sys.stderr)
        return 2

    out_dir = args.out_dir or os.path.dirname(store_path)
    os.makedirs(out_dir, exist_ok=True)

    cache_path = args.embedding_cache
    if not cache_path:
        cache_path = _find_latest_cache(out_dir)
    if not cache_path or not os.path.exists(cache_path):
        print(
            "No embedding cache found. Run plot_scenario_tsne_llm_repr.py first to create *_emb_cache_*.jsonl, "
            "then pass --embedding-cache.",
            file=sys.stderr,
        )
        return 2

    cache_path = os.path.abspath(str(cache_path))
    emb_by_hash = _read_emb_cache(cache_path)
    if not emb_by_hash:
        print(f"No embeddings found in cache: {cache_path}", file=sys.stderr)
        return 2

    # Build dataset: align scenario_store rows with embeddings by hash.
    x_list: List[List[float]] = []
    y_labels: List[str] = []
    used_hashes: List[str] = []
    for r in rows:
        h = str(r.get("hash") or "").strip()
        if not h:
            continue
        label = _axis_from_record(r) if args.target == "axis" else _condition_from_record(r)
        if not label:
            continue
        emb = emb_by_hash.get(h)
        if not emb:
            continue
        x_list.append(emb)
        y_labels.append(label)
        used_hashes.append(h)

    if not x_list:
        print("No matching (hash,label,embedding) triples found.", file=sys.stderr)
        return 2

    observed_labels = sorted(set(y_labels))
    if args.target == "axis":
        label_order = [label for label in axis_order() if label in set(observed_labels)]
        label_order += [label for label in observed_labels if label not in set(label_order)]
    else:
        label_order = sorted(
            observed_labels,
            key=lambda value: (condition_order_index(value), str(value)),
        )
    label_to_id = {lab: i for i, lab in enumerate(label_order)}
    y = [label_to_id[lab] for lab in y_labels]
    num_classes = len(label_order)

    dist = Counter(y_labels)
    majority_acc = max(dist.values()) / len(y_labels) if y_labels else 0.0

    try:
        import numpy as np
        import matplotlib.pyplot as plt
    except Exception as e:
        print(
            "Missing numpy/matplotlib. Run inside your venv (e.g. `/home/kira/.venv/bin/python`). "
            f"Error: {e}",
            file=sys.stderr,
        )
        return 2

    x = np.array(x_list, dtype=np.float32)

    folds = _stratified_kfold_indices(y, k_folds=int(args.k_folds), seed=int(args.seed))
    all_true: List[int] = []
    all_pred: List[int] = []
    fold_metrics: List[FoldMetrics] = []

    for fold_id, test_idx in enumerate(folds, start=1):
        test_set = set(test_idx)
        train_idx = [i for i in range(len(y)) if i not in test_set]
        if not train_idx or not test_idx:
            continue

        x_train = x[train_idx]
        x_test = x[test_idx]
        y_train = [y[i] for i in train_idx]
        y_test = [y[i] for i in test_idx]

        if args.normalize == "l2":
            x_train_n = _l2_normalize_rows(x_train.astype(np.float64))
            x_test_n = _l2_normalize_rows(x_test.astype(np.float64))
        elif args.normalize == "standardize":
            mean, std = _standardize_fit(x_train.astype(np.float64))
            x_train_n = _standardize_apply(x_train.astype(np.float64), mean, std)
            x_test_n = _standardize_apply(x_test.astype(np.float64), mean, std)
            x_train_n = _l2_normalize_rows(x_train_n)
            x_test_n = _l2_normalize_rows(x_test_n)
        else:
            x_train_n = x_train.astype(np.float64)
            x_test_n = x_test.astype(np.float64)

        if args.method == "knn":
            y_pred = _knn_predict(
                x_train_n,
                y_train,
                x_test_n,
                k=int(args.k),
                metric=str(args.metric),
            )
        else:
            w = _linear_probe_fit(
                x_train_n,
                y_train,
                num_classes=num_classes,
                lr=float(args.lr),
                epochs=int(args.epochs),
                l2=float(args.l2),
                seed=int(args.seed) + fold_id,
            )
            y_pred = _linear_probe_predict(x_test_n, w)

        all_true.extend(y_test)
        all_pred.extend(y_pred)

        cm_f = _confusion_matrix(y_test, y_pred, num_classes)
        per_f = _per_class_prf(cm_f)
        fold_metrics.append(
            FoldMetrics(
                accuracy=_accuracy(cm_f),
                macro_f1=_macro_avg(per_f, "f1"),
            )
        )

    cm = _confusion_matrix(all_true, all_pred, num_classes)
    per = _per_class_prf(cm)

    acc = _accuracy(cm)
    macro_f1 = _macro_avg(per, "f1")

    out = {
        "n": len(y_labels),
        "target": args.target,
        "label_distribution": {k: int(v) for k, v in sorted(dist.items(), key=lambda kv: label_to_id[kv[0]])},
        "majority_baseline_accuracy": float(majority_acc),
        "method": str(args.method),
        "metric": str(args.metric),
        "k_folds": int(args.k_folds),
        "normalize": str(args.normalize),
        "embedding_cache": cache_path,
        "metrics": {
            "accuracy": float(acc),
            "macro_f1": float(macro_f1),
            "fold_accuracy": _mean_std([m.accuracy for m in fold_metrics]),
            "fold_macro_f1": _mean_std([m.macro_f1 for m in fold_metrics]),
        },
        "per_class": {
            label_order[c]: {
                "precision": float(v["precision"]),
                "recall": float(v["recall"]),
                "f1": float(v["f1"]),
                "support": int(v["support"]),
            }
            for c, v in per.items()
        },
        "confusion_matrix": {
            "labels": list(label_order),
            "matrix": cm,
        },
    }

    out_json = os.path.join(out_dir, f"{args.out_prefix}_report.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)

    # Plot confusion matrix (normalized by true class).
    cm_arr = np.array(cm, dtype=np.float64)
    row_sums = cm_arr.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0.0] = 1.0
    cm_norm = cm_arr / row_sums

    fig_w = 7.5
    fig_h = 6.0
    plt.figure(figsize=(fig_w, fig_h))
    plt.imshow(cm_norm, cmap="Blues", vmin=0.0, vmax=1.0)
    plt.title(f"{args.target.title()} probe — {args.method} (acc={acc:.3f}, macroF1={macro_f1:.3f})")
    plt.xlabel("Predicted")
    plt.ylabel("True")
    plt.xticks(range(num_classes), [d.replace(" ", "\n") for d in label_order], rotation=0)
    plt.yticks(range(num_classes), [d.replace(" ", "\n") for d in label_order])
    plt.colorbar(fraction=0.046, pad=0.04, label="Row-normalized")

    for i in range(num_classes):
        for j in range(num_classes):
            val = cm_norm[i, j]
            count = int(cm_arr[i, j])
            plt.text(j, i, f"{val:.2f}\n({count})", ha="center", va="center", fontsize=8)

    plt.tight_layout()
    out_png = os.path.join(out_dir, f"{args.out_prefix}_confusion.png")
    plt.savefig(out_png, dpi=200)

    print("Wrote:")
    print(f"- report: {out_json}")
    print(f"- plot:   {out_png}")
    print(f"Accuracy={acc:.3f}  Macro-F1={macro_f1:.3f}  MajorityBaselineAcc={majority_acc:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
