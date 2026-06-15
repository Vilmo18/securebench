# Proposal — PrismVul: Dynamic, Adaptive Secure‑Coding Benchmarking with MCTS + MultiSAST

## 1) Working title (edit later)
**PrismVul: Mapping LLM Secure‑Coding Capability Frontiers via Dynamic Scenario Generation, MCTS Exploration, and Multi‑Tool SAST Triaging**

**One‑sentence pitch:** build a *dynamic* benchmark that automatically generates secure‑coding tasks (by CWE + scenario level), uses MCTS to explore where models succeed/fail, and uses MultiSAST (Bandit + Semgrep + CodeQL) with an LLM triage layer to reduce noise—producing interpretable capability frontiers and root‑cause failure patterns.

---

## 2) Motivation / problem statement
Current secure‑coding evaluations are often:
- **Static** (fixed tasks) → limited coverage, quickly overfit, and poor at discovering *new* failure modes.
- **Hard to interpret** → a single aggregate score hides *where* a model breaks (which weaknesses, under which conditions).
- **Noisy** in practice → SAST tools disagree, produce false positives/negatives, and combine poorly.
- **Weak on difficulty/level control** → labels are often about code length/algorithms, not workflow/security reasoning complexity.

**Goal:** create a benchmark that is *adaptive* (discovers weaknesses), *diagnostic* (explains boundaries), and *reproducible* (auditable artifacts).

This project is inspired by the Prism idea of capability mapping with MCTS (see arXiv:2504.05500), but adapted to **secure‑coding / CWE‑driven evaluation** using SAST and structured analysis.

---

## 3) Core contributions (what’s new)
1. **Dynamic benchmark generator for secure coding**: scenarios are generated on‑the‑fly conditioned on CWE(s) and a **CWE-independent testing condition** (specification clarity, context trustworthiness, risk visibility, constraint pressure, operational realism, compositionality pressure).
2. **MCTS‑driven exploration of the challenge space**: instead of sampling tasks uniformly, we use MCTS to allocate budget to tasks that clarify the model’s capability boundary.
3. **MultiSAST + LLM triage as a noise‑reduction layer**: we run multiple static analyzers and use an LLM as a *reviewer/triager* (filter), not as a fixer, to reduce false positives while preserving recall.
4. **Capability frontier + root‑cause analytics**: Prism‑style plots for frontier detection, exploration dynamics, and failure pattern summaries grounded in artifacts (attempt logs, SAST outputs, triage summaries).

---

## 4) System overview (what the pipeline does)
The benchmark runs in **three phases** over a search tree of *(CWE combination, testing condition)* nodes.

### Phase 1 — Capability mapping (“where can the model succeed?”)
- Prefer exploring tasks the model can solve securely.
- Produces **capability tables**: success/failure rate by CWE and by testing axis.
- Output is used to form an initial frontier estimate.

### Phase 2 — Challenge discovery (“where does the model break?”)
- Shifts exploration toward challenging nodes to find boundary cases.
- Produces a denser set of failures for boundary estimation and for Phase‑3 targeting.

### Phase 3 — Deep analysis (“why does it break?”)
- Selects the most problematic nodes and generates multiple variations per node.
- Extracts persistent SAST tests and summarizes root‑cause categories (e.g., unresolved findings, fixer loops, syntax errors).

**Evaluation mode (PrismVul):**
- Instead of unit tests, we use **SAST** (CodeQL/Semgrep/Bandit) and compute security success from tool outputs after deduplication and triage.
- The “LLM‑as‑judge” is a *triage* layer (filtering false positives), not a source of fix instructions.

---

## 5) Testing-condition taxonomy
Instead of a single scalar difficulty score, we encode the tree axis as a **testing condition taxonomy**.
This keeps the benchmark CWE-independent while making each generated scenario interpretable.

### Axes
- **Specification Clarity:** explicit, implicit, ambiguous, conflicting requirement.
- **Context Trustworthiness:** clean, noisy, unsafe, misleading mitigation context.
- **Risk Visibility:** direct source-to-sink, single-hop, multi-hop, cross-module, hidden sink.
- **Constraint Pressure:** greenfield, minimal patch, legacy compatibility, refactor-only, performance pressure, usability/product pressure.
- **Operational Realism:** toy scenario, single-component app, multi-component service, role/tenant complexity, stateful workflow, concurrent/async setting.
- **Compositionality Pressure:** single weakness, primary+supporting weakness, two-CWE chain, multi-step exploit chain, defense-bypass composition.

**Key rule:** pressure is created by **security reasoning conditions**, not by algorithmic complexity or larger code size.

**How we enforce it:** the scenario designer prompt requires explicit `Condition Axis:` and `Testing Condition:` lines and requires the scenario text to state untrusted inputs, transformations, sensitive sinks, and attacker impact.

---

## 6) Security signal: MultiSAST + triage (how “secure” is decided)
We compute security outcomes primarily from SAST:
- Run **Bandit + Semgrep + CodeQL** (configurable).
- Normalize findings into a common schema and **deduplicate** overlaps.
- Apply thresholds (severity/confidence) and optional **LLM triage**:
  - In `review_only` mode, the judge can mark findings as `TP/FP/UNCERTAIN` with evidence.
  - Judge output is treated as a **filter**, not a fixer. Fix suggestions are suppressed to avoid “cheating”.

**Definition of secure success (configurable per analysis):**
- `sast_clean`: secure if effective findings after triage == 0
- `final`: secure if run’s final `success == true`
- `one_shot` (recommended for Phase 1 capability mapping): secure only if success occurs on attempt 1 (avoids inflating capability with many retries)

This flexibility is important because “success” can mean different things for different research questions:
- Phase‑1 capability mapping should often use **one‑shot** to reflect base capability.
- Phase‑2/3 analyses may use **final** to reflect eventual solvability under iterative attempts.

---

## 7) Research questions (publication‑oriented, tied to benchmark contribution)
Below are RQs designed to be **about the benchmark’s value**, not about specific tools.

### RQ1 — Dynamic benchmark value
**Does an MCTS‑driven, dynamically generated benchmark discover vulnerabilities and capability boundaries more efficiently than static or random sampling?**
- Compare coverage and frontier sharpness at equal compute budget.

### RQ2 — Frontier detection accuracy and stability
**How precisely and stably can we detect secure‑coding capability frontiers across CWE×level under noisy SAST signals?**
- Study the effect of MultiSAST, deduplication, and LLM triage on frontier stability.

### RQ3 — Root causes and failure modes (diagnostic power)
**What recurring implementation patterns explain failures near the boundary, and do they generalize across variations and models?**
- Use Phase‑3 pattern analysis to link persistent SAST tests and code snippets to root‑cause categories.

Optional add‑on (if you want a 4th RQ):
### RQ4 — Level validity (optional)
**Do scenarios labeled by level exhibit increasing measured risk/failure rates, consistent with their intended workflow/attack-surface complexity?**

---

## 8) Experimental design
### Models
Evaluate at least:
- **Code‑specialized** (e.g., CodeLlama / DeepSeek‑Coder)
- **General** (e.g., Llama‑3.x / Mistral)
- Optionally an API model as an upper bound

Record:
- decoding params (temperature, max_tokens)
- context (prompts, system roles)
- attempts budget per node and phase

### Baselines
1. **Random sampling** of (CWE, level) nodes with equal budget.
2. **Static benchmark**: fixed set of scenarios (no adaptive exploration).
3. **Ablations**:
   - MCTS without Phase 2 (no boundary pushing)
   - Single SAST tool vs MultiSAST
   - With vs without judge triage
   - With vs without dedup
   - “Final success” vs “one‑shot success” in capability tables

### Metrics
**Benchmark‑level:**
- coverage: unique CWEs hit, unique CWE‑combos hit, unique level bins explored
- efficiency: boundary discovery per unit compute (runs, tokens, wall time)
- frontier sharpness: how quickly the success→failure transition concentrates

**Model‑level:**
- one‑shot secure success rate by CWE and level
- attempts‑to‑success distribution
- persistent findings across attempts (fixer loops)
- risk distribution (from triage summary + SAST severity/confidence)

**Noise / reliability:**
- tool agreement rates (Bandit vs Semgrep vs CodeQL)
- dedup impact (raw findings vs deduped)
- triage impact (before/after effective findings)

### Statistical analysis
- Confidence intervals via bootstrap over scenarios/nodes.
- Significance tests for baseline comparisons (paired where possible).
- Sensitivity analysis for thresholds (severity/confidence) and MCTS parameters.

---

## 9) Figures / plots (Prism‑style, and how they answer the 4 big questions)
These figures are chosen to directly answer:
1) *dynamic adaptive benchmark*, 2) *MCTS exploration*, 3) *capability frontier*, 4) *root causes*.

### (A) Capability tables (core)
- **CWE capability table**: failure rate by level group (Phase 1, `one_shot` recommended).
- **Frontier heatmap** for top CWE combinations (Phase 2/3).

### (B) MCTS dynamics
- Exploration over time (level × phase, success vs failure markers).
- Tree growth snapshots (nodes / depth / branching).

### (C) Root‑cause summaries (Phase 3)
- Persistent SAST tests by level group (what repeats).
- Failure reasons distribution (why failures happen).
- Optional: per‑CWE root‑cause breakdown (which CWEs drive which failure categories).

### (D) Difficulty validity evidence
- Scenario embedding plots (optional), but stronger: rubric‑compliance + monotonic degradation results.
- Lightweight classifier predicting level from scenario text as a sanity check (report accuracy, confusion matrix).

---

## 10) Threats to validity + mitigations
### SAST noise
- False positives/negatives vary across tools.
  - Mitigation: MultiSAST + dedup + conservative triage (UNCERTAIN when unsure).

### Judge bias / “cheating”
- If the judge provides fixes, it becomes an oracle.
  - Mitigation: judge is *review_only* and fix hints are removed from fixer inputs.

### Difficulty leakage
- “Easy” scenarios accidentally include workflow/state.
  - Mitigation: strict prompt rules + automatic validator (keyword/structure checks) + spot‑check human review.

### Overfitting to generator phrasing
- Models could exploit prompt style.
  - Mitigation: diversify scenario templates; Phase‑3 variations; dedup by semantic similarity.

---

## 11) Ethics and safety
- The benchmark generates **toy but realistic** scenarios; no network access and no external service dependencies.
- We do not publish exploit code; we publish scenarios + safe reference solutions where appropriate.
- Results are used to improve secure coding and benchmarking methodology.

---

## 12) Deliverables
1. Open‑source benchmark runner (PrismBench/PrismVul mode).
2. Scenario corpus + metadata (CWE(s), level, generator seeds, dedup signatures).
3. Run artifacts for reproducibility (attempt logs, SAST outputs, triage summaries).
4. Analysis pipeline + plots (Prism‑style).
5. Paper/report: capability frontiers + root‑cause taxonomy.

---

## 13) Concrete “how to reproduce” (fill with your experiment IDs)
### Run benchmark
```bash
cd pack
./.venv/bin/python src/main.py --mode vuln
```

### Curated Prism‑style plots
```bash
./.venv/bin/python scripts/make_prism_plots_vuln.py --experiment-dir experiments/<EXP_ID>_vuln --curate
```

### CWE capability table (Phase 1, recommended one‑shot)
```bash
./.venv/bin/python scripts/plot_cwe_capability_table_vuln.py \
  --experiments experiments/<EXP_ID>_vuln \
  --phase phase_1 \
  --mode marginal \
  --success-def one_shot \
  --out-prefix cwe_cap_phase1_one_shot
```

---

## 14) References (placeholders)
- Prism (capability mapping with MCTS), arXiv:2504.05500.
- CWE / MITRE: Common Weakness Enumeration.
- Bandit, Semgrep, CodeQL documentation (for tool definitions and rule semantics).

> TODO: add bibtex entries in `references.bib` / `next_refs.bib` and cite them in the paper.
