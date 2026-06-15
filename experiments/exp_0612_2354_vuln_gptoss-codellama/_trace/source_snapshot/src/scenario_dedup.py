from __future__ import annotations

import json
import math
import os
import random
import re
import time
from dataclasses import dataclass
from hashlib import blake2b, sha256
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from loguru import logger


_DEFAULT_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "but",
    "by",
    "can",
    "could",
    "do",
    "does",
    "for",
    "from",
    "have",
    "how",
    "i",
    "if",
    "in",
    "into",
    "is",
    "it",
    "its",
    "must",
    "not",
    "of",
    "on",
    "or",
    "should",
    "so",
    "that",
    "the",
    "their",
    "then",
    "these",
    "this",
    "to",
    "use",
    "using",
    "was",
    "were",
    "when",
    "where",
    "which",
    "with",
    "within",
    "without",
    "you",
    "your",
}


def _project_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))


def normalize_scenario_text(text: str) -> str:
    """
    Normalize scenario text to stabilize hashes/similarity:
    - remove XML-like tags
    - lowercase
    - collapse whitespace
    """
    t = str(text or "")
    t = re.sub(r"<[^>]+>", " ", t)
    t = t.replace("\r\n", "\n").replace("\r", "\n")
    t = t.lower()
    t = re.sub(r"\s+", " ", t).strip()
    return t


def scenario_hash(text: str) -> str:
    return sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def _extract_title(problem_statement: str) -> Optional[str]:
    for line in (problem_statement or "").splitlines():
        s = line.strip()
        if s.startswith("## "):
            title = s[3:].strip()
            return title or None
    return None


def _tokenize(text: str) -> List[str]:
    # Word-ish tokens; keep underscores and digits for stability.
    return re.findall(r"[a-z0-9_]{2,}", text.lower())


def bow_embedding(
    normalized_text: str,
    *,
    ngram_max: int = 2,
    max_features: int = 256,
    stopwords: Optional[Sequence[str]] = None,
) -> Tuple[Dict[str, float], float]:
    """
    Very fast local "embedding": sparse bag-of-words(+ngrams) vector suitable for cosine similarity.
    """
    if max_features <= 0:
        return {}, 0.0

    stop = set(stopwords) if stopwords is not None else _DEFAULT_STOPWORDS
    tokens = [t for t in _tokenize(normalized_text) if t not in stop]

    feats: Dict[str, float] = {}

    def _add(feature: str, inc: float = 1.0) -> None:
        feats[feature] = float(feats.get(feature, 0.0) + inc)

    for tok in tokens:
        _add(tok)

    # Add n-grams to better catch rephrasings with the same structure/phrases.
    # We down-weight longer n-grams so they help disambiguate without overly reducing
    # cosine similarity for near-duplicates with small phrasing changes.
    bigram_weight = 0.25
    trigram_weight = 0.15
    ngram_max = max(1, int(ngram_max))
    if ngram_max >= 2 and len(tokens) >= 2:
        for i in range(len(tokens) - 1):
            _add(f"{tokens[i]}_{tokens[i + 1]}", bigram_weight)
    if ngram_max >= 3 and len(tokens) >= 3:
        for i in range(len(tokens) - 2):
            _add(f"{tokens[i]}_{tokens[i + 1]}_{tokens[i + 2]}", trigram_weight)

    if not feats:
        return {}, 0.0

    # Keep only the top features to bound memory/disk and speed comparisons.
    if len(feats) > max_features:
        items = sorted(feats.items(), key=lambda kv: kv[1], reverse=True)[:max_features]
        feats = {k: float(v) for k, v in items}

    norm = math.sqrt(sum(v * v for v in feats.values())) if feats else 0.0
    return feats, float(norm)


def cosine_similarity_sparse(
    a: Dict[str, float],
    a_norm: float,
    b: Dict[str, float],
    b_norm: float,
) -> float:
    if not a or not b:
        return 0.0
    if a_norm <= 0.0 or b_norm <= 0.0:
        return 0.0
    # Iterate the smaller dict for speed.
    if len(a) > len(b):
        a, b = b, a
        a_norm, b_norm = b_norm, a_norm
    dot = 0.0
    for k, av in a.items():
        bv = b.get(k)
        if bv is not None:
            dot += float(av) * float(bv)
    return float(dot / (a_norm * b_norm))


def _hash64(text: str) -> int:
    """
    Stable 64-bit hash for minhash/simhash-like signatures.
    """
    h = blake2b(str(text or "").encode("utf-8", errors="ignore"), digest_size=8).digest()
    return int.from_bytes(h, "big", signed=False)


def _token_ngrams(tokens: Sequence[str], n: int) -> List[str]:
    n = max(1, int(n))
    if n == 1:
        return [str(t) for t in tokens if str(t)]
    out: List[str] = []
    if len(tokens) < n:
        return out
    for i in range(len(tokens) - n + 1):
        out.append("_".join(tokens[i : i + n]))
    return out


def minhash_signature(
    normalized_text: str,
    *,
    num_perm: int = 64,
    token_ngram: int = 3,
    seed: int = 0,
    stopwords: Optional[Sequence[str]] = None,
) -> List[int]:
    """
    Token-shingle MinHash signature for near-duplicate detection.

    This is more robust than plain BoW cosine when the model keeps the same structure but
    lightly rephrases sentences. It is still lexical (not semantic like sentence embeddings).
    """
    num_perm = max(8, int(num_perm))
    token_ngram = max(1, int(token_ngram))

    stop = set(stopwords) if stopwords is not None else _DEFAULT_STOPWORDS
    tokens = [t for t in _tokenize(normalized_text) if t not in stop]
    shingles = set(_token_ngrams(tokens, token_ngram))
    if not shingles:
        return []

    base_hashes = [_hash64(s) for s in shingles]
    max_hash = (1 << 64) - 1

    rng = random.Random(int(seed))
    # Universal hashing-like parameters (mod 2^64) — stable across processes.
    a = [(rng.getrandbits(64) | 1) & max_hash for _ in range(num_perm)]
    b = [rng.getrandbits(64) & max_hash for _ in range(num_perm)]

    sig: List[int] = []
    for i in range(num_perm):
        ai = a[i]
        bi = b[i]
        min_val = max_hash
        for h in base_hashes:
            v = (ai * h + bi) & max_hash
            if v < min_val:
                min_val = v
        sig.append(int(min_val))
    return sig


def minhash_similarity(sig_a: Sequence[int], sig_b: Sequence[int]) -> float:
    if not sig_a or not sig_b:
        return 0.0
    n = min(len(sig_a), len(sig_b))
    if n <= 0:
        return 0.0
    same = 0
    for i in range(n):
        if int(sig_a[i]) == int(sig_b[i]):
            same += 1
    return float(same / n)


def _default_embeddings_base_url() -> str:
    """
    Default local embeddings endpoint (Ollama OpenAI-compatible).
    """
    endpoint = os.getenv("OLLAMA_ENDPOINT", "http://localhost:11434").rstrip("/")
    return endpoint + "/v1"


def _dense_l2_norm(vec: Sequence[float]) -> float:
    total = 0.0
    for x in vec:
        try:
            v = float(x)
        except Exception:
            v = 0.0
        total += v * v
    return float(math.sqrt(total)) if total > 0.0 else 0.0


def cosine_similarity_dense(
    a: Sequence[float],
    a_norm: float,
    b: Sequence[float],
    b_norm: float,
) -> float:
    if not a or not b:
        return 0.0
    if a_norm <= 0.0 or b_norm <= 0.0:
        return 0.0
    n = min(len(a), len(b))
    if n <= 0:
        return 0.0
    dot = 0.0
    for i in range(n):
        try:
            dot += float(a[i]) * float(b[i])
        except Exception:
            continue
    return float(dot / (float(a_norm) * float(b_norm)))


def _extract_openai_embeddings(resp: Dict[str, Any]) -> Optional[List[List[float]]]:
    data = resp.get("data")
    if isinstance(data, list) and data:
        out: List[List[float]] = []
        for item in data:
            if not isinstance(item, dict):
                return None
            emb = item.get("embedding")
            if not isinstance(emb, list):
                return None
            try:
                out.append([float(x) for x in emb])
            except Exception:
                return None
        return out
    emb = resp.get("embedding")
    if isinstance(emb, list):
        try:
            return [[float(x) for x in emb]]
        except Exception:
            return None
    return None


def semantic_embedding(
    text: str,
    *,
    base_url: Optional[str] = None,
    model: str = "nomic-embed-text",
    api_key: Optional[str] = None,
    timeout_seconds: int = 60,
    max_chars: int = 6000,
) -> Tuple[List[float], float]:
    """
    Sentence-embedding style representation via an OpenAI-compatible /v1/embeddings endpoint.

    Intended for local inference servers (e.g., Ollama). On failure, returns ([], 0.0).
    """
    import urllib.error
    import urllib.request

    base = (base_url or _default_embeddings_base_url()).rstrip("/")
    url = base + "/embeddings"

    payload = {"model": str(model or "").strip() or "nomic-embed-text", "input": [str(text or "")[: max(0, int(max_chars))]]}
    key = api_key or os.getenv("OPENAI_API_KEY") or "local_key"
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    for k, v in headers.items():
        req.add_header(k, v)

    try:
        with urllib.request.urlopen(req, timeout=max(1, int(timeout_seconds))) as resp:
            body = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        logger.opt(exception=True).warning(f"Semantic embedding request failed: {e}")
        return [], 0.0

    try:
        obj = json.loads(body)
    except Exception:
        logger.warning("Semantic embedding endpoint returned non-JSON output.")
        return [], 0.0
    if not isinstance(obj, dict):
        return [], 0.0

    embs = _extract_openai_embeddings(obj)
    if not embs or not embs[0]:
        return [], 0.0
    vec = embs[0]
    return vec, _dense_l2_norm(vec)


@dataclass(frozen=True)
class ScenarioMatch:
    method: str  # "hash" | "cosine" | "minhash" | "semantic"
    similarity: float
    matched_hash: str
    matched_title: Optional[str]


class ScenarioStore:
    def __init__(
        self,
        store_path: str,
        *,
        max_per_bucket: int = 200,
        compare_k: int = 50,
    ) -> None:
        self.store_path = store_path
        self.max_per_bucket = max(1, int(max_per_bucket))
        self.compare_k = max(0, int(compare_k))
        self._buckets: Dict[str, List[Dict[str, Any]]] = {}
        self._hashes: Dict[str, set[str]] = {}

        self._load()

    def _load(self) -> None:
        path = self.store_path
        if not path or not os.path.exists(path):
            return
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
                    bucket = str(rec.get("bucket") or "")
                    h = str(rec.get("hash") or "")
                    if not bucket or not h:
                        continue
                    self._buckets.setdefault(bucket, []).append(rec)
                    self._hashes.setdefault(bucket, set()).add(h)

            # Enforce per-bucket size bounds (keep most recent).
            for bucket, records in list(self._buckets.items()):
                if len(records) > self.max_per_bucket:
                    self._buckets[bucket] = records[-self.max_per_bucket :]
                    self._hashes[bucket] = {str(r.get("hash")) for r in self._buckets[bucket] if r.get("hash")}
        except Exception as e:
            logger.opt(exception=True).warning(f"Failed to load scenario store {path}: {e}")

    def _append(self, rec: Dict[str, Any]) -> None:
        path = self.store_path
        if not path:
            return
        try:
            parent = os.path.dirname(path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.opt(exception=True).warning(f"Failed to persist scenario record to {path}: {e}")

    def has_hash(self, bucket: str, h: str) -> bool:
        return bool(h and bucket and (h in self._hashes.get(bucket, set())))

    def iter_candidates(self, bucket: str) -> Iterable[Dict[str, Any]]:
        records = self._buckets.get(bucket) or []
        if not records:
            return []
        if self.compare_k <= 0:
            return []
        return records[-self.compare_k :]

    def add(self, bucket: str, rec: Dict[str, Any]) -> None:
        if not bucket or not isinstance(rec, dict):
            return
        h = str(rec.get("hash") or "")
        if not h:
            return
        if self.has_hash(bucket, h):
            return

        self._buckets.setdefault(bucket, []).append(rec)
        self._hashes.setdefault(bucket, set()).add(h)
        if len(self._buckets[bucket]) > self.max_per_bucket:
            # Drop oldest.
            dropped = self._buckets[bucket].pop(0)
            dh = str(dropped.get("hash") or "")
            if dh:
                self._hashes[bucket].discard(dh)

        self._append(rec)


class ScenarioDeduplicator:
    """
    Anti-duplication filter for generated scenarios.

    Two-stage detection:
      1) Normalization + SHA-256 hash for exact duplicates
      2) Near-duplicate detection (configurable):
         - "bow": local BoW+n-grams cosine similarity (fast)
         - "minhash": token-shingle MinHash similarity (fast, more robust to light rephrasing)
         - "semantic": sentence embeddings via /v1/embeddings + cosine similarity (semantic, slower)

    Notes on latency:
      - Hash check is O(1) and avoids embedding work for exact duplicates.
      - Cosine checks compare only against the last `compare_k` items per bucket.
    """

    def __init__(
        self,
        *,
        enabled: bool = False,
        store_scope: str = "run",  # global|run|phase
        store_path: Optional[str] = None,
        cosine_threshold: float = 0.93,
        similarity_method: str = "bow",  # bow|minhash|semantic|bow+semantic|minhash+semantic
        minhash_threshold: float = 0.82,
        minhash_num_perm: int = 64,
        minhash_token_ngram: int = 3,
        semantic_enabled: bool = False,
        semantic_threshold: float = 0.92,
        semantic_model: str = "nomic-embed-text",
        semantic_base_url: Optional[str] = None,
        semantic_timeout_seconds: int = 60,
        semantic_max_chars: int = 6000,
        max_regen: int = 3,
        accept_after_max_regen: bool = True,
        max_per_bucket: int = 200,
        compare_k: int = 50,
        ngram_max: int = 2,
        max_features: int = 256,
        mode: str = "vuln",
    ) -> None:
        self.enabled = bool(enabled)
        self.mode = str(mode or "vuln").strip().lower()
        self.store_scope = str(store_scope or "run").strip().lower()
        self.cosine_threshold = max(0.0, min(1.0, float(cosine_threshold)))
        self.similarity_method = str(similarity_method or "bow").strip().lower()
        self.minhash_threshold = max(0.0, min(1.0, float(minhash_threshold)))
        self.minhash_num_perm = max(8, int(minhash_num_perm))
        self.minhash_token_ngram = max(1, int(minhash_token_ngram))
        self.semantic_enabled = bool(semantic_enabled) or ("semantic" in self.similarity_method)
        self.semantic_threshold = max(0.0, min(1.0, float(semantic_threshold)))
        self.semantic_model = str(semantic_model or "nomic-embed-text").strip() or "nomic-embed-text"
        self.semantic_base_url = (str(semantic_base_url).strip() if semantic_base_url else None) or None
        self.semantic_timeout_seconds = max(1, int(semantic_timeout_seconds))
        self.semantic_max_chars = max(256, int(semantic_max_chars))
        self.max_regen = max(0, int(max_regen))
        self.accept_after_max_regen = bool(accept_after_max_regen)

        self.ngram_max = max(1, int(ngram_max))
        self.max_features = max(8, int(max_features))

        # Small handoff cache between check_duplicate() and add() to avoid recomputing expensive embeddings.
        self._last_candidate: Optional[Dict[str, Any]] = None

        self._explicit_store_path = store_path
        self._max_per_bucket = max_per_bucket
        self._compare_k = compare_k
        self._experiment_path: Optional[str] = None

        # Initialized lazily once we know the concrete store path.
        self._store: Optional[ScenarioStore] = None
        self._ensure_store()

    @classmethod
    def from_configs(cls, cfg: Optional[Dict[str, Any]], *, mode: str) -> "ScenarioDeduplicator":
        c = cfg or {}
        if not isinstance(c, dict):
            c = {}
        minhash_cfg = c.get("minhash") if isinstance(c.get("minhash"), dict) else {}
        semantic_cfg = c.get("semantic") if isinstance(c.get("semantic"), dict) else {}
        return cls(
            enabled=bool(c.get("enabled", False)),
            store_scope=str(c.get("scope", c.get("store_scope", "run"))),
            store_path=c.get("store_path"),
            cosine_threshold=float(c.get("cosine_threshold", 0.93)),
            similarity_method=str(c.get("method", c.get("similarity_method", "bow"))),
            minhash_threshold=float(minhash_cfg.get("threshold", c.get("minhash_threshold", 0.82))),
            minhash_num_perm=int(minhash_cfg.get("num_perm", c.get("minhash_num_perm", 64))),
            minhash_token_ngram=int(minhash_cfg.get("token_ngram", c.get("minhash_token_ngram", 3))),
            semantic_enabled=bool(semantic_cfg.get("enabled", c.get("semantic_enabled", False))),
            semantic_threshold=float(semantic_cfg.get("threshold", c.get("semantic_threshold", 0.92))),
            semantic_model=str(semantic_cfg.get("model", c.get("semantic_model", "nomic-embed-text"))),
            semantic_base_url=semantic_cfg.get("base_url", c.get("semantic_base_url")),
            semantic_timeout_seconds=int(semantic_cfg.get("timeout_seconds", c.get("semantic_timeout_seconds", 60))),
            semantic_max_chars=int(semantic_cfg.get("max_chars", c.get("semantic_max_chars", 6000))),
            max_regen=int(c.get("max_regen", 3)),
            accept_after_max_regen=bool(c.get("accept_after_max_regen", True)),
            max_per_bucket=int(c.get("max_per_bucket", 200)),
            compare_k=int(c.get("compare_k", 50)),
            ngram_max=int(c.get("ngram_max", 2)),
            max_features=int(c.get("max_features", 256)),
            mode=mode,
        )

    def set_experiment_path(self, path: Optional[str]) -> None:
        self._experiment_path = path or None
        self._ensure_store(force=True)

    def max_regenerations(self) -> int:
        return self.max_regen

    def allow_accept_after_max_regen(self) -> bool:
        return self.accept_after_max_regen

    def bucket_key(self, concepts: Any, difficulty_level: str, attack_surface: Any = None) -> str:
        if isinstance(concepts, (list, tuple, set)):
            parts = [str(c).strip() for c in concepts if str(c).strip()]
        else:
            parts = [str(concepts).strip()] if str(concepts).strip() else []
        parts = sorted(set(parts))
        diff = str(difficulty_level or "").strip().lower()
        surface = str(attack_surface or "").strip().lower()
        return f"{self.mode}|{','.join(parts)}|{diff}|{surface}"

    def _derive_store_path(self) -> str:
        # If explicitly set in configs, honor it.
        if self._explicit_store_path:
            p = str(self._explicit_store_path)
            if not os.path.isabs(p):
                p = os.path.join(_project_root(), p)
            return p

        scope = self.store_scope
        exp = self._experiment_path
        if exp and scope in {"run", "phase"}:
            base = exp if scope == "phase" else os.path.dirname(exp)
            return os.path.join(base, "scenario_store.jsonl")

        return os.path.join(_project_root(), ".cache", "scenario_store.jsonl")

    def _ensure_store(self, *, force: bool = False) -> None:
        if not self.enabled:
            self._store = None
            return
        path = self._derive_store_path()
        if not force and self._store is not None and self._store.store_path == path:
            return
        self._store = ScenarioStore(
            path,
            max_per_bucket=self._max_per_bucket,
            compare_k=self._compare_k,
        )

    def check_duplicate(
        self,
        bucket: str,
        problem_statement: str,
    ) -> Optional[ScenarioMatch]:
        if not self.enabled:
            return None
        if not bucket:
            return None
        if not self._store:
            self._ensure_store()
        if not self._store:
            return None

        normalized = normalize_scenario_text(problem_statement)
        h = scenario_hash(normalized)
        self._last_candidate = {"bucket": bucket, "hash": h, "normalized": normalized}
        if self._store.has_hash(bucket, h):
            return ScenarioMatch(method="hash", similarity=1.0, matched_hash=h, matched_title=_extract_title(problem_statement))

        method = self.similarity_method or "bow"

        def _bow_stage() -> Optional[ScenarioMatch]:
            if self.cosine_threshold <= 0.0:
                return None

            emb, emb_norm = bow_embedding(
                normalized,
                ngram_max=self.ngram_max,
                max_features=self.max_features,
            )
            self._last_candidate["bow_embedding"] = emb
            self._last_candidate["bow_embedding_norm"] = emb_norm
            if not emb or emb_norm <= 0:
                return None

            for rec in self._store.iter_candidates(bucket):
                if not isinstance(rec, dict):
                    continue
                other = rec.get("embedding")
                other_norm = rec.get("embedding_norm")
                if not isinstance(other, dict):
                    continue
                try:
                    other_norm_f = float(other_norm)
                except Exception:
                    other_norm_f = 0.0
                sim = cosine_similarity_sparse(emb, emb_norm, other, other_norm_f)
                if sim >= self.cosine_threshold:
                    oh = str(rec.get("hash") or "")
                    return ScenarioMatch(
                        method="cosine",
                        similarity=float(sim),
                        matched_hash=oh or "",
                        matched_title=rec.get("title"),
                    )
            return None

        def _minhash_stage() -> Optional[ScenarioMatch]:
            if self.minhash_threshold <= 0.0:
                return None
            sig = minhash_signature(
                normalized,
                num_perm=self.minhash_num_perm,
                token_ngram=self.minhash_token_ngram,
                seed=0,
            )
            self._last_candidate["minhash"] = sig
            if not sig:
                return None
            for rec in self._store.iter_candidates(bucket):
                if not isinstance(rec, dict):
                    continue
                other_sig = rec.get("minhash")
                if not isinstance(other_sig, list):
                    # Backward-compat: compute on the fly from stored normalized text.
                    other_norm_txt = rec.get("normalized")
                    if isinstance(other_norm_txt, str) and other_norm_txt.strip():
                        other_sig = minhash_signature(
                            other_norm_txt,
                            num_perm=self.minhash_num_perm,
                            token_ngram=self.minhash_token_ngram,
                            seed=0,
                        )
                    else:
                        continue
                sim = minhash_similarity(sig, other_sig)
                if sim >= self.minhash_threshold:
                    oh = str(rec.get("hash") or "")
                    return ScenarioMatch(
                        method="minhash",
                        similarity=float(sim),
                        matched_hash=oh or "",
                        matched_title=rec.get("title"),
                    )
            return None

        def _semantic_stage() -> Optional[ScenarioMatch]:
            if not self.semantic_enabled:
                return None
            if self.semantic_threshold <= 0.0:
                return None

            vec, vec_norm = semantic_embedding(
                problem_statement,
                base_url=self.semantic_base_url,
                model=self.semantic_model,
                timeout_seconds=self.semantic_timeout_seconds,
                max_chars=self.semantic_max_chars,
            )
            self._last_candidate["semantic_embedding"] = vec
            self._last_candidate["semantic_embedding_norm"] = vec_norm
            if not vec or vec_norm <= 0:
                return None

            for rec in self._store.iter_candidates(bucket):
                if not isinstance(rec, dict):
                    continue
                other_vec = rec.get("semantic_embedding")
                other_norm = rec.get("semantic_embedding_norm")
                if not isinstance(other_vec, list):
                    continue
                try:
                    other_norm_f = float(other_norm)
                except Exception:
                    other_norm_f = 0.0
                sim = cosine_similarity_dense(vec, vec_norm, other_vec, other_norm_f)
                if sim >= self.semantic_threshold:
                    oh = str(rec.get("hash") or "")
                    return ScenarioMatch(
                        method="semantic",
                        similarity=float(sim),
                        matched_hash=oh or "",
                        matched_title=rec.get("title"),
                    )
            return None

        # Execute near-dup stages in the configured order.
        if method in {"bow", "bow+semantic", "cosine"}:
            m = _bow_stage()
            if m is not None:
                return m
        if method in {"minhash", "minhash+semantic"}:
            m = _minhash_stage()
            if m is not None:
                return m
        if "semantic" in method:
            m = _semantic_stage()
            if m is not None:
                return m

        # Fallback for unknown method values: keep existing behavior.
        if method not in {"bow", "bow+semantic", "cosine", "minhash", "minhash+semantic", "semantic"}:
            return _bow_stage()

        return None

    def add(
        self,
        bucket: str,
        problem_statement: str,
        *,
        meta: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not self.enabled:
            return
        if not bucket:
            return
        if not self._store:
            self._ensure_store()
        if not self._store:
            return

        normalized = normalize_scenario_text(problem_statement)
        h = scenario_hash(normalized)
        if self._store.has_hash(bucket, h):
            return

        cached = self._last_candidate if isinstance(self._last_candidate, dict) else None
        cache_hit = bool(cached and cached.get("bucket") == bucket and cached.get("hash") == h)

        if cache_hit and isinstance(cached.get("bow_embedding"), dict):
            emb = cached.get("bow_embedding") or {}
            emb_norm = float(cached.get("bow_embedding_norm") or 0.0)
        else:
            emb, emb_norm = bow_embedding(
                normalized,
                ngram_max=self.ngram_max,
                max_features=self.max_features,
            )

        # Optional extra representations for near-dup detection.
        mh: List[int] = []
        if "minhash" in (self.similarity_method or ""):
            if cache_hit and isinstance(cached.get("minhash"), list):
                mh = cached.get("minhash") or []
            else:
                mh = minhash_signature(
                    normalized,
                    num_perm=self.minhash_num_perm,
                    token_ngram=self.minhash_token_ngram,
                    seed=0,
                )

        sem_vec: List[float] = []
        sem_norm = 0.0
        if self.semantic_enabled:
            if cache_hit and isinstance(cached.get("semantic_embedding"), list):
                sem_vec = cached.get("semantic_embedding") or []
                try:
                    sem_norm = float(cached.get("semantic_embedding_norm") or 0.0)
                except Exception:
                    sem_norm = 0.0
            else:
                sem_vec, sem_norm = semantic_embedding(
                    problem_statement,
                    base_url=self.semantic_base_url,
                    model=self.semantic_model,
                    timeout_seconds=self.semantic_timeout_seconds,
                    max_chars=self.semantic_max_chars,
                )

        record = {
            "bucket": bucket,
            "hash": h,
            "title": _extract_title(problem_statement),
            "created_at": time.time(),
            "problem_statement": problem_statement,
            "normalized": normalized,
            "embedding": emb,
            "embedding_norm": emb_norm,
            "meta": dict(meta or {}),
        }
        if mh:
            record["minhash"] = mh
            record["minhash_num_perm"] = int(self.minhash_num_perm)
            record["minhash_token_ngram"] = int(self.minhash_token_ngram)
        if sem_vec and sem_norm > 0.0:
            record["semantic_embedding"] = sem_vec
            record["semantic_embedding_norm"] = float(sem_norm)
            record["semantic_model"] = str(self.semantic_model)
            record["semantic_base_url"] = str(self.semantic_base_url or _default_embeddings_base_url())
        self._store.add(bucket, record)
